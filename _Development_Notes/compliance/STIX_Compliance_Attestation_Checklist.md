# STIX Compliance Attestation Checklist

Date: 2026-02-14

## Quarterly Checklist

| Control Area | Check | Evidence | Status |
|---|---|---|---|
| Authorization enforcement | All protected targets reject missing/invalid proof tokens | Integration test logs | pending |
| Evidence integrity | Chain verification passes for sample and production traces | `stix-verify` outputs | pending |
| Key lifecycle | Rotation drill completed with old/new key verification continuity | Key rotation drill report | pending |
| Transport security | mTLS policy enforced and validated in cluster | `deploy/k8s/stix-mtls.yaml` + cluster query output | pending |
| Durable storage | Restart/recovery drill shows no state loss | DR run logs + recovery metrics | pending |
| Replay determinism | Strict replay samples return `MATCH` or investigated drift | Replay report set | pending |

## Sign-off

- Compliance Lead: ____________________ Date: __________
- Security Lead: ______________________ Date: __________
- Platform Lead: ______________________ Date: __________

