#!/usr/bin/env node
/**
 * STIX Replay Tool CLI
 * Replay recorded decisions against policies for verification
 *
 * @module @stix/replay
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import * as fs from 'fs';
import Table from 'cli-table3';

import { loadBundles, extractMultiple, validateForReplay } from './extract.js';
import { loadPolicyPack, loadPolicyArchive, loadPackByHash } from './policyLoader.js';
import { ReplayEngine } from './engine.js';
import { replayBatch, calculateStats, getDriftedResults, getErroredResults } from './replay.js';
import { verifyBundlesForReplay } from './verify.js';
import {
  buildReport,
  formatReportAsJson,
  formatReportAsMarkdown,
  formatReportAsTable,
  formatDetailedDiff,
  formatBatchDiffSummary,
} from './report.js';
import type { ReplayOptions } from './types.js';

const program = new Command();

// =============================================================================
// CLI SETUP
// =============================================================================

program
  .name('stix-replay')
  .description('STIX Replay Tool - Replay recorded decisions for verification')
  .version('0.1.2');

// =============================================================================
// REPLAY COMMAND
// =============================================================================

program
  .command('run')
  .description('Replay recorded decisions against policies')
  .requiredOption('-b, --bundles <path>', 'Path to evidence bundles (file or directory)')
  .requiredOption('-p, --policies <path>', 'Path to policy pack')
  .option('-o, --output <path>', 'Output file for report')
  .option('--strict', 'Require exact reason_code match')
  .option('--strict-obligations', 'Require exact obligations match')
  .option('--strict-policy', 'Require policy hash match')
  .option('--verify', 'Verify evidence schema/hash-chain/signatures before replay')
  .option('--verify-key <path>', 'Public key PEM path for signature verification')
  .option('--verify-key-id <id>', 'Only verify signatures for this key ID')
  .option('-f, --format <format>', 'Output format: json, markdown, table', 'table')
  .option('-v, --verbose', 'Verbose output')
  .action(async (opts) => {
    const options: ReplayOptions = {
      bundlePath: opts.bundles,
      policyPath: opts.policies,
      verify: opts.verify,
      verifyKeyPath: opts.verifyKey,
      verifyKeyId: opts.verifyKeyId,
      strict: opts.strict,
      format: opts.format,
      verbose: opts.verbose,
    };

    await runReplay(options, opts.output, {
      strictReasonCode: opts.strict,
      strictObligations: opts.strictObligations,
      strictPolicyHash: opts.strictPolicy,
    });
  });

// =============================================================================
// VALIDATE COMMAND
// =============================================================================

program
  .command('validate')
  .description('Validate that evidence bundles have sufficient data for replay')
  .requiredOption('-b, --bundles <path>', 'Path to evidence bundles')
  .action(async (opts) => {
    await validateBundles(opts.bundles);
  });

// =============================================================================
// DIFF COMMAND
// =============================================================================

program
  .command('diff')
  .description('Show only the drifted decisions')
  .requiredOption('-b, --bundles <path>', 'Path to evidence bundles')
  .requiredOption('-p, --policies <path>', 'Path to policy pack')
  .option('-n, --limit <n>', 'Limit number of results', parseInt)
  .option('--detail', 'Show detailed diffs')
  .action(async (opts) => {
    await showDiffs(opts.bundles, opts.policies, opts.limit, opts.detail);
  });

// =============================================================================
// STATS COMMAND
// =============================================================================

program
  .command('stats')
  .description('Show replay statistics')
  .requiredOption('-b, --bundles <path>', 'Path to evidence bundles')
  .requiredOption('-p, --policies <path>', 'Path to policy pack')
  .action(async (opts) => {
    await showStats(opts.bundles, opts.policies);
  });

// =============================================================================
// MAIN REPLAY FUNCTION
// =============================================================================

interface CompareOptions {
  strictReasonCode?: boolean;
  strictObligations?: boolean;
  strictPolicyHash?: boolean;
}

async function runReplay(
  options: ReplayOptions,
  outputPath?: string,
  compareOptions: CompareOptions = {}
): Promise<void> {
  const spinner = ora('Loading evidence bundles...').start();

  try {
    // Load bundles
    const bundles = await loadBundles(options.bundlePath);

    if (bundles.length === 0) {
      spinner.fail('No bundles found');
      process.exit(1);
    }

    spinner.text = `Loaded ${bundles.length} bundles`;

    // Optional evidence verification pre-check
    if (options.verify) {
      spinner.text = 'Verifying evidence integrity...';
      const verification = verifyBundlesForReplay(bundles, {
        publicKeyPath: options.verifyKeyPath,
        keyId: options.verifyKeyId,
      });

      if (!verification.valid) {
        spinner.fail(`Evidence verification failed (${verification.errors.length} issues)`);
        for (const error of verification.errors.slice(0, 20)) {
          console.error(chalk.red(`  - ${error}`));
        }
        if (verification.errors.length > 20) {
          console.error(chalk.red(`  ... and ${verification.errors.length - 20} more`));
        }
        process.exit(1);
      }

      for (const warning of verification.warnings) {
        console.log(chalk.yellow(`Warning: ${warning}`));
      }

      spinner.text =
        `Verified ${verification.verifiedEvents} events` +
        (verification.signatureChecks > 0
          ? ` (${verification.signatureChecks} signatures)`
          : '');
    }

    // Extract decisions
    spinner.text = 'Extracting recorded decisions...';
    const decisions = extractMultiple(bundles);

    if (decisions.length === 0) {
      spinner.fail('No valid decisions found in bundles');
      process.exit(1);
    }

    spinner.text = `Extracted ${decisions.length} decisions`;

    // Load policies
    spinner.text = 'Loading policy pack...';
    const policyPack = await loadPolicyPack(options.policyPath);
    spinner.text = `Loaded ${policyPack.policies.length} policies`;

    // Create engine
    const engine = new ReplayEngine(policyPack);

    // Run replay
    spinner.text = 'Replaying decisions...';
    const startTime = Date.now();

    const results = replayBatch(decisions, engine, compareOptions, (current, total) => {
      spinner.text = `Replaying... ${current}/${total}`;
    });

    const duration = Date.now() - startTime;
    spinner.succeed(`Replay complete in ${duration}ms`);

    // Calculate stats
    const stats = calculateStats(results);

    // Build report
    const report = buildReport(results, options, policyPack, stats);

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
    printSummary(stats);

    // Exit with error if drifts found
    if (stats.drifts > 0 && options.strict) {
      process.exit(1);
    }

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

function printSummary(stats: ReturnType<typeof calculateStats>): void {
  console.log('');
  console.log(chalk.bold('Summary:'));
  console.log(`  Total: ${chalk.cyan(stats.total)}`);
  console.log(`  Matches: ${chalk.green(stats.matches)} (${stats.matchRate.toFixed(1)}%)`);
  console.log(`  Drifts: ${chalk.yellow(stats.drifts)} (${stats.driftRate.toFixed(1)}%)`);
  console.log(`  Errors: ${chalk.red(stats.errors)} (${stats.errorRate.toFixed(1)}%)`);

  if (stats.decisionChanges.denyToAllow > 0) {
    console.log(chalk.red(`  ⚠ CRITICAL: ${stats.decisionChanges.denyToAllow} DENY→ALLOW changes`));
  }
  if (stats.decisionChanges.quarantineToAllow > 0) {
    console.log(chalk.red(`  ⚠ CRITICAL: ${stats.decisionChanges.quarantineToAllow} QUARANTINE→ALLOW changes`));
  }
  if (stats.decisionChanges.allowToDeny > 0) {
    console.log(chalk.yellow(`  ⚠ ${stats.decisionChanges.allowToDeny} ALLOW→DENY changes (may block users)`));
  }

  console.log('');
}

async function validateBundles(bundlePath: string): Promise<void> {
  const spinner = ora('Loading bundles...').start();

  try {
    const bundles = await loadBundles(bundlePath);
    spinner.stop();

    let valid = 0;
    let invalid = 0;
    const issues: string[] = [];

    for (const bundle of bundles) {
      const result = validateForReplay(bundle);
      if (result.valid) {
        valid++;
      } else {
        invalid++;
        for (const error of result.errors) {
          issues.push(error);
        }
      }
    }

    console.log(chalk.bold('\nValidation Results'));
    console.log('═'.repeat(50));
    console.log(`Total bundles: ${bundles.length}`);
    console.log(`Valid: ${chalk.green(valid)}`);
    console.log(`Invalid: ${chalk.red(invalid)}`);

    if (issues.length > 0) {
      console.log('\nIssues found:');
      const uniqueIssues = [...new Set(issues)];
      for (const issue of uniqueIssues.slice(0, 10)) {
        console.log(`  - ${issue}`);
      }
      if (uniqueIssues.length > 10) {
        console.log(`  ... and ${uniqueIssues.length - 10} more`);
      }
    }

  } catch (error) {
    spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
  }
}

async function showDiffs(
  bundlePath: string,
  policyPath: string,
  limit?: number,
  showDetail?: boolean
): Promise<void> {
  const spinner = ora('Loading...').start();

  try {
    const bundles = await loadBundles(bundlePath);
    const decisions = extractMultiple(bundles);
    const policyPack = await loadPolicyPack(policyPath);
    const engine = new ReplayEngine(policyPack);

    spinner.text = 'Replaying...';
    const results = replayBatch(decisions, engine);
    const drifted = getDriftedResults(results);

    spinner.stop();

    const toShow = limit ? drifted.slice(0, limit) : drifted;

    console.log(chalk.bold(`\nDrifted Decisions (${drifted.length} total, showing ${toShow.length})`));
    console.log('');

    if (showDetail) {
      for (const result of toShow) {
        console.log(formatDetailedDiff(result));
        console.log('─'.repeat(60));
      }
    } else {
      const table = new Table({
        head: ['Trace ID', 'Recorded', '→', 'Replayed', 'Reason'],
        style: { head: ['cyan'] },
      });

      for (const result of toShow) {
        const recorded = colorDecision(result.recorded.decision);
        const replayed = result.replayed ? colorDecision(result.replayed.decision) : 'ERROR';
        const reason = result.replayed?.reason_code || result.diagnostics.error_message || '';

        table.push([
          result.trace_id.substring(0, 12) + '...',
          recorded,
          '→',
          replayed,
          reason.substring(0, 30),
        ]);
      }

      console.log(table.toString());
    }

    if (drifted.length > toShow.length) {
      console.log(chalk.gray(`\n... and ${drifted.length - toShow.length} more. Use --limit to see more.`));
    }

    // Show summary
    console.log('');
    console.log(formatBatchDiffSummary(results));

  } catch (error) {
    spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
  }
}

async function showStats(bundlePath: string, policyPath: string): Promise<void> {
  const spinner = ora('Loading...').start();

  try {
    const bundles = await loadBundles(bundlePath);
    const decisions = extractMultiple(bundles);
    const policyPack = await loadPolicyPack(policyPath);
    const engine = new ReplayEngine(policyPack);

    spinner.text = 'Replaying...';
    const results = replayBatch(decisions, engine);
    const stats = calculateStats(results);

    spinner.stop();

    console.log(chalk.bold('\nReplay Statistics'));
    console.log('═'.repeat(50));
    console.log(`\nOverall:`);
    console.log(`  Total traces: ${chalk.cyan(stats.total)}`);
    console.log(`  Match rate: ${colorMatchRate(stats.matchRate)}`);
    console.log(`  Drift rate: ${chalk.yellow(stats.driftRate.toFixed(1) + '%')}`);
    console.log(`  Error rate: ${chalk.red(stats.errorRate.toFixed(1) + '%')}`);

    console.log(`\nDecision Changes:`);
    console.log(`  ALLOW→DENY: ${stats.decisionChanges.allowToDeny}`);
    console.log(`  ALLOW→QUARANTINE: ${stats.decisionChanges.allowToQuarantine}`);
    console.log(`  DENY→ALLOW: ${chalk.red(stats.decisionChanges.denyToAllow.toString())} ${stats.decisionChanges.denyToAllow > 0 ? '⚠ CRITICAL' : ''}`);
    console.log(`  DENY→QUARANTINE: ${stats.decisionChanges.denyToQuarantine}`);
    console.log(`  QUARANTINE→ALLOW: ${chalk.red(stats.decisionChanges.quarantineToAllow.toString())} ${stats.decisionChanges.quarantineToAllow > 0 ? '⚠ CRITICAL' : ''}`);
    console.log(`  QUARANTINE→DENY: ${stats.decisionChanges.quarantineToDeny}`);

    console.log('═'.repeat(50));

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

function colorMatchRate(rate: number): string {
  if (rate === 100) return chalk.green(rate.toFixed(1) + '%');
  if (rate >= 95) return chalk.yellow(rate.toFixed(1) + '%');
  return chalk.red(rate.toFixed(1) + '%');
}

// =============================================================================
// RUN CLI
// =============================================================================

program.parse();
