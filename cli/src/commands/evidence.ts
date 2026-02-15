/**
 * STIX CLI - Evidence Commands
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import * as fs from 'fs/promises';
import { request } from 'undici';
import { createGzip } from 'zlib';
import { promisify } from 'util';
import { pipeline } from 'stream/promises';
import { createWriteStream } from 'fs';
import { Readable } from 'stream';

const gzip = promisify(createGzip);

export const evidenceCommand = new Command('evidence')
  .description('Evidence management commands');

// =============================================================================
// EXPORT
// =============================================================================

evidenceCommand
  .command('export')
  .description('Export evidence records for compliance')
  .requiredOption('--api-url <url>', 'STIX Evidence API URL')
  .option('--api-key <key>', 'API key')
  .option('--start-date <date>', 'Start date (ISO format)')
  .option('--end-date <date>', 'End date (ISO format)')
  .option('--trace-id <id>', 'Filter by trace ID')
  .option('--actor-id <id>', 'Filter by actor ID')
  .option('--decision <decision>', 'Filter by decision (ALLOW/DENY/QUARANTINE)')
  .option('--format <format>', 'Output format (json, jsonl, csv)', 'jsonl')
  .option('--output <file>', 'Output file', 'evidence-export.jsonl')
  .option('--compress', 'Compress output with gzip')
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
    startDate?: string;
    endDate?: string;
    traceId?: string;
    actorId?: string;
    decision?: string;
    format: string;
    output: string;
    compress?: boolean;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const spinner = ora('Exporting evidence...').start();

    try {
      // Build query parameters
      const params = new URLSearchParams();
      if (options.startDate) params.set('start_time', options.startDate);
      if (options.endDate) params.set('end_time', options.endDate);
      if (options.traceId) params.set('trace_id', options.traceId);
      if (options.actorId) params.set('actor_id', options.actorId);
      if (options.decision) params.set('decision', options.decision);
      params.set('limit', '10000');

      const url = `${options.apiUrl}/v1/evidence?${params}`;

      const response = await request(url, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
      });

      if (response.statusCode !== 200) {
        throw new Error(`API returned ${response.statusCode}`);
      }

      const body = await response.body.json() as { records: unknown[]; total: number };
      spinner.text = `Processing ${body.records.length} records...`;

      let output: string;
      const outputFile = options.compress ? `${options.output}.gz` : options.output;

      switch (options.format) {
        case 'json':
          output = JSON.stringify(body.records, null, 2);
          break;
        case 'jsonl':
          output = body.records.map(r => JSON.stringify(r)).join('\n');
          break;
        case 'csv':
          output = convertToCSV(body.records as Record<string, unknown>[]);
          break;
        default:
          throw new Error(`Unknown format: ${options.format}`);
      }

      if (options.compress) {
        const readable = Readable.from([output]);
        const gzipStream = createGzip();
        const writeStream = createWriteStream(outputFile);
        await pipeline(readable, gzipStream, writeStream);
      } else {
        await fs.writeFile(outputFile, output);
      }

      spinner.succeed(`Exported ${body.records.length} records to ${outputFile}`);
    } catch (error) {
      spinner.fail(`Export error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// VERIFY-CHAIN
// =============================================================================

evidenceCommand
  .command('verify-chain')
  .description('Verify evidence chain integrity')
  .requiredOption('--api-url <url>', 'STIX Evidence API URL')
  .option('--api-key <key>', 'API key')
  .option('--trace-id <id>', 'Verify specific trace')
  .option('--start-date <date>', 'Start date for verification')
  .option('--end-date <date>', 'End date for verification')
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
    traceId?: string;
    startDate?: string;
    endDate?: string;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const spinner = ora('Verifying evidence chain...').start();

    try {
      let url = `${options.apiUrl}/v1/evidence/verify`;

      if (options.traceId) {
        url = `${options.apiUrl}/v1/evidence/verify/${options.traceId}`;
      }

      const params = new URLSearchParams();
      if (options.startDate) params.set('start_time', options.startDate);
      if (options.endDate) params.set('end_time', options.endDate);

      const fullUrl = params.toString() ? `${url}?${params}` : url;

      const response = await request(fullUrl, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
      });

      const body = await response.body.json() as {
        valid: boolean;
        records_verified: number;
        errors?: string[];
        first_invalid?: string;
      };

      if (body.valid) {
        spinner.succeed(`Chain verified: ${body.records_verified} records, no integrity issues`);
      } else {
        spinner.fail(`Chain verification FAILED`);
        console.log(chalk.red(`  First invalid record: ${body.first_invalid}`));
        if (body.errors) {
          for (const error of body.errors) {
            console.log(chalk.red(`  - ${error}`));
          }
        }
        process.exit(1);
      }
    } catch (error) {
      spinner.fail(`Verification error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// QUERY
// =============================================================================

evidenceCommand
  .command('query')
  .description('Query evidence records')
  .requiredOption('--api-url <url>', 'STIX Evidence API URL')
  .option('--api-key <key>', 'API key')
  .option('--trace-id <id>', 'Filter by trace ID')
  .option('--actor-id <id>', 'Filter by actor ID')
  .option('--action <action>', 'Filter by action')
  .option('--resource-type <type>', 'Filter by resource type')
  .option('--decision <decision>', 'Filter by decision')
  .option('--limit <n>', 'Limit results', '20')
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
    traceId?: string;
    actorId?: string;
    action?: string;
    resourceType?: string;
    decision?: string;
    limit: string;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const spinner = ora('Querying evidence...').start();

    try {
      const params = new URLSearchParams();
      if (options.traceId) params.set('trace_id', options.traceId);
      if (options.actorId) params.set('actor_id', options.actorId);
      if (options.action) params.set('action', options.action);
      if (options.resourceType) params.set('resource_type', options.resourceType);
      if (options.decision) params.set('decision', options.decision);
      params.set('limit', options.limit);

      const url = `${options.apiUrl}/v1/evidence?${params}`;

      const response = await request(url, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
      });

      const body = await response.body.json() as { records: EvidenceRecord[]; total: number };

      spinner.stop();

      console.log(chalk.cyan(`\nFound ${body.total} records (showing ${body.records.length}):\n`));

      for (const record of body.records) {
        const decisionColor = record.decision === 'ALLOW' ? chalk.green :
          record.decision === 'DENY' ? chalk.red : chalk.yellow;

        console.log(`${chalk.gray(record.timestamp)} ${decisionColor(record.decision.padEnd(10))} ` +
          `${chalk.white(record.actor_id)} → ${record.action} on ${record.resource_type}`);
        console.log(chalk.gray(`  trace: ${record.trace_id} | policy: ${record.policy_id}`));
        console.log();
      }
    } catch (error) {
      spinner.fail(`Query error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// STATS
// =============================================================================

evidenceCommand
  .command('stats')
  .description('Get evidence statistics')
  .requiredOption('--api-url <url>', 'STIX Evidence API URL')
  .option('--api-key <key>', 'API key')
  .option('--start-date <date>', 'Start date', new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString())
  .option('--end-date <date>', 'End date', new Date().toISOString())
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
    startDate: string;
    endDate: string;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const spinner = ora('Fetching statistics...').start();

    try {
      const params = new URLSearchParams({
        start_time: options.startDate,
        end_time: options.endDate,
      });

      const url = `${options.apiUrl}/v1/evidence/stats?${params}`;

      const response = await request(url, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
      });

      const stats = await response.body.json() as {
        total: number;
        by_decision: Record<string, number>;
        by_actor_type: Record<string, number>;
        by_env: Record<string, number>;
        unique_actors: number;
        unique_traces: number;
      };

      spinner.stop();

      console.log(chalk.cyan('\n=== Evidence Statistics ===\n'));
      console.log(`Period: ${options.startDate} to ${options.endDate}`);
      console.log(`Total Records: ${stats.total}`);
      console.log(`Unique Actors: ${stats.unique_actors}`);
      console.log(`Unique Traces: ${stats.unique_traces}`);

      console.log(chalk.cyan('\nBy Decision:'));
      for (const [decision, count] of Object.entries(stats.by_decision)) {
        const color = decision === 'ALLOW' ? chalk.green :
          decision === 'DENY' ? chalk.red : chalk.yellow;
        const pct = ((count / stats.total) * 100).toFixed(1);
        console.log(`  ${color(decision.padEnd(12))} ${count.toString().padStart(8)} (${pct}%)`);
      }

      console.log(chalk.cyan('\nBy Actor Type:'));
      for (const [type, count] of Object.entries(stats.by_actor_type)) {
        console.log(`  ${type.padEnd(12)} ${count.toString().padStart(8)}`);
      }

      console.log(chalk.cyan('\nBy Environment:'));
      for (const [env, count] of Object.entries(stats.by_env)) {
        console.log(`  ${env.padEnd(12)} ${count.toString().padStart(8)}`);
      }
    } catch (error) {
      spinner.fail(`Stats error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// HELPERS
// =============================================================================

interface EvidenceRecord {
  event_id: string;
  trace_id: string;
  timestamp: string;
  decision: string;
  actor_id: string;
  actor_type: string;
  action: string;
  resource_type: string;
  policy_id: string;
}

function convertToCSV(records: Record<string, unknown>[]): string {
  if (records.length === 0) return '';

  const headers = Object.keys(records[0]);
  const lines = [headers.join(',')];

  for (const record of records) {
    const values = headers.map(h => {
      const value = record[h];
      if (typeof value === 'string') {
        return `"${value.replace(/"/g, '""')}"`;
      }
      if (typeof value === 'object') {
        return `"${JSON.stringify(value).replace(/"/g, '""')}"`;
      }
      return String(value);
    });
    lines.push(values.join(','));
  }

  return lines.join('\n');
}
