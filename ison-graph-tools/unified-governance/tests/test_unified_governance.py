"""
Unified Governance Tests
========================

Unit tests for unified governance integration.
"""

import pytest
import sys
sys.path.insert(0, "../src")

from ison_graph import ISONGraph
from unified_governance import (
    UnifiedGovernanceEngine,
    quick_unified_governance,
    GovernanceDomain,
    ComplianceStatus,
    RegulationJurisdiction,
    IntegrationEventType,
)


@pytest.fixture
def graph():
    """Create fresh ISONGraph for each test."""
    return ISONGraph()


@pytest.fixture
def engine(graph):
    """Create unified governance engine."""
    return UnifiedGovernanceEngine(graph=graph)


@pytest.fixture
def quick_engine():
    """Create quick unified governance with defaults."""
    return quick_unified_governance("test", setup_defaults=True)


class TestRegulatoryBridgeStore:
    """Tests for RegulatoryBridgeStore."""

    def test_register_regulation(self, engine):
        """Test registering a regulation."""
        engine.regulatory.register_regulation(
            regulation_id="test_reg",
            name="Test Regulation",
            jurisdiction=RegulationJurisdiction.EU,
            description="Test regulation",
        )

        stats = engine.regulatory.get_stats()
        assert stats["total_regulations"] >= 1

    def test_get_regulations_for_pii(self, engine):
        """Test getting regulations for PII type."""
        result = engine.regulatory.get_regulations_for_pii("ssn")

        assert result["pii_type"] == "ssn"
        assert "gdpr" in result["applicable_regulations"]
        assert "ccpa" in result["applicable_regulations"]

    def test_cross_regulation_requirements(self, engine):
        """Test getting cross-regulation requirements."""
        result = engine.regulatory.get_cross_regulation_requirements(
            pii_types=["ssn", "email"]
        )

        assert len(result["pii_types_analyzed"]) == 2
        assert len(result["applicable_regulations"]) > 0
        assert "requirements_by_regulation" in result


class TestPIIComplianceStore:
    """Tests for PIIComplianceStore."""

    def test_link_pii_to_compliance(self, engine):
        """Test linking PII to compliance requirements."""
        result = engine.pii_compliance.link_pii_to_compliance(
            pii_inventory_item_id="inv_001",
            pii_type="ssn",
            source_id="test_db",
            field_location="users.ssn",
            sensitivity_level="top_secret",
            protection_status="unprotected",
        )

        assert result["link_id"] is not None
        assert "gdpr" in result["applicable_regulations"]
        assert result["risk_level"] == "critical"  # Unprotected top_secret

    def test_check_gdpr_compliance(self, engine):
        """Test GDPR compliance check."""
        result = engine.pii_compliance.check_gdpr_compliance(
            pii_type="email",
            processing_purpose="marketing",
            has_consent=True,
            has_legal_basis=True,
            data_minimized=True,
            retention_defined=True,
        )

        assert result["compliant"] is True
        assert result["status"] == ComplianceStatus.COMPLIANT.value

    def test_check_gdpr_compliance_no_consent(self, engine):
        """Test GDPR compliance fails without consent."""
        result = engine.pii_compliance.check_gdpr_compliance(
            pii_type="email",
            processing_purpose="marketing",
            has_consent=False,
            has_legal_basis=False,
            data_minimized=False,
            retention_defined=False,
        )

        assert result["compliant"] is False
        assert len(result["issues"]) > 0

    def test_check_ccpa_compliance(self, engine):
        """Test CCPA compliance check."""
        result = engine.pii_compliance.check_ccpa_compliance(
            pii_type="email",
            has_notice=True,
            opt_out_honored=True,
        )

        assert result["compliant"] is True

    def test_check_ccpa_compliance_opt_out_violated(self, engine):
        """Test CCPA compliance fails when opt-out not honored."""
        result = engine.pii_compliance.check_ccpa_compliance(
            pii_type="email",
            has_notice=True,
            opt_out_honored=False,
        )

        assert result["compliant"] is False
        assert any("opt-out" in str(i).lower() for i in result["issues"])


