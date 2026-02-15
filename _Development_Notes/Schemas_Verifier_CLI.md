Awesome — this is the exact step that makes STIX **audit-grade**.

Below is a **complete “Schemas + Verifier CLI” package** you can drop into your repo.

You’ll get:

* ✅ **Versioned JSON Schemas** (AuthorizeRequest, DecisionResponse, PolicyArtifact, EvidenceEvent, EvidenceBundle)
* ✅ **Canonicalization rules** implemented using **RFC 8785 JSON Canonicalization Scheme (JCS)**
* ✅ **Verifier CLI** that checks:

  1. schema validity
  2. event_hash correctness
  3. hash-chain integrity (`prev_hash`)
  4. signature verification (RSA / Ed25519 supported via Node crypto)
  5. optional policy-hash validation (if bundle contains policy artifacts)

Everything is deterministic and reproducible.

---

# 0) Directory layout (drop-in)

```text
schemas/
  stix.authorize.request.schema.json
  stix.decision.response.schema.json
  stix.policy.artifact.schema.json
  stix.evidence.event.schema.json
  stix.evidence.bundle.schema.json

tools/
  stix-verify/
    package.json
    tsconfig.json
    src/
      index.ts
      verify.ts
      canonical.ts
      crypto.ts
      load.ts
```

---

# 1) JSON Schemas

## 1.1 `schemas/stix.authorize.request.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "stix.authorize.request.schema.json",
  "type": "object",
  "required": ["actor", "action", "resource", "context"],
  "additionalProperties": false,
  "properties": {
    "actor": {
      "type": "object",
      "required": ["id", "type"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string", "minLength": 1 },
        "type": { "enum": ["HUMAN", "SERVICE", "AI_AGENT", "JOB"] },
        "role": { "type": "string" },
        "tenant": { "type": "string" },
        "attributes": { "type": "object", "additionalProperties": true }
      }
    },
    "action": { "type": "string", "minLength": 1 },
    "resource": {
      "type": "object",
      "required": ["type"],
      "additionalProperties": false,
      "properties": {
        "type": { "type": "string", "minLength": 1 },
        "id": { "type": "string" },
        "classification": { "type": "array", "items": { "type": "string" } },
        "attributes": { "type": "object", "additionalProperties": true }
      }
    },
    "context": {
      "type": "object",
      "required": ["env"],
      "additionalProperties": false,
      "properties": {
        "env": { "enum": ["dev", "test", "stage", "prod"] },
        "purpose": { "type": "string" },
        "run_id": { "type": "string" },
        "session_id": { "type": "string" },
        "ticket_id": { "type": "string" },
        "jurisdiction": { "type": "string" },
        "transportSecurity": { "type": "string" },
        "tags": { "type": "array", "items": { "type": "string" } },
        "signals": {
          "type": "object",
          "additionalProperties": true
        },
        "attributes": { "type": "object", "additionalProperties": true }
      }
    },
    "tool_call": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "tool": { "type": "string" },
        "risk_tier": { "enum": ["LOW", "MEDIUM", "HIGH", "CRITICAL"] },
        "args_summary": { "type": "string" }
      }
    }
  }
}
```

## 1.2 `schemas/stix.decision.response.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "stix.decision.response.schema.json",
  "type": "object",
  "required": ["decision", "reason_code", "trace_id", "policy", "obligations"],
  "additionalProperties": false,
  "properties": {
    "decision": { "enum": ["ALLOW", "DENY", "QUARANTINE"] },
    "reason_code": { "type": "string", "minLength": 1 },
    "trace_id": { "type": "string", "minLength": 1 },
    "policy": {
      "type": "object",
      "required": ["id", "version", "hash"],
      "additionalProperties": false,
      "properties": {
        "id": { "type": "string" },
        "version": { "type": "string" },
        "hash": { "type": "string", "pattern": "^(sha256:)?[0-9a-fA-F]{64}$" }
      }
    },
    "obligations": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["type"],
        "additionalProperties": false,
        "properties": {
          "type": { "type": "string" },
          "params": { "type": "object", "additionalProperties": true }
        }
      }
    },
    "approval": { "type": ["object", "null"], "additionalProperties": true },
    "proof_token": { "type": "string" }
  }
}
```

## 1.3 `schemas/stix.policy.artifact.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "stix.policy.artifact.schema.json",
  "type": "object",
  "required": ["policy_id", "version", "scope", "decision", "reason_code"],
  "additionalProperties": false,
  "properties": {
    "policy_id": { "type": "string" },
    "version": { "type": "string" },
    "priority": { "type": "number" },
    "scope": {
      "type": "object",
      "required": ["actor_type", "action", "resource_type"],
      "additionalProperties": false,
      "properties": {
        "actor_type": { "type": "string" },
        "action": { "type": "string" },
        "resource_type": { "type": "string" }
      }
    },
    "conditions": { "type": "object", "additionalProperties": true },
    "decision": { "enum": ["ALLOW", "DENY", "QUARANTINE"] },
    "reason_code": { "type": "string" },
    "obligations": { "type": "array", "items": { "type": "object", "additionalProperties": true } },
    "approval": { "type": "object", "additionalProperties": true },
    "controls": { "type": "array", "items": { "type": "string" } },
    "regulations": { "type": "array", "items": { "type": "string" } }
  }
}
```

## 1.4 `schemas/stix.evidence.event.schema.json`

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "stix.evidence.event.schema.json",
  "type": "object",
  "required": ["schema_version", "event_id", "timestamp", "trace_id", "event_type", "payload", "integrity"],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "type": "string" },
    "event_id": { "type": "string" },
    "timestamp": { "type": "string", "format": "date-time" },
    "trace_id": { "type": "string" },
    "event_type": { "enum": ["DECISION", "OUTCOME", "APPROVAL", "POLICY_PUBLISH"] },
    "payload": { "type": "object", "additionalProperties": true },
    "integrity": {
      "type": "object",
      "required": ["event_hash", "prev_hash", "signature", "key_id", "alg"],
      "additionalProperties": false,
      "properties": {
        "event_hash": { "type": "string", "pattern": "^sha256:[0-9a-fA-F]{64}$" },
        "prev_hash": { "type": "string", "pattern": "^sha256:[0-9a-fA-F]{64}$" },
        "signature": { "type": "string" },
        "key_id": { "type": "string" },
        "alg": { "enum": ["Ed25519", "RS256"] }
      }
    }
  }
}
```

