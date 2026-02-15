/**
 * STIX End-to-End Flow Test
 * Demonstrates the complete authorization flow
 */

import { describe, it, expect, beforeAll } from 'vitest';
import {
  type Actor,
  type Resource,
  type Context,
  type PolicyArtifact,
  type DecisionKind,
  
  // Utils
  generateTraceId,
  generateEventId,
  generateApprovalTicketId,
  hashCanonical,
  isoTimestamp,
  addSeconds,
  ZERO_HASH,
  
  // Crypto
  generateEd25519KeyPair,
  InMemoryKeyStore,
  createProofToken,
  signEvidence,
  
  // Validators
  validatePolicyArtifact,
  
  // Constants
  REASON_CODES,
} from '@stix/shared';

// Mock Policy Store
class MockPolicyStore {
  private policies: Map<string, PolicyArtifact> = new Map();

  addPolicy(policy: PolicyArtifact): void {
    const validated = validatePolicyArtifact(policy);
    this.policies.set(validated.policy_id, validated);
  }

  findMatching(actor: Actor, action: string, resource: Resource): PolicyArtifact[] {
    return Array.from(this.policies.values()).filter(policy => {
      // Check actor type
      if (policy.scope.actor_type !== '*' && policy.scope.actor_type !== actor.type) {
        return false;
      }
      
      // Check action (support wildcards)
      if (policy.scope.action !== '*') {
        const pattern = policy.scope.action.replace('*', '.*');
        if (!new RegExp(`^${pattern}$`).test(action)) {
          return false;
        }
      }
      
      // Check resource type
      if (policy.scope.resource_type !== '*' && policy.scope.resource_type !== resource.type) {
        return false;
      }
      
      return true;
    });
  }

  evaluate(policies: PolicyArtifact[]): { decision: DecisionKind; policy: PolicyArtifact | null; reasonCode: string } {
    if (policies.length === 0) {
      return { decision: 'DENY', policy: null, reasonCode: REASON_CODES.NO_MATCHING_POLICY };
    }

    // Sort by priority
    const sorted = [...policies].sort((a, b) => (a.priority ?? 100) - (b.priority ?? 100));

    // Deny wins at same priority
    for (const policy of sorted) {
      if (policy.decision === 'DENY') {
        return { decision: 'DENY', policy, reasonCode: policy.reason_code };
      }
    }

    // Check for quarantine
    for (const policy of sorted) {
      if (policy.decision === 'QUARANTINE') {
        return { decision: 'QUARANTINE', policy, reasonCode: policy.reason_code };
      }
    }

    // Allow (highest priority)
    const allowPolicy = sorted.find(p => p.decision === 'ALLOW');
    if (allowPolicy) {
      return { decision: 'ALLOW', policy: allowPolicy, reasonCode: allowPolicy.reason_code };
    }

    return { decision: 'DENY', policy: null, reasonCode: REASON_CODES.NO_MATCHING_POLICY };
  }
}

// Mock Evidence Store
class MockEvidenceStore {
  private events: Map<string, unknown> = new Map();
  private traceIndex: Map<string, string[]> = new Map();
  private lastHash: string = ZERO_HASH;
  private keyStore: InMemoryKeyStore;

  constructor(keyStore: InMemoryKeyStore) {
    this.keyStore = keyStore;
  }

  async recordDecision(
    traceId: string,
    decision: DecisionKind,
    actor: Actor,
    action: string,
    resource: Resource,
    policy: PolicyArtifact | null
  ): Promise<{ eventId: string; eventHash: string }> {
    const eventId = generateEventId();
    const signingKey = await this.keyStore.getSigningKey();

    const eventData = {
      schema_version: '1.0',
      event_id: eventId,
      trace_id: traceId,
      timestamp: isoTimestamp(),
      decision,
      reason_code: policy?.reason_code ?? REASON_CODES.NO_MATCHING_POLICY,
      actor,
      action: { name: action },
      resource,
      context: { env: 'test' },
      policy: policy ? {
        id: policy.policy_id,
        version: policy.version,
        hash: hashCanonical(policy),
      } : {
        id: 'default_deny',
        version: '1.0.0',
        hash: ZERO_HASH,
      },
      controls: policy?.controls ?? [],
      regulations: policy?.regulations ?? [],
    };

    const signResult = signEvidence(eventData, this.lastHash, signingKey);

    const event = {
      ...eventData,
      integrity: {
        event_hash: signResult.eventHash,
        prev_hash: this.lastHash,
        signature: signResult.signature,
        key_id: signResult.keyId,
      },
    };

    this.events.set(eventId, event);
    this.lastHash = signResult.eventHash;

    const traceEvents = this.traceIndex.get(traceId) ?? [];
    traceEvents.push(eventId);
    this.traceIndex.set(traceId, traceEvents);

    return { eventId, eventHash: signResult.eventHash };
  }

