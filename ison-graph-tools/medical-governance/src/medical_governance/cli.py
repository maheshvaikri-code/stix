"""
HIPAA Medical Governance CLI
============================

Command-line interface for HIPAA governance operations.
"""

import json
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

console = Console()


def get_engine():
    """Initialize the HIPAA Governance Engine"""
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent.parent))
        from ison_graph import ISONGraph
    except ImportError:
        console.print("[red]Error: ison_graph not found. Please install it first.[/red]")
        raise SystemExit(1)

    from . import HIPAAGovernanceEngine

    graph = ISONGraph("hipaa_governance")
    return HIPAAGovernanceEngine(graph)


@click.group()
@click.version_option(version="1.0.0")
def main():
    """HIPAA Medical Governance CLI

    Comprehensive HIPAA-compliant governance for medical AI systems.
    """
    pass


# =============================================================================
# Dashboard Commands
# =============================================================================

@main.command()
def dashboard():
    """Show compliance dashboard"""
    engine = get_engine()
    data = engine.get_compliance_dashboard()

    # Header panel
    score = data["summary"]["compliance_score"]
    score_color = "green" if score >= 80 else "yellow" if score >= 60 else "red"

    console.print(Panel(
        f"[bold {score_color}]Compliance Score: {score}/100[/bold {score_color}]",
        title="HIPAA Compliance Dashboard",
        subtitle=f"Generated: {data['generated_at'][:19]}"
    ))

    # Alerts
    if data["alerts"]:
        console.print("\n[bold red]Active Alerts:[/bold red]")
        for alert in data["alerts"]:
            severity_color = {
                "critical": "red",
                "high": "orange1",
                "medium": "yellow",
                "low": "blue"
            }.get(alert["severity"], "white")
            console.print(f"  [{severity_color}]{alert['severity'].upper()}[/{severity_color}] {alert['message']}")
    else:
        console.print("\n[green]No active alerts[/green]")

    # Summary table
    table = Table(title="\nGovernance Summary")
    table.add_column("Domain", style="cyan")
    table.add_column("Metric", style="white")
    table.add_column("Value", style="green")

    for domain, metrics in [
        ("Workforce", data["workforce"]),
        ("Patient Rights", data["patient_rights"]),
        ("Breaches", data["breaches"]),
        ("AI Systems", data["ai_systems"]),
        ("Business Associates", data["business_associates"])
    ]:
        for key, value in metrics.items():
            table.add_row(domain, key.replace("_", " ").title(), str(value))

    console.print(table)


@main.command()
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="table")
def report(output_format):
    """Generate compliance report"""
    engine = get_engine()
    report_data = engine.generate_compliance_report()

    if output_format == "json":
        console.print(json.dumps(report_data, indent=2))
    else:
        console.print(Panel(
            f"[bold]Status: {report_data['executive_summary']['overall_status'].upper()}[/bold]\n"
            f"Compliance Score: {report_data['compliance_score']}/100\n"
            f"Critical Issues: {report_data['executive_summary']['critical_issues']}\n"
            f"Total Alerts: {report_data['executive_summary']['total_alerts']}",
            title="HIPAA Compliance Report",
            subtitle=report_data['generated_at'][:19]
        ))

        # Recommendations
        if report_data["recommendations"]:
            console.print("\n[bold]Recommendations:[/bold]")
            for rec in report_data["recommendations"]:
                console.print(f"  - {rec}")


# =============================================================================
# PHI Commands
# =============================================================================

@main.group()
def phi():
    """PHI classification and de-identification"""
    pass


@phi.command("categories")
def phi_categories():
    """List PHI categories"""
    from .schema import PHICategory, SensitivityLevel

    table = Table(title="PHI Categories")
    table.add_column("Category", style="cyan")
    table.add_column("Description")

    for cat in PHICategory:
        table.add_row(cat.value, cat.name.replace("_", " ").title())

    console.print(table)

    console.print("\n[bold]Sensitivity Levels:[/bold]")
    for level in SensitivityLevel:
        console.print(f"  - {level.value}")


