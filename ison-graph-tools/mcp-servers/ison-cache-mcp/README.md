# ISONCache MCP Server

**Token-Efficient Caching** - The shared data layer for all AI agents and ISONGraph tools.

## Why Separate the Cache?

| Problem | Solution |
|---------|----------|
| Each agent manages own cache | **Centralized cache** - single source of truth |
| Token budgets uncoordinated | **Central budget management** - prevent overspending |
| Cache lost on restart | **Persistent storage** - survives restarts |
| No sharing between agents | **Cross-agent sharing** - Agent A's context available to B |
| Tight coupling | **Loose coupling** - agents don't depend on cache internals |
| Can't scale cache separately | **Independent scaling** - scale cache without scaling compute |

## Token Savings

ISON format provides **72% token reduction** compared to JSON:

| Format | Tokens (1000 records) | Savings |
|--------|----------------------|---------|
| JSON | 45,000 | - |
| **ISON** | **12,600** | **72%** |

This means you can fit **3.5x more context** in the same LLM context window.

## Quick Start

### Installation

```bash
pip install ison-cache-mcp
```

### Run the Server

```bash
ison-cache-mcp
# or
python -m ison_cache_mcp.server
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "cache": {
      "command": "python",
      "args": ["-m", "ison_cache_mcp.server"]
    }
  }
}
```

## Tools (35+)

### Basic Cache Operations

| Tool | Description |
|------|-------------|
| `cache_set` | Store value (72% token savings) |
| `cache_get` | Retrieve in ISON format |
| `cache_delete` | Delete a key |
| `cache_exists` | Check if key exists |
| `cache_get_many` | Batch retrieval |
| `cache_set_many` | Batch storage |
| `cache_clear_namespace` | Clear namespace |
| `cache_clear_by_tags` | Clear by tags |
| `cache_keys` | List keys matching pattern |

### Token Budget Management

| Tool | Description |
|------|-------------|
| `budget_create` | Create budget for agent |
| `budget_allocate` | Allocate tokens for purpose |
| `budget_get_remaining` | Check remaining tokens |
| `budget_release` | Release allocated tokens |
| `budget_reset` | Reset to max |
| `budget_list` | List all budgets |

### Token-Budgeted Retrieval

| Tool | Description |
|------|-------------|
| `get_within_budget` | Get data within token limit |
| `get_context_for_llm` | Optimized context retrieval |
| `count_tokens` | Count tokens in content |
| `estimate_tokens` | Estimate without retrieval |

### Graph Caching

| Tool | Description |
|------|-------------|
| `graph_cache_set` | Cache a graph |
| `graph_cache_traverse` | Multi-hop traversal |
| `graph_cache_query` | Pattern query |
| `graph_cache_get_neighborhood` | Get node neighborhood |
| `graph_cache_invalidate` | Invalidate cache |

### Embedding Cache (Semantic)

| Tool | Description |
|------|-------------|
| `embedding_store` | Store with embedding |
| `embedding_search` | Vector similarity search |
| `embedding_search_by_text` | Semantic text search |
| `embedding_delete` | Remove embedding |

### Cross-Agent Sharing

| Tool | Description |
|------|-------------|
| `share_cache` | Share between namespaces |
| `subscribe_to_namespace` | Subscribe to updates |
| `unsubscribe_from_namespace` | Unsubscribe |

### Statistics & Monitoring

| Tool | Description |
|------|-------------|
| `cache_stats` | Cache statistics |
| `token_stats` | Token usage across agents |
| `get_savings_report` | Token savings report |

## Example Workflows

### 1. Coordinated Token Budgets

```python
# Create budgets for multiple agents
await cache.call_tool("budget_create", {
    "agent_id": "researcher",
    "max_tokens": 4000
})

await cache.call_tool("budget_create", {
    "agent_id": "writer",
    "max_tokens": 8000
})

# Allocate for specific purposes
await cache.call_tool("budget_allocate", {
    "agent_id": "researcher",
    "purpose": "search_results",
    "tokens": 2000
})

# Get remaining before LLM call
remaining = await cache.call_tool("budget_get_remaining", {
    "agent_id": "researcher"
})
# Returns: {"remaining": 2000, "allocations": {"search_results": 2000}}
```

