/**
 * STIX Simulation - Difference Calculator
 * Calculate deltas between recorded and simulated decisions
 */

import type { DecisionKind } from '@stix/shared';
import type {
  SimulationInput,
  SimulationResult,
  SimulationDelta,
  DecisionChangeType,
  RiskLevel,
} from './types.js';
import type { EvaluationResult } from './evaluate.js';

// =============================================================================
// DIFF CALCULATION
// =============================================================================

/**
 * Calculate difference between recorded and simulated decision
 */
export function calculateDiff(
  input: SimulationInput,
  simulated: EvaluationResult
): SimulationResult {
  const delta = calculateDelta(
    input.recorded_decision,
    simulated.decision,
    input.recorded_obligations,
    simulated.obligations
  );

  return {
    trace_id: input.trace_id,
    timestamp: input.timestamp,
    recorded: {
      decision: input.recorded_decision,
      policy_id: input.recorded_policy_id,
      policy_hash: input.recorded_policy_hash,
      obligations: input.recorded_obligations,
    },
    simulated: {
      decision: simulated.decision,
      policy_id: simulated.policy_id,
      policy_hash: simulated.policy_hash,
      obligations: simulated.obligations,
      reason_code: simulated.reason_code,
    },
    delta,
  };
}

/**
 * Calculate delta between recorded and simulated values
 */
function calculateDelta(
  recordedDecision: DecisionKind,
  simulatedDecision: DecisionKind,
  recordedObligations: string[],
  simulatedObligations: string[]
): SimulationDelta {
  const decisionChanged = recordedDecision !== simulatedDecision;
  const decisionChangeType = decisionChanged
    ? getDecisionChangeType(recordedDecision, simulatedDecision)
    : null;

  // Calculate obligation changes
  const recordedSet = new Set(recordedObligations);
  const simulatedSet = new Set(simulatedObligations);

  const obligationsAdded = simulatedObligations.filter(o => !recordedSet.has(o));
  const obligationsRemoved = recordedObligations.filter(o => !simulatedSet.has(o));
  const obligationsChanged = obligationsAdded.length > 0 || obligationsRemoved.length > 0;

  // Calculate risk level
  const riskLevel = calculateRiskLevel(decisionChangeType, obligationsAdded);

  return {
    decision_changed: decisionChanged,
    decision_change_type: decisionChangeType,
    obligations_changed: obligationsChanged,
    obligations_added: obligationsAdded,
    obligations_removed: obligationsRemoved,
    risk_level: riskLevel,
  };
}

/**
 * Get the type of decision change
 */
function getDecisionChangeType(
  from: DecisionKind,
  to: DecisionKind
): DecisionChangeType {
  const key = `${from}_TO_${to}` as DecisionChangeType;
  return key;
}

/**
 * Calculate risk level of a change
 */
function calculateRiskLevel(
  changeType: DecisionChangeType | null,
  obligationsAdded: string[]
): RiskLevel {
  // No change = LOW risk
  if (!changeType) {
    // Check if new obligations are restrictive
    const hasRestrictiveObligation = obligationsAdded.some(o =>
      ['MASK_PII', 'REDACT_FIELDS', 'REQUIRE_APPROVAL', 'DUAL_CONTROL'].includes(o)
    );
    return hasRestrictiveObligation ? 'LOW' : 'LOW';
  }

  // Decision changes by severity
  switch (changeType) {
    // Opening up (potentially risky from security perspective)
    case 'DENY_TO_ALLOW':
    case 'QUARANTINE_TO_ALLOW':
      return 'CRITICAL';

    // Blocking (may break workflows)
    case 'ALLOW_TO_DENY':
      return 'HIGH';

    // Adding friction
    case 'ALLOW_TO_QUARANTINE':
      return 'MEDIUM';

    // Reducing friction (usually safer)
    case 'DENY_TO_QUARANTINE':
    case 'QUARANTINE_TO_DENY':
      return 'MEDIUM';

    default:
      return 'LOW';
  }
}

// =============================================================================
// BATCH DIFF CALCULATION
// =============================================================================

/**
 * Calculate diffs for a batch of inputs and results
 */
export function calculateBatchDiffs(
  inputs: SimulationInput[],
  evaluationResults: EvaluationResult[]
): SimulationResult[] {
  if (inputs.length !== evaluationResults.length) {
    throw new Error('Input and result arrays must have same length');
  }

  return inputs.map((input, i) => calculateDiff(input, evaluationResults[i]));
}

// =============================================================================
// DIFF FILTERING
// =============================================================================

/**
 * Filter results to only those with changes
 */
export function filterChangedResults(results: SimulationResult[]): SimulationResult[] {
  return results.filter(r => r.delta.decision_changed || r.delta.obligations_changed);
}

/**
 * Filter results by risk level
 */
export function filterByRiskLevel(
  results: SimulationResult[],
  minRisk: RiskLevel
): SimulationResult[] {
  const riskOrder: Record<RiskLevel, number> = {
    LOW: 0,
    MEDIUM: 1,
    HIGH: 2,
    CRITICAL: 3,
  };

  const minRiskValue = riskOrder[minRisk];
  return results.filter(r => riskOrder[r.delta.risk_level] >= minRiskValue);
}

/**
 * Filter results by decision change type
 */
export function filterByChangeType(
  results: SimulationResult[],
  changeTypes: DecisionChangeType[]
): SimulationResult[] {
  const typeSet = new Set(changeTypes);
  return results.filter(r =>
    r.delta.decision_change_type && typeSet.has(r.delta.decision_change_type)
  );
}

// =============================================================================
// DIFF STATISTICS
// =============================================================================

/**
 * Get statistics about diffs
 */
export function getDiffStats(results: SimulationResult[]): {
  total: number;
  changed: number;
  decisionChanged: number;
  unchanged: number;
  byChangeType: Record<string, number>;
  byRiskLevel: Record<RiskLevel, number>;
  obligationChanges: number;
} {
  const stats = {
    total: results.length,
    changed: 0,
    decisionChanged: 0,
    unchanged: 0,
    byChangeType: {} as Record<string, number>,
    byRiskLevel: { LOW: 0, MEDIUM: 0, HIGH: 0, CRITICAL: 0 } as Record<RiskLevel, number>,
    obligationChanges: 0,
  };

  for (const result of results) {
    if (result.delta.decision_changed) {
      stats.changed++;
      stats.decisionChanged++;
      const changeType = result.delta.decision_change_type!;
      stats.byChangeType[changeType] = (stats.byChangeType[changeType] || 0) + 1;
    } else {
      stats.unchanged++;
    }

    stats.byRiskLevel[result.delta.risk_level]++;

    if (result.delta.obligations_changed) {
      stats.obligationChanges++;
    }
  }

  return stats;
}
