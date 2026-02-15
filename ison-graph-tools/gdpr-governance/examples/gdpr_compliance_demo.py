#!/usr/bin/env python3
"""
GDPR Governance Demo
====================

Demonstrates comprehensive GDPR compliance management using ISONGraph.
"""

import sys
sys.path.insert(0, "../src")

from ison_graph import ISONGraph
from gdpr_governance import (
    GDPRGovernance,
    LawfulBasis,
    SpecialCategoryBasis,
    PersonalDataCategory,
    ConsentType,
    DataSubjectRight,
    BreachSeverity,
    BreachType,
    DPIATrigger,
    TransferMechanism,
    ActorRole,
)


def main():
    print("=" * 60)
    print("GDPR Governance Demo")
    print("=" * 60)

    # Initialize
    graph = ISONGraph()
    gdpr = GDPRGovernance(graph)

    # =========================================================================
    # 1. Organization Setup
    # =========================================================================
    print("\n1. ORGANIZATION SETUP")
    print("-" * 40)

    gdpr.register_organization(
        name="Acme Corp",
        organization_type="controller",
        country="Germany",
        dpo_name="Jane Smith",
        dpo_email="dpo@acme.com",
    )

    controller_id = gdpr.register_controller(
        controller_id="acme_main",
        name="Acme Corporation",
        contact="privacy@acme.com",
        dpo_name="Jane Smith",
    )
    print(f"Registered controller: {controller_id}")

    processor_id = gdpr.register_processor(
        processor_id="cloud_provider",
        name="Cloud Services Inc",
        controller_id=controller_id,
        services="Data hosting and backup",
    )
    print(f"Registered processor: {processor_id}")

    # =========================================================================
    # 2. Records of Processing Activities (Article 30)
    # =========================================================================
    print("\n2. PROCESSING ACTIVITIES (Article 30)")
    print("-" * 40)

    # Marketing newsletter
    activity1 = gdpr.processing.register_activity(
        name="Marketing Newsletter",
        purpose="Send marketing communications to subscribers",
        lawful_basis=LawfulBasis.CONSENT,
        data_categories=[
            PersonalDataCategory.BASIC_IDENTITY,
            PersonalDataCategory.CONTACT,
        ],
        data_subjects=["newsletter_subscribers"],
        recipients=["marketing_team", "email_provider"],
        retention_period="Until consent withdrawn + 30 days",
        security_measures=["encryption_at_rest", "access_control", "audit_logging"],
        controller_id=controller_id,
    )
    print(f"Registered activity: Marketing Newsletter ({activity1})")

    # HR Processing with special category data
    activity2 = gdpr.processing.register_activity(
        name="Employee Health Records",
        purpose="Occupational health management and sick leave tracking",
        lawful_basis=LawfulBasis.LEGAL_OBLIGATION,
        data_categories=[
            PersonalDataCategory.BASIC_IDENTITY,
            PersonalDataCategory.HEALTH,
        ],
        data_subjects=["employees"],
        recipients=["hr_department", "occupational_health_provider"],
        retention_period="Employment duration + 7 years",
        security_measures=["encryption", "access_control", "pseudonymization"],
        controller_id=controller_id,
        special_category_basis=SpecialCategoryBasis.EMPLOYMENT_LAW,
    )
    print(f"Registered activity: Employee Health Records ({activity2})")

    # Check DPIA requirements
    activity_details = gdpr.processing.get_activity(activity2)
    print(f"  DPIA required: {activity_details['dpia_required']}")

    # =========================================================================
    # 3. Data Subject Management
    # =========================================================================
    print("\n3. DATA SUBJECT MANAGEMENT")
    print("-" * 40)

    # Register data subjects
    subject1 = gdpr.data_subjects.register_subject(
        subject_id="user001",
        email="john.doe@example.com",
        data_categories=[
            PersonalDataCategory.BASIC_IDENTITY,
            PersonalDataCategory.CONTACT,
        ],
    )
    print(f"Registered data subject: {subject1}")

    # Add data category record
    gdpr.data_subjects.add_data_category(
        subject_id="user001",
        category=PersonalDataCategory.BEHAVIORAL,
        source="website_analytics",
        purpose="personalization",
    )

    # Get data inventory
    inventory = gdpr.data_subjects.get_subject_data_inventory("user001")
    print(f"  Data categories held: {len(inventory)}")

    # =========================================================================
    # 4. Consent Management (Article 7)
    # =========================================================================
    print("\n4. CONSENT MANAGEMENT (Article 7)")
    print("-" * 40)

    # Record consent
    consent1 = gdpr.consent.record_consent(
        data_subject_id="user001",
        purpose="marketing_newsletter",
        consent_type=ConsentType.MARKETING,
        evidence="web_form_checkbox_clicked",
        privacy_policy_version="2.1",
        expires_in_days=365,
        processing_activity_id=activity1,
    )
    print(f"Recorded consent: {consent1}")

    # Check consent
    consent_check = gdpr.consent.check_consent(
        data_subject_id="user001",
        purpose="marketing_newsletter",
    )
    print(f"  Has valid consent: {consent_check['has_consent']}")

    # Withdraw consent (demonstrating Art 7(3))
    withdrawal = gdpr.consent.withdraw_consent(
        consent_id=consent1,
        reason="User requested opt-out",
    )
    print(f"  Consent withdrawn: {withdrawal['status']}")

    # =========================================================================
    # 5. Data Subject Rights (Articles 15-22)
    # =========================================================================
    print("\n5. DATA SUBJECT RIGHTS (Articles 15-22)")
    print("-" * 40)

    # Submit access request (Article 15)
    request1 = gdpr.rights.submit_request(
        data_subject_id="user001",
        right_type=DataSubjectRight.ACCESS,
        details="User requests copy of all personal data",
    )
    print(f"Access request submitted: {request1}")

    # Verify identity
    gdpr.rights.verify_identity(
        request_id=request1,
        verification_method="email_verification",
        verified_by="support_team",
    )

    # Complete the request
    gdpr.rights.complete_request(
        request_id=request1,
        response="Data export provided via secure download",
        actions_taken=["Generated data export", "Sent secure download link"],
    )
    print(f"  Request completed")

    # Handle erasure request using quick method
    erasure_result = gdpr.handle_erasure_request(
        data_subject_id="user002",
        reason="User exercising right to be forgotten",
    )
    print(f"Erasure request handled: {erasure_result['request_id']}")

    # =========================================================================
    # 6. Data Breach Management (Articles 33-34)
    # =========================================================================
    print("\n6. DATA BREACH MANAGEMENT (Articles 33-34)")
    print("-" * 40)

    # Report breach
    breach_result = gdpr.report_and_assess_breach(
        description="Unauthorized access to customer database detected",
        data_categories=[
            PersonalDataCategory.BASIC_IDENTITY,
            PersonalDataCategory.CONTACT,
        ],
        subjects_affected=150,
        severity=BreachSeverity.HIGH,
    )
    print(f"Breach reported: {breach_result['breach_id']}")
    print(f"  Severity: {breach_result['severity']}")
    print(f"  DPA notification required: {breach_result['dpa_notification_required']}")
    print(f"  Subject notification required: {breach_result['subject_notification_required']}")
    print(f"  72-hour deadline: {breach_result['72_hour_deadline']}")

    # Record containment
    gdpr.breach.record_containment(
        breach_id=breach_result['breach_id'],
        measures=["Revoked compromised credentials", "Blocked suspicious IP addresses"],
    )

    # =========================================================================
    # 7. DPIA Management (Article 35)
    # =========================================================================
    print("\n7. DPIA MANAGEMENT (Article 35)")
    print("-" * 40)

    # Create DPIA for processing with special category data
    dpia_id = gdpr.dpia.create_dpia(
        processing_activity_id=activity2,
        name="Employee Health Data Processing DPIA",
        triggers=[DPIATrigger.LARGE_SCALE_SPECIAL],
        description="Assessment for processing employee health records",
    )
    print(f"DPIA created: {dpia_id}")

    # Start assessment
    gdpr.dpia.start_assessment(dpia_id, assessor="DPO Team")

    # Document necessity
    gdpr.dpia.document_necessity(
        dpia_id=dpia_id,
        necessity_assessment="Processing is necessary for legal compliance with employment law",
        proportionality_assessment="Data minimization applied - only essential health data collected",
    )

    # Add risk
    risk_id = gdpr.dpia.add_risk(
        dpia_id=dpia_id,
        risk_description="Unauthorized access to health records",
        likelihood="medium",
        impact="high",
        affected_rights=["right_to_privacy", "protection_of_health_data"],
    )

    # Add mitigation
    gdpr.dpia.add_mitigation(
        dpia_id=dpia_id,
        risk_id=risk_id,
        mitigation_description="Implement role-based access control and encryption",
        mitigation_type="technical",
        residual_risk="low",
    )

    # Consult DPO
    gdpr.dpia.consult_dpo(
        dpia_id=dpia_id,
        dpo_name="Jane Smith",
        dpo_opinion="Processing is compliant with appropriate safeguards",
        recommendation="approve",
    )

    # Complete DPIA
    gdpr.dpia.complete_dpia(
        dpia_id=dpia_id,
        residual_risk_level="low",
        approved_by="Privacy Committee",
        next_review_days=365,
    )
    print(f"  DPIA completed and approved")

    # =========================================================================
    # 8. International Transfers (Articles 44-49)
    # =========================================================================
    print("\n8. INTERNATIONAL TRANSFERS (Articles 44-49)")
    print("-" * 40)

    # Check adequacy
    adequacy = gdpr.transfer.check_adequacy("United States")
    print(f"US adequacy decision: {adequacy['has_adequacy_decision']}")

    # Register transfer with SCCs
    transfer_id = gdpr.transfer.register_transfer(
        name="Cloud backup to US",
        source_country="Germany",
        destination_country="United States",
        recipient_name="Cloud Services Inc",
        recipient_type=ActorRole.PROCESSOR,
        mechanism=TransferMechanism.STANDARD_CLAUSES,
        data_categories=[PersonalDataCategory.BASIC_IDENTITY],
        processing_activity_id=activity1,
        purpose="Data backup and disaster recovery",
    )
    print(f"Transfer registered: {transfer_id}")

    # Record SCCs
    gdpr.transfer.record_scc(
        transfer_id=transfer_id,
        scc_version="2021/914",
        signed_date="2024-01-15",
        scc_module="Module 2 (Controller to Processor)",
    )

    # Complete TIA (required post-Schrems II)
    gdpr.transfer.complete_tia(
        transfer_id=transfer_id,
        assessment_summary="Transfer assessed for US surveillance laws impact",
        third_country_laws="FISA Section 702, EO 12333 analyzed",
        supplementary_measures=["encryption_in_transit", "encryption_at_rest", "pseudonymization"],
        risk_level="medium",
        assessor="Privacy Team",
    )
    print(f"  TIA completed")

    # Approve and activate
    gdpr.transfer.approve_transfer(transfer_id, approved_by="DPO")
    gdpr.transfer.activate_transfer(transfer_id)
    print(f"  Transfer approved and activated")

    # =========================================================================
    # 9. Compliance Reporting
    # =========================================================================
    print("\n9. COMPLIANCE REPORT")
    print("-" * 40)

    status = gdpr.get_compliance_status("acme_main")

    print(f"Compliance Score: {status['compliance_score']}/100")
    print(f"\nSummary:")
    print(f"  Processing Activities: {status['summary']['processing_activities']}")
    print(f"  Data Subjects: {status['summary']['data_subjects']}")
    print(f"  Active Consents: {status['summary']['active_consents']}")
    print(f"  Pending DSR Requests: {status['summary']['pending_requests']}")
    print(f"  Open Breaches: {status['summary']['open_breaches']}")
    print(f"  Active Transfers: {status['summary']['active_transfers']}")

    if status['issues']:
        print(f"\nCompliance Issues ({len(status['issues'])}):")
        for issue in status['issues']:
            print(f"  [{issue['severity'].upper()}] {issue['issue']}")
            print(f"    Article: {issue['article']}")
            print(f"    Action: {issue['action']}")

    # =========================================================================
    # 10. Export ROPA (Article 30 format)
    # =========================================================================
    print("\n10. RECORDS OF PROCESSING ACTIVITIES (ROPA)")
    print("-" * 40)

    ropa = gdpr.export_ropa()
    print(f"Exported {len(ropa)} processing activities")
    for activity in ropa:
        print(f"  - {activity['name']}: {activity['purpose'][:50]}...")

    # =========================================================================
    # Save graph
    # =========================================================================
    print("\n" + "=" * 60)
    graph.save("gdpr_compliance_demo.json")
    print("Graph saved to gdpr_compliance_demo.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
