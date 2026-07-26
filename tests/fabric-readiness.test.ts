/**
 * Dashboard Fabric readiness model tests.
 */

import { describe, expect, it } from "vitest";
import type { FabricInventory } from "@stix/fabric-types";
import {
  buildDoctrinePosture,
  buildFabricPosture,
  getDoctrineInventory,
} from "@stix/fabric-types";

const now = "2026-07-25T00:00:00.000Z";

describe("Fabric readiness model", () => {
  it("marks a fully wired Fabric inventory as ready without Doctrine records", () => {
    const inventory = createReadyFabricInventory();
    const posture = buildFabricPosture(inventory);
    const doctrine = getDoctrineInventory(inventory);
    const doctrinePosture = buildDoctrinePosture(inventory);

    expect(posture.score).toBe(100);
    expect(posture.level).toBe("ready");
    expect(posture.issues).toEqual([]);
    expect(posture.signals).toHaveLength(6);
    expect(doctrine.agents).toHaveLength(0);
    expect(doctrinePosture.registered).toBe(false);
    expect(doctrinePosture.level).toBe("ready");
    expect(doctrinePosture.summary).toContain(
      "not a STIX Fabric product component",
    );
  });

  it("reports release-blocking Fabric gaps with remediation", () => {
    const inventory = createReadyFabricInventory();
    inventory.agents.data[0].status = "QUARANTINED";
    inventory.stats.active_agents = inventory.stats.active_agents - 1;
    inventory.graph.edges = inventory.graph.edges.filter(
      (edge) => edge.from !== inventory.agents.data[0].agent_id,
    );
    inventory.toolActions.data[0].approval_required = false;

    const posture = buildFabricPosture(inventory);

    expect(posture.level).toBe("blocked");
    expect(posture.issues.map((issue) => issue.id)).toContain(
      "critical-actions-without-approval",
    );
    expect(posture.issues.some((issue) => issue.remediation.length > 0)).toBe(
      true,
    );
  });

  it("computes optional Doctrine observer posture from explicit records", () => {
    const inventory = createDoctrineObserverInventory();

    const doctrine = getDoctrineInventory(inventory);
    const posture = buildDoctrinePosture(inventory);

    expect(doctrine.agents).toHaveLength(1);
    expect(doctrine.enforcementPoints).toHaveLength(1);
    expect(doctrine.actions).toHaveLength(2);
    expect(doctrine.channels).toHaveLength(1);
    expect(posture.score).toBe(100);
    expect(posture.level).toBe("ready");
    expect(posture.registered).toBe(true);
    expect(posture.counts.gates).toBe(8);
  });

  it("surfaces optional Doctrine observer gaps without blocking Fabric readiness", () => {
    const inventory = createDoctrineObserverInventory();
    inventory.toolActions.data = inventory.toolActions.data.filter(
      (action) => action.action_id !== "tool_doctrine_checkpoint",
    );
    inventory.policyChannels.data[0].rollout_state = "PAUSED";
    inventory.policyChannels.data[0].metadata = {};
    inventory.agents.data[0].metadata = {};

    const posture = buildDoctrinePosture(inventory);

    expect(posture.level).toBe("watch");
    expect(posture.issues.map((issue) => issue.id)).toEqual(
      expect.arrayContaining([
        "doctrine-checkpoint-action",
        "doctrine-release-channel",
        "doctrine-g0-g7-coverage",
      ]),
    );
    expect(posture.issues.every((issue) => issue.severity === "warning")).toBe(
      true,
    );
  });
});

