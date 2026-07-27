# Changelog

## [0.1.16] - 2026-07-27

### Dashboard

- Added live approval workflow context to Evidence record details by trace ID.
- Wired Evidence record inspection buttons and export error handling.
- Added a live Policy Drift Check across policy state, Fabric rollout channels, high-risk approval coverage, and readiness signals.
- Renamed the GitLab governance action so navigation no longer implies an immediate check before the operator runs it.

## [0.1.15] - 2026-07-26

### Dashboard

- Added live Fabric registry registration forms for agents, enforcement points, tool actions, and policy channels.
- Invalidated Fabric inventory, graph, statistics, and readiness queries after successful registration.
- Replaced approval quick actions that bypassed required justification with a review flow that enforces role and evidence requirements.
- Replaced the Governance approval matrix sample rows with live delegation data from the approval service.
- Added dashboard refresh/error handling for command-center, governance, approvals, and GitLab evidence views.
- Removed the remaining inert empty-state policy creation button and surfaced the registered GitLab Guardian agent from Fabric inventory.

### Reliability

- Made the dashboard API timeout implementation safe for browser and non-browser client smoke tests.

## [0.1.14] - 2026-07-26

### Dashboard

- Wired dashboard evidence statistics, chain verification, filtered export, and live error states to the running Evidence service.
- Wired approval decisions with configured approver identity and role, including required-role visibility and mismatch guidance.
- Restored dashboard sessions on load and made API key/operator settings apply across the console.
- Added live policy create/edit/import/export controls and connected GitLab quick actions to console routes.
- Added the Evidence filtered export endpoint used by the dashboard and strengthened its integration coverage.

## [0.1.13] - 2026-07-26

### Security

- Bound proof tokens to exact request and argument hashes, action IDs, resource IDs, approval references, authenticated actor fields, and unique replay identifiers.
- Selected target-verifier keys by JWT `kid`, enforced algorithm/key agreement, and enabled resource matching plus request-binding validation by default.
- Reauthorized approved quarantine requests before returning `ALLOW`; approval completion now requires a newly issued proof token.
- Forced enterprise enforcer deployments to `CLOSED` failure mode and bound actor, tenant, role, and attributes to configured workload identities.

### Tests

- Added unit coverage for proof bindings, `kid` selection, resource matching, workload identity binding, enterprise fail-closed behavior, and SDK approval polling.
- Converted integration quarantine workflows from optional skips into deterministic approval, reauthorization, proof, rejection, and tamper tests.

## [0.1.12] - 2026-07-26

### Fixed

- Loaded every YAML document from multi-document policy packs in the policy service instead of only the first document.
- Honored `require_signal`, `env`, `require_resource_attr`, `require_actor_attr`, and tenant-match policy conditions before broad rules can match.
- Wired the dashboard Policy Simulator through the shared API client and React Query mutation path instead of hardcoded localhost fetches.
- Added simulator controls for detection signals and risk tier so presets exercise live Enforcer policy behavior.

### Tests

- Added regression coverage for multi-document policy loading and condition guard evaluation.

All notable changes to STIX are documented here.

## [0.1.11] - 2026-07-26

### Changed

- Reframed Doctrine/FDE as an external governed operating module instead of a STIX Fabric product component.
- Updated the Fabric demo seed so Doctrine observer records are opt-in with `STIX_DEMO_INCLUDE_DOCTRINE=true`.
- Updated the Floci FDE deploy gate to validate STIX Fabric readiness only, while reporting Doctrine/FDE as the operator lane.
- Bumped the monorepo and STIX package versions to `0.1.11`.

### Fixed

- Hardened the Floci AWS smoke to use deterministic object keys and fail on non-local AWS endpoints.
- Prevented host AWS credentials from being passed into the Docker Compose Floci deployment stack.
- Added a pinned default Floci image and explicit Floci container health check for the local deploy lane.
- Upgraded existing `better-sqlite3` consumers to `12.11.1` so full installs work on Node 20 through Node 26.

## [0.1.10] - 2026-07-25

### Added

- Added `pnpm deploy:fde:floci` as a one-command Doctrine/FDE deployment gate.
- Added `scripts/deploy/floci-fde-gate.mjs` to build/start the Floci stack, wait for health, seed Doctrine/Fabric, smoke readiness, smoke dashboard routes, and emit a JSON report.
- Added `.github/workflows/floci-fde.yml` for CI validation of the Floci FDE deployment lane.

