/**
 * STIX Policy Store
 * Storage backends for policy management
 */

import {
  type PolicyArtifact,
  type Logger,
  validatePolicyArtifact,
  PolicyNotFoundError,
  PolicyValidationError,
} from '@stix/shared';
import type { Config } from '../config/index.js';
import * as fs from 'node:fs';
import * as path from 'node:path';
import * as yaml from 'yaml';
import { Pool } from 'pg';

// =============================================================================
// TYPES
// =============================================================================

export interface ListPoliciesOptions {
  active?: boolean;
  tags?: string[];
  limit?: number;
  offset?: number;
}

export interface PolicyStore {
  getPolicy(policyId: string): Promise<PolicyArtifact | null>;
  listPolicies(options?: ListPoliciesOptions): Promise<PolicyArtifact[]>;
  upsertPolicy(policy: PolicyArtifact): Promise<void>;
  deletePolicy(policyId: string): Promise<void>;
  reload(): Promise<void>;
  health(): Promise<boolean>;
}

// =============================================================================
// IN-MEMORY POLICY STORE
// =============================================================================

export class InMemoryPolicyStore implements PolicyStore {
  private policies: Map<string, PolicyArtifact> = new Map();
  protected readonly logger: Logger;
  private readonly policyDirectory?: string;

  constructor(logger: Logger, policyDirectory?: string) {
    this.logger = logger.child({ component: 'InMemoryPolicyStore' });
    this.policyDirectory = policyDirectory;
  }

  async initialize(): Promise<void> {
    if (this.policyDirectory) {
      await this.loadFromDirectory(this.policyDirectory);
    }
    this.logger.info('Policy store initialized', { policy_count: this.policies.size });
  }

  async getPolicy(policyId: string): Promise<PolicyArtifact | null> {
    return this.policies.get(policyId) ?? null;
  }

  async listPolicies(options?: ListPoliciesOptions): Promise<PolicyArtifact[]> {
    let policies = Array.from(this.policies.values());

    // Filter by active status
    if (options?.active !== undefined) {
      policies = policies.filter(p => (p.active ?? true) === options.active);
    }

    // Filter by tags
    if (options?.tags && options.tags.length > 0) {
      policies = policies.filter(p => {
        const policyTags = p.tags ?? [];
        return options.tags!.some(t => policyTags.includes(t));
      });
    }

    // Sort by priority (lower = higher priority)
    policies.sort((a, b) => (a.priority ?? 100) - (b.priority ?? 100));

    // Apply pagination
    const offset = options?.offset ?? 0;
    const limit = options?.limit ?? 1000;
    policies = policies.slice(offset, offset + limit);

    return policies;
  }

  async upsertPolicy(policy: PolicyArtifact): Promise<void> {
    // Validate policy
    const validated = validatePolicyArtifact(policy);

    this.policies.set(validated.policy_id, validated);
    this.logger.debug('Policy upserted', { policy_id: validated.policy_id });
  }

  async deletePolicy(policyId: string): Promise<void> {
    if (!this.policies.has(policyId)) {
      throw new PolicyNotFoundError(policyId);
    }
    this.policies.delete(policyId);
    this.logger.debug('Policy deleted', { policy_id: policyId });
  }

  async reload(): Promise<void> {
    if (this.policyDirectory) {
      this.policies.clear();
      await this.loadFromDirectory(this.policyDirectory);
      this.logger.info('Policies reloaded', { policy_count: this.policies.size });
    }
  }

  async health(): Promise<boolean> {
    return true;
  }

  /**
   * Load policies from a directory of YAML files
   */
  async loadFromDirectory(directory: string): Promise<number> {
    if (!fs.existsSync(directory)) {
      this.logger.warn('Policy directory does not exist', { directory });
      return 0;
    }

    let loaded = 0;
    const files = this.findYamlFiles(directory);

    for (const file of files) {
      try {
        const content = fs.readFileSync(file, 'utf-8');
        const parsed = yaml.parse(content);

        // Handle both single policy and array of policies
        const policies = Array.isArray(parsed) ? parsed : [parsed];

        for (const policy of policies) {
          // Handle policy pack format (has 'policies' array)
          if (policy.policies && Array.isArray(policy.policies)) {
            for (const p of policy.policies) {
              await this.loadPolicy(p, file);
              loaded++;
            }
          } else {
            await this.loadPolicy(policy, file);
            loaded++;
          }
        }

        this.logger.debug('Loaded policy file', { file, count: policies.length });
      } catch (error) {
        this.logger.error('Failed to load policy file', {
          file,
          error: (error as Error).message,
        });
      }
    }

    return loaded;
  }

