# STIX Enterprise Development Vision
## Complete Implementation Blueprint for Claude Code Agents

**Document Version:** 2.0.0  
**Last Updated:** 2026-01-27  
**Classification:** Technical Implementation Guide  
**Target:** Claude Code Agents for Autonomous Execution

---

## EXECUTIVE SUMMARY

STIX (Shield, Trust & Integrity eXecution) is an enterprise-grade compliance-first control framework designed to ensure AI agents, systems, and workflows never drift outside regulatory and policy boundaries. This document provides a complete, executable blueprint for Claude Code agents to implement the full STIX platform.

### Core Mission
Build a production-ready guardrail system that **blocks non-compliant actions BEFORE they occur**, providing:
- Real-time authorization decisions (ALLOW/DENY/QUARANTINE)
- Cryptographically-signed proof tokens
- Tamper-evident audit trails with hash chain integrity
- Human-in-the-loop approval workflows
- Multi-framework compliance mapping (SOC2, HIPAA, PCI-DSS, GDPR, NIST, ISO 27001)

---

## SECTION 1: ARCHITECTURE OVERVIEW

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│  AI Agents          Target Systems        Human Operators       Auditors    │
│  (agent-sdk)        (target-verifier)     (Approval UI)         (stix-tools)│
└────────┬────────────────────┬──────────────────┬─────────────────┬──────────┘
         │                    │                  │                 │
         ▼                    ▼                  ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY / LOAD BALANCER                        │
└────────┬────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STIX ENFORCER SERVICE                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │ Auth Engine │  │ Token Gen   │  │ Cache Layer │  │ Fail Mode Handler   │ │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────────────┘ │
│                              Port: 3001                                      │
└────────┬──────────────────────┬──────────────────────┬──────────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────┐   ┌─────────────────┐   ┌─────────────────┐
│ POLICY SERVICE  │   │ EVIDENCE SERVICE│   │APPROVALS SERVICE│
│                 │   │                 │   │                 │
│ • Policy Store  │   │ • Event Store   │   │ • Ticket Store  │
│ • Eval Engine   │   │ • Hash Chain    │   │ • Workflow Mgr  │
│ • Pattern Match │   │ • Signing       │   │ • Notifications │
│                 │   │                 │   │                 │
│   Port: 3002    │   │   Port: 3003    │   │   Port: 3004    │
└─────────────────┘   └─────────────────┘   └─────────────────┘
         │                      │                      │
         ▼                      ▼                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ PostgreSQL    │  │ Redis Cache   │  │ S3/MinIO      │  │ File System  │  │
│  │ (Production)  │  │ (Hot Cache)   │  │ (Long-term)   │  │ (Dev/Test)   │  │
│  └───────────────┘  └───────────────┘  └───────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
AUTHORIZATION FLOW:
                                                    
1. Agent requests action      2. Enforcer evaluates       3. Response returned
   ┌─────────┐                   ┌─────────────────┐         ┌─────────────┐
   │ Agent   │ ─── Request ───▶  │   ENFORCER      │ ◀─────  │   Policy    │
   │         │ ◀── Response ──── │                 │ ──────▶ │   Service   │
   └─────────┘     (+ token)     │  ┌───────────┐  │         └─────────────┘
                                 │  │ Evaluate  │  │
                                 │  │ Sign      │  │         ┌─────────────┐
                                 │  │ Record    │  │ ──────▶ │  Evidence   │
                                 │  └───────────┘  │         │  Service    │
                                 └─────────────────┘         └─────────────┘

VERIFICATION FLOW:

1. Agent presents token    2. Target verifies        3. Action permitted
   ┌─────────┐               ┌─────────────┐           ┌─────────────┐
   │ Agent   │ ─── Token ──▶ │  Target     │ ◀───────  │  Public Key │
   │         │               │  System     │           │  Registry   │
   └─────────┘               └──────┬──────┘           └─────────────┘
                                    │
                                    ▼
                            [Execute Action]
```

### 1.3 Decision Types

| Decision | Description | Token Generated | Approval Required |
|----------|-------------|-----------------|-------------------|
| **ALLOW** | Action permitted, proceed immediately | ✅ Yes | ❌ No |
| **DENY** | Action blocked, cannot proceed | ❌ No | ❌ No |
| **QUARANTINE** | Action held pending human approval | ❌ No | ✅ Yes |

---

## SECTION 2: CURRENT STATE ANALYSIS

### 2.1 Completed Components ✅

| Component | Location | Status | Notes |
|-----------|----------|--------|-------|
| **Shared Package** | `packages/shared/` | ✅ Complete | Types, utils, validators, crypto, logger, errors |
| **Enforcer Service** | `services/enforcer/` | ⚠️ 80% | Core engine done, routes need testing |
| **Policy Service** | `services/policy/` | ⚠️ 70% | Engine exists, store incomplete |
| **Evidence Service** | `services/evidence/` | ⚠️ 60% | Basic structure, core logic missing |
| **Approvals Service** | `services/approvals/` | ⚠️ 30% | Skeleton only |
| **Agent SDK** | `sdk/agent-sdk/` | ✅ Complete | Full client implementation |
| **Target Verifier** | `sdk/target-verifier/` | ⚠️ 40% | Basic structure |
| **STIX Verify CLI** | `tools/stix-verify/` | ⚠️ 30% | CLI structure only |
| **STIX Replay** | `tools/stix-replay/` | ❌ 10% | Empty structure |
| **Docker Config** | `deploy/docker/` | ✅ Complete | Compose files ready |
| **K8s Config** | `deploy/k8s/` | ✅ Complete | Manifests ready |
| **Example Policies** | `policies/examples/` | ✅ Complete | HIPAA, Financial, Default |
| **Tests** | `tests/` | ⚠️ 50% | E2E framework, needs unit tests |

### 2.2 Critical Gaps 🔴

1. **Policy Service Engine** - Pattern matching and conflict resolution incomplete
2. **Evidence Service Store** - Hash chain implementation missing
3. **Approvals Service** - Full workflow not implemented
4. **Integration Tests** - Service-to-service communication untested
5. **Storage Backends** - PostgreSQL and S3 adapters not built
6. **Key Management** - Production key loading not implemented
7. **Metrics & Observability** - Prometheus endpoints missing

---

## SECTION 3: IMPLEMENTATION PRIORITIES

### Phase 1: Core Services (Priority: CRITICAL)
Complete the four core microservices to enable end-to-end authorization flows.

### Phase 2: Storage & Persistence (Priority: HIGH)
Implement production-ready storage backends for all services.

### Phase 3: SDKs & Tools (Priority: HIGH)
Complete client libraries and operational tooling.

### Phase 4: Security & Production Hardening (Priority: HIGH)
mTLS, key management, secrets, rate limiting.

### Phase 5: Observability & Operations (Priority: MEDIUM)
Metrics, dashboards, alerting, tracing.

### Phase 6: Documentation & Examples (Priority: MEDIUM)
API docs, integration guides, tutorials.

---

## SECTION 4: DETAILED IMPLEMENTATION SPECIFICATIONS

### 4.1 Policy Service - Complete Implementation

**Location:** `services/policy/`

#### 4.1.1 Policy Engine (src/core/engine.ts)

```typescript
/**
 * COMPLETE IMPLEMENTATION SPECIFICATION
 * 
 * The PolicyEngine must implement:
 * 1. Policy loading from YAML files
 * 2. Pattern matching for actor_type, action, resource_type (with wildcards)
 * 3. Condition evaluation (time windows, environments, signals)
 * 4. Priority-based ordering (lower number = higher priority)
 * 5. Conflict resolution (DENY wins at same priority)
 * 6. Caching for performance
 */