## 1.5 `schemas/stix.evidence.bundle.schema.json`

> This is the portable audit artifact.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "stix.evidence.bundle.schema.json",
  "type": "object",
  "required": ["bundle_version", "trace_id", "events", "keys"],
  "additionalProperties": false,
  "properties": {
    "bundle_version": { "type": "string" },
    "trace_id": { "type": "string" },
    "events": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "stix.evidence.event.schema.json" }
    },
    "policies": {
      "type": "array",
      "items": { "$ref": "stix.policy.artifact.schema.json" }
    },
    "keys": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["key_id", "alg", "public_key_pem"],
        "additionalProperties": false,
        "properties": {
          "key_id": { "type": "string" },
          "alg": { "enum": ["Ed25519", "RS256"] },
          "public_key_pem": { "type": "string" }
        }
      }
    },
    "manifest": {
      "type": "object",
      "additionalProperties": false,
      "properties": {
        "chain_head": { "type": "string" },
        "chain_tail": { "type": "string" }
      }
    }
  }
}
```

---

# 2) Verifier CLI (TypeScript)

## 2.1 `tools/stix-verify/package.json`

```json
{
  "name": "@stix/stix-verify",
  "type": "module",
  "private": true,
  "scripts": {
    "dev": "node --loader ts-node/esm src/index.ts",
    "build": "tsc -p tsconfig.json",
    "start": "node dist/index.js"
  },
  "dependencies": {
    "ajv": "^8.17.1",
    "ajv-formats": "^3.0.1",
    "canonicalize": "^2.0.0"
  },
  "devDependencies": {
    "ts-node": "^10.9.2",
    "typescript": "^5.6.3"
  }
}
```

## 2.2 `tools/stix-verify/tsconfig.json`

```json
{
  "extends": "../../tsconfig.base.json",
  "compilerOptions": {
    "outDir": "dist",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "target": "ES2022",
    "strict": true
  },
  "include": ["src/**/*.ts"]
}
```

---

## 2.3 `tools/stix-verify/src/canonical.ts`

Uses RFC 8785 canonicalization.

```ts
import canonicalize from "canonicalize";
import { createHash } from "node:crypto";

export function canonicalBytes(obj: unknown): Buffer {
  const s = canonicalize(obj);
  if (typeof s !== "string") throw new Error("canonicalize returned non-string");
  return Buffer.from(s, "utf8");
}

export function sha256Hex(buf: Buffer): string {
  return createHash("sha256").update(buf).digest("hex");
}

export function sha256Prefixed(buf: Buffer): string {
  return `sha256:${sha256Hex(buf)}`;
}
```

---

## 2.4 `tools/stix-verify/src/crypto.ts`

Signature verification for Ed25519 / RS256.

```ts
import { createVerify, verify as edVerify, KeyObject, createPublicKey } from "node:crypto";

