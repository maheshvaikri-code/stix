/**
 * STIX Shared Policy Artifact Pack Loader
 * Deterministic loading + hashing for PolicyArtifact packs used by runtime/simulate/replay.
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import * as yaml from 'yaml';

import type { PolicyArtifact } from '../types/index.js';
import { hashCanonical } from '../utils/index.js';

// =============================================================================
// TYPES
// =============================================================================

export interface PolicyArtifactPackManifest {
  id?: string;
  version?: string;
  hash?: string;
  name?: string;
  description?: string;
  policies?: Array<{
    file: string;
    id?: string;
    hash?: string;
  }>;
}

export interface PolicyArtifactPack {
  id: string;
  version: string;
  hash: string;
  source: string;
  policies: PolicyArtifact[];
  policyIndex: Map<string, PolicyArtifact>;
  hashIndex: Map<string, PolicyArtifact>;
  metadata?: {
    name?: string;
    description?: string;
  };
}

export interface PolicyArtifactPackStats {
  totalPolicies: number;
  byDecision: Record<string, number>;
  byPriority: { min: number; max: number; avg: number };
  hasObligations: number;
  hasApproval: number;
  regulations: string[];
  controls: string[];
}

// =============================================================================
// LOADING
// =============================================================================

/**
 * Load a policy artifact pack from a directory or file.
 */
export async function loadPolicyArtifactPack(packPath: string): Promise<PolicyArtifactPack> {
  const stat = fs.statSync(packPath);
  if (stat.isDirectory()) {
    return loadPolicyArtifactPackFromDirectory(packPath);
  }
  return loadPolicyArtifactPackFromFile(packPath);
}

/**
 * Load and validate policies from a single file.
 */
export async function loadPolicyArtifactsFromFile(filePath: string): Promise<PolicyArtifact[]> {
  const content = fs.readFileSync(filePath, 'utf-8');
  const ext = path.extname(filePath).toLowerCase();

  let topLevelDocs: unknown[] = [];
  if (ext === '.yaml' || ext === '.yml') {
    const docs = yaml.parseAllDocuments(content);
    topLevelDocs = docs.map((doc, idx) => {
      if (doc.errors.length > 0) {
        throw new Error(`YAML parse error in ${filePath} (doc ${idx + 1})`);
      }
      return doc.toJSON();
    });
  } else if (ext === '.json') {
    topLevelDocs = [JSON.parse(content)];
  } else if (ext === '.jsonl' || ext === '.ndjson') {
    topLevelDocs = content
      .split('\n')
      .filter((line) => line.trim().length > 0)
      .map((line) => JSON.parse(line));
  } else {
    throw new Error(`Unsupported policy file type: ${filePath}`);
  }

  const candidates: unknown[] = [];
  for (const doc of topLevelDocs) {
    candidates.push(...extractPolicyCandidates(doc));
  }

  const policies: PolicyArtifact[] = [];
  for (const candidate of candidates) {
    policies.push(normalizePolicyArtifact(candidate, filePath));
  }

  return policies;
}

function loadPolicyArtifactPackFromFile(filePath: string): Promise<PolicyArtifactPack> {
  const id = path.basename(filePath, path.extname(filePath));
  return buildPolicyArtifactPack({
    sourcePath: filePath,
    id,
    version: '1.0.0',
    policyFilePaths: [filePath],
  });
}

async function loadPolicyArtifactPackFromDirectory(dirPath: string): Promise<PolicyArtifactPack> {
  const manifest = loadManifestIfPresent(dirPath);
  const policyFilePaths = manifest?.policies?.length
    ? manifest.policies.map((entry) => path.resolve(dirPath, entry.file))
    : findPolicyFiles(dirPath);

  return buildPolicyArtifactPack({
    sourcePath: dirPath,
    id: manifest?.id || path.basename(dirPath),
    version: manifest?.version || '1.0.0',
    expectedHash: manifest?.hash,
    policyFilePaths,
    metadata: manifest
      ? {
          name: manifest.name,
          description: manifest.description,
        }
      : undefined,
  });
}

