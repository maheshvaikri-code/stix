/**
 * STIX Fabric-aware Agent SDK helpers.
 *
 * These APIs let an agent join STIX Fabric, publish its tool surface, and keep
 * using STIX Core authorization through the existing wrapped-tool flow.
 */

import { request as undiciRequest, Dispatcher } from 'undici';
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
  FabricEnvironment,
} from '@stix/fabric-types';
import { StixClient } from './client';
import { ToolRegistry } from './tools';
import type {
  FailMode,
  Logger,
  StixClientConfig,
  ToolDefinition,
  WrappedTool,
  WrappedToolResult,
  Context,
} from './types';
import { StixError } from './types';

const DEFAULT_TIMEOUT_MS = 5000;
const DEFAULT_RETRIES = 3;

const noopLogger: Logger = {
  debug: () => {},
  info: () => {},
  warn: () => {},
  error: () => {},
};

export interface FabricClientConfig {
  /** Fabric service URL, for example http://localhost:3005. */
  fabricUrl: string;

  /** Optional service token for Fabric's x-stix-service-token auth. */
  serviceToken?: string;

  /** Request timeout in milliseconds. */
  timeout?: number;

  /** Number of retries on failure. */
  retries?: number;

  /** Custom logger. */
  logger?: Logger;
}

type FabricCollection<T> = {
  data: T[];
  total: number;
};

/** Client for STIX Fabric registry and graph APIs. */
export class FabricClient {
  private readonly fabricUrl: string;
  private readonly serviceToken?: string;
  private readonly timeout: number;
  private readonly retries: number;
  private readonly logger: Logger;

  constructor(config: FabricClientConfig) {
    this.fabricUrl = config.fabricUrl.replace(/\/$/, '');
    this.serviceToken = config.serviceToken;
    this.timeout = config.timeout ?? DEFAULT_TIMEOUT_MS;
    this.retries = config.retries ?? DEFAULT_RETRIES;
    this.logger = config.logger ?? noopLogger;
  }

  async registerAgent(input: CreateFabricAgentInput): Promise<FabricAgent> {
    return this.sendRequest('/api/v1/fabric/agents', input, 'POST');
  }

  async listAgents(): Promise<FabricAgent[]> {
    const response = await this.sendRequest<FabricCollection<FabricAgent>>('/api/v1/fabric/agents', undefined, 'GET');
    return response.data;
  }

  async getAgent(agentId: string): Promise<FabricAgent> {
    return this.sendRequest(`/api/v1/fabric/agents/${encodeURIComponent(agentId)}`, undefined, 'GET');
  }

  async registerEnforcementPoint(input: CreateFabricEnforcementPointInput): Promise<FabricEnforcementPoint> {
    return this.sendRequest('/api/v1/fabric/enforcement-points', input, 'POST');
  }

  async listEnforcementPoints(): Promise<FabricEnforcementPoint[]> {
    const response = await this.sendRequest<FabricCollection<FabricEnforcementPoint>>(
      '/api/v1/fabric/enforcement-points',
      undefined,
      'GET'
    );
    return response.data;
  }

  async getEnforcementPoint(enforcementPointId: string): Promise<FabricEnforcementPoint> {
    return this.sendRequest(
      `/api/v1/fabric/enforcement-points/${encodeURIComponent(enforcementPointId)}`,
      undefined,
      'GET'
    );
  }

  async registerToolAction(input: CreateFabricToolActionInput): Promise<FabricToolAction> {
    return this.sendRequest('/api/v1/fabric/tool-actions', input, 'POST');
  }

  async listToolActions(): Promise<FabricToolAction[]> {
    const response = await this.sendRequest<FabricCollection<FabricToolAction>>(
      '/api/v1/fabric/tool-actions',
      undefined,
      'GET'
    );
    return response.data;
  }

  async getToolAction(actionId: string): Promise<FabricToolAction> {
    return this.sendRequest(`/api/v1/fabric/tool-actions/${encodeURIComponent(actionId)}`, undefined, 'GET');
  }

  async registerPolicyChannel(input: CreateFabricPolicyChannelInput): Promise<FabricPolicyChannel> {
    return this.sendRequest('/api/v1/fabric/policy-channels', input, 'POST');
  }

  async listPolicyChannels(): Promise<FabricPolicyChannel[]> {
    const response = await this.sendRequest<FabricCollection<FabricPolicyChannel>>(
      '/api/v1/fabric/policy-channels',
      undefined,
      'GET'
    );
    return response.data;
  }

  async getPolicyChannel(channelId: string): Promise<FabricPolicyChannel> {
    return this.sendRequest(`/api/v1/fabric/policy-channels/${encodeURIComponent(channelId)}`, undefined, 'GET');
  }

  async getStats(): Promise<FabricRegistryStats> {
    return this.sendRequest('/api/v1/fabric/stats', undefined, 'GET');
  }

