/**
 * STIX Agent SDK Client
 * Core client for STIX authorization and evidence recording
 */

import { request as undiciRequest, Dispatcher } from 'undici';
import type {
  AuthorizeRequest,
  AuthorizeResponse,
  OutcomeRequest,
  Actor,
  Context,
  Resource,
} from '@stix/shared';

import type {
  StixClientConfig,
  AuthorizeParams,
  AuthorizationResult,
  Logger,
  ApprovalRequest,
  ApprovalPollOptions,
  ApprovalStatus,
} from './types';

import {
  StixError,
  AuthorizationDeniedError,
  ApprovalTimeoutError,
  ServiceUnavailableError,
  FailModeTriggeredError,
} from './types';

/**
 * Default configuration values
 */
const DEFAULTS = {
  timeout: 5000,
  retries: 3,
  failMode: 'CLOSED' as const,
  approvalTimeout: 300000, // 5 minutes
  approvalPollInterval: 5000, // 5 seconds
};

/**
 * Console logger implementation
 */
const consoleLogger: Logger = {
  debug: (msg, meta) => console.debug(`[STIX] ${msg}`, meta ?? ''),
  info: (msg, meta) => console.info(`[STIX] ${msg}`, meta ?? ''),
  warn: (msg, meta) => console.warn(`[STIX] ${msg}`, meta ?? ''),
  error: (msg, meta) => console.error(`[STIX] ${msg}`, meta ?? ''),
};

/**
 * No-op logger for silent mode
 */
const noopLogger: Logger = {
  debug: () => {},
  info: () => {},
  warn: () => {},
  error: () => {},
};

/**
 * STIX Client - Main entry point for STIX integration
 *
 * @example
 * ```typescript
 * const stix = new StixClient({
 *   enforcerUrl: 'https://stix-enforcer.internal:8080',
 *   apiKey: process.env.STIX_API_KEY,
 *   defaultActor: {
 *     id: 'agent-001',
 *     type: 'AI_AGENT',
 *     role: 'data-processor'
 *   },
 *   defaultContext: {
 *     env: 'prod',
 *     run_id: crypto.randomUUID()
 *   }
 * });
 *
 * const result = await stix.authorize({
 *   action: 'send_email',
 *   resource: { type: 'email', id: 'customer@example.com' }
 * });
 *
 * if (result.allowed) {
 *   await sendEmail(...);
 *   await stix.recordOutcome(result.traceId, 'SUCCESS');
 * }
 * ```
 */
export class StixClient {
  private readonly config: Required<Omit<StixClientConfig, 'certPath' | 'keyPath' | 'caPath' | 'apiKey' | 'telemetry' | 'logger' | 'defaultActor' | 'defaultContext'>> & Pick<StixClientConfig, 'certPath' | 'keyPath' | 'caPath' | 'apiKey' | 'telemetry' | 'logger' | 'defaultActor' | 'defaultContext'>;
  private readonly logger: Logger;

  constructor(config: StixClientConfig) {
    this.config = {
      enforcerUrl: config.enforcerUrl.replace(/\/$/, ''),
      evidenceUrl: config.evidenceUrl?.replace(/\/$/, '') ?? config.enforcerUrl.replace(/\/$/, ''),
      approvalsUrl: config.approvalsUrl?.replace(/\/$/, '') ?? config.enforcerUrl.replace(/\/$/, ''),
      timeout: config.timeout ?? DEFAULTS.timeout,
      retries: config.retries ?? DEFAULTS.retries,
      failMode: config.failMode ?? DEFAULTS.failMode,
      debug: config.debug ?? false,
      apiKey: config.apiKey,
      certPath: config.certPath,
      keyPath: config.keyPath,
      caPath: config.caPath,
      defaultActor: config.defaultActor,
      defaultContext: config.defaultContext,
      logger: config.logger,
      telemetry: config.telemetry,
    };

    this.logger = config.logger ?? (config.debug ? consoleLogger : noopLogger);
  }

