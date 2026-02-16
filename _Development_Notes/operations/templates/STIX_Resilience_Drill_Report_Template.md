# STIX Resilience Drill Report Template

Date: YYYY-MM-DD
Drill ID: STIX-DR-XXXX

## Drill Scope

- Key rotation cutover
- Evidence service outage simulation
- Service restart and recovery
- Strict replay verification on sampled traces

## Environment

- Cluster/region:
- Build/tag:
- Policy pack hash:
- Signing key IDs involved:

## Timeline

| Time (UTC) | Step | Result |
|---|---|---|
| 00:00 | Start drill | |
| 00:00 | Rotate signing key references | |
| 00:00 | Simulate evidence outage | |
| 00:00 | Restore evidence service | |
| 00:00 | Restart STIX services | |
| 00:00 | Run replay/verify samples | |
| 00:00 | End drill | |

## RTO/RPO Outcomes

- RTO target: 60 minutes
- RPO target: 15 minutes
- Observed RTO:
- Observed RPO:
- Within target: YES | NO

## Validation Evidence

- Health and readiness checks:
  - links/log paths:
- Evidence trace retrieval:
  - links/log paths:
- Approval and policy data continuity:
  - links/log paths:
- Replay verification output:
  - links/log paths:

## Drift and Incident Notes

- Drift detected: YES | NO
- Incident ticket(s):
- Root cause summary:
- Remediation and prevention actions:

## Sign-off

- Incident Commander: ____________________ Date: __________
- Platform SRE Lead: _____________________ Date: __________
- Security Lead: _________________________ Date: __________
