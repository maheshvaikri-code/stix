import { defineConfig } from 'vitest/config';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = path.dirname(fileURLToPath(import.meta.url));
const fromRoot = (relativePath: string) => path.resolve(rootDir, relativePath);

export default defineConfig({
  test: {
    name: 'unit',
    globals: true,
    environment: 'node',
    include: ['tests/*.test.ts', 'packages/**/src/**/*.test.ts'],
    exclude: ['tests/integration/**', '**/node_modules/**', '**/dist/**'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: ['node_modules', 'dist', 'tests'],
    },
    testTimeout: 10000,
  },
  resolve: {
    alias: {
      '@stix/shared': fromRoot('packages/shared/src/index.ts'),
      '@stix/enforcer': fromRoot('services/enforcer/src/index.ts'),
      '@stix/policy': fromRoot('services/policy/src/index.ts'),
      '@stix/evidence': fromRoot('services/evidence/src/index.ts'),
      '@stix/approvals': fromRoot('services/approvals/src/index.ts'),
      '@stix/fabric': fromRoot('services/fabric/src/index.ts'),
      '@stix/agent-sdk': fromRoot('packages/agent-sdk/src/index.ts'),
      '@stix/fabric-types': fromRoot('packages/fabric-types/src/index.ts'),
      '@stix/target-verifier': fromRoot('packages/target-verifier/src/index.ts'),
    },
  },
});
