import type {
  FabricAgent,
  FabricEnforcementPoint,
  FabricInventory,
  FabricPolicyChannel,
  FabricToolAction,
} from "./index.js";

export type FabricReadinessLevel = "ready" | "watch" | "blocked";
export type FabricReadinessSeverity = "info" | "warning" | "critical";

export interface FabricReadinessSignal {
  id: string;
  label: string;
  value: number;
  status: FabricReadinessLevel;
  summary: string;
  recommendation: string;
  className: string;
}

export interface FabricReadinessIssue {
  id: string;
  severity: FabricReadinessSeverity;
  title: string;
  detail: string;
  remediation: string;
}

export interface FabricPosture {
  score: number;
  level: FabricReadinessLevel;
  signals: FabricReadinessSignal[];
  issues: FabricReadinessIssue[];
}

export interface DoctrinePosture {
  score: number;
  level: FabricReadinessLevel;
  summary: string;
  registered: boolean;
  counts: {
    agents: number;
    enforcementPoints: number;
    actions: number;
    channels: number;
    gates: number;
  };
  controls: Array<{
    id: string;
    label: string;
    passed: boolean;
    detail: string;
  }>;
  issues: FabricReadinessIssue[];
}

export interface FabricReadinessReport {
  generated_at: string;
  fabric: FabricPosture;
  doctrine: DoctrinePosture;
}

const EMPTY_STATS = {
  agents: 0,
  enforcement_points: 0,
  tool_actions: 0,
  policy_channels: 0,
  active_agents: 0,
  active_enforcement_points: 0,
  critical_tool_actions: 0,
};

export function buildFabricReadinessReport(
  data: FabricInventory,
  generatedAt = new Date().toISOString(),
): FabricReadinessReport {
  return {
    generated_at: generatedAt,
    fabric: buildFabricPosture(data),
    doctrine: buildDoctrinePosture(data),
  };
}

export function buildFabricPosture(data?: FabricInventory): FabricPosture {
  const stats = data?.stats ?? EMPTY_STATS;
  const agents = data?.agents.data ?? [];
  const enforcementPoints = data?.enforcementPoints.data ?? [];
  const channels = data?.policyChannels.data ?? [];
  const actions = data?.toolActions.data ?? [];
  const graph = data?.graph;

  const activeAgentCoverage = percent(stats.active_agents, stats.agents);
  const activeGuardCoverage = percent(
    stats.active_enforcement_points,
    stats.enforcement_points,
  );
  const protectedAgentCoverage = percent(
    agents.filter((agent) => hasProtectedByEdge(agent.agent_id, graph)).length,
    agents.length,
  );
  const activeChannelCoverage = percent(
    channels.filter((channel) => channel.rollout_state === "ACTIVE").length,
    channels.length,
  );
  const highRiskActions = actions.filter(isHighRiskAction);
  const approvalCoverage = highRiskActions.length
    ? percent(
        highRiskActions.filter((action) => action.approval_required).length,
        highRiskActions.length,
      )
    : 100;
  const productionAgents = agents.filter(
    (agent) => agent.environment === "prod",
  );
  const productionGuardCoverage = productionAgents.length
    ? percent(
        productionAgents.filter((agent) =>
          isAgentProtectedByActivePoint(agent, enforcementPoints),
        ).length,
        productionAgents.length,
      )
    : 100;

  const signals: FabricReadinessSignal[] = [
    makeSignal({
      id: "active-agent-coverage",
      label: "Active agent coverage",
      value: activeAgentCoverage,
      summary: `${stats.active_agents} of ${stats.agents} agents are active.`,
      recommendation: "Activate or decommission inactive agents so inventory state is intentional.",
      className: "h-full rounded-full bg-cyan-300",
    }),
    makeSignal({
      id: "active-enforcement-coverage",
      label: "Active enforcement coverage",
      value: activeGuardCoverage,
      summary: `${stats.active_enforcement_points} of ${stats.enforcement_points} enforcement points are active.`,
      recommendation: "Bring every production guard online or mark retired points as decommissioned.",
      className: "h-full rounded-full bg-emerald-300",
    }),
    makeSignal({
      id: "protected-agent-coverage",
      label: "Protected agent coverage",
      value: protectedAgentCoverage,
      summary: `${countProtectedAgents(agents, graph)} of ${agents.length} agents have graph protection edges.`,
      recommendation: "Link each agent to at least one enforcement point in the Fabric graph.",
      className: "h-full rounded-full bg-teal-300",
    }),
    makeSignal({
      id: "active-policy-channels",
      label: "Active policy channels",
      value: activeChannelCoverage,
      summary: `${channels.filter((channel) => channel.rollout_state === "ACTIVE").length} of ${channels.length} channels are active.`,
      recommendation: "Promote policy bundles into active rollout channels before production use.",
      className: "h-full rounded-full bg-blue-300",
    }),
    makeSignal({
      id: "high-risk-approval-coverage",
      label: "High-risk approval coverage",
      value: approvalCoverage,
      summary: highRiskActions.length
        ? `${highRiskActions.filter((action) => action.approval_required).length} of ${highRiskActions.length} high-risk actions require approval.`
        : "No high-risk actions are registered.",
      recommendation: "Require human approval for critical production-impacting tool actions.",
      className: "h-full rounded-full bg-amber-300",
    }),
    makeSignal({
      id: "production-guard-coverage",
      label: "Production guard coverage",
      value: productionGuardCoverage,
      summary: `${productionAgents.filter((agent) => isAgentProtectedByActivePoint(agent, enforcementPoints)).length} of ${productionAgents.length} production agents are attached to active guards.`,
      recommendation: "Attach every production agent to an active enforcement point.",
      className: "h-full rounded-full bg-indigo-300",
    }),
  ];

  const issues = buildFabricIssues({
    agents,
    enforcementPoints,
    channels,
    actions,
    signals,
  });
  const score = Math.round(
    signals.reduce((sum, signal) => sum + signal.value, 0) / signals.length,
  );

  return {
    score,
    level: readinessLevel(score, issues),
    signals,
    issues,
  };
}