function loadManifestIfPresent(dirPath: string): PolicyArtifactPackManifest | null {
  const yamlPath = path.join(dirPath, 'manifest.yaml');
  const ymlPath = path.join(dirPath, 'manifest.yml');
  const jsonPath = path.join(dirPath, 'manifest.json');

  if (fs.existsSync(yamlPath)) {
    return yaml.parse(fs.readFileSync(yamlPath, 'utf-8'));
  }
  if (fs.existsSync(ymlPath)) {
    return yaml.parse(fs.readFileSync(ymlPath, 'utf-8'));
  }
  if (fs.existsSync(jsonPath)) {
    return JSON.parse(fs.readFileSync(jsonPath, 'utf-8'));
  }

  return null;
}

function findPolicyFiles(dirPath: string): string[] {
  const files: string[] = [];

  function scan(currentDir: string): void {
    const entries = fs.readdirSync(currentDir, { withFileTypes: true });
    for (const entry of entries) {
      const fullPath = path.join(currentDir, entry.name);

      if (entry.isDirectory()) {
        scan(fullPath);
        continue;
      }

      if (!entry.isFile()) continue;
      if (/^manifest\.(ya?ml|json)$/i.test(entry.name)) continue;
      if (!/\.(ya?ml|json|jsonl|ndjson)$/i.test(entry.name)) continue;
      files.push(fullPath);
    }
  }

  scan(dirPath);
  return files;
}

async function buildPolicyArtifactPack(args: {
  sourcePath: string;
  id: string;
  version: string;
  policyFilePaths: string[];
  expectedHash?: string;
  metadata?: { name?: string; description?: string };
}): Promise<PolicyArtifactPack> {
  const policies: PolicyArtifact[] = [];
  for (const filePath of args.policyFilePaths) {
    policies.push(...(await loadPolicyArtifactsFromFile(filePath)));
  }

  policies.sort(
    (a, b) =>
      (a.priority ?? 100) - (b.priority ?? 100) ||
      a.policy_id.localeCompare(b.policy_id)
  );

  const policyIndex = new Map<string, PolicyArtifact>();
  const hashIndex = new Map<string, PolicyArtifact>();

  for (const policy of policies) {
    if (policyIndex.has(policy.policy_id)) {
      throw new Error(`Duplicate policy_id in pack: ${policy.policy_id}`);
    }

    const policyHash = computeRuntimePolicyHash(policy);
    policyIndex.set(policy.policy_id, policy);
    hashIndex.set(policyHash, policy);
    hashIndex.set(stripHashPrefix(policyHash), policy);
  }

  const computedPackHash = computePolicyArtifactPackHash(policies);
  const expectedHash = args.expectedHash ? normalizeHash(args.expectedHash) : undefined;
  if (expectedHash && expectedHash !== computedPackHash) {
    throw new Error(
      `Manifest hash mismatch for ${args.sourcePath}: expected ${expectedHash}, computed ${computedPackHash}`
    );
  }

  return {
    id: args.id,
    version: args.version,
    hash: computedPackHash,
    source: args.sourcePath,
    policies,
    policyIndex,
    hashIndex,
    metadata: args.metadata,
  };
}

function extractPolicyCandidates(doc: unknown): unknown[] {
  if (doc == null) return [];
  if (Array.isArray(doc)) return doc;

  if (typeof doc === 'object') {
    const obj = doc as Record<string, unknown>;
    if (Array.isArray(obj.policies)) return obj.policies;
    if (typeof obj.policy_id === 'string') return [obj];
  }

  return [];
}

