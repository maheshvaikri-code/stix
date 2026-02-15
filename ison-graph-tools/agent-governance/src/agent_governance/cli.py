"""
Agent Governance CLI
====================

Command-line interface for managing agent governance.
"""

import json
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from .engine import GovernanceEngine, quick_governance

console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main():
    """Agent Governance - Comprehensive Governance for AI Agents"""
    pass


@main.command()
@click.argument("name")
@click.option("--defaults/--no-defaults", default=True, help="Set up default policies and values")
def init(name: str, defaults: bool):
    """Initialize a new governance context"""
    engine = quick_governance(name, setup_defaults=defaults)
    engine.save()

    console.print(f"[green]Initialized governance context: {name}[/green]")
    console.print(f"Saved to: {engine.path}")

    if defaults:
        console.print("\nDefaults configured:")
        console.print("  - 6 core values (safety, honesty, etc.)")
        console.print("  - 5 capabilities (read, write, execute, etc.)")
        console.print("  - 6 authority scopes")
        console.print("  - 4 risk categories")
        console.print("  - Default safety policy")


@main.command()
@click.argument("path")
def status(path: str):
    """Show governance status"""
    try:
        engine = GovernanceEngine.load(path)
    except Exception as e:
        console.print(f"[red]Error loading governance: {e}[/red]")
        return

    summary = engine.get_governance_summary()

    # Health panel
    health = summary["health"]
    health_color = "green" if health["status"] == "healthy" else "yellow" if health["status"] == "warning" else "red"
    console.print(Panel(
        f"Health Score: [bold {health_color}]{health['health_score']:.2%}[/bold {health_color}]\n"
        f"Status: {health['status']}",
        title=f"Governance: {engine.name}"
    ))

    # Stats table
    table = Table(title="Governance Statistics")
    table.add_column("Domain", style="cyan")
    table.add_column("Count", justify="right")

    stats = summary["stats"]
    table.add_row("Principals", str(stats["authority"].get("principals", 0)))
    table.add_row("Policies", str(stats["policy"].get("policies", 0)))
    table.add_row("Compliance Frameworks", str(stats["compliance"].get("frameworks", 0)))
    table.add_row("Decisions Recorded", str(stats["audit"].get("decisions", 0)))
    table.add_row("Risks Tracked", str(stats["risk"].get("risks", 0)))
    table.add_row("Capabilities", str(stats["capability"].get("capabilities", 0)))
    table.add_row("Active Incidents", str(summary.get("active_incidents", 0)))
    table.add_row("Pending Escalations", str(summary.get("pending_escalations", 0)))
    table.add_row("Compliance Gaps", str(summary.get("compliance_gaps", 0)))

    console.print(table)


@main.command()
@click.argument("path")
@click.argument("agent_id")
@click.argument("action")
@click.option("--context", "-c", default="{}", help="JSON context for the check")
def check(path: str, agent_id: str, action: str, context: str):
    """Check if an action is permitted"""
    try:
        engine = GovernanceEngine.load(path)
        ctx = json.loads(context)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    result = engine.check_action(agent_id, action, ctx)

    if result["permitted"]:
        console.print(f"[green]PERMITTED[/green]: {action}")
    else:
        console.print(f"[red]DENIED[/red]: {action}")
        console.print(f"Reason: {result['reason']}")

    if result.get("escalation_required"):
        console.print(f"[yellow]Escalation required: {result.get('escalation_level')}[/yellow]")

    console.print("\nChecks passed:", ", ".join(result.get("checks_passed", [])))
    console.print("Checks failed:", ", ".join(result.get("checks_failed", [])))


