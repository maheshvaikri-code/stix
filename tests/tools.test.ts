/**
 * STIX Tools Integration Tests
 * Tests for simulate, replay, and verify tools
 */

import { describe, it, expect, beforeAll, afterAll } from 'vitest';
import * as fs from 'fs';
import * as path from 'path';
import * as os from 'os';

// =============================================================================
// TEST DATA
// =============================================================================

const testPolicy = {
  policy_id: 'test-allow-read',
  version: '1.0.0',
  priority: 100,
  scope: {
    actor_type: 'AI_AGENT',
    action: 'read_*',
    resource_type: 'public_data',
  },
  decision: 'ALLOW',
  reason_code: 'TEST_ALLOWED',
  controls: ['TEST:CTRL1'],
  regulations: ['TEST'],
  active: true,
};

const testDenyPolicy = {
  policy_id: 'test-deny-write',
  version: '1.0.0',
  priority: 10,
  scope: {
    actor_type: 'AI_AGENT',
    action: 'write_*',
    resource_type: 'production_db',
  },
  decision: 'DENY',
  reason_code: 'PROD_BLOCKED',
  controls: ['TEST:CTRL2'],
  regulations: ['TEST'],
  active: true,
};

const testEvidenceBundle = {
  trace_id: 'stix_12345678-1234-1234-1234-123456789abc',
  events: [
    {
      event_type: 'DECISION',
      trace_id: 'stix_12345678-1234-1234-1234-123456789abc',
      timestamp: '2025-01-27T12:00:00.000Z',
      decision: 'ALLOW',
      reason_code: 'TEST_ALLOWED',
      actor: { id: 'agent-1', type: 'AI_AGENT' },
      action: { name: 'read_file' },
      resource: { type: 'public_data', id: 'file-1' },
      context: { env: 'dev' },
      policy: {
        id: 'test-allow-read',
        version: '1.0.0',
        hash: 'sha256:abcd1234',
      },
      obligations: [],
    },
  ],
};

// =============================================================================
// TEST HELPERS
// =============================================================================

let tempDir: string;

function createTempDir(): string {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'stix-test-'));
  return dir;
}

function writeTempFile(filename: string, content: string): string {
  const filepath = path.join(tempDir, filename);
  fs.writeFileSync(filepath, content);
  return filepath;
}

function cleanupTempDir(): void {
  if (tempDir && fs.existsSync(tempDir)) {
    fs.rmSync(tempDir, { recursive: true });
  }
}

// =============================================================================
// POLICY LOADER TESTS
// =============================================================================

describe('Policy Loader', () => {
  beforeAll(() => {
    tempDir = createTempDir();
  });

  afterAll(() => {
    cleanupTempDir();
  });

  it('should load policy from JSON file', async () => {
    const policyFile = writeTempFile('policy.json', JSON.stringify([testPolicy]));

    // Import dynamically to avoid module resolution issues in tests
    const { loadPoliciesFromFile } = await import('@stix/shared');
    const policies = await loadPoliciesFromFile(policyFile);

    expect(policies).toHaveLength(1);
    expect(policies[0].id).toBe('test-allow-read');
    expect(policies[0].decision).toBe('ALLOW');
  });

  it('should load multiple policies from JSON array', async () => {
    const policyFile = writeTempFile(
      'policies.json',
      JSON.stringify([testPolicy, testDenyPolicy])
    );

    const { loadPoliciesFromFile } = await import('@stix/shared');
    const policies = await loadPoliciesFromFile(policyFile);

    expect(policies).toHaveLength(2);
    expect(policies.map(p => p.decision)).toContain('ALLOW');
    expect(policies.map(p => p.decision)).toContain('DENY');
  });

  it('should compute policy hash', async () => {
    const { computePolicyHash, computePackHash } = await import('@stix/shared');

    const hash1 = computePolicyHash(testPolicy as any);
    const hash2 = computePolicyHash(testPolicy as any);

    // Same policy should produce same hash
    expect(hash1).toBe(hash2);
    expect(hash1).toHaveLength(64); // SHA-256 hex

    // Pack hash should be different
    const packHash = computePackHash([testPolicy, testDenyPolicy] as any[]);
    expect(packHash).toHaveLength(64);
    expect(packHash).not.toBe(hash1);
  });

  it('should filter active policies', async () => {
    const { filterActive } = await import('@stix/shared');

    const policies = [
      { ...testPolicy, active: true },
      { ...testDenyPolicy, active: false },
    ] as any[];

    const active = filterActive(policies);
    expect(active).toHaveLength(1);
    expect(active[0].id).toBe('test-allow-read');
  });

  it('should sort policies by priority', async () => {
    const { sortByPriority } = await import('@stix/shared');

    const policies = [
      { ...testPolicy, priority: 100 },
      { ...testDenyPolicy, priority: 10 },
    ] as any[];

    const sorted = sortByPriority(policies);
    expect(sorted[0].priority).toBe(10);
    expect(sorted[1].priority).toBe(100);
  });
});

