/**
 * STIX Error Classes
 * Custom error types used across all STIX services
 * 
 * @module @stix/shared/errors
 */

/**
 * Base STIX Error
 */
export class StixError extends Error {
  public readonly code: string;
  public readonly statusCode: number;
  public readonly details?: unknown;
  public readonly timestamp: string;

  constructor(
    message: string,
    code: string,
    statusCode = 500,
    details?: unknown
  ) {
    super(message);
    this.name = 'StixError';
    this.code = code;
    this.statusCode = statusCode;
    this.details = details;
    this.timestamp = new Date().toISOString();
    Error.captureStackTrace(this, this.constructor);
  }

  toJSON(): Record<string, unknown> {
    return {
      name: this.name,
      code: this.code,
      message: this.message,
      statusCode: this.statusCode,
      details: this.details,
      timestamp: this.timestamp,
    };
  }
}

// =============================================================================
// AUTHORIZATION ERRORS
// =============================================================================

/**
 * Authorization denied error
 */
export class AuthorizationDeniedError extends StixError {
  public readonly reason_code: string;
  public readonly trace_id: string;

  constructor(
    reason_code: string,
    trace_id: string,
    message = 'Authorization denied',
    details?: unknown
  ) {
    super(message, 'AUTHORIZATION_DENIED', 403, details);
    this.name = 'AuthorizationDeniedError';
    this.reason_code = reason_code;
    this.trace_id = trace_id;
  }
}

/**
 * Authorization quarantined error
 */
export class AuthorizationQuarantinedError extends StixError {
  public readonly reason_code: string;
  public readonly trace_id: string;
  public readonly ticket_id?: string;

  constructor(
    reason_code: string,
    trace_id: string,
    ticket_id?: string,
    message = 'Authorization requires approval',
    details?: unknown
  ) {
    super(message, 'AUTHORIZATION_QUARANTINED', 403, details);
    this.name = 'AuthorizationQuarantinedError';
    this.reason_code = reason_code;
    this.trace_id = trace_id;
    this.ticket_id = ticket_id;
  }
}

// =============================================================================
// AUTHENTICATION ERRORS
// =============================================================================

/**
 * Authentication required error
 */
export class AuthenticationRequiredError extends StixError {
  constructor(message = 'Authentication required', details?: unknown) {
    super(message, 'AUTHENTICATION_REQUIRED', 401, details);
    this.name = 'AuthenticationRequiredError';
  }
}

/**
 * Invalid token error
 */
export class InvalidTokenError extends StixError {
  public readonly tokenError: string;

  constructor(tokenError: string, details?: unknown) {
    super(`Invalid token: ${tokenError}`, 'INVALID_TOKEN', 401, details);
    this.name = 'InvalidTokenError';
    this.tokenError = tokenError;
  }
}

/**
 * Token expired error
 */
export class TokenExpiredError extends StixError {
  constructor(details?: unknown) {
    super('Token has expired', 'TOKEN_EXPIRED', 401, details);
    this.name = 'TokenExpiredError';
  }
}

/**
 * Missing STIX token error
 */
export class MissingStixTokenError extends StixError {
  constructor(details?: unknown) {
    super('STIX proof token is required', 'MISSING_STIX_TOKEN', 401, details);
    this.name = 'MissingStixTokenError';
  }
}

// =============================================================================
// POLICY ERRORS
// =============================================================================

/**
 * Policy not found error
 */
export class PolicyNotFoundError extends StixError {
  public readonly policyId: string;

  constructor(policyId: string, details?: unknown) {
    super(`Policy not found: ${policyId}`, 'POLICY_NOT_FOUND', 404, details);
    this.name = 'PolicyNotFoundError';
    this.policyId = policyId;
  }
}

/**
 * Policy validation error
 */
export class PolicyValidationError extends StixError {
  public readonly validationErrors: string[];

  constructor(validationErrors: string[], details?: unknown) {
    super(
      `Policy validation failed: ${validationErrors.join('; ')}`,
      'POLICY_VALIDATION_ERROR',
      400,
      details
    );
    this.name = 'PolicyValidationError';
    this.validationErrors = validationErrors;
  }
}

