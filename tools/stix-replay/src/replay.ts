/**
 * STIX Replay - Core Replay Logic
 * Replay recorded decisions and compare results
 */

import type { RecordedDecision, ReplayResult, ReplayStatus, ReplayDiff, ReplayDiagnostics } from './types.js';
import type { ReplayEngine, EvaluationOutput } from './engine.js';

// =============================================================================
// REPLAY FUNCTIONS
// =============================================================================

/**
 * Replay a single recorded decision
 */
export function replayDecision(
  recorded: RecordedDecision,
  engine: ReplayEngine,
  options: ReplayCompareOptions = {}
): ReplayResult {
  const diagnostics: ReplayDiagnostics = {
    policy_found: false,
    policy_hash_matched: false,
    evaluation_successful: false,
  };

  try {
    // Evaluate with current policies
    const replayed = engine.evaluate({
      actor: recorded.actor,
      action: recorded.action,
      resource: recorded.resource,
      context: recorded.context,
    });

    diagnostics.evaluation_successful = true;

    // Check policy hash match
    const policyPack = engine.getPolicyPack();
    const requestedHash = normalizeHash(recorded.recorded.policy_hash);
    const replayedHash = normalizeHash(replayed.policy_hash);
    diagnostics.policy_found = requestedHash
      ? policyPack.hashIndex.has(requestedHash) || policyPack.hashIndex.has(stripHashPrefix(requestedHash))
      : false;
    diagnostics.policy_hash_matched = Boolean(
      requestedHash && replayedHash && requestedHash === replayedHash
    );
    diagnostics.policy_lookup = {
      requested_hash: recorded.recorded.policy_hash,
      found_hash: replayed.policy_hash,
      found_policy_id: replayed.policy_id,
    };

    // Compare results
    const diff = computeDiff(recorded.recorded, replayed);
    const status = determineStatus(diff, options);

    return {
      status,
      trace_id: recorded.trace_id,
      timestamp: recorded.timestamp,
      recorded: recorded.recorded,
      replayed: {
        decision: replayed.decision,
        reason_code: replayed.reason_code,
        obligations: replayed.obligations,
        policy_id: replayed.policy_id,
        policy_hash: replayed.policy_hash,
      },
      diff,
      diagnostics,
    };
  } catch (error) {
    diagnostics.evaluation_successful = false;
    diagnostics.error_message = (error as Error).message;

    return {
      status: 'ERROR',
      trace_id: recorded.trace_id,
      timestamp: recorded.timestamp,
      recorded: recorded.recorded,
      replayed: null,
      diff: null,
      diagnostics,
    };
  }
}

/**
 * Replay multiple recorded decisions
 */
export function replayBatch(
  decisions: RecordedDecision[],
  engine: ReplayEngine,
  options: ReplayCompareOptions = {},
  progressCallback?: (current: number, total: number) => void
): ReplayResult[] {
  const results: ReplayResult[] = [];

  for (let i = 0; i < decisions.length; i++) {
    const result = replayDecision(decisions[i], engine, options);
    results.push(result);

    if (progressCallback) {
      progressCallback(i + 1, decisions.length);
    }
  }

  return results;
}

// =============================================================================
// COMPARISON OPTIONS
// =============================================================================

export interface ReplayCompareOptions {
  /** Require exact reason_code match */
  strictReasonCode?: boolean;
  /** Require exact obligations match */
  strictObligations?: boolean;
  /** Require policy hash match */
  strictPolicyHash?: boolean;
  /** Ignore obligation order */
  ignoreObligationOrder?: boolean;
}

// =============================================================================
// DIFF COMPUTATION
// =============================================================================

/**
 * Compute differences between recorded and replayed
 */
function computeDiff(
  recorded: RecordedDecision['recorded'],
  replayed: EvaluationOutput
): ReplayDiff {
  const recordedObligations = new Set(recorded.obligations);
  const replayedObligations = new Set(replayed.obligations);

  const obligationsAdded = replayed.obligations.filter(o => !recordedObligations.has(o));
  const obligationsRemoved = recorded.obligations.filter(o => !replayedObligations.has(o));

  return {
    decision_changed: recorded.decision !== replayed.decision,
    reason_code_changed: recorded.reason_code !== replayed.reason_code,
    policy_changed: Boolean(
      recorded.policy_id !== replayed.policy_id ||
      (
        recorded.policy_hash &&
        replayed.policy_hash &&
        normalizeHash(recorded.policy_hash) !== normalizeHash(replayed.policy_hash)
      )
    ),
    obligations_added: obligationsAdded,
    obligations_removed: obligationsRemoved,
  };
}