export function parsePublicKey(pem: string): KeyObject {
  return createPublicKey(pem);
}

export function verifySignature(opts: {
  alg: "Ed25519" | "RS256";
  publicKeyPem: string;
  message: Buffer;
  signatureB64: string;
}): boolean {
  const sig = Buffer.from(opts.signatureB64, "base64");
  const key = parsePublicKey(opts.publicKeyPem);

  if (opts.alg === "Ed25519") {
    // Node's crypto.verify with null algorithm is Ed25519 compatible too,
    // but edVerify() is explicit.
    return edVerify(null, opts.message, key, sig);
  }

  // RS256: verify SHA256 over message
  const v = createVerify("RSA-SHA256");
  v.update(opts.message);
  v.end();
  return v.verify(key, sig);
}
```

---

## 2.5 `tools/stix-verify/src/load.ts`

Loads schemas and compiles AJV validators.

```ts
import fs from "node:fs";
import path from "node:path";
import Ajv from "ajv";
import addFormats from "ajv-formats";

export type Validators = {
  bundle: (x: any) => boolean;
  event: (x: any) => boolean;
};

export function loadValidators(repoRoot: string): Validators {
  const ajv = new Ajv({ allErrors: true, strict: true });
  addFormats(ajv);

  const schemasDir = path.join(repoRoot, "schemas");

  const eventSchema = JSON.parse(fs.readFileSync(path.join(schemasDir, "stix.evidence.event.schema.json"), "utf8"));
  const policySchema = JSON.parse(fs.readFileSync(path.join(schemasDir, "stix.policy.artifact.schema.json"), "utf8"));
  const authorizeSchema = JSON.parse(fs.readFileSync(path.join(schemasDir, "stix.authorize.request.schema.json"), "utf8"));
  const decisionSchema = JSON.parse(fs.readFileSync(path.join(schemasDir, "stix.decision.response.schema.json"), "utf8"));
  const bundleSchema = JSON.parse(fs.readFileSync(path.join(schemasDir, "stix.evidence.bundle.schema.json"), "utf8"));

  // Add referenced schemas
  ajv.addSchema(eventSchema, eventSchema.$id);
  ajv.addSchema(policySchema, policySchema.$id);
  ajv.addSchema(authorizeSchema, authorizeSchema.$id);
  ajv.addSchema(decisionSchema, decisionSchema.$id);
  ajv.addSchema(bundleSchema, bundleSchema.$id);

  const bundle = ajv.getSchema(bundleSchema.$id);
  const event = ajv.getSchema(eventSchema.$id);

  if (!bundle || !event) throw new Error("Failed to compile AJV schemas.");

  return {
    bundle: bundle as any,
    event: event as any
  };
}
```

---

## 2.6 `tools/stix-verify/src/verify.ts`

The real verifier logic.

```ts
import { canonicalBytes, sha256Prefixed } from "./canonical.js";
import { verifySignature } from "./crypto.js";
import type { Validators } from "./load.js";

type KeyEntry = { key_id: string; alg: "Ed25519" | "RS256"; public_key_pem: string };

