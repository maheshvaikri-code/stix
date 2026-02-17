# STIX Quarterly Compliance Attestation - 2026-Q1

Generated: 2026-02-17T00:07:12.771Z

## Evidence Checklist

| Control Area | Check | Evidence | Status |
|---|---|---|---|
| Authorization enforcement | All protected targets reject missing/invalid proof tokens | Integration test logs | complete |
| Evidence integrity | Chain verification passes for sample and production traces | `stix-verify` outputs | complete |
| Key lifecycle | Rotation drill completed with old/new key verification continuity | Key rotation drill report | complete |
| Transport security | mTLS policy enforced and validated in cluster | `deploy/k8s/stix-mtls.yaml` + cluster query output | complete |
| Durable storage | Restart/recovery drill shows no state loss | DR run logs + recovery metrics | complete |
| Replay determinism | Strict replay samples return `MATCH` or investigated drift | Replay report set | complete |

## Required Attachments

- Monthly SLO sign-off packets for quarter: _Development_Notes/operations/2026-02/STIX_Monthly_SLO_Signoff_2026-02.md
- DR drill report and restore logs: artifacts/ops/resilience-drill-report.md
- Key rotation verification report: artifacts/ops/resilience-drill-report.md
- Replay cadence reports and drift investigations (if any): artifacts/ops/replay-report.md
- Performance certification report: _Development_Notes/STIX_Performance_Certification.md

## Risk and Exceptions

- Open exceptions:
  - None | <fill>
- Deferred controls:
  - None | <fill>

## Sign-off

- Compliance Lead: ____________________ Date: __________
- Security Lead: ______________________ Date: __________
- Platform Lead: ______________________ Date: __________
