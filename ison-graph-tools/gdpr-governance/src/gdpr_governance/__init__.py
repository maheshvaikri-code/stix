"""
GDPR Governance for ISONGraph
=============================

Comprehensive GDPR compliance management using ISONGraph.

This package provides tools for managing:
- Records of Processing Activities (Article 30)
- Data Subject management and data inventory
- Consent management (Article 7)
- Data Subject Rights (Articles 15-22)
- Data Breach notification (Articles 33-34)
- Data Protection Impact Assessments (Article 35)
- International Transfers (Articles 44-49)

Usage:
    from ison_graph import ISONGraph
    from gdpr_governance import GDPRGovernance

    graph = ISONGraph()
    gdpr = GDPRGovernance(graph)

    # Register a processing activity
    activity_id = gdpr.processing.register_activity(
        name="Customer Newsletter",
        purpose="Marketing communications",
        lawful_basis=LawfulBasis.CONSENT,
        data_categories=[PersonalDataCategory.BASIC_IDENTITY, PersonalDataCategory.CONTACT],
        data_subjects=["customers"],
        recipients=["internal_marketing"],
        retention_period="Until consent withdrawn",
        security_measures=["encryption", "access_control"],
        controller_id="main_controller",
    )

    # Record consent
    consent_id = gdpr.consent.record_consent(
        data_subject_id="user123",
        purpose="marketing_newsletter",
        consent_type=ConsentType.MARKETING,
        evidence="web_form_checkbox",
    )

    # Handle data subject request
    request_id = gdpr.rights.submit_request(
        data_subject_id="user123",
        right_type=DataSubjectRight.ACCESS,
    )

    # Get compliance status
    status = gdpr.get_compliance_status()
"""

from .schema import (
    # Lawful Basis (Article 6)
    LawfulBasis,
    SpecialCategoryBasis,
    # Personal Data Classification
    PersonalDataCategory,
    DataSensitivity,
    # Consent (Article 7)
    ConsentStatus,
    ConsentType,
    # Data Subject Rights (Articles 15-22)
    DataSubjectRight,
    RightRequestStatus,
    RefusalReason,
    # Data Breach (Articles 33-34)
    BreachSeverity,
    BreachStatus,
    BreachType,
    # DPIA (Article 35)
    DPIAStatus,
    DPIATrigger,
    # International Transfers (Articles 44-49)
    TransferMechanism,
    TransferStatus,
    # Roles
    ActorRole,
    ProcessingPurpose,
    # Data classes
    ProcessingActivity,
    DataSubject,
    ConsentRecord,
    RightRequest,
    DataBreach,
    DPIA,
    InternationalTransfer,
    ComplianceStatus,
)

from .stores import (
    BaseGDPRStore,
    DataSubjectStore,
    ProcessingActivityStore,
    ConsentStore,
    DataSubjectRightsStore,
    DataBreachStore,
    DPIAStore,
    InternationalTransferStore,
)

from .engine import GDPRGovernance

__version__ = "0.1.0"

__all__ = [
    # Main engine
    "GDPRGovernance",
    # Stores
    "BaseGDPRStore",
    "DataSubjectStore",
    "ProcessingActivityStore",
    "ConsentStore",
    "DataSubjectRightsStore",
    "DataBreachStore",
    "DPIAStore",
    "InternationalTransferStore",
    # Enums - Lawful Basis
    "LawfulBasis",
    "SpecialCategoryBasis",
    # Enums - Personal Data
    "PersonalDataCategory",
    "DataSensitivity",
    # Enums - Consent
    "ConsentStatus",
    "ConsentType",
    # Enums - Rights
    "DataSubjectRight",
    "RightRequestStatus",
    "RefusalReason",
    # Enums - Breach
    "BreachSeverity",
    "BreachStatus",
    "BreachType",
    # Enums - DPIA
    "DPIAStatus",
    "DPIATrigger",
    # Enums - Transfer
    "TransferMechanism",
    "TransferStatus",
    # Enums - Other
    "ActorRole",
    "ProcessingPurpose",
    # Data classes
    "ProcessingActivity",
    "DataSubject",
    "ConsentRecord",
    "RightRequest",
    "DataBreach",
    "DPIA",
    "InternationalTransfer",
    "ComplianceStatus",
]
