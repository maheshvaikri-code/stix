# ISONGraph MCP Server

**The Foundation Layer** - Core graph operations MCP server for ISONGraph.

All other ISONGraph MCP servers depend on this for graph storage and queries.

## Why This Server?

ISONGraph is a lightweight, production-ready graph store built on ISON format:

| Feature | ISONGraph | Neo4j |
|---------|-----------|-------|
| Token Efficiency | Native ISON (72% savings) | Requires conversion |
| LLM Optimized | Built for AI context | General purpose |
| Query Language | ISONQL | Cypher |
| Overhead | Minimal | JVM, memory heavy |
| Deployment | Embedded or standalone | Server required |

## Quick Start

### Installation

```bash
pip install isongraph-mcp
```

### Run the Server

```bash
isongraph-mcp
# or
python -m isongraph_mcp.server
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "isongraph": {
      "command": "python",
      "args": ["-m", "isongraph_mcp.server"]
    }
  }
}
```

## Tools (35+)

### Graph Management

| Tool | Description |
|------|-------------|
| `graph_create` | Create a new graph |
| `graph_load` | Load from .ison/.isonl file |
| `graph_save` | Save to file |
| `graph_clone` | Clone a graph |
| `graph_merge` | Merge two graphs |
| `graph_stats` | Get statistics |
| `graph_delete` | Delete from memory |
| `graph_list` | List all graphs |
| `graph_set_default` | Set default graph |

### Node Operations

| Tool | Description |
|------|-------------|
| `node_add` | Add a node |
| `node_get` | Get by type:id |
| `node_update` | Update properties |
| `node_delete` | Delete node and edges |
| `node_find` | Find by properties |
| `node_count` | Count by type |
| `node_types` | List all types |

### Edge Operations

| Tool | Description |
|------|-------------|
| `edge_add` | Add relationship |
| `edge_get` | Get edge |
| `edge_delete` | Delete edge |
| `edge_find` | Find edges |
| `edge_count` | Count by type |
| `edge_types` | List all types |

### Traversal

| Tool | Description |
|------|-------------|
| `traverse_neighbors` | Get neighbors |
| `traverse_multi_hop` | N hops away |
| `traverse_pattern` | Follow pattern |
| `shortest_path` | BFS shortest path |
| `all_paths` | DFS all paths |

### ISONQL Queries

| Tool | Description |
|------|-------------|
| `query_execute` | Execute ISONQL pattern |

### Analysis

| Tool | Description |
|------|-------------|
| `analyze_connectivity` | Check connectivity |
| `analyze_cycles` | Detect cycles |
| `node_degree` | In/out/total degree |

### Serialization

| Tool | Description |
|------|-------------|
| `to_ison` | Serialize to ISON |
| `to_dict` | Serialize to JSON |
| `from_dict` | Load from JSON |

## Example Usage

### Create and Populate a Graph

```python
# Create a graph
await mcp.call_tool("graph_create", {"graph_id": "social"})

# Add nodes
await mcp.call_tool("node_add", {
    "node_type": "person",
    "node_id": 1,
    "properties": {"name": "Alice", "age": 30}
})

await mcp.call_tool("node_add", {
    "node_type": "person",
    "node_id": 2,
    "properties": {"name": "Bob", "age": 25}
})

# Add edge
await mcp.call_tool("edge_add", {
    "rel_type": "KNOWS",
    "source_type": "person",
    "source_id": 1,
    "target_type": "person",
    "target_id": 2,
    "properties": {"since": 2020}
})
```

### Traversal

```python
# Get neighbors
neighbors = await mcp.call_tool("traverse_neighbors", {
    "node_type": "person",
    "node_id": 1,
    "rel_type": "KNOWS"
})
# Returns: {"neighbors": [":person:2"], "count": 1}

# Multi-hop (friends of friends)
fof = await mcp.call_tool("traverse_multi_hop", {
    "node_type": "person",
    "node_id": 1,
    "rel_type": "KNOWS",
    "hops": 2
})
```

### ISONQL Query

```python
# Find friends 2 hops away
result = await mcp.call_tool("query_execute", {
    "query": ":person:1 -[:KNOWS*2]-> *"
})
```

### Save and Load

```python
# Save to file
await mcp.call_tool("graph_save", {
    "path": "social.ison"
})

# Load from file
await mcp.call_tool("graph_load", {
    "path": "social.ison",
    "graph_id": "social_loaded"
})
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AI Agents                                │
│     Claude  │  GPT-4  │  Gemini  │  Custom Agents               │
└──────────────────────────────────────────────────────────────────┘
                               │
                               │ MCP Protocol
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ISONGraph MCP Server                          │
│                    (This Server)                                 │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Graph Operations                         │ │
│  │  Create │ Load │ Save │ Clone │ Merge │ Stats │ Delete    │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │  Node Operations │  │  Edge Operations │  │  Traversal    │ │
│  │  Add │ Get │ Del │  │  Add │ Get │ Del │  │  Neighbors    │ │
│  │  Update │ Find   │  │  Find │ Count    │  │  Multi-hop    │ │
│  └──────────────────┘  └──────────────────┘  │  Pattern      │ │
│                                               │  Paths        │ │
│  ┌──────────────────┐  ┌──────────────────┐  └───────────────┘ │
│  │  ISONQL Queries  │  │  Analysis        │                    │
│  │  Pattern queries │  │  Connectivity    │                    │
│  │                  │  │  Cycles │ Degree │                    │
│  └──────────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                        ISONGraph Core                            │
│  In-memory property graph with ISON persistence                  │
└─────────────────────────────────────────────────────────────────┘
```

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol SDK
- `ison-graph>=1.0.0` - ISONGraph core library

## License

MIT License
