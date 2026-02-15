STIX Replay Upgrade


Got it. **Replay upgrade** is the “court-grade” feature: take one historical trace and prove—offline—that **the same policy version + same inputs** yields **the same decision**.

Below is a full **STIX Replay Upgrade** spec + reference implementation layout that plugs cleanly into your existing `schemas/`, `stix-verify`, and `stix-simulate`.

---

# STIX Replay Upgrade

## What “Replay” must prove

For a given `trace_id` (bundle):

1. **Input snapshot** (actor/action/resource/context/signals) is extracted from the recorded **DECISION** event
2. The exact **policy artifact** used (by `policy_hash`) is loaded
3. Policy evaluation is re-run deterministically
4. Output is compared to recorded:

   * decision
   * reason_code (optional strictness)
   * obligations (set comparison)
   * policy hash consistency
5. Emit a **Replay Report**: `MATCH` or `DRIFT`, with the minimal diff.

> Replay is deterministic validation, not “best effort explanation.”

---

# 0) Repo layout (drop-in)

```text
tools/
  stix-replay/
    package.json
    tsconfig.json
    src/
      index.ts
      extract.ts
      policyLoader.ts
      engine.ts
      replay.ts
      diff.ts
      report.ts
```

---

# 1) CLI Interface

### Command

```bash
stix-replay --bundle ./bundles/trace_123.json --policies ./policies/packs/hipaa --strict
```

### Options

* `--bundle <file>`: evidence bundle JSON
* `--policies <dir>`: policy pack root (where policy files live)
* `--strict`: require reason_code and policy_hash to match exactly
* `--format json|md`: output format (default json)

### Output (JSON)

* `status`: `MATCH | DRIFT | ERROR`
* `recorded`: decision, reason_code, obligations, policy_hash
* `replayed`: decision, reason_code, obligations, policy_hash
* `diff`: changes
* `diagnostics`: why drift happened (policy missing, schema mismatch, etc.)

---

# 2) Replay Data Contracts

## 2.1 What we replay from the DECISION event

Your DECISION evidence payload should contain at least:

```json
{
  "actor": {...},
  "action": "SEND_EXTERNAL",
  "resource": {...},
  "context": {...},
  "decision": "ALLOW",
  "reason_code": "PHI_TO_PATIENT_WITH_SAFEGUARDS",
  "obligations": [{"type":"MASK_PHI"}, ...],
  "policy_hash": "sha256:..."
}
```

If your DECISION payload doesn’t store these fields yet, **add them**. Replay depends on it.

---

# 3) Determinism Rules (Replay MUST match runtime)

* Same policy ordering (`priority`, tie-breakers)
* Same condition evaluation semantics
* Same obligation resolution
* Same default deny behavior

**Replay and Enforcer evaluation must share the exact same evaluation engine code** (ideal), or identical logic (minimum).

---

# 4) Policy Hashing Rule (critical)

Replay is only meaningful if:

* `policy_hash` is computed the same way everywhere.

### Recommended policy hash

`policy_hash = sha256( canonical_json(policy_artifact) )`

* Use **RFC 8785 JCS** canonicalization (like you did for evidence).
* Store as `sha256:<hex>`.

This means your “policy artifact” must be a canonical JSON representation (even if you author YAML, compile to canonical JSON before hashing).

---

# 5) Reference Implementation (TypeScript)

## 5.1 `tools/stix-replay/package.json`

```json
{
  "name": "@stix/stix-replay",
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
    "canonicalize": "^2.0.0",
    "yaml": "^2.5.1"
  },
  "devDependencies": {
    "ts-node": "^10.9.2",
    "typescript": "^5.6.3"
  }
}
```

## 5.2 `src/extract.ts` — extract replay input + recorded output