  /**
   * Request authorization for an action
   *
   * @param params - Authorization parameters
   * @returns Authorization result
   */
  async authorize(params: AuthorizeParams): Promise<AuthorizationResult> {
    const startTime = Date.now();
    const request = this.buildAuthRequest(params);

    this.logger.debug('Requesting authorization', {
      action: request.action,
      resource: request.resource.type,
      actor: request.actor.id
    });

    this.config.telemetry?.onAuthorizationStart?.(request);

    try {
      const response = await this.sendRequest<AuthorizeResponse>(
        `${this.config.enforcerUrl}/v1/authorize`,
        request
      );

      const result = this.mapToResult(response);
      const durationMs = Date.now() - startTime;

      this.logger.info('Authorization complete', {
        decision: result.decision,
        traceId: result.traceId,
        durationMs
      });

      this.config.telemetry?.onAuthorizationComplete?.(request, response, durationMs);

      // Handle approval waiting if requested
      if (result.decision === 'QUARANTINE' && params.waitForApproval) {
        return this.waitForApproval(result, {
          timeout: params.approvalTimeout ?? DEFAULTS.approvalTimeout,
          interval: params.approvalPollInterval ?? DEFAULTS.approvalPollInterval,
        });
      }

      return result;

    } catch (error) {
      const durationMs = Date.now() - startTime;

      if (error instanceof StixError) {
        throw error;
      }

      const err = error instanceof Error ? error : new Error(String(error));
      this.logger.error('Authorization failed', { error: err.message, durationMs });
      this.config.telemetry?.onAuthorizationError?.(request, err, durationMs);

      // Handle fail mode
      return this.handleFailMode(request, err);
    }
  }

  /**
   * Check authorization without waiting for approval
   * Convenience method for pre-flight checks
   */
  async checkAuth(params: AuthorizeParams): Promise<AuthorizationResult> {
    return this.authorize({ ...params, waitForApproval: false });
  }

  /**
   * Authorize and throw if denied
   * Convenience method for simple use cases
   */
  async authorizeOrThrow(params: AuthorizeParams): Promise<AuthorizationResult> {
    const result = await this.authorize(params);
    if (!result.allowed) {
      throw new AuthorizationDeniedError(result);
    }
    return result;
  }

  /**
   * Record execution outcome for evidence
   *
   * @param traceId - Trace ID from authorization
   * @param status - Execution outcome status
   * @param details - Additional outcome details
   */
  async recordOutcome(
    traceId: string,
    status: OutcomeRequest['status'],
    details?: {
      resultSummary?: string;
      errorClass?: string;
      obligationsApplied?: Record<string, boolean>;
    }
  ): Promise<void> {
    this.logger.debug('Recording outcome', { traceId, status });

    try {
      await this.sendRequest<{ success: boolean }>(
        `${this.config.evidenceUrl}/v1/outcome`,
        {
          trace_id: traceId,
          status,
          result_summary: details?.resultSummary,
          error_class: details?.errorClass,
          obligations_applied: details?.obligationsApplied,
        } satisfies OutcomeRequest
      );

      this.config.telemetry?.onOutcomeRecorded?.(traceId, status);
      this.logger.info('Outcome recorded', { traceId, status });

    } catch (error) {
      // Log but don't throw - evidence recording shouldn't break the app
      const err = error instanceof Error ? error : new Error(String(error));
      this.logger.warn('Failed to record outcome', { traceId, error: err.message });
    }
  }

  /**
   * Get approval request status
   */
  async getApprovalStatus(ticketId: string): Promise<ApprovalRequest> {
    const response = await this.sendRequest<{ data: ApprovalRequest }>(
      `${this.config.approvalsUrl}/v1/approvals/${ticketId}`,
      undefined,
      'GET'
    );
    return response.data;
  }

