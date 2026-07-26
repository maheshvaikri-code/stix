#!/usr/bin/env node

/**
 * Seed a running STIX Fabric API with deterministic demo inventory.
 *
 * Doctrine/FDE is intentionally not seeded by default: it is a governed
 * operating module for repo execution, not a STIX Fabric product component.
 * Set STIX_DEMO_INCLUDE_DOCTRINE=true or pass --include-doctrine to add
 * optional read-only observer records for demos that explicitly need them.
 */

import { readFileSync } from "node:fs";

const fabricUrl = (
  process.env.STIX_FABRIC_URL ?? "http://localhost:3005"
).replace(/\/$/, "");
const timeoutMs = Number.parseInt(
  process.env.STIX_DEMO_TIMEOUT_MS ?? "10000",
  10,
);
const includeDoctrine =
  process.env.STIX_DEMO_INCLUDE_DOCTRINE === "true" ||
  process.argv.includes("--include-doctrine");
const rootPackage = JSON.parse(
  readFileSync(new URL("../../package.json", import.meta.url), "utf8"),
);
const bundleVersion = String(rootPackage.version ?? "0.0.0").replaceAll(
  ".",
  "_",
);

const fabricRecords = [
  {
    path: "/api/v1/fabric/agents",
    body: {
      agent_id: "agent_release_captain",
      display_name: "Autonomous Release Captain",
      owner: "platform-security",
      runtime: "codex",
      environment: "prod",
      risk_tier: "HIGH",
      status: "ACTIVE",
      labels: ["release", "codex", "fabric"],
      metadata: {
        lane: "production",
        posture: "governed",
        proof_tokens: "required",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/agents",
    body: {
      agent_id: "agent_clinical_reviewer",
      display_name: "Clinical Compliance Reviewer",
      owner: "healthcare-governance",
      runtime: "claude",
      environment: "stage",
      risk_tier: "CRITICAL",
      status: "ACTIVE",
      labels: ["hipaa", "phi", "review"],
      metadata: {
        lane: "staging",
        policy_pack: "hipaa-healthcare",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/agents",
    body: {
      agent_id: "agent_finops_sentinel",
      display_name: "FinOps Sentinel",
      owner: "finance-platform",
      runtime: "tool-runner",
      environment: "prod",
      risk_tier: "MEDIUM",
      status: "ACTIVE",
      labels: ["sox", "pci", "evidence"],
      metadata: {
        lane: "production",
        policy_pack: "financial-sox-pci",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/agents",
    body: {
      agent_id: "agent_audit_replayer",
      display_name: "Evidence Replay Auditor",
      owner: "audit-platform",
      runtime: "stix-replay",
      environment: "stage",
      risk_tier: "MEDIUM",
      status: "ACTIVE",
      labels: ["evidence", "replay", "audit"],
      metadata: {
        lane: "staging",
        replay: "strict",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/enforcement-points",
    body: {
      enforcement_point_id: "ep_agent_sdk_prod",
      display_name: "Agent SDK Production Gateway",
      type: "sdk",
      environment: "prod",
      status: "ACTIVE",
      url: "http://localhost:3001/api/v1/authorize",
      agent_ids: ["agent_release_captain", "agent_finops_sentinel"],
      metadata: {
        mode: "proof-token",
        latency_budget_ms: 120,
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/enforcement-points",
    body: {
      enforcement_point_id: "ep_clinical_policy_gateway",
      display_name: "Clinical Policy Gateway",
      type: "service_gateway",
      environment: "stage",
      status: "ACTIVE",
      url: "http://localhost:3001/api/v1/authorize",
      agent_ids: ["agent_clinical_reviewer"],
      metadata: {
        policy_pack: "hipaa-healthcare",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/enforcement-points",
    body: {
      enforcement_point_id: "ep_replay_ci",
      display_name: "Evidence Replay CI Gate",
      type: "ci",
      environment: "stage",
      status: "ACTIVE",
      agent_ids: ["agent_audit_replayer"],
      metadata: {
        branch: "main",
        required_for_tags: true,
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/tool-actions",
    body: {
      action_id: "tool_deploy_prod",
      display_name: "Deploy Production Release",
      action: "deploy",
      resource_type: "production_environment",
      risk_tier: "CRITICAL",
      approval_required: true,
      allowed_environments: ["prod"],
      metadata: {
        proof: "required",
        reviewers: 2,
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/tool-actions",
    body: {
      action_id: "tool_scan_diff",
      display_name: "Scan Merge Request Diff",
      action: "scan_diff",
      resource_type: "source_code",
      risk_tier: "HIGH",
      approval_required: true,
      allowed_environments: ["dev", "test", "stage", "prod"],
      metadata: {
        scanners: ["pii", "phi", "pci", "secrets"],
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/tool-actions",
    body: {
      action_id: "tool_export_attestation",
      display_name: "Export Compliance Attestation",
      action: "export_attestation",
      resource_type: "audit_packet",
      risk_tier: "HIGH",
      approval_required: true,
      allowed_environments: ["stage", "prod"],
      metadata: {
        evidence_chain: "required",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/tool-actions",
    body: {
      action_id: "tool_replay_evidence",
      display_name: "Replay Evidence Chain",
      action: "replay_evidence",
      resource_type: "audit_trail",
      risk_tier: "MEDIUM",
      approval_required: false,
      allowed_environments: ["stage", "prod"],
      metadata: {
        drift_tolerance: "zero",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/policy-channels",
    body: {
      channel_id: "channel_prod_guardrails",
      display_name: "Production Guardrails",
      environment: "prod",
      rollout_state: "ACTIVE",
      active_bundle_id: `bundle_${bundleVersion}_prod`,
      metadata: {
        coverage: "core+fabric",
        rollout: "100%",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/policy-channels",
    body: {
      channel_id: "channel_stage_assurance",
      display_name: "Stage Assurance Policies",
      environment: "stage",
      rollout_state: "ACTIVE",
      active_bundle_id: `bundle_${bundleVersion}_stage`,
      metadata: {
        rollout: "100%",
        owner: "platform-security",
        seed: "stix-fabric-demo",
      },
    },
  },
];

const doctrineObserverRecords = [
  {
    path: "/api/v1/fabric/agents",
    body: {
      agent_id: "agent_doctrine_operator",
      display_name: "Doctrine FDE Operator",
      owner: "engineering-governance",
      runtime: "external-doctrine-fde",
      environment: "prod",
      risk_tier: "HIGH",
      status: "ACTIVE",
      labels: ["doctrine", "operator", "external"],
      metadata: {
        boundary: "external-operating-module",
        gates: ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"],
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/enforcement-points",
    body: {
      enforcement_point_id: "ep_doctrine_observer",
      display_name: "Doctrine Observer Adapter",
      type: "mcp_gateway",
      environment: "prod",
      status: "ACTIVE",
      agent_ids: ["agent_doctrine_operator"],
      metadata: {
        mode: "read-only-observer",
        writes: "stix-authorization-required",
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/tool-actions",
    body: {
      action_id: "tool_doctrine_verify",
      display_name: "Observe Doctrine Verify Gates",
      action: "doctrine_verify",
      resource_type: "external_engineering_governance",
      risk_tier: "HIGH",
      approval_required: true,
      allowed_environments: ["prod"],
      metadata: {
        gates: ["G3", "G4", "G5"],
        observer_only: true,
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/tool-actions",
    body: {
      action_id: "tool_doctrine_checkpoint",
      display_name: "Observe Doctrine Checkpoint State",
      action: "doctrine_checkpoint",
      resource_type: "external_hash_chained_state_plane",
      risk_tier: "MEDIUM",
      approval_required: false,
      allowed_environments: ["dev", "test", "stage", "prod"],
      metadata: {
        state_plane: ".doctrine-state",
        observer_only: true,
        seed: "stix-fabric-demo",
      },
    },
  },
  {
    path: "/api/v1/fabric/policy-channels",
    body: {
      channel_id: "channel_doctrine_observer",
      display_name: "Doctrine Observer Lane",
      environment: "prod",
      rollout_state: "ACTIVE",
      active_bundle_id: `bundle_${bundleVersion}_doctrine_observer`,
      metadata: {
        coverage: "g0-g7",
        boundary: "external-operating-module",
        seed: "stix-fabric-demo",
      },
    },
  },
];

async function main() {
  await request("/ready");

  const records = includeDoctrine
    ? [...fabricRecords, ...doctrineObserverRecords]
    : fabricRecords;

  for (const record of records) {
    await request(record.path, {
      method: "POST",
      body: JSON.stringify(record.body),
    });
  }

  const [stats, graph] = await Promise.all([
    request("/api/v1/fabric/stats"),
    request("/api/v1/fabric/graph/summary"),
  ]);

  console.log("Seeded STIX Fabric demo inventory");
  console.log(`Fabric URL: ${fabricUrl}`);
  console.log(
    `Doctrine observer records: ${includeDoctrine ? "included" : "not included"}`,
  );
  console.log(
    `Agents=${stats.agents} EnforcementPoints=${stats.enforcement_points} ToolActions=${stats.tool_actions} PolicyChannels=${stats.policy_channels}`,
  );
  console.log(
    `GraphNodes=${graph.nodes.length} GraphEdges=${graph.edges.length}`,
  );
}

async function request(path, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const response = await fetch(`${fabricUrl}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        "Content-Type": "application/json",
        ...(options.headers ?? {}),
      },
    });

    if (!response.ok) {
      const text = await response.text();
      throw new Error(
        `${options.method ?? "GET"} ${path} failed (${response.status}): ${text}`,
      );
    }

    return response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(
        `${options.method ?? "GET"} ${path} timed out after ${timeoutMs}ms`,
      );
    }
    throw error;
  } finally {
    clearTimeout(timeout);
  }
}

main().catch((error) => {
  console.error("Failed to seed STIX Fabric demo inventory");
  console.error(error instanceof Error ? error.message : error);
  process.exitCode = 1;
});