class TestSubjectUnificationStore:
    """Tests for SubjectUnificationStore."""

    def test_create_unified_subject(self, engine):
        """Test creating a unified subject."""
        subject_id = engine.subjects.create_unified_subject(
            subject_id="user_001",
            email="test@example.com",
            gdpr_data_subject_id="gdpr_001",
            ccpa_consumer_id="ccpa_001",
            jurisdiction=RegulationJurisdiction.GLOBAL,
        )

        assert subject_id == "user_001"

        subject = engine.subjects.get_unified_subject("user_001")
        assert subject["gdpr_data_subject_id"] == "gdpr_001"
        assert subject["ccpa_consumer_id"] == "ccpa_001"

    def test_update_consent_status(self, engine):
        """Test updating consent status."""
        engine.subjects.create_unified_subject(
            subject_id="user_001",
            email="test@example.com",
        )

        result = engine.subjects.update_consent_status(
            subject_id="user_001",
            consent_type="marketing",
            consented=True,
            source_regulation="gdpr",
        )

        assert result["updated"] is True

    def test_update_opt_out_status(self, engine):
        """Test updating opt-out status."""
        engine.subjects.create_unified_subject(
            subject_id="user_001",
            email="test@example.com",
        )

        result = engine.subjects.update_opt_out_status(
            subject_id="user_001",
            opt_out_type="sale",
            opted_out=True,
            source_regulation="ccpa",
        )

        assert result["updated"] is True
        assert result["opted_out"] is True

    def test_cross_regulation_status(self, engine):
        """Test getting cross-regulation status."""
        engine.subjects.create_unified_subject(
            subject_id="user_001",
            email="test@example.com",
            gdpr_data_subject_id="gdpr_001",
            ccpa_consumer_id="ccpa_001",
        )

        engine.subjects.update_consent_status("user_001", "marketing", True, "gdpr")
        engine.subjects.update_opt_out_status("user_001", "sale", True, "ccpa")

        status = engine.subjects.get_cross_regulation_status("user_001")

        assert "gdpr" in status
        assert "ccpa" in status
        assert status["gdpr"]["consents"]["marketing"]["consented"] is True
        assert status["ccpa"]["opt_outs"]["sale"]["opted_out"] is True

    def test_pii_location_tracking(self, engine):
        """Test PII location tracking."""
        engine.subjects.create_unified_subject(
            subject_id="user_001",
            email="test@example.com",
        )

        engine.subjects.register_pii_location(
            subject_id="user_001",
            source_id="db1",
            field_location="users.email",
            pii_type="email",
        )

        locations = engine.subjects.get_pii_locations("user_001")
        assert len(locations) == 1
        assert locations[0]["pii_type"] == "email"


class TestAgentIntegrationStore:
    """Tests for AgentIntegrationStore."""

    def test_register_agent_pii_access(self, engine):
        """Test registering agent PII access."""
        access_id = engine.agent_integration.register_agent_pii_access(
            agent_id="agent_1",
            pii_types=["email", "phone"],
            purpose="support",
            legal_basis="legitimate_interest",
        )

        assert access_id is not None

    def test_check_agent_pii_access(self, engine):
        """Test checking agent PII access."""
        engine.agent_integration.register_agent_pii_access(
            agent_id="agent_1",
            pii_types=["email"],
            purpose="support",
        )

        result = engine.agent_integration.check_agent_pii_access("agent_1", "email")
        assert result["has_access"] is True

        result = engine.agent_integration.check_agent_pii_access("agent_1", "ssn")
        assert result["has_access"] is False

    def test_check_action_compliance(self, engine):
        """Test action compliance check."""
        engine.agent_integration.register_agent_pii_access(
            agent_id="agent_1",
            pii_types=["email"],
            purpose="support",
        )

        result = engine.agent_integration.check_action_compliance(
            agent_id="agent_1",
            action="read_personal_data",
            pii_types_involved=["email"],
        )

        assert result["permitted"] is True

    def test_check_action_compliance_no_access(self, engine):
        """Test action blocked when no access."""
        result = engine.agent_integration.check_action_compliance(
            agent_id="agent_1",
            action="read_personal_data",
            pii_types_involved=["ssn"],
        )

        assert result["permitted"] is False
        assert len(result["blocking_issues"]) > 0

    def test_block_agent_action(self, engine):
        """Test blocking agent action."""
        block_id = engine.agent_integration.block_agent_action(
            agent_id="agent_1",
            action="transfer_data_external",
            reason="Compliance violation",
            regulation="gdpr",
        )

        result = engine.agent_integration.is_action_blocked("agent_1", "transfer_data_external")
        assert result["blocked"] is True


