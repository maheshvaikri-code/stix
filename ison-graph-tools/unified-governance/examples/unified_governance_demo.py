#!/usr/bin/env python3
"""
Unified Governance Demo
=======================

Demonstrates integration of Agent, GDPR, CCPA, and PII governance.
"""

import sys
sys.path.insert(0, "../src")

from ison_graph import ISONGraph
from unified_governance import (
    UnifiedGovernanceEngine,
    quick_unified_governance,
    GovernanceDomain,
    ComplianceStatus,
    RegulationJurisdiction,
)


def main():
    print("=" * 60)
    print("Unified Governance Integration Demo")
    print("=" * 60)

    # =========================================================================
    # 1. Initialize Unified Governance
    # =========================================================================
    print("\n1. INITIALIZATION")
    print("-" * 40)

    engine = quick_unified_governance("demo", setup_defaults=True)
    print("Created UnifiedGovernanceEngine with default regulations:")
    print("  - GDPR (EU)")
    print("  - CCPA (California)")
    print("  - HIPAA (US Federal)")
    print("  - PCI-DSS (Global)")

    # =========================================================================
    # 2. Register Unified Subjects
    # =========================================================================
    print("\n2. SUBJECT UNIFICATION")
    print("-" * 40)

    # Register subjects that span GDPR and CCPA
    engine.register_subject(
        subject_id="user_alice",
        email="alice@example.com",
        name="Alice Smith",
        jurisdiction=RegulationJurisdiction.EU,
        gdpr_data_subject_id="gdpr_alice_001",
        ccpa_consumer_id=None,  # EU only
    )
    print("Registered: Alice (EU jurisdiction, GDPR only)")

    engine.register_subject(
        subject_id="user_bob",
        email="bob@example.com",
        name="Bob Johnson",
        jurisdiction=RegulationJurisdiction.US_CALIFORNIA,
        gdpr_data_subject_id=None,
        ccpa_consumer_id="ccpa_bob_001",  # California only
    )
    print("Registered: Bob (California jurisdiction, CCPA only)")

    engine.register_subject(
        subject_id="user_carol",
        email="carol@example.com",
        name="Carol Davis",
        jurisdiction=RegulationJurisdiction.GLOBAL,
        gdpr_data_subject_id="gdpr_carol_001",
        ccpa_consumer_id="ccpa_carol_001",  # Global, both regulations
    )
    print("Registered: Carol (Global jurisdiction, both GDPR and CCPA)")

    # Set consent/opt-out status
    engine.subjects.update_consent_status(
        subject_id="user_carol",
        consent_type="marketing",
        consented=True,
        source_regulation="gdpr",
    )
    engine.subjects.update_opt_out_status(
        subject_id="user_carol",
        opt_out_type="sale",
        opted_out=True,
        source_regulation="ccpa",
        method="web_form",
    )
    print("Updated Carol: GDPR marketing consent=True, CCPA sale opt-out=True")

    # =========================================================================
    # 3. Grant Agent PII Access
    # =========================================================================
    print("\n3. AGENT PII ACCESS")
    print("-" * 40)

    # Customer support agent - limited PII access
    engine.grant_agent_pii_access(
        agent_id="agent_support",
        pii_types=["email", "phone", "name"],
        purpose="customer_support",
        legal_basis="legitimate_interest",
        consent_verified=True,
    )
    print("Granted agent_support: email, phone, name access")

    # Analytics agent - broader access
    engine.grant_agent_pii_access(
        agent_id="agent_analytics",
        pii_types=["email", "date_of_birth", "postal_code"],
        purpose="analytics",
        legal_basis="consent",
        consent_verified=True,
    )
    print("Granted agent_analytics: email, dob, postal_code access")

    # Fraud detection agent - sensitive data access
    engine.grant_agent_pii_access(
        agent_id="agent_fraud",
        pii_types=["ssn", "credit_card", "financial"],
        purpose="fraud_detection",
        legal_basis="legal_obligation",
        consent_verified=False,
    )
    print("Granted agent_fraud: ssn, credit_card, financial access")

    # =========================================================================
    # 4. Compliance Checks
    # =========================================================================
    print("\n4. COMPLIANCE CHECKING")
    print("-" * 40)

    # Check 1: Support agent reading email (should pass)
    print("\nCheck 1: agent_support reading email...")
    result = engine.check_compliance(
        agent_id="agent_support",
        action="read_personal_data",
        pii_types=["email"],
        data_subject_id="user_alice",
        context={
            "gdpr": {
                "processing_purpose": "customer_support",
                "has_consent": True,
                "has_legal_basis": True,
                "data_minimized": True,
                "retention_defined": True,
            },
        },
    )
    print(f"  Permitted: {result['permitted']}")
    print(f"  Status: {result['overall_status']}")
    print(f"  Risk Level: {result['risk_level']}")

    # Check 2: Analytics agent reading SSN (should fail - no access)
    print("\nCheck 2: agent_analytics reading SSN...")
    result = engine.check_compliance(
        agent_id="agent_analytics",
        action="read_personal_data",
        pii_types=["ssn"],
        data_subject_id="user_bob",
        context={
            "ccpa": {
                "has_notice": True,
                "opt_out_honored": True,
            },
        },
    )
    print(f"  Permitted: {result['permitted']}")
    print(f"  Status: {result['overall_status']}")
    print(f"  Blocking Issues: {len(result['blocking_issues'])}")
    if result['blocking_issues']:
        for issue in result['blocking_issues']:
            print(f"    - {issue.get('issue', issue)}")

    # Check 3: Sharing data with opted-out consumer
    print("\nCheck 3: agent_support sharing Carol's data (opted out)...")

    # First, register Carol's opt-out
    engine.subjects.update_opt_out_status(
        subject_id="user_carol",
        opt_out_type="share",
        opted_out=True,
        source_regulation="ccpa",
    )

    result = engine.check_compliance(
        agent_id="agent_support",
        action="share_with_third_party",
        pii_types=["email", "phone"],
        data_subject_id="user_carol",
        context={
            "ccpa": {
                "has_notice": True,
                "opt_out_honored": False,  # Not honoring opt-out
            },
        },
    )
    print(f"  Permitted: {result['permitted']}")
    print(f"  Status: {result['overall_status']}")
    print(f"  Blocking Issues: {len(result['blocking_issues'])}")
    if result['blocking_issues']:
        for issue in result['blocking_issues']:
            print(f"    - {issue.get('issue', issue)}")

    # =========================================================================
    # 5. Quick Action Checks
    # =========================================================================
    print("\n5. QUICK ACTION CHECKS")
    print("-" * 40)

    actions_to_check = [
        ("agent_support", "read_personal_data", ["email"], "user_alice"),
        ("agent_fraud", "read_personal_data", ["ssn"], "user_bob"),
        ("agent_analytics", "transfer_data_external", ["email"], "user_carol"),
    ]

    for agent, action, pii_types, subject in actions_to_check:
        result = engine.check_agent_action(agent, action, pii_types, subject)
        status = "ALLOWED" if result["permitted"] else "BLOCKED"
        print(f"  {agent} -> {action} ({', '.join(pii_types)}): {status}")

    # =========================================================================
    # 6. Record Actions
    # =========================================================================
    print("\n6. RECORDING ACTIONS")
    print("-" * 40)

    # Record a successful action
    audit_id = engine.record_agent_action(
        agent_id="agent_support",
        action="read_personal_data",
        pii_types=["email", "phone"],
        data_source="customer_db",
        outcome="success",
        data_subject_id="user_alice",
    )
    print(f"Recorded action: {audit_id}")

    # =========================================================================
    # 7. PII Compliance Linking
    # =========================================================================
    print("\n7. PII COMPLIANCE LINKING")
    print("-" * 40)

    # Link PII types to compliance requirements
    link_result = engine.pii_compliance.link_pii_to_compliance(
        pii_inventory_item_id="inv_001",
        pii_type="ssn",
        source_id="customer_db",
        field_location="customers.ssn",
        sensitivity_level="top_secret",
        protection_status="encrypted_at_rest",
    )
    print(f"Linked SSN to compliance:")
    print(f"  Applicable regulations: {link_result['applicable_regulations']}")
    print(f"  Compliance gaps: {len(link_result['compliance_gaps'])}")
    print(f"  Risk level: {link_result['risk_level']}")

    link_result = engine.pii_compliance.link_pii_to_compliance(
        pii_inventory_item_id="inv_002",
        pii_type="email",
        source_id="customer_db",
        field_location="customers.email",
        sensitivity_level="internal",
        protection_status="unprotected",
    )
    print(f"\nLinked email to compliance:")
    print(f"  Applicable regulations: {link_result['applicable_regulations']}")
    print(f"  Compliance gaps: {len(link_result['compliance_gaps'])}")
    print(f"  Risk level: {link_result['risk_level']}")

    # =========================================================================
    # 8. Cross-Regulation Requirements
    # =========================================================================
    print("\n8. CROSS-REGULATION REQUIREMENTS")
    print("-" * 40)

    requirements = engine.regulatory.get_cross_regulation_requirements(
        pii_types=["ssn", "email", "credit_card"]
    )
    print(f"PII types analyzed: {requirements['pii_types_analyzed']}")
    print(f"Applicable regulations: {requirements['applicable_regulations']}")
    print("Requirements by regulation:")
    for reg, reqs in requirements['requirements_by_regulation'].items():
        print(f"  {reg}: {', '.join(reqs)}")

    # =========================================================================
    # 9. Subject PII Map
    # =========================================================================
    print("\n9. SUBJECT PII MAP")
    print("-" * 40)

    # Register PII locations for a subject
    engine.subjects.register_pii_location(
        subject_id="user_alice",
        source_id="customer_db",
        field_location="customers.email",
        pii_type="email",
    )
    engine.subjects.register_pii_location(
        subject_id="user_alice",
        source_id="customer_db",
        field_location="customers.phone",
        pii_type="phone",
    )
    engine.subjects.register_pii_location(
        subject_id="user_alice",
        source_id="analytics_dw",
        field_location="users.email_hash",
        pii_type="email",
    )

    pii_map = engine.subjects.get_pii_map_for_subject("user_alice")
    print(f"Alice's PII Map:")
    print(f"  Total locations: {pii_map['total_locations']}")
    print(f"  Sources: {pii_map['sources_count']}")
    for source, locations in pii_map['pii_map'].items():
        print(f"    {source}:")
        for loc in locations:
            print(f"      - {loc['pii_type']} @ {loc['field_location']}")

    # =========================================================================
    # 10. Rights Request Tracking
    # =========================================================================
    print("\n10. RIGHTS REQUEST TRACKING")
    print("-" * 40)

    # Record a GDPR access request
    engine.subjects.record_rights_request(
        subject_id="user_alice",
        request_type="access",
        source_regulation="gdpr",
        request_id="req_gdpr_001",
        deadline="2024-02-15",
        details={"article": "15"},
    )
    print("Recorded GDPR access request for Alice")

    # Record a CCPA delete request
    engine.subjects.record_rights_request(
        subject_id="user_bob",
        request_type="delete",
        source_regulation="ccpa",
        request_id="req_ccpa_001",
        deadline="2024-02-20",
        details={"section": "1798.105"},
    )
    print("Recorded CCPA delete request for Bob")

    # Get pending requests
    alice_requests = engine.subjects.get_pending_requests("user_alice")
    bob_requests = engine.subjects.get_pending_requests("user_bob")
    print(f"\nPending requests: Alice={len(alice_requests)}, Bob={len(bob_requests)}")

    # =========================================================================
    # 11. Unified Report
    # =========================================================================
    print("\n11. UNIFIED GOVERNANCE REPORT")
    print("-" * 40)

    report = engine.get_unified_report()
    health = report['health']

    print(f"Overall Health Score: {health['overall_score']}/100")
    print(f"Status: {health['status'].upper()}")
    print(f"Critical Items: {health['critical_items']}")
    print(f"High Risk Items: {health['high_risk_items']}")
    print(f"Compliance Gaps: {health['compliance_gaps']}")

    # =========================================================================
    # 12. Executive Summary
    # =========================================================================
    print("\n12. EXECUTIVE SUMMARY")
    print("-" * 40)
    print(engine.get_executive_summary())

    # =========================================================================
    # Save
    # =========================================================================
    engine.save("unified_governance_demo.json")
    print("\nGraph saved to unified_governance_demo.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
