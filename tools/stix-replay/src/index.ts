/**
 * STIX Replay Tool
 * Replay recorded decisions against policies for verification
 *
 * @module @stix/replay
 */

// Types
export * from './types.js';

// Evidence extraction
export {
  loadBundles,
  extractFromBundle,
  extractMultiple,
  validateForReplay,
} from './extract.js';

// Policy loading
export {
  loadPolicyPack,
  loadPolicyArchive,
  loadPackByHash,
  findPolicyByHash,
  findPolicyById,
  packHashMatches,
  computePolicyHash,
  computePackHash,
  type LoadedPolicyPack,
  type PolicyPackManifest,
  type PolicyArchive,
} from './policyLoader.js';

// Replay engine
export {
  ReplayEngine,
  type EvaluationInput,
  type EvaluationOutput,
  type MatchedPolicy,
} from './engine.js';

// Core replay
export {
  replayDecision,
  replayBatch,
  filterByStatus,
  getDriftedResults,
  getMatchedResults,
  getErroredResults,
  filterByDecisionChange,
  calculateStats,
  type ReplayCompareOptions,
  type ReplayStats,
} from './replay.js';

// Verification helpers
export {
  verifyBundlesForReplay,
  type ReplayVerificationOptions,
  type ReplayVerificationResult,
} from './verify.js';

// Report generation
export {
  buildReport,
  formatReportAsJson,
  formatReportAsMarkdown,
  formatReportAsTable,
  formatDetailedDiff,
  formatBatchDiffSummary,
} from './report.js';
