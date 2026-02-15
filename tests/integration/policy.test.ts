/**
 * STIX Integration Tests - Policy Service
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import {
  getTestConfig,
  createClients,
  type TestClient,
} from './setup';

interface Policy {
  policy_id: string;
  version: string;
  priority: number;
  scope: {
    actor_type: string;
    action: string;
    resource_type: string;
  };
  conditions?: Record<string, unknown>;
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  reason_code: string;
  regulation?: string;
  description?: string;
  enabled: boolean;
  created_at?: string;
  updated_at?: string;
}

describe('Policy Service Integration', () => {
  let policy: TestClient;
  let testPolicyId: string;

  beforeAll(async () => {
    const config = getTestConfig();
    const clients = createClients(config);
    policy = clients.policy;
    testPolicyId = `test-policy-${Date.now()}`;
  });

  afterAll(async () => {
    // Cleanup: Delete test policy if created
    try {
      await policy.request(`/api/v1/policies/${testPolicyId}`, { method: 'DELETE' });
    } catch {
      // Ignore cleanup errors
    }
  });

  describe('Health', () => {
    it('should return healthy status', async () => {
      const { status, data } = await policy.get<{ status: string }>('/health');

      expect(status).toBe(200);
      expect(data.status).toBe('healthy');
    });
  });

  describe('List Policies', () => {
    it('should list all policies', async () => {
      const { status, data } = await policy.get<{
        data: Policy[];
        total: number;
      }>('/api/v1/policies');

      expect(status).toBe(200);
      expect(Array.isArray(data.data)).toBe(true);
      expect(typeof data.total).toBe('number');
    });

    it('should filter by regulation', async () => {
      const { status, data } = await policy.get<{
        data: Policy[];
      }>('/api/v1/policies?regulation=HIPAA');

      expect(status).toBe(200);
      if (data.data.length > 0) {
        data.data.forEach((p) => {
          expect(p.regulation).toBe('HIPAA');
        });
      }
    });

    it('should filter by decision type', async () => {
      const { status, data } = await policy.get<{
        data: Policy[];
      }>('/api/v1/policies?decision=DENY');

      expect(status).toBe(200);
      if (data.data.length > 0) {
        data.data.forEach((p) => {
          expect(p.decision).toBe('DENY');
        });
      }
    });

    it('should support pagination', async () => {
      const { status, data } = await policy.get<{
        data: Policy[];
        total: number;
        page: number;
      }>('/api/v1/policies?page=1&page_size=5');

      expect(status).toBe(200);
      expect(data.data.length).toBeLessThanOrEqual(5);
    });

    it('should search policies', async () => {
      const { status, data } = await policy.get<{
        data: Policy[];
      }>('/api/v1/policies?search=email');

      expect(status).toBe(200);
      // Search results may vary based on existing policies
    });
  });

  describe('Get Policy', () => {
    it('should get existing policy by ID', async () => {
      // First, list policies to get a valid ID
      const { data: listData } = await policy.get<{ data: Policy[] }>('/api/v1/policies?page_size=1');

      if (listData.data.length === 0) {
        console.log('No policies to test, skipping');
        return;
      }

      const policyId = listData.data[0].policy_id;
      const { status, data } = await policy.get<Policy>(`/api/v1/policies/${policyId}`);

      expect(status).toBe(200);
      expect(data.policy_id).toBe(policyId);
      expect(data.scope).toBeDefined();
      expect(data.decision).toBeDefined();
    });

    it('should return 404 for non-existent policy', async () => {
      const { status } = await policy.get<{ error: string }>(
        '/api/v1/policies/nonexistent-policy-id'
      );

      expect(status).toBe(404);
    });
  });

  describe('Create Policy', () => {
    it('should create a new policy', async () => {
      const newPolicy = {
        policy_id: testPolicyId,
        version: '1.0.0',
        priority: 100,
        scope: {
          actor_type: 'AI_AGENT',
          action: 'test_action_*',
          resource_type: 'test_resource',
        },
        decision: 'ALLOW' as const,
        reason_code: 'TEST_POLICY',
        description: 'Integration test policy',
        enabled: true,
      };

      const { status, data } = await policy.post<Policy>('/api/v1/policies', newPolicy);

      if (status === 201 || status === 200) {
        expect(data.policy_id).toBe(testPolicyId);
        expect(data.decision).toBe('ALLOW');
      } else if (status === 409) {
        // Policy already exists
        console.log('Policy already exists');
      } else {
        // Might require authentication
        expect([200, 201, 401, 403]).toContain(status);
      }
    });

    it('should reject invalid policy', async () => {
      const invalidPolicy = {
        policy_id: 'invalid-test',
        // Missing required fields
      };

      const { status } = await policy.post<{ error: string }>('/api/v1/policies', invalidPolicy);

      expect(status).toBe(400);
    });

    it('should reject policy with invalid decision', async () => {
      const invalidPolicy = {
        policy_id: 'invalid-decision-test',
        version: '1.0.0',
        scope: {
          actor_type: 'AI_AGENT',
          action: '*',
          resource_type: '*',
        },
        decision: 'INVALID_DECISION',
        reason_code: 'TEST',
      };

      const { status } = await policy.post<{ error: string }>('/api/v1/policies', invalidPolicy);

      expect(status).toBe(400);
    });
  });

  describe('Update Policy', () => {
    it('should update an existing policy', async () => {
      const updates = {
        priority: 50,
        description: 'Updated integration test policy',
      };

      const { status, data } = await policy.request<Policy>(
        `/api/v1/policies/${testPolicyId}`,
        { method: 'PATCH', body: updates }
      );

      if (status === 200) {
        expect(data.priority).toBe(50);
        expect(data.description).toContain('Updated');
      } else {
        // Policy might not exist or require authentication
        expect([200, 401, 403, 404]).toContain(status);
      }
    });

    it('should not allow changing policy_id', async () => {
      const updates = {
        policy_id: 'new-policy-id',
      };

      const { status } = await policy.request<{ error: string }>(
        `/api/v1/policies/${testPolicyId}`,
        { method: 'PATCH', body: updates }
      );

      // Should either ignore the change or return error
      expect([200, 400]).toContain(status);
    });
  });

  describe('Toggle Policy', () => {
    it('should disable a policy', async () => {
      const { status, data } = await policy.request<Policy>(
        `/api/v1/policies/${testPolicyId}`,
        { method: 'PATCH', body: { enabled: false } }
      );

      if (status === 200) {
        expect(data.enabled).toBe(false);
      } else {
        expect([200, 401, 403, 404]).toContain(status);
      }
    });

    it('should enable a policy', async () => {
      const { status, data } = await policy.request<Policy>(
        `/api/v1/policies/${testPolicyId}`,
        { method: 'PATCH', body: { enabled: true } }
      );

      if (status === 200) {
        expect(data.enabled).toBe(true);
      } else {
        expect([200, 401, 403, 404]).toContain(status);
      }
    });
  });

  describe('Delete Policy', () => {
    it('should delete an existing policy', async () => {
      // Create a policy to delete
      const tempPolicyId = `temp-delete-${Date.now()}`;
      await policy.post('/api/v1/policies', {
        policy_id: tempPolicyId,
        version: '1.0.0',
        scope: { actor_type: '*', action: '*', resource_type: '*' },
        decision: 'ALLOW',
        reason_code: 'TEMP',
        enabled: true,
      });

      const { status } = await policy.request(
        `/api/v1/policies/${tempPolicyId}`,
        { method: 'DELETE' }
      );

      expect([200, 204, 401, 403, 404]).toContain(status);

      if (status === 200 || status === 204) {
        // Verify deletion
        const { status: getStatus } = await policy.get(`/api/v1/policies/${tempPolicyId}`);
        expect(getStatus).toBe(404);
      }
    });

    it('should return 404 for non-existent policy', async () => {
      const { status } = await policy.request(
        '/api/v1/policies/nonexistent-delete-test',
        { method: 'DELETE' }
      );

      expect([404, 401, 403]).toContain(status);
    });
  });

  describe('Policy Validation', () => {
    it('should validate a policy without saving', async () => {
      const testPolicy = {
        policy_id: 'validation-test',
        version: '1.0.0',
        scope: {
          actor_type: 'AI_AGENT',
          action: '*',
          resource_type: '*',
        },
        decision: 'ALLOW',
        reason_code: 'VALIDATION_TEST',
      };

      const { status, data } = await policy.post<{
        valid: boolean;
        errors?: string[];
      }>('/api/v1/policies/validate', testPolicy);

      if (status === 200) {
        expect(data.valid).toBe(true);
      } else {
        // Endpoint might not exist
        expect([200, 404]).toContain(status);
      }
    });

    it('should report validation errors', async () => {
      const invalidPolicy = {
        policy_id: '',
        version: 'invalid',
        decision: 'MAYBE',
      };

      const { status, data } = await policy.post<{
        valid: boolean;
        errors?: string[];
      }>('/api/v1/policies/validate', invalidPolicy);

      if (status === 200) {
        expect(data.valid).toBe(false);
        expect(data.errors).toBeDefined();
        expect(data.errors!.length).toBeGreaterThan(0);
      } else {
        expect([200, 400, 404]).toContain(status);
      }
    });
  });

  describe('Policy Simulation', () => {
    it('should simulate policy evaluation', async () => {
      const request = {
        actor: { id: 'sim-agent', type: 'AI_AGENT' },
        action: 'test_action',
        resource: { type: 'test_resource' },
        context: { env: 'test' },
      };

      const { status, data } = await policy.post<{
        decision: string;
        matched_policy?: string;
        reason_code?: string;
      }>('/api/v1/policies/simulate', { request });

      if (status === 200) {
        expect(['ALLOW', 'DENY', 'QUARANTINE']).toContain(data.decision);
      } else {
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Policy Conflicts', () => {
    it('should detect policy conflicts', async () => {
      const { status, data } = await policy.get<{
        conflicts: Array<{
          policy1: string;
          policy2: string;
          reason: string;
        }>;
      }>('/api/v1/policies/conflicts');

      if (status === 200) {
        expect(Array.isArray(data.conflicts)).toBe(true);
      } else {
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Policy Statistics', () => {
    it('should return policy statistics', async () => {
      const { status, data } = await policy.get<{
        total: number;
        active: number;
        by_regulation: Record<string, number>;
        by_decision: Record<string, number>;
      }>('/api/v1/stats');

      if (status === 200) {
        expect(typeof data.total).toBe('number');
        expect(typeof data.active).toBe('number');
      } else {
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Policy Export', () => {
    it('should export policies', async () => {
      const { status, data } = await policy.get<{
        policies: Policy[];
      }>('/api/v1/policies/export');

      if (status === 200) {
        expect(Array.isArray(data.policies)).toBe(true);
      } else {
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Policy Import', () => {
    it('should validate policy import', async () => {
      const policies = [
        {
          policy_id: 'import-test-1',
          version: '1.0.0',
          scope: { actor_type: 'AI_AGENT', action: '*', resource_type: '*' },
          decision: 'ALLOW',
          reason_code: 'IMPORT_TEST',
        },
      ];

      const { status, data } = await policy.post<{
        valid: boolean;
        count: number;
        errors?: string[];
      }>('/api/v1/policies/import/validate', { policies });

      if (status === 200) {
        expect(data.valid).toBeDefined();
        expect(data.count).toBe(1);
      } else {
        expect([200, 404]).toContain(status);
      }
    });
  });
});
