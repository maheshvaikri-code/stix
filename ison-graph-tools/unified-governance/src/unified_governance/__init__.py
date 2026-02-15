"""
Unified Governance for ISONGraph
================================

Integrates Agent, GDPR, CCPA, and PII governance into a unified framework.

This package provides:
- Cross-domain compliance checking
- PII to regulation mapping
- Subject unification (GDPR data subjects + CCPA consumers)
- Agent-PII access control
- Unified audit trails
- Cross-regulation risk assessment

Usage:
    from ison_graph import ISONGraph
    from unified_governance import UnifiedGovernanceEngine

    # Create unified governance
    engine = UnifiedGovernanceEngine()

    # Or use quick setup
    from unified_governance import quick_unified_governance
    engine = quick_unified_governance(setup_defaults=True)

    # Register a unified subject
    engine.register_subject(
        subject_id="user_123",
        email="user@example.com",
        gdpr_data_subject_id="gdpr_ds_123",
        ccpa_consumer_id="ccpa_c_123",
    )

    # Grant agent PII access
    engine.grant_agent_pii_access(
        agent_id="agent_1",
        pii_types=["email", "phone"],
        purpose="customer_support",
        legal_basis="legitimate_interest",
    )

    # Check compliance before action
    result = engine.check_compliance(
        agent_id="agent_1",
        action="read_personal_data",
        pii_types=["email"],
        data_subject_id="user_123",
    )

    if result["permitted"]:
        # Perform action
        engine.record_agent_action(
            agent_id="agent_1",
            action="read_personal_data",
            pii_types=["email"],
            data_source="customer_db",
            outcome="success",
        )
"""

from .schema import (
    # Domains
    GovernanceDomain,
    # Status
    ComplianceStatus,
    CrossDomainRiskLevel,
    # Events
    IntegrationEventType,
    DataProcessingContext,
    # Jurisdiction
    RegulationJurisdiction,
    # Mappings
    PII_REGULATION_REQUIREMENTS,
    AGENT_ACTION_REGULATION_MAP,
    # Data classes
    RegulatoryBinding,
    CrossDomainEvent,
    UnifiedComplianceCheck,
    DataFlowCompliance,
    UnifiedDataSubject,
    IntegratedRiskProfile,
    GovernancePolicy,
    # Edge types
    UNIFIED_EDGE_TYPES,
)

from .stores import (
    BaseUnifiedStore,
    RegulatoryBridgeStore,
    PIIComplianceStore,
    SubjectUnificationStore,
    AgentIntegrationStore,
)

from .engine import (
    UnifiedGovernanceEngine,
    quick_unified_governance,
)

from .memory_integration import (
    GovernanceMemoryStore,
    CachedGovernanceContext,
    GovernanceSessionManager,
    ComplianceDecisionMemory,
    GovernancePattern,
    GovernanceSession,
)

from .governed_cache import (
    GovernedCacheStore,
    CacheAccessLevel,
    CacheDataSensitivity,
    RetentionPolicy,
    CacheOperation,
    CacheAccessGrant,
    CacheAuditEntry,
    GovernedCacheEntry,
)

__version__ = "0.1.0"

__all__ = [
    # Main engine
    "UnifiedGovernanceEngine",
    "quick_unified_governance",
    # Stores
    "BaseUnifiedStore",
    "RegulatoryBridgeStore",
    "PIIComplianceStore",
    "SubjectUnificationStore",
    "AgentIntegrationStore",
    # Enums - Domains
    "GovernanceDomain",
    # Enums - Status
    "ComplianceStatus",
    "CrossDomainRiskLevel",
    # Enums - Events
    "IntegrationEventType",
    "DataProcessingContext",
    # Enums - Jurisdiction
    "RegulationJurisdiction",
    # Mappings
    "PII_REGULATION_REQUIREMENTS",
    "AGENT_ACTION_REGULATION_MAP",
    # Data classes
    "RegulatoryBinding",
    "CrossDomainEvent",
    "UnifiedComplianceCheck",
    "DataFlowCompliance",
    "UnifiedDataSubject",
    "IntegratedRiskProfile",
    "GovernancePolicy",
    # Edge types
    "UNIFIED_EDGE_TYPES",
    # Memory integration
    "GovernanceMemoryStore",
    "CachedGovernanceContext",
    "GovernanceSessionManager",
    "ComplianceDecisionMemory",
    "GovernancePattern",
    "GovernanceSession",
    # Governed cache
    "GovernedCacheStore",
    "CacheAccessLevel",
    "CacheDataSensitivity",
    "RetentionPolicy",
    "CacheOperation",
    "CacheAccessGrant",
    "CacheAuditEntry",
    "GovernedCacheEntry",
]
