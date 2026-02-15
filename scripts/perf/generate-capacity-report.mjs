import fs from 'node:fs';

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

const input = arg('input', 'artifacts/perf/load-result.json');
const output = arg('output', '_Development_Notes/STIX_Performance_Certification.md');

if (!fs.existsSync(input)) {
  throw new Error(`Input file not found: ${input}`);
}

const data = JSON.parse(fs.readFileSync(input, 'utf8'));

const md = `# STIX Performance Certification

Date: ${new Date().toISOString().slice(0, 10)}

## Test Profile

- Target: \`${data.target}\`
- Total requests: ${data.requests}
- Concurrency: ${data.concurrency}
- Duration: ${data.duration_ms} ms

## Results

- Throughput: ${data.throughput_rps} req/s
- Success: ${data.success}
- Failed: ${data.failed}
- Status counts: \`${JSON.stringify(data.status_counts)}\`

## Latency (ms)

- p50: ${data.latency_ms.p50}
- p95: ${data.latency_ms.p95}
- p99: ${data.latency_ms.p99}
- min: ${data.latency_ms.min}
- max: ${data.latency_ms.max}

## Capacity Envelope (Initial)

- Recommended baseline sustained rate: ${Math.floor(data.throughput_rps * 0.6)} req/s
- Recommended burst ceiling: ${Math.floor(data.throughput_rps * 0.85)} req/s
- Follow-up action: repeat test at 2x and 3x current concurrency to define saturation point.
`;

fs.writeFileSync(output, md, 'utf8');
console.log(`Wrote ${output}`);
