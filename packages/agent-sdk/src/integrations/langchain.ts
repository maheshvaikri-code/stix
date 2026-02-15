/**
 * STIX Agent SDK - LangChain Integration
 * Wrap LangChain tools with STIX authorization
 */

import type { StixClient } from '../client';
import type {
  AuthorizationResult,
  RiskTier,
  Resource,
  Context,
} from '../types';
import { AuthorizationDeniedError } from '../types';

/**
 * LangChain-compatible tool interface
 * Matches @langchain/core StructuredTool
 */
interface LangChainTool {
  name: string;
  description: string;
  schema?: unknown;
  invoke(input: unknown, config?: unknown): Promise<unknown>;
}

/**
 * LangChain tool call from agent
 */
interface LangChainToolCall {
  name: string;
  args: Record<string, unknown>;
  id?: string;
}

/**
 * STIX configuration for a LangChain tool
 */
export interface StixToolConfig {
  /** STIX action name (defaults to tool name) */
  action?: string;

  /** Resource type for authorization */
  resourceType: string;

  /** Risk tier */
  riskTier?: RiskTier;

  /** Extract resource from args */
  getResource?: (args: Record<string, unknown>) => string | Resource;

  /** Extract context from args */
  getContext?: (args: Record<string, unknown>) => Partial<Context>;
}

/**
 * Wrapped LangChain tool with STIX authorization
 */
export interface StixLangChainTool extends LangChainTool {
  /** Original unwrapped tool */
  readonly originalTool: LangChainTool;

  /** STIX configuration */
  readonly stixConfig: StixToolConfig;

  /** Check authorization without invoking */
  checkAuth(args: Record<string, unknown>): Promise<AuthorizationResult>;
}

/**
 * Result from STIX-wrapped tool execution
 */
export interface StixToolInvocationResult {
  /** Tool name */
  name: string;

  /** Tool call ID (if provided) */
  callId?: string;

  /** Whether execution was allowed */
  allowed: boolean;

  /** Authorization result */
  authorization: AuthorizationResult;

  /** Execution result (if allowed) */
  result?: unknown;

  /** Error (if denied or failed) */
  error?: Error;
}

/**
 * Wrap a LangChain tool with STIX authorization
 *
 * @example
 * ```typescript
 * import { DuckDuckGoSearchRun } from '@langchain/community/tools/duckduckgo_search';
 *
 * const searchTool = new DuckDuckGoSearchRun();
 *
 * const wrappedSearch = wrapLangChainTool(stix, searchTool, {
 *   resourceType: 'search',
 *   riskTier: 'LOW',
 * });
 *
 * // Use in LangChain agent
 * const agent = createReactAgent({
 *   llm,
 *   tools: [wrappedSearch],
 *   prompt,
 * });
 * ```
 */
export function wrapLangChainTool(
  client: StixClient,
  tool: LangChainTool,
  config: StixToolConfig
): StixLangChainTool {
  const wrappedTool: StixLangChainTool = {
    name: tool.name,
    description: tool.description,
    schema: tool.schema,
    originalTool: tool,
    stixConfig: config,

    async invoke(input: unknown, runConfig?: unknown): Promise<unknown> {
      const args = typeof input === 'object' && input !== null
        ? input as Record<string, unknown>
        : { input };

      // Build resource
      const resource = config.getResource?.(args) ?? config.resourceType;

      // Request authorization
      const authorization = await client.authorize({
        action: config.action ?? tool.name,
        resource: typeof resource === 'string' ? { type: resource } : resource,
        context: config.getContext?.(args),
        toolCall: {
          tool: tool.name,
          risk_tier: config.riskTier,
          args_summary: summarizeArgs(args),
        },
      });

      if (!authorization.allowed) {
        throw new AuthorizationDeniedError(authorization);
      }

      // Execute original tool
      try {
        const result = await tool.invoke(input, runConfig);
        await client.recordOutcome(authorization.traceId, 'SUCCESS');
        return result;
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        await client.recordOutcome(authorization.traceId, 'FAILED', {
          errorClass: error.name,
        });
        throw error;
      }
    },

    async checkAuth(args: Record<string, unknown>): Promise<AuthorizationResult> {
      const resource = config.getResource?.(args) ?? config.resourceType;
      return client.checkAuth({
        action: config.action ?? tool.name,
        resource: typeof resource === 'string' ? { type: resource } : resource,
        context: config.getContext?.(args),
        toolCall: {
          tool: tool.name,
          risk_tier: config.riskTier,
        },
      });
    },
  };

  return wrappedTool;
}