  /**
   * Poll for approval until resolved or timeout
   */
  async waitForApproval(
    result: AuthorizationResult,
    options: ApprovalPollOptions = {}
  ): Promise<AuthorizationResult> {
    if (result.decision !== 'QUARANTINE' || !result.approvalTicketId) {
      return result;
    }

    const timeout = options.timeout ?? DEFAULTS.approvalTimeout;
    const interval = options.interval ?? DEFAULTS.approvalPollInterval;
    const deadline = Date.now() + timeout;
    let previousStatus: ApprovalStatus | undefined;

    this.logger.info('Waiting for approval', {
      ticketId: result.approvalTicketId,
      timeout
    });

    while (Date.now() < deadline) {
      // Check for abort
      if (options.signal?.aborted) {
        throw new StixError('Approval wait aborted', 'APPROVAL_ABORTED');
      }

      const approval = await this.getApprovalStatus(result.approvalTicketId);

      // Notify status change
      if (approval.status !== previousStatus) {
        options.onStatusChange?.(approval.status);
        this.config.telemetry?.onApprovalStatusChange?.(
          result.traceId,
          approval.status,
          previousStatus
        );
        previousStatus = approval.status;
      }

      // Check resolution
      if (approval.status === 'approved') {
        this.logger.info('Approval granted', { ticketId: result.approvalTicketId });

        // Re-authorize to get proof token
        return {
          ...result,
          allowed: true,
          decision: 'ALLOW',
          reasonCode: 'approved_by_human',
          proofToken: undefined, // Would be fetched from approval response in full impl
        };
      }

      if (approval.status === 'denied') {
        this.logger.info('Approval denied', { ticketId: result.approvalTicketId });
        return {
          ...result,
          allowed: false,
          decision: 'DENY',
          reasonCode: 'denied_by_approver',
        };
      }

      if (approval.status === 'expired' || approval.status === 'cancelled') {
        this.logger.info('Approval expired/cancelled', {
          ticketId: result.approvalTicketId,
          status: approval.status
        });
        return {
          ...result,
          allowed: false,
          decision: 'DENY',
          reasonCode: `approval_${approval.status}`,
        };
      }

      // Wait before next poll
      await this.sleep(interval);
    }

    throw new ApprovalTimeoutError(result.traceId, result.approvalTicketId);
  }

  /**
   * Health check
   */
  async health(): Promise<{ healthy: boolean; services: Record<string, boolean> }> {
    const results: Record<string, boolean> = {};

    try {
      await this.sendRequest(`${this.config.enforcerUrl}/health`, undefined, 'GET');
      results.enforcer = true;
    } catch {
      results.enforcer = false;
    }

    return {
      healthy: Object.values(results).every(Boolean),
      services: results,
    };
  }

  // ==========================================================================
  // PRIVATE METHODS
  // ==========================================================================

  private buildAuthRequest(params: AuthorizeParams): AuthorizeRequest {
    // Build actor
    const actor: Actor = {
      id: params.actor?.id ?? this.config.defaultActor?.id ?? 'unknown',
      type: params.actor?.type ?? this.config.defaultActor?.type ?? 'AI_AGENT',
      role: params.actor?.role ?? this.config.defaultActor?.role,
      tenant: params.actor?.tenant ?? this.config.defaultActor?.tenant,
      attributes: {
        ...this.config.defaultActor?.attributes,
        ...params.actor?.attributes,
      },
    };

    // Build resource
    const resource: Resource = typeof params.resource === 'string'
      ? { type: params.resource }
      : params.resource;

    // Build context
    const context: Context = {
      env: params.context?.env ?? this.config.defaultContext?.env ?? 'prod',
      purpose: params.context?.purpose ?? this.config.defaultContext?.purpose,
      run_id: params.context?.run_id ?? this.config.defaultContext?.run_id,
      session_id: params.context?.session_id ?? this.config.defaultContext?.session_id,
      ticket_id: params.context?.ticket_id ?? this.config.defaultContext?.ticket_id,
      jurisdiction: params.context?.jurisdiction ?? this.config.defaultContext?.jurisdiction,
      tags: [
        ...(this.config.defaultContext?.tags ?? []),
        ...(params.context?.tags ?? []),
      ],
      signals: {
        ...this.config.defaultContext?.signals,
        ...params.context?.signals,
      },
      attributes: {
        ...this.config.defaultContext?.attributes,
        ...params.context?.attributes,
      },
    };

    return {
      actor,
      action: params.action,
      resource,
      context,
      tool_call: params.toolCall ? {
        tool: params.toolCall.tool ?? params.action,
        risk_tier: params.toolCall.risk_tier,
        args_summary: params.toolCall.args_summary,
      } : undefined,
    };
  }

