import fs from 'node:fs';
import path from 'node:path';

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

function defaultQuarter() {
  const now = new Date();
  const year = now.getUTCFullYear();
  const month = now.getUTCMonth() + 1;
  const quarter = Math.ceil(month / 3);
  return `${year}-Q${quarter}`;
}

function validateQuarter(value) {
  if (!/^\d{4}-Q[1-4]$/.test(value)) {
    throw new Error('--quarter must be in YYYY-QN format (example: 2026-Q1)');
  }
  return value;
}

function exists(filePath) {
  return filePath ? fs.existsSync(filePath) : false;
}

function statusFor(filePath) {
  return exists(filePath) ? 'complete' : 'pending';
}

const quarter = validateQuarter(arg('quarter', defaultQuarter()));
const output = arg(
  'output',
  `_Development_Notes/operations/${quarter}/STIX_Quarterly_Attestation_${quarter}.md`
);
const monthlyPacket = arg('monthly-packet', '');
const drReport = arg('dr-report', '');
const keyRotationReport = arg('key-rotation-report', '');
const replayReport = arg('replay-report', '');
const performanceReport = arg('performance-report', '');
const generatedAt = new Date().toISOString();

const content = `# STIX Quarterly Compliance Attestation - ${quarter}

Generated: ${generatedAt}

## Evidence Checklist

| Control Area | Check | Evidence | Status |
|---|---|---|---|
| Authorization enforcement | All protected targets reject missing/invalid proof tokens | Integration test logs | ${statusFor(replayReport)} |
| Evidence integrity | Chain verification passes for sample and production traces | \`stix-verify\` outputs | ${statusFor(replayReport)} |
| Key lifecycle | Rotation drill completed with old/new key verification continuity | Key rotation drill report | ${statusFor(keyRotationReport)} |
| Transport security | mTLS policy enforced and validated in cluster | \`deploy/k8s/stix-mtls.yaml\` + cluster query output | complete |
| Durable storage | Restart/recovery drill shows no state loss | DR run logs + recovery metrics | ${statusFor(drReport)} |
| Replay determinism | Strict replay samples return \`MATCH\` or investigated drift | Replay report set | ${statusFor(replayReport)} |

## Required Attachments

- Monthly SLO sign-off packets for quarter: ${monthlyPacket || '<fill>'}
- DR drill report and restore logs: ${drReport || '<fill>'}
- Key rotation verification report: ${keyRotationReport || '<fill>'}
- Replay cadence reports and drift investigations (if any): ${replayReport || '<fill>'}
- Performance certification report: ${performanceReport || '<fill>'}

## Risk and Exceptions

- Open exceptions:
  - None | <fill>
- Deferred controls:
  - None | <fill>

## Sign-off

- Compliance Lead: ____________________ Date: __________
- Security Lead: ______________________ Date: __________
- Platform Lead: ______________________ Date: __________
`;

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, content, 'utf8');
console.log(`Wrote ${output}`);
