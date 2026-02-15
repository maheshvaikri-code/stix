/**
 * STIX Agent SDK
 * Client library for AI agent integration with STIX
 * 
 * Provides a simple, type-safe interface for agents to:
 * - Request authorization for actions
 * - Handle ALLOW/DENY/QUARANTINE decisions
 * - Apply obligations
 * - Report outcomes
 * 
 * @module @stix/agent-sdk
 */

import {
  type AuthorizeRequest,
  type AuthorizeResponse,
  type Actor,
  type Resource,
  type Context,
  type Environment,
  type RiskTier,
  type Obligation,
  type DecisionKind,
  type OutcomeStatus,
  type Logger,
  createLoggerFromEnv,
  retry,
  withTimeout,
  HEADERS,
  TIMEOUTS,
  SERVICE_URLS,
  AuthorizationDeniedError,
  AuthorizationQuarantinedError,
  ServiceUnavailableError,
  MissingStixTokenError,
} from '@stix/shared';

// =============================================================================
// CONFIGURATION
// =============================================================================

export interface StixClientConfig {
  /** STIX Enforcer URL */
  enforcerUrl?: string;
  /** Optional API key for enforcer authentication */
  apiKey?: string;
  /** Default actor information */
  defaultActor?: Partial<Actor>;
  /** Default environment */
  defaultEnv?: Environment;
  /** Timeout in milliseconds */
  timeout?: number;
  /** Retry configuration */
  retry?: {
    maxAttempts?: number;
    initialDelayMs?: number;
  };
  /** Fail mode when STIX is unavailable */
  failMode?: 'CLOSED' | 'OPEN_LOW_RISK_ONLY' | 'OPEN';
  /** Custom logger */
  logger?: Logger;
  /** Enable debug logging */
  debug?: boolean;
}

// =============================================================================
// SDK TYPES
// =============================================================================

export interface AuthorizeOptions {
  /** Actor override */
  actor?: Actor;
  /** Action to perform */
  action: string;
  /** Resource being accessed */
  resource: Resource;
  /** Context */
  context?: Partial<Context>;
  /** Tool call metadata */
  toolCall?: {
    tool: string;
    riskTier?: RiskTier;
    argsSummary?: string;
  };
}

export interface AuthorizationDecision {
  /** Decision outcome */
  decision: DecisionKind;
  /** Whether the action is allowed */
  allowed: boolean;
  /** Whether action is denied */
  denied: boolean;
  /** Whether action requires approval */
  requiresApproval: boolean;
  /** Trace ID for correlation */
  traceId: string;
  /** Reason code */
  reasonCode: string;
  /** Human-readable explanation */
  explanation?: string;
  /** Obligations to apply (for ALLOW) */
  obligations: Obligation[];
  /** Proof token (for ALLOW) */
  proofToken?: string;
  /** Approval ticket ID (for QUARANTINE) */
  approvalTicketId?: string;
  /** Approval expiration */
  approvalExpiresAt?: string;
  /** Raw response */
  raw: AuthorizeResponse;
}

export interface OutcomeOptions {
  /** Trace ID from authorization */
  traceId: string;
  /** Outcome status */
  status: OutcomeStatus;
  /** Result summary */
  resultSummary?: string;
  /** Error class if failed */
  errorClass?: string;
  /** Which obligations were applied */
  obligationsApplied?: Record<string, boolean>;
}

export type ActionExecutor<T> = () => Promise<T>;

export interface ExecuteOptions<T> extends AuthorizeOptions {
  /** The action to execute */
  execute: ActionExecutor<T>;
  /** Callback when authorization is denied */
  onDenied?: (decision: AuthorizationDecision) => void;
  /** Callback when approval is required */
  onQuarantined?: (decision: AuthorizationDecision) => Promise<boolean>;
  /** Auto-record outcome */
  recordOutcome?: boolean;
}

// =============================================================================
// STIX CLIENT
// =============================================================================

export class StixClient {
  private readonly config: Required<StixClientConfig>;
  private readonly logger: Logger;

