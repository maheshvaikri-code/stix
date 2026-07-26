#!/usr/bin/env node

import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { spawnSync } from 'node:child_process';

const defaultComposeFile = 'deploy/docker/docker-compose.yaml';
const defaultReportPath = 'artifacts/deploy/floci-fde-gate-report.json';

const args = new Set(process.argv.slice(2));
const getArgValue = (name, fallback) => {
  const prefix = `${name}=`;
  const found = process.argv.slice(2).find((arg) => arg.startsWith(prefix));
  return found ? found.slice(prefix.length) : fallback;
};

const composeFile = getArgValue('--compose-file', defaultComposeFile);
const reportPath = getArgValue('--report', defaultReportPath);
const skipBuild = args.has('--skip-build');
const teardown = args.has('--teardown');
const timeoutMs = Number.parseInt(getArgValue('--timeout-ms', '180000'), 10);

const endpoints = [
  { id: 'enforcer', url: 'http://localhost:3001/health', expectJson: true },
  { id: 'policy', url: 'http://localhost:3002/health', expectJson: true },
  { id: 'evidence', url: 'http://localhost:3003/health', expectJson: true },
  { id: 'approvals', url: 'http://localhost:3004/health', expectJson: true },
  { id: 'fabric', url: 'http://localhost:3005/health', expectJson: true },
  { id: 'dashboard', url: 'http://localhost:3100/' },
  { id: 'floci', url: 'http://localhost:4566/' },
];

const routes = ['/', '/fabric', '/doctrine', '/settings'];

function run(command, commandArgs, options = {}) {
  const result = spawnSync(command, commandArgs, {
    cwd: process.cwd(),
    env: {
      ...process.env,
      ...options.env,
    },
    encoding: 'utf8',
    stdio: options.capture ? 'pipe' : 'inherit',
  });

  if (result.status !== 0) {
    throw new Error(
      [
        `${command} ${commandArgs.join(' ')} failed with exit code ${result.status}`,
        result.stdout?.trim(),
        result.stderr?.trim(),
      ]
        .filter(Boolean)
        .join('\n'),
    );
  }

  return result.stdout?.trim() ?? '';
}

async function sleep(ms) {
  await new Promise((resolveSleep) => setTimeout(resolveSleep, ms));
}

async function fetchText(url) {
  const response = await fetch(url);
  const text = await response.text();

  return {
    ok: response.ok,
    status: response.status,
    text,
  };
}

async function waitForEndpoints() {
  const deadline = Date.now() + timeoutMs;
  const observed = new Map();

  while (Date.now() < deadline) {
    let allHealthy = true;

    for (const endpoint of endpoints) {
      try {
        const result = await fetchText(endpoint.url);
        observed.set(endpoint.id, result.status);

        if (!result.ok) {
          allHealthy = false;
        }
      } catch {
        observed.set(endpoint.id, 0);
        allHealthy = false;
      }
    }

    if (allHealthy) {
      return Object.fromEntries(observed);
    }

    await sleep(3000);
  }

  throw new Error(
    `Timed out waiting for endpoints: ${JSON.stringify(Object.fromEntries(observed))}`,
  );
}

async function collectHealth() {
  const results = {};

  for (const endpoint of endpoints) {
    const result = await fetchText(endpoint.url);
    results[endpoint.id] = endpoint.expectJson
      ? JSON.parse(result.text)
      : { status: result.status, bytes: result.text.length };
  }

  return results;
}

async function collectRouteSmoke() {
  const results = {};

  for (const route of routes) {
    const result = await fetchText(`http://localhost:3100${route}`);
    results[route] = {
      status: result.status,
      bytes: result.text.length,
    };

    if (!result.ok) {
      throw new Error(`Dashboard route ${route} returned HTTP ${result.status}`);
    }
  }

  return results;
}

async function collectReadiness() {
  const result = await fetchText('http://localhost:3005/api/v1/fabric/readiness');

  if (!result.ok) {
    throw new Error(`Fabric readiness returned HTTP ${result.status}`);
  }

  const readiness = JSON.parse(result.text);

  if (readiness.doctrine?.level !== 'ready') {
    throw new Error(`Doctrine readiness is ${readiness.doctrine?.level ?? 'unknown'}`);
  }

  return {
    generated_at: readiness.generated_at,
    fabric: {
      score: readiness.fabric.score,
      level: readiness.fabric.level,
      issues: readiness.fabric.issues.length,
    },
    doctrine: {
      score: readiness.doctrine.score,
      level: readiness.doctrine.level,
      registered: readiness.doctrine.registered,
      issues: readiness.doctrine.issues.length,
    },
  };
}

function runJson(command, commandArgs) {
  const output = run(command, commandArgs, { capture: true });
  const jsonStart = output.indexOf('{');

  if (jsonStart === -1) {
    throw new Error(`Expected JSON output from ${command} ${commandArgs.join(' ')}`);
  }

  return JSON.parse(output.slice(jsonStart));
}

function writeReport(report) {
  const absoluteReportPath = resolve(reportPath);
  mkdirSync(dirname(absoluteReportPath), { recursive: true });
  writeFileSync(absoluteReportPath, `${JSON.stringify(report, null, 2)}\n`);
  return absoluteReportPath;
}

async function main() {
  const startedAt = new Date().toISOString();
  const composeArgs = ['compose', '-f', composeFile];

  run('docker', [...composeArgs, 'config', '--quiet']);
  run('docker', [...composeArgs, 'up', '-d', ...(skipBuild ? [] : ['--build'])]);

  const waitStatus = await waitForEndpoints();
  const health = await collectHealth();

  run(process.execPath, ['scripts/demo/seed-fabric-demo.mjs'], {
    env: { STIX_FABRIC_URL: 'http://localhost:3005' },
  });

  const readiness = await collectReadiness();
  const routeSmoke = await collectRouteSmoke();
  const flociSmoke = runJson(process.execPath, ['scripts/deploy/floci-aws-smoke.mjs']);

  const report = {
    ok: true,
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    compose_file: composeFile,
    skip_build: skipBuild,
    wait_status: waitStatus,
    health,
    readiness,
    route_smoke: routeSmoke,
    floci_smoke: flociSmoke,
  };

  const absoluteReportPath = writeReport(report);
  console.log(JSON.stringify({ ok: true, report: absoluteReportPath, readiness, routeSmoke, flociSmoke }, null, 2));

  if (teardown) {
    run('docker', [...composeArgs, 'down']);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));

  if (teardown) {
    run('docker', ['compose', '-f', composeFile, 'down']);
  }

  process.exit(1);
});
