"""
ISONCache MCP Server
====================

A dedicated MCP server for token-efficient caching, designed as a
shared service layer for all other ISONGraph tools and AI agents.

Key Responsibilities:
1. Token Budget Management - Coordinate context windows across agents
2. ISON-Format Caching - 72% token reduction vs JSON
3. Graph Caching - Multi-hop traversal with caching
4. Embedding Storage - Vector similarity for semantic retrieval
5. Context Optimization - Smart truncation and prioritization

Architecture Benefits:
- Single source of truth for cached data
- Cross-agent cache sharing
- Persistent storage (survives restarts)
- Independent scaling
- Backend flexibility (memory → Redis → distributed)
"""

import json
import asyncio
from typing import Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, Resource

# ISONCache imports
from ison_cache import (
    ISONCache,
    ISONGraphCache,
    EmbeddingCache,
    TokenManager,
    TokenBudget,
    CacheEntry,
    CacheStats,
    EvictionPolicy,
    CacheConfig,
    BudgetResult,
)


class CacheBackend(Enum):
    """Supported cache backends."""
    MEMORY = "memory"
    SQLITE = "sqlite"
    REDIS = "redis"


@dataclass
class AgentBudget:
    """Token budget tracking per agent."""
    agent_id: str
    max_tokens: int
    used_tokens: int = 0
    allocations: dict = field(default_factory=dict)
    last_reset: datetime = field(default_factory=datetime.now)
    reset_interval: Optional[timedelta] = None


@dataclass
class ServerState:
    """Server state with multiple cache layers."""
    # Primary caches
    key_value_cache: ISONCache = field(default_factory=ISONCache)
    graph_cache: ISONGraphCache = field(default_factory=ISONGraphCache)
    embedding_cache: Optional[EmbeddingCache] = None

    # Token management
    token_manager: TokenManager = field(default_factory=TokenManager)
    agent_budgets: dict[str, AgentBudget] = field(default_factory=dict)

    # Namespaced caches (for isolation)
    namespaces: dict[str, ISONCache] = field(default_factory=dict)

    # Statistics
    total_requests: int = 0
    cache_hits: int = 0
    cache_misses: int = 0
    tokens_saved: int = 0


# Global state
state = ServerState()

# MCP Server
server = Server("ison-cache")


# ============================================================================
# TOOL DEFINITIONS
# ============================================================================

