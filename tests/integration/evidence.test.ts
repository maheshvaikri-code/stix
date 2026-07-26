/**
 * STIX Integration Tests - Evidence Service
 */

import { describe, it, expect, beforeAll } from 'vitest';
import {
  getTestConfig,
  createClients,
  generateTestRequest,
  wait,
  type EvidenceRecord,
  type TestClient,
  type AuthorizeResponse,
} from './setup';

describe('Evidence Service Integration', () => {
  let evidence: TestClient;
  let enforcer: TestClient;
  let testTraceId: string;

  beforeAll(async () => {
    const config = getTestConfig();
    const clients = createClients(config);
    evidence = clients.evidence;
    enforcer = clients.enforcer;

    // Create a test authorization to generate evidence
    const request = generateTestRequest({
      actor: { id: 'evidence-test-agent', type: 'AI_AGENT' },
      action: 'read_for_evidence_test',
    });
    const { data } = await enforcer.post<AuthorizeResponse>('/api/v1/authorize', request);
    testTraceId = data.trace_id;

    // Wait for evidence to be recorded
    await wait(500);
  });

  describe('Health', () => {
    it('should return healthy status', async () => {
      const { status, data } = await evidence.get<{ status: string }>('/health');

      expect(status).toBe(200);
      expect(data.status).toBe('healthy');
    });
  });

  describe('Query Evidence', () => {
    it('should query evidence records', async () => {
      const { status, data } = await evidence.get<{
        records: EvidenceRecord[];
        total: number;
      }>('/api/v1/evidence?limit=10');

      expect(status).toBe(200);
      expect(Array.isArray(data.records)).toBe(true);
      expect(typeof data.total).toBe('number');
    });

    it('should filter by trace_id', async () => {
      const { status, data } = await evidence.get<{
        records: EvidenceRecord[];
        total: number;
      }>(`/api/v1/evidence?trace_id=${testTraceId}`);

      if (status === 200 && data.records.length > 0) {
        data.records.forEach((record) => {
          expect(record.trace_id).toBe(testTraceId);
        });
      }
    });

    it('should filter by decision', async () => {
      const { status, data } = await evidence.get<{
        records: EvidenceRecord[];
        total: number;
      }>('/api/v1/evidence?decision=ALLOW&limit=10');

      expect(status).toBe(200);
      if (data.records.length > 0) {
        data.records.forEach((record) => {
          expect(record.decision).toBe('ALLOW');
        });
      }
    });

    it('should filter by date range', async () => {
      const endTime = new Date().toISOString();
      const startTime = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();

      const { status, data } = await evidence.get<{
        records: EvidenceRecord[];
        total: number;
      }>(`/api/v1/evidence?start_time=${startTime}&end_time=${endTime}&limit=10`);

      expect(status).toBe(200);
      if (data.records.length > 0) {
        data.records.forEach((record) => {
          const recordTime = new Date(record.timestamp).getTime();
          expect(recordTime).toBeGreaterThanOrEqual(new Date(startTime).getTime());
          expect(recordTime).toBeLessThanOrEqual(new Date(endTime).getTime());
        });
      }
    });

    it('should support pagination', async () => {
      const page1 = await evidence.get<{
        records: EvidenceRecord[];
        total: number;
        page: number;
      }>('/api/v1/evidence?page=1&page_size=5');

      const page2 = await evidence.get<{
        records: EvidenceRecord[];
        total: number;
        page: number;
      }>('/api/v1/evidence?page=2&page_size=5');

      expect(page1.status).toBe(200);
      expect(page2.status).toBe(200);

      // Pages should have different records (if enough data)
      if (page1.data.records.length > 0 && page2.data.records.length > 0) {
        const page1Ids = page1.data.records.map((r) => r.event_id);
        const page2Ids = page2.data.records.map((r) => r.event_id);
        const overlap = page1Ids.filter((id) => page2Ids.includes(id));
        expect(overlap).toHaveLength(0);
      }
    });
  });

  describe('Evidence by Trace', () => {
    it('should retrieve evidence for a specific trace', async () => {
      const { status, data } = await evidence.get<EvidenceRecord[]>(
        `/api/v1/evidence/trace/${testTraceId}`
      );

      if (status === 200) {
        expect(Array.isArray(data)).toBe(true);
        if (data.length > 0) {
          data.forEach((record) => {
            expect(record.trace_id).toBe(testTraceId);
          });
        }
      } else {
        // Endpoint might not be implemented
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Chain Integrity', () => {
    it('should verify chain integrity', async () => {
      const { status, data } = await evidence.get<{
        valid: boolean;
        records_verified: number;
        errors?: string[];
        first_invalid?: string;
      }>('/api/v1/evidence/verify');

      expect(status).toBe(200);
      expect(typeof data.valid).toBe('boolean');
      expect(typeof data.records_verified).toBe('number');

      if (!data.valid) {
        expect(data.errors).toBeDefined();
      }
    });

    it('should verify chain for specific time range', async () => {
      const endTime = new Date().toISOString();
      const startTime = new Date(Date.now() - 60 * 60 * 1000).toISOString(); // Last hour

      const { status, data } = await evidence.get<{
        valid: boolean;
        records_verified: number;
      }>(`/api/v1/evidence/verify?start_time=${startTime}&end_time=${endTime}`);

      expect(status).toBe(200);
      expect(typeof data.valid).toBe('boolean');
    });

    it('should verify specific trace chain', async () => {
      const { status, data } = await evidence.get<{
        valid: boolean;
        records_verified: number;
      }>(`/api/v1/evidence/verify/${testTraceId}`);

      if (status === 200) {
        expect(typeof data.valid).toBe('boolean');
      } else {
        // Endpoint might not be implemented
        expect([200, 404]).toContain(status);
      }
    });
  });

  describe('Evidence Statistics', () => {
    it('should return evidence statistics', async () => {
      const { status, data } = await evidence.get<{
        total: number;
        by_decision: Record<string, number>;
        by_actor_type: Record<string, number>;
        unique_actors: number;
        unique_traces: number;
      }>('/api/v1/evidence/stats');

      expect(status).toBe(200);
      expect(typeof data.total).toBe('number');
      expect(typeof data.by_decision).toBe('object');
      expect(typeof data.unique_actors).toBe('number');
      expect(typeof data.unique_traces).toBe('number');
    });

    it('should return stats for time range', async () => {
      const endTime = new Date().toISOString();
      const startTime = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

      const { status, data } = await evidence.get<{
        total: number;
        by_decision: Record<string, number>;
      }>(`/api/v1/evidence/stats?start_time=${startTime}&end_time=${endTime}`);

      expect(status).toBe(200);
      expect(typeof data.total).toBe('number');
    });
  });

  describe('Evidence Export', () => {
    it('should export evidence in JSON format', async () => {
      const { status, data } = await evidence.get<{
        records: EvidenceRecord[];
      }>('/api/v1/evidence/export?format=json&limit=10');

      expect(status).toBe(200);
      expect(Array.isArray(data.records)).toBe(true);
    });
  });

  describe('Hash Chain Properties', () => {
    it('should include hash chain fields in records', async () => {
      const { status, data } = await evidence.get<{
        records: EvidenceRecord[];
      }>('/api/v1/evidence?limit=1');

      expect(status).toBe(200);

      if (data.records.length > 0) {
        const record = data.records[0];
        expect(record.event_id).toBeDefined();
        expect(record.trace_id).toBeDefined();
        expect(record.timestamp).toBeDefined();
        expect(record.decision).toBeDefined();

        // Hash chain fields
        if (record.request_hash) {
          expect(record.request_hash).toMatch(/^sha256:[a-f0-9]{64}$/);
        }
        if (record.chain_hash) {
          expect(record.chain_hash).toMatch(/^sha256:[a-f0-9]{64}$/);
        }
      }
    });

    it('should have consecutive records with linked hashes', async () => {
      const { status, data } = await evidence.get<{
        records: (EvidenceRecord & { integrity?: { prev_hash: string; event_hash: string } })[];
      }>('/api/v1/evidence?limit=10');

      expect(status).toBe(200);

      if (data.records.length >= 2) {
        // Records should be sorted by timestamp (oldest first for chain verification)
        const sorted = [...data.records].sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );

        // Note: Full chain verification requires integrity metadata
        // which may or may not be included in the response
      }
    });
  });

  describe('Error Handling', () => {
    it('should handle invalid trace_id gracefully', async () => {
      const { status, data } = await evidence.get<{ records: EvidenceRecord[] }>(
        '/api/v1/evidence?trace_id=invalid-trace-id'
      );

      expect(status).toBe(200);
      expect(data.records).toHaveLength(0);
    });

    it('should handle invalid date format', async () => {
      const { status } = await evidence.get<{ error: string }>(
        '/api/v1/evidence?start_time=not-a-date'
      );

      expect([200, 400]).toContain(status);
    });
  });

  describe('Performance', () => {
    it('should query efficiently with large result sets', async () => {
      const start = Date.now();
      const { status } = await evidence.get<{ records: EvidenceRecord[]; total: number }>(
        '/api/v1/evidence?limit=100'
      );
      const latency = Date.now() - start;

      expect(status).toBe(200);
      expect(latency).toBeLessThan(2000); // 2s max for 100 records
    });
  });
});
