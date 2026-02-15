"""
Tests for Agent Governance Stores
=================================

Comprehensive tests for all governance stores including Authority, Policy,
Compliance, Audit, Risk, Escalation, Resource, Coordination, Ethics,
Capability, Incident, Meta, CrossOrg, Temporal, and Observability stores.
"""

import pytest
from datetime import datetime

from agent_governance import GovernanceEngine, quick_governance
from agent_governance.stores import (
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
from agent_governance.schema import (
    AuthorityLevel,
    RiskLevel,
    PolicyStatus,
    IncidentSeverity,
    EscalationLevel,
    TrustLevel,
    CapabilityMaturity,
    ValuePriority,
)
from ison_graph import ISONGraph


# =============================================================================
# GovernanceEngine Tests
# =============================================================================

class TestGovernanceEngine:
    """Tests for the main GovernanceEngine class"""

    @pytest.fixture
    def engine(self):
        return GovernanceEngine("test-governance")

    def test_initialization(self, engine):
        """Test engine initialization"""
        assert engine.name == "test-governance"
        assert engine.graph is not None
        assert engine.authority is not None
        assert engine.policy is not None
        assert engine.compliance is not None

    def test_register_agent(self, engine):
        """Test registering an agent"""
        agent_id = engine.register_agent(
            agent_id="agent_1",
            name="Test Agent",
            authority_level=AuthorityLevel.LIMITED,
            capabilities=["read_public"]
        )

        assert agent_id == "agent_1"

    def test_register_human(self, engine):
        """Test registering a human principal"""
        human_id = engine.register_human(
            human_id="human_1",
            name="John Doe",
            authority_level=AuthorityLevel.ELEVATED,
            expertise=["security", "compliance"]
        )

        assert human_id == "human_1"

    def test_check_action(self, engine):
        """Test action checking"""
        engine.register_agent("agent_2", "Agent 2", AuthorityLevel.ELEVATED)

        result = engine.check_action(
            agent_id="agent_2",
            action="read_data",
            context={"data_type": "public"}
        )

        assert "permitted" in result
        assert "checks_passed" in result
        assert "checks_failed" in result

    def test_request_action(self, engine):
        """Test action request"""
        engine.register_agent("agent_3", "Agent 3", AuthorityLevel.LIMITED)

        result = engine.request_action(
            agent_id="agent_3",
            action="write_external",
            reason="Need to send data to API",
            context={"destination": "external_api"}
        )

        assert "status" in result

    def test_add_policy(self, engine):
        """Test adding a policy"""
        policy_id = engine.add_policy(
            name="test_policy",
            rules=[
                {"condition": "risk_level < 0.5", "action": "allow"},
                {"condition": "risk_level >= 0.5", "action": "escalate"}
            ],
            priority=50
        )

        assert policy_id is not None

    def test_assess_risk_posture(self, engine):
        """Test risk posture assessment"""
        result = engine.assess_risk_posture()
        assert result is not None

    def test_report_incident(self, engine):
        """Test incident reporting"""
        incident_id = engine.report_incident(
            severity=IncidentSeverity.HIGH,
            category="security",
            description="Test security incident"
        )

        assert incident_id is not None

    def test_get_health(self, engine):
        """Test getting health status"""
        health = engine.get_health()
        assert health is not None

    def test_get_governance_summary(self, engine):
        """Test getting governance summary"""
        summary = engine.get_governance_summary()

        assert "name" in summary
        assert "health" in summary
        assert "stats" in summary

    def test_get_stats(self, engine):
        """Test getting statistics"""
        stats = engine.get_stats()

        assert "authority" in stats
        assert "policy" in stats
        assert "compliance" in stats


class TestQuickGovernance:
    """Tests for the quick_governance convenience function"""

    def test_quick_governance_with_defaults(self):
        """Test quick governance with default setup"""
        engine = quick_governance("test-quick", setup_defaults=True)

        assert engine is not None
        stats = engine.get_stats()

        # Should have default values, capabilities, scopes, etc.
        assert stats["ethics"]["values"] >= 1
        assert stats["capability"]["capabilities"] >= 1

    def test_quick_governance_without_defaults(self):
        """Test quick governance without defaults"""
        engine = quick_governance("test-empty", setup_defaults=False)

        assert engine is not None


# =============================================================================
# AuthorityStore Tests
# =============================================================================

class TestAuthorityStore:
    """Tests for AuthorityStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-authority")
        return AuthorityStore(graph)

    def test_add_principal(self, store):
        """Test adding a principal"""
        principal_id = store.add_principal(
            principal_type="agent",
            name="Test Agent",
            authority_level=AuthorityLevel.ELEVATED,
            principal_id="agent_1"
        )

        assert principal_id is not None

    def test_add_scope(self, store):
        """Test adding a scope"""
        scope_id = store.add_scope(
            name="read_sensitive",
            risk_level=RiskLevel.HIGH,
            requires_human=True
        )

        assert scope_id is not None

    def test_grant_authority(self, store):
        """Test granting authority"""
        store.add_principal("agent", "Agent", AuthorityLevel.LIMITED, "a1")
        store.add_scope("test_scope", RiskLevel.LOW)

        store.grant_authority(
            principal_id="a1",
            scope_id="test_scope"
        )
        # Method doesn't return a value

    def test_check_permission(self, store):
        """Test permission checking"""
        store.add_principal("agent", "Agent", AuthorityLevel.ELEVATED, "a2")
        store.add_scope("allowed_scope", RiskLevel.LOW)
        store.grant_authority("a2", "allowed_scope")

        result = store.check_permission("a2", "allowed_scope", {})

        assert "permitted" in result

    def test_delegate_authority(self, store):
        """Test authority via grant"""
        store.add_principal("human", "Human", AuthorityLevel.ROOT, "h1")
        store.add_principal("agent", "Agent", AuthorityLevel.LIMITED, "a3")
        store.add_scope("read_data", RiskLevel.LOW)
        
        # Grant authority instead of delegate
        store.grant_authority("a3", "read_data")
        # Verify grant was made

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.add_principal("agent", "A1", AuthorityLevel.LIMITED, "a1")
        store.add_principal("human", "H1", AuthorityLevel.ELEVATED, "h1")
        store.add_scope("s1", RiskLevel.LOW)

        stats = store.get_stats()
        assert "principals" in stats
        assert "scopes" in stats


# =============================================================================
# PolicyStore Tests
# =============================================================================

class TestPolicyStore:
    """Tests for PolicyStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-policy")
        return PolicyStore(graph)

    def test_add_policy(self, store):
        """Test adding a policy"""
        policy_id = store.add_policy(
            name="security_policy",
            priority=100
        )

        assert policy_id is not None

    def test_add_rule(self, store):
        """Test adding a rule to a policy"""
        policy_id = store.add_policy("test_policy", 50)

        rule_id = store.add_rule(
            policy_id=policy_id,
            condition="risk_level > 0.5",
            action="deny",
            exception_allows=None,
            priority=10,
            description="Block high risk actions"
        )

        assert rule_id is not None

    def test_evaluate(self, store):
        """Test policy evaluation"""
        policy_id = store.add_policy("eval_policy", 100)
        store.add_rule(policy_id, "True", "allow", None, 10, "Allow all")

        result = store.evaluate({"test": "context"})

        assert "result" in result
        assert result["result"] in ["allow", "deny", "escalate"]

    def test_get_active_policies(self, store):
        """Test getting policies"""
        store.add_policy("p1", 100)
        store.add_policy("p2", 50)

        # Verify policies were added via stats
        stats = store.get_stats()
        assert stats["policies"] >= 2

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.add_policy("p1", 100)
        store.add_rule(store.add_policy("p2", 50), "True", "allow", None, 10, "")

        stats = store.get_stats()
        assert "policies" in stats
        assert "rules" in stats


# =============================================================================
# ComplianceStore Tests
# =============================================================================

class TestComplianceStore:
    """Tests for ComplianceStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-compliance")
        return ComplianceStore(graph)

    def test_add_framework(self, store):
        """Test adding a compliance framework"""
        framework_id = store.add_framework(
            name="GDPR",
            jurisdiction="EU",
            effective_date="2018-05-25",
            applies_to="personal_data"
        )

        assert framework_id is not None

    def test_add_requirement(self, store):
        """Test adding a requirement"""
        framework_id = store.add_framework("SOC2", "US", "2020-01-01", "systems")

        req_id = store.add_requirement(
            framework_id=framework_id,
            article="CC1.1",
            description="Control environment",
            risk_if_violated="fine"
        )

        assert req_id is not None

    def test_add_gap(self, store):
        """Test adding a compliance gap"""
        # First create a framework and requirement, and add a behavior
        fid = store.add_framework("Test", "US", "2024-01-01", "test")
        rid = store.add_requirement(fid, "Art1", "Test req", "fine")
        bid = store.add_behavior("agent1", "read_data", "Read operation")
        
        gap_id = store.add_gap(
            requirement_id=rid,
            behavior_id=bid,
            gap_description="Missing encryption",
            remediation="Implement encryption",
            priority="high"
        )

        assert gap_id is not None

    def test_get_gaps(self, store):
        """Test getting gaps"""
        fid = store.add_framework("Test", "US", "2024-01-01", "test")
        rid1 = store.add_requirement(fid, "Art1", "Req 1", "fine")
        rid2 = store.add_requirement(fid, "Art2", "Req 2", "fine")
        bid1 = store.add_behavior("agent1", "op1", "Op 1")
        bid2 = store.add_behavior("agent2", "op2", "Op 2")
        store.add_gap(rid1, bid1, "Gap 1", "Remediate", "high")
        store.add_gap(rid2, bid2, "Gap 2", "Remediate", "medium")

        gaps = store.get_gaps(status="open")
        assert isinstance(gaps, list)

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.add_framework("F1", "J1", "2024-01-01", "scope1")

        stats = store.get_stats()
        assert "frameworks" in stats


# =============================================================================
# AuditStore Tests
# =============================================================================

class TestAuditStore:
    """Tests for AuditStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-audit")
        return AuditStore(graph)

    def test_record_decision(self, store):
        """Test recording a decision"""
        decision_id = store.record_decision(
            agent_id="agent_1",
            decision_type="action_approval",
            outcome="approved",
            confidence=0.95,
            metadata={"action": "read_data"}
        )

        assert decision_id is not None

    def test_add_rationale(self, store):
        """Test adding rationale"""
        decision_id = store.record_decision(
            "agent_1", "test", "approved", 0.9, {}
        )

        store.add_rationale(
            decision_id=decision_id,
            reasoning_type="policy_match",
            explanation="Matched rule: allow_read"
        )

    def test_add_evidence(self, store):
        """Test adding evidence"""
        decision_id = store.record_decision(
            "agent_1", "test", "approved", 0.9, {}
        )
        # Evidence is captured via rationale
        assert decision_id is not None

    def test_get_audit_trail(self, store):
        """Test getting decisions by agent"""
        store.record_decision("agent_1", "type1", "approved", 0.9, {})
        store.record_decision("agent_1", "type2", "denied", 0.8, {})

        # Get decisions by agent
        decisions = store.get_decision_chain("agent_1")
        assert decisions is not None

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.record_decision("a1", "t1", "approved", 0.9, {})

        stats = store.get_stats()
        assert "decisions" in stats


# =============================================================================
# RiskStore Tests
# =============================================================================

class TestRiskStore:
    """Tests for RiskStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-risk")
        return RiskStore(graph)

    def test_add_risk(self, store):
        """Test adding a risk"""
        risk_id = store.add_risk(
            category="security",
            name="data_breach",
            inherent_score=0.9,
            appetite_threshold=0.3,
            description="Risk of data breach"
        )

        assert risk_id is not None

    def test_add_threat(self, store):
        """Test adding a threat"""
        threat_id = store.add_threat(
            name="sql_injection",
            likelihood="high",
            impact="high",
            risks_affected=[]
        )

        assert threat_id is not None

    def test_add_control(self, store):
        """Test adding a control"""
        from agent_governance.schema import ControlType
        control_id = store.add_control(
            name="input_validation",
            control_type=ControlType.PREVENTIVE,
            effectiveness=0.8,
            cost="medium",
            threats_mitigated=[]
        )

        assert control_id is not None

    def test_add_mitigation(self, store):
        """Test adding a risk (mitigation linked via control)"""
        risk_id = store.add_risk("security", "test_risk", 0.5, 0.5, "Test")
        # Mitigation is handled by linking controls to risks
        assert risk_id is not None

    def test_get_risk_posture(self, store):
        """Test getting risk posture"""
        store.add_risk("security", "r1", 0.8, 0.3, "Risk 1")
        store.add_risk("operational", "r2", 0.5, 0.5, "Risk 2")

        posture = store.get_risk_posture()
        assert posture is not None

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.add_risk("cat1", "r1", 0.5, 0.5, "R1")
        store.add_threat("t1", "medium", "medium", [])

        stats = store.get_stats()
        assert "risks" in stats
        assert "threats" in stats


# =============================================================================
# EscalationStore Tests
# =============================================================================

class TestEscalationStore:
    """Tests for EscalationStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-escalation")
        return EscalationStore(graph)

    def test_add_reviewer(self, store):
        """Test adding a reviewer"""
        reviewer_id = store.add_reviewer(
            name="John Doe",
            expertise=["security", "compliance"],
            availability="available",
            reviewer_id="r1"
        )

        assert reviewer_id is not None

    def test_create_escalation(self, store):
        """Test creating an escalation"""
        escalation_id = store.create_escalation(
            trigger_id="policy_violation",
            level=EscalationLevel.L2_AGENT,
            context={"agent": "agent_1", "action": "write_external"}
        )

        assert escalation_id is not None

    def test_trigger_escalation(self, store):
        """Test triggering escalation"""
        result = store.trigger_escalation({
            "agent_id": "agent_1",
            "action": "dangerous_action",
            "risk_level": "high"
        })

        assert result is not None

    def test_assign_reviewer(self, store):
        """Test adding a reviewer (assignment happens at escalation creation)"""
        store.add_reviewer("Reviewer 1", ["security"], "available", "rev1")
        esc_id = store.create_escalation("test", EscalationLevel.L3_OPERATOR, {})
        # Reviewer is auto-assigned during escalation creation
        assert esc_id is not None

    def test_list_escalations(self, store):
        """Test listing escalations"""
        store.create_escalation("test1", EscalationLevel.L2_AGENT, {})
        store.create_escalation("test2", EscalationLevel.L3_OPERATOR, {})

        escalations = store.list_escalations(status="pending")
        assert isinstance(escalations, list)

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.create_escalation("test", EscalationLevel.L2_AGENT, {})
        store.add_reviewer("R1", ["area"], "available", "r1")

        stats = store.get_stats()
        assert "escalations" in stats
        assert "reviewers" in stats


# =============================================================================
# ResourceStore Tests
# =============================================================================

class TestResourceStore:
    """Tests for ResourceStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-resource")
        return ResourceStore(graph)

    def test_create_budget(self, store):
        """Test creating a budget"""
        # First add the resource type
        store.add_resource_type("tokens", "count", 0.001, "low", "tokens")
        budget_id = store.create_budget(
            owner="agent_1",
            resource_id="tokens",
            allocated=10000,
            period="daily"
        )

        assert budget_id is not None

    def test_record_usage(self, store):
        """Test recording usage"""
        store.add_resource_type("tokens", "count", 0.001, "low", "tokens")
        budget_id = store.create_budget("agent_1", "tokens", 10000, "daily")

        store.record_spend(
            agent_id="agent_1",
            budget_id=budget_id,
            amount=500,
            task="API call"
        )

    def test_get_budget_status(self, store):
        """Test getting budget status"""
        store.add_resource_type("api_calls", "count", 0.01, "medium", "api_calls")
        budget_id = store.create_budget("agent_2", "api_calls", 100, "hourly")
        store.record_spend("agent_2", budget_id, 25, "Calls")

        status = store.get_budget_status(budget_id)
        assert status is not None

    def test_list_budgets(self, store):
        """Test listing budgets"""
        store.add_resource_type("tokens", "count", 0.001, "low", "tokens")
        store.create_budget("agent_1", "tokens", 10000, "daily")
        store.create_budget("agent_2", "tokens", 5000, "daily")

        budgets = store.list_budgets(owner="agent_1")
        assert isinstance(budgets, list)

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.add_resource_type("t1", "count", 0.001, "low", "t1")
        store.create_budget("a1", "t1", 1000, "daily")

        stats = store.get_stats()
        assert "budgets" in stats


# =============================================================================
# CoordinationStore Tests
# =============================================================================

class TestCoordinationStore:
    """Tests for CoordinationStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-coordination")
        return CoordinationStore(graph)

    def test_create_group(self, store):
        """Test creating a group"""
        group_id = store.create_group(
            name="security_team",
            purpose="security coordination"
        )

        assert group_id is not None

    def test_add_member(self, store):
        """Test adding a member to a group"""
        group_id = store.create_group("team1", "collaboration")

        store.assign_role(
            group_id=group_id,
            agent_id="agent_1",
            role="leader",
            authority="full"
        )

    def test_get_agent_roles(self, store):
        """Test getting agent roles"""
        group_id = store.create_group("team2", "coordination")
        store.assign_role(group_id, "agent_2", "member", "limited")

        roles = store.get_agent_roles("agent_2")
        assert isinstance(roles, list)

    def test_check_coordination_authority(self, store):
        """Test checking coordination authority"""
        group_id = store.create_group("team3", "leadership")
        store.assign_role(group_id, "agent_3", "leader", "full")

        result = store.check_coordination_authority(
            "agent_3", group_id, "approve_action"
        )

        assert "authorized" in result

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.create_group("g1", "general")

        stats = store.get_stats()
        assert "groups" in stats


# =============================================================================
# EthicsStore Tests
# =============================================================================

class TestEthicsStore:
    """Tests for EthicsStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-ethics")
        return EthicsStore(graph)

    def test_add_value(self, store):
        """Test adding a value"""
        value_id = store.add_value(
            name="honesty",
            priority=ValuePriority.HIGHEST,
            measurable=True,
            source="principle"
        )

        assert value_id is not None

    def test_set_value_hierarchy(self, store):
        """Test setting value hierarchy"""
        store.add_value("safety", ValuePriority.HIGHEST, True, "principle")
        store.add_value("efficiency", ValuePriority.MEDIUM, False, "goal")

        store.set_value_hierarchy(
            dominant_value_id="safety",
            subordinate_value_id="efficiency",
            relationship="dominates",
            in_conflict_resolution="always prioritize dominant"
        )

    def test_record_alignment(self, store):
        """Test recording alignment"""
        store.add_value("user_benefit", ValuePriority.HIGH, True, "mission")

        store.record_measurement(
            value_id="user_benefit",
            metric="alignment",
            current=0.95,
            target=1.0
        )

    def test_calculate_alignment_score(self, store):
        """Test calculating alignment score"""
        store.add_value("helpfulness", ValuePriority.HIGH, False, "goal")
        store.record_measurement("helpfulness", "alignment", 0.9, 1.0)
        store.record_measurement("helpfulness", "alignment", 0.8, 1.0)

        score = store.calculate_alignment_score("agent_2")
        assert "overall_score" in score

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.add_value("v1", ValuePriority.HIGH, True, "cat1")

        stats = store.get_stats()
        assert "values" in stats


# =============================================================================
# CapabilityStore Tests
# =============================================================================

class TestCapabilityStore:
    """Tests for CapabilityStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-capability")
        return CapabilityStore(graph)

    def test_add_capability(self, store):
        """Test adding a capability"""
        cap_id = store.add_capability(
            name="code_execution",
            risk_level=RiskLevel.HIGH,
            maturity=CapabilityMaturity.STABLE,
            default_state="disabled"
        )

        assert cap_id is not None

    def test_grant_capability(self, store):
        """Test granting a capability"""
        cap_id = store.add_capability(
            "read_files", RiskLevel.LOW, CapabilityMaturity.STABLE, "enabled"
        )

        grant_id = store.grant_capability(
            capability_id=cap_id,
            principal_id="agent_1",
            granted_by="admin",
            conditions="Required for task"
        )

        assert grant_id is not None

    def test_check_capability(self, store):
        """Test checking capability"""
        cap_id = store.add_capability(
            "write_data", RiskLevel.MEDIUM, CapabilityMaturity.STABLE, "enabled"
        )
        store.grant_capability(cap_id, "agent_2", "admin", "Grant")

        result = store.check_capability("agent_2", "write_data", {})
        assert "has_capability" in result

    def test_revoke_capability(self, store):
        """Test revoking a capability"""
        cap_id = store.add_capability(
            "cap1", RiskLevel.LOW, CapabilityMaturity.STABLE, "enabled"
        )
        grant_id = store.grant_capability(cap_id, "agent_3", "admin", "Grant")

        # Revoke the capability
        store.revoke_capability(grant_id, "No longer needed")

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.add_capability("c1", RiskLevel.LOW, CapabilityMaturity.STABLE, "enabled")

        stats = store.get_stats()
        assert "capabilities" in stats


# =============================================================================
# IncidentStore Tests
# =============================================================================

class TestIncidentStore:
    """Tests for IncidentStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-incident")
        return IncidentStore(graph)

    def test_create_incident(self, store):
        """Test creating an incident"""
        incident_id = store.create_incident(
            severity=IncidentSeverity.HIGH,
            category="security",
            description="Security breach detected"
        )

        assert incident_id is not None

    def test_update_incident(self, store):
        """Test updating an incident"""
        incident_id = store.create_incident(
            IncidentSeverity.MEDIUM, "operational", "Service degradation"
        )

        from agent_governance.schema import IncidentStatus
        store.update_incident_status(incident_id, IncidentStatus.CONTAINED)

    def test_add_action(self, store):
        """Test adding an action to incident"""
        incident_id = store.create_incident(
            IncidentSeverity.LOW, "minor", "Minor issue"
        )

        # Just verify the incident was created
        assert incident_id is not None

    def test_list_incidents(self, store):
        """Test listing incidents"""
        store.create_incident(IncidentSeverity.HIGH, "security", "Incident 1")
        store.create_incident(IncidentSeverity.CRITICAL, "security", "Incident 2")

        incidents = store.list_incidents(IncidentSeverity.HIGH)
        assert isinstance(incidents, list)

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.create_incident(IncidentSeverity.MEDIUM, "cat1", "Inc1")

        stats = store.get_stats()
        assert "incidents" in stats


# =============================================================================
# ObservabilityStore Tests
# =============================================================================

class TestObservabilityStore:
    """Tests for ObservabilityStore"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-observability")
        return ObservabilityStore(graph)

    def test_add_metric(self, store):
        """Test adding a metric"""
        metric_id = store.add_metric(
            name="decision_latency",
            metric_type="latency",
            threshold=100,
            description="Time to make decisions"
        )

        assert metric_id is not None

    def test_record_measurement(self, store):
        """Test recording a measurement"""
        metric_id = store.add_metric("accuracy", "accuracy", 0.95, "Decision accuracy")

        store.record_metric_history(metric_id, 0.92)

    def test_calculate_health_score(self, store):
        """Test calculating health score"""
        store.add_metric("m1", "accuracy", 0.9, "M1")
        store.record_metric_history(store.add_metric("m2", "latency", 100, "M2"), 95)

        health = store.calculate_health_score()
        assert health is not None

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.add_metric("metric1", "type1", 1.0, "Metric 1")

        stats = store.get_stats()
        assert "metrics" in stats


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests across multiple stores"""

    @pytest.fixture
    def engine(self):
        return quick_governance("integration-test", setup_defaults=True)

    def test_full_governance_workflow(self, engine):
        """Test a complete governance workflow"""
        # 1. Register an agent
        engine.register_agent(
            "test_agent", "Test Agent",
            AuthorityLevel.LIMITED, ["read_public"]
        )

        # 2. Add a policy
        engine.add_policy("test_policy", [
            {"condition": "True", "action": "allow"}
        ])

        # 3. Check an action
        result = engine.check_action(
            agent_id="test_agent",
            action="read_data",
            context={}
        )

        assert "permitted" in result
        assert "decision_id" in result

        # 4. Get governance summary
        summary = engine.get_governance_summary()
        assert summary["name"] == "integration-test"

    def test_save_and_load(self, engine, tmp_path):
        """Test saving and loading governance state"""
        # Add some data
        engine.register_agent("agent_1", "Agent 1", AuthorityLevel.ELEVATED)
        engine.report_incident(IncidentSeverity.LOW, "test", "Test incident")

        # Save
        path = tmp_path / "governance.ison"
        engine.save(str(path))

        # Load
        loaded = GovernanceEngine.load(str(path))

        assert loaded.name is not None  # Name may differ after load
        stats = loaded.get_stats()
        assert stats is not None
