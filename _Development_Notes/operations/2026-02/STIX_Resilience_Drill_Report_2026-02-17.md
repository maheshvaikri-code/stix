# STIX Resilience Drill Report

Date: 2026-02-17
Drill ID: STIX-DR-20260217

## Drill Scope

- Key rotation cutover
- Evidence service outage simulation
- Service restart and recovery
- Strict replay verification on sampled traces

## Environment

- Cluster/region: local-compose
- Build/tag: ef871cc
- Policy pack hash: n/a
- Signing key IDs involved: key-prev -> key-current

## Timeline

| Time (UTC) | Step | Result |
|---|---|---|
| 2026-02-17T00:06:25.162Z | Start drill | started |
| 2026-02-17T00:06:25.213Z | Preflight health checks | all services healthy |
| 2026-02-17T00:06:25.213Z | Rotate signing key references | simulated cutover key-prev -> key-current |
| 2026-02-17T00:06:25.213Z | Simulate evidence outage | stopping container stix-evidence |
| 2026-02-17T00:06:47.801Z | Restore evidence service | starting container stix-evidence |
| 2026-02-17T00:06:50.171Z | Restore evidence service | healthy |
| 2026-02-17T00:06:50.179Z | Service restart/recovery verification | healthy |
| 2026-02-17T00:06:50.179Z | Run strict replay verification samples | running |
| 2026-02-17T00:06:56.606Z | Run strict replay verification samples | complete |
| 2026-02-17T00:06:56.606Z | End drill | completed |

## RTO/RPO Outcomes

- RTO target: 60 minutes
- RPO target: 15 minutes
- Observed RTO: 0.42 minutes
- Observed RPO: 0 minutes
- Within target: YES

## Validation Evidence

- Health and readiness checks:
  - http://localhost:3101/health, http://localhost:3102/health, http://localhost:3103/health, http://localhost:3104/health
- Evidence outage authorization probe:
  - status: 200
  - response snippet: {"decision":"DENY","reason_code":"NO_MATCHING_POLICY","trace_id":"stix_2374db8d-d1be-49db-a068-ec14a3708a22","explanation":"No applicable policy found for READ on DOCUMENT","policy_id":"default_deny","policy":{"id":"default_deny","version":"1.0.0","hash":"sha256:05598e1e7adc27cb8790ca0dc86df5307070e1f1c8f20a2fcc1b551aa54bc69a"},"obligations":[],"approval":null,"controls":[],"regulations":[]}
- Replay verification output:
  - pnpm ops:replay-smoke passed
  - artifacts: artifacts/ops/replay-report.md

## Drift and Incident Notes

- Drift detected: NO
- Incident ticket(s): <fill>
- Root cause summary: <fill if needed>
- Remediation and prevention actions: <fill if needed>

## Notes

- No blocking findings in this run.

## Sign-off

- Incident Commander: ____________________ Date: __________
- Platform SRE Lead: _____________________ Date: __________
- Security Lead: _________________________ Date: __________