  constructor(config: StixClientConfig = {}) {
    this.config = {
      enforcerUrl: config.enforcerUrl ?? process.env.STIX_ENFORCER_URL ?? SERVICE_URLS.ENFORCER,
      apiKey: config.apiKey ?? process.env.STIX_API_KEY ?? '',
      defaultActor: config.defaultActor ?? {},
      defaultEnv: config.defaultEnv ?? (process.env.NODE_ENV as Environment) ?? 'dev',
      timeout: config.timeout ?? TIMEOUTS.SERVICE_REQUEST,
      retry: {
        maxAttempts: config.retry?.maxAttempts ?? 3,
        initialDelayMs: config.retry?.initialDelayMs ?? 100,
      },
      failMode: config.failMode ?? 'CLOSED',
      logger: config.logger ?? createLoggerFromEnv('stix-agent-sdk'),
      debug: config.debug ?? false,
    };

    this.logger = this.config.logger;

    if (this.config.debug) {
      this.logger.debug('STIX Client initialized', {
        enforcer_url: this.config.enforcerUrl,
        fail_mode: this.config.failMode,
      });
    }
  }

  /**
   * Request authorization for an action
   */
  async authorize(options: AuthorizeOptions): Promise<AuthorizationDecision> {
    const request = this.buildRequest(options);

    this.logger.debug('Requesting authorization', {
      action: request.action,
      resource_type: request.resource.type,
    });

    try {
      const response = await this.doAuthorize(request);
      return this.buildDecision(response);
    } catch (error) {
      return this.handleAuthorizationError(error as Error, request);
    }
  }

  /**
   * Execute an action with automatic authorization and outcome recording
   */
  async execute<T>(options: ExecuteOptions<T>): Promise<T> {
    // Step 1: Authorize
    const decision = await this.authorize(options);

    // Step 2: Handle decision
    if (decision.denied) {
      options.onDenied?.(decision);
      throw new AuthorizationDeniedError(
        decision.reasonCode,
        decision.explanation ?? 'Action denied'
      );
    }

    if (decision.requiresApproval) {
      // Call the quarantine callback if provided
      if (options.onQuarantined) {
        const shouldContinue = await options.onQuarantined(decision);
        if (!shouldContinue) {
          throw new AuthorizationQuarantinedError(
            decision.approvalTicketId ?? 'unknown',
            decision.explanation ?? 'Requires approval'
          );
        }
      } else {
        throw new AuthorizationQuarantinedError(
          decision.approvalTicketId ?? 'unknown',
          decision.explanation ?? 'Requires approval'
        );
      }
    }

    // Step 3: Execute action
    let result: T;
    let status: OutcomeStatus = 'SUCCESS';
    let errorClass: string | undefined;
    let resultSummary: string | undefined;

    try {
      result = await options.execute();
      resultSummary = typeof result === 'string' ? result.substring(0, 200) : 'Completed';
    } catch (error) {
      status = 'FAILED';
      errorClass = (error as Error).name;
      
      // Re-throw after recording outcome
      if (options.recordOutcome !== false) {
        await this.recordOutcome({
          traceId: decision.traceId,
          status,
          errorClass,
        }).catch(() => {}); // Ignore errors in outcome recording
      }
      throw error;
    }

    // Step 4: Record outcome
    if (options.recordOutcome !== false) {
      await this.recordOutcome({
        traceId: decision.traceId,
        status,
        resultSummary,
        obligationsApplied: this.checkObligations(decision.obligations),
      }).catch(() => {}); // Ignore errors in outcome recording
    }

    return result;
  }

  /**
   * Record execution outcome
   */
  async recordOutcome(options: OutcomeOptions): Promise<void> {
    this.logger.debug('Recording outcome', {
      trace_id: options.traceId,
      status: options.status,
    });

    try {
      await retry(
        async () => {
          return withTimeout(
            this.doRecordOutcome(options),
            this.config.timeout
          );
        },
        {
          maxAttempts: this.config.retry.maxAttempts,
          initialDelayMs: this.config.retry.initialDelayMs,
        }
      );
    } catch (error) {
      // Log but don't throw - outcome recording is best-effort
      this.logger.warn('Failed to record outcome', {
        trace_id: options.traceId,
        error: (error as Error).message,
      });
    }
  }