  private mapToResult(response: AuthorizeResponse): AuthorizationResult {
    return {
      allowed: response.decision === 'ALLOW',
      decision: response.decision,
      traceId: response.trace_id,
      reasonCode: response.reason_code,
      explanation: response.explanation,
      obligations: response.obligations,
      proofToken: response.proof_token,
      approvalRequired: response.decision === 'QUARANTINE' && response.approval?.required,
      approvalTicketId: response.approval?.ticket_id,
      controls: response.controls ?? [],
      regulations: response.regulations ?? [],
    };
  }

  private async handleFailMode(
    request: AuthorizeRequest,
    originalError: Error
  ): Promise<AuthorizationResult> {
    const riskTier = request.tool_call?.risk_tier;

    switch (this.config.failMode) {
      case 'OPEN':
        // Allow all actions when STIX is unavailable
        this.logger.warn('STIX unavailable, fail-open allowing action', {
          action: request.action,
          riskTier,
        });
        return {
          allowed: true,
          decision: 'ALLOW',
          traceId: `fail-open-${Date.now()}`,
          reasonCode: 'stix_unavailable_fail_open',
          obligations: [],
          controls: [],
          regulations: [],
        };

      case 'OPEN_LOW_RISK_ONLY':
        // Allow only low-risk actions when STIX is unavailable
        if (riskTier === 'LOW' || !riskTier) {
          this.logger.warn('STIX unavailable, fail-open allowing low-risk action', {
            action: request.action,
            riskTier,
          });
          return {
            allowed: true,
            decision: 'ALLOW',
            traceId: `fail-open-${Date.now()}`,
            reasonCode: 'stix_unavailable_low_risk_allowed',
            obligations: [],
            controls: [],
            regulations: [],
          };
        }
        throw new FailModeTriggeredError('OPEN_LOW_RISK_ONLY', riskTier);

      case 'CLOSED':
      default:
        // Deny all actions when STIX is unavailable
        throw new ServiceUnavailableError('enforcer', originalError);
    }
  }

  private async sendRequest<T>(
    url: string,
    body?: unknown,
    method: 'POST' | 'GET' = 'POST'
  ): Promise<T> {
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    };

    if (this.config.apiKey) {
      headers['Authorization'] = `Bearer ${this.config.apiKey}`;
    }

    let lastError: Error | undefined;

    for (let attempt = 0; attempt <= this.config.retries; attempt++) {
      try {
        const response = await undiciRequest(url, {
          method,
          headers,
          body: body ? JSON.stringify(body) : undefined,
          bodyTimeout: this.config.timeout,
          headersTimeout: this.config.timeout,
        } as Dispatcher.RequestOptions);

        const data = await response.body.json() as T;

        if (response.statusCode >= 400) {
          throw new StixError(
            `Request failed with status ${response.statusCode}`,
            'REQUEST_FAILED',
            { status: response.statusCode, response: data }
          );
        }

        return data;

      } catch (error) {
        lastError = error instanceof Error ? error : new Error(String(error));

        if (attempt < this.config.retries) {
          const delay = Math.min(1000 * Math.pow(2, attempt), 10000);
          this.logger.debug(`Request failed, retrying in ${delay}ms`, {
            attempt: attempt + 1,
            maxRetries: this.config.retries,
            error: lastError.message,
          });
          await this.sleep(delay);
        }
      }
    }

    throw lastError ?? new Error('Request failed');
  }

  private sleep(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

/**
 * Create a STIX client from environment variables
 *
 * Reads from:
 * - STIX_ENFORCER_URL
 * - STIX_EVIDENCE_URL
 * - STIX_APPROVALS_URL
 * - STIX_API_KEY
 * - STIX_FAIL_MODE
 * - STIX_DEBUG
 */
export function createClientFromEnv(
  overrides?: Partial<StixClientConfig>
): StixClient {
  const config: StixClientConfig = {
    enforcerUrl: process.env.STIX_ENFORCER_URL ?? 'http://localhost:8080',
    evidenceUrl: process.env.STIX_EVIDENCE_URL,
    approvalsUrl: process.env.STIX_APPROVALS_URL,
    apiKey: process.env.STIX_API_KEY,
    failMode: (process.env.STIX_FAIL_MODE as StixClientConfig['failMode']) ?? 'CLOSED',
    debug: process.env.STIX_DEBUG === 'true',
    ...overrides,
  };

  return new StixClient(config);
}
