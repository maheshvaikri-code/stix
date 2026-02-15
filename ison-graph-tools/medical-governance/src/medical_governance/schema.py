"""
HIPAA Medical Governance Schema
===============================

Comprehensive type definitions for HIPAA-compliant medical governance.
Covers all 14 governance domains required for healthcare AI systems.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# HIPAA Regulation References
# =============================================================================

class HIPAARegulation(Enum):
    """HIPAA regulation sections"""
    PRIVACY_RULE = "45_CFR_164.500-534"
    SECURITY_RULE = "45_CFR_164.302-318"
    BREACH_NOTIFICATION = "45_CFR_164.400-414"
    ENFORCEMENT_RULE = "45_CFR_160"
    MINIMUM_NECESSARY = "45_CFR_164.502(b)"
    PATIENT_RIGHTS = "45_CFR_164.520-528"
    BUSINESS_ASSOCIATES = "45_CFR_164.502-504"
    ACCESS_CONTROL = "45_CFR_164.312(a)"
    AUDIT_CONTROLS = "45_CFR_164.312(b)"
    AUTHORIZATION = "45_CFR_164.508"
    ACCOUNTING_DISCLOSURES = "45_CFR_164.528"
    TRAINING = "45_CFR_164.308(a)(5)"
    SANCTIONS = "45_CFR_164.530(e)"


# =============================================================================
# PHI Classification Enums
# =============================================================================

class PHICategory(Enum):
    """Protected Health Information categories"""
    DEMOGRAPHICS = "demographics"                # Name, address, DOB
    IDENTIFIERS = "identifiers"                  # SSN, MRN, etc.
    CLINICAL = "clinical"                        # Diagnosis, meds, procedures
    BILLING = "billing"                          # Charges, insurance info
    DIRECT_IDENTIFIER = "direct_identifier"      # Name, SSN, MRN - must remove
    QUASI_IDENTIFIER = "quasi_identifier"        # DOB, ZIP - must generalize
    CLINICAL_DATA = "clinical_data"              # Diagnosis, meds - standard PHI
    GENOMIC_DATA = "genomic_data"                # DNA, variants - very high
    PSYCHOTHERAPY_NOTES = "psychotherapy_notes"  # Special protection
    SUBSTANCE_ABUSE = "substance_abuse"          # 42 CFR Part 2
    HIV_STATUS = "hiv_status"                    # State law protected
    DERIVED_DATA = "derived_data"                # Risk scores, predictions
    DE_IDENTIFIED = "de_identified"              # Safe harbor compliant


class SensitivityLevel(Enum):
    """Data sensitivity levels"""
    PUBLIC = "public"              # De-identified aggregate
    INTERNAL = "internal"          # Operational non-PHI
    STANDARD = "standard"          # Standard PHI
    PHI = "phi"                    # Standard PHI (alias)
    HIGH = "high"                  # Sensitive PHI
    PHI_HIGH = "phi_high"          # Sensitive PHI (alias)
    CRITICAL = "critical"          # Most sensitive PHI
    PHI_RESTRICTED = "phi_restricted"  # Special categories


class SafeHarborAction(Enum):
    """Actions for Safe Harbor de-identification"""
    REMOVE = "remove"                    # Delete completely
    REMOVE_OR_REKEY = "remove_or_rekey"  # Delete or pseudonymize
    GENERALIZE_YEAR = "generalize_year"  # Keep only year
    TRUNCATE_3 = "truncate_3"            # First 3 digits (ZIP)
    AGGREGATE_90 = "aggregate_90"        # Ages 90+
    SHIFT = "shift"                      # Date shifting
    RETAIN = "retain"                    # Keep as-is
    SPECIAL_CONSENT = "special_consent"  # Requires explicit consent
    SEGREGATE = "segregate"              # Store separately


# =============================================================================
# Access Control Enums
# =============================================================================

class WorkforceRole(Enum):
    """HIPAA workforce roles"""
    PHYSICIAN = "physician"                    # General physician role
    TREATING_PHYSICIAN = "treating_physician"
    CONSULTING_PHYSICIAN = "consulting_physician"
    NURSE = "nurse"
    MEDICAL_ASSISTANT = "medical_assistant"
    REGISTRATION = "registration"
    BILLING_STAFF = "billing_staff"
    IT_ADMINISTRATOR = "it_administrator"
    PRIVACY_OFFICER = "privacy_officer"
    RESEARCHER = "researcher"
    AI_AGENT = "ai_agent"
    EXTERNAL_PROVIDER = "external_provider"
    PATIENT = "patient"
    PATIENT_PROXY = "patient_proxy"
    BUSINESS_ASSOCIATE = "business_associate"


class AccessPurpose(Enum):
    """HIPAA-defined access purposes"""
    TREATMENT = "treatment"                    # 164.506(c)(2)
    PAYMENT = "payment"                        # 164.506(c)(3)
    HEALTHCARE_OPERATIONS = "healthcare_operations"  # 164.506(c)(4)
    RESEARCH = "research"                      # 164.512(i)
    PUBLIC_HEALTH = "public_health"            # 164.512(b)
    LAW_ENFORCEMENT = "law_enforcement"        # 164.512(f)
    JUDICIAL = "judicial"                      # 164.512(e)
    DECEASED = "deceased"                      # 164.512(g)
    ORGAN_DONATION = "organ_donation"          # 164.512(h)
    WORKERS_COMP = "workers_comp"              # 164.512(l)
    PATIENT_REQUEST = "patient_request"        # 164.524
    AI_CLINICAL_SUPPORT = "ai_clinical_support"  # OCR guidance


class AccessContext(Enum):
    """Access context for risk assessment"""
    NORMAL_HOURS = "normal_hours"
    AFTER_HOURS = "after_hours"
    REMOTE_VPN = "remote_vpn"
    REMOTE_PUBLIC = "remote_public"
    EMERGENCY = "emergency"
    BREAK_GLASS = "break_glass"


# =============================================================================
# Consent Enums
# =============================================================================

class ConsentType(Enum):
    """Types of patient consent"""
    GENERAL = "general"                    # General consent
    TREATMENT = "treatment"                # General treatment
    RESEARCH = "research"                  # Research participation
    MARKETING = "marketing"                # Marketing use
    PSYCHOTHERAPY = "psychotherapy"        # Psychotherapy notes
    HIE_PARTICIPATION = "hie_participation"  # Health information exchange
    SUBSTANCE_ABUSE = "substance_abuse"    # 42 CFR Part 2
    HIV_DISCLOSURE = "hiv_disclosure"      # HIV status
    GENETIC = "genetic"                    # Genetic information
    AI_CLINICAL = "ai_clinical"            # AI clinical decision support
    PROXY = "proxy"                        # Proxy authorization
    MINOR = "minor"                        # Minor consent
    DECEASED = "deceased"                  # Deceased records


class ConsentStatus(Enum):
    """Consent record status"""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    PENDING = "pending"
    LIMITED = "limited"      # Partial/conditional
    DENIED = "denied"        # Explicitly refused


# =============================================================================
# Breach & Incident Enums
# =============================================================================

class BreachStatus(Enum):
    """Breach investigation status"""
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    ASSESSED = "assessed"
    CONFIRMED = "confirmed"
    NOT_BREACH = "not_breach"
    NOTIFIED = "notified"
    CLOSED = "closed"


class BreachSeverity(Enum):
    """Breach severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationRecipient(Enum):
    """Breach notification recipients"""
    INDIVIDUALS = "individuals"
    HHS_OCR = "hhs_ocr"
    MEDIA = "media"
    STATE_AG = "state_ag"


