/**
 * STIX Agent SDK - OpenAI Integration
 * Wrap OpenAI function calls with STIX authorization
 */

import type { StixClient } from '../client';
import type {
  AuthorizationResult,
  RiskTier,
  Resource,
  Context,
} from '../types';

/**
 * OpenAI tool definition (from openai SDK)
 */
interface OpenAITool {
  type: 'function';
  function: {
    name: string;
    description?: string;
    parameters?: Record<string, unknown>;
  };
}

/**
 * OpenAI tool call (from chat completion response)
 */
interface OpenAIToolCall {
  id: string;
  type: 'function';
  function: {
    name: string;
    arguments: string;
  };
}

/**
 * STIX-enhanced OpenAI tool definition
 */
export interface StixOpenAITool {
  /** OpenAI tool definition */
  tool: OpenAITool;

  /** STIX action name (defaults to function name) */
  action?: string;

  /** Resource type for authorization */
  resourceType: string;

  /** Risk tier */
  riskTier?: RiskTier;

  /** Extract resource from parsed arguments */
  getResource?: (args: Record<string, unknown>) => string | Resource;

  /** Extract context from parsed arguments */
  getContext?: (args: Record<string, unknown>) => Partial<Context>;

  /** Execute the tool */
  execute: (args: Record<string, unknown>) => unknown | Promise<unknown>;
}

/**
 * Result from executing a STIX-wrapped OpenAI tool
 */
export interface StixToolCallResult {
  /** Tool call ID */
  toolCallId: string;

  /** Tool name */
  name: string;

  /** Whether execution was allowed */
  allowed: boolean;

  /** Authorization result */
  authorization: AuthorizationResult;

  /** Execution result (if allowed and successful) */
  result?: unknown;

  /** Error (if execution failed) */
  error?: Error;

  /** Formatted result for OpenAI messages */
  formattedResult: string;
}

/**
 * Create a STIX-wrapped OpenAI tool handler
 *
 * @example
 * ```typescript
 * const handler = createOpenAIToolHandler(stix, [
 *   {
 *     tool: {
 *       type: 'function',
 *       function: {
 *         name: 'send_email',
 *         description: 'Send an email',
 *         parameters: {
 *           type: 'object',
 *           properties: {
 *             to: { type: 'string' },
 *             subject: { type: 'string' },
 *             body: { type: 'string' }
 *           },
 *           required: ['to', 'subject', 'body']
 *         }
 *       }
 *     },
 *     resourceType: 'email',
 *     riskTier: 'MEDIUM',
 *     getResource: (args) => ({ type: 'email', id: args.to as string }),
 *     execute: async (args) => {
 *       await mailer.send(args.to, args.subject, args.body);
 *       return { sent: true };
 *     }
 *   }
 * ]);
 *
 * // In your chat completion loop
 * const results = await handler.executeToolCalls(message.tool_calls);
 * ```
 */
export function createOpenAIToolHandler(
  client: StixClient,
  tools: StixOpenAITool[]
): OpenAIToolHandler {
  return new OpenAIToolHandler(client, tools);
}

/**
 * OpenAI tool handler with STIX integration
 */
export class OpenAIToolHandler {
  private readonly toolMap = new Map<string, StixOpenAITool>();

  constructor(
    private readonly client: StixClient,
    tools: StixOpenAITool[]
  ) {
    for (const tool of tools) {
      this.toolMap.set(tool.tool.function.name, tool);
    }
  }

  /**
   * Get OpenAI tool definitions for chat completion
   */
  getToolDefinitions(): OpenAITool[] {
    return Array.from(this.toolMap.values()).map(t => t.tool);
  }

