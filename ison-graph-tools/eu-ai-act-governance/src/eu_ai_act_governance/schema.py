"""
EU AI Act Governance Schema
===========================

Comprehensive type definitions for EU AI Act (Regulation 2024/1689) compliance.
Covers risk classification, prohibited practices, high-risk requirements,
conformity assessment, and all regulatory domains.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


# =============================================================================
# EU AI Act Regulation References
# =============================================================================

class AIActArticle(Enum):
    """EU AI Act article references"""
    PROHIBITED_PRACTICES = "Art. 5"
    HIGH_RISK_CLASSIFICATION = "Art. 6"
    HIGH_RISK_CATEGORIES = "Art. 7"
    RISK_MANAGEMENT = "Art. 9"
    DATA_GOVERNANCE = "Art. 10"
    TECHNICAL_DOCUMENTATION = "Art. 11"
    RECORD_KEEPING = "Art. 12"
    TRANSPARENCY = "Art. 13"
    HUMAN_OVERSIGHT = "Art. 14"
    ACCURACY_ROBUSTNESS = "Art. 15"
    QUALITY_MANAGEMENT = "Art. 17"
    CONFORMITY_ASSESSMENT = "Art. 43"
    CE_MARKING = "Art. 48"
    EU_DATABASE = "Art. 49"
    AI_GENERATED_CONTENT = "Art. 50"
    GPAI_OBLIGATIONS = "Art. 51"
    GPAI_SYSTEMIC_RISK = "Art. 52"
    POST_MARKET_MONITORING = "Art. 72"
    INCIDENT_REPORTING = "Art. 73"
    FUNDAMENTAL_RIGHTS = "Art. 27"


# =============================================================================
# Risk Classification (Art. 5-7)
# =============================================================================

class AIRiskLevel(Enum):
    """AI system risk levels per EU AI Act"""
    UNACCEPTABLE = "unacceptable"   # Prohibited (Art. 5)
    HIGH = "high"                    # Annex III systems
    LIMITED = "limited"              # Transparency obligations only
    MINIMAL = "minimal"              # No specific requirements


class ProhibitedPractice(Enum):
    """Prohibited AI practices (Art. 5)"""
    # Art. 5(1)(a) - Subliminal/manipulative techniques
    SUBLIMINAL_MANIPULATION = "subliminal_manipulation"
    DECEPTIVE_MANIPULATION = "deceptive_manipulation"
    MANIPULATION_DECEPTIVE = "manipulation_deceptive"

    # Art. 5(1)(b) - Exploitation of vulnerabilities
    EXPLOITING_VULNERABILITIES = "exploiting_vulnerabilities"
    EXPLOITATION_AGE = "exploitation_age"
    EXPLOITATION_DISABILITY = "exploitation_disability"
    EXPLOITATION_SOCIOECONOMIC = "exploitation_socioeconomic"

    # Art. 5(1)(c) - Social scoring
    SOCIAL_SCORING_PUBLIC = "social_scoring_public"
    SOCIAL_SCORING_PRIVATE = "social_scoring_private"

    # Art. 5(1)(d) - Risk assessment for offending
    PREDICTIVE_POLICING_INDIVIDUAL = "predictive_policing_individual"

    # Art. 5(1)(e) - Facial recognition database scraping
    FACIAL_RECOGNITION_SCRAPING = "facial_recognition_scraping"

    # Art. 5(1)(f) - Emotion inference in workplace/education
    EMOTION_INFERENCE_WORKPLACE = "emotion_inference_workplace"
    EMOTION_INFERENCE_EDUCATION = "emotion_inference_education"
    EMOTION_RECOGNITION_WORKPLACE = "emotion_recognition_workplace"
    EMOTION_RECOGNITION_EDUCATION = "emotion_recognition_education"

    # Art. 5(1)(g) - Biometric categorization (sensitive)
    BIOMETRIC_CATEGORIZATION_SENSITIVE = "biometric_categorization_sensitive"
    BIOMETRIC_CATEGORIZATION_RACE = "biometric_categorization_race"
    BIOMETRIC_CATEGORIZATION_POLITICS = "biometric_categorization_politics"
    BIOMETRIC_CATEGORIZATION_RELIGION = "biometric_categorization_religion"
    BIOMETRIC_CATEGORIZATION_SEXUAL = "biometric_categorization_sexual"

    # Art. 5(1)(h) - Real-time remote biometric identification
    REAL_TIME_BIOMETRIC_PUBLIC = "real_time_biometric_public"


class HighRiskCategory(Enum):
    """High-risk AI categories (Annex III)"""
    # Simplified category names for convenience
    BIOMETRICS = "biometrics"
    CRITICAL_INFRASTRUCTURE = "critical_infrastructure"
    EDUCATION_VOCATIONAL = "education_vocational"
    EMPLOYMENT_WORKERS = "employment_workers"
    ESSENTIAL_SERVICES = "essential_services"
    LAW_ENFORCEMENT = "law_enforcement"
    MIGRATION_ASYLUM = "migration_asylum"
    JUSTICE_DEMOCRACY = "justice_democracy"

    # Point 1 - Biometrics (detailed)
    BIOMETRIC_IDENTIFICATION = "biometric_identification"
    BIOMETRIC_CATEGORIZATION = "biometric_categorization"
    EMOTION_RECOGNITION = "emotion_recognition"

    # Point 2 - Critical infrastructure
    CRITICAL_INFRASTRUCTURE_SAFETY = "critical_infrastructure_safety"
    ROAD_TRAFFIC = "road_traffic"
    WATER_GAS_ELECTRICITY = "water_gas_electricity"

    # Point 3 - Education and training
    EDUCATION_ACCESS = "education_access"
    EDUCATION_ASSESSMENT = "education_assessment"
    EXAM_PROCTORING = "exam_proctoring"

    # Point 4 - Employment
    RECRUITMENT = "recruitment"
    JOB_ADVERTISEMENT = "job_advertisement"
    CV_SCREENING = "cv_screening"
    INTERVIEW_ASSESSMENT = "interview_assessment"
    EMPLOYMENT_DECISIONS = "employment_decisions"
    TASK_ALLOCATION = "task_allocation"
    PERFORMANCE_MONITORING = "performance_monitoring"

    # Point 5 - Essential services
    CREDITWORTHINESS = "creditworthiness"
    CREDIT_SCORING = "credit_scoring"
    INSURANCE_RISK = "insurance_risk"
    INSURANCE_PRICING = "insurance_pricing"
    EMERGENCY_SERVICES = "emergency_services"

    # Point 6 - Law enforcement
    POLYGRAPH = "polygraph"
    EVIDENCE_RELIABILITY = "evidence_reliability"
    CRIME_PREDICTION = "crime_prediction"
    PROFILING = "profiling"

    # Point 7 - Migration and asylum
    MIGRATION_RISK = "migration_risk"
    VISA_APPLICATION = "visa_application"
    ASYLUM_APPLICATION = "asylum_application"
    BORDER_CONTROL = "border_control"

    # Point 8 - Justice and democracy
    LEGAL_RESEARCH = "legal_research"
    LEGAL_INTERPRETATION = "legal_interpretation"
    DISPUTE_RESOLUTION = "dispute_resolution"
    ELECTION_INFLUENCE = "election_influence"


class RiskMitigationStatus(Enum):
    """Risk mitigation status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    FAILED = "failed"


