# STIX - Shield, Trust & Integrity eXecution

<p align="center">
  <img src="Logo\STIX_Logo_trimmed_version.png" alt="STIX Logo" width="300"/>
</p>

<p align="center">
  <strong>Enterprise-Grade Compliance Guardrails for AI Agents and Automated Systems</strong>
</p>

STIX is an execution-path control plane for AI-agent and service actions.
It evaluates each action against policy before execution, returns a deterministic decision (`ALLOW`, `DENY`, `QUARANTINE`), and writes tamper-evident evidence for audit and replay.

> "Trust me, the AI followed policy" is not good enough. STIX proves it.

## STIX Guardian - AI Compliance Agent for GitLab

STIX Guardian is an **external AI agent** that automatically reviews every merge request for regulatory compliance, blocks unsafe AI agent actions in pipelines, and produces **cryptographically verifiable audit trails** - all triggered natively within GitLab.

```text
Developer creates MR with patient data handling code
    |
    v
STIX Guardian triggers automatically (GitLab Duo agent)
    |
    v
Diff scanned for PII/PHI/PCI/secrets (pattern + Claude analysis)
    |
    v
STIX Enforcer evaluates against HIPAA policy pack
    |
    +-- ALLOW: MR approved, 'stix:compliant' label, Ed25519 proof token
    |
    +-- DENY:  MR blocked, inline violation comments, tracking issue
    |
    +-- QUARANTINE: Routed to Privacy Officer for human review
```

### GitLab Duo Integration

The Guardian agent is configured via GitLab Duo flows in `.gitlab/duo/flows/`:

- **stix-guardian.yaml** - Custom agent with compliance review tools, triggered on `assign_reviewer` and `@mention`
- **compliance-gate.yaml** - Custom flow that orchestrates scan → evaluate → decide → record steps on MR open/update

CI/CD compliance gate in `.gitlab-ci.yml` runs `scripts/gitlab/guardian-ci.mjs` on every MR pipeline.

### Claude as Compliance Reasoning Engine (Anthropic Track)

STIX doesn't just "use Claude" - Claude is the **compliance reasoning engine** that feeds into a cryptographically-enforced decision pipeline. The `ComplianceAnalyzer` class (`packages/agent-sdk/src/reasoning/compliance-analyzer.ts`):

- Analyzes code diffs for regulatory violations with specific citations (HIPAA 164.502, PCI-DSS 3.4, etc.)
- Generates remediation suggestions with code examples
- Summarizes context for human approvers on QUARANTINE decisions
- Every analysis result is recorded in the Ed25519 signed evidence chain

### Sustainability (Green Agent Track)

STIX's policy engine evaluates **locally** with zero LLM calls for 80%+ of decisions. Claude is only invoked for QUARANTINE reasoning, complex diffs, and approval summaries. Result: **98% reduction** in LLM API calls vs. naive approaches. The dashboard tracks tokens saved, USD saved, and compute time savings in real-time.

---

## Table of Contents

