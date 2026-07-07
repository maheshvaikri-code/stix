/**
 * STIX Shared Constants
 * Enterprise configuration constants used across all STIX services
 * 
 * @module @stix/shared/constants
 */

// =============================================================================
// SERVICE CONFIGURATION
// =============================================================================

/** Default service ports */
export const SERVICE_PORTS = {
  ENFORCER: 3001,
  POLICY: 3002,
  EVIDENCE: 3003,
  APPROVALS: 3004,
  FABRIC: 3005,
  GATEWAY: 3000,
} as const;

/** Service names for discovery */
export const SERVICE_NAMES = {
  ENFORCER: 'stix-enforcer',
  POLICY: 'stix-policy',
  EVIDENCE: 'stix-evidence',
  APPROVALS: 'stix-approvals',
  FABRIC: 'stix-fabric',
  GATEWAY: 'stix-gateway',
} as const;

/** Internal service URLs (Kubernetes/Docker) */
export const SERVICE_URLS = {
  ENFORCER: `http://${SERVICE_NAMES.ENFORCER}:${SERVICE_PORTS.ENFORCER}`,
  POLICY: `http://${SERVICE_NAMES.POLICY}:${SERVICE_PORTS.POLICY}`,
  EVIDENCE: `http://${SERVICE_NAMES.EVIDENCE}:${SERVICE_PORTS.EVIDENCE}`,
  APPROVALS: `http://${SERVICE_NAMES.APPROVALS}:${SERVICE_PORTS.APPROVALS}`,
  FABRIC: `http://${SERVICE_NAMES.FABRIC}:${SERVICE_PORTS.FABRIC}`,
} as const;

// =============================================================================
// API VERSIONING
// =============================================================================

/** Current API version */
export const API_VERSION = 'v1';

/** API base paths */
export const API_PATHS = {
  AUTHORIZE: '/api/v1/authorize',
  OUTCOME: '/api/v1/outcome',
  EVIDENCE: '/api/v1/evidence',
  POLICIES: '/api/v1/policies',
  APPROVALS: '/api/v1/approvals',
  FABRIC: '/api/v1/fabric',
  HEALTH: '/health',
  READY: '/ready',
  METRICS: '/metrics',
} as const;

// =============================================================================
// SECURITY CONSTANTS
// =============================================================================

/** Token configuration */
export const TOKEN_CONFIG = {
  /** Default token expiration in seconds (5 minutes) */
  DEFAULT_EXPIRY_SECONDS: 300,
  /** Maximum token expiration in seconds (1 hour) */
  MAX_EXPIRY_SECONDS: 3600,
  /** Minimum token expiration in seconds (30 seconds) */
  MIN_EXPIRY_SECONDS: 30,
  /** Token issuer */
  ISSUER: 'stix',
  /** Token type */
  TYPE: 'JWT',
  /** Supported algorithms */
  ALGORITHMS: ['EdDSA', 'ES256'] as const,
} as const;

/** HTTP headers */
export const HEADERS = {
  /** STIX proof token header */
  STIX_PROOF: 'X-STIX-Proof',
  /** STIX trace ID header */
  STIX_TRACE: 'X-STIX-Trace',
  /** Request ID header */
  REQUEST_ID: 'X-Request-ID',
  /** Correlation ID header */
  CORRELATION_ID: 'X-Correlation-ID',
  /** Tenant ID header */
  TENANT_ID: 'X-Tenant-ID',
  /** Client ID header */
  CLIENT_ID: 'X-Client-ID',
  /** API key header */
  API_KEY: 'X-API-Key',
  /** mTLS client certificate header */
  CLIENT_CERT: 'X-Client-Cert',
} as const;

// =============================================================================
// RATE LIMITING
// =============================================================================

/** Rate limit configuration */
export const RATE_LIMITS = {
  /** Requests per second for authorization */
  AUTHORIZE_RPS: 1000,
  /** Requests per second for evidence queries */
  EVIDENCE_QUERY_RPS: 100,
  /** Requests per second for policy updates */
  POLICY_UPDATE_RPS: 10,
  /** Burst multiplier */
  BURST_MULTIPLIER: 2,
  /** Window size in milliseconds */
  WINDOW_MS: 1000,
} as const;

