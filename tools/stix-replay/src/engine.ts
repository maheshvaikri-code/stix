/**
 * STIX Replay - Evaluation Engine
 * Re-evaluate decisions with runtime-compatible policy semantics
 */

import {
  computeRuntimePolicyHash,
  hashCanonical,
  type Actor,
  type Context,
  type DecisionKind,
  type PolicyArtifact,
  type Resource,
} from '@stix/shared';
import type { LoadedPolicyPack } from './policyLoader.js';

// =============================================================================
// TYPES
// =============================================================================

export interface EvaluationInput {
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
}

export interface EvaluationOutput {
  decision: DecisionKind;
  reason_code: string;
  obligations: string[];
  policy_id: string;
  policy_hash: string;
  matched_policies: MatchedPolicy[];
}

export interface MatchedPolicy {
  policy_id: string;
  policy_hash: string;
  decision: DecisionKind;
  priority: number;
}

// =============================================================================
// REPLAY ENGINE
// =============================================================================

export class ReplayEngine {
  private policyPack: LoadedPolicyPack;

  constructor(policyPack: LoadedPolicyPack) {
    this.policyPack = policyPack;
  }

  /**
   * Evaluate an input and return decision
   */
  evaluate(input: EvaluationInput): EvaluationOutput {
    const matchedPolicies = this.findMatchingPolicies(input);

    if (matchedPolicies.length === 0) {
      return {
        decision: 'DENY',
        reason_code: 'NO_MATCHING_POLICY',
        obligations: [],
        policy_id: 'default_deny',
        policy_hash: hashCanonical({ id: 'default_deny', v: '1.0.0' }),
        matched_policies: [],
      };
    }

    matchedPolicies.sort((a, b) => a.priority - b.priority);

    const topPriority = matchedPolicies[0].priority;
    const topPolicies = matchedPolicies.filter((p) => p.priority === topPriority);

    let winningPolicy: MatchedPolicy;
    if (topPolicies.length === 1) {
      winningPolicy = topPolicies[0];
    } else {
      const denyPolicy = topPolicies.find((p) => p.decision === 'DENY');
      const quarantinePolicy = topPolicies.find((p) => p.decision === 'QUARANTINE');
      winningPolicy = denyPolicy || quarantinePolicy || topPolicies[0];
    }

    const fullPolicy = this.policyPack.policyIndex.get(winningPolicy.policy_id);
    const obligations = this.extractObligations(fullPolicy);

    return {
      decision: winningPolicy.decision,
      reason_code: fullPolicy?.reason_code ?? this.buildReasonCode(winningPolicy.policy_id),
      obligations,
      policy_id: winningPolicy.policy_id,
      policy_hash: winningPolicy.policy_hash,
      matched_policies: matchedPolicies,
    };
  }

  /**
   * Find all policies that match the input
   */
  private findMatchingPolicies(input: EvaluationInput): MatchedPolicy[] {
    const matched: MatchedPolicy[] = [];

    for (const policy of this.policyPack.policies) {
      if (policy.active === false) continue;
      if (!this.policyMatches(policy, input)) continue;

      matched.push({
        policy_id: policy.policy_id,
        policy_hash: computeRuntimePolicyHash(policy),
        decision: policy.decision,
        priority: policy.priority ?? 100,
      });
    }

    return matched;
  }

  /**
   * Check if a policy matches the input
   */
  private policyMatches(policy: PolicyArtifact, input: EvaluationInput): boolean {
    const scope = policy.scope;

    if (scope.actor_type !== '*' && scope.actor_type !== input.actor.type) {
      return false;
    }

    if (!this.matchesPattern(scope.action, input.action)) {
      return false;
    }

    if (!this.matchesPattern(scope.resource_type, input.resource.type)) {
      return false;
    }

    const scopeWithExtensions = scope as typeof scope & {
      environments?: string[];
      classifications?: string[];
    };

    if (scopeWithExtensions.environments && scopeWithExtensions.environments.length > 0) {
      if (!scopeWithExtensions.environments.includes(input.context.env)) {
        return false;
      }
    }

    if (scopeWithExtensions.classifications && scopeWithExtensions.classifications.length > 0) {
      const classifications = input.resource.classification || [];
      for (const required of scopeWithExtensions.classifications) {
        if (!classifications.includes(required)) {
          return false;
        }
      }
    }

    return this.matchesConditions(policy, input);
  }

  /**
   * Check conditions block from PolicyArtifact
   */
  private matchesConditions(policy: PolicyArtifact, input: EvaluationInput): boolean {
    const conditions = policy.conditions;
    if (!conditions) return true;

    if (conditions.env && conditions.env !== input.context.env) {
      return false;
    }

    if (conditions.require_signal) {
      const signals = input.context.signals || {};
      for (const [signal, required] of Object.entries(conditions.require_signal)) {
        if (required && !(signals as any)[signal]) {
          return false;
        }
      }
    }

    if (conditions.require_resource_attr) {
      const attrs = input.resource.attributes || {};
      for (const [key, value] of Object.entries(conditions.require_resource_attr)) {
        if ((attrs as any)[key] !== value) {
          return false;
        }
      }
    }

    if (conditions.require_actor_attr) {
      const attrs = input.actor.attributes || {};
      for (const [key, value] of Object.entries(conditions.require_actor_attr)) {
        if ((attrs as any)[key] !== value) {
          return false;
        }
      }
    }

    if (conditions.require_tenant_match) {
      const actorTenant = input.actor.tenant;
      const resourceTenant = (input.resource.attributes as any)?.tenant;
      if (actorTenant !== resourceTenant) {
        return false;
      }
    }

    return true;
  }

  /**
   * Match a scope pattern (glob-style wildcards)
   */
  private matchesPattern(pattern: string, value: string): boolean {
    if (pattern === '*') return true;

    const regex = new RegExp(
      '^' +
      pattern
        .replace(/[.+^${}()|[\]\\]/g, '\\$&')
        .replace(/\*/g, '.*')
        .replace(/\?/g, '.') +
      '$'
    );

    return regex.test(value);
  }

  /**
   * Extract obligation types from policy
   */
  private extractObligations(policy: PolicyArtifact | undefined): string[] {
    if (!policy?.obligations) return [];

    return policy.obligations.map((obligation: { type: string }) => obligation.type);
  }

  /**
   * Build fallback reason code from policy ID
   */
  private buildReasonCode(policyId: string): string {
    return policyId.replace(/[^a-zA-Z0-9]/g, '_').toUpperCase();
  }

  /**
   * Get loaded policy pack
   */
  getPolicyPack(): LoadedPolicyPack {
    return this.policyPack;
  }
}
