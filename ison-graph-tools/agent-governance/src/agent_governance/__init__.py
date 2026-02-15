"""
Agent Governance - Comprehensive Governance Layer for AI Agents
===============================================================

This library provides a complete governance framework for AI agents,
enabling authority control, policy enforcement, compliance tracking,
risk management, and ethical alignment.

15 Governance Domains:
    1. Authority & Delegation: Who can authorize what
    2. Policy Engine: Rules, conditions, and evaluation
    3. Compliance Framework: GDPR, HIPAA, SOX, EU AI Act mapping
    4. Audit Trail: Decision provenance and accountability
    5. Risk Assessment: Threats, controls, and mitigation
    6. Human Oversight: Escalation and review workflows
    7. Resource Governance: Budgets and allocation
    8. Multi-Agent Coordination: Group governance protocols
    9. Ethics & Values: Value alignment and dilemmas
    10. Capability Governance: Feature flags and grants
    11. Incident Response: Detection and recovery
    12. Meta-Governance: Governing the governance
    13. Cross-Organizational: Trust and agreements
    14. Temporal Governance: Time-bound authority
    15. Observability: Metrics and dashboards

Usage:
    from agent_governance import GovernanceEngine, quick_governance

    # Quick setup with defaults
    engine = quick_governance("my-project")

    # Check if an action is permitted
    result = engine.check_action(
        agent_id="agent_1",
        action="write_external",
        context={"data_classification": "internal"}
    )

    if result["permitted"]:
        # Proceed with action
        pass
    elif result["escalation_required"]:
        # Wait for human approval
        pass
    else:
        # Action denied
        print(result["reason"])

Author: Mahesh Vaikri
"""

__version__ = "1.0.0"

from .engine import GovernanceEngine, quick_governance
from .stores import (
    AuthorityStore,
    PolicyStore,
    ComplianceStore,
    AuditStore,
    RiskStore,
    EscalationStore,
    ResourceStore,
    CoordinationStore,
    EthicsStore,
    CapabilityStore,
    IncidentStore,
    MetaGovernanceStore,
    CrossOrgStore,
    TemporalStore,
    ObservabilityStore,
)
from .schema import (
    # Enums
    AuthorityLevel,
    RiskLevel,
    Enforcement,
    PolicyStatus,
    IncidentSeverity,
    IncidentStatus,
    EscalationLevel,
    TrustLevel,
    CapabilityMaturity,
    ControlType,
    ValuePriority,
    GovernanceDomain,
    # Core types
    Principal,
    AuthorityScope,
    Delegation,
    Policy,
    Rule,
    ComplianceFramework,
    ComplianceRequirement,
    Decision,
    Risk,
    Threat,
    Value,
    EthicalPrinciple,
    Capability,
    Incident,
)

__all__ = [
    "__version__",
    # Main classes
    "GovernanceEngine",
    "quick_governance",
    # Stores
    "AuthorityStore",
    "PolicyStore",
    "ComplianceStore",
    "AuditStore",
    "RiskStore",
    "EscalationStore",
    "ResourceStore",
    "CoordinationStore",
    "EthicsStore",
    "CapabilityStore",
    "IncidentStore",
    "MetaGovernanceStore",
    "CrossOrgStore",
    "TemporalStore",
    "ObservabilityStore",
    # Enums
    "AuthorityLevel",
    "RiskLevel",
    "Enforcement",
    "PolicyStatus",
    "IncidentSeverity",
    "IncidentStatus",
    "EscalationLevel",
    "TrustLevel",
    "CapabilityMaturity",
    "ControlType",
    "ValuePriority",
    "GovernanceDomain",
    # Types
    "Principal",
    "AuthorityScope",
    "Delegation",
    "Policy",
    "Rule",
    "ComplianceFramework",
    "ComplianceRequirement",
    "Decision",
    "Risk",
    "Threat",
    "Value",
    "EthicalPrinciple",
    "Capability",
    "Incident",
]
