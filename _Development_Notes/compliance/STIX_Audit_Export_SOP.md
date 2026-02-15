# STIX Audit Export SOP

Date: 2026-02-14

## Objective

Produce an audit-grade evidence bundle for a trace, verify integrity, and attach replay output.

## Prerequisites

- Access to STIX evidence API.
- Public verification key for signed evidence events.
- Access to policy artifacts used for replay.

## Procedure

1. Export trace data:
   - `GET /api/v1/evidence/export/<trace_id>?format=json`
2. Save as file:
   - `trace_<trace_id>.json`
3. Verify chain + signatures:
   - `pnpm --filter @stix/verify exec stix-verify verify trace_<trace_id>.json --key <public_key.pem>`
4. Replay deterministic decision:
   - `pnpm --filter @stix/replay exec stix-replay --bundle trace_<trace_id>.json --policies ./policies --strict`
5. Capture outputs:
   - integrity result
   - replay `MATCH` or `DRIFT`
   - timestamp and operator

## Required Audit Packet

- Exported trace bundle JSON.
- Verifier output log.
- Replay output log.
- Applicable policy artifact hash and version metadata.
- Operator attestation (who exported, when, why).

## Failure Handling

- If verification fails: escalate as integrity incident.
- If replay drifts in strict mode: open policy drift investigation ticket.
- Record every failed export/verify attempt in incident notes.