# =============================================================================
# Business Associate Enums
# =============================================================================

class BAType(Enum):
    """Business associate types"""
    CLOUD_PROVIDER = "cloud_provider"
    CLOUD_HOSTING = "cloud_hosting"
    LABORATORY = "laboratory"
    AI_VENDOR = "ai_vendor"
    BILLING_SERVICE = "billing_service"
    HEALTH_EXCHANGE = "health_exchange"
    RESEARCH_ORG = "research_org"
    DESTRUCTION = "destruction"
    IT_SERVICES = "it_services"
    TRANSCRIPTION = "transcription"


class BAAStatus(Enum):
    """BAA agreement status"""
    ACTIVE = "active"
    EXPIRED = "expired"
    PENDING = "pending"
    TERMINATED = "terminated"
    RENEWAL_DUE = "renewal_due"


class RiskTier(Enum):
    """Business associate risk tier"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# Security Safeguards Enums
# =============================================================================

class SafeguardCategory(Enum):
    """HIPAA security safeguard categories"""
    ADMINISTRATIVE = "administrative"
    PHYSICAL = "physical"
    TECHNICAL = "technical"


class ControlStatus(Enum):
    """Security control status"""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"
    PLANNED = "planned"


# =============================================================================
# Patient Rights Enums
# =============================================================================

class PatientRight(Enum):
    """HIPAA patient rights"""
    ACCESS = "access"                      # 164.524
    AMENDMENT = "amendment"                # 164.526
    ACCOUNTING = "accounting"              # 164.528
    RESTRICTION = "restriction"            # 164.522(a)
    CONFIDENTIAL_COMM = "confidential_comm"  # 164.522(b)
    NOTICE_PRIVACY = "notice_privacy"      # 164.520
    COMPLAINT = "complaint"                # 164.530(d)


class RightRequestStatus(Enum):
    """Patient right request status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    GRANTED = "granted"
    DENIED = "denied"
    PARTIAL = "partial"
    COMPLETE = "complete"


