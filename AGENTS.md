# STIX - Agent Context

This file provides context for AI agents (GitLab Duo, Claude, etc.) operating within this repository.

## Project Overview

STIX (Shield, Trust & Integrity eXecution) is a compliance enforcement platform for AI agents. It evaluates every agent action against YAML policy packs, returns a decision (ALLOW/DENY/QUARANTINE), and records the decision in a tamper-evident audit trail with Ed25519 cryptographic signatures.

## Architecture

- **Enforcer** (`services/enforcer/`, port 3001) - Policy evaluation engine, generates Ed25519 proof tokens
- **Policy** (`services/policy/`, port 3002) - YAML policy pack management (HIPAA, SOX, PCI-DSS)
- **Evidence** (`services/evidence/`, port 3003) - SHA-256 hash-chained, Ed25519-signed audit trail
- **Approvals** (`services/approvals/`, port 3004) - Human-in-the-loop approval workflows
- **Dashboard** (`dashboard/`, port 3100) - Next.js real-time compliance monitoring

## Key Packages

- `packages/shared/` - Shared types, crypto primitives, policy schemas
- `packages/agent-sdk/` - SDK for wrapping AI agent tools with STIX enforcement
- `packages/agent-sdk/src/integrations/gitlab.ts` - GitLab event normalizer, diff scanner, decision mapper
- `packages/agent-sdk/src/reasoning/compliance-analyzer.ts` - Claude-powered compliance reasoning

## Policy Packs

Located in `policies/`:
- `policies/examples/hipaa-healthcare.yaml` - HIPAA compliance rules
- `policies/examples/financial-sox-pci.yaml` - SOX/PCI-DSS compliance rules
- `policies/default/base-policies.yaml` - Default baseline policies

## Compliance Signals

The diff scanner (`scanDiff` in `packages/agent-sdk/src/integrations/gitlab.ts`) detects:
- **PII**: SSN, credit card numbers, email, phone, date of birth, passport, driver's license
- **PHI**: Patient data, diagnosis, medical records, prescriptions, lab results, treatment plans
- **PCI**: CVV, cardholder data, expiry dates
- **Secrets**: API keys, passwords, private keys, AWS credentials, GitHub/GitLab PATs, OpenAI keys

## Decision Framework

- **ALLOW** - Action complies with all policies. Proof token issued.
- **DENY** - Critical violation detected. Action blocked with detailed findings.
- **QUARANTINE** - Requires human compliance review before proceeding.

## API Endpoints

```
POST /api/v1/authorize    - Submit action for policy evaluation
POST /api/v1/outcome      - Record action outcome
GET  /api/v1/evidence     - Query evidence trail
GET  /api/v1/approvals    - List pending approvals
```

## Conventions

- TypeScript monorepo managed with pnpm
- Services use Express.js
- Tests use Vitest
- Dashboard uses Next.js 14 with Recharts and Tailwind CSS
- All crypto uses Ed25519 (EdDSA) for signatures and SHA-256 for hash chains
