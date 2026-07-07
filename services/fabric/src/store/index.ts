/**
 * STIX Fabric registry store.
 *
 * Memory is used for local development and tests. Postgres is the durable
 * production registry backend for Fabric's control-plane state.
 */

import { randomUUID } from 'node:crypto';
import { Pool } from 'pg';
import type {
  CreateFabricAgentInput,
  CreateFabricEnforcementPointInput,
  CreateFabricPolicyChannelInput,
  CreateFabricToolActionInput,
  FabricAgent,
  FabricEnforcementPoint,
  FabricGraphSummary,
  FabricPolicyChannel,
  FabricRegistryStats,
  FabricToolAction,
} from '@stix/fabric-types';
import type { Logger } from '@stix/shared';
import type { Config } from '../config/index.js';

export interface FabricStore {
  createAgent(input: CreateFabricAgentInput): Promise<FabricAgent>;
  listAgents(): Promise<FabricAgent[]>;
  getAgent(agentId: string): Promise<FabricAgent | null>;

  createEnforcementPoint(input: CreateFabricEnforcementPointInput): Promise<FabricEnforcementPoint>;
  listEnforcementPoints(): Promise<FabricEnforcementPoint[]>;
  getEnforcementPoint(enforcementPointId: string): Promise<FabricEnforcementPoint | null>;

  createToolAction(input: CreateFabricToolActionInput): Promise<FabricToolAction>;
  listToolActions(): Promise<FabricToolAction[]>;
  getToolAction(actionId: string): Promise<FabricToolAction | null>;

  createPolicyChannel(input: CreateFabricPolicyChannelInput): Promise<FabricPolicyChannel>;
  listPolicyChannels(): Promise<FabricPolicyChannel[]>;
  getPolicyChannel(channelId: string): Promise<FabricPolicyChannel | null>;

  getStats(): Promise<FabricRegistryStats>;
  getGraphSummary(): Promise<FabricGraphSummary>;
  health(): Promise<boolean>;
}

export class InMemoryFabricStore implements FabricStore {
  private readonly agents = new Map<string, FabricAgent>();
  private readonly enforcementPoints = new Map<string, FabricEnforcementPoint>();
  private readonly toolActions = new Map<string, FabricToolAction>();
  private readonly policyChannels = new Map<string, FabricPolicyChannel>();
  private readonly logger: Logger;

  constructor(logger: Logger) {
    this.logger = logger.child({ component: 'InMemoryFabricStore' });
  }

  async createAgent(input: CreateFabricAgentInput): Promise<FabricAgent> {
    const now = new Date().toISOString();
    const agent: FabricAgent = {
      ...input,
      agent_id: input.agent_id ?? this.createId('agent'),
      labels: input.labels ?? [],
      metadata: input.metadata ?? {},
      created_at: now,
      updated_at: now,
    };
    this.agents.set(agent.agent_id, agent);
    this.logger.info('Registered Fabric agent', { agent_id: agent.agent_id });
    return agent;
  }

  async listAgents(): Promise<FabricAgent[]> {
    return this.sortByCreatedAt(Array.from(this.agents.values()));
  }

  async getAgent(agentId: string): Promise<FabricAgent | null> {
    return this.agents.get(agentId) ?? null;
  }

  async createEnforcementPoint(input: CreateFabricEnforcementPointInput): Promise<FabricEnforcementPoint> {
    const now = new Date().toISOString();
    const enforcementPoint: FabricEnforcementPoint = {
      ...input,
      enforcement_point_id: input.enforcement_point_id ?? this.createId('ep'),
      agent_ids: input.agent_ids ?? [],
      metadata: input.metadata ?? {},
      created_at: now,
      updated_at: now,
    };
    this.enforcementPoints.set(enforcementPoint.enforcement_point_id, enforcementPoint);
    this.logger.info('Registered Fabric enforcement point', {
      enforcement_point_id: enforcementPoint.enforcement_point_id,
    });
    return enforcementPoint;
  }

  async listEnforcementPoints(): Promise<FabricEnforcementPoint[]> {
    return this.sortByCreatedAt(Array.from(this.enforcementPoints.values()));
  }

  async getEnforcementPoint(enforcementPointId: string): Promise<FabricEnforcementPoint | null> {
    return this.enforcementPoints.get(enforcementPointId) ?? null;
  }

