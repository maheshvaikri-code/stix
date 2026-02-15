"""
Code Flow Graph CLI - Command-line interface for code analysis
"""

import os
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from .analyzer import CodeFlowAnalyzer
from .github_loader import is_github_url


console = Console()


@click.group()
@click.version_option(version="1.0.0")
def main():
    """Code Flow Graph - Analyze code repositories and generate flow graphs"""
    pass


@main.command()
@click.argument("source")
@click.option("-o", "--output", default=None, help="Output file path")
@click.option("-f", "--format", "fmt", type=click.Choice(["ison", "json"]), default="ison", help="Output format")
@click.option("-b", "--branch", default=None, help="Git branch to analyze")
@click.option("-l", "--language", multiple=True, help="Languages to analyze (can specify multiple)")
@click.option("-n", "--name", default="code-flow", help="Name for the graph")
@click.option("-v", "--verbose", is_flag=True, help="Verbose output")
def analyze(
    source: str,
    output: Optional[str],
    fmt: str,
    branch: Optional[str],
    language: tuple,
    name: str,
    verbose: bool,
):
    """
    Analyze a repository or directory.

    SOURCE can be a GitHub URL or a local path.

    Examples:

        cfg analyze https://github.com/user/repo

        cfg analyze ./my-project -o graph.ison

        cfg analyze https://github.com/user/repo -l python -l javascript
    """
    languages = list(language) if language else None

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        try:
            analyzer = CodeFlowAnalyzer(name=name)

            if is_github_url(source):
                progress.add_task(description="Cloning repository...", total=None)
                graph = analyzer.analyze_repo(source, branch=branch, languages=languages)
            else:
                progress.add_task(description="Analyzing code...", total=None)
                graph = analyzer.analyze_path(source, languages=languages)

            stats = analyzer.get_stats()

            # Determine output path
            if output is None:
                output = f"{name}.{fmt}"

            # Export
            if fmt == "ison":
                graph.save(output)
            else:
                graph.save_json(output)

            # Print summary
            console.print()
            console.print(f"[green]Analysis complete![/green]")
            console.print()

            table = Table(title="Graph Statistics")
            table.add_column("Element", style="cyan")
            table.add_column("Count", justify="right", style="green")

            table.add_row("Files", str(stats["files"]))
            table.add_row("Modules", str(stats["modules"]))
            table.add_row("Classes", str(stats["classes"]))
            table.add_row("Functions", str(stats["functions"]))
            table.add_row("Variables", str(stats["variables"]))
            table.add_row("Total Nodes", str(stats["total_nodes"]))
            table.add_row("Total Edges", str(stats["total_edges"]))

            console.print(table)
            console.print()
            console.print(f"Output: [blue]{output}[/blue]")

        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            if verbose:
                console.print_exception()
            sys.exit(1)


@main.command()
@click.argument("graph_file")
@click.argument("query")
def query(graph_file: str, query: str):
    """
    Query an existing graph using ISONQL.

    Examples:

        cfg query graph.ison "MATCH (function) RETURN *"

        cfg query graph.ison "TRAVERSE function:main <- CALLS <- function"
    """
    try:
        from ison_graph import ISONGraph
        from ison_graph.query import QueryEngine

        # Load graph
        if graph_file.endswith(".json"):
            graph = ISONGraph.load_json(graph_file)
        else:
            graph = ISONGraph.load(graph_file)

        # Execute query
        engine = QueryEngine(graph)
        result = engine.execute(query)

        # Print results
        console.print()
        console.print(f"[green]Query Results:[/green]")
        console.print()

        if hasattr(result, "nodes"):
            for node in result.nodes:
                console.print(f"  {node.type}:{node.id}")
                for key, value in node.properties.items():
                    console.print(f"    {key}: {value}")
                console.print()
        elif hasattr(result, "edges"):
            for edge in result.edges:
                console.print(f"  {edge.source} -[{edge.rel_type}]-> {edge.target}")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("graph_file")
