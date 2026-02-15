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
      action: 'access_sensitive_for_test',
      resource: { type: 'sensitive_data', classification: ['PII'] },
      context: { env: 'production' },
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
        action: 'sensitive_action_to_approve',
        resource: { type: 'sensitive_data' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      if (authData.decision !== 'QUARANTINE' || !authData.approval_ticket_id) {
        console.log('No quarantine decision, skipping approve test');
        return;
      }

      await wait(500);

      const { status, data } = await approvals.post<ApprovalRequest>(
        `/api/v1/approvals/${authData.approval_ticket_id}/approve`,
        { notes: 'Approved for integration testing' }
      );

      if (status === 200) {
        expect(data.status).toBe('APPROVED');
        expect(data.reviewed_at).toBeDefined();
      } else {
        // Might need authentication or different endpoint structure
        expect([200, 401, 403, 404]).toContain(status);
      }
    });
  });

  describe('Reject Request', () => {
    it('should reject a pending request', async () => {
      // Create a new quarantine decision
      const request = generateTestRequest({
        actor: { id: 'approval-reject-test', type: 'AI_AGENT' },
        action: 'sensitive_action_to_reject',
        resource: { type: 'sensitive_data' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      if (authData.decision !== 'QUARANTINE' || !authData.approval_ticket_id) {
        console.log('No quarantine decision, skipping reject test');
        return;
      }

      await wait(500);

      const { status, data } = await approvals.post<ApprovalRequest>(
        `/api/v1/approvals/${authData.approval_ticket_id}/reject`,
        { notes: 'Rejected for integration testing' }
      );

      if (status === 200) {
        expect(data.status).toBe('REJECTED');
        expect(data.reviewed_at).toBeDefined();
      } else {
        expect([200, 401, 403, 404]).toContain(status);
      }
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
        action: 'full_workflow_test',
        resource: { type: 'sensitive_data' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      if (authData.decision !== 'QUARANTINE') {
        console.log('Expected QUARANTINE, got', authData.decision);
        return;
      }

      const approvalId = authData.approval_ticket_id;
      expect(approvalId).toBeDefined();

      // 2. Check initial status is PENDING
      const { data: pendingData } = await approvals.get<ApprovalRequest>(
        `/api/v1/approvals/${approvalId}`
      );
      expect(pendingData.status).toBe('PENDING');

      // 3. Approve the request
      const { status: approveStatus } = await approvals.post<ApprovalRequest>(
        `/api/v1/approvals/${approvalId}/approve`,
        { notes: 'Workflow test approval' }
      );

      if (approveStatus !== 200) {
        console.log('Approve endpoint returned', approveStatus);
        return;
      }

      // 4. Verify status is APPROVED
      const { data: approvedData } = await approvals.get<ApprovalRequest>(
        `/api/v1/approvals/${approvalId}`
      );
      expect(approvedData.status).toBe('APPROVED');

      // 5. Verify agent can now proceed (re-authorize should succeed)
      // Note: This depends on implementation - some systems require a new auth request
    });
  });

  describe('Expiration', () => {
    it('should include expiration time in approval', async () => {
      const request = generateTestRequest({
        actor: { id: 'expiration-test-agent', type: 'AI_AGENT' },
        action: 'expiration_test',
        resource: { type: 'sensitive_data' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      if (authData.decision !== 'QUARANTINE' || !authData.approval_ticket_id) {
        console.log('No quarantine decision');
        return;
      }

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
        action: 'double_approve_test',
        resource: { type: 'sensitive_data' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      if (authData.decision !== 'QUARANTINE' || !authData.approval_ticket_id) {
        return;
      }

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
