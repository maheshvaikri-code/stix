"""
EU AI Act Governance CLI
========================

Command-line interface for EU AI Act compliance governance.
"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

console = Console()


def get_engine():
    """Get the governance engine with ISONGraph."""
    try:
        from ison_graph import ISONGraph
        from .engine import EUAIActGovernanceEngine

        graph = ISONGraph()
        return EUAIActGovernanceEngine(graph)
    except ImportError:
        console.print("[red]Error: ison-graph package not found. Install with: pip install ison-graph[/red]")
        raise SystemExit(1)


@click.group()
@click.version_option(version="1.0.0")
def main():
    """EU AI Act Compliance Governance CLI

    Manage AI system compliance with the EU AI Act using ISONGraph.
    """
    pass


# =========================================================================
# System Management
# =========================================================================

@main.group()
def system():
    """Manage AI systems."""
    pass


@system.command("register")
@click.option("--name", required=True, help="AI system name")
@click.option("--version", required=True, help="System version")
@click.option("--provider", required=True, help="Provider name")
@click.option("--purpose", required=True, help="Intended purpose")
@click.option("--description", default="", help="Technical description")
def register_system(name, version, provider, purpose, description):
    """Register a new AI system for compliance tracking."""
    engine = get_engine()

    result = engine.onboard_ai_system(
        name=name,
        version=version,
        provider=provider,
        intended_purpose=purpose,
        technical_description=description
    )

    console.print(Panel.fit(
        f"[green]AI System Registered[/green]\n\n"
        f"System ID: [cyan]{result['system_id']}[/cyan]\n"
        f"Risk Assessment ID: {result['risk_assessment_id']}\n"
        f"Screening ID: {result['prohibited_screening_id']}",
        title="Registration Complete"
    ))

    console.print("\n[bold]Next Steps:[/bold]")
    for step in result["next_steps"]:
        console.print(f"  - {step}")


@system.command("status")
@click.argument("system_id")
def system_status(system_id):
    """Get compliance status for an AI system."""
    engine = get_engine()

    status = engine.get_system_compliance_status(system_id)

    if "error" in status:
        console.print(f"[red]Error: {status['error']}[/red]")
        return

    # Header
    console.print(Panel.fit(
        f"[bold]{status.get('system_name', system_id)}[/bold]\n"
        f"Risk Level: [cyan]{status.get('risk_level', 'Not classified')}[/cyan]\n"
        f"Classification: {status.get('classification_status', 'Pending')}",
        title="System Compliance Status"
    ))

    # Compliance areas
    table = Table(title="Compliance Areas")
    table.add_column("Area", style="cyan")
    table.add_column("Status")
    table.add_column("Score")

    for area, data in status.get("compliance_areas", {}).items():
        if isinstance(data, dict):
            area_status = data.get("status", data.get("overall_status", "N/A"))
            score = data.get("compliance_percentage", data.get("compliance_rate", data.get("compliance_score", "N/A")))
            if isinstance(score, (int, float)):
                score = f"{score}%"
            table.add_row(area.replace("_", " ").title(), str(area_status), str(score))

    console.print(table)

    # Overall compliance
    overall = status.get("overall_compliance", {})
    score = overall.get("score", 0)
    status_text = overall.get("status", "Not assessed")

    color = "green" if score >= 80 else "yellow" if score >= 50 else "red"
    console.print(f"\n[bold]Overall Compliance:[/bold] [{color}]{score}% - {status_text}[/{color}]")


@system.command("list")
@click.option("--risk-level", type=click.Choice(["UNACCEPTABLE", "HIGH", "LIMITED", "MINIMAL"]), help="Filter by risk level")
def list_systems(risk_level):
    """List all registered AI systems."""
    engine = get_engine()

    from .schema import AIRiskLevel
    risk = AIRiskLevel[risk_level] if risk_level else None

    systems = engine.risk.list_ai_systems(risk_level=risk)

    if not systems:
        console.print("[yellow]No AI systems found.[/yellow]")
        return

    table = Table(title="Registered AI Systems")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Provider")
    table.add_column("Risk Level")
    table.add_column("Status")

    for system in systems:
        table.add_row(
            system["id"],
            system.get("name", ""),
            system.get("provider", ""),
            system.get("risk_level", "Pending"),
            system.get("classification_status", "")
        )

    console.print(table)


# =========================================================================
# Risk Classification
# =========================================================================

@main.group()
def risk():
    """Risk classification commands."""
    pass


@risk.command("classify")
@click.argument("system_id")
@click.option("--assessor", required=True, help="Person performing classification")
@click.option("--category", type=click.Choice([
    "BIOMETRICS", "CRITICAL_INFRASTRUCTURE", "EDUCATION_VOCATIONAL",
    "EMPLOYMENT_WORKERS", "ESSENTIAL_SERVICES", "LAW_ENFORCEMENT",
    "MIGRATION_ASYLUM", "JUSTICE_DEMOCRACY"
]), help="High-risk category if applicable")
def classify_risk(system_id, assessor, category):
    """Classify risk level for an AI system."""
    engine = get_engine()

    from .schema import HighRiskCategory
    cat = HighRiskCategory[category] if category else None

    result = engine.classify_system_risk(
        system_id=system_id,
        assessor=assessor,
        high_risk_category=cat
    )

    console.print(Panel.fit(
        f"[bold]Risk Classification Complete[/bold]\n\n"
        f"System: [cyan]{system_id}[/cyan]\n"
        f"Risk Level: [bold]{result.get('risk_level', 'Unknown')}[/bold]\n"
        f"Rationale: {result.get('rationale', '')}",
        title="Classification Result"
    ))

    if result.get("next_steps"):
        console.print("\n[bold]Next Steps:[/bold]")
        for step in result["next_steps"]:
            console.print(f"  - {step}")


# =========================================================================
# GPAI Commands
# =========================================================================

@main.group()
def gpai():
    """General-Purpose AI model commands."""
    pass


@gpai.command("register")
@click.option("--name", required=True, help="Model name")
@click.option("--version", required=True, help="Model version")
@click.option("--provider", required=True, help="Provider name")
@click.option("--flops", required=True, type=float, help="Training compute in FLOPs")
@click.option("--parameters", type=int, help="Number of parameters")
def register_gpai(name, version, provider, flops, parameters):
    """Register a General-Purpose AI model."""
    engine = get_engine()

    result = engine.onboard_gpai_model(
        name=name,
        version=version,
        provider=provider,
        training_compute_flops=flops,
        parameters_count=parameters
    )

    console.print(Panel.fit(
        f"[green]GPAI Model Registered[/green]\n\n"
        f"Model ID: [cyan]{result['model_id']}[/cyan]\n"
        f"Category: {result['category']}\n"
        f"Systemic Risk: {'Yes' if result['has_systemic_risk'] else 'No'}\n"
        f"Obligations: {result['obligations_count']}",
        title="GPAI Registration"
    ))


@gpai.command("list")
@click.option("--systemic-risk", is_flag=True, help="Only show models with systemic risk")
def list_gpai(systemic_risk):
    """List registered GPAI models."""
    engine = get_engine()

    models = engine.gpai.list_gpai_models(
        has_systemic_risk=True if systemic_risk else None
    )

    if not models:
        console.print("[yellow]No GPAI models found.[/yellow]")
        return

    table = Table(title="GPAI Models")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Provider")
    table.add_column("Category")
    table.add_column("Systemic Risk")

    for model in models:
        table.add_row(
            model["id"],
            model.get("name", ""),
            model.get("provider", ""),
            model.get("category", ""),
            "Yes" if model.get("has_systemic_risk") else "No"
        )

    console.print(table)


# =========================================================================
# Incident Reporting
# =========================================================================

@main.group()
def incident():
    """Incident reporting commands."""
    pass


@incident.command("report")
@click.option("--system", "system_id", required=True, help="AI system ID")
@click.option("--type", "incident_type", required=True,
              type=click.Choice(["MALFUNCTION", "SAFETY_ISSUE", "SECURITY_BREACH",
                               "DEATH", "SERIOUS_INJURY", "FUNDAMENTAL_RIGHTS_VIOLATION"]),
              help="Incident type")
@click.option("--severity", required=True,
              type=click.Choice(["MINOR", "MODERATE", "MAJOR", "CRITICAL"]),
              help="Severity level")
@click.option("--title", required=True, help="Incident title")
@click.option("--description", required=True, help="Incident description")
@click.option("--reporter", required=True, help="Person reporting")
def report_incident(system_id, incident_type, severity, title, description, reporter):
    """Report a serious incident."""
    engine = get_engine()

    from .schema import IncidentType, IncidentSeverity

    result = engine.report_incident(
        system_id=system_id,
        incident_type=IncidentType[incident_type],
        severity=IncidentSeverity[severity],
        title=title,
        description=description,
        detected_by=reporter
    )

    console.print(Panel.fit(
        f"[red]Incident Reported[/red]\n\n"
        f"Incident ID: [cyan]{result['incident_id']}[/cyan]\n"
        f"Requires Notification: {'Yes' if result['requires_notification'] else 'No'}\n"
        f"Deadline: {result.get('reporting_deadline', 'N/A')}",
        title="Incident Report"
    ))

    if result.get("next_steps"):
        console.print("\n[bold]Required Actions:[/bold]")
        for step in result["next_steps"]:
            console.print(f"  - {step}")


@incident.command("list")
@click.option("--system", "system_id", help="Filter by system ID")
@click.option("--status", type=click.Choice(["DETECTED", "INVESTIGATING", "MITIGATED", "CLOSED"]),
              help="Filter by status")
def list_incidents(system_id, status):
    """List incidents."""
    engine = get_engine()

    from .schema import IncidentStatus

    if system_id:
        incidents = engine.incidents.get_system_incidents(
            system_id,
            status=IncidentStatus[status] if status else None
        )
    else:
        incidents = engine.incidents._find_nodes("incident")
        if status:
            incidents = [i for i in incidents if i.get("status") == status]

    if not incidents:
        console.print("[yellow]No incidents found.[/yellow]")
        return

    table = Table(title="Incidents")
    table.add_column("ID", style="cyan")
    table.add_column("System")
    table.add_column("Type")
    table.add_column("Severity")
    table.add_column("Status")

    for inc in incidents:
        table.add_row(
            inc["id"],
            inc.get("system_id", ""),
            inc.get("incident_type", ""),
            inc.get("severity", ""),
            inc.get("status", "")
        )

    console.print(table)


# =========================================================================
# Statistics
# =========================================================================

@main.command("stats")
def show_stats():
    """Show governance statistics."""
    engine = get_engine()

    stats = engine.get_governance_stats()

    # Systems overview
    risk_stats = stats.get("risk_classification", {})
    console.print(Panel.fit(
        f"Total Systems: {risk_stats.get('total_systems', 0)}\n"
        f"Pending Classification: {risk_stats.get('pending_classification', 0)}\n"
        f"Classified: {risk_stats.get('classified_systems', 0)}",
        title="AI Systems"
    ))

    # By risk level
    by_risk = risk_stats.get("systems_by_risk_level", {})
    if by_risk:
        table = Table(title="Systems by Risk Level")
        table.add_column("Risk Level")
        table.add_column("Count")

        for level, count in by_risk.items():
            table.add_row(level, str(count))

        console.print(table)

    # GPAI
    gpai_stats = stats.get("gpai_governance", {})
    if gpai_stats.get("total_models", 0) > 0:
        console.print(Panel.fit(
            f"Total Models: {gpai_stats.get('total_models', 0)}\n"
            f"Systemic Risk Models: {gpai_stats.get('systemic_risk_models', 0)}\n"
            f"Evaluations: {gpai_stats.get('evaluations', 0)}",
            title="GPAI Models"
        ))

    # Incidents
    incident_stats = stats.get("incident_reporting", {})
    console.print(Panel.fit(
        f"Total Incidents: {incident_stats.get('total_incidents', 0)}\n"
        f"Open Incidents: {incident_stats.get('open_incidents', 0)}\n"
        f"Overdue Notifications: {incident_stats.get('overdue_notifications', 0)}",
        title="Incidents"
    ))


if __name__ == "__main__":
    main()