  async getGraphSummary(): Promise<FabricGraphSummary> {
    return this.sendRequest('/api/v1/fabric/graph/summary', undefined, 'GET');
  }

  async health(): Promise<{ healthy: boolean }> {
    try {
      await this.sendRequest('/health', undefined, 'GET');
      return { healthy: true };
    } catch {
      return { healthy: false };
    }
  }

  private async sendRequest<T>(
    path: string,
    body?: unknown,
    method: 'POST' | 'GET' = 'POST'
  ): Promise<T> {
    const headers: Record<string, string> = {
      Accept: 'application/json',
      'Content-Type': 'application/json',
    };

    if (this.serviceToken) {
      headers['x-stix-service-token'] = this.serviceToken;
    }

    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= this.retries; attempt++) {
      try {
        const response = await undiciRequest(`${this.fabricUrl}${path}`, {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
          bodyTimeout: this.timeout,
          headersTimeout: this.timeout,
        } as Dispatcher.RequestOptions);

        const data = await response.body.json() as T;
        if (response.statusCode >= 400) {
          throw new StixError(`Fabric request failed with status ${response.statusCode}`, 'FABRIC_REQUEST_FAILED', {
            status: response.statusCode,
            response: data,
          });
        }

        return data;
      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));
        if (attempt < this.retries) {
          const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
          this.logger.debug(`Fabric request failed, retrying in ${delay}ms`, {
            attempt: attempt + 1,
            maxRetries: this.retries,
            error: lastError.message,
          });
          await sleep(delay);
        }
      }
    }

    throw lastError ?? new Error('Fabric request failed');
  }
}

export interface FabricToolRegistrationOptions {
  /** Override Fabric action ID. Defaults to the wrapped tool name. */
  actionId?: string;

  /** Override Fabric display name. Defaults to the wrapped tool name. */
  displayName?: string;

  /** Whether this action usually requires human approval metadata. */
  approvalRequired?: boolean;

  /** Environments where this action may appear in Fabric graph edges. */
  allowedEnvironments?: FabricEnvironment[];

  /** Extra Fabric metadata. */
  metadata?: Record<string, unknown>;
}

export interface StixFabricAgentConfig {
  enforcerUrl: string;
  evidenceUrl?: string;
  approvalsUrl?: string;
  fabricUrl: string;
  apiKey?: string;
  serviceToken?: string;
  timeout?: number;
  retries?: number;
  failMode?: FailMode;
  debug?: boolean;
  logger?: Logger;
  defaultContext?: Partial<Context>;
  agent: CreateFabricAgentInput;
  enforcementPoint?: CreateFabricEnforcementPointInput | false;
  tools?: ToolDefinition[];
  registerOnCreate?: boolean;
}

export interface StixFabricAgentRuntime {
  stix: StixClient;
  fabric: FabricClient;
  registry: ToolRegistry;
  agent: FabricAgent;
  enforcementPoint?: FabricEnforcementPoint;
  toolActions: FabricToolAction[];
  registerTool<TArgs = unknown, TResult = unknown>(
    definition: ToolDefinition<TArgs, TResult>,
    options?: FabricToolRegistrationOptions
  ): Promise<WrappedTool<TArgs, TResult>>;
  execute<TArgs = unknown, TResult = unknown>(name: string, args: TArgs): Promise<WrappedToolResult<TResult>>;
  getGraphSummary(): Promise<FabricGraphSummary>;
}

export class StixFabricAgent implements StixFabricAgentRuntime {
  readonly registry: ToolRegistry;
  readonly toolActions: FabricToolAction[];

  constructor(
    readonly stix: StixClient,
    readonly fabric: FabricClient,
    readonly agent: FabricAgent,
    readonly enforcementPoint?: FabricEnforcementPoint,
    initialToolActions: FabricToolAction[] = []
  ) {
    this.registry = new ToolRegistry(stix);
    this.toolActions = [...initialToolActions];
  }

  async registerTool<TArgs = unknown, TResult = unknown>(
    definition: ToolDefinition<TArgs, TResult>,
    options: FabricToolRegistrationOptions = {}
  ): Promise<WrappedTool<TArgs, TResult>> {
    const action = await this.fabric.registerToolAction(toolDefinitionToFabricAction(definition, this.agent.environment, options));
    this.toolActions.push(action);
    return this.registry.register(definition);
  }

  async execute<TArgs = unknown, TResult = unknown>(name: string, args: TArgs): Promise<WrappedToolResult<TResult>> {
    return this.registry.execute<TArgs, TResult>(name, args);
  }

  async getGraphSummary(): Promise<FabricGraphSummary> {
    return this.fabric.getGraphSummary();
  }
}

/**
 * Create a Fabric-aware STIX agent runtime.
 *
 * This registers the agent, the SDK enforcement point, and optional tool action
 * metadata in Fabric, while using STIX Core for runtime authorization.
 */
