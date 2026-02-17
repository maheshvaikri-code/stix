# STIX Execution Board

Date: 2026-02-17

## Open Items (v0.1.1 Post-Release Backlog)

All v0.1.1 post-release backlog items are now closed in-repo.

| ID | Item | Owner | Target Date | Proof Artifact | Status |
|---|---|---|---|---|---|
| STIX-011-001 | Run full resilience drill (key rotation + evidence outage + restart recovery + strict replay verify) | Platform SRE + Security Platform | 2026-03-06 | `_Development_Notes/operations/templates/STIX_Resilience_Drill_Report_Template.md`, `_Development_Notes/operations/2026-02/STIX_Resilience_Drill_Report_2026-02-17.md`, `artifacts/ops/replay-report.md` | done |
| STIX-011-002 | Complete quarterly compliance attestation checklist and sign-off | Compliance + Security + Platform | 2026-03-13 | `_Development_Notes/operations/2026-Q1/STIX_Quarterly_Attestation_2026-Q1.md` with checklist status updates and attachment links | done |
| STIX-011-003 | Publish first monthly SLO/error-budget sign-off packet | Platform SRE | 2026-03-03 | `_Development_Notes/operations/2026-02/STIX_Monthly_SLO_Signoff_2026-02.md` | done |
| STIX-011-004 | Execute performance certification on baseline/elevated/saturation profiles in production-like topology | Performance Engineering | 2026-03-10 | `.github/workflows/ops-cadence.yml` perf job, `_Development_Notes/STIX_Performance_Certification.md`, `_Development_Notes/operations/2026-02/STIX_Perf_Profile_Suite_2026-02-17.json` | done |
| STIX-011-005 | Operationalize scheduled replay/verify sample run and drift triage handoff | Platform + Compliance | 2026-03-17 | `.github/workflows/ops-cadence.yml`, `tests/fixtures/ops/*`, `_Development_Notes/STIX_Operational_Cadence_Runbook.md` | done |
| STIX-011-006 | Governance UX iteration: bind lifecycle/delegation/reporting cards to live APIs and exportable report output | Product + Platform | 2026-03-20 | `dashboard/src/app/governance/page.tsx` + export snapshot action | done |

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
