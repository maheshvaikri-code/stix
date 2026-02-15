#!/usr/bin/env python3
"""
EU AI Act Governance Demo
=========================

Demonstrates comprehensive EU AI Act compliance using ISONGraph.
"""

import sys
from pathlib import Path

# Add parent to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def main():
    """Run EU AI Act governance demonstration."""
    console.print(Panel.fit(
        "[bold blue]EU AI Act Governance Demo[/bold blue]\n"
        "Comprehensive compliance management with ISONGraph",
        title="EU AI Act"
    ))

    # Initialize
    try:
        from ison_graph import ISONGraph
    except ImportError:
        console.print("[red]Please install ison-graph: pip install ison-graph[/red]")
        return

    from eu_ai_act_governance import (
        EUAIActGovernanceEngine,
        AIRiskLevel, HighRiskCategory, ProhibitedPractice,
        IncidentType, IncidentSeverity,
        OversightLevel, OversightMeasure,
        GPAICategory
    )

    graph = ISONGraph()
    engine = EUAIActGovernanceEngine(graph)

    # =========================================================================
    # 1. Register High-Risk AI System (Employment)
    # =========================================================================
    console.print("\n[bold cyan]1. Registering High-Risk AI System[/bold cyan]")
    console.print("   System: AI-Powered Resume Screening Tool")

    result = engine.onboard_ai_system(
        name="ResumeScreen AI",
        version="2.0",
        provider="TechHR Solutions",
        intended_purpose="Automated screening of job applications for initial candidate selection",
        technical_description="NLP-based system analyzing CVs and matching against job requirements",
        deployment_context="Enterprise HR departments"
    )

    system_id = result["system_id"]
    console.print(f"   System ID: [green]{system_id}[/green]")
    console.print(f"   Risk Assessment: {result['risk_assessment_id']}")

    # =========================================================================
    # 2. Classify as High-Risk (Employment Category)
    # =========================================================================
    console.print("\n[bold cyan]2. Risk Classification[/bold cyan]")

    classification = engine.classify_system_risk(
        system_id=system_id,
        assessor="Chief Compliance Officer",
        high_risk_category=HighRiskCategory.EMPLOYMENT_WORKERS
    )

    console.print(f"   Risk Level: [yellow]{classification['risk_level']}[/yellow]")
    console.print(f"   Rationale: {classification['rationale']}")
    console.print(f"   Conformity Assessment Required: {classification['requires_conformity_assessment']}")

    # =========================================================================
    # 3. Prohibited Practices Screening
    # =========================================================================
    console.print("\n[bold cyan]3. Prohibited Practices Screening[/bold cyan]")

    # Screen for relevant prohibited practices
    screening_id = engine.prohibited.create_screening(
        system_id=system_id,
        screener="Ethics Review Board",
        screening_type="pre_market"
    )

    practices_to_check = [
        ProhibitedPractice.SUBLIMINAL_MANIPULATION,
        ProhibitedPractice.EXPLOITING_VULNERABILITIES,
        ProhibitedPractice.BIOMETRIC_CATEGORIZATION_SENSITIVE,
    ]

    for practice in practices_to_check:
        engine.prohibited.check_practice(
            screening_id=screening_id,
            practice=practice,
            indicators_present=[],
            evidence="No indicators found during review",
            conclusion="clear",
            checked_by="Ethics Review Board"
        )
        console.print(f"   {practice.name}: [green]Clear[/green]")

    screening_result = engine.prohibited.complete_screening(
        screening_id=screening_id,
        overall_conclusion="compliant",
        recommendations=["Continue with conformity assessment"],
        completed_by="Ethics Review Board"
    )
    console.print(f"   Overall: [green]{screening_result['market_status'].upper()}[/green]")

    # =========================================================================
    # 4. Initialize High-Risk Requirements
    # =========================================================================
    console.print("\n[bold cyan]4. High-Risk Requirements[/bold cyan]")

    requirement_ids = engine.high_risk.initialize_requirements(
        system_id=system_id,
        responsible_party="TechHR Solutions"
    )
    console.print(f"   Initialized {len(requirement_ids)} Article requirements")

    # Create risk management system
    rms_id = engine.high_risk.create_risk_management_system(
        system_id=system_id,
        owner="Risk Manager",
        methodology="ISO 31000 adapted for AI"
    )

    # Identify key risks
    risks = [
        ("technical", "Model bias against protected groups", "high", "high"),
        ("operational", "Inconsistent screening criteria", "medium", "medium"),
        ("ethical", "Lack of human oversight in decisions", "medium", "high"),
    ]

    for cat, desc, likelihood, impact in risks:
        engine.high_risk.identify_risk(
            rms_id=rms_id,
            risk_category=cat,
            risk_description=desc,
            likelihood=likelihood,
            impact=impact,
            affected_parties=["job_candidates", "employer"]
        )
        console.print(f"   Identified risk: {desc[:40]}...")

    # =========================================================================
    # 5. Data Governance
    # =========================================================================
    console.print("\n[bold cyan]5. Data Governance[/bold cyan]")

    # Register training dataset
    dataset_id = engine.data_governance.register_dataset(
        system_id=system_id,
        dataset_type="training",
        name="Historical Hiring Data 2020-2024",
        source="Internal HR systems",
        size=500000,
        format_type="structured",
        provenance="Company hiring records"
    )
    console.print(f"   Registered dataset: {dataset_id}")

    # Initialize governance requirements
    dg_ids = engine.data_governance.initialize_governance_requirements(
        system_id=system_id,
        responsible_party="Data Governance Team"
    )
    console.print(f"   Initialized {len(dg_ids)} data governance requirements")

    # Create bias monitoring
    bias_monitor_id = engine.data_governance.create_bias_monitoring(
        dataset_id=dataset_id,
        protected_attributes=["gender", "age", "ethnicity", "disability"]
    )
    console.print(f"   Created bias monitoring: {bias_monitor_id}")

    # =========================================================================
    # 6. Human Oversight Configuration
    # =========================================================================
    console.print("\n[bold cyan]6. Human Oversight[/bold cyan]")

    oversight_config_id = engine.oversight.configure_oversight(
        system_id=system_id,
        oversight_level=OversightLevel.HUMAN_ON_THE_LOOP,
        measures=[
            OversightMeasure.OVERRIDE_CAPABILITY,
            OversightMeasure.STOP_BUTTON,
            OversightMeasure.ALERT_SYSTEM,
            OversightMeasure.AUDIT_LOGGING
        ],
        rationale="Employment decisions require human review capability"
    )
    console.print(f"   Oversight level: [cyan]Human-on-the-Loop[/cyan]")

    # Register an operator
    operator_id = engine.oversight.register_operator(
        system_id=system_id,
        operator_name="Jane Smith",
        role="primary_operator",
        organization="TechHR Solutions"
    )

    # Record training
    engine.oversight.record_training(
        operator_id=operator_id,
        training_type="system_capabilities",
        training_date="2024-01-15",
        duration_hours=8,
        trainer="AI Training Department",
        assessment_score=92
    )
    console.print(f"   Operator trained: {operator_id}")

    # =========================================================================
    # 7. Prepare for Market
    # =========================================================================
    console.print("\n[bold cyan]7. Market Preparation[/bold cyan]")

    market_prep = engine.prepare_for_market(
        system_id=system_id,
        provider="TechHR Solutions",
        high_risk_category=HighRiskCategory.EMPLOYMENT_WORKERS,
        responsible_party="Compliance Team"
    )
    console.print(f"   Conformity Assessment: {market_prep['conformity_assessment_id']}")
    console.print(f"   Monitoring Plan: {market_prep['monitoring_plan_id']}")
    console.print(f"   Instructions: {market_prep['instructions_id']}")

    # =========================================================================
    # 8. Register GPAI Model
    # =========================================================================
    console.print("\n[bold cyan]8. GPAI Model Registration[/bold cyan]")
    console.print("   Model: Large Language Model for HR Applications")

    gpai_result = engine.onboard_gpai_model(
        name="HR-GPT Pro",
        version="3.0",
        provider="TechHR Solutions",
        training_compute_flops=5e23,  # Below systemic risk threshold
        parameters_count=70_000_000_000,
        capabilities=["text_generation", "summarization", "classification"]
    )

    console.print(f"   Model ID: [green]{gpai_result['model_id']}[/green]")
    console.print(f"   Category: {gpai_result['category']}")
    console.print(f"   Systemic Risk: {'Yes' if gpai_result['has_systemic_risk'] else 'No'}")
    console.print(f"   Obligations: {gpai_result['obligations_count']}")

    # =========================================================================
    # 9. Simulate Incident
    # =========================================================================
    console.print("\n[bold cyan]9. Incident Reporting[/bold cyan]")

    incident_result = engine.report_incident(
        system_id=system_id,
        incident_type=IncidentType.SAFETY_ISSUE,
        severity=IncidentSeverity.MODERATE,
        title="Systematic bias detected in candidate scoring",
        description="Analysis revealed 15% lower scores for candidates with non-Western names",
        detected_by="Internal Audit Team",
        affected_users=150
    )

    console.print(f"   Incident ID: [red]{incident_result['incident_id']}[/red]")
    console.print(f"   Requires Authority Notification: {incident_result['requires_notification']}")
    console.print(f"   Deadline: {incident_result.get('reporting_deadline', 'N/A')}")

    # Start investigation
    inv_id = engine.incidents.start_investigation(
        incident_id=incident_result["incident_id"],
        investigator="Chief Data Scientist",
        investigation_scope="Training data bias analysis"
    )
    console.print(f"   Investigation started: {inv_id}")

    # Create corrective action
    action_id = engine.incidents.create_corrective_action(
        incident_id=incident_result["incident_id"],
        action_type="immediate",
        description="Suspend automated scoring for affected candidate pool",
        responsible="HR Operations",
        due_date="2024-12-20"
    )
    console.print(f"   Corrective action: {action_id}")

    # =========================================================================
    # 10. Compliance Dashboard
    # =========================================================================
    console.print("\n[bold cyan]10. Compliance Dashboard[/bold cyan]")

    compliance = engine.get_system_compliance_status(system_id)

    table = Table(title=f"Compliance Status: {compliance.get('system_name', system_id)}")
    table.add_column("Area", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    table.add_row("Risk Level", compliance.get("risk_level", "N/A"), "")

    for area, data in compliance.get("compliance_areas", {}).items():
        if isinstance(data, dict):
            status = data.get("status", data.get("overall_status", "N/A"))
            details = ""
            if "compliance_percentage" in data:
                details = f"{data['compliance_percentage']}%"
            elif "compliance_rate" in data:
                details = f"{data['compliance_rate']}%"
            table.add_row(area.replace("_", " ").title(), str(status), details)

    console.print(table)

    overall = compliance.get("overall_compliance", {})
    score = overall.get("score", 0)
    status = overall.get("status", "not_assessed")
    color = "green" if score >= 80 else "yellow" if score >= 50 else "red"

    console.print(f"\n[bold]Overall Compliance Score:[/bold] [{color}]{score}% - {status}[/{color}]")

    # =========================================================================
    # Statistics Summary
    # =========================================================================
    console.print("\n[bold cyan]Statistics Summary[/bold cyan]")

    stats = engine.get_governance_stats()

    table = Table(title="Governance Statistics")
    table.add_column("Category", style="cyan")
    table.add_column("Metric")
    table.add_column("Value")

    # Risk classification
    risk_stats = stats.get("risk_classification", {})
    table.add_row("AI Systems", "Total", str(risk_stats.get("total_systems", 0)))
    table.add_row("", "Classified", str(risk_stats.get("classified_systems", 0)))

    # High-risk
    hr_stats = stats.get("high_risk_requirements", {})
    table.add_row("High-Risk", "Requirements", str(hr_stats.get("total_requirements", 0)))
    table.add_row("", "Risks Identified", str(hr_stats.get("identified_risks", 0)))

    # Data governance
    dg_stats = stats.get("data_governance", {})
    table.add_row("Data Governance", "Datasets", str(dg_stats.get("total_datasets", 0)))
    table.add_row("", "Bias Monitors", str(dg_stats.get("bias_monitors", 0)))

    # Human oversight
    ho_stats = stats.get("human_oversight", {})
    table.add_row("Human Oversight", "Operators", str(ho_stats.get("registered_operators", 0)))
    table.add_row("", "Interventions", str(ho_stats.get("total_interventions", 0)))

    # Incidents
    inc_stats = stats.get("incident_reporting", {})
    table.add_row("Incidents", "Total", str(inc_stats.get("total_incidents", 0)))
    table.add_row("", "Open", str(inc_stats.get("open_incidents", 0)))

    # GPAI
    gpai_stats = stats.get("gpai_governance", {})
    table.add_row("GPAI Models", "Total", str(gpai_stats.get("total_models", 0)))
    table.add_row("", "Systemic Risk", str(gpai_stats.get("systemic_risk_models", 0)))

    console.print(table)

    # =========================================================================
    # Done
    # =========================================================================
    console.print(Panel.fit(
        "[bold green]EU AI Act Governance Demo Complete[/bold green]\n\n"
        "This demonstration showed:\n"
        "- AI system registration and risk classification\n"
        "- Prohibited practices screening\n"
        "- High-risk requirements management\n"
        "- Data governance and bias monitoring\n"
        "- Human oversight configuration\n"
        "- Market preparation workflow\n"
        "- GPAI model governance\n"
        "- Incident reporting and management\n"
        "- Compliance dashboard",
        title="Summary"
    ))


if __name__ == "__main__":
    main()
