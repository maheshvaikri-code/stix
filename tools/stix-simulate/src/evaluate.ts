/**
 * STIX Simulation - Policy Evaluation Engine
 * Deterministic evaluation matching runtime behavior
 */

import type { PolicyArtifact, DecisionKind } from '@stix/shared';
import { computeRuntimePolicyHash, hashCanonical } from '@stix/shared';
import type { SimulationInput } from './types.js';
import type { PolicyPack } from './loadPolicies.js';

// =============================================================================
// EVALUATION RESULT
// =============================================================================

export interface EvaluationResult {
  decision: DecisionKind;
  reason_code: string;
  policy_id: string;
  policy_hash: string;
  obligations: string[];
  controls: string[];
  regulations: string[];
}

// =============================================================================
// POLICY ENGINE (SIMULATION VERSION)
// =============================================================================

/**
 * Simulation policy engine
 * Uses the EXACT same rules as runtime PolicyEngine
 */
export class SimulationPolicyEngine {
  private readonly policies: PolicyArtifact[];
  private readonly packHash: string;

  constructor(pack: PolicyPack) {
    // Only use active policies
    this.policies = pack.policies.filter(p => p.active !== false);
    this.packHash = pack.hash;
  }

  /**
   * Evaluate a simulation input against the policy pack
   */
  evaluate(input: SimulationInput): EvaluationResult {
    // Find matching policies (scope matches)
    const scopeMatches = this.policies.filter(p => this.matchesScope(p, input));

    if (scopeMatches.length === 0) {
      return this.defaultDenyResult('NO_MATCHING_POLICY');
    }

    // Evaluate conditions
    const conditionMatches = scopeMatches.filter(p => this.matchesConditions(p, input));

    if (conditionMatches.length === 0) {
      return this.defaultDenyResult('CONDITIONS_NOT_MET');
    }

    // Resolve conflicts and select winning policy
    const winner = this.resolveConflicts(conditionMatches);

    // Build result
    return this.buildResult(winner);
  }

  /**
   * Check if policy scope matches input
   */
  private matchesScope(policy: PolicyArtifact, input: SimulationInput): boolean {
    const scope = policy.scope;

    // Actor type match (supports '*' wildcard)
    if (scope.actor_type !== '*' && scope.actor_type !== input.actor.type) {
      return false;
    }

    // Action match (supports glob patterns)
    if (!this.matchesPattern(scope.action, input.action)) {
      return false;
    }

    // Resource type match (supports glob patterns)
    if (!this.matchesPattern(scope.resource_type, input.resource.type)) {
      return false;
    }

    // Environment match (if specified)
    const scopeWithExtensions = scope as typeof scope & {
      environments?: string[];
      classifications?: string[];
    };

    if (scopeWithExtensions.environments && scopeWithExtensions.environments.length > 0) {
      if (!scopeWithExtensions.environments.includes(input.context.env)) {
        return false;
      }
    }

    // Classification match (all required must be present)
    if (scopeWithExtensions.classifications && scopeWithExtensions.classifications.length > 0) {
      const resourceClassifications = input.resource.classification || [];
      for (const required of scopeWithExtensions.classifications) {
        if (!resourceClassifications.includes(required)) {
          return false;
        }
      }
    }

    return true;
  }

  /**
   * Check if policy conditions match input
   */
  private matchesConditions(policy: PolicyArtifact, input: SimulationInput): boolean {
    const conditions = policy.conditions;
    if (!conditions) return true;

    // Environment condition
    if (conditions.env && conditions.env !== input.context.env) {
      return false;
    }

    // Signal conditions
    if (conditions.require_signal) {
      const signals = input.context.signals || {};
      for (const [signal, required] of Object.entries(conditions.require_signal)) {
        if (required && !(signals as any)[signal]) {
          return false;
        }
      }
    }

    // Resource attribute conditions
    if (conditions.require_resource_attr) {
      const attrs = input.resource.attributes || {};
      for (const [key, value] of Object.entries(conditions.require_resource_attr)) {
        if ((attrs as any)[key] !== value) {
          return false;
        }
      }
    }

    // Actor attribute conditions
    if (conditions.require_actor_attr) {
      const attrs = input.actor.attributes || {};
      for (const [key, value] of Object.entries(conditions.require_actor_attr)) {
        if ((attrs as any)[key] !== value) {
          return false;
        }
      }
    }

    // Tenant match condition
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
   * Match a pattern (supports glob-style wildcards)
   */
  private matchesPattern(pattern: string, value: string): boolean {
    if (pattern === '*') return true;

    // Convert glob to regex
    const regex = new RegExp(
      '^' +
      pattern
        .replace(/[.+^${}()|[\]\\]/g, '\\$&') // Escape special chars
        .replace(/\*/g, '.*')                  // * -> .*
        .replace(/\?/g, '.')                   // ? -> .
      + '$'
    );

    return regex.test(value);
  }

  /**
   * Resolve policy conflicts
   * Rules:
   * 1. Sort by priority (ascending - lower = higher priority)
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
      // Primary: priority (ascending)
      const priorityA = a.priority ?? 100;
      const priorityB = b.priority ?? 100;

      if (priorityA !== priorityB) {
        return priorityA - priorityB;
      }

      // Secondary: decision strictness
      return decisionOrder[a.decision] - decisionOrder[b.decision];
    });

    return sorted[0];
  }

  /**
   * Build evaluation result from winning policy
   */
  private buildResult(policy: PolicyArtifact): EvaluationResult {
    const policyHash = computeRuntimePolicyHash(policy);

    return {
      decision: policy.decision,
      reason_code: policy.reason_code || `POLICY_${policy.decision}`,
      policy_id: policy.policy_id,
      policy_hash: policyHash,
      obligations: (policy.obligations || []).map(o => o.type),
      controls: policy.controls || [],
      regulations: policy.regulations || [],
    };
  }

  /**
   * Default DENY result
   */
  private defaultDenyResult(reasonCode: string): EvaluationResult {
    return {
      decision: 'DENY',
      reason_code: reasonCode,
      policy_id: 'default_deny',
      policy_hash: hashCanonical({ id: 'default_deny', v: '1.0.0' }),
      obligations: [],
      controls: [],
      regulations: [],
    };
  }
}

/**
 * Run simulation for a single input
 */
export function simulateDecision(
  input: SimulationInput,
  engine: SimulationPolicyEngine
): EvaluationResult {
  return engine.evaluate(input);
}

/**
 * Run simulation for multiple inputs
 */
export function simulateBatch(
  inputs: SimulationInput[],
  engine: SimulationPolicyEngine,
  onProgress?: (current: number, total: number) => void
): EvaluationResult[] {
  const results: EvaluationResult[] = [];

  for (let i = 0; i < inputs.length; i++) {
    results.push(engine.evaluate(inputs[i]));

    if (onProgress && (i % 100 === 0 || i === inputs.length - 1)) {
      onProgress(i + 1, inputs.length);
    }
  }

  return results;
}
