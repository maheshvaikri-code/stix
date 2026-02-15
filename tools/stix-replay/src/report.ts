/**
 * STIX Replay - Report Generator
 * Generate comprehensive replay reports
 */

import type {
  ReplayResult,
  ReplayReport,
  ReplayReportMetadata,
  ReplaySummary,
  ReplayOptions,
} from './types.js';
import type { ReplayStats } from './replay.js';
import type { LoadedPolicyPack } from './policyLoader.js';

// =============================================================================
// REPORT GENERATION
// =============================================================================

/**
 * Build a complete replay report
 */
export function buildReport(
  results: ReplayResult[],
  options: ReplayOptions,
  policyPack: LoadedPolicyPack,
  stats: ReplayStats
): ReplayReport {
  const metadata: ReplayReportMetadata = {
    generated_at: new Date().toISOString(),
    bundle_source: options.bundlePath,
    policy_source: options.policyPath,
    strict_mode: options.strict || false,
    engine_version: '1.0.0',
  };

  const summary: ReplaySummary = {
    total: stats.total,
    matches: stats.matches,
    drifts: stats.drifts,
    errors: stats.errors,
    match_rate: stats.matchRate,
  };

  return {
    metadata,
    results,
    summary,
  };
}

// =============================================================================
// REPORT FORMATTING
// =============================================================================

/**
 * Format report as JSON
 */
export function formatReportAsJson(report: ReplayReport): string {
  return JSON.stringify(report, null, 2);
}

/**
 * Format report as Markdown
 */
export function formatReportAsMarkdown(report: ReplayReport): string {
  const lines: string[] = [];

  lines.push('# STIX Replay Report');
  lines.push('');
  lines.push(`Generated: ${report.metadata.generated_at}`);
  lines.push(`Bundles: ${report.metadata.bundle_source}`);
  lines.push(`Policies: ${report.metadata.policy_source}`);
  lines.push(`Strict Mode: ${report.metadata.strict_mode ? 'Yes' : 'No'}`);
  lines.push('');

  // Summary
  lines.push('## Summary');
  lines.push('');
  lines.push('| Metric | Value |');
  lines.push('|--------|-------|');
  lines.push(`| Total Traces | ${report.summary.total} |`);
  lines.push(`| Matches | ${report.summary.matches} |`);
  lines.push(`| Drifts | ${report.summary.drifts} |`);
  lines.push(`| Errors | ${report.summary.errors} |`);
  lines.push(`| Match Rate | ${report.summary.match_rate.toFixed(1)}% |`);
  lines.push('');

  // Status breakdown
  const statusEmoji = {
    MATCH: ':white_check_mark:',
    DRIFT: ':warning:',
    ERROR: ':x:',
  };

  lines.push('## Status Breakdown');
  lines.push('');
  lines.push(`- ${statusEmoji.MATCH} **MATCH**: ${report.summary.matches} traces replayed identically`);
  lines.push(`- ${statusEmoji.DRIFT} **DRIFT**: ${report.summary.drifts} traces with different decisions`);
  lines.push(`- ${statusEmoji.ERROR} **ERROR**: ${report.summary.errors} traces failed to replay`);
  lines.push('');

  // Drifted results
  const drifted = report.results.filter(r => r.status === 'DRIFT');
  if (drifted.length > 0) {
    lines.push('## Drifted Decisions');
    lines.push('');
    lines.push('| Trace ID | Recorded | Replayed | Reason Code |');
    lines.push('|----------|----------|----------|-------------|');

    for (const result of drifted.slice(0, 50)) {
      const traceShort = result.trace_id.substring(0, 16) + '...';
      const recorded = result.recorded.decision;
      const replayed = result.replayed?.decision || 'N/A';
      const reason = result.replayed?.reason_code || result.diagnostics.error_message || '';

      lines.push(`| ${traceShort} | ${recorded} | ${replayed} | ${reason} |`);
    }

    if (drifted.length > 50) {
      lines.push(`| ... | ... | ... | ${drifted.length - 50} more drifts |`);
    }
    lines.push('');
  }

  // Error results
  const errors = report.results.filter(r => r.status === 'ERROR');
  if (errors.length > 0) {
    lines.push('## Errors');
    lines.push('');
    lines.push('| Trace ID | Error |');
    lines.push('|----------|-------|');

    for (const result of errors.slice(0, 20)) {
      const traceShort = result.trace_id.substring(0, 16) + '...';
      const error = result.diagnostics.error_message || 'Unknown error';
      lines.push(`| ${traceShort} | ${error} |`);
    }

    if (errors.length > 20) {
      lines.push(`| ... | ${errors.length - 20} more errors |`);
    }
    lines.push('');
  }

  // Recommendations
  lines.push('## Recommendations');
  lines.push('');

  if (report.summary.match_rate === 100) {
    lines.push('- :white_check_mark: All decisions replay identically. Policy is stable.');
  } else if (report.summary.match_rate >= 95) {
    lines.push('- Minor drift detected. Review drifted decisions before deployment.');
  } else if (report.summary.match_rate >= 80) {
    lines.push('- Significant drift detected. Investigate policy changes carefully.');
  } else {
    lines.push('- :warning: Major drift detected! Do not deploy without thorough review.');
  }

  if (report.summary.errors > 0) {
    lines.push(`- ${report.summary.errors} traces failed to replay. Check policy coverage.`);
  }

  return lines.join('\n');
}

