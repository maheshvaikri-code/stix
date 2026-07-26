#!/usr/bin/env node

import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { spawnSync } from "node:child_process";
import YAML from "yaml";

const defaultComposeFile = "deploy/docker/docker-compose.yaml";
const defaultReportPath = "artifacts/deploy/floci-fde-gate-report.json";

const args = new Set(process.argv.slice(2));
const getArgValue = (name, fallback) => {
  const prefix = `${name}=`;
  const found = process.argv.slice(2).find((arg) => arg.startsWith(prefix));
  return found ? found.slice(prefix.length) : fallback;
};

const composeFile = getArgValue("--compose-file", defaultComposeFile);
const reportPath = getArgValue("--report", defaultReportPath);
const projectName = getArgValue("--project-name", "");
const skipBuild = args.has("--skip-build");
const teardown = args.has("--teardown");
const resetVolumes = args.has("--reset-volumes");
const checkOnly = args.has("--check-only");
const includeDoctrineObserver = args.has("--include-doctrine-observer");
const timeoutMs = Number.parseInt(getArgValue("--timeout-ms", "180000"), 10);

const endpoints = [
  { id: "enforcer", url: "http://localhost:3001/health", expectJson: true },
  { id: "policy", url: "http://localhost:3002/health", expectJson: true },
  { id: "evidence", url: "http://localhost:3003/health", expectJson: true },
  { id: "approvals", url: "http://localhost:3004/health", expectJson: true },
  { id: "fabric", url: "http://localhost:3005/health", expectJson: true },
  { id: "dashboard", url: "http://localhost:3100/" },
  { id: "floci", url: "http://localhost:4566/" },
];

const routes = includeDoctrineObserver
  ? ["/", "/fabric", "/doctrine", "/settings"]
  : ["/", "/fabric", "/settings"];

function run(command, commandArgs, options = {}) {
  const result = spawnSync(command, commandArgs, {
    cwd: process.cwd(),
    env: {
      ...process.env,
      ...options.env,
    },
    encoding: "utf8",
    stdio: options.capture ? "pipe" : "inherit",
  });

  if (result.status !== 0) {
    throw new Error(
      [
        `${command} ${commandArgs.join(" ")} failed with exit code ${result.status}`,
        result.stdout?.trim(),
        result.stderr?.trim(),
      ]
        .filter(Boolean)
        .join("\n"),
    );
  }

  return result.stdout?.trim() ?? "";
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

function composeArgs() {
  return [
    "compose",
    ...(projectName ? ["-p", projectName] : []),
    "-f",
    composeFile,
  ];
}

function validateComposeContract() {
  const raw = readFileSync(composeFile, "utf8");
  const compose = YAML.parse(raw);
  const services = compose?.services ?? {};
  const failures = [];

  for (const [serviceName, service] of Object.entries(services)) {
    if (service?.container_name) {
      failures.push(
        `services.${serviceName}.container_name must be omitted so isolated Compose project names work.`,
      );
    }
  }

  const floci = services.floci;
  if (!floci) {
    failures.push("services.floci is required for the FDE local AWS lane.");
  } else {
    if (
      typeof floci.image !== "string" ||
      floci.image.includes("floci/floci:latest")
    ) {
      failures.push(
        "services.floci.image must default to a pinned Floci release tag, not latest.",
      );
    }
    if (!String(floci.ports ?? "").includes("4566")) {
      failures.push("services.floci must expose host port 4566.");
    }
    const flociEnv = envMap(floci.environment);
    expectEnv(
      flociEnv,
      "FLOCI_DEFAULT_REGION",
      "${AWS_DEFAULT_REGION:-us-east-1}",
      failures,
    );
    expectEnv(flociEnv, "FLOCI_HOSTNAME", "floci", failures);
    expectEnv(flociEnv, "FLOCI_BASE_URL", "http://floci:4566", failures);
  }

  for (const serviceName of [
    "enforcer",
    "policy",
    "evidence",
    "approvals",
    "fabric",
  ]) {
    const service = services[serviceName];
    if (!service) {
      failures.push(`services.${serviceName} is missing.`);
      continue;
    }

    const env = envMap(service.environment);
    expectEnv(
      env,
      "AWS_ENDPOINT_URL",
      "http://floci:4566",
      failures,
      serviceName,
    );
    expectEnv(env, "AWS_ACCESS_KEY_ID", "test", failures, serviceName);
    expectEnv(env, "AWS_SECRET_ACCESS_KEY", "test", failures, serviceName);
  }

  if (
    raw.includes("${AWS_ACCESS_KEY_ID") ||
    raw.includes("${AWS_SECRET_ACCESS_KEY")
  ) {
    failures.push(
      "Compose must not pass host AWS credentials into the FDE local emulator stack.",
    );
  }

  if (failures.length) {
    throw new Error(
      `Floci FDE compose contract failed:\n- ${failures.join("\n- ")}`,
    );
  }

  return {
    floci_image: floci.image,
    floci_port: "4566",
    aws_endpoint_url: "http://floci:4566",
    credentials: "static dummy values only",
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
      throw new Error(
        `Dashboard route ${route} returned HTTP ${result.status}`,
      );
    }
  }

  return results;
}