interface PolicyEngine {
  // Core evaluation
  evaluate(request: EvaluationRequest): Promise<PolicyDecision>;
  
  // Policy management
  loadPolicies(directory: string): Promise<void>;
  reloadPolicies(): Promise<void>;
  
  // Pattern matching
  matchesScope(policy: PolicyArtifact, request: EvaluationRequest): boolean;
  evaluateConditions(policy: PolicyArtifact, request: EvaluationRequest): boolean;
  
  // Conflict resolution
  resolvePolicies(matches: PolicyArtifact[]): PolicyArtifact;
}

// Pattern matching rules:
// - "*" matches any value
// - "prefix*" matches prefix + anything
// - "exact" matches exact string
// - Array values: any match = true

// Conflict resolution:
// 1. Sort by priority (ascending - lower = higher priority)
// 2. At same priority: DENY wins over QUARANTINE wins over ALLOW
// 3. Return first policy after conflict resolution
```

#### 4.1.2 Policy Store (src/store/index.ts)

```typescript
/**
 * STORAGE BACKENDS:
 * 1. InMemoryPolicyStore - Development/testing
 * 2. FilePolicyStore - Load from YAML files
 * 3. PostgresPolicyStore - Production with versioning
 */

interface PolicyStore {
  // CRUD
  getPolicy(policyId: string): Promise<PolicyArtifact | null>;
  listPolicies(options: ListOptions): Promise<PolicyArtifact[]>;
  upsertPolicy(policy: PolicyArtifact): Promise<void>;
  deletePolicy(policyId: string): Promise<void>;
  
  // Bulk operations
  loadFromDirectory(path: string): Promise<number>;
  reload(): Promise<void>;
  
  // Querying
  findMatching(request: EvaluationRequest): Promise<PolicyArtifact[]>;
  
  // Health
  health(): Promise<boolean>;
}
```

#### 4.1.3 Files to Create/Update

| File | Action | Description |
|------|--------|-------------|
| `src/core/engine.ts` | UPDATE | Complete pattern matching, conditions, conflict resolution |
| `src/core/matcher.ts` | CREATE | Glob pattern and wildcard matching utilities |
| `src/core/conditions.ts` | CREATE | Condition evaluation (time, env, signals) |
| `src/store/memory.ts` | CREATE | In-memory store implementation |
| `src/store/file.ts` | CREATE | YAML file loading |
| `src/store/postgres.ts` | CREATE | PostgreSQL store with versioning |
| `src/routes/index.ts` | UPDATE | Add missing validation, error handling |
| `src/types.ts` | CREATE | Service-specific type definitions |

---

### 4.2 Evidence Service - Complete Implementation

**Location:** `services/evidence/`

#### 4.2.1 Evidence Core (src/core/chain.ts)

```typescript
/**
 * HASH CHAIN IMPLEMENTATION
 * 
 * Each event links to the previous via cryptographic hash:
 * 
 * Event[0]                Event[1]                Event[2]
 * ┌─────────────┐        ┌─────────────┐        ┌─────────────┐
 * │ prev: ZERO  │        │ prev: H(E0) │        │ prev: H(E1) │
 * │ data: {...} │  ───▶  │ data: {...} │  ───▶  │ data: {...} │
 * │ sig: S(E0)  │        │ sig: S(E1)  │        │ sig: S(E2)  │
 * └─────────────┘        └─────────────┘        └─────────────┘
 *       │                      │                      │
 *       ▼                      ▼                      ▼
 *    H(E0)                  H(E1)                  H(E2)
 * 
 * ZERO_HASH = sha256("STIX_GENESIS_BLOCK_V1")
 */

interface HashChainManager {
  // Event creation
  createEvent(data: EvidenceEventData, prevHash: string): EvidenceEvent;
  signEvent(event: EvidenceEvent, key: SigningKey): SignedEvidenceEvent;
  
  // Chain operations
  getChainHead(traceId: string): Promise<string>;
  appendToChain(event: SignedEvidenceEvent): Promise<void>;
  
  // Verification
  verifyEvent(event: SignedEvidenceEvent): Promise<boolean>;
  verifyChain(traceId: string): Promise<ChainVerificationResult>;
  
