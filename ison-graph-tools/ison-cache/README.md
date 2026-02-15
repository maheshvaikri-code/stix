# ISONCache

**Token-Efficient Cache for LLM Applications**

ISONCache is a caching system specifically designed for Large Language Model (LLM) applications. It uses the ISON format to achieve 50-70% token reduction compared to JSON, enabling more efficient context injection and better utilization of limited context windows.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Components](#core-components)
  - [ISONCache (Key-Value)](#isoncache-key-value)
  - [ISONGraphCache (Graph)](#isongraphcache-graph)
  - [EmbeddingCache (Vector)](#embeddingcache-vector)
- [Token Management](#token-management)
- [Server Protocols](#server-protocols)
  - [MCP Server](#mcp-server)
  - [Redis Protocol (RESP)](#redis-protocol-resp)
  - [HTTP REST API](#http-rest-api)
- [CLI Reference](#cli-reference)
- [Configuration](#configuration)
- [Use Cases](#use-cases)
- [Architecture](#architecture)
- [API Reference](#api-reference)

---

## Features

| Feature | Description |
|---------|-------------|
| **Token Efficiency** | 50-70% fewer tokens than JSON using ISON format |
| **Token Budgeting** | Retrieve as much data as fits within N tokens |
| **Graph Caching** | Store and traverse knowledge graphs with hop limits |
| **Embedding Search** | Semantic similarity search with token budgets |
| **Multiple Protocols** | MCP, Redis (RESP), HTTP REST API support |
| **Eviction Policies** | LRU, LFU, FIFO, TTL, Priority-based eviction |
| **Persistence** | In-memory and SQLite backends |

---

## Installation

### Basic Installation

```bash
cd tools/ison-cache
pip install -e .
```

### With Optional Dependencies

```bash
# MCP server support (for Claude integration)
pip install -e ".[mcp]"

# HTTP/REST API (FastAPI + Uvicorn)
pip install -e ".[http]"

# Embedding support (sentence-transformers)
pip install -e ".[embeddings]"

# Redis protocol enhancements
pip install -e ".[redis]"

# Everything
pip install -e ".[all]"

# Development (includes pytest)
pip install -e ".[dev]"
```

---

## Quick Start

### Python API

```python
from ison_cache import ISONCache, ISONGraphCache, EmbeddingCache
from ison_cache.schema import Priority

# ============================================================
# 1. Basic Key-Value Caching
# ============================================================

cache = ISONCache(max_memory_mb=100, default_ttl=3600)

# Store data - tokens are automatically counted
cache.set("user:101", {
    "id": 101,
    "name": "Alice Chen",
    "email": "alice@example.com",
    "role": "admin"
})

# Retrieve as ISON format (ready for LLM context)
ison_output = cache.get("user:101")
print(ison_output)
# Output:
# object.user_101
# id name email role
# 101 "Alice Chen" alice@example.com admin

# ============================================================
# 2. Token-Budgeted Retrieval
# ============================================================

# Get as many items as fit within 500 tokens
result = cache.get_within_budget(
    patterns="user:*",
    token_budget=500,
    priority=Priority.HITS  # Most accessed first
)

print(f"Used {result.tokens_used} of {result.tokens_budget} tokens")
print(f"Included: {result.keys_included}")
print(f"Excluded: {result.keys_excluded}")
print(result.ison)  # Combined ISON output

# ============================================================
# 3. Graph Caching with Traversal
# ============================================================

graph_cache = ISONGraphCache()

# Store a knowledge graph
entities = [
    {"id": "user:101", "type": "person", "name": "Alice"},
    {"id": "user:102", "type": "person", "name": "Bob"},
    {"id": "project:1", "type": "project", "name": "ISON"},
]
relations = [
    {"from": "user:101", "to": "project:1", "type": "CREATED"},
    {"from": "user:102", "to": "project:1", "type": "CONTRIBUTES"},
]

graph_cache.set_graph("knowledge:main", entities, relations)

# Multi-hop traversal with token budget
result = graph_cache.traverse(
    start_entity="user:101",
    max_hops=2,
    token_budget=1000
)
print(result.ison)

# ============================================================
# 4. Embedding Similarity Search
# ============================================================

emb_cache = EmbeddingCache(embedding_model="all-MiniLM-L6-v2")

# Store documents
emb_cache.set("doc:1", "Machine learning is a subset of AI")
emb_cache.set("doc:2", "Deep learning uses neural networks")
emb_cache.set("doc:3", "Python is a programming language")

# Semantic search
results = emb_cache.search("artificial intelligence", k=2)
for r in results:
    print(f"{r.key}: {r.text} (score: {r.score:.3f})")
```

### CLI Quick Start

```bash
# Set and get values
isoncache cache set user:101 '{"id": 101, "name": "Alice"}'
isoncache cache get user:101

# List keys
isoncache cache keys "user:*"

# View statistics
isoncache cache stats

# Start servers
isoncache server mcp   # MCP for Claude
isoncache server http  # REST API on port 8380
isoncache server resp  # Redis protocol on port 6380
```

---

## Core Components

### ISONCache (Key-Value)

The primary cache for storing and retrieving key-value pairs with automatic ISON serialization.

#### Constructor

```python
ISONCache(
    config: Optional[CacheConfig] = None,
    max_memory_mb: int = 1024,      # Maximum memory usage
    default_ttl: int = 3600,        # Default TTL in seconds
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
    token_model: str = "cl100k_base"  # Tokenizer model
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `set(key, value, ttl, tags, priority)` | Store a value |
| `get(key, max_tokens, format)` | Retrieve value as ISON |
| `get_raw(key)` | Get raw Python value |
| `delete(key)` | Delete a key |
| `exists(key)` | Check if key exists |
| `ttl(key)` | Get remaining TTL |
| `expire(key, ttl)` | Set new TTL |
| `persist(key)` | Remove TTL |
| `mset(items, ttl)` | Set multiple keys |
| `mget(keys, max_tokens, merge)` | Get multiple as combined ISON |
| `mdelete(keys)` | Delete multiple keys |
| `keys(pattern)` | Get keys matching glob pattern |
| `scan(pattern, count, cursor)` | Incrementally scan keys |
| `get_within_budget(patterns, token_budget, priority)` | Token-budgeted retrieval |
| `get_by_tag(tag)` | Get keys with tag |
| `delete_by_tag(tag)` | Delete keys with tag |
| `clear()` | Clear all entries |
| `stats()` | Get statistics |

#### Examples

```python
from ison_cache import ISONCache
from ison_cache.schema import Priority, EvictionPolicy

# Create cache with custom settings
cache = ISONCache(
    max_memory_mb=512,
    default_ttl=7200,
    eviction_policy=EvictionPolicy.LFU  # Least Frequently Used
)

# Store with tags and priority
cache.set(
    "product:1001",
    {"id": 1001, "name": "Laptop", "price": 999.99},
    ttl=3600,
    tags=["electronics", "featured"],
    priority=10  # Higher priority = kept longer during eviction
)

# Store multiple items
cache.mset({
    "product:1002": {"id": 1002, "name": "Mouse", "price": 49.99},
    "product:1003": {"id": 1003, "name": "Keyboard", "price": 79.99},
}, ttl=3600)

# Get combined output (merges into table format)
combined = cache.mget(["product:1001", "product:1002", "product:1003"])
print(combined)
# Output:
# table.product
# id name price
# 1001 Laptop 999.99
# 1002 Mouse 49.99
# 1003 Keyboard 79.99

# Token-budgeted retrieval with priority
result = cache.get_within_budget(
    patterns=["product:*", "user:*"],
    token_budget=1000,
    priority=Priority.RECENT,  # Most recently accessed first
    exclude_keys={"product:1001"}  # Exclude specific keys
)

# Get items by tag
electronics = cache.get_by_tag("electronics")
```

---

### ISONGraphCache (Graph)

Cache for storing and traversing knowledge graphs.

#### Constructor

```python
ISONGraphCache(
    config: Optional[CacheConfig] = None,
    default_ttl: int = 3600,
    token_model: str = "cl100k_base"
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `set_graph(key, entities, relations, observations, ttl)` | Store a graph |
| `get_graph(key, max_tokens)` | Get graph as ISON |
| `get_graph_raw(key)` | Get raw GraphEntry |
| `delete(key)` | Delete a graph |
| `traverse(start_entity, max_hops, relation_types, token_budget, direction)` | Multi-hop traversal |
| `get_neighbors(entity_id, relation_types, direction)` | Get immediate neighbors |
| `find_path(from_entity, to_entity, max_hops, relation_types)` | Find shortest path |
| `get_entity(entity_id)` | Get entity by ID |
| `find_entities(entity_type, name_pattern, **properties)` | Find entities |
| `merge_graph(key, entities, relations)` | Merge into existing graph |
| `stats()` | Get statistics |
| `clear()` | Clear all graphs |

#### Examples

```python
from ison_cache import ISONGraphCache

graph_cache = ISONGraphCache()

# Define a knowledge graph
entities = [
    {"id": "alice", "type": "person", "name": "Alice Chen", "role": "engineer"},
    {"id": "bob", "type": "person", "name": "Bob Smith", "role": "designer"},
    {"id": "ison", "type": "project", "name": "ISON Format", "status": "active"},
    {"id": "cache", "type": "project", "name": "ISONCache", "status": "active"},
    {"id": "acme", "type": "company", "name": "Acme Corp"},
]

relations = [
    {"from": "alice", "to": "ison", "type": "CREATED"},
    {"from": "alice", "to": "cache", "type": "CREATED"},
    {"from": "bob", "to": "ison", "type": "CONTRIBUTES_TO"},
    {"from": "alice", "to": "acme", "type": "WORKS_AT"},
    {"from": "bob", "to": "acme", "type": "WORKS_AT"},
    {"from": "ison", "to": "acme", "type": "OWNED_BY"},
]

# Store the graph
graph_cache.set_graph("knowledge:main", entities, relations, ttl=7200)

# Traverse 2 hops from Alice
result = graph_cache.traverse(
    start_entity="alice",
    max_hops=2,
    direction="out",  # "out", "in", or "both"
    token_budget=500
)
print(f"Found {len(result.entities_included)} entities")
print(f"Traversed {result.hops_traversed} hops")
print(f"Used {result.tokens_used} tokens")
print(result.ison)

# Filter by relation types
projects_result = graph_cache.traverse(
    start_entity="alice",
    max_hops=1,
    relation_types=["CREATED", "CONTRIBUTES_TO"]
)

# Get neighbors
neighbors = graph_cache.get_neighbors("alice", direction="out")

# Find path between entities
path = graph_cache.find_path("alice", "bob", max_hops=3)
if path:
    print("Path found:", [r["type"] for r in path])

# Find entities by criteria
engineers = graph_cache.find_entities(entity_type="person", role="engineer")
active_projects = graph_cache.find_entities(entity_type="project", status="active")

# Merge new data into existing graph
graph_cache.merge_graph("knowledge:main",
    entities=[{"id": "carol", "type": "person", "name": "Carol"}],
    relations=[{"from": "carol", "to": "cache", "type": "CONTRIBUTES_TO"}]
)
```

---

### EmbeddingCache (Vector)

Cache for text embeddings with similarity search.

#### Constructor

```python
EmbeddingCache(
    config: Optional[CacheConfig] = None,
    embedding_model: Optional[str] = None,  # e.g., "all-MiniLM-L6-v2"
    embedding_dim: int = 384,
    default_ttl: int = 86400
)
```

#### Methods

| Method | Description |
|--------|-------------|
| `set(key, text, vector, metadata, ttl)` | Store text with embedding |
| `get(key)` | Get embedding entry |
| `delete(key)` | Delete entry |
| `search(query, k, metric, token_budget, filter_fn)` | Similarity search |
| `search_by_vector(vector, k, metric)` | Search with pre-computed vector |
| `search_to_ison(query, k, token_budget)` | Search returning ISON |
| `mset(items, vectors, ttl)` | Batch set |
| `batch_embed(texts)` | Batch compute embeddings |
| `reindex()` | Recompute all embeddings |
| `stats()` | Get statistics |
| `clear()` | Clear all entries |

#### Examples

```python
from ison_cache import EmbeddingCache

# With sentence-transformers model
emb_cache = EmbeddingCache(embedding_model="all-MiniLM-L6-v2")

# Or with custom embedding dimension (uses hash-based fallback)
emb_cache = EmbeddingCache(embedding_dim=384)

# Store documents
documents = [
    ("doc:1", "Machine learning is a subset of artificial intelligence"),
    ("doc:2", "Deep learning uses neural networks with many layers"),
    ("doc:3", "Natural language processing helps computers understand text"),
    ("doc:4", "Computer vision enables image recognition and analysis"),
    ("doc:5", "Reinforcement learning trains agents through rewards"),
]

for key, text in documents:
    emb_cache.set(key, text, metadata={"source": "wiki"})

# Similarity search
results = emb_cache.search("neural networks and AI", k=3)
for r in results:
    print(f"{r.key}: score={r.score:.3f}, tokens={r.tokens}")
    print(f"  {r.text}")

# Search with token budget
results = emb_cache.search(
    "machine learning algorithms",
    k=10,
    token_budget=200  # Only return results fitting in 200 tokens
)

# Search with filter
results = emb_cache.search(
    "deep learning",
    k=5,
    filter_fn=lambda e: e.metadata.get("source") == "wiki"
)

# Get ISON-formatted results
ison_results = emb_cache.search_to_ison("AI applications", k=5)
print(ison_results)

# Batch operations
emb_cache.mset({
    "doc:6": "Generative AI creates new content",
    "doc:7": "Large language models process text",
})

# Pre-compute embeddings
texts = ["query one", "query two", "query three"]
vectors = emb_cache.batch_embed(texts)
```

---

## Token Management

### TokenManager

Count and manage tokens for ISON content.

```python
from ison_cache import TokenManager, TokenBudget

tm = TokenManager(model="cl100k_base")

# Count tokens
count = tm.count_tokens("Hello world")

# Count tokens for a value (estimates ISON format)
tokens = tm.count_value_tokens({"id": 1, "name": "Test"})

# Compare ISON vs JSON
comparison = tm.compare_formats([
    {"id": 1, "name": "Product A", "price": 99.99},
    {"id": 2, "name": "Product B", "price": 149.99},
])
print(f"JSON: {comparison['json_tokens']} tokens")
print(f"ISON: {comparison['ison_tokens']} tokens")
print(f"Savings: {comparison['savings_percent']}%")

# Truncate text to fit budget
truncated, actual_tokens = tm.truncate_to_budget(
    "Long text...",
    budget=100,
    suffix="..."
)
```

### TokenBudget

Track token usage within a budget.

```python
from ison_cache import TokenBudget

budget = TokenBudget(total=1000)

# Check and consume
if budget.can_fit(250):
    budget.consume(250)

print(f"Remaining: {budget.remaining}")
print(f"Utilization: {budget.utilization}%")
```

---

## Server Protocols

### MCP Server

Model Context Protocol server for Claude Desktop integration.

#### Start Server

```bash
isoncache server mcp
```

Or in Python:

```python
from ison_cache.mcp_server import serve
serve()
```

#### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "isoncache": {
      "command": "python",
      "args": ["-m", "ison_cache.mcp_server"],
      "env": {
        "ISONCACHE_MAX_MEMORY_MB": "512",
        "ISONCACHE_DEFAULT_TTL": "3600"
      }
    }
  }
}
```

#### Available MCP Tools

| Tool | Description |
|------|-------------|
| `cache_set` | Store a value with optional TTL |
| `cache_get` | Retrieve value in ISON format |
| `cache_mget` | Get multiple values combined |
| `cache_budget_get` | Get values within token budget |
| `cache_delete` | Delete a key |
| `cache_keys` | List keys matching pattern |
| `cache_stats` | Get cache statistics |
| `graph_set` | Store a knowledge graph |
| `graph_get` | Retrieve graph in ISON format |
| `graph_traverse` | Multi-hop graph traversal |
| `embedding_set` | Store text with embedding |
| `embedding_search` | Semantic similarity search |

---

### Redis Protocol (RESP)

Drop-in Redis replacement with ISON extensions.

#### Start Server

```bash
isoncache server resp --host 127.0.0.1 --port 6380
```

Or in Python:

```python
from ison_cache.protocols.resp import run_server
run_server(host="127.0.0.1", port=6380)
```

#### Supported Commands

**Standard Redis Commands:**
- `SET key value [EX seconds]`
- `GET key`
- `DEL key [key ...]`
- `EXISTS key [key ...]`
- `KEYS pattern`
- `SCAN cursor [MATCH pattern] [COUNT count]`
- `TTL key`
- `EXPIRE key seconds`
- `PERSIST key`
- `MSET key value [key value ...]`
- `MGET key [key ...]`
- `PING [message]`
- `ECHO message`
- `INFO`
- `DBSIZE`
- `FLUSHALL` / `FLUSHDB`

**ISONCache Extensions:**
- `GETISON key [max_tokens]` - Get as ISON with token limit
- `BUDGET pattern token_budget [PRIORITY hits|recent|oldest|tokens]` - Token-budgeted retrieval
- `GRAPHSET key entities_json relations_json [EX seconds]` - Store graph
- `GRAPHGET key [max_tokens]` - Get graph as ISON
- `TRAVERSE entity [HOPS n] [TYPES type1,type2] [BUDGET n] [DIRECTION out|in|both]` - Graph traversal

#### Using with Redis Clients

```python
import redis

# Connect to ISONCache RESP server
r = redis.Redis(host='localhost', port=6380)

# Standard operations work
r.set('user:101', '{"id": 101, "name": "Alice"}')
value = r.get('user:101')

# Use ISON extensions via execute_command
ison_value = r.execute_command('GETISON', 'user:101', 500)

# Token-budgeted retrieval
result = r.execute_command('BUDGET', 'user:*', 1000, 'PRIORITY', 'hits')
```

---

### HTTP REST API

FastAPI-based REST API server.

#### Start Server

```bash
isoncache server http --host 127.0.0.1 --port 8380
```

Or in Python:

```python
from ison_cache.protocols.http import run_server
run_server(host="127.0.0.1", port=8380)
```

#### API Endpoints

**Cache Operations:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/cache/set` | Store a value |
| GET | `/cache/get/{key}` | Get value (ISON or raw) |
| DELETE | `/cache/delete/{key}` | Delete key |
| GET | `/cache/exists/{key}` | Check existence |
| GET | `/cache/ttl/{key}` | Get TTL |
| GET | `/cache/keys?pattern=*` | List keys |
| POST | `/cache/mset` | Set multiple |
| POST | `/cache/mget` | Get multiple |
| POST | `/cache/budget` | Token-budgeted get |
| GET | `/cache/stats` | Statistics |
| POST | `/cache/clear` | Clear cache |

**Graph Operations:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/graph/set` | Store graph |
| GET | `/graph/get/{key}` | Get graph |
| DELETE | `/graph/delete/{key}` | Delete graph |
| POST | `/graph/traverse` | Traverse graph |
| GET | `/graph/entity/{entity_id}` | Get entity |
| GET | `/graph/stats` | Statistics |

**Embedding Operations:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/embedding/set` | Store with embedding |
| POST | `/embedding/search` | Similarity search |
| GET | `/embedding/search/ison` | Search as ISON |
| GET | `/embedding/stats` | Statistics |

**System:**

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/info` | Server info |

#### Example Requests

```bash
# Store a value
curl -X POST http://localhost:8380/cache/set \
  -H "Content-Type: application/json" \
  -d '{"key": "user:101", "value": {"id": 101, "name": "Alice"}, "ttl": 3600}'

# Get value as ISON
curl http://localhost:8380/cache/get/user:101

# Token-budgeted retrieval
curl -X POST http://localhost:8380/cache/budget \
  -H "Content-Type: application/json" \
  -d '{"patterns": "user:*", "token_budget": 500, "priority": "hits"}'

# Store graph
curl -X POST http://localhost:8380/graph/set \
  -H "Content-Type: application/json" \
  -d '{
    "key": "knowledge:main",
    "entities": [{"id": "alice", "name": "Alice"}],
    "relations": [{"from": "alice", "to": "project:1", "type": "CREATED"}]
  }'

# Traverse graph
curl -X POST http://localhost:8380/graph/traverse \
  -H "Content-Type: application/json" \
  -d '{"start_entity": "alice", "max_hops": 2, "token_budget": 500}'

# Similarity search
curl -X POST http://localhost:8380/embedding/search \
  -H "Content-Type: application/json" \
  -d '{"query": "machine learning", "k": 5}'
```

---

## CLI Reference

### Cache Commands

```bash
# Set a value
isoncache cache set <key> <value> [--ttl SECONDS] [--tags TAG1 TAG2]

# Get a value
isoncache cache get <key> [--max-tokens N] [--raw]

# Delete keys
isoncache cache delete <key> [<key> ...]

# List keys
isoncache cache keys [--pattern PATTERN]

# View statistics
isoncache cache stats

# Clear cache
isoncache cache clear

# Token-budgeted retrieval
isoncache cache budget <pattern> <token_budget> [--priority hits|recent|oldest|tokens]
```

### Graph Commands

```bash
# Set graph from JSON files
isoncache graph set <key> <entities.json> <relations.json> [--ttl SECONDS]

# Get graph
isoncache graph get <key> [--max-tokens N]

# Traverse from entity
isoncache graph traverse <entity> [--hops N] [--types TYPE1 TYPE2] [--budget N] [--direction out|in|both]

# View statistics
isoncache graph stats
```

### Server Commands

```bash
# Start MCP server
isoncache server mcp

# Start HTTP server
isoncache server http [--host HOST] [--port PORT]

# Start Redis protocol server
isoncache server resp [--host HOST] [--port PORT]
```

### Utility Commands

```bash
# Compare ISON vs JSON tokens
isoncache compare '{"id": 1, "name": "Test"}'

# Count tokens
isoncache tokenize "Some text to count"

# Show info
isoncache info
```

---

## Configuration

### CacheConfig

```python
from ison_cache.schema import CacheConfig, EvictionPolicy

config = CacheConfig(
    # Memory limits
    max_memory_mb=1024,
    max_entries=100000,

    # TTL settings
    default_ttl_seconds=3600,
    min_ttl_seconds=1,
    max_ttl_seconds=86400 * 30,

    # Eviction
    eviction_policy=EvictionPolicy.LRU,
    eviction_batch_size=100,

    # Token settings
    default_token_budget=4000,
    token_model="cl100k_base",

    # Persistence
    persist_path="/path/to/cache.db",
    persist_interval_seconds=300,

    # Server settings
    host="127.0.0.1",
    port=6380,
    enable_mcp=True,
    enable_http=False,
    enable_resp=False,
)

cache = ISONCache(config=config)
```

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ISONCACHE_BACKEND` | Storage backend (memory, sqlite) | memory |
| `ISONCACHE_PATH` | SQLite database path | :memory: |
| `ISONCACHE_MAX_MEMORY_MB` | Maximum memory in MB | 1024 |
| `ISONCACHE_DEFAULT_TTL` | Default TTL in seconds | 3600 |
| `ISONCACHE_TOKEN_MODEL` | Tokenizer model | cl100k_base |

---

## Use Cases

### 1. RAG Context Caching

```python
import hashlib
from ison_cache import ISONCache

cache = ISONCache(default_ttl=300)  # 5-minute cache

def get_rag_context(query: str, retriever) -> str:
    # Create cache key from query hash
    query_hash = hashlib.md5(query.encode()).hexdigest()[:16]
    cache_key = f"rag:{query_hash}"

    # Check cache first
    cached = cache.get(cache_key)
    if cached:
        return cached

    # Retrieve and cache
    chunks = retriever.retrieve(query)
    cache.set(cache_key, {
        "query": query,
        "chunks": chunks,
        "timestamp": datetime.now().isoformat()
    })

    return cache.get(cache_key)
```

### 2. Agent Session Memory

```python
from ison_cache import ISONGraphCache

graph_cache = ISONGraphCache(default_ttl=7200)  # 2-hour sessions

def update_session_memory(session_id: str, entities: list, relations: list):
    """Add new knowledge to session memory"""
    graph_cache.merge_graph(
        f"session:{session_id}",
        entities=entities,
        relations=relations
    )

def get_relevant_context(session_id: str, current_topic: str, token_budget: int) -> str:
    """Get relevant subgraph for current conversation"""
    result = graph_cache.traverse(
        start_entity=current_topic,
        max_hops=2,
        token_budget=token_budget
    )
    return result.ison
```

### 3. Tool Results Caching

```python
from ison_cache import ISONCache
from ison_cache.schema import Priority

cache = ISONCache()

# Cache tool results with appropriate TTLs
cache.set("weather:austin:today", weather_api_result, ttl=1800)  # 30 min
cache.set("stock:AAPL:quote", stock_api_result, ttl=60)  # 1 min
cache.set("news:tech:latest", news_api_result, ttl=300)  # 5 min

# Retrieve all relevant tool context within budget
result = cache.get_within_budget(
    patterns=["weather:*", "stock:*", "news:*"],
    token_budget=1500,
    priority=Priority.RECENT
)

# Use in prompt
context = f"""
Current context:
{result.ison}
"""
```

### 4. Semantic Document Cache

```python
from ison_cache import EmbeddingCache

# Initialize with sentence-transformers model
emb_cache = EmbeddingCache(
    embedding_model="all-MiniLM-L6-v2",
    default_ttl=86400  # 24 hours
)

# Index documents
for doc in documents:
    emb_cache.set(
        key=f"doc:{doc['id']}",
        text=doc['content'],
        metadata={"title": doc['title'], "source": doc['source']}
    )

# Query with token budget
def get_relevant_docs(query: str, token_budget: int) -> str:
    results = emb_cache.search(
        query=query,
        k=20,
        token_budget=token_budget
    )

    # Format for LLM
    return emb_cache.search_to_ison(query, k=len(results))
```

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           ISONCache Server                               │
├─────────────────────────────────────────────────────────────────────────┤
│  Protocol Layer                                                          │
│  ├── MCP Server (stdio) ──────────────── Claude Desktop Integration    │
│  ├── HTTP/REST API (FastAPI) ─────────── Web Applications              │
│  └── RESP Protocol ───────────────────── Redis Client Compatibility    │
├─────────────────────────────────────────────────────────────────────────┤
│  Cache Layer                                                             │
│  ├── ISONCache ───────────────────────── Key-Value with ISON output    │
│  ├── ISONGraphCache ──────────────────── Graph storage + traversal     │
│  └── EmbeddingCache ──────────────────── Vector similarity search      │
├─────────────────────────────────────────────────────────────────────────┤
│  Core Services                                                           │
│  ├── TokenManager ────────────────────── Token counting & budgeting    │
│  ├── ISONSerializer ──────────────────── Python ↔ ISON conversion      │
│  └── EvictionEngine ──────────────────── LRU/LFU/TTL/Priority          │
├─────────────────────────────────────────────────────────────────────────┤
│  Storage Backends                                                        │
│  ├── MemoryBackend ───────────────────── In-memory (default)           │
│  └── SQLiteBackend ───────────────────── Persistent storage            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## API Reference

### Schema Classes

```python
from ison_cache.schema import (
    # Cache entry
    CacheEntry,        # Cached value with metadata

    # Configuration
    CacheConfig,       # Full configuration
    EvictionPolicy,    # LRU, LFU, FIFO, TTL, RANDOM, PRIORITY
    ValueType,         # OBJECT, TABLE, GRAPH, RAW, EMBEDDING
    Priority,          # HITS, RECENT, OLDEST, TOKENS, PRIORITY

    # Results
    BudgetResult,      # Token-budgeted retrieval result
    TraversalResult,   # Graph traversal result
    SimilarityResult,  # Embedding search result

    # Graph
    GraphEntry,        # Cached graph

    # Embedding
    EmbeddingEntry,    # Cached embedding

    # Statistics
    CacheStats,        # Cache statistics
)
```

### Serializer Functions

```python
from ison_cache.serializer import (
    to_ison,           # Convert value to ISON string
    from_ison,         # Parse ISON to Python objects
    to_ison_graph,     # Convert graph to ISON
)

# Example
ison_str = to_ison({"id": 1, "name": "Test"}, name="item")
parsed = from_ison(ison_str)
```

---

## License

MIT License - See LICENSE file for details.

## Contributing

Contributions are welcome! Please see the main ISONGraph repository for guidelines.

## Related Projects

- [ISONGraph](../ison-graph/) - Graph database using ISON format
- [ISON Parser](https://github.com/isongraph/ison-py) - ISON format parser