// =============================================================================
// EVIDENCE EXTRACTION TESTS
// =============================================================================

describe('Evidence Extraction', () => {
  beforeAll(() => {
    tempDir = createTempDir();
  });

  afterAll(() => {
    cleanupTempDir();
  });

  it('should load evidence bundle from JSON', async () => {
    const bundleFile = writeTempFile(
      'evidence.json',
      JSON.stringify(testEvidenceBundle)
    );

    // Dynamic import to test the extract module
    const { loadBundles } = await import('../tools/stix-replay/src/extract.js');
    const bundles = await loadBundles(bundleFile);

    expect(bundles).toHaveLength(1);
    expect(bundles[0].trace_id).toBe(testEvidenceBundle.trace_id);
  });

  it('should extract decision from bundle', async () => {
    const bundleFile = writeTempFile(
      'evidence2.json',
      JSON.stringify(testEvidenceBundle)
    );

    const { loadBundles, extractFromBundle } = await import(
      '../tools/stix-replay/src/extract.js'
    );

    const bundles = await loadBundles(bundleFile);
    const decision = extractFromBundle(bundles[0]);

    expect(decision.trace_id).toBe(testEvidenceBundle.trace_id);
    expect(decision.recorded.decision).toBe('ALLOW');
    expect(decision.actor.type).toBe('AI_AGENT');
  });

  it('should load JSONL bundles', async () => {
    const jsonlContent = [
      JSON.stringify(testEvidenceBundle),
      JSON.stringify({ ...testEvidenceBundle, trace_id: 'stix_second-trace-id' }),
    ].join('\n');

    const bundleFile = writeTempFile('evidence.jsonl', jsonlContent);

    const { loadBundles } = await import('../tools/stix-replay/src/extract.js');
    const bundles = await loadBundles(bundleFile);

    expect(bundles).toHaveLength(2);
  });

  it('should validate bundle for replay', async () => {
    const { validateForReplay } = await import(
      '../tools/stix-replay/src/extract.js'
    );

    const result = validateForReplay(testEvidenceBundle);

    expect(result.valid).toBe(true);
    expect(result.errors).toHaveLength(0);

    const invalidBundle = {
      ...testEvidenceBundle,
      events: testEvidenceBundle.events.map((event) => ({
        ...event,
        policy: { id: event.policy.id, version: event.policy.version },
      })),
    };
    const invalidResult = validateForReplay(invalidBundle);

    expect(invalidResult.valid).toBe(false);
    expect(invalidResult.errors).toContain('Missing policy_hash - cannot verify policy match');
  });
});

// =============================================================================
// SIMULATION TESTS
// =============================================================================

describe('Simulation Engine', () => {
  beforeAll(() => {
    tempDir = createTempDir();
  });

  afterAll(() => {
    cleanupTempDir();
  });

  it('should load evidence for simulation', async () => {
    const bundleFile = writeTempFile(
      'sim-evidence.json',
      JSON.stringify([testEvidenceBundle])
    );

    const { loadEvidenceBundles } = await import(
      '../tools/stix-simulate/src/loadEvidence.js'
    );

    const inputs = await loadEvidenceBundles(bundleFile);
    expect(inputs.length).toBeGreaterThanOrEqual(1);
  });

  it('should calculate diff statistics', async () => {
    const { getDiffStats } = await import('../tools/stix-simulate/src/diff.js');

    const results = [
      {
        trace_id: 'test-1',
        timestamp: '2025-01-27T12:00:00Z',
        recorded: { decision: 'ALLOW', reason_code: 'A' },
        simulated: { decision: 'ALLOW', reason_code: 'A' },
        delta: {
          decision_changed: false,
          obligations_changed: false,
          risk_level: 'LOW',
        },
      },
      {
        trace_id: 'test-2',
        timestamp: '2025-01-27T12:00:00Z',
        recorded: { decision: 'ALLOW', reason_code: 'A' },
        simulated: { decision: 'DENY', reason_code: 'B' },
        delta: {
          decision_changed: true,
          decision_change_type: 'ALLOW_TO_DENY',
          obligations_changed: false,
          risk_level: 'HIGH',
        },
      },
    ] as any[];

    const stats = getDiffStats(results);

    expect(stats.total).toBe(2);
    expect(stats.unchanged).toBe(1);
    expect(stats.decisionChanged).toBe(1);
    expect(stats.byChangeType['ALLOW_TO_DENY']).toBe(1);
  });
});

// =============================================================================
// REPLAY ENGINE TESTS
// =============================================================================

