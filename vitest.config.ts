import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    globals: true,
    environment: 'node',
    include: ['tests/**/*.test.ts', 'packages/**/src/**/*.test.ts'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules', 'dist', 'tests'],
    },
    testTimeout: 10000,
  },
  resolve: {
    alias: {
      '@stix/shared': './packages/shared/src/index.ts',
      '@stix/enforcer': './services/enforcer/src/index.ts',
      '@stix/policy': './services/policy/src/index.ts',
      '@stix/evidence': './services/evidence/src/index.ts',
      '@stix/approvals': './services/approvals/src/index.ts',
      '@stix/agent-sdk': './sdk/agent-sdk/src/index.ts',
      '@stix/target-verifier': './sdk/target-verifier/src/index.ts',
    },
  },
});
