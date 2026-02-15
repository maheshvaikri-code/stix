import fs from 'node:fs';
import path from 'node:path';

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

const baseUrl = arg('url', 'http://localhost:3001');
const apiKey = arg('api-key', '');
const totalRequests = Number.parseInt(arg('requests', '500'), 10);
const concurrency = Number.parseInt(arg('concurrency', '20'), 10);
const output = arg('output', 'artifacts/perf/load-result.json');

if (!Number.isFinite(totalRequests) || totalRequests <= 0) {
  throw new Error('--requests must be a positive integer');
}
if (!Number.isFinite(concurrency) || concurrency <= 0) {
  throw new Error('--concurrency must be a positive integer');
}

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
    if (id >= totalRequests) return;

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

function quantile(values, q) {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const index = Math.min(sorted.length - 1, Math.floor(q * sorted.length));
  return sorted[index];
}

const startedAt = new Date().toISOString();
const started = performance.now();
await Promise.all(Array.from({ length: concurrency }, () => worker()));
const durationMs = performance.now() - started;

const result = {
  started_at: startedAt,
  target: baseUrl,
  requests: totalRequests,
  concurrency,
  duration_ms: Math.round(durationMs),
  throughput_rps: Number((totalRequests / (durationMs / 1000)).toFixed(2)),
  success: ok,
  failed: fail,
  status_counts: Object.fromEntries(statusCounts.entries()),
  latency_ms: {
    min: Number((Math.min(...latencies, 0)).toFixed(2)),
    p50: Number(quantile(latencies, 0.5).toFixed(2)),
    p95: Number(quantile(latencies, 0.95).toFixed(2)),
    p99: Number(quantile(latencies, 0.99).toFixed(2)),
    max: Number((Math.max(...latencies, 0)).toFixed(2)),
  },
};

const outputDir = path.dirname(output);
fs.mkdirSync(outputDir, { recursive: true });
fs.writeFileSync(output, JSON.stringify(result, null, 2), 'utf8');
console.log(JSON.stringify(result, null, 2));