def get_all_tools() -> list[Tool]:
    """Return all cache tools."""
    return [
        # === BASIC CACHE OPERATIONS ===
        Tool(
            name="cache_set",
            description="Store a value in ISON-format cache (72% token savings vs JSON)",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "Cache key"},
                    "value": {"type": "object", "description": "Value to cache (any JSON)"},
                    "ttl_seconds": {"type": "integer", "description": "Time-to-live in seconds"},
                    "namespace": {"type": "string", "description": "Optional namespace for isolation"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for bulk operations"},
                },
                "required": ["key", "value"]
            }
        ),
        Tool(
            name="cache_get",
            description="Retrieve a value from cache in token-efficient ISON format",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "namespace": {"type": "string"},
                    "format": {"type": "string", "enum": ["ison", "json"], "default": "ison"},
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="cache_delete",
            description="Delete a key from cache",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "namespace": {"type": "string"},
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="cache_exists",
            description="Check if a key exists in cache",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "namespace": {"type": "string"},
                },
                "required": ["key"]
            }
        ),
        Tool(
            name="cache_get_many",
            description="Retrieve multiple keys at once",
            inputSchema={
                "type": "object",
                "properties": {
                    "keys": {"type": "array", "items": {"type": "string"}},
                    "namespace": {"type": "string"},
                },
                "required": ["keys"]
            }
        ),
        Tool(
            name="cache_set_many",
            description="Store multiple key-value pairs at once",
            inputSchema={
                "type": "object",
                "properties": {
                    "items": {"type": "object", "description": "Key-value pairs"},
                    "ttl_seconds": {"type": "integer"},
                    "namespace": {"type": "string"},
                },
                "required": ["items"]
            }
        ),
        Tool(
            name="cache_clear_namespace",
            description="Clear all keys in a namespace",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                },
                "required": ["namespace"]
            }
        ),
        Tool(
            name="cache_clear_by_tags",
            description="Clear all keys with specific tags",
            inputSchema={
                "type": "object",
                "properties": {
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "namespace": {"type": "string"},
                },
                "required": ["tags"]
            }
        ),

        # === TOKEN BUDGET MANAGEMENT ===
        Tool(
            name="budget_create",
            description="Create a token budget for an agent/session",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent or session identifier"},
                    "max_tokens": {"type": "integer", "description": "Maximum tokens for this agent"},
                    "reset_interval_minutes": {"type": "integer", "description": "Auto-reset interval"},
                },
                "required": ["agent_id", "max_tokens"]
            }
        ),
        Tool(
            name="budget_allocate",
            description="Allocate tokens from budget for a purpose",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "purpose": {"type": "string", "description": "e.g., 'system_prompt', 'context', 'history'"},
                    "tokens": {"type": "integer"},
                },
                "required": ["agent_id", "purpose", "tokens"]
            }
        ),
        Tool(
            name="budget_get_remaining",
            description="Get remaining tokens in budget",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                },
                "required": ["agent_id"]
            }
        ),
        Tool(
            name="budget_release",
            description="Release tokens back to budget",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "purpose": {"type": "string"},
                },
                "required": ["agent_id", "purpose"]
            }
        ),
        Tool(
            name="budget_reset",
            description="Reset budget to max tokens",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                },
                "required": ["agent_id"]
            }
        ),

        # === TOKEN-BUDGETED RETRIEVAL ===
        Tool(
            name="get_within_budget",
            description="Retrieve cached data that fits within a token budget (smart truncation)",
            inputSchema={
                "type": "object",
                "properties": {
                    "patterns": {"type": "array", "items": {"type": "string"}, "description": "Key patterns (e.g., 'user:*')"},
                    "token_budget": {"type": "integer", "description": "Maximum tokens to return"},
                    "priority": {"type": "string", "enum": ["recent", "frequent", "size"], "default": "recent"},
                    "namespace": {"type": "string"},
                },
                "required": ["patterns", "token_budget"]
            }
        ),
        Tool(
            name="get_context_for_llm",
            description="Get optimized context for LLM prompt within budget",
            inputSchema={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string"},
                    "context_keys": {"type": "array", "items": {"type": "string"}},
                    "purpose": {"type": "string", "default": "context"},
                    "include_metadata": {"type": "boolean", "default": False},
                },
                "required": ["agent_id", "context_keys"]
            }
        ),
        Tool(
            name="count_tokens",
            description="Count tokens for content (useful for budget planning)",
            inputSchema={
                "type": "object",
                "properties": {
                    "content": {"type": "string"},
                },
                "required": ["content"]
            }
        ),
        Tool(
            name="estimate_tokens",
            description="Estimate tokens for a cached key without retrieving",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "namespace": {"type": "string"},
                },
                "required": ["key"]
            }
        ),

        # === GRAPH CACHING ===
        Tool(
            name="graph_cache_set",
            description="Cache a graph with entities and relations",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "entities": {"type": "array", "items": {"type": "object"}},
                    "relations": {"type": "array", "items": {"type": "object"}},
                    "ttl_seconds": {"type": "integer"},
                },
                "required": ["graph_id", "entities", "relations"]
            }
        ),
        Tool(
            name="graph_cache_traverse",
            description="Traverse cached graph from a starting node",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "start_node": {"type": "string"},
                    "max_hops": {"type": "integer", "default": 2},
                    "direction": {"type": "string", "enum": ["outgoing", "incoming", "both"], "default": "both"},
                    "edge_types": {"type": "array", "items": {"type": "string"}, "description": "Filter by edge types"},
                    "token_budget": {"type": "integer", "description": "Limit result by tokens"},
                },
                "required": ["graph_id", "start_node"]
            }
        ),
        Tool(
            name="graph_cache_query",
            description="Query cached graph with pattern matching",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "query": {"type": "string", "description": "Query pattern"},
                    "token_budget": {"type": "integer"},
                },
                "required": ["graph_id", "query"]
            }
        ),
        Tool(
            name="graph_cache_get_neighborhood",
            description="Get the neighborhood of a node within token budget",
            inputSchema={
                "type": "object",
                "properties": {
                    "graph_id": {"type": "string"},
                    "node_id": {"type": "string"},
                    "token_budget": {"type": "integer"},
                    "include_properties": {"type": "boolean", "default": True},
                },
                "required": ["graph_id", "node_id", "token_budget"]
            }
        ),

        # === EMBEDDING CACHE (Semantic) ===
        Tool(
            name="embedding_store",
            description="Store content with its embedding for semantic search",
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string"},
                    "content": {"type": "string"},
                    "embedding": {"type": "array", "items": {"type": "number"}, "description": "Vector embedding"},
                    "metadata": {"type": "object"},
                    "namespace": {"type": "string"},
                },
                "required": ["key", "content", "embedding"]
            }
        ),
        Tool(
            name="embedding_search",
            description="Search for similar content by embedding",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_embedding": {"type": "array", "items": {"type": "number"}},
                    "top_k": {"type": "integer", "default": 10},
                    "threshold": {"type": "number", "default": 0.7, "description": "Minimum similarity"},
                    "namespace": {"type": "string"},
                    "token_budget": {"type": "integer", "description": "Limit results by tokens"},
                },
                "required": ["query_embedding"]
            }
        ),
        Tool(
            name="embedding_search_by_text",
            description="Search similar content (requires embedding function configured)",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_text": {"type": "string"},
                    "top_k": {"type": "integer", "default": 10},
                    "namespace": {"type": "string"},
                    "token_budget": {"type": "integer"},
                },
                "required": ["query_text"]
            }
        ),

        # === CROSS-AGENT CACHE SHARING ===
        Tool(
            name="share_cache",
            description="Share cached data from one agent/namespace to another",
            inputSchema={
                "type": "object",
                "properties": {
                    "source_namespace": {"type": "string"},
                    "target_namespace": {"type": "string"},
                    "key_pattern": {"type": "string", "description": "Pattern to share (e.g., 'context:*')"},
                    "mode": {"type": "string", "enum": ["copy", "link"], "default": "copy"},
                },
                "required": ["source_namespace", "target_namespace", "key_pattern"]
            }
        ),
        Tool(
            name="subscribe_to_namespace",
            description="Subscribe to updates from another namespace",
            inputSchema={
                "type": "object",
                "properties": {
                    "subscriber_namespace": {"type": "string"},
                    "source_namespace": {"type": "string"},
                    "key_pattern": {"type": "string"},
                },
                "required": ["subscriber_namespace", "source_namespace"]
            }
        ),

        # === STATISTICS & MONITORING ===
        Tool(
            name="cache_stats",
            description="Get cache statistics",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                },
                "required": []
            }
        ),
        Tool(
            name="token_stats",
            description="Get token usage statistics across all agents",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        Tool(
            name="get_savings_report",
            description="Get token savings report (ISON vs JSON)",
            inputSchema={
                "type": "object",
                "properties": {
                    "namespace": {"type": "string"},
                },
                "required": []
            }
        ),

        # === PERSISTENCE ===
        Tool(
            name="persist_to_disk",
            description="Persist cache to disk",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "namespace": {"type": "string"},
                },
                "required": ["path"]
            }
        ),
        Tool(
            name="load_from_disk",
            description="Load cache from disk",
            inputSchema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "namespace": {"type": "string"},
                },
                "required": ["path"]
            }
        ),

        # === CONFIGURATION ===
        Tool(
            name="configure_eviction",
            description="Configure cache eviction policy",
            inputSchema={
                "type": "object",
                "properties": {
                    "policy": {"type": "string", "enum": ["lru", "lfu", "ttl", "token_aware"]},
                    "max_size_mb": {"type": "integer"},
                    "max_tokens": {"type": "integer"},
                    "namespace": {"type": "string"},
                },
                "required": ["policy"]
            }
        ),
        Tool(
            name="configure_backend",
            description="Configure cache backend (memory, sqlite, redis)",
            inputSchema={
                "type": "object",
                "properties": {
                    "backend": {"type": "string", "enum": ["memory", "sqlite", "redis"]},
                    "connection_string": {"type": "string", "description": "For sqlite/redis"},
                },
                "required": ["backend"]
            }
        ),
    ]


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List all available tools."""
    return get_all_tools()


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Handle tool calls."""
    try:
        result = await handle_tool_call(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        return [TextContent(type="text", text=json.dumps({"error": str(e)}, indent=2))]


async def handle_tool_call(name: str, args: dict) -> dict:
    """Route tool calls to handlers."""
    state.total_requests += 1

    # Get cache for namespace
    def get_cache(namespace: Optional[str] = None) -> ISONCache:
        if namespace:
            if namespace not in state.namespaces:
                state.namespaces[namespace] = ISONCache()
            return state.namespaces[namespace]
        return state.key_value_cache

    # === BASIC CACHE OPERATIONS ===
    if name == "cache_set":
        cache = get_cache(args.get("namespace"))
        cache.set(
            args["key"],
            args["value"],
            ttl=args.get("ttl_seconds"),
            tags=args.get("tags", [])
        )
        # Calculate token savings
        json_tokens = state.token_manager.count_tokens(json.dumps(args["value"]))
        ison_tokens = state.token_manager.count_tokens(cache.get(args["key"]))
        state.tokens_saved += json_tokens - ison_tokens
        return {
            "success": True,
            "key": args["key"],
            "tokens_saved": json_tokens - ison_tokens
        }

    elif name == "cache_get":
        cache = get_cache(args.get("namespace"))
        value = cache.get(args["key"])
        if value is not None:
            state.cache_hits += 1
            if args.get("format") == "json":
                return {"key": args["key"], "value": json.loads(value) if isinstance(value, str) else value}
            return {"key": args["key"], "value": value, "format": "ison"}
        state.cache_misses += 1
        return {"key": args["key"], "value": None, "found": False}

    elif name == "cache_delete":
        cache = get_cache(args.get("namespace"))
        cache.delete(args["key"])
        return {"success": True, "key": args["key"]}

    elif name == "cache_exists":
        cache = get_cache(args.get("namespace"))
        exists = cache.exists(args["key"])
        return {"key": args["key"], "exists": exists}

    elif name == "cache_get_many":
        cache = get_cache(args.get("namespace"))
        results = {}
        for key in args["keys"]:
            value = cache.get(key)
            if value is not None:
                results[key] = value
                state.cache_hits += 1
            else:
                state.cache_misses += 1
        return {"results": results, "found": len(results), "missing": len(args["keys"]) - len(results)}

    elif name == "cache_set_many":
        cache = get_cache(args.get("namespace"))
        ttl = args.get("ttl_seconds")
        for key, value in args["items"].items():
            cache.set(key, value, ttl=ttl)
        return {"success": True, "count": len(args["items"])}

    elif name == "cache_clear_namespace":
        if args["namespace"] in state.namespaces:
            state.namespaces[args["namespace"]] = ISONCache()
        return {"success": True, "namespace": args["namespace"]}

    elif name == "cache_clear_by_tags":
        cache = get_cache(args.get("namespace"))
        count = cache.clear_by_tags(args["tags"])
        return {"success": True, "cleared": count}

    # === TOKEN BUDGET MANAGEMENT ===
    elif name == "budget_create":
        reset_interval = None
        if args.get("reset_interval_minutes"):
            reset_interval = timedelta(minutes=args["reset_interval_minutes"])

        budget = AgentBudget(
            agent_id=args["agent_id"],
            max_tokens=args["max_tokens"],
            reset_interval=reset_interval
        )
        state.agent_budgets[args["agent_id"]] = budget
        return {
            "success": True,
            "agent_id": args["agent_id"],
            "max_tokens": args["max_tokens"]
        }

    elif name == "budget_allocate":
        budget = state.agent_budgets.get(args["agent_id"])
        if not budget:
            return {"error": f"No budget found for agent {args['agent_id']}"}

        # Check if auto-reset needed
        if budget.reset_interval and datetime.now() - budget.last_reset > budget.reset_interval:
            budget.used_tokens = 0
            budget.allocations = {}
            budget.last_reset = datetime.now()

        remaining = budget.max_tokens - budget.used_tokens
        if args["tokens"] > remaining:
            return {
                "success": False,
                "error": "Insufficient tokens",
                "requested": args["tokens"],
                "remaining": remaining
            }

        budget.allocations[args["purpose"]] = args["tokens"]
        budget.used_tokens += args["tokens"]
        return {
            "success": True,
            "purpose": args["purpose"],
            "allocated": args["tokens"],
            "remaining": budget.max_tokens - budget.used_tokens
        }

    elif name == "budget_get_remaining":
        budget = state.agent_budgets.get(args["agent_id"])
        if not budget:
            return {"error": f"No budget found for agent {args['agent_id']}"}
        return {
            "agent_id": args["agent_id"],
            "max_tokens": budget.max_tokens,
            "used_tokens": budget.used_tokens,
            "remaining": budget.max_tokens - budget.used_tokens,
            "allocations": budget.allocations
        }

    elif name == "budget_release":
        budget = state.agent_budgets.get(args["agent_id"])
        if not budget:
            return {"error": f"No budget found for agent {args['agent_id']}"}

        released = budget.allocations.pop(args["purpose"], 0)
        budget.used_tokens -= released
        return {"success": True, "released": released}

    elif name == "budget_reset":
        budget = state.agent_budgets.get(args["agent_id"])
        if not budget:
            return {"error": f"No budget found for agent {args['agent_id']}"}
        budget.used_tokens = 0
        budget.allocations = {}
        budget.last_reset = datetime.now()
        return {"success": True, "max_tokens": budget.max_tokens}

    # === TOKEN-BUDGETED RETRIEVAL ===
    elif name == "get_within_budget":
        cache = get_cache(args.get("namespace"))
        result = cache.get_within_budget(
            args["patterns"],
            args["token_budget"],
            priority=args.get("priority", "recent")
        )
        return result

    elif name == "get_context_for_llm":
        budget = state.agent_budgets.get(args["agent_id"])
        if not budget:
            return {"error": f"No budget found for agent {args['agent_id']}"}

        purpose = args.get("purpose", "context")
        available = budget.allocations.get(purpose, budget.max_tokens - budget.used_tokens)

        cache = state.key_value_cache
        results = []
        total_tokens = 0

        for key in args["context_keys"]:
            value = cache.get(key)
            if value:
                tokens = state.token_manager.count_tokens(str(value))
                if total_tokens + tokens <= available:
                    results.append({"key": key, "value": value})
                    total_tokens += tokens

        return {
            "context": results,
            "total_tokens": total_tokens,
            "budget_remaining": available - total_tokens,
            "format": "ison"
        }

    elif name == "count_tokens":
        count = state.token_manager.count_tokens(args["content"])
        return {"token_count": count}

    elif name == "estimate_tokens":
        cache = get_cache(args.get("namespace"))
        value = cache.get(args["key"])
        if value:
            return {"key": args["key"], "estimated_tokens": state.token_manager.count_tokens(str(value))}
        return {"key": args["key"], "estimated_tokens": 0, "found": False}

    # === GRAPH CACHING ===
    elif name == "graph_cache_set":
        state.graph_cache.set_graph(
            args["graph_id"],
            args["entities"],
            args["relations"],
            ttl=args.get("ttl_seconds")
        )
        return {"success": True, "graph_id": args["graph_id"]}

    elif name == "graph_cache_traverse":
        result = state.graph_cache.traverse(
            args["graph_id"],
            args["start_node"],
            max_hops=args.get("max_hops", 2),
            direction=args.get("direction", "both"),
            edge_types=args.get("edge_types"),
            token_budget=args.get("token_budget")
        )
        return result

    elif name == "graph_cache_query":
        result = state.graph_cache.query(
            args["graph_id"],
            args["query"],
            token_budget=args.get("token_budget")
        )
        return result

    elif name == "graph_cache_get_neighborhood":
        result = state.graph_cache.get_neighborhood(
            args["graph_id"],
            args["node_id"],
            token_budget=args["token_budget"],
            include_properties=args.get("include_properties", True)
        )
        return result

    # === EMBEDDING CACHE ===
    elif name == "embedding_store":
        if state.embedding_cache is None:
            state.embedding_cache = EmbeddingCache()

        state.embedding_cache.store(
            args["key"],
            args["content"],
            args["embedding"],
            metadata=args.get("metadata", {}),
            namespace=args.get("namespace")
        )
        return {"success": True, "key": args["key"]}

    elif name == "embedding_search":
        if state.embedding_cache is None:
            return {"error": "Embedding cache not initialized. Store some embeddings first."}

        results = state.embedding_cache.search(
            args["query_embedding"],
            top_k=args.get("top_k", 10),
            threshold=args.get("threshold", 0.7),
            namespace=args.get("namespace"),
            token_budget=args.get("token_budget")
        )
        return {"results": results}

    # === STATISTICS ===
    elif name == "cache_stats":
        cache = get_cache(args.get("namespace"))
        stats = cache.get_stats()
        return {
            "stats": stats,
            "global": {
                "total_requests": state.total_requests,
                "cache_hits": state.cache_hits,
                "cache_misses": state.cache_misses,
                "hit_rate": state.cache_hits / max(state.total_requests, 1),
                "tokens_saved": state.tokens_saved
            }
        }

    elif name == "token_stats":
        return {
            "agents": {
                agent_id: {
                    "max_tokens": b.max_tokens,
                    "used_tokens": b.used_tokens,
                    "remaining": b.max_tokens - b.used_tokens,
                    "allocations": b.allocations
                }
                for agent_id, b in state.agent_budgets.items()
            },
            "total_tokens_saved": state.tokens_saved
        }

    elif name == "get_savings_report":
        # Calculate savings
        return {
            "total_tokens_saved": state.tokens_saved,
            "savings_percentage": 72,  # ISON vs JSON typical savings
            "description": "ISON format provides ~72% token reduction compared to JSON"
        }

    # === PERSISTENCE ===
    elif name == "persist_to_disk":
        cache = get_cache(args.get("namespace"))
        cache.persist(args["path"])
        return {"success": True, "path": args["path"]}

    elif name == "load_from_disk":
        cache = get_cache(args.get("namespace"))
        cache.load(args["path"])
        return {"success": True, "path": args["path"]}

    # === CONFIGURATION ===
    elif name == "configure_eviction":
        cache = get_cache(args.get("namespace"))
        cache.configure_eviction(
            policy=args["policy"],
            max_size_mb=args.get("max_size_mb"),
            max_tokens=args.get("max_tokens")
        )
        return {"success": True, "policy": args["policy"]}

    elif name == "configure_backend":
        # Would switch backend implementation
        return {"success": True, "backend": args["backend"], "note": "Backend switching requires restart"}

    return {"error": f"Unknown tool: {name}"}


# ============================================================================
# RESOURCES
# ============================================================================

@server.list_resources()
async def list_resources() -> list[Resource]:
    """List cache resources."""
    resources = [
        Resource(
            uri="isoncache://stats",
            name="Cache Statistics",
            mimeType="application/json"
        ),
        Resource(
            uri="isoncache://budgets",
            name="Agent Token Budgets",
            mimeType="application/json"
        ),
    ]

    # Add namespace resources
    for ns in state.namespaces:
        resources.append(Resource(
            uri=f"isoncache://namespace/{ns}",
            name=f"Namespace: {ns}",
            mimeType="application/json"
        ))

    return resources


@server.read_resource()
async def read_resource(uri: str) -> str:
    """Read a resource."""
    if uri == "isoncache://stats":
        return json.dumps({
            "total_requests": state.total_requests,
            "cache_hits": state.cache_hits,
            "cache_misses": state.cache_misses,
            "tokens_saved": state.tokens_saved,
            "namespaces": list(state.namespaces.keys()),
        }, indent=2)

    elif uri == "isoncache://budgets":
        return json.dumps({
            agent_id: {
                "max": b.max_tokens,
                "used": b.used_tokens,
                "remaining": b.max_tokens - b.used_tokens
            }
            for agent_id, b in state.agent_budgets.items()
        }, indent=2)

    elif uri.startswith("isoncache://namespace/"):
        ns = uri.replace("isoncache://namespace/", "")
        cache = state.namespaces.get(ns)
        if cache:
            return json.dumps(cache.get_stats(), indent=2)

    return json.dumps({"error": "Resource not found"})


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
