"""
ISONCache CLI
=============

Command-line interface for ISONCache management.
"""

import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

console = Console()


# Shared cache instances
_cache = None
_graph_cache = None


def get_cache():
    """Get or create cache instance"""
    global _cache
    if _cache is None:
        from .cache import ISONCache
        _cache = ISONCache()
    return _cache


def get_graph_cache():
    """Get or create graph cache instance"""
    global _graph_cache
    if _graph_cache is None:
        from .graph_cache import ISONGraphCache
        _graph_cache = ISONGraphCache()
    return _graph_cache


@click.group()
@click.version_option(version="1.0.0")
def main():
    """ISONCache - Token-Efficient Cache for LLM Applications

    A caching system optimized for LLM context injection using ISON format.
    """
    pass


# =============================================================================
# Cache Commands
# =============================================================================

@main.group()
def cache():
    """Key-value cache operations."""
    pass


@cache.command("set")
@click.argument("key")
@click.argument("value")
@click.option("--ttl", "-t", type=int, default=3600, help="TTL in seconds")
@click.option("--tags", "-g", multiple=True, help="Tags for the entry")
def cache_set(key: str, value: str, ttl: int, tags: tuple):
    """Set a cache entry.

    VALUE can be JSON or a plain string.
    """
    c = get_cache()

    # Try to parse as JSON
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        parsed = value

    entry = c.set(key, parsed, ttl=ttl, tags=list(tags) if tags else None)

    console.print(Panel.fit(
        f"[green]Key set successfully[/green]\n\n"
        f"Key: [cyan]{entry.key}[/cyan]\n"
        f"Tokens: {entry.tokens}\n"
        f"Expires in: {entry.ttl_seconds}s",
        title="Cache Set"
    ))


@cache.command("get")
@click.argument("key")
@click.option("--max-tokens", "-m", type=int, help="Maximum tokens")
@click.option("--raw", is_flag=True, help="Return raw JSON instead of ISON")
def cache_get(key: str, max_tokens: Optional[int], raw: bool):
    """Get a cache entry."""
    c = get_cache()

    if raw:
        result = c.get_raw(key)
        if result is None:
            console.print("[red]Key not found[/red]")
            return
        console.print_json(data=result)
    else:
        result = c.get(key, max_tokens=max_tokens)
        if result is None:
            console.print("[red]Key not found[/red]")
            return
        console.print(Syntax(result, "text", theme="monokai"))


@cache.command("delete")
@click.argument("keys", nargs=-1)
def cache_delete(keys: tuple):
    """Delete cache entries."""
    c = get_cache()
    deleted = 0
    for key in keys:
        if c.delete(key):
            deleted += 1
            console.print(f"[green]Deleted:[/green] {key}")
        else:
            console.print(f"[yellow]Not found:[/yellow] {key}")

    console.print(f"\nDeleted {deleted} of {len(keys)} keys")


@cache.command("keys")
@click.option("--pattern", "-p", default="*", help="Glob pattern")
def cache_keys(pattern: str):
    """List cache keys."""
    c = get_cache()
    keys = c.keys(pattern)

    if not keys:
        console.print("[yellow]No keys found[/yellow]")
        return

    table = Table(title=f"Cache Keys ({len(keys)} matches)")
    table.add_column("Key", style="cyan")
    table.add_column("Tokens", justify="right")
    table.add_column("TTL", justify="right")

    for key in keys[:100]:  # Limit display
        entry = c._entries.get(key)
        if entry:
            ttl = entry.ttl_seconds
            ttl_str = f"{ttl}s" if ttl else "persistent"
            table.add_row(key, str(entry.tokens), ttl_str)

    console.print(table)

    if len(keys) > 100:
        console.print(f"\n[dim]... and {len(keys) - 100} more[/dim]")


