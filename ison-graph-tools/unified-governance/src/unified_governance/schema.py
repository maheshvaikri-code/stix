"""
Unified Governance Schema
=========================

Cross-domain data models for integrating GDPR, CCPA, PII, and Agent Governance.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set


# =============================================================================
# Governance Domain Types
# =============================================================================

class GovernanceDomain(str, Enum):
    """Governance domains available in the unified system."""
    AGENT = "agent"
    GDPR = "gdpr"
    CCPA = "ccpa"
    PII = "pii"
    HIPAA = "hipaa"
    PCI_DSS = "pci_dss"
    SOX = "sox"
    EU_AI_ACT = "eu_ai_act"


class ComplianceStatus(str, Enum):
    """Cross-domain compliance status."""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"
    PENDING_REVIEW = "pending_review"
    REMEDIATION_IN_PROGRESS = "remediation_in_progress"


class IntegrationEventType(str, Enum):
    """Types of cross-domain integration events."""
    PII_DETECTED = "pii_detected"
    CONSENT_CHANGED = "consent_changed"
    DATA_SUBJECT_REQUEST = "data_subject_request"
    CONSUMER_REQUEST = "consumer_request"
    BREACH_DETECTED = "breach_detected"
    POLICY_VIOLATION = "policy_violation"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"
    COMPLIANCE_GAP_FOUND = "compliance_gap_found"
    DATA_FLOW_RECORDED = "data_flow_recorded"
    AGENT_ACTION_BLOCKED = "agent_action_blocked"


class DataProcessingContext(str, Enum):
    """Context for data processing across domains."""
    AGENT_OPERATION = "agent_operation"
    USER_REQUEST = "user_request"
    AUTOMATED_PROCESSING = "automated_processing"
    ANALYTICS = "analytics"
    MARKETING = "marketing"
    LEGAL_OBLIGATION = "legal_obligation"
    VITAL_INTERESTS = "vital_interests"
    PUBLIC_INTEREST = "public_interest"


class CrossDomainRiskLevel(str, Enum):
    """Unified risk levels across domains."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINIMAL = "minimal"


class RegulationJurisdiction(str, Enum):
    """Jurisdictions for regulatory compliance."""
    EU = "eu"
    US_FEDERAL = "us_federal"
    US_CALIFORNIA = "us_california"
    US_VIRGINIA = "us_virginia"
    US_COLORADO = "us_colorado"
    UK = "uk"
    GLOBAL = "global"


# =============================================================================
# Cross-Domain Mappings
# =============================================================================

# PII Type to Regulation Mapping
PII_REGULATION_REQUIREMENTS: Dict[str, Dict[str, List[str]]] = {
    "ssn": {
        "gdpr": ["explicit_consent", "data_minimization", "encryption"],
        "ccpa": ["notice_at_collection", "do_not_sell", "right_to_delete"],
        "hipaa": ["minimum_necessary", "access_controls", "audit_logging"],
    },
    "email": {
        "gdpr": ["consent_or_legitimate_interest", "right_to_erasure"],
        "ccpa": ["notice_at_collection", "right_to_know"],
    },
    "credit_card": {
        "pci_dss": ["encryption", "access_control", "audit_trail", "tokenization"],
        "gdpr": ["security_measures", "data_minimization"],
        "ccpa": ["reasonable_security"],
    },
    "health_record": {
        "hipaa": ["authorization", "minimum_necessary", "encryption", "audit"],
        "gdpr": ["explicit_consent", "special_category_processing"],
    },
    "biometric": {
        "gdpr": ["explicit_consent", "special_category_processing", "dpia"],
        "ccpa": ["sensitive_pi_consent", "notice"],
        "bipa": ["written_consent", "retention_policy", "destruction_policy"],
    },
    "financial": {
        "glba": ["privacy_notice", "opt_out", "safeguards"],
        "gdpr": ["consent_or_legitimate_interest"],
        "ccpa": ["notice_at_collection"],
    },
}

# Agent Action to Regulation Impact
AGENT_ACTION_REGULATION_MAP: Dict[str, Set[GovernanceDomain]] = {
    "read_personal_data": {GovernanceDomain.GDPR, GovernanceDomain.CCPA, GovernanceDomain.PII},
    "write_personal_data": {GovernanceDomain.GDPR, GovernanceDomain.CCPA, GovernanceDomain.PII},
    "transfer_data_external": {GovernanceDomain.GDPR, GovernanceDomain.CCPA},
    "process_health_data": {GovernanceDomain.HIPAA, GovernanceDomain.GDPR},
    "process_payment": {GovernanceDomain.PCI_DSS},
    "automated_decision": {GovernanceDomain.GDPR, GovernanceDomain.EU_AI_ACT},
    "profiling": {GovernanceDomain.GDPR, GovernanceDomain.CCPA},
    "share_with_third_party": {GovernanceDomain.GDPR, GovernanceDomain.CCPA},
    "delete_data": {GovernanceDomain.GDPR, GovernanceDomain.CCPA},
    "export_data": {GovernanceDomain.GDPR, GovernanceDomain.CCPA},
}


# =============================================================================
# Cross-Domain Data Classes
# =============================================================================

@dataclass
class RegulatoryBinding:
    """Binding between a data element and regulatory requirements."""
    binding_id: str
    data_element_id: str
    data_element_type: str  # pii_type, field_name, etc.
    regulations: List[str]
    requirements: Dict[str, List[str]]  # regulation -> requirements
    compliance_status: Dict[str, ComplianceStatus]  # regulation -> status
    last_assessed: str
    assessor: str = ""
    notes: str = ""