  /**
   * Check if a proof token is valid for a request
   */
  async verifyToken(token: string, resource: Resource): Promise<boolean> {
    // This would verify the token locally or with the enforcer
    // For now, return true if token exists
    return !!token;
  }

  /**
   * Create a child client with merged configuration
   */
  child(config: Partial<StixClientConfig>): StixClient {
    return new StixClient({
      ...this.config,
      ...config,
      defaultActor: { ...this.config.defaultActor, ...config.defaultActor },
    });
  }

  /**
   * Build authorization request
   */
  private buildRequest(options: AuthorizeOptions): AuthorizeRequest {
    const actor: Actor = {
      id: options.actor?.id ?? this.config.defaultActor.id ?? 'unknown',
      type: options.actor?.type ?? this.config.defaultActor.type ?? 'AI_AGENT',
      role: options.actor?.role ?? this.config.defaultActor.role,
      tenant: options.actor?.tenant ?? this.config.defaultActor.tenant,
      attributes: {
        ...this.config.defaultActor.attributes,
        ...options.actor?.attributes,
      },
    };

    const context: Context = {
      env: options.context?.env ?? this.config.defaultEnv,
      purpose: options.context?.purpose,
      run_id: options.context?.run_id,
      session_id: options.context?.session_id,
      ticket_id: options.context?.ticket_id,
      jurisdiction: options.context?.jurisdiction,
      tags: options.context?.tags,
      signals: options.context?.signals,
      attributes: options.context?.attributes,
    };

    return {
      actor,
      action: options.action,
      resource: options.resource,
      context,
      tool_call: options.toolCall ? {
        tool: options.toolCall.tool,
        risk_tier: options.toolCall.riskTier,
        args_summary: options.toolCall.argsSummary,
      } : undefined,
    };
  }

  /**
   * Build decision from response
   */
  private buildDecision(response: AuthorizeResponse): AuthorizationDecision {
    return {
      decision: response.decision,
      allowed: response.decision === 'ALLOW',
      denied: response.decision === 'DENY',
      requiresApproval: response.decision === 'QUARANTINE',
      traceId: response.trace_id,
      reasonCode: response.reason_code,
      explanation: response.explanation,
      obligations: response.obligations,
      proofToken: response.proof_token,
      approvalTicketId: response.approval?.ticket_id,
      approvalExpiresAt: response.approval?.expires_at,
      raw: response,
    };
  }

  /**
   * Perform authorization request
   */
  private async doAuthorize(request: AuthorizeRequest): Promise<AuthorizeResponse> {
    return retry(
      async () => {
        return withTimeout(
          this.fetchAuthorize(request),
          this.config.timeout
        );
      },
      {
        maxAttempts: this.config.retry.maxAttempts,
        initialDelayMs: this.config.retry.initialDelayMs,
      }
    );
  }

