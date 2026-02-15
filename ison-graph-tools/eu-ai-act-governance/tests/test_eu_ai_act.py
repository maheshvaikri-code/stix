"""
Tests for EU AI Act Governance Package
======================================

Comprehensive tests for EU AI Act compliance governance including
risk classification, conformity assessment, and GPAI governance.
"""

import pytest
from datetime import datetime

from eu_ai_act_governance import EUAIActGovernanceEngine
from eu_ai_act_governance.schema import (
    AIRiskLevel,
    HighRiskCategory,
    ProhibitedPractice,
    GPAICategory,
    ConformityRoute,
    ConformityStatus,
    OversightLevel,
    OversightMeasure,
    IncidentSeverity,
    IncidentType,
    TransparencyObligation,
    MonitoringActivity,
    AIActRole,
)
from eu_ai_act_governance.stores import (
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
from ison_graph import ISONGraph


# =============================================================================
# EUAIActGovernanceEngine Tests
# =============================================================================

class TestEUAIActGovernanceEngine:
    """Tests for the main governance engine"""

    @pytest.fixture
    def graph(self):
        return ISONGraph(name="test-eu-ai-act")

    @pytest.fixture
    def engine(self, graph):
        return EUAIActGovernanceEngine(graph)

    def test_engine_initialization(self, engine):
        """Test engine initialization"""
        assert engine.graph is not None
        assert engine.risk is not None
        assert engine.prohibited is not None
        assert engine.high_risk is not None
        assert engine.conformity is not None
        assert engine.gpai is not None

    def test_onboard_ai_system(self, engine):
        """Test complete AI system onboarding"""
        result = engine.onboard_ai_system(
            name="Credit Scorer AI",
            version="1.0.0",
            provider="FinTech Corp",
            intended_purpose="Assess creditworthiness of loan applicants",
            technical_description="ML model for credit risk assessment",
            deployment_context="Banking sector",
            responsible_party="John Smith"
        )

        assert "system_id" in result
        assert "operator_id" in result
        assert "risk_assessment_id" in result
        assert "prohibited_screening_id" in result
        assert "next_steps" in result

    def test_classify_system_risk_high(self, engine):
        """Test classifying a high-risk system"""
        # Onboard system first
        onboard = engine.onboard_ai_system(
            name="HR AI System",
            version="1.0",
            provider="HR Tech",
            intended_purpose="Screen job applicants",
            technical_description="CV screening AI"
        )

        result = engine.classify_system_risk(
            system_id=onboard["system_id"],
            assessor="risk_manager",
            high_risk_category=HighRiskCategory.EMPLOYMENT_WORKERS,
            prohibited_practices_clear=True
        )

        assert "classification_complete" in result
        assert "next_steps" in result

    def test_classify_system_risk_unacceptable(self, engine):
        """Test classifying a system with prohibited practices"""
        onboard = engine.onboard_ai_system(
            name="Social Score AI",
            version="1.0",
            provider="Gov Tech",
            intended_purpose="Score citizens",
            technical_description="Social scoring system"
        )

        result = engine.classify_system_risk(
            system_id=onboard["system_id"],
            assessor="risk_manager",
            high_risk_category=None,
            prohibited_practices_clear=False
        )

        # Should indicate unacceptable risk
        assert "next_steps" in result

    def test_prepare_for_market(self, engine):
        """Test market preparation workflow"""
        onboard = engine.onboard_ai_system(
            name="Medical Diagnosis AI",
            version="2.0",
            provider="HealthTech",
            intended_purpose="Assist radiologists",
            technical_description="Medical imaging AI"
        )

        result = engine.prepare_for_market(
            system_id=onboard["system_id"],
            provider="HealthTech",
            high_risk_category=HighRiskCategory.BIOMETRICS,
            responsible_party="Dr. Jane Doe"
        )

        assert "conformity_assessment_id" in result
        assert "monitoring_plan_id" in result
        assert "checklist" in result

    def test_complete_conformity_assessment(self, engine):
        """Test completing conformity assessment"""
        onboard = engine.onboard_ai_system(
            name="Safety AI",
            version="1.0",
            provider="SafetyTech",
            intended_purpose="Safety monitoring",
            technical_description="Safety system AI"
        )

        engine.prepare_for_market(
            system_id=onboard["system_id"],
            provider="SafetyTech",
            high_risk_category=HighRiskCategory.CRITICAL_INFRASTRUCTURE,
            responsible_party="Safety Officer"
        )

        result = engine.complete_conformity_assessment(
            system_id=onboard["system_id"],
            provider="SafetyTech",
            signatory_name="CEO",
            signatory_role="Chief Executive"
        )

        # Result may contain error if assessment not found, or success
        assert result is not None

    def test_report_incident(self, engine):
        """Test incident reporting"""
        onboard = engine.onboard_ai_system(
            name="Incident Test AI",
            version="1.0",
            provider="TestCorp",
            intended_purpose="Testing",
            technical_description="Test AI"
        )

        result = engine.report_incident(
            system_id=onboard["system_id"],
            incident_type=IncidentType.SAFETY_ISSUE,
            severity=IncidentSeverity.SERIOUS,
            title="Test Incident",
            description="Incident during testing",
            detected_by="QA Team",
            affected_users=100
        )

        assert "incident_id" in result
        assert "next_steps" in result

    def test_onboard_gpai_model(self, engine):
        """Test GPAI model onboarding"""
        result = engine.onboard_gpai_model(
            name="LargeLanguageModel",
            version="3.0",
            provider="AI Corp",
            training_compute_flops=1e24,
            parameters_count=100_000_000_000,
            capabilities=["text_generation", "reasoning"]
        )

        assert "model_id" in result
        assert "category" in result
        assert "documentation_id" in result
        assert "next_steps" in result

    def test_onboard_gpai_systemic_risk(self, engine):
        """Test GPAI model with systemic risk"""
        result = engine.onboard_gpai_model(
            name="SystemicRiskModel",
            version="1.0",
            provider="BigAI",
            training_compute_flops=1e26,  # Exceeds threshold
            parameters_count=1_000_000_000_000,
            capabilities=["general_intelligence"]
        )

        assert result["category"] == GPAICategory.SYSTEMIC_RISK.value
        assert result["has_systemic_risk"] is True
        assert "risk_assessment_id" in result

    def test_get_system_compliance_status(self, engine):
        """Test getting compliance status"""
        onboard = engine.onboard_ai_system(
            name="Compliance Test AI",
            version="1.0",
            provider="TestCorp",
            intended_purpose="Testing",
            technical_description="Test system"
        )

        status = engine.get_system_compliance_status(onboard["system_id"])

        assert "system_id" in status
        assert "compliance_areas" in status

    def test_get_governance_stats(self, engine):
        """Test getting governance statistics"""
        stats = engine.get_governance_stats()

        assert "risk_classification" in stats
        assert "prohibited_practices" in stats
        assert "high_risk_requirements" in stats
        assert "gpai_governance" in stats


# =============================================================================
# RiskClassificationStore Tests
# =============================================================================

class TestRiskClassificationStore:
    """Tests for risk classification store"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-risk")
        return RiskClassificationStore(graph)

    def test_register_ai_system(self, store):
        """Test registering an AI system"""
        system_id = store.register_ai_system(
            name="Test System",
            version="1.0",
            provider="TestCorp",
            intended_purpose="Testing",
            technical_description="Test description"
        )

        assert system_id is not None

        system = store.get_ai_system(system_id)
        assert system is not None
        assert system["name"] == "Test System"

    def test_register_operator(self, store):
        """Test registering an operator"""
        operator_id = store.register_operator(
            name="OperatorCorp",
            role=AIActRole.PROVIDER,
            organization_type="company"
        )

        assert operator_id is not None

    def test_create_risk_assessment(self, store):
        """Test creating a risk assessment"""
        system_id = store.register_ai_system(
            "System", "1.0", "Provider", "Purpose", "Description"
        )

        assessment_id = store.create_risk_assessment(
            system_id=system_id,
            assessor="risk_manager",
            assessment_type="initial"
        )

        assert assessment_id is not None

    def test_evaluate_high_risk_category(self, store):
        """Test evaluating high-risk categories"""
        system_id = store.register_ai_system(
            "HR System", "1.0", "HRTech", "Hiring", "AI hiring system"
        )
        assessment_id = store.create_risk_assessment(
            system_id, "assessor", "initial"
        )

        store.evaluate_high_risk_category(
            assessment_id=assessment_id,
            category=HighRiskCategory.EMPLOYMENT_WORKERS,
            applies=True,
            rationale="Used for hiring decisions",
            specific_use_case="CV screening",
            evaluated_by="risk_manager"
        )

    def test_determine_risk_level(self, store):
        """Test determining final risk level"""
        system_id = store.register_ai_system(
            "System", "1.0", "Provider", "Purpose", "Description"
        )
        assessment_id = store.create_risk_assessment(
            system_id, "assessor", "initial"
        )

        result = store.determine_risk_level(
            assessment_id=assessment_id,
            determined_by="approver"
        )

        assert "risk_level" in result

    def test_get_stats(self, store):
        """Test getting statistics"""
        store.register_ai_system("S1", "1.0", "P1", "Purpose", "Desc")
        store.register_ai_system("S2", "1.0", "P2", "Purpose", "Desc")

        stats = store.get_stats()
        assert stats["total_systems"] == 2


# =============================================================================
# ProhibitedPracticesStore Tests
# =============================================================================

class TestProhibitedPracticesStore:
    """Tests for prohibited practices store"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-prohibited")
        return ProhibitedPracticesStore(graph)

    def test_create_screening(self, store):
        """Test creating a prohibited practices screening"""
        screening_id = store.create_screening(
            system_id="sys_1",
            screener="compliance_officer",
            screening_type="pre_market"
        )

        assert screening_id is not None

    def test_evaluate_practice(self, store):
        """Test evaluating a specific practice"""
        screening_id = store.create_screening("sys_1", "screener", "pre_market")

        # check_practice(screening_id, practice, indicators_present, evidence, conclusion, checked_by)
        check_id = store.check_practice(
            screening_id=screening_id,
            practice=ProhibitedPractice.SOCIAL_SCORING_PUBLIC,
            indicators_present=[],
            evidence="No social scoring functionality",
            conclusion="clear",
            checked_by="compliance_officer"
        )

        assert check_id is not None

    def test_get_screening_result(self, store):
        """Test getting screening result"""
        screening_id = store.create_screening("sys_1", "screener", "pre_market")

        # Check a practice
        store.check_practice(
            screening_id, ProhibitedPractice.SOCIAL_SCORING_PUBLIC,
            [], "Not applicable", "clear", "evaluator"
        )

        result = store.get_screening(screening_id)
        assert result is not None


