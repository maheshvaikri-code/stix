/**
 * STIX Simulation - Report Generator
 * Generate comprehensive simulation reports
 */

import type {
  SimulationResult,
  SimulationReport,
  ReportMetadata,
  ReportSummary,
  DecisionChanges,
  ObligationChanges,
  RiskAssessment,
  HighRiskItem,
  RiskLevel,
  SimulationOptions,
} from './types.js';
import type { PolicyPack } from './loadPolicies.js';

// =============================================================================
// REPORT GENERATION
// =============================================================================

/**
 * Build a complete simulation report
 */
export function buildReport(
  results: SimulationResult[],
  options: SimulationOptions,
  policyPack: PolicyPack
): SimulationReport {
  const metadata = buildMetadata(options, policyPack);
  const summary = buildSummary(results);
  const decisionChanges = buildDecisionChanges(results);
  const obligationChanges = buildObligationChanges(results);
  const riskAssessment = buildRiskAssessment(results);
  const highRiskItems = extractHighRiskItems(results);

  const report: SimulationReport = {
    metadata,
    summary,
    decision_changes: decisionChanges,
    obligation_changes: obligationChanges,
    risk_assessment: riskAssessment,
    high_risk_items: highRiskItems,
  };

  // Include detailed results if requested
  if (options.includeResults) {
    const maxResults = options.maxResults || 1000;
    report.results = results.slice(0, maxResults);
  }

  return report;
}

/**
 * Build report metadata
 */
function buildMetadata(options: SimulationOptions, policyPack: PolicyPack): ReportMetadata {
  return {
    generated_at: new Date().toISOString(),
    evidence_source: options.evidencePath,
    policy_source: options.policyPath,
    baseline_hash: options.baselineHash,
    time_window_start: options.since,
    time_window_end: options.until,
    engine_version: '1.0.0',
  };
}

/**
 * Build summary statistics
 */
function buildSummary(results: SimulationResult[]): ReportSummary {
  let decisionChangesCount = 0;
  let obligationChangesOnly = 0;
  let unchanged = 0;
  let approvalVolumeEstimate = 0;
  let highRiskBlocks = 0;

  for (const result of results) {
    if (result.delta.decision_changed) {
      decisionChangesCount++;

      // Count new QUARANTINE decisions
      if (result.simulated.decision === 'QUARANTINE') {
        approvalVolumeEstimate++;
      }

      // Count high-risk blocks
      if (
        result.delta.risk_level === 'HIGH' ||
        result.delta.risk_level === 'CRITICAL'
      ) {
        highRiskBlocks++;
      }
    } else if (result.delta.obligations_changed) {
      obligationChangesOnly++;
    } else {
      unchanged++;
    }
  }

  return {
    total_traces: results.length,
    decision_changes_count: decisionChangesCount,
    obligation_changes_only: obligationChangesOnly,
    unchanged,
    approval_volume_estimate: approvalVolumeEstimate,
    high_risk_blocks: highRiskBlocks,
  };
}

/**
 * Build decision changes breakdown
 */
function buildDecisionChanges(results: SimulationResult[]): DecisionChanges {
  const changes: DecisionChanges = {
    allow_to_deny: 0,
    allow_to_quarantine: 0,
    deny_to_allow: 0,
    deny_to_quarantine: 0,
    quarantine_to_allow: 0,
    quarantine_to_deny: 0,
  };

  for (const result of results) {
    if (!result.delta.decision_changed) continue;

    const from = result.recorded.decision;
    const to = result.simulated.decision;

    if (from === 'ALLOW' && to === 'DENY') changes.allow_to_deny++;
    if (from === 'ALLOW' && to === 'QUARANTINE') changes.allow_to_quarantine++;
    if (from === 'DENY' && to === 'ALLOW') changes.deny_to_allow++;
    if (from === 'DENY' && to === 'QUARANTINE') changes.deny_to_quarantine++;
    if (from === 'QUARANTINE' && to === 'ALLOW') changes.quarantine_to_allow++;
    if (from === 'QUARANTINE' && to === 'DENY') changes.quarantine_to_deny++;
  }

  return changes;
}

/**
 * Build obligation changes summary
 */
function buildObligationChanges(results: SimulationResult[]): ObligationChanges {
  const added: Record<string, number> = {};
  const removed: Record<string, number> = {};
  let totalChanged = 0;

  for (const result of results) {
    if (!result.delta.obligations_changed) continue;

    totalChanged++;

    for (const obligation of result.delta.obligations_added) {
      added[obligation] = (added[obligation] || 0) + 1;
    }

    for (const obligation of result.delta.obligations_removed) {
      removed[obligation] = (removed[obligation] || 0) + 1;
    }
  }

  return {
    total_changed: totalChanged,
    added,
    removed,
  };
}

