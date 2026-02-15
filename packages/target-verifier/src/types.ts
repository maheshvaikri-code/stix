/**
 * STIX Target Verifier Types
 * Type definitions for protected target verification
 *
 * @module @stix/target-verifier
 */

import type { DecisionKind, Obligation, RiskTier } from '@stix/shared';

// =============================================================================
// VERIFICATION REQUEST
// =============================================================================

/**
 * Request to verify a proof token before executing a protected action
 */
export interface VerifyRequest {
  /** The proof token from STIX-Token header */
  token: string;

  /** Expected action that the token should authorize */
  expectedAction: string;

  /** Expected resource type */
  expectedResourceType?: string;

  /** Expected resource ID */
  expectedResourceId?: string;

  /** Additional context to validate */
  context?: Record<string, unknown>;

  /** Whether to check token expiration strictly */
  strictExpiration?: boolean;

  /** Maximum allowed token age in seconds */
  maxTokenAge?: number;
}

// =============================================================================
// VERIFICATION RESULT
// =============================================================================

/**
 * Result of token verification
 */
export interface VerifyResult {
  /** Whether verification succeeded */
  valid: boolean;

  /** Decision from the token (if valid) */
  decision?: DecisionKind;

  /** Trace ID from the authorization */
  traceId?: string;

  /** Policy ID that made the decision */
  policyId?: string;

  /** Policy version */
  policyVersion?: string;

  /** Reason code */
  reasonCode?: string;

  /** Obligations that must be applied */
  obligations?: Obligation[];

  /** Risk tier of the action */
  riskTier?: RiskTier;

  /** Token expiration timestamp */
  expiresAt?: string;

  /** Token issued at timestamp */
  issuedAt?: string;

  /** Errors if verification failed */
  errors?: VerificationError[];

  /** Raw claims from the token */
  claims?: TokenClaims;
}

/**
 * Verification error details
 */
export interface VerificationError {
  /** Error code */
  code: VerificationErrorCode;

  /** Human-readable message */
  message: string;

  /** Additional details */
  details?: Record<string, unknown>;
}

/**
 * Verification error codes
 */
export type VerificationErrorCode =
  | 'TOKEN_MISSING'
  | 'TOKEN_MALFORMED'
  | 'TOKEN_EXPIRED'
  | 'TOKEN_NOT_YET_VALID'
  | 'SIGNATURE_INVALID'
  | 'KEY_NOT_FOUND'
  | 'ACTION_MISMATCH'
  | 'RESOURCE_MISMATCH'
  | 'DECISION_DENIED'
  | 'DECISION_QUARANTINE'
  | 'CLAIMS_INVALID'
  | 'CONTEXT_MISMATCH'
  | 'INTERNAL_ERROR';

// =============================================================================
// TOKEN CLAIMS
// =============================================================================

/**
 * Claims extracted from a proof token
 */
export interface TokenClaims {
  /** Issuer (STIX Enforcer) */
  iss: string;

  /** Subject (trace ID) */
  sub: string;

  /** Issued at (unix timestamp) */
  iat: number;

  /** Expiration (unix timestamp) */
  exp: number;

  /** Not before (unix timestamp) */
  nbf?: number;

  /** JWT ID */
  jti?: string;

  /** Decision */
  decision: DecisionKind;

  /** Reason code */
  reason_code: string;

  /** Policy ID */
  policy_id: string;

  /** Policy version */
  policy_version: string;

  /** Policy hash */
  policy_hash: string;

  /** Pack hash */
  pack_hash: string;

  /** Actor ID */
  actor_id: string;

  /** Actor type */
  actor_type: string;

  /** Action name */
  action: string;

  /** Resource type */
  resource_type: string;

  /** Resource ID */
  resource_id?: string;

  /** Risk tier */
  risk_tier?: RiskTier;

  /** Obligations (JSON encoded) */
  obligations?: string;

  /** Evidence hash */
  evidence_hash?: string;

  /** Request hash */
  request_hash?: string;
}

// =============================================================================
// VERIFIER CONFIGURATION
// =============================================================================

/**
 * Configuration for the target verifier
 */
export interface VerifierConfig {
  /** Public keys for signature verification (PEM or JWK) */
  publicKeys: PublicKeyConfig[];

  /** Expected token issuer */
  expectedIssuer?: string;

  /** Clock skew tolerance in seconds */
  clockSkew?: number;

  /** Default max token age in seconds */
  defaultMaxTokenAge?: number;

  /** Whether to require action matching */
  requireActionMatch?: boolean;

  /** Whether to require resource matching */
  requireResourceMatch?: boolean;

  /** Allowed algorithms */
  allowedAlgorithms?: string[];

  /** Whether to cache verified tokens */
  enableCache?: boolean;

  /** Cache TTL in seconds */
  cacheTtl?: number;
}

/**
 * Public key configuration
 */
export interface PublicKeyConfig {
  /** Key ID */
  keyId: string;

  /** Algorithm (EdDSA, ES256) */
  algorithm: 'EdDSA' | 'ES256';

  /** Public key in PEM format */
  pem?: string;

  /** Public key in JWK format */
  jwk?: Record<string, unknown>;
}

// =============================================================================
// PROTECTION WRAPPER
// =============================================================================

/**
 * Options for protecting an action
 */
export interface ProtectOptions {
  /** Action being protected */
  action: string;

  /** Resource type */
  resourceType: string;

  /** Resource ID */
  resourceId?: string;

  /** Custom validation function */
  validate?: (claims: TokenClaims) => boolean | Promise<boolean>;

  /** Whether to log the verification */
  logVerification?: boolean;

  /** Headers to look for the token */
  tokenHeaders?: string[];
}

/**
 * Protected action context
 */
export interface ProtectedContext {
  /** The verification result */
  verification: VerifyResult;

  /** Trace ID for correlation */
  traceId: string;

  /** Claims from the token */
  claims: TokenClaims;

  /** Obligations to apply */
  obligations: Obligation[];

  /** Function to report outcome */
  reportOutcome: (success: boolean, details?: Record<string, unknown>) => Promise<void>;
}

// =============================================================================
// AUDIT
// =============================================================================

/**
 * Audit event for target verification
 */
export interface VerificationAuditEvent {
  /** Event timestamp */
  timestamp: string;

  /** Event type */
  type: 'VERIFICATION_SUCCESS' | 'VERIFICATION_FAILURE' | 'ACTION_EXECUTED' | 'ACTION_BLOCKED';

  /** Trace ID */
  traceId?: string;

  /** Token JTI */
  tokenJti?: string;

  /** Action */
  action: string;

  /** Resource */
  resource: {
    type: string;
    id?: string;
  };

  /** Decision */
  decision?: DecisionKind;

  /** Errors */
  errors?: VerificationError[];

  /** Duration in ms */
  durationMs?: number;

  /** Additional metadata */
  metadata?: Record<string, unknown>;
}

/**
 * Audit logger interface
 */
export interface AuditLogger {
  log(event: VerificationAuditEvent): void | Promise<void>;
}
