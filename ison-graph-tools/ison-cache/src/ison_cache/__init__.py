"""
ISONCache - Token-Efficient Cache for LLM Applications
=======================================================

A caching system optimized for LLM context injection using ISON format.
Provides 72% token reduction compared to JSON with native graph support.

Features:
- Token-aware caching with budget management
- ISON-formatted output ready for LLM context
- Graph caching with multi-hop traversal
- Multiple backends (memory, SQLite, Redis)
- MCP server, HTTP API, and RESP protocol support
- Embedding store with vector similarity search

Usage:
    from ison_cache import ISONCache, ISONGraphCache

    # Basic key-value cache
    cache = ISONCache()
    cache.set("user:101", {"id": 101, "name": "Alice"})
    value = cache.get("user:101")  # Returns ISON-formatted string

    # Graph cache with traversal
    graph_cache = ISONGraphCache()
    graph_cache.set_graph("session:abc", entities, relations)
    subgraph = graph_cache.traverse("user:101", max_hops=2)

    # Token-budgeted retrieval
    result = cache.get_within_budget(["user:*"], token_budget=2000)

Author: Mahesh Vaikri
Version: 1.0.0
"""

from .cache import ISONCache
from .graph_cache import ISONGraphCache
from .embedding_cache import EmbeddingCache
from .token_manager import TokenManager, TokenBudget
from .schema import (
    CacheEntry,
    CacheStats,
    EvictionPolicy,
    CacheConfig,
    BudgetResult,
)

__version__ = "1.0.0"
__author__ = "Mahesh Vaikri"

__all__ = [
    # Version
    "__version__",

    # Core Classes
    "ISONCache",
    "ISONGraphCache",
    "EmbeddingCache",

    # Token Management
    "TokenManager",
    "TokenBudget",

    # Schema
    "CacheEntry",
    "CacheStats",
    "EvictionPolicy",
    "CacheConfig",
    "BudgetResult",
]