@phi.command("safe-harbor")
def phi_safe_harbor():
    """List Safe Harbor identifiers"""
    from .stores.phi_classification import PHIClassificationStore

    console.print(Panel(
        "\n".join([f"  {i+1}. {ident}" for i, ident in enumerate(PHIClassificationStore.SAFE_HARBOR_IDENTIFIERS)]),
        title="18 Safe Harbor Identifiers (45 CFR 164.514(b)(2))",
        subtitle="Must be removed for Safe Harbor de-identification"
    ))


# =============================================================================
# Workforce Commands
# =============================================================================

@main.group()
def workforce():
    """Workforce and training management"""
    pass


@workforce.command("list")
def workforce_list():
    """List workforce members"""
    engine = get_engine()
    members = engine.workforce.list_workforce_members()

    if not members:
        console.print("[yellow]No workforce members found[/yellow]")
        return

    table = Table(title="Workforce Members")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Role")
    table.add_column("Department")
    table.add_column("PHI Access")
    table.add_column("Status")

    for m in members:
        status_color = "green" if m.get("status") == "active" else "red"
        table.add_row(
            m.get("id", ""),
            m.get("name", ""),
            m.get("role", ""),
            m.get("department", ""),
            m.get("phi_access_level", "none"),
            f"[{status_color}]{m.get('status', '')}[/{status_color}]"
        )

    console.print(table)


@workforce.command("training")
@click.option("--expiring", type=int, help="Show training expiring in N days")
def workforce_training(expiring):
    """Show training status"""
    engine = get_engine()

    if expiring:
        records = engine.workforce.get_expiring_training(expiring)
        if not records:
            console.print(f"[green]No training expiring in {expiring} days[/green]")
            return

        table = Table(title=f"Training Expiring in {expiring} Days")
        table.add_column("Member ID")
        table.add_column("Training Type")
        table.add_column("Expires")

        for r in records:
            table.add_row(
                r.get("member_id", ""),
                r.get("training_type", ""),
                r.get("expiration_date", "")[:10]
            )

        console.print(table)
    else:
        stats = engine.workforce.get_stats()
        console.print(Panel(
            f"Total Training Records: {stats.get('training_records', 0)}",
            title="Training Overview"
        ))


# =============================================================================
# Patient Rights Commands
# =============================================================================

@main.group()
def rights():
    """Patient rights management"""
    pass


@rights.command("pending")
def rights_pending():
    """Show pending patient rights requests"""
    engine = get_engine()
    pending = engine.patient_rights.get_pending_requests()

    if not pending:
        console.print("[green]No pending patient rights requests[/green]")
        return

    table = Table(title="Pending Patient Rights Requests")
    table.add_column("ID", style="cyan")
    table.add_column("Patient")
    table.add_column("Type")
    table.add_column("Request Date")
    table.add_column("Deadline")

    for r in pending:
        table.add_row(
            r.get("id", ""),
            r.get("patient_id", ""),
            r.get("right_type", ""),
            r.get("request_date", "")[:10],
            r.get("deadline", "")[:10] if r.get("deadline") else "N/A"
        )

    console.print(table)


@rights.command("overdue")
def rights_overdue():
    """Show overdue patient rights requests"""
    engine = get_engine()
    overdue = engine.patient_rights.get_overdue_requests()

    if not overdue:
        console.print("[green]No overdue requests[/green]")
        return

    console.print(f"[bold red]WARNING: {len(overdue)} overdue patient rights requests![/bold red]")

    table = Table(title="Overdue Requests")
    table.add_column("ID", style="red")
    table.add_column("Patient")
    table.add_column("Type")
    table.add_column("Deadline")

    for r in overdue:
        table.add_row(
            r.get("id", ""),
            r.get("patient_id", ""),
            r.get("right_type", ""),
            r.get("deadline", "")[:10]
        )

    console.print(table)


# =============================================================================
# Breach Commands
# =============================================================================

@main.group()
def breach():
    """Breach notification management"""
    pass


