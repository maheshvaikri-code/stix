/**
 * STIX Agent SDK - Anthropic Integration
 * Wrap Anthropic Claude tool calls with STIX authorization
 */

import type { StixClient } from '../client';
import type {
  AuthorizationResult,
  RiskTier,
  Resource,
  Context,
} from '../types';

/**
 * Anthropic tool definition
 */
interface AnthropicTool {
  name: string;
  description: string;
  input_schema: {
    type: 'object';
    properties: Record<string, unknown>;
    required?: string[];
  };
}

/**
 * Anthropic tool use block
 */
interface AnthropicToolUse {
  type: 'tool_use';
  id: string;
  name: string;
  input: Record<string, unknown>;
}

/**
 * Anthropic tool result block
 */
interface AnthropicToolResult {
  type: 'tool_result';
  tool_use_id: string;
  content: string;
  is_error?: boolean;
}

/**
 * STIX-enhanced Anthropic tool definition
 */
export interface StixAnthropicTool {
  /** Anthropic tool definition */
  tool: AnthropicTool;

  /** STIX action name (defaults to tool name) */
  action?: string;

  /** Resource type for authorization */
  resourceType: string;

  /** Risk tier */
  riskTier?: RiskTier;

  /** Extract resource from input */
  getResource?: (input: Record<string, unknown>) => string | Resource;

  /** Extract context from input */
  getContext?: (input: Record<string, unknown>) => Partial<Context>;

  /** Execute the tool */
  execute: (input: Record<string, unknown>) => unknown | Promise<unknown>;
}

/**
 * Result from executing a STIX-wrapped Anthropic tool
 */
export interface StixAnthropicToolResult {
  /** Tool use ID */
  toolUseId: string;

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

  /** Formatted as Anthropic tool result block */
  toolResult: AnthropicToolResult;
}

/**
 * Create a STIX-wrapped Anthropic tool handler
 *
 * @example
 * ```typescript
 * const handler = createAnthropicToolHandler(stix, [
 *   {
 *     tool: {
 *       name: 'send_email',
 *       description: 'Send an email to a recipient',
 *       input_schema: {
 *         type: 'object',
 *         properties: {
 *           to: { type: 'string', description: 'Email address' },
 *           subject: { type: 'string' },
 *           body: { type: 'string' }
 *         },
 *         required: ['to', 'subject', 'body']
 *       }
 *     },
 *     resourceType: 'email',
 *     riskTier: 'MEDIUM',
 *     getResource: (input) => ({ type: 'email', id: input.to as string }),
 *     execute: async (input) => {
 *       await mailer.send(input.to, input.subject, input.body);
 *       return { sent: true };
 *     }
 *   }
 * ]);
 *
 * // In your message loop
 * const results = await handler.executeToolUses(content.filter(b => b.type === 'tool_use'));
 * ```
 */
export function createAnthropicToolHandler(
  client: StixClient,
  tools: StixAnthropicTool[]
): AnthropicToolHandler {
  return new AnthropicToolHandler(client, tools);
}

/**
 * Anthropic tool handler with STIX integration
 */
export class AnthropicToolHandler {
  private readonly toolMap = new Map<string, StixAnthropicTool>();

  constructor(
    private readonly client: StixClient,
    tools: StixAnthropicTool[]
  ) {
    for (const tool of tools) {
      this.toolMap.set(tool.tool.name, tool);
    }
  }

  /**
   * Get Anthropic tool definitions for message creation
   */
  getToolDefinitions(): AnthropicTool[] {
    return Array.from(this.toolMap.values()).map(t => t.tool);
  }

