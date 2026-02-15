# STIX Execution Board

Date: 2026-02-14

## Closed Items (P0)

| ID | Item | Owner | Target Date | Proof Artifact | Status |
|---|---|---|---|---|---|
| STIX-P0-001 | Durable persistent storage wiring (policy/evidence/approvals) | Platform | 2026-02-14 | `services/policy/src/store/index.ts`, `services/evidence/src/store/index.ts`, `services/approvals/src/index.ts`, successful `pnpm build` | done |
| STIX-P0-002 | Signing key lifecycle source hardening (`SIGNING_KEY_PEM` + key id) | Security Platform | 2026-02-14 | `services/enforcer/src/index.ts`, `services/evidence/src/index.ts`, key rotation runbook | done |
| STIX-P0-003 | Transport hardening profile and runbooks | Platform Security | 2026-02-14 | `deploy/k8s/stix-mtls.yaml`, transport security runbook | done |

## Closed Items (P2)

| ID | Item | Owner | Target Date | Proof Artifact | Status |
|---|---|---|---|---|---|
| STIX-P2-001 | Compliance packaging and attestations | Compliance + Security | 2026-02-14 | `_Development_Notes/compliance/STIX_Control_Mapping.md`, `_Development_Notes/compliance/STIX_Audit_Export_SOP.md`, `_Development_Notes/compliance/STIX_Compliance_Attestation_Checklist.md` | done |
| STIX-P2-002 | SLO/DR maturity and runbooks | Platform SRE | 2026-02-14 | `_Development_Notes/STIX_SLO_and_Error_Budget.md`, `_Development_Notes/STIX_Disaster_Recovery_Runbook.md`, `scripts/dr/*` | done |
| STIX-P2-003 | Scale/performance certification | Performance Engineering | 2026-02-14 | `scripts/perf/stix-load.mjs`, `scripts/perf/generate-capacity-report.mjs`, `_Development_Notes/STIX_Performance_Certification_Runbook.md` | done |
| STIX-P2-004 | Governance UX depth | Product + Platform | 2026-02-14 | `dashboard/src/app/governance/page.tsx`, `_Development_Notes/STIX_Governance_UX_Spec.md` | done |
