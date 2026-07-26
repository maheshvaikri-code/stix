/**
 * STIX Shared Types
 * Core type definitions used across all STIX services
 * 
 * @module @stix/shared/types
 */

// =============================================================================
// ENUMS & LITERALS
// =============================================================================

/** Decision outcomes from STIX authorization */
export type DecisionKind = 'ALLOW' | 'DENY' | 'QUARANTINE';

/** Actor types that can request authorization */
export type ActorType = 'HUMAN' | 'SERVICE' | 'AI_AGENT' | 'JOB' | 'SYSTEM';

/** Actor type filter in policies (supports wildcard) */
export type ActorTypeFilter = ActorType | '*';

/** Environment classifications */
export type Environment = 'dev' | 'test' | 'stage' | 'prod';

/** Risk tier classifications */
export type RiskTier = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

/** Evidence schema versions */
export type SchemaVersion = '1.0';

/** Obligation types that can be attached to ALLOW decisions */
export type ObligationType = 
  | 'REDACT_FIELDS'
  | 'MASK_PII'
  | 'WATERMARK_OUTPUT'
  | 'REQUIRE_APPROVAL'
  | 'RATE_LIMIT'
  | 'LOG_LEVEL'
  | 'ENCRYPT_TRANSIT'
  | 'DUAL_CONTROL'
  | 'TIME_LIMIT'
  | 'NOTIFY'
  | 'AUDIT_LOG'
  | 'DATA_FORMAT'
  | 'DATA_MASK'
  | 'NOTIFY_DPO'
  | 'NOTIFY_SERVICE_PROVIDERS'
  | 'PROVIDE_EXPLANATION'
  | 'RESPOND_WITHIN'
  | 'STOP_PROCESSING';

/** Outcome statuses for execution results */
export type OutcomeStatus = 'SUCCESS' | 'FAILED' | 'SKIPPED' | 'PENDING';

/** Fail modes for STIX unavailability */
export type FailMode = 'CLOSED' | 'OPEN_LOW_RISK_ONLY' | 'OPEN';

// =============================================================================
// CORE INTERFACES
// =============================================================================

/**
 * Actor - Who is performing the action
 */
export interface Actor {
  /** Unique identifier for the actor */
  id: string;
  /** Type of actor */
  type: ActorType;
  /** Role/permission set */
  role?: string;
  /** Tenant/organization identifier */
  tenant?: string;
  /** Additional actor attributes */
  attributes?: Record<string, unknown>;
}

/**
 * Resource - What is being accessed/acted upon
 */
export interface Resource {
  /** Resource type classification */
  type: string;
  /** Specific resource identifier */
  id?: string;
  /** Data classification labels */
  classification?: string[];
  /** Additional resource attributes */
  attributes?: Record<string, unknown>;
}

/**
 * Detection signals from local classification
 */
export interface DetectionSignals {
  /** Personally Identifiable Information detected */
  piiDetected?: boolean;
  /** Protected Health Information detected */
  phiDetected?: boolean;
  /** Payment Card Industry data detected */
  pciDetected?: boolean;
  /** Secrets/credentials detected */
  secretsDetected?: boolean;
  /** Custom detection signals */
  custom?: Record<string, boolean>;
}

/**
 * Context - Environmental and situational context
 */
export interface Context {
  /** Execution environment */
  env: Environment;
  /** Business purpose/justification */
  purpose?: string;
  /** Correlation ID for the agent run */
  run_id?: string;
  /** Session/conversation identifier */
  session_id?: string;
  /** Change ticket/work item reference */
  ticket_id?: string;
  /** Geographic jurisdiction */
  jurisdiction?: string;
  /** Context tags */
  tags?: string[];
  /** Detection signals */
  signals?: DetectionSignals;
  /** Additional context attributes */
  attributes?: Record<string, unknown>;
}

/**
 * Tool call metadata
 */
export interface ToolCall {
  /** Tool name/identifier */
  tool: string;
  /** Risk tier of the tool */
  risk_tier?: RiskTier;
  /** Safe summary of arguments (no sensitive data) */
  args_summary?: string;
  /** Caller-computed hash of the exact raw arguments, when available */
  args_hash?: string;
}

// =============================================================================
// REQUEST/RESPONSE INTERFACES
// =============================================================================

/**
 * Authorization Request - Input to STIX Enforcer
 */