### 2. Cross-Agent Context Sharing

```python
# Agent 1 caches research results
await cache.call_tool("cache_set", {
    "key": "research:topic_analysis",
    "value": {"findings": [...], "sources": [...]},
    "namespace": "agent_1"
})

# Share with Agent 2
await cache.call_tool("share_cache", {
    "source_namespace": "agent_1",
    "target_namespace": "agent_2",
    "key_pattern": "research:*"
})

# Agent 2 retrieves shared context
result = await cache.call_tool("cache_get", {
    "key": "research:topic_analysis",
    "namespace": "agent_2"
})
```

### 3. Graph Context with Budget

```python
# Cache a knowledge graph
await cache.call_tool("graph_cache_set", {
    "graph_id": "project_knowledge",
    "entities": [
        {"id": "module:auth", "type": "module", "name": "Authentication"},
        {"id": "func:login", "type": "function", "name": "login"},
    ],
    "relations": [
        {"source": "module:auth", "target": "func:login", "type": "CONTAINS"},
    ]
})

# Traverse within token budget
result = await cache.call_tool("graph_cache_traverse", {
    "graph_id": "project_knowledge",
    "start_node": "module:auth",
    "max_hops": 2,
    "token_budget": 1500
})
# Returns subgraph that fits in 1500 tokens
```

### 4. Semantic Search with Budget

```python
# Store documents with embeddings
await cache.call_tool("embedding_store", {
    "key": "doc:readme",
    "content": "# Project Overview\n...",
    "embedding": [0.1, 0.2, ...],  # from embedding model
    "metadata": {"type": "documentation"}
})

# Search similar content within budget
results = await cache.call_tool("embedding_search", {
    "query_embedding": [0.15, 0.22, ...],
    "top_k": 5,
    "token_budget": 2000
})
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI Agents                                │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────┐    │
│  │  Claude   │  │   GPT-4   │  │  Agent 1  │  │  Agent 2  │    │
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘    │
└────────┼──────────────┼──────────────┼──────────────┼───────────┘
         │              │              │              │
         └──────────────┴──────────────┴──────────────┘
                               │
                               │ MCP Protocol
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ISONCache MCP Server                          │
│                    (This Server)                                 │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                 Token Budget Manager                     │   │
│  │  agent_1: 4000 tokens (2500 used, 1500 remaining)       │   │
│  │  agent_2: 8000 tokens (3200 used, 4800 remaining)       │   │
│  │  shared:  10000 tokens (coordinated across all)         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   Key-Value  │  │    Graph     │  │  Embedding   │         │
│  │    Cache     │  │    Cache     │  │    Cache     │         │
│  │  (72% save)  │  │  (traversal) │  │  (semantic)  │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
│                               │                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Storage Backend                       │   │
│  │        Memory  ←→  SQLite  ←→  Redis (distributed)      │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Backend Options

| Backend | Use Case | Persistence | Performance |
|---------|----------|-------------|-------------|
| **Memory** | Development, single-agent | No | Fastest |
| **SQLite** | Single-machine, persistent | Yes | Fast |
| **Redis** | Distributed, multi-server | Yes | Fast + Scalable |

## Benefits for Agent Developers

```python
# Before: Tight coupling
class MyAgent:
    def __init__(self):
        self.cache = InMemoryCache()  # Each agent has own cache
        self.token_counter = TokenCounter()  # Duplicated logic

# After: Use cache MCP server
class MyAgent:
    async def get_context(self, keys, budget):
        return await self.mcp_client.call_tool("get_context_for_llm", {
            "agent_id": self.id,
            "context_keys": keys,
            "purpose": "context"
        })
```

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol SDK
- `ison-cache>=1.0.0` - ISONCache core library

## License

MIT License
