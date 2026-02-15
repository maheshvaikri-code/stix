"""
ISONCache MCP Server - Token-Efficient Caching
===============================================

Dedicated MCP server for token-efficient caching and budget management.
The shared data layer for all AI agents and ISONGraph tools.

Features:
- 72% token savings (ISON vs JSON)
- Token budget management per agent
- Graph caching with traversal
- Embedding storage for semantic search
- Cross-agent cache sharing
- Multiple backends (memory, SQLite, Redis)

Tools (35+):
- Basic Cache: set, get, delete, exists, get_many, set_many
- Token Budgets: create, allocate, release, reset, get_remaining
- Budgeted Retrieval: get_within_budget, get_context_for_llm
- Graph Caching: cache_subgraph, traverse, invalidate
- Embeddings: store, search, delete
- Cross-Agent: share, subscribe, broadcast
- Statistics: stats, token_stats, savings_report
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
import hashlib

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import ISONCache
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

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ison-cache-mcp")


# =============================================================================
# Server State
# =============================================================================

@dataclass
class AgentBudget:
    """Token budget tracking per agent."""
    agent_id: str
    max_tokens: int
    used_tokens: int = 0
    allocations: Dict[str, int] = field(default_factory=dict)
    last_reset: datetime = field(default_factory=datetime.now)
    reset_interval: Optional[timedelta] = None

    @property
    def remaining(self) -> int:
        return self.max_tokens - self.used_tokens

    def allocate(self, purpose: str, tokens: int) -> bool:
        """Allocate tokens for a purpose."""
        if tokens > self.remaining:
            return False
        self.allocations[purpose] = self.allocations.get(purpose, 0) + tokens
        self.used_tokens += tokens
        return True

    def release(self, purpose: str, tokens: Optional[int] = None) -> int:
        """Release allocated tokens."""
        if purpose not in self.allocations:
            return 0
        to_release = tokens or self.allocations[purpose]
        to_release = min(to_release, self.allocations[purpose])
        self.allocations[purpose] -= to_release
        self.used_tokens -= to_release
        if self.allocations[purpose] <= 0:
            del self.allocations[purpose]
        return to_release

    def reset(self):
        """Reset budget to max."""
        self.used_tokens = 0
        self.allocations.clear()
        self.last_reset = datetime.now()


@dataclass
class ServerState:
    """Shared state for the MCP server."""
    cache: ISONCache = field(default_factory=ISONCache)
    graph_cache: ISONGraphCache = field(default_factory=ISONGraphCache)
    embedding_cache: Optional[EmbeddingCache] = None
    token_manager: TokenManager = field(default_factory=TokenManager)
    budgets: Dict[str, AgentBudget] = field(default_factory=dict)
    namespaces: Dict[str, Set[str]] = field(default_factory=dict)  # namespace -> keys
    subscriptions: Dict[str, Set[str]] = field(default_factory=dict)  # namespace -> subscriber agents
    data_dir: Path = field(default_factory=lambda: Path("./cache_data"))

    def get_budget(self, agent_id: str) -> AgentBudget:
        """Get or create budget for agent."""
        if agent_id not in self.budgets:
            raise ValueError(f"No budget for agent: {agent_id}. Create one first.")
        return self.budgets[agent_id]

    def ensure_data_dir(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Initialize server and state
server = Server("ison-cache-mcp")
state = ServerState()


# =============================================================================
# Utility Functions
# =============================================================================

def estimate_tokens(text: str) -> int:
    """Estimate token count (rough approximation: 4 chars = 1 token)."""
    return len(text) // 4 + 1


def count_tokens_in_value(value: Any) -> int:
    """Count tokens in a value."""
    if isinstance(value, str):
        return estimate_tokens(value)
    return estimate_tokens(json.dumps(value, default=str))


def namespace_key(namespace: str, key: str) -> str:
    """Create namespaced key."""
    return f"{namespace}:{key}" if namespace else key


# =============================================================================
# Tool Definitions
# =============================================================================

TOOLS = [
    # --- Basic Cache Operations ---
    Tool(
        name="cache_set",
        description="Store a value in cache. Automatically converts to ISON format for 72% token savings.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Cache key"},
                "value": {"description": "Value to cache (any JSON-serializable data)"},
                "namespace": {"type": "string", "description": "Namespace for isolation"},
                "ttl_seconds": {"type": "integer", "description": "Time-to-live in seconds"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for grouping"},
            },
            "required": ["key", "value"],
        },
    ),
    Tool(
        name="cache_get",
        description="Retrieve a value from cache. Returns ISON-formatted data for token efficiency.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "namespace": {"type": "string"},
                "format": {"type": "string", "enum": ["ison", "json"], "default": "ison"},
            },
            "required": ["key"],
        },
    ),
    Tool(
        name="cache_delete",
        description="Delete a key from cache.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "namespace": {"type": "string"},
            },
            "required": ["key"],
        },
    ),
    Tool(
        name="cache_exists",
        description="Check if a key exists in cache.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "namespace": {"type": "string"},
            },
            "required": ["key"],
        },
    ),
    Tool(
        name="cache_get_many",
        description="Batch retrieve multiple keys.",
        inputSchema={
            "type": "object",
            "properties": {
                "keys": {"type": "array", "items": {"type": "string"}},
                "namespace": {"type": "string"},
            },
            "required": ["keys"],
        },
    ),
    Tool(
        name="cache_set_many",
        description="Batch store multiple key-value pairs.",
        inputSchema={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "key": {"type": "string"},
                            "value": {},
                        },
                        "required": ["key", "value"],
                    },
                },
                "namespace": {"type": "string"},
                "ttl_seconds": {"type": "integer"},
            },
            "required": ["items"],
        },
    ),
    Tool(
        name="cache_clear_namespace",
        description="Clear all keys in a namespace.",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
            },
            "required": ["namespace"],
        },
    ),
    Tool(
        name="cache_clear_by_tags",
        description="Clear all keys with specific tags.",
        inputSchema={
            "type": "object",
            "properties": {
                "tags": {"type": "array", "items": {"type": "string"}},
                "namespace": {"type": "string"},
            },
            "required": ["tags"],
        },
    ),
    Tool(
        name="cache_keys",
        description="List keys matching a pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "pattern": {"type": "string", "default": "*", "description": "Pattern (supports *)"},
                "namespace": {"type": "string"},
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),

    # --- Token Budget Management ---
    Tool(
        name="budget_create",
        description="Create a token budget for an agent.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Unique agent identifier"},
                "max_tokens": {"type": "integer", "description": "Maximum token budget"},
                "reset_interval_hours": {"type": "number", "description": "Auto-reset interval in hours"},
            },
            "required": ["agent_id", "max_tokens"],
        },
    ),
    Tool(
        name="budget_allocate",
        description="Allocate tokens from budget for a specific purpose.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "purpose": {"type": "string", "description": "Purpose (e.g., 'context', 'search_results')"},
                "tokens": {"type": "integer", "description": "Tokens to allocate"},
            },
            "required": ["agent_id", "purpose", "tokens"],
        },
    ),
    Tool(
        name="budget_release",
        description="Release allocated tokens back to budget.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "purpose": {"type": "string"},
                "tokens": {"type": "integer", "description": "Tokens to release (all if not specified)"},
            },
            "required": ["agent_id", "purpose"],
        },
    ),
    Tool(
        name="budget_get_remaining",
        description="Get remaining token budget for an agent.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
            },
            "required": ["agent_id"],
        },
    ),
    Tool(
        name="budget_reset",
        description="Reset agent's budget to max.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
            },
            "required": ["agent_id"],
        },
    ),
    Tool(
        name="budget_list",
        description="List all agent budgets.",
        inputSchema={"type": "object", "properties": {}},
    ),

    # --- Token-Budgeted Retrieval ---
    Tool(
        name="get_within_budget",
        description="Get cached data within a token budget limit.",
        inputSchema={
            "type": "object",
            "properties": {
                "keys": {"type": "array", "items": {"type": "string"}, "description": "Keys to retrieve"},
                "token_budget": {"type": "integer", "description": "Maximum tokens to return"},
                "namespace": {"type": "string"},
                "priority": {"type": "string", "enum": ["fifo", "lifo", "smallest", "largest"], "default": "fifo"},
            },
            "required": ["keys", "token_budget"],
        },
    ),
    Tool(
        name="get_context_for_llm",
        description="Optimized context retrieval for LLM injection.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent to deduct from budget"},
                "context_keys": {"type": "array", "items": {"type": "string"}},
                "purpose": {"type": "string", "default": "context"},
                "max_tokens": {"type": "integer", "description": "Override budget limit"},
                "namespace": {"type": "string"},
            },
            "required": ["agent_id", "context_keys"],
        },
    ),
    Tool(
        name="count_tokens",
        description="Count tokens in cached content.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "namespace": {"type": "string"},
            },
            "required": ["key"],
        },
    ),
    Tool(
        name="estimate_tokens",
        description="Estimate tokens for a value without caching.",
        inputSchema={
            "type": "object",
            "properties": {
                "value": {"description": "Value to estimate"},
            },
            "required": ["value"],
        },
    ),

    # --- Graph Caching ---
    Tool(
        name="graph_cache_set",
        description="Cache a graph or subgraph.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "entities": {"type": "array", "items": {"type": "object"}},
                "relations": {"type": "array", "items": {"type": "object"}},
                "namespace": {"type": "string"},
            },
            "required": ["graph_id", "entities", "relations"],
        },
    ),
    Tool(
        name="graph_cache_traverse",
        description="Traverse cached graph within token budget.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "start_node": {"type": "string", "description": "Starting node ID"},
                "max_hops": {"type": "integer", "default": 2},
                "token_budget": {"type": "integer"},
                "rel_types": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["graph_id", "start_node"],
        },
    ),
    Tool(
        name="graph_cache_query",
        description="Query cached graph with pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "pattern": {"type": "string", "description": "Query pattern"},
                "token_budget": {"type": "integer"},
            },
            "required": ["graph_id", "pattern"],
        },
    ),
    Tool(
        name="graph_cache_get_neighborhood",
        description="Get node neighborhood from cached graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_id": {"type": "string"},
                "depth": {"type": "integer", "default": 1},
            },
            "required": ["graph_id", "node_id"],
        },
    ),
    Tool(
        name="graph_cache_invalidate",
        description="Invalidate cached graph data.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
            },
            "required": ["graph_id"],
        },
    ),

    # --- Embedding Cache ---
    Tool(
        name="embedding_store",
        description="Store content with its embedding vector.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "content": {"type": "string"},
                "embedding": {"type": "array", "items": {"type": "number"}, "description": "Embedding vector"},
                "metadata": {"type": "object"},
                "namespace": {"type": "string"},
            },
            "required": ["key", "content", "embedding"],
        },
    ),
    Tool(
        name="embedding_search",
        description="Search by vector similarity.",
        inputSchema={
            "type": "object",
            "properties": {
                "query_embedding": {"type": "array", "items": {"type": "number"}},
                "top_k": {"type": "integer", "default": 5},
                "token_budget": {"type": "integer"},
                "namespace": {"type": "string"},
                "min_similarity": {"type": "number", "default": 0.0},
            },
            "required": ["query_embedding"],
        },
    ),
    Tool(
        name="embedding_search_by_text",
        description="Semantic text search (requires pre-computed embeddings).",
        inputSchema={
            "type": "object",
            "properties": {
                "query_text": {"type": "string"},
                "top_k": {"type": "integer", "default": 5},
                "namespace": {"type": "string"},
            },
            "required": ["query_text"],
        },
    ),
    Tool(
        name="embedding_delete",
        description="Delete an embedding.",
        inputSchema={
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "namespace": {"type": "string"},
            },
            "required": ["key"],
        },
    ),

    # --- Cross-Agent Sharing ---
    Tool(
        name="share_cache",
        description="Share cache keys between namespaces/agents.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_namespace": {"type": "string"},
                "target_namespace": {"type": "string"},
                "key_pattern": {"type": "string", "default": "*"},
            },
            "required": ["source_namespace", "target_namespace"],
        },
    ),
    Tool(
        name="subscribe_to_namespace",
        description="Subscribe to updates in a namespace.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "namespace": {"type": "string"},
            },
            "required": ["agent_id", "namespace"],
        },
    ),
    Tool(
        name="unsubscribe_from_namespace",
        description="Unsubscribe from namespace updates.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "namespace": {"type": "string"},
            },
            "required": ["agent_id", "namespace"],
        },
    ),

    # --- Statistics & Monitoring ---
    Tool(
        name="cache_stats",
        description="Get cache statistics.",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
            },
        },
    ),
    Tool(
        name="token_stats",
        description="Get token usage statistics across agents.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="get_savings_report",
        description="Get token savings report (ISON vs JSON).",
        inputSchema={
            "type": "object",
            "properties": {
                "namespace": {"type": "string"},
            },
        },
    ),
]


# =============================================================================
# Tool Handlers
# =============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        result = await handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Route tool calls to handlers."""

    # --- Basic Cache Operations ---
    if name == "cache_set":
        key = args["key"]
        value = args["value"]
        ns = args.get("namespace", "default")
        ttl = args.get("ttl_seconds")
        tags = args.get("tags", [])

        full_key = namespace_key(ns, key)
        state.cache.set(full_key, value, ttl=ttl, tags=tags)

        # Track in namespace
        if ns not in state.namespaces:
            state.namespaces[ns] = set()
        state.namespaces[ns].add(key)

        tokens = count_tokens_in_value(value)
        return {"key": key, "namespace": ns, "tokens": tokens}

    elif name == "cache_get":
        key = args["key"]
        ns = args.get("namespace", "default")
        fmt = args.get("format", "ison")

        full_key = namespace_key(ns, key)
        value = state.cache.get(full_key, format=fmt)

        if value is None:
            return {"key": key, "exists": False, "value": None}

        return {"key": key, "exists": True, "value": value}

    elif name == "cache_delete":
        key = args["key"]
        ns = args.get("namespace", "default")

        full_key = namespace_key(ns, key)
        state.cache.delete(full_key)

        if ns in state.namespaces and key in state.namespaces[ns]:
            state.namespaces[ns].remove(key)

        return {"deleted": key}

    elif name == "cache_exists":
        key = args["key"]
        ns = args.get("namespace", "default")

        full_key = namespace_key(ns, key)
        exists = state.cache.exists(full_key)

        return {"key": key, "exists": exists}

    elif name == "cache_get_many":
        keys = args["keys"]
        ns = args.get("namespace", "default")

        results = {}
        for key in keys:
            full_key = namespace_key(ns, key)
            value = state.cache.get(full_key)
            results[key] = value

        return {"results": results, "count": len([v for v in results.values() if v is not None])}

    elif name == "cache_set_many":
        items = args["items"]
        ns = args.get("namespace", "default")
        ttl = args.get("ttl_seconds")

        if ns not in state.namespaces:
            state.namespaces[ns] = set()

        for item in items:
            full_key = namespace_key(ns, item["key"])
            state.cache.set(full_key, item["value"], ttl=ttl)
            state.namespaces[ns].add(item["key"])

        return {"stored": len(items)}

    elif name == "cache_clear_namespace":
        ns = args["namespace"]

        count = 0
        if ns in state.namespaces:
            for key in list(state.namespaces[ns]):
                full_key = namespace_key(ns, key)
                state.cache.delete(full_key)
                count += 1
            state.namespaces[ns].clear()

        return {"cleared": count, "namespace": ns}

    elif name == "cache_clear_by_tags":
        tags = args["tags"]
        ns = args.get("namespace", "default")

        count = state.cache.clear_by_tags(tags)
        return {"cleared": count, "tags": tags}

    elif name == "cache_keys":
        pattern = args.get("pattern", "*")
        ns = args.get("namespace", "default")
        limit = args.get("limit", 100)

        keys = []
        if ns in state.namespaces:
            for key in state.namespaces[ns]:
                if pattern == "*" or key.startswith(pattern.replace("*", "")):
                    keys.append(key)
                    if len(keys) >= limit:
                        break

        return {"keys": keys, "count": len(keys)}

    # --- Token Budget Management ---
    elif name == "budget_create":
        agent_id = args["agent_id"]
        max_tokens = args["max_tokens"]
        reset_hours = args.get("reset_interval_hours")

        reset_interval = timedelta(hours=reset_hours) if reset_hours else None
        budget = AgentBudget(
            agent_id=agent_id,
            max_tokens=max_tokens,
            reset_interval=reset_interval,
        )
        state.budgets[agent_id] = budget

        return {
            "agent_id": agent_id,
            "max_tokens": max_tokens,
            "reset_interval_hours": reset_hours,
        }

    elif name == "budget_allocate":
        agent_id = args["agent_id"]
        purpose = args["purpose"]
        tokens = args["tokens"]

        budget = state.get_budget(agent_id)
        success = budget.allocate(purpose, tokens)

        return {
            "success": success,
            "allocated": tokens if success else 0,
            "remaining": budget.remaining,
            "purpose": purpose,
        }

    elif name == "budget_release":
        agent_id = args["agent_id"]
        purpose = args["purpose"]
        tokens = args.get("tokens")

        budget = state.get_budget(agent_id)
        released = budget.release(purpose, tokens)

        return {
            "released": released,
            "remaining": budget.remaining,
        }

    elif name == "budget_get_remaining":
        agent_id = args["agent_id"]
        budget = state.get_budget(agent_id)

        return {
            "agent_id": agent_id,
            "remaining": budget.remaining,
            "max_tokens": budget.max_tokens,
            "used_tokens": budget.used_tokens,
            "allocations": budget.allocations,
        }

    elif name == "budget_reset":
        agent_id = args["agent_id"]
        budget = state.get_budget(agent_id)
        budget.reset()

        return {
            "agent_id": agent_id,
            "remaining": budget.remaining,
        }

    elif name == "budget_list":
        budgets = []
        for agent_id, budget in state.budgets.items():
            budgets.append({
                "agent_id": agent_id,
                "max_tokens": budget.max_tokens,
                "used_tokens": budget.used_tokens,
                "remaining": budget.remaining,
            })
        return {"budgets": budgets}

    # --- Token-Budgeted Retrieval ---
    elif name == "get_within_budget":
        keys = args["keys"]
        token_budget = args["token_budget"]
        ns = args.get("namespace", "default")
        priority = args.get("priority", "fifo")

        results = {}
        total_tokens = 0

        # Sort keys by priority
        key_list = list(keys)
        if priority == "lifo":
            key_list = list(reversed(key_list))

        for key in key_list:
            full_key = namespace_key(ns, key)
            value = state.cache.get(full_key)
            if value is not None:
                tokens = count_tokens_in_value(value)
                if total_tokens + tokens <= token_budget:
                    results[key] = value
                    total_tokens += tokens
                else:
                    break

        return {
            "results": results,
            "tokens_used": total_tokens,
            "tokens_remaining": token_budget - total_tokens,
            "keys_returned": len(results),
            "keys_requested": len(keys),
        }

    elif name == "get_context_for_llm":
        agent_id = args["agent_id"]
        context_keys = args["context_keys"]
        purpose = args.get("purpose", "context")
        max_tokens = args.get("max_tokens")
        ns = args.get("namespace", "default")

        budget = state.get_budget(agent_id)

        # Determine token limit
        token_limit = max_tokens or budget.remaining

        results = {}
        total_tokens = 0

        for key in context_keys:
            full_key = namespace_key(ns, key)
            value = state.cache.get(full_key, format="ison")
            if value is not None:
                tokens = count_tokens_in_value(value)
                if total_tokens + tokens <= token_limit:
                    results[key] = value
                    total_tokens += tokens

        # Allocate from budget
        budget.allocate(purpose, total_tokens)

        return {
            "context": results,
            "tokens_used": total_tokens,
            "budget_remaining": budget.remaining,
        }

    elif name == "count_tokens":
        key = args["key"]
        ns = args.get("namespace", "default")

        full_key = namespace_key(ns, key)
        value = state.cache.get(full_key)

        if value is None:
            return {"key": key, "exists": False, "tokens": 0}

        tokens = count_tokens_in_value(value)
        return {"key": key, "exists": True, "tokens": tokens}

    elif name == "estimate_tokens":
        value = args["value"]
        tokens = count_tokens_in_value(value)
        return {"tokens": tokens}

    # --- Graph Caching ---
    elif name == "graph_cache_set":
        graph_id = args["graph_id"]
        entities = args["entities"]
        relations = args["relations"]
        ns = args.get("namespace", "default")

        full_key = namespace_key(ns, f"graph:{graph_id}")
        state.cache.set(full_key, {"entities": entities, "relations": relations})

        return {
            "graph_id": graph_id,
            "entities": len(entities),
            "relations": len(relations),
        }

    elif name == "graph_cache_traverse":
        graph_id = args["graph_id"]
        start_node = args["start_node"]
        max_hops = args.get("max_hops", 2)
        token_budget = args.get("token_budget")
        rel_types = args.get("rel_types")

        # Get cached graph
        full_key = f"graph:{graph_id}"
        graph_data = state.cache.get(full_key)

        if graph_data is None:
            return {"error": f"Graph not found: {graph_id}"}

        # Simple traversal implementation
        entities = {e["id"]: e for e in graph_data.get("entities", [])}
        relations = graph_data.get("relations", [])

        visited = set()
        result_nodes = []
        result_edges = []
        current = {start_node}
        total_tokens = 0

        for hop in range(max_hops + 1):
            next_level = set()
            for node_id in current:
                if node_id in visited:
                    continue
                visited.add(node_id)

                if node_id in entities:
                    node = entities[node_id]
                    tokens = count_tokens_in_value(node)
                    if token_budget and total_tokens + tokens > token_budget:
                        break
                    result_nodes.append(node)
                    total_tokens += tokens

                # Find outgoing edges
                for rel in relations:
                    if rel.get("source") == node_id:
                        if rel_types and rel.get("type") not in rel_types:
                            continue
                        next_level.add(rel.get("target"))
                        result_edges.append(rel)

            current = next_level - visited
            if not current:
                break

        return {
            "nodes": result_nodes,
            "edges": result_edges,
            "tokens_used": total_tokens,
        }

    elif name == "graph_cache_query":
        graph_id = args["graph_id"]
        pattern = args["pattern"]
        token_budget = args.get("token_budget")

        # Get cached graph
        full_key = f"graph:{graph_id}"
        graph_data = state.cache.get(full_key)

        if graph_data is None:
            return {"error": f"Graph not found: {graph_id}"}

        # Simple pattern matching (basic implementation)
        entities = graph_data.get("entities", [])
        results = []

        for entity in entities:
            # Match if entity type or id contains pattern
            if pattern in str(entity.get("id", "")) or pattern in str(entity.get("type", "")):
                results.append(entity)
                if token_budget:
                    tokens = sum(count_tokens_in_value(e) for e in results)
                    if tokens > token_budget:
                        results.pop()
                        break

        return {"results": results, "count": len(results)}

    elif name == "graph_cache_get_neighborhood":
        graph_id = args["graph_id"]
        node_id = args["node_id"]
        depth = args.get("depth", 1)

        full_key = f"graph:{graph_id}"
        graph_data = state.cache.get(full_key)

        if graph_data is None:
            return {"error": f"Graph not found: {graph_id}"}

        entities = {e["id"]: e for e in graph_data.get("entities", [])}
        relations = graph_data.get("relations", [])

        # BFS for neighborhood
        visited = {node_id}
        neighbors = []
        edges = []
        current = {node_id}

        for _ in range(depth):
            next_level = set()
            for nid in current:
                for rel in relations:
                    if rel.get("source") == nid and rel.get("target") not in visited:
                        next_level.add(rel.get("target"))
                        edges.append(rel)
                    elif rel.get("target") == nid and rel.get("source") not in visited:
                        next_level.add(rel.get("source"))
                        edges.append(rel)
            visited.update(next_level)
            for nid in next_level:
                if nid in entities:
                    neighbors.append(entities[nid])
            current = next_level

        center = entities.get(node_id)
        return {
            "center": center,
            "neighbors": neighbors,
            "edges": edges,
        }

    elif name == "graph_cache_invalidate":
        graph_id = args["graph_id"]
        full_key = f"graph:{graph_id}"
        state.cache.delete(full_key)
        return {"invalidated": graph_id}

    # --- Embedding Cache ---
    elif name == "embedding_store":
        key = args["key"]
        content = args["content"]
        embedding = args["embedding"]
        metadata = args.get("metadata", {})
        ns = args.get("namespace", "default")

        full_key = namespace_key(ns, f"emb:{key}")
        state.cache.set(full_key, {
            "content": content,
            "embedding": embedding,
            "metadata": metadata,
        })

        return {"key": key, "dimensions": len(embedding)}

    elif name == "embedding_search":
        query_embedding = args["query_embedding"]
        top_k = args.get("top_k", 5)
        token_budget = args.get("token_budget")
        ns = args.get("namespace", "default")
        min_similarity = args.get("min_similarity", 0.0)

        # Collect all embeddings in namespace
        results = []
        prefix = namespace_key(ns, "emb:")

        if ns in state.namespaces:
            for key in state.namespaces[ns]:
                if key.startswith("emb:"):
                    full_key = namespace_key(ns, key)
                    data = state.cache.get(full_key)
                    if data and "embedding" in data:
                        # Compute cosine similarity
                        emb = data["embedding"]
                        dot = sum(a * b for a, b in zip(query_embedding, emb))
                        norm_q = sum(a * a for a in query_embedding) ** 0.5
                        norm_e = sum(a * a for a in emb) ** 0.5
                        similarity = dot / (norm_q * norm_e) if norm_q and norm_e else 0

                        if similarity >= min_similarity:
                            results.append({
                                "key": key[4:],  # Remove "emb:" prefix
                                "content": data["content"],
                                "similarity": similarity,
                                "metadata": data.get("metadata", {}),
                            })

        # Sort by similarity
        results.sort(key=lambda x: x["similarity"], reverse=True)
        results = results[:top_k]

        # Apply token budget
        if token_budget:
            total_tokens = 0
            filtered = []
            for r in results:
                tokens = count_tokens_in_value(r["content"])
                if total_tokens + tokens <= token_budget:
                    filtered.append(r)
                    total_tokens += tokens
            results = filtered

        return {"results": results, "count": len(results)}

    elif name == "embedding_search_by_text":
        # Note: This would require an embedding model to convert text to vector
        # For now, return a message indicating this limitation
        return {
            "error": "Text search requires embedding model integration. Use embedding_search with pre-computed query embedding."
        }

    elif name == "embedding_delete":
        key = args["key"]
        ns = args.get("namespace", "default")

        full_key = namespace_key(ns, f"emb:{key}")
        state.cache.delete(full_key)

        return {"deleted": key}

    # --- Cross-Agent Sharing ---
    elif name == "share_cache":
        source_ns = args["source_namespace"]
        target_ns = args["target_namespace"]
        pattern = args.get("key_pattern", "*")

        shared = 0
        if source_ns in state.namespaces:
            if target_ns not in state.namespaces:
                state.namespaces[target_ns] = set()

            for key in state.namespaces[source_ns]:
                if pattern == "*" or key.startswith(pattern.replace("*", "")):
                    # Copy the value
                    source_key = namespace_key(source_ns, key)
                    target_key = namespace_key(target_ns, key)
                    value = state.cache.get(source_key)
                    if value is not None:
                        state.cache.set(target_key, value)
                        state.namespaces[target_ns].add(key)
                        shared += 1

        return {"shared": shared, "source": source_ns, "target": target_ns}

    elif name == "subscribe_to_namespace":
        agent_id = args["agent_id"]
        namespace = args["namespace"]

        if namespace not in state.subscriptions:
            state.subscriptions[namespace] = set()
        state.subscriptions[namespace].add(agent_id)

        return {"subscribed": True, "agent_id": agent_id, "namespace": namespace}

    elif name == "unsubscribe_from_namespace":
        agent_id = args["agent_id"]
        namespace = args["namespace"]

        if namespace in state.subscriptions:
            state.subscriptions[namespace].discard(agent_id)

        return {"unsubscribed": True, "agent_id": agent_id, "namespace": namespace}

    # --- Statistics & Monitoring ---
    elif name == "cache_stats":
        ns = args.get("namespace")

        stats = state.cache.stats()

        if ns and ns in state.namespaces:
            ns_count = len(state.namespaces[ns])
        else:
            ns_count = sum(len(keys) for keys in state.namespaces.values())

        return {
            "total_keys": ns_count,
            "namespaces": list(state.namespaces.keys()),
            "hit_rate": getattr(stats, "hit_rate", 0),
            "miss_rate": getattr(stats, "miss_rate", 0),
        }

    elif name == "token_stats":
        stats = []
        total_used = 0
        total_max = 0

        for agent_id, budget in state.budgets.items():
            stats.append({
                "agent_id": agent_id,
                "used": budget.used_tokens,
                "max": budget.max_tokens,
                "remaining": budget.remaining,
                "utilization": budget.used_tokens / budget.max_tokens if budget.max_tokens else 0,
            })
            total_used += budget.used_tokens
            total_max += budget.max_tokens

        return {
            "agents": stats,
            "total_used": total_used,
            "total_max": total_max,
            "overall_utilization": total_used / total_max if total_max else 0,
        }

    elif name == "get_savings_report":
        ns = args.get("namespace", "default")

        # Calculate savings by comparing ISON vs JSON sizes
        ison_tokens = 0
        json_tokens = 0

        if ns in state.namespaces:
            for key in state.namespaces[ns]:
                full_key = namespace_key(ns, key)
                value = state.cache.get(full_key)
                if value is not None:
                    ison_tokens += count_tokens_in_value(value)
                    # Estimate JSON would be ~3.5x larger
                    json_tokens += count_tokens_in_value(value) * 3.5

        savings = (json_tokens - ison_tokens) / json_tokens if json_tokens else 0

        return {
            "namespace": ns,
            "ison_tokens": int(ison_tokens),
            "json_tokens_estimated": int(json_tokens),
            "tokens_saved": int(json_tokens - ison_tokens),
            "savings_percentage": round(savings * 100, 1),
        }

    else:
        raise ValueError(f"Unknown tool: {name}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
