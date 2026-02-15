/**
 * Evidence Service Client
 * HTTP client for communicating with the STIX Evidence Service
 */

import {
  type Actor,
  type Resource,
  type Context,
  type PolicyRef,
  type DecisionKind,
  type RiskTier,
  type Logger,
  retry,
  withTimeout,
  ServiceUnavailableError,
} from '@stix/shared';
import type { Config } from '../config/index.js';

// =============================================================================
// TYPES
// =============================================================================

export interface RecordDecisionRequest {
  trace_id: string;
  timestamp: string;
  decision: DecisionKind;
  reason_code: string;
  actor: Actor;
  action: {
    name: string;
    tool?: string;
    risk_tier?: RiskTier;
  };
  resource: Resource;
  context: Context;
  policy: PolicyRef;
  controls: string[];
  regulations: string[];
}

export interface RecordOutcomeRequest {
  trace_id: string;
  status: 'SUCCESS' | 'FAILED' | 'SKIPPED' | 'PENDING';
  result_summary?: string;
  error_class?: string;
  obligations_applied?: Record<string, boolean>;
}

export interface EvidenceEventView {
  event_id: string;
  trace_id: string;
  timestamp: string;
  decision?: DecisionKind;
  reason_code?: string;
  actor_id?: string;
  actor_type?: string;
  action?: string;
  resource_type?: string;
  resource_id?: string;
  policy_id?: string;
}

export interface EvidenceListResponse {
  data?: EvidenceEventView[];
  records?: EvidenceEventView[];
  total?: number;
  page?: number;
  page_size?: number;
  has_more?: boolean;
}

export interface EvidenceStatsResponse {
  total: number;
  by_decision?: Record<string, number>;
  by_actor_type?: Record<string, number>;
  by_action?: Record<string, number>;
  unique_actors?: number;
  unique_traces?: number;
}

// =============================================================================
// EVIDENCE CLIENT
// =============================================================================

