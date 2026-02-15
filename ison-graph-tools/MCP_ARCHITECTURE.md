# ISONGraph MCP Architecture - Separation of Concerns

## Overview

By separating ISONCache as a dedicated MCP server, we enable a **layered architecture** where cache becomes a shared service rather than embedded in each tool.

## Architecture Comparison

### Monolithic (Before)

```
┌────────────────────────────────────────────────────────────────┐
│                    Single MCP Server                           │
│                                                                │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐    │
│  │ Memory   │Governance│ Learning │ GDPR     │ HIPAA    │    │
│  │ [cache]  │ [cache]  │ [cache]  │ [cache]  │ [cache]  │    │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘    │
│                                                                │
│  Problems:                                                     │
│  - Each tool has its own cache (duplicated data)              │
│  - No token budget coordination                                │
│  - Cache lost when server restarts                             │
│  - Can't scale cache independently                             │
│  - Tight coupling between tools and caching logic              │
└────────────────────────────────────────────────────────────────┘
```

### Separated (After)

```
┌────────────────────────────────────────────────────────────────┐
│                      AI Agents Layer                           │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │  Claude  │  │  GPT-4   │  │  Gemini  │  │ Custom   │      │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘      │
└───────┼─────────────┼─────────────┼─────────────┼─────────────┘
        │             │             │             │
        ▼             ▼             ▼             ▼
┌────────────────────────────────────────────────────────────────┐
│                    Tool MCP Servers Layer                      │
│                                                                │
│  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐│
│  │  Agent MCP      │  │  Compliance MCP │  │  Code Flow MCP ││
│  │  - Memory       │  │  - GDPR         │  │  - Analysis    ││
│  │  - Governance   │  │  - CCPA         │  │  - Queries     ││
│  │  - Learning     │  │  - HIPAA        │  │                ││
│  └────────┬────────┘  └────────┬────────┘  └───────┬────────┘│
└───────────┼────────────────────┼───────────────────┼──────────┘
            │                    │                   │
            └────────────────────┼───────────────────┘
                                 │
                                 ▼
┌────────────────────────────────────────────────────────────────┐
│                   ISONCache MCP Server                         │
│                   (Shared Data Layer)                          │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │              Token Budget Coordinator                    │  │
│  │  - Per-agent budgets    - Cross-agent coordination      │  │
│  │  - Purpose allocations  - Automatic reset               │  │
│  └─────────────────────────────────────────────────────────┘  │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │  Key-Value   │  │    Graph     │  │  Embedding   │        │
│  │    Cache     │  │    Cache     │  │    Cache     │        │
│  │  (ISON fmt)  │  │ (traversal)  │  │  (vectors)   │        │
│  └──────────────┘  └──────────────┘  └──────────────┘        │
│                                                                │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                   Persistence Layer                      │  │
│  │         Memory ←→ SQLite ←→ Redis (distributed)         │  │
│  └─────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────┘
```

## Benefits of Separation

### 1. Single Source of Truth

| Problem | Solution |
|---------|----------|
| Agent 1 caches user context | **Centralized**: One cache for all agents |
| Agent 2 caches same user context | **No duplication**: Shared cache entries |
| Inconsistency between caches | **Consistency**: Single source |

```python
# Agent 1 caches context
await cache_mcp.call("cache_set", {"key": "user:123:context", "value": {...}})

# Agent 2 reads same context (no duplication)
context = await cache_mcp.call("cache_get", {"key": "user:123:context"})
```

### 2. Coordinated Token Budgets

```
Without ISONCache MCP:
┌─────────────────┐  ┌─────────────────┐
│     Agent 1     │  │     Agent 2     │
│ budget: 4000    │  │ budget: 4000    │
│ used: 3500      │  │ used: 3800      │
│                 │  │                 │
│ (no coordination - might exceed total LLM limit)
└─────────────────┘  └─────────────────┘

With ISONCache MCP:
┌─────────────────────────────────────────┐
│           ISONCache MCP                  │
│  Total Budget: 8000 tokens               │
│  ┌─────────────────────────────────┐    │
│  │ Agent 1: 3500/4000 allocated    │    │
│  │ Agent 2: 3800/4000 allocated    │    │
│  │ System:  700 remaining          │    │
│  │                                 │    │
│  │ Coordination: If Agent 1 needs  │    │
│  │ more, can borrow from Agent 2   │    │
│  └─────────────────────────────────┘    │
└─────────────────────────────────────────┘
```

### 3. Persistence & Durability

```
Without:
Agent restarts → Cache lost → Cold start every time

With ISONCache MCP:
┌─────────────────────────────────────────┐
│           ISONCache MCP                  │
│                                         │
│  Agent restarts → Cache persists        │
│                                         │
│  ┌───────────┐                          │
│  │  Memory   │ ←── Hot data             │
│  └─────┬─────┘                          │
│        │ spillover                      │
│  ┌─────▼─────┐                          │
│  │  SQLite   │ ←── Persistent           │
│  └─────┬─────┘                          │
│        │ scale out                      │
│  ┌─────▼─────┐                          │
│  │   Redis   │ ←── Distributed          │
│  └───────────┘                          │
└─────────────────────────────────────────┘
```

### 4. Cross-Agent Context Sharing

