#!/usr/bin/env python3
"""
PII Governance Demo
===================

Demonstrates comprehensive PII detection, classification, and governance.
"""

import sys
sys.path.insert(0, "../src")

from ison_graph import ISONGraph
from pii_governance import (
    PIIGovernance,
    PIIType,
    SensitivityLevel,
    ProtectionStatus,
    DataSourceType,
    StorageLocation,
    Regulation,
)


def main():
    print("=" * 60)
    print("PII Governance Demo")
    print("=" * 60)

    # Initialize
    graph = ISONGraph()
    pii = PIIGovernance(graph)

    # =========================================================================
    # 1. Register Data Sources
    # =========================================================================
    print("\n1. DATA SOURCE REGISTRATION")
    print("-" * 40)

    # Customer database
    pii.inventory.register_data_source(
        source_id="customer_db",
        name="Customer Database",
        source_type=DataSourceType.DATABASE,
        storage_location=StorageLocation.ON_PREMISE,
        owner="data_engineering",
        custodian="dba_team",
        description="Primary customer information database",
    )
    print("Registered: Customer Database")

    # Analytics warehouse
    pii.inventory.register_data_source(
        source_id="analytics_dw",
        name="Analytics Data Warehouse",
        source_type=DataSourceType.DATA_WAREHOUSE,
        storage_location=StorageLocation.CLOUD_AWS,
        owner="analytics_team",
        description="Business intelligence data warehouse",
    )
    print("Registered: Analytics Data Warehouse")

    # HR system
    pii.inventory.register_data_source(
        source_id="hr_system",
        name="HR Management System",
        source_type=DataSourceType.SAAS_APPLICATION,
        storage_location=StorageLocation.CLOUD_AWS,
        owner="hr_department",
        description="Employee HR records",
    )
    print("Registered: HR Management System")

    # =========================================================================
    # 2. PII Classification
    # =========================================================================
    print("\n2. PII CLASSIFICATION")
    print("-" * 40)

    # Classify fields in customer database
    fields_to_classify = [
        {
            "name": "customer_email",
            "id": "customers.email",
            "sample_values": ["john@example.com", "jane.doe@company.org"]
        },
        {
            "name": "phone_number",
            "id": "customers.phone",
            "sample_values": ["+1-555-123-4567", "(555) 987-6543"]
        },
        {
            "name": "ssn",
            "id": "customers.ssn",
            "sample_values": ["123-45-6789", "987-65-4321"]
        },
        {
            "name": "credit_card_number",
            "id": "payments.cc_number",
            "sample_values": ["4111111111111111", "5500000000000004"]
        },
        {
            "name": "date_of_birth",
            "id": "customers.dob",
            "sample_values": ["01/15/1985", "12/25/1990"]
        },
    ]

    discovery_result = pii.discover_and_classify(
        source_id="customer_db",
        fields=fields_to_classify,
    )

    print(f"Analyzed {discovery_result['fields_analyzed']} fields")
    print(f"PII found: {discovery_result['pii_found']} fields")

    for classification in discovery_result['classifications']:
        print(f"  - {classification['field_name']}: {classification['pii_type']} "
              f"({classification['sensitivity']})")

    # =========================================================================
    # 3. Text Scanning
    # =========================================================================
    print("\n3. TEXT SCANNING FOR PII")
    print("-" * 40)

    sample_text = """
    Customer Support Ticket #12345
    Name: John Smith
    Email: john.smith@email.com
    Phone: 555-123-4567
    SSN: 123-45-6789
    Credit Card: 4111111111111111
    Address: 123 Main St, Anytown, 12345
    """

    scan_result = pii.scan_text_for_pii(sample_text)

    print(f"Text length: {scan_result['text_length']} characters")
    print(f"Total detections: {scan_result['total_detections']}")
    print(f"Unique PII types: {scan_result['unique_pii_types']}")
    print("\nDetections:")
    for detection in scan_result['detections']:
        print(f"  - {detection['pii_type']}: '{detection['matched_text']}' "
              f"at position {detection['start']}-{detection['end']}")

    # =========================================================================
    # 4. Inventory Management
    # =========================================================================
    print("\n4. PII INVENTORY")
    print("-" * 40)

    # Add inventory items
    pii.inventory.add_inventory_item(
        source_id="customer_db",
        pii_type="ssn",
        field_location="customers.ssn",
        record_count=50000,
        sensitivity=SensitivityLevel.TOP_SECRET,
        protection_status=ProtectionStatus.ENCRYPTED_AT_REST,
        business_purpose="Identity verification",
        data_owner="compliance_team",
        retention_period="7 years",
        regulations=["gdpr", "ccpa", "glba"],
    )

    pii.inventory.add_inventory_item(
        source_id="customer_db",
        pii_type="email",
        field_location="customers.email",
        record_count=150000,
        sensitivity=SensitivityLevel.INTERNAL,
        protection_status=ProtectionStatus.UNPROTECTED,
        business_purpose="Customer communication",
        data_owner="marketing_team",
        retention_period="Account lifetime + 2 years",
        regulations=["gdpr", "ccpa"],
    )

    pii.inventory.add_inventory_item(
        source_id="customer_db",
        pii_type="credit_card",
        field_location="payments.cc_number",
        record_count=75000,
        sensitivity=SensitivityLevel.RESTRICTED,
        protection_status=ProtectionStatus.TOKENIZED,
        business_purpose="Payment processing",
        data_owner="finance_team",
        retention_period="Transaction + 90 days",
        regulations=["pci_dss", "gdpr", "ccpa"],
    )

    inventory_stats = pii.inventory.get_stats()
    print(f"Total inventory items: {inventory_stats['total_inventory_items']}")
    print(f"Unprotected items: {inventory_stats['unprotected_items']}")
    print(f"By sensitivity: {inventory_stats['by_sensitivity']}")

    # =========================================================================
    # 5. Data Lineage
    # =========================================================================
    print("\n5. DATA LINEAGE")
    print("-" * 40)

    # Record data flows
    pii.lineage.record_data_flow(
        source_system="customer_db",
        target_system="analytics_dw",
        pii_types=["email", "date_of_birth", "postal_code"],
        purpose="Customer analytics and reporting",
        transformation="Aggregation and pseudonymization",
        frequency="daily",
    )
    print("Recorded flow: Customer DB -> Analytics DW")

    pii.lineage.record_data_flow(
        source_system="hr_system",
        target_system="analytics_dw",
        pii_types=["employee_id", "salary", "job_title"],
        purpose="HR analytics",
        transformation="Anonymization",
        frequency="weekly",
    )
    print("Recorded flow: HR System -> Analytics DW")

    # Trace lineage
    upstream = pii.lineage.trace_upstream("analytics_dw")
    print(f"\nUpstream systems for Analytics DW: {len(upstream['upstream_systems'])}")
    for sys in upstream['upstream_systems']:
        print(f"  - {sys['system']}: {sys['pii_types']}")

    # Impact analysis
    impact = pii.lineage.impact_analysis("customer_db")
    print(f"\nImpact analysis for Customer DB:")
    print(f"  Affected systems: {impact['affected_systems_count']}")
    print(f"  Impact level: {impact['impact_level']}")

    # =========================================================================
    # 6. Risk Assessment
    # =========================================================================
    print("\n6. RISK ASSESSMENT")
    print("-" * 40)

    assessment_result = pii.assess_data_source_risk(
        source_id="customer_db",
        assessor="privacy_team",
        regulations=[Regulation.GDPR, Regulation.CCPA, Regulation.PCI_DSS],
    )

    print(f"Assessment completed: {assessment_result['assessment_id']}")
    print(f"Scores:")
    print(f"  Sensitivity: {assessment_result['scores']['sensitivity_score']}")
    print(f"  Exposure: {assessment_result['scores']['exposure_score']}")
    print(f"  Protection: {assessment_result['scores']['protection_score']}")
    print(f"  Overall Risk: {assessment_result['scores']['overall_risk_level']}")
    print(f"Compliance gaps found: {assessment_result['compliance_gaps']['total_gaps']}")

    # =========================================================================
    # 7. PII Map
    # =========================================================================
    print("\n7. PII MAP")
    print("-" * 40)

    pii_map = pii.get_pii_map()
    print(f"Sources with PII: {pii_map['sources_with_pii']}")

    for source_id, source_info in pii_map['map'].items():
        print(f"\n  {source_id}:")
        for pii_type, fields in source_info['pii_types'].items():
            print(f"    - {pii_type}: {len(fields)} field(s)")

    # =========================================================================
    # 8. Regulation Coverage
    # =========================================================================
    print("\n8. REGULATION COVERAGE")
    print("-" * 40)

    gdpr_coverage = pii.get_regulation_coverage(Regulation.GDPR)
    print(f"GDPR covered items: {gdpr_coverage['covered_items']}")

    pci_coverage = pii.get_regulation_coverage(Regulation.PCI_DSS)
    print(f"PCI-DSS covered items: {pci_coverage['covered_items']}")

    # =========================================================================
    # 9. Governance Report
    # =========================================================================
    print("\n9. GOVERNANCE REPORT")
    print("-" * 40)

    report = pii.get_governance_report()

    print(f"Governance Score: {report['governance_score']}/100")
    print(f"\nSummary:")
    print(f"  Data Sources: {report['summary']['total_data_sources']}")
    print(f"  PII Classifications: {report['summary']['total_pii_classifications']}")
    print(f"  Unverified: {report['summary']['unverified_classifications']}")
    print(f"  Inventory Items: {report['summary']['total_inventory_items']}")
    print(f"  Unprotected: {report['summary']['unprotected_items']}")
    print(f"  Data Flows: {report['summary']['data_flows_tracked']}")

    if report['issues']:
        print(f"\nIssues ({len(report['issues'])}):")
        for issue in report['issues']:
            print(f"  [{issue['severity'].upper()}] {issue['issue']}")
            print(f"    Action: {issue['action']}")

    # =========================================================================
    # 10. Executive Summary
    # =========================================================================
    print("\n10. EXECUTIVE SUMMARY")
    print("-" * 40)
    print(pii.get_executive_summary())

    # =========================================================================
    # Save graph
    # =========================================================================
    print("\n" + "=" * 60)
    graph.save("pii_governance_demo.json")
    print("Graph saved to pii_governance_demo.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