  // Integrity
  computeEventHash(event: EvidenceEvent): string;
  verifyChainIntegrity(events: EvidenceEvent[]): boolean;
}

interface ChainVerificationResult {
  valid: boolean;
  eventCount: number;
  firstEvent: string;
  lastEvent: string;
  brokenAt?: string;
  errors: string[];
}
```

#### 4.2.2 Evidence Store (src/store/index.ts)

```typescript
/**
 * STORAGE BACKENDS:
 * 1. InMemoryEvidenceStore - Development/testing
 * 2. SQLiteEvidenceStore - Local persistence
 * 3. PostgresEvidenceStore - Production
 * 4. S3EvidenceStore - Long-term archival
 */

interface EvidenceStore {
  // Write operations
  recordDecision(event: DecisionEvent): Promise<string>;
  recordOutcome(event: OutcomeEvent): Promise<string>;
  
  // Read operations
  getEvent(eventId: string): Promise<EvidenceEvent | null>;
  getEventsByTrace(traceId: string): Promise<EvidenceEvent[]>;
  getEventsByActor(actorId: string, options: QueryOptions): Promise<EvidenceEvent[]>;
  getEventsByResource(resourceType: string, resourceId?: string, options: QueryOptions): Promise<EvidenceEvent[]>;
  
  // Chain operations
  getChainHead(traceId: string): Promise<string>;
  verifyChain(traceId: string): Promise<ChainVerificationResult>;
  
  // Export
  exportTrace(traceId: string, format: 'json' | 'csv'): Promise<string>;
  
  // Health
  health(): Promise<boolean>;
}
```

#### 4.2.3 Files to Create/Update

| File | Action | Description |
|------|--------|-------------|
| `src/core/chain.ts` | CREATE | Hash chain manager implementation |
| `src/core/signer.ts` | CREATE | Evidence signing with Ed25519 |
| `src/store/memory.ts` | CREATE | In-memory store |
| `src/store/sqlite.ts` | CREATE | SQLite persistence |
| `src/store/postgres.ts` | CREATE | PostgreSQL store |
| `src/store/s3.ts` | CREATE | S3 archival |
| `src/routes/index.ts` | UPDATE | Complete all endpoints |
| `src/routes/export.ts` | CREATE | Export/download endpoints |

---

### 4.3 Approvals Service - Complete Implementation

**Location:** `services/approvals/`

#### 4.3.1 Approvals Core (src/core/workflow.ts)

```typescript
/**
 * APPROVAL WORKFLOW
 * 
 * 1. Ticket created by Enforcer when QUARANTINE decision made
 * 2. Notifications sent to approvers
 * 3. Approvers review and decide (APPROVE/REJECT)
 * 4. Once required approvals received, ticket status updated
 * 5. Agent can retry authorization with approved ticket
 */

interface ApprovalWorkflow {
  // Ticket lifecycle
  createTicket(request: CreateTicketRequest): Promise<ApprovalTicket>;
  getTicket(ticketId: string): Promise<ApprovalTicket | null>;
  listTickets(options: ListTicketsOptions): Promise<ApprovalTicket[]>;
  
  // Decision handling
  submitDecision(ticketId: string, decision: ApprovalDecision): Promise<ApprovalTicket>;
  
  // Status checks
  isApproved(ticketId: string): Promise<boolean>;
  checkExpiration(ticketId: string): Promise<void>;
  
  // Notifications
  notifyApprovers(ticket: ApprovalTicket): Promise<void>;
  notifyRequester(ticket: ApprovalTicket, status: string): Promise<void>;
  
  // Cleanup
  expireStaleTickets(): Promise<number>;
  cancelTicket(ticketId: string, reason: string): Promise<void>;
}

interface ApprovalTicket {
  ticket_id: string;
  trace_id: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'EXPIRED' | 'CANCELLED';
  
  // Request details
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
  
  // Approval requirements
  required_count: number;
  required_role?: string;
  require_justification: boolean;
  
  // Decisions made
  decisions: ApprovalDecision[];
  
  // Timestamps
  created_at: string;
  expires_at: string;
  resolved_at?: string;
}
```

#### 4.3.2 Files to Create

| File | Action | Description |
|------|--------|-------------|
| `src/core/workflow.ts` | CREATE | Approval workflow manager |
| `src/core/notifications.ts` | CREATE | Email/webhook notifications |
| `src/store/index.ts` | CREATE | Store factory |
| `src/store/memory.ts` | CREATE | In-memory store |
| `src/store/postgres.ts` | CREATE | PostgreSQL store |
| `src/routes/index.ts` | CREATE | All REST endpoints |
| `src/routes/tickets.ts` | CREATE | Ticket CRUD operations |
| `src/routes/decisions.ts` | CREATE | Decision submission |
| `src/routes/health.ts` | CREATE | Health endpoints |
| `src/config/index.ts` | CREATE | Configuration |
| `src/index.ts` | UPDATE | Complete service entry point |

---

### 4.4 Target Verifier SDK - Complete Implementation

**Location:** `sdk/target-verifier/`

```typescript
/**
 * TARGET VERIFIER SDK
 * 
 * Used by target systems (databases, APIs, tools) to:
 * 1. Verify STIX proof tokens
 * 2. Extract claims from tokens
 * 3. Check token expiration
 * 4. Validate resource access rights
 */

interface StixVerifier {
  // Token verification
  verifyToken(token: string): Promise<VerificationResult>;
  verifyTokenForResource(token: string, resource: Resource): Promise<VerificationResult>;
  
  // Claims extraction
  extractClaims(token: string): TokenClaims;
  
  // Key management
  refreshPublicKeys(): Promise<void>;
  
  // Middleware helpers
  expressMiddleware(): ExpressMiddleware;
  fastifyPlugin(): FastifyPlugin;
}