# =============================================================================
# Conformity Assessment (Art. 43-49)
# =============================================================================

class ConformityRoute(Enum):
    """Conformity assessment procedures"""
    INTERNAL_CONTROL = "internal_control"           # Annex VI
    INTERNAL_CONTROL_QMS = "internal_control_qms"   # Internal control with QMS
    QUALITY_MANAGEMENT_SYSTEM = "quality_management_system"  # Annex VII
    NOTIFIED_BODY = "notified_body"                 # Third-party assessment
    EU_TYPE_EXAMINATION = "eu_type_examination"     # For specific products


class ConformityStatus(Enum):
    """Conformity assessment status"""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    UNDER_REVIEW = "under_review"
    PENDING_REVIEW = "pending_review"
    PASSED = "passed"
    FAILED = "failed"
    CONDITIONAL = "conditional"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"


class CEMarkingStatus(Enum):
    """CE marking status"""
    NOT_APPLICABLE = "not_applicable"
    PENDING = "pending"
    APPLIED = "applied"
    VALID = "valid"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"


# =============================================================================
# Documentation Requirements (Art. 11, Annex IV)
# =============================================================================

class DocumentationType(Enum):
    """Technical documentation types (Annex IV)"""
    GENERAL_DESCRIPTION = "general_description"
    SYSTEM_ARCHITECTURE = "system_architecture"
    ALGORITHM_DESCRIPTION = "algorithm_description"
    DETAILED_DESCRIPTION = "detailed_description"
    DEVELOPMENT_PROCESS = "development_process"
    MONITORING_FUNCTIONING = "monitoring_functioning"
    RISK_MANAGEMENT = "risk_management"
    DATA_REQUIREMENTS = "data_requirements"
    TRAINING_PROCESS = "training_process"
    TESTING_VALIDATION = "testing_validation"
    PERFORMANCE_METRICS = "performance_metrics"
    CYBERSECURITY = "cybersecurity"
    CONFORMITY_DECLARATION = "conformity_declaration"
    INSTRUCTIONS_FOR_USE = "instructions_for_use"
    CHANGE_LOG = "change_log"
    MONITORING_PLAN = "monitoring_plan"


