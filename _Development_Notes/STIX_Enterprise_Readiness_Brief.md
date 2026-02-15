# STIX Enterprise Readiness Brief

Date: 2026-02-14
Audience: CIO, CISO, Compliance, Platform Engineering

## Executive Summary

STIX is an enterprise control plane for AI-agent actions. It enforces deterministic authorization, records tamper-evident evidence, and supports replay/simulation for audit-grade verification. Current implementation is production-capable for regulated environments when deployed with standard enterprise platform controls (PKI/secret manager/service mesh) and operated on a recurring governance cadence.

## What STIX Solves

- Prevents ungoverned agent/tool execution.
- Converts policy and compliance requirements into deterministic runtime decisions.
- Produces signed, hash-chained audit evidence by default.
- Enables post-incident and audit replay with policy/version traceability.

## Core Capabilities

- Real-time decisions: `ALLOW`, `DENY`, `QUARANTINE`
- Human-in-the-loop approvals for quarantined actions
- Protected-target verification model (proof token required)
- Evidence integrity: hash-chain + signatures
- Policy-as-code lifecycle and deterministic policy evaluation
- Replay and simulation tooling for policy drift and impact analysis
- Dashboard visibility for decisions, evidence, approvals, governance lifecycle

## Enterprise Controls Implemented

- Durable Postgres-backed policy, evidence, and approvals storage
- Production fail-fast guardrails (no unsafe memory fallback in prod profiles)
- Service-to-service auth guardrails
- API-key ingress guardrails on enforcer
- Signing key guardrails with secret-managed key support (`SIGNING_KEY_PEM` + `SIGNING_KEY_ID`)
- Kubernetes strict mTLS profile artifact (`deploy/k8s/stix-mtls.yaml`)
- DR, key-rotation, compliance, and performance runbooks/scripts

## Deployment and Operations Model

- Reference deployment: Docker Compose and Kubernetes manifests included
- Recommended production baseline:
  - Postgres durable backend
  - Service mesh mTLS enforcement
  - Secret manager backed signing keys
  - Scheduled replay/verify and DR drills
- Operational artifacts:
  - DR scripts: `scripts/dr/*`
  - Perf harness: `scripts/perf/*`
  - Compliance pack: `_Development_Notes/compliance/*`

## Readiness Status

- P0 control-path engineering items: complete
- P2 artifacts (compliance, DR/SLO, perf certification, governance UX): delivered
- Remaining work is recurring operational cadence, not missing platform capability

## Best-Fit Enterprise Use Cases

- Regulated AI workflows (healthcare, finance, critical operations)
- High-assurance approval and audit requirements
- Environments requiring deterministic, explainable authorization decisions

## Proof Artifacts for Due Diligence

- Architecture and readiness: `_Development_Notes/STIX_Enterprise_Readiness.md`
- Execution board: `_Development_Notes/STIX_Execution_Board.md`
- Transport security: `_Development_Notes/STIX_Transport_Security_Runbook.md`
- Key lifecycle: `_Development_Notes/STIX_Key_Rotation_Runbook.md`
- Compliance mapping: `_Development_Notes/compliance/STIX_Control_Mapping.md`
- Audit SOP: `_Development_Notes/compliance/STIX_Audit_Export_SOP.md`

