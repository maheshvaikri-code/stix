"""
Agent Integration Store
=======================

Integrates agent actions with PII and regulatory compliance.
"""

from typing import Any, Dict, List, Optional, Set

from .base import BaseUnifiedStore
from ..schema import (
    GovernanceDomain,
    ComplianceStatus,
    CrossDomainRiskLevel,
    IntegrationEventType,
    AGENT_ACTION_REGULATION_MAP,
)


class AgentIntegrationStore(BaseUnifiedStore):
    """
    Store for integrating agent governance with PII and regulation compliance.

    Provides:
    - Agent action to PII type mapping
    - Pre-action compliance checking
    - Agent-PII audit trail
    - Regulatory blocking for agent actions
    """

    def __init__(self, graph):
        super().__init__(graph, "agent_integration")

    # =========================================================================
    # Agent-PII Mapping
    # =========================================================================

    def register_agent_pii_access(
        self,
        agent_id: str,
        pii_types: List[str],
        purpose: str,
        legal_basis: str = "",
        consent_verified: bool = False,
        expires_at: str = "",
    ) -> str:
        """Register an agent's access to specific PII types."""
        access_id = self._generate_id("agent_pii_access")

        # Determine applicable regulations
        applicable_regulations = set()
        for pii_type in pii_types:
            # Check built-in mappings
            from ..schema import PII_REGULATION_REQUIREMENTS
            if pii_type in PII_REGULATION_REQUIREMENTS:
                applicable_regulations.update(PII_REGULATION_REQUIREMENTS[pii_type].keys())

        self._add_node("agent_pii_access", access_id, {
            "agent_id": agent_id,
            "pii_types": pii_types,
            "purpose": purpose,
            "legal_basis": legal_basis,
            "consent_verified": consent_verified,
            "expires_at": expires_at,
            "applicable_regulations": list(applicable_regulations),
            "status": "active",
        })

        self._add_edge(
            "agent_pii_access", access_id,
            "ACCESS_FOR",
            "principal", agent_id,
            {}
        )

        return access_id

    def check_agent_pii_access(
        self,
        agent_id: str,
        pii_type: str,
    ) -> Dict[str, Any]:
        """Check if an agent has access to a specific PII type."""
        accesses = self._find_nodes("agent_pii_access", agent_id=agent_id, status="active")

        for access in accesses:
            if pii_type in access.get("pii_types", []):
                # Check expiration
                expires_at = access.get("expires_at")
                if expires_at and expires_at < self._now():
                    continue

                return {
                    "has_access": True,
                    "access_id": access.get("id"),
                    "purpose": access.get("purpose"),
                    "legal_basis": access.get("legal_basis"),
                    "consent_verified": access.get("consent_verified"),
                }

        return {
            "has_access": False,
            "reason": f"No active access registered for agent '{agent_id}' to PII type '{pii_type}'",
        }

    # =========================================================================
    # Pre-Action Compliance Check
    # =========================================================================

    def check_action_compliance(
        self,
        agent_id: str,
        action: str,
        pii_types_involved: List[str],
        data_subject_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Check if an agent action is compliant with all applicable regulations.

        Returns a comprehensive compliance check result.
        """
        check_id = self._generate_id("action_check")
        issues = []
        blocking_issues = []
        warnings = []

        # Get affected regulations for this action
        affected_regulations = AGENT_ACTION_REGULATION_MAP.get(action, set())

        # Add regulations for PII types
        from ..schema import PII_REGULATION_REQUIREMENTS
        for pii_type in pii_types_involved:
            if pii_type in PII_REGULATION_REQUIREMENTS:
                for reg in PII_REGULATION_REQUIREMENTS[pii_type].keys():
                    if reg == "gdpr":
                        affected_regulations.add(GovernanceDomain.GDPR)
                    elif reg == "ccpa":
                        affected_regulations.add(GovernanceDomain.CCPA)
                    elif reg == "hipaa":
                        affected_regulations.add(GovernanceDomain.HIPAA)
                    elif reg == "pci_dss":
                        affected_regulations.add(GovernanceDomain.PCI_DSS)

        # Check PII access
        for pii_type in pii_types_involved:
            access_check = self.check_agent_pii_access(agent_id, pii_type)
            if not access_check.get("has_access"):
                blocking_issues.append({
                    "domain": "pii",
                    "issue": f"No registered access to PII type '{pii_type}'",
                    "action_required": "Register agent PII access",
                })

        # Check consent if data subject is specified
        if data_subject_id and GovernanceDomain.GDPR in affected_regulations:
            warnings.append({
                "domain": "gdpr",
                "issue": "Verify consent status for data subject",
                "data_subject_id": data_subject_id,
            })

        # Check CCPA opt-out
        if data_subject_id and GovernanceDomain.CCPA in affected_regulations:
            if action in ["share_with_third_party", "transfer_data_external"]:
                warnings.append({
                    "domain": "ccpa",
                    "issue": "Verify consumer has not opted out of sharing",
                    "data_subject_id": data_subject_id,
                })

        # Determine overall status
        if blocking_issues:
            status = ComplianceStatus.NON_COMPLIANT
            permitted = False
        elif warnings:
            status = ComplianceStatus.PARTIAL
            permitted = True  # Permitted with warnings
        else:
            status = ComplianceStatus.COMPLIANT
            permitted = True

        # Calculate risk level
        risk_level = self._calculate_action_risk(
            action, pii_types_involved, len(blocking_issues), len(warnings)
        )

        result = {
            "check_id": check_id,
            "agent_id": agent_id,
            "action": action,
            "pii_types_involved": pii_types_involved,
            "affected_regulations": [r.value for r in affected_regulations],
            "permitted": permitted,
            "status": status.value,
            "blocking_issues": blocking_issues,
            "warnings": warnings,
            "risk_level": risk_level,
            "timestamp": self._now(),
        }

        # Record check
        self._add_node("agent_action_check", check_id, result)

        return result

    def _calculate_action_risk(
        self,
        action: str,
        pii_types: List[str],
        blocking_count: int,
        warning_count: int,
    ) -> str:
        """Calculate risk level for an agent action."""
        high_risk_actions = [
            "write_personal_data",
            "transfer_data_external",
            "share_with_third_party",
            "automated_decision",
            "profiling",
        ]

        sensitive_pii = ["ssn", "health_record", "credit_card", "biometric", "genetic"]

        base_score = 0

        # Action risk
        if action in high_risk_actions:
            base_score += 3

        # PII sensitivity
        for pii in pii_types:
            if pii in sensitive_pii:
                base_score += 2
            else:
                base_score += 1

        # Issues
        base_score += blocking_count * 3
        base_score += warning_count * 1

        if base_score >= 10:
            return CrossDomainRiskLevel.CRITICAL.value
        elif base_score >= 7:
            return CrossDomainRiskLevel.HIGH.value
        elif base_score >= 4:
            return CrossDomainRiskLevel.MEDIUM.value
        elif base_score >= 2:
            return CrossDomainRiskLevel.LOW.value
        else:
            return CrossDomainRiskLevel.MINIMAL.value

    # =========================================================================
    # Agent Action Audit
    # =========================================================================

    def record_agent_pii_action(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_source: str,
        outcome: str,
        compliance_check_id: Optional[str] = None,
        data_subject_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record an agent action involving PII for audit purposes."""
        audit_id = self._generate_id("agent_pii_audit")

        self._add_node("agent_pii_audit", audit_id, {
            "agent_id": agent_id,
            "action": action,
            "pii_types": pii_types,
            "data_source": data_source,
            "outcome": outcome,
            "compliance_check_id": compliance_check_id,
            "data_subject_id": data_subject_id,
            "details": details or {},
        })

        # Link to agent
        self._add_edge(
            "agent_pii_audit", audit_id,
            "ACTION_BY",
            "principal", agent_id,
            {}
        )

        # Link to compliance check if exists
        if compliance_check_id:
            self._add_edge(
                "agent_pii_audit", audit_id,
                "CHECKED_BY",
                "agent_action_check", compliance_check_id,
                {}
            )

        return audit_id

    def get_agent_pii_audit_trail(
        self,
        agent_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get PII-related audit trail for an agent."""
        audits = self._find_nodes("agent_pii_audit", agent_id=agent_id)

        # Sort by timestamp descending
        audits.sort(key=lambda x: x.get("_created_at", ""), reverse=True)

        return audits[:limit]

    def get_pii_access_audit(
        self,
        pii_type: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get all agent actions involving a specific PII type."""
        all_audits = self._find_nodes("agent_pii_audit")

        relevant = [
            a for a in all_audits
            if pii_type in a.get("pii_types", [])
        ]

        relevant.sort(key=lambda x: x.get("_created_at", ""), reverse=True)

        return relevant[:limit]

    # =========================================================================
    # Regulatory Blocking
    # =========================================================================

    def block_agent_action(
        self,
        agent_id: str,
        action: str,
        reason: str,
        regulation: str,
        blocked_by: str = "system",
        until: str = "",
    ) -> str:
        """Block an agent from performing a specific action."""
        block_id = self._generate_id("agent_block")

        self._add_node("agent_action_block", block_id, {
            "agent_id": agent_id,
            "action": action,
            "reason": reason,
            "regulation": regulation,
            "blocked_by": blocked_by,
            "until": until,
            "status": "active",
        })

        self._add_edge(
            "agent_action_block", block_id,
            "BLOCKS",
            "principal", agent_id,
            {"action": action}
        )

        return block_id

    def is_action_blocked(
        self,
        agent_id: str,
        action: str,
    ) -> Dict[str, Any]:
        """Check if an action is blocked for an agent."""
        blocks = self._find_nodes(
            "agent_action_block",
            agent_id=agent_id,
            action=action,
            status="active"
        )

        # Filter expired blocks
        active_blocks = []
        for block in blocks:
            until = block.get("until")
            if until and until < self._now():
                continue
            active_blocks.append(block)

        if active_blocks:
            return {
                "blocked": True,
                "blocks": [
                    {
                        "block_id": b.get("id"),
                        "reason": b.get("reason"),
                        "regulation": b.get("regulation"),
                        "until": b.get("until"),
                    }
                    for b in active_blocks
                ],
            }

        return {"blocked": False}

    def remove_block(self, block_id: str, removed_by: str) -> Dict[str, Any]:
        """Remove an action block."""
        block = self._get_node("agent_action_block", block_id)
        if not block:
            return {"error": "Block not found"}

        self._update_node("agent_action_block", block_id, {
            "status": "removed",
            "removed_by": removed_by,
            "removed_at": self._now(),
        })

        return {"removed": True, "block_id": block_id}

    # =========================================================================
    # Cross-Domain Event Triggering
    # =========================================================================

    def trigger_compliance_event(
        self,
        event_type: IntegrationEventType,
        agent_id: str,
        action: str,
        affected_domains: List[GovernanceDomain],
        description: str,
        triggered_actions: Optional[List[str]] = None,
    ) -> str:
        """Trigger a cross-domain compliance event from an agent action."""
        event_id = self._generate_id("agent_event")

        self._add_node("agent_compliance_event", event_id, {
            "event_type": event_type.value if isinstance(event_type, IntegrationEventType) else event_type,
            "agent_id": agent_id,
            "action": action,
            "affected_domains": [d.value if isinstance(d, GovernanceDomain) else d for d in affected_domains],
            "description": description,
            "triggered_actions": triggered_actions or [],
            "status": "triggered",
        })

        return event_id

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get agent integration statistics."""
        accesses = self._find_nodes("agent_pii_access")
        checks = self._find_nodes("agent_action_check")
        audits = self._find_nodes("agent_pii_audit")
        blocks = self._find_nodes("agent_action_block", status="active")
        events = self._find_nodes("agent_compliance_event")

        # Count checks by status
        check_status = {}
        for check in checks:
            status = check.get("status", "unknown")
            check_status[status] = check_status.get(status, 0) + 1

        # Count by risk level
        risk_breakdown = {}
        for check in checks:
            risk = check.get("risk_level", "unknown")
            risk_breakdown[risk] = risk_breakdown.get(risk, 0) + 1

        # Count blocked actions
        blocked_actions = {}
        for block in blocks:
            action = block.get("action", "unknown")
            blocked_actions[action] = blocked_actions.get(action, 0) + 1

        return {
            "total_pii_access_grants": len(accesses),
            "active_pii_access_grants": len([a for a in accesses if a.get("status") == "active"]),
            "total_action_checks": len(checks),
            "check_status_breakdown": check_status,
            "risk_level_breakdown": risk_breakdown,
            "total_audit_records": len(audits),
            "active_blocks": len(blocks),
            "blocked_actions": blocked_actions,
            "total_compliance_events": len(events),
        }