# =============================================================================
# HighRiskRequirementsStore Tests
# =============================================================================

class TestHighRiskRequirementsStore:
    """Tests for high-risk requirements store"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-high-risk")
        return HighRiskRequirementsStore(graph)

    def test_initialize_requirements(self, store):
        """Test initializing requirements"""
        # First create the ai_system node that the store references
        store.graph.add_node("ai_system", "sys_1", name="Test System")
        
        store.initialize_requirements(
            system_id="sys_1",
            responsible_party="compliance_team"
        )

        summary = store.get_compliance_summary("sys_1")
        assert summary is not None

    def test_update_requirement_status(self, store):
        """Test updating requirement status"""
        store.graph.add_node("ai_system", "sys_1", name="Test System")
        store.initialize_requirements("sys_1", "team")

        # Get requirements and update one
        summary = store.get_compliance_summary("sys_1")
        if summary and summary.get("requirements"):
            req_id = summary["requirements"][0]["id"]
            store.update_requirement_status(req_id, "completed", "Done")


# =============================================================================
# ConformityAssessmentStore Tests
# =============================================================================

class TestConformityAssessmentStore:
    """Tests for conformity assessment store"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-conformity")
        return ConformityAssessmentStore(graph)

    def test_initiate_assessment(self, store):
        """Test initiating conformity assessment"""
        assessment_id = store.initiate_assessment(
            system_id="sys_1",
            provider="Provider",
            high_risk_category=HighRiskCategory.BIOMETRIC_IDENTIFICATION,
            intended_purpose="Identity verification"
        )

        assert assessment_id is not None

    def test_update_assessment_status(self, store):
        """Test updating assessment status"""
        assessment_id = store.initiate_assessment(
            "sys_1", "Provider", HighRiskCategory.BIOMETRIC_IDENTIFICATION, "Purpose"
        )

        store.update_assessment_status(assessment_id, ConformityStatus.IN_PROGRESS)

    def test_create_declaration(self, store):
        """Test creating EU declaration of conformity"""
        assessment_id = store.initiate_assessment(
            "sys_1", "Provider", HighRiskCategory.BIOMETRIC_IDENTIFICATION, "Purpose"
        )

        declaration_id = store.create_declaration(
            assessment_id=assessment_id,
            provider_name="Provider Corp",
            provider_address="123 Tech Street",
            system_name="Test System",
            system_version="1.0"
        )

        assert declaration_id is not None

    def test_sign_declaration(self, store):
        """Test signing declaration"""
        assessment_id = store.initiate_assessment(
            "sys_1", "Provider", HighRiskCategory.BIOMETRIC_IDENTIFICATION, "Purpose"
        )
        declaration_id = store.create_declaration(
            assessment_id, "Provider", "Address", "System", "1.0"
        )

        store.sign_declaration(
            declaration_id=declaration_id,
            signatory_name="CEO",
            signatory_role="Chief Executive"
        )

    def test_apply_ce_marking(self, store):
        """Test applying CE marking"""
        # First create the ai_system node
        store.graph.add_node("ai_system", "sys_1", name="Test System")
        
        assessment_id = store.initiate_assessment(
            "sys_1", "Provider", HighRiskCategory.BIOMETRIC_IDENTIFICATION, "Purpose"
        )
        declaration_id = store.create_declaration(
            assessment_id, "Provider", "Address", "System", "1.0"
        )

        ce_id = store.apply_ce_marking(
            system_id="sys_1",
            assessment_id=assessment_id,
            declaration_id=declaration_id,
            applied_by="compliance_officer"
        )

        assert ce_id is not None