# =============================================================================
# AI Governance Enums
# =============================================================================

class AISystemType(Enum):
    """Types of AI systems accessing PHI"""
    DIAGNOSTIC = "diagnostic"              # Clinical diagnosis support
    TRANSCRIPTION = "transcription"
    DECISION_SUPPORT = "decision_support"
    ANALYTICS = "analytics"
    CARE_GAP = "care_gap"
    RESEARCH = "research"
    CODING = "coding"
    RISK_STRATIFICATION = "risk_stratification"
    POPULATION_HEALTH = "population_health"


class AIGovernanceRequirement(Enum):
    """AI-specific governance requirements"""
    RISK_ASSESSMENT = "risk_assessment"
    DATA_GOVERNANCE = "data_governance"
    PHI_MINIMIZATION = "phi_minimization"
    OUTPUT_MONITORING = "output_monitoring"
    MINIMUM_NECESSARY = "minimum_necessary"
    NO_TRAINING_PHI = "no_training_phi"
    AUDIT_LOGGING = "audit_logging"
    NO_IDENTIFIERS = "no_identifiers"
    DE_IDENTIFICATION = "de_identification"
    IRB_APPROVAL = "irb_approval"
    HUMAN_OVERSIGHT = "human_oversight"
    OUTPUT_FILTERING = "output_filtering"


class AIDeploymentStatus(Enum):
    """AI system deployment status"""
    DEVELOPMENT = "development"
    PILOT = "pilot"
    PRODUCTION = "production"
    DEPRECATED = "deprecated"


# =============================================================================
# Workforce Enums
# =============================================================================

class TrainingType(Enum):
    """HIPAA training types"""
    HIPAA_BASICS = "hipaa_basics"
    PRIVACY_BASICS = "privacy_basics"
    PRIVACY_PRACTICES = "privacy_practices"
    SECURITY_AWARENESS = "security_awareness"
    PHI_HANDLING = "phi_handling"
    BREACH_REPORTING = "breach_reporting"
    BREACH_RESPONSE = "breach_response"
    AI_SYSTEM_USE = "ai_system_use"
    MINIMUM_NECESSARY = "minimum_necessary"
    PATIENT_RIGHTS = "patient_rights"
    ROLE_SPECIFIC = "role_specific"


