# STIX Operational Cadence Runbook

Date: 2026-02-16

## Purpose

Operationalize recurring replay/verify, monthly SLO packets, and performance certification evidence for enterprise governance.

## Workflow Automation

- Workflow: `.github/workflows/ops-cadence.yml`
- Weekly cadence job:
  - Replay and verify fixture evidence.
  - Publishes replay report artifact under `artifacts/ops/`.
- Monthly cadence job:
  - Generates monthly SLO sign-off packet template.
  - Publishes packet artifact under `artifacts/ops/`.
- Optional performance job (manual):
  - Runs baseline certification against a provided enforcer URL.
  - Produces `artifacts/perf/load-result.json` and capacity report.

## Local Dry-Run Commands

- `pnpm ops:replay-smoke`
- `pnpm ops:slo-signoff -- --month YYYY-MM --output artifacts/ops/slo-signoff-YYYY-MM.md`
- `pnpm perf:load -- --url http://localhost:3001 --requests 2000 --concurrency 50 --output artifacts/perf/load-result.json`
- `pnpm perf:report -- --input artifacts/perf/load-result.json --output _Development_Notes/STIX_Performance_Certification.md`

## Drift Triage Handoff

When replay reports any drift:

1. Classify impact:
   - Critical: `DENY -> ALLOW` or `QUARANTINE -> ALLOW`
   - High: `ALLOW -> DENY` blocking production paths
   - Medium/Low: reason/obligation-only drift
2. Create incident/investigation ticket with:
   - Trace IDs
   - Recorded vs replayed decision details
   - Policy version/hash context
   - Report artifact link
3. Assign ownership:
   - Platform on-call for service/runtime regressions
   - Policy owner for policy-pack drift
   - Compliance lead for audit-impacting drift
4. Resolution gate:
   - No production promotion until critical drift is resolved or approved with documented exception.

## Evidence Retention

- Keep workflow artifacts for audit period required by your policy.
- Copy monthly approved sign-off packets into `_Development_Notes/compliance/` for long-term audit packet assembly.
