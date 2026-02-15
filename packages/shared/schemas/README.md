# STIX JSON Schemas

This directory contains JSON Schema definitions for the STIX policy enforcement system.

## Schemas

| Schema | Description |
|--------|-------------|
| `AuthorizeRequest.json` | Request to authorize an action |
| `AuthorizeResponse.json` | Response from the policy engine |
| `EvidenceEvent.json` | Immutable evidence event in the audit chain |
| `PolicyArtifact.json` | Policy definition artifact |
| `ApprovalTicket.json` | Approval workflow ticket |

## Usage

### Validation

Use any JSON Schema validator to validate STIX messages:

```typescript
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import schema from './AuthorizeRequest.json';

const ajv = new Ajv();
addFormats(ajv);
const validate = ajv.compile(schema);

const request = {
  actor: { id: 'user-123', type: 'HUMAN' },
  action: 'read',
  resource: { type: 'patient_record' },
  context: { env: 'prod' }
};

if (validate(request)) {
  console.log('Valid request');
} else {
  console.log('Validation errors:', validate.errors);
}
```

### Code Generation

Generate TypeScript types from schemas:

```bash
npx json-schema-to-typescript AuthorizeRequest.json > AuthorizeRequest.d.ts
```

### API Documentation

Reference schemas in OpenAPI specifications:

```yaml
components:
  schemas:
    AuthorizeRequest:
      $ref: 'https://stix.dev/schemas/AuthorizeRequest.json'
```

## Generating Schemas

Schemas can be regenerated from Zod validators:

```bash
cd packages/shared/schemas
npx tsx generate.ts
```

This requires `zod-to-json-schema` to be installed:

```bash
pnpm add -D zod-to-json-schema
```

## Schema Versioning

All schemas include a `$id` field with the canonical URL:

- `https://stix.dev/schemas/AuthorizeRequest.json`
- `https://stix.dev/schemas/AuthorizeResponse.json`
- etc.

The `schema_version` field in `EvidenceEvent` tracks the evidence format version independently.