  /**
   * Fetch authorization from enforcer
   */
  private async fetchAuthorize(request: AuthorizeRequest): Promise<AuthorizeResponse> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.config.apiKey) {
      headers[HEADERS.API_KEY] = this.config.apiKey;
    }

    const response = await fetch(`${this.config.enforcerUrl}/api/v1/authorize`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ message: 'Unknown error' }));
      throw new Error(`Authorization request failed: ${error.message ?? response.statusText}`);
    }

    return response.json() as Promise<AuthorizeResponse>;
  }

  /**
   * Record outcome to enforcer
   */
  private async doRecordOutcome(options: OutcomeOptions): Promise<void> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };
    if (this.config.apiKey) {
      headers[HEADERS.API_KEY] = this.config.apiKey;
    }

    const response = await fetch(`${this.config.enforcerUrl}/api/v1/outcome`, {
      method: 'POST',
      headers,
      body: JSON.stringify({
        trace_id: options.traceId,
        status: options.status,
        result_summary: options.resultSummary,
        error_class: options.errorClass,
        obligations_applied: options.obligationsApplied,
      }),
    });

    if (!response.ok) {
      throw new Error(`Outcome recording failed: ${response.statusText}`);
    }
  }

  /**
   * Handle authorization error based on fail mode
   */
  private handleAuthorizationError(
    error: Error,
    request: AuthorizeRequest
  ): AuthorizationDecision {
    this.logger.warn('Authorization error, applying fail mode', {
      fail_mode: this.config.failMode,
      error: error.message,
    });

    // Create a synthetic decision based on fail mode
    const baseDecision: AuthorizationDecision = {
      decision: 'DENY',
      allowed: false,
      denied: true,
      requiresApproval: false,
      traceId: `fail_${Date.now()}`,
      reasonCode: 'STIX_UNAVAILABLE',
      explanation: `STIX unavailable: ${error.message}`,
      obligations: [],
      raw: {
        decision: 'DENY',
        reason_code: 'STIX_UNAVAILABLE',
        trace_id: `fail_${Date.now()}`,
        policy: { id: 'fail_mode', version: '1.0.0', hash: 'sha256:' + '0'.repeat(64) },
        obligations: [],
        approval: null,
      },
    };

    switch (this.config.failMode) {
      case 'OPEN':
        baseDecision.decision = 'ALLOW';
        baseDecision.allowed = true;
        baseDecision.denied = false;
        baseDecision.reasonCode = 'FAIL_OPEN';
        baseDecision.raw.decision = 'ALLOW';
        baseDecision.raw.reason_code = 'FAIL_OPEN';
        break;

      case 'OPEN_LOW_RISK_ONLY':
        const riskTier = request.tool_call?.risk_tier ?? 'HIGH';
        if (riskTier === 'LOW') {
          baseDecision.decision = 'ALLOW';
          baseDecision.allowed = true;
          baseDecision.denied = false;
          baseDecision.reasonCode = 'FAIL_OPEN_LOW_RISK';
          baseDecision.raw.decision = 'ALLOW';
          baseDecision.raw.reason_code = 'FAIL_OPEN_LOW_RISK';
        }
        break;

      case 'CLOSED':
      default:
        // Keep as DENY
        break;
    }

    return baseDecision;
  }

  /**
   * Check which obligations were applied
   */
  private checkObligations(obligations: Obligation[]): Record<string, boolean> {
    const applied: Record<string, boolean> = {};
    for (const obligation of obligations) {
      // In a real implementation, you would track which obligations were actually applied
      applied[obligation.type] = true;
    }
    return applied;
  }
}

// =============================================================================
// MIDDLEWARE HELPERS
// =============================================================================

/**
 * Create a tool wrapper that enforces STIX authorization
 */
export function withStix<T extends (...args: any[]) => Promise<any>>(
  client: StixClient,
  tool: string,
  riskTier: RiskTier,
  handler: T
): T {
  return (async (...args: Parameters<T>): Promise<ReturnType<T>> => {
    return client.execute({
      action: tool,
      resource: { type: 'tool', id: tool },
      toolCall: {
        tool,
        riskTier,
        argsSummary: JSON.stringify(args).substring(0, 200),
      },
      execute: () => handler(...args),
    });
  }) as T;
}

/**
 * Decorator for STIX-protected methods
 */
export function stixProtected(
  tool: string,
  riskTier: RiskTier
) {
  return function (
    target: any,
    propertyKey: string,
    descriptor: PropertyDescriptor
  ) {
    const originalMethod = descriptor.value;
    
    descriptor.value = async function (...args: any[]) {
      const client: StixClient = (this as any).stixClient;
      if (!client) {
        throw new Error('StixClient not found on class instance');
      }
      
      return client.execute({
        action: tool,
        resource: { type: 'tool', id: tool },
        toolCall: { tool, riskTier },
        execute: () => originalMethod.apply(this, args),
      });
    };
    
    return descriptor;
  };
}

// =============================================================================
// EXPORTS
// =============================================================================

export {
  // Re-export types from shared
  type AuthorizeRequest,
  type AuthorizeResponse,
  type Actor,
  type Resource,
  type Context,
  type Environment,
  type RiskTier,
  type Obligation,
  type DecisionKind,
  type OutcomeStatus,
  
  // Re-export errors
  AuthorizationDeniedError,
  AuthorizationQuarantinedError,
  MissingStixTokenError,
  
  // Re-export constants
  HEADERS,
} from '@stix/shared';