export interface AuthorizeRequest {
  /** Who is performing the action */
  actor: Actor;
  /** Stable caller-supplied action identifier (derived when omitted) */
  action_id?: string;
  /** What action is being performed */
  action: string;
  /** What resource is being accessed */
  resource: Resource;
  /** Environmental context */
  context: Context;
  /** Tool call metadata (for agent actions) */
  tool_call?: ToolCall;
  /** Approval ticket reference used for a post-approval reauthorization */
  approval_ref?: string;
}

/**
 * Obligation to be applied when action is allowed
 */
export interface Obligation {
  /** Type of obligation */
  type: ObligationType;
  /** Obligation parameters */
  params?: Record<string, unknown>;
}

/**
 * Approval information for QUARANTINE decisions
 */
export interface ApprovalInfo {
  /** Whether approval is required */
  required: boolean;
  /** Ticket/request ID for tracking */
  ticket_id?: string;
  /** Role required for approval */
  approver_role?: string;
  /** Number of approvers required */
  require_count?: number;
  /** Whether justification is required */
  require_justification?: boolean;
  /** Expiration timestamp */
  expires_at?: string;
}

/**
 * Policy reference in decisions
 */
export interface PolicyRef {
  /** Policy identifier */
  id: string;
  /** Policy version */
  version: string;
  /** Content hash for replay */
  hash: string;
}

/**
 * Authorization Response - Output from STIX Enforcer
 */
export interface AuthorizeResponse {
  /** Decision outcome */
  decision: DecisionKind;
  /** Machine-readable reason code */
  reason_code: string;
  /** Correlation trace ID */
  trace_id: string;
  /** Stable action identifier bound into the proof token */
  action_id?: string;
  /** Human-readable explanation */
  explanation?: string;
  /** Policy that produced this decision */
  policy: PolicyRef;
  /** Obligations to apply (for ALLOW) */
  obligations: Obligation[];
  /** Approval information (for QUARANTINE) */
  approval: ApprovalInfo | null;
  /** Proof token (for ALLOW) - used by protected targets */
  proof_token?: string;
  /** Control framework mappings */
  controls?: string[];
  /** Regulation references */
  regulations?: string[];
}

/**
 * Outcome recording request
 */
export interface OutcomeRequest {
  /** Trace ID from authorization */
  trace_id: string;
  /** Execution status */
  status: OutcomeStatus;
  /** Result summary (safe) */
  result_summary?: string;
  /** Error class if failed */
  error_class?: string;
  /** Obligations that were applied */
  obligations_applied?: Record<string, boolean>;
  /** Actor who performed the action */
  actor?: Actor;
  /** Action metadata */
  action?: ActionMeta;
  /** Resource metadata */
  resource?: Resource;
  /** Context snapshot */
  context?: Context;
  /** Policy reference */
  policy?: PolicyRef;
}

/**
 * Action metadata for evidence
 */
export interface ActionMeta {
  /** Action name */
  name: string;
  /** Tool used */
  tool?: string;
  /** Risk tier */
  risk_tier?: RiskTier;
  /** Optional action parameters snapshot */
  params?: Record<string, unknown>;
}

// =============================================================================
// EVIDENCE INTERFACES
// =============================================================================

/**
 * Integrity block for tamper-evident evidence
 */
export interface IntegrityBlock {
  /** SHA-256 hash of canonical event */
  event_hash: string;
  /** Hash of previous event in chain */
  prev_hash: string;
  /** Ed25519 signature */
  signature: string;
  /** Key identifier used for signing */
  key_id?: string;
  /** Hash/signature algorithm hint */
  algorithm?: string;
}

/**
 * Outcome information in evidence
 */
export interface OutcomeInfo {
  /** Execution status */
  status?: OutcomeStatus;
  /** Result summary */
  result_summary?: string;
  /** Error class if failed */
  error_class?: string;
}

/**
 * Obligations applied tracking
 */
export interface ObligationsApplied {
  /** Redaction was applied */
  redaction?: boolean;
  /** Watermark was applied */
  watermark?: boolean;
  /** Rate limit enforced */
  rate_limit?: boolean;
  /** PII masking applied */
  pii_masked?: boolean;
}

/**
 * Canonical Evidence Event - Immutable audit record
 */