function createReadyFabricInventory(): FabricInventory {
  return {
    agents: {
      total: 3,
      data: [
        {
          agent_id: "agent_release_captain",
          display_name: "Autonomous Release Captain",
          owner: "platform-security",
          runtime: "codex",
          environment: "prod",
          risk_tier: "HIGH",
          status: "ACTIVE",
          labels: ["release", "fabric"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          agent_id: "agent_finops_sentinel",
          display_name: "FinOps Sentinel",
          owner: "finance-platform",
          runtime: "tool-runner",
          environment: "prod",
          risk_tier: "MEDIUM",
          status: "ACTIVE",
          labels: ["sox", "pci"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          agent_id: "agent_audit_replayer",
          display_name: "Evidence Replay Auditor",
          owner: "audit-platform",
          runtime: "stix-replay",
          environment: "stage",
          risk_tier: "MEDIUM",
          status: "ACTIVE",
          labels: ["evidence", "audit"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ],
    },
    enforcementPoints: {
      total: 2,
      data: [
        {
          enforcement_point_id: "ep_agent_sdk_prod",
          display_name: "Agent SDK Production Gateway",
          type: "sdk",
          environment: "prod",
          status: "ACTIVE",
          url: "http://localhost:3001/api/v1/authorize",
          agent_ids: ["agent_release_captain", "agent_finops_sentinel"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          enforcement_point_id: "ep_replay_ci",
          display_name: "Evidence Replay CI Gate",
          type: "ci",
          environment: "stage",
          status: "ACTIVE",
          agent_ids: ["agent_audit_replayer"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ],
    },
    toolActions: {
      total: 3,
      data: [
        {
          action_id: "tool_deploy_prod",
          display_name: "Deploy Production Release",
          action: "deploy",
          resource_type: "production_environment",
          risk_tier: "CRITICAL",
          approval_required: true,
          allowed_environments: ["prod"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          action_id: "tool_scan_diff",
          display_name: "Scan Merge Request Diff",
          action: "scan_diff",
          resource_type: "source_code",
          risk_tier: "HIGH",
          approval_required: true,
          allowed_environments: ["dev", "test", "stage", "prod"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          action_id: "tool_replay_evidence",
          display_name: "Replay Evidence Chain",
          action: "replay_evidence",
          resource_type: "audit_trail",
          risk_tier: "MEDIUM",
          approval_required: false,
          allowed_environments: ["stage", "prod"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ],
    },
    policyChannels: {
      total: 2,
      data: [
        {
          channel_id: "channel_prod_guardrails",
          display_name: "Production Guardrails",
          environment: "prod",
          rollout_state: "ACTIVE",
          active_bundle_id: "bundle_0_1_11_prod",
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          channel_id: "channel_stage_assurance",
          display_name: "Stage Assurance Policies",
          environment: "stage",
          rollout_state: "ACTIVE",
          active_bundle_id: "bundle_0_1_11_stage",
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ],
    },
    stats: {
      agents: 3,
      enforcement_points: 2,
      tool_actions: 3,
      policy_channels: 2,
      active_agents: 3,
      active_enforcement_points: 2,
      critical_tool_actions: 1,
    },
    graph: {
      nodes: [
        {
          id: "agent_release_captain",
          type: "agent",
          label: "Autonomous Release Captain",
          status: "ACTIVE",
          risk_tier: "HIGH",
        },
        {
          id: "agent_finops_sentinel",
          type: "agent",
          label: "FinOps Sentinel",
          status: "ACTIVE",
          risk_tier: "MEDIUM",
        },
        {
          id: "agent_audit_replayer",
          type: "agent",
          label: "Evidence Replay Auditor",
          status: "ACTIVE",
          risk_tier: "MEDIUM",
        },
        {
          id: "ep_agent_sdk_prod",
          type: "enforcement_point",
          label: "Agent SDK Production Gateway",
          status: "ACTIVE",
        },
        {
          id: "ep_replay_ci",
          type: "enforcement_point",
          label: "Evidence Replay CI Gate",
          status: "ACTIVE",
        },
        {
          id: "tool_deploy_prod",
          type: "tool_action",
          label: "Deploy Production Release",
          risk_tier: "CRITICAL",
        },
        {
          id: "channel_prod_guardrails",
          type: "policy_channel",
          label: "Production Guardrails",
          status: "ACTIVE",
        },
      ],
      edges: [
        {
          from: "agent_release_captain",
          to: "ep_agent_sdk_prod",
          relation: "protected_by",
        },
        {
          from: "agent_finops_sentinel",
          to: "ep_agent_sdk_prod",
          relation: "protected_by",
        },
        {
          from: "agent_audit_replayer",
          to: "ep_replay_ci",
          relation: "protected_by",
        },
        {
          from: "agent_release_captain",
          to: "tool_deploy_prod",
          relation: "can_execute",
        },
        {
          from: "agent_release_captain",
          to: "channel_prod_guardrails",
          relation: "governed_by",
        },
      ],
      stats: {
        agents: 3,
        enforcement_points: 2,
        tool_actions: 3,
        policy_channels: 2,
        active_agents: 3,
        active_enforcement_points: 2,
        critical_tool_actions: 1,
      },
    },
  };
}

function createDoctrineObserverInventory(): FabricInventory {
  return {
    agents: {
      total: 1,
      data: [
        {
          agent_id: "agent_doctrine_operator",
          display_name: "Doctrine FDE Operator",
          owner: "engineering-governance",
          runtime: "external-doctrine-fde",
          environment: "prod",
          risk_tier: "HIGH",
          status: "ACTIVE",
          labels: ["doctrine", "operator", "external"],
          metadata: {
            gates: ["G0", "G1", "G2", "G3", "G4", "G5", "G6", "G7"],
          },
          created_at: now,
          updated_at: now,
        },
      ],
    },
    enforcementPoints: {
      total: 1,
      data: [
        {
          enforcement_point_id: "ep_doctrine_observer",
          display_name: "Doctrine Observer Adapter",
          type: "mcp_gateway",
          environment: "prod",
          status: "ACTIVE",
          agent_ids: ["agent_doctrine_operator"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ],
    },
    toolActions: {
      total: 2,
      data: [
        {
          action_id: "tool_doctrine_verify",
          display_name: "Observe Doctrine Verify Gates",
          action: "doctrine_verify",
          resource_type: "external_engineering_governance",
          risk_tier: "HIGH",
          approval_required: true,
          allowed_environments: ["prod"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
        {
          action_id: "tool_doctrine_checkpoint",
          display_name: "Observe Doctrine Checkpoint State",
          action: "doctrine_checkpoint",
          resource_type: "external_hash_chained_state_plane",
          risk_tier: "MEDIUM",
          approval_required: false,
          allowed_environments: ["prod"],
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ],
    },
    policyChannels: {
      total: 1,
      data: [
        {
          channel_id: "channel_doctrine_observer",
          display_name: "Doctrine Observer Lane",
          environment: "prod",
          rollout_state: "ACTIVE",
          active_bundle_id: "bundle_0_1_11_doctrine_observer",
          metadata: {
            coverage: "g0-g7",
          },
          created_at: now,
          updated_at: now,
        },
      ],
    },
    stats: {
      agents: 1,
      enforcement_points: 1,
      tool_actions: 2,
      policy_channels: 1,
      active_agents: 1,
      active_enforcement_points: 1,
      critical_tool_actions: 0,
    },
    graph: {
      nodes: [],
      edges: [],
      stats: {
        agents: 1,
        enforcement_points: 1,
        tool_actions: 2,
        policy_channels: 1,
        active_agents: 1,
        active_enforcement_points: 1,
        critical_tool_actions: 0,
      },
    },
  };
}
