"""
GDPR Governance Tests
=====================

Unit tests for GDPR compliance governance.
"""

import pytest
import sys
sys.path.insert(0, "../src")

from ison_graph import ISONGraph
from gdpr_governance import (
    GDPRGovernance,
    LawfulBasis,
    PersonalDataCategory,
    ConsentType,
    ConsentStatus,
    DataSubjectRight,
    RightRequestStatus,
    BreachSeverity,
    BreachType,
    DPIATrigger,
    DPIAStatus,
    TransferMechanism,
    ActorRole,
)


@pytest.fixture
def graph():
    """Create fresh ISONGraph for each test"""
    return ISONGraph()


@pytest.fixture
def gdpr(graph):
    """Create GDPR governance instance"""
    return GDPRGovernance(graph)


class TestDataSubjectStore:
    """Tests for DataSubjectStore"""

    def test_register_subject(self, gdpr):
        """Test registering a data subject"""
        subject_id = gdpr.data_subjects.register_subject(
            subject_id="test001",
            email="test@example.com",
        )
        assert subject_id == "subject_test001"

        subject = gdpr.data_subjects.get_subject("test001")
        assert subject is not None
        assert subject["email"] == "test@example.com"

    def test_add_data_category(self, gdpr):
        """Test adding data categories to a subject"""
        gdpr.data_subjects.register_subject(subject_id="test001")

        cat_id = gdpr.data_subjects.add_data_category(
            subject_id="test001",
            category=PersonalDataCategory.CONTACT,
            source="registration_form",
            purpose="communication",
        )

        assert cat_id is not None
        inventory = gdpr.data_subjects.get_subject_data_inventory("test001")
        assert len(inventory) == 1
        assert inventory[0]["category"] == "contact"

    def test_delete_subject_data(self, gdpr):
        """Test deleting subject data (Article 17)"""
        gdpr.data_subjects.register_subject(subject_id="test001")
        gdpr.data_subjects.add_data_category(
            subject_id="test001",
            category=PersonalDataCategory.CONTACT,
            source="form",
            purpose="comm",
        )

        result = gdpr.data_subjects.delete_subject_data(
            subject_id="test001",
            reason="erasure_request",
        )

        assert result["deleted_count"] == 1
        inventory = gdpr.data_subjects.get_subject_data_inventory("test001")
        assert len(inventory) == 0


class TestProcessingActivityStore:
    """Tests for ProcessingActivityStore"""

    def test_register_activity(self, gdpr):
        """Test registering a processing activity"""
        activity_id = gdpr.processing.register_activity(
            name="Test Activity",
            purpose="Testing",
            lawful_basis=LawfulBasis.CONSENT,
            data_categories=[PersonalDataCategory.BASIC_IDENTITY],
            data_subjects=["customers"],
            recipients=["internal"],
            retention_period="1 year",
            security_measures=["encryption"],
            controller_id="controller1",
        )

        assert activity_id is not None
        activity = gdpr.processing.get_activity(activity_id)
        assert activity["name"] == "Test Activity"
        assert activity["lawful_basis"] == "consent"

    def test_dpia_trigger_detection(self, gdpr):
        """Test automatic DPIA trigger detection"""
        activity_id = gdpr.processing.register_activity(
            name="Health Processing",
            purpose="Health monitoring",
            lawful_basis=LawfulBasis.LEGAL_OBLIGATION,
            data_categories=[PersonalDataCategory.HEALTH],
            data_subjects=["employees"],
            recipients=["hr"],
            retention_period="7 years",
            security_measures=["encryption"],
            controller_id="controller1",
        )

        activity = gdpr.processing.get_activity(activity_id)
        assert activity["dpia_required"] is True


class TestConsentStore:
    """Tests for ConsentStore"""

    def test_record_consent(self, gdpr):
        """Test recording consent"""
        consent_id = gdpr.consent.record_consent(
            data_subject_id="user001",
            purpose="marketing",
            consent_type=ConsentType.MARKETING,
            evidence="checkbox",
        )

        assert consent_id is not None
        check = gdpr.consent.check_consent("user001", "marketing")
        assert check["has_consent"] is True

    def test_withdraw_consent(self, gdpr):
        """Test withdrawing consent (Article 7(3))"""
        consent_id = gdpr.consent.record_consent(
            data_subject_id="user001",
            purpose="marketing",
        )

        result = gdpr.consent.withdraw_consent(
            consent_id=consent_id,
            reason="opt-out",
        )

        assert result["status"] == "withdrawn"
        check = gdpr.consent.check_consent("user001", "marketing")
        assert check["has_consent"] is False

    def test_consent_expiry(self, gdpr):
        """Test consent expiry handling"""
        consent_id = gdpr.consent.record_consent(
            data_subject_id="user001",
            purpose="marketing",
            expires_in_days=-1,  # Already expired
        )

        check = gdpr.consent.check_consent("user001", "marketing")
        assert check["status"] == "expired"
        assert check["has_consent"] is False