class DocumentStatus(Enum):
    """Document status"""
    DRAFT = "draft"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    OUTDATED = "outdated"


# =============================================================================
# Quality Management (Art. 17)
# =============================================================================

class QMSElement(Enum):
    """Quality Management System elements"""
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    DESIGN_CONTROL = "design_control"
    DESIGN_VERIFICATION = "design_verification"
    DEVELOPMENT_PROCESS = "development_process"
    QUALITY_CONTROL = "quality_control"
    RESOURCE_MANAGEMENT = "resource_management"
    DATA_MANAGEMENT = "data_management"
    POST_MARKET_MONITORING = "post_market_monitoring"
    INCIDENT_REPORTING = "incident_reporting"
    COMMUNICATION_AUTHORITIES = "communication_authorities"
    CORRECTIVE_ACTIONS = "corrective_actions"
    SUPPLIER_MANAGEMENT = "supplier_management"


class QMSStatus(Enum):
    """QMS implementation status"""
    DRAFT = "draft"
    NOT_IMPLEMENTED = "not_implemented"
    PARTIALLY_IMPLEMENTED = "partially_implemented"
    IMPLEMENTED = "implemented"
    CERTIFIED = "certified"
    NON_CONFORMING = "non_conforming"


# =============================================================================
# Data Governance (Art. 10)
# =============================================================================

class DataGovernanceRequirement(Enum):
    """Data governance requirements"""
    RELEVANCE = "relevance"
    REPRESENTATIVENESS = "representativeness"
    ERROR_FREE = "error_free"
    COMPLETENESS = "completeness"
    STATISTICAL_PROPERTIES = "statistical_properties"
    BIAS_EXAMINATION = "bias_examination"
    DATA_GAPS = "data_gaps"
    PERSONAL_DATA_MEASURES = "personal_data_measures"


class DataQualityStatus(Enum):
    """Data quality assessment status"""
    NOT_ASSESSED = "not_assessed"
    ASSESSING = "assessing"
    COMPLIANT = "compliant"
    NON_COMPLIANT = "non_compliant"
    REMEDIATION_NEEDED = "remediation_needed"


class BiasType(Enum):
    """Types of bias in AI systems"""
    SELECTION_BIAS = "selection_bias"
    MEASUREMENT_BIAS = "measurement_bias"
    CONFIRMATION_BIAS = "confirmation_bias"
    HISTORICAL_BIAS = "historical_bias"
    REPRESENTATION_BIAS = "representation_bias"
    AGGREGATION_BIAS = "aggregation_bias"
    EVALUATION_BIAS = "evaluation_bias"
    DEPLOYMENT_BIAS = "deployment_bias"


# =============================================================================
# Human Oversight (Art. 14)
# =============================================================================

class OversightMeasure(Enum):
    """Human oversight measures"""
    UNDERSTAND_CAPABILITIES = "understand_capabilities"
    AWARENESS_AUTOMATION_BIAS = "awareness_automation_bias"
    INTERPRET_OUTPUT = "interpret_output"
    DECIDE_NOT_USE = "decide_not_use"
    INTERVENE_OPERATION = "intervene_operation"
    STOP_SYSTEM = "stop_system"
    # Additional measures
    OVERRIDE_CAPABILITY = "override_capability"
    STOP_BUTTON = "stop_button"
    ALERT_SYSTEM = "alert_system"
    AUDIT_LOGGING = "audit_logging"


