/**
 * STIX Agent SDK Types
 * Type definitions for the Agent SDK
 */

import type {
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
} from '@stix/shared';

// Re-export commonly used types
export type {
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
};

// =============================================================================
// CLIENT CONFIGURATION
// =============================================================================

/**
 * STIX Client configuration
 */
export interface StixClientConfig {
  /** Enforcer service URL */
  enforcerUrl: string;

  /** Evidence service URL (optional, defaults to enforcerUrl) */
  evidenceUrl?: string;

  /** Approvals service URL (optional, defaults to enforcerUrl) */
  approvalsUrl?: string;

  /** API key for authentication */
  apiKey?: string;

  /** mTLS certificate path */
  certPath?: string;

  /** mTLS key path */
  keyPath?: string;

  /** CA certificate path */
  caPath?: string;

  /** Default actor information */
  defaultActor?: Partial<Actor>;

  /** Default context */
  defaultContext?: Partial<Context>;

  /** Request timeout in milliseconds */
  timeout?: number;

  /** Number of retries on failure */
  retries?: number;

  /** Fail mode when STIX is unavailable */
  failMode?: FailMode;

  /** Enable debug logging */
  debug?: boolean;

  /** Custom logger */
  logger?: Logger;

  /** Telemetry hooks */
  telemetry?: TelemetryHooks;
}

/**
 * Logger interface for custom logging
 */
export interface Logger {
  debug(message: string, meta?: Record<string, unknown>): void;
  info(message: string, meta?: Record<string, unknown>): void;
  warn(message: string, meta?: Record<string, unknown>): void;
  error(message: string, meta?: Record<string, unknown>): void;
}

/**
 * Telemetry hooks for observability
 */
export interface TelemetryHooks {
  /** Called before authorization request */
  onAuthorizationStart?(request: AuthorizeRequest): void;

  /** Called after authorization response */
  onAuthorizationComplete?(
    request: AuthorizeRequest,
    response: AuthorizeResponse,
    durationMs: number
  ): void;

  /** Called on authorization error */
  onAuthorizationError?(
    request: AuthorizeRequest,
    error: Error,
    durationMs: number
  ): void;

  /** Called when outcome is recorded */
  onOutcomeRecorded?(traceId: string, status: OutcomeStatus): void;

  /** Called when approval status changes */
  onApprovalStatusChange?(
    traceId: string,
    status: ApprovalStatus,
    previousStatus?: ApprovalStatus
  ): void;
}

// =============================================================================
// AUTHORIZATION TYPES
// =============================================================================

/**
 * Simplified authorization request for SDK
 */
export interface AuthorizeParams {
  /** Action being performed */
  action: string;

  /** Resource being accessed */
  resource: string | Resource;

  /** Actor override (uses default if not provided) */
  actor?: Partial<Actor>;

  /** Context override (merges with default) */
  context?: Partial<Context>;

  /** Tool call metadata */
  toolCall?: Partial<ToolCall>;

  /** Wait for approval if quarantined */
  waitForApproval?: boolean;

  /** Approval timeout in milliseconds */
  approvalTimeout?: number;

  /** Approval poll interval in milliseconds */
  approvalPollInterval?: number;
}

/**
 * Authorization result for SDK consumers
 */
export interface AuthorizationResult {
  /** Whether action is allowed */
  allowed: boolean;

  /** Decision kind */
  decision: DecisionKind;

  /** Trace ID for correlation */
  traceId: string;

  /** Reason code */
  reasonCode: string;

  /** Human-readable explanation */
  explanation?: string;

  /** Obligations to apply */
  obligations: Obligation[];

  /** Proof token (if allowed) */
  proofToken?: string;

  /** Approval required (if quarantined) */
  approvalRequired?: boolean;

  /** Approval ticket ID */
  approvalTicketId?: string;

  /** Control framework mappings */
  controls: string[];

  /** Regulation references */
  regulations: string[];
}

// =============================================================================
// APPROVAL TYPES
// =============================================================================

/**
 * Approval request status
 */
export type ApprovalStatus =
  | 'pending'
  | 'approved'
  | 'denied'
  | 'expired'
  | 'cancelled';

/**
 * Approval request details
 */
export interface ApprovalRequest {
  /** Request ID */
  id: string;

  /** Trace ID */
  traceId: string;

  /** Current status */
  status: ApprovalStatus;

  /** Requester actor */
  actor: Actor;

  /** Requested action */
  action: string;

  /** Requested resource */
  resource: Resource;

  /** Request context */
  context: Context;

  /** Required approver role */
  approverRole?: string;

