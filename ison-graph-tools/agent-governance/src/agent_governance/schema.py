"""
Agent Governance Schema Definitions
====================================

Comprehensive type definitions for all 15 governance domains:
1. Authority & Delegation
2. Policy Engine
3. Compliance Framework
4. Audit Trail
5. Risk Assessment
6. Human Oversight & Escalation
7. Resource Governance
8. Multi-Agent Coordination
9. Ethics & Values
10. Capability Governance
11. Incident Response
12. Meta-Governance
13. Cross-Organizational
14. Temporal Governance
15. Observability & Telemetry
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# =============================================================================
# Core Enums
# =============================================================================

class AuthorityLevel(str, Enum):
    ROOT = "root"
    META = "meta"
    ELEVATED = "elevated"
    DELEGATED = "delegated"
    LIMITED = "limited"
    NONE = "none"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Enforcement(str, Enum):
    HARD = "hard"  # Cannot be overridden
    SOFT = "soft"  # Can be overridden with approval


class PolicyStatus(str, Enum):
    ACTIVE = "active"
    DRAFT = "draft"
    DEPRECATED = "deprecated"
    SUSPENDED = "suspended"


class IncidentSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(str, Enum):
    ACTIVE = "active"
    CONTAINED = "contained"
    RESOLVED = "resolved"
    CLOSED = "closed"


class EscalationLevel(str, Enum):
    L1_AUTO = "L1_auto"
    L2_AGENT = "L2_agent"
    L3_OPERATOR = "L3_operator"
    L4_MANAGER = "L4_manager"
    L5_EXECUTIVE = "L5_executive"
    L6_BOARD = "L6_board"


class TrustLevel(str, Enum):
    INTERNAL = "internal"
    TRUSTED = "trusted"
    VERIFIED = "verified"
    LIMITED = "limited"
    UNTRUSTED = "untrusted"


class CapabilityMaturity(str, Enum):
    STABLE = "stable"
    BETA = "beta"
    EXPERIMENTAL = "experimental"
    DEPRECATED = "deprecated"


class ControlType(str, Enum):
    PREVENTIVE = "preventive"
    DETECTIVE = "detective"
    CORRECTIVE = "corrective"


class ValuePriority(str, Enum):
    HIGHEST = "highest"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


# =============================================================================
# 1. Authority & Delegation Types
# =============================================================================

@dataclass
class Principal:
    """An entity that can hold authority (human, agent, or system)"""
    id: str
    type: str  # "human", "agent", "system"
    name: str
    authority_level: AuthorityLevel
    active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthorityScope:
    """A scope of authority that can be granted"""
    id: str
    name: str
    risk_level: RiskLevel
    requires_human: bool = False
    conditions: Optional[str] = None
    description: str = ""


@dataclass
class Delegation:
    """A delegation of authority from one principal to another"""
    id: str
    from_principal: str
    to_principal: str
    scopes: List[str]
    conditions: str = ""
    granted_at: str = ""
    expires_at: Optional[str] = None
    revocable: bool = True
    audit_required: bool = True


@dataclass
class DelegationChain:
    """Tracks multi-hop delegations"""
    id: str
    chain: List[str]  # List of delegation IDs
    depth: int
    authority_decay: float  # 0.0-1.0, how much authority is retained
    root_principal: str
    leaf_principal: str


# =============================================================================
# 2. Policy Engine Types
# =============================================================================

@dataclass
class Policy:
    """A governance policy containing rules"""
    id: str
    name: str
    priority: int
    status: PolicyStatus
    effective_date: str
    description: str = ""
    owner: str = ""
    version: str = "1.0"


@dataclass
class Rule:
    """A rule within a policy"""
    id: str
    policy_id: str
    condition: str  # Expression to evaluate
    action: str  # Action to take if condition matches
    exception_allows: Optional[str] = None
    priority: int = 0
    description: str = ""


@dataclass
class RuleCondition:
    """A condition that can be evaluated"""
    id: str
    rule_id: str
    expression: str
    eval_type: str  # "attribute", "threshold", "function", "computed"
    cacheable: bool = True


@dataclass
class PolicyEvaluation:
    """Record of a policy evaluation"""
    id: str
    rule_id: str
    context_hash: str
    result: str  # "allow", "deny", "escalate"
    explanation: str
    timestamp: str
    duration_ms: int = 0
    inputs: Dict[str, Any] = field(default_factory=dict)


# =============================================================================
# 3. Compliance Framework Types
# =============================================================================

@dataclass
class ComplianceFramework:
    """A regulatory or compliance framework"""
    id: str
    name: str  # GDPR, HIPAA, SOX, EU AI Act, etc.
    jurisdiction: str
    effective_date: str
    applies_to: str
    description: str = ""


@dataclass
class ComplianceRequirement:
    """A specific requirement from a framework"""
    id: str
    framework_id: str
    article: str
    description: str
    risk_if_violated: str
    mandatory: bool = True


@dataclass
class ComplianceControl:
    """A control that satisfies requirements"""
    id: str
    name: str
    type: str  # "technical", "procedural", "physical"
    automated: bool
    description: str = ""
    evidence_location: str = ""


@dataclass
class ComplianceGap:
    """A gap in compliance coverage"""
    id: str
    requirement_id: str
    behavior_id: str
    gap_description: str
    remediation: str
    priority: str
    due_date: Optional[str] = None


# =============================================================================
# 4. Audit Trail Types
# =============================================================================

@dataclass
class Decision:
    """A decision made by an agent"""
    id: str
    agent_id: str
    type: str  # "data_access", "action_execution", "recommendation", etc.
    timestamp: str
    outcome: str
    confidence: float
    reversible: bool = True


@dataclass
class DecisionInput:
    """An input that influenced a decision"""
    id: str
    decision_id: str
    input_type: str
    source: str
    content_hash: str
    sensitivity: str  # "low", "medium", "high"


@dataclass
class DecisionRationale:
    """The rationale behind a decision"""
    id: str
    decision_id: str
    reasoning_type: str
    explanation: str
    verifiable: bool = True


@dataclass
class DecisionEffect:
    """The effect of a decision"""
    id: str
    decision_id: str
    effect_type: str
    target: str
    reversible: bool = True
    reversed: bool = False


@dataclass
class Counterfactual:
    """What would have happened under different conditions"""
    id: str
    decision_id: str
    if_different: str
    would_result: str


# =============================================================================
# 5. Risk Assessment Types
# =============================================================================

@dataclass
class Risk:
    """A risk to be managed"""
    id: str
    category: str  # "operational", "security", "compliance", etc.
    name: str
    inherent_score: float  # 0.0-1.0
    residual_score: float
    appetite_threshold: float
    description: str = ""


@dataclass
class Threat:
    """A threat that contributes to risk"""
    id: str
    name: str
    likelihood: str  # "high", "medium", "low"
    impact: str
    risks_affected: List[str]
    description: str = ""


@dataclass
class RiskControl:
    """A control that mitigates risk"""
    id: str
    name: str
    type: ControlType
    effectiveness: float  # 0.0-1.0
    cost: str  # "low", "medium", "high"
    threats_mitigated: List[str]


@dataclass
class RiskIncident:
    """A risk incident that occurred"""
    id: str
    risk_id: str
    threat_id: str
    severity: str
    timestamp: str
    resolved: bool
    root_cause: str = ""
    lessons_learned: str = ""


# =============================================================================
# 6. Human Oversight & Escalation Types
# =============================================================================

@dataclass
class EscalationTrigger:
    """A condition that triggers escalation"""
    id: str
    condition: str
    level: EscalationLevel
    cooldown: str
    context: str
    description: str = ""


@dataclass
class HumanReviewer:
    """A human available for review"""
    id: str
    name: str
    expertise: List[str]
    availability: str
    fatigue_score: float = 0.0
    current_load: int = 0


@dataclass
class EscalationEvent:
    """An escalation event"""
    id: str
    trigger_id: str
    level: EscalationLevel
    assigned_to: Optional[str]
    status: str  # "pending", "assigned", "resolved", "escalated"
    created_at: str
    resolved_at: Optional[str] = None
    resolution: str = ""


@dataclass
class HumanDecisionFeedback:
    """Feedback from human decisions for learning"""
    id: str
    escalation_id: str
    human_action: str
    agent_would_have: str
    learning: str
    timestamp: str


# =============================================================================
# 7. Resource Governance Types
# =============================================================================

@dataclass
class ResourceType:
    """A type of resource to govern"""
    id: str
    name: str
    unit: str
    cost_per_unit: float
    scarcity: str  # "low", "medium", "high"


@dataclass
class Budget:
    """A budget allocation"""
    id: str
    owner: str
    resource_id: str
    allocated: float
    consumed: float
    period: str  # "hourly", "daily", "monthly"
    alert_threshold: float = 0.8


@dataclass
class SpendEvent:
    """A resource spend event"""
    id: str
    agent_id: str
    resource_id: str
    amount: float
    task: str
    timestamp: str
    approved: bool = True


@dataclass
class AllocationPolicy:
    """A policy for resource allocation"""
    id: str
    name: str
    priority: str
    conditions: str
    description: str = ""


# =============================================================================
# 8. Multi-Agent Coordination Types
# =============================================================================

@dataclass
class AgentGroup:
    """A group of coordinating agents"""
    id: str
    name: str
    purpose: str
    formation: str  # "dynamic", "static", "fixed"
    status: str


@dataclass
class CoordinationRole:
    """A role within an agent group"""
    id: str
    group_id: str
    agent_id: str
    role: str  # "coordinator", "worker", "chair", etc.
    authority: str
    duration: str  # "session", "permanent", "task"


@dataclass
class CoordinationProtocol:
    """A protocol for agent coordination"""
    id: str
    group_id: str
    type: str  # "task_distribution", "voting", "conflict", etc.
    rules: str
    enforced_by: str = ""


@dataclass
class SharedState:
    """Shared state among agents"""
    id: str
    group_id: str
    state_type: str
    owner: str
    access: str  # Access control specification


@dataclass
class CoordinationViolation:
    """A violation of coordination protocol"""
    id: str
    agent_id: str
    protocol_id: str
    violation: str
    action_taken: str
    timestamp: str


# =============================================================================
# 9. Ethics & Values Types
# =============================================================================

@dataclass
class Value:
    """A core value"""
    id: str
    name: str
    priority: ValuePriority
    measurable: bool
    source: str  # "mission", "principle", "operational"
    description: str = ""


@dataclass
class EthicalPrinciple:
    """An ethical principle derived from values"""
    id: str
    name: str
    derived_from: List[str]  # Value IDs
    operationalization: str  # How to measure/enforce
    description: str = ""


@dataclass
class EthicalDilemma:
    """A dilemma involving conflicting values"""
    id: str
    situation: str
    values_in_tension: List[str]
    resolution_principle: str
    examples: List[str] = field(default_factory=list)


@dataclass
class ValueMeasurement:
    """Measurement of value alignment"""
    id: str
    value_id: str
    metric: str
    current: float
    target: float
    trend: str  # "improving", "stable", "declining"
    timestamp: str


@dataclass
class ValueViolation:
    """A violation of a value"""
    id: str
    value_id: str
    agent_id: str
    context: str
    severity: str
    remediation: str
    timestamp: str


# =============================================================================
# 10. Capability Governance Types
# =============================================================================

@dataclass
class Capability:
    """A capability that can be enabled/disabled"""
    id: str
    name: str
    risk_level: RiskLevel
    maturity: CapabilityMaturity
    default_state: str  # "enabled", "disabled"
    description: str = ""


@dataclass
class FeatureFlag:
    """A feature flag controlling capability"""
    id: str
    capability_id: str
    name: str
    state: str  # "enabled", "disabled"
    conditions: str


@dataclass
class CapabilityGrant:
    """A grant of capability to an agent"""
    id: str
    capability_id: str
    principal_id: str
    granted_by: str
    conditions: str
    granted_at: str
    expires_at: Optional[str] = None


@dataclass
class CapabilityRequest:
    """A request for capability"""
    id: str
    capability_id: str
    requester_id: str
    reason: str
    status: str  # "pending", "approved", "denied"
    reviewer: Optional[str] = None
    reviewed_at: Optional[str] = None


# =============================================================================
# 11. Incident Response Types
# =============================================================================

@dataclass
class Incident:
    """A governance incident"""
    id: str
    severity: IncidentSeverity
    category: str  # "safety", "data_breach", "service", etc.
    status: IncidentStatus
    detected_at: str
    resolved_at: Optional[str] = None
    description: str = ""


@dataclass
class IncidentPhase:
    """A phase in incident response"""
    id: str
    name: str  # "detection", "triage", "containment", etc.
    typical_duration: str
    authority_level: str


@dataclass
class ResponseAction:
    """An action taken in response to incident"""
    id: str
    incident_id: str
    phase_id: str
    action: str
    executed_by: str
    timestamp: str
    result: str = ""


@dataclass
class IncidentCommunication:
    """Communication about an incident"""
    id: str
    incident_id: str
    type: str  # "alert", "status", "escalation"
    audience: str
    sent_at: str
    content_hash: str


@dataclass
class PostMortem:
    """Post-mortem analysis of an incident"""
    id: str
    incident_id: str
    findings: List[str]
    root_causes: List[str]
    actions: List[str]
    completed_at: str


# =============================================================================
# 12. Meta-Governance Types
# =============================================================================

@dataclass
class GovernanceRule:
    """A rule about governance itself"""
    id: str
    domain: str
    rule: str
    version: str
    effective_date: str
    description: str = ""


@dataclass
class GovernanceChange:
    """A change to governance rules"""
    id: str
    rule_id: str
    change_type: str  # "amendment", "threshold", "new_level"
    proposed_by: str
    status: str  # "pending", "approved", "rejected"
    reviewed_by: Optional[str] = None
    rationale: str = ""


@dataclass
class GovernanceReview:
    """A scheduled review of governance"""
    id: str
    type: str
    frequency: str
    last_review: str
    next_review: str
    findings: List[str] = field(default_factory=list)


@dataclass
class GovernanceAuthority:
    """Authority over governance itself"""
    id: str
    name: str
    scope: str
    members: List[str]
    decision_process: str = ""


# =============================================================================
# 13. Cross-Organizational Types
# =============================================================================

@dataclass
class Organization:
    """An organization in the governance ecosystem"""
    id: str
    name: str
    trust_level: TrustLevel
    jurisdiction: str
    agreement_status: str


@dataclass
class ExternalAgent:
    """An agent from another organization"""
    id: str
    org_id: str
    name: str
    capabilities: List[str]
    certified: bool


@dataclass
class TrustAgreement:
    """An agreement between organizations"""
    id: str
    org_a: str
    org_b: str
    type: str  # "data_processing", "service_level", "nda"
    signed_date: str
    expires_date: str
    terms: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CrossOrgPolicy:
    """A policy governing cross-org interactions"""
    id: str
    organizations: List[str]
    policy: str
    enforcement: str


# =============================================================================
# 14. Temporal Governance Types
# =============================================================================

@dataclass
class TemporalAuthority:
    """Time-bound authority"""
    id: str
    principal_id: str
    authority_id: str
    granted_at: str
    expires_at: str
    renewable: bool


@dataclass
class RuleVersion:
    """A version of a rule over time"""
    id: str
    rule_id: str
    version: str
    effective_from: str
    effective_until: Optional[str]
    changes: str


@dataclass
class TemporalContext:
    """The governance context at a point in time"""
    id: str
    timestamp: str
    active_rules: List[str]
    active_authorities: List[str]


@dataclass
class ScheduledChange:
    """A scheduled governance change"""
    id: str
    type: str  # "rule_update", "authority_exp", "review"
    target_id: str
    scheduled_for: str
    status: str


# =============================================================================
# 15. Observability Types
# =============================================================================

@dataclass
class GovernanceMetric:
    """A metric about governance system health"""
    id: str
    name: str
    type: str  # "throughput", "latency", "accuracy", etc.
    current: float
    threshold: float
    status: str  # "healthy", "warning", "critical"


@dataclass
class DecisionPattern:
    """A pattern detected in decisions"""
    id: str
    pattern: str
    frequency: str
    expected: float
    anomaly_score: float


@dataclass
class TelemetryStream:
    """A stream of telemetry data"""
    id: str
    source: str
    data_type: str
    retention: str
    sampling: str


@dataclass
class Dashboard:
    """A governance dashboard"""
    id: str
    name: str
    audience: str
    refresh_rate: str
    metrics: List[str]


@dataclass
class Alert:
    """An alert from the governance system"""
    id: str
    metric_id: str
    condition: str
    severity: str
    notification_channel: str
    triggered_at: str
    acknowledged: bool = False


# =============================================================================
# Edge Type Definitions
# =============================================================================

EDGE_TYPES = {
    # Authority edges
    "GRANTS": "Principal grants scope to another principal",
    "DELEGATES": "Principal delegates authority",
    "DELEGATION_CHAIN": "Links in delegation chain",
    "CANNOT_DELEGATE": "Restriction on delegation",
    "AUTHORITY_INHERITANCE": "Authority inherited from parent",

    # Policy edges
    "POLICY_CONTAINS": "Policy contains rule",
    "RULE_EVALUATES": "Rule evaluates condition",
    "RULE_PRECEDENCE": "Rule takes precedence over another",
    "EXCEPTION_ALLOWS": "Exception allows override",

    # Compliance edges
    "REQUIREMENT_FROM": "Requirement from framework",
    "SATISFIED_BY": "Requirement satisfied by control",
    "REQUIRES_COMPLIANCE": "Behavior requires compliance",
    "COMPLIANCE_GAP": "Gap in compliance",
    "AUDIT_EVIDENCE": "Evidence for audit",

    # Audit edges
    "DECISION_INPUT": "Input to decision",
    "DECISION_RATIONALE": "Rationale for decision",
    "DECISION_EFFECT": "Effect of decision",
    "DECISION_CHAIN": "Chain of related decisions",
    "COUNTERFACTUAL": "Alternative outcome",

    # Risk edges
    "THREAT_TO": "Threat contributes to risk",
    "MITIGATED_BY": "Risk mitigated by control",
    "RISK_REDUCED_BY": "Risk reduced by control",
    "INCIDENT_FOR": "Incident related to risk",

    # Escalation edges
    "ESCALATION_PATH": "Path for escalation",
    "ASSIGNED_TO": "Escalation assigned to reviewer",
    "FEEDBACK_FROM": "Feedback from human decision",

    # Resource edges
    "BUDGET_FOR": "Budget allocated for resource",
    "SPEND_FROM": "Spend event from budget",
    "ALLOCATION_POLICY": "Policy for allocation",

    # Coordination edges
    "ROLE_IN": "Agent has role in group",
    "PROTOCOL_FOR": "Protocol for group",
    "SHARED_STATE": "State shared in group",
    "COORDINATION_VIOLATION": "Violation of protocol",

    # Ethics edges
    "VALUE_HIERARCHY": "Value dominates another",
    "PRINCIPLE_FROM": "Principle derived from value",
    "DILEMMA_INVOLVES": "Dilemma involves values",
    "VALUE_MEASUREMENT": "Measurement of value",
    "VALUE_VIOLATION": "Violation of value",

    # Capability edges
    "CAPABILITY_GRANT": "Grant of capability",
    "CAPABILITY_REQUEST": "Request for capability",
    "CAPABILITY_DEPENDENCY": "Capability depends on another",
    "FEATURE_FLAG": "Flag controlling capability",

    # Incident edges
    "INCIDENT_PHASE": "Phase of incident",
    "RESPONSE_ACTION": "Action in response",
    "INCIDENT_COMMUNICATION": "Communication about incident",
    "POST_MORTEM": "Post-mortem of incident",

    # Meta-governance edges
    "RULE_AUTHORITY": "Authority over rule",
    "GOVERNANCE_CHANGE": "Change to governance",
    "GOVERNANCE_REVIEW": "Review of governance",

    # Cross-org edges
    "TRUST_RELATIONSHIP": "Trust between orgs",
    "AGREEMENT_BETWEEN": "Agreement between orgs",
    "CROSS_ORG_POLICY": "Policy for cross-org",

    # Temporal edges
    "TEMPORAL_AUTHORITY": "Time-bound authority",
    "RULE_VERSION": "Version of rule",
    "SCHEDULED_CHANGE": "Scheduled change",

    # Observability edges
    "METRIC_ALERT": "Alert from metric",
    "PATTERN_DETECTED": "Pattern detected",
    "DASHBOARD_SHOWS": "Dashboard shows metric",
}


# =============================================================================
# Governance Domain Enum
# =============================================================================

class GovernanceDomain(str, Enum):
    ACCESS_CONTROL = "access_control"
    DECISION_AUTHORITY = "decision_authority"
    COMPLIANCE = "compliance"
    ETHICS = "ethics"
    RESOURCE = "resource"
    AUDIT = "audit"
    COORDINATION = "coordination"
    HUMAN_OVERSIGHT = "human_oversight"
    RISK = "risk"
    CAPABILITY = "capability"
    INCIDENT = "incident"
    META = "meta"
    CROSS_ORG = "cross_org"
    TEMPORAL = "temporal"
    OBSERVABILITY = "observability"
    ROLLBACK = "rollback"


# =============================================================================
# 16. Rollback & Recovery Types
# =============================================================================

class RollbackStatus(str, Enum):
    """Status of a rollback operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"
    CANCELLED = "cancelled"


