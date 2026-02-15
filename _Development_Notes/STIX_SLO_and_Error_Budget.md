# STIX SLO and Error Budget

Date: 2026-02-14

## Service Level Objectives

| Service | SLI | SLO Target | Window |
|---|---|---|---|
| Enforcer `/api/v1/authorize` | Availability | 99.95% | 30 days |
| Enforcer `/api/v1/authorize` | p95 latency | <= 150 ms | 30 days |
| Policy `/api/v1/evaluate` | p95 latency | <= 75 ms | 30 days |
| Evidence write endpoints | Successful writes | 99.99% | 30 days |
| Approvals API | Availability | 99.90% | 30 days |

## Error Budget

- Enforcer availability budget at 99.95%: 21m 36s monthly downtime.
- Evidence write success budget at 99.99%: 4m 19s monthly failures.
- Burn rate policy:
  - >2x burn over 6h: freeze non-critical deploys.
  - >4x burn over 1h: incident response and rollback consideration.

## Alerting Thresholds

1. Enforcer 5xx ratio > 1% for 5m.
2. Evidence write failures > 0.1% for 5m.
3. Pending approvals SLA breach rate > 5% daily.
4. Replay drift detected in production validation sample.

## Reporting Cadence

1. Daily operational dashboard review.
2. Weekly SLO trend review in engineering/compliance sync.
3. Monthly SLO and error-budget sign-off.

