"""
PII Governance Schema
=====================

Comprehensive PII classification taxonomy and data models.
Covers detection, classification, and cross-regulation mapping.
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set
from datetime import datetime


# =============================================================================
# PII Categories and Types
# =============================================================================

class PIICategory(str, Enum):
    """High-level PII categories"""
    DIRECT_IDENTIFIERS = "direct_identifiers"      # Directly identifies individual
    QUASI_IDENTIFIERS = "quasi_identifiers"        # Can identify when combined
    SENSITIVE_PII = "sensitive_pii"                # Requires extra protection
    FINANCIAL = "financial"                         # Financial information
    HEALTH = "health"                               # Health/medical data
    BIOMETRIC = "biometric"                         # Biometric identifiers
    ONLINE = "online"                               # Online identifiers
    GOVERNMENT_ID = "government_id"                 # Government-issued IDs
    AUTHENTICATION = "authentication"               # Credentials/auth data


class PIIType(str, Enum):
    """Specific PII data types"""
    # Direct Identifiers
    FULL_NAME = "full_name"
    FIRST_NAME = "first_name"
    LAST_NAME = "last_name"
    MAIDEN_NAME = "maiden_name"
    ALIAS = "alias"

    # Contact Information
    EMAIL = "email"
    PHONE_NUMBER = "phone_number"
    MOBILE_NUMBER = "mobile_number"
    FAX_NUMBER = "fax_number"
    STREET_ADDRESS = "street_address"
    CITY = "city"
    STATE_PROVINCE = "state_province"
    POSTAL_CODE = "postal_code"
    COUNTRY = "country"

    # Government IDs
    SSN = "ssn"                                     # Social Security Number
    SSN_LAST4 = "ssn_last4"                        # Last 4 of SSN
    NATIONAL_ID = "national_id"                    # National ID number
    PASSPORT_NUMBER = "passport_number"
    DRIVERS_LICENSE = "drivers_license"
    TAX_ID = "tax_id"
    VOTER_ID = "voter_id"
    MILITARY_ID = "military_id"

    # Financial
    CREDIT_CARD = "credit_card"
    CREDIT_CARD_CVV = "credit_card_cvv"
    DEBIT_CARD = "debit_card"
    BANK_ACCOUNT = "bank_account"
    ROUTING_NUMBER = "routing_number"
    IBAN = "iban"
    SWIFT_CODE = "swift_code"
    INCOME = "income"
    CREDIT_SCORE = "credit_score"

    # Health/Medical
    MEDICAL_RECORD_NUMBER = "medical_record_number"
    HEALTH_INSURANCE_ID = "health_insurance_id"
    DIAGNOSIS = "diagnosis"
    MEDICATION = "medication"
    LAB_RESULTS = "lab_results"
    MEDICAL_CONDITION = "medical_condition"
    DISABILITY = "disability"

    # Biometric
    FINGERPRINT = "fingerprint"
    FACIAL_RECOGNITION = "facial_recognition"
    RETINA_SCAN = "retina_scan"
    VOICE_PRINT = "voice_print"
    DNA = "dna"
    GAIT = "gait"

    # Online Identifiers
    IP_ADDRESS = "ip_address"
    MAC_ADDRESS = "mac_address"
    DEVICE_ID = "device_id"
    COOKIE_ID = "cookie_id"
    ADVERTISING_ID = "advertising_id"
    USERNAME = "username"
    USER_ID = "user_id"

    # Authentication
    PASSWORD = "password"
    PASSWORD_HASH = "password_hash"
    SECURITY_QUESTION = "security_question"
    PIN = "pin"
    API_KEY = "api_key"
    ACCESS_TOKEN = "access_token"
    PRIVATE_KEY = "private_key"

    # Demographics
    DATE_OF_BIRTH = "date_of_birth"
    AGE = "age"
    GENDER = "gender"
    RACE_ETHNICITY = "race_ethnicity"
    RELIGION = "religion"
    SEXUAL_ORIENTATION = "sexual_orientation"
    POLITICAL_AFFILIATION = "political_affiliation"
    MARITAL_STATUS = "marital_status"

    # Employment
    EMPLOYEE_ID = "employee_id"
    JOB_TITLE = "job_title"
    SALARY = "salary"
    PERFORMANCE_REVIEW = "performance_review"
    WORK_HISTORY = "work_history"

    # Education
    STUDENT_ID = "student_id"
    GRADES = "grades"
    ENROLLMENT_STATUS = "enrollment_status"
    EDUCATION_RECORDS = "education_records"

    # Location
    GPS_COORDINATES = "gps_coordinates"
    GEOLOCATION = "geolocation"
    HOME_ADDRESS = "home_address"
    WORK_ADDRESS = "work_address"

    # Legal
    CRIMINAL_RECORD = "criminal_record"
    COURT_RECORDS = "court_records"
    IMMIGRATION_STATUS = "immigration_status"

    # Other
    PHOTOGRAPH = "photograph"
    VIDEO = "video"
    SIGNATURE = "signature"
    VEHICLE_ID = "vehicle_id"                      # VIN, license plate
    INSURANCE_POLICY = "insurance_policy"


# =============================================================================
# Sensitivity Classification
# =============================================================================

class SensitivityLevel(str, Enum):
    """Data sensitivity levels"""
    PUBLIC = "public"                  # Publicly available
    INTERNAL = "internal"              # Internal use only
    CONFIDENTIAL = "confidential"      # Limited access
    RESTRICTED = "restricted"          # Highly restricted
    TOP_SECRET = "top_secret"          # Maximum protection


class RiskLevel(str, Enum):
    """Risk levels for PII exposure"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


