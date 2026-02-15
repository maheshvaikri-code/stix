/**
 * STIX Authorization Engine
 * Core decision-making logic for authorization requests
 */

import {
  type AuthorizeRequest,
  type AuthorizeResponse,
  type PolicyDecision,
  type PolicyRef,
  type Obligation,
  type ApprovalInfo,
  type DecisionKind,
  type RiskTier,
  type Logger,
  generateTraceId,
  generateApprovalTicketId,
  isoTimestamp,
  unixTimestamp,
  hashCanonical,
  createProofToken,
  type SigningKey,
  REASON_CODES,
  TOKEN_CONFIG,
} from '@stix/shared';
import type { Config } from '../config/index.js';
import type { PolicyClient } from '../services/policy-client.js';
import type { EvidenceClient } from '../services/evidence-client.js';
import type { ApprovalsClient } from '../services/approvals-client.js';
import type { CacheService } from '../services/cache.js';

// =============================================================================
// TYPES
// =============================================================================

export interface AuthorizationContext {
  request: AuthorizeRequest;
  traceId: string;
  startTime: number;
  logger: Logger;
}

export interface AuthorizationResult {
  response: AuthorizeResponse;
  durationMs: number;
  cached: boolean;
}

// =============================================================================
// AUTHORIZATION ENGINE
// =============================================================================

export class AuthorizationEngine {
  private readonly config: Config;
  private readonly logger: Logger;
  private readonly policyClient: PolicyClient;
  private readonly evidenceClient: EvidenceClient;
  private readonly approvalsClient: ApprovalsClient;
  private readonly cache: CacheService | null;
  private readonly signingKey: SigningKey | null;

  constructor(
    config: Config,
    logger: Logger,
    policyClient: PolicyClient,
    evidenceClient: EvidenceClient,
    approvalsClient: ApprovalsClient,
    cache: CacheService | null,
    signingKey: SigningKey | null
  ) {
    this.config = config;
    this.logger = logger.child({ component: 'AuthorizationEngine' });
    this.policyClient = policyClient;
    this.evidenceClient = evidenceClient;
    this.approvalsClient = approvalsClient;
    this.cache = cache;
    this.signingKey = signingKey;
  }

  /**
   * Process authorization request
   */
  async authorize(request: AuthorizeRequest): Promise<AuthorizationResult> {
    const startTime = Date.now();
    const traceId = generateTraceId();
    
    const ctx: AuthorizationContext = {
      request,
      traceId,
      startTime,
      logger: this.logger.child({ trace_id: traceId }),
    };

    ctx.logger.info('Processing authorization request', {
      actor_id: request.actor.id,
      action: request.action,
      resource_type: request.resource.type,
    });

    try {
      // Check cache first
      if (this.config.authorization.cacheEnabled && this.cache) {
        const cached = await this.checkCache(ctx);
        if (cached) {
          ctx.logger.debug('Cache hit', { decision: cached.decision });
          return {
            response: { ...cached, trace_id: traceId },
            durationMs: Date.now() - startTime,
            cached: true,
          };
        }
      }

      // Evaluate policy
      const policyDecision = await this.evaluatePolicy(ctx);
      
      // Build response
      const response = await this.buildResponse(ctx, policyDecision);
      
      // Record evidence
      await this.recordEvidence(ctx, response);
      
      // Cache if enabled
      if (this.config.authorization.cacheEnabled && this.cache) {
        await this.cacheResponse(ctx, response);
      }

      const durationMs = Date.now() - startTime;
      ctx.logger.info('Authorization complete', {
        decision: response.decision,
        reason_code: response.reason_code,
        duration_ms: durationMs,
      });

      return {
        response,
        durationMs,
        cached: false,
      };
    } catch (error) {
      ctx.logger.error('Authorization failed', {}, error as Error);
      
      // Fail mode handling
      return this.handleFailure(ctx, error as Error);
    }
  }