  /**
   * Execute a single tool use with STIX authorization
   */
  async executeToolUse(toolUse: AnthropicToolUse): Promise<StixAnthropicToolResult> {
    const tool = this.toolMap.get(toolUse.name);

    if (!tool) {
      return {
        toolUseId: toolUse.id,
        name: toolUse.name,
        allowed: false,
        authorization: {
          allowed: false,
          decision: 'DENY',
          traceId: 'unknown-tool',
          reasonCode: 'unknown_tool',
          explanation: `Tool ${toolUse.name} not found`,
          obligations: [],
          controls: [],
          regulations: [],
        },
        toolResult: {
          type: 'tool_result',
          tool_use_id: toolUse.id,
          content: JSON.stringify({ error: `Unknown tool: ${toolUse.name}` }),
          is_error: true,
        },
      };
    }

    // Build resource
    const resource = tool.getResource?.(toolUse.input) ?? tool.resourceType;

    // Request authorization
    const authorization = await this.client.authorize({
      action: tool.action ?? toolUse.name,
      resource: typeof resource === 'string' ? { type: resource } : resource,
      context: tool.getContext?.(toolUse.input),
      toolCall: {
        tool: toolUse.name,
        risk_tier: tool.riskTier,
        args_summary: summarizeInput(toolUse.input),
      },
    });

    if (!authorization.allowed) {
      return {
        toolUseId: toolUse.id,
        name: toolUse.name,
        allowed: false,
        authorization,
        toolResult: {
          type: 'tool_result',
          tool_use_id: toolUse.id,
          content: JSON.stringify({
            error: 'Authorization denied',
            reason: authorization.reasonCode,
            explanation: authorization.explanation,
          }),
          is_error: true,
        },
      };
    }

    // Execute the tool
    try {
      const result = await tool.execute(toolUse.input);

      // Record success
      await this.client.recordOutcome(authorization.traceId, 'SUCCESS');

      return {
        toolUseId: toolUse.id,
        name: toolUse.name,
        allowed: true,
        authorization,
        result,
        toolResult: {
          type: 'tool_result',
          tool_use_id: toolUse.id,
          content: typeof result === 'string' ? result : JSON.stringify(result),
        },
      };
    } catch (err) {
      const error = err instanceof Error ? err : new Error(String(err));

      // Record failure
      await this.client.recordOutcome(authorization.traceId, 'FAILED', {
        errorClass: error.name,
      });

      return {
        toolUseId: toolUse.id,
        name: toolUse.name,
        allowed: true,
        authorization,
        error,
        toolResult: {
          type: 'tool_result',
          tool_use_id: toolUse.id,
          content: JSON.stringify({ error: error.message }),
          is_error: true,
        },
      };
    }
  }

  /**
   * Execute multiple tool uses
   * Runs in parallel for efficiency
   */
  async executeToolUses(toolUses: AnthropicToolUse[]): Promise<StixAnthropicToolResult[]> {
    return Promise.all(toolUses.map(tu => this.executeToolUse(tu)));
  }

  /**
   * Get tool results formatted for Anthropic API
   */
  getToolResults(results: StixAnthropicToolResult[]): AnthropicToolResult[] {
    return results.map(r => r.toolResult);
  }
}

/**
 * Middleware for Anthropic Claude messages
 * Intercepts tool uses and applies STIX authorization
 *
 * @example
 * ```typescript
 * const anthropic = new Anthropic();
 * const stixMiddleware = createAnthropicMiddleware(stix, tools);
 *
 * let response = await anthropic.messages.create({
 *   model: 'claude-3-opus-20240229',
 *   messages,
 *   tools: stixMiddleware.getTools(),
 *   max_tokens: 1024,
 * });
 *
 * while (response.stop_reason === 'tool_use') {
 *   const toolUses = response.content.filter(b => b.type === 'tool_use');
 *   const results = await stixMiddleware.handleToolUses(toolUses);
 *
 *   messages.push({ role: 'assistant', content: response.content });
 *   messages.push({ role: 'user', content: results.toolResults });
 *
 *   response = await anthropic.messages.create({
 *     model: 'claude-3-opus-20240229',
 *     messages,
 *     tools: stixMiddleware.getTools(),
 *     max_tokens: 1024,
 *   });
 * }
 * ```
 */
