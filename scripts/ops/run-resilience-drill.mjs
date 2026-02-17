import fs from 'node:fs';
import path from 'node:path';
import { execSync } from 'node:child_process';

function arg(name, fallback) {
  const idx = process.argv.indexOf(`--${name}`);
  if (idx === -1) return fallback;
  return process.argv[idx + 1] ?? fallback;
}

function intArg(name, fallback) {
  const value = Number.parseInt(arg(name, String(fallback)), 10);
  if (!Number.isFinite(value) || value < 0) {
    throw new Error(`--${name} must be an integer >= 0`);
  }
  return value;
}

function boolArg(name, fallback) {
  const value = arg(name, fallback ? 'true' : 'false');
  return value === 'true';
}

function isoNow() {
  return new Date().toISOString();
}

function toShortSha(value) {
  if (!value) return 'local';
  return value.slice(0, 8);
}

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function checkHealth(url, requestTimeoutMs = 3000) {
  try {
    const timeoutSignal =
      typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function'
        ? AbortSignal.timeout(requestTimeoutMs)
        : undefined;

    const res = await fetch(url, {
      method: 'GET',
      signal: timeoutSignal,
    });
    return res.ok;
  } catch {
    return false;
  }
}

async function waitForHealthy(url, timeoutMs, pollMs, requestTimeoutMs = 3000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    if (await checkHealth(url, requestTimeoutMs)) return true;
    await sleep(pollMs);
  }
  return false;
}

function runCommand(command, strict = true) {
  try {
    const output = execSync(command, { encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] });
    return { ok: true, output: output.trim() };
  } catch (error) {
    const stderr = error?.stderr ? String(error.stderr) : '';
    const stdout = error?.stdout ? String(error.stdout) : '';
    const message = `${stdout}\n${stderr}`.trim() || String(error);
    if (strict) {
      throw new Error(`Command failed: ${command}\n${message}`);
    }
    return { ok: false, output: message };
  }
}

const dateStamp = new Date().toISOString().slice(0, 10);
const drillId = arg('drill-id', `STIX-DR-${dateStamp.replace(/-/g, '')}`);
const output = arg('output', 'artifacts/ops/resilience-drill-report.md');
const outageSeconds = intArg('outage-seconds', 15);
const preflightTimeoutSeconds = intArg('preflight-timeout-seconds', 120);
const preflightRequestTimeoutMs = intArg('preflight-request-timeout-ms', 3000);
const requireAllPreflight = boolArg('require-all-preflight', true);
const rtoTargetMin = intArg('rto-target-min', 60);
const rpoTargetMin = intArg('rpo-target-min', 15);
const observedRpoMin = intArg('observed-rpo-min', 0);

const enforcerUrl = arg('enforcer-url', 'http://localhost:3001');
const policyUrl = arg('policy-url', 'http://localhost:3002');
const evidenceUrl = arg('evidence-url', 'http://localhost:3003');
const approvalsUrl = arg('approvals-url', 'http://localhost:3004');
const evidenceContainer = arg('evidence-container', 'stix-evidence');
const runReplay = boolArg('run-replay', true);
const runComposeBootstrap = boolArg('bootstrap-compose', false);

const environmentLabel = arg('environment', 'local-compose');
const policyPackHash = arg('policy-pack-hash', 'n/a');
const oldKeyId = arg('old-key-id', 'key-prev');
const newKeyId = arg('new-key-id', 'key-current');
const buildTag = arg('build-tag', toShortSha(process.env.GITHUB_SHA ?? 'local'));

const timeline = [];
const notes = [];
let replayResult = { ok: false, output: 'not run' };
let outageAuthorizeStatus = 'n/a';
let outageAuthorizeBody = '';

const outageStart = new Date();
let restoreHealthyAt = new Date();

function pushStep(step, result) {
  timeline.push({
    time: isoNow(),
    step,
    result,
  });
}

pushStep('Start drill', 'started');

if (runComposeBootstrap) {
  pushStep('Bootstrap compose stack', 'running');
  runCommand('pnpm docker:up');
  pushStep('Bootstrap compose stack', 'complete');
}

const healthChecks = [
  { name: 'enforcer', url: `${enforcerUrl}/health` },
  { name: 'policy', url: `${policyUrl}/health` },
  { name: 'evidence', url: `${evidenceUrl}/health` },
  { name: 'approvals', url: `${approvalsUrl}/health` },
];

pushStep(
  'Wait for service health',
  `up to ${preflightTimeoutSeconds}s for all health endpoints`
);

const preflightChecks = await Promise.all(
  healthChecks.map((service) =>
    waitForHealthy(
      service.url,
      preflightTimeoutSeconds * 1000,
      2000,
      preflightRequestTimeoutMs
    )
  )
);

const failedServices = healthChecks
  .filter((_, index) => !preflightChecks[index])
  .map((service) => service.name);
const enforcerHealthy = preflightChecks[0] === true;

if (!enforcerHealthy) {
  throw new Error(
    'Preflight health check failed for enforcer. Cannot run resilience drill.'
  );
}