  getEventsByTrace(traceId: string): unknown[] {
    const eventIds = this.traceIndex.get(traceId) ?? [];
    return eventIds.map(id => this.events.get(id)).filter(Boolean);
  }

  verifyChain(): { valid: boolean; count: number } {
    const events = Array.from(this.events.values()) as Array<{
      integrity: { event_hash: string; prev_hash: string };
    }>;
    
    let prevHash = ZERO_HASH;
    for (const event of events) {
      if (event.integrity.prev_hash !== prevHash) {
        return { valid: false, count: events.length };
      }
      prevHash = event.integrity.event_hash;
    }

    return { valid: true, count: events.length };
  }
}

// Mock Approvals Store
class MockApprovalsStore {
  private tickets: Map<string, {
    ticketId: string;
    traceId: string;
    status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
    expiresAt: string;
    approvals: Array<{ approverId: string; timestamp: string }>;
  }> = new Map();

  createTicket(traceId: string, expiresInSeconds: number): string {
    const ticketId = generateApprovalTicketId();
    this.tickets.set(ticketId, {
      ticketId,
      traceId,
      status: 'PENDING',
      expiresAt: addSeconds(expiresInSeconds),
      approvals: [],
    });
    return ticketId;
  }

  approve(ticketId: string, approverId: string): boolean {
    const ticket = this.tickets.get(ticketId);
    if (!ticket || ticket.status !== 'PENDING') {
      return false;
    }

    ticket.approvals.push({ approverId, timestamp: isoTimestamp() });
    ticket.status = 'APPROVED';
    return true;
  }

  isApproved(ticketId: string): boolean {
    const ticket = this.tickets.get(ticketId);
    return ticket?.status === 'APPROVED';
  }

  getTicket(ticketId: string) {
    return this.tickets.get(ticketId);
  }
}

// Simulated Enforcer
class MockEnforcer {
  private policyStore: MockPolicyStore;
  private evidenceStore: MockEvidenceStore;
  private approvalsStore: MockApprovalsStore;
  private keyStore: InMemoryKeyStore;

  constructor(
    policyStore: MockPolicyStore,
    evidenceStore: MockEvidenceStore,
    approvalsStore: MockApprovalsStore,
    keyStore: InMemoryKeyStore
  ) {
    this.policyStore = policyStore;
    this.evidenceStore = evidenceStore;
    this.approvalsStore = approvalsStore;
    this.keyStore = keyStore;
  }

  async authorize(
    actor: Actor,
    action: string,
    resource: Resource,
    _context: Context
  ): Promise<{
    decision: DecisionKind;
    traceId: string;
    reasonCode: string;
    proofToken?: string;
    approvalTicketId?: string;
  }> {
    const traceId = generateTraceId();

    // Find matching policies
    const matchingPolicies = this.policyStore.findMatching(actor, action, resource);

    // Evaluate policies
    const { decision, policy, reasonCode } = this.policyStore.evaluate(matchingPolicies);

    // Record evidence
    await this.evidenceStore.recordDecision(traceId, decision, actor, action, resource, policy);

    // Build response
    const response: {
      decision: DecisionKind;
      traceId: string;
      reasonCode: string;
      proofToken?: string;
      approvalTicketId?: string;
    } = {
      decision,
      traceId,
      reasonCode,
    };

    // Generate proof token for ALLOW
    if (decision === 'ALLOW') {
      const signingKey = await this.keyStore.getSigningKey();
      response.proofToken = createProofToken(
        {
          iss: 'stix',
          sub: actor.id,
          act: action,
          res: resource.type,
          cls: resource.classification ?? [],
          pol: policy ? hashCanonical(policy) : ZERO_HASH,
          tid: traceId,
          iat: Math.floor(Date.now() / 1000),
          exp: Math.floor(Date.now() / 1000) + 300,
        },
        signingKey
      );
    }

    // Create approval ticket for QUARANTINE
    if (decision === 'QUARANTINE') {
      response.approvalTicketId = this.approvalsStore.createTicket(traceId, 3600);
    }

    return response;
  }