```python
# Research Agent caches findings
await cache_mcp.call("cache_set", {
    "key": "research:ai_safety",
    "value": {"findings": [...], "sources": [...]},
    "namespace": "research_agent",
    "tags": ["research", "shareable"]
})

# Share with Writing Agent
await cache_mcp.call("share_cache", {
    "source_namespace": "research_agent",
    "target_namespace": "writing_agent",
    "key_pattern": "research:*"
})

# Writing Agent accesses shared research
result = await cache_mcp.call("cache_get", {
    "key": "research:ai_safety",
    "namespace": "writing_agent"
})

# Collaborative workflow without tight coupling!
```

### 5. Independent Scaling

```
Monolithic:
┌─────────────────────────────┐
│  All-in-one MCP Server      │
│  (can't scale parts)        │
│  CPU: High, Memory: High    │
└─────────────────────────────┘

Separated:
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  Agent MCP   │  │ Compliance   │  │  Cache MCP   │
│  CPU: High   │  │ CPU: Low     │  │ Memory: High │
│  Memory: Low │  │ Memory: Low  │  │ CPU: Low     │
│              │  │              │  │              │
│  Scale: +CPU │  │  Scale: -    │  │ Scale: +RAM  │
└──────────────┘  └──────────────┘  └──────────────┘
                                           │
                                    Scale separately!
                                           │
                              ┌────────────┴────────────┐
                              │     Redis Cluster       │
                              │  (horizontal scaling)   │
                              └─────────────────────────┘
```

### 6. Failure Isolation

```
Monolithic:
Cache bug → Entire server crashes → All tools unavailable

Separated:
┌────────────┐  ┌────────────┐
│ Agent MCP  │  │ Cache MCP  │
│   (OK)     │  │  (crash)   │
└────────────┘  └────────────┘
       │              │
       │              X (failure)
       │
       └── Agent MCP continues with degraded caching
           (can fallback to no-cache mode)
```

## Recommended MCP Server Layout

```
┌─────────────────────────────────────────────────────────────────┐
│                    Production Deployment                        │
│                                                                 │
│  Layer 1: AI Agents                                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐                        │
│  │ Claude  │  │ Custom  │  │ Swarm   │                        │
│  └────┬────┘  └────┬────┘  └────┬────┘                        │
│       │            │            │                              │
│  Layer 2: Domain MCP Servers                                    │
│  ┌─────────────────┐  ┌─────────────────┐                     │
│  │  isongraph-     │  │  isongraph-     │                     │
│  │  agent-mcp      │  │  compliance-mcp │                     │
│  │  - Memory       │  │  - GDPR         │                     │
│  │  - Governance   │  │  - CCPA         │                     │
│  │  - Learning     │  │  - HIPAA        │                     │
│  │  - Code Flow    │  │  - EU AI Act    │                     │
│  └────────┬────────┘  └────────┬────────┘                     │
│           │                    │                               │
│  Layer 3: Shared Services                                       │
│  ┌─────────────────────────────────────────────────────────┐  │
│  │                 ison-cache-mcp                           │  │
│  │  - Token Budget Management                               │  │
│  │  - ISON-format Caching (72% savings)                    │  │
│  │  - Graph Caching                                         │  │
│  │  - Embedding Storage                                     │  │
│  │  - Cross-agent Sharing                                   │  │
│  └─────────────────────────────────────────────────────────┘  │
│                            │                                   │
│  Layer 4: Storage                                               │
│  ┌───────────┐  ┌───────────┐  ┌───────────┐                 │
│  │  SQLite   │  │   Redis   │  │  Postgres │                 │
│  │  (local)  │  │ (cluster) │  │  (graphs) │                 │
│  └───────────┘  └───────────┘  └───────────┘                 │
└─────────────────────────────────────────────────────────────────┘
```

## Configuration Examples

### Claude Desktop - Multiple MCP Servers

```json
{
  "mcpServers": {
    "cache": {
      "command": "python",
      "args": ["-m", "ison_cache_mcp.server"],
      "env": {
        "CACHE_BACKEND": "redis",
        "REDIS_URL": "redis://localhost:6379"
      }
    },
    "agent": {
      "command": "python",
      "args": ["-m", "isongraph_agent_mcp.server"],
      "env": {
        "CACHE_MCP_URL": "stdio://cache"
      }
    },
    "compliance": {
      "command": "python",
      "args": ["-m", "isongraph_compliance_mcp.server"],
      "env": {
        "CACHE_MCP_URL": "stdio://cache"
      }
    }
  }
}
```

### Docker Compose - Distributed Setup

```yaml
version: '3.8'
services:
  cache-mcp:
    image: isongraph/cache-mcp:latest
    environment:
      - CACHE_BACKEND=redis
      - REDIS_URL=redis://redis:6379
    ports:
      - "8001:8001"

  agent-mcp:
    image: isongraph/agent-mcp:latest
    environment:
      - CACHE_MCP_URL=http://cache-mcp:8001
    depends_on:
      - cache-mcp

  compliance-mcp:
    image: isongraph/compliance-mcp:latest
    environment:
      - CACHE_MCP_URL=http://cache-mcp:8001
    depends_on:
      - cache-mcp

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

volumes:
  redis-data:
```

## Summary

| Aspect | Monolithic | Separated |
|--------|------------|-----------|
| Cache duplication | Yes | No |
| Token coordination | No | Yes |
| Persistence | Per-server | Centralized |
| Cross-agent sharing | Complex | Simple |
| Scaling | All-or-nothing | Independent |
| Failure isolation | No | Yes |
| Complexity | Lower | Moderate |
| Best for | Prototyping | Production |

**Recommendation**: Start with monolithic for development, separate cache for production multi-agent systems.
