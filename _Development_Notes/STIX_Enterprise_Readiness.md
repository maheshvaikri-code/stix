# STIX Enterprise Readiness

Date: 2026-02-14

## Executive Call

- Enterprise value: high for regulated AI/action governance.
- Ready today: controlled and broad enterprise production, assuming standard platform controls (PKI/secret manager/service mesh) are present.
- Residual risk: operational certification depth (drills/compliance packaging), not core control-path capability.

## Why STIX Is Worth It

- Deterministic policy decisions at execution time.
- Tamper-evident, cryptographically signed evidence chain.
- Replay/simulation workflow to detect policy drift before rollout.
- Clear mapping to audit, incident response, and compliance evidence workflows.

## Current Verdict

STIX core control-path hardening is complete in-repo; remaining work is operational validation/certification activities.

## Progress Update

- 2026-02-09: Implemented fail-fast storage guardrails to block `prod + memory` configurations and remove silent fallback behavior in selected services.
- 2026-02-09: Implemented production signing-key guardrails in enforcer/evidence to block ephemeral key generation in `prod`.
- 2026-02-09: Added enforcer evidence-write mode (`EVIDENCE_WRITE_MODE`) with `prod` defaulting to `strict` to avoid silent audit-write loss.
- 2026-02-09: Implemented API-key auth guardrail for enforcer ingress (`API_KEY_AUTH_ENABLED`, `API_KEYS`) with `prod` default enabled.
- 2026-02-09: Implemented service-token auth guardrail (`SERVICE_TOKEN_AUTH_ENABLED`, `SERVICE_AUTH_TOKEN`) on policy/evidence/approvals API routes and outbound token forwarding from enforcer clients.
- 2026-02-09: Replaced enforcer trace lookup and stats routes to query evidence service data instead of in-memory demo counters.
- 2026-02-09: Hardened verifier defaults: strict key posture in target verifier and explicit opt-in for unsigned signature checks in `stix-verify`.
- 2026-02-09: Enforced production cache fail-fast behavior in enforcer (no silent Redis-to-memory fallback).
- 2026-02-13: Fixed approvals client parsing for wrapped API responses and standardized approval expiry handoff on `expires_at`.
- 2026-02-13: Moved auth hooks ahead of route registration in enforcer/policy/evidence/approvals so ingress and service-token auth are actually enforced.
- 2026-02-13: Replaced evidence `/api/v1/evidence/verify` demo counting path with per-trace hash-chain verification aggregation.
- 2026-02-14: Full monorepo `pnpm build` and `pnpm typecheck` pass cleanly, resolving repository-wide TypeScript/build drift as a release gate.
- 2026-02-14: Wired durable Postgres backends into policy/evidence/approvals runtime paths and deployment manifests (`docker-compose`, `k8s`).
- 2026-02-14: Added secret-managed signing key source support (`SIGNING_KEY_PEM` + `SIGNING_KEY_ID`) for enforcer and evidence services.
- 2026-02-14: Added transport hardening artifacts: strict Istio mTLS profile (`deploy/k8s/stix-mtls.yaml`) and transport/key rotation runbooks.
- 2026-02-14: Closed remaining incomplete source branches by wiring approvals core Postgres factory path and removing unwired evidence storage declarations.
- 2026-02-14: Added compliance packaging artifacts (control mapping, audit export SOP, attestation checklist).
- 2026-02-14: Added SLO/DR assets (targets, DR runbook, backup/restore/verification scripts).
- 2026-02-14: Added reproducible performance harness and capacity report generator.
- 2026-02-14: Added governance UX page and specification for policy lifecycle/delegation/reporting workflows.

## Current Remaining Gaps

- No open code or documentation backlog items remain on the execution board.
- Remaining work is operational execution cadence (running recurring drills/reports), not missing implementation artifacts.

## Must-Have Before Broad Enterprise Production

| Priority | Gap | Why it blocks enterprise rollout | Code evidence | Required change | Done when | Status |
|---|---|---|---|---|---|
| P0 | Durable persistent storage implementation | Volatile storage would break audit continuity and replay trust | `services/policy/src/store/index.ts`, `services/evidence/src/store/index.ts`, `services/approvals/src/index.ts`, `deploy/docker/docker-compose.yaml`, `deploy/k8s/stix-platform.yaml` | Wire and validate durable backend paths | Production profile runs on Postgres-backed services and survives restart/recovery without state loss | Done |
| P0 | Signing key lifecycle management | Ephemeral/manual keying weakens custody and rotation safety | `services/enforcer/src/index.ts`, `services/evidence/src/index.ts`, `_Development_Notes/STIX_Key_Rotation_Runbook.md` | Support secret-managed key source + codified rotation process | Rotation can cut over to new key IDs while preserving verification continuity | Done |
| P0 | Transport security profile | Plaintext internal traffic is not acceptable in enterprise deployments | `deploy/k8s/stix-mtls.yaml`, `_Development_Notes/STIX_Transport_Security_Runbook.md` | Codify strict mTLS policy and cert lifecycle | Cluster enforces strict mTLS and passes cert rotation checks | Done |

## Can Wait (Phase 2, After P0/P1)

| Priority | Item | Notes |
|---|---|---|
| P2 | Compliance packaging and attestations | Implemented docs/checklists; continue recurring evidence collection cadence |
| P2 | SLO/DR maturity and runbooks | Runbooks/scripts in place; continue scheduled drill execution |
| P2 | Scale/performance certification | Harness/report generator in place; continue periodic benchmark runs per topology |
| P2 | Governance UX depth | Governance page/spec delivered; continue API-backed UX iteration |

## Readiness Decision Gate

Ship to broad enterprise production only after:

1. All P0 items complete and validated in staging.
2. P1 items complete for target deployment model.
3. One full resilience drill passes: key rotation + evidence outage + restart recovery + replay verification.
4. Security/compliance sign-off documented.

## Practical Next Step

Execution board is now established at `_Development_Notes/STIX_Execution_Board.md` with closed P0 items and open P2 operational tracks. Continue tracking:

- owner,
- target date,
- proof artifact (test/log/report),
- gate status (`open`, `blocked`, `done`).