function normalizePolicyArtifact(candidate: unknown, filePath: string): PolicyArtifact {
  if (!candidate || typeof candidate !== 'object') {
    throw new Error(`Invalid policy in ${filePath}: policy must be an object`);
  }

  const raw = candidate as Record<string, any>;
  if (typeof raw.policy_id !== 'string' || raw.policy_id.length === 0) {
    throw new Error(`Invalid policy in ${filePath}: missing policy_id`);
  }
  if (!raw.scope || typeof raw.scope !== 'object') {
    throw new Error(`Invalid policy in ${filePath}: missing scope`);
  }
  if (!isValidDecision(raw.decision)) {
    throw new Error(`Invalid policy in ${filePath}: invalid decision '${raw.decision}'`);
  }

  const scope = raw.scope as Record<string, any>;
  if (typeof scope.actor_type !== 'string' || typeof scope.action !== 'string' || typeof scope.resource_type !== 'string') {
    throw new Error(`Invalid policy in ${filePath}: scope.actor_type/action/resource_type are required`);
  }

  const normalized: PolicyArtifact = {
    policy_id: raw.policy_id,
    version: typeof raw.version === 'string' ? raw.version : '1.0.0',
    priority: typeof raw.priority === 'number' ? raw.priority : 100,
    description: typeof raw.description === 'string' ? raw.description : undefined,
    scope: {
      actor_type: normalizeActorType(scope.actor_type),
      action: scope.action,
      resource_type: scope.resource_type,
      environments: Array.isArray(scope.environments) ? scope.environments : undefined,
      classifications: Array.isArray(scope.classifications) ? scope.classifications : undefined,
    },
    conditions: normalizeConditions(raw.conditions),
    decision: raw.decision,
    reason_code:
      typeof raw.reason_code === 'string' && raw.reason_code.length > 0
        ? raw.reason_code
        : `POLICY_${raw.decision}`,
    obligations: normalizeObligations(raw.obligations),
    approval: normalizeApproval(raw.approval),
    controls: Array.isArray(raw.controls) ? raw.controls : undefined,
    regulations: Array.isArray(raw.regulations) ? raw.regulations : undefined,
    tags: Array.isArray(raw.tags) ? raw.tags : undefined,
    active: raw.active !== false,
    created_at: typeof raw.created_at === 'string' ? raw.created_at : undefined,
    updated_at: typeof raw.updated_at === 'string' ? raw.updated_at : undefined,
  };

  return normalized;
}

function normalizeConditions(raw: unknown): PolicyArtifact['conditions'] {
  if (!raw) return undefined;

  if (Array.isArray(raw)) {
    const mapped = mapLegacyConditions(raw);
    return Object.keys(mapped).length > 0 ? mapped : undefined;
  }

  if (typeof raw !== 'object') return undefined;
  const obj = { ...(raw as Record<string, unknown>) };
  if (typeof obj.environment === 'string' && obj.env === undefined) {
    obj.env = normalizeEnvironment(obj.environment);
  }
  delete obj.environment;
  return obj as PolicyArtifact['conditions'];
}

function mapLegacyConditions(conditions: unknown[]): NonNullable<PolicyArtifact['conditions']> {
  const mapped: Record<string, unknown> = {};
  const legacyUnmapped: unknown[] = [];

  for (const entry of conditions) {
    if (!entry || typeof entry !== 'object') {
      legacyUnmapped.push(entry);
      continue;
    }

    const cond = entry as Record<string, any>;
    const field = typeof cond.field === 'string' ? cond.field : '';
    const op = typeof cond.op === 'string' ? cond.op : typeof cond.operator === 'string' ? cond.operator : '';
    const value = cond.value;

    if ((field === 'context.environment' || field === 'context.env') && (op === 'eq' || op === 'equals')) {
      mapped.env = normalizeEnvironment(value);
      continue;
    }

    if (field.startsWith('context.signals.') && (op === 'eq' || op === 'equals')) {
      const key = field.slice('context.signals.'.length);
      const requireSignal = (mapped.require_signal ?? {}) as Record<string, unknown>;
      requireSignal[key] = value;
      mapped.require_signal = requireSignal;
      continue;
    }

    if (field.startsWith('resource.attributes.') && (op === 'eq' || op === 'equals')) {
      const key = field.slice('resource.attributes.'.length);
      const requireResourceAttr = (mapped.require_resource_attr ?? {}) as Record<string, unknown>;
      requireResourceAttr[key] = value;
      mapped.require_resource_attr = requireResourceAttr;
      continue;
    }

    if (field.startsWith('actor.attributes.') && (op === 'eq' || op === 'equals')) {
      const key = field.slice('actor.attributes.'.length);
      const requireActorAttr = (mapped.require_actor_attr ?? {}) as Record<string, unknown>;
      requireActorAttr[key] = value;
      mapped.require_actor_attr = requireActorAttr;
      continue;
    }

    // Best-effort fallback for common actor/resource/context field checks.
    if (field.startsWith('actor.') && (op === 'eq' || op === 'equals')) {
      const key = field.slice('actor.'.length);
      const requireActorAttr = (mapped.require_actor_attr ?? {}) as Record<string, unknown>;
      requireActorAttr[key] = value;
      mapped.require_actor_attr = requireActorAttr;
      continue;
    }

    if (field.startsWith('resource.') && (op === 'eq' || op === 'equals')) {
      const key = field.slice('resource.'.length);
      const requireResourceAttr = (mapped.require_resource_attr ?? {}) as Record<string, unknown>;
      requireResourceAttr[key] = value;
      mapped.require_resource_attr = requireResourceAttr;
      continue;
    }

    legacyUnmapped.push(entry);
  }

  if (legacyUnmapped.length > 0) {
    mapped.custom = { legacy_conditions: legacyUnmapped };
  }

  return mapped as NonNullable<PolicyArtifact['conditions']>;
}

