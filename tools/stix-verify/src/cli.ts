#!/usr/bin/env node
/**
 * STIX Evidence Verification CLI
 * Verify hash chains, signatures, and evidence integrity
 * 
 * @module @stix/verify
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import * as fs from 'fs';
import * as path from 'path';
import { execSync } from 'node:child_process';
import type { EvidenceEvent } from '@stix/shared';

type SharedModule = typeof import('@stix/shared');

function isMissingSharedDist(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;

  const moduleError = error as { code?: string; url?: string; message?: string };
  if (moduleError.code !== 'ERR_MODULE_NOT_FOUND') return false;

  const details = `${moduleError.url ?? ''} ${moduleError.message ?? ''}`;
  return /(?:@stix[\\/])?shared[\\/]dist/i.test(details) || details.includes('packages/shared/dist');
}

async function loadSharedModule(): Promise<SharedModule> {
  try {
    return await import('@stix/shared');
  } catch (error) {
    if (!isMissingSharedDist(error)) {
      throw error;
    }

    console.warn(
      chalk.yellow(
        'Shared dist artifacts were missing. Running `pnpm --filter @stix/shared build` and retrying...'
      )
    );

    execSync('pnpm --filter @stix/shared build', { stdio: 'inherit' });
    return import('@stix/shared');
  }
}

const shared = await loadSharedModule();
const {
  verifyHashChain,
  verifyEvidenceSignature,
  loadPublicKey,
  canonicalize,
  sha256,
  ZERO_HASH,
} = shared;

const program = new Command();

// =============================================================================
// CLI SETUP
// =============================================================================

program
  .name('stix-verify')
  .description('STIX Evidence Verification CLI')
  .version('0.1.9');

// =============================================================================
// VERIFY CHAIN COMMAND
// =============================================================================

program
  .command('chain')
  .description('Verify hash chain integrity of evidence events')
  .argument('<file>', 'Path to evidence file (JSON or JSONL)')
  .option('-v, --verbose', 'Show detailed output')
  .option('--limit <n>', 'Limit number of events to verify', parseInt)
  .action(async (file: string, options: { verbose?: boolean; limit?: number }) => {
    const spinner = ora('Loading evidence file...').start();

    try {
      // Load events
      const events = await loadEventsFromFile(file);
      spinner.text = `Loaded ${events.length} events`;

      if (events.length === 0) {
        spinner.fail('No events found in file');
        process.exit(1);
      }

      // Limit if specified
      const eventsToVerify = options.limit 
        ? events.slice(0, options.limit) 
        : events;

      spinner.text = `Verifying chain of ${eventsToVerify.length} events...`;

      // Verify hash chain
      const result = verifyHashChain(eventsToVerify);

      if (result.valid) {
        spinner.succeed(chalk.green(`✓ Hash chain verified: ${result.verifiedCount} events`));
      } else {
        spinner.fail(chalk.red(`✗ Hash chain verification failed`));
        
        console.log('\nErrors:');
        for (const error of result.errors) {
          console.log(chalk.red(`  - Event ${error.index} (${error.eventId}): ${error.error}`));
        }
        
        process.exit(1);
      }

      // Show details if verbose
      if (options.verbose) {
        console.log('\nChain Details:');
        console.log(`  First event: ${eventsToVerify[0].event_id}`);
        console.log(`  Last event: ${eventsToVerify[eventsToVerify.length - 1].event_id}`);
        console.log(`  Genesis hash: ${ZERO_HASH}`);
        console.log(`  Latest hash: ${eventsToVerify[eventsToVerify.length - 1].integrity.event_hash}`);
      }

    } catch (error) {
      spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
      process.exit(1);
    }
  });

// =============================================================================
// VERIFY SIGNATURE COMMAND
// =============================================================================

program
  .command('signature')
  .description('Verify cryptographic signatures of evidence events')
  .argument('<file>', 'Path to evidence file (JSON or JSONL)')
  .option('-k, --key <path>', 'Path to public key PEM file')
  .option('--key-id <id>', 'Key ID to verify against')
  .option('--allow-unsigned', 'Allow missing key and skip signature verification')
  .option('-v, --verbose', 'Show detailed output')
  .action(async (file: string, options: { key?: string; keyId?: string; allowUnsigned?: boolean; verbose?: boolean }) => {
    const spinner = ora('Loading evidence file...').start();

    try {
      const events = await loadEventsFromFile(file);
      spinner.text = `Loaded ${events.length} events`;

      if (!options.key) {
        if (options.allowUnsigned) {
          spinner.warn('No public key provided; skipping signature verification due to --allow-unsigned');
          console.log(chalk.yellow('\nStrict verification is disabled by --allow-unsigned.'));
          process.exit(0);
        }

        spinner.fail('No public key provided');
        console.log(chalk.red('\nSignature verification requires --key (or explicitly pass --allow-unsigned).'));
        process.exit(1);
      }

      // Load public key
      const keyPem = fs.readFileSync(options.key, 'utf-8');
      const publicKey = loadPublicKey(keyPem);

      spinner.text = 'Verifying signatures...';

      let verified = 0;
      let failed = 0;
      const errors: Array<{ eventId: string; error: string }> = [];

      for (const event of events) {
        // Check key ID if specified
        if (options.keyId && event.integrity.key_id !== options.keyId) {
          continue;
        }
        if (!event.integrity.key_id) {
          failed++;
          errors.push({ eventId: event.event_id, error: 'Missing integrity.key_id' });
          continue;
        }

        // Build event without integrity for verification
        const { integrity, ...eventWithoutIntegrity } = event;
        const keyId = integrity.key_id as string;

        const result = verifyEvidenceSignature(
          eventWithoutIntegrity as Record<string, unknown>,
          {
            ...integrity,
            key_id: keyId,
          },
          {
            keyId,
            algorithm: 'EdDSA',
            publicKey,
          }
        );

        if (result.valid) {
          verified++;
        } else {
          failed++;
          errors.push({ eventId: event.event_id, error: result.error ?? 'Unknown error' });
        }
      }

      if (failed === 0) {
        spinner.succeed(chalk.green(`✓ All signatures verified: ${verified} events`));
      } else {
        spinner.fail(chalk.red(`✗ Signature verification failed: ${failed}/${verified + failed}`));
        
        if (options.verbose) {
          console.log('\nFailed events:');
          for (const error of errors.slice(0, 10)) {
            console.log(chalk.red(`  - ${error.eventId}: ${error.error}`));
          }
          if (errors.length > 10) {
            console.log(chalk.red(`  ... and ${errors.length - 10} more`));
          }
        }
        
        process.exit(1);
      }

    } catch (error) {
      spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
      process.exit(1);
    }
  });

// =============================================================================
// VERIFY EVENT COMMAND
// =============================================================================

program
  .command('event')
  .description('Verify a single evidence event')
  .argument('<event-json>', 'Event JSON string or file path')
  .option('-k, --key <path>', 'Path to public key PEM file')
  .option('-p, --prev-hash <hash>', 'Expected previous hash')
  .action(async (eventArg: string, options: { key?: string; prevHash?: string }) => {
    try {
      // Parse event
      let event: EvidenceEvent;
      if (fs.existsSync(eventArg)) {
        event = JSON.parse(fs.readFileSync(eventArg, 'utf-8'));
      } else {
        event = JSON.parse(eventArg);
      }

      console.log(chalk.bold('\nEvent Verification Report'));
      console.log('═'.repeat(50));

      console.log(`\nEvent ID: ${chalk.cyan(event.event_id)}`);
      console.log(`Trace ID: ${chalk.cyan(event.trace_id)}`);
      console.log(`Decision: ${colorDecision(event.decision ?? 'UNKNOWN')}`);
      console.log(`Timestamp: ${event.timestamp}`);

      // Verify hash
      const { integrity, ...eventWithoutIntegrity } = event;
      const computedHash = sha256(canonicalize(eventWithoutIntegrity));
      const hashValid = computedHash === integrity.event_hash;
      
      console.log(`\nHash Verification: ${hashValid ? chalk.green('✓ VALID') : chalk.red('✗ INVALID')}`);
      if (!hashValid) {
        console.log(chalk.red(`  Expected: ${integrity.event_hash}`));
        console.log(chalk.red(`  Computed: ${computedHash}`));
      }

      // Verify prev_hash if provided
      if (options.prevHash) {
        const prevValid = integrity.prev_hash === options.prevHash;
        console.log(`\nPrev Hash: ${prevValid ? chalk.green('✓ MATCHES') : chalk.red('✗ MISMATCH')}`);
      }

      // Verify signature if key provided
      if (options.key) {
        const keyPath = options.key;
        const keyPem = fs.readFileSync(keyPath, 'utf-8');
        const publicKey = loadPublicKey(keyPem);
        if (!integrity.key_id) {
          console.log(chalk.red('\nSignature: ✗ INVALID'));
          console.log(chalk.red('  Error: Missing integrity.key_id'));
          console.log('\n' + '═'.repeat(50));
          return;
        }
        const keyId = integrity.key_id;

        const sigResult = verifyEvidenceSignature(
          eventWithoutIntegrity as Record<string, unknown>,
          {
            ...integrity,
            key_id: keyId,
          },
          { keyId, algorithm: 'EdDSA', publicKey }
        );
        
        console.log(`\nSignature: ${sigResult.valid ? chalk.green('✓ VALID') : chalk.red('✗ INVALID')}`);
        if (!sigResult.valid) {
          console.log(chalk.red(`  Error: ${sigResult.error}`));
        }
      }

      console.log('\n' + '═'.repeat(50));

    } catch (error) {
      console.error(chalk.red(`Error: ${(error as Error).message}`));
      process.exit(1);
    }
  });

// =============================================================================
// STATS COMMAND
// =============================================================================

program
  .command('stats')
  .description('Show statistics for evidence file')
  .argument('<file>', 'Path to evidence file')
  .action(async (file: string) => {
    const spinner = ora('Analyzing evidence file...').start();

    try {
      const events = await loadEventsFromFile(file);
      spinner.stop();

      const stats = {
        total: events.length,
        decisions: { ALLOW: 0, DENY: 0, QUARANTINE: 0 },
        actors: new Set<string>(),
        actions: new Set<string>(),
        resourceTypes: new Set<string>(),
        timeRange: { first: '', last: '' },
      };

      for (const event of events) {
        const decision = event.decision;
        if (decision === 'ALLOW' || decision === 'DENY' || decision === 'QUARANTINE') {
          const key = decision as keyof typeof stats.decisions;
          stats.decisions[key]++;
        }
        if (event.actor?.id) {
          stats.actors.add(event.actor.id);
        }
        if (event.action?.name) {
          stats.actions.add(event.action.name);
        }
        if (event.resource?.type) {
          stats.resourceTypes.add(event.resource.type);
        }
      }

      if (events.length > 0) {
        const sorted = [...events].sort((a, b) => a.timestamp.localeCompare(b.timestamp));
        stats.timeRange.first = sorted[0].timestamp;
        stats.timeRange.last = sorted[sorted.length - 1].timestamp;
      }

      console.log(chalk.bold('\nEvidence Statistics'));
      console.log('═'.repeat(50));
      console.log(`Total Events: ${chalk.cyan(stats.total)}`);
      console.log(`\nDecisions:`);
      console.log(`  ${chalk.green('ALLOW')}: ${stats.decisions.ALLOW}`);
      console.log(`  ${chalk.red('DENY')}: ${stats.decisions.DENY}`);
      console.log(`  ${chalk.yellow('QUARANTINE')}: ${stats.decisions.QUARANTINE}`);
      console.log(`\nUnique Actors: ${stats.actors.size}`);
      console.log(`Unique Actions: ${stats.actions.size}`);
      console.log(`Resource Types: ${stats.resourceTypes.size}`);
      console.log(`\nTime Range:`);
      console.log(`  First: ${stats.timeRange.first}`);
      console.log(`  Last: ${stats.timeRange.last}`);
      console.log('═'.repeat(50));

    } catch (error) {
      spinner.fail(chalk.red(`Error: ${(error as Error).message}`));
      process.exit(1);
    }
  });

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

async function loadEventsFromFile(filePath: string): Promise<EvidenceEvent[]> {
  const content = fs.readFileSync(filePath, 'utf-8');
  const ext = path.extname(filePath).toLowerCase();

  if (ext === '.jsonl' || ext === '.ndjson') {
    // JSONL format: one event per line
    return content
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line) as EvidenceEvent);
  }

  // JSON format: array or single object
  const parsed = JSON.parse(content);
  if (Array.isArray(parsed)) {
    return parsed;
  }
  return [parsed];
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

// =============================================================================
// RUN CLI
// =============================================================================

program.parse();


