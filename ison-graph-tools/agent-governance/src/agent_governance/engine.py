"""
Governance Engine
=================

Main orchestration class that coordinates all governance stores and
provides unified governance operations.
"""

import os
from typing import Any, Dict, List, Optional

from ison_graph import ISONGraph

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
    RollbackStore,
)
from .schema import (
    AuthorityLevel,
    RiskLevel,
    PolicyStatus,
    IncidentSeverity,
    EscalationLevel,
    TrustLevel,
    CapabilityMaturity,
    ValuePriority,
    RollbackType,
    RollbackTrigger,
    RollbackStatus,
    SnapshotType,
)


class GovernanceEngine:
    """
    Main governance engine coordinating all governance domains.

    Usage:
        from agent_governance import GovernanceEngine

        # Initialize governance for a project
        engine = GovernanceEngine("my-project")

        # Check if an action is permitted
        result = engine.check_action(
            agent_id="agent_1",
            action="write_external",
            context={"data": "...", "destination": "api"}
        )

        # Save governance state
        engine.save("governance.ison")
    """

    def __init__(self, name: str, path: Optional[str] = None):
        """
        Initialize the governance engine.

        Args:
            name: Name of the governance context
            path: Optional path for persistence
        """
        self.name = name
        self.path = path or os.path.join(os.getcwd(), f".{name}-governance")
        self.graph = ISONGraph(name=f"{name}-governance")

        # Initialize all stores
        self.authority = AuthorityStore(self.graph)
        self.policy = PolicyStore(self.graph)
        self.compliance = ComplianceStore(self.graph)
        self.audit = AuditStore(self.graph)
        self.risk = RiskStore(self.graph)
        self.escalation = EscalationStore(self.graph)
        self.resource = ResourceStore(self.graph)
        self.coordination = CoordinationStore(self.graph)
        self.ethics = EthicsStore(self.graph)
        self.capability = CapabilityStore(self.graph)
        self.incident = IncidentStore(self.graph)
        self.meta = MetaGovernanceStore(self.graph)
        self.crossorg = CrossOrgStore(self.graph)
        self.temporal = TemporalStore(self.graph)
        self.observability = ObservabilityStore(self.graph)
        self.rollback = RollbackStore(self.graph)

    # =========================================================================
    # Core Governance Operations
    # =========================================================================

    def check_action(
        self,
        agent_id: str,
        action: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Comprehensive check if an agent can perform an action.

        This is the main entry point for governance checks.

        Returns:
            {
                "permitted": bool,
                "reason": str,
                "checks_passed": List[str],
                "checks_failed": List[str],
                "escalation_required": bool,
                "escalation_level": Optional[str]
            }
        """
        ctx = context or {}
        checks_passed = []
        checks_failed = []
        escalation_required = False
        escalation_level = None

        # 1. Check authority
        auth_check = self.authority.check_permission(agent_id, action, ctx)
        if auth_check["permitted"]:
            checks_passed.append("authority")
        else:
            checks_failed.append(f"authority: {auth_check['reason']}")

        # 2. Check capability
        cap_check = self.capability.check_capability(agent_id, action, ctx)
        if cap_check.get("has_capability"):
            checks_passed.append("capability")
        else:
            checks_failed.append(f"capability: {cap_check.get('reason', 'No capability')}")

        # 3. Evaluate policies
        policy_result = self.policy.evaluate(ctx)
        if policy_result["result"] == "allow":
            checks_passed.append("policy")
        elif policy_result["result"] == "escalate":
            checks_passed.append("policy (needs escalation)")
            escalation_required = True
            escalation_level = EscalationLevel.L3_OPERATOR.value
        else:
            checks_failed.append(f"policy: {policy_result['explanation']}")

        # 4. Check resource budget
        if "resource_type" in ctx and "amount" in ctx:
            budgets = self.resource.list_budgets(owner=agent_id)
            if budgets:
                budget_status = self.resource.get_budget_status(budgets[0]["id"])
                if not budget_status.get("exhausted"):
                    checks_passed.append("resource")
                else:
                    checks_failed.append("resource: budget exhausted")

        # 5. Check ethics/values
        if "values_context" in ctx:
            alignment = self.ethics.calculate_alignment_score(agent_id)
            if alignment.get("overall_score", 1.0) >= 0.7:
                checks_passed.append("ethics")
            else:
                checks_failed.append("ethics: low alignment score")
                escalation_required = True
                escalation_level = EscalationLevel.L4_MANAGER.value

        # 6. Check coordination (if in a group)
        roles = self.coordination.get_agent_roles(agent_id)
        if roles:
            for role in roles:
                coord_check = self.coordination.check_coordination_authority(
                    agent_id, role.get("group_id"), action
                )
                if coord_check.get("authorized"):
                    checks_passed.append("coordination")
                    break
            else:
                checks_failed.append("coordination: not authorized in any group")

        # Determine final result
        critical_failures = [f for f in checks_failed if "authority" in f or "capability" in f]
        permitted = len(critical_failures) == 0 and len(checks_passed) > 0

        # Record the decision
        decision_id = self.audit.record_decision(
            agent_id=agent_id,
            decision_type="action_check",
            outcome="permitted" if permitted else "denied",
            confidence=len(checks_passed) / (len(checks_passed) + len(checks_failed)) if checks_passed or checks_failed else 1.0,
            metadata={
                "action": action,
                "context": ctx,
                "checks_passed": checks_passed,
                "checks_failed": checks_failed
            }
        )

        # Add rationale
        self.audit.add_rationale(
            decision_id,
            "governance_check",
            f"Passed: {checks_passed}. Failed: {checks_failed}"
        )

        return {
            "permitted": permitted,
            "reason": "All checks passed" if permitted else "; ".join(checks_failed),
            "checks_passed": checks_passed,
            "checks_failed": checks_failed,
            "escalation_required": escalation_required,
            "escalation_level": escalation_level,
            "decision_id": decision_id
        }

    def request_action(
        self,
        agent_id: str,
        action: str,
        reason: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Request permission for an action (may trigger escalation).

        Use this when an agent wants to perform an action that may need approval.
        """
        check = self.check_action(agent_id, action, context)

        if check["permitted"]:
            return {
                "status": "approved",
                "message": "Action permitted",
                **check
            }

        if check["escalation_required"]:
            # Create escalation
            escalation_ids = self.escalation.trigger_escalation({
                "agent_id": agent_id,
                "action": action,
                "reason": reason,
                **(context or {})
            })

            return {
                "status": "pending_approval",
                "message": "Action requires human approval",
                "escalation_ids": escalation_ids,
                **check
            }

        return {
            "status": "denied",
            "message": check["reason"],
            **check
        }

    # =========================================================================
    # Principal & Authority Setup
    # =========================================================================

    def register_agent(
        self,
        agent_id: str,
        name: str,
        authority_level: AuthorityLevel = AuthorityLevel.LIMITED,
        capabilities: Optional[List[str]] = None
    ) -> str:
        """Register a new agent in the governance system"""
        # Add as principal
        self.authority.add_principal(
            "agent", name, authority_level, principal_id=agent_id
        )

        # Grant default capabilities
        if capabilities:
            for cap_name in capabilities:
                caps = self.capability._find_nodes("capability", name=cap_name)
                if caps:
                    self.capability.grant_capability(
                        caps[0]["id"],
                        agent_id,
                        "system",
                        "default_grant"
                    )

        return agent_id

    def register_human(
        self,
        human_id: str,
        name: str,
        authority_level: AuthorityLevel = AuthorityLevel.ELEVATED,
        expertise: Optional[List[str]] = None
    ) -> str:
        """Register a human principal"""
        self.authority.add_principal(
            "human", name, authority_level, principal_id=human_id
        )

        # Add as potential reviewer
        if expertise:
            self.escalation.add_reviewer(
                name, expertise, "business", reviewer_id=human_id
            )

        return human_id

    # =========================================================================
    # Policy Management
    # =========================================================================

    def add_policy(
        self,
        name: str,
        rules: List[Dict[str, str]],
        priority: int = 50
    ) -> str:
        """Add a governance policy with rules"""
        policy_id = self.policy.add_policy(name, priority)

        for rule in rules:
            self.policy.add_rule(
                policy_id,
                rule.get("condition", "True"),
                rule.get("action", "allow"),
                rule.get("exception"),
                rule.get("priority", 0),
                rule.get("description", "")
            )

        return policy_id

    # =========================================================================
    # Risk Management
    # =========================================================================

    def assess_risk_posture(self) -> Dict[str, Any]:
        """Get comprehensive risk posture"""
        return self.risk.get_risk_posture()

    def report_incident(
        self,
        severity: IncidentSeverity,
        category: str,
        description: str
    ) -> str:
        """Report a governance incident"""
        incident_id = self.incident.create_incident(severity, category, description)

        # Auto-escalate for critical incidents
        if severity == IncidentSeverity.CRITICAL:
            self.escalation.trigger_escalation({
                "incident_id": incident_id,
                "severity": severity.value,
                "category": category
            })

        return incident_id

    # =========================================================================
    # Compliance
    # =========================================================================

    def check_compliance(self, behavior_id: str) -> Dict[str, Any]:
        """Check compliance for a behavior"""
        return self.compliance.assess_behavior_compliance(behavior_id)

    def add_compliance_framework(
        self,
        name: str,
        jurisdiction: str,
        requirements: List[Dict[str, str]]
    ) -> str:
        """Add a compliance framework with requirements"""
        framework_id = self.compliance.add_framework(
            name, jurisdiction, "2024-01-01", "ai_systems"
        )

        for req in requirements:
            self.compliance.add_requirement(
                framework_id,
                req.get("article", ""),
                req.get("description", ""),
                req.get("risk", "fine")
            )

        return framework_id

    # =========================================================================
    # Health & Observability
    # =========================================================================

    def get_health(self) -> Dict[str, Any]:
        """Get overall governance health"""
        return self.observability.calculate_health_score()

    def get_governance_summary(self) -> Dict[str, Any]:
        """Get comprehensive governance summary"""
        return {
            "name": self.name,
            "health": self.get_health(),
            "risk_posture": self.assess_risk_posture(),
            "active_incidents": len(self.incident.list_incidents(IncidentSeverity.CRITICAL)),
            "pending_escalations": len(self.escalation.list_escalations(status="pending")),
            "compliance_gaps": len(self.compliance.get_gaps(status="open")),
            "stats": self.get_stats()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics from all stores"""
        return {
            "authority": self.authority.get_stats(),
            "policy": self.policy.get_stats(),
            "compliance": self.compliance.get_stats(),
            "audit": self.audit.get_stats(),
            "risk": self.risk.get_stats(),
            "escalation": self.escalation.get_stats(),
            "resource": self.resource.get_stats(),
            "coordination": self.coordination.get_stats(),
            "ethics": self.ethics.get_stats(),
            "capability": self.capability.get_stats(),
            "incident": self.incident.get_stats(),
            "meta": self.meta.get_stats(),
            "crossorg": self.crossorg.get_stats(),
            "temporal": self.temporal.get_stats(),
            "observability": self.observability.get_stats(),
            "rollback": self.rollback.get_stats(),
        }

    # =========================================================================
    # Rollback & Transaction Support
    # =========================================================================

    def begin_transaction(
        self,
        name: str,
        agent_id: str,
        action_type: str,
        auto_snapshot: bool = True
    ) -> str:
        """
        Begin a transaction boundary for rollback support.

        Args:
            name: Name of the transaction
            agent_id: Agent performing the action
            action_type: Type of action being performed
            auto_snapshot: Whether to create automatic snapshots

        Returns:
            Transaction boundary ID
        """
        return self.rollback.begin_transaction(
            agent_id=agent_id,
            name=name,
            description=action_type  # Use action_type as description
        )

    def commit_transaction(self, transaction_id: str, success: bool = True) -> Dict[str, Any]:
        """Commit or fail a transaction"""
        return self.rollback.commit_transaction(transaction_id)

    def create_snapshot(
        self,
        action_id: str,
        action_type: str,
        agent_id: str,
        state_before: Dict[str, Any],
        snapshot_type: SnapshotType = SnapshotType.FULL,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ) -> str:
        """
        Create a state snapshot before an action.

        Args:
            action_id: Unique ID for the action
            action_type: Type of action being performed
            agent_id: Agent performing the action
            state_before: State to snapshot
            snapshot_type: Type of snapshot
            resource_type: Optional resource type
            resource_id: Optional resource ID

        Returns:
            Snapshot ID
        """
        affected = []
        if resource_type and resource_id:
            affected = [f"{resource_type}:{resource_id}"]
        return self.rollback.create_snapshot(
            action_id=action_id,
            agent_id=agent_id,
            state_data=state_before,
            affected_resources=affected,
            snapshot_type=snapshot_type
        )

    def record_action_result(
        self,
        snapshot_id: str,
        state_after: Dict[str, Any],
        success: bool = True
    ) -> Dict[str, Any]:
        """Record the result of an action for potential rollback"""
        return self.rollback.record_action_result(snapshot_id, state_after, success)

    def initiate_rollback(
        self,
        transaction_id: str,
        rollback_type: RollbackType,
        trigger: RollbackTrigger,
        reason: str = "",
        triggered_by: str = "",
        target_checkpoint: Optional[str] = None
    ) -> str:
        """
        Initiate a rollback operation.

        Args:
            transaction_id: ID of the transaction to rollback
            rollback_type: Type of rollback
            trigger: What triggered the rollback
            reason: Why the rollback is needed
            triggered_by: Who triggered the rollback
            target_checkpoint: Optional checkpoint to rollback to

        Returns:
            Rollback operation ID
        """
        return self.rollback.initiate_rollback(
            transaction_id=transaction_id,
            rollback_type=rollback_type,
            trigger=trigger,
            triggered_by=triggered_by,
            target_checkpoint=target_checkpoint,
            reason=reason
        )

    def execute_rollback(self, rollback_id: str, executor_id: str = "system") -> Dict[str, Any]:
        """Execute a pending rollback operation"""
        return self.rollback.execute_rollback(rollback_id, executor_id=executor_id)

    def create_checkpoint(
        self,
        transaction_id: str,
        name: str,
        snapshot_id: str,
        step_number: Optional[int] = None
    ) -> str:
        """
        Create a named checkpoint for multi-step operations.

        Args:
            transaction_id: Transaction to create checkpoint in
            name: Checkpoint name
            snapshot_id: Snapshot to associate with checkpoint
            step_number: Optional step number

        Returns:
            Checkpoint ID
        """
        return self.rollback.create_checkpoint(
            transaction_id=transaction_id,
            name=name,
            snapshot_id=snapshot_id,
            step_number=step_number
        )

    def rollback_to_checkpoint(
        self,
        transaction_id: str,
        checkpoint_id: str,
        reason: str,
        triggered_by: str
    ) -> Dict[str, Any]:
        """Rollback to a specific checkpoint"""
        rollback_id = self.initiate_rollback(
            transaction_id=transaction_id,
            rollback_type=RollbackType.CHECKPOINT,
            trigger=RollbackTrigger.MANUAL,
            reason=reason,
            triggered_by=triggered_by,
            target_checkpoint=checkpoint_id
        )
        return self.execute_rollback(rollback_id, executor_id=triggered_by)

    def add_rollback_policy(
        self,
        name: str,
        condition: str,
        action_types: List[str],
        auto_rollback: bool = False,
        max_rollback_age_hours: int = 24,
        priority: int = 50
    ) -> str:
        """
        Add an automatic rollback policy.

        Args:
            name: Policy name
            condition: Condition expression for triggering
            action_types: Action types this policy applies to
            auto_rollback: Whether to auto-execute rollback
            max_rollback_age_hours: Max age for rollback eligibility
            priority: Policy priority

        Returns:
            Policy ID
        """
        from .schema import RollbackType
        # Convert action_types to trigger conditions
        trigger_conditions = [condition] + [f"action_type:{at}" for at in action_types]
        return self.rollback.create_rollback_policy(
            name=name,
            trigger_conditions=trigger_conditions,
            rollback_type=RollbackType.FULL,
            max_rollback_depth=10,
            timeout_seconds=max_rollback_age_hours * 3600,
            requires_approval=not auto_rollback
        )

    def get_rollback_history(
        self,
        agent_id: Optional[str] = None,
        action_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get rollback operation history"""
        return self.rollback.get_rollback_history(
            agent_id=agent_id,
            action_type=action_type,
            limit=limit
        )

    # =========================================================================
    # Persistence
    # =========================================================================

    def save(self, path: Optional[str] = None):
        """Save governance state to file"""
        save_path = path or os.path.join(self.path, "governance.ison")
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        self.graph.save(save_path)

    @classmethod
    def load(cls, path: str, name: Optional[str] = None) -> "GovernanceEngine":
        """Load governance state from file"""
        graph = ISONGraph.load(path)
        engine_name = name or graph.name.replace("-governance", "")
        engine = cls(engine_name)
        engine.graph = graph
        # Reinitialize stores with loaded graph
        engine.authority = AuthorityStore(graph)
        engine.policy = PolicyStore(graph)
        engine.compliance = ComplianceStore(graph)
        engine.audit = AuditStore(graph)
        engine.risk = RiskStore(graph)
        engine.escalation = EscalationStore(graph)
        engine.resource = ResourceStore(graph)
        engine.coordination = CoordinationStore(graph)
        engine.ethics = EthicsStore(graph)
        engine.capability = CapabilityStore(graph)
        engine.incident = IncidentStore(graph)
        engine.meta = MetaGovernanceStore(graph)
        engine.crossorg = CrossOrgStore(graph)
        engine.temporal = TemporalStore(graph)
        engine.observability = ObservabilityStore(graph)
        engine.rollback = RollbackStore(graph)
        return engine


# =========================================================================
# Convenience Functions
# =========================================================================

def quick_governance(name: str, setup_defaults: bool = True) -> GovernanceEngine:
    """
    Quick setup for governance with sensible defaults.

    Args:
        name: Name of the governance context
        setup_defaults: Whether to set up default policies, values, etc.
    """
    engine = GovernanceEngine(name)

    if setup_defaults:
        # Add default values (names are used as IDs)
        engine.ethics.add_value("user_benefit", ValuePriority.HIGHEST, True, "mission")
        engine.ethics.add_value("honesty", ValuePriority.HIGHEST, True, "principle")
        engine.ethics.add_value("safety", ValuePriority.HIGHEST, True, "principle")
        engine.ethics.add_value("privacy", ValuePriority.HIGH, True, "principle")
        engine.ethics.add_value("fairness", ValuePriority.HIGH, True, "principle")
        engine.ethics.add_value("transparency", ValuePriority.HIGH, True, "principle")

        # Add value hierarchy (using names as IDs)
        engine.ethics.set_value_hierarchy("safety", "user_benefit", "dominates", "always")

        # Add default capabilities
        engine.capability.add_capability("read_public", RiskLevel.LOW, CapabilityMaturity.STABLE, "enabled")
        engine.capability.add_capability("write_internal", RiskLevel.MEDIUM, CapabilityMaturity.STABLE, "disabled")
        engine.capability.add_capability("write_external", RiskLevel.HIGH, CapabilityMaturity.STABLE, "disabled")
        engine.capability.add_capability("code_execution", RiskLevel.HIGH, CapabilityMaturity.STABLE, "disabled")
        engine.capability.add_capability("financial_transaction", RiskLevel.CRITICAL, CapabilityMaturity.STABLE, "disabled")

        # Add default scopes
        engine.authority.add_scope("read_public", RiskLevel.LOW)
        engine.authority.add_scope("read_internal", RiskLevel.MEDIUM)
        engine.authority.add_scope("write_internal", RiskLevel.MEDIUM)
        engine.authority.add_scope("write_external", RiskLevel.HIGH, requires_human=True)
        engine.authority.add_scope("execute_code", RiskLevel.HIGH)
        engine.authority.add_scope("financial", RiskLevel.CRITICAL, requires_human=True)

        # Add default risks
        engine.risk.add_risk("operational", "service_unavailability", 0.6, 0.3, "Service disruption risk")
        engine.risk.add_risk("security", "data_breach", 0.8, 0.4, "Data security breach risk")
        engine.risk.add_risk("compliance", "regulatory_violation", 0.7, 0.35, "Regulatory compliance violation")
        engine.risk.add_risk("safety", "harmful_content", 0.9, 0.3, "Risk of generating harmful content")

        # Add default policy
        engine.add_policy("default_safety", [
            {"condition": "safety_score < 0.5", "action": "deny", "description": "Block unsafe actions"},
            {"condition": "confidence < 0.7", "action": "escalate", "description": "Escalate uncertain decisions"},
        ], priority=100)

        # Add default metrics (include descriptions to avoid parsing issues)
        engine.observability.add_metric("decision_accuracy", "accuracy", 0.95, "Accuracy of governance decisions")
        engine.observability.add_metric("decision_latency_ms", "latency", 100, "Decision latency in milliseconds")
        engine.observability.add_metric("escalation_rate", "throughput", 0.15, "Rate of escalations to humans")

        # Add default rollback policies
        engine.add_rollback_policy(
            name="auto_rollback_on_error",
            condition="error_count > 3",
            action_types=["write_external", "code_execution", "financial_transaction"],
            auto_rollback=True,
            max_rollback_age_hours=24,
            priority=100
        )
        engine.add_rollback_policy(
            name="rollback_on_escalation",
            condition="escalation_required == True",
            action_types=["write_external", "financial_transaction"],
            auto_rollback=False,
            max_rollback_age_hours=48,
            priority=90
        )

    return engine
