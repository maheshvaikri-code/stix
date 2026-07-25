# STIX Core and STIX Fabric

STIX is organized as two product layers:

- **STIX Core** is the trusted execution engine.
- **STIX Fabric** is the agent policy fabric built on top of STIX Core.

This split keeps the current runtime precise while giving the platform a clear path toward distributed enterprise governance.

## Product Model

| Layer | Role | Primary Users |
|---|---|---|
| STIX Core | Enforce decisions, issue proof, record evidence, and replay policy outcomes | Platform engineers, security engineers, agent/runtime builders |
| STIX Fabric | Coordinate policies, agents, tools, approvals, rollout, and compliance posture across many enforcement points | Governance teams, security leaders, compliance officers, platform owners |

## STIX Core

STIX Core is the execution-path control plane already present in this repository.

It contains:

- `services/enforcer` for authorization and outcome recording.
- `services/policy` for policy pack loading, evaluation, and simulation.
- `services/evidence` for hash-chained, signed audit evidence.
- `services/approvals` for human-in-the-loop workflows.
- `packages/agent-sdk` for wrapping agent tools and integrations.
- `packages/target-verifier` for proof-token validation at protected targets.
- `tools/stix-verify`, `tools/stix-replay`, and `tools/stix-simulate` for audit, replay, and drift analysis.

Core answers one question:

> Should this agent or service action be allowed right now, and can we prove the decision later?

## STIX Fabric

STIX Fabric is the broader product direction: a distributed policy, approval, and evidence fabric for autonomous AI actions.

Fabric uses STIX Core as the enforcement substrate and adds the enterprise coordination layer:

- Agent registry: identity, owner, environment, runtime, risk tier, and allowed scopes.
- Enforcement point registry: SDK clients, CI/CD gates, MCP/tool gateways, service gateways, and protected targets.
- Tool/action registry: normalized actions, risk labels, approval requirements, and allowed destinations.
- Policy distribution: signed policy bundles, rollout channels, environment overlays, and drift detection.
- Governance graph: relationships between agents, tools, policies, decisions, approvals, evidence, and outcomes.
- Enterprise controls: RBAC, tenant/team boundaries, approval routing, audit exports, SIEM/GRC webhooks.
- Fabric dashboard: compliance posture, active violations, policy drift, approvals, replay results, and evidence search.

Fabric answers a larger question:

> How do we govern every autonomous action across every agent, tool, team, and environment?

## Storage Model

STIX Core already supports the storage primitives Fabric needs:

| State | Current Core Storage | Fabric Direction |
|---|---|---|
| Policy packs | File, file-watch, memory, Postgres | GitOps-backed signed bundles plus Postgres metadata |
| Evidence | Memory, Postgres | Postgres for hot evidence, object storage for archives |
| Approvals | Memory, Postgres | Postgres with routing, SLA, and escalation metadata |
| Decision cache | Redis or in-memory fallback | Redis for distributed cache and rate-limit state |
| Agent/tool registries | STIX Fabric memory or Postgres registry API | Postgres system of record, graph expansion, and inventory history |
| Reports/exports | Files/artifacts | Object storage or durable artifact backend |

Memory is for development and tests only. Production should use Postgres and Redis.

## Why This Split Matters

The split prevents overloading one product name:

- STIX Core remains small, testable, embeddable, and enforcement-focused.
- STIX Fabric becomes the enterprise platform that coordinates many Core enforcement points.

This also creates a clean product ladder:

1. Start with STIX Core for one runtime, one gateway, or one CI/CD workflow.
2. Add Fabric when the organization needs central registry, rollout, posture, and audit governance across many runtimes.

## Repository Strategy

For now, keep STIX Core and early Fabric capabilities in this monorepo.

Recommended near-term layout:

```text
services/
  enforcer/       # STIX Core
  policy/         # STIX Core
  evidence/       # STIX Core
  approvals/      # STIX Core
  fabric/         # STIX Fabric API/control-plane service

packages/
  agent-sdk/      # STIX Core integration SDK
  target-verifier/# STIX Core proof verifier
  fabric-types/   # Fabric registry/control-plane types

dashboard/        # Evolves into the STIX Fabric console
```

Do not rename package names until the API boundary is stable. Public positioning can use STIX Core and STIX Fabric immediately without forcing disruptive import or deployment changes.

## Near-Term Fabric MVP

The first Fabric milestone adds:

- Agent registry.
- Enforcement point registry.
- Tool/action registry.
- Policy channels for dev, stage, and prod.
- Durable Postgres-backed registry storage.
- Registry graph summary API.
- Fabric-aware Agent SDK bridge for self-registration.
- Fabric console dashboard views for registry posture, graph summary, and agent/tool inventory.

The next milestone should add:

- Evidence and approval graph joins.
- Approval routing rules.
- Webhook/SIEM export hooks.
- Drift detection and policy rollout guardrails in the Fabric console.

## Local Fabric Console Demo

To view the emerging STIX Fabric console with live registry data:

```bash
pnpm --filter @stix/fabric start
pnpm demo:fabric:seed
pnpm --filter @stix/dashboard start
```

Then open:

```text
http://localhost:3100/fabric
http://localhost:3100/doctrine
```

The seed command writes stable demo agents, enforcement points, tool actions, and policy channels to the running Fabric API at `http://localhost:3005` by default. Override with `STIX_FABRIC_URL` when the Fabric service is running elsewhere.

The demo seed includes Doctrine as a governed engineering-runtime integration. See `docs/integrations/STIX_DOCTRINE_INTEGRATION.md` for the current registry-level boundary and the safe adapter path.

The Fabric service exposes `GET /api/v1/fabric/readiness` as the backend readiness report for Fabric and Doctrine posture. The dashboard prefers that API and keeps a local shared fallback for offline/development views. `/fabric` shows graph coverage, approval coverage, policy-channel posture, and remediation cards. `/doctrine` shows whether Doctrine is represented as a runtime, gatekeeper, verify/checkpoint action pair, active release channel, and G0-G7 gate set.

## Positioning

Recommended public language:

> STIX Core is the trusted execution engine for agent actions. STIX Fabric is the policy fabric that coordinates governance, approvals, and evidence across agents, tools, runtimes, and enterprise workflows.

Short version:

> STIX Core enforces. STIX Fabric governs.
