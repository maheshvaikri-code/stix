/**
 * STIX Policy Evaluation Engine
 * Implements pattern matching, condition evaluation, and conflict resolution
 */

import {
  type PolicyArtifact,
  type PolicyDecision,
  type Actor,
  type Resource,
  type Context,
  type DecisionKind,
  type Logger,
  hashCanonical,
} from '@stix/shared';
import type { Config } from '../config/index.js';
import type { PolicyStore } from '../store/index.js';
import {
  matchesActorType,
  matchesAction,
  matchesResourceType,
  matchesEnvironment,
  matchesClassifications,
} from './matcher.js';
import { evaluateConditions, type ConditionContext } from './conditions.js';

// =============================================================================
// TYPES
// =============================================================================

export interface EvaluationRequest {
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
  tool_call?: {
    tool: string;
    risk_tier?: string;
    args_summary?: string;
  };
}

interface CacheEntry {
  decision: PolicyDecision;
  expires: number;
}

// =============================================================================
// POLICY ENGINE
// =============================================================================

export class PolicyEngine {
  private readonly config: Config;
  private readonly logger: Logger;
  private readonly store: PolicyStore;
  private cache: Map<string, CacheEntry> = new Map();
  private cacheCleanupInterval: ReturnType<typeof setInterval> | null = null;

  constructor(config: Config, logger: Logger, store: PolicyStore) {
    this.config = config;
    this.logger = logger.child({ component: 'PolicyEngine' });
    this.store = store;

    // Start cache cleanup
    if (config.caching?.enabled) {
      this.startCacheCleanup();
    }
  }

  /**
   * Evaluate policy for a request
   */
  async evaluate(request: EvaluationRequest): Promise<PolicyDecision> {
    const startTime = Date.now();
    const requestId = Math.random().toString(36).substring(7);

    this.logger.debug('Starting policy evaluation', {
      request_id: requestId,
      actor_type: request.actor.type,
      action: request.action,
      resource_type: request.resource.type,
      env: request.context.env,
    });

    try {
      // Check cache first
      if (this.config.caching?.enabled) {
        const cached = this.getFromCache(request);
        if (cached) {
          this.logger.debug('Cache hit', { request_id: requestId });
          return cached;
        }
      }

      // Get all active policies
      const allPolicies = await this.store.listPolicies({ active: true });
      this.logger.debug('Loaded policies', {
        request_id: requestId,
        policy_count: allPolicies.length,
      });

      // Find matching policies (scope matches)
      const scopeMatches = allPolicies.filter(p => this.matchesScope(p, request));
      this.logger.debug('Scope matches', {
        request_id: requestId,
        match_count: scopeMatches.length,
        policy_ids: scopeMatches.map(p => p.policy_id),
      });

      if (scopeMatches.length === 0) {
        const decision = this.createDefaultDenyDecision(request, 'NO_MATCHING_POLICY');
        this.cacheDecision(request, decision);
        return decision;
      }

      // Evaluate conditions
      const conditionCtx = this.buildConditionContext(request);
      const validMatches = scopeMatches.filter(p => {
        if (!p.conditions) return true;
        return evaluateConditions(p.conditions, conditionCtx);
      });

      this.logger.debug('Condition matches', {
        request_id: requestId,
        match_count: validMatches.length,
        policy_ids: validMatches.map(p => p.policy_id),
      });

      if (validMatches.length === 0) {
        const decision = this.createDefaultDenyDecision(request, 'CONDITIONS_NOT_MET');
        this.cacheDecision(request, decision);
        return decision;
      }

      // Resolve conflicts and select winning policy
      const winner = this.resolveConflicts(validMatches);
      this.logger.debug('Policy winner', {
        request_id: requestId,
        policy_id: winner.policy_id,
        decision: winner.decision,
        priority: winner.priority,
      });

      // Build decision
      const decision = this.buildDecision(winner, request);

      // Cache result
      this.cacheDecision(request, decision);

      const durationMs = Date.now() - startTime;
      this.logger.info('Policy evaluation complete', {
        request_id: requestId,
        policy_id: winner.policy_id,
        decision: decision.decision,
        reason_code: decision.reason_code,
        duration_ms: durationMs,
      });

      return decision;
    } catch (error) {
      this.logger.error('Policy evaluation failed', {
        request_id: requestId,
        error: (error as Error).message,
      });

      // Fail closed - return DENY
      return this.createDefaultDenyDecision(request, 'EVALUATION_ERROR');
    }
  }

  /**
   * Check if policy scope matches request
   */
  private matchesScope(policy: PolicyArtifact, request: EvaluationRequest): boolean {
    const scope = policy.scope;

    // Actor type match (supports '*' wildcard)
    if (!matchesActorType(scope.actor_type, request.actor.type)) {
      return false;
    }

    // Action match (supports glob patterns)
    if (!matchesAction(scope.action, request.action)) {
      return false;
    }

    // Resource type match (supports glob patterns)
    if (!matchesResourceType(scope.resource_type, request.resource.type)) {
      return false;
    }

    // Environment match (array - any match)
    if (!matchesEnvironment(scope.environments, request.context.env)) {
      return false;
    }

    // Classification match (all required must be present)
    if (!matchesClassifications(scope.classifications, request.resource.classification)) {
      return false;
    }

    return true;
  }

