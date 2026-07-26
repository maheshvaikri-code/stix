/**
 * STIX Validators
 * Zod schemas for runtime validation across all STIX services
 * 
 * @module @stix/shared/validators
 */

import { z } from 'zod';

// =============================================================================
// BASE SCHEMAS
// =============================================================================

/** UUID v4 pattern */
export const UuidSchema = z.string().uuid();

/** Trace ID pattern: stix_{uuid} */
export const TraceIdSchema = z.string().regex(
  /^stix_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/,
  'Invalid trace ID format'
);

/** Event ID pattern: evt_{uuid} */
export const EventIdSchema = z.string().regex(
  /^evt_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/,
  'Invalid event ID format'
);

/** Approval ticket ID pattern: appr_{uuid} */
export const ApprovalTicketIdSchema = z.string().regex(
  /^appr_[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/,
  'Invalid approval ticket ID format'
);

/** SHA-256 hash pattern */
export const HashSchema = z.string().regex(
  /^sha256:[a-f0-9]{64}$/,
  'Invalid hash format'
);

/** ISO-8601 timestamp */
export const TimestampSchema = z.string().datetime();

/** Semantic version */
export const SemverSchema = z.string().regex(
  /^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$/,
  'Invalid semantic version'
);

// =============================================================================
// ENUM SCHEMAS
// =============================================================================

/** Decision kinds */
export const DecisionKindSchema = z.enum(['ALLOW', 'DENY', 'QUARANTINE']);

/** Actor types */
export const ActorTypeSchema = z.enum(['HUMAN', 'SERVICE', 'AI_AGENT', 'JOB', 'SYSTEM']);

/** Actor type filter (allows wildcard '*') */
export const ActorTypeFilterSchema = z.union([
  ActorTypeSchema,
  z.literal('*'),
]);

/** Environments */
export const EnvironmentSchema = z.preprocess((value) => {
  if (typeof value !== 'string') return value;
  const normalized = value.trim().toLowerCase();
  return normalized === 'production' ? 'prod' : normalized;
}, z.enum(['dev', 'test', 'stage', 'prod']));

/** Risk tiers */
export const RiskTierSchema = z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']);

/** Schema versions */
export const SchemaVersionSchema = z.enum(['1.0']);

/** Obligation types */
export const ObligationTypeSchema = z.enum([
  'REDACT_FIELDS',
  'MASK_PII',
  'WATERMARK_OUTPUT',
  'REQUIRE_APPROVAL',
  'RATE_LIMIT',
  'LOG_LEVEL',
  'ENCRYPT_TRANSIT',
  'DUAL_CONTROL',
  'TIME_LIMIT',
  'NOTIFY',
  'AUDIT_LOG',
  'DATA_FORMAT',
  'DATA_MASK',
  'NOTIFY_DPO',
  'NOTIFY_SERVICE_PROVIDERS',
  'PROVIDE_EXPLANATION',
  'RESPOND_WITHIN',
  'STOP_PROCESSING',
]);

/** Outcome statuses */
export const OutcomeStatusSchema = z.enum(['SUCCESS', 'FAILED', 'SKIPPED', 'PENDING']);

/** Fail modes */
export const FailModeSchema = z.enum(['CLOSED', 'OPEN_LOW_RISK_ONLY', 'OPEN']);

// =============================================================================
// CORE OBJECT SCHEMAS
// =============================================================================

/** Actor schema */
export const ActorSchema = z.object({
  id: z.string().min(1).max(255),
  type: ActorTypeSchema,
  role: z.string().max(255).optional(),
  tenant: z.string().max(255).optional(),
  attributes: z.record(z.unknown()).optional(),
});

/** Resource schema */
export const ResourceSchema = z.object({
  type: z.string().min(1).max(255),
  id: z.string().max(1024).optional(),
  classification: z.array(z.string().max(64)).optional(),
  attributes: z.record(z.unknown()).optional(),
});

/** Detection signals schema */
export const DetectionSignalsSchema = z.object({
  piiDetected: z.boolean().optional(),
  phiDetected: z.boolean().optional(),
  pciDetected: z.boolean().optional(),
  secretsDetected: z.boolean().optional(),
  custom: z.record(z.boolean()).optional(),
});

/** Context schema */
export const ContextSchema = z.object({
  env: EnvironmentSchema,
  purpose: z.string().max(1024).optional(),
  run_id: z.string().max(255).optional(),
  session_id: z.string().max(255).optional(),
  ticket_id: z.string().max(255).optional(),
  jurisdiction: z.string().max(64).optional(),
  tags: z.array(z.string().max(64)).optional(),
  signals: DetectionSignalsSchema.optional(),
  attributes: z.record(z.unknown()).optional(),
});

/** Tool call schema */
export const ToolCallSchema = z.object({
  tool: z.string().min(1).max(255),
  risk_tier: RiskTierSchema.optional(),
  args_summary: z.string().max(2048).optional(),
  args_hash: HashSchema.optional(),
});

/** Obligation schema */
export const ObligationSchema = z.object({
  type: ObligationTypeSchema,
  params: z.record(z.unknown()).optional(),
});

/** Approval info schema */
export const ApprovalInfoSchema = z.object({
  required: z.boolean(),
  ticket_id: ApprovalTicketIdSchema.optional(),
  approver_role: z.string().max(255).optional(),
  require_count: z.number().int().min(1).max(10).optional(),
  require_justification: z.boolean().optional(),
  expires_at: TimestampSchema.optional(),
});

/** Policy reference schema */
export const PolicyRefSchema = z.object({
  id: z.string().min(1).max(255),
  version: SemverSchema,
  hash: HashSchema,
});

// =============================================================================
// REQUEST SCHEMAS
// =============================================================================

/** Authorization request schema */
export const AuthorizeRequestSchema = z.object({
  actor: ActorSchema,
  action_id: z.string().min(1).max(255).optional(),
  action: z.string().min(1).max(255),
  resource: ResourceSchema,
  context: ContextSchema,
  tool_call: ToolCallSchema.optional(),
  approval_ref: ApprovalTicketIdSchema.optional(),
});

/** Outcome request schema */
export const OutcomeRequestSchema = z.object({
  trace_id: TraceIdSchema,
  status: OutcomeStatusSchema,
  result_summary: z.string().max(4096).optional(),
  error_class: z.string().max(255).optional(),
  obligations_applied: z.record(z.boolean()).optional(),
  actor: ActorSchema.optional(),
  action: z.object({
    name: z.string().min(1).max(255),
    tool: z.string().max(255).optional(),
    risk_tier: RiskTierSchema.optional(),
  }).optional(),
  resource: ResourceSchema.optional(),
  context: ContextSchema.optional(),
  policy: PolicyRefSchema.optional(),
});

// =============================================================================
// RESPONSE SCHEMAS
// =============================================================================

/** Authorization response schema */
export const AuthorizeResponseSchema = z.object({
  decision: DecisionKindSchema,
  reason_code: z.string().min(1).max(64),
  trace_id: TraceIdSchema,
  action_id: z.string().min(1).max(255).optional(),
  explanation: z.string().max(2048).optional(),
  policy: PolicyRefSchema,
  obligations: z.array(ObligationSchema),
  approval: ApprovalInfoSchema.nullable(),
  proof_token: z.string().optional(),
  controls: z.array(z.string().max(64)).optional(),
  regulations: z.array(z.string().max(64)).optional(),
});

// =============================================================================
// EVIDENCE SCHEMAS
// =============================================================================

/** Integrity block schema */
export const IntegrityBlockSchema = z.object({
  event_hash: HashSchema,
  prev_hash: HashSchema,
  signature: z.string().min(1).max(512),
  key_id: z.string().min(1).max(255),
});

/** Outcome info schema */
export const OutcomeInfoSchema = z.object({
  status: OutcomeStatusSchema.optional(),
  result_summary: z.string().max(4096).optional(),
  error_class: z.string().max(255).optional(),
});

/** Obligations applied schema */
export const ObligationsAppliedSchema = z.object({
  redaction: z.boolean().optional(),
  watermark: z.boolean().optional(),
  rate_limit: z.boolean().optional(),
  pii_masked: z.boolean().optional(),
});

/** Action meta schema */
export const ActionMetaSchema = z.object({
  name: z.string().min(1).max(255),
  tool: z.string().max(255).optional(),
  risk_tier: RiskTierSchema.optional(),
});

/** Evidence event schema */
export const EvidenceEventSchema = z.object({
  schema_version: SchemaVersionSchema,
  event_id: EventIdSchema,
  trace_id: TraceIdSchema,
  timestamp: TimestampSchema,
  
  decision: DecisionKindSchema,
  reason_code: z.string().min(1).max(64),
  
  actor: ActorSchema,
  action: ActionMetaSchema,
  resource: ResourceSchema,
  context: ContextSchema,
  
  policy: PolicyRefSchema,
  
  controls: z.array(z.string().max(64)),
  regulations: z.array(z.string().max(64)),
  
  obligations_applied: ObligationsAppliedSchema.optional(),
  outcome: OutcomeInfoSchema.optional(),
  
  integrity: IntegrityBlockSchema,
});

// =============================================================================
// POLICY SCHEMAS
// =============================================================================

/** Policy scope schema - supports wildcards */
export const PolicyScopeSchema = z.object({
  actor_type: ActorTypeFilterSchema,
  action: z.string().min(1).max(255),
  resource_type: z.string().min(1).max(255),
  environments: z.array(EnvironmentSchema).optional(),
  classifications: z.array(z.string().min(1).max(255)).optional(),
});

/** Policy conditions schema */
export const PolicyConditionsSchema = z.object({
  env: EnvironmentSchema.optional(),
  require_signal: DetectionSignalsSchema.partial().optional(),
  require_resource_attr: z.record(z.unknown()).optional(),
  require_actor_attr: z.record(z.unknown()).optional(),
  require_tenant_match: z.boolean().optional(),
  custom: z.record(z.unknown()).optional(),
});

/** Policy approval config schema */
export const PolicyApprovalConfigSchema = z.object({
  approver_role: z.string().max(255).optional(),
  require_count: z.number().int().min(1).max(10).optional(),
  require_ticket: z.boolean().optional(),
  require_justification: z.boolean().optional(),
  timeout_hours: z.number().int().min(1).max(168).optional(),
});

/** Policy artifact schema */
export const PolicyArtifactSchema = z.object({
  policy_id: z.string().min(1).max(255),
  version: SemverSchema,
  priority: z.number().int().min(0).max(1000).optional(),
  description: z.string().max(2048).optional(),
  scope: PolicyScopeSchema,
  conditions: PolicyConditionsSchema.optional(),
  decision: DecisionKindSchema,
  reason_code: z.string().min(1).max(64),
  obligations: z.array(ObligationSchema).optional(),
  approval: PolicyApprovalConfigSchema.optional(),
  controls: z.array(z.string().max(64)).optional(),
  regulations: z.array(z.string().max(64)).optional(),
  tags: z.array(z.string().max(64)).optional(),
  active: z.boolean().optional(),
  created_at: TimestampSchema.optional(),
  updated_at: TimestampSchema.optional(),
});

// =============================================================================
// APPROVAL SCHEMAS
// =============================================================================

/** Approval status */
export const ApprovalStatusSchema = z.enum(['PENDING', 'APPROVED', 'REJECTED', 'EXPIRED', 'CANCELLED']);

/** Approval decision */
export const ApprovalDecisionSchema = z.object({
  approver_id: z.string().min(1).max(255),
  approver_role: z.string().max(255).optional(),
  decision: z.enum(['APPROVE', 'REJECT']),
  justification: z.string().max(4096).optional(),
  timestamp: TimestampSchema,
});

/** Approval ticket schema */
export const ApprovalTicketSchema = z.object({
  ticket_id: ApprovalTicketIdSchema,
  trace_id: TraceIdSchema,
  status: ApprovalStatusSchema,
  
  actor: ActorSchema,
  action: z.string().min(1).max(255),
  resource: ResourceSchema,
  context: ContextSchema,
  
  required_count: z.number().int().min(1).max(10),
  required_role: z.string().max(255).optional(),
  require_justification: z.boolean(),
  
  decisions: z.array(ApprovalDecisionSchema),
  
  created_at: TimestampSchema,
  expires_at: TimestampSchema,
  resolved_at: TimestampSchema.optional(),
});

// =============================================================================
// API SCHEMAS
// =============================================================================

/** Pagination params schema */
export const PaginationParamsSchema = z.object({
  page: z.number().int().min(1).optional(),
  limit: z.number().int().min(1).max(100).optional(),
  sort_by: z.string().max(64).optional(),
  sort_order: z.enum(['asc', 'desc']).optional(),
});

/** API error schema */
export const ApiErrorSchema = z.object({
  code: z.string().min(1).max(64),
  message: z.string().min(1).max(2048),
  details: z.unknown().optional(),
});

/** Health check response schema */
export const HealthResponseSchema = z.object({
  status: z.enum(['healthy', 'degraded', 'unhealthy']),
  version: z.string(),
  service: z.string(),
  uptime: z.number(),
  timestamp: TimestampSchema,
  checks: z.record(z.object({
    status: z.enum(['pass', 'fail', 'warn']),
    message: z.string().optional(),
    duration_ms: z.number().optional(),
  })).optional(),
});

// =============================================================================
// TOKEN SCHEMAS
// =============================================================================

/** Proof token header schema */
export const ProofTokenHeaderSchema = z.object({
  alg: z.enum(['EdDSA', 'ES256']),
  typ: z.literal('JWT'),
  kid: z.string().min(1).max(255),
});

/** Proof token claims schema */
export const ProofTokenClaimsSchema = z.object({
  iss: z.literal('stix'),
  sub: z.string().min(1).max(255),
  act: z.string().min(1).max(255),
  res: z.string().min(1).max(255),
  cls: z.array(z.string().max(64)),
  pol: HashSchema,
  tid: TraceIdSchema,
  iat: z.number().int().positive(),
  exp: z.number().int().positive(),
  replay_id: z.string().min(1).max(255).optional(),
  jti: z.string().min(1).max(255).optional(),
  request_hash: HashSchema.optional(),
  arguments_hash: HashSchema.optional(),
  action_id: z.string().min(1).max(255).optional(),
  resource_id: z.string().max(1024).optional(),
  approval_ref: ApprovalTicketIdSchema.optional(),
  decision: DecisionKindSchema.optional(),
  reason_code: z.string().max(64).optional(),
  policy_id: z.string().max(255).optional(),
  policy_version: SemverSchema.optional(),
  policy_hash: HashSchema.optional(),
  pack_hash: HashSchema.optional(),
  actor_id: z.string().max(255).optional(),
  actor_type: ActorTypeSchema.optional(),
  actor_role: z.string().max(255).optional(),
  actor_tenant: z.string().max(255).optional(),
  action: z.string().max(255).optional(),
  resource_type: z.string().max(255).optional(),
  risk_tier: RiskTierSchema.optional(),
  obligations: z.string().max(16384).optional(),
});

// =============================================================================
// UTILITY TYPES
// =============================================================================

export type Actor = z.infer<typeof ActorSchema>;
export type Resource = z.infer<typeof ResourceSchema>;
export type Context = z.infer<typeof ContextSchema>;
export type ToolCall = z.infer<typeof ToolCallSchema>;
export type Obligation = z.infer<typeof ObligationSchema>;
export type ApprovalInfo = z.infer<typeof ApprovalInfoSchema>;
export type PolicyRef = z.infer<typeof PolicyRefSchema>;
export type AuthorizeRequest = z.infer<typeof AuthorizeRequestSchema>;
export type AuthorizeResponse = z.infer<typeof AuthorizeResponseSchema>;
export type OutcomeRequest = z.infer<typeof OutcomeRequestSchema>;
export type EvidenceEvent = z.infer<typeof EvidenceEventSchema>;
export type PolicyArtifact = z.infer<typeof PolicyArtifactSchema>;
export type ApprovalTicket = z.infer<typeof ApprovalTicketSchema>;
export type HealthResponse = z.infer<typeof HealthResponseSchema>;

// =============================================================================
// VALIDATION HELPERS
// =============================================================================

/**
 * Validate authorization request
 */
export function validateAuthorizeRequest(data: unknown): AuthorizeRequest {
  return AuthorizeRequestSchema.parse(data);
}

/**
 * Validate outcome request
 */
export function validateOutcomeRequest(data: unknown): OutcomeRequest {
  return OutcomeRequestSchema.parse(data);
}

/**
 * Validate policy artifact
 */
export function validatePolicyArtifact(data: unknown): PolicyArtifact {
  return PolicyArtifactSchema.parse(data);
}

/**
 * Validate evidence event
 */
export function validateEvidenceEvent(data: unknown): EvidenceEvent {
  return EvidenceEventSchema.parse(data);
}

/**
 * Safe parse with result
 */
export function safeParse<T>(
  schema: z.ZodSchema<T>,
  data: unknown
): { success: true; data: T } | { success: false; errors: z.ZodError } {
  const result = schema.safeParse(data);
  if (result.success) {
    return { success: true, data: result.data };
  }
  return { success: false, errors: result.error };
}

/**
 * Format Zod errors for API response
 */
export function formatZodErrors(error: z.ZodError): Array<{ field: string; message: string }> {
  return error.errors.map(err => ({
    field: err.path.join('.'),
    message: err.message,
  }));
}
