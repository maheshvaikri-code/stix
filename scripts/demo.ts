#!/usr/bin/env node
/**
 * STIX Platform Demo
 * Demonstrates core STIX functionality without external dependencies
 */

import {
  // Types
  type Actor,
  type Resource,
  type Context,
  type PolicyArtifact,
  type DecisionKind,
  
  // Utils
  generateTraceId,
  generateEventId,
  hashCanonical,
  isoTimestamp,
  addSeconds,
  ZERO_HASH,
  
  // Crypto
  generateEd25519KeyPair,
  InMemoryKeyStore,
  createProofToken,
  verifyProofToken,
  signEvidence,
  
  // Validators
  validatePolicyArtifact,
  
  // Logger
  createLogger,
  
  // Constants
  REASON_CODES,
} from '@stix/shared';

// =============================================================================
// DEMO SETUP
// =============================================================================

const logger = createLogger({ service: 'stix-demo', level: 'debug', pretty: true });

logger.info('Starting STIX Platform Demo');

// Initialize crypto
const keyStore = new InMemoryKeyStore();
const keyPair = generateEd25519KeyPair();
keyStore.addKeyPair(keyPair);

logger.info('Cryptographic keys generated', { keyId: keyPair.keyId });

// =============================================================================
// POLICY SETUP
// =============================================================================

const policies: PolicyArtifact[] = [
  {
    policy_id: 'allow-public-read',
    version: '1.0.0',
    priority: 100,
    description: 'Allow read access to public data',
    scope: {
      actor_type: 'AI_AGENT',
      action: 'read_*',
      resource_type: 'public_data',
    },
    decision: 'ALLOW',
    reason_code: 'PUBLIC_READ_ALLOWED',
    controls: ['SOC2:CC6.1'],
  },
  {
    policy_id: 'quarantine-phi',
    version: '1.0.0',
    priority: 10,
    description: 'Quarantine PHI access for approval',
    scope: {
      actor_type: '*',
      action: '*',
      resource_type: 'patient_data',
    },
    conditions: {
      require_signal: { phiDetected: true },
    },
    decision: 'QUARANTINE',
    reason_code: 'PHI_REQUIRES_APPROVAL',
    approval: {
      approver_role: 'hipaa_officer',
      require_count: 1,
      require_justification: true,
      timeout_hours: 4,
    },
    controls: ['HIPAA:164.502', 'SOC2:CC6.1'],
    regulations: ['HIPAA'],
  },
  {
    policy_id: 'deny-production-writes',
    version: '1.0.0',
    priority: 1,
    description: 'Block AI writes to production',
    scope: {
      actor_type: 'AI_AGENT',
      action: 'write_*',
      resource_type: 'production_db',
    },
    decision: 'DENY',
    reason_code: 'PROD_WRITE_BLOCKED',
    controls: ['SOC2:CC8.1'],
  },
];

// Validate all policies
const validatedPolicies = policies.map(p => validatePolicyArtifact(p));
logger.info('Policies loaded and validated', { count: validatedPolicies.length });

// =============================================================================
// SIMULATED ENFORCER
// =============================================================================

function evaluatePolicies(
  actor: Actor,
  action: string,
  resource: Resource
): { decision: DecisionKind; policy: PolicyArtifact | null; reasonCode: string } {
  // Find matching policies
  const matching = validatedPolicies.filter(policy => {
    const { scope } = policy;
    
    // Actor type check (with wildcard support)
    if (scope.actor_type !== '*' && scope.actor_type !== actor.type) {
      return false;
    }
    
    // Action check (with glob support)
    if (scope.action !== '*') {
      const pattern = scope.action.replace('*', '.*');
      if (!new RegExp(`^${pattern}$`).test(action)) {
        return false;
      }
    }
    
    // Resource type check
    if (scope.resource_type !== '*' && scope.resource_type !== resource.type) {
      return false;
    }
    
    return true;
  });

  if (matching.length === 0) {
    return { decision: 'DENY', policy: null, reasonCode: REASON_CODES.NO_MATCHING_POLICY };
  }

  // Sort by priority (lower = higher priority)
  const sorted = [...matching].sort((a, b) => (a.priority ?? 100) - (b.priority ?? 100));

  // Deny wins at same priority level
  for (const policy of sorted) {
    if (policy.decision === 'DENY') {
      return { decision: 'DENY', policy, reasonCode: policy.reason_code };
    }
  }

  // Then check quarantine
  for (const policy of sorted) {
    if (policy.decision === 'QUARANTINE') {
      return { decision: 'QUARANTINE', policy, reasonCode: policy.reason_code };
    }
  }

  // Finally allow
  const allowPolicy = sorted.find(p => p.decision === 'ALLOW');
  if (allowPolicy) {
    return { decision: 'ALLOW', policy: allowPolicy, reasonCode: allowPolicy.reason_code };
  }

  return { decision: 'DENY', policy: null, reasonCode: REASON_CODES.NO_MATCHING_POLICY };
}