export async function createStixAgent(config: StixFabricAgentConfig): Promise<StixFabricAgent> {
  const fabric = new FabricClient({
    fabricUrl: config.fabricUrl,
    serviceToken: config.serviceToken,
    timeout: config.timeout,
    retries: config.retries,
    logger: config.logger,
  });

  const shouldRegister = config.registerOnCreate ?? true;
  const agent = shouldRegister
    ? await fabric.registerAgent(config.agent)
    : agentFromConfig(config.agent);

  const stix = new StixClient({
    enforcerUrl: config.enforcerUrl,
    evidenceUrl: config.evidenceUrl,
    approvalsUrl: config.approvalsUrl,
    apiKey: config.apiKey,
    timeout: config.timeout,
    retries: config.retries,
    failMode: config.failMode,
    debug: config.debug,
    logger: config.logger,
    defaultActor: {
      id: agent.agent_id,
      type: 'AI_AGENT',
      attributes: {
        ...config.agent.metadata,
        stix_fabric_agent_id: agent.agent_id,
        owner: agent.owner,
        runtime: agent.runtime,
        risk_tier: agent.risk_tier,
        labels: agent.labels,
      },
    },
    defaultContext: {
      env: agent.environment,
      ...config.defaultContext,
    },
  } satisfies StixClientConfig);

  const enforcementPoint = shouldRegister && config.enforcementPoint !== false
    ? await fabric.registerEnforcementPoint(config.enforcementPoint ?? defaultEnforcementPoint(agent))
    : undefined;

  const runtime = new StixFabricAgent(stix, fabric, agent, enforcementPoint);

  for (const tool of config.tools ?? []) {
    if (shouldRegister) {
      await runtime.registerTool(tool);
    } else {
      runtime.registry.register(tool);
    }
  }

  return runtime;
}

export function createFabricClientFromEnv(overrides: Partial<FabricClientConfig> = {}): FabricClient {
  return new FabricClient({
    fabricUrl: process.env.STIX_FABRIC_URL ?? 'http://localhost:3005',
    serviceToken: process.env.STIX_SERVICE_TOKEN ?? process.env.STIX_FABRIC_SERVICE_TOKEN,
    ...overrides,
  });
}

export async function createStixAgentFromEnv(
  config: Omit<StixFabricAgentConfig, 'enforcerUrl' | 'fabricUrl' | 'apiKey' | 'serviceToken'> &
    Partial<Pick<StixFabricAgentConfig, 'enforcerUrl' | 'fabricUrl' | 'apiKey' | 'serviceToken'>>
): Promise<StixFabricAgent> {
  return createStixAgent({
    enforcerUrl: process.env.STIX_ENFORCER_URL ?? 'http://localhost:3001',
    fabricUrl: process.env.STIX_FABRIC_URL ?? 'http://localhost:3005',
    apiKey: process.env.STIX_API_KEY,
    serviceToken: process.env.STIX_SERVICE_TOKEN ?? process.env.STIX_FABRIC_SERVICE_TOKEN,
    ...config,
  });
}

function toolDefinitionToFabricAction<TArgs, TResult>(
  definition: ToolDefinition<TArgs, TResult>,
  environment: FabricEnvironment,
  options: FabricToolRegistrationOptions
): CreateFabricToolActionInput {
  const riskTier = definition.riskTier ?? 'MEDIUM';
  return {
    action_id: options.actionId ?? definition.name,
    display_name: options.displayName ?? definition.name,
    action: definition.action,
    resource_type: definition.resourceType,
    risk_tier: riskTier,
    approval_required: options.approvalRequired ?? (riskTier === 'HIGH' || riskTier === 'CRITICAL'),
    allowed_environments: options.allowedEnvironments ?? [environment],
    metadata: {
      description: definition.description,
      ...options.metadata,
    },
  };
}

function defaultEnforcementPoint(agent: FabricAgent): CreateFabricEnforcementPointInput {
  return {
    enforcement_point_id: `ep_${sanitizeId(agent.agent_id)}_sdk`,
    display_name: `${agent.display_name} SDK Enforcement`,
    type: 'sdk',
    environment: agent.environment,
    status: 'ACTIVE',
    agent_ids: [agent.agent_id],
    metadata: {
      runtime: agent.runtime,
      source: '@stix/agent-sdk',
    },
  };
}

function agentFromConfig(input: CreateFabricAgentInput): FabricAgent {
  if (!input.agent_id) {
    throw new StixError('registerOnCreate=false requires agent.agent_id', 'FABRIC_AGENT_ID_REQUIRED');
  }

  const now = new Date().toISOString();
  return {
    ...input,
    agent_id: input.agent_id,
    labels: input.labels ?? [],
    metadata: input.metadata ?? {},
    created_at: now,
    updated_at: now,
  };
}

function sanitizeId(value: string): string {
  return value.replace(/[^a-zA-Z0-9_-]/g, '_');
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}