@cache.command("stats")
def cache_stats():
    """Show cache statistics."""
    c = get_cache()
    stats = c.stats()

    table = Table(title="Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Entries", str(stats.total_entries))
    table.add_row("Total Tokens", str(stats.total_tokens))
    table.add_row("Hits", str(stats.total_hits))
    table.add_row("Misses", str(stats.total_misses))
    table.add_row("Hit Rate", f"{stats.hit_rate:.1f}%")
    table.add_row("Memory", f"{stats.memory_bytes / 1024 / 1024:.2f} MB")
    table.add_row("Evictions", str(stats.total_evictions))

    console.print(table)

    if stats.entries_by_type:
        type_table = Table(title="Entries by Type")
        type_table.add_column("Type", style="cyan")
        type_table.add_column("Count", justify="right")

        for t, count in stats.entries_by_type.items():
            type_table.add_row(t, str(count))

        console.print(type_table)


@cache.command("clear")
@click.confirmation_option(prompt="Clear all cache entries?")
def cache_clear():
    """Clear all cache entries."""
    c = get_cache()
    count = c.clear()
    console.print(f"[green]Cleared {count} entries[/green]")


@cache.command("budget")
@click.argument("pattern")
@click.argument("token_budget", type=int)
@click.option("--priority", "-p",
              type=click.Choice(["hits", "recent", "oldest", "tokens"]),
              default="hits", help="Priority for selection")
def cache_budget(pattern: str, token_budget: int, priority: str):
    """Get values within token budget."""
    from .schema import Priority

    c = get_cache()
    result = c.get_within_budget(
        patterns=pattern,
        token_budget=token_budget,
        priority=Priority[priority.upper()]
    )

    console.print(Panel.fit(
        f"[bold]Token Budget Result[/bold]\n\n"
        f"Budget: {result.tokens_budget}\n"
        f"Used: {result.tokens_used} ({result.utilization:.1f}%)\n"
        f"Included: {len(result.keys_included)} keys\n"
        f"Excluded: {len(result.keys_excluded)} keys\n"
        f"Truncated: {result.truncated}",
        title="Budget Query"
    ))

    if result.ison:
        console.print("\n[bold]ISON Output:[/bold]")
        console.print(Syntax(result.ison, "text", theme="monokai"))


# =============================================================================
# Graph Commands
# =============================================================================

@main.group()
def graph():
    """Graph cache operations."""
    pass


@graph.command("set")
@click.argument("key")
@click.argument("entities_file", type=click.Path(exists=True))
@click.argument("relations_file", type=click.Path(exists=True))
@click.option("--ttl", "-t", type=int, help="TTL in seconds")
def graph_set(key: str, entities_file: str, relations_file: str, ttl: Optional[int]):
    """Set a graph from JSON files."""
    gc = get_graph_cache()

    with open(entities_file) as f:
        entities = json.load(f)
    with open(relations_file) as f:
        relations = json.load(f)

    entry = gc.set_graph(key, entities, relations, ttl=ttl)

    console.print(Panel.fit(
        f"[green]Graph set successfully[/green]\n\n"
        f"Key: [cyan]{entry.key}[/cyan]\n"
        f"Entities: {entry.entity_count}\n"
        f"Relations: {entry.relation_count}\n"
        f"Tokens: {entry.tokens}",
        title="Graph Set"
    ))


@graph.command("get")
@click.argument("key")
@click.option("--max-tokens", "-m", type=int, help="Maximum tokens")
def graph_get(key: str, max_tokens: Optional[int]):
    """Get a cached graph."""
    gc = get_graph_cache()

    result = gc.get_graph(key, max_tokens=max_tokens)
    if result is None:
        console.print("[red]Graph not found[/red]")
        return

    console.print(Syntax(result, "text", theme="monokai"))


@graph.command("traverse")
@click.argument("entity")
@click.option("--hops", "-h", type=int, default=2, help="Maximum hops")
@click.option("--types", "-t", multiple=True, help="Relation types to follow")
@click.option("--budget", "-b", type=int, help="Token budget")
@click.option("--direction", "-d",
              type=click.Choice(["out", "in", "both"]),
              default="out", help="Traversal direction")