export interface EvidenceEvent {
  /** Schema version for compatibility */
  schema_version?: SchemaVersion;
  /** Unique event identifier */
  event_id: string;
  /** Correlation trace ID */
  trace_id: string;
  /** ISO-8601 timestamp with milliseconds */
  timestamp: string;
  /** Legacy event kind used by some stores/routes */
  event_type?: 'DECISION' | 'OUTCOME';
  /** Legacy payload version marker */
  version?: string;
  
  /** Decision outcome */
  decision?: DecisionKind;
  /** Machine-readable reason code */
  reason_code?: string;
  
  /** Actor who performed the action */
  actor?: Actor;
  /** Action metadata */
  action?: ActionMeta;
  /** Resource metadata */
  resource?: Resource;
  /** Context snapshot */
  context?: Context;
  
  /** Policy reference */
  policy?: PolicyRef;
  
  /** Control framework mappings */
  controls?: string[];
  /** Regulation references */
  regulations?: string[];
  /** Legacy obligations list */
  obligations?: Obligation[];
  /** Legacy pack hash */
  pack_hash?: string;
  /** Optional metadata bag */
  metadata?: Record<string, unknown>;
  
  /** Obligations that were applied */
  obligations_applied?: ObligationsApplied;
  /** Execution outcome */
  outcome?: OutcomeInfo;
  
  /** Integrity block (hash chain + signature) */
  integrity: IntegrityBlock;
}

// =============================================================================
// POLICY INTERFACES
// =============================================================================

/**
 * Policy scope definition
 * Supports wildcards: '*' matches any value
 */
export interface PolicyScope {
  /** Actor type filter (supports '*' wildcard) */
  actor_type: ActorTypeFilter;
  /** Action filter (supports glob patterns like 'read_*') */
  action: string;
  /** Resource type filter (supports glob patterns) */
  resource_type: string;
  /** Optional environment allow-list */
  environments?: Environment[];
  /** Optional required resource classifications */
  classifications?: string[];
}

/**
 * Policy conditions
 */
export interface PolicyConditions {
  /** Environment filter */
  env?: Environment;
  /** Legacy time window condition */
  time_window?: { start?: string; end?: string };
  /** Required detection signals */
  require_signal?: Partial<DetectionSignals>;
  /** Legacy required signal map */
  require_signals?: Record<string, boolean | string | number>;
  /** Required resource attributes */
  require_resource_attr?: Record<string, unknown>;
  /** Legacy required attributes across actor/resource/context */
  require_attributes?: Record<string, unknown>;
  /** Allowed risk tiers */
  risk_tiers?: string[];
  /** Required context tags */
  tags?: string[];
  /** Allowed jurisdictions */
  jurisdictions?: string[];
  /** Allowed tenants */
  tenants?: string[];
  /** Custom expression */
  expression?: string;
  /** Required actor attributes */
  require_actor_attr?: Record<string, unknown>;
  /** Tenant match requirement */
  require_tenant_match?: boolean;
  /** Custom conditions */
  custom?: Record<string, unknown>;
}

/**
 * Policy approval configuration
 */
export interface PolicyApproval {
  /** Role required for approval */
  approver_role?: string;
  /** Number of approvers required */
  require_count?: number;
  /** Whether ticket is required */
  require_ticket?: boolean;
  /** Whether justification is required */
  require_justification?: boolean;
  /** Approval timeout in hours */
  timeout_hours?: number;
}

/**
 * Policy artifact - Immutable policy definition
 */
export interface PolicyArtifact {
  /** Unique policy identifier */
  policy_id: string;
  /** Semantic version */
  version: string;
  /** Priority (lower = higher priority) */
  priority?: number;
  /** Description */
  description?: string;
  /** When the action should match */
  scope: PolicyScope;
  /** Conditions that must be met */
  conditions?: PolicyConditions;
  /** Decision to return */
  decision: DecisionKind;
  /** Reason code */
  reason_code: string;
  /** Obligations for ALLOW */
  obligations?: Obligation[];
  /** Approval config for QUARANTINE */
  approval?: PolicyApproval;
  /** Control framework mappings */
  controls?: string[];
  /** Regulation references */
  regulations?: string[];
  /** Legacy single regulation label */
  regulation?: string;
  /** Policy tags */
  tags?: string[];
  /** Legacy computed hash */
  hash?: string;
  /** Legacy metadata */
  metadata?: Record<string, unknown>;
  /** Whether policy is active */
  active?: boolean;
  /** Creation timestamp */
  created_at?: string;
  /** Last update timestamp */
  updated_at?: string;
}