class TestUnifiedGovernanceEngine:
    """Tests for UnifiedGovernanceEngine."""

    def test_check_compliance(self, quick_engine):
        """Test comprehensive compliance check."""
        # Register subject
        quick_engine.register_subject(
            subject_id="user_001",
            email="test@example.com",
        )

        # Grant access
        quick_engine.grant_agent_pii_access(
            agent_id="agent_1",
            pii_types=["email"],
            purpose="support",
        )

        # Check compliance
        result = quick_engine.check_compliance(
            agent_id="agent_1",
            action="read_personal_data",
            pii_types=["email"],
            data_subject_id="user_001",
            context={
                "gdpr": {
                    "has_consent": True,
                    "has_legal_basis": True,
                    "data_minimized": True,
                    "retention_defined": True,
                    "processing_purpose": "support",
                },
            },
        )

        assert result["permitted"] is True
        assert result["overall_status"] in [
            ComplianceStatus.COMPLIANT.value,
            ComplianceStatus.PARTIAL.value,
        ]

    def test_check_compliance_blocked(self, quick_engine):
        """Test compliance check blocks unauthorized access."""
        result = quick_engine.check_compliance(
            agent_id="agent_1",
            action="read_personal_data",
            pii_types=["ssn"],
        )

        assert result["permitted"] is False
        assert len(result["blocking_issues"]) > 0

    def test_check_agent_action_quick(self, quick_engine):
        """Test quick action check."""
        quick_engine.grant_agent_pii_access(
            agent_id="agent_1",
            pii_types=["email"],
            purpose="support",
        )

        result = quick_engine.check_agent_action(
            agent_id="agent_1",
            action="read_personal_data",
            pii_types=["email"],
        )

        assert "permitted" in result
        assert "risk_level" in result

    def test_record_agent_action(self, quick_engine):
        """Test recording agent action."""
        audit_id = quick_engine.record_agent_action(
            agent_id="agent_1",
            action="read_personal_data",
            pii_types=["email"],
            data_source="test_db",
            outcome="success",
        )

        assert audit_id is not None

    def test_unified_report(self, quick_engine):
        """Test unified report generation."""
        report = quick_engine.get_unified_report()

        assert "generated_at" in report
        assert "cross_domain" in report
        assert "health" in report

    def test_executive_summary(self, quick_engine):
        """Test executive summary generation."""
        summary = quick_engine.get_executive_summary()

        assert "UNIFIED GOVERNANCE EXECUTIVE SUMMARY" in summary
        assert "Health Score" in summary

    def test_save_and_load(self, quick_engine, tmp_path):
        """Test save and load functionality."""
        # Add some data
        quick_engine.register_subject(
            subject_id="user_001",
            email="test@example.com",
        )

        # Save
        save_path = str(tmp_path / "test_unified.json")
        quick_engine.save(save_path)

        # Load
        loaded = UnifiedGovernanceEngine.load(save_path)

        # Verify
        subject = loaded.subjects.get_unified_subject("user_001")
        assert subject is not None
        assert subject["email"] == "test@example.com"


class TestCrossRegulationScenarios:
    """Integration tests for cross-regulation scenarios."""

    def test_gdpr_ccpa_subject(self, quick_engine):
        """Test subject covered by both GDPR and CCPA."""
        # Register global subject
        quick_engine.register_subject(
            subject_id="global_user",
            email="global@example.com",
            jurisdiction=RegulationJurisdiction.GLOBAL,
            gdpr_data_subject_id="gdpr_global",
            ccpa_consumer_id="ccpa_global",
        )

        # Set GDPR consent
        quick_engine.subjects.update_consent_status(
            "global_user", "marketing", True, "gdpr"
        )

        # Set CCPA opt-out
        quick_engine.subjects.update_opt_out_status(
            "global_user", "sale", True, "ccpa"
        )

        # Check cross-regulation status
        status = quick_engine.subjects.get_cross_regulation_status("global_user")

        assert status["gdpr"]["consents"]["marketing"]["consented"] is True
        assert status["ccpa"]["opt_outs"]["sale"]["opted_out"] is True

    def test_sensitive_pii_multi_regulation(self, quick_engine):
        """Test sensitive PII requires multiple regulations."""
        requirements = quick_engine.regulatory.get_cross_regulation_requirements(
            pii_types=["ssn", "credit_card"]
        )

        # Should have multiple regulations
        assert len(requirements["applicable_regulations"]) > 1
        assert "gdpr" in requirements["applicable_regulations"]
        assert "ccpa" in requirements["applicable_regulations"]

    def test_agent_blocked_by_opt_out(self, quick_engine):
        """Test agent blocked when consumer opted out."""
        # Register subject with opt-out
        quick_engine.register_subject(
            subject_id="opted_out_user",
            email="optout@example.com",
            ccpa_consumer_id="ccpa_optout",
        )
        quick_engine.subjects.update_opt_out_status(
            "opted_out_user", "share", True, "ccpa"
        )

        # Grant agent access
        quick_engine.grant_agent_pii_access(
            agent_id="sharing_agent",
            pii_types=["email"],
            purpose="partner_sharing",
        )

        # Check compliance for sharing action
        result = quick_engine.check_compliance(
            agent_id="sharing_agent",
            action="share_with_third_party",
            pii_types=["email"],
            data_subject_id="opted_out_user",
            context={
                "ccpa": {
                    "has_notice": True,
                    "opt_out_honored": False,
                },
            },
        )

        # Should have blocking issues due to opt-out
        assert len(result["blocking_issues"]) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
