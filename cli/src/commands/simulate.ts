/**
 * STIX CLI - Simulate Command
 */

import { Command } from 'commander';
import chalk from 'chalk';
import ora from 'ora';
import * as fs from 'fs/promises';
import * as path from 'path';
import { glob } from 'glob';
import { parse as parseYaml } from 'yaml';

interface SimulationScenario {
  name: string;
  description?: string;
  request: {
    actor: {
      id: string;
      type: string;
      role?: string;
      tenant?: string;
    };
    action: string;
    resource: {
      type: string;
      id?: string;
      classification?: string[];
    };
    context: {
      env: string;
      purpose?: string;
      signals?: Record<string, boolean>;
    };
  };
  expected: {
    decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
    reason_code?: string;
  };
}

interface PolicyArtifact {
  policy_id: string;
  version: string;
  priority?: number;
  scope: {
    actor_type: string;
    action: string;
    resource_type: string;
  };
  conditions?: Record<string, unknown>;
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  reason_code: string;
}

export const simulateCommand = new Command('simulate')
  .description('Simulate policy evaluation')
  .requiredOption('--policy-dir <path>', 'Directory containing policies')
  .option('--scenario-dir <path>', 'Directory containing test scenarios')
  .option('--scenario <file>', 'Single scenario file to run')
  .option('--verbose', 'Show detailed output')
  .action(async (options: {
    policyDir: string;
    scenarioDir?: string;
    scenario?: string;
    verbose?: boolean;
  }) => {
    const spinner = ora('Loading policies...').start();

    try {
      // Load policies
      const policies = await loadPolicies(options.policyDir);
      spinner.text = `Loaded ${policies.length} policies`;

      // Load scenarios
      let scenarios: SimulationScenario[] = [];

      if (options.scenario) {
        const content = await fs.readFile(options.scenario, 'utf-8');
        const parsed = parseYaml(content) as { scenarios?: SimulationScenario[] };
        scenarios = parsed.scenarios || [];
      } else if (options.scenarioDir) {
        scenarios = await loadScenarios(options.scenarioDir);
      } else {
        spinner.fail('Must specify --scenario or --scenario-dir');
        process.exit(1);
      }

      spinner.text = `Running ${scenarios.length} scenarios...`;

      // Run simulations
      let passed = 0;
      let failed = 0;
      const results: SimulationResult[] = [];

      for (const scenario of scenarios) {
        const result = runSimulation(scenario, policies);
        results.push(result);

        if (result.passed) {
          passed++;
          if (options.verbose) {
            console.log(chalk.green(`  ✓ ${scenario.name}`));
          }
        } else {
          failed++;
          console.log(chalk.red(`  ✗ ${scenario.name}`));
          console.log(chalk.red(`    Expected: ${result.expected}`));
          console.log(chalk.red(`    Actual: ${result.actual}`));
          if (result.matchedPolicy) {
            console.log(chalk.gray(`    Policy: ${result.matchedPolicy}`));
          }
        }
      }

      spinner.stop();

      // Summary
      console.log();
      if (failed === 0) {
        console.log(chalk.green(`All ${passed} simulations passed`));
      } else {
        console.log(chalk.red(`${failed} failed, ${passed} passed out of ${scenarios.length} simulations`));
        process.exit(1);
      }
    } catch (error) {
      spinner.fail(`Simulation error: ${(error as Error).message}`);
      process.exit(1);
    }
  });

interface SimulationResult {
  scenario: string;
  passed: boolean;
  expected: string;
  actual: string;
  matchedPolicy?: string;
}

async function loadPolicies(policyDir: string): Promise<PolicyArtifact[]> {
  const policies: PolicyArtifact[] = [];
  const files = await glob('**/*.yaml', { cwd: policyDir });

  for (const file of files) {
    const content = await fs.readFile(path.join(policyDir, file), 'utf-8');
    const parsed = parseYaml(content) as { policies?: PolicyArtifact[] };
    if (parsed.policies) {
      policies.push(...parsed.policies);
    }
  }

  // Sort by priority (lower is higher priority)
  policies.sort((a, b) => (a.priority ?? 1000) - (b.priority ?? 1000));

  return policies;
}

async function loadScenarios(scenarioDir: string): Promise<SimulationScenario[]> {
  const scenarios: SimulationScenario[] = [];
  const files = await glob('**/*.yaml', { cwd: scenarioDir });

  for (const file of files) {
    const content = await fs.readFile(path.join(scenarioDir, file), 'utf-8');
    const parsed = parseYaml(content) as { scenarios?: SimulationScenario[] };
    if (parsed.scenarios) {
      scenarios.push(...parsed.scenarios);
    }
  }

  return scenarios;
}

function runSimulation(
  scenario: SimulationScenario,
  policies: PolicyArtifact[]
): SimulationResult {
  const { request, expected } = scenario;

  // Find matching policy (first match wins due to priority sorting)
  let matchedPolicy: PolicyArtifact | undefined;
  let decision = 'DENY'; // Default deny if no policy matches

  for (const policy of policies) {
    if (matchesScope(request, policy.scope)) {
      if (matchesConditions(request, policy.conditions)) {
        matchedPolicy = policy;
        decision = policy.decision;
        break;
      }
    }
  }

  // Apply decision precedence: DENY > QUARANTINE > ALLOW
  // This is handled by priority sorting, but we could implement explicit precedence here

  const passed = decision === expected.decision;

  return {
    scenario: scenario.name,
    passed,
    expected: expected.decision,
    actual: decision,
    matchedPolicy: matchedPolicy?.policy_id,
  };
}

function matchesScope(
  request: SimulationScenario['request'],
  scope: PolicyArtifact['scope']
): boolean {
  // Actor type match
  if (scope.actor_type !== '*' && scope.actor_type !== request.actor.type) {
    return false;
  }

  // Action match (supports glob patterns)
  if (scope.action !== '*' && !matchPattern(scope.action, request.action)) {
    return false;
  }

  // Resource type match (supports glob patterns)
  if (scope.resource_type !== '*' && !matchPattern(scope.resource_type, request.resource.type)) {
    return false;
  }

  return true;
}

function matchesConditions(
  request: SimulationScenario['request'],
  conditions?: Record<string, unknown>
): boolean {
  if (!conditions) return true;

  // Environment condition
  if (conditions.env && conditions.env !== request.context.env) {
    return false;
  }

  // Signal requirements
  if (conditions.require_signal) {
    const signals = conditions.require_signal as Record<string, boolean>;
    for (const [signal, required] of Object.entries(signals)) {
      if (required && !request.context.signals?.[signal]) {
        return false;
      }
    }
  }

  // Resource classification
  if (conditions.require_classification) {
    const requiredClass = conditions.require_classification as string[];
    const hasClass = request.resource.classification?.some(c => requiredClass.includes(c));
    if (!hasClass) {
      return false;
    }
  }

  return true;
}

function matchPattern(pattern: string, value: string): boolean {
  if (pattern === value) return true;

  // Simple glob matching
  if (pattern.includes('*')) {
    const regex = new RegExp('^' + pattern.replace(/\*/g, '.*') + '$');
    return regex.test(value);
  }

  return false;
}
