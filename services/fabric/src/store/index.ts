/**
 * STIX Fabric registry store.
 *
 * The first Fabric milestone uses an in-memory registry for local development
 * and tests. The interface is intentionally shaped for a durable Postgres
 * implementation without changing routes.
 */

import { randomUUID } from 'node:crypto';
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

    return {
      agents: agents.length,
      enforcement_points: enforcementPoints.length,
      tool_actions: toolActions.length,
      policy_channels: this.policyChannels.size,
      active_agents: agents.filter((agent) => agent.status === 'ACTIVE').length,
      active_enforcement_points: enforcementPoints.filter((point) => point.status === 'ACTIVE').length,
      critical_tool_actions: toolActions.filter((action) => action.risk_tier === 'CRITICAL').length,
    };
  }

  async getGraphSummary(): Promise<FabricGraphSummary> {
    const agents = await this.listAgents();
    const enforcementPoints = await this.listEnforcementPoints();
    const toolActions = await this.listToolActions();
    const policyChannels = await this.listPolicyChannels();
    const stats = await this.getStats();

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

export async function createFabricStore(logger: Logger): Promise<FabricStore> {
  return new InMemoryFabricStore(logger);
}
