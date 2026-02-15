"""
PII Governance Tests
====================

Unit tests for PII governance.
"""

import pytest
import sys
sys.path.insert(0, "../src")

from ison_graph import ISONGraph
from pii_governance import (
    PIIGovernance,
    PIIType,
    PIICategory,
    SensitivityLevel,
    ProtectionStatus,
    DataSourceType,
    StorageLocation,
    Regulation,
    RiskLevel,
    DetectionConfidence,
)


@pytest.fixture
def graph():
    """Create fresh ISONGraph for each test"""
    return ISONGraph()


@pytest.fixture
def pii(graph):
    """Create PII governance instance"""
    return PIIGovernance(graph)


class TestClassificationStore:
    """Tests for ClassificationStore"""

    def test_classify_email_from_values(self, pii):
        """Test email detection from sample values"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test DB",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        class_id = pii.classification.classify_field(
            field_name="contact_info",
            field_id="users.contact",
            source_id="test_db",
            sample_values=["user@example.com", "test@test.org"],
        )

        assert class_id is not None
        classification = pii.classification.get_classification(class_id)
        assert classification["pii_type"] == PIIType.EMAIL.value

    def test_classify_ssn_from_values(self, pii):
        """Test SSN detection from sample values"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test DB",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        class_id = pii.classification.classify_field(
            field_name="tax_id",
            field_id="users.tax_id",
            source_id="test_db",
            sample_values=["123-45-6789", "987-65-4321"],
        )

        classification = pii.classification.get_classification(class_id)
        assert classification["pii_type"] == PIIType.SSN.value
        assert classification["sensitivity"] == SensitivityLevel.TOP_SECRET.value

    def test_classify_from_column_name(self, pii):
        """Test classification from column name inference"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test DB",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        class_id = pii.classification.classify_field(
            field_name="customer_email_address",
            field_id="customers.email",
            source_id="test_db",
        )

        classification = pii.classification.get_classification(class_id)
        assert classification["pii_type"] == PIIType.EMAIL.value

    def test_detect_pii_in_text(self, pii):
        """Test PII detection in free text"""
        text = "Contact: john@email.com, SSN: 123-45-6789, IP: 192.168.1.1"

        detections = pii.classification.detect_pii_in_text(text)

        assert len(detections) >= 3
        pii_types = [d["pii_type"] for d in detections]
        assert PIIType.EMAIL.value in pii_types
        assert PIIType.SSN.value in pii_types
        assert PIIType.IP_ADDRESS.value in pii_types

    def test_verify_classification(self, pii):
        """Test manual verification of classification"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test DB",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        class_id = pii.classification.classify_field(
            field_name="id_number",
            field_id="users.id",
            source_id="test_db",
        )

        # Verify as passport number
        result = pii.classification.verify_classification(
            classification_id=class_id,
            verified_type=PIIType.PASSPORT_NUMBER,
            verified_by="analyst",
        )

        assert result["verified"] is True
        classification = pii.classification.get_classification(class_id)
        assert classification["pii_type"] == PIIType.PASSPORT_NUMBER.value


