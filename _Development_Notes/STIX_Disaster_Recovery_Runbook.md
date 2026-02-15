# STIX Disaster Recovery Runbook

Date: 2026-02-14

## Targets

- RTO: 60 minutes
- RPO: 15 minutes

## Recovery Scope

- Postgres data for policy, evidence, approvals.
- Redis cache warm-up (non-authoritative).
- Service health and authorization/evidence continuity verification.

## Backup Procedure

1. Execute backup script:
   - `powershell -ExecutionPolicy Bypass -File scripts/dr/backup-postgres.ps1`
2. Archive output in immutable backup location.
3. Record checksum and operator metadata.

## Restore Procedure

1. Provision clean Postgres instance.
2. Execute restore:
   - `powershell -ExecutionPolicy Bypass -File scripts/dr/restore-postgres.ps1 -BackupFile <path>`
3. Restart STIX services.
4. Run service verification:
   - `powershell -ExecutionPolicy Bypass -File scripts/dr/verify-dr.ps1`

## Validation Checklist

1. `/health` and `/ready` return healthy for all services.
2. Evidence trace retrieval works for known trace IDs.
3. Approval tickets and policy records are present after restore.
4. Replay verification succeeds on sampled traces.

## Incident Escalation

1. If RTO exceeds 60 minutes: escalate to Incident Commander.
2. If data gap exceeds RPO: open compliance incident and impact review.
3. Document root cause, remediation, and prevention actions.