interface VerificationResult {
  valid: boolean;
  expired: boolean;
  claims?: TokenClaims;
  error?: string;
}
```

#### 4.4.1 Files to Create

| File | Action | Description |
|------|--------|-------------|
| `src/verifier.ts` | CREATE | Core verification logic |
| `src/keys.ts` | CREATE | Public key fetching/caching |
| `src/middleware/express.ts` | CREATE | Express middleware |
| `src/middleware/fastify.ts` | CREATE | Fastify plugin |
| `src/index.ts` | UPDATE | Complete exports |

---

### 4.5 CLI Tools - Complete Implementation

#### 4.5.1 STIX Verify CLI (tools/stix-verify/)

```typescript
/**
 * CLI COMMANDS:
 * 
 * stix-verify token <token>           - Verify a proof token
 * stix-verify chain <trace-id>        - Verify evidence chain integrity
 * stix-verify policy <policy-file>    - Validate policy YAML
 * stix-verify health                  - Check all service health
 */
```

#### 4.5.2 STIX Replay (tools/stix-replay/)

```typescript
/**
 * CLI COMMANDS:
 * 
 * stix-replay trace <trace-id>        - Replay authorization trace
 * stix-replay audit <date-range>      - Generate audit report
 * stix-replay export <trace-id>       - Export trace to JSON/CSV
 * stix-replay simulate <scenario>     - Simulate policy changes
 */
```

---

## SECTION 5: FILE-BY-FILE IMPLEMENTATION GUIDE

### 5.1 Policy Service Files

#### File: services/policy/src/core/engine.ts

```typescript
/**
 * STIX Policy Evaluation Engine
 * Implements pattern matching, condition evaluation, and conflict resolution
 */

import {
  type PolicyArtifact,
  type PolicyDecision,
  type PolicyScope,
  type PolicyConditions,
  type Actor,
  type Resource,
  type Context,
  type Logger,
  hashCanonical,
  isoTimestamp,
} from '@stix/shared';
import type { Config } from '../config/index.js';
import type { PolicyStore } from '../store/index.js';
import { matchesPattern, matchesGlob } from './matcher.js';
import { evaluateConditions } from './conditions.js';

export interface EvaluationRequest {
  actor: Actor;
  action: string;
  resource: Resource;
  context: Context;
  tool_call?: {
    tool: string;
    risk_tier?: string;
    args_summary?: string;
  };
}

export class PolicyEngine {
  private readonly config: Config;
  private readonly logger: Logger;
  private readonly store: PolicyStore;
  private cache: Map<string, { decision: PolicyDecision; expires: number }> = new Map();

  constructor(config: Config, logger: Logger, store: PolicyStore) {
    this.config = config;
    this.logger = logger.child({ component: 'PolicyEngine' });
    this.store = store;
  }

  async evaluate(request: EvaluationRequest): Promise<PolicyDecision> {
    const startTime = Date.now();
    
    // Check cache
    const cacheKey = this.buildCacheKey(request);
    const cached = this.cache.get(cacheKey);
    if (cached && cached.expires > Date.now()) {
      this.logger.debug('Cache hit', { cache_key: cacheKey });
      return cached.decision;
    }

    // Find matching policies
    const allPolicies = await this.store.listPolicies({ active: true });
    const matches = allPolicies.filter(p => this.matchesScope(p, request));
    
    this.logger.debug('Found matching policies', { count: matches.length });

    if (matches.length === 0) {
      return this.defaultDeny(request);
    }

    // Evaluate conditions and filter
    const validMatches = matches.filter(p => {
      if (!p.conditions) return true;
      return evaluateConditions(p.conditions, request);
    });

    if (validMatches.length === 0) {
      return this.defaultDeny(request);
    }

    // Resolve conflicts
    const winner = this.resolveConflicts(validMatches);
    const decision = this.buildDecision(winner, request);

    // Cache result
    if (this.config.caching?.enabled) {
      this.cache.set(cacheKey, {
        decision,
        expires: Date.now() + (this.config.caching.ttlSeconds * 1000),
      });
    }

    this.logger.info('Policy evaluation complete', {
      policy_id: winner.policy_id,
      decision: decision.decision,
      duration_ms: Date.now() - startTime,
    });

    return decision;
  }

  /**
   * Check if policy scope matches request
   */
  private matchesScope(policy: PolicyArtifact, request: EvaluationRequest): boolean {
    const scope = policy.scope;
    
    // Actor type match (supports '*' wildcard)
    if (!matchesPattern(scope.actor_type, request.actor.type)) {
      return false;
    }

    // Action match (supports glob patterns)
    if (!matchesGlob(scope.action, request.action)) {
      return false;
    }

    // Resource type match (supports glob patterns)
    if (!matchesGlob(scope.resource_type, request.resource.type)) {
      return false;
    }

    // Environment match (array - any match)
    if (scope.environments && scope.environments.length > 0) {
      if (!scope.environments.includes(request.context.env)) {
        return false;
      }
    }

    // Classification match (array - all must be present)
    if (scope.classifications && scope.classifications.length > 0) {
      const resourceClassifications = request.resource.classification ?? [];
      const hasAll = scope.classifications.every(c => resourceClassifications.includes(c));
      if (!hasAll) return false;
    }

    return true;
  }

  /**
   * Resolve policy conflicts using priority and decision type
   */
  private resolveConflicts(policies: PolicyArtifact[]): PolicyArtifact {
    // Sort by priority (ascending - lower number = higher priority)
    const sorted = [...policies].sort((a, b) => {
      const priorityA = a.priority ?? 100;
      const priorityB = b.priority ?? 100;
      
      if (priorityA !== priorityB) {
        return priorityA - priorityB;
      }
      
      // At same priority: DENY > QUARANTINE > ALLOW
      const decisionOrder = { DENY: 0, QUARANTINE: 1, ALLOW: 2 };
      return decisionOrder[a.decision] - decisionOrder[b.decision];
    });

    return sorted[0];
  }