  /**
   * Build condition context from request
   */
  private buildConditionContext(request: EvaluationRequest): ConditionContext {
    return {
      actor: request.actor,
      resource: request.resource,
      context: request.context as unknown as ConditionContext['context'],
      tool_call: request.tool_call,
    };
  }

  /**
   * Resolve policy conflicts using priority and decision type
   * 
   * Resolution rules:
   * 1. Sort by priority (ascending - lower number = higher priority)
   * 2. At same priority: DENY > QUARANTINE > ALLOW (conservative)
   */
  private resolveConflicts(policies: PolicyArtifact[]): PolicyArtifact {
    if (policies.length === 1) {
      return policies[0];
    }

    const decisionOrder: Record<DecisionKind, number> = {
      DENY: 0,
      QUARANTINE: 1,
      ALLOW: 2,
    };

    const sorted = [...policies].sort((a, b) => {
      // Primary sort: priority (ascending)
      const priorityA = a.priority ?? 100;
      const priorityB = b.priority ?? 100;

      if (priorityA !== priorityB) {
        return priorityA - priorityB;
      }

      // Secondary sort: decision strictness (DENY > QUARANTINE > ALLOW)
      return decisionOrder[a.decision] - decisionOrder[b.decision];
    });

    return sorted[0];
  }

  /**
   * Build policy decision from winning policy
   */
  private buildDecision(policy: PolicyArtifact, request: EvaluationRequest): PolicyDecision {
    const policyHash = hashCanonical({
      id: policy.policy_id,
      version: policy.version,
      decision: policy.decision,
      scope: policy.scope,
    });

    const decision: PolicyDecision = {
      decision: policy.decision,
      reason_code: policy.reason_code ?? `POLICY_${policy.decision}`,
      explanation: policy.description,
      policy: {
        id: policy.policy_id,
        version: policy.version,
        hash: policyHash,
      },
      obligations: policy.obligations ?? [],
      approval: null,
      controls: policy.controls ?? [],
      regulations: policy.regulations ?? [],
    };

    // Add approval info for QUARANTINE decisions
    if (policy.decision === 'QUARANTINE' && policy.approval) {
      const timeoutHours = policy.approval.timeout_hours ?? 24;
      const expiresAt = new Date(Date.now() + timeoutHours * 60 * 60 * 1000).toISOString();

      decision.approval = {
        required: true,
        approver_role: policy.approval.approver_role,
        require_count: policy.approval.require_count ?? 1,
        require_justification: policy.approval.require_justification ?? false,
        expires_at: expiresAt,
      };
    }

    return decision;
  }

  /**
   * Create default DENY decision
   */
  private createDefaultDenyDecision(
    request: EvaluationRequest,
    reasonCode: string
  ): PolicyDecision {
    return {
      decision: 'DENY',
      reason_code: reasonCode,
      explanation: `No applicable policy found for ${request.action} on ${request.resource.type}`,
      policy: {
        id: 'default_deny',
        version: '1.0.0',
        hash: hashCanonical({ id: 'default_deny', v: '1.0.0' }),
      },
      obligations: [],
      approval: null,
      controls: [],
      regulations: [],
    };
  }

  /**
   * Build cache key from request
   */
  private buildCacheKey(request: EvaluationRequest): string {
    return hashCanonical({
      actor_type: request.actor.type,
      actor_role: request.actor.role,
      actor_tenant: request.actor.tenant,
      action: request.action,
      resource_type: request.resource.type,
      resource_classification: request.resource.classification?.sort(),
      env: request.context.env,
      risk_tier: request.tool_call?.risk_tier,
    });
  }

  /**
   * Get cached decision
   */
  private getFromCache(request: EvaluationRequest): PolicyDecision | null {
    const key = this.buildCacheKey(request);
    const entry = this.cache.get(key);

    if (!entry) return null;
    if (entry.expires < Date.now()) {
      this.cache.delete(key);
      return null;
    }

    return entry.decision;
  }

  /**
   * Cache decision
   */
  private cacheDecision(request: EvaluationRequest, decision: PolicyDecision): void {
    if (!this.config.caching?.enabled) return;

    // Don't cache QUARANTINE decisions (state can change)
    if (decision.decision === 'QUARANTINE') return;

    const key = this.buildCacheKey(request);
    const ttlSeconds = this.config.caching.ttlSeconds ?? 60;

    this.cache.set(key, {
      decision,
      expires: Date.now() + (ttlSeconds * 1000),
    });
  }

  /**
   * Start cache cleanup interval
   */
  private startCacheCleanup(): void {
    // Clean up expired entries every minute
    this.cacheCleanupInterval = setInterval(() => {
      const now = Date.now();
      let cleaned = 0;

      for (const [key, entry] of this.cache.entries()) {
        if (entry.expires < now) {
          this.cache.delete(key);
          cleaned++;
        }
      }

      if (cleaned > 0) {
        this.logger.debug('Cache cleanup', { removed: cleaned, remaining: this.cache.size });
      }
    }, 60_000);
  }

  /**
   * Stop cache cleanup
   */
  stopCacheCleanup(): void {
    if (this.cacheCleanupInterval) {
      clearInterval(this.cacheCleanupInterval);
      this.cacheCleanupInterval = null;
    }
  }

  /**
   * Clear cache
   */
  clearCache(): void {
    this.cache.clear();
    this.logger.debug('Cache cleared');
  }
}

// Re-export for routes
export { evaluateConditions } from './conditions.js';