export class EvidenceClient {
  private readonly config: Config;
  protected readonly logger: Logger;
  private readonly baseUrl: string;
  private readonly serviceAuthToken: string | null;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger.child({ component: 'EvidenceClient' });
    this.baseUrl = config.services.evidenceUrl;
    this.serviceAuthToken = config.services.serviceAuthToken || null;
  }

  /**
   * Record authorization decision
   */
  async recordDecision(request: RecordDecisionRequest): Promise<void> {
    this.logger.debug('Recording decision', {
      trace_id: request.trace_id,
      decision: request.decision,
    });

    try {
      await retry(
        async () => {
          return withTimeout(
            this.doRecordDecision(request),
            this.config.timeouts.serviceRequest
          );
        },
        {
          maxAttempts: this.config.retry.maxAttempts,
          initialDelayMs: this.config.retry.initialDelayMs,
          maxDelayMs: this.config.retry.maxDelayMs,
        }
      );
    } catch (error) {
      this.handleWriteFailure('decision', request.trace_id, error);
    }
  }

  /**
   * Perform actual decision recording
   */
  private async doRecordDecision(request: RecordDecisionRequest): Promise<void> {
    const headers = this.buildHeaders();
    const response = await fetch(`${this.baseUrl}/api/v1/evidence/decision`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      const message = this.extractErrorMessage(payload, response.status);
      throw new Error(`Evidence recording failed: ${message}`);
    }
  }

  /**
   * Record execution outcome
   */
  async recordOutcome(request: RecordOutcomeRequest): Promise<void> {
    this.logger.debug('Recording outcome', {
      trace_id: request.trace_id,
      status: request.status,
    });

    try {
      await retry(
        async () => {
          return withTimeout(
            this.doRecordOutcome(request),
            this.config.timeouts.serviceRequest
          );
        },
        {
          maxAttempts: this.config.retry.maxAttempts,
          initialDelayMs: this.config.retry.initialDelayMs,
          maxDelayMs: this.config.retry.maxDelayMs,
        }
      );
    } catch (error) {
      this.handleWriteFailure('outcome', request.trace_id, error);
    }
  }

  /**
   * Perform actual outcome recording
   */
  private async doRecordOutcome(request: RecordOutcomeRequest): Promise<void> {
    const headers = this.buildHeaders();
    const response = await fetch(`${this.baseUrl}/api/v1/evidence/outcome`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      const message = this.extractErrorMessage(payload, response.status);
      throw new Error(`Outcome recording failed: ${message}`);
    }
  }

  /**
   * Health check
   */
  async health(): Promise<boolean> {
    try {
      const response = await fetch(`${this.baseUrl}/health`, {
        headers: this.buildHeaders(false),
      });
      return response.ok;
    } catch {
      return false;
    }
  }

  async getTraceEvents(traceId: string): Promise<EvidenceEventView[]> {
    const response = await fetch(`${this.baseUrl}/api/v1/evidence/trace/${encodeURIComponent(traceId)}`, {
      headers: this.buildHeaders(false),
    });
    if (response.status === 404) {
      return [];
    }
    if (!response.ok) {
      throw new ServiceUnavailableError('evidence', {
        operation: 'get_trace',
        trace_id: traceId,
        status: response.status,
      });
    }
    return response.json() as Promise<EvidenceEventView[]>;
  }

  async queryEvents(params: {
    page?: number;
    pageSize?: number;
    decision?: DecisionKind;
    traceId?: string;
    actorId?: string;
    startTime?: string;
    endTime?: string;
  }): Promise<EvidenceListResponse> {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.pageSize) query.set('page_size', String(params.pageSize));
    if (params.decision) query.set('decision', params.decision);
    if (params.traceId) query.set('trace_id', params.traceId);
    if (params.actorId) query.set('actor_id', params.actorId);
    if (params.startTime) query.set('start_time', params.startTime);
    if (params.endTime) query.set('end_time', params.endTime);

    const response = await fetch(`${this.baseUrl}/api/v1/evidence?${query.toString()}`, {
      headers: this.buildHeaders(false),
    });
    if (!response.ok) {
      throw new ServiceUnavailableError('evidence', {
        operation: 'query_events',
        status: response.status,
      });
    }
    return response.json() as Promise<EvidenceListResponse>;
  }

  async getStats(): Promise<EvidenceStatsResponse> {
    const response = await fetch(`${this.baseUrl}/api/v1/evidence/stats`, {
      headers: this.buildHeaders(false),
    });
    if (!response.ok) {
      throw new ServiceUnavailableError('evidence', {
        operation: 'get_stats',
        status: response.status,
      });
    }
    return response.json() as Promise<EvidenceStatsResponse>;
  }

  private handleWriteFailure(
    operation: 'decision' | 'outcome',
    traceId: string,
    error: unknown
  ): void {
    const message = (error as Error).message;
    const writeMode = this.config.evidence.writeMode;

    this.logger.error(`Failed to record ${operation}`, {
      trace_id: traceId,
      error: message,
      write_mode: writeMode,
    });

    if (writeMode === 'strict') {
      throw new ServiceUnavailableError('evidence', {
        operation,
        trace_id: traceId,
        cause: message,
      });
    }
  }

  private buildHeaders(withJson = true): Record<string, string> {
    const headers: Record<string, string> = {};
    if (withJson) {
      headers['Content-Type'] = 'application/json';
    }
    if (this.serviceAuthToken) {
      headers['X-STIX-Service-Token'] = this.serviceAuthToken;
    }
    return headers;
  }

  private extractErrorMessage(payload: unknown, status: number): string {
    if (payload && typeof payload === 'object') {
      const body = payload as {
        message?: unknown;
        error?: { message?: unknown };
      };
      const fromError = body.error?.message;
      if (typeof fromError === 'string' && fromError.length > 0) {
        return fromError;
      }
      if (typeof body.message === 'string' && body.message.length > 0) {
        return body.message;
      }
    }
    return `Status ${status}`;
  }
}

// =============================================================================
// MOCK EVIDENCE CLIENT (for development/testing)
// =============================================================================

export class MockEvidenceClient extends EvidenceClient {
  private readonly events: RecordDecisionRequest[] = [];
  private readonly outcomes: RecordOutcomeRequest[] = [];

  async recordDecision(request: RecordDecisionRequest): Promise<void> {
    this.events.push(request);
    this.logger.debug('Mock: Recorded decision', { trace_id: request.trace_id });
  }

  async recordOutcome(request: RecordOutcomeRequest): Promise<void> {
    this.outcomes.push(request);
    this.logger.debug('Mock: Recorded outcome', { trace_id: request.trace_id });
  }

  async health(): Promise<boolean> {
    return true;
  }

  // Test helpers
  getEvents(): RecordDecisionRequest[] {
    return [...this.events];
  }

  getOutcomes(): RecordOutcomeRequest[] {
    return [...this.outcomes];
  }

  clear(): void {
    this.events.length = 0;
    this.outcomes.length = 0;
  }
}