/**
 * Wrap multiple LangChain tools with STIX authorization
 */
export function wrapLangChainTools(
  client: StixClient,
  tools: Array<{ tool: LangChainTool; config: StixToolConfig }>
): StixLangChainTool[] {
  return tools.map(({ tool, config }) => wrapLangChainTool(client, tool, config));
}

/**
 * Create a STIX tool executor for LangChain agents
 * Handles authorization and outcome recording automatically
 *
 * @example
 * ```typescript
 * const executor = createStixToolExecutor(stix, {
 *   tools: [
 *     { tool: searchTool, config: { resourceType: 'search', riskTier: 'LOW' } },
 *     { tool: emailTool, config: { resourceType: 'email', riskTier: 'MEDIUM' } },
 *   ],
 *   onDenied: (toolName, reason) => {
 *     console.log(`Tool ${toolName} denied: ${reason}`);
 *   }
 * });
 *
 * // Execute tool calls from agent
 * const results = await executor.executeToolCalls(agentAction.toolCalls);
 * ```
 */
export function createStixToolExecutor(
  client: StixClient,
  options: {
    tools: Array<{ tool: LangChainTool; config: StixToolConfig }>;
    onDenied?: (toolName: string, reasonCode: string) => void;
    onError?: (toolName: string, error: Error) => void;
  }
): StixToolExecutor {
  return new StixToolExecutor(client, options);
}

/**
 * STIX tool executor for LangChain agents
 */
export class StixToolExecutor {
  private readonly toolMap = new Map<string, StixLangChainTool>();

  constructor(
    _client: StixClient,
    private readonly options: {
      tools: Array<{ tool: LangChainTool; config: StixToolConfig }>;
      onDenied?: (toolName: string, reasonCode: string) => void;
      onError?: (toolName: string, error: Error) => void;
    }
  ) {
    const wrapped = wrapLangChainTools(_client, options.tools);
    for (const tool of wrapped) {
      this.toolMap.set(tool.name, tool);
    }
  }

  /**
   * Get all wrapped tools for agent initialization
   */
  getTools(): StixLangChainTool[] {
    return Array.from(this.toolMap.values());
  }

  /**
   * Execute a single tool call
   */
  async executeToolCall(toolCall: LangChainToolCall): Promise<StixToolInvocationResult> {
    const tool = this.toolMap.get(toolCall.name);

    if (!tool) {
      return {
        name: toolCall.name,
        callId: toolCall.id,
        allowed: false,
        authorization: {
          allowed: false,
          decision: 'DENY',
          traceId: 'unknown-tool',
          reasonCode: 'unknown_tool',
          explanation: `Tool ${toolCall.name} not found`,
          obligations: [],
          controls: [],
          regulations: [],
        },
        error: new Error(`Unknown tool: ${toolCall.name}`),
      };
    }

    try {
      const result = await tool.invoke(toolCall.args);
      return {
        name: toolCall.name,
        callId: toolCall.id,
        allowed: true,
        authorization: {
          allowed: true,
          decision: 'ALLOW',
          traceId: 'executed',
          reasonCode: 'allowed',
          obligations: [],
          controls: [],
          regulations: [],
        },
        result,
      };
    } catch (err) {
      if (err instanceof AuthorizationDeniedError) {
        this.options.onDenied?.(toolCall.name, err.result.reasonCode);
        return {
          name: toolCall.name,
          callId: toolCall.id,
          allowed: false,
          authorization: err.result,
          error: err,
        };
      }

      const error = err instanceof Error ? err : new Error(String(err));
      this.options.onError?.(toolCall.name, error);
      return {
        name: toolCall.name,
        callId: toolCall.id,
        allowed: true,
        authorization: {
          allowed: true,
          decision: 'ALLOW',
          traceId: 'executed-failed',
          reasonCode: 'allowed_but_failed',
          obligations: [],
          controls: [],
          regulations: [],
        },
        error,
      };
    }
  }