@dataclass
class CrossDomainEvent:
    """Event that spans multiple governance domains."""
    event_id: str
    event_type: IntegrationEventType
    source_domain: GovernanceDomain
    affected_domains: List[GovernanceDomain]
    timestamp: str
    entity_id: str
    entity_type: str
    event_data: Dict[str, Any]
    triggered_actions: List[str] = field(default_factory=list)
    resolution_status: str = "pending"
    resolved_at: str = ""


@dataclass
class UnifiedComplianceCheck:
    """Result of checking compliance across all domains."""
    check_id: str
    entity_id: str
    entity_type: str
    action: str
    context: DataProcessingContext
    timestamp: str

    # Per-domain results
    domain_results: Dict[GovernanceDomain, Dict[str, Any]]

    # Aggregate results
    overall_status: ComplianceStatus
    blocking_issues: List[str]
    warnings: List[str]
    recommendations: List[str]
    risk_level: CrossDomainRiskLevel

    # Metadata
    checked_regulations: List[str] = field(default_factory=list)
    required_consents: List[str] = field(default_factory=list)
    data_subject_rights_applicable: List[str] = field(default_factory=list)


@dataclass
class DataFlowCompliance:
    """Compliance status for a data flow across domains."""
    flow_id: str
    source_system: str
    target_system: str
    pii_types: List[str]

    # Regulatory compliance per regulation
    gdpr_compliance: Optional[Dict[str, Any]] = None
    ccpa_compliance: Optional[Dict[str, Any]] = None
    hipaa_compliance: Optional[Dict[str, Any]] = None
    pci_compliance: Optional[Dict[str, Any]] = None

    # Overall
    is_compliant: bool = False
    gaps: List[str] = field(default_factory=list)
    required_controls: List[str] = field(default_factory=list)


@dataclass
class UnifiedDataSubject:
    """Unified view of a data subject across GDPR and CCPA."""
    subject_id: str

    # GDPR identity
    gdpr_data_subject_id: Optional[str] = None

    # CCPA identity
    ccpa_consumer_id: Optional[str] = None

    # Common attributes
    jurisdiction: RegulationJurisdiction = RegulationJurisdiction.GLOBAL

    # Rights status across regulations
    active_requests: List[Dict[str, Any]] = field(default_factory=list)
    consent_status: Dict[str, bool] = field(default_factory=dict)
    opt_out_status: Dict[str, bool] = field(default_factory=dict)

    # PII inventory
    pii_locations: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class IntegratedRiskProfile:
    """Risk profile aggregated across all governance domains."""
    profile_id: str
    entity_id: str
    entity_type: str  # data_source, agent, system, etc.
    assessed_at: str

    # Domain-specific scores
    pii_risk_score: float = 0.0
    gdpr_risk_score: float = 0.0
    ccpa_risk_score: float = 0.0
    agent_risk_score: float = 0.0

    # Aggregate
    overall_risk_score: float = 0.0
    risk_level: CrossDomainRiskLevel = CrossDomainRiskLevel.LOW

    # Issues
    critical_issues: List[str] = field(default_factory=list)
    high_issues: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class GovernancePolicy:
    """Cross-domain governance policy."""
    policy_id: str
    name: str
    description: str
    domains: List[GovernanceDomain]
    priority: int

    # Conditions
    applies_to_pii_types: List[str] = field(default_factory=list)
    applies_to_actions: List[str] = field(default_factory=list)
    applies_to_jurisdictions: List[RegulationJurisdiction] = field(default_factory=list)

    # Rules
    rules: List[Dict[str, Any]] = field(default_factory=list)

    # Metadata
    created_at: str = ""
    updated_at: str = ""
    owner: str = ""
    status: str = "active"


# =============================================================================
# Edge Types for Cross-Domain Relationships
# =============================================================================

UNIFIED_EDGE_TYPES = {
    # PII to Regulation links
    "PII_REQUIRES_REGULATION": "Links PII type to required regulation",
    "PII_GOVERNED_BY": "Links PII inventory item to governance domain",

    # Data Subject/Consumer unification
    "SAME_SUBJECT_AS": "Links GDPR data subject to CCPA consumer",
    "SUBJECT_HAS_PII": "Links unified subject to PII locations",

    # Cross-domain compliance
    "COMPLIANCE_CHECK": "Links entity to compliance check result",
    "TRIGGERS_IN_DOMAIN": "Event in one domain triggers action in another",

    # Risk aggregation
    "CONTRIBUTES_RISK_TO": "Risk in one domain affects another",
    "RISK_PROFILE_FOR": "Integrated risk profile for entity",

    # Policy application
    "CROSS_DOMAIN_POLICY": "Policy spanning multiple domains",
    "POLICY_APPLIES_TO": "Policy applies to entity type",

    # Data flow compliance
    "FLOW_COMPLIANCE": "Compliance status for data flow",
    "FLOW_REQUIRES": "Data flow requires specific controls",

    # Agent-PII interaction
    "AGENT_PROCESSES_PII": "Agent processes specific PII type",
    "AGENT_REQUIRES_CONSENT": "Agent action requires consent",
    "AGENT_BLOCKED_BY_REGULATION": "Agent action blocked by regulation",

    # Breach/Incident correlation
    "BREACH_AFFECTS_REGULATION": "Breach has regulatory implications",
    "INCIDENT_TRIGGERS_NOTIFICATION": "Incident requires regulatory notification",
}
