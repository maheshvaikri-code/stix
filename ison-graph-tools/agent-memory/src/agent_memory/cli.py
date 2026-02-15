"""
Agent Memory CLI - Command-line interface for memory management
"""

import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree

from .memory import AgentMemory


console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main():
    """Agent Memory - Persistent memory system for coding agents"""
    pass


# =============================================================================
# Memory Management
# =============================================================================

@main.command()
@click.argument("name")
@click.option("-o", "--output", default=None, help="Output file path")
def init(name: str, output: Optional[str]):
    """Initialize a new memory store for a project"""
    memory = AgentMemory(name=name)

    output_path = output or f"{name}.memory"
    memory.save(output_path)

    console.print(f"[green]Initialized memory store: {output_path}[/green]")
    console.print(f"Project: {name}")


@main.command()
@click.argument("memory_file")
def stats(memory_file: str):
    """Show memory statistics"""
    try:
        memory = AgentMemory.load(memory_file)
        all_stats = memory.get_stats()

        console.print()
        console.print(Panel(f"[bold]Memory: {all_stats['name']}[/bold]"))

        # Overview table
        overview = Table(title="Overview")
        overview.add_column("Metric", style="cyan")
        overview.add_column("Value", justify="right", style="green")
        overview.add_row("Total Nodes", str(all_stats["total_nodes"]))
        overview.add_row("Total Edges", str(all_stats["total_edges"]))
        console.print(overview)

        # Store breakdown
        stores = Table(title="Memory Stores")
        stores.add_column("Store", style="cyan")
        stores.add_column("Items", justify="right", style="green")

        for store_name, store_stats in all_stats["stores"].items():
            total = sum(v for v in store_stats.values() if isinstance(v, int))
            stores.add_row(store_name, str(total))

        console.print(stores)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("memory_file")