class ViolationSeverity(Enum):
    """Policy violation severity"""
    LOW = "low"
    MINOR = "minor"
    MODERATE = "moderate"
    MEDIUM = "medium"
    SERIOUS = "serious"
    HIGH = "high"
    WILLFUL = "willful"
    CRITICAL = "critical"


class SanctionType(Enum):
    """Sanction types"""
    VERBAL_WARNING = "verbal_warning"
    WRITTEN_WARNING = "written_warning"
    RETRAINING = "retraining"
    ACCESS_REVOCATION = "access_revocation"
    SUSPENSION = "suspension"
    TERMINATION = "termination"


# =============================================================================
# Data Classes - PHI Classification
# =============================================================================

@dataclass
class PHICategoryDef:
    """PHI category definition"""
    id: str
    name: str
    hipaa_designation: str
    sensitivity: SensitivityLevel
    examples: List[str] = field(default_factory=list)
    safe_harbor_action: SafeHarborAction = SafeHarborAction.RETAIN


@dataclass
class DataElement:
    """Individual data element classification"""
    id: str
    field_name: str
    phi_category: PHICategory
    hipaa_identifier: bool  # One of 18 identifiers
    safe_harbor_action: SafeHarborAction
    sensitivity_level: SensitivityLevel
    description: str = ""


# =============================================================================
# Data Classes - Access Control
# =============================================================================

@dataclass
class UserRole:
    """User role definition"""
    id: str
    name: str
    workforce_type: WorkforceRole
    is_covered_entity: bool
    default_phi_access: AccessPurpose
    description: str = ""


@dataclass
class AccessPolicy:
    """Access policy definition"""
    id: str
    role_id: str
    purpose: AccessPurpose
    data_scope: str
    time_limit: str
    conditions: str
    minimum_necessary_profile: Optional[str] = None


@dataclass
class AccessDecision:
    """Recorded access decision"""
    id: str
    user_id: str
    patient_id: str
    decision: str  # granted, denied
    policy_applied: str
    context: AccessContext
    timestamp: str
    phi_accessed: List[str] = field(default_factory=list)
    reason: str = ""


# =============================================================================
# Data Classes - Minimum Necessary
# =============================================================================

@dataclass
class UseCase:
    """Use case definition for minimum necessary"""
    id: str
    name: str
    purpose: AccessPurpose
    requester_type: str
    frequency: str  # high, medium, low
    description: str = ""


@dataclass
class MinimumNecessaryProfile:
    """Minimum necessary profile for a use case"""
    id: str
    use_case_id: str
    phi_required: List[str]
    phi_excluded: List[str]
    justification: str


@dataclass
class FieldJustification:
    """Justification for a field in minimum necessary profile"""
    id: str
    profile_id: str
    field_name: str
    justification: str
    alternative_if_denied: str


# =============================================================================
# Data Classes - Consent
# =============================================================================

@dataclass
class ConsentRecord:
    """Patient consent record"""
    id: str
    patient_id: str
    consent_type: ConsentType
    status: ConsentStatus
    granted_date: str
    expires: Optional[str]
    scope: str
    witness: Optional[str] = None
    revoked_date: Optional[str] = None
    revoked_by: Optional[str] = None


@dataclass
class ConsentScope:
    """Scope details for a consent"""
    id: str
    consent_id: str
    scope_type: str  # data_elements, time_period, recipients
    included: List[str]
    excluded: List[str] = field(default_factory=list)


# =============================================================================
# Data Classes - Audit & Disclosure
# =============================================================================

@dataclass
class AuditEvent:
    """PHI access audit event"""
    id: str
    event_type: str  # access, disclosure, amendment
    timestamp: str
    actor_id: str
    actor_type: str
    patient_id: str
    action: str  # view, query, transmit, modify
    phi_accessed: List[str]
    purpose: AccessPurpose
    location: str = ""
    session_id: str = ""


@dataclass
class DisclosureRecord:
    """PHI disclosure record for accounting"""
    id: str
    patient_id: str
    disclosure_date: str
    recipient: str
    recipient_type: str
    purpose: AccessPurpose
    phi_disclosed: List[str]
    requires_accounting: bool
    exception_type: Optional[str] = None