  /**
   * Execute a single tool call with STIX authorization
   */
  async executeToolCall(toolCall: OpenAIToolCall): Promise<StixToolCallResult> {
    const tool = this.toolMap.get(toolCall.function.name);

    if (!tool) {
      return {
        toolCallId: toolCall.id,
        name: toolCall.function.name,
        allowed: false,
        authorization: {
          allowed: false,
          decision: 'DENY',
          traceId: 'unknown-tool',
          reasonCode: 'unknown_tool',
          explanation: `Tool ${toolCall.function.name} not found`,
          obligations: [],
          controls: [],
          regulations: [],
        },
        formattedResult: JSON.stringify({
          error: `Unknown tool: ${toolCall.function.name}`
        }),
      };
    }

    // Parse arguments
    let args: Record<string, unknown>;
    try {
      args = JSON.parse(toolCall.function.arguments);
    } catch {
      return {
        toolCallId: toolCall.id,
        name: toolCall.function.name,
        allowed: false,
        authorization: {
          allowed: false,
          decision: 'DENY',
          traceId: 'invalid-args',
          reasonCode: 'invalid_arguments',
          explanation: 'Failed to parse tool arguments',
          obligations: [],
          controls: [],
          regulations: [],
        },
        formattedResult: JSON.stringify({
          error: 'Invalid tool arguments'
        }),
      };
    }

    // Build resource
    const resource = tool.getResource?.(args) ?? tool.resourceType;

    // Request authorization
    const authorization = await this.client.authorize({
      action: tool.action ?? toolCall.function.name,
      resource: typeof resource === 'string' ? { type: resource } : resource,
      context: tool.getContext?.(args),
      toolCall: {
        tool: toolCall.function.name,
        risk_tier: tool.riskTier,
        args_summary: summarizeArgs(args),
      },
    });

    if (!authorization.allowed) {
      return {
        toolCallId: toolCall.id,
        name: toolCall.function.name,
        allowed: false,
        authorization,
        formattedResult: JSON.stringify({
          error: 'Authorization denied',
          reason: authorization.reasonCode,
          explanation: authorization.explanation,
        }),
      };
    }

    // Execute the tool
    try {
      const result = await tool.execute(args);

      // Record success
      await this.client.recordOutcome(authorization.traceId, 'SUCCESS');

      return {
        toolCallId: toolCall.id,
        name: toolCall.function.name,
        allowed: true,
        authorization,
        result,
        formattedResult: JSON.stringify(result),
      };
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));

      // Record failure
      await this.client.recordOutcome(authorization.traceId, 'FAILED', {
        errorClass: error.name,
      });

      return {
        toolCallId: toolCall.id,
        name: toolCall.function.name,
        allowed: true,
        authorization,
        error,
        formattedResult: JSON.stringify({
          error: error.message,
        }),
      };
    }
  }

  /**
   * Execute multiple tool calls
   * Runs in parallel for efficiency
   */
  async executeToolCalls(toolCalls: OpenAIToolCall[]): Promise<StixToolCallResult[]> {
    return Promise.all(toolCalls.map(tc => this.executeToolCall(tc)));
  }

  /**
   * Format results as OpenAI tool messages
   */
  formatAsMessages(results: StixToolCallResult[]): OpenAIToolMessage[] {
    return results.map(r => ({
      role: 'tool' as const,
      tool_call_id: r.toolCallId,
      content: r.formattedResult,
    }));
  }
}

/**
 * OpenAI tool message format
 */
interface OpenAIToolMessage {
  role: 'tool';
  tool_call_id: string;
  content: string;
}

/**
 * Middleware for OpenAI chat completions
 * Intercepts tool calls and applies STIX authorization
 *
 * @example
 * ```typescript
 * const openai = new OpenAI();
 * const stixMiddleware = createOpenAIMiddleware(stix, tools);
 *
 * // Use with chat completions
 * let response = await openai.chat.completions.create({
 *   model: 'gpt-4',
 *   messages,
 *   tools: stixMiddleware.getTools(),
 * });
 *
 * while (response.choices[0].finish_reason === 'tool_calls') {
 *   const toolCalls = response.choices[0].message.tool_calls;
 *   const results = await stixMiddleware.handleToolCalls(toolCalls);
 *
 *   messages.push(response.choices[0].message);
 *   messages.push(...results.messages);
 *
 *   response = await openai.chat.completions.create({
 *     model: 'gpt-4',
 *     messages,
 *     tools: stixMiddleware.getTools(),
 *   });
 * }
 * ```
 */
export function createOpenAIMiddleware(
  client: StixClient,
  tools: StixOpenAITool[]
): {
  getTools: () => OpenAITool[];
  handleToolCalls: (toolCalls: OpenAIToolCall[]) => Promise<{
    results: StixToolCallResult[];
    messages: OpenAIToolMessage[];
  }>;
} {
  const handler = new OpenAIToolHandler(client, tools);

  return {
    getTools: () => handler.getToolDefinitions(),
    handleToolCalls: async (toolCalls: OpenAIToolCall[]) => {
      const results = await handler.executeToolCalls(toolCalls);
      const messages = handler.formatAsMessages(results);
      return { results, messages };
    },
  };
}

/**
 * Create STIX-wrapped tools from OpenAI tool definitions
 * Convenience factory for common patterns
 */
export function wrapOpenAITools(
  client: StixClient,
  tools: Array<{
    definition: OpenAITool;
    resourceType: string;
    riskTier?: RiskTier;
    execute: (args: Record<string, unknown>) => unknown | Promise<unknown>;
  }>
): OpenAIToolHandler {
  const stixTools: StixOpenAITool[] = tools.map(t => ({
    tool: t.definition,
    resourceType: t.resourceType,
    riskTier: t.riskTier,
    execute: t.execute,
  }));

  return new OpenAIToolHandler(client, stixTools);
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
