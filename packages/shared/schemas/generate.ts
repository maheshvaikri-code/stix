#!/usr/bin/env tsx
/**
 * Generate JSON Schema files from Zod schemas
 * Run with: npx tsx generate.ts
 */

import * as fs from 'fs';
import * as path from 'path';
import { zodToJsonSchema } from 'zod-to-json-schema';

import {
  // Base schemas
  TraceIdSchema,
  EventIdSchema,
  ApprovalTicketIdSchema,
  HashSchema,

  // Enum schemas
  DecisionKindSchema,
  ActorTypeSchema,
  EnvironmentSchema,
  RiskTierSchema,
  ObligationTypeSchema,
  OutcomeStatusSchema,

  // Core object schemas
  ActorSchema,
  ResourceSchema,
  ContextSchema,
  ToolCallSchema,
  ObligationSchema,
  ApprovalInfoSchema,
  PolicyRefSchema,

  // Request/Response schemas
  AuthorizeRequestSchema,
  AuthorizeResponseSchema,
  OutcomeRequestSchema,

  // Evidence schemas
  EvidenceEventSchema,
  IntegrityBlockSchema,

  // Policy schemas
  PolicyArtifactSchema,
  PolicyScopeSchema,
  PolicyConditionsSchema,

  // Approval schemas
  ApprovalTicketSchema,
  ApprovalDecisionSchema,
  ApprovalStatusSchema,

  // API schemas
  HealthResponseSchema,
  ApiErrorSchema,

  // Token schemas
  ProofTokenClaimsSchema,
  ProofTokenHeaderSchema,
} from '../src/validators/index.js';

const outDir = __dirname;

// Schema definitions to generate
const schemas = [
  // Core types
  { name: 'Actor', schema: ActorSchema },
  { name: 'Resource', schema: ResourceSchema },
  { name: 'Context', schema: ContextSchema },
  { name: 'ToolCall', schema: ToolCallSchema },
  { name: 'Obligation', schema: ObligationSchema },
  { name: 'ApprovalInfo', schema: ApprovalInfoSchema },
  { name: 'PolicyRef', schema: PolicyRefSchema },

  // Request/Response
  { name: 'AuthorizeRequest', schema: AuthorizeRequestSchema },
  { name: 'AuthorizeResponse', schema: AuthorizeResponseSchema },
  { name: 'OutcomeRequest', schema: OutcomeRequestSchema },

  // Evidence
  { name: 'EvidenceEvent', schema: EvidenceEventSchema },
  { name: 'IntegrityBlock', schema: IntegrityBlockSchema },

  // Policy
  { name: 'PolicyArtifact', schema: PolicyArtifactSchema },
  { name: 'PolicyScope', schema: PolicyScopeSchema },
  { name: 'PolicyConditions', schema: PolicyConditionsSchema },

  // Approval
  { name: 'ApprovalTicket', schema: ApprovalTicketSchema },
  { name: 'ApprovalDecision', schema: ApprovalDecisionSchema },

  // API
  { name: 'HealthResponse', schema: HealthResponseSchema },
  { name: 'ApiError', schema: ApiErrorSchema },

  // Token
  { name: 'ProofTokenClaims', schema: ProofTokenClaimsSchema },
  { name: 'ProofTokenHeader', schema: ProofTokenHeaderSchema },

  // Enums
  { name: 'DecisionKind', schema: DecisionKindSchema },
  { name: 'ActorType', schema: ActorTypeSchema },
  { name: 'Environment', schema: EnvironmentSchema },
  { name: 'RiskTier', schema: RiskTierSchema },
  { name: 'ObligationType', schema: ObligationTypeSchema },
  { name: 'OutcomeStatus', schema: OutcomeStatusSchema },
  { name: 'ApprovalStatus', schema: ApprovalStatusSchema },
];

// Generate each schema
for (const { name, schema } of schemas) {
  const jsonSchema = zodToJsonSchema(schema, {
    name,
    $refStrategy: 'none',
  });

  // Add metadata
  (jsonSchema as any).$id = `https://stix.dev/schemas/${name}.json`;
  (jsonSchema as any).$schema = 'https://json-schema.org/draft/2020-12/schema';

  const filename = `${name}.json`;
  const filepath = path.join(outDir, filename);

  fs.writeFileSync(filepath, JSON.stringify(jsonSchema, null, 2));
  console.log(`Generated: ${filename}`);
}

// Generate combined schema with all definitions
const combinedSchema = {
  $schema: 'https://json-schema.org/draft/2020-12/schema',
  $id: 'https://stix.dev/schemas/stix.json',
  title: 'STIX Schema',
  description: 'Complete schema definitions for the STIX policy enforcement system',
  $defs: {} as Record<string, any>,
};

for (const { name, schema } of schemas) {
  const jsonSchema = zodToJsonSchema(schema, {
    name,
    $refStrategy: 'none',
  });

  // Remove wrapper properties from zodToJsonSchema
  const def = (jsonSchema as any).definitions?.[name] || jsonSchema;
  delete def.$schema;
  delete def.$id;

  combinedSchema.$defs[name] = def;
}

fs.writeFileSync(
  path.join(outDir, 'stix.json'),
  JSON.stringify(combinedSchema, null, 2)
);
console.log('Generated: stix.json (combined)');

console.log(`\nGenerated ${schemas.length + 1} schema files`);