/**
 * Policy conflict error
 */
export class PolicyConflictError extends StixError {
  public readonly conflictingPolicies: string[];

  constructor(conflictingPolicies: string[], details?: unknown) {
    super(
      `Policy conflict detected: ${conflictingPolicies.join(', ')}`,
      'POLICY_CONFLICT',
      409,
      details
    );
    this.name = 'PolicyConflictError';
    this.conflictingPolicies = conflictingPolicies;
  }
}

// =============================================================================
// EVIDENCE ERRORS
// =============================================================================

/**
 * Evidence not found error
 */
export class EvidenceNotFoundError extends StixError {
  public readonly eventId: string;

  constructor(eventId: string, details?: unknown) {
    super(`Evidence not found: ${eventId}`, 'EVIDENCE_NOT_FOUND', 404, details);
    this.name = 'EvidenceNotFoundError';
    this.eventId = eventId;
  }
}

/**
 * Evidence integrity error
 */
export class EvidenceIntegrityError extends StixError {
  public readonly eventId: string;
  public readonly integrityError: string;

  constructor(eventId: string, integrityError: string, details?: unknown) {
    super(
      `Evidence integrity check failed for ${eventId}: ${integrityError}`,
      'EVIDENCE_INTEGRITY_ERROR',
      500,
      details
    );
    this.name = 'EvidenceIntegrityError';
    this.eventId = eventId;
    this.integrityError = integrityError;
  }
}

/**
 * Evidence write error
 */
export class EvidenceWriteError extends StixError {
  constructor(message: string, details?: unknown) {
    super(message, 'EVIDENCE_WRITE_ERROR', 500, details);
    this.name = 'EvidenceWriteError';
  }
}

// =============================================================================
// APPROVAL ERRORS
// =============================================================================

/**
 * Approval not found error
 */
export class ApprovalNotFoundError extends StixError {
  public readonly ticketId: string;

  constructor(ticketId: string, details?: unknown) {
    super(`Approval ticket not found: ${ticketId}`, 'APPROVAL_NOT_FOUND', 404, details);
    this.name = 'ApprovalNotFoundError';
    this.ticketId = ticketId;
  }
}

/**
 * Approval expired error
 */
export class ApprovalExpiredError extends StixError {
  public readonly ticketId: string;

  constructor(ticketId: string, details?: unknown) {
    super(`Approval ticket has expired: ${ticketId}`, 'APPROVAL_EXPIRED', 410, details);
    this.name = 'ApprovalExpiredError';
    this.ticketId = ticketId;
  }
}

/**
 * Approval already processed error
 */
export class ApprovalAlreadyProcessedError extends StixError {
  public readonly ticketId: string;
  public readonly status: string;

  constructor(ticketId: string, status: string, details?: unknown) {
    super(
      `Approval ticket already ${status}: ${ticketId}`,
      'APPROVAL_ALREADY_PROCESSED',
      409,
      details
    );
    this.name = 'ApprovalAlreadyProcessedError';
    this.ticketId = ticketId;
    this.status = status;
  }
}

/**
 * Insufficient approval error
 */
export class InsufficientApprovalError extends StixError {
  public readonly ticketId: string;
  public readonly required: number;
  public readonly current: number;

  constructor(ticketId: string, required: number, current: number, details?: unknown) {
    super(
      `Insufficient approvals for ${ticketId}: ${current}/${required}`,
      'INSUFFICIENT_APPROVAL',
      403,
      details
    );
    this.name = 'InsufficientApprovalError';
    this.ticketId = ticketId;
    this.required = required;
    this.current = current;
  }
}

// =============================================================================
// VALIDATION ERRORS
// =============================================================================

/**
 * Validation error
 */
export class ValidationError extends StixError {
  public readonly field?: string;
  public readonly validationErrors: Array<{
    field: string;
    message: string;
    code?: string;
  }>;

  constructor(
    errors: Array<{ field: string; message: string; code?: string }>,
    details?: unknown
  ) {
    const message = errors.map(e => `${e.field}: ${e.message}`).join('; ');
    super(`Validation failed: ${message}`, 'VALIDATION_ERROR', 400, details);
    this.name = 'ValidationError';
    this.validationErrors = errors;
  }
}