def graph_traverse(entity: str, hops: int, types: tuple, budget: Optional[int], direction: str):
    """Traverse from an entity."""
    gc = get_graph_cache()

    result = gc.traverse(
        start_entity=entity,
        max_hops=hops,
        relation_types=list(types) if types else None,
        token_budget=budget,
        direction=direction,
    )

    console.print(Panel.fit(
        f"[bold]Traversal Result[/bold]\n\n"
        f"Entities: {len(result.entities_included)}\n"
        f"Relations: {result.relations_included}\n"
        f"Hops: {result.hops_traversed}\n"
        f"Tokens: {result.tokens_used}\n"
        f"Truncated: {result.truncated}",
        title="Graph Traversal"
    ))

    if result.ison:
        console.print("\n[bold]ISON Output:[/bold]")
        console.print(Syntax(result.ison, "text", theme="monokai"))


@graph.command("stats")
def graph_stats():
    """Show graph cache statistics."""
    gc = get_graph_cache()
    stats = gc.stats()

    table = Table(title="Graph Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Graphs", str(stats["graphs"]))
    table.add_row("Entities", str(stats["entities"]))
    table.add_row("Relations", str(stats["relations"]))
    table.add_row("Tokens", str(stats["tokens"]))
    table.add_row("Indexed Entities", str(stats["indexed_entities"]))

    console.print(table)


# =============================================================================
# Server Commands
# =============================================================================

@main.group()
def server():
    """Server management commands."""
    pass


@server.command("mcp")
def server_mcp():
    """Start MCP server (stdio)."""
    from .mcp_server import serve
    console.print("[cyan]Starting ISONCache MCP server...[/cyan]")
    serve()


@server.command("http")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind")
@click.option("--port", "-p", type=int, default=8380, help="Port to bind")
def server_http(host: str, port: int):
    """Start HTTP/REST API server."""
    try:
        from .protocols.http import run_server
        console.print(f"[cyan]Starting HTTP server on {host}:{port}...[/cyan]")
        run_server(host=host, port=port)
    except ImportError as e:
        console.print(f"[red]Error: {e}[/red]")
        console.print("Install with: pip install ison-cache[http]")


@server.command("resp")
@click.option("--host", "-h", default="127.0.0.1", help="Host to bind")
@click.option("--port", "-p", type=int, default=6380, help="Port to bind")
def server_resp(host: str, port: int):
    """Start Redis-compatible RESP server."""
    from .protocols.resp import run_server
    console.print(f"[cyan]Starting RESP server on {host}:{port}...[/cyan]")
    run_server(host=host, port=port)


# =============================================================================
# Utility Commands
# =============================================================================

@main.command("compare")
@click.argument("value")
def compare_formats(value: str):
    """Compare token counts between ISON and JSON."""
    from .token_manager import TokenManager

    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        console.print("[red]Invalid JSON[/red]")
        return

    tm = TokenManager()
    comparison = tm.compare_formats(parsed)

    table = Table(title="Format Comparison")
    table.add_column("Format", style="cyan")
    table.add_column("Tokens", justify="right")

    table.add_row("JSON", str(comparison["json_tokens"]))
    table.add_row("ISON", str(comparison["ison_tokens"]))
    table.add_row("Savings", f"{comparison['savings']} ({comparison['savings_percent']}%)")

    console.print(table)


@main.command("tokenize")
@click.argument("text")
def tokenize_text(text: str):
    """Count tokens in text."""
    from .token_manager import TokenManager

    tm = TokenManager()
    count = tm.count_tokens(text)

    console.print(f"Tokens: [cyan]{count}[/cyan]")


@main.command("info")
def show_info():
    """Show package information."""
    console.print(Panel.fit(
        "[bold]ISONCache[/bold]\n\n"
        "Token-Efficient Cache for LLM Applications\n\n"
        "Features:\n"
        "  - 72% token reduction vs JSON\n"
        "  - Token-budgeted retrieval\n"
        "  - Graph caching with traversal\n"
        "  - Embedding similarity search\n"
        "  - Redis-compatible protocol\n"
        "  - MCP server support\n\n"
        "Version: 1.0.0",
        title="ISONCache Info"
    ))


if __name__ == "__main__":
    main()