  /**
   * Load a single policy with validation
   */
  private async loadPolicy(policy: unknown, sourceFile: string): Promise<void> {
    try {
      const validated = validatePolicyArtifact(policy as PolicyArtifact);
      this.policies.set(validated.policy_id, validated);
      this.logger.debug('Policy loaded', {
        policy_id: validated.policy_id,
        source_file: sourceFile,
      });
    } catch (error) {
      this.logger.warn('Skipping invalid policy', {
        file: sourceFile,
        error: (error as Error).message,
      });
    }
  }

  /**
   * Recursively find all YAML files in directory
   */
  private findYamlFiles(directory: string): string[] {
    const files: string[] = [];

    const entries = fs.readdirSync(directory, { withFileTypes: true });

    for (const entry of entries) {
      const fullPath = path.join(directory, entry.name);

      if (entry.isDirectory()) {
        files.push(...this.findYamlFiles(fullPath));
      } else if (entry.isFile() && /\.ya?ml$/i.test(entry.name)) {
        files.push(fullPath);
      }
    }

    return files;
  }
}

// =============================================================================
// FILE-WATCHING POLICY STORE
// =============================================================================

export class FileWatchingPolicyStore extends InMemoryPolicyStore {
  private watcher: fs.FSWatcher | null = null;
  private readonly watchDirectory: string;
  private debounceTimer: ReturnType<typeof setTimeout> | null = null;

  constructor(logger: Logger, policyDirectory: string) {
    super(logger, policyDirectory);
    this.watchDirectory = policyDirectory;
  }

  async initialize(): Promise<void> {
    await super.initialize();
    this.startWatching();
  }

  /**
   * Start watching for file changes
   */
  private startWatching(): void {
    if (!fs.existsSync(this.watchDirectory)) return;

    try {
      this.watcher = fs.watch(this.watchDirectory, { recursive: true }, (eventType, filename) => {
        if (filename && /\.ya?ml$/i.test(filename)) {
          this.scheduleReload();
        }
      });

      this.logger.info('File watching enabled', { directory: this.watchDirectory });
    } catch (error) {
      this.logger.warn('Failed to enable file watching', {
        error: (error as Error).message,
      });
    }
  }

  /**
   * Schedule a reload with debouncing
   */
  private scheduleReload(): void {
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
    }

    this.debounceTimer = setTimeout(async () => {
      this.logger.info('Policy file change detected, reloading...');
      await this.reload();
    }, 1000);
  }

  /**
   * Stop watching
   */
  stopWatching(): void {
    if (this.watcher) {
      this.watcher.close();
      this.watcher = null;
    }
    if (this.debounceTimer) {
      clearTimeout(this.debounceTimer);
      this.debounceTimer = null;
    }
  }
}

// =============================================================================
// POSTGRES POLICY STORE
// =============================================================================

export class PostgresPolicyStore implements PolicyStore {
  private readonly logger: Logger;
  private readonly pool: Pool;
  private readonly policyDirectory?: string;

  constructor(config: Config, logger: Logger, policyDirectory?: string) {
    this.logger = logger.child({ component: 'PostgresPolicyStore' });
    this.policyDirectory = policyDirectory;
    this.pool = new Pool({
      connectionString: config.storage.postgresUrl,
      max: 20,
      min: 2,
      idleTimeoutMillis: 30000,
      connectionTimeoutMillis: 5000,
    });
  }

  async initialize(): Promise<void> {
    await this.pool.query(`
      CREATE TABLE IF NOT EXISTS stix_policies (
        policy_id TEXT PRIMARY KEY,
        priority INTEGER NOT NULL DEFAULT 100,
        active BOOLEAN NOT NULL DEFAULT true,
        tags TEXT[] NOT NULL DEFAULT '{}',
        artifact JSONB NOT NULL,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
      );
      CREATE INDEX IF NOT EXISTS idx_stix_policies_active ON stix_policies(active);
      CREATE INDEX IF NOT EXISTS idx_stix_policies_priority ON stix_policies(priority);
      CREATE INDEX IF NOT EXISTS idx_stix_policies_tags ON stix_policies USING GIN(tags);
    `);

    // Bootstrap from policy directory only when DB is empty.
    if (this.policyDirectory) {
      const count = await this.pool.query<{ count: string }>('SELECT COUNT(*)::text AS count FROM stix_policies');
      if (Number.parseInt(count.rows[0]?.count ?? '0', 10) === 0) {
        const bootstrapStore = new InMemoryPolicyStore(this.logger, this.policyDirectory);
        await bootstrapStore.initialize();
        const bootPolicies = await bootstrapStore.listPolicies({ limit: 100000 });
        for (const policy of bootPolicies) {
          await this.upsertPolicy(policy);
        }
        this.logger.info('Bootstrapped postgres policy store from directory', {
          policy_count: bootPolicies.length,
          directory: this.policyDirectory,
        });
      }
    }
  }