@main.command()
@click.argument("path")
def health(path: str):
    """Show detailed health metrics"""
    try:
        engine = GovernanceEngine.load(path)
    except Exception as e:
        console.print(f"[red]Error loading governance: {e}[/red]")
        return

    health = engine.get_health()

    table = Table(title="Governance Health")
    table.add_column("Component", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Weight", justify="right")
    table.add_column("Contribution", justify="right")

    for name, data in health.get("components", {}).items():
        score = data.get("score", 0)
        color = "green" if score >= 0.9 else "yellow" if score >= 0.7 else "red"
        table.add_row(
            name,
            f"[{color}]{score:.2%}[/{color}]",
            f"{data.get('weight', 0):.2f}",
            f"{data.get('contribution', 0):.4f}"
        )

    console.print(table)

    health_color = "green" if health["status"] == "healthy" else "yellow" if health["status"] == "warning" else "red"
    console.print(f"\nOverall: [{health_color}]{health['health_score']:.2%} ({health['status']})[/{health_color}]")


@main.command()
@click.argument("path")
def risks(path: str):
    """Show risk posture"""
    try:
        engine = GovernanceEngine.load(path)
    except Exception as e:
        console.print(f"[red]Error loading governance: {e}[/red]")
        return

    posture = engine.assess_risk_posture()

    console.print(Panel(
        f"Posture: [bold]{posture.get('posture', 'unknown')}[/bold]\n"
        f"Average Residual Score: {posture.get('average_residual_score', 0):.2%}",
        title="Risk Posture"
    ))

    table = Table(title="Risk Summary")
    table.add_column("Level", style="cyan")
    table.add_column("Count", justify="right")

    levels = posture.get("by_level", {})
    for level in ["critical", "high", "medium", "low"]:
        color = "red" if level == "critical" else "yellow" if level == "high" else "blue" if level == "medium" else "green"
        table.add_row(f"[{color}]{level.upper()}[/{color}]", str(levels.get(level, 0)))

    console.print(table)

    console.print(f"\nWithin Appetite: {posture.get('within_appetite', 0)}")
    console.print(f"Appetite Breached: {posture.get('appetite_breached', 0)}")


@main.command()
@click.argument("path")
@click.argument("agent_id")
@click.argument("name")
@click.option("--level", "-l", default="limited", help="Authority level: root, elevated, delegated, limited")
def register(path: str, agent_id: str, name: str, level: str):
    """Register a new agent"""
    try:
        engine = GovernanceEngine.load(path)
    except Exception as e:
        console.print(f"[red]Error loading governance: {e}[/red]")
        return

    from .schema import AuthorityLevel

    level_map = {
        "root": AuthorityLevel.ROOT,
        "elevated": AuthorityLevel.ELEVATED,
        "delegated": AuthorityLevel.DELEGATED,
        "limited": AuthorityLevel.LIMITED,
    }

    auth_level = level_map.get(level, AuthorityLevel.LIMITED)
    engine.register_agent(agent_id, name, auth_level)
    engine.save()

    console.print(f"[green]Registered agent: {name} ({agent_id})[/green]")
    console.print(f"Authority level: {level}")


@main.command()
@click.argument("path")
def incidents(path: str):
    """List active incidents"""
    try:
        engine = GovernanceEngine.load(path)
    except Exception as e:
        console.print(f"[red]Error loading governance: {e}[/red]")
        return

    from .schema import IncidentStatus

    active = engine.incident.list_incidents(status=IncidentStatus.ACTIVE)

    if not active:
        console.print("[green]No active incidents[/green]")
        return

    table = Table(title="Active Incidents")
    table.add_column("ID", style="cyan")
    table.add_column("Severity")
    table.add_column("Category")
    table.add_column("Phase")
    table.add_column("Detected")

    for inc in active:
        severity = inc.get("severity", "unknown")
        color = "red" if severity == "critical" else "yellow" if severity == "high" else "blue"
        table.add_row(
            inc["id"],
            f"[{color}]{severity}[/{color}]",
            inc.get("category", ""),
            inc.get("current_phase", ""),
            inc.get("detected_at", "")[:19]
        )

    console.print(table)


@main.command()
@click.argument("path")
def escalations(path: str):
    """List pending escalations"""
    try:
        engine = GovernanceEngine.load(path)
    except Exception as e:
        console.print(f"[red]Error loading governance: {e}[/red]")
        return

    pending = engine.escalation.list_escalations(status="pending")

    if not pending:
        console.print("[green]No pending escalations[/green]")
        return

    table = Table(title="Pending Escalations")
    table.add_column("ID", style="cyan")
    table.add_column("Level")
    table.add_column("Assigned To")
    table.add_column("Created")

    for esc in pending:
        table.add_row(
            esc["id"],
            esc.get("level", ""),
            esc.get("assigned_to", "unassigned"),
            esc.get("created_at", "")[:19]
        )

    console.print(table)


if __name__ == "__main__":
    main()