export function buildDoctrinePosture(data?: FabricInventory): DoctrinePosture {
  const doctrine = getDoctrineInventory(data);
  const gates = collectDoctrineGates(doctrine.agents, doctrine.channels);
  const hasAgent = doctrine.agents.length > 0;
  const hasGatekeeper = doctrine.enforcementPoints.some(
    (point) => point.status === "ACTIVE",
  );
  const hasVerifyAction = doctrine.actions.some((action) =>
    action.action.toLowerCase().includes("verify"),
  );
  const hasCheckpointAction = doctrine.actions.some((action) =>
    action.action.toLowerCase().includes("checkpoint"),
  );
  const hasActiveChannel = doctrine.channels.some(
    (channel) => channel.rollout_state === "ACTIVE",
  );
  const hasGateCoverage = gates.size >= 8;

  const controls = [
    {
      id: "agent-runtime",
      label: "Doctrine runtime registered",
      passed: hasAgent,
      detail: hasAgent
        ? `${doctrine.agents.length} Doctrine runtime record(s) in Fabric.`
        : "No Doctrine runtime agent record found.",
    },
    {
      id: "gatekeeper",
      label: "Gatekeeper active",
      passed: hasGatekeeper,
      detail: hasGatekeeper
        ? "Doctrine gatekeeper enforcement point is active."
        : "No active Doctrine enforcement point is registered.",
    },
    {
      id: "verify-action",
      label: "Verify action modeled",
      passed: hasVerifyAction,
      detail: hasVerifyAction
        ? "Doctrine gate verification is visible as a governed tool action."
        : "Doctrine verify action is missing from Fabric tool actions.",
    },
    {
      id: "checkpoint-action",
      label: "Checkpoint action modeled",
      passed: hasCheckpointAction,
      detail: hasCheckpointAction
        ? "Doctrine checkpointing is visible as a governed tool action."
        : "Doctrine checkpoint action is missing from Fabric tool actions.",
    },
    {
      id: "release-channel",
      label: "Gold build channel active",
      passed: hasActiveChannel,
      detail: hasActiveChannel
        ? "Doctrine release promotion has an active policy channel."
        : "Doctrine release channel is not active.",
    },
    {
      id: "g0-g7-coverage",
      label: "G0-G7 gate coverage",
      passed: hasGateCoverage,
      detail: hasGateCoverage
        ? "All eight Doctrine gates are represented in metadata."
        : `${gates.size} of 8 Doctrine gates are represented in metadata.`,
    },
  ];

  const issues: FabricReadinessIssue[] = controls
    .filter((control) => !control.passed)
    .map((control) => ({
      id: `doctrine-${control.id}`,
      severity: control.id === "agent-runtime" ? "critical" : "warning",
      title: control.label,
      detail: control.detail,
      remediation: doctrineRemediation(control.id),
    }));

  const score = Math.round(
    (controls.filter((control) => control.passed).length / controls.length) *
      100,
  );

  return {
    score,
    level: readinessLevel(score, issues),
    summary: controls.every((control) => control.passed)
      ? "Doctrine is fully represented as a read-only STIX Fabric runtime."
      : "Doctrine is partially represented; complete the missing registry records before enforcement wrapping.",
    registered: controls.some((control) => control.passed),
    counts: {
      agents: doctrine.agents.length,
      enforcementPoints: doctrine.enforcementPoints.length,
      actions: doctrine.actions.length,
      channels: doctrine.channels.length,
      gates: gates.size,
    },
    controls,
    issues,
  };
}

