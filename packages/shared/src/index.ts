/**
 * STIX Shared Package
 * Enterprise-grade shared utilities for Shield, Trust & Integrity eXecution
 * 
 * @module @stix/shared
 * @version 0.1.9
 */

// =============================================================================
// TYPE EXPORTS
// =============================================================================

export type {
  // Enums & Literals
  DecisionKind,
  ActorType,
  ActorTypeFilter,
  Environment,
  RiskTier,
  SchemaVersion,
  ObligationType,
  OutcomeStatus,
  FailMode,
  
  // Core interfaces
  Actor,
  Resource,
  DetectionSignals,
  Context,
  ToolCall,
  
  // Request/Response
  AuthorizeRequest,
  AuthorizeResponse,
  Obligation,
  ApprovalInfo,
  PolicyRef,
  OutcomeRequest,
  ActionMeta,
  
  // Evidence
  EvidenceEvent,
  IntegrityBlock,
  OutcomeInfo,
  ObligationsApplied,
  
  // Policy
  PolicyArtifact,
  PolicyScope,
  PolicyConditions,
  PolicyApproval,
  PolicyDecision,
  
  // Token
  ProofTokenHeader,
  ProofTokenClaims,
  
  // API
  ApiResponse,
  HealthResponse,
  PaginationParams,
  PaginatedResponse,
} from './types/index.js';

// =============================================================================
// CONSTANTS EXPORTS
// =============================================================================

export {
  // Service configuration
  SERVICE_PORTS,
  SERVICE_NAMES,
  SERVICE_URLS,
  
  // API versioning
  API_VERSION,
  API_PATHS,
  
  // Security
  TOKEN_CONFIG,
  HEADERS,
  
  // Rate limiting
  RATE_LIMITS,
  
  // Timeouts
  TIMEOUTS,
  
  // Retry
  RETRY_CONFIG,
  
  // Pagination
  PAGINATION,
  
  // Evidence
  EVIDENCE_CONFIG,
  
  // Approvals
  APPROVAL_CONFIG,
  
  // Policy
  POLICY_CONFIG,
  
  // Compliance
  CONTROL_FRAMEWORKS,
  CONTROL_MAPPINGS,
  
  // Error codes
  ERROR_CODES,
  
  // Reason codes
  REASON_CODES,
  
  // Risk classification
  RISK_THRESHOLDS,
  DEFAULT_TOOL_RISK_TIERS,
  
  // Environment
  ENVIRONMENT_CONFIG,
  
  // Metrics
  METRICS,
  
  // Logging
  LOG_LEVELS,
  LOG_LEVEL_PRIORITY,
} from './constants/index.js';

// =============================================================================
// UTILS EXPORTS
// =============================================================================

export {
  // ID generation
  generateTraceId,
  generateEventId,
  generateRequestId,
  generateApprovalTicketId,
  
  // Canonicalization
  canonicalize,
  sortObjectKeys,
  
  // Hashing
  sha256,
  sha256Raw,
  hashCanonical,
  ZERO_HASH,
  
  // Timestamps
  isoTimestamp,
  unixTimestamp,
  parseIsoTimestamp,
  isExpired,
  addSeconds,
  
  // Base64url
  toBase64Url,
  fromBase64Url,
  stringToBase64Url,
  base64UrlToString,
  
  // Hex
  hexToBytes,
  bytesToHex,
  
  // Validation
  isValidHash,
  isValidTraceId,
  isValidEventId,
  isValidUuid,
  
  // Object utilities
  deepClone,
  deepMerge,
  pick,
  omit,
  
  // String utilities
  truncate,
  mask,
  maskSsn,
  maskEmail,
  
  // Async utilities
  sleep,
  retry,
  withTimeout,
  
  // Environment
  requireEnv,
  getEnv,
  getEnvNumber,
  getEnvBool,
  isProduction,
  isDevelopment,
} from './utils/index.js';

// =============================================================================
// ERROR EXPORTS
// =============================================================================

export {
  // Base error
  StixError,
  
  // Authorization errors
  AuthorizationDeniedError,
  AuthorizationQuarantinedError,
  
  // Authentication errors
  AuthenticationRequiredError,
  InvalidTokenError,
  TokenExpiredError,
  MissingStixTokenError,
  
  // Policy errors
  PolicyNotFoundError,
  PolicyValidationError,
  PolicyConflictError,
  
  // Evidence errors
  EvidenceNotFoundError,
  EvidenceIntegrityError,
  EvidenceWriteError,
  
  // Approval errors
  ApprovalNotFoundError,
  ApprovalExpiredError,
  ApprovalAlreadyProcessedError,
  InsufficientApprovalError,
  
  // Validation errors
  ValidationError,
  InvalidRequestError,
  
  // Service errors
  ServiceUnavailableError,
  ServiceTimeoutError,
  InternalError,
  ConfigurationError,
  
  // Rate limiting
  RateLimitExceededError,
  
  // Crypto errors
  SignatureVerificationError,
  HashChainError,
  
  // Utilities
  isStixError,
  toStixError,
  createErrorResponse,
} from './errors/index.js';