/**
 * Invalid request error
 */
export class InvalidRequestError extends StixError {
  constructor(message: string, details?: unknown) {
    super(message, 'INVALID_REQUEST', 400, details);
    this.name = 'InvalidRequestError';
  }
}

// =============================================================================
// SERVICE ERRORS
// =============================================================================

/**
 * Service unavailable error
 */
export class ServiceUnavailableError extends StixError {
  public readonly serviceName: string;

  constructor(serviceName: string, details?: unknown) {
    super(`Service unavailable: ${serviceName}`, 'SERVICE_UNAVAILABLE', 503, details);
    this.name = 'ServiceUnavailableError';
    this.serviceName = serviceName;
  }
}

/**
 * Service timeout error
 */
export class ServiceTimeoutError extends StixError {
  public readonly serviceName: string;
  public readonly timeoutMs?: number;

  constructor(serviceName: string, timeoutMs?: number, details?: unknown) {
    const message = timeoutMs
      ? `Service timeout: ${serviceName} after ${timeoutMs}ms`
      : `Service timeout: ${serviceName}`;
    super(message, 'SERVICE_TIMEOUT', 504, details);
    this.name = 'ServiceTimeoutError';
    this.serviceName = serviceName;
    this.timeoutMs = timeoutMs;
  }
}

/**
 * Internal error
 */
export class InternalError extends StixError {
  constructor(message = 'Internal server error', details?: unknown) {
    super(message, 'INTERNAL_ERROR', 500, details);
    this.name = 'InternalError';
  }
}

/**
 * Configuration error
 */
export class ConfigurationError extends StixError {
  public readonly configKey?: string;

  constructor(message: string, configKey?: string, details?: unknown) {
    super(message, 'CONFIGURATION_ERROR', 500, details);
    this.name = 'ConfigurationError';
    this.configKey = configKey;
  }
}

// =============================================================================
// RATE LIMITING ERRORS
// =============================================================================

/**
 * Rate limit exceeded error
 */
export class RateLimitExceededError extends StixError {
  public readonly retryAfterSeconds?: number;

  constructor(retryAfterSeconds?: number, details?: unknown) {
    const message = retryAfterSeconds
      ? `Rate limit exceeded. Retry after ${retryAfterSeconds} seconds`
      : 'Rate limit exceeded';
    super(message, 'RATE_LIMIT_EXCEEDED', 429, details);
    this.name = 'RateLimitExceededError';
    this.retryAfterSeconds = retryAfterSeconds;
  }
}

// =============================================================================
// CRYPTO ERRORS
// =============================================================================

/**
 * Signature verification error
 */
export class SignatureVerificationError extends StixError {
  constructor(message = 'Signature verification failed', details?: unknown) {
    super(message, 'SIGNATURE_VERIFICATION_ERROR', 401, details);
    this.name = 'SignatureVerificationError';
  }
}

/**
 * Hash chain error
 */
export class HashChainError extends StixError {
  public readonly eventId: string;

  constructor(eventId: string, message: string, details?: unknown) {
    super(`Hash chain error at ${eventId}: ${message}`, 'HASH_CHAIN_ERROR', 500, details);
    this.name = 'HashChainError';
    this.eventId = eventId;
  }
}

// =============================================================================
// UTILITY FUNCTIONS
// =============================================================================

/**
 * Check if an error is a STIX error
 */
export function isStixError(error: unknown): error is StixError {
  return error instanceof StixError;
}

/**
 * Convert any error to a StixError
 */
export function toStixError(error: unknown): StixError {
  if (error instanceof StixError) {
    return error;
  }

  if (error instanceof Error) {
    return new InternalError(error.message, {
      originalName: error.name,
      stack: error.stack,
    });
  }

  return new InternalError('Unknown error', { originalError: error });
}

/**
 * Create error response object
 */
export function createErrorResponse(error: StixError): {
  success: false;
  error: {
    code: string;
    message: string;
    details?: unknown;
  };
} {
  return {
    success: false,
    error: {
      code: error.code,
      message: error.message,
      details: error.details,
    },
  };
}