  /**
   * Build policy decision response
   */
  private buildDecision(policy: PolicyArtifact, request: EvaluationRequest): PolicyDecision {
    const policyHash = hashCanonical({
      id: policy.policy_id,
      version: policy.version,
      decision: policy.decision,
    });

    const decision: PolicyDecision = {
      decision: policy.decision,
      reason_code: policy.reason_code ?? `POLICY_${policy.decision}`,
      explanation: policy.description,
      policy: {
        id: policy.policy_id,
        version: policy.version,
        hash: policyHash,
      },
      obligations: policy.obligations ?? [],
      approval: null,
      controls: policy.controls ?? [],
      regulations: policy.regulations ?? [],
    };

    // Add approval info for QUARANTINE
    if (policy.decision === 'QUARANTINE' && policy.approval) {
      decision.approval = {
        required: true,
        approver_role: policy.approval.approver_role,
        require_count: policy.approval.require_count ?? 1,
        require_justification: policy.approval.require_justification ?? false,
        timeout_hours: policy.approval.timeout_hours ?? 24,
      };
    }

    return decision;
  }

  /**
   * Default DENY decision when no policies match
   */
  private defaultDeny(request: EvaluationRequest): PolicyDecision {
    return {
      decision: 'DENY',
      reason_code: 'NO_MATCHING_POLICY',
      explanation: 'No policy found for this request',
      policy: {
        id: 'default_deny',
        version: '1.0.0',
        hash: 'sha256:' + '0'.repeat(64),
      },
      obligations: [],
      approval: null,
      controls: [],
      regulations: [],
    };
  }

  /**
   * Build cache key from request
   */
  private buildCacheKey(request: EvaluationRequest): string {
    return hashCanonical({
      actor_type: request.actor.type,
      action: request.action,
      resource_type: request.resource.type,
      env: request.context.env,
    });
  }
}
```

#### File: services/policy/src/core/matcher.ts

```typescript
/**
 * Pattern matching utilities for policy evaluation
 */

/**
 * Match exact value or wildcard '*'
 */
export function matchesPattern(pattern: string | '*', value: string): boolean {
  if (pattern === '*') return true;
  return pattern === value;
}

/**
 * Match glob patterns (*, prefix*, *suffix, pre*fix)
 */
export function matchesGlob(pattern: string, value: string): boolean {
  if (pattern === '*') return true;
  if (!pattern.includes('*')) return pattern === value;

  const regex = new RegExp(
    '^' + pattern.replace(/\*/g, '.*').replace(/\?/g, '.') + '$'
  );
  return regex.test(value);
}

/**
 * Match array of patterns (any match = true)
 */
export function matchesAnyPattern(patterns: string[], value: string): boolean {
  return patterns.some(p => matchesGlob(p, value));
}

/**
 * Match all patterns (all must match)
 */
export function matchesAllPatterns(patterns: string[], values: string[]): boolean {
  return patterns.every(p => values.some(v => matchesGlob(p, v)));
}
```

#### File: services/policy/src/core/conditions.ts

```typescript
/**
 * Policy condition evaluation
 */

import type { PolicyConditions, Context } from '@stix/shared';
import type { EvaluationRequest } from './engine.js';

export function evaluateConditions(
  conditions: PolicyConditions,
  request: EvaluationRequest
): boolean {
  // Time window check
  if (conditions.time_window) {
    if (!isWithinTimeWindow(conditions.time_window)) {
      return false;
    }
  }

  // Signal checks
  if (conditions.require_signals) {
    const signals = request.context.signals ?? {};
    for (const [key, required] of Object.entries(conditions.require_signals)) {
      if (required && !signals[key]) {
        return false;
      }
    }
  }

  // Attribute checks
  if (conditions.require_attributes) {
    const attrs = {
      ...request.actor.attributes,
      ...request.context.attributes,
    };
    for (const [key, value] of Object.entries(conditions.require_attributes)) {
      if (attrs[key] !== value) {
        return false;
      }
    }
  }

  return true;
}

function isWithinTimeWindow(window: { start?: string; end?: string }): boolean {
  const now = new Date();
  
  if (window.start) {
    const startTime = parseTimeString(window.start);
    if (now < startTime) return false;
  }
  
  if (window.end) {
    const endTime = parseTimeString(window.end);
    if (now > endTime) return false;
  }
  
  return true;
}

function parseTimeString(timeStr: string): Date {
  // Supports: "HH:mm" (daily recurring) or ISO datetime
  if (timeStr.includes('T') || timeStr.includes('-')) {
    return new Date(timeStr);
  }
  
  // Daily time window
  const [hours, minutes] = timeStr.split(':').map(Number);
  const today = new Date();
  today.setHours(hours, minutes, 0, 0);
  return today;
}
```

---

### 5.2 Evidence Service Files

#### File: services/evidence/src/core/chain.ts

```typescript
/**
 * STIX Hash Chain Manager
 * Implements tamper-evident event chain with cryptographic integrity
 */

import {
  type EvidenceEvent,
  type SigningKey,
  hashCanonical,
  signEvidence,
  verifyEvidenceSignature,
  ZERO_HASH,
  isoTimestamp,
  generateEventId,
} from '@stix/shared';

export interface ChainVerificationResult {
  valid: boolean;
  eventCount: number;
  firstEventId?: string;
  lastEventId?: string;
  brokenAtEventId?: string;
  errors: string[];
}

export class HashChainManager {
  private readonly signingKey: SigningKey | null;
  private chainHeads: Map<string, string> = new Map(); // trace_id -> latest hash

  constructor(signingKey: SigningKey | null) {
    this.signingKey = signingKey;
  }