function normalizeObligations(raw: unknown): PolicyArtifact['obligations'] {
  if (!Array.isArray(raw)) return undefined;

  const obligations = raw
    .map((item) => {
      if (typeof item === 'string') {
        if (!isObligationType(item)) return null;
        return { type: item };
      }
      if (!item || typeof item !== 'object') {
        return null;
      }
      const obligation = item as Record<string, unknown>;
      if (typeof obligation.type !== 'string' || obligation.type.length === 0) {
        return null;
      }
      if (!isObligationType(obligation.type)) {
        return null;
      }
      return {
        type: obligation.type,
        params:
          obligation.params && typeof obligation.params === 'object'
            ? (obligation.params as Record<string, unknown>)
            : undefined,
      };
    })
    .filter(
      (item): item is NonNullable<PolicyArtifact['obligations']>[number] => item !== null
    );

  return obligations.length > 0 ? obligations : undefined;
}

function normalizeApproval(raw: unknown): PolicyArtifact['approval'] {
  if (!raw || typeof raw !== 'object') return undefined;
  const approval = raw as Record<string, unknown>;

  const normalized: NonNullable<PolicyArtifact['approval']> = {
    approver_role:
      typeof approval.approver_role === 'string'
        ? approval.approver_role
        : Array.isArray(approval.approver_roles) && typeof approval.approver_roles[0] === 'string'
          ? approval.approver_roles[0]
          : undefined,
    require_count:
      typeof approval.require_count === 'number'
        ? approval.require_count
        : approval.required === true
          ? 1
          : undefined,
    require_ticket:
      typeof approval.require_ticket === 'boolean'
        ? approval.require_ticket
        : undefined,
    require_justification:
      typeof approval.require_justification === 'boolean'
        ? approval.require_justification
        : undefined,
    timeout_hours:
      typeof approval.timeout_hours === 'number'
        ? approval.timeout_hours
        : undefined,
  };

  if (
    normalized.approver_role === undefined &&
    normalized.require_count === undefined &&
    normalized.require_ticket === undefined &&
    normalized.require_justification === undefined &&
    normalized.timeout_hours === undefined
  ) {
    return undefined;
  }

  return normalized;
}

function isValidDecision(value: unknown): value is PolicyArtifact['decision'] {
  return value === 'ALLOW' || value === 'DENY' || value === 'QUARANTINE';
}

function normalizeActorType(value: string): PolicyArtifact['scope']['actor_type'] {
  const normalized = String(value).toUpperCase();
  if (
    normalized === '*' ||
    normalized === 'HUMAN' ||
    normalized === 'SERVICE' ||
    normalized === 'AI_AGENT' ||
    normalized === 'JOB' ||
    normalized === 'SYSTEM'
  ) {
    return normalized as PolicyArtifact['scope']['actor_type'];
  }

  return '*';
}