/**
 * Policy evaluation result
 */
export interface PolicyDecision {
  /** Decision outcome */
  decision: DecisionKind;
  /** Reason code */
  reason_code: string;
  /** Policy reference */
  policy: PolicyRef;
  /** Obligations to apply */
  obligations: Obligation[];
  /** Approval information */
  approval: ApprovalInfo | null;
  /** Control mappings */
  controls: string[];
  /** Regulation references */
  regulations: string[];
  /** Explanation */
  explanation?: string;
}

// =============================================================================
// PROOF TOKEN INTERFACES
// =============================================================================

/**
 * STIX Proof Token Claims
 */
export interface ProofTokenClaims {
  /** Issuer (always "stix") */
  iss: string;
  /** Subject (actor ID) */
  sub: string;
  /** Action */
  act: string;
  /** Resource type */
  res: string;
  /** Classification labels */
  cls: string[];
  /** Policy hash */
  pol: string;
  /** Trace ID */
  tid: string;
  /** Issued at (Unix timestamp) */
  iat: number;
  /** Expiration (Unix timestamp) */
  exp: number;
  /** Unique replay identifier (also emitted as JWT jti) */
  replay_id?: string;
  /** JWT ID for consumers that use standard replay terminology */
  jti?: string;
  /** Hash of the exact authorization request */
  request_hash?: string;
  /** Hash of the exact tool-call argument metadata */
  arguments_hash?: string;
  /** Stable action identifier */
  action_id?: string;
  /** Exact resource identifier */
  resource_id?: string;
  /** Approval ticket that authorized this proof, when applicable */
  approval_ref?: string;
  /** Full decision fields used by target verifiers */
  decision?: DecisionKind;
  reason_code?: string;
  policy_id?: string;
  policy_version?: string;
  policy_hash?: string;
  pack_hash?: string;
  actor_id?: string;
  actor_type?: ActorType;
  actor_role?: string;
  actor_tenant?: string;
  action?: string;
  resource_type?: string;
  risk_tier?: RiskTier;
  obligations?: string;
}

/** Security binding persisted with an approval ticket. */
export interface ApprovalBinding {
  request_hash: string;
  arguments_hash: string;
  action_id: string;
  actor_id: string;
  actor_type: ActorType;
  actor_role?: string;
  actor_tenant?: string;
  action: string;
  resource_type: string;
  resource_id?: string;
}

/**
 * Token header
 */
export interface ProofTokenHeader {
  /** Algorithm */
  alg: 'EdDSA' | 'ES256';
  /** Type */
  typ: 'JWT';
  /** Key ID */
  kid: string;
}

// =============================================================================
// API INTERFACES
// =============================================================================

/**
 * Standard API response wrapper
 */
export interface ApiResponse<T> {
  /** Whether request was successful */
  success: boolean;
  /** Response data */
  data?: T;
  /** Error information */
  error?: {
    code: string;
    message: string;
    details?: unknown;
  };
  /** Request metadata */
  meta?: {
    request_id: string;
    timestamp: string;
    duration_ms: number;
  };
}

/**
 * Health check response
 */
export interface HealthResponse {
  /** Service status */
  status: 'healthy' | 'degraded' | 'unhealthy';
  /** Service version */
  version: string;
  /** Service name */
  service: string;
  /** Uptime in seconds */
  uptime: number;
  /** Timestamp */
  timestamp: string;
  /** Component health checks */
  checks?: Record<string, {
    status: 'pass' | 'fail' | 'warn';
    message?: string;
    duration_ms?: number;
  }>;
}

/**
 * Pagination parameters
 */
export interface PaginationParams {
  /** Page number (1-indexed) */
  page?: number;
  /** Items per page */
  limit?: number;
  /** Sort field */
  sort_by?: string;
  /** Sort order */
  sort_order?: 'asc' | 'desc';
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  /** Items */
  items: T[];
  /** Total count */
  total: number;
  /** Current page */
  page: number;
  /** Items per page */
  limit: number;
  /** Total pages */
  pages: number;
  /** Has next page */
  has_next: boolean;
  /** Has previous page */
  has_prev: boolean;
}
