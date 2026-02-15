/**
 * STIX Replay - Policy Loader
 * Delegates to shared deterministic PolicyArtifact pack loader
 */

import * as fs from 'node:fs';
import * as path from 'node:path';
import * as yaml from 'yaml';
import {
  loadPolicyArtifactPack,
  computeRuntimePolicyHash,
  computePolicyArtifactPackHash,
  normalizeHash as normalizeSharedHash,
  stripHashPrefix,
  type PolicyArtifactPack,
  type PolicyArtifact,
} from '@stix/shared';

// =============================================================================
// TYPES
// =============================================================================

export interface PolicyPackManifest {
  id?: string;
  version?: string;
  hash?: string;
  policies?: PolicyManifestEntry[];
}

export interface PolicyManifestEntry {
  id?: string;
  file: string;
  hash?: string;
}

export type LoadedPolicyPack = PolicyArtifactPack;

// =============================================================================
// POLICY LOADING
// =============================================================================

/**
 * Load a policy pack from a directory or file
 */
export async function loadPolicyPack(policyPath: string): Promise<LoadedPolicyPack> {
  return loadPolicyArtifactPack(policyPath);
}

// =============================================================================
// POLICY LOOKUP
// =============================================================================

/**
 * Find a policy by hash
 */
export function findPolicyByHash(
  pack: LoadedPolicyPack,
  hash: string
): PolicyArtifact | undefined {
  const normalized = normalizeHash(hash);
  return pack.hashIndex.get(normalized) || pack.hashIndex.get(stripHashPrefix(normalized));
}

/**
 * Find a policy by ID
 */
export function findPolicyById(
  pack: LoadedPolicyPack,
  id: string
): PolicyArtifact | undefined {
  return pack.policyIndex.get(id);
}

/**
 * Check if pack hash matches
 */
export function packHashMatches(pack: LoadedPolicyPack, expectedHash: string): boolean {
  const expected = normalizeHash(expectedHash);
  const actual = normalizeHash(pack.hash);
  const expectedRaw = stripHashPrefix(expected);
  const actualRaw = stripHashPrefix(actual);

  return actual === expected || actualRaw.startsWith(expectedRaw) || expectedRaw.startsWith(actualRaw);
}

// =============================================================================
// HASHING
// =============================================================================

/**
 * Compute runtime-compatible hash for a single policy
 */
export function computePolicyHash(policy: PolicyArtifact): string {
  return computeRuntimePolicyHash(policy);
}

/**
 * Compute deterministic hash for entire policy pack
 */
export function computePackHash(policies: PolicyArtifact[]): string {
  return computePolicyArtifactPackHash(policies);
}

// =============================================================================
// VERSIONED POLICY STORAGE
// =============================================================================

export interface PolicyArchive {
  baseDir: string;
  versionIndex: Map<string, string>; // hash -> version dir
}

/**
 * Load a policy archive (multiple versions)
 */
export async function loadPolicyArchive(archiveDir: string): Promise<PolicyArchive> {
  const versionIndex = new Map<string, string>();
  const entries = fs.readdirSync(archiveDir, { withFileTypes: true });

  for (const entry of entries) {
    if (!entry.isDirectory()) continue;

    const versionDir = path.join(archiveDir, entry.name);
    const manifest = loadManifest(versionDir);

    if (manifest?.hash) {
      const normalized = normalizeHash(manifest.hash);
      versionIndex.set(normalized, versionDir);
      versionIndex.set(stripHashPrefix(normalized), versionDir);
      continue;
    }

    // Fallback: compute hash from actual pack contents.
    try {
      const pack = await loadPolicyPack(versionDir);
      versionIndex.set(pack.hash, versionDir);
      versionIndex.set(stripHashPrefix(pack.hash), versionDir);
    } catch {
      // Ignore unreadable pack directories.
    }
  }

  return {
    baseDir: archiveDir,
    versionIndex,
  };
}

/**
 * Load policy pack by hash from archive
 */
export async function loadPackByHash(
  archive: PolicyArchive,
  hash: string
): Promise<LoadedPolicyPack | null> {
  const normalized = normalizeHash(hash);
  const raw = stripHashPrefix(normalized);

  let versionDir = archive.versionIndex.get(normalized) || archive.versionIndex.get(raw);

  if (!versionDir) {
    for (const [storedHash, dir] of archive.versionIndex) {
      const storedRaw = stripHashPrefix(storedHash);
      if (storedRaw.startsWith(raw) || raw.startsWith(storedRaw)) {
        versionDir = dir;
        break;
      }
    }
  }

  if (!versionDir) {
    return null;
  }

  return loadPolicyPack(versionDir);
}

function loadManifest(versionDir: string): PolicyPackManifest | null {
  const yamlPath = path.join(versionDir, 'manifest.yaml');
  const ymlPath = path.join(versionDir, 'manifest.yml');
  const jsonPath = path.join(versionDir, 'manifest.json');

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

function normalizeHash(hash: string): string {
  return normalizeSharedHash(hash);
}