@breach.command("list")
@click.option("--status", type=str, help="Filter by status")
def breach_list(status):
    """List breaches"""
    engine = get_engine()

    if status:
        from .schema import BreachStatus
        try:
            status_enum = BreachStatus(status)
            breaches = engine.breach.list_breaches(status_enum)
        except ValueError:
            console.print(f"[red]Invalid status: {status}[/red]")
            return
    else:
        breaches = engine.breach.list_breaches()

    if not breaches:
        console.print("[green]No breaches found[/green]")
        return

    table = Table(title="Breaches")
    table.add_column("ID", style="cyan")
    table.add_column("Status")
    table.add_column("Affected")
    table.add_column("Discovered")
    table.add_column("Deadline")

    for b in breaches:
        status_color = {
            "reported": "yellow",
            "confirmed": "red",
            "not_breach": "green",
            "notified": "blue"
        }.get(b.get("status", ""), "white")

        table.add_row(
            b.get("id", ""),
            f"[{status_color}]{b.get('status', '')}[/{status_color}]",
            str(b.get("affected_count", 0)),
            b.get("discovered_date", "")[:10],
            b.get("notification_deadline", "")[:10] if b.get("notification_deadline") else "N/A"
        )

    console.print(table)


@breach.command("notifications")
def breach_notifications():
    """Check breach notification status"""
    engine = get_engine()
    status = engine.breach.check_notification_deadlines()

    if status.get("overdue"):
        console.print(f"[bold red]CRITICAL: {len(status['overdue'])} overdue notifications![/bold red]")
        for n in status["overdue"]:
            console.print(f"  - {n.get('id')}: {n.get('recipient')} (deadline: {n.get('deadline', '')[:10]})")

    if status.get("upcoming_7_days"):
        console.print(f"\n[yellow]Upcoming in 7 days: {len(status['upcoming_7_days'])} notifications[/yellow]")
        for n in status["upcoming_7_days"]:
            console.print(f"  - {n.get('id')}: {n.get('recipient')} (deadline: {n.get('deadline', '')[:10]})")

    if not status.get("overdue") and not status.get("upcoming_7_days"):
        console.print("[green]No pending or overdue breach notifications[/green]")


# =============================================================================
# AI System Commands
# =============================================================================

@main.group()
def ai():
    """AI system governance"""
    pass


@ai.command("list")
def ai_list():
    """List AI systems"""
    engine = get_engine()
    systems = engine.ai_governance.list_ai_systems()

    if not systems:
        console.print("[yellow]No AI systems registered[/yellow]")
        return

    table = Table(title="AI Systems")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Risk Tier")
    table.add_column("PHI Access")
    table.add_column("Status")

    for s in systems:
        status_color = {
            "approved": "green",
            "pending_approval": "yellow",
            "suspended": "red"
        }.get(s.get("status", ""), "white")

        risk_color = {
            "critical": "red",
            "high": "orange1",
            "medium": "yellow",
            "low": "green"
        }.get(s.get("risk_tier", ""), "white")

        table.add_row(
            s.get("id", ""),
            s.get("name", ""),
            s.get("system_type", ""),
            f"[{risk_color}]{s.get('risk_tier', '')}[/{risk_color}]",
            "Yes" if s.get("phi_access_required") else "No",
            f"[{status_color}]{s.get('status', '')}[/{status_color}]"
        )

    console.print(table)


@ai.command("incidents")
def ai_incidents():
    """Show AI incidents"""
    engine = get_engine()
    incidents = engine.ai_governance.get_ai_incidents(status="open")

    if not incidents:
        console.print("[green]No open AI incidents[/green]")
        return

    table = Table(title="Open AI Incidents")
    table.add_column("ID", style="cyan")
    table.add_column("System")
    table.add_column("Type")
    table.add_column("Severity")
    table.add_column("Affected Patients")

    for i in incidents:
        sev_color = {
            "critical": "red",
            "high": "orange1",
            "medium": "yellow",
            "low": "blue"
        }.get(i.get("severity", ""), "white")

        table.add_row(
            i.get("id", ""),
            i.get("system_id", ""),
            i.get("incident_type", ""),
            f"[{sev_color}]{i.get('severity', '')}[/{sev_color}]",
            str(i.get("affected_patients", 0))
        )

    console.print(table)


# =============================================================================
# Business Associate Commands
# =============================================================================

@main.group()
def ba():
    """Business associate management"""
    pass


