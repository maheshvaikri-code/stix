/**
 * STIX Fabric shared types.
 *
 * These types model the control-plane registry that sits above STIX Core.
 * STIX Core enforces. STIX Fabric governs.
 */

export type FabricEnvironment = 'dev' | 'test' | 'stage' | 'prod';
export type FabricRiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type FabricLifecycleStatus = 'ACTIVE' | 'INACTIVE' | 'QUARANTINED' | 'DECOMMISSIONED';

export type EnforcementPointType =
  | 'sdk'
  | 'ci'
  | 'mcp_gateway'
  | 'tool_gateway'
  | 'service_gateway'
  | 'target';

export type PolicyRolloutState = 'DRAFT' | 'CANARY' | 'ACTIVE' | 'PAUSED' | 'RETIRED';

export interface FabricTimestamps {
  created_at: string;
  updated_at: string;
}

export interface FabricAgent extends FabricTimestamps {
  agent_id: string;
  display_name: string;
  owner: string;
  runtime: string;
  environment: FabricEnvironment;
  risk_tier: FabricRiskTier;
  status: FabricLifecycleStatus;
  labels: string[];
  metadata: Record<string, unknown>;
}

export type CreateFabricAgentInput = Omit<
  FabricAgent,
  'agent_id' | 'labels' | 'metadata' | 'created_at' | 'updated_at'
> & {
  agent_id?: string;
  labels?: string[];
  metadata?: Record<string, unknown>;
};

export interface FabricEnforcementPoint extends FabricTimestamps {
  enforcement_point_id: string;
  display_name: string;
  type: EnforcementPointType;
  environment: FabricEnvironment;
  status: FabricLifecycleStatus;
  url?: string;
  agent_ids: string[];
  metadata: Record<string, unknown>;
}

export type CreateFabricEnforcementPointInput = Omit<
  FabricEnforcementPoint,
  'enforcement_point_id' | 'agent_ids' | 'metadata' | 'created_at' | 'updated_at'
> & {
  enforcement_point_id?: string;
  agent_ids?: string[];
  metadata?: Record<string, unknown>;
};

export interface FabricToolAction extends FabricTimestamps {
  action_id: string;
  display_name: string;
  action: string;
  resource_type: string;
  risk_tier: FabricRiskTier;
  approval_required: boolean;
  allowed_environments: FabricEnvironment[];
  metadata: Record<string, unknown>;
}

export type CreateFabricToolActionInput = Omit<
  FabricToolAction,
  'action_id' | 'metadata' | 'created_at' | 'updated_at'
> & {
  action_id?: string;
  metadata?: Record<string, unknown>;
};

export interface FabricPolicyChannel extends FabricTimestamps {
  channel_id: string;
  display_name: string;
  environment: FabricEnvironment;
  rollout_state: PolicyRolloutState;
  active_bundle_id?: string;
  metadata: Record<string, unknown>;
}

export type CreateFabricPolicyChannelInput = Omit<
  FabricPolicyChannel,
  'channel_id' | 'metadata' | 'created_at' | 'updated_at'
> & {
  channel_id?: string;
  metadata?: Record<string, unknown>;
};

export interface FabricRegistryStats {
  agents: number;
  enforcement_points: number;
  tool_actions: number;
  policy_channels: number;
  active_agents: number;
  active_enforcement_points: number;
  critical_tool_actions: number;
}

export interface FabricGraphSummary {
  nodes: Array<{
    id: string;
    type: 'agent' | 'enforcement_point' | 'tool_action' | 'policy_channel';
    label: string;
    status?: string;
    risk_tier?: string;
  }>;
  edges: Array<{
    from: string;
    to: string;
    relation: 'protected_by' | 'can_execute' | 'governed_by';
  }>;
  stats: FabricRegistryStats;
}