async function collectReadiness() {
  const result = await fetchText(
    "http://localhost:3005/api/v1/fabric/readiness",
  );

  if (!result.ok) {
    throw new Error(`Fabric readiness returned HTTP ${result.status}`);
  }

  const readiness = JSON.parse(result.text);
  if (readiness.fabric?.level !== "ready") {
    throw new Error(
      `Fabric readiness is ${readiness.fabric?.level ?? "unknown"}`,
    );
  }

  return {
    generated_at: readiness.generated_at,
    fabric: {
      score: readiness.fabric.score,
      level: readiness.fabric.level,
      issues: readiness.fabric.issues.length,
    },
    doctrine_operator: {
      external_module: true,
      product_component: false,
      registered_observer: Boolean(readiness.doctrine?.registered),
      level: readiness.doctrine?.level ?? "ready",
      issues: readiness.doctrine?.issues?.length ?? 0,
    },
  };
}

function runJson(command, commandArgs) {
  const output = run(command, commandArgs, { capture: true });
  const jsonStart = output.indexOf("{");

  if (jsonStart === -1) {
    throw new Error(
      `Expected JSON output from ${command} ${commandArgs.join(" ")}`,
    );
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
  const dockerComposeArgs = composeArgs();
  const composeContract = validateComposeContract();

  run("docker", [...dockerComposeArgs, "config", "--quiet"]);

  if (checkOnly) {
    console.log(
      JSON.stringify(
        {
          ok: true,
          check_only: true,
          compose_file: composeFile,
          compose_contract: composeContract,
        },
        null,
        2,
      ),
    );
    return;
  }

  if (resetVolumes) {
    run("docker", [...dockerComposeArgs, "down", "--volumes"]);
  }

  run("docker", [
    ...dockerComposeArgs,
    "up",
    "-d",
    ...(skipBuild ? [] : ["--build"]),
  ]);

  const waitStatus = await waitForEndpoints();
  const health = await collectHealth();

  run(process.execPath, ["scripts/demo/seed-fabric-demo.mjs"], {
    env: {
      STIX_FABRIC_URL: "http://localhost:3005",
      STIX_DEMO_INCLUDE_DOCTRINE: includeDoctrineObserver ? "true" : "false",
    },
  });

  const readiness = await collectReadiness();
  const routeSmoke = await collectRouteSmoke();
  const flociSmoke = runJson(process.execPath, [
    "scripts/deploy/floci-aws-smoke.mjs",
  ]);

  const report = {
    ok: true,
    started_at: startedAt,
    completed_at: new Date().toISOString(),
    doctrine_fde: {
      engaged: true,
      role: "external governed operating module",
      fabric_product_component: false,
      cloud_verified: false,
      emulator_verified: true,
      provider: "aws",
    },
    compose_file: composeFile,
    project_name: projectName || "compose-default",
    check_only: checkOnly,
    skip_build: skipBuild,
    reset_volumes: resetVolumes,
    include_doctrine_observer: includeDoctrineObserver,
    compose_contract: composeContract,
    wait_status: waitStatus,
    health,
    readiness,
    route_smoke: routeSmoke,
    floci_smoke: flociSmoke,
  };

  const absoluteReportPath = writeReport(report);
  console.log(
    JSON.stringify(
      {
        ok: true,
        report: absoluteReportPath,
        readiness,
        routeSmoke,
        flociSmoke,
      },
      null,
      2,
    ),
  );

  if (teardown) {
    run("docker", [
      ...dockerComposeArgs,
      "down",
      ...(resetVolumes ? ["--volumes"] : []),
    ]);
  }
}

main().catch((error) => {
  console.error(error instanceof Error ? error.message : String(error));

  if (teardown) {
    run("docker", [
      ...composeArgs(),
      "down",
      ...(resetVolumes ? ["--volumes"] : []),
    ]);
  }

  process.exit(1);
});

function envMap(value) {
  if (Array.isArray(value)) {
    return Object.fromEntries(
      value.map((entry) => {
        const [key, ...rest] = String(entry).split("=");
        return [key, rest.join("=")];
      }),
    );
  }

  if (value && typeof value === "object") {
    return value;
  }

  return {};
}

function expectEnv(env, key, expected, failures, serviceName = "floci") {
  if (env[key] !== expected) {
    failures.push(
      `services.${serviceName}.environment.${key} must be ${expected}.`,
    );
  }
}
