/**
 * Policy Service Client
 * HTTP client for communicating with the STIX Policy Service
 */

import {
  type AuthorizeRequest,
  type PolicyDecision,
  type PolicyRef,
  type Logger,
  retry,
  withTimeout,
  ServiceUnavailableError,
  ServiceTimeoutError,
  PolicyNotFoundError,
  REASON_CODES,
  hashCanonical,
} from '@stix/shared';
import type { Config } from '../config/index.js';

// =============================================================================
// TYPES
// =============================================================================

export interface PolicyEvaluationRequest {
  actor: AuthorizeRequest['actor'];
  action: string;
  resource: AuthorizeRequest['resource'];
  context: AuthorizeRequest['context'];
  tool_call?: AuthorizeRequest['tool_call'];
}

// =============================================================================
// POLICY CLIENT
// =============================================================================

export class PolicyClient {
  private readonly config: Config;
  protected readonly logger: Logger;
  private readonly baseUrl: string;
  private readonly serviceAuthToken: string | null;

  constructor(config: Config, logger: Logger) {
    this.config = config;
    this.logger = logger.child({ component: 'PolicyClient' });
    this.baseUrl = config.services.policyUrl;
    this.serviceAuthToken = config.services.serviceAuthToken || null;
  }

  /**
   * Evaluate policy for request
   */
  async evaluate(request: PolicyEvaluationRequest): Promise<PolicyDecision> {
    this.logger.debug('Evaluating policy', {
      actor_type: request.actor.type,
      action: request.action,
      resource_type: request.resource.type,
    });

    try {
      const result = await retry(
        async () => {
          return withTimeout(
            this.doEvaluate(request),
            this.config.timeouts.policyEvaluation
          );
        },
        {
          maxAttempts: this.config.retry.maxAttempts,
          initialDelayMs: this.config.retry.initialDelayMs,
          maxDelayMs: this.config.retry.maxDelayMs,
        }
      );

      return result;
    } catch (error) {
      if ((error as Error).message?.includes('timeout')) {
        throw new ServiceTimeoutError('Policy service');
      }
      throw new ServiceUnavailableError('Policy service', (error as Error).message);
    }
  }

  /**
   * Perform actual policy evaluation
   */
  private async doEvaluate(request: PolicyEvaluationRequest): Promise<PolicyDecision> {
    const headers = this.buildHeaders();
    const response = await fetch(`${this.baseUrl}/api/v1/evaluate`, {
      method: 'POST',
      headers,
      body: JSON.stringify(request),
    });

    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      const message = this.extractErrorMessage(payload, response.status);
      throw new Error(`Policy evaluation failed: ${message}`);
    }

    const result = await response.json() as PolicyDecision;
    return result;
  }

  /**
   * Get policy by ID
   */
  async getPolicy(policyId: string): Promise<PolicyRef> {
    this.logger.debug('Fetching policy', { policy_id: policyId });

    const response = await fetch(`${this.baseUrl}/api/v1/policies/${policyId}`, {
      headers: this.buildHeaders(false),
    });

    if (!response.ok) {
      if (response.status === 404) {
        throw new PolicyNotFoundError(policyId);
      }
      throw new ServiceUnavailableError('Policy service', `Status: ${response.status}`);
    }

    return response.json() as Promise<PolicyRef>;
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
// MOCK POLICY CLIENT (for development/testing)
// =============================================================================

export class MockPolicyClient extends PolicyClient {
  private readonly policies: Map<string, PolicyDecision> = new Map();

  constructor(config: Config, logger: Logger) {
    super(config, logger);
    this.setupDefaultPolicies();
  }

  /**
   * Setup default policies for testing
   */
  private setupDefaultPolicies(): void {
    // Default DENY for unmatched requests
    // Actual policy matching happens in evaluate
  }

  /**
   * Evaluate policy using mock rules
   */
  async evaluate(request: PolicyEvaluationRequest): Promise<PolicyDecision> {
    // Simple rule-based evaluation for testing
    
    // Rule: DENY if accessing production data in non-prod env
    if (
      request.resource.type.includes('production') &&
      request.context.env !== 'prod'
    ) {
      return this.createDecision('DENY', 'ENVIRONMENT_RESTRICTION', 'deny-prod-access');
    }

    // Rule: QUARANTINE if PII detected
    if (request.context.signals?.piiDetected) {
      return this.createQuarantineDecision(
        'PII_DETECTED',
        'quarantine-pii',
        'data_steward'
      );
    }

    // Rule: QUARANTINE for CRITICAL risk tier
    if (request.tool_call?.risk_tier === 'CRITICAL') {
      return this.createQuarantineDecision(
        'HIGH_RISK_ACTION',
        'quarantine-critical',
        'security_admin'
      );
    }

    // Rule: ALLOW with obligations for HIGH risk
    if (request.tool_call?.risk_tier === 'HIGH') {
      return this.createDecision('ALLOW', 'POLICY_ALLOW', 'allow-high-risk', [
        { type: 'LOG_LEVEL', params: { level: 'info' } },
        { type: 'WATERMARK_OUTPUT' },
      ]);
    }

    // Default: ALLOW for authenticated requests
    if (request.actor.id && request.actor.type) {
      return this.createDecision('ALLOW', 'POLICY_ALLOW', 'default-allow');
    }

    // Fallback: DENY
    return this.createDecision('DENY', 'UNAUTHORIZED_ACTOR', 'default-deny');
  }

  private createDecision(
    decision: 'ALLOW' | 'DENY',
    reasonCode: string,
    policyId: string,
    obligations: PolicyDecision['obligations'] = []
  ): PolicyDecision {
    return {
      decision,
      reason_code: reasonCode,
      policy: {
        id: policyId,
        version: '1.0.0',
        hash: `sha256:${hashCanonical({ id: policyId, v: '1.0.0' }).replace('sha256:', '')}`,
      },
      obligations,
      approval: null,
      controls: ['SOC2:CC6.1'],
      regulations: ['GDPR:Art.6'],
    };
  }

  private createQuarantineDecision(
    reasonCode: string,
    policyId: string,
    approverRole: string
  ): PolicyDecision {
    return {
      decision: 'QUARANTINE',
      reason_code: reasonCode,
      policy: {
        id: policyId,
        version: '1.0.0',
        hash: `sha256:${hashCanonical({ id: policyId, v: '1.0.0' }).replace('sha256:', '')}`,
      },
      obligations: [],
      approval: {
        required: true,
        approver_role: approverRole,
        require_count: 1,
        require_justification: true,
        expires_at: new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString(),
      },
      controls: ['SOC2:CC6.1'],
      regulations: ['GDPR:Art.6'],
    };
  }

  async health(): Promise<boolean> {
    return true;
  }
}