if (requireAllPreflight && failedServices.length > 0) {
  throw new Error(
    `Preflight health checks failed for: ${failedServices.join(', ')}. Ensure all services are running before executing resilience drill.`
  );
}
if (failedServices.length === 0) {
  pushStep('Preflight health checks', 'all services healthy');
} else {
  pushStep(
    'Preflight health checks',
    `enforcer healthy; proceeding with degraded peers: ${failedServices.join(', ')}`
  );
  notes.push(
    `Preflight degraded peers: ${failedServices.join(', ')} (drill continued because require-all-preflight=false).`
  );
}

pushStep('Rotate signing key references', `simulated cutover ${oldKeyId} -> ${newKeyId}`);

pushStep('Simulate evidence outage', `stopping container ${evidenceContainer}`);
outageStart.setTime(Date.now());
runCommand(`docker stop ${evidenceContainer}`);

const authBody = {
  actor: { id: 'drill-agent', type: 'AI_AGENT' },
  action: 'READ',
  resource: { type: 'DOCUMENT', id: 'drill-target' },
  context: { env: 'stage', purpose: 'resilience-drill' },
};

try {
  const response = await fetch(`${enforcerUrl}/api/v1/authorize`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(authBody),
  });
  outageAuthorizeStatus = String(response.status);
  outageAuthorizeBody = (await response.text()).slice(0, 500);
} catch (error) {
  outageAuthorizeStatus = 'FETCH_ERROR';
  outageAuthorizeBody = String(error);
}

await sleep(outageSeconds * 1000);

pushStep('Restore evidence service', `starting container ${evidenceContainer}`);
runCommand(`docker start ${evidenceContainer}`);

const evidenceRecovered = await waitForHealthy(`${evidenceUrl}/health`, 120000, 2000);
if (!evidenceRecovered) {
  pushStep('Restore evidence service', 'failed to become healthy in timeout');
  throw new Error('Evidence service did not recover within timeout window.');
}
restoreHealthyAt = new Date();
pushStep('Restore evidence service', 'healthy');

const drVerification = await Promise.all([
  checkHealth(`${enforcerUrl}/health`),
  checkHealth(`${policyUrl}/health`),
  checkHealth(`${evidenceUrl}/health`),
  checkHealth(`${approvalsUrl}/health`),
]);
pushStep(
  'Service restart/recovery verification',
  drVerification.every(Boolean) ? 'healthy' : 'failed'
);

if (runReplay) {
  pushStep('Run strict replay verification samples', 'running');
  replayResult = runCommand('pnpm ops:replay-smoke', false);
  pushStep(
    'Run strict replay verification samples',
    replayResult.ok ? 'complete' : 'failed'
  );
}

pushStep('End drill', 'completed');

const observedRtoMin = Number(((restoreHealthyAt.getTime() - outageStart.getTime()) / 60000).toFixed(2));
const withinTarget = observedRtoMin <= rtoTargetMin && observedRpoMin <= rpoTargetMin;

if (!withinTarget) {
  notes.push('Observed RTO/RPO exceeded target. Review and corrective action required.');
}
if (!replayResult.ok) {
  notes.push('Replay verification failed during drill execution.');
}
if (!drVerification.every(Boolean)) {
  notes.push('One or more services were unhealthy after recovery check.');
}

const report = `# STIX Resilience Drill Report

Date: ${dateStamp}
Drill ID: ${drillId}

## Drill Scope

- Key rotation cutover
- Evidence service outage simulation
- Service restart and recovery
- Strict replay verification on sampled traces

## Environment

- Cluster/region: ${environmentLabel}
- Build/tag: ${buildTag}
- Policy pack hash: ${policyPackHash}
- Signing key IDs involved: ${oldKeyId} -> ${newKeyId}

## Timeline

| Time (UTC) | Step | Result |
|---|---|---|
${timeline.map((entry) => `| ${entry.time} | ${entry.step} | ${entry.result} |`).join('\n')}

## RTO/RPO Outcomes

- RTO target: ${rtoTargetMin} minutes
- RPO target: ${rpoTargetMin} minutes
- Observed RTO: ${observedRtoMin} minutes
- Observed RPO: ${observedRpoMin} minutes
- Within target: ${withinTarget ? 'YES' : 'NO'}

## Validation Evidence

- Health and readiness checks:
  - ${enforcerUrl}/health, ${policyUrl}/health, ${evidenceUrl}/health, ${approvalsUrl}/health
- Evidence outage authorization probe:
  - status: ${outageAuthorizeStatus}
  - response snippet: ${outageAuthorizeBody || 'n/a'}
- Replay verification output:
  - ${replayResult.ok ? 'pnpm ops:replay-smoke passed' : 'pnpm ops:replay-smoke failed'}
  - artifacts: artifacts/ops/replay-report.md

## Drift and Incident Notes

- Drift detected: ${replayResult.ok ? 'NO' : 'YES'}
- Incident ticket(s): <fill>
- Root cause summary: <fill if needed>
- Remediation and prevention actions: <fill if needed>

## Notes

${notes.length > 0 ? notes.map((note) => `- ${note}`).join('\n') : '- No blocking findings in this run.'}

## Sign-off

- Incident Commander: ____________________ Date: __________
- Platform SRE Lead: _____________________ Date: __________
- Security Lead: _________________________ Date: __________
`;

fs.mkdirSync(path.dirname(output), { recursive: true });
fs.writeFileSync(output, report, 'utf8');
console.log(`Wrote ${output}`);
