#!/usr/bin/env node

import { promises as fs } from 'node:fs';
import path from 'node:path';
import process from 'node:process';
import { parseAllDocuments } from 'yaml';

const ROOT = process.cwd();
const requestedPath = process.argv[2] || 'policies';
const POLICY_PATH = path.resolve(ROOT, requestedPath);
const VALID_DECISIONS = new Set(['ALLOW', 'DENY', 'QUARANTINE']);

async function main() {
  const files = await findYamlFiles(POLICY_PATH);

  if (files.length === 0) {
    throw new Error(`No policy YAML files found under ${relative(POLICY_PATH)}`);
  }

  const errors = [];
  let policyCount = 0;

  for (const file of files) {
    const content = await fs.readFile(file, 'utf8');
    const docs = parseAllDocuments(content, { prettyErrors: true });

    if (docs.length === 0) {
      errors.push(`${relative(file)}: empty YAML document`);
      continue;
    }

    for (let i = 0; i < docs.length; i++) {
      const doc = docs[i];
      if (doc.errors.length > 0) {
        for (const err of doc.errors) {
          errors.push(`${relative(file)}: YAML parse error in doc ${i + 1}: ${err.message}`);
        }
        continue;
      }

      const value = doc.toJSON();
      const policies = extractPolicies(value);

      if (policies.error) {
        errors.push(`${relative(file)}: doc ${i + 1}: ${policies.error}`);
        continue;
      }

      for (const policy of policies.items) {
        policyCount += 1;
        const validationErrors = validatePolicy(policy);
        for (const err of validationErrors) {
          const id = typeof policy?.policy_id === 'string' ? policy.policy_id : '<missing-policy-id>';
          errors.push(`${relative(file)}: policy ${id}: ${err}`);
        }
      }
    }
  }

  if (errors.length > 0) {
    console.error('Policy validation failed.');
    for (const err of errors) {
      console.error(`- ${err}`);
    }
    process.exit(1);
  }

  const summary = `Validated ${policyCount} policies in ${files.length} YAML file(s).`;
  console.log(summary);

  const outputPath = process.env.GITHUB_STEP_SUMMARY;
  if (outputPath) {
    await fs.appendFile(outputPath, `${summary}\n`);
  }
}

function extractPolicies(value) {
  if (value == null) {
    return { items: [] };
  }

  if (Array.isArray(value)) {
    return { items: value };
  }

  if (typeof value === 'object') {
    if (Array.isArray(value.policies)) {
      return { items: value.policies };
    }

    if (value.policy_id) {
      return { items: [value] };
    }
  }

  return {
    items: [],
    error: 'unsupported policy document structure (expected array, {policies: []}, or single policy object)'
  };
}

function validatePolicy(policy) {
  const errors = [];

  if (!isPlainObject(policy)) {
    return ['policy entry must be an object'];
  }

  if (!policy.policy_id || typeof policy.policy_id !== 'string') {
    errors.push('missing required field: policy_id (string)');
  }

  if (!policy.version || typeof policy.version !== 'string') {
    errors.push('missing required field: version (string)');
  }

  if (!isPlainObject(policy.scope)) {
    errors.push('missing required field: scope (object)');
  } else {
    if (!policy.scope.actor_type) {
      errors.push('scope.actor_type is required');
    }
    if (!policy.scope.action) {
      errors.push('scope.action is required');
    }
    if (!policy.scope.resource_type) {
      errors.push('scope.resource_type is required');
    }
  }

  if (!policy.decision || typeof policy.decision !== 'string') {
    errors.push('missing required field: decision (string)');
  } else if (!VALID_DECISIONS.has(policy.decision)) {
    errors.push(`decision must be one of ${Array.from(VALID_DECISIONS).join(', ')}`);
  }

  if (!policy.reason_code || typeof policy.reason_code !== 'string') {
    errors.push('missing required field: reason_code (string)');
  }

  return errors;
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

async function findYamlFiles(dir) {
  let stat;
  try {
    stat = await fs.stat(dir);
  } catch (err) {
    throw new Error(`Cannot access policy path ${relative(dir)}: ${err.message}`);
  }

  if (stat.isFile()) {
    if (dir.endsWith('.yaml')) {
      return [dir];
    }
    return [];
  }

  let entries;
  try {
    entries = await fs.readdir(dir, { withFileTypes: true });
  } catch (err) {
    throw new Error(`Cannot read policy path ${relative(dir)}: ${err.message}`);
  }

  const results = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      results.push(...await findYamlFiles(fullPath));
      continue;
    }

    if (entry.isFile() && fullPath.endsWith('.yaml')) {
      results.push(fullPath);
    }
  }

  return results;
}

function relative(filePath) {
  return path.relative(ROOT, filePath).replace(/\\/g, '/');
}

main().catch((err) => {
  console.error(err.message);
  process.exit(1);
});