  /**
   * Create a new evidence event
   */
  createEvent(
    traceId: string,
    eventType: 'DECISION' | 'OUTCOME',
    data: Record<string, any>
  ): EvidenceEvent {
    const prevHash = this.chainHeads.get(traceId) ?? ZERO_HASH;
    const eventId = generateEventId();
    const timestamp = isoTimestamp();

    const event: EvidenceEvent = {
      event_id: eventId,
      trace_id: traceId,
      event_type: eventType,
      timestamp,
      version: 'v1.0',
      integrity: {
        prev_hash: prevHash,
        event_hash: '', // Computed below
        signature: '', // Added if signing enabled
        algorithm: 'sha256',
        key_id: this.signingKey?.keyId,
      },
      ...data,
    };

    // Compute event hash
    event.integrity.event_hash = this.computeEventHash(event);

    // Sign if key available
    if (this.signingKey) {
      const signResult = signEvidence(event, this.signingKey);
      event.integrity.signature = signResult.signature;
    }

    // Update chain head
    this.chainHeads.set(traceId, event.integrity.event_hash);

    return event;
  }

  /**
   * Compute hash of event (excluding signature)
   */
  computeEventHash(event: EvidenceEvent): string {
    // Hash everything except the signature itself
    const hashData = {
      event_id: event.event_id,
      trace_id: event.trace_id,
      event_type: event.event_type,
      timestamp: event.timestamp,
      version: event.version,
      prev_hash: event.integrity.prev_hash,
      // Include all data fields
      ...Object.fromEntries(
        Object.entries(event).filter(([k]) => 
          !['integrity', 'event_id', 'trace_id', 'event_type', 'timestamp', 'version'].includes(k)
        )
      ),
    };

    return hashCanonical(hashData);
  }

  /**
   * Verify a single event's integrity
   */
  async verifyEvent(event: EvidenceEvent): Promise<boolean> {
    // Verify hash
    const computedHash = this.computeEventHash(event);
    if (computedHash !== event.integrity.event_hash) {
      return false;
    }

    // Verify signature if present
    if (event.integrity.signature) {
      const verified = await verifyEvidenceSignature(event, event.integrity.signature);
      if (!verified) return false;
    }

    return true;
  }

  /**
   * Verify entire chain integrity
   */
  verifyChain(events: EvidenceEvent[]): ChainVerificationResult {
    if (events.length === 0) {
      return {
        valid: true,
        eventCount: 0,
        errors: [],
      };
    }

    // Sort by timestamp
    const sorted = [...events].sort((a, b) => 
      new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );

    const errors: string[] = [];
    let expectedPrevHash = ZERO_HASH;

    for (let i = 0; i < sorted.length; i++) {
      const event = sorted[i];

      // Check prev_hash linkage
      if (event.integrity.prev_hash !== expectedPrevHash) {
        errors.push(`Event ${event.event_id}: prev_hash mismatch`);
        return {
          valid: false,
          eventCount: sorted.length,
          firstEventId: sorted[0].event_id,
          lastEventId: sorted[sorted.length - 1].event_id,
          brokenAtEventId: event.event_id,
          errors,
        };
      }

      // Verify hash
      const computedHash = this.computeEventHash(event);
      if (computedHash !== event.integrity.event_hash) {
        errors.push(`Event ${event.event_id}: event_hash mismatch (tampered)`);
        return {
          valid: false,
          eventCount: sorted.length,
          firstEventId: sorted[0].event_id,
          lastEventId: sorted[sorted.length - 1].event_id,
          brokenAtEventId: event.event_id,
          errors,
        };
      }

      expectedPrevHash = event.integrity.event_hash;
    }

    return {
      valid: true,
      eventCount: sorted.length,
      firstEventId: sorted[0].event_id,
      lastEventId: sorted[sorted.length - 1].event_id,
      errors: [],
    };
  }

  /**
   * Get current chain head for a trace
   */
  getChainHead(traceId: string): string {
    return this.chainHeads.get(traceId) ?? ZERO_HASH;
  }

  /**
   * Initialize chain head from stored events
   */
  initializeChainHead(traceId: string, lastHash: string): void {
    this.chainHeads.set(traceId, lastHash);
  }
}
```

#### File: services/evidence/src/store/memory.ts

```typescript
/**
 * In-memory evidence store for development and testing
 */

import {
  type EvidenceEvent,
  type SigningKey,
  EvidenceNotFoundError,
  ZERO_HASH,
} from '@stix/shared';
import { HashChainManager, type ChainVerificationResult } from '../core/chain.js';
import type { Config } from '../config/index.js';
import type { Logger } from '@stix/shared';

export interface QueryOptions {
  limit?: number;
  offset?: number;
  startDate?: string;
  endDate?: string;
}

export interface EvidenceStore {
  recordDecision(data: DecisionEventData): Promise<EvidenceEvent>;
  recordOutcome(data: OutcomeEventData): Promise<EvidenceEvent>;
  getEvent(eventId: string): Promise<EvidenceEvent | null>;
  getEventsByTrace(traceId: string): Promise<EvidenceEvent[]>;
  getEventsByActor(actorId: string, options?: QueryOptions): Promise<EvidenceEvent[]>;
  verifyChain(traceId: string): Promise<ChainVerificationResult>;
  health(): Promise<boolean>;
}

export interface DecisionEventData {
  trace_id: string;
  decision: string;
  reason_code: string;
  actor: any;
  action: any;
  resource: any;
  context: any;
  policy: any;
  controls: string[];
  regulations: string[];
}

export interface OutcomeEventData {
  trace_id: string;
  status: string;
  result_summary?: string;
  error_class?: string;
  obligations_applied?: Record<string, boolean>;
}

export class InMemoryEvidenceStore implements EvidenceStore {
  private events: Map<string, EvidenceEvent> = new Map();
  private traceIndex: Map<string, string[]> = new Map();
  private actorIndex: Map<string, string[]> = new Map();
  private chainManager: HashChainManager;
  private logger: Logger;

  constructor(config: Config, logger: Logger, signingKey: SigningKey | null) {
    this.logger = logger.child({ component: 'InMemoryEvidenceStore' });
    this.chainManager = new HashChainManager(signingKey);
  }

