# STIX Monthly SLO Sign-off - 2026-02

Generated: 2026-02-17T00:07:04.565Z

## SLO Summary

- Enforcer availability target: 99.95%
- Enforcer p95 latency target: <= 150ms
- Policy p95 latency target: <= 75ms
- Evidence write success target: 99.99%
- Approvals availability target: 99.90%

## Error Budget Review

- 6h burn-rate (>2x): PASS | FAIL | N/A
- 1h burn-rate (>4x): PASS | FAIL | N/A
- Incident rollbacks executed: YES | NO

## Capacity Snapshot

- Performance suite artifact attached.
- Baseline: 2000 requests @ concurrency 50
- Baseline throughput (rps): 1617.74
- Baseline p95 latency (ms): 44.04
- Elevated throughput (rps): 3445.9
- Elevated p95 latency (ms): 46.67
- Max verified concurrency: 100
## Replay/Verify Snapshot

- Replay report artifact attached.
- Paste investigation ticket IDs for any drift findings below.

Tickets:
- 
## Compliance and Operations Attestation

- DR drill executed this month: YES | NO
- Key rotation verification executed this month: YES | NO
- mTLS posture validated in cluster: YES | NO
- Compliance checklist updated: YES | NO

## Sign-off

- Platform SRE Lead: ____________________ Date: __________
- Security Lead: ________________________ Date: __________
- Compliance Lead: ______________________ Date: __________