class RollbackType(str, Enum):
    """Type of rollback operation"""
    FULL = "full"  # Complete rollback of all changes
    PARTIAL = "partial"  # Rollback specific steps
    CHECKPOINT = "checkpoint"  # Rollback to checkpoint
    COMPENSATING = "compensating"  # Execute compensating transaction
    CASCADING = "cascading"  # Rollback with dependent actions


class SnapshotType(str, Enum):
    """Type of state snapshot"""
    FULL = "full"  # Complete state capture
    INCREMENTAL = "incremental"  # Only changes since last snapshot
    DELTA = "delta"  # Diff from baseline
    SCHEMA = "schema"  # Schema/structure only
    DATA = "data"  # Data only


class CompensatingActionType(str, Enum):
    """Type of compensating action"""
    UNDO = "undo"  # Direct undo
    REVERSE = "reverse"  # Reverse operation
    RESTORE = "restore"  # Restore from snapshot
    NULLIFY = "nullify"  # Nullify effects
    REVERT = "revert"  # Revert to previous state


class RollbackTrigger(str, Enum):
    """What triggered the rollback"""
    MANUAL = "manual"  # User/admin initiated
    AUTOMATIC = "automatic"  # System detected issue
    POLICY = "policy"  # Policy violation
    ERROR = "error"  # Error during execution
    TIMEOUT = "timeout"  # Operation timeout
    ESCALATION = "escalation"  # Escalation decision


