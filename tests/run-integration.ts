#!/usr/bin/env tsx
/**
 * STIX Integration Test Runner
 *
 * Prerequisites:
 * - All STIX services must be running
 * - Services should be accessible at configured URLs
 *
 * Usage:
 *   pnpm test:integration          # Run all integration tests
 *   pnpm test:integration:watch    # Run in watch mode
 *
 * Environment Variables:
 *   STIX_ENFORCER_URL   - Enforcer service URL (default: http://localhost:3001)
 *   STIX_POLICY_URL     - Policy service URL (default: http://localhost:3002)
 *   STIX_EVIDENCE_URL   - Evidence service URL (default: http://localhost:3003)
 *   STIX_APPROVALS_URL  - Approvals service URL (default: http://localhost:3004)
 *   STIX_API_KEY        - API key for authentication (optional)
 *   STIX_TEST_TIMEOUT   - Test timeout in ms (default: 30000)
 */

import { spawn } from 'child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const services = [
  { name: 'Enforcer', url: process.env.STIX_ENFORCER_URL || 'http://localhost:3001' },
  { name: 'Policy', url: process.env.STIX_POLICY_URL || 'http://localhost:3002' },
  { name: 'Evidence', url: process.env.STIX_EVIDENCE_URL || 'http://localhost:3003' },
  { name: 'Approvals', url: process.env.STIX_APPROVALS_URL || 'http://localhost:3004' },
];

async function checkService(name: string, url: string): Promise<boolean> {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);

    const response = await fetch(`${url}/health`, { signal: controller.signal });
    clearTimeout(timeout);

    return response.ok;
  } catch {
    return false;
  }
}

async function checkAllServices(): Promise<boolean> {
  console.log('\n🔍 Checking service health...\n');

  let allHealthy = true;

  for (const service of services) {
    const isHealthy = await checkService(service.name, service.url);
    const status = isHealthy ? '✅' : '❌';
    console.log(`  ${status} ${service.name}: ${service.url}`);

    if (!isHealthy) {
      allHealthy = false;
    }
  }

  console.log();

  return allHealthy;
}

async function runTests(): Promise<void> {
  const args = process.argv.slice(2);
  const watch = args.includes('--watch') || args.includes('-w');
  const filter = args.find((arg) => !arg.startsWith('-'));

  const vitestArgs = [
    'vitest',
    'run',
    '--config',
    'vitest.integration.config.ts',
  ];

  if (watch) {
    vitestArgs[1] = 'watch';
  }

  if (filter) {
    vitestArgs.push('--testNamePattern', filter);
  }

  console.log('🧪 Running integration tests...\n');
  console.log(`   Command: npx ${vitestArgs.join(' ')}\n`);

  const child = spawn('npx', vitestArgs, {
    stdio: 'inherit',
    cwd: __dirname,
    shell: true,
  });

  child.on('exit', (code) => {
    process.exit(code || 0);
  });
}

async function main(): Promise<void> {
  console.log('═'.repeat(60));
  console.log('        STIX Integration Test Suite');
  console.log('═'.repeat(60));

  const skipHealthCheck = process.argv.includes('--skip-health');

  if (!skipHealthCheck) {
    const allHealthy = await checkAllServices();

    if (!allHealthy) {
      console.log('⚠️  Some services are not healthy.');
      console.log('   Make sure all STIX services are running before running integration tests.\n');
      console.log('   To start services:');
      console.log('     pnpm run dev     # Start all services in development mode\n');
      console.log('   To skip health check:');
      console.log('     pnpm test:integration -- --skip-health\n');

      const forceRun = process.argv.includes('--force');
      if (!forceRun) {
        console.log('   To force run anyway:');
        console.log('     pnpm test:integration -- --force\n');
        process.exit(1);
      }

      console.log('   Running anyway due to --force flag...\n');
    }
  }

  await runTests();
}

main().catch((error) => {
  console.error('Error running integration tests:', error);
  process.exit(1);
});