### Changed

- Hardened `scripts/deploy/floci-aws-smoke.mjs` to tolerate existing S3-compatible buckets.
- Documented the one-command FDE gate and CI teardown mode.
- Bumped the monorepo and STIX package versions to `0.1.10`.

## [0.1.9] - 2026-07-25

### Added

- Added Floci AWS emulator support to the Docker deployment stack for FDE/Doctrine deployment drills.
- Added a deployable dashboard image target so `/fabric` and `/doctrine` are included in the containerized stack.
- Added `pnpm deploy:floci:smoke` for S3-compatible Floci artifact round-trip validation.
- Added a lean `.dockerignore` for reproducible Docker build contexts.
- Added Floci AWS deployment documentation and v0.1.9 release readiness evidence.

### Changed

- Isolated the Docker Compose project with `name: stix` to prevent non-STIX orphan cleanup collisions.
- Docker Compose now waits for healthy Floci, Postgres, Redis, and STIX services before starting dependent services.
- Docker image builds now use the repo-pinned `pnpm@8.12.0` and copy `.npmrc` for deterministic frozen installs.
- Fixed staging and production Kustomize overlays to patch the existing `stix-config` ConfigMap instead of invalid generator merge behavior.
- Bumped the monorepo and STIX package versions to `0.1.9`.

## [0.1.8] - 2026-07-25

### Added

- Promoted Fabric readiness calculation into `@stix/fabric-types` as shared control-plane logic.
- Added `GET /api/v1/fabric/readiness` to return Fabric and Doctrine readiness from the Fabric service.
- Added dashboard API client and React Query hook support for backend readiness.
- Added Fabric service test coverage for the readiness endpoint.

### Changed

- `/fabric` and `/doctrine` now prefer the backend readiness report while retaining local fallback calculation.
- Bumped the monorepo and STIX package versions to `0.1.8`.

## [0.1.7] - 2026-07-25

### Added

- Added a reusable dashboard Fabric readiness model that computes posture score, readiness level, exceptions, and remediation guidance from existing Fabric registry data.
- Added Doctrine readiness controls for runtime registration, gatekeeper activation, verify/checkpoint action modeling, active gold-build channel, and G0-G7 coverage.
- Added unit coverage for Fabric and Doctrine readiness calculations.

### Changed

- `/fabric` now shows readiness exceptions and remediation cards instead of only raw posture bars.
- `/doctrine` now shows a computed readiness score, gate coverage, control checklist, and missing-control exceptions.
- Bumped the monorepo and STIX package versions to `0.1.7`.

## [0.1.6] - 2026-07-25

### Added

- Added a STIX Fabric console route for Doctrine-aware governance posture at `/doctrine`.
- Added an animated Fabric orbit visualization on `/fabric` using `animejs` and `motion`.
- Added a deterministic Fabric demo seed script with Doctrine OS registry records:
  - `pnpm demo:fabric:seed`
- Added a local integration launcher for the real-client enforcer stack:
  - `scripts/dev/start-enforcer-integration.ps1`
- Added Doctrine integration documentation:
  - `docs/integrations/STIX_DOCTRINE_INTEGRATION.md`
- Added release QA evidence:
  - `docs/releases/v0.1.6.md`

### Changed

- Bumped the monorepo and STIX package versions to `0.1.6`.
- Dashboard stats now degrade partially when one Core service is unavailable instead of failing the full overview.
- Dashboard lint now runs through the ESLint CLI instead of deprecated `next lint`.
- Hardened production dependencies across Next.js, Fastify, OpenTelemetry, YAML parsing, globbing, HTTP clients, and mail transport packages.
- Set `auto-install-peers=false` for deterministic pnpm installs.

### Fixed

- Fixed Fastify 5 compatibility for empty JSON `DELETE` requests in the policy service.
- Fixed OpenTelemetry v2 resource construction in `@stix/observability`.
- Fixed enforcer error normalization for unknown Fastify request errors.
- Fixed dashboard/Recharts type compatibility after dependency hardening.

### Security

- Production audit is clean for moderate, high, and critical advisories:
  - `pnpm audit --prod --audit-level moderate`
- One low, pathless `cli` advisory remains reported by pnpm audit and is documented in `docs/releases/v0.1.6.md`.