def stats(graph_file: str):
    """
    Show statistics for a graph file.

    Examples:

        cfg stats graph.ison
    """
    try:
        from ison_graph import ISONGraph

        # Load graph
        if graph_file.endswith(".json"):
            graph = ISONGraph.load_json(graph_file)
        else:
            graph = ISONGraph.load(graph_file)

        console.print()
        table = Table(title=f"Graph: {graph_file}")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", justify="right", style="green")

        table.add_row("Name", graph.name)
        table.add_row("Total Nodes", str(graph.node_count()))
        table.add_row("Total Edges", str(graph.edge_count()))

        # Count by type
        node_types = {}
        for node in graph.nodes():
            node_type = node.type
            node_types[node_type] = node_types.get(node_type, 0) + 1

        console.print(table)
        console.print()

        if node_types:
            type_table = Table(title="Nodes by Type")
            type_table.add_column("Type", style="cyan")
            type_table.add_column("Count", justify="right", style="green")
            for nt, count in sorted(node_types.items()):
                type_table.add_row(nt, str(count))
            console.print(type_table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


@main.command()
@click.argument("graph_file")
@click.option("-o", "--output", required=True, help="Output file path")
@click.option("-f", "--format", "fmt", type=click.Choice(["dot", "mermaid"]), default="dot", help="Output format")
def export(graph_file: str, output: str, fmt: str):
    """
    Export a graph for visualization.

    Examples:

        cfg export graph.ison -o graph.dot -f dot

        cfg export graph.ison -o graph.md -f mermaid
    """
    try:
        from ison_graph import ISONGraph

        # Load graph
        if graph_file.endswith(".json"):
            graph = ISONGraph.load_json(graph_file)
        else:
            graph = ISONGraph.load(graph_file)

        if fmt == "dot":
            content = _export_dot(graph)
        else:
            content = _export_mermaid(graph)

        with open(output, "w") as f:
            f.write(content)

        console.print(f"[green]Exported to {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


def _export_dot(graph) -> str:
    """Export graph to DOT format for Graphviz"""
    lines = ["digraph CodeFlow {", "  rankdir=LR;", "  node [shape=box];", ""]

    # Node styles by type
    styles = {
        "file": 'style=filled, fillcolor="#e3f2fd"',
        "class": 'style=filled, fillcolor="#fff3e0"',
        "function": 'style=filled, fillcolor="#e8f5e9"',
        "module": 'style=filled, fillcolor="#f3e5f5"',
        "variable": 'style=filled, fillcolor="#fce4ec"',
    }

    # Add nodes
    for node in graph.nodes():
        label = node.properties.get("name", node.id)
        style = styles.get(node.type, "")
        node_id = f"{node.type}_{node.id}".replace(".", "_").replace("/", "_").replace("-", "_")
        lines.append(f'  {node_id} [label="{label}", {style}];')

    lines.append("")

    # Add edges
    for edge in graph.edges():
        src_type, src_id = edge.source
        tgt_type, tgt_id = edge.target
        src = f"{src_type}_{src_id}".replace(".", "_").replace("/", "_").replace("-", "_")
        tgt = f"{tgt_type}_{tgt_id}".replace(".", "_").replace("/", "_").replace("-", "_")
        lines.append(f'  {src} -> {tgt} [label="{edge.rel_type}"];')

    lines.append("}")
    return "\n".join(lines)


def _export_mermaid(graph) -> str:
    """Export graph to Mermaid format"""
    lines = ["```mermaid", "flowchart LR", ""]

    # Add nodes
    for node in graph.nodes():
        label = node.properties.get("name", node.id)
        node_id = f"{node.type}_{node.id}".replace(".", "_").replace("/", "_").replace("-", "_")

        if node.type == "class":
            lines.append(f"  {node_id}[/{label}\\]")
        elif node.type == "function":
            lines.append(f"  {node_id}({label})")
        elif node.type == "file":
            lines.append(f"  {node_id}[{label}]")
        else:
            lines.append(f"  {node_id}({label})")

    lines.append("")

    # Add edges
    for edge in graph.edges():
        src_type, src_id = edge.source
        tgt_type, tgt_id = edge.target
        src = f"{src_type}_{src_id}".replace(".", "_").replace("/", "_").replace("-", "_")
        tgt = f"{tgt_type}_{tgt_id}".replace(".", "_").replace("/", "_").replace("-", "_")
        lines.append(f"  {src} -->|{edge.rel_type}| {tgt}")

    lines.append("```")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