@dataclass
class AccountingRequest:
    """Patient request for accounting of disclosures"""
    id: str
    patient_id: str
    request_date: str
    period_requested: str
    status: RightRequestStatus
    fulfilled_date: Optional[str] = None


# =============================================================================
# Data Classes - Business Associates
# =============================================================================

@dataclass
class BusinessAssociate:
    """Business associate record"""
    id: str
    name: str
    ba_type: BAType
    service: str
    risk_tier: RiskTier
    contact_email: str = ""
    contact_phone: str = ""


@dataclass
class BAAgreement:
    """Business associate agreement"""
    id: str
    ba_id: str
    effective_date: str
    expiration_date: Optional[str]
    status: BAAStatus
    version: str
    phi_scope: List[str] = field(default_factory=list)


@dataclass
class BADataFlow:
    """Data flow to/from business associate"""
    id: str
    ba_id: str
    direction: str  # inbound, outbound, bidirectional
    phi_categories: List[str]
    volume: str
    frequency: str
    encryption_required: bool = True


# =============================================================================
# Data Classes - Breach
# =============================================================================

@dataclass
class PotentialBreach:
    """Potential breach incident"""
    id: str
    discovered_date: str
    discovered_by: str
    description: str
    status: BreachStatus
    affected_count: int = 0
    phi_types: List[str] = field(default_factory=list)


@dataclass
class BreachAssessment:
    """Breach risk assessment"""
    id: str
    breach_id: str
    assessment_date: str
    assessor: str
    is_breach: bool
    risk_level: BreachSeverity
    factors: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BreachNotification:
    """Breach notification record"""
    id: str
    breach_id: str
    recipient: NotificationRecipient
    deadline: str
    notification_date: Optional[str]
    status: str
    method: str = ""


# =============================================================================
# Data Classes - Patient Rights
# =============================================================================

@dataclass
class PatientRightRequest:
    """Patient right exercise request"""
    id: str
    patient_id: str
    right_type: PatientRight
    request_date: str
    status: RightRequestStatus
    deadline: str
    scope: str = ""
    format_requested: str = ""


@dataclass
class RightResponse:
    """Response to patient right request"""
    id: str
    request_id: str
    response_date: str
    action: str  # granted, denied, partial
    reason: str = ""
    documentation: str = ""


# =============================================================================
# Data Classes - AI Governance
# =============================================================================

@dataclass
class AISystem:
    """AI system registration"""
    id: str
    name: str
    system_type: AISystemType
    phi_access: List[str]
    deployment: AIDeploymentStatus
    vendor: Optional[str] = None
    model_version: str = ""
    description: str = ""


@dataclass
class AIGovernanceRule:
    """AI-specific governance rule"""
    id: str
    ai_system_id: str
    requirement: AIGovernanceRequirement
    implementation: str
    hipaa_basis: str
    status: ControlStatus


@dataclass
class AIDataFlowControl:
    """Data flow control for AI system"""
    id: str
    ai_system_id: str
    direction: str  # input, output
    phi_allowed: List[str]
    phi_blocked: List[str]
    enforcement: str  # api_filter, query_filter, output_filter


@dataclass
class AIAccessAudit:
    """AI system PHI access audit"""
    id: str
    ai_system_id: str
    patient_id: str
    timestamp: str
    phi_accessed: List[str]
    phi_filtered: List[str]
    purpose: str
    result_summary: str


# =============================================================================
# Data Classes - Security Safeguards
# =============================================================================

@dataclass
class SecuritySafeguard:
    """Security safeguard requirement"""
    id: str
    category: SafeguardCategory
    name: str
    regulation: str
    required: bool
    description: str = ""


@dataclass
class SecurityControl:
    """Security control implementation"""
    id: str
    safeguard_id: str
    control_name: str
    implementation: str
    status: ControlStatus
    last_tested: Optional[str] = None
    evidence: str = ""


