"""
EU AI Act Governance
====================

A comprehensive governance layer for EU AI Act compliance built on ISONGraph.

This package provides tools for:
- Risk classification (Art. 5-7)
- Prohibited practices detection (Art. 5)
- High-risk system requirements (Art. 8-15)
- Conformity assessment (Art. 43-49)
- Technical documentation (Art. 11, Annex IV)
- Data governance (Art. 10)
- Human oversight (Art. 14)
- Transparency (Art. 13, 50)
- Post-market monitoring (Art. 72)
- Incident reporting (Art. 73)
- GPAI model governance (Art. 51-56)

Example usage:
    from ison_graph import ISONGraph
    from eu_ai_act_governance import EUAIActGovernanceEngine

    # Initialize
    graph = ISONGraph()
    engine = EUAIActGovernanceEngine(graph)

    # Onboard an AI system
    result = engine.onboard_ai_system(
        name="My AI System",
        version="1.0",
        provider="My Company",
        intended_purpose="Customer service automation",
        technical_description="NLP-based chatbot"
    )

    # Classify risk
    classification = engine.classify_system_risk(
        system_id=result["system_id"],
        assessor="compliance_officer"
    )

    # Get compliance status
    status = engine.get_system_compliance_status(result["system_id"])
"""

__version__ = "1.0.0"

from .engine import EUAIActGovernanceEngine
from .schema import (
    # Risk levels
    AIRiskLevel,
    ProhibitedPractice,
    HighRiskCategory,

    # Conformity
    ConformityRoute,
    ConformityStatus,
    CEMarkingStatus,

    # Documentation
    DocumentationType,
    QMSElement,
    QMSStatus,

    # Data governance
    DataGovernanceRequirement,
    BiasType,

    # Oversight
    OversightMeasure,
    OversightLevel,
    OversightStatus,

    # Transparency
    TransparencyObligation,
    DisclosureStatus,

    # Monitoring
    MonitoringActivity,
    MonitoringFrequency,

    # Incidents
    IncidentSeverity,
    IncidentType,
    IncidentStatus,

    # GPAI
    GPAICategory,
    GPAIRequirement,
    SystemicRiskIndicator,

    # Operators
    AIActRole,
    ProviderObligation,
    DeployerObligation,

    # Rights
    FundamentalRight,
    ImpactLevel,
)

from .stores import (
    RiskClassificationStore,
    ProhibitedPracticesStore,
    HighRiskRequirementsStore,
    ConformityAssessmentStore,
    TechnicalDocumentationStore,
    DataGovernanceStore,
    HumanOversightStore,
    TransparencyStore,
    PostMarketMonitoringStore,
    IncidentReportingStore,
    GPAIGovernanceStore,
)

__all__ = [
    # Main engine
    "EUAIActGovernanceEngine",

    # Risk classification
    "AIRiskLevel",
    "ProhibitedPractice",
    "HighRiskCategory",

    # Conformity
    "ConformityRoute",
    "ConformityStatus",
    "CEMarkingStatus",

    # Documentation
    "DocumentationType",
    "QMSElement",
    "QMSStatus",

    # Data governance
    "DataGovernanceRequirement",
    "BiasType",

    # Oversight
    "OversightMeasure",
    "OversightLevel",
    "OversightStatus",

    # Transparency
    "TransparencyObligation",
    "DisclosureStatus",

    # Monitoring
    "MonitoringActivity",
    "MonitoringFrequency",

    # Incidents
    "IncidentSeverity",
    "IncidentType",
    "IncidentStatus",

    # GPAI
    "GPAICategory",
    "GPAIRequirement",
    "SystemicRiskIndicator",

    # Operators
    "AIActRole",
    "ProviderObligation",
    "DeployerObligation",

    # Rights
    "FundamentalRight",
    "ImpactLevel",

    # Stores
    "RiskClassificationStore",
    "ProhibitedPracticesStore",
    "HighRiskRequirementsStore",
    "ConformityAssessmentStore",
    "TechnicalDocumentationStore",
    "DataGovernanceStore",
    "HumanOversightStore",
    "TransparencyStore",
    "PostMarketMonitoringStore",
    "IncidentReportingStore",
    "GPAIGovernanceStore",
]