@ba.command("list")
def ba_list():
    """List business associates"""
    engine = get_engine()
    bas = engine.business_associate.list_business_associates()

    if not bas:
        console.print("[yellow]No business associates found[/yellow]")
        return

    table = Table(title="Business Associates")
    table.add_column("ID", style="cyan")
    table.add_column("Name")
    table.add_column("Type")
    table.add_column("Risk Tier")
    table.add_column("Service")

    for b in bas:
        risk_color = {
            "critical": "red",
            "high": "orange1",
            "medium": "yellow",
            "low": "green"
        }.get(b.get("risk_tier", ""), "white")

        table.add_row(
            b.get("id", ""),
            b.get("name", ""),
            b.get("ba_type", ""),
            f"[{risk_color}]{b.get('risk_tier', '')}[/{risk_color}]",
            b.get("service", "")
        )

    console.print(table)


@ba.command("baa-status")
def ba_baa_status():
    """Check BAA expiration status"""
    engine = get_engine()
    status = engine.business_associate.check_baa_expiration()

    if status.get("expired"):
        console.print(f"[bold red]CRITICAL: {len(status['expired'])} expired BAAs![/bold red]")
        for baa in status["expired"]:
            console.print(f"  - {baa.get('id')}: expired {baa.get('expiration_date', '')[:10]}")

    if status.get("expiring_90_days"):
        console.print(f"\n[yellow]Expiring in 90 days: {len(status['expiring_90_days'])} BAAs[/yellow]")
        for baa in status["expiring_90_days"]:
            console.print(f"  - {baa.get('id')}: expires {baa.get('expiration_date', '')[:10]}")

    if not status.get("expired") and not status.get("expiring_90_days"):
        console.print("[green]All BAAs are current[/green]")


# =============================================================================
# Stats Command
# =============================================================================

@main.command()
@click.option("--format", "output_format", type=click.Choice(["json", "table"]), default="table")
def stats(output_format):
    """Show governance statistics"""
    engine = get_engine()
    all_stats = engine.export_all_stats()

    if output_format == "json":
        console.print(json.dumps(all_stats, indent=2))
    else:
        tree = Tree("[bold]HIPAA Governance Statistics[/bold]")

        for domain, domain_stats in all_stats.items():
            branch = tree.add(f"[cyan]{domain.replace('_', ' ').title()}[/cyan]")
            for key, value in domain_stats.items():
                if isinstance(value, dict):
                    sub_branch = branch.add(key.replace("_", " ").title())
                    for k, v in value.items():
                        sub_branch.add(f"{k}: {v}")
                else:
                    branch.add(f"{key.replace('_', ' ').title()}: {value}")

        console.print(tree)


# =============================================================================
# Init Command
# =============================================================================

@main.command()
def init():
    """Initialize HIPAA governance with default configuration"""
    engine = get_engine()

    console.print("[bold]Initializing HIPAA Governance...[/bold]")

    # Add default PHI categories
    from .schema import PHICategory, SensitivityLevel

    console.print("  Adding PHI categories...")
    for cat in PHICategory:
        engine.phi.add_phi_category(
            cat.value,
            cat,
            SensitivityLevel.STANDARD,
            f"PHI category: {cat.name}"
        )

    # Add default training requirements
    from .schema import TrainingType, WorkforceRole

    console.print("  Adding training requirements...")
    all_roles = [r.value for r in WorkforceRole]

    engine.workforce.add_training_requirement(
        TrainingType.HIPAA_BASICS,
        all_roles,
        365,
        required=True
    )
    engine.workforce.add_training_requirement(
        TrainingType.PRIVACY_PRACTICES,
        all_roles,
        365,
        required=True
    )
    engine.workforce.add_training_requirement(
        TrainingType.SECURITY_AWARENESS,
        all_roles,
        365,
        required=True
    )

    # Add default consent types
    from .schema import ConsentType

    console.print("  Adding consent types...")
    engine.consent.add_consent_type(
        "general_tpo",
        ConsentType.GENERAL,
        "45 CFR 164.506",
        "Treatment, Payment, Operations",
        "implied"
    )
    engine.consent.add_consent_type(
        "research_authorization",
        ConsentType.RESEARCH,
        "45 CFR 164.508",
        "Research activities",
        "required"
    )

    console.print("[green]HIPAA Governance initialized successfully![/green]")
    console.print("\nRun 'hipaa dashboard' to view compliance status.")


if __name__ == "__main__":
    from pathlib import Path
    main()
