import { describe, expect, it, vi } from 'vitest';
import {
  createLogger,
  generateEd25519KeyPair,
  hashCanonical,
  loadPrivateKey,
  parseProofTokenUnsafe,
  type PolicyDecision,
  type Logger,
} from '@stix/shared';
import { loadConfig } from '../services/enforcer/src/config/index.js';
import { AuthorizationEngine } from '../services/enforcer/src/core/engine.js';
import type { PolicyClient } from '../services/enforcer/src/services/policy-client.js';
import type { EvidenceClient } from '../services/enforcer/src/services/evidence-client.js';
import type { ApprovalsClient, ApprovalTicket } from '../services/enforcer/src/services/approvals-client.js';

function makeEngine(policyDecision: PolicyDecision) {
  const logger = createLogger({ service: 'enforcer-test', level: 'error', pretty: false });
  const config = loadConfig();
  config.authorization.cacheEnabled = false;
  const keyPair = generateEd25519KeyPair();
  const signingKey = {
    keyId: keyPair.keyId,
    algorithm: keyPair.algorithm,
    privateKey: loadPrivateKey(keyPair.privateKey),
  };
  const tickets = new Map<string, ApprovalTicket>();

  const policyClient = {
    evaluate: vi.fn(async () => policyDecision),
  } as unknown as PolicyClient;
  const evidenceClient = {
    recordDecision: vi.fn(async () => undefined),
  } as unknown as EvidenceClient;
  const approvalsClient = {
    createTicket: vi.fn(async (request) => {
      const ticket = {
        ...request,
        status: 'PENDING' as const,
        decisions: [],
        created_at: new Date().toISOString(),
      } as ApprovalTicket;
      tickets.set(ticket.ticket_id, ticket);
      return ticket;
    }),
    getTicket: vi.fn(async (ticketId: string) => tickets.get(ticketId) as ApprovalTicket),
  } as unknown as ApprovalsClient;

  const engine = new AuthorizationEngine(
    config,
    logger,
    policyClient,
    evidenceClient,
    approvalsClient,
    null,
    signingKey
  );

  return { engine, tickets };
}

const allowPolicy: PolicyDecision = {
  decision: 'ALLOW',
  reason_code: 'POLICY_ALLOW',
  policy: { id: 'policy-allow', version: '1.0.0', hash: hashCanonical({ policy: 'allow' }) },
  obligations: [],
  approval: null,
  controls: [],
  regulations: [],
};

const quarantinePolicy: PolicyDecision = {
  decision: 'QUARANTINE',
  reason_code: 'REQUIRES_APPROVAL',
  policy: { id: 'policy-review', version: '1.0.0', hash: hashCanonical({ policy: 'review' }) },
  obligations: [],
  approval: {
    required: true,
    approver_role: 'security',
    require_count: 1,
    require_justification: true,
  },
  controls: [],
  regulations: [],
};

const request = {
  actor: { id: 'agent-1', type: 'AI_AGENT' as const, tenant: 'tenant-1', role: 'writer' },
  action: 'write_file',
  resource: { type: 'file', id: 'file-1' },
  context: { env: 'test' as const, purpose: 'proof binding' },
  tool_call: { tool: 'write', args_summary: 'file-1:content-v1' },
};

describe('enforcer proof and approval bindings', () => {
  it('binds exact request, arguments, action, resource, and replay claims', async () => {
    const { engine } = makeEngine(allowPolicy);
    const result = await engine.authorize(request);
    expect(result.response.decision).toBe('ALLOW');
    expect(result.response.proof_token).toBeDefined();

    const parsed = parseProofTokenUnsafe(result.response.proof_token!);
    expect(parsed.claims?.request_hash).toBe(hashCanonical({
      ...request,
      action_id: result.response.action_id,
      approval_ref: undefined,
    }));
    expect(parsed.claims?.arguments_hash).toBe(hashCanonical(request.tool_call));
    expect(parsed.claims?.action_id).toBe(result.response.action_id);
    expect(parsed.claims?.resource_id).toBe('file-1');
    expect(parsed.claims?.replay_id).toBe(parsed.claims?.jti);
    expect(parsed.claims?.approval_ref).toBeUndefined();
  });

  it('requires an approved ticket to reauthorize the exact original request', async () => {
    const { engine, tickets } = makeEngine(quarantinePolicy);
    const pending = await engine.authorize(request);
    const ticketId = pending.response.approval?.ticket_id;
    expect(pending.response.decision).toBe('QUARANTINE');
    expect(pending.response.proof_token).toBeUndefined();
    expect(ticketId).toBeDefined();

    const ticket = tickets.get(ticketId!);
    ticket!.status = 'APPROVED';
    const approved = await engine.authorize({ ...request, approval_ref: ticketId });
    expect(approved.response.decision).toBe('ALLOW');
    expect(approved.response.proof_token).toBeDefined();

    const approvedClaims = parseProofTokenUnsafe(approved.response.proof_token!).claims;
    expect(approvedClaims?.approval_ref).toBe(ticketId);

    const changedResource = await engine.authorize({
      ...request,
      resource: { type: 'file', id: 'file-2' },
      approval_ref: ticketId,
    });
    expect(changedResource.response.decision).toBe('DENY');
    expect(changedResource.response.proof_token).toBeUndefined();
  });
});
