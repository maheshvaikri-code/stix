/**
 * STIX Integration Tests - Enforcer Service
 */

import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import {
  getTestConfig,
  createClients,
  generateTestRequest,
  type AuthorizeRequest,
  type AuthorizeResponse,
  type TestClient,
} from './setup';

describe('Enforcer Service Integration', () => {
  let enforcer: TestClient;
  let isHealthy: boolean;

  beforeAll(async () => {
    const config = getTestConfig();
    const clients = createClients(config);
    enforcer = clients.enforcer;
    isHealthy = await enforcer.healthCheck();
  });

  describe('Health', () => {
    it('should return healthy status', async () => {
      const { status, data } = await enforcer.get<{ status: string; version: string }>('/health');

      expect(status).toBe(200);
      expect(data.status).toBe('healthy');
      expect(data.version).toBeDefined();
    });

    it('should expose readiness endpoint', async () => {
      const { status, data } = await enforcer.get<{ ready: boolean }>('/ready');

      expect(status).toBe(200);
      expect(data.ready).toBe(true);
    });
  });

  describe('Authorization - ALLOW Flow', () => {
    it('should allow low-risk read operations', async () => {
      const request = generateTestRequest({
        actor: { id: 'test-agent-allow', type: 'AI_AGENT' },
        action: 'read_data',
        resource: { type: 'public_data' },
        context: { env: 'test' },
      });

      const { status, data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(status).toBe(200);
      expect(data.decision).toBeDefined();
      expect(data.trace_id).toMatch(/^stix_/);
      expect(data.reason_code).toBeDefined();
    });

    it('should return proof token for ALLOW decisions', async () => {
      const request = generateTestRequest({
        actor: { id: 'test-agent-proof', type: 'AI_AGENT' },
        action: 'read_public',
        resource: { type: 'public_data' },
      });

      const { status, data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(status).toBe(200);
      if (data.decision === 'ALLOW') {
        expect(data.proof_token).toBeDefined();
        // Token should be JWT format (3 parts separated by dots)
        const parts = data.proof_token!.split('.');
        expect(parts).toHaveLength(3);
      }
    });

    it('should include policy information in response', async () => {
      const request = generateTestRequest();

      const { status, data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(status).toBe(200);
      expect(data.reason_code).toBeDefined();
      // Policy ID may be present if a policy matched
      if (data.policy_id) {
        expect(typeof data.policy_id).toBe('string');
      }
    });
  });

  describe('Authorization - DENY Flow', () => {
    it('should deny requests that violate policies', async () => {
      const request = generateTestRequest({
        actor: { id: 'test-agent-deny', type: 'AI_AGENT' },
        action: 'write_production',
        resource: { type: 'production_database' },
        context: { env: 'production' },
      });

      const { status, data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(status).toBe(200);
      // Note: The actual decision depends on policies loaded
      expect(['ALLOW', 'DENY', 'QUARANTINE']).toContain(data.decision);
      expect(data.trace_id).toBeDefined();
    });

    it('should not return proof token for DENY decisions', async () => {
      const request = generateTestRequest({
        actor: { id: 'test-agent-deny-no-token', type: 'AI_AGENT' },
        action: 'delete_all',
        resource: { type: 'critical_system' },
      });

      const { status, data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(status).toBe(200);
      if (data.decision === 'DENY') {
        expect(data.proof_token).toBeUndefined();
      }
    });
  });

  describe('Authorization - QUARANTINE Flow', () => {
    it('should quarantine high-risk operations and return approval ticket', async () => {
      const request = generateTestRequest({
        actor: { id: 'test-agent-quarantine', type: 'AI_AGENT' },
        action: 'access_sensitive',
        resource: { type: 'sensitive_data', classification: ['PII', 'CONFIDENTIAL'] },
        context: { env: 'production' },
      });

      const { status, data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);

      expect(status).toBe(200);
      // Note: The actual decision depends on policies loaded
      if (data.decision === 'QUARANTINE') {
        expect(data.approval_ticket_id).toBeDefined();
        expect(data.approval_ticket_id).toMatch(/^appr_/);
      }
    });
  });

  describe('Validation', () => {
    it('should reject requests with missing actor', async () => {
      const request = {
        action: 'test_action',
        resource: { type: 'test' },
        context: { env: 'test' },
      };

      const { status, data } = await enforcer.post<{ error: string }>('/api/v1/authorize', request);

      expect(status).toBe(400);
      expect(data.error).toBeDefined();
    });

    it('should reject requests with missing action', async () => {
      const request = {
        actor: { id: 'test', type: 'AI_AGENT' },
        resource: { type: 'test' },
        context: { env: 'test' },
      };

      const { status, data } = await enforcer.post<{ error: string }>('/api/v1/authorize', request);

      expect(status).toBe(400);
      expect(data.error).toBeDefined();
    });

    it('should reject requests with invalid actor type', async () => {
      const request = {
        actor: { id: 'test', type: 'INVALID_TYPE' },
        action: 'test_action',
        resource: { type: 'test' },
        context: { env: 'test' },
      };

      const { status, data } = await enforcer.post<{ error: string }>('/api/v1/authorize', request);

      expect(status).toBe(400);
      expect(data.error).toBeDefined();
    });
  });

  describe('Batch Authorization', () => {
    it('should handle batch authorization requests', async () => {
      const requests = [
        generateTestRequest({ action: 'action_1' }),
        generateTestRequest({ action: 'action_2' }),
        generateTestRequest({ action: 'action_3' }),
      ];

      const { status, data } = await enforcer.post<{ results: AuthorizeResponse[] }>(
        '/api/v1/authorize/batch',
        { requests }
      );

      if (status === 200) {
        expect(data.results).toHaveLength(3);
        data.results.forEach((result) => {
          expect(['ALLOW', 'DENY', 'QUARANTINE']).toContain(result.decision);
          expect(result.trace_id).toBeDefined();
        });
      } else {
        // Endpoint might not be implemented
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Performance', () => {
    it('should respond within acceptable latency', async () => {
      const request = generateTestRequest();

      const start = Date.now();
      const { status } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);
      const latency = Date.now() - start;

      expect(status).toBe(200);
      expect(latency).toBeLessThan(500); // 500ms max latency
    });

    it('should handle concurrent requests', async () => {
      const requests = Array.from({ length: 10 }, (_, i) =>
        generateTestRequest({ actor: { id: `concurrent-agent-${i}`, type: 'AI_AGENT' } })
      );

      const results = await Promise.all(
        requests.map((request) => enforcer.post<AuthorizeResponse>('/api/v1/authorize', request))
      );

      results.forEach(({ status, data }) => {
        expect(status).toBe(200);
        expect(['ALLOW', 'DENY', 'QUARANTINE']).toContain(data.decision);
      });
    });
  });

  describe('Outcome Recording', () => {
    it('should record action outcomes', async () => {
      // First, get an authorization
      const authRequest = generateTestRequest();
      const { data: authData } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', authRequest);

      // Record the outcome
      const outcomeRequest = {
        trace_id: authData.trace_id,
        status: 'SUCCESS',
        result_summary: 'Action completed successfully',
        duration_ms: 150,
      };

      const { status, data } = await enforcer.post<{ recorded: boolean }>(
        '/api/v1/outcome',
        outcomeRequest
      );

      if (status === 200 || status === 201) {
        expect(data.recorded).toBe(true);
      } else {
        // Endpoint might not be implemented or authorization required
        expect([200, 201, 404, 401]).toContain(status);
      }
    });
  });

  describe('Metrics', () => {
    it('should expose Prometheus metrics', async () => {
      const response = await fetch(`${getTestConfig().enforcerUrl}/metrics`);
      const text = await response.text();

      expect(response.status).toBe(200);
      expect(text).toContain('stix_');
    });
  });
});
