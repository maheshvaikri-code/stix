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
  type ApprovalBinding,
  type DecisionKind,
  type RiskTier,
  type Logger,
  generateTraceId,
  generateRequestId,
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

class ApprovalBindingError extends Error {
  readonly forceClosed = true;

  constructor(message: string) {
    super(message);
    this.name = 'ApprovalBindingError';
  }
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
      // Validate approval references before any cache or policy result can be used.
      if (request.approval_ref) {
        await this.validateApprovalReference(request);
      }

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
    return `authz:${this.buildRequestBinding(request).request_hash}`;
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

    // Approval never overrides a DENY. It only satisfies the human-review
    // branch after the policy has been evaluated again.
    if (ctx.request.approval_ref && decision.decision === 'QUARANTINE') {
      return {
        ...decision,
        decision: 'ALLOW',
        reason_code: 'APPROVED_BY_HUMAN',
        approval: null,
        explanation: `${decision.explanation ?? 'Policy requires approval'}; approval ${ctx.request.approval_ref} verified`,
      };
    }

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
      action_id: this.buildRequestBinding(ctx.request).action_id,
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
      security_binding: this.buildRequestBinding(ctx.request),
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
    const binding = this.buildRequestBinding(ctx.request);
    const replayId = generateRequestId();

    const claims = {
      iss: TOKEN_CONFIG.ISSUER,
      sub: ctx.request.actor.id,
      act: ctx.request.action,
      res: ctx.request.resource.type,
      cls: ctx.request.resource.classification ?? [],
      pol: policyDecision.policy.hash,
      tid: ctx.traceId,
      jti: replayId,
      replay_id: replayId,
      request_hash: binding.request_hash,
      arguments_hash: binding.arguments_hash,
      action_id: binding.action_id,
      resource_id: ctx.request.resource.id,
      approval_ref: ctx.request.approval_ref,
      decision: 'ALLOW' as const,
      reason_code: policyDecision.reason_code,
      policy_id: policyDecision.policy.id,
      policy_version: policyDecision.policy.version,
      policy_hash: policyDecision.policy.hash,
      pack_hash: policyDecision.policy.hash,
      actor_id: ctx.request.actor.id,
      actor_type: ctx.request.actor.type,
      actor_role: ctx.request.actor.role,
      actor_tenant: ctx.request.actor.tenant,
      action: ctx.request.action,
      resource_type: ctx.request.resource.type,
      risk_tier: ctx.request.tool_call?.risk_tier,
      obligations: JSON.stringify(policyDecision.obligations ?? []),
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
    const failMode = (error as Error & { forceClosed?: boolean }).forceClosed
      ? 'CLOSED'
      : this.config.authorization.defaultFailMode;
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
      action_id: this.buildRequestBinding(ctx.request).action_id,
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

  /**
   * Build the immutable request binding used by proofs and approvals.
   * approval_ref is intentionally excluded so reauthorization can prove that
   * the approved request is byte-for-byte equivalent to the original request.
   */
  private buildRequestBinding(request: AuthorizeRequest): ApprovalBinding {
    const baseRequest = {
      ...request,
      approval_ref: undefined,
    };
    const actionId = request.action_id ?? `act_${hashCanonical(baseRequest).slice(7)}`;
    const hashableRequest = {
      ...baseRequest,
      action_id: actionId,
    };

    return {
      request_hash: hashCanonical(hashableRequest),
      arguments_hash: request.tool_call?.args_hash ?? hashCanonical(request.tool_call ?? null),
      action_id: actionId,
      actor_id: request.actor.id,
      actor_type: request.actor.type,
      actor_role: request.actor.role,
      actor_tenant: request.actor.tenant,
      action: request.action,
      resource_type: request.resource.type,
      resource_id: request.resource.id,
    };
  }

  private async validateApprovalReference(request: AuthorizeRequest): Promise<void> {
    const ticketId = request.approval_ref;
    if (!ticketId) return;

    let ticket;
    try {
      ticket = await this.approvalsClient.getTicket(ticketId);
    } catch (error) {
      throw new ApprovalBindingError(
        `Approval reference '${ticketId}' could not be loaded: ${(error as Error).message}`
      );
    }

    if (ticket.status !== 'APPROVED') {
      throw new ApprovalBindingError(
        `Approval reference '${ticketId}' is not approved (status=${ticket.status})`
      );
    }

    const binding = ticket.security_binding;
    const current = this.buildRequestBinding(request);
    if (!binding ||
      binding.request_hash !== current.request_hash ||
      binding.arguments_hash !== current.arguments_hash ||
      binding.action_id !== current.action_id ||
      binding.actor_id !== current.actor_id ||
      binding.actor_type !== current.actor_type ||
      binding.actor_role !== current.actor_role ||
      binding.actor_tenant !== current.actor_tenant ||
      binding.action !== current.action ||
      binding.resource_type !== current.resource_type ||
      binding.resource_id !== current.resource_id) {
      throw new ApprovalBindingError(
        `Approval reference '${ticketId}' does not bind the exact authorization request`
      );
    }
  }
}
