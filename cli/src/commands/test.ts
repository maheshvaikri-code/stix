/**
 * STIX CLI - Test Commands
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import { request } from 'undici';

export const testCommand = new Command('test')
  .description('Run tests against STIX services');

// =============================================================================
// SMOKE TEST
// =============================================================================

testCommand
  .command('smoke')
  .description('Run smoke tests against STIX services')
  .requiredOption('--api-url <url>', 'STIX API URL')
  .option('--api-key <key>', 'API key')
  .option('--timeout <ms>', 'Request timeout', '10000')
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
    timeout: string;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const timeout = parseInt(options.timeout, 10);
    const enforcerUrl = normalizeServiceUrl(options.apiUrl);
    const policyUrl = normalizeServiceUrl(
      process.env.STIX_POLICY_URL ?? deriveSiblingServiceUrl(enforcerUrl, 3002)
    );
    const evidenceUrl = normalizeServiceUrl(
      process.env.STIX_EVIDENCE_URL ?? deriveSiblingServiceUrl(enforcerUrl, 3003)
    );

    console.log(chalk.cyan('\n=== STIX Smoke Tests ===\n'));
    console.log(`Target: ${enforcerUrl}\n`);

    let passed = 0;
    let failed = 0;

    // Test 1: Health check
    const healthResult = await runTest('Health Check', async () => {
      const response = await request(`${enforcerUrl}/health`, {
        method: 'GET',
        headersTimeout: timeout,
      });
      if (response.statusCode !== 200) {
        throw new Error(`Status ${response.statusCode}`);
      }
      const body = await response.body.json() as { status: string };
      if (body.status !== 'healthy') {
        throw new Error(`Status: ${body.status}`);
      }
      return `Status: ${body.status}`;
    });
    healthResult.passed ? passed++ : failed++;

    // Test 2: Policy list
    const policyResult = await runTest('List Policies', async () => {
      const response = await request(`${policyUrl}/api/v1/policies`, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
        headersTimeout: timeout,
      });
      if (response.statusCode !== 200) {
        throw new Error(`Status ${response.statusCode}`);
      }
      const body = await response.body.json() as { total: number };
      return `${body.total} policies loaded`;
    });
    policyResult.passed ? passed++ : failed++;

    // Test 3: Simple authorization request
    const authResult = await runTest('Authorization Request', async () => {
      const response = await request(`${enforcerUrl}/api/v1/authorize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
        },
        body: JSON.stringify({
          actor: { id: 'smoke-test', type: 'SERVICE' },
          action: 'smoke_test',
          resource: { type: 'test' },
          context: { env: 'test' },
        }),
        headersTimeout: timeout,
      });
      if (response.statusCode !== 200) {
        const body = await response.body.text();
        throw new Error(`Status ${response.statusCode}: ${body}`);
      }
      const body = await response.body.json() as { decision: string; trace_id: string };
      return `Decision: ${body.decision}, Trace: ${body.trace_id.substring(0, 8)}...`;
    });
    authResult.passed ? passed++ : failed++;

    // Test 4: Evidence endpoint
    const evidenceResult = await runTest('Evidence Endpoint', async () => {
      const response = await request(`${evidenceUrl}/api/v1/evidence?limit=1`, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
        headersTimeout: timeout,
      });
      // May return 200 or 404 depending on if evidence service is separate
      if (response.statusCode !== 200 && response.statusCode !== 404) {
        throw new Error(`Status ${response.statusCode}`);
      }
      return `Endpoint accessible`;
    });
    evidenceResult.passed ? passed++ : failed++;

    // Test 5: Metrics endpoint
    const metricsResult = await runTest('Metrics Endpoint', async () => {
      const response = await request(`${enforcerUrl}/metrics`, {
        method: 'GET',
        headersTimeout: timeout,
      });
      if (response.statusCode !== 200) {
        throw new Error(`Status ${response.statusCode}`);
      }
      const body = await response.body.text();
      if (!body.includes('stix_')) {
        throw new Error('No STIX metrics found');
      }
      return 'Metrics available';
    });
    metricsResult.passed ? passed++ : failed++;

    // Summary
    console.log(chalk.cyan('\n=== Summary ===\n'));
    if (failed === 0) {
      console.log(chalk.green(`All ${passed} smoke tests passed`));
    } else {
      console.log(chalk.red(`${failed} failed, ${passed} passed`));
      process.exit(1);
    }
  });

// =============================================================================
// INTEGRATION TEST
// =============================================================================

testCommand
  .command('integration')
  .description('Run integration tests')
  .requiredOption('--api-url <url>', 'STIX API URL')
  .option('--api-key <key>', 'API key')
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const enforcerUrl = normalizeServiceUrl(options.apiUrl);

    console.log(chalk.cyan('\n=== STIX Integration Tests ===\n'));

    let passed = 0;
    let failed = 0;

    // Test 1: Full authorization flow
    const flowResult = await runTest('Full Authorization Flow', async () => {
      // Request authorization
      const authResponse = await request(`${enforcerUrl}/api/v1/authorize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
        },
        body: JSON.stringify({
          actor: { id: 'integration-test', type: 'SERVICE', role: 'test-runner' },
          action: 'read_data',
          resource: { type: 'test_data', id: 'test-123' },
          context: { env: 'test', purpose: 'integration testing' },
        }),
      });

      const authBody = await authResponse.body.json() as {
        decision: string;
        trace_id: string;
        proof_token?: string;
      };

      if (!authBody.trace_id) {
        throw new Error('No trace_id returned');
      }

      // Record outcome
      const outcomeResponse = await request(`${enforcerUrl}/api/v1/outcome`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
        },
        body: JSON.stringify({
          trace_id: authBody.trace_id,
          status: 'SUCCESS',
          result_summary: 'Integration test completed',
        }),
      });

      if (outcomeResponse.statusCode !== 200 && outcomeResponse.statusCode !== 201) {
        throw new Error(`Outcome recording failed: ${outcomeResponse.statusCode}`);
      }

      return `Trace: ${authBody.trace_id.substring(0, 8)}..., Decision: ${authBody.decision}`;
    });
    flowResult.passed ? passed++ : failed++;

    // Test 2: Policy evaluation consistency
    const consistencyResult = await runTest('Policy Consistency', async () => {
      const requests = Array(5).fill(null).map(() =>
        request(`${enforcerUrl}/api/v1/authorize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
          },
          body: JSON.stringify({
            actor: { id: 'consistency-test', type: 'AI_AGENT' },
            action: 'send_email',
            resource: { type: 'email' },
            context: { env: 'test' },
          }),
        })
      );

      const responses = await Promise.all(requests);
      const bodies = await Promise.all(
        responses.map(r => r.body.json() as Promise<{ decision: string }>)
      );

      const decisions = bodies.map(b => b.decision);
      const unique = new Set(decisions);

      if (unique.size !== 1) {
        throw new Error(`Inconsistent decisions: ${decisions.join(', ')}`);
      }

      return `All 5 requests returned: ${decisions[0]}`;
    });
    consistencyResult.passed ? passed++ : failed++;

    // Test 3: Rate limiting
    const rateLimitResult = await runTest('Rate Limiting', async () => {
      // Send many requests quickly
      const requests = Array(20).fill(null).map(() =>
        request(`${enforcerUrl}/api/v1/authorize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
          },
          body: JSON.stringify({
            actor: { id: 'rate-limit-test', type: 'AI_AGENT' },
            action: 'test_rate_limit',
            resource: { type: 'test' },
            context: { env: 'test' },
          }),
        })
      );

      const responses = await Promise.all(requests);
      const statusCodes = responses.map(r => r.statusCode);

      // At least some should succeed
      const success = statusCodes.filter(c => c === 200).length;
      if (success === 0) {
        throw new Error('All requests failed');
      }

      // If rate limiting is configured, some might be rejected
      const limited = statusCodes.filter(c => c === 429).length;

      return `${success} succeeded, ${limited} rate limited`;
    });
    rateLimitResult.passed ? passed++ : failed++;

    // Test 4: Error handling
    const errorResult = await runTest('Error Handling', async () => {
      // Send malformed request
      const response = await request(`${enforcerUrl}/api/v1/authorize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
        },
        body: JSON.stringify({
          // Missing required fields
          actor: { id: 'error-test' },
        }),
      });

      if (response.statusCode !== 400) {
        throw new Error(`Expected 400, got ${response.statusCode}`);
      }

      const body = await response.body.json() as { error: string };
      if (!body.error) {
        throw new Error('No error message in response');
      }

      return 'Properly returns 400 for invalid requests';
    });
    errorResult.passed ? passed++ : failed++;

    // Summary
    console.log(chalk.cyan('\n=== Summary ===\n'));
    if (failed === 0) {
      console.log(chalk.green(`All ${passed} integration tests passed`));
    } else {
      console.log(chalk.red(`${failed} failed, ${passed} passed`));
      process.exit(1);
    }
  });

// =============================================================================
// LOAD TEST
// =============================================================================

testCommand
  .command('load')
  .description('Run load tests')
  .requiredOption('--api-url <url>', 'STIX API URL')
  .option('--api-key <key>', 'API key')
  .option('--requests <n>', 'Total requests to send', '1000')
  .option('--concurrency <n>', 'Concurrent requests', '10')
  .option('--duration <seconds>', 'Test duration in seconds', '30')
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
    requests: string;
    concurrency: string;
    duration: string;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const enforcerUrl = normalizeServiceUrl(options.apiUrl);
    const totalRequests = parseInt(options.requests, 10);
    const concurrency = parseInt(options.concurrency, 10);
    const duration = parseInt(options.duration, 10) * 1000;

    console.log(chalk.cyan('\n=== STIX Load Test ===\n'));
    console.log(`Target: ${enforcerUrl}`);
    console.log(`Requests: ${totalRequests}`);
    console.log(`Concurrency: ${concurrency}`);
    console.log(`Duration: ${options.duration}s\n`);

    const spinner = ora('Running load test...').start();

    const startTime = Date.now();
    const latencies: number[] = [];
    let completed = 0;
    let errors = 0;
    let success = 0;

    const sendRequest = async (): Promise<void> => {
      const reqStart = Date.now();
      try {
        const response = await request(`${enforcerUrl}/api/v1/authorize`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {}),
          },
          body: JSON.stringify({
            actor: { id: `load-test-${completed}`, type: 'SERVICE' },
            action: 'load_test',
            resource: { type: 'test' },
            context: { env: 'test' },
          }),
        });

        const latency = Date.now() - reqStart;
        latencies.push(latency);

        if (response.statusCode === 200) {
          success++;
        } else {
          errors++;
        }
        await response.body.text(); // Consume body
      } catch {
        errors++;
      }
      completed++;
    };

    // Run concurrent requests
    const running: Promise<void>[] = [];

    while (completed < totalRequests && Date.now() - startTime < duration) {
      while (running.length < concurrency && completed + running.length < totalRequests) {
        const p = sendRequest().then(() => {
          running.splice(running.indexOf(p), 1);
        });
        running.push(p);
      }
      await Promise.race(running);
      spinner.text = `Running: ${completed}/${totalRequests} (${errors} errors)`;
    }

    await Promise.all(running);

    spinner.stop();

    // Calculate statistics
    const elapsed = (Date.now() - startTime) / 1000;
    const rps = completed / elapsed;

    latencies.sort((a, b) => a - b);
    const p50 = latencies[Math.floor(latencies.length * 0.5)];
    const p95 = latencies[Math.floor(latencies.length * 0.95)];
    const p99 = latencies[Math.floor(latencies.length * 0.99)];
    const avg = latencies.reduce((a, b) => a + b, 0) / latencies.length;

    console.log(chalk.cyan('=== Results ===\n'));
    console.log(`Completed: ${completed} requests`);
    console.log(`Success: ${success}`);
    console.log(`Errors: ${errors}`);
    console.log(`Duration: ${elapsed.toFixed(2)}s`);
    console.log(`Throughput: ${rps.toFixed(2)} req/s`);
    console.log();
    console.log(chalk.cyan('Latency:'));
    console.log(`  Avg: ${avg.toFixed(2)}ms`);
    console.log(`  P50: ${p50}ms`);
    console.log(`  P95: ${p95}ms`);
    console.log(`  P99: ${p99}ms`);

    if (errors > completed * 0.01) {
      console.log(chalk.red('\nWarning: Error rate > 1%'));
      process.exit(1);
    }
  });

// =============================================================================
// HELPERS
// =============================================================================

interface TestResult {
  name: string;
  passed: boolean;
  message?: string;
  error?: string;
}

function normalizeServiceUrl(url: string): string {
  return url.replace(/\/$/, '');
}

function deriveSiblingServiceUrl(baseUrl: string, port: number): string {
  try {
    const parsed = new URL(baseUrl);
    if (parsed.port) {
      parsed.port = String(port);
    }
    return normalizeServiceUrl(parsed.toString());
  } catch {
    return normalizeServiceUrl(baseUrl.replace(/:3001(?=\/|$)/, `:${port}`));
  }
}

async function runTest(
  name: string,
  fn: () => Promise<string>
): Promise<TestResult> {
  const spinner = ora(name).start();

  try {
    const message = await fn();
    spinner.succeed(`${name}: ${chalk.gray(message)}`);
    return { name, passed: true, message };
  } catch (error) {
    const errorMessage = (error as Error).message;
    spinner.fail(`${name}: ${chalk.red(errorMessage)}`);
    return { name, passed: false, error: errorMessage };
  }
}