# =============================================================================
# Regulatory Frameworks
# =============================================================================

class Regulation(str, Enum):
    """Privacy/data protection regulations"""
    GDPR = "gdpr"                      # EU General Data Protection Regulation
    CCPA = "ccpa"                      # California Consumer Privacy Act
    CPRA = "cpra"                      # California Privacy Rights Act
    HIPAA = "hipaa"                    # Health Insurance Portability Act
    PCI_DSS = "pci_dss"                # Payment Card Industry
    FERPA = "ferpa"                    # Family Educational Rights
    GLBA = "glba"                      # Gramm-Leach-Bliley Act
    SOX = "sox"                        # Sarbanes-Oxley
    COPPA = "coppa"                    # Children's Online Privacy
    LGPD = "lgpd"                      # Brazil Lei Geral de Proteção de Dados
    PIPEDA = "pipeda"                  # Canada Personal Information Protection
    PDPA = "pdpa"                      # Singapore Personal Data Protection
    APPI = "appi"                      # Japan Act on Protection of Personal Info
    STATE_PRIVACY = "state_privacy"    # US State privacy laws


class RegulationCategory(str, Enum):
    """Regulation-specific data categories"""
    # GDPR
    GDPR_PERSONAL_DATA = "gdpr_personal_data"
    GDPR_SPECIAL_CATEGORY = "gdpr_special_category"

    # CCPA/CPRA
    CCPA_PERSONAL_INFO = "ccpa_personal_info"
    CCPA_SENSITIVE_PI = "ccpa_sensitive_pi"

    # HIPAA
    HIPAA_PHI = "hipaa_phi"                        # Protected Health Information
    HIPAA_EPHI = "hipaa_ephi"                      # Electronic PHI

    # PCI-DSS
    PCI_CARDHOLDER_DATA = "pci_cardholder_data"
    PCI_SENSITIVE_AUTH = "pci_sensitive_auth"

    # FERPA
    FERPA_EDUCATION_RECORDS = "ferpa_education_records"
    FERPA_PII = "ferpa_pii"


# =============================================================================
# Data Sources and Locations
# =============================================================================

class DataSourceType(str, Enum):
    """Types of data sources"""
    DATABASE = "database"
    FILE_SYSTEM = "file_system"
    CLOUD_STORAGE = "cloud_storage"
    API = "api"
    APPLICATION = "application"
    LOG_FILE = "log_file"
    EMAIL = "email"
    DATA_WAREHOUSE = "data_warehouse"
    DATA_LAKE = "data_lake"
    SAAS_APPLICATION = "saas_application"
    SPREADSHEET = "spreadsheet"
    BACKUP = "backup"


class StorageLocation(str, Enum):
    """Data storage locations"""
    ON_PREMISE = "on_premise"
    CLOUD_AWS = "cloud_aws"
    CLOUD_AZURE = "cloud_azure"
    CLOUD_GCP = "cloud_gcp"
    HYBRID = "hybrid"
    THIRD_PARTY = "third_party"
    UNKNOWN = "unknown"


# =============================================================================
# Detection and Discovery
# =============================================================================