export function getDoctrineInventory(data?: FabricInventory) {
  const agents = data?.agents.data.filter((agent) =>
    [agent.agent_id, agent.runtime, agent.display_name, ...agent.labels].some(
      includesDoctrine,
    ),
  ) ?? [];
  const enforcementPoints =
    data?.enforcementPoints.data.filter((point) =>
      [point.enforcement_point_id, point.display_name, point.type].some(
        includesDoctrine,
      ),
    ) ?? [];
  const actions =
    data?.toolActions.data.filter((action) =>
      [action.action_id, action.action, action.display_name].some(
        includesDoctrine,
      ),
    ) ?? [];
  const channels =
    data?.policyChannels.data.filter((channel) =>
      [channel.channel_id, channel.display_name, channel.active_bundle_id ?? ""].some(
        includesDoctrine,
      ),
    ) ?? [];

  return {
    agents,
    enforcementPoints,
    actions,
    channels,
  };
}

function buildFabricIssues({
  agents,
  enforcementPoints,
  channels,
  actions,
  signals,
}: {
  agents: FabricAgent[];
  enforcementPoints: FabricEnforcementPoint[];
  channels: FabricPolicyChannel[];
  actions: FabricToolAction[];
  signals: FabricReadinessSignal[];
}): FabricReadinessIssue[] {
  const issues: FabricReadinessIssue[] = [];

  if (!agents.length) {
    issues.push({
      id: "no-agents",
      severity: "critical",
      title: "No agents registered",
      detail: "Fabric cannot govern a runtime that is not represented in the registry.",
      remediation: "Register agents through the Fabric API or seed a demo inventory.",
    });
  }

  if (!enforcementPoints.length) {
    issues.push({
      id: "no-enforcement-points",
      severity: "critical",
      title: "No enforcement points registered",
      detail: "Agents need SDK, gateway, CI, MCP, or target enforcement points.",
      remediation: "Register at least one enforcement point and attach agent IDs.",
    });
  }

  if (!channels.some((channel) => channel.rollout_state === "ACTIVE")) {
    issues.push({
      id: "no-active-policy-channel",
      severity: "critical",
      title: "No active policy channel",
      detail: "Policy rollout lanes exist only after a channel is active.",
      remediation: "Promote a policy bundle to an ACTIVE policy channel.",
    });
  }

  const unapprovedCritical = actions.filter(
    (action) => action.risk_tier === "CRITICAL" && !action.approval_required,
  );
  if (unapprovedCritical.length) {
    issues.push({
      id: "critical-actions-without-approval",
      severity: "critical",
      title: "Critical actions without approval",
      detail: `${unapprovedCritical.length} critical action(s) can run without human approval.`,
      remediation: "Set approval_required=true on all critical tool actions.",
    });
  }

  for (const signal of signals) {
    if (signal.status === "blocked") {
      issues.push({
        id: `${signal.id}-blocked`,
        severity: "warning",
        title: `${signal.label} below release threshold`,
        detail: signal.summary,
        remediation: signal.recommendation,
      });
    }
  }

  return dedupeIssues(issues);
}

