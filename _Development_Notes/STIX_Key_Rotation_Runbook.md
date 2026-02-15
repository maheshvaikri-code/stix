# STIX Signing Key Rotation Runbook

Date: 2026-02-14

## Scope

- Enforcer proof-token signing keys.
- Evidence signing keys.
- Rotation via secret-managed key material (`SIGNING_KEY_PEM`) or file-based key path.

## Runtime Support

- `services/enforcer` supports:
  - `SIGNING_KEY_ID` + `SIGNING_KEY_PATH`
  - `SIGNING_KEY_ID` + `SIGNING_KEY_PEM`
- `services/evidence` supports:
  - `SIGNING_KEY_ID` + `SIGNING_KEY_PATH`
  - `SIGNING_KEY_ID` + `SIGNING_KEY_PEM`
- Production guardrails require configured signing key source + key id.

## Rotation Procedure

1. Generate new keypair in KMS/HSM or enterprise key service.
2. Publish new private key to secret manager and set new `SIGNING_KEY_ID`.
3. Roll out enforcer and evidence with updated secret references.
4. Keep old verification keys available for token/event verification window.
5. Verify:
   - New decisions/events carry new `key_id`.
   - Existing historical events still verify with retained public key set.
6. Decommission old key after retention window and verification audit.

## Validation Checklist

- Startup logs show loaded signing key source and `key_id`.
- `pnpm build` and `pnpm typecheck` are clean after key configuration change.
- Replay/verify tooling succeeds for both pre-rotation and post-rotation traces.