- [Why STIX](#why-stix)
- [Capability Snapshot](#capability-snapshot)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Quick Start (Local Development)](#quick-start-local-development)
- [Run Full End-to-End Locally (Real Services)](#run-full-end-to-end-locally-real-services)
- [How to Use STIX](#how-to-use-stix)
- [Deploying STIX](#deploying-stix)
- [Combined Architecture Integration](#combined-architecture-integration)
- [Regulated Industry Playbooks](#regulated-industry-playbooks)
- [Enterprise Hardening Checklist](#enterprise-hardening-checklist)
- [Operations and Verification](#operations-and-verification)
- [Enterprise Readiness Status](#enterprise-readiness-status)
- [Documentation Index](#documentation-index)
- [Contributing](#contributing)
- [License](#license)

## Why STIX

Modern agentic systems can execute high-impact operations quickly. STIX gives you a deterministic enforcement layer so decisions are governed before action, not audited after harm.

STIX is useful when you need all of the following:

- runtime policy enforcement on AI/service actions,
- human approval for high-risk actions,
- cryptographically verifiable audit evidence,
- replay/simulation to detect policy drift before rollout,
- regulator-aligned control mapping and evidence export workflows.

## Capability Snapshot

| Domain | STIX Capability |
|---|---|
| Enforcement | Policy-based `ALLOW` / `DENY` / `QUARANTINE` decisions |
| Guardrails | Human-in-the-loop approval workflows |
| Evidence | Hash-chained, signed evidence events |
| Verification | Chain and signature verification tooling |
| Replay | Replay and drift analysis tooling |
| Integrations | Agent SDK and target verifier SDK |
| Governance | Policy lifecycle docs, runbooks, and dashboard support |

## Architecture

STIX services in this repo:

| Service | Default Port | Purpose |
|---|---:|---|
| `enforcer` | `3001` | Main authorization and outcome endpoint |
| `policy` | `3002` | Policy evaluation and management |
| `evidence` | `3003` | Evidence storage and verification |
| `approvals` | `3004` | Approval ticket workflows |
| `redis` | `6379` | Decision/cache support |
| `postgres` | `5432` | Durable policy/evidence/approvals store |

Core request flow:

1. Caller submits action context to Enforcer.
2. Enforcer evaluates policy and returns `ALLOW`, `DENY`, or `QUARANTINE`.
3. Enforcer writes decision/outcome evidence.
4. Protected target verifies STIX proof token before allowing execution.

## Repository Layout

```text
stix/
|- services/
|  |- enforcer/
|  |- policy/
|  |- evidence/
|  \- approvals/
|- sdk/
|  |- agent-sdk/
|  \- target-verifier/
|- tools/
|  |- stix-verify/
|  \- stix-replay/
|- policies/
|  |- default/
|  \- examples/
|- deploy/
|  |- docker/
|  \- k8s/
|- scripts/
|  |- dr/
|  \- perf/
\- _Development_Notes/
```

## Quick Start (Local Development)

This mode is best for fast development feedback.

### Prerequisites

- Node.js `20+`
- pnpm `8+`

### Install and build

```bash
pnpm install
pnpm build
```

### Start services (watch mode)

```bash
pnpm dev
```

### Health checks

```bash
curl http://localhost:3001/health
curl http://localhost:3002/health
curl http://localhost:3003/health
curl http://localhost:3004/health
```

Note: when Enforcer runs with `NODE_ENV=dev` or `NODE_ENV=test`, it uses mock downstream clients by design.

## Run Full End-to-End Locally (Real Services)

Use this when you want real Policy/Evidence/Approvals calls and durable Postgres-backed stores.

### Build and run Docker Compose stack

```bash
pnpm docker:build
pnpm docker:up
pnpm docker:logs
```

If local host ports `3001-3004` are already in use, override published ports:

```bash
STIX_ENFORCER_PORT=3101 STIX_POLICY_PORT=3102 STIX_EVIDENCE_PORT=3103 STIX_APPROVALS_PORT=3104 pnpm docker:up
```

PowerShell:

```powershell
$env:STIX_ENFORCER_PORT='3101'; $env:STIX_POLICY_PORT='3102'; $env:STIX_EVIDENCE_PORT='3103'; $env:STIX_APPROVALS_PORT='3104'; pnpm docker:up
```

### Stop stack

```bash
pnpm docker:down
```

Compose file used by these scripts: `deploy/docker/docker-compose.yaml`.

## How to Use STIX

### 1) Call authorization endpoint

```bash
curl -X POST http://localhost:3001/api/v1/authorize \
  -H "Content-Type: application/json" \
  -d '{
    "actor": {"id": "svc-ops", "type": "SERVICE", "attributes": {"authenticated": true}},
    "action": "read_document",
    "resource": {"type": "document", "id": "doc-123"},
    "context": {"env": "stage", "purpose": "support"}
  }'
```

### 2) Record outcome

```bash
curl -X POST http://localhost:3001/api/v1/outcome \
  -H "Content-Type: application/json" \
  -d '{
    "trace_id": "<TRACE_ID_FROM_AUTHORIZE>",
    "status": "SUCCESS",
    "result_summary": "Action executed"
  }'
```

### 3) Query evidence

```bash
curl "http://localhost:3003/api/v1/evidence?limit=20"
```

### 4) Work with approvals

```bash
curl "http://localhost:3004/api/v1/approvals/pending"
```

### TypeScript integration with Agent SDK

```ts
import { StixClient } from '@stix/agent-sdk';

const stix = new StixClient({
  enforcerUrl: 'http://localhost:3001',
  defaultActor: { id: 'agent-1', type: 'AI_AGENT', tenant: 'acme' },
  defaultEnv: 'stage',
});

const decision = await stix.authorize({
  action: 'read_document',
  resource: { type: 'document', id: 'doc-123' },
  context: { purpose: 'analysis' },
});

if (decision.allowed) {
  // execute protected action
}
```

## Deploying STIX

### Build service images from monorepo Dockerfile

```bash
docker build -f deploy/docker/Dockerfile --target enforcer -t stix/enforcer:latest .
docker build -f deploy/docker/Dockerfile --target policy -t stix/policy:latest .
docker build -f deploy/docker/Dockerfile --target evidence -t stix/evidence:latest .
docker build -f deploy/docker/Dockerfile --target approvals -t stix/approvals:latest .
```

### Kubernetes deployment

```bash
kubectl apply -f deploy/k8s/stix-platform.yaml
```

Optional strict internal mTLS profile (Istio):

```bash
kubectl apply -f deploy/k8s/stix-mtls.yaml
```

### Production-critical environment settings

`enforcer`:

- `NODE_ENV=prod`
- `POLICY_SERVICE_URL`, `EVIDENCE_SERVICE_URL`, `APPROVALS_SERVICE_URL`
- `SERVICE_AUTH_TOKEN`
- `API_KEY_AUTH_ENABLED=true`
- `API_KEYS=<comma-separated-keys>`
- `EVIDENCE_WRITE_MODE=strict`
- `SIGNING_KEY_ID` + (`SIGNING_KEY_PATH` or `SIGNING_KEY_PEM`)

`policy`, `evidence`, `approvals`:

- `NODE_ENV=prod`
- `STORAGE_TYPE=postgres`
- `POSTGRES_URL`
- `SERVICE_TOKEN_AUTH_ENABLED=true`
- `SERVICE_AUTH_TOKEN`

`evidence` also requires signing in prod:

- `SIGNING_ENABLED=true`
- `SIGNING_KEY_ID` + (`SIGNING_KEY_PATH` or `SIGNING_KEY_PEM`)

## Combined Architecture Integration

Use STIX as the execution-governance layer behind a model safety layer (Bedrock/Azure/Vertex/custom):

1. Model safety evaluates prompt/output risk.
2. Adapter normalizes safety signals.
3. STIX Enforcer decides `ALLOW` / `DENY` / `QUARANTINE`.
4. Final gate enforces provider + STIX decision.

Reference guide:

- `docs/COMBINED_ARCHITECTURE_INTEGRATION.md`

Adapter command:

```bash
pnpm integration:combined-adapter -- \
  --provider bedrock \
  --provider-input tests/fixtures/integrations/bedrock-safety.json \
  --stix-request tests/fixtures/integrations/base-authorize-request.json \
  --enforcer-url http://localhost:3001 \
  --output artifacts/integrations/combined-bedrock.json
```

Dry-run mapping check:

```bash
pnpm integration:combined-adapter -- \
  --provider azure \
  --provider-input tests/fixtures/integrations/azure-safety.json \
  --stix-request tests/fixtures/integrations/base-authorize-request.json \
  --dry-run true \
  --output artifacts/integrations/combined-azure-dry-run.json
```

## Regulated Industry Playbooks

Policy packs are in `policies/examples/` and `policies/default/`.

Compatibility snapshot from in-repo schema validation (2026-02-14):

| Pack | Valid / Total | Status |
|---|---:|---|
| `policies/examples/hipaa-healthcare.yaml` | `25/25` | Ready starter pack |
| `policies/examples/financial-sox-pci.yaml` | `25/25` | Ready starter pack |
| `policies/examples/default-policies.yaml` | `8/8` | Ready baseline pack |
| `policies/default/base-policies.yaml` | `16/30` | Mixed legacy + current schema |
| `policies/examples/gdpr-eu-data-protection.yaml` | `5/30` | Mostly reference templates |
| `policies/examples/ccpa-california-privacy.yaml` | `0/30` | Reference templates; needs normalization |

### Healthcare (HIPAA/HITECH)

Start with `policies/examples/hipaa-healthcare.yaml` and tailor:

- actor roles (`privacy_officer`, `irb_administrator`, etc.),
- PHI signal plumbing (`phiDetected`),
- emergency access and break-glass processes,
- retention/export workflows in `_Development_Notes/compliance/`.

### Financial Services (SOX/PCI/AML)

Start with `policies/examples/financial-sox-pci.yaml` and tailor:

- transaction thresholds and risk signals,
- dual-control approval roles,
- period-close restrictions,
- audit export controls and evidence retention.

### Privacy Programs (GDPR/CCPA/CPRA)

Current GDPR/CCPA packs are best treated as policy blueprints.
Use them as source material, then convert to current STIX policy schema before rollout.

## Enterprise Hardening Checklist

- Run all services in `prod` mode.
- Use Postgres-backed durable storage for policy/evidence/approvals.
- Enforce service token auth between services.
- Enforce enforcer ingress API key auth.
- Use managed secret store for signing keys.
- Apply strict mTLS profile for internal traffic.
- Set `DEFAULT_FAIL_MODE=CLOSED`.
- Keep `EVIDENCE_WRITE_MODE=strict`.
- Wire backup/restore and replay/verify into runbooks.
- Apply repository branch and tag protection controls from `_Development_Notes/STIX_Branch_Protection_Checklist.md`.

## Operations and Verification

### DR scripts

```bash
pnpm dr:backup
pnpm dr:restore -- -BackupFile artifacts/dr/<backup-file>.sql
pnpm dr:verify
```

### Performance scripts

```bash
pnpm perf:load -- --url http://localhost:3001 --requests 1000 --concurrency 50
pnpm perf:suite -- --url http://localhost:3101 --baseline-requests 2000 --baseline-concurrency 50 --output-dir artifacts/perf
pnpm perf:report
```

### Resilience drill automation

```bash
pnpm ops:resilience-drill -- --enforcer-url http://localhost:3101 --policy-url http://localhost:3102 --evidence-url http://localhost:3103 --approvals-url http://localhost:3104 --evidence-container stix-evidence --outage-seconds 10 --output artifacts/ops/resilience-drill-report.md
```

### Evidence verification CLI

```bash
pnpm --filter @stix/verify start -- chain ./path/to/evidence.json
pnpm --filter @stix/verify start -- signature ./path/to/evidence.json --key ./keys/public.pem
```

### Replay CLI

```bash
pnpm --filter @stix/replay start -- --help
```

### Operational cadence automation

- Scheduled workflow: `.github/workflows/ops-cadence.yml`
- Local replay/verify cadence smoke:

```bash
pnpm ops:replay-smoke
```

- Local monthly SLO sign-off packet generation:

```bash
pnpm ops:slo-signoff -- --month YYYY-MM --output artifacts/ops/slo-signoff-YYYY-MM.md
```

- Local quarterly attestation packet generation:

```bash
pnpm ops:attestation-packet -- --quarter YYYY-QN --output artifacts/ops/STIX_Quarterly_Attestation_YYYY-QN.md
```

### GitHub Actions verification checklist

Run a fresh cadence check from latest `main`:

1. Open `Actions` in `https://github.com/STIX-Govern/stix`.
2. Select workflow `Ops Cadence`.
3. Click `Run workflow`.
4. Choose branch `main`.
5. Click `Run workflow`.

Expected result for a standard manual run:

- `Replay and Verify Cadence Check`: success
- `Monthly SLO Sign-off Packet`: success
- `Performance Certification (Optional)`: skipped unless `run_perf=true`
- `Quarterly Attestation Packet`: skipped unless `run_attestation=true`
- Artifacts: `replay-verify-cadence` and `slo-signoff-packet`

Stale rerun behavior:

- If a run starts from an older commit SHA, `ops-cadence.yml` auto-dispatches a fresh run on latest `main` and skips the stale replay step.

## Enterprise Readiness Status

Current status is documented in `_Development_Notes/STIX_Enterprise_Readiness.md`.

High-level summary:

- P0 control-path engineering items are complete.
- P2 artifacts (compliance pack, DR/SLO runbooks, perf harness, governance UX artifacts) are delivered.
- Remaining work is operational cadence (drills, attestations, periodic certification), not missing core platform capability.

## Documentation Index

- Architecture and overview: `STIX_Comprehensive_Documentation.md`
- Enterprise deployment guide: `docs/ENTERPRISE_DEPLOYMENT.md`
- Combined integration guide: `docs/COMBINED_ARCHITECTURE_INTEGRATION.md`
- Enterprise readiness brief: `_Development_Notes/STIX_Enterprise_Readiness_Brief.md`
- Enterprise readiness (detailed): `_Development_Notes/STIX_Enterprise_Readiness.md`
- Enterprise guardrail system: `_Development_Notes/STIX_Enterprise_Guardrail_System.md`
- Simulation engine: `_Development_Notes/STIX_SIMULATION_ENGINE.md`
- Replay upgrade notes: `_Development_Notes/STIX_Replay_Upgrade.md`
- Compliance artifacts: `_Development_Notes/compliance/STIX_Control_Mapping.md`
- Audit export SOP: `_Development_Notes/compliance/STIX_Audit_Export_SOP.md`
- DR runbook: `_Development_Notes/STIX_Disaster_Recovery_Runbook.md`
- SLO and error budget: `_Development_Notes/STIX_SLO_and_Error_Budget.md`
- Transport security runbook: `_Development_Notes/STIX_Transport_Security_Runbook.md`
- Key rotation runbook: `_Development_Notes/STIX_Key_Rotation_Runbook.md`
- Branch protection checklist: `_Development_Notes/STIX_Branch_Protection_Checklist.md`
- Operational cadence runbook: `_Development_Notes/STIX_Operational_Cadence_Runbook.md`
- Monthly sign-off packet (example): `_Development_Notes/operations/2026-02/STIX_Monthly_SLO_Signoff_2026-02.md`
- Quarterly attestation packet (example): `_Development_Notes/operations/2026-Q1/STIX_Quarterly_Attestation_2026-Q1.md`

## Contributing

See `CONTRIBUTING.md`.

## License

Apache License 2.0. See [LICENSE](LICENSE).
