# STIX Combined Architecture Integration

Date: 2026-02-18

## Goal

Integrate a model-safety layer and STIX in one control flow:

1. Model-safety service evaluates prompt/output risk.
2. Adapter normalizes those safety signals.
3. Adapter calls STIX Enforcer (`/api/v1/authorize`).
4. Final execution gate uses both provider and STIX decisions.

This pattern is intended for enterprise environments where content safety and execution-time action governance must both be enforced.

## Reference Flow

```text
User Request
  -> Model Safety Layer (Bedrock/Azure/Vertex/etc.)
  -> Signal Adapter (normalize + enrich context)
  -> STIX Enforcer (ALLOW / DENY / QUARANTINE)
  -> Target System (executes only when gate allows)
  -> STIX Outcome + Evidence
```

## Decision Contract

Recommended final gate logic:

1. If provider says block/high-risk unsafe content: final decision = `DENY`.
2. Else use STIX decision:
   - `ALLOW`: execute with obligations.
   - `DENY`: do not execute.
   - `QUARANTINE`: request human approval.

## Mapping to STIX Request

The adapter should inject provider signals into:

- `context.signals`
- `context.tags`
- `context.attributes.guardrail`
- `tool_call.risk_tier`

Example STIX authorization payload:

```json
{
  "actor": {
    "id": "agent-support-01",
    "type": "AI_AGENT",
    "tenant": "acme"
  },
  "action": "SEND_EMAIL",
  "resource": {
    "type": "EMAIL",
    "id": "msg-123"
  },
  "context": {
    "env": "prod",
    "purpose": "customer_support",
    "signals": {
      "piiDetected": true,
      "custom": {
        "provider_block_recommended": false,
        "prompt_injection_detected": false
      }
    },
    "tags": [
      "provider:azure",
      "safety:medium"
    ],
    "attributes": {
      "guardrail": {
        "provider": "azure",
        "blockRecommended": false,
        "riskTier": "MEDIUM",
        "reasons": []
      }
    }
  },
  "tool_call": {
    "tool": "email.send",
    "risk_tier": "MEDIUM",
    "args_summary": "customer support email"
  }
}
```

## Included Adapter Template

Script:

- `scripts/integrations/combined-architecture-adapter.mjs`

Command:

```bash
pnpm integration:combined-adapter -- \
  --provider bedrock \
  --provider-input tests/fixtures/integrations/bedrock-safety.json \
  --stix-request tests/fixtures/integrations/base-authorize-request.json \
  --enforcer-url http://localhost:3001 \
  --output artifacts/integrations/combined-bedrock.json
```

Dry-run (normalize + build STIX request only):

```bash
pnpm integration:combined-adapter -- \
  --provider azure \
  --provider-input tests/fixtures/integrations/azure-safety.json \
  --stix-request tests/fixtures/integrations/base-authorize-request.json \
  --dry-run true \
  --output artifacts/integrations/combined-azure-dry-run.json
```

Supported provider modes in template:

- `bedrock`
- `azure`
- `vertex`
- `generic`

## Fixture Files

- `tests/fixtures/integrations/base-authorize-request.json`
- `tests/fixtures/integrations/bedrock-safety.json`
- `tests/fixtures/integrations/azure-safety.json`
- `tests/fixtures/integrations/vertex-safety.json`

## Rollout Checklist

1. Define provider-to-STIX mapping for your exact provider payload shape.
2. Add policy rules for injected tags/signals (`provider:*`, `safety:*`, `provider_block_recommended`).
3. Enforce final gate contract in execution service (provider + STIX).
4. Send outcomes to `/api/v1/outcome` after execution.
5. Add replay scenarios with provider signal variants.
6. Add operational alerts for high-rate `QUARANTINE` or provider block spikes.

## Notes

- This adapter is a reference starter, not a provider SDK replacement.
- Keep provider raw payloads out of logs unless redacted.
- In production, route secrets and service auth through your existing secret manager and service identity controls.