  async createToolAction(input: CreateFabricToolActionInput): Promise<FabricToolAction> {
    const now = new Date().toISOString();
    const toolAction: FabricToolAction = {
      ...input,
      action_id: input.action_id ?? this.createId('action'),
      metadata: input.metadata ?? {},
      created_at: now,
      updated_at: now,
    };
    this.toolActions.set(toolAction.action_id, toolAction);
    this.logger.info('Registered Fabric tool action', { action_id: toolAction.action_id });
    return toolAction;
  }

  async listToolActions(): Promise<FabricToolAction[]> {
    return this.sortByCreatedAt(Array.from(this.toolActions.values()));
  }

  async getToolAction(actionId: string): Promise<FabricToolAction | null> {
    return this.toolActions.get(actionId) ?? null;
  }

  async createPolicyChannel(input: CreateFabricPolicyChannelInput): Promise<FabricPolicyChannel> {
    const now = new Date().toISOString();
    const channel: FabricPolicyChannel = {
      ...input,
      channel_id: input.channel_id ?? this.createId('channel'),
      metadata: input.metadata ?? {},
      created_at: now,
      updated_at: now,
    };
    this.policyChannels.set(channel.channel_id, channel);
    this.logger.info('Registered Fabric policy channel', { channel_id: channel.channel_id });
    return channel;
  }

  async listPolicyChannels(): Promise<FabricPolicyChannel[]> {
    return this.sortByCreatedAt(Array.from(this.policyChannels.values()));
  }

  async getPolicyChannel(channelId: string): Promise<FabricPolicyChannel | null> {
    return this.policyChannels.get(channelId) ?? null;
  }

  async getStats(): Promise<FabricRegistryStats> {
    const agents = Array.from(this.agents.values());
    const enforcementPoints = Array.from(this.enforcementPoints.values());
    const toolActions = Array.from(this.toolActions.values());

    return createStats(agents, enforcementPoints, toolActions, this.policyChannels.size);
  }

  async getGraphSummary(): Promise<FabricGraphSummary> {
    return buildGraphSummary(
      await this.listAgents(),
      await this.listEnforcementPoints(),
      await this.listToolActions(),
      await this.listPolicyChannels(),
      await this.getStats()
    );
  }

  async health(): Promise<boolean> {
    return true;
  }

  private createId(prefix: string): string {
    return `${prefix}_${randomUUID()}`;
  }

  private sortByCreatedAt<T extends { created_at: string }>(items: T[]): T[] {
    return items.sort((a, b) => a.created_at.localeCompare(b.created_at));
  }
}

type TimestampValue = string | Date;

type AgentRow = Omit<FabricAgent, 'created_at' | 'updated_at'> & {
  created_at: TimestampValue;
  updated_at: TimestampValue;
};

type EnforcementPointRow = Omit<FabricEnforcementPoint, 'created_at' | 'updated_at'> & {
  created_at: TimestampValue;
  updated_at: TimestampValue;
};

type ToolActionRow = Omit<FabricToolAction, 'allowed_environments' | 'created_at' | 'updated_at'> & {
  allowed_envs: FabricToolAction['allowed_environments'];
  created_at: TimestampValue;
  updated_at: TimestampValue;
};

type PolicyChannelRow = Omit<FabricPolicyChannel, 'created_at' | 'updated_at'> & {
  created_at: TimestampValue;
  updated_at: TimestampValue;
};

export class PostgresFabricStore implements FabricStore {
  private readonly pool: Pool;
  private readonly logger: Logger;

