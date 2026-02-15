STIX SIMULATION ENGINE

Perfect.
This is the **STIX Simulation Engine** — the piece enterprises *need* before they dare to enforce policies in prod.

What follows is a **complete, concrete design + reference implementation spec** for **`stix-simulate`**, fully aligned with everything we’ve already built (HIPAA pack, schemas, verifier).

---

# STIX SIMULATION ENGINE

**Purpose:**
Safely answer:

> *“What would have happened if this policy existed last week?”*

Without blocking anything.

---

## 1️⃣ What “Simulate” Means in STIX (Very Precise)

Simulation is **not**:

* a replay of a single decision (that’s replay)
* a best-effort prediction
* a dashboard toy

Simulation **is**:

* Deterministic re-evaluation of **historical evidence**
* Using a **candidate policy set**
* Producing **impact metrics + diffs**
* Without writing new evidence
* Without changing runtime behavior

> Simulation is how compliance teams approve enforcement.

---

## 2️⃣ Inputs & Outputs

### Inputs

1. **Evidence bundles** (exported from Evidence Service)
2. **Candidate policy pack** (Git branch / folder / archive)
3. Optional:

   * time window
   * tenant
   * action/resource filters

### Outputs

* Decision deltas:

  * ALLOW → DENY
  * ALLOW → QUARANTINE
  * QUARANTINE → DENY
* Obligation diffs
* Approval volume estimates
* False positive candidates
* Summary report (JSON + human-readable)

---

## 3️⃣ Simulation Architecture

```text
┌────────────────────┐
│ Evidence Bundles   │  (past reality)
└─────────┬──────────┘
          │
          ▼
┌──────────────────────────┐
│ Simulation Engine        │
│  - canonical input load  │
│  - policy compile        │
│  - deterministic eval   │
│  - diff engine           │
└─────────┬────────────────┘
          │
          ▼
┌──────────────────────────┐
│ Simulation Report        │
│  - metrics               │
│  - deltas                │
│  - risk summary          │
└──────────────────────────┘
```

**Critical rule:**
Simulation **never** calls Enforcer, Evidence Service, or Approval Service.

---

## 4️⃣ CLI Interface

### Command

```bash
stix-simulate \
  --evidence ./bundles/ \
  --policies ./policies/packs/hipaa \
  --baseline current \
  --output ./report.json
```

### Options

```text
--evidence <dir|file>     Evidence bundles (JSON)
--policies <dir>          Candidate policy pack
--baseline <hash|current> Baseline policy set
--since <ISO time>        Optional start time
--until <ISO time>        Optional end time
--strict                  Require DECISION + OUTCOME events
--format json|md          Output format
```

---

## 5️⃣ Simulation Data Model

### 5.1 Canonical Simulation Input

Derived from evidence DECISION event:

```ts
type SimulationInput = {
  trace_id: string;
  actor: object;
  action: string;
  resource: object;
  context: object;
  signals: object;
  recorded_decision: "ALLOW" | "DENY" | "QUARANTINE";
  recorded_policy_hash: string;
  recorded_obligations: string[];
};
```

> This guarantees **identical input** to runtime evaluation.

---

### 5.2 Simulation Result

```ts
type SimulationResult = {
  trace_id: string;
  recorded: {
    decision: string;
    obligations: string[];
    policy_hash: string;
  };
  simulated: {
    decision: string;
    obligations: string[];
    policy_id: string;
    policy_hash: string;
  };
  delta: {
    decision_changed: boolean;
    obligations_changed: boolean;
    risk_level: "LOW" | "MEDIUM" | "HIGH";
  };
};
```

---

## 6️⃣ Impact Metrics (What Enterprises Care About)

### Aggregated Metrics

```json
{
  "total_traces": 12483,
  "decision_changes": {
    "allow_to_deny": 312,
    "allow_to_quarantine": 91,
    "quarantine_to_deny": 27
  },
  "approval_volume_estimate": 118,
  "high_risk_blocks": 64,
  "unchanged": 12053
}
```

### Why this matters

* Compliance: *“How many actions would now be blocked?”*
* Security: *“What risks were previously allowed?”*
* Ops: *“How many approvals will we need?”*

---

## 7️⃣ Deterministic Evaluation Rules (Non-Negotiable)

Simulation uses the **exact same rules** as runtime:

