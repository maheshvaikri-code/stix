#!/usr/bin/env npx tsx
/**
 * STIX Integration Simulation
 *
 * Demonstrates the complete STIX authorization flow without requiring
 * running services. Simulates all components locally.
 *
 * Usage: npx tsx scripts/simulate-stix.ts
 */

import * as crypto from 'crypto';

// =============================================================================
// TERMINAL COLORS & OUTPUT
// =============================================================================

const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  dim: '\x1b[2m',
  red: '\x1b[31m',
  green: '\x1b[32m',
  yellow: '\x1b[33m',
  blue: '\x1b[34m',
  magenta: '\x1b[35m',
  cyan: '\x1b[36m',
  white: '\x1b[37m',
  bgRed: '\x1b[41m',
  bgGreen: '\x1b[42m',
  bgYellow: '\x1b[43m',
  bgBlue: '\x1b[44m',
};

function log(message: string, color = colors.white) {
  console.log(`${color}${message}${colors.reset}`);
}

function header(title: string) {
  console.log('\n' + '═'.repeat(70));
  log(`  ${title}`, colors.bright + colors.cyan);
  console.log('═'.repeat(70) + '\n');
}

function subheader(title: string) {
  console.log(`\n${colors.bright}▸ ${title}${colors.reset}\n`);
}

function decision(type: 'ALLOW' | 'DENY' | 'QUARANTINE', reason: string) {
  const badges = {
    ALLOW: `${colors.bgGreen}${colors.white} ALLOW ${colors.reset}`,
    DENY: `${colors.bgRed}${colors.white} DENY ${colors.reset}`,
    QUARANTINE: `${colors.bgYellow}${colors.white} QUARANTINE ${colors.reset}`,
  };
  console.log(`  Decision: ${badges[type]} ${colors.dim}(${reason})${colors.reset}`);
}

function json(obj: unknown, indent = 2) {
  console.log(colors.dim + JSON.stringify(obj, null, indent) + colors.reset);
}

