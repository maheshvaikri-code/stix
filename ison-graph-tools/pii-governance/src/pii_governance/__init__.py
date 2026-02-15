"""
PII Governance for ISONGraph
============================

Comprehensive PII detection, classification, and governance using ISONGraph.

This package provides tools for:
- PII detection and classification (regex, column name inference)
- Sensitivity level mapping
- Data source inventory management
- Risk assessment and scoring
- Compliance gap analysis
- Data lineage and flow tracking
- Cross-regulation mapping (GDPR, CCPA, HIPAA, PCI-DSS, etc.)

Usage:
    from ison_graph import ISONGraph
    from pii_governance import PIIGovernance

    graph = ISONGraph()
    pii = PIIGovernance(graph)

    # Register a data source
    pii.inventory.register_data_source(
        source_id="customer_db",
        name="Customer Database",
        source_type=DataSourceType.DATABASE,
        storage_location=StorageLocation.ON_PREMISE,
        owner="data_team",
    )

    # Classify PII fields
    pii.classification.classify_field(
        field_name="email",
        field_id="customers.email",
        source_id="customer_db",
        sample_values=["user@example.com", "test@test.com"],
    )

    # Scan text for PII
    detections = pii.scan_text_for_pii("Contact: john@email.com, SSN: 123-45-6789")

    # Get governance report
    report = pii.get_governance_report()
"""

from .schema import (
    # PII Categories and Types
    PIICategory,
    PIIType,
    # Sensitivity
    SensitivityLevel,
    RiskLevel,
    # Regulations
    Regulation,
    RegulationCategory,
    # Data Sources
    DataSourceType,
    StorageLocation,
    # Detection
    DetectionMethod,
    DetectionConfidence,
    # Protection
    ProtectionStatus,
    AccessControl,
    # Lifecycle
    DataLifecycleStage,
    RetentionStatus,
    # Mappings
    PII_REGULATION_MAP,
    PII_SENSITIVITY_MAP,
    # Data classes
    PIIField,
    DataSource,
    PIIInventoryItem,
    RiskAssessment,
    DataLineage,
)

from .stores import (
    BasePIIStore,
    ClassificationStore,
    InventoryStore,
    RiskAssessmentStore,
    LineageStore,
)

from .engine import PIIGovernance

__version__ = "0.1.0"

__all__ = [
    # Main engine
    "PIIGovernance",
    # Stores
    "BasePIIStore",
    "ClassificationStore",
    "InventoryStore",
    "RiskAssessmentStore",
    "LineageStore",
    # Enums - PII
    "PIICategory",
    "PIIType",
    # Enums - Sensitivity
    "SensitivityLevel",
    "RiskLevel",
    # Enums - Regulations
    "Regulation",
    "RegulationCategory",
    # Enums - Data Sources
    "DataSourceType",
    "StorageLocation",
    # Enums - Detection
    "DetectionMethod",
    "DetectionConfidence",
    # Enums - Protection
    "ProtectionStatus",
    "AccessControl",
    # Enums - Lifecycle
    "DataLifecycleStage",
    "RetentionStatus",
    # Mappings
    "PII_REGULATION_MAP",
    "PII_SENSITIVITY_MAP",
    # Data classes
    "PIIField",
    "DataSource",
    "PIIInventoryItem",
    "RiskAssessment",
    "DataLineage",
]