/**
 * Format report as table (for CLI)
 */
export function formatReportAsTable(report: ReplayReport): string {
  const lines: string[] = [];

  lines.push('╔══════════════════════════════════════════════════════════════╗');
  lines.push('║                    STIX REPLAY REPORT                        ║');
  lines.push('╠══════════════════════════════════════════════════════════════╣');
  lines.push(`║ Total Traces:      ${report.summary.total.toString().padEnd(42)}║`);
  lines.push(`║ Matches:           ${report.summary.matches.toString().padEnd(42)}║`);
  lines.push(`║ Drifts:            ${report.summary.drifts.toString().padEnd(42)}║`);
  lines.push(`║ Errors:            ${report.summary.errors.toString().padEnd(42)}║`);
  lines.push(`║ Match Rate:        ${(report.summary.match_rate.toFixed(1) + '%').padEnd(42)}║`);
  lines.push('╠══════════════════════════════════════════════════════════════╣');

  // Status indicator
  let statusLine: string;
  if (report.summary.match_rate === 100) {
    statusLine = '✓ ALL DECISIONS MATCH - Safe to deploy';
  } else if (report.summary.match_rate >= 95) {
    statusLine = '⚠ Minor drift detected - Review before deploy';
  } else if (report.summary.match_rate >= 80) {
    statusLine = '⚠ Significant drift - Investigate carefully';
  } else {
    statusLine = '✗ MAJOR DRIFT - Do not deploy!';
  }

  lines.push(`║ ${statusLine.padEnd(61)}║`);
  lines.push('╚══════════════════════════════════════════════════════════════╝');

  return lines.join('\n');
}

// =============================================================================
// DETAILED DIFF OUTPUT
// =============================================================================

/**
 * Format detailed diff for a single result
 */
export function formatDetailedDiff(result: ReplayResult): string {
  const lines: string[] = [];

  lines.push(`Trace: ${result.trace_id}`);
  lines.push(`Status: ${result.status}`);
  lines.push(`Timestamp: ${result.timestamp}`);
  lines.push('');

  lines.push('Recorded:');
  lines.push(`  Decision: ${result.recorded.decision}`);
  lines.push(`  Reason: ${result.recorded.reason_code}`);
  lines.push(`  Policy: ${result.recorded.policy_id}`);
  lines.push(`  Obligations: ${result.recorded.obligations.join(', ') || 'none'}`);
  lines.push('');

  if (result.replayed) {
    lines.push('Replayed:');
    lines.push(`  Decision: ${result.replayed.decision}`);
    lines.push(`  Reason: ${result.replayed.reason_code}`);
    lines.push(`  Policy: ${result.replayed.policy_id}`);
    lines.push(`  Obligations: ${result.replayed.obligations.join(', ') || 'none'}`);
    lines.push('');
  }

  if (result.diff) {
    lines.push('Differences:');
    if (result.diff.decision_changed) {
      lines.push(`  - Decision: ${result.recorded.decision} → ${result.replayed?.decision}`);
    }
    if (result.diff.reason_code_changed) {
      lines.push(`  - Reason code changed`);
    }
    if (result.diff.policy_changed) {
      lines.push(`  - Policy changed`);
    }
    if (result.diff.obligations_added.length > 0) {
      lines.push(`  - Obligations added: ${result.diff.obligations_added.join(', ')}`);
    }
    if (result.diff.obligations_removed.length > 0) {
      lines.push(`  - Obligations removed: ${result.diff.obligations_removed.join(', ')}`);
    }
  }

  if (result.diagnostics.error_message) {
    lines.push('');
    lines.push(`Error: ${result.diagnostics.error_message}`);
  }

  return lines.join('\n');
}

/**
 * Format batch diff summary
 */
export function formatBatchDiffSummary(results: ReplayResult[]): string {
  const drifted = results.filter(r => r.status === 'DRIFT');

  const decisionChanges = new Map<string, number>();

  for (const result of drifted) {
    if (result.diff?.decision_changed && result.replayed) {
      const change = `${result.recorded.decision}→${result.replayed.decision}`;
      decisionChanges.set(change, (decisionChanges.get(change) || 0) + 1);
    }
  }

  const lines: string[] = [];
  lines.push('Decision Change Summary:');

  for (const [change, count] of decisionChanges) {
    lines.push(`  ${change}: ${count}`);
  }

  return lines.join('\n');
}