  async getPolicy(policyId: string): Promise<PolicyArtifact | null> {
    const result = await this.pool.query<{ artifact: PolicyArtifact }>(
      'SELECT artifact FROM stix_policies WHERE policy_id = $1',
      [policyId]
    );
    return result.rows[0]?.artifact ?? null;
  }

  async listPolicies(options?: ListPoliciesOptions): Promise<PolicyArtifact[]> {
    const conditions: string[] = [];
    const params: unknown[] = [];
    let idx = 1;

    if (options?.active !== undefined) {
      conditions.push(`active = $${idx++}`);
      params.push(options.active);
    }

    if (options?.tags && options.tags.length > 0) {
      conditions.push(`tags && $${idx++}::text[]`);
      params.push(options.tags);
    }

    const where = conditions.length > 0 ? `WHERE ${conditions.join(' AND ')}` : '';
    const offset = options?.offset ?? 0;
    const limit = options?.limit ?? 1000;

    const result = await this.pool.query<{ artifact: PolicyArtifact }>(
      `SELECT artifact
       FROM stix_policies
       ${where}
       ORDER BY priority ASC, policy_id ASC
       OFFSET $${idx++}
       LIMIT $${idx}`,
      [...params, offset, limit]
    );

    return result.rows.map(r => r.artifact);
  }

  async upsertPolicy(policy: PolicyArtifact): Promise<void> {
    const validated = validatePolicyArtifact(policy);
    const active = validated.active ?? true;
    const priority = validated.priority ?? 100;
    const tags = validated.tags ?? [];

    await this.pool.query(
      `INSERT INTO stix_policies (policy_id, priority, active, tags, artifact, updated_at)
       VALUES ($1, $2, $3, $4::text[], $5::jsonb, NOW())
       ON CONFLICT (policy_id) DO UPDATE SET
         priority = EXCLUDED.priority,
         active = EXCLUDED.active,
         tags = EXCLUDED.tags,
         artifact = EXCLUDED.artifact,
         updated_at = NOW()`,
      [validated.policy_id, priority, active, tags, JSON.stringify(validated)]
    );
  }

  async deletePolicy(policyId: string): Promise<void> {
    const result = await this.pool.query('DELETE FROM stix_policies WHERE policy_id = $1', [policyId]);
    if ((result.rowCount ?? 0) === 0) {
      throw new PolicyNotFoundError(policyId);
    }
  }

  async reload(): Promise<void> {
    if (!this.policyDirectory) {
      return;
    }

    const bootstrapStore = new InMemoryPolicyStore(this.logger, this.policyDirectory);
    await bootstrapStore.initialize();
    const policies = await bootstrapStore.listPolicies({ limit: 100000 });

    for (const policy of policies) {
      await this.upsertPolicy(policy);
    }

    this.logger.info('Reloaded policies into postgres store', {
      policy_count: policies.length,
      directory: this.policyDirectory,
    });
  }

  async health(): Promise<boolean> {
    try {
      await this.pool.query('SELECT 1');
      return true;
    } catch {
      return false;
    }
  }
}

// =============================================================================
// FACTORY
// =============================================================================

export async function createPolicyStore(
  config: Config,
  logger: Logger
): Promise<PolicyStore> {
  const storeType = config.storage?.type ?? 'memory';
  const policyDirectory = resolvePolicyDirectory(
    config.storage?.policyDirectory ?? './policies/examples'
  );

  let store: PolicyStore;

  switch (storeType) {
    case 'file':
    case 'file-watch':
      store = new FileWatchingPolicyStore(logger, policyDirectory);
      await (store as FileWatchingPolicyStore).initialize();
      break;

    case 'memory':
      store = new InMemoryPolicyStore(logger, policyDirectory);
      await (store as InMemoryPolicyStore).initialize();
      break;

    case 'postgres':
      if (!config.storage.postgresUrl) {
        throw new Error('STORAGE_TYPE=postgres requires POSTGRES_URL for stix-policy.');
      }
      store = new PostgresPolicyStore(config, logger, policyDirectory);
      await (store as PostgresPolicyStore).initialize();
      break;

    default:
      throw new Error(`Unsupported policy storage type: ${storeType}`);
  }

  return store;
}

function resolvePolicyDirectory(directory: string): string {
  if (path.isAbsolute(directory)) return directory;

  const cwdResolved = path.resolve(process.cwd(), directory);
  if (fs.existsSync(cwdResolved)) return cwdResolved;

  // Common when running from services/policy: climb to repo root
  const repoResolved = path.resolve(process.cwd(), '..', '..', directory);
  if (fs.existsSync(repoResolved)) return repoResolved;

  return cwdResolved;
}