  /**
   * Check cache for existing decision
   */
  private async checkCache(ctx: AuthorizationContext): Promise<AuthorizeResponse | null> {
    if (!this.cache) return null;

    const cacheKey = this.buildCacheKey(ctx.request);
    const cached = await this.cache.get<AuthorizeResponse>(cacheKey);
    
    if (cached) {
      ctx.logger.debug('Found cached decision', { key: cacheKey });
      return cached;
    }
    
    return null;
  }

  /**
   * Build cache key from request
   */
  private buildCacheKey(request: AuthorizeRequest): string {
    const keyParts = [
      request.actor.id,
      request.actor.type,
      request.action,
      request.resource.type,
      request.resource.id ?? '',
      request.context.env,
    ];
    return `authz:${hashCanonical(keyParts)}`;
  }

  /**
   * Evaluate policy for request
   */
  private async evaluatePolicy(ctx: AuthorizationContext): Promise<PolicyDecision> {
    ctx.logger.debug('Evaluating policy');

    const decision = await this.policyClient.evaluate({
      actor: ctx.request.actor,
      action: ctx.request.action,
      resource: ctx.request.resource,
      context: ctx.request.context,
      tool_call: ctx.request.tool_call,
    });

    ctx.logger.debug('Policy evaluation complete', {
      decision: decision.decision,
      policy_id: decision.policy.id,
    });

    return decision;
  }

  /**
   * Build authorization response
   */
  private async buildResponse(
    ctx: AuthorizationContext,
    policyDecision: PolicyDecision
  ): Promise<AuthorizeResponse> {
    const response: AuthorizeResponse = {
      decision: policyDecision.decision,
      reason_code: policyDecision.reason_code,
      trace_id: ctx.traceId,
      explanation: policyDecision.explanation,
      policy: policyDecision.policy,
      obligations: policyDecision.obligations,
      approval: null,
      controls: policyDecision.controls,
      regulations: policyDecision.regulations,
    };

    // Handle QUARANTINE - create approval request
    if (policyDecision.decision === 'QUARANTINE' && policyDecision.approval?.required) {
      const approvalInfo = await this.createApprovalRequest(ctx, policyDecision);
      response.approval = approvalInfo;
    }

    // Handle ALLOW - generate proof token
    if (policyDecision.decision === 'ALLOW' && this.signingKey) {
      response.proof_token = this.generateProofToken(ctx, policyDecision);
    }

    return response;
  }

  /**
   * Create approval request for QUARANTINE decisions
   */
  private async createApprovalRequest(
    ctx: AuthorizationContext,
    policyDecision: PolicyDecision
  ): Promise<ApprovalInfo> {
    const ticketId = generateApprovalTicketId();
    const approval = policyDecision.approval!;
    const expiresAt = this.resolveApprovalExpiry(approval.expires_at);

    // Create ticket in approvals service
    await this.approvalsClient.createTicket({
      ticket_id: ticketId,
      trace_id: ctx.traceId,
      actor: ctx.request.actor,
      action: ctx.request.action,
      resource: ctx.request.resource,
      context: ctx.request.context,
      required_count: approval.require_count ?? 1,
      required_role: approval.approver_role,
      require_justification: approval.require_justification ?? false,
      expires_at: expiresAt,
    });

    ctx.logger.info('Created approval request', {
      ticket_id: ticketId,
      expires_at: expiresAt,
    });

    return {
      required: true,
      ticket_id: ticketId,
      approver_role: approval.approver_role,
      require_count: approval.require_count,
      require_justification: approval.require_justification,
      expires_at: expiresAt,
    };
  }

  private resolveApprovalExpiry(requestedExpiry?: string): string {
    if (requestedExpiry) {
      const parsed = new Date(requestedExpiry);
      if (!Number.isNaN(parsed.getTime()) && parsed.getTime() > Date.now()) {
        return parsed.toISOString();
      }
    }

    // Default approval TTL when policy decision does not carry a valid expiration.
    return new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
  }

