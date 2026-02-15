/**
 * STIX Agent SDK - Tool Wrappers
 * Wrap any tool function with STIX authorization
 */

import type { StixClient } from './client';
import type {
  ToolDefinition,
  WrappedTool,
  WrappedToolResult,
  AuthorizationResult,
  AuthorizeParams,
  OutcomeStatus,
  Resource,
  Context,
  RiskTier,
} from './types';

import { AuthorizationDeniedError } from './types';

/**
 * Wrap a tool function with STIX authorization
 *
 * @example
 * ```typescript
 * const sendEmail = wrapTool(stix, {
 *   name: 'send_email',
 *   action: 'send_email',
 *   resourceType: 'email',
 *   riskTier: 'MEDIUM',
 *   getResource: (args) => ({ type: 'email', id: args.to }),
 *   execute: async (args) => {
 *     await mailer.send(args.to, args.subject, args.body);
 *     return { sent: true };
 *   }
 * });
 *
 * // Execute with authorization
 * const result = await sendEmail.execute({ to: 'user@example.com', subject: 'Hi' });
 * if (result.success) {
 *   console.log('Email sent!', result.result);
 * } else {
 *   console.log('Denied:', result.authorization.reasonCode);
 * }
 *
 * // Or throw on denial
 * const result = await sendEmail.executeOrThrow({ to: 'user@example.com', subject: 'Hi' });
 * ```
 */
export function wrapTool<TArgs = unknown, TResult = unknown>(
  client: StixClient,
  definition: ToolDefinition<TArgs, TResult>
): WrappedTool<TArgs, TResult> {
  return {
    name: definition.name,
    description: definition.description,

    async execute(args: TArgs): Promise<WrappedToolResult<TResult>> {
      // Build authorization params
      const authParams = buildAuthParams(definition, args);

      // Request authorization
      const authorization = await client.authorize(authParams);

      if (!authorization.allowed) {
        return {
          success: false,
          authorization,
          outcomeStatus: 'SKIPPED',
        };
      }

      // Execute the tool
      let result: TResult | undefined;
      let error: Error | undefined;
      let outcomeStatus: OutcomeStatus = 'SUCCESS';

      try {
        result = await definition.execute(args);
      } catch (err) {
        error = err instanceof Error ? err : new Error(String(err));
        outcomeStatus = 'FAILED';
      }

      // Record outcome
      await client.recordOutcome(authorization.traceId, outcomeStatus, {
        resultSummary: result ? 'Tool executed successfully' : undefined,
        errorClass: error?.name,
        obligationsApplied: buildObligationsApplied(authorization),
      });

      return {
        success: !error,
        authorization,
        result,
        error,
        outcomeStatus,
      };
    },

    async executeOrThrow(args: TArgs): Promise<TResult> {
      const result = await this.execute(args);

      if (!result.authorization.allowed) {
        throw new AuthorizationDeniedError(result.authorization);
      }

      if (result.error) {
        throw result.error;
      }

      return result.result as TResult;
    },

    async checkAuth(args: TArgs): Promise<AuthorizationResult> {
      const authParams = buildAuthParams(definition, args);
      return client.checkAuth(authParams);
    },
  };
}

/**
 * Create a tool registry for batch wrapping
 */
export function createToolRegistry(client: StixClient): ToolRegistry {
  return new ToolRegistry(client);
}

/**
 * Tool registry for managing multiple wrapped tools
 */
export class ToolRegistry {
  private readonly tools = new Map<string, WrappedTool>();

  constructor(private readonly client: StixClient) {}

  /**
   * Register a tool
   */
  register<TArgs = unknown, TResult = unknown>(
    definition: ToolDefinition<TArgs, TResult>
  ): WrappedTool<TArgs, TResult> {
    const wrapped = wrapTool(this.client, definition);
    this.tools.set(definition.name, wrapped as WrappedTool);
    return wrapped;
  }

  /**
   * Register multiple tools
   */
  registerAll(definitions: ToolDefinition[]): void {
    for (const def of definitions) {
      this.register(def);
    }
  }