@dataclass
class ActionSnapshot:
    """Snapshot of state before an action"""
    id: str
    action_id: str
    agent_id: str
    snapshot_type: SnapshotType
    timestamp: str
    state_data: Dict[str, Any]
    affected_resources: List[str]
    checksum: str
    size_bytes: int = 0
    expires_at: Optional[str] = None


@dataclass
class CompensatingTransaction:
    """Definition of how to compensate/undo an action"""
    id: str
    action_type: str
    compensating_action: str
    action_type_enum: CompensatingActionType
    preconditions: List[str]
    postconditions: List[str]
    idempotent: bool = True
    timeout_seconds: int = 300
    retry_policy: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RollbackCheckpoint:
    """A checkpoint for multi-step rollback"""
    id: str
    transaction_id: str
    step_number: int
    name: str
    timestamp: str
    snapshot_id: str
    can_rollback_to: bool = True
    dependencies: List[str] = field(default_factory=list)


@dataclass
class RollbackOperation:
    """A rollback operation"""
    id: str
    transaction_id: str
    rollback_type: RollbackType
    trigger: RollbackTrigger
    triggered_by: str
    status: RollbackStatus
    started_at: str
    completed_at: Optional[str] = None
    target_checkpoint: Optional[str] = None
    steps_total: int = 0
    steps_completed: int = 0
    error_message: str = ""


@dataclass
class RollbackStep:
    """A single step in a rollback operation"""
    id: str
    rollback_id: str
    step_number: int
    action_to_undo: str
    compensating_action: str
    status: RollbackStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: str = ""
    retries: int = 0


@dataclass
class RollbackPolicy:
    """Policy for automatic rollback"""
    id: str
    name: str
    trigger_conditions: List[str]
    rollback_type: RollbackType
    max_rollback_depth: int
    timeout_seconds: int
    requires_approval: bool = False
    notification_channels: List[str] = field(default_factory=list)


@dataclass
class TransactionBoundary:
    """Defines a logical transaction boundary"""
    id: str
    name: str
    agent_id: str
    started_at: str
    status: str = "active"  # "active", "committed", "rolled_back"
    completed_at: Optional[str] = None
    actions: List[str] = field(default_factory=list)
    checkpoints: List[str] = field(default_factory=list)
