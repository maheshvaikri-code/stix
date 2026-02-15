# STIX — Shield, Trust & Integrity eXecution

## Comprehensive Documentation

**Version:** 1.0  
**Status:** Architecture & Design Specification  
**Last Updated:** January 2026

---

# Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [What STIX Is — And Is Not](#2-what-stix-is--and-is-not)
3. [Design Principles](#3-design-principles)
4. [Architecture Overview](#4-architecture-overview)
5. [Core Components](#5-core-components)
6. [The Unavoidability Mechanism](#6-the-unavoidability-mechanism)
7. [Guardrail Domains](#7-guardrail-domains)
8. [Data Architecture](#8-data-architecture)
9. [Policy Lifecycle](#9-policy-lifecycle)
10. [Agent SDK Ergonomics](#10-agent-sdk-ergonomics)
11. [Verification & Replay](#11-verification--replay)
12. [Security Architecture](#12-security-architecture)
13. [Mental Models](#13-mental-models)
14. [Sequence Flows](#14-sequence-flows)
15. [Use Cases](#15-use-cases)
16. [Capabilities](#16-capabilities)
17. [Features](#17-features)
18. [Market Positioning](#18-market-positioning)
19. [Implementation Blueprint](#19-implementation-blueprint)
20. [Summary](#20-summary)

---

# 1. Executive Summary

## 1.1 Definition

**STIX** is a **deterministic, execution-path enforcement layer** that shields regulated systems and AI agents from non-compliant actions by making policy evaluation mandatory before any guarded action executes — while producing tamper-evident, regulator-readable evidence by construction.

## 1.2 The Core Promise

| Word | Meaning in STIX |
|------|-----------------|
| **Shield** | Blocks non-compliant actions before they execute |
| **Trust** | Deterministic, replayable decisions that auditors can verify |
| **Integrity** | Tamper-evident, hash-chained, signed evidence |
| **eXecution** | Enforcement happens in the execution path, not after the fact |

## 1.3 The One-Sentence Definition

> *"STIX shields systems by enforcing risk, compliance, regulation, and audit requirements at runtime — making policy evaluation a mandatory step in the execution path."*

## 1.4 Core Guarantees

| Guarantee | Description |
|-----------|-------------|
| **All guarded actions are mediated** | Nothing reaches the target without a STIX decision |
| **Decisions are explainable and reproducible** | Same input + same policy = same outcome |
| **Evidence is produced automatically** | No ALLOW without an audit record |

## 1.5 Key Differentiators

| What Others Do | What STIX Does |
|----------------|----------------|
| Detect violations after | **Block violations before** |
| Advisory guardrails | **Enforcing guardrails** |
| Post-facto audit reporting | **Evidence by construction** |
| "We support compliance" checklists | **"Compliance is technically enforced"** |
| Trust teams to follow rules | **Systems that cannot break rules** |

---

# 2. What STIX Is — And Is Not

## 2.1 STIX IS:

- ✅ An **execution-path guardrail layer**
- ✅ A **deterministic policy enforcement engine**
- ✅ A **tamper-evident evidence system**
- ✅ A **control primitive** that other systems integrate with
- ✅ A **shield** against non-compliant execution

## 2.2 STIX IS NOT:

- ❌ A System of Record for business data
- ❌ A GRC platform or SIEM replacement
- ❌ An AI observability or monitoring tool
- ❌ A risk scoring engine
- ❌ A compliance reporting dashboard
- ❌ A data warehouse

## 2.3 The Critical Distinction

> *"STIX enforces and proves compliance; your systems remain the system of record."*

STIX stores **control evidence** (decisions, context snapshots, policy references), never **business records** (customer data, transactions, PHI/PCI contents).

## 2.4 Storage Boundary

| ✅ STIX Stores | ❌ STIX Never Stores |
|----------------|----------------------|
| Decisions (ALLOW/DENY/QUARANTINE) | Customer records |
| Context snapshots (safe fields only) | Financial transactions |
| Policy references (id, version, hash) | Claims / medical data |
| Control & regulation mappings | Full PII/PHI/PCI payloads |
| Tamper-evident integrity metadata | Business state |
| Outcome status summaries | Raw sensitive content |

---

# 3. Design Principles

| Principle | Description |
|-----------|-------------|
| **Fail-Closed** | Compliance failure = execution stops (especially for high-risk actions) |
| **Zero-Trust Execution** | No action is trusted without validation |
| **Policy as Code** | Regulations encoded as enforceable, testable logic |
| **Deterministic** | Same request + same policy version = same decision (always) |
| **No Bypass Path** | Protected targets reject calls without STIX proof |
| **Evidence-by-Construction** | No ALLOW without an evidence event |
| **Least Payload** | Store summaries, hashes, classifications — never raw PII/PHI/PCI |
| **Regulator-Readable** | Outputs make sense to auditors, not just engineers |
| **Composable** | Integrates with existing systems; doesn't replace them |
| **Auditable** | Every decision produces verifiable proof |

---

# 4. Architecture Overview

## 4.1 High-Level Flow

```
┌──────────────────────────────────────────────────┐
│           Actors (Humans / Apps / Agents / Jobs)  │
└──────────────────────────────────────────────────┘
                        │ Intent (action + resource + context)
                        ▼
┌──────────────────────────────────────────────────┐
│           STIX Enforcement Plane                  │
│  ┌────────────────────────────────────────────┐  │
│  │  1. Context Resolver                       │  │
│  │     • Identity / Role / Tenant             │  │
│  │     • Environment (dev/test/prod)          │  │
│  │     • Data Classification                  │  │
│  │     • Jurisdiction                         │  │
│  │                                            │  │
│  │  2. Policy Engine (Deterministic)          │  │
│  │     • Versioned rules                      │  │
│  │     • Reason codes                         │  │
│  │     • Control/regulation mapping           │  │
│  │                                            │  │
│  │  3. Obligation Engine                      │  │
│  │     • Redaction / Masking                  │  │
│  │     • Approvals / Rate limits              │  │
│  │                                            │  │
│  │  4. Decision Engine                        │  │
│  │     • ALLOW / DENY / QUARANTINE            │  │
│  │                                            │  │
│  │  5. Evidence Engine                        │  │
│  │     • Canonicalize → Hash → Sign → Store   │  │
│  └────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────┘
                        │
           ┌────────────┴────────────┐
           ▼                         ▼
    ┌──────────────┐        ┌────────────────┐
    │   EXECUTE    │        │ BLOCK / HOLD   │
    │ (with proof) │        │ (with reason)  │
    └──────────────┘        └────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────┐
│        Protected Targets                          │
│   (APIs / Data / Models / Tools / CI-CD)          │
└──────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────┐
│        Evidence Stores                            │
│   Hot Query Store    │    Immutable Vault         │
│   (operational)      │    (regulator-grade)       │
└──────────────────────────────────────────────────┘
```

## 4.2 Deployment Choke Points

STIX achieves **unavoidability** by sitting at architectural choke points:

| Choke Point | What It Guards | Priority |
|-------------|----------------|----------|
| **Agent SDK / Tool Bus** | All agent tool calls | Primary |
| **LLM Gateway** | Prompts and model outputs | High |
| **API Gateway / Service Mesh** | Service-to-service calls | High |
| **Data Gateway** | Database queries and data exports | High |
| **CI/CD Pipeline** | Deployment and infrastructure changes | Medium |

**Recommendation:** Deploy at least **two choke points** for defense-in-depth.

## 4.3 Logical Components

```
┌─────────────────────────────────────────────────────────────┐
│                    STIX ENFORCEMENT PLANE                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   Context   │  │   Policy    │  │     Obligation      │  │
│  │  Resolver   │──│   Engine    │──│       Engine        │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│         │               │                    │              │
│         └───────────────┼────────────────────┘              │
│                         ▼                                   │
│                  ┌─────────────┐                            │
│                  │  Decision   │                            │
│                  │   Engine    │                            │
│                  └─────────────┘                            │
│                         │                                   │
│                         ▼                                   │
│                  ┌─────────────┐                            │
│                  │  Evidence   │                            │
│                  │   Engine    │                            │
│                  └─────────────┘                            │
│                         │                                   │
│         ┌───────────────┴───────────────┐                   │
│         ▼                               ▼                   │
│  ┌─────────────┐                ┌─────────────┐            │
│  │  Hot Store  │                │   Immutable │            │
│  │  (Query)    │                │    Vault    │            │
│  └─────────────┘                └─────────────┘            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

# 5. Core Components

## 5.1 STIX Enforcer (Authorization Service)

**Purpose:** Central authorization and token minting service

**Responsibilities:**
- Validate request identity & context
- Select policy set by tenant/environment/action/resource
- Evaluate policy deterministically
- Return decision + obligations + trace_id
- Mint **STIX Proof Token** on ALLOW
- Record execution outcomes

**Key Endpoints:**

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/authorize` | POST | Evaluate action and return decision |
| `/outcome` | POST | Record execution result (success/failure) |
| `/explain/{trace_id}` | GET | Get decision explanation |
| `/keys` | GET | Public keys for token verification |
| `/health` | GET | Service health check |

## 5.2 Policy Engine (Policy-as-Code)

**Purpose:** Deterministic policy evaluation

**Characteristics:**
- Versioned, immutable policy artifacts
- Deterministic evaluation (no external calls, no randomness)
- Produces: reason codes, obligations, control/regulation mapping

**Policy Structure (YAML):**

```yaml
policy_id: STIX-AI-001
version: 1.0.0
priority: 10                    # Lower = higher priority

scope:
  actor_type: AI_AGENT
  action: SEND_EXTERNAL
  resource_type: MESSAGE

conditions:
  env: prod
  require_signal:
    piiDetected: true
  require_resource_attr:
    destination: EXTERNAL

decision: DENY
reason_code: DATA_EGRESS_EXTERNAL_PII

obligations: []                 # Optional obligations for ALLOW

controls: [DLP-01]
regulations: [GDPR.Art5, PCI-DSS.3]
```

**Conflict Resolution (Deny-Wins):**

| Priority | Rule |
|----------|------|
| 1st | **Priority field** (lower number wins) |
| 2nd | **Decision rank** (DENY < QUARANTINE < ALLOW) |
| 3rd | **Policy ID** (lexicographic tie-breaker) |

## 5.3 Context Resolver

**Purpose:** Assemble decision context from multiple sources

**Context Sources:**

| Source | Data Collected |
|--------|----------------|
| Identity Provider | Actor ID, type, role, tenant |
| Environment | dev/test/stage/prod |
| Classification Service | Data sensitivity labels |
| SDK Signals | Local PII/PHI/PCI detection |
| Request Metadata | Jurisdiction, purpose, correlation IDs |

## 5.4 Obligation Engine

**Purpose:** Enforce constraints when action is allowed

| Obligation Type | Description |
|-----------------|-------------|
| `REDACT_FIELDS` | Remove sensitive fields before execution |
| `MASK_PII` | Replace PII with masked values (e.g., `***-**-1234`) |
| `WATERMARK_OUTPUT` | Add traceability markers to outputs |
| `REQUIRE_APPROVAL` | Pause execution for human sign-off |
| `RATE_LIMIT` | Enforce quotas and throttling |
| `LOG_LEVEL` | Increase evidence detail level |
| `ENCRYPT_TRANSIT` | Require encryption for data in transit |
| `DUAL_CONTROL` | Require two-person approval |

## 5.5 Decision Engine

**Purpose:** Return final authorization decision

| Decision | Meaning | Action |
|----------|---------|--------|
| ✅ **ALLOW** | Compliant (possibly with obligations) | Execute with proof token |
| ❌ **DENY** | Non-compliant | Block immediately |
| ⏸️ **QUARANTINE** | Requires approval | Pause, create ticket, await human |

## 5.6 Evidence Engine

**Purpose:** Create tamper-evident audit records

**Pipeline:**

```
1. CANONICALIZE  →  Stable JSON (sorted keys, minified, UTF-8)
        │
        ▼
2. HASH          →  SHA-256 of canonical event
        │
        ▼
3. CHAIN         →  Include prev_hash for tamper detection
        │
        ▼
4. SIGN          →  Ed25519 signature
        │
        ▼
5. STORE         →  Write to hot store + immutable vault
```

---

# 6. The Unavoidability Mechanism

## 6.1 STIX Proof Token

When STIX returns ALLOW, it mints a **short-lived cryptographic token** (JWT/PASETO):

```json
{
  "iss": "stix",
  "sub": "agent-42",
  "act": "SEND_EXTERNAL",
  "res": "MESSAGE",
  "cls": ["PII"],
  "pol": "sha256:abc123...",
  "tid": "stix_98fa7b2c...",
  "iat": 1700000000,
  "exp": 1700000045
}
```

**Token Properties:**

| Property | Value | Purpose |
|----------|-------|---------|
| **TTL** | 30–60 seconds | Prevent token reuse |
| **Algorithm** | Ed25519 / ES256 | Cryptographic security |
| **Scope** | Specific action/resource | Prevent scope escalation |
| **Trace ID** | Links to evidence | Auditability |
| **Policy Hash** | Version binding | Determinism |

## 6.2 Protected Target Enforcement

Every protected service/tool **MUST:**

1. ✅ Require STIX proof token in `Authorization: Bearer <token>`
2. ✅ Verify signature against STIX public key
3. ✅ Verify TTL (reject expired tokens)
4. ✅ Verify scope matches requested action/resource
5. ✅ **Reject** missing or invalid tokens with `401 Unauthorized`

**Result:** Even if someone bypasses the SDK, the protected service rejects the call.

## 6.3 Bypass Detection & Prevention

| Mechanism | Description |
|-----------|-------------|
| **Missing token events** | Logged as evidence with `BYPASS_ATTEMPT` reason |
| **Unguarded tool detection** | SDK fails startup if raw tools detected in production |
| **Attestation hooks** | Optional runtime environment verification |
| **Network policies** | Protected targets only accept connections from STIX |
| **Continuous monitoring** | Alert on bypass attempt patterns |

## 6.4 Defense in Depth

```
┌─────────────────────────────────────────────────────────┐
│                    DEFENSE LAYERS                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   Layer 1: SDK Enforcement                              │
│   └── Tool calls wrapped, authorization required        │
│                                                         │
│   Layer 2: Token Verification                           │
│   └── Protected targets verify STIX tokens              │
│                                                         │
│   Layer 3: Network Policies                             │
│   └── Only STIX can reach protected services            │
│                                                         │
│   Layer 4: Bypass Detection                             │
│   └── Missing tokens logged and alerted                 │
│                                                         │
│   Layer 5: Audit Verification                           │
│   └── Evidence integrity continuously verified          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

# 7. Guardrail Domains

## 7.1 Data Access Guardrails

**Purpose:** Control who can access what data, where, and how

| Control | Example Policy |
|---------|----------------|
| Role-based data access | "Only claims-processor role can read claims data" |
| Data flow restrictions | "PCI data cannot leave approved systems" |
| Export controls | "PHI export requires break-glass + justification" |
| Masking requirements | "PII to external destinations must be masked" |
| Geographic restrictions | "EU citizen data cannot leave EU region" |
| Purpose limitation | "Customer data only for stated purpose" |

**Example Policy:**

```yaml
policy_id: DATA-001
scope:
  actor_type: AI_AGENT
  action: DATA_EXPORT
  resource_type: CUSTOMER_RECORD

conditions:
  require_resource_attr:
    classification: PCI
    destination: EXTERNAL

decision: DENY
reason_code: PCI_EXTERNAL_EXPORT_BLOCKED
controls: [PCI-DSS-3.4]
```

## 7.2 Action Execution Guardrails

**Purpose:** Control high-risk operations and changes

| Control | Example Policy |
|---------|----------------|
| High-value transaction approvals | "Wire transfer > $10K requires manager approval" |
| Production change controls | "Prod deploy requires ticket + 2-person approval" |
| Schema change controls | "DB migration requires change request linkage" |
| Privileged action logging | "All admin actions require enhanced logging" |
| Time-based restrictions | "No production changes during freeze periods" |

**Example Policy:**

```yaml
policy_id: OPS-001
scope:
  actor_type: SERVICE
  action: DEPLOY_PROD
  resource_type: APPLICATION

conditions:
  env: prod

decision: QUARANTINE
reason_code: PROD_DEPLOY_REQUIRES_APPROVAL
approval:
  approver_role: ReleaseManager
  require_ticket: true
controls: [ITGC-CM-01]
```

## 7.3 AI / Agent Guardrails *(Primary Market Wedge)*

**Purpose:** Control autonomous AI agent behavior

| Control | Example Policy |
|---------|----------------|
| Tool access restrictions | "Agent can query KB but cannot email externally" |
| Prompt/output policy | "Prompts with PCI data blocked unless redacted" |
| Autonomous action limits | "Tool `wire_transfer` requires human approval" |
| LLM egress controls | "No sensitive data to external models" |
| Hallucination prevention | "Agent outputs must cite sources" |
| Scope limitations | "Agent cannot access data outside assigned tenant" |

**Example Policy:**

```yaml
policy_id: AGENT-001
scope:
  actor_type: AI_AGENT
  action: SEND_EXTERNAL
  resource_type: MESSAGE

conditions:
  require_signal:
    piiDetected: true

decision: DENY
reason_code: AGENT_PII_EGRESS_BLOCKED
controls: [AI-GOV-01, DLP-01]
regulations: [GDPR.Art5]
```

## 7.4 Audit Determinism Guardrails

**Purpose:** Ensure complete audit coverage

| Control | Example Policy |
|---------|----------------|
| No action without evidence | "Access without classification tag = blocked" |
| Control mapping required | "If control mapping missing → deny" |
| Structured logging | "Every decision produces regulator-readable proof" |
| Retention enforcement | "Evidence must be retained per regulation" |

---

# 8. Data Architecture

## 8.1 Canonical Schemas

### 8.1.1 Authorize Request

```json
{
  "actor": {
    "id": "agent-42",
    "type": "AI_AGENT",
    "role": "claims-processor",
    "tenant": "acme",
    "attributes": {}
  },
  "action": "SEND_EXTERNAL",
  "resource": {
    "type": "MESSAGE",
    "id": "msg-123",
    "classification": ["PII"],
    "attributes": {
      "destination_domain": "gmail.com",
      "destination": "EXTERNAL"
    }
  },
  "context": {
    "env": "prod",
    "purpose": "customer_notification",
    "run_id": "run-170...",
    "session_id": "sess-001",
    "ticket_id": "JIRA-1234",
    "jurisdiction": "US",
    "tags": ["customer-facing"],
    "signals": {
      "piiDetected": true,
      "phiDetected": false,
      "pciDetected": false,
      "secretsDetected": false
    }
  },
  "tool_call": {
    "tool": "send_email",
    "risk_tier": "HIGH",
    "args_summary": "to=external; body_len=231"
  }
}
```

### 8.1.2 Decision Response

```json
{
  "decision": "DENY",
  "reason_code": "DATA_EGRESS_EXTERNAL_PII",
  "trace_id": "stix_98fa7b2c-1234-5678-9abc-def012345678",
  "explanation": "PII detected in message body; external egress blocked by policy STIX-AI-001",
  "policy": {
    "id": "STIX-AI-001",
    "version": "1.0.0",
    "hash": "sha256:abc123def456..."
  },
  "obligations": [],
  "approval": null,
  "proof_token": null
}
```

### 8.1.3 Evidence Event (Canonical, Signed)

```json
{
  "schema_version": "1.0",
  "event_id": "evt_01J8X9Y2Z3A4B5C6D7E8F9G0H1",
  "trace_id": "stix_98fa7b2c-1234-5678-9abc-def012345678",
  "timestamp": "2026-01-22T12:34:56.789Z",

  "decision": "DENY",
  "reason_code": "DATA_EGRESS_EXTERNAL_PII",

  "actor": {
    "id": "agent-42",
    "type": "AI_AGENT",
    "role": "claims-processor",
    "tenant": "acme"
  },
  "action": {
    "name": "SEND_EXTERNAL",
    "tool": "send_email",
    "risk_tier": "HIGH"
  },
  "resource": {
    "type": "MESSAGE",
    "classification": ["PII"],
    "attributes": {
      "destination": "EXTERNAL"
    }
  },
  "context": {
    "env": "prod",
    "purpose": "customer_notification",
    "jurisdiction": "US"
  },

  "policy": {
    "id": "STIX-AI-001",
    "version": "1.0.0",
    "hash": "sha256:abc123def456..."
  },

  "controls": ["DLP-01"],
  "regulations": ["GDPR.Art5", "PCI-DSS.3"],

  "obligations_applied": {
    "redaction": false,
    "watermark": false
  },

  "outcome": {
    "status": "BLOCKED",
    "result_summary": "",
    "error_class": ""
  },

  "integrity": {
    "event_hash": "sha256:evt789ghi012...",
    "prev_hash": "sha256:prev456def...",
    "signature": "ed25519:sig123abc...",
    "key_id": "evidence-key-1"
  }
}
```

## 8.2 Canonicalization Rules

| Rule | Requirement |
|------|-------------|
| **Encoding** | UTF-8 |
| **Key ordering** | Lexicographic at every object level |
| **Timestamps** | ISO-8601 Zulu with milliseconds (`2026-01-22T12:34:56.789Z`) |
| **Whitespace** | None (minified JSON) |
| **Null handling** | Omit missing optional fields; explicit null where required |
| **Hashes** | Lowercase hex with prefix (`sha256:...`) |
| **Arrays** | Preserve order (do not sort unless schema specifies) |
| **Numbers** | No floating-point precision issues; use strings for IDs |

## 8.3 Storage Architecture

### 8.3.1 Hot Evidence Store (Query Plane)

**Purpose:** Fast search, operational queries, dashboards

| Characteristic | Value |
|----------------|-------|
| **Type** | Append-only table |
| **Partitioning** | By tenant + date |
| **Indexing** | trace_id, decision, reason_code, actor.id, action.name |
| **Retention** | Configurable (typically 90 days hot) |
| **Technology** | Postgres / ClickHouse / Elasticsearch |

### 8.3.2 Immutable Evidence Vault (Trust Plane)

**Purpose:** Regulator-grade non-repudiation, long-term retention

| Characteristic | Value |
|----------------|-------|
| **Type** | WORM storage OR hash-chained append-only log |
| **Immutability** | Object Lock / Write-once enforcement |
| **Integrity** | Hash chain + Merkle batch roots |
| **Signing** | Ed25519 signatures per event |
| **Retention** | Per regulation (e.g., 7 years for SOX) |
| **Technology** | S3 Object Lock / Azure Immutable Blob / Custom |

### 8.3.3 Policy Store

**Purpose:** Policy versioning and retrieval

| Characteristic | Value |
|----------------|-------|
| **Versioning** | Immutable versions; updates create new versions |
| **Content addressing** | Retrieve by policy hash (for replay) |
| **Change control** | Who/when/why/approval records |
| **Testing** | Test results stored per version |

---

# 9. Policy Lifecycle

## 9.1 Create (Add)

```
1. DRAFT       →  Author writes policy YAML
       │
       ▼
2. TEST        →  Run unit tests (golden allow/deny/quarantine cases)
       │
       ▼
3. SIMULATE    →  Dry-run on historical evidence (impact analysis)
       │
       ▼
4. REVIEW      →  Approval workflow (required for production)
       │
       ▼
5. PUBLISH     →  New immutable version created with content hash
```

## 9.2 Update

- **Never mutate** — Updates create new versions
- **Environment scoped** — Activation is per environment
- **Evidence generated** — Produces policy-change evidence event
- **Impact linked** — Impact report stored and linked to approval ticket

## 9.3 Delete (Deactivate)

- **Regulated deletion = deactivation only**
- **Archive immutable** — Versions retained based on regulation
- **Audited** — Deletion itself is an evidence event

## 9.4 Policy APIs

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/policies` | POST | Create new policy |
| `/policies/{id}` | PUT | Create new version |
| `/policies/{id}` | GET | Get policy by ID |
| `/policies/{id}/test` | POST | Run unit tests |
| `/policies/{id}/simulate` | POST | Impact analysis |
| `/policies/{id}/activate` | POST | Activate for environment |
| `/policies/{id}/deactivate` | POST | Deactivate policy |
| `/policy/by-hash/{hash}` | GET | Retrieve by content hash (for replay) |

## 9.5 Policy Testing

**Required Test Cases:**

| Test Type | Description |
|-----------|-------------|
| **Allow cases** | Requests that should be allowed |
| **Deny cases** | Requests that should be denied |
| **Quarantine cases** | Requests requiring approval |
| **Obligation cases** | Verify obligations are attached |
| **Edge cases** | Boundary conditions |

**Example Test:**

```yaml
tests:
  - name: "Deny PII to external"
    input:
      actor: { type: AI_AGENT }
      action: SEND_EXTERNAL
      resource: { type: MESSAGE, classification: [PII] }
      context: { signals: { piiDetected: true } }
    expected:
      decision: DENY
      reason_code: DATA_EGRESS_EXTERNAL_PII
```

---

# 10. Agent SDK Ergonomics

## 10.1 Design Goals

| Goal | Description |
|------|-------------|
| **One-line integration** | Minimal code to get started |
| **Zero policy knowledge** | Developers don't need to understand policies |
| **Fail-closed defaults** | Deny if STIX unreachable |
| **Typed results** | Structured outcomes, not booleans |
| **First-class obligations** | Automatic redaction, approvals, rate limits |
| **Automatic evidence** | No manual logging required |

## 10.2 Mental Model for Developers

> *"I register tools. STIX wraps them. The agent uses them normally. If it's not allowed, I get a structured denial that I can handle."*

## 10.3 Guarded Result Pattern

```typescript
type GuardedResult<T> =
  | { kind: "OK"; value: T; trace_id: string }
  | { kind: "DENIED"; decision: DecisionResponse }
  | { kind: "QUARANTINED"; decision: DecisionResponse };
```

Agents **must branch** on this result — no silent failures.

## 10.4 Tool Registration

```typescript
const sendEmailMeta: ToolMeta = {
  name: "send_email",
  action: "SEND_EXTERNAL",
  resourceType: "MESSAGE",
  riskTier: "HIGH",
  
  // Safe summary of arguments (no sensitive data)
  summarizeArgs: (args) => `to=${args.to}; body_len=${args.body.length}`,
  
  // Local classification signals
  classify: (args) => ({
    piiDetected: /\b\d{3}-\d{2}-\d{4}\b/.test(args.body)
  }),
  
  // Derive resource attributes
  deriveResourceAttributes: (args) => ({
    destination: "EXTERNAL",
    destination_domain: args.to.split("@")[1]
  })
};
```

## 10.5 Integration Example

```typescript
// Initialize client
const stix = new StixClient(enforcerUrl);

// Configure guardrails with actor context
const guardrails = new StixGuardrails(stix, {
  actor: { id: "agent-42", type: "AI_AGENT", role: "claims-processor" },
  context: { env: "prod", purpose: "customer_notification" }
});

// Register tools
const registry = new ToolRegistry(guardrails);
registry.add(sendEmailMeta, sendEmailHandler);
registry.add(queryDbMeta, queryDbHandler);
registry.add(httpGetMeta, httpGetHandler);

// Build guarded tools
const tools = registry.build();

// Use tools - authorization is automatic
const result = await tools["send_email"]({
  to: "customer@example.com",
  subject: "Your claim status",
  body: "Your claim has been processed."
});

// Handle result
if (result.kind === "OK") {
  console.log("Email sent:", result.value);
} else if (result.kind === "DENIED") {
  console.log("Blocked:", result.decision.reason_code);
} else if (result.kind === "QUARANTINED") {
  console.log("Needs approval:", result.decision.approval.ticket_id);
}
```

## 10.6 Agent Runtime Behavior

| Outcome | Agent Action |
|---------|--------------|
| **ALLOW** | Proceed with execution |
| **ALLOW + obligations** | SDK applies redaction/limits automatically |
| **DENY** | Pivot to safe alternative, explain to user |
| **QUARANTINE** | Request approval, wait for human, or choose safer path |

## 10.7 SDK Execution Pipeline

```
Agent calls tool(args)
        │
        ▼
SDK wraps request
        │
        ▼
POST /authorize to Enforcer
        │
        ├── DENY ──────────► Return DENIED(decision)
        │
        ├── QUARANTINE ────► Return QUARANTINED(decision)
        │
        └── ALLOW
              │
              ▼
        Apply pre-obligations (redact/mask)
              │
              ▼
        Execute tool with proof_token
              │
              ├── SUCCESS ──► POST /outcome (SUCCESS)
              │                     │
              │                     ▼
              │               Return OK(result, trace_id)
              │
              └── FAILURE ──► POST /outcome (FAILED)
                                    │
                                    ▼
                              Throw error
```

---

# 11. Verification & Replay

## 11.1 stix-verify (Integrity Verification)

**Purpose:** Validate evidence chain integrity

**Command:**
```bash
stix-verify --from 2026-01-01 --to 2026-01-31
```

**Validates:**

| Check | Description |
|-------|-------------|
| ✅ Signatures | Ed25519 signatures are valid |
| ✅ Hash chain | Each event links to previous via prev_hash |
| ✅ Merkle roots | Batch roots match computed values |
| ✅ Completeness | No gaps in event sequence |
| ✅ Configuration | Vault immutability settings verified |

**Output:**
```
Verifying evidence from 2026-01-01 to 2026-01-31...
Events checked: 15,234
Signatures valid: 15,234
Chain intact: YES
Merkle roots valid: 31/31

VERIFY PASS
```

## 11.2 stix-replay (Determinism Verification)

**Purpose:** Prove decisions are reproducible

**Command:**
```bash
stix-replay stix_98fa7b2c-1234-5678-9abc-def012345678
```

**Process:**

```
1. FETCH EVENT    →  Get evidence by trace_id
        │
        ▼
2. FETCH POLICY   →  Get policy by policy.hash
        │
        ▼
3. RE-EVALUATE    →  Run policy engine with captured context
        │
        ▼
4. COMPARE        →  Assert decision matches recorded decision
        │
        ▼
5. REPORT         →  Output match/mismatch result
```

**Output:**
```json
{
  "trace_id": "stix_98fa7b2c-1234-5678-9abc-def012345678",
  "recorded": {
    "decision": "DENY",
    "reason_code": "DATA_EGRESS_EXTERNAL_PII",
    "policy_hash": "sha256:abc123..."
  },
  "replayed": {
    "decision": "DENY",
    "reason_code": "DATA_EGRESS_EXTERNAL_PII",
    "policy_id": "STIX-AI-001",
    "version": "1.0.0"
  },
  "match": true
}
```

> *Replay is what auditors love: "Show me it would still deny today with the policy version at the time."*

---

# 12. Security Architecture

## 12.1 Trust Boundaries

```
┌─────────────────────────────────────────────────────────────┐
│                      TRUST BOUNDARIES                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   SDK ──────────────► Enforcer                              │
│         [Authenticated + Rate-limited]                      │
│                                                             │
│   Enforcer ─────────► Policy Service                        │
│         [Internal mTLS]                                     │
│                                                             │
│   Enforcer ─────────► Evidence Service                      │
│         [Internal mTLS]                                     │
│                                                             │
│   Evidence ─────────► Vault/Store                           │
│         [mTLS + Least-privileged credentials]               │
│                                                             │
│   Protected Targets ─► (verify STIX tokens)                 │
│         [Public key verification]                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## 12.2 Key Management

| Key Type | Algorithm | Storage | Rotation | Purpose |
|----------|-----------|---------|----------|---------|
| **Token signing** | Ed25519 / ES256 | KMS/HSM | 90 days | Sign proof tokens |
| **Evidence signing** | Ed25519 | KMS/HSM | 90 days | Sign evidence events |
| **mTLS certificates** | RSA-2048 / ECDSA | Cert manager | 30 days | Service authentication |

**Key Ring Management:**
- Maintain `kid` (key ID) in tokens and evidence
- Support old keys until retention requires removal
- Key compromise = revoke, rotate, publish incident evidence

## 12.3 Token Security

| Property | Requirement |
|----------|-------------|
| **TTL** | 30–60 seconds |
| **Scoped claims** | Action, resource, policy hash |
| **Auditable** | Every ALLOW token corresponds to evidence event |
| **Non-reusable** | Short TTL prevents replay attacks |

## 12.4 Fail Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| **CLOSED** (default) | Deny all high-risk actions if STIX unreachable | Production |
| **OPEN_LOW_RISK_ONLY** | Allow only pre-approved low-risk actions | Graceful degradation |
| **OPEN** | Allow all (logging only) | Development only |

## 12.5 Incident Response

| Scenario | Response |
|----------|----------|
| **Key compromise** | Revoke key, rotate, publish incident evidence, notify |
| **STIX outage** | Fail-closed for high-risk; emit outage evidence |
| **Vault write failure** | Degrade to queued durable pipeline; no ALLOW without ack |
| **Bypass detected** | Alert, log evidence, investigate, remediate |

---

# 13. Mental Models

## 13.1 Human: Policy Author

> *"I write rules that are enforced at runtime. My rule changes are versioned, tested, approved, and traceable. I can see the impact of my changes before they go live."*

**Key Activities:**
- Draft policy YAML
- Write test cases
- Review impact analysis
- Approve for production

## 13.2 Human: Auditor

> *"Every action has a trace_id, decision, policy hash, and proof signature. I can verify integrity independently. I can replay any decision to confirm it was correct."*

**Key Activities:**
- Query evidence by various dimensions
- Verify integrity with stix-verify
- Replay decisions with stix-replay
- Export evidence for external review

## 13.3 Human: Operator (SRE/SecOps)

> *"If STIX is down, risky operations stop. I can see denies by reason_code and resolve by policy or workflow. I get alerts on bypass attempts."*

**Key Activities:**
- Monitor STIX health
- Investigate deny patterns
- Respond to bypass alerts
- Manage approvals queue

## 13.4 Agent Runtime

> *"I propose actions. STIX judges them. Deny/quarantine gives reason codes; I must adjust my plan or request approval. I never 'work around' STIX — I change my approach."*

**Agent Behavior:**
- Receive structured decisions
- Pivot on denial (choose safer alternative)
- Request approval when quarantined
- Never attempt bypass

---

# 14. Sequence Flows

## 14.1 ALLOW (Happy Path)

```
Agent                SDK                 Enforcer            Policy              Evidence            Target
  │                   │                     │                   │                   │                   │
  │ call tool(args)   │                     │                   │                   │                   │
  │──────────────────►│                     │                   │                   │                   │
  │                   │ POST /authorize     │                   │                   │                   │
  │                   │────────────────────►│                   │                   │                   │
  │                   │                     │ evaluate          │                   │                   │
  │                   │                     │──────────────────►│                   │                   │
  │                   │                     │◄──────────────────│                   │                   │
  │                   │                     │ decision=ALLOW    │                   │                   │
  │                   │                     │                   │                   │                   │
  │                   │                     │ emit evidence     │                   │                   │
  │                   │                     │──────────────────────────────────────►│                   │
  │                   │                     │◄──────────────────────────────────────│                   │
  │                   │◄────────────────────│                   │                   │                   │
  │                   │ ALLOW + proof_token │                   │                   │                   │
  │                   │                     │                   │                   │                   │
  │                   │ apply obligations   │                   │                   │                   │
  │                   │ (redact/mask)       │                   │                   │                   │
  │                   │                     │                   │                   │                   │
  │                   │ execute with token  │                   │                   │                   │
  │                   │─────────────────────────────────────────────────────────────────────────────────►│
  │                   │                     │                   │                   │                   │
  │                   │◄─────────────────────────────────────────────────────────────────────────────────│
  │                   │ result              │                   │                   │                   │
  │                   │                     │                   │                   │                   │
  │                   │ POST /outcome       │                   │                   │                   │
  │                   │────────────────────►│                   │                   │                   │
  │                   │                     │──────────────────────────────────────►│                   │
  │◄──────────────────│                     │                   │                   │                   │
  │ OK(result)        │                     │                   │                   │                   │
```

## 14.2 DENY (Block)

```
Agent                SDK                 Enforcer            Policy              Evidence
  │                   │                     │                   │                   │
  │ call tool(args)   │                     │                   │                   │
  │──────────────────►│                     │                   │                   │
  │                   │ POST /authorize     │                   │                   │
  │                   │────────────────────►│                   │                   │
  │                   │                     │ evaluate          │                   │
  │                   │                     │──────────────────►│                   │
  │                   │                     │◄──────────────────│                   │
  │                   │                     │ decision=DENY     │                   │
  │                   │                     │                   │                   │
  │                   │                     │ emit evidence     │                   │
  │                   │                     │──────────────────────────────────────►│
  │                   │◄────────────────────│                   │                   │
  │                   │ DENY + reason_code  │                   │                   │
  │◄──────────────────│                     │                   │                   │
  │ DENIED(decision)  │                     │                   │                   │
  │                   │                     │                   │                   │
  │ (no execution)    │                     │                   │                   │
```

## 14.3 QUARANTINE (Approval Required)

```
Agent                SDK                 Enforcer            Approvals           Evidence
  │                   │                     │                   │                   │
  │ call tool(args)   │                     │                   │                   │
  │──────────────────►│                     │                   │                   │
  │                   │ POST /authorize     │                   │                   │
  │                   │────────────────────►│                   │                   │
  │                   │                     │ evaluate          │                   │
  │                   │                     │ decision=QUARANTINE                   │
  │                   │                     │                   │                   │
  │                   │                     │ create ticket     │                   │
  │                   │                     │──────────────────►│                   │
  │                   │                     │◄──────────────────│                   │
  │                   │                     │ ticket_id         │                   │
  │                   │                     │                   │                   │
  │                   │                     │ emit evidence     │                   │
  │                   │                     │──────────────────────────────────────►│
  │                   │◄────────────────────│                   │                   │
  │                   │ QUARANTINE + ticket │                   │                   │
  │◄──────────────────│                     │                   │                   │
  │ QUARANTINED       │                     │                   │                   │
  │                   │                     │                   │                   │
  │ (pivot or wait)   │                     │                   │                   │
```

---

# 15. Use Cases

## 15.1 AI Agent Guardrails

### Use Case: Prevent AI Agent Data Exfiltration

**Scenario:** An AI agent processes customer claims and needs to send notifications. The agent must not send PII to external email addresses.

**STIX Solution:**
- Policy denies `SEND_EXTERNAL` action when `piiDetected: true`
- SDK automatically detects PII in message body
- Agent receives `DENIED` with reason code
- Agent must redact PII or use internal notification system

**Policy:**
```yaml
policy_id: AGENT-DATA-001
scope:
  actor_type: AI_AGENT
  action: SEND_EXTERNAL
  resource_type: MESSAGE
conditions:
  require_signal:
    piiDetected: true
decision: DENY
reason_code: AGENT_PII_EXTERNAL_BLOCKED
```

### Use Case: AI Agent Tool Restrictions

**Scenario:** AI agents should query databases but not modify data without human approval.

**STIX Solution:**
- `DB_READ` actions are allowed
- `DB_WRITE` actions require `QUARANTINE` and approval
- Evidence tracks all database access

**Policies:**
```yaml
# Allow reads
policy_id: AGENT-DB-001
scope:
  actor_type: AI_AGENT
  action: DB_READ
  resource_type: DB_RECORD
decision: ALLOW
reason_code: DB_READ_ALLOWED

# Quarantine writes
policy_id: AGENT-DB-002
scope:
  actor_type: AI_AGENT
  action: DB_WRITE
  resource_type: DB_RECORD
decision: QUARANTINE
reason_code: DB_WRITE_REQUIRES_APPROVAL
approval:
  approver_role: DataOwner
```

### Use Case: LLM Prompt/Output Governance

**Scenario:** Prevent sensitive data from being sent to external LLM APIs.

**STIX Solution:**
- LLM Gateway checks prompts before sending
- Blocks prompts containing PCI/PHI/PII
- Redacts sensitive content if configured
- Logs all LLM interactions

---

## 15.2 Financial Services

### Use Case: High-Value Transaction Controls

**Scenario:** Wire transfers above $10,000 require dual approval.

**STIX Solution:**
- Policy triggers `QUARANTINE` for high-value transfers
- Creates approval ticket requiring two approvers
- Evidence captures full transaction context
- Blocked until approvals received

**Policy:**
```yaml
policy_id: FIN-WIRE-001
scope:
  actor_type: SERVICE
  action: WIRE_TRANSFER
  resource_type: PAYMENT
conditions:
  require_resource_attr:
    amount_usd_gte: 10000
decision: QUARANTINE
reason_code: HIGH_VALUE_REQUIRES_DUAL_APPROVAL
approval:
  approver_role: TreasuryManager
  require_count: 2
controls: [SOX-ITGC-02]
```

### Use Case: PCI Data Access Controls

**Scenario:** Only authorized services can access cardholder data.

**STIX Solution:**
- Data Gateway enforces STIX policy on all queries
- Denies access to PCI data without proper role
- Masks card numbers in responses
- Complete audit trail for PCI compliance

### Use Case: Fraud Detection Integration

**Scenario:** Block transactions flagged by fraud detection system.

**STIX Solution:**
- Context includes fraud risk score
- High-risk transactions are quarantined
- Evidence captures fraud signals for investigation

---

## 15.3 Healthcare

### Use Case: HIPAA PHI Access Controls

**Scenario:** Healthcare AI agents must not access PHI without break-glass justification.

**STIX Solution:**
- Policy denies PHI access by default
- Break-glass requires explicit justification and ticket
- All PHI access logged with full context
- Automatic HIPAA audit report generation

**Policy:**
```yaml
policy_id: HIPAA-PHI-001
scope:
  actor_type: AI_AGENT
  action: DATA_READ
  resource_type: PATIENT_RECORD
conditions:
  require_resource_attr:
    classification: PHI
decision: QUARANTINE
reason_code: PHI_REQUIRES_BREAK_GLASS
approval:
  approver_role: PrivacyOfficer
  require_justification: true
controls: [HIPAA-164.312]
regulations: [HIPAA.Privacy]
```

### Use Case: Patient Data Export Controls

**Scenario:** Patient data cannot be exported without proper authorization.

**STIX Solution:**
- Export actions blocked by default
- Requires data use agreement verification
- Geographic restrictions enforced
- Complete chain of custody in evidence

---

## 15.4 Cloud & DevOps

### Use Case: Production Deployment Controls

**Scenario:** Production deployments require change ticket and approval.

**STIX Solution:**
- CI/CD pipeline calls STIX before deploy
- Verifies change ticket exists and is approved
- Blocks unauthorized deployments
- Evidence links deployment to change record

**Policy:**
```yaml
policy_id: CICD-PROD-001
scope:
  actor_type: SERVICE
  action: DEPLOY_PROD
  resource_type: APPLICATION
conditions:
  env: prod
decision: QUARANTINE
reason_code: PROD_DEPLOY_REQUIRES_TICKET
approval:
  approver_role: ReleaseManager
  require_ticket: true
controls: [ITGC-CM-01]
```

### Use Case: Infrastructure Change Controls

**Scenario:** Infrastructure changes require security review.

**STIX Solution:**
- Terraform/IaC changes routed through STIX
- Security-sensitive changes require review
- Auto-approve low-risk changes
- Full audit trail of infrastructure changes

### Use Case: Secret Access Controls

**Scenario:** Access to production secrets requires justification.

**STIX Solution:**
- Vault/secret manager integrates with STIX
- Requires purpose and ticket for access
- Time-limited access tokens
- Complete secret access audit trail

---

## 15.5 Compliance & Audit

### Use Case: Continuous Compliance Monitoring

**Scenario:** Demonstrate continuous compliance for SOC 2/ISO 27001.

**STIX Solution:**
- All control-relevant actions flow through STIX
- Policies map to specific controls
- Evidence automatically tagged with control IDs
- Real-time compliance dashboards

### Use Case: Regulatory Examination Preparation

**Scenario:** Prepare evidence package for regulatory examination.

**STIX Solution:**
- Query evidence by regulation/control
- Export signed evidence bundles
- Verification tools for examiner use
- Replay capability for decision review

### Use Case: Incident Investigation

**Scenario:** Investigate security incident with full context.

**STIX Solution:**
- Query all actions by actor/resource/time
- Trace decision chain with trace_ids
- Verify evidence integrity
- Export for forensic analysis

---

## 15.6 Multi-Tenant SaaS

### Use Case: Tenant Data Isolation

**Scenario:** Ensure AI agents cannot access data across tenant boundaries.

**STIX Solution:**
- Tenant ID included in all contexts
- Policies enforce tenant isolation
- Deny cross-tenant data access
- Per-tenant evidence partitioning

**Policy:**
```yaml
policy_id: TENANT-ISO-001
scope:
  actor_type: AI_AGENT
  action: DATA_READ
  resource_type: TENANT_DATA
conditions:
  require_tenant_match: true  # actor.tenant == resource.tenant
decision: DENY
reason_code: CROSS_TENANT_ACCESS_BLOCKED
controls: [ISO-SEC-01]
```

### Use Case: Customer-Specific Policies

**Scenario:** Enterprise customers require custom compliance policies.

**STIX Solution:**
- Per-tenant policy configuration
- Custom control mappings
- Customer-specific evidence retention
- White-label audit reports

---

# 16. Capabilities

## 16.1 Core Enforcement Capabilities

| Capability | Description |
|------------|-------------|
| **Runtime Authorization** | Evaluate every action against policy before execution |
| **Deterministic Decisions** | Same input + same policy = same output (always) |
| **Cryptographic Proof Tokens** | Short-lived tokens proving authorization |
| **Unavoidable Enforcement** | Protected targets reject unauthorized requests |
| **Fail-Closed Defaults** | High-risk actions blocked when STIX unavailable |

## 16.2 Policy Management Capabilities

| Capability | Description |
|------------|-------------|
| **Policy-as-Code** | Policies defined in YAML/JSON, version controlled |
| **Immutable Versioning** | Policy updates create new versions; no mutations |
| **Impact Analysis** | Simulate policy changes against historical data |
| **Unit Testing** | Automated testing of policy logic |
| **Approval Workflows** | Required sign-off for production policies |
| **Conflict Resolution** | Deterministic priority-based policy selection |

## 16.3 Evidence & Audit Capabilities

| Capability | Description |
|------------|-------------|
| **Automatic Evidence Generation** | Every decision produces audit record |
| **Tamper-Evident Storage** | Hash-chained, signed evidence events |
| **Immutable Vault** | WORM-compliant long-term storage |
| **Integrity Verification** | Independent verification of evidence chain |
| **Decision Replay** | Reproduce any decision with original policy |
| **Flexible Querying** | Search by actor, action, decision, time, etc. |
| **Export & Reporting** | Signed evidence bundles for auditors |

## 16.4 Integration Capabilities

| Capability | Description |
|------------|-------------|
| **Agent SDK** | Native integration for AI agents |
| **API Gateway Integration** | Service mesh / gateway filters |
| **LLM Gateway** | Prompt/output policy enforcement |
| **Data Gateway** | Database proxy integration |
| **CI/CD Integration** | Pipeline gates for deployments |
| **Approval System Integration** | ServiceNow, Jira, Slack connectors |
| **SIEM/GRC Integration** | Evidence export to existing tools |

## 16.5 Security Capabilities

| Capability | Description |
|------------|-------------|
| **mTLS Everywhere** | Encrypted service-to-service communication |
| **KMS/HSM Integration** | Hardware-backed key management |
| **Key Rotation** | Automated signing key rotation |
| **Bypass Detection** | Alert on unauthorized access attempts |
| **Rate Limiting** | Protect against abuse |
| **Workload Identity** | Cloud-native authentication |

## 16.6 Operational Capabilities

| Capability | Description |
|------------|-------------|
| **High Availability** | Multi-AZ deployment support |
| **Horizontal Scaling** | Stateless enforcer scales horizontally |
| **Low Latency** | P95 authorization < 50ms |
| **Graceful Degradation** | Configurable fail modes |
| **Health Monitoring** | Comprehensive health endpoints |
| **Observability** | Metrics, traces, and logs |

---

# 17. Features

## 17.1 Enforcement Features

### 17.1.1 Three-Outcome Decision Model

| Outcome | Description | Agent Behavior |
|---------|-------------|----------------|
| **ALLOW** | Action is compliant | Proceed with execution |
| **DENY** | Action is non-compliant | Block, pivot to alternative |
| **QUARANTINE** | Requires human approval | Wait or escalate |

### 17.1.2 Obligation System

| Obligation | Description |
|------------|-------------|
| **REDACT_FIELDS** | Remove specified fields from payload |
| **MASK_PII** | Replace PII with masked values |
| **WATERMARK_OUTPUT** | Add traceability markers |
| **REQUIRE_APPROVAL** | Create approval ticket |
| **RATE_LIMIT** | Enforce request quotas |
| **LOG_LEVEL** | Increase evidence detail |
| **ENCRYPT_TRANSIT** | Require TLS for data |
| **DUAL_CONTROL** | Require two approvers |

### 17.1.3 Context-Aware Evaluation

| Context Element | Usage |
|-----------------|-------|
| **Actor identity** | Who is performing the action |
| **Actor role** | What permissions they have |
| **Environment** | dev/test/stage/prod |
| **Data classification** | PII/PHI/PCI/Confidential |
| **Destination** | Internal/External |
| **Jurisdiction** | Geographic restrictions |
| **Purpose** | Business justification |
| **Risk signals** | Local detection flags |

### 17.1.4 Proof Token System

| Feature | Description |
|---------|-------------|
| **Short TTL** | 30-60 second validity |
| **Scoped claims** | Action/resource specific |
| **Policy binding** | Includes policy hash |
| **Trace linkage** | Links to evidence |
| **Cryptographic signing** | Ed25519/ES256 |

---

## 17.2 Policy Features

### 17.2.1 Policy Structure

```yaml
policy_id: string           # Unique identifier
version: string             # Semantic version
priority: number            # Lower = higher priority (optional)

scope:
  actor_type: string        # HUMAN | SERVICE | AI_AGENT | JOB
  action: string            # Action type
  resource_type: string     # Resource type

conditions:                 # All must match
  env: string               # Environment filter
  require_signal:           # Required detection signals
    piiDetected: boolean
  require_resource_attr:    # Required resource attributes
    destination: string

decision: string            # ALLOW | DENY | QUARANTINE
reason_code: string         # Machine-readable code

obligations: []             # For ALLOW decisions
approval:                   # For QUARANTINE decisions
  approver_role: string
  require_count: number
  require_ticket: boolean

controls: []                # Control framework IDs
regulations: []             # Regulation references
```

### 17.2.2 Conflict Resolution

| Priority | Rule |
|----------|------|
| 1 | Explicit `priority` field (lower wins) |
| 2 | Decision rank: DENY < QUARANTINE < ALLOW |
| 3 | Policy ID (lexicographic) |

### 17.2.3 Policy Testing

| Test Type | Description |
|-----------|-------------|
| **Allow cases** | Verify allowed requests |
| **Deny cases** | Verify blocked requests |
| **Quarantine cases** | Verify approval triggers |
| **Obligation cases** | Verify obligation attachment |
| **Edge cases** | Boundary conditions |
| **Regression tests** | Prevent unintended changes |

### 17.2.4 Impact Analysis

| Analysis | Description |
|----------|-------------|
| **Historical simulation** | Run new policy against past events |
| **Decision delta** | Show what would change |
| **Risk assessment** | Highlight potential issues |
| **Approval requirement** | Block risky changes |

---

## 17.3 Evidence Features

### 17.3.1 Evidence Event Structure

| Field | Description |
|-------|-------------|
| **schema_version** | Schema version for compatibility |
| **event_id** | Unique event identifier |
| **trace_id** | Correlation ID across events |
| **timestamp** | ISO-8601 with milliseconds |
| **decision** | ALLOW/DENY/QUARANTINE |
| **reason_code** | Machine-readable reason |
| **actor** | Who performed the action |
| **action** | What was attempted |
| **resource** | What was accessed |
| **context** | Environmental context |
| **policy** | Policy ID, version, hash |
| **controls** | Control framework mappings |
| **regulations** | Regulation references |
| **obligations_applied** | What obligations were applied |
| **outcome** | Execution result |
| **integrity** | Hash, chain, signature |

### 17.3.2 Integrity Features

| Feature | Description |
|---------|-------------|
| **Canonical JSON** | Stable serialization for hashing |
| **SHA-256 hashing** | Cryptographic content hash |
| **Hash chaining** | Each event links to previous |
| **Ed25519 signing** | Cryptographic signatures |
| **Key identification** | Key ID in every event |
| **Merkle batching** | Daily batch roots |

### 17.3.3 Storage Features

| Feature | Hot Store | Immutable Vault |
|---------|-----------|-----------------|
| **Purpose** | Operational queries | Regulatory proof |
| **Mutability** | Append-only | WORM |
| **Indexing** | Full indexing | Minimal |
| **Retention** | Short-term | Long-term |
| **Query speed** | Fast | Slower |
| **Verification** | Basic | Full chain |

### 17.3.4 Query & Export Features

| Feature | Description |
|---------|-------------|
| **Trace lookup** | Get all events by trace_id |
| **Multi-dimensional search** | Filter by actor, action, decision, time |
| **Control-based queries** | Find events by control ID |
| **Regulation-based queries** | Find events by regulation |
| **JSONL export** | Machine-readable export |
| **Signed bundles** | Tamper-evident export packages |
| **Audit reports** | Human-readable summaries |

---

## 17.4 SDK Features

### 17.4.1 Tool Wrapping

| Feature | Description |
|---------|-------------|
| **Automatic authorization** | Every tool call checked |
| **Typed results** | OK/DENIED/QUARANTINED |
| **Obligation enforcement** | Pre/post execution hooks |
| **Outcome recording** | Success/failure evidence |
| **Error handling** | Structured error responses |

### 17.4.2 Tool Metadata

| Field | Description |
|-------|-------------|
| **name** | Tool identifier |
| **action** | Action type for policy |
| **resourceType** | Resource type for policy |
| **riskTier** | LOW/MEDIUM/HIGH/CRITICAL |
| **summarizeArgs** | Safe argument summary function |
| **classify** | Local signal detection function |
| **deriveResourceAttributes** | Attribute extraction function |

### 17.4.3 Integration Patterns

| Pattern | Description |
|---------|-------------|
| **Tool registry** | Register all tools centrally |
| **Guarded wrapper** | Automatic enforcement |
| **Context provider** | Automatic context assembly |
| **Fail-closed** | Deny on error by default |

---

## 17.5 Verification Features

### 17.5.1 stix-verify

| Check | Description |
|-------|-------------|
| **Signature verification** | Validate Ed25519 signatures |
| **Hash chain verification** | Validate prev_hash linkage |
| **Merkle root verification** | Validate batch roots |
| **Completeness check** | Detect missing events |
| **Configuration audit** | Verify vault settings |

### 17.5.2 stix-replay

| Feature | Description |
|---------|-------------|
| **Event retrieval** | Fetch by trace_id |
| **Policy retrieval** | Fetch by policy hash |
| **Deterministic re-evaluation** | Run policy engine |
| **Decision comparison** | Assert match |
| **Audit report** | Document replay result |

---

## 17.6 Operational Features

### 17.6.1 Deployment

| Feature | Description |
|---------|-------------|
| **Containerized** | Docker/Kubernetes ready |
| **Helm charts** | Kubernetes deployment |
| **Terraform modules** | Infrastructure as code |
| **Multi-AZ** | High availability |
| **Auto-scaling** | Horizontal scaling |

### 17.6.2 Monitoring

| Feature | Description |
|---------|-------------|
| **Health endpoints** | Liveness/readiness probes |
| **Metrics export** | Prometheus/StatsD |
| **Distributed tracing** | OpenTelemetry |
| **Structured logging** | JSON logs |
| **Alerting integration** | PagerDuty/Slack |

### 17.6.3 Administration

| Feature | Description |
|---------|-------------|
| **Policy reload** | Hot reload without restart |
| **Key rotation** | Zero-downtime rotation |
| **Configuration management** | Environment-based config |
| **Backup/restore** | Evidence backup procedures |

---

# 18. Market Positioning

## 18.1 Target Industries

| Industry | Primary Use Cases |
|----------|-------------------|
| 🏦 **Banking & Financial Services** | Transaction controls, fraud prevention, regulatory compliance |
| 🏥 **Healthcare & Life Sciences** | PHI access controls, HIPAA compliance, clinical AI |
| ⚖️ **Legal & Insurance** | Document access, claims processing, policy enforcement |
| 🤖 **Enterprise AI / GenAI Platforms** | Agent guardrails, LLM governance, prompt security |
| ☁️ **Cloud & Data Platforms** | Multi-tenant isolation, data governance, DevOps controls |
| 🧾 **GRC & Risk Systems** | Continuous compliance, audit automation |

## 18.2 Primary Buyers

| Buyer | Pain Point |
|-------|------------|
| **CISO** | Personal accountability for security incidents |
| **Chief Risk Officer** | Need hard guarantees, not dashboards |
| **Head of AI Governance** | Fear of AI autonomy and compliance gaps |
| **Head of Platform Engineering** | Need control primitives for shared services |
| **Audit Teams** | Need verifiable, exportable evidence |
| **Compliance Officers** | Need continuous compliance proof |

## 18.3 Competitive Differentiation

| What Others Do | What STIX Does |
|----------------|----------------|
| Detect violations after | **Block violations before** |
| Advisory guardrails | **Enforcing guardrails** |
| Post-facto audit reporting | **Evidence by construction** |
| "We support compliance" checklists | **"Compliance is technically enforced"** |
| Trust teams to follow rules | **Systems that cannot break rules** |
| Probabilistic risk reduction | **Deterministic enforcement** |
| Manual audit preparation | **Automatic audit evidence** |

## 18.4 Taglines & Positioning

| Audience | Tagline |
|----------|---------|
| **Executive** | *"STIX — Where compliance is enforced, not requested."* |
| **Technical** | *"STIX shields your execution path."* |
| **Regulator** | *"STIX — Trust through enforcement."* |
| **Marketing** | *"STIX shields. Evidence proves. Auditors trust."* |
| **Definitive** | *"If STIX is present, certain classes of violations cannot occur."* |

## 18.5 What STIX Specializes In

| Specialization | Description |
|----------------|-------------|
| **Unavoidability** | Token-required targets, multi-choke-point enforcement |
| **Tamper-Evident Audit** | Hash-chained, signed, WORM-capable evidence |
| **Replayable Determinism** | Prove any decision using policy hash + context |
| **Regulator-Ready Format** | Canonical schema + verification tooling |
| **Policy Lifecycle Rigor** | Tests, approvals, diffs, impact analysis |

---

# 19. Implementation Blueprint

## 19.1 Service Architecture

```
stix/
├─ services/
│  ├─ enforcer/           # Authorize + token mint + outcome
│  │  ├─ src/
│  │  │  ├─ index.ts
│  │  │  ├─ config.ts
│  │  │  ├─ types.ts
│  │  │  └─ http.ts
│  │  └─ tests/
│  │
│  ├─ policy/             # CRUD, versioning, tests, evaluation
│  │  ├─ src/
│  │  │  ├─ index.ts
│  │  │  ├─ types.ts
│  │  │  ├─ store.ts
│  │  │  └─ evaluator.ts
│  │  └─ tests/
│  │
│  ├─ evidence/           # Canonicalize, hash, sign, store
│  │  ├─ src/
│  │  │  ├─ index.ts
│  │  │  ├─ config.ts
│  │  │  ├─ canonical.ts
│  │  │  ├─ hashchain.ts
│  │  │  ├─ signer.ts
│  │  │  └─ storage.ts
│  │  └─ tests/
│  │
│  ├─ approvals/          # Quarantine workflows (v1.1)
│  │  └─ src/
│  │
│  └─ target-demo/        # Protected target example
│     └─ src/
│
├─ sdk/
│  ├─ agent-sdk/          # Tool wrapping + obligations
│  │  ├─ src/
│  │  │  ├─ index.ts
│  │  │  ├─ types.ts
│  │  │  ├─ stixClient.ts
│  │  │  ├─ guardrails.ts
│  │  │  ├─ obligations.ts
│  │  │  └─ toolRegistry.ts
│  │  └─ tests/
│  │
│  ├─ target-verifier/    # Service-side token verification
│  │  └─ src/
│  │
│  └─ llm-gateway/        # Prompt/output enforcement (later)
│     └─ src/
│
├─ tools/
│  ├─ stix-verify/        # Integrity verification CLI
│  │  └─ src/
│  │
│  └─ stix-replay/        # Determinism verification CLI
│     └─ src/
│
├─ schemas/               # JSON Schema definitions
│  ├─ authorize.schema.json
│  ├─ decision.schema.json
│  └─ evidence.schema.json
│
├─ policies/              # Example policies + tests
│  └─ examples/
│
└─ deploy/
   ├─ helm/
   ├─ k8s/
   └─ terraform/
```

## 19.2 Phased Rollout

| Phase | Scope | Deliverables |
|-------|-------|--------------|
| **Phase 1** | Core Enforcement | Authorize API, deny/allow/quarantine, hot evidence store |
| **Phase 2** | Integrity | Canonicalization, hash chain, signatures, immutable vault |
| **Phase 3** | Unavoidability | Proof token, service-side verification, bypass detection |
| **Phase 4** | Policy Rigor | Unit tests, impact analysis, approvals, replay tooling |
| **Phase 5** | Advanced | LLM gateway, approval workflows, multi-tenant |

## 19.3 Non-Functional Requirements

| Requirement | Target |
|-------------|--------|
| **Authorization latency** | P95 < 50ms (regional) |
| **Availability** | 99.9% uptime |
| **Scalability** | 10K req/sec per instance |
| **Evidence durability** | At-least-once delivery |
| **Evidence latency** | < 1 second to hot store |

## 19.4 Acceptance Criteria (Hard Gates)

STIX is **not complete** unless:

- ❌ No guarded action can execute without STIX token
- ❌ No ALLOW occurs without an evidence event
- ❌ Evidence fails verification → build fails
- ❌ Same input ≠ different output (determinism broken)
- ❌ Policies cannot be replayed

---

# 20. Summary

## 20.1 What STIX Is

**STIX — Shield, Trust & Integrity eXecution** is a deterministic enforcement layer that:

1. **Shields** regulated systems and AI agents from non-compliant execution
2. **Builds Trust** through replayable, verifiable decisions
3. **Ensures Integrity** with tamper-evident, hash-chained evidence
4. **Controls eXecution** by sitting in the mandatory path — not monitoring after the fact

## 20.2 Core Value Proposition

> *"STIX is not a compliance platform. STIX is not a monitoring tool. STIX is a deterministic enforcement layer that makes non-compliant execution impossible and produces audit evidence by construction."*

## 20.3 Key Differentiators

- **Unavoidability** — Protected targets require STIX proof tokens
- **Determinism** — Same input + same policy = same decision (always)
- **Tamper-Evidence** — Hash-chained, signed, WORM-capable evidence
- **Replayability** — Prove any decision using policy hash + captured context
- **Regulator-Ready** — Canonical schema + independent verification tooling

## 20.4 The Bottom Line

> **"Anyone can add a check. Very few can make bypass impossible, decisions replayable, and evidence indisputable. That is what STIX specializes in."**

---

# Appendices

## Appendix A: Glossary

| Term | Definition |
|------|------------|
| **GAS** | Guarded Action Surface — actions requiring STIX enforcement |
| **SoR** | System of Record — authoritative source for business data |
| **WORM** | Write Once Read Many — immutable storage pattern |
| **Obligations** | Constraints applied to allowed actions (redact, mask, etc.) |
| **Trace ID** | Correlation ID linking decision to evidence to outcome |
| **Proof Token** | Short-lived cryptographic token proving STIX authorization |
| **Policy Hash** | Content hash of policy artifact for versioning/replay |
| **Evidence Event** | Immutable audit record of a STIX decision |
| **Hot Store** | Queryable operational evidence storage |
| **Immutable Vault** | Tamper-evident long-term evidence storage |

## Appendix B: Regulation Mapping

| Regulation | Relevant STIX Capabilities |
|------------|---------------------------|
| **GDPR** | Data access controls, purpose limitation, audit trail |
| **HIPAA** | PHI access controls, break-glass, audit requirements |
| **PCI-DSS** | Cardholder data protection, access logging |
| **SOX** | Financial controls, change management, audit trail |
| **SOC 2** | Security controls, availability, audit evidence |
| **ISO 27001** | Information security controls, access management |

## Appendix C: Control Framework Mapping

| Framework | STIX Support |
|-----------|--------------|
| **NIST CSF** | Protect, Detect, Respond capabilities |
| **CIS Controls** | Access control, audit logging, data protection |
| **COBIT** | IT governance, risk management |
| **ITIL** | Change management, incident management |

---

*Document Version: 1.0*  
*Last Updated: January 2026*  
*Status: Architecture & Design Specification*