/**
 * Build risk assessment
 */
function buildRiskAssessment(results: SimulationResult[]): RiskAssessment {
  const byLevel = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
  };

  for (const result of results) {
    switch (result.delta.risk_level) {
      case 'CRITICAL':
        byLevel.critical++;
        break;
      case 'HIGH':
        byLevel.high++;
        break;
      case 'MEDIUM':
        byLevel.medium++;
        break;
      case 'LOW':
        byLevel.low++;
        break;
    }
  }

  // Determine overall risk
  let overallRisk: RiskLevel = 'LOW';
  const riskFactors: string[] = [];

  if (byLevel.critical > 0) {
    overallRisk = 'CRITICAL';
    riskFactors.push(`${byLevel.critical} critical-risk changes (DENY→ALLOW or QUARANTINE→ALLOW)`);
  } else if (byLevel.high > 0) {
    overallRisk = 'HIGH';
    riskFactors.push(`${byLevel.high} high-risk changes (ALLOW→DENY)`);
  } else if (byLevel.medium > 0) {
    overallRisk = 'MEDIUM';
    riskFactors.push(`${byLevel.medium} medium-risk changes`);
  }

  // Additional risk factors
  const changedResults = results.filter(r => r.delta.decision_changed);
  if (changedResults.length > results.length * 0.1) {
    riskFactors.push(`High change rate: ${((changedResults.length / results.length) * 100).toFixed(1)}% of decisions affected`);
  }

  return {
    overall_risk: overallRisk,
    by_level: byLevel,
    risk_factors: riskFactors,
  };
}

/**
 * Extract high-risk items requiring attention
 */
function extractHighRiskItems(results: SimulationResult[], limit = 50): HighRiskItem[] {
  const highRisk = results.filter(
    r => r.delta.risk_level === 'HIGH' || r.delta.risk_level === 'CRITICAL'
  );

  return highRisk.slice(0, limit).map(r => ({
    trace_id: r.trace_id,
    timestamp: r.timestamp,
    change_type: r.delta.decision_change_type!,
    recorded_decision: r.recorded.decision,
    simulated_decision: r.simulated.decision,
    actor_id: 'unknown', // Would need input data
    action: 'unknown',
    resource_type: 'unknown',
    reason: getRiskReason(r),
  }));
}

/**
 * Get human-readable risk reason
 */
function getRiskReason(result: SimulationResult): string {
  const from = result.recorded.decision;
  const to = result.simulated.decision;

  if (from === 'DENY' && to === 'ALLOW') {
    return 'Previously blocked action would now be allowed';
  }
  if (from === 'QUARANTINE' && to === 'ALLOW') {
    return 'Action that required approval would now be auto-allowed';
  }
  if (from === 'ALLOW' && to === 'DENY') {
    return 'Previously allowed action would now be blocked';
  }
  if (from === 'ALLOW' && to === 'QUARANTINE') {
    return 'Action would now require approval';
  }

  return 'Decision changed';
}

// =============================================================================
// REPORT FORMATTING
// =============================================================================

/**
 * Format report as JSON
 */
export function formatReportAsJson(report: SimulationReport): string {
  return JSON.stringify(report, null, 2);
}

/**
 * Format report as Markdown
 */
