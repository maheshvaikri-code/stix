/**
 * STIX Shared Policy Loader
 * Common policy loading utilities used across tools
 *
 * @module @stix/shared/policy
 */

import * as fs from 'fs';
import * as path from 'path';
import { createHash } from 'crypto';

// =============================================================================
// TYPES
// =============================================================================

/**
 * Core policy definition
 */
export interface Policy {
  id: string;
  policy_id?: string;  // Alias for id
  version: string;
  priority: number;
  description?: string;
  scope?: PolicyScope;
  match?: PolicyMatch;
  conditions?: PolicyCondition[];
  decision: 'ALLOW' | 'DENY' | 'QUARANTINE';
  reason_code: string;
  obligations?: PolicyObligation[];
  approval?: PolicyApprovalConfig;
  controls?: string[];
  regulations?: string[];
  tags?: string[];
  active?: boolean;
}

export interface PolicyScope {
  actor_type: string;
  action: string;
  resource_type: string;
}

export interface PolicyMatch {
  actor?: any;
  action?: string;
  resource?: any;
}

export interface PolicyCondition {
  field: string;
  operator: string;
  value: any;
}

export interface PolicyObligation {
  type: string;
  params?: Record<string, any>;
}

export interface PolicyApprovalConfig {
  approver_role?: string;
  require_count?: number;
  require_justification?: boolean;
  require_ticket?: boolean;
  timeout_hours?: number;
}

/**
 * Loaded policy pack with metadata
 */
export interface PolicyPack {
  id: string;
  version: string;
  hash: string;
  source: string;
  policies: Policy[];
  metadata?: PolicyPackMetadata;
}

export interface PolicyPackMetadata {
  name?: string;
  description?: string;
  author?: string;
  created_at?: string;
  updated_at?: string;
  regulations?: string[];
  tags?: string[];
}

/**
 * Policy pack manifest
 */
export interface PolicyPackManifest {
  id: string;
  version: string;
  name?: string;
  description?: string;
  policies: PolicyFileEntry[];
}

export interface PolicyFileEntry {
  file: string;
  id?: string;
  hash?: string;
}

// =============================================================================
// LOADING
// =============================================================================

/**
 * Load a policy pack from a file or directory
 */
export async function loadPolicyPack(packPath: string): Promise<PolicyPack> {
  const stat = fs.statSync(packPath);

  if (stat.isDirectory()) {
    return loadPackFromDirectory(packPath);
  } else {
    return loadPackFromFile(packPath);
  }
}

/**
 * Load policies from a directory
 */
async function loadPackFromDirectory(dirPath: string): Promise<PolicyPack> {
  const policies: Policy[] = [];

  // Check for manifest
  const manifestPath = path.join(dirPath, 'manifest.yaml');
  const manifestJsonPath = path.join(dirPath, 'manifest.json');

  let manifest: PolicyPackManifest | null = null;

  if (fs.existsSync(manifestPath)) {
    const yaml = await importYaml();
    manifest = yaml.parse(fs.readFileSync(manifestPath, 'utf-8'));
  } else if (fs.existsSync(manifestJsonPath)) {
    manifest = JSON.parse(fs.readFileSync(manifestJsonPath, 'utf-8'));
  }

  if (manifest) {
    // Load from manifest
    for (const entry of manifest.policies) {
      const filePath = path.join(dirPath, entry.file);
      const filePolicies = await loadPoliciesFromFile(filePath);
      policies.push(...filePolicies);
    }

    return {
      id: manifest.id,
      version: manifest.version,
      hash: computePackHash(policies),
      source: dirPath,
      policies,
      metadata: {
        name: manifest.name,
        description: manifest.description,
      },
    };
  }

  // No manifest - scan for policy files
  const files = findPolicyFiles(dirPath);

  for (const file of files) {
    const filePolicies = await loadPoliciesFromFile(file);
    policies.push(...filePolicies);
  }

  return {
    id: path.basename(dirPath),
    version: '1.0.0',
    hash: computePackHash(policies),
    source: dirPath,
    policies,
  };
}

