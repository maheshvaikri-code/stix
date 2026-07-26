import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { InMemoryPolicyStore } from '../services/policy/src/store/index.js';

const tempDirs: string[] = [];

const logger = {
  child: () => logger,
  debug: vi.fn(),
  info: vi.fn(),
  warn: vi.fn(),
  error: vi.fn(),
};

describe('InMemoryPolicyStore policy pack loading', () => {
  afterEach(() => {
    while (tempDirs.length > 0) {
      const dir = tempDirs.pop();
      if (dir) rmSync(dir, { recursive: true, force: true });
    }
    vi.clearAllMocks();
  });

  it('loads every policy from a multi-document YAML pack', async () => {
    const dir = mkdtempSync(path.join(tmpdir(), 'stix-policy-pack-'));
    tempDirs.push(dir);

    writeFileSync(
      path.join(dir, 'pack.yaml'),
      `policy_id: first-policy
version: "1.0.0"
priority: 10
scope:
  actor_type: AI_AGENT
  action: read_*
  resource_type: patient_data
decision: DENY
reason_code: FIRST_POLICY
---
policy_id: second-policy
version: "1.0.0"
priority: 20
scope:
  actor_type: SERVICE
  action: process_payment
  resource_type: payment_token
decision: ALLOW
reason_code: SECOND_POLICY
`,
    );

    const store = new InMemoryPolicyStore(logger as never, dir);
    await store.initialize();

    const policies = await store.listPolicies({ limit: 10 });
    expect(policies.map((policy) => policy.policy_id)).toEqual([
      'first-policy',
      'second-policy',
    ]);
  });
});