1. Policy ordering by `priority`
2. Same tie-break rules
3. Same condition evaluation
4. Same obligation resolution
5. Same default deny

> If simulation ≠ runtime → STIX is broken.

---

## 8️⃣ Reference Implementation (TypeScript)

### 8.1 Repo layout

```text
tools/stix-simulate/
  package.json
  tsconfig.json
  src/
    index.ts
    loadEvidence.ts
    loadPolicies.ts
    evaluate.ts
    diff.ts
    report.ts
```

---

### 8.2 `loadEvidence.ts`

```ts
export function loadSimulationInputs(bundles: any[]): SimulationInput[] {
  const inputs: SimulationInput[] = [];

  for (const bundle of bundles) {
    const decisionEvent = bundle.events.find(
      (e: any) => e.event_type === "DECISION"
    );
    if (!decisionEvent) continue;

    const p = decisionEvent.payload;

    inputs.push({
      trace_id: decisionEvent.trace_id,
      actor: p.actor,
      action: p.action,
      resource: p.resource,
      context: p.context,
      signals: p.context?.signals ?? {},
      recorded_decision: p.decision,
      recorded_policy_hash: p.policy_hash,
      recorded_obligations: p.obligations?.map((o: any) => o.type) ?? []
    });
  }
  return inputs;
}
```

---

### 8.3 `evaluate.ts`

```ts
export function simulateDecision(
  input: SimulationInput,
  policyEngine: PolicyEngine
) {
  const result = policyEngine.evaluate({
    actor: input.actor,
    action: input.action,
    resource: input.resource,
    context: input.context,
    signals: input.signals
  });

  return {
    decision: result.decision,
    obligations: result.obligations.map((o: any) => o.type),
    policy_id: result.policy.id,
    policy_hash: result.policy.hash
  };
}
```

---

### 8.4 `diff.ts`

```ts
export function diffDecision(recorded: any, simulated: any) {
  const decision_changed = recorded.decision !== simulated.decision;
  const obligations_changed =
    JSON.stringify(recorded.obligations.sort()) !==
    JSON.stringify(simulated.obligations.sort());

  let risk: "LOW" | "MEDIUM" | "HIGH" = "LOW";
  if (decision_changed && simulated.decision === "DENY") risk = "HIGH";
  if (decision_changed && simulated.decision === "QUARANTINE") risk = "MEDIUM";

  return {
    decision_changed,
    obligations_changed,
    risk_level: risk
  };
}
```

---

### 8.5 `report.ts`

```ts
export function buildReport(results: SimulationResult[]) {
  const summary = {
    total_traces: results.length,
    allow_to_deny: 0,
    allow_to_quarantine: 0,
    unchanged: 0
  };

  for (const r of results) {
    if (!r.delta.decision_changed) summary.unchanged++;
    if (r.recorded.decision === "ALLOW" && r.simulated.decision === "DENY")
      summary.allow_to_deny++;
    if (r.recorded.decision === "ALLOW" && r.simulated.decision === "QUARANTINE")
      summary.allow_to_quarantine++;
  }

  return { summary, results };
}
```

---

## 9️⃣ Why Simulation Is a Killer Feature

From an enterprise architect’s lens:

| Problem                  | STIX Simulation   |
| ------------------------ | ----------------- |
| Fear of blocking prod    | Safe, offline     |
| Compliance approval      | Quantified impact |
| Policy change risk       | Deterministic     |
| Audit defensibility      | Evidence-backed   |
| Dev/Compliance alignment | Shared artifact   |

This is **why STIX becomes unavoidable**.

---

## 10️⃣ How Simulation Fits the STIX Maturity Model

| Stage     | Capability               |
| --------- | ------------------------ |
| Enforce   | Enforcer + tokens        |
| Prove     | Evidence + verifier      |
| Trust     | Replay                   |
| **Adopt** | **Simulation**           |
| Optimize  | Continuous policy tuning |

Simulation is the **adoption unlock**.

---

## What’s Next (Strong Recommendation)

The only missing piece now is:

### 🔜 **Replay Upgrade**

* Take **one trace**
* Load policy by hash
* Re-evaluate
* Produce **byte-for-byte equivalence report**

That gives:

> *“We can prove exactly why this was allowed.”*

If you’re ready, say:

👉 **Next: replay upgrade**

You’re building something very rare here — this is **compliance turned into executable truth**.