def health(memory_file: str):
    """Check memory health and get recommendations"""
    try:
        memory = AgentMemory.load(memory_file)
        health = memory._consolidator.get_memory_health()

        console.print()
        console.print(Panel("[bold]Memory Health Report[/bold]"))

        # Age distribution
        age = Table(title="Memory Age Distribution")
        age.add_column("Age", style="cyan")
        age.add_column("Count", justify="right", style="green")
        dist = health["age_distribution"]
        age.add_row("Recent (< 7 days)", str(dist["recent_7d"]))
        age.add_row("Medium (7-30 days)", str(dist["medium_30d"]))
        age.add_row("Old (> 30 days)", str(dist["old_30d_plus"]))
        console.print(age)

        # Recommendations
        if health["recommendations"]:
            console.print()
            console.print("[yellow]Recommendations:[/yellow]")
            for rec in health["recommendations"]:
                console.print(f"  - {rec}")
        else:
            console.print("[green]Memory is healthy![/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("memory_file")
def consolidate(memory_file: str):
    """Run memory consolidation"""
    try:
        memory = AgentMemory.load(memory_file)
        summary = memory._consolidator.consolidate()
        memory.save(memory_file)

        console.print()
        console.print("[green]Consolidation complete![/green]")
        console.print(f"  Decayed: {summary['decayed']}")
        console.print(f"  Strengthened: {summary['strengthened']}")
        console.print(f"  Merged: {summary['merged']}")
        console.print(f"  Archived: {summary['archived']}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# =============================================================================
# Context Queries
# =============================================================================

@main.command()
@click.argument("memory_file")
@click.argument("task")
@click.option("-f", "--files", multiple=True, help="Files being modified")
@click.option("--json", "as_json", is_flag=True, help="Output as JSON")
def context(memory_file: str, task: str, files: tuple, as_json: bool):
    """Get coding context for a task"""
    try:
        memory = AgentMemory.load(memory_file)
        ctx = memory.get_context(task=task, files=list(files))

        if as_json:
            console.print(json.dumps(ctx.to_dict(), indent=2))
        else:
            console.print()
            console.print(Panel(f"[bold]Context for: {task}[/bold]"))
            console.print(ctx.to_prompt())

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("memory_file")
@click.argument("suggestion")
def check(memory_file: str, suggestion: str):
    """Check a suggestion against memory"""
    try:
        memory = AgentMemory.load(memory_file)
        warnings = memory.check_suggestion(suggestion)

        if warnings:
            console.print()
            console.print("[yellow]Warnings found:[/yellow]")
            for w in warnings:
                console.print(f"  - [{w.get('type', 'warning')}] {w}")
        else:
            console.print("[green]No conflicts found.[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# =============================================================================
# Memory Recording
# =============================================================================

@main.group()
def add():
    """Add memories"""
    pass


@add.command("convention")
@click.argument("memory_file")
@click.option("-c", "--category", required=True, help="Category (naming, imports, etc)")
@click.option("-r", "--rule", required=True, help="The convention rule")
@click.option("-e", "--enforced-by", default="manual", help="Enforcement tool")
def add_convention(memory_file: str, category: str, rule: str, enforced_by: str):
    """Add a code convention"""
    try:
        memory = AgentMemory.load(memory_file)
        conv_id = memory.conventions.add_convention(category, rule, enforced_by)
        memory.save(memory_file)

        console.print(f"[green]Added convention: {conv_id}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@add.command("decision")
@click.argument("memory_file")
@click.option("-t", "--title", required=True, help="Decision title")
@click.option("-c", "--context", required=True, help="Decision context")
@click.option("-d", "--decider", multiple=True, help="Decision makers")
def add_decision(memory_file: str, title: str, context: str, decider: tuple):
    """Add an architectural decision"""
    try:
        memory = AgentMemory.load(memory_file)
        dec_id = memory.decisions.add_decision(
            title=title,
            context=context,
            deciders=list(decider)
        )
        memory.save(memory_file)

        console.print(f"[green]Added decision: {dec_id}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@add.command("bug-pattern")
@click.argument("memory_file")
@click.option("-n", "--name", required=True, help="Pattern name")
@click.option("-s", "--signature", required=True, help="How to recognize it")
@click.option("-m", "--module", multiple=True, help="Affected modules")
def add_bug_pattern(memory_file: str, name: str, signature: str, module: tuple):
    """Add a bug pattern"""
    try:
        memory = AgentMemory.load(memory_file)
        pattern_id = memory.bugs.add_pattern(
            name=name,
            signature=signature,
            modules_affected=list(module)
        )
        memory.save(memory_file)

        console.print(f"[green]Added bug pattern: {pattern_id}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@add.command("skill")
@click.argument("memory_file")
@click.option("-n", "--name", required=True, help="Skill name")
@click.option("-c", "--category", required=True, help="Category (language, framework, etc)")
@click.option("-p", "--proficiency", default=0.5, type=float, help="Initial proficiency")
def add_skill(memory_file: str, name: str, category: str, proficiency: float):
    """Add a skill"""
    try:
        memory = AgentMemory.load(memory_file)
        skill_id = memory.skills.add_skill(
            name=name,
            category=category,
            proficiency=proficiency
        )
        memory.save(memory_file)

        console.print(f"[green]Added skill: {skill_id}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# =============================================================================
# List Commands
# =============================================================================

@main.group()
def list():
    """List memories"""
    pass


@list.command("conventions")
@click.argument("memory_file")
def list_conventions(memory_file: str):
    """List all conventions"""
    try:
        memory = AgentMemory.load(memory_file)

        table = Table(title="Conventions")
        table.add_column("Category", style="cyan")
        table.add_column("Rule", style="white")
        table.add_column("Enforced By", style="green")

        for node in memory.graph.nodes():
            if node.type == "convention":
                table.add_row(
                    node.properties.get("category", ""),
                    node.properties.get("rule", ""),
                    node.properties.get("enforced_by", "")
                )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@list.command("decisions")
@click.argument("memory_file")
def list_decisions(memory_file: str):
    """List all decisions"""
    try:
        memory = AgentMemory.load(memory_file)

        table = Table(title="Decisions")
        table.add_column("Title", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Context", style="white")

        for node in memory.graph.nodes():
            if node.type == "decision":
                table.add_row(
                    node.properties.get("title", ""),
                    node.properties.get("status", ""),
                    node.properties.get("context", "")[:50] + "..."
                )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@list.command("skills")
@click.argument("memory_file")
def list_skills(memory_file: str):
    """List all skills"""
    try:
        memory = AgentMemory.load(memory_file)

        table = Table(title="Skills")
        table.add_column("Name", style="cyan")
        table.add_column("Category", style="white")
        table.add_column("Proficiency", justify="right", style="green")

        for node in memory.graph.nodes():
            if node.type == "skill":
                prof = float(node.properties.get("proficiency", 0))
                table.add_row(
                    node.properties.get("name", ""),
                    node.properties.get("category", ""),
                    f"{prof:.0%}"
                )

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# =============================================================================
# Session Management
# =============================================================================

@main.command()
@click.argument("memory_file")
@click.argument("task")
def start_session(memory_file: str, task: str):
    """Start a new coding session"""
    try:
        memory = AgentMemory.load(memory_file)
        session_id = memory.start_session(task)
        memory.save(memory_file)

        console.print(f"[green]Started session: {session_id}[/green]")
        console.print(f"Task: {task}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("memory_file")
@click.argument("session_id")
@click.option("-c", "--completion", default=1.0, type=float, help="Completion percentage")
def end_session(memory_file: str, session_id: str, completion: float):
    """End a coding session"""
    try:
        memory = AgentMemory.load(memory_file)
        memory.end_session(session_id, completion)
        memory.save(memory_file)

        console.print(f"[green]Ended session: {session_id}[/green]")
        console.print(f"Completion: {completion:.0%}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


# =============================================================================
# Export
# =============================================================================

@main.command()
@click.argument("memory_file")
@click.option("-o", "--output", required=True, help="Output file path")
@click.option("-f", "--format", "fmt", type=click.Choice(["json", "ison"]), default="json", help="Output format")
def export(memory_file: str, output: str, fmt: str):
    """Export memory to a different format"""
    try:
        memory = AgentMemory.load(memory_file)

        if fmt == "json":
            memory.export_json(output)
        else:
            memory.save(output)

        console.print(f"[green]Exported to: {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
