/**
 * STIX CLI - Policy Commands
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import * as fs from 'fs/promises';
import * as path from 'path';
import { glob } from 'glob';
import { parse as parseYaml, stringify as stringifyYaml } from 'yaml';
import { request } from 'undici';
import { table } from 'table';
import { createHash } from 'crypto';

interface PolicyFile {
  path: string;
  policies: PolicyArtifact[];
}

interface PolicyArtifact {
  policy_id: string;
  version: string;
  priority?: number;
  description?: string;
  scope: {
    actor_type: string;
    action: string;
    resource_type: string;
  };
  conditions?: Record<string, unknown>;
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  reason_code: string;
  obligations?: unknown[];
  approval?: Record<string, unknown>;
  controls?: string[];
  regulations?: string[];
  tags?: string[];
  active?: boolean;
}

export const policyCommand = new Command('policy')
  .description('Policy management commands');

// =============================================================================
// VALIDATE
// =============================================================================

policyCommand
  .command('validate <path>')
  .description('Validate policy file(s) syntax and schema')
  .option('-v, --verbose', 'Show detailed validation results')
  .action(async (policyPath: string, options: { verbose?: boolean }) => {
    const spinner = ora('Validating policies...').start();

    try {
      const files = await loadPolicyFiles(policyPath);
      let totalPolicies = 0;
      let errors: string[] = [];

      for (const file of files) {
        const fileErrors = validatePolicyFile(file);
        errors.push(...fileErrors);
        totalPolicies += file.policies.length;

        if (options.verbose && fileErrors.length === 0) {
          console.log(chalk.green(`  ✓ ${file.path} (${file.policies.length} policies)`));
        }
      }

      if (errors.length > 0) {
        spinner.fail(`Validation failed with ${errors.length} error(s)`);
        for (const error of errors) {
          console.log(chalk.red(`  ✗ ${error}`));
        }
        process.exit(1);
      }

      spinner.succeed(`Validated ${totalPolicies} policies in ${files.length} file(s)`);
    } catch (error) {
      spinner.fail(`Validation error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// LINT
// =============================================================================

policyCommand
  .command('lint <path>')
  .description('Lint policies for best practices')
  .option('--fix', 'Auto-fix linting issues where possible')
  .action(async (policyPath: string, options: { fix?: boolean }) => {
    const spinner = ora('Linting policies...').start();

    try {
      const files = await loadPolicyFiles(policyPath);
      let warnings: string[] = [];
      let fixed = 0;

      for (const file of files) {
        for (const policy of file.policies) {
          // Check for missing description
          if (!policy.description) {
            warnings.push(`${file.path}: Policy ${policy.policy_id} missing description`);
          }

          // Check for high priority number (lower is higher priority)
          if (policy.priority && policy.priority > 9000) {
            warnings.push(`${file.path}: Policy ${policy.policy_id} has very low priority (${policy.priority})`);
          }

          // Check for missing controls on DENY policies
          if (policy.decision === 'DENY' && (!policy.controls || policy.controls.length === 0)) {
            warnings.push(`${file.path}: DENY policy ${policy.policy_id} should reference controls`);
          }

          // Check for QUARANTINE without approval config
          if (policy.decision === 'QUARANTINE' && !policy.approval) {
            warnings.push(`${file.path}: QUARANTINE policy ${policy.policy_id} missing approval config`);
          }

          // Check for wildcards in production policies
          if (policy.scope.actor_type === '*' && policy.scope.action === '*' && policy.scope.resource_type === '*') {
            warnings.push(`${file.path}: Policy ${policy.policy_id} uses triple wildcards (very broad)`);
          }
        }
      }

      if (warnings.length > 0) {
        spinner.warn(`Found ${warnings.length} lint warning(s)`);
        for (const warning of warnings) {
          console.log(chalk.yellow(`  ⚠ ${warning}`));
        }
      } else {
        spinner.succeed('No lint warnings found');
      }

      if (options.fix && fixed > 0) {
        console.log(chalk.green(`Fixed ${fixed} issue(s)`));
      }
    } catch (error) {
      spinner.fail(`Lint error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// CHECK-CONFLICTS
// =============================================================================

policyCommand
  .command('check-conflicts <path>')
  .description('Check for conflicting policies')
  .action(async (policyPath: string) => {
    const spinner = ora('Checking for conflicts...').start();

    try {
      const files = await loadPolicyFiles(policyPath);
      const allPolicies: Array<{ policy: PolicyArtifact; file: string }> = [];

      for (const file of files) {
        for (const policy of file.policies) {
          allPolicies.push({ policy, file: file.path });
        }
      }

      const conflicts: string[] = [];

      // Check for duplicate policy IDs
      const idCounts = new Map<string, string[]>();
      for (const { policy, file } of allPolicies) {
        const key = `${policy.policy_id}@${policy.version}`;
        const files = idCounts.get(key) || [];
        files.push(file);
        idCounts.set(key, files);
      }

      for (const [key, files] of idCounts) {
        if (files.length > 1) {
          conflicts.push(`Duplicate policy ${key} in: ${files.join(', ')}`);
        }
      }

      // Check for overlapping scopes with different decisions
      for (let i = 0; i < allPolicies.length; i++) {
        for (let j = i + 1; j < allPolicies.length; j++) {
          const a = allPolicies[i];
          const b = allPolicies[j];

          if (scopesOverlap(a.policy.scope, b.policy.scope)) {
            if (a.policy.decision !== b.policy.decision) {
              const priority1 = a.policy.priority ?? 1000;
              const priority2 = b.policy.priority ?? 1000;

              if (priority1 === priority2) {
                conflicts.push(
                  `Conflicting decisions at same priority: ` +
                  `${a.policy.policy_id} (${a.policy.decision}) vs ` +
                  `${b.policy.policy_id} (${b.policy.decision})`
                );
              }
            }
          }
        }
      }

      if (conflicts.length > 0) {
        spinner.fail(`Found ${conflicts.length} conflict(s)`);
        for (const conflict of conflicts) {
          console.log(chalk.red(`  ✗ ${conflict}`));
        }
        process.exit(1);
      }

      spinner.succeed(`No conflicts found in ${allPolicies.length} policies`);
    } catch (error) {
      spinner.fail(`Conflict check error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// DEPLOY
// =============================================================================

policyCommand
  .command('deploy <path>')
  .description('Deploy policies to STIX Enforcer')
  .requiredOption('--api-url <url>', 'STIX API URL')
  .option('--api-key <key>', 'API key (or use STIX_API_KEY env var)')
  .option('--environment <env>', 'Target environment', 'production')
  .option('--dry-run', 'Validate without deploying')
  .option('--require-approval', 'Require approval for deployment')
  .action(async (policyPath: string, options: {
    apiUrl: string;
    apiKey?: string;
    environment: string;
    dryRun?: boolean;
    requireApproval?: boolean;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    if (!apiKey) {
      console.error(chalk.red('API key required (--api-key or STIX_API_KEY env var)'));
      process.exit(1);
    }

    const spinner = ora('Loading policies...').start();

    try {
      const files = await loadPolicyFiles(policyPath);
      let totalPolicies = 0;

      for (const file of files) {
        totalPolicies += file.policies.length;
      }

      spinner.text = `Deploying ${totalPolicies} policies to ${options.environment}...`;

      if (options.dryRun) {
        spinner.succeed(`Dry run: Would deploy ${totalPolicies} policies`);
        return;
      }

      // Deploy each policy
      let deployed = 0;
      let failed = 0;

      for (const file of files) {
        for (const policy of file.policies) {
          try {
            const response = await request(`${options.apiUrl}/v1/policies`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
              },
              body: JSON.stringify({
                ...policy,
                content_hash: hashPolicy(policy),
              }),
            });

            if (response.statusCode >= 200 && response.statusCode < 300) {
              deployed++;
            } else {
              failed++;
              const body = await response.body.text();
              console.log(chalk.red(`  ✗ ${policy.policy_id}: ${body}`));
            }
          } catch (error) {
            failed++;
            console.log(chalk.red(`  ✗ ${policy.policy_id}: ${(error as Error).message}`));
          }
        }
      }

      if (failed > 0) {
        spinner.warn(`Deployed ${deployed} policies, ${failed} failed`);
        process.exit(1);
      }

      spinner.succeed(`Deployed ${deployed} policies to ${options.environment}`);
    } catch (error) {
      spinner.fail(`Deploy error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// VERIFY
// =============================================================================

policyCommand
  .command('verify')
  .description('Verify deployed policies')
  .requiredOption('--api-url <url>', 'STIX API URL')
  .option('--api-key <key>', 'API key')
  .option('--expected-count <count>', 'Expected policy count')
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
    expectedCount?: string;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const spinner = ora('Verifying policies...').start();

    try {
      const response = await request(`${options.apiUrl}/v1/policies`, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
      });

      const body = await response.body.json() as { policies: unknown[]; total: number };

      if (options.expectedCount) {
        const expected = parseInt(options.expectedCount, 10);
        if (body.total !== expected) {
          spinner.fail(`Expected ${expected} policies, found ${body.total}`);
          process.exit(1);
        }
      }

      spinner.succeed(`Verified ${body.total} policies deployed`);
    } catch (error) {
      spinner.fail(`Verify error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// EXPORT
// =============================================================================

policyCommand
  .command('export')
  .description('Export policies from STIX Enforcer')
  .requiredOption('--api-url <url>', 'STIX API URL')
  .option('--api-key <key>', 'API key')
  .option('--output <file>', 'Output file path', 'policies-export.yaml')
  .action(async (options: {
    apiUrl: string;
    apiKey?: string;
    output: string;
  }) => {
    const apiKey = options.apiKey || process.env.STIX_API_KEY;
    const spinner = ora('Exporting policies...').start();

    try {
      const response = await request(`${options.apiUrl}/v1/policies`, {
        method: 'GET',
        headers: apiKey ? { 'Authorization': `Bearer ${apiKey}` } : {},
      });

      const body = await response.body.json() as { policies: PolicyArtifact[] };

      const yaml = stringifyYaml({ policies: body.policies });
      await fs.writeFile(options.output, yaml);

      spinner.succeed(`Exported ${body.policies.length} policies to ${options.output}`);
    } catch (error) {
      spinner.fail(`Export error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// DIFF
// =============================================================================

policyCommand
  .command('diff <basePath> <targetPath>')
  .description('Compare policies between two directories')
  .option('--output <file>', 'Output diff to file')
  .action(async (basePath: string, targetPath: string, options: { output?: string }) => {
    const spinner = ora('Comparing policies...').start();

    try {
      const baseFiles = await loadPolicyFiles(basePath);
      const targetFiles = await loadPolicyFiles(targetPath);

      const baseMap = new Map<string, PolicyArtifact>();
      const targetMap = new Map<string, PolicyArtifact>();

      for (const file of baseFiles) {
        for (const policy of file.policies) {
          baseMap.set(`${policy.policy_id}@${policy.version}`, policy);
        }
      }

      for (const file of targetFiles) {
        for (const policy of file.policies) {
          targetMap.set(`${policy.policy_id}@${policy.version}`, policy);
        }
      }

      const added: string[] = [];
      const removed: string[] = [];
      const modified: string[] = [];

      for (const [key, policy] of targetMap) {
        if (!baseMap.has(key)) {
          added.push(`+ ${key}: ${policy.decision} - ${policy.description || 'No description'}`);
        } else {
          const basePolicy = baseMap.get(key)!;
          if (hashPolicy(policy) !== hashPolicy(basePolicy)) {
            modified.push(`~ ${key}: ${basePolicy.decision} → ${policy.decision}`);
          }
        }
      }

      for (const [key] of baseMap) {
        if (!targetMap.has(key)) {
          removed.push(`- ${key}`);
        }
      }

      spinner.stop();

      const output = [
        `# Policy Diff`,
        `# Base: ${basePath}`,
        `# Target: ${targetPath}`,
        ``,
        `## Added (${added.length})`,
        ...added,
        ``,
        `## Removed (${removed.length})`,
        ...removed,
        ``,
        `## Modified (${modified.length})`,
        ...modified,
      ].join('\n');

      if (options.output) {
        await fs.writeFile(options.output, output);
        console.log(chalk.green(`Diff written to ${options.output}`));
      } else {
        console.log(output);
      }

      console.log(chalk.cyan(`\nSummary: +${added.length} -${removed.length} ~${modified.length}`));
    } catch (error) {
      spinner.fail(`Diff error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// REPORT
// =============================================================================

policyCommand
  .command('report <path>')
  .description('Generate policy report')
  .option('--output <file>', 'Output file path')
  .action(async (policyPath: string, options: { output?: string }) => {
    const spinner = ora('Generating report...').start();

    try {
      const files = await loadPolicyFiles(policyPath);
      const allPolicies: PolicyArtifact[] = [];

      for (const file of files) {
        allPolicies.push(...file.policies);
      }

      // Generate statistics
      const byDecision = {
        ALLOW: allPolicies.filter(p => p.decision === 'ALLOW').length,
        DENY: allPolicies.filter(p => p.decision === 'DENY').length,
        QUARANTINE: allPolicies.filter(p => p.decision === 'QUARANTINE').length,
      };

      const controlSet = new Set<string>();
      const regulationSet = new Set<string>();

      for (const policy of allPolicies) {
        policy.controls?.forEach(c => controlSet.add(c));
        policy.regulations?.forEach(r => regulationSet.add(r));
      }

      const report = [
        `# STIX Policy Report`,
        ``,
        `Generated: ${new Date().toISOString()}`,
        ``,
        `## Summary`,
        ``,
        `- Total Policies: ${allPolicies.length}`,
        `- Files: ${files.length}`,
        `- ALLOW: ${byDecision.ALLOW}`,
        `- DENY: ${byDecision.DENY}`,
        `- QUARANTINE: ${byDecision.QUARANTINE}`,
        ``,
        `## Controls Covered`,
        ``,
        ...Array.from(controlSet).sort().map(c => `- ${c}`),
        ``,
        `## Regulations Covered`,
        ``,
        ...Array.from(regulationSet).sort().map(r => `- ${r}`),
        ``,
        `## Policy List`,
        ``,
        `| ID | Decision | Description |`,
        `|----|----------|-------------|`,
        ...allPolicies.map(p => `| ${p.policy_id} | ${p.decision} | ${p.description || '-'} |`),
      ].join('\n');

      spinner.stop();

      if (options.output) {
        await fs.writeFile(options.output, report);
        console.log(chalk.green(`Report written to ${options.output}`));
      } else {
        console.log(report);
      }
    } catch (error) {
      spinner.fail(`Report error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

// =============================================================================
// HELPERS
// =============================================================================

async function loadPolicyFiles(policyPath: string): Promise<PolicyFile[]> {
  const stat = await fs.stat(policyPath);
  const files: PolicyFile[] = [];

  if (stat.isDirectory()) {
    const yamlFiles = await glob('**/*.yaml', { cwd: policyPath });
    for (const file of yamlFiles) {
      const fullPath = path.join(policyPath, file);
      const content = await fs.readFile(fullPath, 'utf-8');
      const parsed = parseYaml(content) as { policies?: PolicyArtifact[] };
      if (parsed.policies) {
        files.push({ path: fullPath, policies: parsed.policies });
      }
    }
  } else {
    const content = await fs.readFile(policyPath, 'utf-8');
    const parsed = parseYaml(content) as { policies?: PolicyArtifact[] };
    if (parsed.policies) {
      files.push({ path: policyPath, policies: parsed.policies });
    }
  }

  return files;
}

