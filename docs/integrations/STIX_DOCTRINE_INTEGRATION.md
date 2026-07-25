# STIX + Doctrine Integration

STIX Fabric treats Doctrine as an engineering-governance runtime that can be represented in the Fabric registry.

## Model

| Doctrine concept | STIX Fabric representation |
|---|---|
| `.Doctrine.md` operating system | Agent runtime: `agent_doctrine_os` |
| `doctrineos` MCP/server tools | Enforcement point: `ep_doctrine_gatekeeper` |
| Gate verification | Tool action: `tool_doctrine_verify` |
| State-plane checkpointing | Tool action: `tool_doctrine_checkpoint` |
| Gold build promotion | Policy channel: `channel_doctrine_gold_build` |

## Local Demo Wiring

Run a Fabric service and seed the demo registry:

```bash
pnpm --filter @stix/fabric start
pnpm demo:fabric:seed
pnpm --filter @stix/dashboard start
```

Open:

```text
http://localhost:3100/fabric
```

The seeded records make Doctrine visible in the Fabric UI as a governed agent runtime, with gate/checkpoint actions included in the inventory and graph.

## Boundary

This integration is registry-level today. STIX does not execute Doctrine tools directly from the dashboard yet. The safe next step is a small adapter service that exposes read-only Doctrine gate/state summaries, then later adds signed STIX authorization around write actions such as checkpoint or promotion.

## Readiness Controls

The Fabric service returns Doctrine readiness from registry records at `GET /api/v1/fabric/readiness`, and the dashboard uses that backend report when available. The current controls are:

| Control | Source |
|---|---|
| Doctrine runtime registered | `agent_doctrine_os` or another Doctrine-labeled agent |
| Gatekeeper active | Active Doctrine enforcement point |
| Verify action modeled | Doctrine verify tool action |
| Checkpoint action modeled | Doctrine checkpoint tool action |
| Gold build channel active | Active Doctrine policy channel |
| G0-G7 gate coverage | Gate metadata on the Doctrine agent or channel |

These controls are read-only posture signals. They show whether Doctrine is represented well enough for future enforcement wrapping.