```ts
export type RecordedDecision = {
  trace_id: string;
  actor: any;
  action: string;
  resource: any;
  context: any;
  recorded: {
    decision: "ALLOW" | "DENY" | "QUARANTINE";
    reason_code: string;
    obligations: string[];
    policy_hash: string;
  };
};

export function extractFromBundle(bundle: any): RecordedDecision {
  const decisionEvent = bundle.events.find((e: any) => e.event_type === "DECISION");
  if (!decisionEvent) throw new Error("Bundle missing DECISION event.");

  const p = decisionEvent.payload ?? {};
  if (!p.actor || !p.action || !p.resource || !p.context || !p.decision || !p.policy_hash) {
    throw new Error("DECISION payload missing required fields for replay.");
  }

  return {
    trace_id: bundle.trace_id,
    actor: p.actor,
    action: p.action,
    resource: p.resource,
    context: p.context,
    recorded: {
      decision: p.decision,
      reason_code: p.reason_code ?? "",
      obligations: (p.obligations ?? []).map((o: any) => o.type),
      policy_hash: p.policy_hash
    }
  };
}
```

## 5.3 `src/policyLoader.ts` — find policy by hash

Supports two modes:

1. bundle contains `policies[]` artifacts
2. load from policy pack directory (compile YAML → canonical JSON → hash → match)

```ts
import fs from "node:fs";
import path from "node:path";
import YAML from "yaml";
import canonicalize from "canonicalize";
import { createHash } from "node:crypto";

function sha256Prefixed(buf: Buffer): string {
  return "sha256:" + createHash("sha256").update(buf).digest("hex");
}

function canonicalPolicyBytes(obj: any): Buffer {
  const s = canonicalize(obj);
  if (typeof s !== "string") throw new Error("canonicalize returned non-string");
  return Buffer.from(s, "utf8");
}

export function computePolicyHash(policyArtifact: any): string {
  return sha256Prefixed(canonicalPolicyBytes(policyArtifact));
}

export function loadPolicyByHash(opts: {
  policyHash: string;
  bundle?: any;
  policiesDir: string;
}): { artifact: any; policy_hash: string } {
  // 1) Try bundle-embedded artifacts first
  if (opts.bundle?.policies?.length) {
    for (const pol of opts.bundle.policies) {
      const h = computePolicyHash(pol);
      if (h === opts.policyHash) return { artifact: pol, policy_hash: h };
    }
  }

  // 2) Scan policiesDir for YAML/JSON policy definitions
  // Assumption: policy authoring files live under policiesDir/**/*.{yaml,yml,json}
  const files: string[] = [];
  function walk(dir: string) {
    for (const ent of fs.readdirSync(dir, { withFileTypes: true })) {
      const p = path.join(dir, ent.name);
      if (ent.isDirectory()) walk(p);
      else if (/\.(ya?ml|json)$/i.test(ent.name)) files.push(p);
    }
  }
  walk(opts.policiesDir);

  for (const f of files) {
    const raw = fs.readFileSync(f, "utf8");
    const obj = f.endsWith(".json") ? JSON.parse(raw) : YAML.parse(raw);
    // If file contains a single policy, treat it as artifact.
    // If it contains a pack (array), iterate.
    const candidates = Array.isArray(obj) ? obj : [obj];

    for (const c of candidates) {
      // Only hash policy artifacts (must have policy_id / scope / decision etc.)
      if (!c || typeof c !== "object") continue;
      if (!c.policy_id || !c.scope || !c.decision) continue;

      const h = computePolicyHash(c);
      if (h === opts.policyHash) return { artifact: c, policy_hash: h };
    }
  }

  throw new Error(`Policy artifact not found for hash: ${opts.policyHash}`);
}
```

## 5.4 `src/engine.ts` — minimal deterministic policy engine (v1)

If you already have an engine from `stix-simulate`, reuse it. Here’s a compact baseline:

