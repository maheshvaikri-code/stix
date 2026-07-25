#!/usr/bin/env node
/**
 * STIX CLI - Command line tools for STIX management
 */

import { Command } from 'commander';
import { policyCommand } from './commands/policy.js';
import { evidenceCommand } from './commands/evidence.js';
import { simulateCommand } from './commands/simulate.js';
import { testCommand } from './commands/test.js';

const program = new Command();

program
  .name('stix')
  .description('STIX CLI - Shield Trust and Integrity eXecution')
  .version('0.1.7');

// Register commands
program.addCommand(policyCommand);
program.addCommand(evidenceCommand);
program.addCommand(simulateCommand);
program.addCommand(testCommand);

// Parse and execute
program.parse();
