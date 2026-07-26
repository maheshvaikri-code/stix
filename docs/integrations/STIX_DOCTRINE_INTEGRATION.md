# STIX + Doctrine Integration

Doctrine/FDE is a governed operating module for engineering execution in this repository or any other repository. It is not a STIX Fabric product component.

STIX Fabric can optionally observe Doctrine/FDE metadata when a team wants the dashboard to display operator-gate posture, but those records are read-only observer metadata and are not required for Fabric readiness.

## Model

| Doctrine concept                | Optional STIX observer representation                |
| ------------------------------- | ---------------------------------------------------- |
| `.Doctrine.md` operating system | External operator record: `agent_doctrine_operator`  |
| Read-only Doctrine/FDE adapter  | Observer enforcement point: `ep_doctrine_observer`   |
| Gate verification status        | Observer tool action: `tool_doctrine_verify`         |
| State-plane checkpoint status   | Observer tool action: `tool_doctrine_checkpoint`     |
| Gold build lane metadata        | Observer policy channel: `channel_doctrine_observer` |

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

The default seed contains STIX Fabric product records only. To include optional Doctrine observer metadata for a specific demo:

```bash
STIX_DEMO_INCLUDE_DOCTRINE=true pnpm demo:fabric:seed
```

Those optional records make Doctrine visible as an external operator lane, not as a Fabric-owned runtime.

## Boundary

This integration is optional observer-level metadata today. STIX does not execute Doctrine tools directly from the dashboard. The safe next step is a small adapter service that exposes signed, read-only Doctrine gate/state summaries, then later adds signed STIX authorization around write actions such as checkpoint or promotion.

## Readiness Controls

The Fabric service includes a `doctrine` posture section at `GET /api/v1/fabric/readiness` for compatibility with the dashboard. That section is optional operator posture. Missing Doctrine observer records do not block STIX Fabric readiness. The current controls are:

| Control                            | Source                                                                         |
| ---------------------------------- | ------------------------------------------------------------------------------ |
| Optional operator runtime observed | `agent_doctrine_operator` or another Doctrine-labeled external operator record |
| Optional gatekeeper active         | Active read-only Doctrine observer enforcement point                           |
| Verify action observed             | Doctrine verify observer tool action                                           |
| Checkpoint action observed         | Doctrine checkpoint observer tool action                                       |
| Optional gold build channel active | Active Doctrine observer policy channel                                        |
| G0-G7 gate coverage                | Gate metadata on the optional Doctrine operator record or observer channel     |

These controls are read-only posture signals. They show whether optional Doctrine observer metadata is complete enough for future enforcement wrapping, not whether STIX Fabric itself is ready.
