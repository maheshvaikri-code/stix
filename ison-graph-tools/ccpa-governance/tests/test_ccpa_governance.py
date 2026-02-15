"""
CCPA Governance Tests
=====================

Unit tests for CCPA compliance governance.
"""

import pytest
import sys
sys.path.insert(0, "../src")

from ison_graph import ISONGraph
from ccpa_governance import (
    CCPAGovernance,
    PersonalInfoCategory,
    ConsumerRight,
    RequestStatus,
    DenialReason,
    NoticeType,
    BusinessRole,
    BusinessSize,
    OptOutStatus,
)


@pytest.fixture
def graph():
    """Create fresh ISONGraph for each test"""
    return ISONGraph()


@pytest.fixture
def ccpa(graph):
    """Create CCPA governance instance"""
    return CCPAGovernance(graph)


class TestConsumerStore:
    """Tests for ConsumerStore"""

    def test_register_consumer(self, ccpa):
        """Test registering a consumer"""
        consumer_id = ccpa.consumers.register_consumer(
            consumer_id="test001",
            email="test@example.com",
            is_california_resident=True,
        )
        assert consumer_id == "consumer_test001"

        consumer = ccpa.consumers.get_consumer("test001")
        assert consumer is not None
        assert consumer["email"] == "test@example.com"
        assert consumer["is_california_resident"] == "True"

    def test_add_personal_info(self, ccpa):
        """Test adding PI to a consumer"""
        ccpa.consumers.register_consumer(consumer_id="test001")

        pi_id = ccpa.consumers.add_personal_info(
            consumer_id="test001",
            category=PersonalInfoCategory.IDENTIFIERS,
            source="registration",
            purpose="service_delivery",
        )

        assert pi_id is not None
        inventory = ccpa.consumers.get_consumer_pi_inventory("test001")
        assert len(inventory) == 1
        assert inventory[0]["category"] == "identifiers"

    def test_opt_out_status(self, ccpa):
        """Test opt-out status updates"""
        ccpa.consumers.register_consumer(consumer_id="test001")

        # Opt out of sale
        result = ccpa.consumers.update_opt_out_status(
            consumer_id="test001",
            opt_out_sale=True,
            method="website",
        )

        assert result["opt_out_sale"] is True

        status = ccpa.consumers.check_opt_out_status("test001")
        assert status["can_sell"] is False

    def test_gpc_signal(self, ccpa):
        """Test Global Privacy Control handling"""
        ccpa.consumers.register_consumer(consumer_id="test001")

        result = ccpa.consumers.update_opt_out_status(
            consumer_id="test001",
            gpc_detected=True,
        )

        status = ccpa.consumers.check_opt_out_status("test001")
        assert status["gpc_detected"] is True
        assert status["can_sell"] is False  # GPC should block sale

    def test_delete_pi(self, ccpa):
        """Test deleting consumer PI"""
        ccpa.consumers.register_consumer(consumer_id="test001")
        ccpa.consumers.add_personal_info(
            consumer_id="test001",
            category=PersonalInfoCategory.IDENTIFIERS,
            source="form",
            purpose="service",
        )

        result = ccpa.consumers.delete_consumer_pi(
            consumer_id="test001",
            reason="consumer_request",
        )

        assert result["deleted_count"] == 1
        inventory = ccpa.consumers.get_consumer_pi_inventory("test001")
        assert len(inventory) == 0