  async recordDecision(data: DecisionEventData): Promise<EvidenceEvent> {
    const event = this.chainManager.createEvent(data.trace_id, 'DECISION', {
      decision: data.decision,
      reason_code: data.reason_code,
      actor: data.actor,
      action: data.action,
      resource: data.resource,
      context: data.context,
      policy: data.policy,
      controls: data.controls,
      regulations: data.regulations,
    });

    this.storeEvent(event);
    this.logger.debug('Recorded decision event', { event_id: event.event_id });
    
    return event;
  }

  async recordOutcome(data: OutcomeEventData): Promise<EvidenceEvent> {
    const event = this.chainManager.createEvent(data.trace_id, 'OUTCOME', {
      outcome: {
        status: data.status,
        result_summary: data.result_summary,
        error_class: data.error_class,
      },
      obligations_applied: data.obligations_applied,
    });

    this.storeEvent(event);
    this.logger.debug('Recorded outcome event', { event_id: event.event_id });
    
    return event;
  }

  async getEvent(eventId: string): Promise<EvidenceEvent | null> {
    return this.events.get(eventId) ?? null;
  }

  async getEventsByTrace(traceId: string): Promise<EvidenceEvent[]> {
    const eventIds = this.traceIndex.get(traceId) ?? [];
    return eventIds.map(id => this.events.get(id)!).filter(Boolean);
  }

  async getEventsByActor(actorId: string, options?: QueryOptions): Promise<EvidenceEvent[]> {
    const eventIds = this.actorIndex.get(actorId) ?? [];
    let events = eventIds.map(id => this.events.get(id)!).filter(Boolean);
    
    if (options?.limit) {
      events = events.slice(options.offset ?? 0, (options.offset ?? 0) + options.limit);
    }
    
    return events;
  }

  async verifyChain(traceId: string): Promise<ChainVerificationResult> {
    const events = await this.getEventsByTrace(traceId);
    return this.chainManager.verifyChain(events);
  }

  async health(): Promise<boolean> {
    return true;
  }

  private storeEvent(event: EvidenceEvent): void {
    this.events.set(event.event_id, event);
    
    // Index by trace
    const traceEvents = this.traceIndex.get(event.trace_id) ?? [];
    traceEvents.push(event.event_id);
    this.traceIndex.set(event.trace_id, traceEvents);
    
    // Index by actor
    const actorId = (event as any).actor?.id;
    if (actorId) {
      const actorEvents = this.actorIndex.get(actorId) ?? [];
      actorEvents.push(event.event_id);
      this.actorIndex.set(actorId, actorEvents);
    }
  }
}

export async function createEvidenceStore(
  config: Config,
  logger: Logger,
  signingKey: SigningKey | null
): Promise<EvidenceStore> {
  const storeType = config.storage?.type ?? 'memory';
  
  switch (storeType) {
    case 'memory':
      return new InMemoryEvidenceStore(config, logger, signingKey);
    // Future: case 'postgres': return new PostgresEvidenceStore(config, logger, signingKey);
    default:
      return new InMemoryEvidenceStore(config, logger, signingKey);
  }
}
```

---

## SECTION 6: TESTING STRATEGY

### 6.1 Unit Tests (Per Service)

```
tests/
├── unit/
│   ├── shared/
│   │   ├── utils.test.ts
│   │   ├── crypto.test.ts
│   │   ├── validators.test.ts
│   │   └── errors.test.ts
│   ├── policy/
│   │   ├── engine.test.ts
│   │   ├── matcher.test.ts
│   │   ├── conditions.test.ts
│   │   └── store.test.ts
│   ├── evidence/
│   │   ├── chain.test.ts
│   │   └── store.test.ts
│   └── approvals/
│       ├── workflow.test.ts
│       └── store.test.ts
```

### 6.2 Integration Tests

```
tests/
├── integration/
│   ├── enforcer-policy.test.ts      # Enforcer -> Policy communication
│   ├── enforcer-evidence.test.ts    # Enforcer -> Evidence recording
│   ├── enforcer-approvals.test.ts   # Enforcer -> Approval creation
│   ├── approval-flow.test.ts        # Full approval workflow
│   └── full-authorization.test.ts   # Complete authorization flow
```

### 6.3 E2E Tests

```
tests/
├── e2e/
│   ├── allow-flow.test.ts           # ALLOW decision end-to-end
│   ├── deny-flow.test.ts            # DENY decision end-to-end
│   ├── quarantine-flow.test.ts      # QUARANTINE with approval
│   ├── evidence-chain.test.ts       # Hash chain integrity
│   └── fail-mode.test.ts            # Service unavailability handling
```

---

## SECTION 7: DEPLOYMENT CHECKLIST

### 7.1 Development Environment

```bash
# Prerequisites
node --version  # >= 20.0.0
pnpm --version  # >= 8.0.0

# Setup
cd D:\Research\STIX
pnpm install
pnpm build

# Run services locally
pnpm dev

# Run tests
pnpm test
```

### 7.2 Docker Deployment

```bash
# Build and start all services
pnpm docker:build
pnpm docker:up

# View logs
pnpm docker:logs

# Stop services
pnpm docker:down
```

### 7.3 Kubernetes Deployment

```bash
# Create namespace
kubectl create namespace stix

# Apply configurations
kubectl apply -f deploy/k8s/namespace.yaml
kubectl apply -f deploy/k8s/configmap.yaml
kubectl apply -f deploy/k8s/secrets.yaml
kubectl apply -f deploy/k8s/services/
kubectl apply -f deploy/k8s/deployments/

# Verify
kubectl get pods -n stix
kubectl get services -n stix
```

### 7.4 Production Checklist

- [ ] Configure PostgreSQL for production storage
- [ ] Set up Redis cluster for caching
- [ ] Generate Ed25519 signing keys
- [ ] Configure mTLS certificates
- [ ] Set DEFAULT_FAIL_MODE=CLOSED
- [ ] Configure network policies
- [ ] Enable Prometheus metrics
- [ ] Set up Grafana dashboards
- [ ] Configure alerting rules
- [ ] Implement backup strategy for evidence store
- [ ] Configure log aggregation
- [ ] Set up horizontal pod autoscaling
- [ ] Configure resource limits and requests

---

## SECTION 8: EXECUTION INSTRUCTIONS FOR CLAUDE CODE AGENTS

### 8.1 Execution Order

```
PHASE 1: Core Infrastructure
1. Verify shared package builds correctly
2. Complete policy service engine and store
3. Complete evidence service chain and store
4. Complete approvals service workflow and store