class OversightLevel(Enum):
    """Level of human oversight"""
    HUMAN_IN_THE_LOOP = "human_in_the_loop"      # Human decides
    HUMAN_ON_THE_LOOP = "human_on_the_loop"      # Human monitors
    HUMAN_IN_COMMAND = "human_in_command"         # Human can override


class OversightStatus(Enum):
    """Oversight implementation status"""
    NOT_IMPLEMENTED = "not_implemented"
    DESIGNED = "designed"
    IMPLEMENTED = "implemented"
    TESTED = "tested"
    OPERATIONAL = "operational"
    DISABLED = "disabled"


# =============================================================================
# Transparency (Art. 13, 50)
# =============================================================================

class TransparencyObligation(Enum):
    """Transparency obligations"""
    # Art. 13 - High-risk systems
    DEPLOYER_INFORMATION = "deployer_information"
    INSTRUCTIONS_FOR_USE = "instructions_for_use"
    INTENDED_PURPOSE = "intended_purpose"
    ACCURACY_METRICS = "accuracy_metrics"
    KNOWN_LIMITATIONS = "known_limitations"
    CAPABILITY_DISCLOSURE = "capability_disclosure"
    LIMITATION_DISCLOSURE = "limitation_disclosure"

    # Art. 50 - Specific systems
    AI_INTERACTION_DISCLOSURE = "ai_interaction_disclosure"
    EMOTION_RECOGNITION_DISCLOSURE = "emotion_recognition_disclosure"
    BIOMETRIC_DISCLOSURE = "biometric_disclosure"
    DEEPFAKE_DISCLOSURE = "deepfake_disclosure"
    AI_GENERATED_CONTENT = "ai_generated_content"


class DisclosureStatus(Enum):
    """Disclosure implementation status"""
    NOT_REQUIRED = "not_required"
    DRAFT = "draft"
    REQUIRED = "required"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"


# =============================================================================
# Post-Market Monitoring (Art. 72)
# =============================================================================

class MonitoringActivity(Enum):
    """Post-market monitoring activities"""
    PERFORMANCE_TRACKING = "performance_tracking"
    ERROR_ANALYSIS = "error_analysis"
    USER_FEEDBACK = "user_feedback"
    FEEDBACK_COLLECTION = "feedback_collection"
    INCIDENT_ANALYSIS = "incident_analysis"
    COMPLAINT_HANDLING = "complaint_handling"
    RISK_REASSESSMENT = "risk_reassessment"
    DOCUMENTATION_UPDATE = "documentation_update"
    AUTHORITY_REPORTING = "authority_reporting"
    BIAS_MONITORING = "bias_monitoring"
    COMPLIANCE_AUDIT = "compliance_audit"
    SECURITY_MONITORING = "security_monitoring"


class MonitoringFrequency(Enum):
    """Monitoring frequency"""
    CONTINUOUS = "continuous"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"
    EVENT_TRIGGERED = "event_triggered"


# =============================================================================
# Incident Reporting (Art. 73)
# =============================================================================

class IncidentSeverity(Enum):
    """Incident severity levels"""
    MINOR = "minor"
    LOW = "low"
    MODERATE = "moderate"
    MEDIUM = "medium"
    MAJOR = "major"
    HIGH = "high"
    CRITICAL = "critical"
    SERIOUS = "serious"  # Per Art. 73 definition


class IncidentType(Enum):
    """Types of AI incidents"""
    MALFUNCTION = "malfunction"
    SAFETY_ISSUE = "safety_issue"
    DEATH = "death"
    SERIOUS_INJURY = "serious_injury"
    SERIOUS_HEALTH_DAMAGE = "serious_health_damage"
    SERIOUS_PROPERTY_DAMAGE = "serious_property_damage"
    SERIOUS_ENVIRONMENTAL_DAMAGE = "serious_environmental_damage"
    FUNDAMENTAL_RIGHTS_VIOLATION = "fundamental_rights_violation"
    SAFETY_MALFUNCTION = "safety_malfunction"
    SECURITY_BREACH = "security_breach"
    PERFORMANCE_DEGRADATION = "performance_degradation"
    BIAS_DETECTED = "bias_detected"
    UNINTENDED_BEHAVIOR = "unintended_behavior"


