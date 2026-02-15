/**
 * STIX Simulation Engine Types
 * Type definitions for simulation inputs, outputs, and reports
 */

import type { DecisionKind, Actor, Resource, Context, Obligation } from '@stix/shared';

// =============================================================================
// SIMULATION INPUT
// =============================================================================

/**
 * Canonical simulation input derived from evidence DECISION event
 */
export interface SimulationInput {
  /** Trace ID from original decision */
  trace_id: string;
  /** Actor who performed the action */
  actor: Actor;
  /** Action that was performed */
  action: string;
  /** Resource that was accessed */
  resource: Resource;
  /** Context at time of decision */
  context: Context;
  /** Recorded decision outcome */
  recorded_decision: DecisionKind;
  /** Hash of policy used for recorded decision */
  recorded_policy_hash: string;
  /** Policy ID used for recorded decision */
  recorded_policy_id: string;
  /** Obligations from recorded decision */
  recorded_obligations: string[];
  /** Original timestamp */
  timestamp: string;
}

// =============================================================================
// SIMULATION RESULT
// =============================================================================

/**
 * Result of simulating a single decision
 */
export interface SimulationResult {
  /** Trace ID being simulated */
  trace_id: string;
  /** Original timestamp */
  timestamp: string;
  /** Recorded decision details */
  recorded: {
    decision: DecisionKind;
    policy_id: string;
    policy_hash: string;
    obligations: string[];
  };
  /** Simulated decision details */
  simulated: {
    decision: DecisionKind;
    policy_id: string;
    policy_hash: string;
    obligations: string[];
    reason_code: string;
  };
  /** Delta between recorded and simulated */
  delta: SimulationDelta;
}

/**
 * Delta between recorded and simulated decisions
 */
export interface SimulationDelta {
  /** Whether the decision outcome changed */
  decision_changed: boolean;
  /** Type of decision change */
  decision_change_type: DecisionChangeType | null;
  /** Whether obligations changed */
  obligations_changed: boolean;
  /** Obligations added */
  obligations_added: string[];
  /** Obligations removed */
  obligations_removed: string[];
  /** Risk level of the change */
  risk_level: RiskLevel;
}

/**
 * Types of decision changes
 */
export type DecisionChangeType =
  | 'ALLOW_TO_DENY'
  | 'ALLOW_TO_QUARANTINE'
  | 'DENY_TO_ALLOW'
  | 'DENY_TO_QUARANTINE'
  | 'QUARANTINE_TO_ALLOW'
  | 'QUARANTINE_TO_DENY';

/**
 * Risk levels for changes
 */
export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

// =============================================================================
// SIMULATION REPORT
// =============================================================================

/**
 * Complete simulation report
 */
export interface SimulationReport {
  /** Report metadata */
  metadata: ReportMetadata;
  /** Summary statistics */
  summary: ReportSummary;
  /** Decision change breakdown */
  decision_changes: DecisionChanges;
  /** Obligation changes */
  obligation_changes: ObligationChanges;
  /** Risk assessment */
  risk_assessment: RiskAssessment;
  /** Individual results (optional, can be large) */
  results?: SimulationResult[];
  /** High-risk items requiring attention */
  high_risk_items: HighRiskItem[];
}

/**
 * Report metadata
 */
export interface ReportMetadata {
  /** Report generation timestamp */
  generated_at: string;
  /** Evidence source path */
  evidence_source: string;
  /** Policy pack path */
  policy_source: string;
  /** Baseline policy hash (if comparing) */
  baseline_hash?: string;
  /** Time window start */
  time_window_start?: string;
  /** Time window end */
  time_window_end?: string;
  /** Simulation engine version */
  engine_version: string;
}

/**
 * Summary statistics
 */
export interface ReportSummary {
  /** Total traces evaluated */
  total_traces: number;
  /** Traces with decision changes */
  decision_changes_count: number;
  /** Traces with obligation changes only */
  obligation_changes_only: number;
  /** Unchanged traces */
  unchanged: number;
  /** Estimated approval volume (QUARANTINE count) */
  approval_volume_estimate: number;
  /** High-risk blocks count */
  high_risk_blocks: number;
}

/**
 * Decision change breakdown
 */
export interface DecisionChanges {
  allow_to_deny: number;
  allow_to_quarantine: number;
  deny_to_allow: number;
  deny_to_quarantine: number;
  quarantine_to_allow: number;
  quarantine_to_deny: number;
}

/**
 * Obligation change summary
 */
export interface ObligationChanges {
  /** Total traces with obligation changes */
  total_changed: number;
  /** Obligations added (type -> count) */
  added: Record<string, number>;
  /** Obligations removed (type -> count) */
  removed: Record<string, number>;
}

/**
 * Risk assessment summary
 */
export interface RiskAssessment {
  /** Overall risk level */
  overall_risk: RiskLevel;
  /** Count by risk level */
  by_level: {
    critical: number;
    high: number;
    medium: number;
    low: number;
  };
  /** Risk factors identified */
  risk_factors: string[];
}

/**
 * High-risk item requiring attention
 */
export interface HighRiskItem {
  trace_id: string;
  timestamp: string;
  change_type: DecisionChangeType;
  recorded_decision: DecisionKind;
  simulated_decision: DecisionKind;
  actor_id: string;
  action: string;
  resource_type: string;
  reason: string;
}

// =============================================================================
// CONFIGURATION
// =============================================================================

/**
 * Simulation configuration options
 */
export interface SimulationOptions {
  /** Path to evidence bundles */
  evidencePath: string;
  /** Path to candidate policy pack */
  policyPath: string;
  /** Baseline policy hash (optional) */
  baselineHash?: string;
  /** Time window start (ISO string) */
  since?: string;
  /** Time window end (ISO string) */
  until?: string;
  /** Require both DECISION and OUTCOME events */
  strict?: boolean;
  /** Output format */
  format?: 'json' | 'markdown' | 'table';
  /** Include full results in report */
  includeResults?: boolean;
  /** Maximum results to include */
  maxResults?: number;
  /** Verbose output */
  verbose?: boolean;
}