PHASE 2: Service Integration
5. Complete enforcer routes and clients
6. Test service-to-service communication
7. Implement integration tests

PHASE 3: SDKs and Tools
8. Complete target-verifier SDK
9. Complete stix-verify CLI
10. Complete stix-replay tool

PHASE 4: Testing and Documentation
11. Complete unit tests for all services
12. Complete E2E tests
13. Generate OpenAPI documentation
14. Write integration guides
```

### 8.2 Agent Execution Commands

```bash
# Start implementation
cd D:\Research\STIX

# Build shared package first (dependency for all)
cd packages/shared && pnpm build && cd ../..

# Implement Policy Service
# [Create/update files as specified in Section 5.1]
cd services/policy && pnpm build && pnpm test && cd ../..

# Implement Evidence Service  
# [Create/update files as specified in Section 5.2]
cd services/evidence && pnpm build && pnpm test && cd ../..

# Implement Approvals Service
# [Create/update files as specified in Section 4.3]
cd services/approvals && pnpm build && pnpm test && cd ../..

# Verify full build
pnpm build

# Run all tests
pnpm test

# Start services
pnpm dev
```

### 8.3 Success Criteria

| Criterion | Validation |
|-----------|------------|
| Shared package builds | `cd packages/shared && pnpm build` exits 0 |
| All services build | `pnpm build` exits 0 |
| All tests pass | `pnpm test` exits 0 |
| Services start | `pnpm dev` starts all 4 services |
| Health checks pass | `curl localhost:3001/health` returns 200 |
| Authorization works | Demo script runs successfully |
| Evidence chain valid | `stix-verify chain <trace-id>` validates |

---

## SECTION 9: API REFERENCE

### 9.1 Enforcer Service (Port 3001)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/authorize` | Request authorization |
| POST | `/api/v1/authorize/retry` | Retry with approval |
| POST | `/api/v1/outcome` | Record execution outcome |
| GET | `/health` | Liveness check |
| GET | `/ready` | Readiness check |

### 9.2 Policy Service (Port 3002)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/evaluate` | Evaluate policy |
| GET | `/api/v1/policies` | List policies |
| GET | `/api/v1/policies/:id` | Get policy |
| POST | `/api/v1/policies` | Create policy |
| PUT | `/api/v1/policies/:id` | Update policy |
| DELETE | `/api/v1/policies/:id` | Delete policy |
| POST | `/api/v1/policies/reload` | Reload from disk |

### 9.3 Evidence Service (Port 3003)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/evidence/decision` | Record decision |
| POST | `/api/v1/evidence/outcome` | Record outcome |
| GET | `/api/v1/evidence/:eventId` | Get event |
| GET | `/api/v1/evidence/trace/:traceId` | Get trace events |
| GET | `/api/v1/evidence/verify/:traceId` | Verify chain |
| GET | `/api/v1/evidence/export/:traceId` | Export trace |

### 9.4 Approvals Service (Port 3004)

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/approvals/tickets` | Create ticket |
| GET | `/api/v1/approvals/tickets/:id` | Get ticket |
| GET | `/api/v1/approvals/tickets` | List tickets |
| POST | `/api/v1/approvals/tickets/:id/decide` | Submit decision |
| POST | `/api/v1/approvals/tickets/:id/cancel` | Cancel ticket |
| GET | `/api/v1/approvals/check` | Check approval status |

---

## SECTION 10: GLOSSARY

| Term | Definition |
|------|------------|
| **Actor** | Entity requesting authorization (AI agent, human, service) |
| **Decision** | Authorization outcome (ALLOW, DENY, QUARANTINE) |
| **Evidence** | Immutable record of authorization decision and outcome |
| **Hash Chain** | Cryptographically-linked sequence of evidence events |
| **Obligation** | Action required when authorization is granted |
| **Policy** | Rule defining authorization conditions |
| **Proof Token** | Signed JWT proving authorization was granted |
| **Quarantine** | Decision requiring human approval before action |
| **Trace ID** | Unique identifier correlating all events in a flow |

---

## APPENDIX A: DIRECTORY STRUCTURE

```
D:\Research\STIX\
├── packages/
│   └── shared/                 # Shared utilities, types, crypto
├── services/
│   ├── enforcer/              # Authorization decision engine
│   ├── policy/                # Policy management and evaluation
│   ├── evidence/              # Audit trail with hash chain
│   └── approvals/             # Human-in-the-loop workflows
├── sdk/
│   ├── agent-sdk/             # Client SDK for AI agents
│   └── target-verifier/       # SDK for target systems
├── tools/
│   ├── stix-verify/           # CLI for verification
│   └── stix-replay/           # CLI for audit replay
├── policies/
│   └── examples/              # Example policy packs
├── deploy/
│   ├── docker/                # Docker Compose configs
│   └── k8s/                   # Kubernetes manifests
├── tests/
│   ├── unit/                  # Unit tests
│   ├── integration/           # Integration tests
│   └── e2e/                   # End-to-end tests
├── docs/                      # Documentation
├── scripts/                   # Build and utility scripts
├── package.json               # Root package config
├── pnpm-workspace.yaml        # Workspace config
├── tsconfig.base.json         # Base TypeScript config
├── vitest.config.ts           # Test configuration
└── CLAUDE_CODE_DEVELOPMENT_VISION.md  # This document
```

---

**END OF DOCUMENT**

*This document serves as the authoritative implementation guide for STIX. Claude Code agents should follow this specification precisely to achieve a production-ready enterprise compliance platform.*
