/**
 * STIX Simulation - Policy Loader
 * Delegates to shared deterministic PolicyArtifact pack loader
 */

import {
  loadPolicyArtifactPack,
  getPolicyArtifactPackStats,
  type PolicyArtifactPack,
  type PolicyArtifactPackStats,
} from '@stix/shared';

// =============================================================================
// POLICY LOADING
// =============================================================================

/**
 * Loaded policy pack for simulation
 */
export type PolicyPack = PolicyArtifactPack;

/**
 * Load a policy pack from a directory or file
 */
export async function loadPolicyPack(policyPath: string): Promise<PolicyPack> {
  return loadPolicyArtifactPack(policyPath);
}

/**
 * Get policy pack statistics
 */
export function getPolicyStats(pack: PolicyPack): PolicyArtifactPackStats {
  return getPolicyArtifactPackStats(pack);
}
