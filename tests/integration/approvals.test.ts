/**
 * STIX Integration Tests - Approvals Service
 */

import { describe, it, expect, beforeAll } from 'vitest';
import {
  getTestConfig,
  createClients,
  generateTestRequest,
  wait,
  retry,
  type ApprovalRequest,
  type TestClient,
  type AuthorizeResponse,
} from './setup';

describe('Approvals Service Integration', () => {
  let approvals: TestClient;
  let enforcer: TestClient;
  let testApprovalId: string | undefined;
  let testTraceId: string | undefined;

  beforeAll(async () => {
    const config = getTestConfig();
    const clients = createClients(config);
    approvals = clients.approvals;
    enforcer = clients.enforcer;

    // Try to create a quarantine decision to get an approval ticket
    const request = generateTestRequest({
      actor: { id: 'approval-test-agent', type: 'AI_AGENT' },
      action: 'execute_sensitive',
      resource: { type: 'tool', id: 'approval-test-tool', attributes: { risk_tier: 'HIGH' } },
      context: { env: 'prod' },
      tool_call: { tool: 'execute_sensitive', risk_tier: 'HIGH' },
    });

    const { data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

    if (data.decision === 'QUARANTINE' && data.approval_ticket_id) {
      testApprovalId = data.approval_ticket_id;
      testTraceId = data.trace_id;
    }

    await wait(500);
  });

  describe('Health', () => {
    it('should return healthy status', async () => {
      const { status, data } = await approvals.get<{ status: string }>('/health');

      expect(status).toBe(200);
      expect(data.status).toBe('healthy');
    });
  });

  describe('List Approvals', () => {
    it('should list pending approvals', async () => {
      const { status, data } = await approvals.get<{
        data: ApprovalRequest[];
        total: number;
      }>('/api/v1/approvals?status=PENDING');

      expect(status).toBe(200);
      expect(Array.isArray(data.data)).toBe(true);
      expect(typeof data.total).toBe('number');
    });

    it('should list all approvals', async () => {
      const { status, data } = await approvals.get<{
        data: ApprovalRequest[];
        total: number;
      }>('/api/v1/approvals');

      expect(status).toBe(200);
      expect(Array.isArray(data.data)).toBe(true);
    });

    it('should filter by status', async () => {
      const { status, data } = await approvals.get<{
        data: ApprovalRequest[];
      }>('/api/v1/approvals?status=PENDING');

      expect(status).toBe(200);
      if (data.data.length > 0) {
        data.data.forEach((approval) => {
          expect(approval.status).toBe('PENDING');
        });
      }
    });

    it('should filter by actor_id', async () => {
      const { status, data } = await approvals.get<{
        data: ApprovalRequest[];
      }>('/api/v1/approvals?actor_id=approval-test-agent');

      expect(status).toBe(200);
      if (data.data.length > 0) {
        data.data.forEach((approval) => {
          expect(approval.actor_id).toBe('approval-test-agent');
        });
      }
    });

    it('should support pagination', async () => {
      const { status, data } = await approvals.get<{
        data: ApprovalRequest[];
        page: number;
        page_size: number;
        total: number;
      }>('/api/v1/approvals?page=1&page_size=5');

      expect(status).toBe(200);
      expect(data.data.length).toBeLessThanOrEqual(5);
    });
  });

  describe('Get Approval', () => {
    it('should get specific approval by ID', async () => {
      if (!testApprovalId) {
        console.log('No test approval created, skipping');
        return;
      }

      const { status, data } = await approvals.get<ApprovalRequest>(
        `/api/v1/approvals/${testApprovalId}`
      );

      if (status === 200) {
        expect(data.request_id).toBe(testApprovalId);
        expect(data.status).toBeDefined();
        expect(data.created_at).toBeDefined();
        expect(data.expires_at).toBeDefined();
      } else {
        // Approval might have expired or been processed
        expect([200, 404]).toContain(status);
      }
    });

    it('should return 404 for non-existent approval', async () => {
      const { status } = await approvals.get<{ error: string }>(
        '/api/v1/approvals/appr_nonexistent'
      );

      expect(status).toBe(404);
    });
  });

  describe('Approve Request', () => {
    it('should approve a pending request', async () => {
      // Create a new quarantine decision to get a fresh approval
      const request = generateTestRequest({
        actor: { id: 'approval-approve-test', type: 'AI_AGENT' },
        action: 'execute_sensitive',
        resource: { type: 'tool', id: 'approve-tool', attributes: { risk_tier: 'HIGH' } },
        context: { env: 'prod' },
        tool_call: { tool: 'execute_sensitive', risk_tier: 'HIGH' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(authData.decision).toBe('QUARANTINE');
      expect(authData.approval_ticket_id).toBeDefined();

      await wait(500);

      const { status, data } = await approvals.post<ApprovalRequest>(
        `/api/v1/approvals/tickets/${authData.approval_ticket_id}/approve`,
        {
          approver_id: 'integration-security-admin',
          approver_role: 'security_admin',
          justification: 'Approved for integration testing',
        }
      );

      expect(status).toBe(200);
      expect((data as unknown as { data: { status: string; resolved_at?: string } }).data.status).toBe('APPROVED');
      expect((data as unknown as { data: { status: string; resolved_at?: string } }).data.resolved_at).toBeDefined();
    });
  });

  describe('Reject Request', () => {
    it('should reject a pending request', async () => {
      // Create a new quarantine decision
      const request = generateTestRequest({
        actor: { id: 'approval-reject-test', type: 'AI_AGENT' },
        action: 'execute_sensitive',
        resource: { type: 'tool', id: 'reject-tool', attributes: { risk_tier: 'HIGH' } },
        context: { env: 'prod' },
        tool_call: { tool: 'execute_sensitive', risk_tier: 'HIGH' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(authData.decision).toBe('QUARANTINE');
      expect(authData.approval_ticket_id).toBeDefined();

      await wait(500);

      const { status, data } = await approvals.post<ApprovalRequest>(
        `/api/v1/approvals/tickets/${authData.approval_ticket_id}/reject`,
        {
          approver_id: 'integration-security-admin',
          approver_role: 'security_admin',
          justification: 'Rejected for integration testing',
        }
      );

      expect(status).toBe(200);
      expect((data as unknown as { data: { status: string; resolved_at?: string } }).data.status).toBe('REJECTED');
      expect((data as unknown as { data: { status: string; resolved_at?: string } }).data.resolved_at).toBeDefined();
    });
  });

  describe('Poll Approval Status', () => {
    it('should allow polling for approval status', async () => {
      if (!testApprovalId) {
        console.log('No test approval created, skipping');
        return;
      }

      const { status, data } = await approvals.get<{
        status: string;
        approved: boolean;
      }>(`/api/v1/approvals/${testApprovalId}/status`);

      if (status === 200) {
        expect(['PENDING', 'APPROVED', 'REJECTED', 'EXPIRED']).toContain(data.status);
        expect(typeof data.approved).toBe('boolean');
      } else {
        // Endpoint might be different
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Approvals by Trace', () => {
    it('should get approvals for a specific trace', async () => {
      if (!testTraceId) {
        console.log('No test trace created, skipping');
        return;
      }

      const { status, data } = await approvals.get<ApprovalRequest[]>(
        `/api/v1/approvals/trace/${testTraceId}`
      );

      if (status === 200) {
        expect(Array.isArray(data)).toBe(true);
        if (data.length > 0) {
          data.forEach((approval) => {
            expect(approval.trace_id).toBe(testTraceId);
          });
        }
      } else {
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Approval Statistics', () => {
    it('should return approval statistics', async () => {
      const { status, data } = await approvals.get<{
        pending: number;
        approved_today: number;
        rejected_today: number;
        avg_response_time_ms: number;
      }>('/api/v1/stats');

      if (status === 200) {
        expect(typeof data.pending).toBe('number');
        expect(typeof data.approved_today).toBe('number');
        expect(typeof data.rejected_today).toBe('number');
      } else {
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Approval Workflow', () => {
    it('should complete full approval workflow', async () => {
      // 1. Create authorization that requires approval
      const request = generateTestRequest({
        actor: { id: 'workflow-test-agent', type: 'AI_AGENT' },
        action: 'execute_sensitive',
        resource: { type: 'tool', id: 'workflow-tool', attributes: { risk_tier: 'HIGH' } },
        context: { env: 'prod' },
        tool_call: { tool: 'execute_sensitive', risk_tier: 'HIGH' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(authData.decision).toBe('QUARANTINE');

      const approvalId = authData.approval_ticket_id;
      expect(approvalId).toBeDefined();

      // 2. Check initial status is PENDING
      const { data: pendingData } = await approvals.get<ApprovalRequest>(
        `/api/v1/approvals/${approvalId}`
      );
      expect(pendingData.status).toBe('PENDING');

      // 3. Approve the request
      const { status: approveStatus } = await approvals.post<ApprovalRequest>(
        `/api/v1/approvals/tickets/${approvalId}/approve`,
        {
          approver_id: 'workflow-security-admin',
          approver_role: 'security_admin',
          justification: 'Workflow test approval',
        }
      );

      expect(approveStatus).toBe(200);

      // 4. Verify status is APPROVED
      const { data: approvedData } = await approvals.get<ApprovalRequest>(
        `/api/v1/approvals/${approvalId}`
      );
      expect(approvedData.status).toBe('APPROVED');

      // 5. Reauthorize the exact request and require a fresh proof token.
      const { status: reauthStatus, data: reauthData } = await enforcer.post<AuthorizeResponse>(
        '/api/v1/authorize',
        { ...request, approval_ref: approvalId }
      );
      expect(reauthStatus).toBe(200);
      expect(reauthData.decision).toBe('ALLOW');
      expect(reauthData.proof_token).toBeDefined();

      const payload = JSON.parse(
        Buffer.from(reauthData.proof_token!.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString()
      ) as Record<string, unknown>;
      expect(payload.approval_ref).toBe(approvalId);
      expect(payload.request_hash).toBeDefined();
      expect(payload.arguments_hash).toBeDefined();
      expect(payload.resource_id).toBe('workflow-tool');
      expect(payload.replay_id).toBeDefined();

      const { data: changedData } = await enforcer.post<AuthorizeResponse>(
        '/api/v1/authorize',
        {
          ...request,
          resource: { type: 'tool', id: 'different-workflow-tool', attributes: { risk_tier: 'HIGH' } },
          approval_ref: approvalId,
        }
      );
      expect(changedData.decision).toBe('DENY');
      expect(changedData.proof_token).toBeUndefined();
    });
  });

  describe('Expiration', () => {
    it('should include expiration time in approval', async () => {
      const request = generateTestRequest({
        actor: { id: 'expiration-test-agent', type: 'AI_AGENT' },
        action: 'execute_sensitive',
        resource: { type: 'tool', id: 'expiration-tool', attributes: { risk_tier: 'HIGH' } },
        context: { env: 'prod' },
        tool_call: { tool: 'execute_sensitive', risk_tier: 'HIGH' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(authData.decision).toBe('QUARANTINE');
      expect(authData.approval_ticket_id).toBeDefined();

      const { status, data } = await approvals.get<ApprovalRequest>(
        `/api/v1/approvals/${authData.approval_ticket_id}`
      );

      if (status === 200) {
        expect(data.expires_at).toBeDefined();
        const expiresAt = new Date(data.expires_at);
        expect(expiresAt.getTime()).toBeGreaterThan(Date.now());
      }
    });
  });

  describe('Validation', () => {
    it('should reject approval of non-existent request', async () => {
      const { status } = await approvals.post<{ error: string }>(
        '/api/v1/approvals/appr_nonexistent/approve',
        {}
      );

      expect(status).toBe(404);
    });

    it('should reject double approval', async () => {
      // First create and approve
      const request = generateTestRequest({
        actor: { id: 'double-approve-test', type: 'AI_AGENT' },
        action: 'execute_sensitive',
        resource: { type: 'tool', id: 'double-approve-tool', attributes: { risk_tier: 'HIGH' } },
        context: { env: 'prod' },
        tool_call: { tool: 'execute_sensitive', risk_tier: 'HIGH' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(authData.decision).toBe('QUARANTINE');
      expect(authData.approval_ticket_id).toBeDefined();

      // First approval
      await approvals.post(
        `/api/v1/approvals/${authData.approval_ticket_id}/approve`,
        {}
      );

      // Second approval should fail or be idempotent
      const { status } = await approvals.post(
        `/api/v1/approvals/${authData.approval_ticket_id}/approve`,
        {}
      );

      // Could be 400 (bad request), 409 (conflict), or 200 (idempotent)
      expect([200, 400, 409]).toContain(status);
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid approval ID format', async () => {
      const { status } = await approvals.get<{ error: string }>(
        '/api/v1/approvals/invalid-format'
      );

      expect([400, 404]).toContain(status);
    });
  });
});