  getEvidenceStore(): MockEvidenceStore {
    return this.evidenceStore;
  }

  getApprovalsStore(): MockApprovalsStore {
    return this.approvalsStore;
  }
}

describe('STIX End-to-End Flow', () => {
  let keyStore: InMemoryKeyStore;
  let policyStore: MockPolicyStore;
  let evidenceStore: MockEvidenceStore;
  let approvalsStore: MockApprovalsStore;
  let enforcer: MockEnforcer;

  beforeAll(() => {
    // Initialize key store
    keyStore = new InMemoryKeyStore();
    keyStore.addKeyPair(generateEd25519KeyPair());

    // Initialize stores
    policyStore = new MockPolicyStore();
    evidenceStore = new MockEvidenceStore(keyStore);
    approvalsStore = new MockApprovalsStore();

    // Initialize enforcer
    enforcer = new MockEnforcer(policyStore, evidenceStore, approvalsStore, keyStore);

    // Add sample policies
    policyStore.addPolicy({
      policy_id: 'allow-low-risk-read',
      version: '1.0.0',
      priority: 100,
      scope: {
        actor_type: 'AI_AGENT',
        action: 'read_*',
        resource_type: 'public_data',
      },
      decision: 'ALLOW',
      reason_code: 'LOW_RISK_READ',
      controls: ['SOC2:CC6.1'],
    });

    policyStore.addPolicy({
      policy_id: 'quarantine-high-risk',
      version: '1.0.0',
      priority: 50,
      scope: {
        actor_type: 'AI_AGENT',
        action: '*',
        resource_type: 'sensitive_data',
      },
      decision: 'QUARANTINE',
      reason_code: 'HIGH_RISK_REQUIRES_APPROVAL',
      approval: {
        approver_role: 'security_admin',
        require_count: 1,
        timeout_hours: 24,
      },
      controls: ['SOC2:CC6.1', 'HIPAA:164.502'],
    });

    policyStore.addPolicy({
      policy_id: 'deny-production-access',
      version: '1.0.0',
      priority: 10,
      scope: {
        actor_type: 'AI_AGENT',
        action: 'write_*',
        resource_type: 'production_db',
      },
      decision: 'DENY',
      reason_code: 'PRODUCTION_WRITE_BLOCKED',
      controls: ['SOC2:CC8.1'],
    });
  });

  describe('ALLOW Flow', () => {
    it('should allow low-risk read operations', async () => {
      const result = await enforcer.authorize(
        { id: 'agent-1', type: 'AI_AGENT' },
        'read_file',
        { type: 'public_data', id: 'file-123' },
        { env: 'dev' }
      );

      expect(result.decision).toBe('ALLOW');
      expect(result.reasonCode).toBe('LOW_RISK_READ');
      expect(result.proofToken).toBeTruthy();
      expect(result.traceId).toMatch(/^stix_/);
    });

    it('should generate valid proof tokens', async () => {
      const result = await enforcer.authorize(
        { id: 'agent-2', type: 'AI_AGENT' },
        'read_data',
        { type: 'public_data' },
        { env: 'dev' }
      );

      expect(result.proofToken).toBeTruthy();
      
      // Token should have 3 parts (header.payload.signature)
      const parts = result.proofToken!.split('.');
      expect(parts).toHaveLength(3);
    });
  });

  describe('DENY Flow', () => {
    it('should deny production write operations', async () => {
      const result = await enforcer.authorize(
        { id: 'agent-1', type: 'AI_AGENT' },
        'write_record',
        { type: 'production_db', id: 'table-1' },
        { env: 'prod' }
      );

      expect(result.decision).toBe('DENY');
      expect(result.reasonCode).toBe('PRODUCTION_WRITE_BLOCKED');
      expect(result.proofToken).toBeUndefined();
    });

    it('should deny when no matching policy exists', async () => {
      const result = await enforcer.authorize(
        { id: 'human-1', type: 'HUMAN' },
        'unknown_action',
        { type: 'unknown_resource' },
        { env: 'dev' }
      );

      expect(result.decision).toBe('DENY');
      expect(result.reasonCode).toBe(REASON_CODES.NO_MATCHING_POLICY);
    });
  });

  describe('QUARANTINE Flow', () => {
    it('should quarantine high-risk operations', async () => {
      const result = await enforcer.authorize(
        { id: 'agent-1', type: 'AI_AGENT' },
        'access_sensitive',
        { type: 'sensitive_data', id: 'record-1' },
        { env: 'prod' }
      );

      expect(result.decision).toBe('QUARANTINE');
      expect(result.reasonCode).toBe('HIGH_RISK_REQUIRES_APPROVAL');
      expect(result.approvalTicketId).toMatch(/^appr_/);
    });

    it('should allow operation after approval', async () => {
      const result = await enforcer.authorize(
        { id: 'agent-1', type: 'AI_AGENT' },
        'access_sensitive',
        { type: 'sensitive_data' },
        { env: 'prod' }
      );

      expect(result.decision).toBe('QUARANTINE');
      expect(result.approvalTicketId).toBeTruthy();

      // Approve the ticket
      const approved = enforcer.getApprovalsStore().approve(
        result.approvalTicketId!,
        'admin-1'
      );
      expect(approved).toBe(true);

      // Verify approval
      const isApproved = enforcer.getApprovalsStore().isApproved(result.approvalTicketId!);
      expect(isApproved).toBe(true);
    });
  });

  describe('Evidence & Audit Trail', () => {
    it('should record all decisions in evidence store', async () => {
      const result = await enforcer.authorize(
        { id: 'agent-3', type: 'AI_AGENT' },
        'read_file',
        { type: 'public_data' },
        { env: 'dev' }
      );

      const events = enforcer.getEvidenceStore().getEventsByTrace(result.traceId);
      expect(events).toHaveLength(1);
    });

    it('should maintain hash chain integrity', async () => {
      // Make several authorization requests
      for (let i = 0; i < 5; i++) {
        await enforcer.authorize(
          { id: `agent-${i}`, type: 'AI_AGENT' },
          'read_file',
          { type: 'public_data' },
          { env: 'dev' }
        );
      }

      const chainVerification = enforcer.getEvidenceStore().verifyChain();
      expect(chainVerification.valid).toBe(true);
      expect(chainVerification.count).toBeGreaterThanOrEqual(5);
    });
  });

  describe('Priority & Conflict Resolution', () => {
    it('should respect policy priority (deny-wins at same level)', async () => {
      // Add conflicting policies at same priority
      policyStore.addPolicy({
        policy_id: 'conflict-allow',
        version: '1.0.0',
        priority: 50,
        scope: {
          actor_type: 'AI_AGENT',
          action: 'conflicting_action',
          resource_type: 'conflict_resource',
        },
        decision: 'ALLOW',
        reason_code: 'CONFLICT_ALLOW',
      });

      policyStore.addPolicy({
        policy_id: 'conflict-deny',
        version: '1.0.0',
        priority: 50,
        scope: {
          actor_type: 'AI_AGENT',
          action: 'conflicting_action',
          resource_type: 'conflict_resource',
        },
        decision: 'DENY',
        reason_code: 'CONFLICT_DENY',
      });

      const result = await enforcer.authorize(
        { id: 'agent-1', type: 'AI_AGENT' },
        'conflicting_action',
        { type: 'conflict_resource' },
        { env: 'dev' }
      );

      // Deny should win at same priority
      expect(result.decision).toBe('DENY');
      expect(result.reasonCode).toBe('CONFLICT_DENY');
    });
  });
});