/**
 * Load policies from a single file
 */
async function loadPackFromFile(filePath: string): Promise<PolicyPack> {
  const policies = await loadPoliciesFromFile(filePath);

  return {
    id: path.basename(filePath, path.extname(filePath)),
    version: '1.0.0',
    hash: computePackHash(policies),
    source: filePath,
    policies,
  };
}

/**
 * Load policies from a file (YAML or JSON)
 */
export async function loadPoliciesFromFile(filePath: string): Promise<Policy[]> {
  const content = fs.readFileSync(filePath, 'utf-8');
  const ext = path.extname(filePath).toLowerCase();

  let documents: any[];

  if (ext === '.yaml' || ext === '.yml') {
    const yaml = await importYaml();
    documents = yaml.parseAllDocuments(content).map((doc: any) => doc.toJSON());
  } else if (ext === '.json') {
    const parsed = JSON.parse(content);
    documents = Array.isArray(parsed) ? parsed : [parsed];
  } else if (ext === '.jsonl') {
    documents = content
      .split('\n')
      .filter(line => line.trim())
      .map(line => JSON.parse(line));
  } else {
    throw new Error(`Unsupported file type: ${ext}`);
  }

  // Normalize and filter valid policies
  return documents
    .filter(doc => doc && (doc.id || doc.policy_id))
    .map(normalizePolicy);
}

/**
 * Find all policy files in a directory
 */
function findPolicyFiles(dirPath: string): string[] {
  const files: string[] = [];

  function scanDir(dir: string) {
    const entries = fs.readdirSync(dir, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(dir, entry.name);

      if (entry.isDirectory()) {
        scanDir(fullPath);
      } else if (entry.isFile()) {
        const ext = path.extname(entry.name).toLowerCase();
        if (['.yaml', '.yml', '.json'].includes(ext)) {
          // Skip manifest files
          if (!entry.name.startsWith('manifest')) {
            files.push(fullPath);
          }
        }
      }
    }
  }

  scanDir(dirPath);
  return files;
}

/**
 * Normalize policy format
 */
function normalizePolicy(raw: any): Policy {
  return {
    id: raw.id || raw.policy_id,
    version: raw.version || '1.0.0',
    priority: raw.priority ?? 1000,
    description: raw.description,
    scope: raw.scope,
    match: raw.match || convertScopeToMatch(raw.scope),
    conditions: normalizeConditions(raw.conditions),
    decision: raw.decision,
    reason_code: raw.reason_code,
    obligations: raw.obligations,
    approval: raw.approval,
    controls: raw.controls || [],
    regulations: raw.regulations || [],
    tags: raw.tags || [],
    active: raw.active !== false,
  };
}

/**
 * Convert scope to match format
 */
function convertScopeToMatch(scope: PolicyScope | undefined): PolicyMatch | undefined {
  if (!scope) return undefined;

  return {
    actor: scope.actor_type !== '*' ? { type: scope.actor_type } : undefined,
    action: scope.action,
    resource: scope.resource_type !== '*' ? { type: scope.resource_type } : undefined,
  };
}

/**
 * Normalize conditions format
 */
function normalizeConditions(conditions: any): PolicyCondition[] | undefined {
  if (!conditions) return undefined;

  // If already array of conditions
  if (Array.isArray(conditions)) {
    return conditions;
  }

  // Convert object format to condition array
  const result: PolicyCondition[] = [];

  if (conditions.require_signal) {
    for (const [key, value] of Object.entries(conditions.require_signal)) {
      result.push({
        field: `context.signals.${key}`,
        operator: 'eq',
        value,
      });
    }
  }

  if (conditions.require_resource_attr) {
    for (const [key, value] of Object.entries(conditions.require_resource_attr)) {
      result.push({
        field: `resource.attributes.${key}`,
        operator: 'eq',
        value,
      });
    }
  }

  if (conditions.require_actor_attr) {
    for (const [key, value] of Object.entries(conditions.require_actor_attr)) {
      result.push({
        field: `actor.attributes.${key}`,
        operator: 'eq',
        value,
      });
    }
  }

  if (conditions.env) {
    result.push({
      field: 'context.env',
      operator: 'eq',
      value: conditions.env,
    });
  }

  if (conditions.require_context) {
    for (const [key, value] of Object.entries(conditions.require_context)) {
      result.push({
        field: `context.${key}`,
        operator: 'eq',
        value,
      });
    }
  }

  return result.length > 0 ? result : undefined;
}