  constructor(config: Config, logger: Logger) {
    if (!config.storage.postgresUrl) {
      throw new Error('STORAGE_TYPE=postgres requires POSTGRES_URL for stix-fabric.');
    }

    this.logger = logger.child({ component: 'PostgresFabricStore' });
    this.pool = new Pool({
      connectionString: config.storage.postgresUrl,
      max: 20,
      min: 2,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
  }

  async initialize(): Promise<void> {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS stix_fabric_agents (
        agent_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        owner TEXT NOT NULL,
        runtime TEXT NOT NULL,
        environment TEXT NOT NULL,
        risk_tier TEXT NOT NULL,
        status TEXT NOT NULL,
        labels TEXT[] NOT NULL DEFAULT '{}',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_agents_environment ON stix_fabric_agents(environment);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_agents_status ON stix_fabric_agents(status);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_agents_risk_tier ON stix_fabric_agents(risk_tier);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_agents_labels ON stix_fabric_agents USING GIN(labels);

      CREATE TABLE IF NOT EXISTS stix_fabric_enforcement_points (
        enforcement_point_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        point_type TEXT NOT NULL,
        environment TEXT NOT NULL,
        status TEXT NOT NULL,
        url TEXT,
        agent_ids TEXT[] NOT NULL DEFAULT '{}',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_ep_environment ON stix_fabric_enforcement_points(environment);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_ep_status ON stix_fabric_enforcement_points(status);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_ep_agent_ids ON stix_fabric_enforcement_points USING GIN(agent_ids);

      CREATE TABLE IF NOT EXISTS stix_fabric_tool_actions (
        action_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        action_name TEXT NOT NULL,
        resource_type TEXT NOT NULL,
        risk_tier TEXT NOT NULL,
        approval_required BOOLEAN NOT NULL DEFAULT false,
        allowed_envs TEXT[] NOT NULL DEFAULT '{}',
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_actions_name ON stix_fabric_tool_actions(action_name);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_actions_resource ON stix_fabric_tool_actions(resource_type);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_actions_risk_tier ON stix_fabric_tool_actions(risk_tier);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_actions_allowed_envs ON stix_fabric_tool_actions USING GIN(allowed_envs);

      CREATE TABLE IF NOT EXISTS stix_fabric_policy_channels (
        channel_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL,
        environment TEXT NOT NULL,
        rollout_state TEXT NOT NULL,
        active_bundle_id TEXT,
        metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL
      );
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_channels_environment ON stix_fabric_policy_channels(environment);
      CREATE INDEX IF NOT EXISTS idx_stix_fabric_channels_rollout_state ON stix_fabric_policy_channels(rollout_state);
    `);

    this.logger.info('Postgres Fabric store initialized');
  }

  async createAgent(input: CreateFabricAgentInput): Promise<FabricAgent> {
    const now = new Date().toISOString();
    const agent: FabricAgent = {
      ...input,
      agent_id: input.agent_id ?? this.createId('agent'),
      labels: input.labels ?? [],
      metadata: input.metadata ?? {},
      created_at: now,
      updated_at: now,
    };

    await this.pool.query(
      `INSERT INTO stix_fabric_agents (
         agent_id, display_name, owner, runtime, environment, risk_tier, status,
         labels, metadata, created_at, updated_at
       ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8::text[], $9::jsonb, $10, $11)
       ON CONFLICT (agent_id) DO UPDATE SET
         display_name = EXCLUDED.display_name,
         owner = EXCLUDED.owner,
         runtime = EXCLUDED.runtime,
         environment = EXCLUDED.environment,
         risk_tier = EXCLUDED.risk_tier,
         status = EXCLUDED.status,
         labels = EXCLUDED.labels,
         metadata = EXCLUDED.metadata,
         updated_at = EXCLUDED.updated_at`,
      [
        agent.agent_id,
        agent.display_name,
        agent.owner,
        agent.runtime,
        agent.environment,
        agent.risk_tier,
        agent.status,
        agent.labels,
        JSON.stringify(agent.metadata),
        agent.created_at,
        agent.updated_at,
      ]
    );

    this.logger.info('Registered Fabric agent', { agent_id: agent.agent_id });
    return agent;
  }

  async listAgents(): Promise<FabricAgent[]> {
    const result = await this.pool.query<AgentRow>(
      `SELECT agent_id, display_name, owner, runtime, environment, risk_tier, status,
              labels, metadata, created_at, updated_at
       FROM stix_fabric_agents
       ORDER BY created_at ASC, agent_id ASC`
    );
    return result.rows.map((row) => this.toAgent(row));
  }

  async getAgent(agentId: string): Promise<FabricAgent | null> {
    const result = await this.pool.query<AgentRow>(
      `SELECT agent_id, display_name, owner, runtime, environment, risk_tier, status,
              labels, metadata, created_at, updated_at
       FROM stix_fabric_agents
       WHERE agent_id = $1`,
      [agentId]
    );
    return result.rows[0] ? this.toAgent(result.rows[0]) : null;
  }

  async createEnforcementPoint(input: CreateFabricEnforcementPointInput): Promise<FabricEnforcementPoint> {
    const now = new Date().toISOString();
    const enforcementPoint: FabricEnforcementPoint = {
      ...input,
      enforcement_point_id: input.enforcement_point_id ?? this.createId('ep'),
      agent_ids: input.agent_ids ?? [],
      metadata: input.metadata ?? {},
      created_at: now,
      updated_at: now,
    };

    await this.pool.query(
      `INSERT INTO stix_fabric_enforcement_points (
         enforcement_point_id, display_name, point_type, environment, status,
         url, agent_ids, metadata, created_at, updated_at
       ) VALUES ($1, $2, $3, $4, $5, $6, $7::text[], $8::jsonb, $9, $10)
       ON CONFLICT (enforcement_point_id) DO UPDATE SET
         display_name = EXCLUDED.display_name,
         point_type = EXCLUDED.point_type,
         environment = EXCLUDED.environment,
         status = EXCLUDED.status,
         url = EXCLUDED.url,
         agent_ids = EXCLUDED.agent_ids,
         metadata = EXCLUDED.metadata,
         updated_at = EXCLUDED.updated_at`,
      [
        enforcementPoint.enforcement_point_id,
        enforcementPoint.display_name,
        enforcementPoint.type,
        enforcementPoint.environment,
        enforcementPoint.status,
        enforcementPoint.url,
        enforcementPoint.agent_ids,
        JSON.stringify(enforcementPoint.metadata),
        enforcementPoint.created_at,
        enforcementPoint.updated_at,
      ]
    );

    this.logger.info('Registered Fabric enforcement point', {
      enforcement_point_id: enforcementPoint.enforcement_point_id,
    });
    return enforcementPoint;
  }

  async listEnforcementPoints(): Promise<FabricEnforcementPoint[]> {
    const result = await this.pool.query<EnforcementPointRow>(
      `SELECT enforcement_point_id, display_name, point_type AS type, environment, status,
              url, agent_ids, metadata, created_at, updated_at
       FROM stix_fabric_enforcement_points
       ORDER BY created_at ASC, enforcement_point_id ASC`
    );
    return result.rows.map((row) => this.toEnforcementPoint(row));
  }

  async getEnforcementPoint(enforcementPointId: string): Promise<FabricEnforcementPoint | null> {
    const result = await this.pool.query<EnforcementPointRow>(
      `SELECT enforcement_point_id, display_name, point_type AS type, environment, status,
              url, agent_ids, metadata, created_at, updated_at
       FROM stix_fabric_enforcement_points
       WHERE enforcement_point_id = $1`,
      [enforcementPointId]
    );
    return result.rows[0] ? this.toEnforcementPoint(result.rows[0]) : null;
  }

  async createToolAction(input: CreateFabricToolActionInput): Promise<FabricToolAction> {
    const now = new Date().toISOString();
    const toolAction: FabricToolAction = {
      ...input,
      action_id: input.action_id ?? this.createId('action'),
      metadata: input.metadata ?? {},
      created_at: now,
      updated_at: now,
    };

    await this.pool.query(
      `INSERT INTO stix_fabric_tool_actions (
         action_id, display_name, action_name, resource_type, risk_tier,
         approval_required, allowed_envs, metadata, created_at, updated_at
       ) VALUES ($1, $2, $3, $4, $5, $6, $7::text[], $8::jsonb, $9, $10)
       ON CONFLICT (action_id) DO UPDATE SET
         display_name = EXCLUDED.display_name,
         action_name = EXCLUDED.action_name,
         resource_type = EXCLUDED.resource_type,
         risk_tier = EXCLUDED.risk_tier,
         approval_required = EXCLUDED.approval_required,
         allowed_envs = EXCLUDED.allowed_envs,
         metadata = EXCLUDED.metadata,
         updated_at = EXCLUDED.updated_at`,
      [
        toolAction.action_id,
        toolAction.display_name,
        toolAction.action,
        toolAction.resource_type,
        toolAction.risk_tier,
        toolAction.approval_required,
        toolAction.allowed_environments,
        JSON.stringify(toolAction.metadata),
        toolAction.created_at,
        toolAction.updated_at,
      ]
    );

    this.logger.info('Registered Fabric tool action', { action_id: toolAction.action_id });
    return toolAction;
  }

  async listToolActions(): Promise<FabricToolAction[]> {
    const result = await this.pool.query<ToolActionRow>(
      `SELECT action_id, display_name, action_name AS action, resource_type, risk_tier,
              approval_required, allowed_envs, metadata, created_at, updated_at
       FROM stix_fabric_tool_actions
       ORDER BY created_at ASC, action_id ASC`
    );
    return result.rows.map((row) => this.toToolAction(row));
  }

  async getToolAction(actionId: string): Promise<FabricToolAction | null> {
    const result = await this.pool.query<ToolActionRow>(
      `SELECT action_id, display_name, action_name AS action, resource_type, risk_tier,
              approval_required, allowed_envs, metadata, created_at, updated_at
       FROM stix_fabric_tool_actions
       WHERE action_id = $1`,
      [actionId]
    );
    return result.rows[0] ? this.toToolAction(result.rows[0]) : null;
  }

  async createPolicyChannel(input: CreateFabricPolicyChannelInput): Promise<FabricPolicyChannel> {
    const now = new Date().toISOString();
    const channel: FabricPolicyChannel = {
      ...input,
      channel_id: input.channel_id ?? this.createId('channel'),
      metadata: input.metadata ?? {},
      created_at: now,
      updated_at: now,
    };

    await this.pool.query(
      `INSERT INTO stix_fabric_policy_channels (
         channel_id, display_name, environment, rollout_state, active_bundle_id,
         metadata, created_at, updated_at
       ) VALUES ($1, $2, $3, $4, $5, $6::jsonb, $7, $8)
       ON CONFLICT (channel_id) DO UPDATE SET
         display_name = EXCLUDED.display_name,
         environment = EXCLUDED.environment,
         rollout_state = EXCLUDED.rollout_state,
         active_bundle_id = EXCLUDED.active_bundle_id,
         metadata = EXCLUDED.metadata,
         updated_at = EXCLUDED.updated_at`,
      [
        channel.channel_id,
        channel.display_name,
        channel.environment,
        channel.rollout_state,
        channel.active_bundle_id,
        JSON.stringify(channel.metadata),
        channel.created_at,
        channel.updated_at,
      ]
    );

    this.logger.info('Registered Fabric policy channel', { channel_id: channel.channel_id });
    return channel;
  }

  async listPolicyChannels(): Promise<FabricPolicyChannel[]> {
    const result = await this.pool.query<PolicyChannelRow>(
      `SELECT channel_id, display_name, environment, rollout_state, active_bundle_id,
              metadata, created_at, updated_at
       FROM stix_fabric_policy_channels
       ORDER BY created_at ASC, channel_id ASC`
    );
    return result.rows.map((row) => this.toPolicyChannel(row));
  }

  async getPolicyChannel(channelId: string): Promise<FabricPolicyChannel | null> {
    const result = await this.pool.query<PolicyChannelRow>(
      `SELECT channel_id, display_name, environment, rollout_state, active_bundle_id,
              metadata, created_at, updated_at
       FROM stix_fabric_policy_channels
       WHERE channel_id = $1`,
      [channelId]
    );
    return result.rows[0] ? this.toPolicyChannel(result.rows[0]) : null;
  }

  async getStats(): Promise<FabricRegistryStats> {
    const [totalRes, activeAgentsRes, activePointsRes, criticalActionsRes] = await Promise.all([
      this.pool.query<{
        agents: string;
        enforcement_points: string;
        tool_actions: string;
        policy_channels: string;
      }>(`
        SELECT
          (SELECT COUNT(*)::text FROM stix_fabric_agents) AS agents,
          (SELECT COUNT(*)::text FROM stix_fabric_enforcement_points) AS enforcement_points,
          (SELECT COUNT(*)::text FROM stix_fabric_tool_actions) AS tool_actions,
          (SELECT COUNT(*)::text FROM stix_fabric_policy_channels) AS policy_channels
      `),
      this.pool.query<{ count: string }>(
        "SELECT COUNT(*)::text AS count FROM stix_fabric_agents WHERE status = 'ACTIVE'"
      ),
      this.pool.query<{ count: string }>(
        "SELECT COUNT(*)::text AS count FROM stix_fabric_enforcement_points WHERE status = 'ACTIVE'"
      ),
      this.pool.query<{ count: string }>(
        "SELECT COUNT(*)::text AS count FROM stix_fabric_tool_actions WHERE risk_tier = 'CRITICAL'"
      ),
    ]);

    const totals = totalRes.rows[0];
    return {
      agents: parseCount(totals?.agents),
      enforcement_points: parseCount(totals?.enforcement_points),
      tool_actions: parseCount(totals?.tool_actions),
      policy_channels: parseCount(totals?.policy_channels),
      active_agents: parseCount(activeAgentsRes.rows[0]?.count),
      active_enforcement_points: parseCount(activePointsRes.rows[0]?.count),
      critical_tool_actions: parseCount(criticalActionsRes.rows[0]?.count),
    };
  }

  async getGraphSummary(): Promise<FabricGraphSummary> {
    return buildGraphSummary(
      await this.listAgents(),
      await this.listEnforcementPoints(),
      await this.listToolActions(),
      await this.listPolicyChannels(),
      await this.getStats()
    );
  }

  async health(): Promise<boolean> {
    try {
      await this.pool.query('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }

  private createId(prefix: string): string {
    return `${prefix}_${randomUUID()}`;
  }

  private toAgent(row: AgentRow): FabricAgent {
    return {
      ...row,
      labels: row.labels ?? [],
      metadata: row.metadata ?? {},
      created_at: toIsoString(row.created_at),
      updated_at: toIsoString(row.updated_at),
    };
  }

  private toEnforcementPoint(row: EnforcementPointRow): FabricEnforcementPoint {
    return {
      ...row,
      agent_ids: row.agent_ids ?? [],
      metadata: row.metadata ?? {},
      created_at: toIsoString(row.created_at),
      updated_at: toIsoString(row.updated_at),
    };
  }

  private toToolAction(row: ToolActionRow): FabricToolAction {
    return {
      ...row,
      allowed_environments: row.allowed_envs ?? [],
      metadata: row.metadata ?? {},
      created_at: toIsoString(row.created_at),
      updated_at: toIsoString(row.updated_at),
    };
  }

  private toPolicyChannel(row: PolicyChannelRow): FabricPolicyChannel {
    return {
      ...row,
      metadata: row.metadata ?? {},
      created_at: toIsoString(row.created_at),
      updated_at: toIsoString(row.updated_at),
    };
  }
}

export async function createFabricStore(config: Config, logger: Logger): Promise<FabricStore> {
  switch (config.storage.type) {
    case 'memory':
      return new InMemoryFabricStore(logger);
    case 'postgres': {
      const store = new PostgresFabricStore(config, logger);
      await store.initialize();
      return store;
    }
  }
}

function createStats(
  agents: FabricAgent[],
  enforcementPoints: FabricEnforcementPoint[],
  toolActions: FabricToolAction[],
  policyChannels: number
): FabricRegistryStats {
  return {
    agents: agents.length,
    enforcement_points: enforcementPoints.length,
    tool_actions: toolActions.length,
    policy_channels: policyChannels,
    active_agents: agents.filter((agent) => agent.status === 'ACTIVE').length,
    active_enforcement_points: enforcementPoints.filter((point) => point.status === 'ACTIVE').length,
    critical_tool_actions: toolActions.filter((action) => action.risk_tier === 'CRITICAL').length,
  };
}

function buildGraphSummary(
  agents: FabricAgent[],
  enforcementPoints: FabricEnforcementPoint[],
  toolActions: FabricToolAction[],
  policyChannels: FabricPolicyChannel[],
  stats: FabricRegistryStats
): FabricGraphSummary {
  const nodes: FabricGraphSummary['nodes'] = [
    ...agents.map((agent) => ({
      id: agent.agent_id,
      type: 'agent' as const,
      label: agent.display_name,
      status: agent.status,
      risk_tier: agent.risk_tier,
    })),
    ...enforcementPoints.map((point) => ({
      id: point.enforcement_point_id,
      type: 'enforcement_point' as const,
      label: point.display_name,
      status: point.status,
    })),
    ...toolActions.map((action) => ({
      id: action.action_id,
      type: 'tool_action' as const,
      label: action.display_name,
      risk_tier: action.risk_tier,
    })),
    ...policyChannels.map((channel) => ({
      id: channel.channel_id,
      type: 'policy_channel' as const,
      label: channel.display_name,
      status: channel.rollout_state,
    })),
  ];

  const activeChannels = policyChannels.filter((channel) => channel.rollout_state === 'ACTIVE');
  const edges: FabricGraphSummary['edges'] = [];

  for (const point of enforcementPoints) {
    for (const agentId of point.agent_ids) {
      edges.push({ from: agentId, to: point.enforcement_point_id, relation: 'protected_by' });
    }
  }

  for (const agent of agents) {
    for (const action of toolActions) {
      if (action.allowed_environments.includes(agent.environment)) {
        edges.push({ from: agent.agent_id, to: action.action_id, relation: 'can_execute' });
      }
    }
    for (const channel of activeChannels.filter((item) => item.environment === agent.environment)) {
      edges.push({ from: agent.agent_id, to: channel.channel_id, relation: 'governed_by' });
    }
  }

  return { nodes, edges, stats };
}

function toIsoString(value: TimestampValue): string {
  return value instanceof Date ? value.toISOString() : new Date(value).toISOString();
}

function parseCount(value: string | undefined): number {
  return Number.parseInt(value ?? '0', 10);
}
