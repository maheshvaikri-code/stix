/**
 * STIX Replay Tool Types
 * Type definitions for replay inputs, outputs, and reports
 */

import type { DecisionKind, Actor, Resource, Context } from '@stix/shared';

// =============================================================================
// REPLAY INPUT
// =============================================================================

/**
 * Recorded decision extracted from evidence bundle
 */
export interface RecordedDecision {
  /** Trace ID from original decision */
  trace_id: string;
  /** Actor from original request */
  actor: Actor;
  /** Action from original request */
  action: string;
  /** Resource from original request */
  resource: Resource;
  /** Context from original request */
  context: Context;
  /** Timestamp of original decision */
  timestamp: string;
  /** Recorded decision details */
  recorded: {
    decision: DecisionKind;
    reason_code: string;
    obligations: string[];
    policy_id: string;
    policy_hash: string;
  };
}

// =============================================================================
// REPLAY RESULT
// =============================================================================

/**
 * Replay status
 */
export type ReplayStatus = 'MATCH' | 'DRIFT' | 'ERROR';

/**
 * Result of replaying a single decision
 */
export interface ReplayResult {
  /** Replay status */
  status: ReplayStatus;
  /** Trace ID */
  trace_id: string;
  /** Timestamp */
  timestamp: string;
  /** Recorded decision details */
  recorded: {
    decision: DecisionKind;
    reason_code: string;
    obligations: string[];
    policy_id: string;
    policy_hash: string;
  };
  /** Replayed decision details */
  replayed: {
    decision: DecisionKind;
    reason_code: string;
    obligations: string[];
    policy_id: string;
    policy_hash: string;
  } | null;
  /** Differences between recorded and replayed */
  diff: ReplayDiff | null;
  /** Diagnostic information */
  diagnostics: ReplayDiagnostics;
}

/**
 * Differences between recorded and replayed decisions
 */
export interface ReplayDiff {
  /** Decision changed */
  decision_changed: boolean;
  /** Reason code changed */
  reason_code_changed: boolean;
  /** Policy changed */
  policy_changed: boolean;
  /** Obligations added in replay */
  obligations_added: string[];
  /** Obligations removed in replay */
  obligations_removed: string[];
}

/**
 * Diagnostic information for replay
 */
export interface ReplayDiagnostics {
  /** Policy found for hash */
  policy_found: boolean;
  /** Policy hash matched */
  policy_hash_matched: boolean;
  /** Evaluation successful */
  evaluation_successful: boolean;
  /** Error message if any */
  error_message?: string;
  /** Policy lookup details */
  policy_lookup?: {
    requested_hash: string;
    found_hash?: string;
    found_policy_id?: string;
  };
}

// =============================================================================
// REPLAY REPORT
// =============================================================================

/**
 * Complete replay report
 */
export interface ReplayReport {
  /** Report metadata */
  metadata: ReplayReportMetadata;
  /** Individual replay results */
  results: ReplayResult[];
  /** Summary statistics */
  summary: ReplaySummary;
}

/**
 * Replay report metadata
 */
export interface ReplayReportMetadata {
  /** Report generation timestamp */
  generated_at: string;
  /** Bundle source */
  bundle_source: string;
  /** Policy source */
  policy_source: string;
  /** Strict mode enabled */
  strict_mode: boolean;
  /** Engine version */
  engine_version: string;
}

/**
 * Replay summary statistics
 */
export interface ReplaySummary {
  /** Total traces replayed */
  total: number;
  /** Matches (identical) */
  matches: number;
  /** Drifts (differences) */
  drifts: number;
  /** Errors */
  errors: number;
  /** Match rate percentage */
  match_rate: number;
}

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Replay configuration options
 */
export interface ReplayOptions {
  /** Path to evidence bundle(s) */
  bundlePath: string;
  /** Path to policy pack */
  policyPath: string;
  /** Verify evidence integrity before replay */
  verify?: boolean;
  /** Optional public key PEM path for signature verification */
  verifyKeyPath?: string;
  /** Optional key ID filter for signature verification */
  verifyKeyId?: string;
  /** Require exact reason_code match */
  strict?: boolean;
  /** Output format */
  format?: 'json' | 'markdown' | 'table';
  /** Verbose output */
  verbose?: boolean;
}