  /**
   * Get a registered tool
   */
  get<TArgs = unknown, TResult = unknown>(
    name: string
  ): WrappedTool<TArgs, TResult> | undefined {
    return this.tools.get(name) as WrappedTool<TArgs, TResult> | undefined;
  }

  /**
   * Get all registered tools
   */
  getAll(): Map<string, WrappedTool> {
    return new Map(this.tools);
  }

  /**
   * Check if a tool is registered
   */
  has(name: string): boolean {
    return this.tools.has(name);
  }

  /**
   * Execute a tool by name
   */
  async execute<TArgs = unknown, TResult = unknown>(
    name: string,
    args: TArgs
  ): Promise<WrappedToolResult<TResult>> {
    const tool = this.get<TArgs, TResult>(name);
    if (!tool) {
      throw new Error(`Tool not found: ${name}`);
    }
    return tool.execute(args);
  }
}

/**
 * Decorator factory for class method tools
 *
 * @example
 * ```typescript
 * class MyAgent {
 *   @StixAuthorized({
 *     action: 'send_email',
 *     resourceType: 'email',
 *     riskTier: 'MEDIUM'
 *   })
 *   async sendEmail(to: string, subject: string) {
 *     // Implementation
 *   }
 * }
 * ```
 */
export function StixAuthorized(options: {
  action: string;
  resourceType: string;
  riskTier?: RiskTier;
  getResource?: (args: unknown[]) => string | Resource;
  getContext?: (args: unknown[]) => Partial<Context>;
  }) {
  return function (
    _target: unknown,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ): PropertyDescriptor {
    const originalMethod = descriptor.value;

    descriptor.value = async function (this: { stix?: StixClient }, ...args: unknown[]) {
      const client = (this as { stix?: StixClient }).stix;
      if (!client) {
        throw new Error(
          'StixClient not found on instance. Add a "stix" property to use @StixAuthorized.'
        );
      }

      const resource = options.getResource?.(args) ?? options.resourceType;
      const context = options.getContext?.(args);

      const result = await client.authorize({
        action: options.action,
        resource,
        context,
        toolCall: {
          tool: propertyKey,
          risk_tier: options.riskTier,
        },
      });

      if (!result.allowed) {
        throw new AuthorizationDeniedError(result);
      }

      try {
        const returnValue = await originalMethod.apply(this, args);
        await client.recordOutcome(result.traceId, 'SUCCESS');
        return returnValue;
      } catch (error) {
        await client.recordOutcome(result.traceId, 'FAILED', {
          errorClass: error instanceof Error ? error.name : 'Error',
        });
        throw error;
      }
    };

    return descriptor;
  };
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function buildAuthParams<TArgs>(
  definition: ToolDefinition<TArgs, unknown>,
  args: TArgs
): AuthorizeParams {
  const resource = definition.getResource?.(args) ?? definition.resourceType;
  const context = definition.getContext?.(args);
  const argsSummary = definition.summarizeArgs?.(args);

  return {
    action: definition.action,
    resource: typeof resource === 'string' ? { type: resource } : resource,
    context,
    toolCall: {
      tool: definition.name,
      risk_tier: definition.riskTier,
      args_summary: argsSummary,
    },
  };
}

function buildObligationsApplied(
  auth: AuthorizationResult
): Record<string, boolean> | undefined {
  if (auth.obligations.length === 0) {
    return undefined;
  }

  const applied: Record<string, boolean> = {};
  for (const obligation of auth.obligations) {
    // Mark all obligations as applied - caller should override if needed
    applied[obligation.type.toLowerCase()] = true;
  }
  return applied;
}

// =============================================================================
// COMMON TOOL FACTORIES
// =============================================================================

/**
 * Create a file operation tool
 */
export function createFileTool<TResult = unknown>(
  client: StixClient,
  options: {
    name: string;
    action: 'read' | 'write' | 'delete' | 'list';
    riskTier?: RiskTier;
    execute: (path: string, ...args: unknown[]) => TResult | Promise<TResult>;
  }
): WrappedTool<{ path: string; [key: string]: unknown }, TResult> {
  return wrapTool(client, {
    name: options.name,
    action: `file_${options.action}`,
    resourceType: 'file',
    riskTier: options.riskTier ?? (options.action === 'read' ? 'LOW' : 'MEDIUM'),
    getResource: (args) => ({
      type: 'file',
      id: args.path,
      attributes: { operation: options.action },
    }),
    summarizeArgs: (args) => `path=${args.path}`,
    execute: (args) => options.execute(args.path, ...Object.values(args).slice(1)),
  });
}

/**
 * Create a database query tool
 */
export function createDatabaseTool<TResult = unknown>(
  client: StixClient,
  options: {
    name: string;
    databaseType: 'postgres' | 'mysql' | 'sqlite' | 'mongodb';
    riskTier?: RiskTier;
    execute: (query: string, params?: unknown[]) => TResult | Promise<TResult>;
  }
): WrappedTool<{ query: string; params?: unknown[] }, TResult> {
  return wrapTool(client, {
    name: options.name,
    action: 'database_query',
    resourceType: 'database',
    riskTier: options.riskTier ?? 'MEDIUM',
    getResource: (args) => {
      // Extract table from query if possible
      const tableMatch = args.query.match(/(?:FROM|INTO|UPDATE)\s+(\w+)/i);
      return {
        type: 'database',
        id: options.databaseType,
        attributes: {
          table: tableMatch?.[1],
          queryType: detectQueryType(args.query),
        },
      };
    },
    summarizeArgs: (args) => {
      // Summarize query without sensitive data
      const queryType = detectQueryType(args.query);
      const tableMatch = args.query.match(/(?:FROM|INTO|UPDATE)\s+(\w+)/i);
      return `${queryType} on ${tableMatch?.[1] ?? 'unknown'}`;
    },
    execute: (args) => options.execute(args.query, args.params),
  });
}

/**
 * Create an HTTP request tool
 */
export function createHttpTool<TResult = unknown>(
  client: StixClient,
  options: {
    name: string;
    riskTier?: RiskTier;
    execute: (url: string, method: string, body?: unknown) => TResult | Promise<TResult>;
  }
): WrappedTool<{ url: string; method?: string; body?: unknown }, TResult> {
  return wrapTool(client, {
    name: options.name,
    action: 'http_request',
    resourceType: 'http',
    riskTier: options.riskTier ?? 'MEDIUM',
    getResource: (args) => {
      const url = new URL(args.url);
      return {
        type: 'http',
        id: url.hostname,
        attributes: {
          method: args.method ?? 'GET',
          path: url.pathname,
        },
      };
    },
    summarizeArgs: (args) => {
      try {
        const url = new URL(args.url);
        return `${args.method ?? 'GET'} ${url.hostname}${url.pathname}`;
      } catch {
        return `${args.method ?? 'GET'} ${args.url.substring(0, 50)}`;
      }
    },
    execute: (args) => options.execute(args.url, args.method ?? 'GET', args.body),
  });
}

/**
 * Create an email tool
 */
export function createEmailTool<TResult = unknown>(
  client: StixClient,
  options: {
    name: string;
    riskTier?: RiskTier;
    execute: (to: string, subject: string, body: string) => TResult | Promise<TResult>;
  }
): WrappedTool<{ to: string; subject: string; body: string }, TResult> {
  return wrapTool(client, {
    name: options.name,
    action: 'send_email',
    resourceType: 'email',
    riskTier: options.riskTier ?? 'MEDIUM',
    getResource: (args) => ({
      type: 'email',
      id: args.to,
      attributes: { domain: args.to.split('@')[1] },
    }),
    summarizeArgs: (args) => `to=${args.to} subject=${args.subject.substring(0, 30)}`,
    execute: (args) => options.execute(args.to, args.subject, args.body),
  });
}

function detectQueryType(query: string): string {
  const normalized = query.trim().toUpperCase();
  if (normalized.startsWith('SELECT')) return 'SELECT';
  if (normalized.startsWith('INSERT')) return 'INSERT';
  if (normalized.startsWith('UPDATE')) return 'UPDATE';
  if (normalized.startsWith('DELETE')) return 'DELETE';
  if (normalized.startsWith('CREATE')) return 'DDL';
  if (normalized.startsWith('DROP')) return 'DDL';
  if (normalized.startsWith('ALTER')) return 'DDL';
  return 'OTHER';
}