// =============================================================================
// VALIDATOR EXPORTS
// =============================================================================

export {
  // Base schemas
  UuidSchema,
  TraceIdSchema,
  EventIdSchema,
  ApprovalTicketIdSchema,
  HashSchema,
  TimestampSchema,
  SemverSchema,
  
  // Enum schemas
  DecisionKindSchema,
  ActorTypeSchema,
  ActorTypeFilterSchema,
  EnvironmentSchema,
  RiskTierSchema,
  SchemaVersionSchema,
  ObligationTypeSchema,
  OutcomeStatusSchema,
  FailModeSchema,
  
  // Core object schemas
  ActorSchema,
  ResourceSchema,
  DetectionSignalsSchema,
  ContextSchema,
  ToolCallSchema,
  ObligationSchema,
  ApprovalInfoSchema,
  PolicyRefSchema,
  
  // Request schemas
  AuthorizeRequestSchema,
  OutcomeRequestSchema,
  
  // Response schemas
  AuthorizeResponseSchema,
  
  // Evidence schemas
  IntegrityBlockSchema,
  OutcomeInfoSchema,
  ObligationsAppliedSchema,
  ActionMetaSchema,
  EvidenceEventSchema,
  
  // Policy schemas
  PolicyScopeSchema,
  PolicyConditionsSchema,
  PolicyApprovalConfigSchema,
  PolicyArtifactSchema,
  
  // Approval schemas
  ApprovalStatusSchema,
  ApprovalDecisionSchema,
  ApprovalTicketSchema,
  
  // API schemas
  PaginationParamsSchema,
  ApiErrorSchema,
  HealthResponseSchema,
  
  // Token schemas
  ProofTokenHeaderSchema,
  ProofTokenClaimsSchema,
  
  // Validation helpers
  validateAuthorizeRequest,
  validateOutcomeRequest,
  validatePolicyArtifact,
  validateEvidenceEvent,
  safeParse,
  formatZodErrors,
} from './validators/index.js';

// =============================================================================
// LOGGER EXPORTS
// =============================================================================

export {
  Logger,
  createLogger,
  createLoggerFromEnv,
  logRequest,
  logAudit,
  logMetric,
} from './logger/index.js';

export type {
  LogLevel,
  LogContext,
  LogEntry,
  LoggerConfig,
  RequestLogContext,
  AuditLogContext,
  MetricLogContext,
} from './logger/index.js';

// =============================================================================
// CRYPTO EXPORTS
// =============================================================================

export {
  // Key generation
  generateEd25519KeyPair,
  generateES256KeyPair,
  loadPrivateKey,
  loadPublicKey,
  
  // Signing
  signEd25519,
  signES256,
  sign,
  
  // Verification
  verifyEd25519,
  verifyES256,
  verify,
  
  // Hashing (crypto module has its own implementation)
  verifyHash,
  
  // Proof tokens
  createProofToken,
  verifyProofToken,
  parseProofTokenUnsafe,
  
  // Evidence signing
  signEvidence,
  verifyEvidenceSignature,
  verifyHashChain,
  
  // Key store
  InMemoryKeyStore,
  
  // Random
  randomBytes,
  randomHex,
  randomUuid,
} from './crypto/index.js';

export type {
  KeyPair,
  SigningKey,
  VerificationKey,
  KeyStore,
  EvidenceSigningResult,
  HashChainVerificationResult,
} from './crypto/index.js';

// =============================================================================
// POLICY LOADER EXPORTS
// =============================================================================

export {
  // Loading
  loadPolicyPack,
  loadPoliciesFromFile,

  // Hashing
  computePolicyHash,
  computePackHash,
  formatHash,

  // Indexing
  indexById,
  indexByHash,
  filterActive,
  sortByPriority,

  // Statistics
  getPackStats,
} from './policy/index.js';

export {
  // PolicyArtifact pack loading
  loadPolicyArtifactPack,
  loadPolicyArtifactsFromFile,

  // Runtime-compatible hashing
  computeRuntimePolicyHash,
  computePolicyArtifactPackHash,
  normalizeHash,
  stripHashPrefix,

  // PolicyArtifact stats
  getPolicyArtifactPackStats,
} from './policy/artifact-pack.js';

export type {
  Policy,
  PolicyPack,
  PolicyPackManifest,
  PolicyPackMetadata,
  PolicyPackStats,
  PolicyScope as LoadedPolicyScope,
  PolicyMatch,
  PolicyCondition,
  PolicyObligation as LoadedPolicyObligation,
  PolicyApprovalConfig,
} from './policy/index.js';

export type {
  PolicyArtifactPack,
  PolicyArtifactPackManifest,
  PolicyArtifactPackStats,
} from './policy/artifact-pack.js';

// =============================================================================
// VERSION
// =============================================================================

export const VERSION = '0.1.9';
export const PACKAGE_NAME = '@stix/shared';
