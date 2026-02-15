"""
ISON Memory MCP CLI

Command-line interface for managing the ISON Memory MCP server.

Usage:
    ison-memory-mcp serve          # Start the MCP server (stdio)
    ison-memory-mcp serve --http   # Start with HTTP transport
    ison-memory-mcp stats          # Show memory statistics
    ison-memory-mcp compact        # Run compaction
    ison-memory-mcp backup         # Create backup
    ison-memory-mcp export         # Export to ISON file
    ison-memory-mcp config         # Show/edit configuration
    ison-memory-mcp init           # Initialize configuration
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from ison_memory_mcp.config import (
    MemoryConfig,
    load_config,
    save_config,
    get_default_config_path,
    get_default_memory_path,
    StorageFormat,
    CompactionStrategy
)


console = Console()


def run_async(coro):
    """Helper to run async functions"""
    return asyncio.run(coro)


@click.group()
@click.version_option(version="1.0.0", prog_name="ison-memory-mcp")
@click.option(
    "--config", "-c",
    type=click.Path(exists=False, path_type=Path),
    help="Path to configuration file"
)
@click.pass_context
def cli(ctx: click.Context, config: Optional[Path]) -> None:
    """ISON Memory MCP Server - Persistent memory for Claude"""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config


@cli.command()
@click.option(
    "--transport", "-t",
    type=click.Choice(["stdio", "http", "sse"]),
    default="stdio",
    help="Transport protocol"
)
@click.option("--host", default="127.0.0.1", help="HTTP/SSE host")
@click.option("--port", default=8765, help="HTTP/SSE port")
@click.option("--debug", is_flag=True, help="Enable debug logging")
@click.pass_context
def serve(
    ctx: click.Context,
    transport: str,
    host: str,
    port: int,
    debug: bool
) -> None:
    """Start the MCP server"""
    config_path = ctx.obj.get("config_path")
    config = load_config(config_path)

    config.server.transport = transport
    config.server.host = host
    config.server.port = port
    config.debug = debug

    if debug:
        import logging
        logging.basicConfig(level=logging.DEBUG)

    if transport == "stdio":
        # Run in stdio mode (default for MCP)
        from ison_memory_mcp.server import run_server
        run_async(run_server(config))
    else:
        console.print(f"[yellow]HTTP/SSE transport starting on {host}:{port}[/yellow]")
        console.print("[red]HTTP/SSE transport not yet implemented[/red]")
        sys.exit(1)


@cli.command()
@click.pass_context
def stats(ctx: click.Context) -> None:
    """Show memory statistics"""
    config_path = ctx.obj.get("config_path")
    config = load_config(config_path)

    async def show_stats():
        from ison_memory_mcp.store import MemoryStore

        store = MemoryStore(config)
        await store.initialize()

        try:
            memory_stats = await store.get_stats()

            # Create summary table
            table = Table(title="Memory Statistics")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            table.add_row("Entities", str(memory_stats.entity_count))
            table.add_row("Observations", str(memory_stats.observation_count))
            table.add_row("Relations", str(memory_stats.relation_count))
            table.add_row("Database Size", f"{memory_stats.database_size_bytes / (1024*1024):.2f} MB")

            if memory_stats.oldest_entity:
                table.add_row("Oldest Entity", memory_stats.oldest_entity.strftime("%Y-%m-%d"))
            if memory_stats.newest_entity:
                table.add_row("Newest Entity", memory_stats.newest_entity.strftime("%Y-%m-%d"))
            if memory_stats.last_compaction:
                table.add_row("Last Compaction", memory_stats.last_compaction.strftime("%Y-%m-%d %H:%M"))
            if memory_stats.last_backup:
                table.add_row("Last Backup", memory_stats.last_backup.strftime("%Y-%m-%d %H:%M"))

            console.print(table)

            # Entity type breakdown
            if memory_stats.entity_types:
                type_table = Table(title="Entity Types")
                type_table.add_column("Type", style="cyan")
                type_table.add_column("Count", style="green")
                for etype, count in sorted(memory_stats.entity_types.items()):
                    type_table.add_row(etype, str(count))
                console.print(type_table)

            # Relation type breakdown
            if memory_stats.relation_types:
                rel_table = Table(title="Relation Types")
                rel_table.add_column("Type", style="cyan")
                rel_table.add_column("Count", style="green")
                for rtype, count in sorted(memory_stats.relation_types.items()):
                    rel_table.add_row(rtype, str(count))
                console.print(rel_table)

            # Also print ISON format
            console.print("\n[bold]ISON Format:[/bold]")
            console.print(Syntax(memory_stats.to_ison(), "text", theme="monokai"))

        finally:
            await store.close()

    run_async(show_stats())


@cli.command()
@click.option(
    "--strategy", "-s",
    type=click.Choice(["time_based", "relevance", "aggressive", "smart"]),
    default="smart",
    help="Compaction strategy"
)
@click.option("--dry-run", is_flag=True, help="Simulate without making changes")
@click.pass_context
def compact(ctx: click.Context, strategy: str, dry_run: bool) -> None:
    """Run memory compaction"""
    config_path = ctx.obj.get("config_path")
    config = load_config(config_path)

    async def run_compact():
        from ison_memory_mcp.store import MemoryStore
        from ison_memory_mcp.compaction import MemoryCompactor

        store = MemoryStore(config)
        await store.initialize()

        compactor = MemoryCompactor(config)

        try:
            console.print(f"[yellow]Running {strategy} compaction...[/yellow]")
            if dry_run:
                console.print("[cyan]DRY RUN - No changes will be made[/cyan]")

            result = await compactor.compact(
                store,
                CompactionStrategy(strategy),
                dry_run
            )

            if result.success:
                console.print(f"[green]Compaction completed in {result.duration_seconds:.2f}s[/green]")

                table = Table(title="Compaction Results")
                table.add_column("Type", style="cyan")
                table.add_column("Before", style="yellow")
                table.add_column("After", style="green")
                table.add_column("Removed", style="red")

                table.add_row(
                    "Entities",
                    str(result.entities_before),
                    str(result.entities_after),
                    str(result.entities_removed)
                )
                table.add_row(
                    "Observations",
                    str(result.observations_before),
                    str(result.observations_after),
                    str(result.observations_removed)
                )
                table.add_row(
                    "Relations",
                    str(result.relations_before),
                    str(result.relations_after),
                    str(result.relations_removed)
                )

                console.print(table)

                if result.size_saved_bytes > 0:
                    console.print(
                        f"[green]Space saved: {result.size_saved_bytes / (1024*1024):.2f} MB[/green]"
                    )
            else:
                console.print("[red]Compaction failed[/red]")
                for error in result.errors:
                    console.print(f"  [red]- {error}[/red]")

        finally:
            await store.close()

    run_async(run_compact())


@cli.command()
@click.option("--include-ison/--no-ison", default=True, help="Include ISON export")
@click.pass_context
def backup(ctx: click.Context, include_ison: bool) -> None:
    """Create a memory backup"""
    config_path = ctx.obj.get("config_path")
    config = load_config(config_path)

    async def run_backup():
        from ison_memory_mcp.store import MemoryStore
        from ison_memory_mcp.compaction import BackupManager

        store = MemoryStore(config)
        await store.initialize()

        backup_mgr = BackupManager(config)

        try:
            console.print("[yellow]Creating backup...[/yellow]")

            result = await backup_mgr.create_backup(store, include_ison)

            if result.success:
                console.print(f"[green]Backup created: {result.backup_path}[/green]")
                console.print(f"  Size: {result.size_bytes / (1024*1024):.2f} MB")
                console.print(f"  Compressed: {result.compressed}")
            else:
                console.print("[red]Backup failed[/red]")
                for error in result.errors:
                    console.print(f"  [red]- {error}[/red]")

        finally:
            await store.close()

    run_async(run_backup())


@cli.command()
@click.pass_context
def backups(ctx: click.Context) -> None:
    """List available backups"""
    config_path = ctx.obj.get("config_path")
    config = load_config(config_path)

    from ison_memory_mcp.compaction import BackupManager

    backup_mgr = BackupManager(config)
    backup_list = backup_mgr.list_backups()

    if not backup_list:
        console.print("[yellow]No backups found[/yellow]")
        return

    table = Table(title="Available Backups")
    table.add_column("Name", style="cyan")
    table.add_column("Size", style="green")
    table.add_column("Created", style="yellow")
    table.add_column("Compressed", style="blue")

    for backup in backup_list:
        table.add_row(
            backup["name"],
            f"{backup['size_mb']:.2f} MB",
            backup["created_at"][:19],
            "Yes" if backup["compressed"] else "No"
        )

    console.print(table)


@cli.command()
@click.option(
    "--format", "-f",
    type=click.Choice(["ison", "isonl", "isongraph"]),
    default="ison",
    help="Export format"
)
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file path")
@click.pass_context
def export(ctx: click.Context, format: str, output: Optional[Path]) -> None:
    """Export memory to ISON file"""
    config_path = ctx.obj.get("config_path")
    config = load_config(config_path)

    async def run_export():
        from ison_memory_mcp.store import MemoryStore

        store = MemoryStore(config)
        await store.initialize()

        try:
            if format == "isonl":
                content = await store.export_to_isonl()
                ext = "isonl"
            elif format == "isongraph":
                content = await store.export_to_isongraph()
                ext = "isongraph"
            else:
                content = await store.export_to_ison()
                ext = "ison"

            output_path = output or Path(f"memory_export.{ext}")
            output_path.write_text(content, encoding="utf-8")

            console.print(f"[green]Exported to: {output_path}[/green]")
            console.print(f"  Format: {format}")
            console.print(f"  Size: {output_path.stat().st_size / 1024:.2f} KB")

        finally:
            await store.close()

    run_async(run_export())


@cli.command("config")
@click.option("--show", is_flag=True, help="Show current configuration")
@click.option("--edit", is_flag=True, help="Open configuration in editor")
@click.option("--path", is_flag=True, help="Show configuration file path")
@click.pass_context
def config_cmd(ctx: click.Context, show: bool, edit: bool, path: bool) -> None:
    """Show or edit configuration"""
    config_path = ctx.obj.get("config_path") or get_default_config_path()

    if path:
        console.print(f"Config path: {config_path}")
        console.print(f"Memory path: {get_default_memory_path()}")
        return

    if edit:
        import subprocess
        editor = "notepad" if sys.platform == "win32" else "nano"
        if config_path.exists():
            subprocess.run([editor, str(config_path)])
        else:
            console.print("[yellow]Config file doesn't exist. Creating default...[/yellow]")
            config = MemoryConfig()
            save_config(config, config_path)
            subprocess.run([editor, str(config_path)])
        return

    # Default: show config
    if config_path.exists():
        content = config_path.read_text()
        console.print(Panel(
            Syntax(content, "toml", theme="monokai"),
            title=f"Configuration: {config_path}"
        ))
    else:
        console.print("[yellow]No configuration file found. Using defaults.[/yellow]")
        config = MemoryConfig()
        console.print(Panel(
            Syntax(config.to_toml(), "toml", theme="monokai"),
            title="Default Configuration"
        ))


@cli.command()
@click.option("--force", "-f", is_flag=True, help="Overwrite existing configuration")
@click.pass_context
def init(ctx: click.Context, force: bool) -> None:
    """Initialize ISON Memory MCP configuration"""
    config_path = ctx.obj.get("config_path") or get_default_config_path()

    if config_path.exists() and not force:
        console.print(f"[yellow]Configuration already exists: {config_path}[/yellow]")
        console.print("Use --force to overwrite")
        return

    config = MemoryConfig()
    config.ensure_directories()
    save_config(config, config_path)

    console.print(f"[green]Configuration created: {config_path}[/green]")
    console.print(f"[green]Memory directory: {config.storage.path.parent}[/green]")

    # Show quick start
    console.print("\n[bold]Quick Start:[/bold]")
    console.print("1. Add to Claude Desktop config:")
    console.print('   "ison-memory": {')
    console.print('     "command": "ison-memory-mcp",')
    console.print('     "args": ["serve"]')
    console.print('   }')
    console.print("\n2. Or run directly:")
    console.print("   ison-memory-mcp serve")


@cli.command()
@click.argument("query")
@click.option("--limit", "-l", default=20, help="Maximum results")
@click.pass_context
def search(ctx: click.Context, query: str, limit: int) -> None:
    """Search memory from command line"""
    config_path = ctx.obj.get("config_path")
    config = load_config(config_path)

    async def run_search():
        from ison_memory_mcp.store import MemoryStore

        store = MemoryStore(config)
        await store.initialize()

        try:
            result = await store.search(query, limit)

            console.print(f"[bold]Search Results for '{query}'[/bold]")
            console.print(f"Found {result.total_count} items in {result.search_time_ms:.2f}ms\n")

            console.print(Syntax(result.to_ison(), "text", theme="monokai"))

        finally:
            await store.close()

    run_async(run_search())


def main() -> None:
    """Main entry point"""
    cli(obj={})


if __name__ == "__main__":
    main()