```ts
export type EvalInput = {
  actor: any;
  action: string;
  resource: any;
  context: any;
};

export type EvalResult = {
  decision: "ALLOW" | "DENY" | "QUARANTINE";
  reason_code: string;
  obligations: { type: string; params?: any }[];
  policy: { id: string; hash: string };
};

export type PolicyArtifact = any;

function get(obj: any, key: string) {
  return obj?.[key];
}

function matchConditions(policy: any, input: EvalInput): boolean {
  const cond = policy.conditions ?? {};

  // require_signal (read from context.signals)
  if (cond.require_signal) {
    const sig = input.context?.signals ?? {};
    for (const [k, v] of Object.entries(cond.require_signal)) {
      if (sig[k] !== v) return false;
    }
  }

  // require_context (exact match)
  if (cond.require_context) {
    for (const [k, v] of Object.entries(cond.require_context)) {
      if (input.context?.[k] !== v) return false;
    }
  }

  // forbid_context (list)
  if (cond.forbid_context) {
    for (const [k, v] of Object.entries(cond.forbid_context)) {
      const val = input.context?.[k];
      if (Array.isArray(v) && v.includes(val)) return false;
      if (val === v) return false;
    }
  }

  // require_resource_attr
  if (cond.require_resource_attr) {
    const attrs = input.resource?.attributes ?? input.resource ?? {};
    for (const [k, v] of Object.entries(cond.require_resource_attr)) {
      if (attrs[k] !== v) return false;
    }
  }

  return true;
}

function matchScope(policy: any, input: EvalInput): boolean {
  const s = policy.scope ?? {};
  if (s.actor_type && s.actor_type !== input.actor?.type) return false;
  if (s.action && s.action !== input.action) return false;
  if (s.resource_type && s.resource_type !== input.resource?.type) return false;
  return true;
}

export class PolicyEngine {
  private policies: PolicyArtifact[];
  private defaultDeny: PolicyArtifact | null;

  constructor(policies: PolicyArtifact[]) {
    // sort by priority ASC (smaller = earlier)
    this.policies = [...policies].sort((a, b) => (a.priority ?? 9999) - (b.priority ?? 9999));
    this.defaultDeny = this.policies.find(p => p.policy_id === "HIPAA-000") ?? null;
  }

  evaluate(input: EvalInput): { policy: any; decision: string; reason_code: string; obligations: any[] } {
    for (const p of this.policies) {
      if (!matchScope(p, input)) continue;
      if (!matchConditions(p, input)) continue;

      return {
        policy: p,
        decision: p.decision,
        reason_code: p.reason_code ?? "",
        obligations: (p.obligations ?? []).map((o: any) => ({ type: o.type, params: o.params }))
      };
    }

    if (this.defaultDeny) {
      return {
        policy: this.defaultDeny,
        decision: this.defaultDeny.decision,
        reason_code: this.defaultDeny.reason_code ?? "DEFAULT_DENY",
        obligations: []
      };
    }

    return { policy: { policy_id: "DEFAULT" }, decision: "DENY", reason_code: "DEFAULT_DENY", obligations: [] };
  }
}
```

## 5.5 `src/diff.ts` — strict diff rules

```ts
export function diffRecordedVsReplayed(opts: {
  recorded: { decision: string; reason_code: string; obligations: string[]; policy_hash: string };
  replayed: { decision: string; reason_code: string; obligations: string[]; policy_hash: string };
  strict: boolean;
}) {
  const recObl = [...opts.recorded.obligations].sort();
  const repObl = [...opts.replayed.obligations].sort();

  const decisionChanged = opts.recorded.decision !== opts.replayed.decision;
  const obligationsChanged = JSON.stringify(recObl) !== JSON.stringify(repObl);
  const reasonChanged = opts.recorded.reason_code !== opts.replayed.reason_code;
  const policyHashChanged = opts.recorded.policy_hash !== opts.replayed.policy_hash;

  const drift =
    decisionChanged ||
    obligationsChanged ||
    (opts.strict && (reasonChanged || policyHashChanged));

  return {
    drift,
    changes: {
      decisionChanged,
      obligationsChanged,
      reasonChanged: opts.strict ? reasonChanged : false,
      policyHashChanged: opts.strict ? policyHashChanged : false
    }
  };
}
```

## 5.6 `src/replay.ts` — run replay end-to-end