export function createAnthropicMiddleware(
  client: StixClient,
  tools: StixAnthropicTool[]
): {
  getTools: () => AnthropicTool[];
  handleToolUses: (toolUses: AnthropicToolUse[]) => Promise<{
    results: StixAnthropicToolResult[];
    toolResults: AnthropicToolResult[];
  }>;
} {
  const handler = new AnthropicToolHandler(client, tools);

  return {
    getTools: () => handler.getToolDefinitions(),
    handleToolUses: async (toolUses: AnthropicToolUse[]) => {
      const results = await handler.executeToolUses(toolUses);
      const toolResults = handler.getToolResults(results);
      return { results, toolResults };
    },
  };
}

/**
 * Create a Claude computer use handler with STIX
 * Specifically for Claude's computer use capability
 */
export function createComputerUseHandler(
  client: StixClient,
  options: {
    /** Actions that require HIGH risk authorization */
    highRiskActions?: string[];
    /** Actions that are always denied */
    blockedActions?: string[];
    /** Execute computer action */
    execute: (action: string, params: Record<string, unknown>) => Promise<unknown>;
  }
): {
  handleComputerUse: (toolUse: AnthropicToolUse) => Promise<StixAnthropicToolResult>;
} {
  const highRisk = new Set(options.highRiskActions ?? ['click', 'type', 'key']);
  const blocked = new Set(options.blockedActions ?? []);

  return {
    async handleComputerUse(toolUse: AnthropicToolUse): Promise<StixAnthropicToolResult> {
      const action = toolUse.input.action as string;

      // Check blocked actions
      if (blocked.has(action)) {
        return {
          toolUseId: toolUse.id,
          name: toolUse.name,
          allowed: false,
          authorization: {
            allowed: false,
            decision: 'DENY',
            traceId: 'blocked-action',
            reasonCode: 'computer_action_blocked',
            explanation: `Computer action ${action} is blocked by policy`,
            obligations: [],
            controls: [],
            regulations: [],
          },
          toolResult: {
            type: 'tool_result',
            tool_use_id: toolUse.id,
            content: JSON.stringify({ error: `Action ${action} is blocked` }),
            is_error: true,
          },
        };
      }

      // Authorize
      const authorization = await client.authorize({
        action: `computer_${action}`,
        resource: {
          type: 'computer',
          id: 'display',
          attributes: toolUse.input,
        },
        toolCall: {
          tool: 'computer',
          risk_tier: highRisk.has(action) ? 'HIGH' : 'MEDIUM',
          args_summary: `action=${action}`,
        },
      });

      if (!authorization.allowed) {
        return {
          toolUseId: toolUse.id,
          name: toolUse.name,
          allowed: false,
          authorization,
          toolResult: {
            type: 'tool_result',
            tool_use_id: toolUse.id,
            content: JSON.stringify({
              error: 'Authorization denied',
              reason: authorization.reasonCode,
            }),
            is_error: true,
          },
        };
      }

      try {
        const result = await options.execute(action, toolUse.input);
        await client.recordOutcome(authorization.traceId, 'SUCCESS');

        return {
          toolUseId: toolUse.id,
          name: toolUse.name,
          allowed: true,
          authorization,
          result,
          toolResult: {
            type: 'tool_result',
            tool_use_id: toolUse.id,
            content: typeof result === 'string' ? result : JSON.stringify(result),
          },
        };
      } catch (err) {
        const error = err instanceof Error ? err : new Error(String(err));
        await client.recordOutcome(authorization.traceId, 'FAILED', {
          errorClass: error.name,
        });

        return {
          toolUseId: toolUse.id,
          name: toolUse.name,
          allowed: true,
          authorization,
          error,
          toolResult: {
            type: 'tool_result',
            tool_use_id: toolUse.id,
            content: JSON.stringify({ error: error.message }),
            is_error: true,
          },
        };
      }
    },
  };
}

function summarizeInput(input: Record<string, unknown>): string {
  const pairs: string[] = [];
  for (const [key, value] of Object.entries(input)) {
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