class TestConsumerRightsStore:
    """Tests for ConsumerRightsStore"""

    def test_submit_request(self, ccpa):
        """Test submitting a consumer request"""
        request_id = ccpa.rights.submit_request(
            consumer_id="test001",
            right_type=ConsumerRight.RIGHT_TO_KNOW,
        )

        assert request_id is not None
        request = ccpa.rights.get_request(request_id)
        assert request["status"] == RequestStatus.RECEIVED.value
        assert request["right_type"] == "right_to_know"

    def test_request_lifecycle(self, ccpa):
        """Test full request lifecycle"""
        request_id = ccpa.rights.submit_request(
            consumer_id="test001",
            right_type=ConsumerRight.RIGHT_TO_DELETE,
        )

        # Verify
        ccpa.rights.verify_consumer(
            request_id=request_id,
            verification_method="email",
            verified_by="support",
        )

        request = ccpa.rights.get_request(request_id)
        assert request["status"] == RequestStatus.IN_PROGRESS.value

        # Complete
        ccpa.rights.complete_request(
            request_id=request_id,
            response="Data deleted",
            actions_taken=["deleted_pi"],
        )

        request = ccpa.rights.get_request(request_id)
        assert request["status"] == RequestStatus.COMPLETED.value

    def test_45_day_deadline(self, ccpa):
        """Test that deadline is set to 45 days"""
        from datetime import datetime, timedelta

        request_id = ccpa.rights.submit_request(
            consumer_id="test001",
            right_type=ConsumerRight.RIGHT_TO_KNOW,
        )

        request = ccpa.rights.get_request(request_id)
        deadline = datetime.fromisoformat(request["deadline"])
        received = datetime.fromisoformat(request["received_at"])

        # Should be approximately 45 days
        diff = (deadline - received).days
        assert 44 <= diff <= 46

    def test_extend_deadline(self, ccpa):
        """Test extending deadline by additional 45 days"""
        request_id = ccpa.rights.submit_request(
            consumer_id="test001",
            right_type=ConsumerRight.RIGHT_TO_KNOW,
        )

        result = ccpa.rights.extend_deadline(
            request_id=request_id,
            reason="Complex request",
        )

        assert "new_deadline" in result
        request = ccpa.rights.get_request(request_id)
        assert request["extended"] == "True"


class TestSaleShareStore:
    """Tests for SaleShareStore"""

    def test_record_sale(self, ccpa):
        """Test recording a PI sale"""
        ccpa.consumers.register_consumer(consumer_id="test001")
        ccpa.sale_share.register_recipient(
            recipient_id="third_party",
            name="Third Party Co",
            role=BusinessRole.THIRD_PARTY,
        )

        result = ccpa.sale_share.record_sale(
            consumer_id="test001",
            recipient_id="third_party",
            pi_categories=[PersonalInfoCategory.IDENTIFIERS],
            purpose="advertising",
        )

        assert "sale_id" in result

    def test_sale_blocked_by_opt_out(self, ccpa):
        """Test that sale is blocked when consumer opted out"""
        ccpa.consumers.register_consumer(consumer_id="test001")
        ccpa.consumers.update_opt_out_status(
            consumer_id="test001",
            opt_out_sale=True,
        )
        ccpa.sale_share.register_recipient(
            recipient_id="third_party",
            name="Third Party",
            role=BusinessRole.THIRD_PARTY,
        )

        result = ccpa.sale_share.record_sale(
            consumer_id="test001",
            recipient_id="third_party",
            pi_categories=[PersonalInfoCategory.IDENTIFIERS],
            purpose="advertising",
        )

        assert "error" in result
        assert result["sale_blocked"] is True

    def test_record_share(self, ccpa):
        """Test recording PI sharing for advertising"""
        ccpa.consumers.register_consumer(consumer_id="test001")
        ccpa.sale_share.register_recipient(
            recipient_id="ad_partner",
            name="Ad Partner",
            role=BusinessRole.THIRD_PARTY,
        )

        result = ccpa.sale_share.record_share(
            consumer_id="test001",
            recipient_id="ad_partner",
            pi_categories=[PersonalInfoCategory.INTERNET_ACTIVITY],
            advertising_purpose="behavioral_ads",
        )

        assert "share_id" in result


