#!/usr/bin/env python3
"""
ISONCache + Agent Memory Integration Demo
==========================================

Demonstrates how ISONCache integrates with AgentMemory to provide:
- Token-efficient context retrieval
- Semantic search over memories
- Cached context building
- ISON-formatted output for LLMs
"""

import sys
from pathlib import Path

# Add paths for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "ison-cache" / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()


def main():
    """Run the integration demo."""
    console.print(Panel.fit(
        "[bold blue]ISONCache + Agent Memory Integration[/bold blue]\n"
        "Token-Efficient Memory Retrieval for Coding Agents",
        title="Integration Demo"
    ))

    # Import components
    from agent_memory import AgentMemory
    from agent_memory.cache_integration import (
        CachedAgentMemory,
        SemanticMemory,
        MemoryGraphCache,
        get_context_with_budget,
    )

    # ==========================================================================
    # 1. Create Agent Memory with Sample Data
    # ==========================================================================
    console.print("\n[bold cyan]1. Creating Agent Memory with Sample Data[/bold cyan]")

    memory = AgentMemory("demo-project")

    # Add conventions
    memory.conventions.add_convention(
        category="naming",
        rule="snake_case_functions",
        enforced_by="ruff"
    )
    memory.conventions.add_convention(
        category="imports",
        rule="absolute_imports",
        enforced_by="isort"
    )
    memory.conventions.add_convention(
        category="typing",
        rule="use_type_hints",
        enforced_by="mypy"
    )

    # Add decisions
    memory.decisions.add_decision(
        title="Use PostgreSQL for primary database",
        context="ACID compliance and JSON support needed. All entities stored in PostgreSQL, Redis for caching only."
    )
    memory.decisions.add_decision(
        title="Implement async I/O with asyncio",
        context="High concurrency requirements. Use aiohttp for HTTP, asyncpg for database."
    )

    # Add bug patterns
    memory.bugs.add_pattern(
        name="connection_pool_exhaustion",
        signature="ConnectionPoolExhaustedError - Database connections not being released"
    )
    memory.bugs.add_fix_pattern(
        bug_pattern_name="connection_pool_exhaustion",
        fix_template="Use context manager or ensure close() is called"
    )
    memory.bugs.add_pattern(
        name="race_condition_cache",
        signature="Inconsistent cache state - Race condition when updating cache"
    )
    memory.bugs.add_fix_pattern(
        bug_pattern_name="race_condition_cache",
        fix_template="Use atomic operations or distributed locks"
    )

    # Add dependencies
    memory.dependencies.add_dependency(
        name="asyncpg",
        version="0.29.0",
        category="database"
    )
    memory.dependencies.add_quirk(
        dependency_name="asyncpg",
        description="Pool connections must be explicitly closed"
    )
    memory.dependencies.add_workaround(
        quirk_description="Pool connections must be explicitly closed",
        solution="Use async with pool.acquire() as conn pattern"
    )

    # Add performance info
    memory.performance.add_hot_path(
        name="user_auth_flow",
        frequency="1000/sec"
    )
    memory.performance.add_constraint(
        operation="user_auth_flow",
        constraint="<100ms",
        reason="User experience requirement"
    )

    console.print("   Added: 3 conventions, 2 decisions, 2 bug patterns, 1 dependency, 1 hot path")

    # ==========================================================================
    # 2. Token-Efficient Context Retrieval
    # ==========================================================================
    console.print("\n[bold cyan]2. Token-Efficient Context Retrieval[/bold cyan]")

    cached_memory = CachedAgentMemory(memory, cache_max_mb=50)

    # Get context with small budget
    context = cached_memory.get_cached_context(
        task="Modify the database connection pooling",
        files=["src/db/pool.py"],
        token_budget=500,
    )

    console.print(f"   Budget: {context.tokens_budget} tokens")
    console.print(f"   Used: {context.tokens_used} tokens ({context.utilization:.1f}%)")
    console.print(f"   Included: {', '.join(context.categories_included)}")
    if context.categories_truncated:
        console.print(f"   Truncated: {', '.join(context.categories_truncated)}")
    console.print(f"   From cache: {context.from_cache}")

    console.print("\n   [bold]ISON Output:[/bold]")
    console.print(Syntax(context.ison_output[:500] + "...", "text"))

    # Get context with larger budget
    context_large = cached_memory.get_cached_context(
        task="Modify the database connection pooling",
        files=["src/db/pool.py"],
        token_budget=2000,
    )

    console.print(f"\n   With 2000 token budget:")
    console.print(f"   Used: {context_large.tokens_used} tokens ({context_large.utilization:.1f}%)")
    console.print(f"   Included: {', '.join(context_large.categories_included)}")

    # ==========================================================================
    # 3. Semantic Memory Search
    # ==========================================================================
    console.print("\n[bold cyan]3. Semantic Memory Search[/bold cyan]")

    semantic = SemanticMemory(memory)

    # Index all memories
    index_stats = semantic.index_all()
    console.print(f"   Indexed: {index_stats}")

    # Search by meaning
    results = semantic.search("database connection issues", k=3)

    console.print("\n   [bold]Search: 'database connection issues'[/bold]")
    for r in results:
        console.print(f"   - [{r.memory_type}] {r.key}: {r.content[:60]}... (score: {r.score:.3f})")

    # Search for async patterns
    results2 = semantic.search("async programming patterns", k=3)

    console.print("\n   [bold]Search: 'async programming patterns'[/bold]")
    for r in results2:
        console.print(f"   - [{r.memory_type}] {r.key}: {r.content[:60]}... (score: {r.score:.3f})")

    # Get as ISON
    ison_results = semantic.search_to_ison("cache invalidation", k=3, token_budget=500)
    console.print("\n   [bold]ISON Search Results:[/bold]")
    console.print(Syntax(ison_results, "text"))

    # ==========================================================================
    # 4. Graph Cache Traversal
    # ==========================================================================
    console.print("\n[bold cyan]4. Graph Cache Traversal[/bold cyan]")

    graph_cache = MemoryGraphCache(memory)
    sync_stats = graph_cache.sync()

    console.print(f"   Synced: {sync_stats['entities']} entities, {sync_stats['relations']} relations")

    # Find related memories (if any relations exist)
    # Note: This requires actual edges in the memory graph
    console.print("   Graph cache ready for traversal queries")

    # ==========================================================================
    # 5. Quick Context Function
    # ==========================================================================
    console.print("\n[bold cyan]5. Quick Context Function[/bold cyan]")

    quick_ison = get_context_with_budget(
        memory,
        task="Add logging to authentication",
        files=["src/auth/login.py"],
        token_budget=1000,
    )

    console.print("   [bold]Quick Context (1000 tokens):[/bold]")
    console.print(Syntax(quick_ison[:400] + "...", "text"))

    # ==========================================================================
    # 6. Cache Statistics
    # ==========================================================================
    console.print("\n[bold cyan]6. Cache Statistics[/bold cyan]")

    stats = cached_memory.stats()

    table = Table(title="Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Memory Name", stats["memory_name"])
    table.add_row("Cache Entries", str(stats["cache"]["entries"]))
    table.add_row("Total Tokens", str(stats["cache"]["tokens"]))
    table.add_row("Cache Hits", str(stats["cache"]["hits"]))
    table.add_row("Cache Misses", str(stats["cache"]["misses"]))
    table.add_row("Hit Rate", f"{stats['cache']['hit_rate']:.1f}%")

    console.print(table)

    sem_stats = semantic.stats()
    console.print(f"\n   Semantic Memory: {sem_stats['embedding_cache']['entries']} indexed documents")

    # ==========================================================================
    # Summary
    # ==========================================================================
    console.print(Panel.fit(
        "[bold green]Integration Demo Complete[/bold green]\n\n"
        "Demonstrated features:\n"
        "- Token-efficient context retrieval with budgets\n"
        "- ISON-formatted output for LLM injection\n"
        "- Semantic search over memories\n"
        "- Graph cache for relationship traversal\n"
        "- Automatic caching of context builds\n\n"
        "[bold]Use Cases:[/bold]\n"
        "- Inject relevant memories into LLM prompts\n"
        "- Find related memories by meaning\n"
        "- Optimize context window usage\n"
        "- Cache expensive memory queries",
        title="Summary"
    ))


if __name__ == "__main__":
    main()