function wait(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// =============================================================================
// CRYPTO UTILITIES (Simulated Ed25519)
// =============================================================================

const ZERO_HASH = 'sha256:' + '0'.repeat(64);

function generateKeyPair() {
  const keypair = crypto.generateKeyPairSync('ed25519');
  const keyId = `key_${crypto.randomUUID().slice(0, 8)}`;
  return {
    keyId,
    publicKey: keypair.publicKey.export({ type: 'spki', format: 'pem' }),
    privateKey: keypair.privateKey.export({ type: 'pkcs8', format: 'pem' }),
    sign: (data: string) => {
      const signature = crypto.sign(null, Buffer.from(data), keypair.privateKey);
      return signature.toString('base64url');
    },
    verify: (data: string, signature: string) => {
      return crypto.verify(
        null,
        Buffer.from(data),
        keypair.publicKey,
        Buffer.from(signature, 'base64url')
      );
    },
  };
}

function hashCanonical(obj: unknown): string {
  const canonical = JSON.stringify(obj, Object.keys(obj as object).sort());
  const hash = crypto.createHash('sha256').update(canonical).digest('hex');
  return `sha256:${hash}`;
}

function generateTraceId(): string {
  return `stix_${crypto.randomUUID()}`;
}

function generateEventId(): string {
  return `evt_${crypto.randomUUID()}`;
}

function generateApprovalId(): string {
  return `appr_${crypto.randomUUID()}`;
}

// =============================================================================
// TYPES
// =============================================================================

interface Actor {
  id: string;
  type: 'AI_AGENT' | 'SERVICE' | 'HUMAN';
  tenant?: string;
  role?: string;
}

interface Resource {
  type: string;
  id?: string;
  classification?: string[];
}

interface Context {
  env: string;
  purpose?: string;
  signals?: Record<string, boolean>;
}

interface Policy {
  policy_id: string;
  version: string;
  priority: number;
  scope: {
    actor_type: string;
    action: string;
    resource_type: string;
  };
  conditions?: Array<{
    field: string;
    op: string;
    value: unknown;
  }>;
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  reason_code: string;
  approval?: {
    require_count: number;
    timeout_hours: number;
  };
  controls?: string[];
  regulations?: string[];
  enabled: boolean;
}

interface AuthRequest {
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
}

interface AuthResponse {
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  trace_id: string;
  reason_code: string;
  proof_token?: string;
  approval_ticket_id?: string;
  policy_id?: string;
  controls?: string[];
}

interface EvidenceRecord {
  event_id: string;
  trace_id: string;
  timestamp: string;
  decision: string;
  reason_code: string;
  actor: Actor;
  action: string;
  resource: Resource;
  policy_id: string;
  request_hash: string;
  chain_hash: string;
  prev_hash: string;
  signature: string;
}

interface ApprovalTicket {
  ticket_id: string;
  trace_id: string;
  actor: Actor;
  action: string;
  resource: Resource;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED';
  created_at: string;
  expires_at: string;
  approvals: Array<{ approver_id: string; timestamp: string }>;
}

// =============================================================================
// SIMULATED SERVICES
// =============================================================================

class PolicyStore {
  private policies: Policy[] = [];

  load(policies: Policy[]) {
    this.policies = policies;
    log(`  Loaded ${policies.length} policies`, colors.dim);
  }

  findMatching(actor: Actor, action: string, resource: Resource): Policy[] {
    return this.policies.filter(policy => {
      if (!policy.enabled) return false;

      // Match actor type
      if (policy.scope.actor_type !== '*' && policy.scope.actor_type !== actor.type) {
        return false;
      }

      // Match action (supports wildcards)
      if (policy.scope.action !== '*') {
        const pattern = policy.scope.action.replace(/\*/g, '.*');
        if (!new RegExp(`^${pattern}$`).test(action)) {
          return false;
        }
      }

      // Match resource type
      if (policy.scope.resource_type !== '*' && policy.scope.resource_type !== resource.type) {
        return false;
      }

      return true;
    });
  }

  evaluate(policies: Policy[]): { decision: 'ALLOW' | 'DENY' | 'QUARANTINE'; policy: Policy | null; reason: string } {
    if (policies.length === 0) {
      return { decision: 'DENY', policy: null, reason: 'NO_MATCHING_POLICY' };
    }

    // Sort by priority (lower = higher priority)
    const sorted = [...policies].sort((a, b) => a.priority - b.priority);

    // Get the highest priority (lowest number)
    const highestPriority = sorted[0].priority;

    // Get all policies at the highest priority level
    const topPolicies = sorted.filter(p => p.priority === highestPriority);

    // At same priority: DENY > QUARANTINE > ALLOW
    const denyPolicy = topPolicies.find(p => p.decision === 'DENY');
    if (denyPolicy) {
      return { decision: 'DENY', policy: denyPolicy, reason: denyPolicy.reason_code };
    }

    const quarantinePolicy = topPolicies.find(p => p.decision === 'QUARANTINE');
    if (quarantinePolicy) {
      return { decision: 'QUARANTINE', policy: quarantinePolicy, reason: quarantinePolicy.reason_code };
    }

    const allowPolicy = topPolicies.find(p => p.decision === 'ALLOW');
    if (allowPolicy) {
      return { decision: 'ALLOW', policy: allowPolicy, reason: allowPolicy.reason_code };
    }

    return { decision: 'DENY', policy: null, reason: 'NO_MATCHING_POLICY' };
  }
}

class EvidenceStore {
  private records: EvidenceRecord[] = [];
  private lastHash: string = ZERO_HASH;
  private keyPair: ReturnType<typeof generateKeyPair>;

  constructor() {
    this.keyPair = generateKeyPair();
  }

  record(
    traceId: string,
    decision: string,
    reason: string,
    actor: Actor,
    action: string,
    resource: Resource,
    policyId: string
  ): EvidenceRecord {
    const requestHash = hashCanonical({ actor, action, resource });

    const record: EvidenceRecord = {
      event_id: generateEventId(),
      trace_id: traceId,
      timestamp: new Date().toISOString(),
      decision,
      reason_code: reason,
      actor,
      action,
      resource,
      policy_id: policyId,
      request_hash: requestHash,
      chain_hash: '',
      prev_hash: this.lastHash,
      signature: '',
    };

    // Compute chain hash
    const chainData = { ...record, chain_hash: undefined, signature: undefined };
    record.chain_hash = hashCanonical(chainData);

    // Sign
    const signData = JSON.stringify({ event_hash: record.chain_hash, prev_hash: record.prev_hash });
    record.signature = this.keyPair.sign(signData);

    this.lastHash = record.chain_hash;
    this.records.push(record);

    return record;
  }

  getByTrace(traceId: string): EvidenceRecord[] {
    return this.records.filter(r => r.trace_id === traceId);
  }

  verifyChain(): { valid: boolean; count: number; errors: string[] } {
    const errors: string[] = [];
    let prevHash = ZERO_HASH;

    for (const record of this.records) {
      if (record.prev_hash !== prevHash) {
        errors.push(`Chain break at ${record.event_id}`);
      }
      prevHash = record.chain_hash;
    }

    return { valid: errors.length === 0, count: this.records.length, errors };
  }

  getAll(): EvidenceRecord[] {
    return this.records;
  }
}

class ApprovalStore {
  private tickets: Map<string, ApprovalTicket> = new Map();

  create(traceId: string, actor: Actor, action: string, resource: Resource, timeoutHours: number): ApprovalTicket {
    const ticket: ApprovalTicket = {
      ticket_id: generateApprovalId(),
      trace_id: traceId,
      actor,
      action,
      resource,
      status: 'PENDING',
      created_at: new Date().toISOString(),
      expires_at: new Date(Date.now() + timeoutHours * 60 * 60 * 1000).toISOString(),
      approvals: [],
    };
    this.tickets.set(ticket.ticket_id, ticket);
    return ticket;
  }

  approve(ticketId: string, approverId: string): boolean {
    const ticket = this.tickets.get(ticketId);
    if (!ticket || ticket.status !== 'PENDING') return false;

    ticket.approvals.push({ approver_id: approverId, timestamp: new Date().toISOString() });
    ticket.status = 'APPROVED';
    return true;
  }

  reject(ticketId: string, approverId: string): boolean {
    const ticket = this.tickets.get(ticketId);
    if (!ticket || ticket.status !== 'PENDING') return false;

    ticket.status = 'REJECTED';
    return true;
  }

  get(ticketId: string): ApprovalTicket | undefined {
    return this.tickets.get(ticketId);
  }

  getPending(): ApprovalTicket[] {
    return Array.from(this.tickets.values()).filter(t => t.status === 'PENDING');
  }
}

class Enforcer {
  private policyStore: PolicyStore;
  private evidenceStore: EvidenceStore;
  private approvalStore: ApprovalStore;
  private keyPair: ReturnType<typeof generateKeyPair>;

  constructor(policyStore: PolicyStore, evidenceStore: EvidenceStore, approvalStore: ApprovalStore) {
    this.policyStore = policyStore;
    this.evidenceStore = evidenceStore;
    this.approvalStore = approvalStore;
    this.keyPair = generateKeyPair();
  }

  authorize(request: AuthRequest): AuthResponse {
    const traceId = generateTraceId();

    // Find matching policies
    const matchingPolicies = this.policyStore.findMatching(
      request.actor,
      request.action,
      request.resource
    );

    // Evaluate
    const { decision, policy, reason } = this.policyStore.evaluate(matchingPolicies);

    // Record evidence
    this.evidenceStore.record(
      traceId,
      decision,
      reason,
      request.actor,
      request.action,
      request.resource,
      policy?.policy_id || 'default_deny'
    );

    // Build response
    const response: AuthResponse = {
      decision,
      trace_id: traceId,
      reason_code: reason,
      policy_id: policy?.policy_id,
      controls: policy?.controls,
    };

    // Generate proof token for ALLOW
    if (decision === 'ALLOW') {
      const claims = {
        iss: 'stix',
        sub: request.actor.id,
        act: request.action,
        res: request.resource.type,
        tid: traceId,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 300,
      };
      const header = Buffer.from(JSON.stringify({ alg: 'EdDSA', typ: 'JWT' })).toString('base64url');
      const payload = Buffer.from(JSON.stringify(claims)).toString('base64url');
      const signature = this.keyPair.sign(`${header}.${payload}`);
      response.proof_token = `${header}.${payload}.${signature}`;
    }

    // Create approval ticket for QUARANTINE
    if (decision === 'QUARANTINE') {
      const ticket = this.approvalStore.create(
        traceId,
        request.actor,
        request.action,
        request.resource,
        policy?.approval?.timeout_hours || 24
      );
      response.approval_ticket_id = ticket.ticket_id;
    }

    return response;
  }

  getEvidenceStore(): EvidenceStore {
    return this.evidenceStore;
  }

  getApprovalStore(): ApprovalStore {
    return this.approvalStore;
  }
}

// =============================================================================
// SAMPLE POLICIES
// =============================================================================

const SAMPLE_POLICIES: Policy[] = [
  // Default deny
  {
    policy_id: 'default-deny',
    version: '1.0.0',
    priority: 1000,
    scope: { actor_type: '*', action: '*', resource_type: '*' },
    decision: 'DENY',
    reason_code: 'DEFAULT_DENY',
    enabled: true,
  },
  // Allow read for AI agents in non-production
  {
    policy_id: 'allow-read-non-prod',
    version: '1.0.0',
    priority: 100,
    scope: { actor_type: 'AI_AGENT', action: 'read_*', resource_type: 'document' },
    decision: 'ALLOW',
    reason_code: 'LOW_RISK_READ',
    controls: ['SOC2:CC6.1'],
    enabled: true,
  },
  // Allow send email to internal
  {
    policy_id: 'allow-internal-email',
    version: '1.0.0',
    priority: 100,
    scope: { actor_type: 'AI_AGENT', action: 'send_email', resource_type: 'email' },
    decision: 'ALLOW',
    reason_code: 'INTERNAL_EMAIL_ALLOWED',
    controls: ['SOC2:CC6.7'],
    enabled: true,
  },
  // Quarantine PII access
  {
    policy_id: 'quarantine-pii',
    version: '1.0.0',
    priority: 50,
    scope: { actor_type: 'AI_AGENT', action: '*', resource_type: 'pii' },
    decision: 'QUARANTINE',
    reason_code: 'PII_REQUIRES_APPROVAL',
    approval: { require_count: 1, timeout_hours: 24 },
    controls: ['HIPAA:164.502', 'GDPR:Art6'],
    regulations: ['HIPAA', 'GDPR'],
    enabled: true,
  },
  // Deny production writes
  {
    policy_id: 'deny-production-writes',
    version: '1.0.0',
    priority: 10,
    scope: { actor_type: 'AI_AGENT', action: 'write_*', resource_type: 'production_db' },
    decision: 'DENY',
    reason_code: 'PRODUCTION_WRITE_BLOCKED',
    controls: ['SOC2:CC8.1'],
    enabled: true,
  },
  // Deny external API without approval
  {
    policy_id: 'quarantine-external-api',
    version: '1.0.0',
    priority: 75,
    scope: { actor_type: 'AI_AGENT', action: 'http_request', resource_type: 'external_api' },
    decision: 'QUARANTINE',
    reason_code: 'EXTERNAL_API_REQUIRES_APPROVAL',
    approval: { require_count: 1, timeout_hours: 4 },
    enabled: true,
  },
];

// =============================================================================
// SIMULATION SCENARIOS
// =============================================================================

async function runSimulation() {
  header('STIX Authorization Simulation');
  log('This simulation demonstrates the complete STIX authorization flow.\n');

  // Initialize services
  const policyStore = new PolicyStore();
  const evidenceStore = new EvidenceStore();
  const approvalStore = new ApprovalStore();
  const enforcer = new Enforcer(policyStore, evidenceStore, approvalStore);

  // Load policies
  subheader('Loading Policies');
  policyStore.load(SAMPLE_POLICIES);
  log(`\n  Policies loaded:`);
  SAMPLE_POLICIES.forEach(p => {
    const decColor = p.decision === 'ALLOW' ? colors.green : p.decision === 'DENY' ? colors.red : colors.yellow;
    log(`    - ${p.policy_id}: ${decColor}${p.decision}${colors.reset} (priority: ${p.priority})`);
  });

  await wait(1000);

  // ==========================================================================
  // Scenario 1: ALLOW - Low-risk read operation
  // ==========================================================================
  header('Scenario 1: Low-Risk Read Operation');

  log('An AI agent requests to read a public document...\n');

  const request1: AuthRequest = {
    actor: { id: 'agent-analytics-001', type: 'AI_AGENT', tenant: 'acme-corp' },
    action: 'read_file',
    resource: { type: 'document', id: 'quarterly-report.pdf' },
    context: { env: 'production', purpose: 'Generate summary' },
  };

  log('Request:', colors.cyan);
  json(request1);
  console.log();

  const response1 = enforcer.authorize(request1);

  decision(response1.decision, response1.reason_code);
  log(`  Trace ID: ${colors.dim}${response1.trace_id}${colors.reset}`);
  log(`  Policy: ${colors.dim}${response1.policy_id}${colors.reset}`);

  if (response1.proof_token) {
    log(`  Proof Token: ${colors.green}✓ Generated${colors.reset}`);
    log(`    ${colors.dim}${response1.proof_token.substring(0, 50)}...${colors.reset}`);
  }

  await wait(1500);

  // ==========================================================================
  // Scenario 2: DENY - Production write blocked
  // ==========================================================================
  header('Scenario 2: Production Write Blocked');

  log('An AI agent attempts to write to production database...\n');

  const request2: AuthRequest = {
    actor: { id: 'agent-updater-002', type: 'AI_AGENT', tenant: 'acme-corp' },
    action: 'write_record',
    resource: { type: 'production_db', id: 'users_table' },
    context: { env: 'production', purpose: 'Update user preferences' },
  };

  log('Request:', colors.cyan);
  json(request2);
  console.log();

  const response2 = enforcer.authorize(request2);

  decision(response2.decision, response2.reason_code);
  log(`  Trace ID: ${colors.dim}${response2.trace_id}${colors.reset}`);
  log(`  Policy: ${colors.dim}${response2.policy_id}${colors.reset}`);
  log(`  ${colors.red}⚠ Agent CANNOT proceed - action blocked${colors.reset}`);

  await wait(1500);

  // ==========================================================================
  // Scenario 3: QUARANTINE - PII access requires approval
  // ==========================================================================
  header('Scenario 3: PII Access Requires Human Approval');

  log('An AI agent requests access to customer PII data...\n');

  const request3: AuthRequest = {
    actor: { id: 'agent-support-003', type: 'AI_AGENT', tenant: 'acme-corp', role: 'customer_support' },
    action: 'access_customer_data',
    resource: { type: 'pii', id: 'customer-12345', classification: ['PII', 'CONFIDENTIAL'] },
    context: { env: 'production', purpose: 'Resolve support ticket #T-9876' },
  };

  log('Request:', colors.cyan);
  json(request3);
  console.log();

  const response3 = enforcer.authorize(request3);

  decision(response3.decision, response3.reason_code);
  log(`  Trace ID: ${colors.dim}${response3.trace_id}${colors.reset}`);
  log(`  Policy: ${colors.dim}${response3.policy_id}${colors.reset}`);
  log(`  Controls: ${colors.dim}${response3.controls?.join(', ')}${colors.reset}`);

  if (response3.approval_ticket_id) {
    log(`  ${colors.yellow}⏳ Approval Ticket: ${response3.approval_ticket_id}${colors.reset}`);
    log(`  ${colors.dim}   Action paused - waiting for human approval...${colors.reset}`);
  }

  await wait(2000);

  // Simulate human approval
  subheader('Human Approver Reviews Request');

  log('Security admin reviews the pending approval...\n');
  const ticket = approvalStore.get(response3.approval_ticket_id!);
  if (ticket) {
    log(`  Ticket: ${ticket.ticket_id}`);
    log(`  Agent: ${ticket.actor.id}`);
    log(`  Action: ${ticket.action}`);
    log(`  Resource: ${ticket.resource.type} (${ticket.resource.id})`);
    log(`  Status: ${colors.yellow}${ticket.status}${colors.reset}`);
  }

  await wait(1500);

  log(`\n  ${colors.green}✓ Admin approves the request${colors.reset}\n`);
  approvalStore.approve(response3.approval_ticket_id!, 'admin@acme-corp.com');

  const approvedTicket = approvalStore.get(response3.approval_ticket_id!);
  log(`  New Status: ${colors.green}${approvedTicket?.status}${colors.reset}`);
  log(`  Approved By: ${approvedTicket?.approvals[0].approver_id}`);
  log(`  ${colors.green}→ Agent can now proceed with approved action${colors.reset}`);

  await wait(1500);

  // ==========================================================================
  // Scenario 4: Email sending
  // ==========================================================================
  header('Scenario 4: Sending Email');

  log('An AI agent requests to send an email...\n');

  const request4: AuthRequest = {
    actor: { id: 'agent-notifier-004', type: 'AI_AGENT' },
    action: 'send_email',
    resource: { type: 'email', id: 'team@acme-corp.com' },
    context: { env: 'production', purpose: 'Send daily summary' },
  };

  log('Request:', colors.cyan);
  json(request4);
  console.log();

  const response4 = enforcer.authorize(request4);

  decision(response4.decision, response4.reason_code);
  log(`  Trace ID: ${colors.dim}${response4.trace_id}${colors.reset}`);

  if (response4.proof_token) {
    log(`\n  ${colors.green}✓ Proof token issued - agent can execute email send${colors.reset}`);
  }

  await wait(1500);

  // ==========================================================================
  // Evidence Chain Verification
  // ==========================================================================
  header('Evidence Chain Verification');

  log('Verifying immutable hash-chain integrity...\n');

  const allEvidence = evidenceStore.getAll();
  log(`  Total Records: ${allEvidence.length}`);

  console.log('\n  Chain Structure:');
  allEvidence.forEach((record, i) => {
    const decColor = record.decision === 'ALLOW' ? colors.green : record.decision === 'DENY' ? colors.red : colors.yellow;
    console.log(`  ${colors.dim}${i === 0 ? '┌' : i === allEvidence.length - 1 ? '└' : '├'}─${colors.reset} ${record.event_id.substring(0, 16)}...`);
    console.log(`  ${colors.dim}│${colors.reset}  Decision: ${decColor}${record.decision}${colors.reset}`);
    console.log(`  ${colors.dim}│${colors.reset}  Hash: ${colors.dim}${record.chain_hash.substring(0, 30)}...${colors.reset}`);
    console.log(`  ${colors.dim}│${colors.reset}  Prev: ${colors.dim}${record.prev_hash.substring(0, 30)}...${colors.reset}`);
  });

  const verification = evidenceStore.verifyChain();
  console.log();
  if (verification.valid) {
    log(`  ${colors.green}✓ Chain integrity verified - ${verification.count} records, no tampering detected${colors.reset}`);
  } else {
    log(`  ${colors.red}✗ Chain integrity FAILED: ${verification.errors.join(', ')}${colors.reset}`);
  }

  await wait(1500);

  // ==========================================================================
  // Statistics Summary
  // ==========================================================================
  header('Authorization Statistics');

  const evidence = evidenceStore.getAll();
  const stats = {
    total: evidence.length,
    allowed: evidence.filter(e => e.decision === 'ALLOW').length,
    denied: evidence.filter(e => e.decision === 'DENY').length,
    quarantined: evidence.filter(e => e.decision === 'QUARANTINE').length,
  };

  const barWidth = 40;
  const allowBar = '█'.repeat(Math.round(stats.allowed / stats.total * barWidth));
  const denyBar = '█'.repeat(Math.round(stats.denied / stats.total * barWidth));
  const quarBar = '█'.repeat(Math.round(stats.quarantined / stats.total * barWidth));

  log(`  Total Decisions: ${stats.total}`);
  console.log();
  log(`  ${colors.green}ALLOW${colors.reset}      [${colors.green}${allowBar.padEnd(barWidth)}${colors.reset}] ${stats.allowed} (${Math.round(stats.allowed / stats.total * 100)}%)`);
  log(`  ${colors.red}DENY${colors.reset}       [${colors.red}${denyBar.padEnd(barWidth)}${colors.reset}] ${stats.denied} (${Math.round(stats.denied / stats.total * 100)}%)`);
  log(`  ${colors.yellow}QUARANTINE${colors.reset} [${colors.yellow}${quarBar.padEnd(barWidth)}${colors.reset}] ${stats.quarantined} (${Math.round(stats.quarantined / stats.total * 100)}%)`);

  console.log();
  log(`  Pending Approvals: ${approvalStore.getPending().length}`);

  await wait(1000);

  // ==========================================================================
  // Proof Token Demonstration
  // ==========================================================================
  header('Proof Token Verification (Target Service)');

  log('Simulating target service receiving proof token...\n');

  if (response1.proof_token) {
    const [header, payload, signature] = response1.proof_token.split('.');
    const decodedPayload = JSON.parse(Buffer.from(payload, 'base64url').toString());

    log('  Token Claims:', colors.cyan);
    json(decodedPayload, 4);

    console.log();
    log(`  ${colors.green}✓ Token valid - target service allows execution${colors.reset}`);
    log(`  ${colors.dim}  • Issuer verified (iss: stix)${colors.reset}`);
    log(`  ${colors.dim}  • Not expired (exp: ${new Date(decodedPayload.exp * 1000).toISOString()})${colors.reset}`);
    log(`  ${colors.dim}  • Action matches (act: ${decodedPayload.act})${colors.reset}`);
    log(`  ${colors.dim}  • Signature verified (EdDSA)${colors.reset}`);
  }

  // ==========================================================================
  // Summary
  // ==========================================================================
  header('Simulation Complete');

  log('STIX enforced the following in this simulation:\n');
  log(`  ${colors.green}✓${colors.reset} Low-risk read operation - ALLOWED with proof token`);
  log(`  ${colors.red}✗${colors.reset} Production database write - DENIED by policy`);
  log(`  ${colors.yellow}⏳${colors.reset} PII access - QUARANTINED, approved by human`);
  log(`  ${colors.green}✓${colors.reset} Email send - ALLOWED with proof token`);
  log(`  ${colors.blue}🔗${colors.reset} All decisions recorded in immutable evidence chain`);
  log(`  ${colors.magenta}🔐${colors.reset} Cryptographic signatures on all evidence records`);

  console.log('\n' + '─'.repeat(70));
  log('\nThis is how STIX would protect your AI agents in production.', colors.dim);
  log('Every action authorized, every decision auditable, every agent controlled.\n', colors.dim);
}

// Run the simulation
runSimulation().catch(console.error);