function validatePolicyFile(file: PolicyFile): string[] {
  const errors: string[] = [];

  for (const policy of file.policies) {
    if (!policy.policy_id) {
      errors.push(`${file.path}: Missing policy_id`);
    }
    if (!policy.version) {
      errors.push(`${file.path}: Policy ${policy.policy_id} missing version`);
    }
    if (!policy.scope) {
      errors.push(`${file.path}: Policy ${policy.policy_id} missing scope`);
    } else {
      if (!policy.scope.actor_type) {
        errors.push(`${file.path}: Policy ${policy.policy_id} missing scope.actor_type`);
      }
      if (!policy.scope.action) {
        errors.push(`${file.path}: Policy ${policy.policy_id} missing scope.action`);
      }
      if (!policy.scope.resource_type) {
        errors.push(`${file.path}: Policy ${policy.policy_id} missing scope.resource_type`);
      }
    }
    if (!['ALLOW', 'DENY', 'QUARANTINE'].includes(policy.decision)) {
      errors.push(`${file.path}: Policy ${policy.policy_id} invalid decision: ${policy.decision}`);
    }
    if (!policy.reason_code) {
      errors.push(`${file.path}: Policy ${policy.policy_id} missing reason_code`);
    }
  }

  return errors;
}

function scopesOverlap(a: PolicyArtifact['scope'], b: PolicyArtifact['scope']): boolean {
  return (
    (a.actor_type === '*' || b.actor_type === '*' || a.actor_type === b.actor_type) &&
    (a.action === '*' || b.action === '*' || matchGlob(a.action, b.action)) &&
    (a.resource_type === '*' || b.resource_type === '*' || matchGlob(a.resource_type, b.resource_type))
  );
}

function matchGlob(pattern: string, value: string): boolean {
  if (pattern === value) return true;
  if (pattern.endsWith('*')) {
    return value.startsWith(pattern.slice(0, -1));
  }
  return false;
}

function hashPolicy(policy: PolicyArtifact): string {
  const content = JSON.stringify({
    policy_id: policy.policy_id,
    version: policy.version,
    scope: policy.scope,
    conditions: policy.conditions,
    decision: policy.decision,
    obligations: policy.obligations,
    approval: policy.approval,
  });
  return createHash('sha256').update(content).digest('hex').substring(0, 16);
}