// =============================================================================
// TIMEOUTS
// =============================================================================

/** Timeout configuration in milliseconds */
export const TIMEOUTS = {
  /** Service request timeout */
  SERVICE_REQUEST: 5000,
  /** Policy evaluation timeout */
  POLICY_EVALUATION: 2000,
  /** Evidence write timeout */
  EVIDENCE_WRITE: 3000,
  /** Approval operation timeout */
  APPROVAL_OPERATION: 5000,
  /** Database connection timeout */
  DATABASE_CONNECTION: 10000,
  /** Database query timeout */
  DATABASE_QUERY: 5000,
  /** Cache operation timeout */
  CACHE_OPERATION: 1000,
  /** Graceful shutdown timeout */
  GRACEFUL_SHUTDOWN: 30000,
} as const;

// =============================================================================
// RETRY CONFIGURATION
// =============================================================================

/** Retry configuration */
export const RETRY_CONFIG = {
  /** Maximum retry attempts */
  MAX_ATTEMPTS: 3,
  /** Initial delay in milliseconds */
  INITIAL_DELAY_MS: 100,
  /** Maximum delay in milliseconds */
  MAX_DELAY_MS: 5000,
  /** Backoff factor */
  BACKOFF_FACTOR: 2,
  /** Jitter factor (0-1) */
  JITTER_FACTOR: 0.1,
} as const;

// =============================================================================
// PAGINATION
// =============================================================================

/** Pagination defaults */
export const PAGINATION = {
  /** Default page size */
  DEFAULT_LIMIT: 20,
  /** Maximum page size */
  MAX_LIMIT: 100,
  /** Minimum page size */
  MIN_LIMIT: 1,
  /** Default page number */
  DEFAULT_PAGE: 1,
} as const;

// =============================================================================
// EVIDENCE CONFIGURATION
// =============================================================================

/** Evidence configuration */
export const EVIDENCE_CONFIG = {
  /** Schema version */
  SCHEMA_VERSION: '1.0' as const,
  /** Hash algorithm */
  HASH_ALGORITHM: 'sha256',
  /** Signature algorithm */
  SIGNATURE_ALGORITHM: 'Ed25519',
  /** Maximum batch size for evidence writes */
  MAX_BATCH_SIZE: 100,
  /** Retention period in days */
  DEFAULT_RETENTION_DAYS: 2555, // 7 years
  /** Archive after days */
  ARCHIVE_AFTER_DAYS: 365,
} as const;

// =============================================================================
// APPROVAL CONFIGURATION
// =============================================================================

/** Approval configuration */
export const APPROVAL_CONFIG = {
  /** Default timeout in hours */
  DEFAULT_TIMEOUT_HOURS: 24,
  /** Maximum timeout in hours */
  MAX_TIMEOUT_HOURS: 168, // 7 days
  /** Minimum timeout in hours */
  MIN_TIMEOUT_HOURS: 1,
  /** Default required approvers */
  DEFAULT_REQUIRED_APPROVERS: 1,
  /** Maximum required approvers */
  MAX_REQUIRED_APPROVERS: 5,
} as const;

// =============================================================================
// POLICY CONFIGURATION
// =============================================================================

/** Policy configuration */
export const POLICY_CONFIG = {
  /** Default priority (lower = higher priority) */
  DEFAULT_PRIORITY: 100,
  /** Minimum priority */
  MIN_PRIORITY: 0,
  /** Maximum priority */
  MAX_PRIORITY: 1000,
  /** Cache TTL in seconds */
  CACHE_TTL_SECONDS: 60,
  /** Maximum policies per tenant */
  MAX_POLICIES_PER_TENANT: 1000,
} as const;

// =============================================================================
// COMPLIANCE FRAMEWORKS
// =============================================================================

/** Control framework identifiers */
export const CONTROL_FRAMEWORKS = {
  SOC2: 'SOC2',
  HIPAA: 'HIPAA',
  GDPR: 'GDPR',
  PCI_DSS: 'PCI-DSS',
  ISO27001: 'ISO27001',
  NIST: 'NIST',
  FedRAMP: 'FedRAMP',
  CCPA: 'CCPA',
} as const;

