# Changelog

All notable changes to STIX are documented here.

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
