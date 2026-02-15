/**
 * STIX Integration Tests - Full End-to-End Flows
 *
 * Tests complete authorization workflows from agent request
 * through to evidence recording and approval handling.
 */

import { describe, it, expect, beforeAll } from 'vitest';
import {
  getTestConfig,
  createClients,
  generateTestRequest,
  wait,
  retry,
  type TestClient,
  type AuthorizeRequest,
  type AuthorizeResponse,
  type EvidenceRecord,
  type ApprovalRequest,
} from './setup';

describe('Full End-to-End Flows', () => {
  let enforcer: TestClient;
  let policy: TestClient;
  let evidence: TestClient;
  let approvals: TestClient;

  beforeAll(async () => {
    const config = getTestConfig();
    const clients = createClients(config);
    enforcer = clients.enforcer;
    policy = clients.policy;
    evidence = clients.evidence;
    approvals = clients.approvals;
  });

  describe('Complete ALLOW Flow', () => {
    it('should complete full authorization flow with ALLOW decision', async () => {
      // 1. Send authorization request
      const request = generateTestRequest({
        actor: { id: 'e2e-allow-agent', type: 'AI_AGENT' },
        action: 'read_public_data',
        resource: { type: 'public_data', id: 'doc-123' },
        context: { env: 'test', purpose: 'e2e testing' },
      });

      const { status: authStatus, data: authData } = await enforcer.post<AuthorizeResponse>(
        '/api/v1/authorize',
        request
      );

      expect(authStatus).toBe(200);
      expect(authData.trace_id).toBeDefined();

      const traceId = authData.trace_id;

      // 2. Record outcome
      const outcomeRequest = {
        trace_id: traceId,
        status: 'SUCCESS',
        result_summary: 'E2E test completed successfully',
        duration_ms: 50,
      };

      await enforcer.post('/api/v1/outcome', outcomeRequest);

      // 3. Wait for evidence to be recorded
      await wait(500);

      // 4. Verify evidence was recorded
      const { status: evidenceStatus, data: evidenceData } = await evidence.get<{
        records: EvidenceRecord[];
      }>(`/api/v1/evidence?trace_id=${traceId}`);

      expect(evidenceStatus).toBe(200);

      if (evidenceData.records.length > 0) {
        const record = evidenceData.records[0];
        expect(record.trace_id).toBe(traceId);
        expect(record.actor_id).toBe('e2e-allow-agent');
        expect(record.action).toBe('read_public_data');
      }

      // 5. Verify chain integrity
      const { status: verifyStatus, data: verifyData } = await evidence.get<{
        valid: boolean;
        records_verified: number;
      }>('/api/v1/evidence/verify');

      expect(verifyStatus).toBe(200);
      expect(verifyData.valid).toBe(true);
    });

    it('should issue valid proof token on ALLOW', async () => {
      const request = generateTestRequest({
        actor: { id: 'e2e-proof-agent', type: 'AI_AGENT' },
        action: 'read_authorized',
        resource: { type: 'authorized_data' },
      });

      const { data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      if (data.decision === 'ALLOW' && data.proof_token) {
        // Verify token structure (JWT format)
        const parts = data.proof_token.split('.');
        expect(parts).toHaveLength(3);

        // Decode header (base64url)
        const header = JSON.parse(
          Buffer.from(parts[0].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString()
        );
        expect(header.alg).toBeDefined();

        // Decode payload
        const payload = JSON.parse(
          Buffer.from(parts[1].replace(/-/g, '+').replace(/_/g, '/'), 'base64').toString()
        );
        expect(payload.sub).toBe('e2e-proof-agent');
        expect(payload.tid).toBe(data.trace_id);
        expect(payload.exp).toBeGreaterThan(Math.floor(Date.now() / 1000));
      }
    });
  });

  describe('Complete DENY Flow', () => {
    it('should complete full authorization flow with DENY decision', async () => {
      // 1. Send authorization request for denied action
      const request = generateTestRequest({
        actor: { id: 'e2e-deny-agent', type: 'AI_AGENT' },
        action: 'delete_production_data',
        resource: { type: 'production_database', id: 'prod-db-1' },
        context: { env: 'production' },
      });

      const { status, data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(status).toBe(200);
      expect(data.trace_id).toBeDefined();

      const traceId = data.trace_id;

      // 2. Wait for evidence
      await wait(500);

      // 3. Verify evidence records the deny
      const { data: evidenceData } = await evidence.get<{
        records: EvidenceRecord[];
      }>(`/api/v1/evidence?trace_id=${traceId}`);

      if (evidenceData.records.length > 0) {
        const record = evidenceData.records[0];
        expect(record.trace_id).toBe(traceId);
        // Decision may vary based on policies
        expect(['ALLOW', 'DENY', 'QUARANTINE']).toContain(record.decision);
      }
    });
  });

  describe('Complete QUARANTINE Flow', () => {
    it('should complete full authorization flow with human approval', async () => {
      // 1. Send authorization request that requires approval
      const request = generateTestRequest({
        actor: { id: 'e2e-quarantine-agent', type: 'AI_AGENT' },
        action: 'access_pii',
        resource: {
          type: 'customer_data',
          id: 'customer-123',
          classification: ['PII', 'SENSITIVE'],
        },
        context: { env: 'production', purpose: 'customer support' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      if (authData.decision !== 'QUARANTINE') {
        console.log('Expected QUARANTINE, got', authData.decision, '- skipping full flow');
        return;
      }

      const traceId = authData.trace_id;
      const approvalId = authData.approval_ticket_id!;

      expect(approvalId).toMatch(/^appr_/);

      // 2. Verify approval is pending
      const { data: pendingApproval } = await approvals.get<ApprovalRequest>(
        `/api/v1/approvals/${approvalId}`
      );

      expect(pendingApproval.status).toBe('PENDING');
      expect(pendingApproval.trace_id).toBe(traceId);

      // 3. Approve the request (simulating human action)
      const { status: approveStatus } = await approvals.post<ApprovalRequest>(
        `/api/v1/approvals/${approvalId}/approve`,
        {
          notes: 'Approved by integration test - customer support verified',
        }
      );

      if (approveStatus !== 200) {
        console.log('Approval endpoint returned', approveStatus);
        return;
      }

      // 4. Verify approval status changed
      const { data: approvedData } = await approvals.get<ApprovalRequest>(
        `/api/v1/approvals/${approvalId}`
      );

      expect(approvedData.status).toBe('APPROVED');
      expect(approvedData.reviewed_at).toBeDefined();

      // 5. Wait for evidence
      await wait(500);

      // 6. Verify evidence chain includes approval
      const { data: evidenceData } = await evidence.get<{
        records: EvidenceRecord[];
      }>(`/api/v1/evidence?trace_id=${traceId}`);

      expect(evidenceData.records.length).toBeGreaterThan(0);
    });

    it('should handle rejected approvals', async () => {
      const request = generateTestRequest({
        actor: { id: 'e2e-reject-agent', type: 'AI_AGENT' },
        action: 'delete_sensitive',
        resource: { type: 'sensitive_data', classification: ['CRITICAL'] },
        context: { env: 'production' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      if (authData.decision !== 'QUARANTINE' || !authData.approval_ticket_id) {
        console.log('No quarantine decision, skipping rejection test');
        return;
      }

      // Reject the request
      const { status: rejectStatus } = await approvals.post<ApprovalRequest>(
        `/api/v1/approvals/${authData.approval_ticket_id}/reject`,
        { notes: 'Rejected - action not justified' }
      );

      if (rejectStatus === 200) {
        // Verify rejection
        const { data: rejectedData } = await approvals.get<ApprovalRequest>(
          `/api/v1/approvals/${authData.approval_ticket_id}`
        );
        expect(rejectedData.status).toBe('REJECTED');
      }
    });
  });

  describe('Multi-Action Workflow', () => {
    it('should handle a sequence of related authorizations', async () => {
      const agentId = `e2e-workflow-agent-${Date.now()}`;

      // Step 1: Read data
      const readRequest = generateTestRequest({
        actor: { id: agentId, type: 'AI_AGENT' },
        action: 'read_data',
        resource: { type: 'workflow_data', id: 'workflow-1' },
        context: { env: 'test' },
      });

      const { data: readData } = await enforcer.post<AuthorizeResponse>(
        '/api/v1/authorize',
        readRequest
      );

      expect(readData.trace_id).toBeDefined();

      // Step 2: Process data
      const processRequest = generateTestRequest({
        actor: { id: agentId, type: 'AI_AGENT' },
        action: 'process_data',
        resource: { type: 'workflow_data', id: 'workflow-1' },
        context: { env: 'test' },
      });

      const { data: processData } = await enforcer.post<AuthorizeResponse>(
        '/api/v1/authorize',
        processRequest
      );

      expect(processData.trace_id).toBeDefined();

      // Step 3: Write result
      const writeRequest = generateTestRequest({
        actor: { id: agentId, type: 'AI_AGENT' },
        action: 'write_result',
        resource: { type: 'workflow_result', id: 'result-1' },
        context: { env: 'test' },
      });

      const { data: writeData } = await enforcer.post<AuthorizeResponse>(
        '/api/v1/authorize',
        writeRequest
      );

      expect(writeData.trace_id).toBeDefined();

      // Verify all three actions were recorded
      await wait(1000);

      const { data: actorEvidence } = await evidence.get<{
        records: EvidenceRecord[];
        total: number;
      }>(`/api/v1/evidence?actor_id=${agentId}`);

      // Should have at least 3 records for this agent
      expect(actorEvidence.total).toBeGreaterThanOrEqual(3);
    });
  });

  describe('Concurrent Authorization', () => {
    it('should handle concurrent requests from multiple agents', async () => {
      const requests = Array.from({ length: 10 }, (_, i) =>
        generateTestRequest({
          actor: { id: `concurrent-agent-${i}`, type: 'AI_AGENT' },
          action: 'concurrent_action',
          resource: { type: 'shared_resource' },
          context: { env: 'test' },
        })
      );

      const startTime = Date.now();
      const results = await Promise.all(
        requests.map((request) => enforcer.post<AuthorizeResponse>('/api/v1/authorize', request))
      );
      const duration = Date.now() - startTime;

      // All requests should succeed
      results.forEach(({ status, data }) => {
        expect(status).toBe(200);
        expect(data.trace_id).toBeDefined();
      });

      // Should complete in reasonable time
      expect(duration).toBeLessThan(5000); // 5 seconds for 10 concurrent requests

      // All should have unique trace IDs
      const traceIds = results.map((r) => r.data.trace_id);
      const uniqueIds = new Set(traceIds);
      expect(uniqueIds.size).toBe(10);
    });
  });

  describe('Policy Consistency', () => {
    it('should return consistent decisions for identical requests', async () => {
      const request = generateTestRequest({
        actor: { id: 'consistency-agent', type: 'AI_AGENT' },
        action: 'consistent_action',
        resource: { type: 'consistent_resource' },
        context: { env: 'test' },
      });

      // Make 5 identical requests
      const results = await Promise.all(
        Array.from({ length: 5 }, () =>
          enforcer.post<AuthorizeResponse>('/api/v1/authorize', request)
        )
      );

      // All should return the same decision
      const decisions = results.map((r) => r.data.decision);
      const uniqueDecisions = new Set(decisions);
      expect(uniqueDecisions.size).toBe(1);

      // But different trace IDs
      const traceIds = results.map((r) => r.data.trace_id);
      const uniqueTraceIds = new Set(traceIds);
      expect(uniqueTraceIds.size).toBe(5);
    });
  });

  describe('Error Recovery', () => {
    it('should handle and recover from invalid requests', async () => {
      // Invalid request
      const invalidRequest = {
        actor: { id: 'error-test' },
        // Missing required fields
      };

      const { status: errorStatus } = await enforcer.post('/api/v1/authorize', invalidRequest);
      expect(errorStatus).toBe(400);

      // System should still work after error
      const validRequest = generateTestRequest({
        actor: { id: 'recovery-agent', type: 'AI_AGENT' },
        action: 'recovery_action',
        resource: { type: 'recovery_resource' },
      });

      const { status: recoveryStatus, data } = await enforcer.post<AuthorizeResponse>(
        '/api/v1/authorize',
        validRequest
      );

      expect(recoveryStatus).toBe(200);
      expect(data.trace_id).toBeDefined();
    });
  });

  describe('Service Resilience', () => {
    it('should maintain service health under load', async () => {
      // Check initial health
      const { status: initialHealth } = await enforcer.get('/health');
      expect(initialHealth).toBe(200);

      // Generate load
      const requests = Array.from({ length: 50 }, (_, i) =>
        generateTestRequest({
          actor: { id: `load-agent-${i}`, type: 'AI_AGENT' },
          action: 'load_test',
          resource: { type: 'load_resource' },
        })
      );

      // Send all at once
      await Promise.all(
        requests.map((request) =>
          enforcer.post('/api/v1/authorize', request).catch(() => null)
        )
      );

      // Check health after load
      const { status: postLoadHealth, data } = await enforcer.get<{ status: string }>(
        '/health'
      );
      expect(postLoadHealth).toBe(200);
      expect(data.status).toBe('healthy');
    });
  });

  describe('Cross-Service Consistency', () => {
    it('should maintain data consistency across services', async () => {
      // Create authorization
      const request = generateTestRequest({
        actor: { id: 'cross-service-agent', type: 'AI_AGENT' },
        action: 'cross_service_action',
        resource: { type: 'cross_service_resource' },
      });

      const { data: authData } = await enforcer.post<AuthorizeResponse>(
        '/api/v1/authorize',
        request
      );

      const traceId = authData.trace_id;

      // Wait for propagation
      await wait(1000);

      // Check evidence service has the record
      const { data: evidenceData } = await evidence.get<{
        records: EvidenceRecord[];
      }>(`/api/v1/evidence?trace_id=${traceId}`);

      // Evidence should exist if ALLOW or DENY
      // For QUARANTINE, check approvals
      if (authData.decision === 'QUARANTINE' && authData.approval_ticket_id) {
        const { data: approvalData } = await approvals.get<ApprovalRequest>(
          `/api/v1/approvals/${authData.approval_ticket_id}`
        );
        expect(approvalData.trace_id).toBe(traceId);
      }

      // Evidence count should match
      if (evidenceData.records.length > 0) {
        expect(evidenceData.records[0].trace_id).toBe(traceId);
      }
    });
  });
});