/** Common control mappings */
export const CONTROL_MAPPINGS = {
  ACCESS_CONTROL: {
    SOC2: ['CC6.1', 'CC6.2', 'CC6.3'],
    HIPAA: ['164.312(a)(1)', '164.312(d)'],
    PCI_DSS: ['7.1', '7.2', '7.3'],
    ISO27001: ['A.9.1', 'A.9.2', 'A.9.4'],
    NIST: ['AC-1', 'AC-2', 'AC-3'],
  },
  AUDIT_LOGGING: {
    SOC2: ['CC7.1', 'CC7.2'],
    HIPAA: ['164.312(b)'],
    PCI_DSS: ['10.1', '10.2', '10.3'],
    ISO27001: ['A.12.4'],
    NIST: ['AU-1', 'AU-2', 'AU-3'],
  },
  DATA_PROTECTION: {
    SOC2: ['CC6.6', 'CC6.7'],
    HIPAA: ['164.312(e)(1)', '164.312(e)(2)'],
    PCI_DSS: ['3.1', '3.2', '3.4'],
    GDPR: ['Art.32'],
    ISO27001: ['A.8.2', 'A.10.1'],
  },
} as const;

// =============================================================================
// ERROR CODES
// =============================================================================

/** STIX error codes */
export const ERROR_CODES = {
  // Authorization errors (1xxx)
  AUTHORIZATION_DENIED: 'STIX1001',
  AUTHORIZATION_QUARANTINED: 'STIX1002',
  AUTHORIZATION_TIMEOUT: 'STIX1003',
  
  // Authentication errors (2xxx)
  AUTHENTICATION_REQUIRED: 'STIX2001',
  INVALID_TOKEN: 'STIX2002',
  TOKEN_EXPIRED: 'STIX2003',
  MISSING_TOKEN: 'STIX2004',
  INVALID_SIGNATURE: 'STIX2005',
  
  // Policy errors (3xxx)
  POLICY_NOT_FOUND: 'STIX3001',
  POLICY_VALIDATION_ERROR: 'STIX3002',
  POLICY_CONFLICT: 'STIX3003',
  NO_MATCHING_POLICY: 'STIX3004',
  
  // Evidence errors (4xxx)
  EVIDENCE_NOT_FOUND: 'STIX4001',
  EVIDENCE_INTEGRITY_ERROR: 'STIX4002',
  EVIDENCE_WRITE_ERROR: 'STIX4003',
  HASH_CHAIN_ERROR: 'STIX4004',
  
  // Approval errors (5xxx)
  APPROVAL_NOT_FOUND: 'STIX5001',
  APPROVAL_EXPIRED: 'STIX5002',
  APPROVAL_ALREADY_PROCESSED: 'STIX5003',
  INSUFFICIENT_APPROVAL: 'STIX5004',
  
  // Validation errors (6xxx)
  VALIDATION_ERROR: 'STIX6001',
  INVALID_REQUEST: 'STIX6002',
  MISSING_REQUIRED_FIELD: 'STIX6003',
  INVALID_FORMAT: 'STIX6004',
  
  // Service errors (9xxx)
  SERVICE_UNAVAILABLE: 'STIX9001',
  SERVICE_TIMEOUT: 'STIX9002',
  INTERNAL_ERROR: 'STIX9003',
  CONFIGURATION_ERROR: 'STIX9004',
  RATE_LIMIT_EXCEEDED: 'STIX9005',
} as const;

// =============================================================================
// REASON CODES
// =============================================================================

/** Standard reason codes for decisions */
export const REASON_CODES = {
  // ALLOW reasons
  POLICY_ALLOW: 'POLICY_ALLOW',
  APPROVAL_GRANTED: 'APPROVAL_GRANTED',
  LOW_RISK_ALLOWED: 'LOW_RISK_ALLOWED',
  TENANT_OVERRIDE: 'TENANT_OVERRIDE',
  
  // DENY reasons
  POLICY_DENY: 'POLICY_DENY',
  UNAUTHORIZED_ACTOR: 'UNAUTHORIZED_ACTOR',
  UNAUTHORIZED_RESOURCE: 'UNAUTHORIZED_RESOURCE',
  CLASSIFICATION_VIOLATION: 'CLASSIFICATION_VIOLATION',
  ENVIRONMENT_RESTRICTION: 'ENVIRONMENT_RESTRICTION',
  RATE_LIMIT_EXCEEDED: 'RATE_LIMIT_EXCEEDED',
  
  // QUARANTINE reasons
  REQUIRES_APPROVAL: 'REQUIRES_APPROVAL',
  HIGH_RISK_ACTION: 'HIGH_RISK_ACTION',
  SENSITIVE_DATA_ACCESS: 'SENSITIVE_DATA_ACCESS',
  PII_DETECTED: 'PII_DETECTED',
  CROSS_TENANT_ACCESS: 'CROSS_TENANT_ACCESS',
  
  // Default
  DEFAULT_DENY: 'DEFAULT_DENY',
  NO_MATCHING_POLICY: 'NO_MATCHING_POLICY',
} as const;

