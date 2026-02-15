"""
HIPAA Medical Governance Demo
=============================

Demonstrates the comprehensive HIPAA-compliant governance capabilities
for medical AI systems using ISONGraph.

This example shows:
1. PHI Classification & De-identification
2. Workforce Onboarding & Training
3. Patient Consent Management
4. AI System Governance
5. PHI Access Authorization
6. Breach Management
7. Patient Rights Handling
8. Compliance Reporting
"""

import sys
from pathlib import Path

# Add parent paths for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from ison_graph import ISONGraph
from medical_governance import (
    HIPAAGovernanceEngine,
    PHICategory,
    SensitivityLevel,
    WorkforceRole,
    AccessPurpose,
    ConsentType,
    ConsentStatus,
    AISystemType,
    RiskTier,
    PatientRight,
    TrainingType,
    BAType,
)


def main():
    print("=" * 60)
    print("HIPAA Medical Governance Demo")
    print("=" * 60)

    # Initialize ISONGraph and HIPAA Governance Engine
    graph = ISONGraph("hipaa_demo")
    engine = HIPAAGovernanceEngine(graph)

    print("\n[1] INITIALIZED HIPAA GOVERNANCE ENGINE")
    print("    - Connected to ISONGraph backend")
    print("    - 10 governance stores ready")

    # =========================================================================
    # 1. PHI Classification Setup
    # =========================================================================
    print("\n" + "-" * 60)
    print("[2] PHI CLASSIFICATION & DE-IDENTIFICATION")
    print("-" * 60)

    # Import SafeHarborAction for PHI classification
    from medical_governance.schema import SafeHarborAction

    # Add PHI data elements (not categories - we add data elements)
    engine.phi.add_data_element(
        "patient_name",
        PHICategory.DEMOGRAPHICS,
        hipaa_identifier=True,
        safe_harbor_action=SafeHarborAction.REMOVE,
        sensitivity_level=SensitivityLevel.HIGH,
        description="Patient full name - Safe Harbor identifier"
    )
    engine.phi.add_data_element(
        "ssn",
        PHICategory.IDENTIFIERS,
        hipaa_identifier=True,
        safe_harbor_action=SafeHarborAction.REMOVE,
        sensitivity_level=SensitivityLevel.CRITICAL,
        description="Social Security Number - Safe Harbor identifier"
    )
    engine.phi.add_data_element(
        "mrn",
        PHICategory.IDENTIFIERS,
        hipaa_identifier=True,
        safe_harbor_action=SafeHarborAction.REMOVE_OR_REKEY,
        sensitivity_level=SensitivityLevel.HIGH,
        description="Medical Record Number"
    )
    engine.phi.add_data_element(
        "dob",
        PHICategory.DEMOGRAPHICS,
        hipaa_identifier=True,
        safe_harbor_action=SafeHarborAction.GENERALIZE_YEAR,
        sensitivity_level=SensitivityLevel.STANDARD,
        description="Date of birth"
    )
    engine.phi.add_data_element(
        "zip",
        PHICategory.DEMOGRAPHICS,
        hipaa_identifier=True,
        safe_harbor_action=SafeHarborAction.TRUNCATE_3,
        sensitivity_level=SensitivityLevel.STANDARD,
        description="ZIP code"
    )
    engine.phi.add_data_element(
        "diagnosis",
        PHICategory.CLINICAL,
        hipaa_identifier=False,
        safe_harbor_action=SafeHarborAction.RETAIN,
        sensitivity_level=SensitivityLevel.HIGH,
        description="Medical diagnosis information"
    )
    engine.phi.add_data_element(
        "medications",
        PHICategory.CLINICAL,
        hipaa_identifier=False,
        safe_harbor_action=SafeHarborAction.RETAIN,
        sensitivity_level=SensitivityLevel.STANDARD,
        description="Prescribed medications"
    )

    print("    Added PHI data elements: patient_name, ssn, mrn, dob, zip, diagnosis, medications")

    # Demonstrate Safe Harbor de-identification
    sample_record = {
        "patient_name": "John Smith",
        "ssn": "123-45-6789",
        "mrn": "MRN-12345",
        "dob": "1985-03-15",
        "diagnosis": "Type 2 Diabetes",
        "medications": ["Metformin 500mg", "Lisinopril 10mg"],
        "zip": "12345-6789"
    }

    deidentified = engine.phi.apply_safe_harbor(sample_record)
    print(f"\n    Original record: {sample_record}")
    print(f"    De-identified:   {deidentified['data']}")
    print(f"    Elements removed: {deidentified['removed_fields']}")

    # =========================================================================
    # 2. Workforce Onboarding
    # =========================================================================
    print("\n" + "-" * 60)
    print("[3] WORKFORCE ONBOARDING & TRAINING")
    print("-" * 60)

    # Onboard workforce members
    dr_smith = engine.onboard_workforce_member(
        name="Dr. Sarah Smith",
        employee_id="EMP001",
        role=WorkforceRole.PHYSICIAN,
        department="Internal Medicine"
    )
    print(f"    Onboarded: {dr_smith['name']} ({dr_smith['role']})")
    print(f"    Required training: {dr_smith['required_training']}")

    nurse_jones = engine.onboard_workforce_member(
        name="Nurse Mike Jones",
        employee_id="EMP002",
        role=WorkforceRole.NURSE,
        department="Internal Medicine"
    )
    print(f"    Onboarded: {nurse_jones['name']} ({nurse_jones['role']})")

    # Record training completion
    engine.workforce.record_training(
        dr_smith["member_id"],
        TrainingType.HIPAA_BASICS,
        "2024-01-15",
        score=95.0,
        instructor="HIPAA Training System"
    )
    engine.workforce.record_training(
        dr_smith["member_id"],
        TrainingType.PRIVACY_PRACTICES,
        "2024-01-15",
        score=92.0
    )
    print(f"\n    Recorded HIPAA training for Dr. Smith")

    # Set PHI access level
    engine.workforce.set_phi_access_level(
        dr_smith["member_id"],
        "full",
        "HR_Director",
        "Physician requiring full PHI access for patient care"
    )
    print(f"    Set PHI access level: full")

    # =========================================================================
    # 3. Patient Consent Management
    # =========================================================================
    print("\n" + "-" * 60)
    print("[4] PATIENT CONSENT MANAGEMENT")
    print("-" * 60)

    # Add consent for a patient
    patient_id = "PAT-2024-001"

    consent_id = engine.consent.add_consent(
        patient_id,
        ConsentType.GENERAL,
        ConsentStatus.ACTIVE,
        scope="treatment_payment_operations",
        witness="Registration Staff"
    )
    print(f"    Added general TPO consent for patient {patient_id}")

    # Add research consent
    research_consent = engine.consent.add_consent(
        patient_id,
        ConsentType.RESEARCH,
        ConsentStatus.ACTIVE,
        scope="diabetes_research_study",
        expires="2025-12-31T00:00:00+00:00"
    )
    print(f"    Added research consent (expires 2025-12-31)")

    # Add consent scope
    engine.consent.add_consent_scope(
        research_consent,
        "data_elements",
        included=["diagnosis", "medications", "lab_results"],
        excluded=["psychiatric_notes", "substance_abuse"]
    )
    print(f"    Defined research consent scope")

    # Check consent
    consent_check = engine.consent.check_consent(
        patient_id, ConsentType.RESEARCH, AccessPurpose.RESEARCH
    )
    print(f"\n    Research consent check: {consent_check}")

    # =========================================================================
    # 4. AI System Governance
    # =========================================================================
    print("\n" + "-" * 60)
    print("[5] AI SYSTEM GOVERNANCE")
    print("-" * 60)

    # Onboard an AI system
    ai_system = engine.onboard_ai_system(
        name="DiabetesPredictor",
        system_type=AISystemType.DIAGNOSTIC,
        purpose="Predict diabetes progression risk",
        vendor="HealthAI Corp",
        version="2.1.0",
        phi_access_required=True,
        phi_scope={
            "categories": ["diagnosis", "medications", "lab_results"],
            "sensitivity_levels": ["standard", "high"],
            "purposes": ["treatment", "research"],
            "retention_days": 30
        }
    )
    print(f"    Onboarded AI system: {ai_system['name']}")
    print(f"    Risk tier: {ai_system['risk_tier']}")
    print(f"    Requirements: {ai_system['requirements_count']}")

    # Approve the AI system
    engine.ai_governance.approve_ai_system(
        ai_system["system_id"],
        approved_by="Privacy Officer",
        conditions=["Monthly audit review", "PHI access logging required"]
    )
    print(f"    AI system approved with conditions")

    # =========================================================================
    # 5. PHI Access Authorization
    # =========================================================================
    print("\n" + "-" * 60)
    print("[6] PHI ACCESS AUTHORIZATION")
    print("-" * 60)

    # Assign patient to physician
    engine.access.assign_patient(
        dr_smith["member_id"], patient_id, "Internal Medicine"
    )
    print(f"    Assigned patient {patient_id} to Dr. Smith")

    # Authorize PHI access for treatment
    auth_result = engine.authorize_phi_access(
        actor_id=dr_smith["member_id"],
        actor_type="workforce",
        patient_id=patient_id,
        phi_elements=["diagnosis", "medications", "patient_name"],
        purpose=AccessPurpose.TREATMENT,
        session_id="SESSION-001"
    )
    print(f"\n    Treatment access authorization:")
    print(f"    - Authorized: {auth_result['authorized']}")
    print(f"    - Allowed elements: {auth_result['allowed_elements']}")
    if auth_result['denied_elements']:
        print(f"    - Denied elements: {auth_result['denied_elements']}")

    # Try unauthorized access (research without consent scope)
    auth_result_2 = engine.authorize_phi_access(
        actor_id=dr_smith["member_id"],
        actor_type="workforce",
        patient_id=patient_id,
        phi_elements=["psychiatric_notes"],
        purpose=AccessPurpose.RESEARCH,
        session_id="SESSION-002"
    )
    print(f"\n    Research access authorization (restricted element):")
    print(f"    - Authorized: {auth_result_2['authorized']}")
    print(f"    - Denial reasons: {auth_result_2['denial_reasons']}")

    # =========================================================================
    # 6. Business Associate Management
    # =========================================================================
    print("\n" + "-" * 60)
    print("[7] BUSINESS ASSOCIATE MANAGEMENT")
    print("-" * 60)

    # Add a business associate
    ba_id = engine.business_associate.add_business_associate(
        name="CloudMed EHR",
        ba_type=BAType.CLOUD_PROVIDER,
        service="Electronic Health Records hosting",
        risk_tier=RiskTier.HIGH,
        contact_email="compliance@cloudmed.example.com"
    )
    print(f"    Added BA: CloudMed EHR")

    # Add BAA
    baa_id = engine.business_associate.add_baa(
        ba_id,
        effective_date="2024-01-01",
        expiration_date="2026-12-31",
        version="3.0",
        phi_scope=["all_phi_categories"]
    )
    print(f"    Added BAA (expires 2026-12-31)")

    # Add data flow
    engine.business_associate.add_data_flow(
        ba_id,
        direction="bidirectional",
        phi_categories=["demographics", "clinical", "billing"],
        volume="high",
        frequency="continuous",
        encryption_required=True
    )
    print(f"    Defined data flow: bidirectional, encrypted")

    # =========================================================================
    # 7. Breach Management
    # =========================================================================
    print("\n" + "-" * 60)
    print("[8] BREACH MANAGEMENT")
    print("-" * 60)

    # Report a potential breach
    breach = engine.report_breach(
        discovered_by="IT Security Team",
        description="Unauthorized access to patient records detected from external IP",
        affected_count=150,
        phi_types=["demographics", "diagnosis"]
    )
    print(f"    Reported potential breach: {breach['breach_id']}")
    print(f"    Affected count: 150")
    print(f"    Notification deadline: {breach['notification_deadline'][:10]}")

    # Perform risk assessment
    risk_result = engine.assess_breach_risk(
        breach["breach_id"],
        assessor="Privacy Officer",
        phi_nature={
            "includes_financial": False,
            "includes_clinical": True,
            "includes_identifiers": True
        },
        unauthorized_person={
            "known": False,
            "has_obligation": False
        },
        acquired_viewed={
            "evidence_of_access": True,
            "encryption_protected": False
        },
        risk_mitigated={
            "effectiveness": 0.3
        }
    )
    print(f"\n    Risk assessment completed:")
    print(f"    - Risk score: {risk_result['risk_score']:.2f}")
    print(f"    - Notification required: {risk_result['notification_required']}")

    # =========================================================================
    # 8. Patient Rights
    # =========================================================================
    print("\n" + "-" * 60)
    print("[9] PATIENT RIGHTS HANDLING")
    print("-" * 60)

    # Handle access request
    access_request = engine.handle_patient_right_request(
        patient_id,
        PatientRight.ACCESS,
        {
            "format": "electronic",
            "scope": "full_record"
        }
    )
    print(f"    Patient access request: {access_request['request_id']}")
    print(f"    Deadline: {access_request['deadline_days']} days")

    # Handle amendment request
    amendment_request = engine.handle_patient_right_request(
        patient_id,
        PatientRight.AMENDMENT,
        {
            "element": "medication_allergy",
            "proposed_change": "Add penicillin allergy",
            "reason": "Allergy not documented in initial intake"
        }
    )
    print(f"    Amendment request: {amendment_request['request_id']}")
    print(f"    Deadline: {amendment_request['deadline_days']} days")

    # =========================================================================
    # 9. Compliance Dashboard
    # =========================================================================
    print("\n" + "-" * 60)
    print("[10] COMPLIANCE DASHBOARD")
    print("-" * 60)

    dashboard = engine.get_compliance_dashboard()
    print(f"\n    Compliance Score: {dashboard['summary']['compliance_score']}/100")
    print(f"    Total Alerts: {dashboard['summary']['total_alerts']}")

    if dashboard["alerts"]:
        print(f"\n    Active Alerts:")
        for alert in dashboard["alerts"]:
            print(f"    - [{alert['severity'].upper()}] {alert['message']}")

    print(f"\n    Workforce: {dashboard['workforce']['active_members']} active members")
    print(f"    Patient Rights: {dashboard['patient_rights']['pending_requests']} pending requests")
    print(f"    Breaches: {dashboard['breaches']['pending_notifications']} pending notifications")
    print(f"    AI Systems: {dashboard['ai_systems']['approved_systems']} approved systems")

    # =========================================================================
    # 10. Generate Report
    # =========================================================================
    print("\n" + "-" * 60)
    print("[11] COMPLIANCE REPORT")
    print("-" * 60)

    report = engine.generate_compliance_report()
    print(f"\n    Report Type: {report['report_type']}")
    print(f"    Overall Status: {report['executive_summary']['overall_status']}")
    print(f"    Compliance Score: {report['compliance_score']}/100")

    print(f"\n    Recommendations:")
    for rec in report["recommendations"]:
        print(f"    - {rec}")

    # =========================================================================
    # Final Statistics
    # =========================================================================
    print("\n" + "=" * 60)
    print("DEMO COMPLETE - FINAL STATISTICS")
    print("=" * 60)

    stats = engine.export_all_stats()
    print(f"\n    PHI Elements: {stats['phi_classification'].get('total_elements', 0)}")
    print(f"    Workforce Members: {stats['workforce'].get('workforce_members', 0)}")
    print(f"    Consent Records: {stats['consent'].get('total_consents', 0)}")
    print(f"    AI Systems: {stats['ai_governance'].get('ai_systems', 0)}")
    print(f"    Audit Events: {stats['disclosure'].get('total_audit_events', 0)}")
    print(f"    Business Associates: {stats['business_associate'].get('business_associates', 0)}")
    print(f"    Breaches: {stats['breach'].get('total_breaches', 0)}")
    print(f"    Patient Rights Requests: {stats['patient_rights'].get('total_requests', 0)}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