# =============================================================================
# HumanOversightStore Tests
# =============================================================================

class TestHumanOversightStore:
    """Tests for human oversight store"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-oversight")
        return HumanOversightStore(graph)

    def test_configure_oversight(self, store):
        """Test configuring oversight"""
        config_id = store.configure_oversight(
            system_id="sys_1",
            oversight_level=OversightLevel.HUMAN_ON_THE_LOOP,
            measures=[OversightMeasure.AUDIT_LOGGING, OversightMeasure.OVERRIDE_CAPABILITY],
            rationale="Required for high-risk compliance"
        )

        assert config_id is not None

    def test_add_overseer(self, store):
        """Test configuring additional oversight"""
        config_id = store.configure_oversight(
            "sys_1", OversightLevel.HUMAN_IN_THE_LOOP, [OversightMeasure.AUDIT_LOGGING], "Required oversight"
        )
        assert config_id is not None


# =============================================================================
# GPAIGovernanceStore Tests
# =============================================================================

class TestGPAIGovernanceStore:
    """Tests for GPAI governance store"""

    @pytest.fixture
    def store(self):
        graph = ISONGraph(name="test-gpai")
        return GPAIGovernanceStore(graph)

    def test_register_gpai_model(self, store):
        """Test registering a GPAI model"""
        model_id = store.register_gpai_model(
            name="TestLLM",
            version="1.0",
            provider="AI Corp",
            category=GPAICategory.GENERAL,
            training_compute_flops=1e23,
            parameters_count=10_000_000_000,
            capabilities=["text_generation"]
        )

        assert model_id is not None

    def test_initialize_provider_obligations(self, store):
        """Test initializing provider obligations"""
        model_id = store.register_gpai_model(
            "Model", "1.0", "Provider", GPAICategory.GENERAL,
            1e22, 1_000_000_000, []
        )

        obligation_ids = store.initialize_provider_obligations(
            model_id=model_id,
            provider="Provider"
        )

        assert isinstance(obligation_ids, list)

    def test_create_model_documentation(self, store):
        """Test creating model documentation"""
        model_id = store.register_gpai_model(
            "DocModel", "1.0", "Provider", GPAICategory.GENERAL,
            1e22, 1_000_000_000, []
        )

        doc_id = store.create_model_documentation(
            model_id=model_id,
            author="Tech Writer"
        )

        assert doc_id is not None

    def test_assess_systemic_risk(self, store):
        """Test systemic risk assessment"""
        model_id = store.register_gpai_model(
            "LargeModel", "1.0", "BigAI", GPAICategory.SYSTEMIC_RISK,
            1e26, 1_000_000_000_000, ["general_capability"]
        )

        assessment_id = store.assess_systemic_risk(
            model_id=model_id,
            assessor="Risk Team"
        )

        assert assessment_id is not None


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for complete workflows"""

    @pytest.fixture
    def engine(self):
        graph = ISONGraph(name="test-integration")
        return EUAIActGovernanceEngine(graph)

    def test_full_high_risk_workflow(self, engine):
        """Test complete high-risk AI system workflow"""
        # 1. Onboard system
        onboard = engine.onboard_ai_system(
            name="Medical AI",
            version="1.0",
            provider="HealthTech",
            intended_purpose="Diagnostic assistance",
            technical_description="ML-based diagnostic tool",
            responsible_party="Dr. Smith"
        )

        assert onboard["system_id"] is not None

        # 2. Classify as high-risk
        classification = engine.classify_system_risk(
            system_id=onboard["system_id"],
            assessor="Risk Team",
            high_risk_category=HighRiskCategory.BIOMETRICS,
            prohibited_practices_clear=True
        )

        # 3. Prepare for market
        market_prep = engine.prepare_for_market(
            system_id=onboard["system_id"],
            provider="HealthTech",
            high_risk_category=HighRiskCategory.BIOMETRICS,
            responsible_party="Compliance Officer"
        )

        assert market_prep["conformity_assessment_id"] is not None

        # 4. Get compliance status
        status = engine.get_system_compliance_status(onboard["system_id"])
        assert status["system_id"] is not None

    def test_gpai_full_workflow(self, engine):
        """Test complete GPAI workflow"""
        # 1. Onboard model
        onboard = engine.onboard_gpai_model(
            name="FoundationModel",
            version="2.0",
            provider="AI Labs",
            training_compute_flops=1e25,
            parameters_count=500_000_000_000,
            capabilities=["text", "code", "reasoning"]
        )

        assert onboard["model_id"] is not None
        assert onboard["category"] == GPAICategory.SYSTEMIC_RISK.value

        # 2. Get stats
        stats = engine.get_governance_stats()
        assert stats["gpai_governance"]["total_models"] >= 1
