"""
ISONGraph MCP Server - Core Graph Operations
============================================

The foundation MCP server providing graph operations for ISONGraph.
All other MCP servers depend on this for graph storage and queries.

Tools:
- Graph Management: create, load, save, clone, merge, stats, delete
- Node Operations: add, get, update, delete, find, count
- Edge Operations: add, get, update, delete, find, count
- ISONQL Queries: execute, traverse, match, aggregate, explain
- Schema: set, get, validate, enforce
- Indexing: create, drop, list, rebuild
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import ISONGraph
from ison_graph import (
    ISONGraph,
    Node,
    Edge,
    Path as GraphPath,
    Direction,
    NodeRef,
    GraphError,
    NodeNotFoundError,
    EdgeNotFoundError,
    DuplicateNodeError,
    DuplicateEdgeError,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("isongraph-mcp")

# =============================================================================
# Server State
# =============================================================================

@dataclass
class ServerState:
    """Shared state for the MCP server."""
    graphs: Dict[str, ISONGraph] = field(default_factory=dict)
    default_graph: Optional[str] = None
    data_dir: Path = field(default_factory=lambda: Path("./data"))

    def get_graph(self, graph_id: Optional[str] = None) -> ISONGraph:
        """Get a graph by ID or the default graph."""
        gid = graph_id or self.default_graph
        if not gid:
            raise ValueError("No graph specified and no default graph set")
        if gid not in self.graphs:
            raise ValueError(f"Graph not found: {gid}")
        return self.graphs[gid]

    def ensure_data_dir(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Initialize server and state
server = Server("isongraph-mcp")
state = ServerState()


# =============================================================================
# Tool Definitions
# =============================================================================

TOOLS = [
    # --- Graph Management ---
    Tool(
        name="graph_create",
        description="Create a new graph. Returns graph_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Unique identifier for the graph"},
                "name": {"type": "string", "description": "Display name for the graph"},
                "directed": {"type": "boolean", "default": True, "description": "Whether edges are directed"},
                "set_as_default": {"type": "boolean", "default": True, "description": "Set as default graph"},
            },
            "required": ["graph_id"],
        },
    ),
    Tool(
        name="graph_load",
        description="Load a graph from an ISON/ISONL file.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the .ison or .isonl file"},
                "graph_id": {"type": "string", "description": "ID to assign to the loaded graph"},
                "set_as_default": {"type": "boolean", "default": True},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="graph_save",
        description="Save a graph to an ISON/ISONL file.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Graph to save (uses default if not specified)"},
                "path": {"type": "string", "description": "Output file path"},
                "format": {"type": "string", "enum": ["ison", "isonl", "auto"], "default": "auto"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="graph_clone",
        description="Clone a graph to a new graph_id.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_id": {"type": "string", "description": "Source graph ID"},
                "target_id": {"type": "string", "description": "Target graph ID for the clone"},
            },
            "required": ["source_id", "target_id"],
        },
    ),
    Tool(
        name="graph_merge",
        description="Merge one graph into another.",
        inputSchema={
            "type": "object",
            "properties": {
                "source_id": {"type": "string", "description": "Source graph to merge from"},
                "target_id": {"type": "string", "description": "Target graph to merge into"},
                "overwrite": {"type": "boolean", "default": False, "description": "Overwrite existing nodes/edges"},
            },
            "required": ["source_id", "target_id"],
        },
    ),
    Tool(
        name="graph_stats",
        description="Get statistics about a graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Graph ID (uses default if not specified)"},
            },
        },
    ),
    Tool(
        name="graph_delete",
        description="Delete a graph from memory.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Graph ID to delete"},
            },
            "required": ["graph_id"],
        },
    ),
    Tool(
        name="graph_list",
        description="List all loaded graphs.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="graph_set_default",
        description="Set the default graph for operations.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "Graph ID to set as default"},
            },
            "required": ["graph_id"],
        },
    ),

    # --- Node Operations ---
    Tool(
        name="node_add",
        description="Add a node to the graph. Returns the node reference.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string", "description": "Type of node (e.g., 'person', 'company')"},
                "node_id": {"type": ["string", "integer"], "description": "Unique ID within the type"},
                "properties": {"type": "object", "description": "Node properties"},
            },
            "required": ["node_type", "node_id"],
        },
    ),
    Tool(
        name="node_get",
        description="Get a node by type and ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string"},
                "node_id": {"type": ["string", "integer"]},
            },
            "required": ["node_type", "node_id"],
        },
    ),
    Tool(
        name="node_update",
        description="Update node properties.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string"},
                "node_id": {"type": ["string", "integer"]},
                "properties": {"type": "object", "description": "Properties to update/add"},
            },
            "required": ["node_type", "node_id", "properties"],
        },
    ),
    Tool(
        name="node_delete",
        description="Delete a node and all its edges.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string"},
                "node_id": {"type": ["string", "integer"]},
            },
            "required": ["node_type", "node_id"],
        },
    ),
    Tool(
        name="node_find",
        description="Find nodes matching property criteria.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string", "description": "Filter by type (optional)"},
                "where": {"type": "object", "description": "Property filters (key: value)"},
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    Tool(
        name="node_count",
        description="Count nodes, optionally filtered by type.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string", "description": "Filter by type (optional)"},
            },
        },
    ),
    Tool(
        name="node_types",
        description="Get all node types in the graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
            },
        },
    ),

    # --- Edge Operations ---
    Tool(
        name="edge_add",
        description="Add an edge between two nodes.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "rel_type": {"type": "string", "description": "Relationship type (e.g., 'KNOWS', 'WORKS_AT')"},
                "source_type": {"type": "string"},
                "source_id": {"type": ["string", "integer"]},
                "target_type": {"type": "string"},
                "target_id": {"type": ["string", "integer"]},
                "properties": {"type": "object", "description": "Edge properties"},
            },
            "required": ["rel_type", "source_type", "source_id", "target_type", "target_id"],
        },
    ),
    Tool(
        name="edge_get",
        description="Get an edge by its components.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "rel_type": {"type": "string"},
                "source_type": {"type": "string"},
                "source_id": {"type": ["string", "integer"]},
                "target_type": {"type": "string"},
                "target_id": {"type": ["string", "integer"]},
            },
            "required": ["rel_type", "source_type", "source_id", "target_type", "target_id"],
        },
    ),
    Tool(
        name="edge_delete",
        description="Delete an edge.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "rel_type": {"type": "string"},
                "source_type": {"type": "string"},
                "source_id": {"type": ["string", "integer"]},
                "target_type": {"type": "string"},
                "target_id": {"type": ["string", "integer"]},
            },
            "required": ["rel_type", "source_type", "source_id", "target_type", "target_id"],
        },
    ),
    Tool(
        name="edge_find",
        description="Find edges matching criteria.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "rel_type": {"type": "string", "description": "Filter by relationship type"},
                "source_type": {"type": "string"},
                "source_id": {"type": ["string", "integer"]},
                "target_type": {"type": "string"},
                "target_id": {"type": ["string", "integer"]},
                "limit": {"type": "integer", "default": 100},
            },
        },
    ),
    Tool(
        name="edge_count",
        description="Count edges, optionally filtered by type.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "rel_type": {"type": "string"},
            },
        },
    ),
    Tool(
        name="edge_types",
        description="Get all edge/relationship types in the graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
            },
        },
    ),

    # --- Traversal Operations ---
    Tool(
        name="traverse_neighbors",
        description="Get neighboring nodes.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string"},
                "node_id": {"type": ["string", "integer"]},
                "rel_type": {"type": "string", "description": "Filter by relationship type"},
                "direction": {"type": "string", "enum": ["out", "in", "both"], "default": "out"},
            },
            "required": ["node_type", "node_id"],
        },
    ),
    Tool(
        name="traverse_multi_hop",
        description="Get nodes N hops away.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string"},
                "node_id": {"type": ["string", "integer"]},
                "hops": {"type": "integer", "default": 1},
                "rel_type": {"type": "string"},
                "direction": {"type": "string", "enum": ["out", "in", "both"], "default": "out"},
            },
            "required": ["node_type", "node_id"],
        },
    ),
    Tool(
        name="traverse_pattern",
        description="Traverse following a pattern of relationship types.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string"},
                "node_id": {"type": ["string", "integer"]},
                "pattern": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rel_type": {"type": "string"},
                            "direction": {"type": "string", "enum": ["out", "in", "both"]},
                        },
                        "required": ["rel_type"],
                    },
                    "description": "List of {rel_type, direction} steps",
                },
            },
            "required": ["node_type", "node_id", "pattern"],
        },
    ),
    Tool(
        name="shortest_path",
        description="Find shortest path between two nodes.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "start_type": {"type": "string"},
                "start_id": {"type": ["string", "integer"]},
                "end_type": {"type": "string"},
                "end_id": {"type": ["string", "integer"]},
                "rel_type": {"type": "string"},
                "max_hops": {"type": "integer", "default": 10},
            },
            "required": ["start_type", "start_id", "end_type", "end_id"],
        },
    ),
    Tool(
        name="all_paths",
        description="Find all paths between two nodes.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "start_type": {"type": "string"},
                "start_id": {"type": ["string", "integer"]},
                "end_type": {"type": "string"},
                "end_id": {"type": ["string", "integer"]},
                "rel_type": {"type": "string"},
                "max_hops": {"type": "integer", "default": 5},
            },
            "required": ["start_type", "start_id", "end_type", "end_id"],
        },
    ),

    # --- ISONQL Queries ---
    Tool(
        name="query_execute",
        description="Execute an ISONQL query pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "query": {"type": "string", "description": "ISONQL query pattern (e.g., ':person:1 -[:KNOWS*2]-> *')"},
            },
            "required": ["query"],
        },
    ),

    # --- Graph Analysis ---
    Tool(
        name="analyze_connectivity",
        description="Analyze graph connectivity (is_connected, components).",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
            },
        },
    ),
    Tool(
        name="analyze_cycles",
        description="Check if graph has cycles.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "rel_type": {"type": "string"},
            },
        },
    ),
    Tool(
        name="node_degree",
        description="Get degree (in/out/total) for a node.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
                "node_type": {"type": "string"},
                "node_id": {"type": ["string", "integer"]},
            },
            "required": ["node_type", "node_id"],
        },
    ),

    # --- Serialization ---
    Tool(
        name="to_ison",
        description="Serialize graph to ISON format string.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
            },
        },
    ),
    Tool(
        name="to_dict",
        description="Serialize graph to JSON/dict format.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string"},
            },
        },
    ),
    Tool(
        name="from_dict",
        description="Load graph from JSON/dict data.",
        inputSchema={
            "type": "object",
            "properties": {
                "graph_id": {"type": "string", "description": "ID for the new graph"},
                "data": {"type": "object", "description": "Graph data with nodes and edges"},
                "set_as_default": {"type": "boolean", "default": True},
            },
            "required": ["graph_id", "data"],
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

    # --- Graph Management ---
    if name == "graph_create":
        graph_id = args["graph_id"]
        graph_name = args.get("name", graph_id)
        directed = args.get("directed", True)

        if graph_id in state.graphs:
            raise ValueError(f"Graph already exists: {graph_id}")

        graph = ISONGraph(name=graph_name, directed=directed)
        state.graphs[graph_id] = graph

        if args.get("set_as_default", True):
            state.default_graph = graph_id

        return {"graph_id": graph_id, "name": graph_name, "directed": directed}

    elif name == "graph_load":
        path = Path(args["path"])
        graph_id = args.get("graph_id", path.stem)

        graph = ISONGraph.load(path)
        state.graphs[graph_id] = graph

        if args.get("set_as_default", True):
            state.default_graph = graph_id

        return {
            "graph_id": graph_id,
            "nodes": graph.node_count(),
            "edges": graph.edge_count(),
        }

    elif name == "graph_save":
        graph = state.get_graph(args.get("graph_id"))
        path = Path(args["path"])
        fmt = args.get("format", "auto")

        state.ensure_data_dir()
        graph.save(path, format=fmt)

        return {"path": str(path), "format": fmt}

    elif name == "graph_clone":
        source = state.get_graph(args["source_id"])
        target_id = args["target_id"]

        # Clone by serializing and deserializing
        data = source.to_dict()
        cloned = ISONGraph.from_dict(data, name=target_id)
        state.graphs[target_id] = cloned

        return {"graph_id": target_id, "nodes": cloned.node_count(), "edges": cloned.edge_count()}

    elif name == "graph_merge":
        source = state.get_graph(args["source_id"])
        target = state.get_graph(args["target_id"])
        overwrite = args.get("overwrite", False)

        added_nodes = 0
        added_edges = 0

        # Merge nodes
        for node in source.nodes():
            if not target.has_node(node.type, node.id):
                target.add_node(node.type, node.id, **node.properties)
                added_nodes += 1
            elif overwrite:
                target.update_node(node.type, node.id, **node.properties)

        # Merge edges
        for edge in source.edges():
            if not target.has_edge(edge.rel_type, edge.source, edge.target):
                try:
                    target.add_edge(edge.rel_type, edge.source, edge.target, **edge.properties)
                    added_edges += 1
                except NodeNotFoundError:
                    pass  # Skip if nodes don't exist

        return {"added_nodes": added_nodes, "added_edges": added_edges}

    elif name == "graph_stats":
        graph = state.get_graph(args.get("graph_id"))

        return {
            "name": graph.name,
            "directed": graph.directed,
            "node_count": graph.node_count(),
            "edge_count": graph.edge_count(),
            "node_types": graph.node_types(),
            "edge_types": graph.edge_types(),
            "is_connected": graph.is_connected(),
        }

    elif name == "graph_delete":
        graph_id = args["graph_id"]
        if graph_id not in state.graphs:
            raise ValueError(f"Graph not found: {graph_id}")

        del state.graphs[graph_id]
        if state.default_graph == graph_id:
            state.default_graph = None

        return {"deleted": graph_id}

    elif name == "graph_list":
        return {
            "graphs": list(state.graphs.keys()),
            "default": state.default_graph,
        }

    elif name == "graph_set_default":
        graph_id = args["graph_id"]
        if graph_id not in state.graphs:
            raise ValueError(f"Graph not found: {graph_id}")
        state.default_graph = graph_id
        return {"default": graph_id}

    # --- Node Operations ---
    elif name == "node_add":
        graph = state.get_graph(args.get("graph_id"))
        props = args.get("properties", {})

        node = graph.add_node(args["node_type"], args["node_id"], **props)

        return {
            "ref": f":{node.type}:{node.id}",
            "type": node.type,
            "id": node.id,
            "properties": node.properties,
        }

    elif name == "node_get":
        graph = state.get_graph(args.get("graph_id"))
        node = graph.get_node(args["node_type"], args["node_id"])

        return {
            "ref": f":{node.type}:{node.id}",
            "type": node.type,
            "id": node.id,
            "properties": node.properties,
        }

    elif name == "node_update":
        graph = state.get_graph(args.get("graph_id"))
        node = graph.update_node(args["node_type"], args["node_id"], **args["properties"])

        return {
            "ref": f":{node.type}:{node.id}",
            "properties": node.properties,
        }

    elif name == "node_delete":
        graph = state.get_graph(args.get("graph_id"))
        ref = f":{args['node_type']}:{args['node_id']}"
        graph.remove_node(args["node_type"], args["node_id"])

        return {"deleted": ref}

    elif name == "node_find":
        graph = state.get_graph(args.get("graph_id"))
        node_type = args.get("node_type")
        where = args.get("where", {})
        limit = args.get("limit", 100)

        results = []
        for node in graph.nodes(node_type):
            # Check where conditions
            match = True
            for key, value in where.items():
                if node.properties.get(key) != value:
                    match = False
                    break

            if match:
                results.append({
                    "ref": f":{node.type}:{node.id}",
                    "type": node.type,
                    "id": node.id,
                    "properties": node.properties,
                })
                if len(results) >= limit:
                    break

        return {"nodes": results, "count": len(results)}

    elif name == "node_count":
        graph = state.get_graph(args.get("graph_id"))
        return {"count": graph.node_count(args.get("node_type"))}

    elif name == "node_types":
        graph = state.get_graph(args.get("graph_id"))
        return {"types": graph.node_types()}

    # --- Edge Operations ---
    elif name == "edge_add":
        graph = state.get_graph(args.get("graph_id"))
        source = (args["source_type"], args["source_id"])
        target = (args["target_type"], args["target_id"])
        props = args.get("properties", {})

        edge = graph.add_edge(args["rel_type"], source, target, **props)

        return {
            "rel_type": edge.rel_type,
            "source": f":{edge.source[0]}:{edge.source[1]}",
            "target": f":{edge.target[0]}:{edge.target[1]}",
            "properties": edge.properties,
        }

    elif name == "edge_get":
        graph = state.get_graph(args.get("graph_id"))
        source = (args["source_type"], args["source_id"])
        target = (args["target_type"], args["target_id"])

        edge = graph.get_edge(args["rel_type"], source, target)

        return {
            "rel_type": edge.rel_type,
            "source": f":{edge.source[0]}:{edge.source[1]}",
            "target": f":{edge.target[0]}:{edge.target[1]}",
            "properties": edge.properties,
        }

    elif name == "edge_delete":
        graph = state.get_graph(args.get("graph_id"))
        source = (args["source_type"], args["source_id"])
        target = (args["target_type"], args["target_id"])

        graph.remove_edge(args["rel_type"], source, target)

        return {"deleted": True}

    elif name == "edge_find":
        graph = state.get_graph(args.get("graph_id"))
        rel_type = args.get("rel_type")
        source = None
        target = None
        limit = args.get("limit", 100)

        if args.get("source_type") and args.get("source_id") is not None:
            source = (args["source_type"], args["source_id"])
        if args.get("target_type") and args.get("target_id") is not None:
            target = (args["target_type"], args["target_id"])

        results = []
        for edge in graph.edges(rel_type=rel_type, source=source, target=target):
            results.append({
                "rel_type": edge.rel_type,
                "source": f":{edge.source[0]}:{edge.source[1]}",
                "target": f":{edge.target[0]}:{edge.target[1]}",
                "properties": edge.properties,
            })
            if len(results) >= limit:
                break

        return {"edges": results, "count": len(results)}

    elif name == "edge_count":
        graph = state.get_graph(args.get("graph_id"))
        return {"count": graph.edge_count(args.get("rel_type"))}

    elif name == "edge_types":
        graph = state.get_graph(args.get("graph_id"))
        return {"types": graph.edge_types()}

    # --- Traversal Operations ---
    elif name == "traverse_neighbors":
        graph = state.get_graph(args.get("graph_id"))
        node_ref = (args["node_type"], args["node_id"])
        rel_type = args.get("rel_type")
        direction = Direction(args.get("direction", "out"))

        neighbors = graph.neighbors(node_ref, rel_type, direction)

        return {
            "neighbors": [f":{n[0]}:{n[1]}" for n in neighbors],
            "count": len(neighbors),
        }

    elif name == "traverse_multi_hop":
        graph = state.get_graph(args.get("graph_id"))
        start = (args["node_type"], args["node_id"])
        hops = args.get("hops", 1)
        rel_type = args.get("rel_type")
        direction = Direction(args.get("direction", "out"))

        nodes = graph.multi_hop(start, rel_type, hops, direction)

        return {
            "nodes": [f":{n[0]}:{n[1]}" for n in nodes],
            "count": len(nodes),
            "hops": hops,
        }

    elif name == "traverse_pattern":
        graph = state.get_graph(args.get("graph_id"))
        start = (args["node_type"], args["node_id"])

        pattern = []
        for step in args["pattern"]:
            direction = Direction(step.get("direction", "out"))
            pattern.append((step["rel_type"], direction))

        nodes = graph.traverse(start, pattern)

        return {
            "nodes": [f":{n[0]}:{n[1]}" for n in nodes],
            "count": len(nodes),
        }

    elif name == "shortest_path":
        graph = state.get_graph(args.get("graph_id"))
        start = (args["start_type"], args["start_id"])
        end = (args["end_type"], args["end_id"])
        rel_type = args.get("rel_type")
        max_hops = args.get("max_hops", 10)

        path = graph.shortest_path(start, end, rel_type, max_hops)

        if path is None:
            return {"path": None, "exists": False}

        return {
            "exists": True,
            "length": path.length,
            "nodes": [f":{n[0]}:{n[1]}" for n in path.nodes],
            "edges": [
                {
                    "rel_type": e.rel_type,
                    "source": f":{e.source[0]}:{e.source[1]}",
                    "target": f":{e.target[0]}:{e.target[1]}",
                }
                for e in path.edges
            ],
        }

    elif name == "all_paths":
        graph = state.get_graph(args.get("graph_id"))
        start = (args["start_type"], args["start_id"])
        end = (args["end_type"], args["end_id"])
        rel_type = args.get("rel_type")
        max_hops = args.get("max_hops", 5)

        paths = graph.all_paths(start, end, rel_type, max_hops)

        return {
            "count": len(paths),
            "paths": [
                {
                    "length": p.length,
                    "nodes": [f":{n[0]}:{n[1]}" for n in p.nodes],
                }
                for p in paths
            ],
        }

    # --- ISONQL Queries ---
    elif name == "query_execute":
        graph = state.get_graph(args.get("graph_id"))
        query = args["query"]

        nodes = graph.query(query)

        return {
            "nodes": [f":{n[0]}:{n[1]}" for n in nodes],
            "count": len(nodes),
        }

    # --- Graph Analysis ---
    elif name == "analyze_connectivity":
        graph = state.get_graph(args.get("graph_id"))
        components = graph.connected_components()

        return {
            "is_connected": len(components) <= 1,
            "component_count": len(components),
            "components": [
                [f":{n[0]}:{n[1]}" for n in comp]
                for comp in components[:10]  # Limit to first 10
            ],
        }

    elif name == "analyze_cycles":
        graph = state.get_graph(args.get("graph_id"))
        rel_type = args.get("rel_type")

        return {"has_cycles": graph.has_cycle(rel_type)}

    elif name == "node_degree":
        graph = state.get_graph(args.get("graph_id"))
        node_ref = (args["node_type"], args["node_id"])

        return {
            "in_degree": graph.in_degree(node_ref),
            "out_degree": graph.out_degree(node_ref),
            "total_degree": graph.degree(node_ref),
        }

    # --- Serialization ---
    elif name == "to_ison":
        graph = state.get_graph(args.get("graph_id"))
        return {"ison": graph.to_ison()}

    elif name == "to_dict":
        graph = state.get_graph(args.get("graph_id"))
        return graph.to_dict()

    elif name == "from_dict":
        graph_id = args["graph_id"]
        data = args["data"]

        graph = ISONGraph.from_dict(data, name=graph_id)
        state.graphs[graph_id] = graph

        if args.get("set_as_default", True):
            state.default_graph = graph_id

        return {
            "graph_id": graph_id,
            "nodes": graph.node_count(),
            "edges": graph.edge_count(),
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