/**
 * Determine replay status from diff
 */
function determineStatus(
  diff: ReplayDiff,
  options: ReplayCompareOptions
): ReplayStatus {
  // Decision change is always drift
  if (diff.decision_changed) {
    return 'DRIFT';
  }

  // Check strict options
  if (options.strictReasonCode && diff.reason_code_changed) {
    return 'DRIFT';
  }

  if (options.strictObligations) {
    if (diff.obligations_added.length > 0 || diff.obligations_removed.length > 0) {
      return 'DRIFT';
    }
  }

  if (options.strictPolicyHash && diff.policy_changed) {
    return 'DRIFT';
  }

  return 'MATCH';
}

// =============================================================================
// FILTERING
// =============================================================================

/**
 * Filter results by status
 */
export function filterByStatus(results: ReplayResult[], status: ReplayStatus): ReplayResult[] {
  return results.filter(r => r.status === status);
}

/**
 * Get only drifted results
 */
export function getDriftedResults(results: ReplayResult[]): ReplayResult[] {
  return filterByStatus(results, 'DRIFT');
}

/**
 * Get only matched results
 */
export function getMatchedResults(results: ReplayResult[]): ReplayResult[] {
  return filterByStatus(results, 'MATCH');
}

/**
 * Get only errored results
 */
export function getErroredResults(results: ReplayResult[]): ReplayResult[] {
  return filterByStatus(results, 'ERROR');
}

/**
 * Filter results by decision change type
 */
export function filterByDecisionChange(
  results: ReplayResult[],
  from: string,
  to: string
): ReplayResult[] {
  return results.filter(
    r =>
      r.diff?.decision_changed &&
      r.recorded.decision === from &&
      r.replayed?.decision === to
  );
}

// =============================================================================
// STATISTICS
// =============================================================================

export interface ReplayStats {
  total: number;
  matches: number;
  drifts: number;
  errors: number;
  matchRate: number;
  driftRate: number;
  errorRate: number;
  decisionChanges: {
    allowToDeny: number;
    allowToQuarantine: number;
    denyToAllow: number;
    denyToQuarantine: number;
    quarantineToAllow: number;
    quarantineToDeny: number;
  };
}

/**
 * Calculate replay statistics
 */
export function calculateStats(results: ReplayResult[]): ReplayStats {
  const total = results.length;
  const matches = results.filter(r => r.status === 'MATCH').length;
  const drifts = results.filter(r => r.status === 'DRIFT').length;
  const errors = results.filter(r => r.status === 'ERROR').length;

  const decisionChanges = {
    allowToDeny: 0,
    allowToQuarantine: 0,
    denyToAllow: 0,
    denyToQuarantine: 0,
    quarantineToAllow: 0,
    quarantineToDeny: 0,
  };

  for (const result of results) {
    if (!result.diff?.decision_changed || !result.replayed) continue;

    const from = result.recorded.decision;
    const to = result.replayed.decision;

    if (from === 'ALLOW' && to === 'DENY') decisionChanges.allowToDeny++;
    if (from === 'ALLOW' && to === 'QUARANTINE') decisionChanges.allowToQuarantine++;
    if (from === 'DENY' && to === 'ALLOW') decisionChanges.denyToAllow++;
    if (from === 'DENY' && to === 'QUARANTINE') decisionChanges.denyToQuarantine++;
    if (from === 'QUARANTINE' && to === 'ALLOW') decisionChanges.quarantineToAllow++;
    if (from === 'QUARANTINE' && to === 'DENY') decisionChanges.quarantineToDeny++;
  }

  return {
    total,
    matches,
    drifts,
    errors,
    matchRate: total > 0 ? (matches / total) * 100 : 0,
    driftRate: total > 0 ? (drifts / total) * 100 : 0,
    errorRate: total > 0 ? (errors / total) * 100 : 0,
    decisionChanges,
  };
}

function normalizeHash(hash: string): string {
  if (!hash) return '';
  return hash.startsWith('sha256:') ? hash : `sha256:${hash}`;
}

function stripHashPrefix(hash: string): string {
  return hash.startsWith('sha256:') ? hash.slice('sha256:'.length) : hash;
}
