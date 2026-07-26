#!/usr/bin/env node
/**
 * STIX Simulation Engine CLI
 * Simulate policy impact on historical evidence
 *
 * @module @stix/simulate
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import * as fs from 'fs';
import Table from 'cli-table3';

import { loadEvidenceBundles, getEvidenceStats } from './loadEvidence.js';
import { loadPolicyPack, getPolicyStats } from './loadPolicies.js';
import { SimulationPolicyEngine, simulateBatch } from './evaluate.js';
import { calculateBatchDiffs, getDiffStats } from './diff.js';
import {
  buildReport,
  formatReportAsJson,
  formatReportAsMarkdown,
  formatReportAsTable,
} from './report.js';
import type { SimulationOptions, SimulationReport } from './types.js';

const program = new Command();

// =============================================================================
// CLI SETUP
// =============================================================================

program
  .name('stix-simulate')
  .description('STIX Simulation Engine - Simulate policy impact on historical evidence')
  .version('0.1.9');

// =============================================================================
// SIMULATE COMMAND
// =============================================================================

program
  .command('run')
  .description('Run simulation on evidence with candidate policies')
  .requiredOption('-e, --evidence <path>', 'Path to evidence bundles (file or directory)')
  .requiredOption('-p, --policies <path>', 'Path to candidate policy pack')
  .option('-o, --output <path>', 'Output file for report')
  .option('--since <date>', 'Only include evidence after this date (ISO format)')
  .option('--until <date>', 'Only include evidence before this date (ISO format)')
  .option('--strict', 'Require both DECISION and OUTCOME events')
  .option('-f, --format <format>', 'Output format: json, markdown, table', 'table')
  .option('--include-results', 'Include individual results in report')
  .option('--max-results <n>', 'Maximum results to include', parseInt)
  .option('-v, --verbose', 'Verbose output')
  .action(async (opts) => {
    const options: SimulationOptions = {
      evidencePath: opts.evidence,
      policyPath: opts.policies,
      since: opts.since,
      until: opts.until,
      strict: opts.strict,
      format: opts.format,
      includeResults: opts.includeResults,
      maxResults: opts.maxResults,
      verbose: opts.verbose,
    };

    await runSimulation(options, opts.output);
  });

// =============================================================================
// STATS COMMAND
// =============================================================================

program
  .command('stats')
  .description('Show statistics for evidence and policies')
  .option('-e, --evidence <path>', 'Path to evidence bundles')
  .option('-p, --policies <path>', 'Path to policy pack')
  .action(async (opts) => {
    if (opts.evidence) {
      await showEvidenceStats(opts.evidence);
    }
    if (opts.policies) {
      await showPolicyStats(opts.policies);
    }
    if (!opts.evidence && !opts.policies) {
      console.log(chalk.yellow('Please specify --evidence or --policies'));
    }
  });

// =============================================================================
// DIFF COMMAND
// =============================================================================

program
  .command('diff')
  .description('Show only the differences (changed decisions)')
  .requiredOption('-e, --evidence <path>', 'Path to evidence bundles')
  .requiredOption('-p, --policies <path>', 'Path to candidate policy pack')
  .option('--risk <level>', 'Minimum risk level: LOW, MEDIUM, HIGH, CRITICAL', 'LOW')
  .option('-n, --limit <n>', 'Limit number of results', parseInt)
  .action(async (opts) => {
    await showDiffs(opts.evidence, opts.policies, opts.risk, opts.limit);
  });

// =============================================================================
// MAIN SIMULATION FUNCTION
// =============================================================================

async function runSimulation(options: SimulationOptions, outputPath?: string): Promise<void> {
  const spinner = ora('Loading evidence bundles...').start();

  try {
    // Load evidence
    const inputs = await loadEvidenceBundles(options.evidencePath, {
      since: options.since,
      until: options.until,
      strict: options.strict,
    });

    if (inputs.length === 0) {
      spinner.fail('No evidence found matching criteria');
      process.exit(1);
    }

    spinner.text = `Loaded ${inputs.length} evidence traces`;

    // Load policies
    spinner.text = 'Loading policy pack...';
    const policyPack = await loadPolicyPack(options.policyPath);
    spinner.text = `Loaded ${policyPack.policies.length} policies`;

    // Create simulation engine
    const engine = new SimulationPolicyEngine(policyPack);

    // Run simulation
    spinner.text = 'Running simulation...';
    const startTime = Date.now();

    const evaluationResults = simulateBatch(inputs, engine, (current, total) => {
      spinner.text = `Simulating... ${current}/${total}`;
    });

    // Calculate diffs
    spinner.text = 'Calculating differences...';
    const results = calculateBatchDiffs(inputs, evaluationResults);

    const duration = Date.now() - startTime;
    spinner.succeed(`Simulation complete in ${duration}ms`);

    // Build report
    const report = buildReport(results, options, policyPack);

    // Output report
    let output: string;
    switch (options.format) {
      case 'json':
        output = formatReportAsJson(report);
        break;
      case 'markdown':
        output = formatReportAsMarkdown(report);
        break;
      default:
        output = formatReportAsTable(report);
    }

    if (outputPath) {
      fs.writeFileSync(outputPath, output);
      console.log(chalk.green(`\nReport written to: ${outputPath}`));
    } else {
      console.log('\n' + output);
    }

    // Print summary
    printSummary(report);

  } catch (error) {
    spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
    if (options.verbose) {
      console.error(error);
    }
    process.exit(1);
  }
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

function printSummary(report: SimulationReport): void {
  console.log('');
  console.log(chalk.bold('Summary:'));

  const { summary, risk_assessment, decision_changes } = report;

  // Overall stats
  console.log(`  Total traces evaluated: ${chalk.cyan(summary.total_traces)}`);
  console.log(`  Decision changes: ${chalk.yellow(summary.decision_changes_count)} (${((summary.decision_changes_count / summary.total_traces) * 100).toFixed(1)}%)`);
  console.log(`  Unchanged: ${chalk.green(summary.unchanged)}`);

  // Risk assessment
  const riskColor = {
    LOW: chalk.green,
    MEDIUM: chalk.yellow,
    HIGH: chalk.red,
    CRITICAL: chalk.bgRed.white,
  }[risk_assessment.overall_risk] || chalk.white;

  console.log(`  Overall risk: ${riskColor(risk_assessment.overall_risk)}`);

  // Key changes
  if (decision_changes.allow_to_deny > 0) {
    console.log(`  ${chalk.red('⚠')} ALLOW→DENY: ${decision_changes.allow_to_deny} (would block)`);
  }
  if (decision_changes.allow_to_quarantine > 0) {
    console.log(`  ${chalk.yellow('⏸')} ALLOW→QUARANTINE: ${decision_changes.allow_to_quarantine} (would require approval)`);
  }
  if (decision_changes.deny_to_allow > 0) {
    console.log(`  ${chalk.red('⚠')} DENY→ALLOW: ${decision_changes.deny_to_allow} (CRITICAL - opens access)`);
  }

  console.log('');
}

async function showEvidenceStats(evidencePath: string): Promise<void> {
  const spinner = ora('Loading evidence...').start();

  try {
    const inputs = await loadEvidenceBundles(evidencePath);
    spinner.stop();

    const stats = getEvidenceStats(inputs);

    console.log(chalk.bold('\nEvidence Statistics'));
    console.log('═'.repeat(50));
    console.log(`Total traces: ${chalk.cyan(stats.total)}`);
    console.log(`\nDecisions:`);
    console.log(`  ${chalk.green('ALLOW')}: ${stats.byDecision.ALLOW || 0}`);
    console.log(`  ${chalk.red('DENY')}: ${stats.byDecision.DENY || 0}`);
    console.log(`  ${chalk.yellow('QUARANTINE')}: ${stats.byDecision.QUARANTINE || 0}`);
    console.log(`\nUnique actors: ${stats.uniqueActors}`);
    console.log(`Unique actions: ${stats.uniqueActions}`);
    console.log(`Resource types: ${stats.uniqueResourceTypes}`);
    if (stats.timeRange) {
      console.log(`\nTime range:`);
      console.log(`  First: ${stats.timeRange.first}`);
      console.log(`  Last: ${stats.timeRange.last}`);
    }
    console.log('═'.repeat(50));

  } catch (error) {
    spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
  }
}

async function showPolicyStats(policyPath: string): Promise<void> {
  const spinner = ora('Loading policies...').start();

  try {
    const pack = await loadPolicyPack(policyPath);
    spinner.stop();

    const stats = getPolicyStats(pack);

    console.log(chalk.bold('\nPolicy Pack Statistics'));
    console.log('═'.repeat(50));
    console.log(`Pack ID: ${chalk.cyan(pack.id)}`);
    console.log(`Pack hash: ${pack.hash.substring(0, 16)}...`);
    console.log(`Total policies: ${stats.totalPolicies}`);
    console.log(`\nBy decision:`);
    console.log(`  ${chalk.green('ALLOW')}: ${stats.byDecision.ALLOW || 0}`);
    console.log(`  ${chalk.red('DENY')}: ${stats.byDecision.DENY || 0}`);
    console.log(`  ${chalk.yellow('QUARANTINE')}: ${stats.byDecision.QUARANTINE || 0}`);
    console.log(`\nPriority range: ${stats.byPriority.min} - ${stats.byPriority.max} (avg: ${stats.byPriority.avg.toFixed(1)})`);
    console.log(`With obligations: ${stats.hasObligations}`);
    console.log(`With approval: ${stats.hasApproval}`);
    if (stats.regulations.length > 0) {
      console.log(`\nRegulations: ${stats.regulations.join(', ')}`);
    }
    console.log('═'.repeat(50));

  } catch (error) {
    spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
  }
}

async function showDiffs(
  evidencePath: string,
  policyPath: string,
  minRisk: string,
  limit?: number
): Promise<void> {
  const spinner = ora('Loading...').start();

  try {
    // Load evidence and policies
    const inputs = await loadEvidenceBundles(evidencePath);
    const policyPack = await loadPolicyPack(policyPath);
    const engine = new SimulationPolicyEngine(policyPack);

    spinner.text = 'Simulating...';

    // Run simulation
    const evaluationResults = simulateBatch(inputs, engine);
    const results = calculateBatchDiffs(inputs, evaluationResults);

    // Filter to changed only
    const changed = results.filter(r => r.delta.decision_changed);

    // Filter by risk level
    const riskOrder: Record<string, number> = {
      LOW: 0,
      MEDIUM: 1,
      HIGH: 2,
      CRITICAL: 3,
    };
    const minRiskValue = riskOrder[minRisk] || 0;
    const filtered = changed.filter(r => riskOrder[r.delta.risk_level] >= minRiskValue);

    spinner.stop();

    // Display results
    const toShow = limit ? filtered.slice(0, limit) : filtered;

    console.log(chalk.bold(`\nDecision Changes (${filtered.length} total, showing ${toShow.length})`));
    console.log('');

    const table = new Table({
      head: ['Trace ID', 'Recorded', '→', 'Simulated', 'Risk', 'Reason'],
      style: { head: ['cyan'] },
    });

    for (const result of toShow) {
      const from = colorDecision(result.recorded.decision);
      const to = colorDecision(result.simulated.decision);
      const risk = colorRisk(result.delta.risk_level);

      table.push([
        result.trace_id.substring(0, 12) + '...',
        from,
        '→',
        to,
        risk,
        result.simulated.reason_code,
      ]);
    }

    console.log(table.toString());

    if (filtered.length > toShow.length) {
      console.log(chalk.gray(`\n... and ${filtered.length - toShow.length} more. Use --limit to see more.`));
    }

  } catch (error) {
    spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
  }
}

function colorDecision(decision: string): string {
  switch (decision) {
    case 'ALLOW':
      return chalk.green(decision);
    case 'DENY':
      return chalk.red(decision);
    case 'QUARANTINE':
      return chalk.yellow(decision);
    default:
      return decision;
  }
}

function colorRisk(risk: string): string {
  switch (risk) {
    case 'CRITICAL':
      return chalk.bgRed.white(risk);
    case 'HIGH':
      return chalk.red(risk);
    case 'MEDIUM':
      return chalk.yellow(risk);
    case 'LOW':
      return chalk.green(risk);
    default:
      return risk;
  }
}

// =============================================================================
// RUN CLI
// =============================================================================

program.parse();