function isObligationType(
  value: string
): value is NonNullable<PolicyArtifact['obligations']>[number]['type'] {
  return (
    value === 'REDACT_FIELDS' ||
    value === 'MASK_PII' ||
    value === 'WATERMARK_OUTPUT' ||
    value === 'REQUIRE_APPROVAL' ||
    value === 'RATE_LIMIT' ||
    value === 'LOG_LEVEL' ||
    value === 'ENCRYPT_TRANSIT' ||
    value === 'DUAL_CONTROL' ||
    value === 'TIME_LIMIT' ||
    value === 'NOTIFY' ||
    value === 'AUDIT_LOG' ||
    value === 'DATA_FORMAT' ||
    value === 'DATA_MASK' ||
    value === 'NOTIFY_DPO' ||
    value === 'NOTIFY_SERVICE_PROVIDERS' ||
    value === 'PROVIDE_EXPLANATION' ||
    value === 'RESPOND_WITHIN' ||
    value === 'STOP_PROCESSING'
  );
}

function normalizeEnvironment(value: unknown): string {
  if (value === 'production') return 'prod';
  if (value === 'staging') return 'stage';
  return String(value);
}

// =============================================================================
// HASHING
// =============================================================================

/**
 * Runtime-compatible policy hash used by policy engine decisions.
 */
export function computeRuntimePolicyHash(policy: PolicyArtifact): string {
  return hashCanonical({
    id: policy.policy_id,
    version: policy.version,
    decision: policy.decision,
    scope: policy.scope,
  });
}

/**
 * Deterministic hash for an entire policy artifact pack.
 */
export function computePolicyArtifactPackHash(policies: PolicyArtifact[]): string {
  const sorted = [...policies].sort((a, b) => a.policy_id.localeCompare(b.policy_id));
  return hashCanonical({
    policies: sorted.map((policy) => ({
      id: policy.policy_id,
      version: policy.version,
      priority: policy.priority ?? 100,
      decision: policy.decision,
      hash: computeRuntimePolicyHash(policy),
    })),
  });
}

// =============================================================================
// HELPERS
// =============================================================================

export function normalizeHash(hash: string): string {
  return hash.startsWith('sha256:') ? hash : `sha256:${hash}`;
}

export function stripHashPrefix(hash: string): string {
  return hash.startsWith('sha256:') ? hash.slice('sha256:'.length) : hash;
}

/**
 * Basic pack stats used by CLI reporting.
 */
export function getPolicyArtifactPackStats(pack: PolicyArtifactPack): PolicyArtifactPackStats {
  const stats: PolicyArtifactPackStats = {
    totalPolicies: pack.policies.length,
    byDecision: { ALLOW: 0, DENY: 0, QUARANTINE: 0 },
    byPriority: { min: 0, max: 0, avg: 0 },
    hasObligations: 0,
    hasApproval: 0,
    regulations: [],
    controls: [],
  };

  if (pack.policies.length === 0) return stats;

  const regulations = new Set<string>();
  const controls = new Set<string>();
  const priorities: number[] = [];

  for (const policy of pack.policies) {
    stats.byDecision[policy.decision] = (stats.byDecision[policy.decision] ?? 0) + 1;
    priorities.push(policy.priority ?? 100);

    if (policy.obligations && policy.obligations.length > 0) {
      stats.hasObligations++;
    }
    if (policy.approval) {
      stats.hasApproval++;
    }

    for (const reg of policy.regulations ?? []) {
      regulations.add(reg);
    }
    for (const control of policy.controls ?? []) {
      controls.add(control);
    }
  }

  stats.byPriority = {
    min: Math.min(...priorities),
    max: Math.max(...priorities),
    avg: priorities.reduce((sum, p) => sum + p, 0) / priorities.length,
  };
  stats.regulations = Array.from(regulations);
  stats.controls = Array.from(controls);

  return stats;
}
