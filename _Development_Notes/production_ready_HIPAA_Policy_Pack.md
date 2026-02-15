production-ready HIPAA Policy Pack

Perfect. Below is a **production-ready HIPAA Policy Pack (v1.0)** for STIX — written the way enterprises actually adopt it: **controls first, policies next, tests included**.

This is **drop-in**. You can put this under `policies/packs/hipaa/`.

---

# STIX HIPAA Policy Pack — v1.0

**Scope:** Healthcare Claims + PHI handling
**Objective:** Enforce HIPAA Security & Privacy Rules at execution time
**Philosophy:** *Default deny, explicit allow, deterministic obligations, immutable evidence*

---

## 1️⃣ Control Library (HIPAA-Aligned)

> Controls are **stable primitives**. Policies reference these — regulations map *onto* them.

### `controls.yaml`

```yaml
version: 1.0
controls:

  ACCESS_PROD_DATA:
    description: Access to production healthcare data
    hipaa_refs: [164.312(a)(1)]

  PHI_EGRESS_EXTERNAL:
    description: PHI leaving organizational boundary
    hipaa_refs: [164.312(e)(1)]

  MINIMUM_NECESSARY:
    description: Minimum necessary data principle
    hipaa_refs: [164.502(b)]

  AUDIT_LOGGING_REQUIRED:
    description: Audit logging of access and actions
    hipaa_refs: [164.312(b)]

  STRONG_AUTH_REQUIRED:
    description: Strong authentication for sensitive actions
    hipaa_refs: [164.312(d)]

  HUMAN_APPROVAL_REQUIRED:
    description: Human approval before high-risk disclosure
    hipaa_refs: [164.308(a)(1)(ii)(B)]

  DATA_INTEGRITY_PROTECTION:
    description: Prevent improper alteration or destruction
    hipaa_refs: [164.312(c)(1)]

  TRANSMISSION_SECURITY:
    description: Secure transmission of PHI
    hipaa_refs: [164.312(e)(1)]
```

---

## 2️⃣ Obligation Catalog (Deterministic Enforcement)

### `obligations.yaml`

```yaml
version: 1.0
obligations:

  MASK_PHI:
    description: Redact PHI fields deterministically
    enforcement: agent_sdk

  WATERMARK_OUTPUT:
    description: Add confidentiality watermark
    enforcement: agent_sdk

  ATTACHMENTS_DENY:
    description: Remove all attachments
    enforcement: agent_sdk

  LOG_LEVEL_FULL:
    description: Emit full audit detail
    enforcement: enforcer

  REQUIRE_APPROVAL:
    description: Pause execution pending approval
    enforcement: approval_service

  REQUIRE_TLS:
    description: Enforce TLS/mTLS
    enforcement: protected_target
```

---

## 3️⃣ Policy Set (Core HIPAA Enforcement)

### Policy 01 — Default Deny (Safety Net)

```yaml
policy_id: HIPAA-000
priority: 0
scope: { actor_type: AI_AGENT }
decision: DENY
reason_code: DEFAULT_DENY
controls: []
regulations: []
```

---

### Policy 02 — Allow PHI Read from Prod DB (Audited)

```yaml
policy_id: HIPAA-101
priority: 10
scope:
  actor_type: AI_AGENT
  action: DB_READ
  resource_type: CLAIM_RECORD

conditions:
  require_context:
    env: prod

decision: ALLOW
reason_code: PHI_DB_READ_ALLOWED
controls:
  - ACCESS_PROD_DATA
  - AUDIT_LOGGING_REQUIRED
obligations:
  - type: LOG_LEVEL_FULL
regulations:
  - HIPAA.164.312.a.1
  - HIPAA.164.312.b
```

---

### Policy 03 — Deny PHI to Unknown External

```yaml
policy_id: HIPAA-201
priority: 5
scope:
  actor_type: AI_AGENT
  action: SEND_EXTERNAL
  resource_type: MESSAGE

conditions:
  require_signal:
    phiDetected: true
  require_resource_attr:
    recipientType: EXTERNAL_UNKNOWN

decision: DENY
reason_code: PHI_EGRESS_EXTERNAL_BLOCKED
controls:
  - PHI_EGRESS_EXTERNAL
regulations:
  - HIPAA.164.312.e.1
```

---

### Policy 04 — Allow PHI to Patient with Obligations

```yaml
policy_id: HIPAA-202
priority: 20
scope:
  actor_type: AI_AGENT
  action: SEND_EXTERNAL
  resource_type: MESSAGE

conditions:
  require_signal:
    phiDetected: true
  require_resource_attr:
    recipientType: EXTERNAL_PATIENT

decision: ALLOW
reason_code: PHI_TO_PATIENT_WITH_SAFEGUARDS
controls:
  - PHI_EGRESS_EXTERNAL
  - MINIMUM_NECESSARY
obligations:
  - type: MASK_PHI
  - type: WATERMARK_OUTPUT
  - type: ATTACHMENTS_DENY
regulations:
  - HIPAA.164.502.b
  - HIPAA.164.312.e.1
```