class IncidentStatus(Enum):
    """Incident handling status"""
    DETECTED = "detected"
    REPORTED = "reported"
    INVESTIGATING = "investigating"
    MITIGATED = "mitigated"
    CORRECTIVE_ACTION = "corrective_action"
    RESOLVED = "resolved"
    CLOSED = "closed"


# =============================================================================
# GPAI Models (Art. 51-56)
# =============================================================================

class GPAICategory(Enum):
    """General-purpose AI model categories"""
    GENERAL = "general"                      # Basic GPAI
    STANDARD = "standard"                    # Art. 51 obligations
    SYSTEMIC_RISK = "systemic_risk"         # Art. 52+ additional obligations


class GPAIRequirement(Enum):
    """GPAI model requirements"""
    # Standard (Art. 53)
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    INSTRUCTIONS_FOR_USE = "instructions_for_use"
    DOWNSTREAM_PROVIDER_INFO = "downstream_provider_info"
    COPYRIGHT_POLICY = "copyright_policy"
    COPYRIGHT_COMPLIANCE = "copyright_compliance"
    TRAINING_DATA_SUMMARY = "training_data_summary"
    EU_REPRESENTATIVE = "eu_representative"

    # Systemic risk (Art. 55)
    MODEL_EVALUATION = "model_evaluation"
    ADVERSARIAL_TESTING = "adversarial_testing"
    RISK_ASSESSMENT = "risk_assessment"
    INCIDENT_TRACKING = "incident_tracking"
    INCIDENT_REPORTING = "incident_reporting"
    CYBERSECURITY_PROTECTION = "cybersecurity_protection"
    CYBERSECURITY_MEASURES = "cybersecurity_measures"
    ENERGY_CONSUMPTION = "energy_consumption"
    ENERGY_REPORTING = "energy_reporting"


class SystemicRiskIndicator(Enum):
    """Indicators of systemic risk"""
    HIGH_CAPABILITY = "high_capability"
    WIDE_DEPLOYMENT = "wide_deployment"
    FLOP_THRESHOLD = "flop_threshold"          # 10^25 FLOPs
    CRITICAL_SECTOR_USE = "critical_sector_use"
    MANIPULATION_POTENTIAL = "manipulation_potential"


# =============================================================================
# Roles and Responsibilities
# =============================================================================

class AIActRole(Enum):
    """Roles under EU AI Act"""
    PROVIDER = "provider"                    # Develops/places on market
    DEPLOYER = "deployer"                    # Uses under own authority
    IMPORTER = "importer"                    # Places on EU market
    DISTRIBUTOR = "distributor"              # Makes available on market
    AUTHORIZED_REPRESENTATIVE = "authorized_representative"
    NOTIFIED_BODY = "notified_body"
    MARKET_SURVEILLANCE = "market_surveillance"


class ProviderObligation(Enum):
    """Provider obligations for high-risk AI"""
    RISK_MANAGEMENT_SYSTEM = "risk_management_system"
    DATA_GOVERNANCE = "data_governance"
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    RECORD_KEEPING = "record_keeping"
    TRANSPARENCY = "transparency"
    HUMAN_OVERSIGHT = "human_oversight"
    ACCURACY_ROBUSTNESS = "accuracy_robustness"
    CONFORMITY_ASSESSMENT = "conformity_assessment"
    EU_DATABASE_REGISTRATION = "eu_database_registration"
    CORRECTIVE_ACTIONS = "corrective_actions"
    COOPERATION_AUTHORITIES = "cooperation_authorities"


class DeployerObligation(Enum):
    """Deployer obligations for high-risk AI"""
    INSTRUCTIONS_COMPLIANCE = "instructions_compliance"
    HUMAN_OVERSIGHT = "human_oversight"
    INPUT_DATA_RELEVANT = "input_data_relevant"
    MONITORING_OPERATION = "monitoring_operation"
    RECORD_KEEPING = "record_keeping"
    INCIDENT_REPORTING = "incident_reporting"
    FUNDAMENTAL_RIGHTS_ASSESSMENT = "fundamental_rights_assessment"


# =============================================================================
# Fundamental Rights (Art. 27)
# =============================================================================