  /**
   * Execute multiple tool calls
   */
  async executeToolCalls(toolCalls: LangChainToolCall[]): Promise<StixToolInvocationResult[]> {
    return Promise.all(toolCalls.map(tc => this.executeToolCall(tc)));
  }
}

/**
 * Create a STIX callback handler for LangChain
 * Logs all tool invocations to STIX evidence
 */
export function createStixCallbackHandler(client: StixClient): StixCallbackHandler {
  return new StixCallbackHandler(client);
}

/**
 * LangChain callback handler for STIX integration
 * Provides observability into agent execution
 */
export class StixCallbackHandler {
  private runIdMap = new Map<string, string>();

  constructor(_client: StixClient) {
    void _client;
  }

  /**
   * Called when a chain starts
   */
  async handleChainStart(
    _chain: { name?: string },
    _inputs: Record<string, unknown>,
    runId: string
  ): Promise<void> {
    this.runIdMap.set(runId, Date.now().toString());
  }

  /**
   * Called when a tool starts
   */
  async handleToolStart(
    _tool: { name: string },
    _input: string,
    _runId: string,
    _parentRunId?: string
  ): Promise<void> {
    // Tool start is logged when authorization is requested
  }

  /**
   * Called when a tool ends
   */
  async handleToolEnd(
    _output: string,
    _runId: string
  ): Promise<void> {
    // Tool end is logged as outcome in the wrapped tool
  }

  /**
   * Called when a tool errors
   */
  async handleToolError(
    _error: Error,
    _runId: string
  ): Promise<void> {
    // Tool error is logged as outcome in the wrapped tool
  }

  /**
   * Called when a chain ends
   */
  async handleChainEnd(
    _outputs: Record<string, unknown>,
    runId: string
  ): Promise<void> {
    this.runIdMap.delete(runId);
  }

  /**
   * Called when a chain errors
   */
  async handleChainError(
    _error: Error,
    runId: string
  ): Promise<void> {
    this.runIdMap.delete(runId);
  }
}

/**
 * Create a STIX-aware agent executor factory
 * Use this to create LangChain agents with built-in STIX authorization
 *
 * @example
 * ```typescript
 * const createAgent = createStixAgentFactory(stix);
 *
 * const agent = createAgent({
 *   llm: new ChatOpenAI(),
 *   tools: [
 *     { tool: searchTool, config: { resourceType: 'search' } },
 *     { tool: calculatorTool, config: { resourceType: 'calculator' } },
 *   ],
 *   prompt: hubPrompt,
 * });
 *
 * // Agent automatically checks STIX authorization before each tool use
 * await agent.invoke({ input: 'Search for AI news' });
 * ```
 */
export function createStixAgentFactory(client: StixClient) {
  return function createAgent(options: {
    llm: unknown;
    tools: Array<{ tool: LangChainTool; config: StixToolConfig }>;
    prompt: unknown;
    createAgentFn: (params: {
      llm: unknown;
      tools: LangChainTool[];
      prompt: unknown;
    }) => unknown;
    createExecutorFn: (params: {
      agent: unknown;
      tools: LangChainTool[];
    }) => unknown;
  }) {
    const wrappedTools = wrapLangChainTools(client, options.tools);

    const agent = options.createAgentFn({
      llm: options.llm,
      tools: wrappedTools,
      prompt: options.prompt,
    });

    return options.createExecutorFn({
      agent,
      tools: wrappedTools,
    });
  };
}

function summarizeArgs(args: Record<string, unknown>): string {
  const pairs: string[] = [];
  for (const [key, value] of Object.entries(args)) {
    if (typeof value === 'string' && value.length > 50) {
      pairs.push(`${key}=${value.substring(0, 47)}...`);
    } else if (typeof value === 'object') {
      pairs.push(`${key}=[object]`);
    } else {
      pairs.push(`${key}=${String(value)}`);
    }
  }
  return pairs.join(' ').substring(0, 200);
}