---

### Policy 05 — Quarantine PHI to Provider with Attachments

```yaml
policy_id: HIPAA-203
priority: 15
scope:
  actor_type: AI_AGENT
  action: SEND_EXTERNAL
  resource_type: MESSAGE

conditions:
  require_signal:
    phiDetected: true
  require_resource_attr:
    recipientType: PARTNER
    hasAttachments: true

decision: QUARANTINE
reason_code: PHI_ATTACHMENT_REQUIRES_APPROVAL
controls:
  - HUMAN_APPROVAL_REQUIRED
  - PHI_EGRESS_EXTERNAL
approval:
  approver_role: PrivacyOfficer
regulations:
  - HIPAA.164.308.a.1
```

---

### Policy 06 — Enforce Secure Transmission

```yaml
policy_id: HIPAA-301
priority: 30
scope:
  actor_type: AI_AGENT
  action: SEND_EXTERNAL

conditions:
  require_context:
    transportSecurity: TLS

decision: ALLOW
reason_code: SECURE_TRANSMISSION_VERIFIED
controls:
  - TRANSMISSION_SECURITY
obligations:
  - type: REQUIRE_TLS
regulations:
  - HIPAA.164.312.e.1
```

---

### Policy 07 — Deny PHI in Non-Prod Environments

```yaml
policy_id: HIPAA-401
priority: 8
scope:
  actor_type: AI_AGENT
  resource_classification: PHI

conditions:
  forbid_context:
    env: [dev, test]

decision: DENY
reason_code: PHI_NON_PROD_BLOCKED
controls:
  - DATA_INTEGRITY_PROTECTION
regulations:
  - HIPAA.164.312.c.1
```

---

### Policy 08 — Require Strong Auth for High-Risk Actions

```yaml
policy_id: HIPAA-501
priority: 12
scope:
  actor_type: AI_AGENT
  action: SEND_EXTERNAL

conditions:
  require_context:
    risk_tier: HIGH

decision: QUARANTINE
reason_code: STRONG_AUTH_REQUIRED
controls:
  - STRONG_AUTH_REQUIRED
approval:
  approver_role: SecurityOfficer
regulations:
  - HIPAA.164.312.d
```

---

## 4️⃣ Evidence Guarantees (What Auditors Get)

Each enforced action emits:

* `trace_id`
* `policy_id + policy_hash`
* decision + reason_code
* obligations issued & applied
* approval metadata (if any)
* cryptographic integrity chain

This satisfies:

* **HIPAA 164.312(b)** audit controls
* **Non-repudiation**
* **Forensic reconstruction**

---

## 5️⃣ Test Matrix (Mandatory)

### `tests/hipaa-core.yaml`

```yaml
tests:

  - name: deny_phi_to_unknown
    input:
      action: SEND_EXTERNAL
      signals: { phiDetected: true }
      resource: { recipientType: EXTERNAL_UNKNOWN }
    expect:
      decision: DENY
      reason_code: PHI_EGRESS_EXTERNAL_BLOCKED

  - name: allow_phi_to_patient_with_redaction
    input:
      action: SEND_EXTERNAL
      signals: { phiDetected: true }
      resource: { recipientType: EXTERNAL_PATIENT }
    expect:
      decision: ALLOW
      obligations:
        - MASK_PHI
        - WATERMARK_OUTPUT
        - ATTACHMENTS_DENY

  - name: quarantine_provider_with_attachment
    input:
      action: SEND_EXTERNAL
      signals: { phiDetected: true }
      resource: { recipientType: PARTNER, hasAttachments: true }
    expect:
      decision: QUARANTINE
      approval_required: true
```

---

## 6️⃣ Why This HIPAA Pack Is Strong (Architect’s View)

✔ **Executable, not descriptive**
✔ **Deterministic & replayable**
✔ **Maps cleanly to HIPAA clauses**
✔ **Forces minimum necessary at runtime**
✔ **Human approval only where required**
✔ **Zero UI dependency**
✔ **Unavoidable enforcement**

This is **not** a GRC checklist.
This is **HIPAA turned into code that blocks execution**.

---

## Next Logical Step

I strongly recommend next we do **Schemas + Verifier CLI**, so you can:

* export a HIPAA audit bundle
* cryptographically verify evidence
* replay a decision from 6 months ago

If you agree, just say:

👉 **“Next: Schemas + Verifier”**

After that, STIX becomes *audit-grade complete*.