@dataclass
class RiskFinding:
    """Security risk finding"""
    id: str
    assessment_id: str
    finding: str
    severity: str
    cvss_score: float
    remediation_status: str
    remediation_due: Optional[str] = None


# =============================================================================
# Data Classes - Workforce
# =============================================================================

@dataclass
class TrainingRequirement:
    """Training requirement definition"""
    id: str
    name: str
    training_type: TrainingType
    audience: str
    frequency: str  # annual, initial, etc.
    regulation: str


@dataclass
class TrainingCompletion:
    """Training completion record"""
    id: str
    employee_id: str
    training_id: str
    completion_date: str
    expires: str
    score: float


@dataclass
class PolicyViolation:
    """Policy violation record"""
    id: str
    employee_id: str
    violation_type: str
    severity: ViolationSeverity
    date: str
    status: str
    description: str = ""


@dataclass
class Sanction:
    """Sanction applied for violation"""
    id: str
    violation_id: str
    sanction_type: SanctionType
    effective_date: str
    documentation: str


# =============================================================================
# Edge Types
# =============================================================================

HIPAA_EDGE_TYPES = {
    # PHI Classification
    "ELEMENT_CLASSIFICATION": "Links data element to sensitivity level",
    "SAFE_HARBOR_REQUIRES": "Safe harbor action required for element",

    # Access Control
    "HAS_ROLE": "User has role",
    "ROLE_PERMITS": "Role permits access to scope",
    "ACCESS_GRANTED": "Access was granted",
    "ACCESS_DENIED": "Access was denied",
    "BREAK_GLASS": "Emergency access override",

    # Minimum Necessary
    "USE_CASE_PROFILE": "Use case has minimum necessary profile",
    "PROFILE_ALLOWS": "Profile allows field access",
    "PROFILE_BLOCKS": "Profile blocks field access",
    "FIELD_JUSTIFIED": "Field access justified",

    # Consent
    "HAS_CONSENT": "Patient has consent record",
    "CONSENT_ENABLES": "Consent enables access",
    "CONSENT_BLOCKS": "Consent blocks access",
    "CONSENT_REVOKED": "Consent was revoked",

    # Audit
    "AUDIT_EVENT": "Audit event for patient",
    "DISCLOSURE_TO": "PHI disclosed to recipient",
    "REQUIRES_ACCOUNTING": "Disclosure requires accounting",
    "ACCOUNTING_EXCEPTION": "TPO exception for accounting",

    # Business Associate
    "HAS_BAA": "Business associate has agreement",
    "BAA_CONTROLS": "BAA controls data flow",
    "BA_SUBCONTRACTOR": "BA has subcontractor",
    "BA_INCIDENT": "BA had incident",

    # Breach
    "BREACH_ASSESSMENT": "Breach has assessment",
    "BREACH_NOTIFICATION": "Breach requires notification",
    "BREACH_AFFECTED": "Breach affected individual",
    "BREACH_MITIGATED": "Breach was mitigated",

    # Patient Rights
    "RIGHT_REQUEST": "Patient requested right",
    "RIGHT_RESPONSE": "Response to right request",
    "RESTRICTION_ACTIVE": "Active restriction on PHI",

    # AI Governance
    "AI_GOVERNED_BY": "AI system governed by rule",
    "AI_ACCESS_AUDIT": "AI access was audited",
    "AI_FILTERED": "AI query was filtered",
    "AI_HUMAN_REVIEW": "AI decision requires human review",

    # Security
    "SAFEGUARD_CONTROL": "Safeguard has control",
    "CONTROL_TESTED": "Control was tested",
    "RISK_FINDING": "Risk finding from assessment",
    "RISK_REMEDIATED": "Risk was remediated",

    # Workforce
    "TRAINING_REQUIRED": "Training required for role",
    "TRAINING_COMPLETED": "Training was completed",
    "VIOLATION_RECORDED": "Violation was recorded",
    "SANCTION_APPLIED": "Sanction was applied",
}