class TestNoticeStore:
    """Tests for NoticeStore"""

    def test_create_notice(self, ccpa):
        """Test creating a notice"""
        notice_id = ccpa.notices.create_notice(
            notice_type=NoticeType.PRIVACY_POLICY,
            version="1.0",
            effective_date="2024-01-01",
            content_summary="Privacy policy",
        )

        assert notice_id is not None
        notice = ccpa.notices.get_current_notice(NoticeType.PRIVACY_POLICY)
        assert notice is not None
        assert notice["version"] == "1.0"

    def test_notice_compliance_check(self, ccpa):
        """Test notice compliance checking"""
        # Create required notices
        ccpa.notices.create_notice(
            notice_type=NoticeType.PRIVACY_POLICY,
            version="1.0",
            effective_date="2024-01-01",
            content_summary="Policy",
        )
        ccpa.notices.create_notice(
            notice_type=NoticeType.NOTICE_AT_COLLECTION,
            version="1.0",
            effective_date="2024-01-01",
            content_summary="Collection notice",
        )
        ccpa.notices.create_notice(
            notice_type=NoticeType.DO_NOT_SELL_LINK,
            version="1.0",
            effective_date="2024-01-01",
            content_summary="DNS link",
        )
        ccpa.notices.create_notice(
            notice_type=NoticeType.LIMIT_SPI_LINK,
            version="1.0",
            effective_date="2024-01-01",
            content_summary="Limit SPI",
        )

        compliance = ccpa.notices.check_notice_compliance()
        assert compliance["all_notices_present"] is True


class TestServiceProviderStore:
    """Tests for ServiceProviderStore"""

    def test_register_service_provider(self, ccpa):
        """Test registering a service provider"""
        sp_id = ccpa.service_providers.register_service_provider(
            provider_id="sp001",
            name="Analytics Corp",
            services="Analytics",
            pi_categories=[PersonalInfoCategory.INTERNET_ACTIVITY],
            contract_date="2024-01-01",
        )

        assert sp_id == "sp001"
        sp = ccpa.service_providers.get_service_provider("sp001")
        assert sp is not None
        assert sp["name"] == "Analytics Corp"

    def test_register_contractor(self, ccpa):
        """Test registering a contractor (CPRA)"""
        contractor_id = ccpa.service_providers.register_contractor(
            contractor_id="contractor001",
            name="Email Vendor",
            services="Email delivery",
            pi_categories=[PersonalInfoCategory.IDENTIFIERS],
            contract_date="2024-01-01",
            business_purpose="email_communications",
        )

        assert contractor_id == "contractor001"

    def test_contract_compliance_check(self, ccpa):
        """Test contract compliance checking"""
        ccpa.service_providers.register_service_provider(
            provider_id="sp001",
            name="Provider",
            services="Services",
            pi_categories=[PersonalInfoCategory.IDENTIFIERS],
            contract_date="2024-01-01",
        )

        compliance = ccpa.service_providers.check_contract_compliance("sp001")
        assert compliance["compliant"] is True


class TestCCPAGovernanceEngine:
    """Tests for main CCPAGovernance engine"""

    def test_compliance_status(self, ccpa):
        """Test compliance status generation"""
        status = ccpa.get_compliance_status()

        assert "compliance_score" in status
        assert "summary" in status
        assert "issues" in status

    def test_handle_delete_request(self, ccpa):
        """Test coordinated delete request handling"""
        ccpa.consumers.register_consumer(consumer_id="test001")
        ccpa.consumers.add_personal_info(
            consumer_id="test001",
            category=PersonalInfoCategory.IDENTIFIERS,
            source="form",
            purpose="service",
        )

        result = ccpa.handle_delete_request(
            consumer_id="test001",
            verified=True,
        )

        assert result["status"] == "completed"
        assert result["deleted_count"] >= 0

    def test_process_opt_out(self, ccpa):
        """Test opt-out processing"""
        ccpa.consumers.register_consumer(consumer_id="test001")

        result = ccpa.process_opt_out(
            consumer_id="test001",
            opt_out_sale=True,
            opt_out_share=True,
        )

        assert result["opt_out_sale"] is True
        assert result["opt_out_share"] is True

    def test_can_sell_pi(self, ccpa):
        """Test can_sell_pi check"""
        ccpa.consumers.register_consumer(consumer_id="test001")

        # Initially can sell
        result = ccpa.can_sell_pi("test001")
        assert result["can_sell"] is True

        # After opt-out, cannot sell
        ccpa.process_opt_out(consumer_id="test001", opt_out_sale=True)
        result = ccpa.can_sell_pi("test001")
        assert result["can_sell"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