class DetectionMethod(str, Enum):
    """How PII was detected"""
    MANUAL_CLASSIFICATION = "manual_classification"
    REGEX_PATTERN = "regex_pattern"
    ML_CLASSIFICATION = "ml_classification"
    NER = "ner"                        # Named Entity Recognition
    COLUMN_NAME = "column_name"        # Inferred from column/field name
    METADATA = "metadata"
    DATA_CATALOG = "data_catalog"
    USER_REPORTED = "user_reported"


class DetectionConfidence(str, Enum):
    """Confidence level of detection"""
    LOW = "low"                        # < 60%
    MEDIUM = "medium"                  # 60-80%
    HIGH = "high"                      # 80-95%
    CONFIRMED = "confirmed"            # 95%+ or manually verified


# =============================================================================
# Data Protection Status
# =============================================================================

class ProtectionStatus(str, Enum):
    """Current protection status of PII"""
    UNPROTECTED = "unprotected"
    ENCRYPTED_AT_REST = "encrypted_at_rest"
    ENCRYPTED_IN_TRANSIT = "encrypted_in_transit"
    FULLY_ENCRYPTED = "fully_encrypted"
    TOKENIZED = "tokenized"
    MASKED = "masked"
    PSEUDONYMIZED = "pseudonymized"
    ANONYMIZED = "anonymized"
    REDACTED = "redacted"


class AccessControl(str, Enum):
    """Access control status"""
    OPEN = "open"                      # No access control
    ROLE_BASED = "role_based"          # RBAC
    ATTRIBUTE_BASED = "attribute_based"  # ABAC
    NEED_TO_KNOW = "need_to_know"
    PRIVILEGED = "privileged"
    RESTRICTED = "restricted"


# =============================================================================
# Data Lifecycle
# =============================================================================

class DataLifecycleStage(str, Enum):
    """Data lifecycle stages"""
    COLLECTION = "collection"
    PROCESSING = "processing"
    STORAGE = "storage"
    USAGE = "usage"
    SHARING = "sharing"
    ARCHIVAL = "archival"
    DELETION = "deletion"


class RetentionStatus(str, Enum):
    """Data retention status"""
    ACTIVE = "active"
    PENDING_REVIEW = "pending_review"
    PENDING_DELETION = "pending_deletion"
    ARCHIVED = "archived"
    DELETED = "deleted"
    LEGAL_HOLD = "legal_hold"


# =============================================================================
# Cross-Regulation Mapping
# =============================================================================

# Maps PII types to applicable regulations
PII_REGULATION_MAP: Dict[PIIType, Set[Regulation]] = {
    # Government IDs - covered by most regulations
    PIIType.SSN: {Regulation.GDPR, Regulation.CCPA, Regulation.GLBA, Regulation.HIPAA},
    PIIType.PASSPORT_NUMBER: {Regulation.GDPR, Regulation.CCPA},
    PIIType.DRIVERS_LICENSE: {Regulation.GDPR, Regulation.CCPA},

    # Financial - PCI-DSS, GLBA
    PIIType.CREDIT_CARD: {Regulation.PCI_DSS, Regulation.GDPR, Regulation.CCPA, Regulation.GLBA},
    PIIType.CREDIT_CARD_CVV: {Regulation.PCI_DSS},
    PIIType.BANK_ACCOUNT: {Regulation.GLBA, Regulation.GDPR, Regulation.CCPA},

    # Health - HIPAA
    PIIType.MEDICAL_RECORD_NUMBER: {Regulation.HIPAA, Regulation.GDPR},
    PIIType.HEALTH_INSURANCE_ID: {Regulation.HIPAA, Regulation.GDPR},
    PIIType.DIAGNOSIS: {Regulation.HIPAA, Regulation.GDPR},
    PIIType.MEDICATION: {Regulation.HIPAA, Regulation.GDPR},

    # Education - FERPA
    PIIType.STUDENT_ID: {Regulation.FERPA, Regulation.GDPR},
    PIIType.GRADES: {Regulation.FERPA, Regulation.GDPR},
    PIIType.EDUCATION_RECORDS: {Regulation.FERPA, Regulation.GDPR},

    # Biometric - GDPR special category, CCPA sensitive
    PIIType.FINGERPRINT: {Regulation.GDPR, Regulation.CCPA},
    PIIType.FACIAL_RECOGNITION: {Regulation.GDPR, Regulation.CCPA},
    PIIType.DNA: {Regulation.GDPR, Regulation.CCPA, Regulation.HIPAA},

    # Children - COPPA
    PIIType.DATE_OF_BIRTH: {Regulation.COPPA, Regulation.GDPR, Regulation.CCPA},
}