// =============================================================================
// RISK CLASSIFICATION
// =============================================================================

/** Risk tier thresholds */
export const RISK_THRESHOLDS = {
  LOW: { maxScore: 25 },
  MEDIUM: { maxScore: 50 },
  HIGH: { maxScore: 75 },
  CRITICAL: { maxScore: 100 },
} as const;

/** Default risk tiers for common tools */
export const DEFAULT_TOOL_RISK_TIERS = {
  // Low risk
  'read_file': 'LOW',
  'list_directory': 'LOW',
  'search': 'LOW',
  'get_status': 'LOW',
  
  // Medium risk
  'write_file': 'MEDIUM',
  'update_record': 'MEDIUM',
  'send_notification': 'MEDIUM',
  'query_database': 'MEDIUM',
  
  // High risk
  'delete_file': 'HIGH',
  'execute_command': 'HIGH',
  'modify_permissions': 'HIGH',
  'access_secrets': 'HIGH',
  
  // Critical risk
  'delete_database': 'CRITICAL',
  'modify_security_settings': 'CRITICAL',
  'access_production_data': 'CRITICAL',
  'deploy_infrastructure': 'CRITICAL',
} as const;

// =============================================================================
// ENVIRONMENT CONFIGURATION
// =============================================================================

/** Environment-specific settings */
export const ENVIRONMENT_CONFIG = {
  dev: {
    strictMode: false,
    debugLogging: true,
    mockServices: true,
    skipValidation: false,
  },
  test: {
    strictMode: true,
    debugLogging: true,
    mockServices: true,
    skipValidation: false,
  },
  stage: {
    strictMode: true,
    debugLogging: false,
    mockServices: false,
    skipValidation: false,
  },
  prod: {
    strictMode: true,
    debugLogging: false,
    mockServices: false,
    skipValidation: false,
  },
} as const;

// =============================================================================
// METRIC NAMES
// =============================================================================

/** Prometheus metric names */
export const METRICS = {
  // Counters
  AUTHORIZE_REQUESTS_TOTAL: 'stix_authorize_requests_total',
  AUTHORIZE_DECISIONS_TOTAL: 'stix_authorize_decisions_total',
  EVIDENCE_EVENTS_TOTAL: 'stix_evidence_events_total',
  APPROVAL_REQUESTS_TOTAL: 'stix_approval_requests_total',
  ERRORS_TOTAL: 'stix_errors_total',
  
  // Histograms
  AUTHORIZE_DURATION_SECONDS: 'stix_authorize_duration_seconds',
  EVIDENCE_WRITE_DURATION_SECONDS: 'stix_evidence_write_duration_seconds',
  POLICY_EVALUATION_DURATION_SECONDS: 'stix_policy_evaluation_duration_seconds',
  
  // Gauges
  ACTIVE_CONNECTIONS: 'stix_active_connections',
  POLICY_COUNT: 'stix_policy_count',
  PENDING_APPROVALS: 'stix_pending_approvals',
  CACHE_SIZE: 'stix_cache_size',
} as const;

// =============================================================================
// LOG LEVELS
// =============================================================================

/** Log levels */
export const LOG_LEVELS = {
  error: 0,
  warn: 1,
  info: 2,
  http: 3,
  debug: 4,
  trace: 5,
} as const;

/** Log level priority (lower = higher priority) - same as LOG_LEVELS */
export const LOG_LEVEL_PRIORITY = LOG_LEVELS;