// =============================================================================
// HASHING
// =============================================================================

/**
 * Compute hash for a single policy
 */
export function computePolicyHash(policy: Policy): string {
  const normalized = JSON.stringify(policy, Object.keys(policy).sort());
  return createHash('sha256').update(normalized).digest('hex');
}

/**
 * Compute hash for entire policy pack
 */
export function computePackHash(policies: Policy[]): string {
  const sortedPolicies = [...policies].sort((a, b) => a.id.localeCompare(b.id));
  const hashes = sortedPolicies.map(p => computePolicyHash(p));
  return createHash('sha256').update(hashes.join('')).digest('hex');
}

/**
 * Format hash with prefix
 */
export function formatHash(hash: string): string {
  return `sha256:${hash}`;
}

// =============================================================================
// INDEXING
// =============================================================================

/**
 * Create policy index by ID
 */
export function indexById(policies: Policy[]): Map<string, Policy> {
  const index = new Map<string, Policy>();
  for (const policy of policies) {
    index.set(policy.id, policy);
  }
  return index;
}

/**
 * Create policy index by hash
 */
export function indexByHash(policies: Policy[]): Map<string, Policy> {
  const index = new Map<string, Policy>();
  for (const policy of policies) {
    index.set(computePolicyHash(policy), policy);
  }
  return index;
}

/**
 * Filter active policies
 */
export function filterActive(policies: Policy[]): Policy[] {
  return policies.filter(p => p.active !== false);
}

/**
 * Sort policies by priority
 */
export function sortByPriority(policies: Policy[]): Policy[] {
  return [...policies].sort((a, b) => a.priority - b.priority);
}

// =============================================================================
// STATISTICS
// =============================================================================

export interface PolicyPackStats {
  totalPolicies: number;
  activePolicies: number;
  byDecision: Record<string, number>;
  byPriority: {
    min: number;
    max: number;
    avg: number;
  };
  hasObligations: number;
  hasApproval: number;
  regulations: string[];
  controls: string[];
}

/**
 * Calculate statistics for a policy pack
 */
export function getPackStats(pack: PolicyPack): PolicyPackStats {
  const policies = pack.policies;

  const byDecision: Record<string, number> = {};
  let hasObligations = 0;
  let hasApproval = 0;
  const regulations = new Set<string>();
  const controls = new Set<string>();
  const priorities: number[] = [];

  for (const policy of policies) {
    // Decision counts
    byDecision[policy.decision] = (byDecision[policy.decision] || 0) + 1;

    // Obligations
    if (policy.obligations && policy.obligations.length > 0) {
      hasObligations++;
    }

    // Approval
    if (policy.approval) {
      hasApproval++;
    }

    // Regulations
    for (const reg of policy.regulations || []) {
      regulations.add(reg);
    }

    // Controls
    for (const ctrl of policy.controls || []) {
      controls.add(ctrl);
    }

    // Priority
    priorities.push(policy.priority);
  }

  return {
    totalPolicies: policies.length,
    activePolicies: filterActive(policies).length,
    byDecision,
    byPriority: {
      min: Math.min(...priorities),
      max: Math.max(...priorities),
      avg: priorities.reduce((a, b) => a + b, 0) / priorities.length,
    },
    hasObligations,
    hasApproval,
    regulations: Array.from(regulations),
    controls: Array.from(controls),
  };
}

// =============================================================================
// HELPERS
// =============================================================================

let yamlModule: any = null;

async function importYaml() {
  if (!yamlModule) {
    yamlModule = await import('yaml');
  }
  return yamlModule;
}
