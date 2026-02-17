import fs from 'node:fs';
import path from 'node:path';

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

function toMonthLabel(monthValue) {
  if (/^\d{4}-\d{2}$/.test(monthValue)) return monthValue;
  throw new Error('--month must be in YYYY-MM format');
}

function readJsonIfExists(filePath) {
  if (!filePath) return null;
  if (!fs.existsSync(filePath)) return null;
  return JSON.parse(fs.readFileSync(filePath, 'utf8'));
}

const defaultMonth = new Date().toISOString().slice(0, 7);
const month = toMonthLabel(arg('month', defaultMonth));
const output = arg('output', `artifacts/ops/slo-signoff-${month}.md`);
const perfInput = arg('perf-input', '');
const replayInput = arg('replay-input', '');

const perf = readJsonIfExists(perfInput);
const replay = replayInput && fs.existsSync(replayInput)
  ? fs.readFileSync(replayInput, 'utf8')
  : '';

const generatedAt = new Date().toISOString();
const perfBaseline = perf?.profiles?.baseline;
const perfElevated = perf?.profiles?.elevated;

const perfSection = perf
  ? perfBaseline
    ? [
        '## Capacity Snapshot',
        '',
        '- Performance suite artifact attached.',
        `- Baseline: ${perfBaseline.requests} requests @ concurrency ${perfBaseline.concurrency}`,
        `- Baseline throughput (rps): ${perfBaseline.throughput_rps}`,
        `- Baseline p95 latency (ms): ${perfBaseline.latency_ms?.p95 ?? 'n/a'}`,
        `- Elevated throughput (rps): ${perfElevated?.throughput_rps ?? 'n/a'}`,
        `- Elevated p95 latency (ms): ${perfElevated?.latency_ms?.p95 ?? 'n/a'}`,
        `- Max verified concurrency: ${perf?.recommended?.max_verified_concurrency ?? 'n/a'}`,
        '',
      ].join('\n')
    : [
        '## Capacity Snapshot',
        '',
        `- Requests: ${perf.requests}`,
        `- Concurrency: ${perf.concurrency}`,
        `- Throughput (rps): ${perf.throughput_rps}`,
        `- Success: ${perf.success}`,
        `- Failed: ${perf.failed}`,
        `- p95 latency (ms): ${perf.latency_ms?.p95 ?? 'n/a'}`,
        `- p99 latency (ms): ${perf.latency_ms?.p99 ?? 'n/a'}`,
        '',
      ].join('\n')
  : [
      '## Capacity Snapshot',
      '',
      '- No performance artifact attached in this run.',
      '- Attach `artifacts/perf/load-result.json` for baseline certification.',
      '',
    ].join('\n');

const replaySection = replay
  ? [
      '## Replay/Verify Snapshot',
      '',
      '- Replay report artifact attached.',
      '- Paste investigation ticket IDs for any drift findings below.',
      '',
      'Tickets:',
      '- ',
      '',
    ].join('\n')
  : [
      '## Replay/Verify Snapshot',
      '',
      '- No replay report attached in this run.',
      '- Run `ops-cadence` replay job and attach report before sign-off.',
      '',
    ].join('\n');

const report = `# STIX Monthly SLO Sign-off - ${month}

Generated: ${generatedAt}

## SLO Summary

- Enforcer availability target: 99.95%
- Enforcer p95 latency target: <= 150ms
- Policy p95 latency target: <= 75ms
- Evidence write success target: 99.99%
- Approvals availability target: 99.90%

## Error Budget Review

- 6h burn-rate (>2x): PASS | FAIL | N/A
- 1h burn-rate (>4x): PASS | FAIL | N/A
- Incident rollbacks executed: YES | NO

${perfSection}${replaySection}## Compliance and Operations Attestation

- DR drill executed this month: YES | NO
- Key rotation verification executed this month: YES | NO
- mTLS posture validated in cluster: YES | NO
- Compliance checklist updated: YES | NO

## Sign-off

- Platform SRE Lead: ____________________ Date: __________
- Security Lead: ________________________ Date: __________
- Compliance Lead: ______________________ Date: __________
`;

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, report, 'utf8');
console.log(`Wrote ${output}`);
