# STIX Control Mapping (v1)

Date: 2026-02-14

## Scope

This document maps implemented STIX controls to common enterprise frameworks for audit packaging.

## SOC 2 (Security / Availability / Confidentiality)

| Framework Control | STIX Control | Evidence Artifact |
|---|---|---|
| CC6.1 Logical access | Enforcer API key auth + service token auth | `services/enforcer/src/index.ts`, `services/*/src/index.ts` |
| CC6.6 Change management | Policy-as-code lifecycle, governance page lifecycle states | `dashboard/src/app/governance/page.tsx`, policy repo history |
| CC7.2 Change monitoring | Replay/simulation for drift detection | `tools/stix-replay`, `tools/stix-simulate` outputs |
| CC7.3 Incident response | QUARANTINE + approvals workflow | `services/approvals/src/index.ts` |
| CC8.1 Availability controls | Durable Postgres stores + restart continuity | `services/*/src/store*`, `deploy/docker/docker-compose.yaml` |

## HIPAA (Technical Safeguards)

| HIPAA Section | STIX Control | Evidence Artifact |
|---|---|---|
| 164.312(a)(1) Access control | Deterministic authorization before action | `services/enforcer/src/core/engine.ts` |
| 164.312(b) Audit controls | Signed hash-chained evidence events | `services/evidence/src/core/chain.ts`, `services/evidence/src/store/index.ts` |
| 164.312(c)(1) Integrity | Tamper-evident chain verification endpoints | `/api/v1/evidence/verify` and tool verification outputs |
| 164.312(d) Person/entity auth | Service-token and API-key ingress controls | service auth hooks in each service |
| 164.312(e)(1) Transmission security | Strict mTLS profile in Kubernetes mesh | `deploy/k8s/stix-mtls.yaml` |

## ISO 27001 (Selected)

| ISO Control | STIX Control | Evidence Artifact |
|---|---|---|
| A.5.15 Access control | Policy-based deterministic enforcement | Policy artifacts and evaluation logs |
| A.8.15 Logging | Immutable evidence records with signatures | Evidence exports + verification report |
| A.8.16 Monitoring | Dashboard + stats + verification tooling | dashboard pages, `tools/stix-verify` |
| A.5.30 ICT readiness | DR runbook + backup/restore scripts | `_Development_Notes/STIX_Disaster_Recovery_Runbook.md`, `scripts/dr/*` |

## Packaging Notes

1. Attach replay/verify reports to control narratives.
2. Include key rotation logs by `key_id` as cryptographic control evidence.
3. Include mTLS policy manifests and cluster policy status output.