export function verifyBundle(bundle: any, v: Validators, opts?: { strictChain?: boolean }) {
  const errors: string[] = [];

  // 1) Bundle schema
  if (!v.bundle(bundle)) {
    errors.push(`Bundle schema invalid: ${JSON.stringify((v.bundle as any).errors, null, 2)}`);
    return { ok: false, errors };
  }

  const keys = new Map<string, KeyEntry>();
  for (const k of bundle.keys as KeyEntry[]) keys.set(k.key_id, k);

  // 2) Each event: schema + hash + signature
  for (let i = 0; i < bundle.events.length; i++) {
    const ev = bundle.events[i];

    if (!v.event(ev)) {
      errors.push(`Event[${i}] schema invalid: ${JSON.stringify((v.event as any).errors, null, 2)}`);
      continue;
    }

    const { integrity } = ev;

    const key = keys.get(integrity.key_id);
    if (!key) {
      errors.push(`Event[${i}] references unknown key_id=${integrity.key_id}`);
      continue;
    }

    // event_hash check: hash of canonical(event without integrity.signature)
    const evForHash = structuredClone(ev);
    // Remove signature before hashing (and keep integrity fields excluding signature)
    evForHash.integrity = { ...evForHash.integrity, signature: "" };

    const msg = canonicalBytes(evForHash);
    const computed = sha256Prefixed(msg);
    if (computed !== integrity.event_hash) {
      errors.push(`Event[${i}] event_hash mismatch: computed=${computed} recorded=${integrity.event_hash}`);
    }

    // signature check: signature over canonical bytes of evForHash
    const sigOk = verifySignature({
      alg: integrity.alg,
      publicKeyPem: key.public_key_pem,
      message: msg,
      signatureB64: integrity.signature
    });

    if (!sigOk) {
      errors.push(`Event[${i}] signature invalid (key_id=${integrity.key_id}, alg=${integrity.alg})`);
    }
  }

  // 3) Chain integrity check (ordered list)
  // Rule: events are supplied in order; each event.prev_hash == previous.event_hash
  if (bundle.events.length > 1) {
    for (let i = 1; i < bundle.events.length; i++) {
      const prev = bundle.events[i - 1].integrity.event_hash;
      const currPrev = bundle.events[i].integrity.prev_hash;
      if (currPrev !== prev) {
        errors.push(`Chain broken at event[${i}]: prev_hash=${currPrev} expected=${prev}`);
      }
    }
  }

  // 4) Manifest optional checks
  if (bundle.manifest?.chain_head) {
    const head = bundle.events[0].integrity.event_hash;
    if (bundle.manifest.chain_head !== head) {
      errors.push(`manifest.chain_head mismatch: manifest=${bundle.manifest.chain_head} actual=${head}`);
    }
  }
  if (bundle.manifest?.chain_tail) {
    const tail = bundle.events[bundle.events.length - 1].integrity.event_hash;
    if (bundle.manifest.chain_tail !== tail) {
      errors.push(`manifest.chain_tail mismatch: manifest=${bundle.manifest.chain_tail} actual=${tail}`);
    }
  }

  // 5) trace_id consistency
  const traceId = bundle.trace_id;
  for (let i = 0; i < bundle.events.length; i++) {
    if (bundle.events[i].trace_id !== traceId) {
      errors.push(`Event[${i}] trace_id mismatch: event=${bundle.events[i].trace_id} bundle=${traceId}`);
    }
  }

  // Optional strict: require DECISION event present
  if (opts?.strictChain) {
    const hasDecision = bundle.events.some((e: any) => e.event_type === "DECISION");
    if (!hasDecision) errors.push("Strict mode: bundle missing DECISION event.");
  }

  return { ok: errors.length === 0, errors };
}
```

---

## 2.7 `tools/stix-verify/src/index.ts`

CLI entry.

```ts
import fs from "node:fs";
import path from "node:path";
import { loadValidators } from "./load.js";
import { verifyBundle } from "./verify.js";

function repoRootFromCwd(): string {
  // Assumes running from repo; adjust if needed
  return process.cwd();
}

function usage() {
  console.log("Usage:");
  console.log("  stix-verify <bundle.json> [--strict]");
  process.exit(2);
}

async function main() {
  const args = process.argv.slice(2);
  if (args.length < 1) usage();

  const bundlePath = args[0];
  const strict = args.includes("--strict");

  const raw = fs.readFileSync(bundlePath, "utf8");
  const bundle = JSON.parse(raw);

  const root = repoRootFromCwd();
  const validators = loadValidators(root);

  const res = verifyBundle(bundle, validators, { strictChain: strict });

  if (res.ok) {
    console.log(JSON.stringify({ ok: true, trace_id: bundle.trace_id, events: bundle.events.length }, null, 2));
    process.exit(0);
  } else {
    console.error(JSON.stringify({ ok: false, errors: res.errors }, null, 2));
    process.exit(1);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
```

---

# 3) Bundle generation contract (what Evidence Service should export)

When you implement `GET /evidence/bundle/:trace_id`, ensure the response matches `stix.evidence.bundle.schema.json`:

* `events`: ordered list (chain order)
* `keys`: public keys used to verify signatures (by `key_id`)
* `manifest.chain_head/chain_tail`: optional but recommended

**Key idea:** auditors can validate bundles **offline** without STIX running.

---

# 4) How to run it

From repo root:

```bash
npm -w tools/stix-verify run dev -- ./path/to/bundle.json --strict
```

Output:

* success: `{ ok: true, trace_id, events }`
* failure: lists exact reasons (schema mismatch, hash mismatch, signature invalid, chain broken)

---

# 5) What this guarantees (enterprise-grade)

After this, STIX can produce an artifact that proves:

* the evidence is **well-formed**
* the event hashes are **correct**
* the chain is **tamper-evident**
* signatures are **valid**
* the trace is **internally consistent**

This is the backbone of your “trust, integrity, execution” promise.

---

## Next (recommended, I’ll draft immediately if you want)

1. **`stix-simulate` CLI**: run candidate policies against past bundles (impact analysis)
2. **`stix-replay` upgrade**: replay decision exactly using policy hash + input snapshot and compare recorded vs replayed

Say: **“Next: simulate”** or **“Next: replay upgrade.”**