  /**
   * Generate proof token for ALLOW decisions
   */
  private generateProofToken(
    ctx: AuthorizationContext,
    policyDecision: PolicyDecision
  ): string {
    if (!this.signingKey) {
      throw new Error('No signing key available');
    }

    const now = unixTimestamp();
    const expirySeconds = this.config.authorization.tokenExpirySeconds;

    const claims = {
      iss: TOKEN_CONFIG.ISSUER,
      sub: ctx.request.actor.id,
      act: ctx.request.action,
      res: ctx.request.resource.type,
      cls: ctx.request.resource.classification ?? [],
      pol: policyDecision.policy.hash,
      tid: ctx.traceId,
      iat: now,
      exp: now + expirySeconds,
    };

    return createProofToken(claims, this.signingKey);
  }

  /**
   * Record evidence for decision
   */
  private async recordEvidence(
    ctx: AuthorizationContext,
    response: AuthorizeResponse
  ): Promise<void> {
    try {
      await this.evidenceClient.recordDecision({
        trace_id: ctx.traceId,
        timestamp: isoTimestamp(),
        decision: response.decision,
        reason_code: response.reason_code,
        actor: ctx.request.actor,
        action: {
          name: ctx.request.action,
          tool: ctx.request.tool_call?.tool,
          risk_tier: ctx.request.tool_call?.risk_tier,
        },
        resource: ctx.request.resource,
        context: ctx.request.context,
        policy: response.policy,
        controls: response.controls ?? [],
        regulations: response.regulations ?? [],
      });
      
      ctx.logger.debug('Evidence recorded');
    } catch (error) {
      if (this.config.evidence.writeMode === 'strict') {
        throw error;
      }
      ctx.logger.error('Failed to record evidence', {}, error as Error);
    }
  }

  /**
   * Cache authorization response
   */
  private async cacheResponse(
    ctx: AuthorizationContext,
    response: AuthorizeResponse
  ): Promise<void> {
    if (!this.cache) return;

    // Don't cache QUARANTINE decisions
    if (response.decision === 'QUARANTINE') {
      return;
    }

    const cacheKey = this.buildCacheKey(ctx.request);
    const ttlSeconds = this.config.authorization.cacheTtlSeconds;
    
    await this.cache.set(cacheKey, response, ttlSeconds);
    ctx.logger.debug('Response cached', { key: cacheKey, ttl: ttlSeconds });
  }

  /**
   * Handle authorization failure based on fail mode
   */
  private handleFailure(
    ctx: AuthorizationContext,
    error: Error
  ): AuthorizationResult {
    const failMode = this.config.authorization.defaultFailMode;
    ctx.logger.warn('Applying fail mode', { fail_mode: failMode, error: error.message });

    let decision: DecisionKind;
    let reasonCode: string;

    switch (failMode) {
      case 'OPEN':
        decision = 'ALLOW';
        reasonCode = REASON_CODES.LOW_RISK_ALLOWED;
        break;
        
      case 'OPEN_LOW_RISK_ONLY':
        // Allow only if tool is low risk
        const riskTier = ctx.request.tool_call?.risk_tier ?? 'HIGH';
        if (riskTier === 'LOW') {
          decision = 'ALLOW';
          reasonCode = REASON_CODES.LOW_RISK_ALLOWED;
        } else {
          decision = 'DENY';
          reasonCode = REASON_CODES.DEFAULT_DENY;
        }
        break;
        
      case 'CLOSED':
      default:
        decision = 'DENY';
        reasonCode = REASON_CODES.DEFAULT_DENY;
        break;
    }

    const response: AuthorizeResponse = {
      decision,
      reason_code: reasonCode,
      trace_id: ctx.traceId,
      explanation: `Fail mode: ${failMode}. Error: ${error.message}`,
      policy: {
        id: 'fail_mode',
        version: '1.0.0',
        hash: 'sha256:' + '0'.repeat(64),
      },
      obligations: [],
      approval: null,
    };

    return {
      response,
      durationMs: Date.now() - ctx.startTime,
      cached: false,
    };
  }
}