class FundamentalRight(Enum):
    """Fundamental rights potentially impacted"""
    HUMAN_DIGNITY = "human_dignity"
    PRIVACY = "privacy"
    DATA_PROTECTION = "data_protection"
    NON_DISCRIMINATION = "non_discrimination"
    EQUALITY = "equality"
    FREEDOM_EXPRESSION = "freedom_expression"
    FREEDOM_ASSEMBLY = "freedom_assembly"
    ACCESS_JUSTICE = "access_justice"
    CONSUMER_PROTECTION = "consumer_protection"
    WORKERS_RIGHTS = "workers_rights"
    CHILD_RIGHTS = "child_rights"
    DISABILITY_RIGHTS = "disability_rights"


class ImpactLevel(Enum):
    """Fundamental rights impact level"""
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    SEVERE = "severe"


# =============================================================================
# Compliance Deadlines
# =============================================================================

class ComplianceDeadline(Enum):
    """Key EU AI Act compliance deadlines"""
    PROHIBITED_PRACTICES = "2025-02-02"      # 6 months after entry
    AI_LITERACY = "2025-02-02"               # 6 months
    GPAI_MODELS = "2025-08-02"               # 12 months
    HIGH_RISK_ANNEX_III = "2026-08-02"       # 24 months
    HIGH_RISK_PRODUCTS = "2027-08-02"        # 36 months


# =============================================================================
# Edge Types for ISONGraph
# =============================================================================

EU_AI_ACT_EDGE_TYPES = {
    # Classification
    "CLASSIFIED_AS": "AI system risk classification",
    "FALLS_UNDER": "Falls under category",
    "PROHIBITED_BY": "Prohibited by article",

    # Requirements
    "HAS_REQUIREMENT": "Has compliance requirement",
    "FULFILLED_BY": "Requirement fulfilled by",
    "MITIGATED_BY": "Risk mitigated by",

    # Documentation
    "DOCUMENTED_IN": "Documented in",
    "REFERENCES": "References document",

    # Assessment
    "ASSESSED_BY": "Assessed by",
    "CERTIFIED_BY": "Certified by notified body",

    # Monitoring
    "MONITORED_BY": "Monitored by activity",
    "REPORTED_INCIDENT": "Reported incident",

    # GPAI
    "USES_GPAI": "Uses GPAI model",
    "DERIVED_FROM": "Derived from model",

    # Roles
    "PROVIDED_BY": "Provided by",
    "DEPLOYED_BY": "Deployed by",
    "OVERSEEN_BY": "Overseen by human",

    # Rights
    "IMPACTS_RIGHT": "Impacts fundamental right",
}


# =============================================================================
# Dataclasses
# =============================================================================

@dataclass
class AISystemRecord:
    """AI system registration record"""
    id: str
    name: str
    version: str
    provider: str
    risk_level: AIRiskLevel
    high_risk_category: Optional[HighRiskCategory] = None
    intended_purpose: str = ""
    deployment_status: str = "development"
    eu_database_id: Optional[str] = None
    ce_marking: CEMarkingStatus = CEMarkingStatus.NOT_APPLICABLE


@dataclass
class RiskAssessment:
    """Risk assessment record"""
    id: str
    system_id: str
    risk_level: AIRiskLevel
    assessment_date: str
    assessor: str
    methodology: str
    findings: List[str] = field(default_factory=list)
    mitigations: List[str] = field(default_factory=list)


@dataclass
class ConformityAssessmentRecord:
    """Conformity assessment record"""
    id: str
    system_id: str
    route: ConformityRoute
    status: ConformityStatus
    notified_body: Optional[str] = None
    certificate_id: Optional[str] = None
    valid_until: Optional[str] = None


@dataclass
class IncidentRecord:
    """Incident report record"""
    id: str
    system_id: str
    incident_type: IncidentType
    severity: IncidentSeverity
    description: str
    detected_date: str
    reported_date: Optional[str] = None
    authority_notified: bool = False
    status: IncidentStatus = IncidentStatus.DETECTED


@dataclass
class GPAIModelRecord:
    """GPAI model record"""
    id: str
    name: str
    provider: str
    category: GPAICategory
    training_flops: Optional[float] = None
    systemic_risk: bool = False
    downstream_systems: List[str] = field(default_factory=list)