export function formatReportAsMarkdown(report: SimulationReport): string {
  const lines: string[] = [];

  lines.push('# STIX Simulation Report');
  lines.push('');
  lines.push(`Generated: ${report.metadata.generated_at}`);
  lines.push(`Evidence: ${report.metadata.evidence_source}`);
  lines.push(`Policies: ${report.metadata.policy_source}`);
  lines.push('');

  // Summary
  lines.push('## Summary');
  lines.push('');
  lines.push(`| Metric | Value |`);
  lines.push(`|--------|-------|`);
  lines.push(`| Total Traces | ${report.summary.total_traces} |`);
  lines.push(`| Decision Changes | ${report.summary.decision_changes_count} |`);
  lines.push(`| Obligation Changes Only | ${report.summary.obligation_changes_only} |`);
  lines.push(`| Unchanged | ${report.summary.unchanged} |`);
  lines.push(`| Approval Volume Estimate | ${report.summary.approval_volume_estimate} |`);
  lines.push(`| High-Risk Blocks | ${report.summary.high_risk_blocks} |`);
  lines.push('');

  // Risk Assessment
  lines.push('## Risk Assessment');
  lines.push('');
  lines.push(`**Overall Risk: ${report.risk_assessment.overall_risk}**`);
  lines.push('');
  lines.push('| Risk Level | Count |');
  lines.push('|------------|-------|');
  lines.push(`| Critical | ${report.risk_assessment.by_level.critical} |`);
  lines.push(`| High | ${report.risk_assessment.by_level.high} |`);
  lines.push(`| Medium | ${report.risk_assessment.by_level.medium} |`);
  lines.push(`| Low | ${report.risk_assessment.by_level.low} |`);
  lines.push('');

  if (report.risk_assessment.risk_factors.length > 0) {
    lines.push('### Risk Factors');
    lines.push('');
    for (const factor of report.risk_assessment.risk_factors) {
      lines.push(`- ${factor}`);
    }
    lines.push('');
  }

  // Decision Changes
  lines.push('## Decision Changes');
  lines.push('');
  lines.push('| Change Type | Count |');
  lines.push('|-------------|-------|');
  lines.push(`| ALLOW → DENY | ${report.decision_changes.allow_to_deny} |`);
  lines.push(`| ALLOW → QUARANTINE | ${report.decision_changes.allow_to_quarantine} |`);
  lines.push(`| DENY → ALLOW | ${report.decision_changes.deny_to_allow} |`);
  lines.push(`| DENY → QUARANTINE | ${report.decision_changes.deny_to_quarantine} |`);
  lines.push(`| QUARANTINE → ALLOW | ${report.decision_changes.quarantine_to_allow} |`);
  lines.push(`| QUARANTINE → DENY | ${report.decision_changes.quarantine_to_deny} |`);
  lines.push('');

  // Obligation Changes
  if (report.obligation_changes.total_changed > 0) {
    lines.push('## Obligation Changes');
    lines.push('');
    lines.push(`Total traces with obligation changes: ${report.obligation_changes.total_changed}`);
    lines.push('');

    if (Object.keys(report.obligation_changes.added).length > 0) {
      lines.push('### Obligations Added');
      lines.push('');
      for (const [type, count] of Object.entries(report.obligation_changes.added)) {
        lines.push(`- ${type}: ${count}`);
      }
      lines.push('');
    }

    if (Object.keys(report.obligation_changes.removed).length > 0) {
      lines.push('### Obligations Removed');
      lines.push('');
      for (const [type, count] of Object.entries(report.obligation_changes.removed)) {
        lines.push(`- ${type}: ${count}`);
      }
      lines.push('');
    }
  }

  // High-Risk Items
  if (report.high_risk_items.length > 0) {
    lines.push('## High-Risk Items Requiring Attention');
    lines.push('');
    lines.push('| Trace ID | Change | Reason |');
    lines.push('|----------|--------|--------|');
    for (const item of report.high_risk_items.slice(0, 20)) {
      lines.push(`| ${item.trace_id.substring(0, 16)}... | ${item.recorded_decision}→${item.simulated_decision} | ${item.reason} |`);
    }
    if (report.high_risk_items.length > 20) {
      lines.push(`| ... | ... | ${report.high_risk_items.length - 20} more items |`);
    }
    lines.push('');
  }

  return lines.join('\n');
}

/**
 * Format report as table (for CLI)
 */
export function formatReportAsTable(report: SimulationReport): string {
  const lines: string[] = [];

  lines.push('╔══════════════════════════════════════════════════════════════╗');
  lines.push('║                  STIX SIMULATION REPORT                       ║');
  lines.push('╠══════════════════════════════════════════════════════════════╣');
  lines.push(`║ Total Traces:      ${report.summary.total_traces.toString().padEnd(42)}║`);
  lines.push(`║ Decision Changes:  ${report.summary.decision_changes_count.toString().padEnd(42)}║`);
  lines.push(`║ Unchanged:         ${report.summary.unchanged.toString().padEnd(42)}║`);
  lines.push(`║ Overall Risk:      ${report.risk_assessment.overall_risk.padEnd(42)}║`);
  lines.push('╠══════════════════════════════════════════════════════════════╣');
  lines.push('║ DECISION CHANGES                                              ║');
  lines.push('╠══════════════════════════════════════════════════════════════╣');
  lines.push(`║ ALLOW → DENY:       ${report.decision_changes.allow_to_deny.toString().padEnd(41)}║`);
  lines.push(`║ ALLOW → QUARANTINE: ${report.decision_changes.allow_to_quarantine.toString().padEnd(41)}║`);
  lines.push(`║ DENY → ALLOW:       ${report.decision_changes.deny_to_allow.toString().padEnd(41)}║`);
  lines.push('╚══════════════════════════════════════════════════════════════╝');

  return lines.join('\n');
}