# Maps PII types to sensitivity levels
PII_SENSITIVITY_MAP: Dict[PIIType, SensitivityLevel] = {
    # Top Secret
    PIIType.SSN: SensitivityLevel.TOP_SECRET,
    PIIType.CREDIT_CARD_CVV: SensitivityLevel.TOP_SECRET,
    PIIType.PASSWORD: SensitivityLevel.TOP_SECRET,
    PIIType.PRIVATE_KEY: SensitivityLevel.TOP_SECRET,
    PIIType.DNA: SensitivityLevel.TOP_SECRET,

    # Restricted
    PIIType.CREDIT_CARD: SensitivityLevel.RESTRICTED,
    PIIType.BANK_ACCOUNT: SensitivityLevel.RESTRICTED,
    PIIType.MEDICAL_RECORD_NUMBER: SensitivityLevel.RESTRICTED,
    PIIType.DIAGNOSIS: SensitivityLevel.RESTRICTED,
    PIIType.FINGERPRINT: SensitivityLevel.RESTRICTED,
    PIIType.CRIMINAL_RECORD: SensitivityLevel.RESTRICTED,

    # Confidential
    PIIType.PASSPORT_NUMBER: SensitivityLevel.CONFIDENTIAL,
    PIIType.DRIVERS_LICENSE: SensitivityLevel.CONFIDENTIAL,
    PIIType.DATE_OF_BIRTH: SensitivityLevel.CONFIDENTIAL,
    PIIType.INCOME: SensitivityLevel.CONFIDENTIAL,
    PIIType.GPS_COORDINATES: SensitivityLevel.CONFIDENTIAL,

    # Internal
    PIIType.EMAIL: SensitivityLevel.INTERNAL,
    PIIType.PHONE_NUMBER: SensitivityLevel.INTERNAL,
    PIIType.STREET_ADDRESS: SensitivityLevel.INTERNAL,
    PIIType.IP_ADDRESS: SensitivityLevel.INTERNAL,

    # Default to Confidential for unlisted
}


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class PIIField:
    """Represents a PII field/column"""
    id: str
    name: str
    pii_type: PIIType
    category: PIICategory
    sensitivity: SensitivityLevel
    detection_method: DetectionMethod
    confidence: DetectionConfidence
    source_id: str
    location: str = ""                 # Table.column, file path, etc.
    sample_count: int = 0
    protection_status: ProtectionStatus = ProtectionStatus.UNPROTECTED
    regulations: List[Regulation] = field(default_factory=list)
    discovered_at: str = ""
    last_scanned: str = ""
    verified: bool = False
    verified_by: str = ""


@dataclass
class DataSource:
    """Represents a data source containing PII"""
    id: str
    name: str
    source_type: DataSourceType
    storage_location: StorageLocation
    connection_info: str = ""          # Encrypted/masked connection details
    owner: str = ""
    custodian: str = ""
    pii_fields: List[str] = field(default_factory=list)
    sensitivity_level: SensitivityLevel = SensitivityLevel.INTERNAL
    last_scan: str = ""
    scan_frequency: str = ""
    created_at: str = ""


@dataclass
class PIIInventoryItem:
    """Item in the PII inventory"""
    id: str
    pii_type: PIIType
    data_source_id: str
    field_location: str
    record_count: int
    sensitivity: SensitivityLevel
    risk_level: RiskLevel
    protection_status: ProtectionStatus
    retention_status: RetentionStatus
    regulations: List[Regulation]
    data_owner: str = ""
    business_purpose: str = ""
    retention_period: str = ""
    created_at: str = ""
    last_updated: str = ""


@dataclass
class RiskAssessment:
    """PII risk assessment record"""
    id: str
    scope: str                         # What was assessed
    risk_level: RiskLevel
    sensitivity_score: float           # 0-100
    exposure_score: float              # 0-100
    protection_score: float            # 0-100
    compliance_gaps: List[Dict[str, Any]]
    recommendations: List[str]
    assessed_by: str = ""
    assessed_at: str = ""
    next_review: str = ""


@dataclass
class DataLineage:
    """Tracks data flow and lineage"""
    id: str
    pii_field_id: str
    source_system: str
    target_system: str
    transformation: str = ""
    purpose: str = ""
    created_at: str = ""
