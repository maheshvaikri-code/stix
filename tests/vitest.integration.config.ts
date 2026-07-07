import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    name: 'integration',
    include: ['integration/**/*.test.ts'],
    testTimeout: 30000,
    hookTimeout: 30000,
    sequence: {
      shuffle: false,
    },
    reporters: ['verbose'],
    coverage: {
      enabled: false,
    },
    // Environment variables for tests
    env: {
      STIX_ENFORCER_URL: process.env.STIX_ENFORCER_URL ?? 'http://localhost:3001',
      STIX_POLICY_URL: process.env.STIX_POLICY_URL ?? 'http://localhost:3002',
      STIX_EVIDENCE_URL: process.env.STIX_EVIDENCE_URL ?? 'http://localhost:3003',
      STIX_APPROVALS_URL: process.env.STIX_APPROVALS_URL ?? 'http://localhost:3004',
    },
  },
});
