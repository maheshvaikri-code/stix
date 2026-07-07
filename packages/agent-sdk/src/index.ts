/**
 * STIX Agent SDK
 * Enterprise policy enforcement for AI agents
 *
 * @packageDocumentation
 *
 * @example Basic Usage
 * ```typescript
 * import { StixClient, wrapTool } from '@stix/agent-sdk';
 *
 * // Initialize client
 * const stix = new StixClient({
 *   enforcerUrl: 'https://stix-enforcer.internal:3001',
 *   apiKey: process.env.STIX_API_KEY,
 *   defaultActor: {
 *     id: 'agent-001',
 *     type: 'AI_AGENT',
 *     role: 'data-processor'
 *   },
 *   defaultContext: {
 *     env: 'prod',
 *     run_id: crypto.randomUUID()
 *   }
 * });
 *
 * // Wrap a tool
 * const sendEmail = wrapTool(stix, {
 *   name: 'send_email',
 *   action: 'send_email',
 *   resourceType: 'email',
 *   riskTier: 'MEDIUM',
 *   execute: async (args) => {
 *     await mailer.send(args.to, args.subject, args.body);
 *     return { sent: true };
 *   }
 * });
 *
 * // Execute with authorization
 * const result = await sendEmail.executeOrThrow({
 *   to: 'user@example.com',
 *   subject: 'Hello',
 *   body: 'World'
 * });
 * ```
 *
 * @example Direct Authorization
 * ```typescript
 * const result = await stix.authorize({
 *   action: 'read_database',
 *   resource: { type: 'database', id: 'customers' },
 *   context: { purpose: 'analytics' }
 * });
 *
 * if (result.allowed) {
 *   const data = await db.query('SELECT * FROM customers');
 *   await stix.recordOutcome(result.traceId, 'SUCCESS');
 * } else {
 *   console.log('Denied:', result.reasonCode);
 * }
 * ```
 *
 * @example Wait for Approval
 * ```typescript
 * const result = await stix.authorize({
 *   action: 'delete_account',
 *   resource: { type: 'user_account', id: 'user-123' },
 *   waitForApproval: true,
 *   approvalTimeout: 300000 // 5 minutes
 * });
 *
 * if (result.allowed) {
 *   // Approval was granted
 *   await deleteAccount('user-123');
 * }
 * ```
 */

// Core client
export { StixClient, createClientFromEnv } from './client';

// Tool wrappers
export {
  wrapTool,
  createToolRegistry,
  ToolRegistry,
  StixAuthorized,
  createFileTool,
  createDatabaseTool,
  createHttpTool,
  createEmailTool,
} from './tools';

// Types
export type {
  // Configuration
  StixClientConfig,
  Logger,
  TelemetryHooks,

  // Authorization
  AuthorizeParams,
  AuthorizationResult,

  // Approvals
  ApprovalStatus,
  ApprovalRequest,
  ApprovalRecord,
  ApprovalPollOptions,

  // Tools
  ToolDefinition,
  WrappedTool,
  WrappedToolResult,

  // Re-exported from @stix/shared
  Actor,
  ActorType,
  AuthorizeRequest,
  AuthorizeResponse,
  Context,
  DecisionKind,
  Environment,
  FailMode,
  Obligation,
  OutcomeStatus,
  Resource,
  RiskTier,
  ToolCall,
} from './types';

// Errors
export {
  StixError,
  AuthorizationDeniedError,
  ApprovalTimeoutError,
  ServiceUnavailableError,
  FailModeTriggeredError,
} from './types';

// Integrations - GitLab
export {
  GitLabGuardian,
  createGitLabGuardianFromEnv,
  normalizeGitLabEvent,
  normalizeMergeRequestEvent,
  normalizePipelineEvent,
  normalizeIssueEvent,
  scanDiff,
  formatDecisionComment,
  mapDecisionToGitLabActions,
} from './integrations/gitlab';

export type {
  GitLabEvent,
  GitLabMergeRequestEvent,
  GitLabPipelineEvent,
  GitLabIssueEvent,
  GitLabNoteEvent,
  GitLabDiffEntry,
  GitLabUser,
  GitLabProject,
  GitLabGuardianConfig,
  GitLabAuthorizeInput,
  GitLabResponse,
  GitLabAction,
  DiffScanResult,
  DiffFinding,
} from './integrations/gitlab';

// Reasoning - Claude-powered compliance analysis
export {
  ComplianceAnalyzer,
  createComplianceAnalyzerFromEnv,
  formatAnalysisAsComment,
} from './reasoning/compliance-analyzer';

export type {
  ComplianceAnalysis,
  ComplianceViolation,
  ApprovalSummary,
  ComplianceAnalyzerConfig,
} from './reasoning/compliance-analyzer';
