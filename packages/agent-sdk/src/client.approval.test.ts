import { describe, expect, it, vi } from 'vitest';
import { StixClient } from './client';
import type { ApprovalRequest, AuthorizationResult } from './types';

function quarantinedResult(): AuthorizationResult {
  return {
    allowed: false,
    decision: 'QUARANTINE',
    traceId: 'stix_trace_approval',
    reasonCode: 'REQUIRES_APPROVAL',
    obligations: [],
    approvalRequired: true,
    approvalTicketId: 'appr_test_1',
    controls: [],
    regulations: [],
    request: {
      actor: { id: 'agent-1', type: 'AI_AGENT' },
      action: 'write',
      resource: { type: 'file', id: 'file-1' },
      context: { env: 'test' },
    },
  };
}

const approvedTicket: ApprovalRequest = {
  id: 'appr_test_1',
  traceId: 'stix_trace_approval',
  status: 'approved',
  actor: { id: 'agent-1', type: 'AI_AGENT' },
  action: 'write',
  resource: { type: 'file', id: 'file-1' },
  createdAt: new Date().toISOString(),
  requiredCount: 1,
  currentCount: 1,
  approvals: [],
  expiresAt: new Date(Date.now() + 60_000).toISOString(),
};

describe('StixClient approval completion', () => {
  it('reauthorizes the original request and returns the newly issued proof', async () => {
    const client = new StixClient({ enforcerUrl: 'http://enforcer.test' });
    vi.spyOn(client, 'getApprovalStatus').mockResolvedValue(approvedTicket);
    (client as unknown as { sendRequest: ReturnType<typeof vi.fn> }).sendRequest = vi.fn()
      .mockResolvedValue({
        decision: 'ALLOW',
        trace_id: 'stix_trace_reauthorized',
        reason_code: 'APPROVED_BY_HUMAN',
        action_id: 'act_1',
        policy: { id: 'p1', version: '1.0.0', hash: 'sha256:' + '1'.repeat(64) },
        obligations: [],
        approval: null,
        proof_token: 'proof-after-approval',
      });

    const result = await client.waitForApproval(quarantinedResult(), { interval: 0 });

    expect(result.allowed).toBe(true);
    expect(result.decision).toBe('ALLOW');
    expect(result.proofToken).toBe('proof-after-approval');
    expect((client as unknown as { sendRequest: ReturnType<typeof vi.fn> }).sendRequest)
      .toHaveBeenCalledWith(
        'http://enforcer.test/api/v1/authorize',
        expect.objectContaining({ approval_ref: 'appr_test_1' })
      );
  });

  it('never converts an approved ticket to ALLOW when reauthorization has no proof', async () => {
    const client = new StixClient({ enforcerUrl: 'http://enforcer.test' });
    vi.spyOn(client, 'getApprovalStatus').mockResolvedValue(approvedTicket);
    (client as unknown as { sendRequest: ReturnType<typeof vi.fn> }).sendRequest = vi.fn()
      .mockResolvedValue({
        decision: 'ALLOW',
        trace_id: 'stix_trace_reauthorized',
        reason_code: 'APPROVED_BY_HUMAN',
        policy: { id: 'p1', version: '1.0.0', hash: 'sha256:' + '1'.repeat(64) },
        obligations: [],
        approval: null,
      });

    const result = await client.waitForApproval(quarantinedResult(), { interval: 0 });

    expect(result.allowed).toBe(false);
    expect(result.decision).toBe('DENY');
    expect(result.proofToken).toBeUndefined();
  });
});
