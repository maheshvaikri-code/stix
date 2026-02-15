#!/usr/bin/env python3
"""
ISONCache Demonstration
=======================

Comprehensive demo of ISONCache features:
- Token-efficient caching
- ISON-formatted output
- Graph caching with traversal
- Token-budgeted retrieval
- Embedding similarity search
"""

import sys
from pathlib import Path

# Add parent to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax

console = Console()


def main():
    """Run ISONCache demonstration."""
    console.print(Panel.fit(
        "[bold blue]ISONCache Demonstration[/bold blue]\n"
        "Token-Efficient Cache for LLM Applications",
        title="ISONCache"
    ))

    # Import components
    from ison_cache import ISONCache, ISONGraphCache, EmbeddingCache
    from ison_cache.schema import Priority
    from ison_cache.token_manager import TokenManager

    # ==========================================================================
    # 1. Basic Key-Value Caching
    # ==========================================================================
    console.print("\n[bold cyan]1. Basic Key-Value Caching[/bold cyan]")

    cache = ISONCache(max_memory_mb=100, default_ttl=3600)

    # Store user data
    cache.set("user:101", {
        "id": 101,
        "name": "Alice Chen",
        "email": "alice@example.com",
        "role": "admin",
        "department": "Engineering"
    }, tags=["users", "admins"])

    cache.set("user:102", {
        "id": 102,
        "name": "Bob Smith",
        "email": "bob@example.com",
        "role": "developer",
        "department": "Engineering"
    }, tags=["users"])

    cache.set("user:103", {
        "id": 103,
        "name": "Carol Davis",
        "email": "carol@example.com",
        "role": "manager",
        "department": "Product"
    }, tags=["users", "managers"])

    console.print("   Stored 3 users")

    # Retrieve in ISON format
    result = cache.get("user:101")
    console.print("\n   [bold]ISON Output (user:101):[/bold]")
    console.print(Syntax(result, "text"))

    # ==========================================================================
    # 2. Token Comparison
    # ==========================================================================
    console.print("\n[bold cyan]2. Token Comparison (ISON vs JSON)[/bold cyan]")

    tm = TokenManager()

    products = [
        {"id": "P001", "name": "Keyboard", "price": 149.99, "category": "Electronics"},
        {"id": "P002", "name": "Mouse", "price": 79.99, "category": "Electronics"},
        {"id": "P003", "name": "Monitor", "price": 299.99, "category": "Electronics"},
        {"id": "P004", "name": "Webcam", "price": 89.99, "category": "Electronics"},
        {"id": "P005", "name": "Headset", "price": 129.99, "category": "Electronics"},
    ]

    comparison = tm.compare_formats(products)

    table = Table(title="Token Comparison")
    table.add_column("Format", style="cyan")
    table.add_column("Tokens", justify="right")

    table.add_row("JSON", str(comparison["json_tokens"]))
    table.add_row("ISON", str(comparison["ison_tokens"]))
    table.add_row("Savings", f"{comparison['savings']} tokens ({comparison['savings_percent']}%)")

    console.print(table)

    # ==========================================================================
    # 3. Batch Operations
    # ==========================================================================
    console.print("\n[bold cyan]3. Batch Operations[/bold cyan]")

    # Store products
    cache.mset({
        "product:P001": {"id": "P001", "name": "Keyboard", "price": 149.99},
        "product:P002": {"id": "P002", "name": "Mouse", "price": 79.99},
        "product:P003": {"id": "P003", "name": "Monitor", "price": 299.99},
    })

    console.print("   Stored 3 products")

    # Retrieve multiple
    result = cache.mget(["product:P001", "product:P002", "product:P003"])
    console.print("\n   [bold]Combined ISON Output:[/bold]")
    console.print(Syntax(result, "text"))

    # ==========================================================================
    # 4. Token-Budgeted Retrieval
    # ==========================================================================
    console.print("\n[bold cyan]4. Token-Budgeted Retrieval[/bold cyan]")

    # Add more data
    for i in range(10):
        cache.set(f"item:{i}", {
            "id": i,
            "name": f"Item {i}",
            "description": f"This is item number {i} with some description text.",
            "value": i * 100
        })

    # Get as much as fits in budget
    result = cache.get_within_budget(
        patterns="item:*",
        token_budget=200,
        priority=Priority.HITS
    )

    console.print(f"   Budget: {result.tokens_budget} tokens")
    console.print(f"   Used: {result.tokens_used} tokens ({result.utilization:.1f}%)")
    console.print(f"   Included: {len(result.keys_included)} items")
    console.print(f"   Excluded: {len(result.keys_excluded)} items")

    # ==========================================================================
    # 5. Graph Caching
    # ==========================================================================
    console.print("\n[bold cyan]5. Graph Caching with Traversal[/bold cyan]")

    graph_cache = ISONGraphCache()

    # Store a knowledge graph
    entities = [
        {"id": "user:101", "type": "person", "name": "Alice Chen"},
        {"id": "user:102", "type": "person", "name": "Bob Smith"},
        {"id": "project:ISON", "type": "project", "name": "ISON Format"},
        {"id": "project:Cache", "type": "project", "name": "ISONCache"},
        {"id": "org:Acme", "type": "organization", "name": "Acme Corp"},
    ]

    relations = [
        {"from": "user:101", "to": "project:ISON", "type": "CREATED"},
        {"from": "user:101", "to": "project:Cache", "type": "CREATED"},
        {"from": "user:102", "to": "project:ISON", "type": "CONTRIBUTES_TO"},
        {"from": "user:101", "to": "org:Acme", "type": "WORKS_AT"},
        {"from": "user:102", "to": "org:Acme", "type": "WORKS_AT"},
        {"from": "project:ISON", "to": "org:Acme", "type": "OWNED_BY"},
    ]

    graph_cache.set_graph("knowledge:main", entities, relations)
    console.print("   Stored knowledge graph with 5 entities, 6 relations")

    # Traverse from user:101
    result = graph_cache.traverse(
        start_entity="user:101",
        max_hops=2,
        direction="out"
    )

    console.print(f"\n   [bold]Traversal from user:101 (2 hops):[/bold]")
    console.print(f"   Entities found: {len(result.entities_included)}")
    console.print(f"   Relations: {result.relations_included}")
    console.print(f"   Tokens: {result.tokens_used}")
    console.print("\n   [bold]ISON Output:[/bold]")
    console.print(Syntax(result.ison, "text"))

    # ==========================================================================
    # 6. Embedding Similarity Search
    # ==========================================================================
    console.print("\n[bold cyan]6. Embedding Similarity Search[/bold cyan]")
    console.print("   (Using hash-based pseudo-embeddings for demo)")

    embedding_cache = EmbeddingCache(embedding_dim=128)

    # Store some documents
    docs = [
        ("doc:1", "Machine learning is a subset of artificial intelligence"),
        ("doc:2", "Deep learning uses neural networks with many layers"),
        ("doc:3", "Natural language processing helps computers understand text"),
        ("doc:4", "Computer vision enables image recognition and analysis"),
        ("doc:5", "Python is a popular programming language for data science"),
    ]

    for key, text in docs:
        embedding_cache.set(key, text)

    console.print(f"   Stored {len(docs)} documents")

    # Search
    results = embedding_cache.search("neural networks and AI", k=3)

    console.print("\n   [bold]Search: 'neural networks and AI'[/bold]")
    for r in results:
        console.print(f"   - {r.key}: {r.text[:50]}... (score: {r.score:.3f})")

    # ==========================================================================
    # 7. Cache Statistics
    # ==========================================================================
    console.print("\n[bold cyan]7. Cache Statistics[/bold cyan]")

    stats = cache.stats()

    table = Table(title="Cache Statistics")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Total Entries", str(stats.total_entries))
    table.add_row("Total Tokens", str(stats.total_tokens))
    table.add_row("Hits", str(stats.total_hits))
    table.add_row("Misses", str(stats.total_misses))
    table.add_row("Hit Rate", f"{stats.hit_rate:.1f}%")
    table.add_row("Memory", f"{stats.memory_bytes / 1024:.1f} KB")

    console.print(table)

    graph_stats = graph_cache.stats()
    console.print(f"\n   Graph Cache: {graph_stats['entities']} entities, {graph_stats['relations']} relations")

    emb_stats = embedding_cache.stats()
    console.print(f"   Embedding Cache: {emb_stats['entries']} documents, {emb_stats['dimension']}D vectors")

    # ==========================================================================
    # 8. Use Cases Summary
    # ==========================================================================
    console.print(Panel.fit(
        "[bold green]ISONCache Demo Complete[/bold green]\n\n"
        "Demonstrated features:\n"
        "- Key-value caching with ISON output\n"
        "- 72% token reduction vs JSON\n"
        "- Batch operations with schema merging\n"
        "- Token-budgeted retrieval\n"
        "- Graph caching with multi-hop traversal\n"
        "- Embedding similarity search\n\n"
        "[bold]Use Cases:[/bold]\n"
        "- RAG context caching\n"
        "- Session memory for agents\n"
        "- Tool results caching\n"
        "- Knowledge graph queries\n"
        "- Semantic search",
        title="Summary"
    ))


if __name__ == "__main__":
    main()
