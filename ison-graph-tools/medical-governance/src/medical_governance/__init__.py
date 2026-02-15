"""
HIPAA Medical Governance
========================

A comprehensive HIPAA-compliant governance layer for medical AI systems
built on ISONGraph.

This package provides:
- PHI Classification & De-identification (Safe Harbor, Expert Determination)
- Access Control & Authorization (45 CFR 164.312(a))
- Minimum Necessary Standard (45 CFR 164.502(b))
- Consent Management (45 CFR 164.508/164.522)
- Audit Trail & Accounting of Disclosures (45 CFR 164.312(b), 164.528)
- Business Associate Governance (45 CFR 164.308(b))
- Breach Notification (45 CFR 164.400-414)
- Patient Rights Management (45 CFR 164.520-528)
- AI-Specific PHI Governance
- Workforce Training & Sanctions (45 CFR 164.308(a)(3), 164.530(e))

Usage:
    from ison_graph import ISONGraph
    from medical_governance import HIPAAGovernanceEngine

    # Initialize with ISONGraph backend
    graph = ISONGraph("medical_governance")
    engine = HIPAAGovernanceEngine(graph)

    # Authorize PHI access
    result = engine.authorize_phi_access(
        actor_id="dr_smith",
        actor_type="workforce",
        patient_id="patient_123",
        phi_elements=["diagnosis", "medications"],
        purpose=AccessPurpose.TREATMENT
    )

    # Get compliance dashboard
    dashboard = engine.get_compliance_dashboard()
"""

__version__ = "1.0.0"

from .schema import (
    # PHI Categories
    PHICategory,
    SensitivityLevel,
    SafeHarborAction,

    # Access & Roles
    WorkforceRole,
    AccessPurpose,

    # Consent
    ConsentType,
    ConsentStatus,

    # Breach
    BreachStatus,
    BreachSeverity,
    NotificationRecipient,

    # Business Associate
    BAType,
    BAAStatus,
    RiskTier,

    # Patient Rights
    PatientRight,
    RightRequestStatus,

    # AI Systems
    AISystemType,
    AIGovernanceRequirement,

    # Workforce
    TrainingType,
    ViolationSeverity,
    SanctionType,
)

from .engine import HIPAAGovernanceEngine

from .stores import (
    PHIClassificationStore,
    HIPAAAccessStore,
    MinimumNecessaryStore,
    ConsentStore,
    DisclosureStore,
    BusinessAssociateStore,
    BreachStore,
    PatientRightsStore,
    AIGovernanceStore,
    WorkforceStore,
)

__all__ = [
    # Main Engine
    "HIPAAGovernanceEngine",

    # Stores
    "PHIClassificationStore",
    "HIPAAAccessStore",
    "MinimumNecessaryStore",
    "ConsentStore",
    "DisclosureStore",
    "BusinessAssociateStore",
    "BreachStore",
    "PatientRightsStore",
    "AIGovernanceStore",
    "WorkforceStore",

    # PHI Categories
    "PHICategory",
    "SensitivityLevel",
    "SafeHarborAction",

    # Access & Roles
    "WorkforceRole",
    "AccessPurpose",

    # Consent
    "ConsentType",
    "ConsentStatus",

    # Breach
    "BreachStatus",
    "BreachSeverity",
    "NotificationRecipient",

    # Business Associate
    "BAType",
    "BAAStatus",
    "RiskTier",

    # Patient Rights
    "PatientRight",
    "RightRequestStatus",

    # AI Systems
    "AISystemType",
    "AIGovernanceRequirement",

    # Workforce
    "TrainingType",
    "ViolationSeverity",
    "SanctionType",
]
