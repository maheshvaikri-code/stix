import fs from 'node:fs';
import path from 'node:path';

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

function intArg(name, fallback) {
  const value = Number.parseInt(arg(name, String(fallback)), 10);
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(`--${name} must be a positive integer`);
  }
  return value;
}

function floatArg(name, fallback) {
  const value = Number.parseFloat(arg(name, String(fallback)));
  if (!Number.isFinite(value) || value <= 0) {
    throw new Error(`--${name} must be a positive number`);
  }
  return value;
}

function quantile(values, q) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor(q * sorted.length));
  return sorted[index];
}

async function runLoadProfile({
  name,
  baseUrl,
  apiKey,
  requests,
  concurrency,
}) {
  const authBody = {
    actor: { id: 'perf-agent', type: 'AI_AGENT' },
    action: 'READ',
    resource: { type: 'DOCUMENT', id: 'perf-target' },
    context: { env: 'stage', purpose: 'perf-test' },
  };

  const headers = { 'Content-Type': 'application/json' };
  if (apiKey) {
    headers['x-stix-api-key'] = apiKey;
  }

  let nextId = 0;
  let ok = 0;
  let fail = 0;
  const latencies = [];
  const statusCounts = new Map();

  async function worker() {
    while (true) {
      const id = nextId++;
      if (id >= requests) return;

      const started = performance.now();
      try {
        const res = await fetch(`${baseUrl}/api/v1/authorize`, {
          method: 'POST',
          headers,
          body: JSON.stringify(authBody),
        });

        const elapsedMs = performance.now() - started;
        latencies.push(elapsedMs);
        statusCounts.set(String(res.status), (statusCounts.get(String(res.status)) ?? 0) + 1);

        if (res.ok) {
          ok++;
        } else {
          fail++;
        }

        await res.arrayBuffer().catch(() => undefined);
      } catch {
        const elapsedMs = performance.now() - started;
        latencies.push(elapsedMs);
        fail++;
        statusCounts.set('FETCH_ERROR', (statusCounts.get('FETCH_ERROR') ?? 0) + 1);
      }
    }
  }

  const startedAt = new Date().toISOString();
  const started = performance.now();
  await Promise.all(Array.from({ length: concurrency }, () => worker()));
  const durationMs = performance.now() - started;
  const failRate = requests > 0 ? fail / requests : 1;

  return {
    profile: name,
    started_at: startedAt,
    target: baseUrl,
    requests,
    concurrency,
    duration_ms: Math.round(durationMs),
    throughput_rps: Number((requests / (durationMs / 1000)).toFixed(2)),
    success: ok,
    failed: fail,
    fail_rate: Number(failRate.toFixed(4)),
    status_counts: Object.fromEntries(statusCounts.entries()),
    latency_ms: {
      min: Number(Math.min(...latencies, 0).toFixed(2)),
      p50: Number(quantile(latencies, 0.5).toFixed(2)),
      p95: Number(quantile(latencies, 0.95).toFixed(2)),
      p99: Number(quantile(latencies, 0.99).toFixed(2)),
      max: Number(Math.max(...latencies, 0).toFixed(2)),
    },
  };
}

const baseUrl = arg('url', 'http://localhost:3001');
const apiKey = arg('api-key', '');
const outputDir = arg('output-dir', 'artifacts/perf');

const baselineRequests = intArg('baseline-requests', 2000);
const baselineConcurrency = intArg('baseline-concurrency', 50);
const elevatedRequests = intArg('elevated-requests', 5000);
const elevatedConcurrency = intArg('elevated-concurrency', 100);
const saturationRequests = intArg('saturation-requests', 4000);
const saturationStartConcurrency = intArg('saturation-start-concurrency', elevatedConcurrency + 50);
const saturationMaxConcurrency = intArg('saturation-max-concurrency', elevatedConcurrency + 200);
const saturationStep = intArg('saturation-step', 50);

const p95TargetMs = floatArg('p95-target-ms', 150);
const failRateTarget = floatArg('fail-rate-target', 0.01);

fs.mkdirSync(outputDir, { recursive: true });

console.log('Running baseline profile...');
const baseline = await runLoadProfile({
  name: 'baseline',
  baseUrl,
  apiKey,
  requests: baselineRequests,
  concurrency: baselineConcurrency,
});
fs.writeFileSync(path.join(outputDir, 'baseline.json'), JSON.stringify(baseline, null, 2), 'utf8');

console.log('Running elevated profile...');
const elevated = await runLoadProfile({
  name: 'elevated',
  baseUrl,
  apiKey,
  requests: elevatedRequests,
  concurrency: elevatedConcurrency,
});
fs.writeFileSync(path.join(outputDir, 'elevated.json'), JSON.stringify(elevated, null, 2), 'utf8');

const saturationRuns = [];
let breachPoint = null;
for (
  let concurrency = saturationStartConcurrency;
  concurrency <= saturationMaxConcurrency;
  concurrency += saturationStep
) {
  console.log(`Running saturation probe at concurrency=${concurrency}...`);
  const run = await runLoadProfile({
    name: `saturation-${concurrency}`,
    baseUrl,
    apiKey,
    requests: saturationRequests,
    concurrency,
  });
  saturationRuns.push(run);
  fs.writeFileSync(
    path.join(outputDir, `saturation-${concurrency}.json`),
    JSON.stringify(run, null, 2),
    'utf8'
  );

  if (run.latency_ms.p95 > p95TargetMs || run.fail_rate > failRateTarget) {
    breachPoint = {
      concurrency,
      reason:
        run.latency_ms.p95 > p95TargetMs
          ? `p95 ${run.latency_ms.p95}ms exceeded ${p95TargetMs}ms`
          : `fail rate ${run.fail_rate} exceeded ${failRateTarget}`,
      run,
    };
    break;
  }
}

const saturationBest = [...saturationRuns]
  .reverse()
  .find((run) => run.latency_ms.p95 <= p95TargetMs && run.fail_rate <= failRateTarget) ?? null;

const generatedAt = new Date().toISOString();
const summary = {
  generated_at: generatedAt,
  target: baseUrl,
  profiles: {
    baseline,
    elevated,
  },
  saturation: {
    runs: saturationRuns,
    breach_point: breachPoint,
    best_within_target: saturationBest,
    p95_target_ms: p95TargetMs,
    fail_rate_target: failRateTarget,
  },
  recommended: {
    sustained_rps: Math.floor(Math.max(0, baseline.throughput_rps * 0.6)),
    burst_rps: Math.floor(Math.max(0, elevated.throughput_rps * 0.85)),
    max_verified_concurrency: saturationBest?.concurrency ?? elevated.concurrency,
  },
};

const suiteOutput = path.join(outputDir, 'profile-suite.json');
fs.writeFileSync(suiteOutput, JSON.stringify(summary, null, 2), 'utf8');

console.log(`Wrote ${suiteOutput}`);
console.log(JSON.stringify(summary, null, 2));