  /** Number of approvals required */
  requiredCount: number;

  /** Current approval count */
  currentCount: number;

  /** Approvals received */
  approvals: ApprovalRecord[];

  /** Request timestamp */
  createdAt: string;

  /** Expiration timestamp */
  expiresAt: string;

  /** Resolution timestamp */
  resolvedAt?: string;
}

/**
 * Individual approval record
 */
export interface ApprovalRecord {
  /** Approver ID */
  approverId: string;

  /** Approval decision */
  decision: 'approve' | 'deny';

  /** Justification */
  justification?: string;

  /** Timestamp */
  timestamp: string;
}

/**
 * Approval polling options
 */
export interface ApprovalPollOptions {
  /** Maximum time to wait (ms) */
  timeout?: number;

  /** Poll interval (ms) */
  interval?: number;

  /** Callback on status change */
  onStatusChange?: (status: ApprovalStatus) => void;

  /** Abort signal */
  signal?: AbortSignal;
}

// =============================================================================
// TOOL WRAPPER TYPES
// =============================================================================

/**
 * Tool definition for wrapping
 */
export interface ToolDefinition<TArgs = unknown, TResult = unknown> {
  /** Tool name */
  name: string;

  /** Tool description */
  description?: string;

  /** Risk tier */
  riskTier?: RiskTier;

  /** Resource type accessed by tool */
  resourceType: string;

  /** Action performed by tool */
  action: string;

  /** Function to extract resource from args */
  getResource?: (args: TArgs) => string | Resource;

  /** Function to extract context from args */
  getContext?: (args: TArgs) => Partial<Context>;

  /** Function to summarize args (for evidence) */
  summarizeArgs?: (args: TArgs) => string;

  /** The actual tool function */
  execute: (args: TArgs) => TResult | Promise<TResult>;
}

/**
 * Wrapped tool function
 */
export interface WrappedTool<TArgs = unknown, TResult = unknown> {
  /** Tool name */
  name: string;

  /** Tool description */
  description?: string;

  /** Execute with STIX authorization */
  execute(args: TArgs): Promise<WrappedToolResult<TResult>>;

  /** Execute and throw on denial */
  executeOrThrow(args: TArgs): Promise<TResult>;

  /** Check authorization without executing */
  checkAuth(args: TArgs): Promise<AuthorizationResult>;
}

/**
 * Result from wrapped tool execution
 */
export interface WrappedToolResult<TResult = unknown> {
  /** Whether execution was successful */
  success: boolean;

  /** Authorization result */
  authorization: AuthorizationResult;

  /** Tool execution result (if allowed) */
  result?: TResult;

  /** Error (if any) */
  error?: Error;

  /** Outcome status */
  outcomeStatus: OutcomeStatus;
}

// =============================================================================
// ERROR TYPES
// =============================================================================

/**
 * Base STIX SDK error
 */
export class StixError extends Error {
  constructor(
    message: string,
    public readonly code: string,
    public readonly details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'StixError';
  }
}

/**
 * Authorization denied error
 */
export class AuthorizationDeniedError extends StixError {
  constructor(
    public readonly result: AuthorizationResult
  ) {
    super(
      `Authorization denied: ${result.reasonCode}`,
      'AUTHORIZATION_DENIED',
      { result }
    );
    this.name = 'AuthorizationDeniedError';
  }
}

/**
 * Approval timeout error
 */
export class ApprovalTimeoutError extends StixError {
  constructor(
    public readonly traceId: string,
    public readonly ticketId: string
  ) {
    super(
      `Approval timeout for trace ${traceId}`,
      'APPROVAL_TIMEOUT',
      { traceId, ticketId }
    );
    this.name = 'ApprovalTimeoutError';
  }
}

/**
 * STIX service unavailable error
 */
export class ServiceUnavailableError extends StixError {
  constructor(
    public readonly service: string,
    public readonly cause?: Error
  ) {
    super(
      `STIX service unavailable: ${service}`,
      'SERVICE_UNAVAILABLE',
      { service, cause: cause?.message }
    );
    this.name = 'ServiceUnavailableError';
  }
}

/**
 * Fail mode triggered error
 */
export class FailModeTriggeredError extends StixError {
  constructor(
    public readonly failMode: FailMode,
    public readonly riskTier?: RiskTier
  ) {
    super(
      `STIX unavailable, fail mode ${failMode} blocked action`,
      'FAIL_MODE_TRIGGERED',
      { failMode, riskTier }
    );
    this.name = 'FailModeTriggeredError';
  }
}
