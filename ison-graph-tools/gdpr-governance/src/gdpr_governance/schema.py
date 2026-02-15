"""
GDPR Governance Schema
======================

Data models and enums for GDPR compliance governance.
Based on the General Data Protection Regulation (EU) 2016/679.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


# =============================================================================
# Article 6 - Lawful Basis for Processing
# =============================================================================

class LawfulBasis(str, Enum):
    """GDPR Article 6 - Lawful bases for processing personal data"""
    CONSENT = "consent"                      # Art 6(1)(a)
    CONTRACT = "contract"                    # Art 6(1)(b)
    LEGAL_OBLIGATION = "legal_obligation"    # Art 6(1)(c)
    VITAL_INTERESTS = "vital_interests"      # Art 6(1)(d)
    PUBLIC_TASK = "public_task"              # Art 6(1)(e)
    LEGITIMATE_INTERESTS = "legitimate_interests"  # Art 6(1)(f)


class SpecialCategoryBasis(str, Enum):
    """GDPR Article 9 - Basis for processing special category data"""
    EXPLICIT_CONSENT = "explicit_consent"           # Art 9(2)(a)
    EMPLOYMENT_LAW = "employment_law"               # Art 9(2)(b)
    VITAL_INTERESTS = "vital_interests"             # Art 9(2)(c)
    LEGITIMATE_ACTIVITIES = "legitimate_activities" # Art 9(2)(d)
    MANIFESTLY_PUBLIC = "manifestly_public"         # Art 9(2)(e)
    LEGAL_CLAIMS = "legal_claims"                   # Art 9(2)(f)
    PUBLIC_INTEREST = "public_interest"             # Art 9(2)(g)
    HEALTH_PURPOSES = "health_purposes"             # Art 9(2)(h)
    PUBLIC_HEALTH = "public_health"                 # Art 9(2)(i)
    ARCHIVING_RESEARCH = "archiving_research"       # Art 9(2)(j)


# =============================================================================
# Personal Data Classification
# =============================================================================

class PersonalDataCategory(str, Enum):
    """Categories of personal data under GDPR"""
    BASIC_IDENTITY = "basic_identity"           # Name, address, email
    CONTACT = "contact"                          # Phone, address
    IDENTIFICATION = "identification"            # ID numbers, passport
    FINANCIAL = "financial"                      # Bank details, income
    LOCATION = "location"                        # GPS, IP address
    ONLINE_IDENTIFIERS = "online_identifiers"   # Cookies, device IDs
    PROFESSIONAL = "professional"                # Employment, education
    BEHAVIORAL = "behavioral"                    # Preferences, habits
    BIOMETRIC = "biometric"                      # Fingerprints, facial recognition
    GENETIC = "genetic"                          # DNA data
    HEALTH = "health"                            # Medical records
    RACIAL_ETHNIC = "racial_ethnic"              # Race, ethnicity
    POLITICAL = "political"                      # Political opinions
    RELIGIOUS = "religious"                      # Religious beliefs
    TRADE_UNION = "trade_union"                  # Trade union membership
    SEXUAL_ORIENTATION = "sexual_orientation"    # Sexual orientation
    CRIMINAL = "criminal"                        # Criminal convictions


class DataSensitivity(str, Enum):
    """Data sensitivity levels"""
    STANDARD = "standard"           # Regular personal data
    SPECIAL_CATEGORY = "special"    # Art 9 special category data
    CRIMINAL = "criminal"           # Art 10 criminal data
    CHILDREN = "children"           # Art 8 children's data


# =============================================================================
# Consent Management (Article 7)
# =============================================================================

class ConsentStatus(str, Enum):
    """Status of data subject consent"""
    PENDING = "pending"
    GIVEN = "given"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"
    REFUSED = "refused"
    NOT_REQUIRED = "not_required"


class ConsentType(str, Enum):
    """Types of consent"""
    STANDARD = "standard"           # Regular consent
    EXPLICIT = "explicit"           # Art 9 explicit consent
    PARENTAL = "parental"           # Art 8 parental consent
    MARKETING = "marketing"         # Marketing communications
    PROFILING = "profiling"         # Automated decision-making
    TRANSFER = "transfer"           # Cross-border transfers


# =============================================================================
# Data Subject Rights (Articles 15-22)
# =============================================================================

class DataSubjectRight(str, Enum):
    """GDPR Data Subject Rights"""
    ACCESS = "access"                       # Art 15 - Right of access
    RECTIFICATION = "rectification"         # Art 16 - Right to rectification
    ERASURE = "erasure"                     # Art 17 - Right to erasure
    RESTRICTION = "restriction"             # Art 18 - Right to restriction
    PORTABILITY = "portability"             # Art 20 - Right to data portability
    OBJECTION = "objection"                 # Art 21 - Right to object
    AUTOMATED_DECISION = "automated_decision"  # Art 22 - Automated decision-making
    WITHDRAW_CONSENT = "withdraw_consent"   # Art 7(3) - Withdraw consent


class RightRequestStatus(str, Enum):
    """Status of data subject right request"""
    RECEIVED = "received"
    IDENTITY_VERIFICATION = "identity_verification"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REFUSED = "refused"
    EXTENDED = "extended"  # Extension under Art 12(3)


class RefusalReason(str, Enum):
    """Reasons for refusing a data subject request"""
    IDENTITY_NOT_VERIFIED = "identity_not_verified"
    MANIFESTLY_UNFOUNDED = "manifestly_unfounded"
    EXCESSIVE = "excessive"
    LEGAL_EXCEPTION = "legal_exception"
    RIGHTS_OF_OTHERS = "rights_of_others"
    PUBLIC_INTEREST = "public_interest"


# =============================================================================
# Data Breach (Articles 33-34)
# =============================================================================

class BreachSeverity(str, Enum):
    """Severity levels for data breaches"""
    LOW = "low"           # Unlikely to result in risk
    MEDIUM = "medium"     # Risk to rights and freedoms
    HIGH = "high"         # High risk to rights and freedoms
    CRITICAL = "critical" # Severe impact likely


class BreachStatus(str, Enum):
    """Status of breach handling"""
    DETECTED = "detected"
    INVESTIGATING = "investigating"
    CONTAINED = "contained"
    ASSESSED = "assessed"
    NOTIFIED_DPA = "notified_dpa"       # Art 33 - Notify supervisory authority
    NOTIFIED_SUBJECTS = "notified_subjects"  # Art 34 - Notify data subjects
    REMEDIATED = "remediated"
    CLOSED = "closed"


class BreachType(str, Enum):
    """Types of data breaches"""
    CONFIDENTIALITY = "confidentiality"  # Unauthorized disclosure
    INTEGRITY = "integrity"               # Unauthorized alteration
    AVAILABILITY = "availability"         # Loss of access


# =============================================================================
# DPIA (Article 35)
# =============================================================================

class DPIAStatus(str, Enum):
    """Status of Data Protection Impact Assessment"""
    NOT_REQUIRED = "not_required"
    REQUIRED = "required"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    REVIEWED = "reviewed"
    CONSULTATION_REQUIRED = "consultation_required"  # Art 36


class DPIATrigger(str, Enum):
    """Triggers requiring DPIA under Article 35"""
    SYSTEMATIC_MONITORING = "systematic_monitoring"
    LARGE_SCALE_SPECIAL = "large_scale_special"
    AUTOMATED_DECISIONS = "automated_decisions"
    PROFILING = "profiling"
    BIOMETRIC = "biometric"
    GENETIC = "genetic"
    VULNERABLE_SUBJECTS = "vulnerable_subjects"
    INNOVATIVE_TECHNOLOGY = "innovative_technology"
    CROSS_BORDER = "cross_border"
    DENIAL_OF_SERVICE = "denial_of_service"


# =============================================================================
# International Transfers (Articles 44-49)
# =============================================================================

class TransferMechanism(str, Enum):
    """Mechanisms for international data transfers"""
    ADEQUACY_DECISION = "adequacy_decision"      # Art 45
    STANDARD_CLAUSES = "standard_clauses"        # Art 46(2)(c) - SCCs
    BINDING_RULES = "binding_corporate_rules"    # Art 47 - BCRs
    APPROVED_CODE = "approved_code"              # Art 46(2)(e)
    APPROVED_CERTIFICATION = "approved_certification"  # Art 46(2)(f)
    DEROGATION_CONSENT = "derogation_consent"    # Art 49(1)(a)
    DEROGATION_CONTRACT = "derogation_contract"  # Art 49(1)(b)
    DEROGATION_PUBLIC = "derogation_public"      # Art 49(1)(d)
    DEROGATION_LEGAL = "derogation_legal"        # Art 49(1)(e)
    DEROGATION_VITAL = "derogation_vital"        # Art 49(1)(f)


class TransferStatus(str, Enum):
    """Status of international transfer"""
    PENDING_ASSESSMENT = "pending_assessment"
    APPROVED = "approved"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"


# =============================================================================
# Roles and Actors
# =============================================================================

class ActorRole(str, Enum):
    """GDPR actor roles"""
    CONTROLLER = "controller"           # Art 4(7)
    JOINT_CONTROLLER = "joint_controller"  # Art 26
    PROCESSOR = "processor"             # Art 4(8)
    SUB_PROCESSOR = "sub_processor"
    DPO = "dpo"                         # Art 37 - Data Protection Officer
    REPRESENTATIVE = "representative"   # Art 27
    SUPERVISORY_AUTHORITY = "supervisory_authority"


# =============================================================================
# Processing Activity (Article 30)
# =============================================================================

class ProcessingPurpose(str, Enum):
    """Common processing purposes"""
    SERVICE_DELIVERY = "service_delivery"
    CONTRACT_PERFORMANCE = "contract_performance"
    CUSTOMER_SUPPORT = "customer_support"
    MARKETING = "marketing"
    ANALYTICS = "analytics"
    SECURITY = "security"
    LEGAL_COMPLIANCE = "legal_compliance"
    HR_MANAGEMENT = "hr_management"
    RESEARCH = "research"
    PROFILING = "profiling"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ProcessingActivity:
    """Records of Processing Activities (Article 30)"""
    id: str
    name: str
    purpose: str
    lawful_basis: LawfulBasis
    data_categories: List[PersonalDataCategory]
    data_subjects: List[str]
    recipients: List[str]
    retention_period: str
    security_measures: List[str]
    controller_id: str
    processor_id: Optional[str] = None
    transfer_countries: List[str] = field(default_factory=list)
    transfer_mechanism: Optional[TransferMechanism] = None
    dpia_required: bool = False
    dpia_id: Optional[str] = None
    created_at: str = ""
    updated_at: str = ""


@dataclass
class DataSubject:
    """Data subject record"""
    id: str
    external_id: Optional[str] = None  # Customer ID, etc.
    email: Optional[str] = None
    data_categories: List[PersonalDataCategory] = field(default_factory=list)
    consents: List[str] = field(default_factory=list)
    pending_requests: List[str] = field(default_factory=list)
    created_at: str = ""
    last_activity: str = ""


@dataclass
class ConsentRecord:
    """Consent record"""
    id: str
    data_subject_id: str
    purpose: str
    consent_type: ConsentType
    status: ConsentStatus
    lawful_basis: LawfulBasis
    given_at: Optional[str] = None
    withdrawn_at: Optional[str] = None
    expires_at: Optional[str] = None
    evidence: str = ""  # How consent was obtained
    version: str = ""   # Privacy policy version


@dataclass
class RightRequest:
    """Data subject right request"""
    id: str
    data_subject_id: str
    right_type: DataSubjectRight
    status: RightRequestStatus
    received_at: str
    deadline: str  # 1 month from receipt
    completed_at: Optional[str] = None
    response: Optional[str] = None
    refused_reason: Optional[RefusalReason] = None
    extended: bool = False
    extension_reason: Optional[str] = None


@dataclass
class DataBreach:
    """Data breach record (Articles 33-34)"""
    id: str
    detected_at: str
    breach_type: BreachType
    severity: BreachSeverity
    status: BreachStatus
    description: str
    data_categories_affected: List[PersonalDataCategory]
    subjects_affected_count: int
    cause: str
    containment_measures: List[str] = field(default_factory=list)
    dpa_notification_required: bool = False
    dpa_notified_at: Optional[str] = None
    subject_notification_required: bool = False
    subjects_notified_at: Optional[str] = None
    remediation_actions: List[str] = field(default_factory=list)
    lessons_learned: str = ""


@dataclass
class DPIA:
    """Data Protection Impact Assessment (Article 35)"""
    id: str
    processing_activity_id: str
    status: DPIAStatus
    triggers: List[DPIATrigger]
    necessity_assessment: str
    proportionality_assessment: str
    risks_identified: List[Dict[str, Any]] = field(default_factory=list)
    mitigations: List[Dict[str, Any]] = field(default_factory=list)
    residual_risk_level: str = ""
    dpo_opinion: str = ""
    consultation_required: bool = False
    consultation_response: str = ""
    created_at: str = ""
    completed_at: Optional[str] = None
    next_review: Optional[str] = None


@dataclass
class InternationalTransfer:
    """International data transfer record"""
    id: str
    source_country: str
    destination_country: str
    recipient_name: str
    recipient_type: ActorRole
    mechanism: TransferMechanism
    status: TransferStatus
    data_categories: List[PersonalDataCategory]
    processing_activity_id: str
    safeguards: List[str] = field(default_factory=list)
    tia_completed: bool = False  # Transfer Impact Assessment
    created_at: str = ""


@dataclass
class ComplianceStatus:
    """Overall GDPR compliance status"""
    organization_id: str
    processing_activities_documented: int
    lawful_bases_documented: int
    consent_records: int
    pending_right_requests: int
    open_breaches: int
    dpias_required: int
    dpias_completed: int
    transfers_documented: int
    last_audit: Optional[str] = None
    compliance_score: float = 0.0
    issues: List[Dict[str, Any]] = field(default_factory=list)