class TestInventoryStore:
    """Tests for InventoryStore"""

    def test_register_data_source(self, pii):
        """Test registering a data source"""
        source_id = pii.inventory.register_data_source(
            source_id="customer_db",
            name="Customer Database",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="data_team",
        )

        assert source_id == "customer_db"
        source = pii.inventory.get_data_source("customer_db")
        assert source is not None
        assert source["name"] == "Customer Database"

    def test_add_inventory_item(self, pii):
        """Test adding inventory item"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        item_id = pii.inventory.add_inventory_item(
            source_id="test_db",
            pii_type="email",
            field_location="users.email",
            record_count=1000,
            sensitivity=SensitivityLevel.INTERNAL,
            protection_status=ProtectionStatus.ENCRYPTED_AT_REST,
            business_purpose="Communication",
            data_owner="marketing",
        )

        assert item_id is not None
        item = pii.inventory.get_inventory_item(item_id)
        assert item["pii_type"] == "email"

    def test_risk_calculation(self, pii):
        """Test risk level calculation"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        # High sensitivity + unprotected = critical risk
        item_id = pii.inventory.add_inventory_item(
            source_id="test_db",
            pii_type="ssn",
            field_location="users.ssn",
            record_count=1000,
            sensitivity=SensitivityLevel.TOP_SECRET,
            protection_status=ProtectionStatus.UNPROTECTED,
            business_purpose="Identity",
            data_owner="compliance",
        )

        item = pii.inventory.get_inventory_item(item_id)
        assert item["risk_level"] == RiskLevel.CRITICAL.value

    def test_update_protection_status(self, pii):
        """Test updating protection status"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        item_id = pii.inventory.add_inventory_item(
            source_id="test_db",
            pii_type="email",
            field_location="users.email",
            record_count=1000,
            sensitivity=SensitivityLevel.INTERNAL,
            protection_status=ProtectionStatus.UNPROTECTED,
            business_purpose="Communication",
            data_owner="marketing",
        )

        result = pii.inventory.update_protection_status(
            item_id=item_id,
            protection_status=ProtectionStatus.ENCRYPTED_AT_REST,
        )

        assert result["protection_status"] == ProtectionStatus.ENCRYPTED_AT_REST.value


class TestRiskAssessmentStore:
    """Tests for RiskAssessmentStore"""

    def test_create_assessment(self, pii):
        """Test creating a risk assessment"""
        assessment_id = pii.risk.create_assessment(
            name="Test Assessment",
            scope="Test scope",
            assessor="analyst",
        )

        assert assessment_id is not None
        assessment = pii.risk.get_assessment(assessment_id)
        assert assessment["status"] == "in_progress"

    def test_calculate_risk_scores(self, pii):
        """Test risk score calculation"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        pii.inventory.add_inventory_item(
            source_id="test_db",
            pii_type="ssn",
            field_location="users.ssn",
            record_count=1000,
            sensitivity=SensitivityLevel.TOP_SECRET,
            protection_status=ProtectionStatus.ENCRYPTED_AT_REST,
            business_purpose="Identity",
            data_owner="compliance",
        )

        assessment_id = pii.risk.create_assessment(
            name="Test",
            scope="Test",
            assessor="analyst",
            data_sources=["test_db"],
        )

        scores = pii.risk.calculate_risk_scores(assessment_id)

        assert "sensitivity_score" in scores
        assert "protection_score" in scores
        assert "overall_risk_level" in scores


class TestLineageStore:
    """Tests for LineageStore"""

    def test_record_data_flow(self, pii):
        """Test recording a data flow"""
        flow_id = pii.lineage.record_data_flow(
            source_system="system_a",
            target_system="system_b",
            pii_types=["email", "phone"],
            purpose="Analytics",
        )

        assert flow_id is not None
        flow = pii.lineage.get_data_flow(flow_id)
        assert flow["source_system"] == "system_a"
        assert flow["target_system"] == "system_b"

    def test_trace_downstream(self, pii):
        """Test downstream lineage tracing"""
        pii.lineage.record_data_flow(
            source_system="db",
            target_system="warehouse",
            pii_types=["email"],
            purpose="ETL",
        )
        pii.lineage.record_data_flow(
            source_system="warehouse",
            target_system="reporting",
            pii_types=["email"],
            purpose="Reporting",
        )

        downstream = pii.lineage.trace_downstream("db")

        assert len(downstream["downstream_systems"]) >= 1

    def test_impact_analysis(self, pii):
        """Test impact analysis"""
        pii.lineage.record_data_flow(
            source_system="source",
            target_system="target1",
            pii_types=["email"],
            purpose="Flow 1",
        )
        pii.lineage.record_data_flow(
            source_system="source",
            target_system="target2",
            pii_types=["phone"],
            purpose="Flow 2",
        )

        impact = pii.lineage.impact_analysis("source")

        assert impact["affected_systems_count"] >= 2


class TestPIIGovernanceEngine:
    """Tests for main PIIGovernance engine"""

    def test_discover_and_classify(self, pii):
        """Test discovery and classification"""
        pii.inventory.register_data_source(
            source_id="test_db",
            name="Test",
            source_type=DataSourceType.DATABASE,
            storage_location=StorageLocation.ON_PREMISE,
            owner="test",
        )

        result = pii.discover_and_classify(
            source_id="test_db",
            fields=[
                {
                    "name": "email",
                    "id": "users.email",
                    "sample_values": ["test@example.com"]
                },
                {
                    "name": "ssn",
                    "id": "users.ssn",
                    "sample_values": ["123-45-6789"]
                },
            ],
        )

        assert result["pii_found"] >= 2

    def test_scan_text_for_pii(self, pii):
        """Test text scanning"""
        result = pii.scan_text_for_pii(
            "Email: test@example.com, Phone: 555-123-4567"
        )

        assert result["total_detections"] >= 2

    def test_get_governance_report(self, pii):
        """Test governance report generation"""
        report = pii.get_governance_report()

        assert "governance_score" in report
        assert "summary" in report
        assert "issues" in report

    def test_get_executive_summary(self, pii):
        """Test executive summary generation"""
        summary = pii.get_executive_summary()

        assert "PII GOVERNANCE EXECUTIVE SUMMARY" in summary
        assert "GOVERNANCE SCORE" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
