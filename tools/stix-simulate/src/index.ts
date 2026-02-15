/**
 * STIX Simulation Engine
 * Simulate policy impact on historical evidence
 *
 * @module @stix/simulate
 */

// Types
export * from './types.js';

// Evidence loading
export {
  loadEvidenceBundles,
  getEvidenceStats,
} from './loadEvidence.js';

// Policy loading
export {
  loadPolicyPack,
  getPolicyStats,
  type PolicyPack,
} from './loadPolicies.js';

// Evaluation
export {
  SimulationPolicyEngine,
  simulateDecision,
  simulateBatch,
  type EvaluationResult,
} from './evaluate.js';

// Diff calculation
export {
  calculateDiff,
  calculateBatchDiffs,
  filterChangedResults,
  filterByRiskLevel,
  filterByChangeType,
  getDiffStats,
} from './diff.js';

// Report generation
export {
  buildReport,
  formatReportAsJson,
  formatReportAsMarkdown,
  formatReportAsTable,
} from './report.js';