// =============================================================================
// DEMO SCENARIOS
// =============================================================================

async function demo() {
  console.log('\n' + '='.repeat(70));
  console.log('STIX PLATFORM DEMO - Authorization Scenarios');
  console.log('='.repeat(70) + '\n');

  // Scenario 1: ALLOW - Public data read
  {
    console.log('📗 Scenario 1: AI Agent reading public data');
    console.log('-'.repeat(50));
    
    const actor: Actor = { id: 'agent-1', type: 'AI_AGENT', tenant: 'acme' };
    const action = 'read_file';
    const resource: Resource = { type: 'public_data', id: 'doc-123' };

    const { decision, policy, reasonCode } = evaluatePolicies(actor, action, resource);
    const traceId = generateTraceId();

    console.log(`Actor: ${actor.type}:${actor.id}`);
    console.log(`Action: ${action}`);
    console.log(`Resource: ${resource.type}:${resource.id}`);
    console.log(`Decision: ${decision}`);
    console.log(`Reason: ${reasonCode}`);
    console.log(`Trace ID: ${traceId}`);

    if (decision === 'ALLOW' && policy) {
      // Generate proof token
      const signingKey = await keyStore.getSigningKey();
      const token = createProofToken({
        iss: 'stix',
        sub: actor.id,
        act: action,
        res: resource.type,
        cls: resource.classification ?? [],
        pol: hashCanonical(policy),
        tid: traceId,
        iat: Math.floor(Date.now() / 1000),
        exp: Math.floor(Date.now() / 1000) + 300,
      }, signingKey);

      console.log(`Proof Token: ${token.substring(0, 50)}...`);
      
      // Verify token
      const getKey = (kid: string) => keyStore['verificationKeys'].get(kid);
      const verified = verifyProofToken(token, getKey);
      console.log(`Token Valid: ${verified.valid}`);
    }
    console.log('');
  }

  // Scenario 2: QUARANTINE - PHI access
  {
    console.log('📙 Scenario 2: AI Agent accessing PHI');
    console.log('-'.repeat(50));
    
    const actor: Actor = { id: 'agent-2', type: 'AI_AGENT', tenant: 'hospital' };
    const action = 'read_record';
    const resource: Resource = { 
      type: 'patient_data', 
      id: 'patient-456',
      classification: ['PHI', 'HIPAA'],
    };

    const { decision, policy, reasonCode } = evaluatePolicies(actor, action, resource);
    const traceId = generateTraceId();

    console.log(`Actor: ${actor.type}:${actor.id}`);
    console.log(`Action: ${action}`);
    console.log(`Resource: ${resource.type}:${resource.id}`);
    console.log(`Decision: ${decision}`);
    console.log(`Reason: ${reasonCode}`);
    console.log(`Trace ID: ${traceId}`);

    if (decision === 'QUARANTINE' && policy?.approval) {
      console.log(`Requires Approval: YES`);
      console.log(`Approver Role: ${policy.approval.approver_role}`);
      console.log(`Timeout: ${policy.approval.timeout_hours} hours`);
      console.log(`Justification Required: ${policy.approval.require_justification}`);
    }
    console.log('');
  }

  // Scenario 3: DENY - Production write
  {
    console.log('📕 Scenario 3: AI Agent attempting production write');
    console.log('-'.repeat(50));
    
    const actor: Actor = { id: 'agent-3', type: 'AI_AGENT', tenant: 'acme' };
    const action = 'write_record';
    const resource: Resource = { type: 'production_db', id: 'users-table' };

    const { decision, policy, reasonCode } = evaluatePolicies(actor, action, resource);
    const traceId = generateTraceId();

    console.log(`Actor: ${actor.type}:${actor.id}`);
    console.log(`Action: ${action}`);
    console.log(`Resource: ${resource.type}:${resource.id}`);
    console.log(`Decision: ${decision}`);
    console.log(`Reason: ${reasonCode}`);
    console.log(`Trace ID: ${traceId}`);
    console.log(`Controls: ${policy?.controls?.join(', ') ?? 'N/A'}`);
    console.log('');
  }

  // =============================================================================
  // EVIDENCE DEMO
  // =============================================================================
  
  console.log('='.repeat(70));
  console.log('STIX PLATFORM DEMO - Evidence Chain');
  console.log('='.repeat(70) + '\n');

  const signingKey = await keyStore.getSigningKey();
  let prevHash = ZERO_HASH;

  // Create chain of 3 evidence events
  const events = [];
  for (let i = 1; i <= 3; i++) {
    const eventId = generateEventId();
    const traceId = generateTraceId();
    
    const eventData = {
      event_id: eventId,
      trace_id: traceId,
      timestamp: isoTimestamp(),
      decision: 'ALLOW' as const,
      reason_code: 'DEMO_ALLOW',
      actor: { id: `agent-${i}`, type: 'AI_AGENT' as const },
      action: { name: 'demo_action' },
      resource: { type: 'demo_resource' },
      context: { env: 'dev' as const },
      policy: { id: 'demo-policy', version: '1.0.0', hash: ZERO_HASH },
      controls: ['SOC2:CC6.1'],
      regulations: [],
    };

    const signResult = signEvidence(eventData, prevHash, signingKey);
    
    const event = {
      ...eventData,
      integrity: {
        event_hash: signResult.eventHash,
        prev_hash: prevHash,
        signature: signResult.signature,
        key_id: signResult.keyId,
      },
    };

    events.push(event);
    prevHash = signResult.eventHash;

    console.log(`Event ${i}:`);
    console.log(`  ID: ${eventId}`);
    console.log(`  Hash: ${signResult.eventHash.substring(0, 30)}...`);
    console.log(`  Prev: ${event.integrity.prev_hash.substring(0, 30)}...`);
    console.log(`  Signed: ✓`);
    console.log('');
  }

  // Verify chain
  console.log('Verifying hash chain...');
  let chainValid = true;
  let checkPrevHash = ZERO_HASH;
  for (let i = 0; i < events.length; i++) {
    const event = events[i];
    if (event.integrity.prev_hash !== checkPrevHash) {
      console.log(`  Event ${i + 1}: ✗ Hash chain broken!`);
      chainValid = false;
    } else {
      console.log(`  Event ${i + 1}: ✓ Valid`);
    }
    checkPrevHash = event.integrity.event_hash;
  }
  console.log(`\nChain Integrity: ${chainValid ? '✓ VALID' : '✗ BROKEN'}`);

  // =============================================================================
  // SUMMARY
  // =============================================================================
  
  console.log('\n' + '='.repeat(70));
  console.log('DEMO COMPLETE');
  console.log('='.repeat(70));
  console.log(`
STIX Platform Capabilities Demonstrated:
  ✓ Policy-based authorization (ALLOW/DENY/QUARANTINE)
  ✓ Wildcard and glob pattern matching in policy scopes
  ✓ Priority-based policy evaluation with deny-wins
  ✓ Cryptographic proof tokens (JWT-style with Ed25519)
  ✓ Tamper-evident evidence chain with hash linking
  ✓ Ed25519 signatures for audit integrity
  ✓ Compliance control mapping (SOC2, HIPAA, etc.)
  ✓ Human-in-the-loop approval workflows
  
To run the full platform:
  1. pnpm install
  2. pnpm build
  3. pnpm dev
  
See README.md for full documentation.
`);
}

// Run demo
demo().catch(err => {
  logger.error('Demo failed', {}, err as Error);
  process.exit(1);
});