function makeSignal(
  input: Omit<FabricReadinessSignal, "status">,
): FabricReadinessSignal {
  return {
    ...input,
    value: clampPercent(input.value),
    status: signalStatus(input.value),
  };
}

function signalStatus(value: number): FabricReadinessLevel {
  if (value >= 90) return "ready";
  if (value >= 70) return "watch";
  return "blocked";
}

function readinessLevel(
  score: number,
  issues: FabricReadinessIssue[],
): FabricReadinessLevel {
  if (issues.some((issue) => issue.severity === "critical")) return "blocked";
  if (score >= 90) return "ready";
  if (score >= 70) return "watch";
  return "blocked";
}

function percent(value: number, total: number) {
  if (total <= 0) return 0;
  return Math.round((value / total) * 100);
}

function clampPercent(value: number) {
  return Math.max(0, Math.min(100, Math.round(value)));
}

function isHighRiskAction(action: FabricToolAction) {
  return action.risk_tier === "HIGH" || action.risk_tier === "CRITICAL";
}

function hasProtectedByEdge(agentId: string, graph?: FabricInventory["graph"]) {
  return graph?.edges.some(
    (edge) => edge.from === agentId && edge.relation === "protected_by",
  ) ?? false;
}

function countProtectedAgents(
  agents: FabricAgent[],
  graph?: FabricInventory["graph"],
) {
  return agents.filter((agent) => hasProtectedByEdge(agent.agent_id, graph)).length;
}

function isAgentProtectedByActivePoint(
  agent: FabricAgent,
  enforcementPoints: FabricEnforcementPoint[],
) {
  return enforcementPoints.some(
    (point) =>
      point.status === "ACTIVE" && point.agent_ids.includes(agent.agent_id),
  );
}

function includesDoctrine(value: string) {
  return value.toLowerCase().includes("doctrine");
}

function collectDoctrineGates(
  agents: FabricAgent[],
  channels: FabricPolicyChannel[],
) {
  const gates = new Set<string>();

  for (const agent of agents) {
    collectGateValues(agent.metadata.gates, gates);
  }

  for (const channel of channels) {
    collectGateValues(channel.metadata.gates, gates);
    const coverage = channel.metadata.coverage;
    if (typeof coverage === "string" && coverage.toLowerCase().includes("g0-g7")) {
      for (let index = 0; index <= 7; index += 1) {
        gates.add(`G${index}`);
      }
    }
  }

  return gates;
}

function collectGateValues(value: unknown, gates: Set<string>) {
  if (!Array.isArray(value)) {
    return;
  }

  for (const item of value) {
    if (typeof item === "string" && /^G[0-7]$/i.test(item)) {
      gates.add(item.toUpperCase());
    }
  }
}

function doctrineRemediation(controlId: string) {
  const remediations: Record<string, string> = {
    "agent-runtime": "Register `agent_doctrine_os` through the Fabric API.",
    gatekeeper: "Register `ep_doctrine_gatekeeper` and keep it ACTIVE.",
    "verify-action": "Register `tool_doctrine_verify` as a Fabric tool action.",
    "checkpoint-action": "Register `tool_doctrine_checkpoint` as a Fabric tool action.",
    "release-channel": "Register and activate `channel_doctrine_gold_build`.",
    "g0-g7-coverage": "Add G0-G7 metadata to the Doctrine agent or policy channel.",
  };

  return remediations[controlId] ?? "Complete the missing Doctrine Fabric record.";
}

function dedupeIssues(issues: FabricReadinessIssue[]) {
  const seen = new Set<string>();
  return issues.filter((issue) => {
    if (seen.has(issue.id)) return false;
    seen.add(issue.id);
    return true;
  });
}
