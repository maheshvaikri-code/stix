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

function renderSingleProfileReport(single) {
  return `## Test Profile

- Target: \`${single.target}\`
- Total requests: ${single.requests}
- Concurrency: ${single.concurrency}
- Duration: ${single.duration_ms} ms

## Results

- Throughput: ${single.throughput_rps} req/s
- Success: ${single.success}
- Failed: ${single.failed}
- Status counts: \`${JSON.stringify(single.status_counts)}\`

## Latency (ms)

- p50: ${single.latency_ms.p50}
- p95: ${single.latency_ms.p95}
- p99: ${single.latency_ms.p99}
- min: ${single.latency_ms.min}
- max: ${single.latency_ms.max}

## Capacity Envelope (Initial)

- Recommended baseline sustained rate: ${Math.floor(single.throughput_rps * 0.6)} req/s
- Recommended burst ceiling: ${Math.floor(single.throughput_rps * 0.85)} req/s
- Follow-up action: repeat test at 2x and 3x current concurrency to define saturation point.`;
}

function renderSuiteReport(suite) {
  const baseline = suite.profiles?.baseline;
  const elevated = suite.profiles?.elevated;
  const saturationRuns = suite.saturation?.runs ?? [];
  const breach = suite.saturation?.breach_point;
  const best = suite.saturation?.best_within_target;

  return `## Profile Suite Summary

- Target: \`${suite.target ?? baseline?.target ?? 'n/a'}\`
- Generated at: ${suite.generated_at ?? new Date().toISOString()}

## Profiles

| Profile | Requests | Concurrency | Throughput (rps) | p95 (ms) | Failure Rate |
|---|---:|---:|---:|---:|---:|
| Baseline | ${baseline?.requests ?? 'n/a'} | ${baseline?.concurrency ?? 'n/a'} | ${baseline?.throughput_rps ?? 'n/a'} | ${baseline?.latency_ms?.p95 ?? 'n/a'} | ${baseline?.fail_rate ?? 'n/a'} |
| Elevated | ${elevated?.requests ?? 'n/a'} | ${elevated?.concurrency ?? 'n/a'} | ${elevated?.throughput_rps ?? 'n/a'} | ${elevated?.latency_ms?.p95 ?? 'n/a'} | ${elevated?.fail_rate ?? 'n/a'} |
${saturationRuns
  .map(
    (run) =>
      `| ${run.profile} | ${run.requests} | ${run.concurrency} | ${run.throughput_rps} | ${run.latency_ms?.p95 ?? 'n/a'} | ${run.fail_rate ?? 'n/a'} |`
  )
  .join('\n')}

## Saturation Findings

- Breach point: ${
    breach
      ? `concurrency ${breach.concurrency} (${breach.reason})`
      : 'No breach detected in configured probe range'
  }
- Max verified concurrency within target: ${best?.concurrency ?? elevated?.concurrency ?? 'n/a'}

## Capacity Envelope (Certified)

- Recommended sustained rate: ${suite.recommended?.sustained_rps ?? 'n/a'} req/s
- Recommended burst ceiling: ${suite.recommended?.burst_rps ?? 'n/a'} req/s
- Max verified concurrency: ${suite.recommended?.max_verified_concurrency ?? 'n/a'}
`;
}

const title = `# STIX Performance Certification

Date: ${new Date().toISOString().slice(0, 10)}
`;

const md =
  data && data.profiles && data.saturation
    ? `${title}\n${renderSuiteReport(data)}`
    : `${title}\n${renderSingleProfileReport(data)}`;

fs.writeFileSync(output, md, 'utf8');
console.log(`Wrote ${output}`);