describe('Replay Engine', () => {
  beforeAll(() => {
    tempDir = createTempDir();
  });

  afterAll(() => {
    cleanupTempDir();
  });

  it('should replay a decision', async () => {
    // Create test policy pack
    const policyFile = writeTempFile(
      'replay-policies.json',
      JSON.stringify([testPolicy])
    );

    const { loadPolicyPack } = await import(
      '../tools/stix-replay/src/policyLoader.js'
    );
    const { ReplayEngine } = await import('../tools/stix-replay/src/engine.js');

    const pack = await loadPolicyPack(policyFile);
    const engine = new ReplayEngine(pack);

    const result = engine.evaluate({
      actor: { id: 'agent-1', type: 'AI_AGENT' },
      action: 'read_file',
      resource: { type: 'public_data' },
      context: { env: 'dev' },
    });

    expect(result.decision).toBe('ALLOW');
    expect(result.policy_id).toBe('test-allow-read');
  });

  it('should calculate replay statistics', async () => {
    const { calculateStats } = await import('../tools/stix-replay/src/replay.js');

    const results = [
      { status: 'MATCH', trace_id: 't1', recorded: { decision: 'ALLOW' } },
      { status: 'MATCH', trace_id: 't2', recorded: { decision: 'ALLOW' } },
      { status: 'DRIFT', trace_id: 't3', recorded: { decision: 'ALLOW' }, replayed: { decision: 'DENY' }, diff: { decision_changed: true } },
      { status: 'ERROR', trace_id: 't4', recorded: { decision: 'ALLOW' } },
    ] as any[];

    const stats = calculateStats(results);

    expect(stats.total).toBe(4);
    expect(stats.matches).toBe(2);
    expect(stats.drifts).toBe(1);
    expect(stats.errors).toBe(1);
    expect(stats.matchRate).toBe(50);
  });
});

// =============================================================================
// REPORT GENERATION TESTS
// =============================================================================

describe('Report Generation', () => {
  it('should format simulation report as JSON', async () => {
    const { formatReportAsJson } = await import(
      '../tools/stix-simulate/src/report.js'
    );

    const report = {
      metadata: { generated_at: '2025-01-27T12:00:00Z' },
      summary: { total_traces: 10, decision_changes_count: 2 },
      decision_changes: { allow_to_deny: 1, deny_to_allow: 1 },
      obligation_changes: { total_changed: 0, added: {}, removed: {} },
      risk_assessment: { overall_risk: 'MEDIUM', by_level: { critical: 0, high: 1 }, risk_factors: [] },
      high_risk_items: [],
    };

    const json = formatReportAsJson(report as any);
    expect(json).toContain('"total_traces": 10');
    expect(json).toContain('"decision_changes_count": 2');
  });

  it('should format replay report as markdown', async () => {
    const { formatReportAsMarkdown } = await import(
      '../tools/stix-replay/src/report.js'
    );

    const report = {
      metadata: {
        generated_at: '2025-01-27T12:00:00Z',
        bundle_source: 'test/bundles',
        policy_source: 'test/policies',
        strict_mode: false,
      },
      summary: { total: 10, matches: 8, drifts: 2, errors: 0, match_rate: 80 },
      results: [],
    };

    const markdown = formatReportAsMarkdown(report);
    expect(markdown).toContain('# STIX Replay Report');
    expect(markdown).toContain('| Total Traces | 10 |');
    expect(markdown).toContain('| Match Rate | 80.0% |');
  });

  it('should format simulation report as table', async () => {
    const { formatReportAsTable } = await import(
      '../tools/stix-simulate/src/report.js'
    );

    const report = {
      summary: { total_traces: 100, decision_changes_count: 5, unchanged: 95 },
      decision_changes: { allow_to_deny: 2, allow_to_quarantine: 3, deny_to_allow: 0 },
      risk_assessment: { overall_risk: 'MEDIUM' },
    };

    const table = formatReportAsTable(report as any);
    expect(table).toContain('STIX SIMULATION REPORT');
    expect(table).toContain('Total Traces');
    expect(table).toContain('100');
  });
});

// =============================================================================
// POLICY PACK STATISTICS TESTS
// =============================================================================

describe('Policy Pack Statistics', () => {
  it('should calculate pack statistics', async () => {
    const { getPackStats } = await import('@stix/shared');

    const pack = {
      id: 'test-pack',
      version: '1.0.0',
      hash: 'abc123',
      source: 'test',
      policies: [
        { ...testPolicy, priority: 100, obligations: [{ type: 'LOG_LEVEL' }] },
        { ...testDenyPolicy, priority: 10, approval: { approver_role: 'admin' } },
      ],
    } as any;

    const stats = getPackStats(pack);

    expect(stats.totalPolicies).toBe(2);
    expect(stats.byDecision['ALLOW']).toBe(1);
    expect(stats.byDecision['DENY']).toBe(1);
    expect(stats.byPriority.min).toBe(10);
    expect(stats.byPriority.max).toBe(100);
    expect(stats.hasObligations).toBe(1);
    expect(stats.hasApproval).toBe(1);
    expect(stats.regulations).toContain('TEST');
    expect(stats.controls).toContain('TEST:CTRL1');
  });
});
