"""
CCPA/CPRA Governance Schema
===========================

Data models and enums for California Consumer Privacy Act compliance.
Includes CPRA (California Privacy Rights Act) amendments effective Jan 2023.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


# =============================================================================
# Business Roles and Relationships
# =============================================================================

class BusinessRole(str, Enum):
    """CCPA business classifications"""
    BUSINESS = "business"                    # Collects/controls PI
    SERVICE_PROVIDER = "service_provider"    # Processes on behalf of business
    CONTRACTOR = "contractor"                # CPRA addition
    THIRD_PARTY = "third_party"              # Receives PI via sale/share


class BusinessSize(str, Enum):
    """Business size thresholds for CCPA applicability"""
    LARGE = "large"           # >$25M revenue
    MEDIUM = "medium"         # 50K-100K consumers
    DATA_SELLER = "data_seller"  # Derives >50% revenue from selling PI
    SMALL = "small"           # Below thresholds (exempt)


# =============================================================================
# Personal Information Categories (CCPA Section 1798.140)
# =============================================================================

class PersonalInfoCategory(str, Enum):
    """Categories of Personal Information under CCPA"""
    # Standard categories
    IDENTIFIERS = "identifiers"                    # Name, alias, SSN, ID numbers
    CUSTOMER_RECORDS = "customer_records"          # Name, address, phone, financial
    PROTECTED_CLASS = "protected_class"            # Age, race, religion, disability
    COMMERCIAL_INFO = "commercial_info"            # Purchase history, tendencies
    BIOMETRIC = "biometric"                        # Fingerprints, face, voice
    INTERNET_ACTIVITY = "internet_activity"        # Browsing, search, interaction
    GEOLOCATION = "geolocation"                    # Physical location data
    SENSORY_DATA = "sensory_data"                  # Audio, visual, thermal, olfactory
    PROFESSIONAL_INFO = "professional_info"        # Employment, education
    EDUCATION_INFO = "education_info"              # Non-public education records
    INFERENCES = "inferences"                      # Profiles, preferences, behaviors

    # CPRA Sensitive Personal Information (SPI) categories
    SSN_ID_NUMBERS = "ssn_id_numbers"              # SSN, driver's license, passport
    FINANCIAL_ACCOUNT = "financial_account"        # Account + credentials
    PRECISE_GEOLOCATION = "precise_geolocation"   # Within 1,850 feet
    RACIAL_ETHNIC = "racial_ethnic"               # Race, ethnicity
    RELIGIOUS_BELIEFS = "religious_beliefs"        # Religious/philosophical beliefs
    UNION_MEMBERSHIP = "union_membership"          # Union membership
    MAIL_EMAIL_TEXT = "mail_email_text"           # Contents of communications
    GENETIC_DATA = "genetic_data"                  # Genetic information
    BIOMETRIC_ID = "biometric_id"                  # Biometric for identification
    HEALTH_INFO = "health_info"                    # Health data
    SEX_LIFE = "sex_life"                          # Sex life or sexual orientation


class SensitivePersonalInfo(str, Enum):
    """CPRA Sensitive Personal Information (SPI) requiring additional protections"""
    SSN_ID = "ssn_id"
    FINANCIAL_CREDENTIALS = "financial_credentials"
    PRECISE_GEOLOCATION = "precise_geolocation"
    RACE_ETHNICITY = "race_ethnicity"
    RELIGION = "religion"
    UNION = "union"
    COMMUNICATIONS = "communications"
    GENETIC = "genetic"
    BIOMETRIC = "biometric"
    HEALTH = "health"
    SEX_ORIENTATION = "sex_orientation"


# =============================================================================
# Consumer Rights (CCPA Sections 1798.100-1798.125)
# =============================================================================

class ConsumerRight(str, Enum):
    """CCPA/CPRA Consumer Rights"""
    # Original CCPA rights
    RIGHT_TO_KNOW = "right_to_know"               # 1798.100, 1798.110
    RIGHT_TO_DELETE = "right_to_delete"           # 1798.105
    RIGHT_TO_OPT_OUT_SALE = "opt_out_sale"       # 1798.120
    RIGHT_TO_NON_DISCRIMINATION = "non_discrimination"  # 1798.125

    # CPRA additions
    RIGHT_TO_CORRECT = "right_to_correct"         # 1798.106
    RIGHT_TO_OPT_OUT_SHARE = "opt_out_share"     # 1798.120 (sharing for cross-context ads)
    RIGHT_TO_LIMIT_SPI = "limit_spi"             # 1798.121 (limit sensitive PI use)
    RIGHT_TO_ACCESS = "right_to_access"          # Beyond 12 months
    RIGHT_TO_PORTABILITY = "right_to_portability"  # Machine-readable format


class RequestStatus(str, Enum):
    """Status of consumer rights request"""
    RECEIVED = "received"
    VERIFICATION_PENDING = "verification_pending"
    VERIFICATION_FAILED = "verification_failed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    DENIED = "denied"
    EXTENDED = "extended"


class DenialReason(str, Enum):
    """Reasons for denying a consumer request"""
    IDENTITY_NOT_VERIFIED = "identity_not_verified"
    NO_PERSONAL_INFO = "no_personal_info"
    LEGAL_EXCEPTION = "legal_exception"
    SERVICE_PROVIDER_EXCEPTION = "service_provider_exception"
    SECURITY_EXCEPTION = "security_exception"
    FREE_SPEECH = "free_speech"
    LEGAL_CLAIMS = "legal_claims"
    RESEARCH_EXCEPTION = "research_exception"
    INTERNAL_USE = "internal_use"
    INCOMPATIBLE_USE = "incompatible_use"


# =============================================================================
# Sale and Sharing of Personal Information
# =============================================================================

class SaleShareType(str, Enum):
    """Types of PI transfer under CCPA"""
    SALE = "sale"                           # Monetary or valuable consideration
    SHARE = "share"                         # CPRA: Cross-context behavioral advertising
    SERVICE_PROVIDER = "service_provider"   # Not a sale (business purpose)
    CONTRACTOR = "contractor"               # CPRA: Not a sale with contract


class OptOutStatus(str, Enum):
    """Consumer opt-out status"""
    NOT_OPTED_OUT = "not_opted_out"
    OPTED_OUT_SALE = "opted_out_sale"
    OPTED_OUT_SHARE = "opted_out_share"
    OPTED_OUT_BOTH = "opted_out_both"
    OPTED_OUT_SPI = "opted_out_spi"          # CPRA: Limit SPI use
    GPC_DETECTED = "gpc_detected"            # Global Privacy Control signal


class OptOutMethod(str, Enum):
    """How opt-out was submitted"""
    WEBSITE_LINK = "website_link"            # "Do Not Sell" link
    PRIVACY_PORTAL = "privacy_portal"
    EMAIL = "email"
    TOLL_FREE = "toll_free"
    AUTHORIZED_AGENT = "authorized_agent"
    GPC_SIGNAL = "gpc_signal"                # Global Privacy Control
    OPT_OUT_PREFERENCE_SIGNAL = "oops"       # CPRA opt-out preference signals


# =============================================================================
# Business Purposes and Exemptions
# =============================================================================

class BusinessPurpose(str, Enum):
    """CCPA Business Purposes (not considered sale)"""
    AUDITING = "auditing"
    SECURITY = "security"
    DEBUGGING = "debugging"
    SHORT_TERM_USE = "short_term_use"
    SERVICE_DELIVERY = "service_delivery"
    INTERNAL_RESEARCH = "internal_research"
    QUALITY_ASSURANCE = "quality_assurance"


class LegalException(str, Enum):
    """CCPA exceptions to consumer rights"""
    COMPLETE_TRANSACTION = "complete_transaction"
    SECURITY_INCIDENT = "security_incident"
    DEBUG_ERRORS = "debug_errors"
    FREE_SPEECH = "free_speech"
    RESEARCH = "research"
    INTERNAL_USE = "internal_use"
    LEGAL_OBLIGATION = "legal_obligation"
    OTHERWISE_LAWFUL = "otherwise_lawful"


# =============================================================================
# Notice and Disclosure Requirements
# =============================================================================

class NoticeType(str, Enum):
    """Types of CCPA notices"""
    NOTICE_AT_COLLECTION = "notice_at_collection"  # 1798.100
    PRIVACY_POLICY = "privacy_policy"              # 1798.130
    DO_NOT_SELL_LINK = "do_not_sell_link"          # 1798.135
    FINANCIAL_INCENTIVE = "financial_incentive"    # 1798.125
    LIMIT_SPI_LINK = "limit_spi_link"             # CPRA: Limit sensitive PI


class DisclosureCategory(str, Enum):
    """Categories businesses must disclose"""
    CATEGORIES_COLLECTED = "categories_collected"
    SOURCES = "sources"
    BUSINESS_PURPOSE = "business_purpose"
    THIRD_PARTIES = "third_parties"
    SPECIFIC_PIECES = "specific_pieces"
    CATEGORIES_SOLD = "categories_sold"           # If applicable
    CATEGORIES_SHARED = "categories_shared"       # CPRA
    RETENTION_PERIODS = "retention_periods"       # CPRA


# =============================================================================
# Financial Incentives (Section 1798.125)
# =============================================================================

class IncentiveType(str, Enum):
    """Types of financial incentives"""
    DISCOUNT = "discount"
    REWARD_PROGRAM = "reward_program"
    FREE_SERVICE = "free_service"
    PREMIUM_SERVICE = "premium_service"
    DIFFERENT_PRICE = "different_price"
    DIFFERENT_QUALITY = "different_quality"


class IncentiveStatus(str, Enum):
    """Consumer status in incentive program"""
    NOT_ENROLLED = "not_enrolled"
    ENROLLED = "enrolled"
    OPTED_OUT = "opted_out"
    WITHDRAWN = "withdrawn"


# =============================================================================
# Minors (Section 1798.120(c))
# =============================================================================

class MinorCategory(str, Enum):
    """Age categories for minor protections"""
    UNDER_13 = "under_13"     # Requires parental opt-in
    AGE_13_TO_15 = "13_to_15"  # Requires minor's opt-in
    AGE_16_PLUS = "16_plus"    # Standard opt-out applies


# =============================================================================
# Enforcement and Compliance
# =============================================================================

class ViolationType(str, Enum):
    """Types of CCPA violations"""
    FAILURE_TO_RESPOND = "failure_to_respond"
    UNAUTHORIZED_SALE = "unauthorized_sale"
    MISSING_NOTICE = "missing_notice"
    DISCRIMINATION = "discrimination"
    DATA_BREACH = "data_breach"
    MINOR_VIOLATION = "minor_violation"


class ComplianceArea(str, Enum):
    """Areas of CCPA compliance"""
    PRIVACY_POLICY = "privacy_policy"
    NOTICE_AT_COLLECTION = "notice_at_collection"
    OPT_OUT_MECHANISM = "opt_out_mechanism"
    VERIFICATION_PROCESS = "verification_process"
    REQUEST_HANDLING = "request_handling"
    SERVICE_PROVIDER_CONTRACTS = "service_provider_contracts"
    EMPLOYEE_TRAINING = "employee_training"
    DATA_INVENTORY = "data_inventory"
    SECURITY_MEASURES = "security_measures"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class Consumer:
    """CCPA Consumer record"""
    id: str
    external_id: Optional[str] = None
    email: Optional[str] = None
    is_california_resident: bool = True
    is_minor: bool = False
    minor_category: Optional[MinorCategory] = None
    opt_out_status: OptOutStatus = OptOutStatus.NOT_OPTED_OUT
    pi_categories: List[PersonalInfoCategory] = field(default_factory=list)
    created_at: str = ""
    last_activity: str = ""


@dataclass
class ConsumerRequest:
    """Consumer rights request record"""
    id: str
    consumer_id: str
    right_type: ConsumerRight
    status: RequestStatus
    received_at: str
    deadline: str  # 45 days from receipt
    verified_at: Optional[str] = None
    completed_at: Optional[str] = None
    response: Optional[str] = None
    denial_reason: Optional[DenialReason] = None
    extended: bool = False
    extension_reason: Optional[str] = None


@dataclass
class SaleShareRecord:
    """Record of PI sale or sharing"""
    id: str
    consumer_id: str
    recipient_id: str
    recipient_role: BusinessRole
    transfer_type: SaleShareType
    pi_categories: List[PersonalInfoCategory]
    purpose: str
    consideration: str = ""  # What was received in exchange
    transferred_at: str = ""
    opt_out_honored: bool = True


@dataclass
class ServiceProviderContract:
    """Service provider/contractor contract record"""
    id: str
    provider_id: str
    provider_name: str
    role: BusinessRole
    contract_date: str
    services: str
    pi_categories: List[PersonalInfoCategory]
    restrictions: List[str] = field(default_factory=list)
    audit_rights: bool = False
    expires_at: Optional[str] = None


@dataclass
class FinancialIncentive:
    """Financial incentive program record"""
    id: str
    name: str
    incentive_type: IncentiveType
    description: str
    value_calculation: str  # Method for calculating PI value
    pi_required: List[PersonalInfoCategory]
    opt_in_required: bool = True
    notice_provided: bool = False
    created_at: str = ""


@dataclass
class NoticeRecord:
    """Notice/disclosure record"""
    id: str
    notice_type: NoticeType
    version: str
    effective_date: str
    content_summary: str
    categories_disclosed: List[DisclosureCategory]
    url: Optional[str] = None
    last_updated: str = ""


@dataclass
class ComplianceStatus:
    """Overall CCPA compliance status"""
    business_id: str
    is_subject_to_ccpa: bool
    privacy_policy_current: bool
    notice_at_collection: bool
    opt_out_mechanism: bool
    request_handling_process: bool
    verification_process: bool
    service_provider_contracts: int
    pending_requests: int
    overdue_requests: int
    opt_out_consumers: int
    compliance_score: float = 0.0
    issues: List[Dict[str, Any]] = field(default_factory=list)