class TestDataSubjectRightsStore:
    """Tests for DataSubjectRightsStore"""

    def test_submit_request(self, gdpr):
        """Test submitting a DSR request"""
        request_id = gdpr.rights.submit_request(
            data_subject_id="user001",
            right_type=DataSubjectRight.ACCESS,
        )

        assert request_id is not None
        request = gdpr.rights.get_request(request_id)
        assert request["status"] == "received"
        assert request["right_type"] == "access"

    def test_request_lifecycle(self, gdpr):
        """Test full request lifecycle"""
        request_id = gdpr.rights.submit_request(
            data_subject_id="user001",
            right_type=DataSubjectRight.ACCESS,
        )

        # Verify identity
        gdpr.rights.verify_identity(
            request_id=request_id,
            verification_method="email",
            verified_by="support",
        )

        request = gdpr.rights.get_request(request_id)
        assert request["identity_verified"] == "True"

        # Complete request
        gdpr.rights.complete_request(
            request_id=request_id,
            response="Data provided",
            actions_taken=["export_generated"],
        )

        request = gdpr.rights.get_request(request_id)
        assert request["status"] == "completed"

    def test_extend_deadline(self, gdpr):
        """Test extending DSR deadline (Article 12(3))"""
        request_id = gdpr.rights.submit_request(
            data_subject_id="user001",
            right_type=DataSubjectRight.PORTABILITY,
        )

        result = gdpr.rights.extend_deadline(
            request_id=request_id,
            reason="Complex request involving multiple systems",
        )

        assert "new_deadline" in result
        request = gdpr.rights.get_request(request_id)
        assert request["extended"] == "True"


class TestDataBreachStore:
    """Tests for DataBreachStore"""

    def test_report_breach(self, gdpr):
        """Test reporting a breach"""
        breach_id = gdpr.breach.report_breach(
            description="Data leak detected",
            breach_type=BreachType.CONFIDENTIALITY,
        )

        assert breach_id is not None
        breach = gdpr.breach.get_breach(breach_id)
        assert breach["status"] == "detected"
        assert breach["dpa_deadline"] is not None

    def test_breach_assessment(self, gdpr):
        """Test breach severity assessment"""
        breach_id = gdpr.breach.report_breach(
            description="Breach",
            breach_type=BreachType.CONFIDENTIALITY,
        )

        gdpr.breach.assess_severity(
            breach_id=breach_id,
            severity=BreachSeverity.HIGH,
            risk_assessment="High risk assessment",
            dpa_notification_required=True,
            subject_notification_required=True,
        )

        breach = gdpr.breach.get_breach(breach_id)
        assert breach["severity"] == "high"
        assert breach["dpa_notification_required"] == "True"


class TestDPIAStore:
    """Tests for DPIAStore"""

    def test_create_dpia(self, gdpr):
        """Test creating a DPIA"""
        dpia_id = gdpr.dpia.create_dpia(
            processing_activity_id="activity1",
            name="Test DPIA",
            triggers=[DPIATrigger.PROFILING],
        )

        assert dpia_id is not None
        dpia = gdpr.dpia.get_dpia(dpia_id)
        assert dpia["status"] == "required"

    def test_dpia_workflow(self, gdpr):
        """Test complete DPIA workflow"""
        dpia_id = gdpr.dpia.create_dpia(
            processing_activity_id="activity1",
            name="Test DPIA",
            triggers=[DPIATrigger.PROFILING],
        )

        gdpr.dpia.start_assessment(dpia_id, "Assessor")
        gdpr.dpia.document_necessity(
            dpia_id, "Necessary", "Proportionate"
        )

        risk_id = gdpr.dpia.add_risk(
            dpia_id,
            "Risk description",
            "medium", "high",
            ["privacy"],
        )

        gdpr.dpia.add_mitigation(
            dpia_id, risk_id,
            "Mitigation", "technical", "low",
        )

        gdpr.dpia.consult_dpo(
            dpia_id, "DPO Name", "Opinion", "approve"
        )

        gdpr.dpia.complete_dpia(
            dpia_id, "low", "Approver"
        )

        dpia = gdpr.dpia.get_dpia(dpia_id)
        assert dpia["status"] == "completed"


class TestInternationalTransferStore:
    """Tests for InternationalTransferStore"""

    def test_adequacy_check(self, gdpr):
        """Test checking adequacy decisions"""
        uk_check = gdpr.transfer.check_adequacy("United Kingdom")
        assert uk_check["has_adequacy_decision"] is True

        us_check = gdpr.transfer.check_adequacy("United States")
        assert us_check["has_adequacy_decision"] is False

    def test_register_transfer(self, gdpr):
        """Test registering a transfer"""
        transfer_id = gdpr.transfer.register_transfer(
            name="US Transfer",
            source_country="Germany",
            destination_country="United States",
            recipient_name="US Provider",
            recipient_type=ActorRole.PROCESSOR,
            mechanism=TransferMechanism.STANDARD_CLAUSES,
            data_categories=[PersonalDataCategory.BASIC_IDENTITY],
            processing_activity_id="activity1",
            purpose="Cloud hosting",
        )

        assert transfer_id is not None
        transfer = gdpr.transfer.get_transfer(transfer_id)
        assert transfer["tia_required"] == "True"
        assert transfer["has_adequacy"] == "False"


class TestGDPRGovernanceEngine:
    """Tests for main GDPRGovernance engine"""

    def test_compliance_status(self, gdpr):
        """Test compliance status generation"""
        status = gdpr.get_compliance_status()

        assert "compliance_score" in status
        assert "summary" in status
        assert "issues" in status

    def test_handle_erasure_request(self, gdpr):
        """Test coordinated erasure handling"""
        # Setup
        gdpr.data_subjects.register_subject("user001")
        gdpr.consent.record_consent("user001", "marketing")

        # Handle erasure
        result = gdpr.handle_erasure_request("user001")

        assert result["status"] == "completed"

    def test_export_ropa(self, gdpr):
        """Test ROPA export"""
        gdpr.processing.register_activity(
            name="Activity 1",
            purpose="Purpose 1",
            lawful_basis=LawfulBasis.CONSENT,
            data_categories=[PersonalDataCategory.BASIC_IDENTITY],
            data_subjects=["customers"],
            recipients=["internal"],
            retention_period="1 year",
            security_measures=["encryption"],
            controller_id="controller1",
        )

        ropa = gdpr.export_ropa()
        assert len(ropa) == 1
        assert ropa[0]["name"] == "Activity 1"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