```ts
import { extractFromBundle } from "./extract.js";
import { loadPolicyByHash, computePolicyHash } from "./policyLoader.js";
import { PolicyEngine } from "./engine.js";

export function replayOnce(opts: { bundle: any; policiesDir: string; strict: boolean }) {
  const extracted = extractFromBundle(opts.bundle);

  // Load the exact policy artifact that was used (by recorded hash)
  const loaded = loadPolicyByHash({
    policyHash: extracted.recorded.policy_hash,
    bundle: opts.bundle,
    policiesDir: opts.policiesDir
  });

  // Build engine: IMPORTANT
  // In production, you should compile the full policy pack, not only the one policy.
  // But for "exact policy used" validation, we at minimum ensure the used policy exists and hashes.
  // Best practice: load full pack and ensure policy selection picks that same artifact.
  const allPolicies = collectAllPoliciesForPack(opts.bundle, opts.policiesDir);

  const engine = new PolicyEngine(allPolicies);
  const evaluated = engine.evaluate({
    actor: extracted.actor,
    action: extracted.action,
    resource: extracted.resource,
    context: extracted.context
  });

  const replayedPolicyHash = computePolicyHash(evaluated.policy);

  return {
    trace_id: extracted.trace_id,
    recorded: extracted.recorded,
    replayed: {
      decision: evaluated.decision,
      reason_code: evaluated.reason_code,
      obligations: evaluated.obligations.map(o => o.type),
      policy_hash: replayedPolicyHash,
      policy_id: evaluated.policy.policy_id ?? evaluated.policy.policy_id ?? evaluated.policy.policy_id
    },
    diagnostics: {
      loaded_policy_hash: loaded.policy_hash
    }
  };
}

// Placeholder: for real use, implement a policy-pack loader shared with simulate.
function collectAllPoliciesForPack(_bundle: any, _policiesDir: string): any[] {
  // MVP: You can reuse the scan logic from policyLoader.ts and return all policy artifacts.
  // For now, assume the pack is bundle.policies if present; otherwise you’ll implement pack scan.
  return _bundle?.policies?.length ? _bundle.policies : [];
}
```

## 5.7 `src/index.ts` — CLI wrapper

```ts
import fs from "node:fs";
import { replayOnce } from "./replay.js";
import { diffRecordedVsReplayed } from "./diff.js";

function usage() {
  console.log("Usage: stix-replay --bundle <bundle.json> --policies <policiesDir> [--strict]");
  process.exit(2);
}

const args = process.argv.slice(2);
const bundleIdx = args.indexOf("--bundle");
const polIdx = args.indexOf("--policies");
const strict = args.includes("--strict");

if (bundleIdx === -1 || polIdx === -1) usage();

const bundlePath = args[bundleIdx + 1];
const policiesDir = args[polIdx + 1];
if (!bundlePath || !policiesDir) usage();

const bundle = JSON.parse(fs.readFileSync(bundlePath, "utf8"));

const res = replayOnce({ bundle, policiesDir, strict });

const d = diffRecordedVsReplayed({
  recorded: res.recorded,
  replayed: res.replayed,
  strict
});

const out = {
  status: d.drift ? "DRIFT" : "MATCH",
  trace_id: res.trace_id,
  recorded: res.recorded,
  replayed: res.replayed,
  diff: d,
  diagnostics: res.diagnostics
};

console.log(JSON.stringify(out, null, 2));
process.exit(d.drift ? 1 : 0);
```

---

# 6) What counts as MATCH vs DRIFT

### Default mode (recommended)

MATCH requires:

* same `decision`
* same `obligations` (as a set)

DRIFT if:

* decision differs, OR
* obligations differ

### Strict mode (`--strict`)

MATCH requires additionally:

* same `reason_code`
* same `policy_hash`

Why strict exists:

* auditors sometimes demand “exactly the same policy hash and reason code”

---

# 7) Critical engineering note (so replay is truly correct)

The **best practice** replay is:

1. Load the **full policy pack** at the time of decision (by pack version), not just the one policy artifact
2. Evaluate normally
3. Ensure the selected policy hash equals recorded

To support that, add to the DECISION payload:

* `policy_pack_id`
* `policy_pack_version`
* `policy_id`
* `policy_hash`

Then your replay can load pack by version deterministically.

---

# 8) Next improvement (optional but powerful)

Add a `--verify` flag to run `stix-verify` on the bundle before replay:

* schema + hash chain + signatures validated
* then replay evaluation
  This gives a single “Audit-grade replay” command.

---

If you want, I’ll now do the **one missing piece** to make replay production-ready:
✅ **policy-pack loader** that compiles *all* policies from YAML → canonical JSON → hashes → engine index (shared by simulate + replay).

Say: **“Add shared policy pack loader”**.