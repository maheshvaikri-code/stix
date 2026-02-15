"""
Converter MCP Server - Format Transformation
=============================================

MCP server for converting ISONGraph to/from various formats.
Supports GraphML, RDF, CSV, Cypher, DOT, JSON.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from ison_graph import ISONGraph
from converters import GraphMLConverter, RDFConverter, CSVConverter, CypherConverter, DOTConverter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("converter-mcp")


@dataclass
class ServerState:
    graphs: Dict[str, ISONGraph] = field(default_factory=dict)
    default_graph: Optional[str] = None


server = Server("converter-mcp")
state = ServerState()


TOOLS = [
    # Graph Management
    Tool(name="graph_load", description="Load a graph for conversion.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "data": {"type": "object"}, "format": {"type": "string", "enum": ["ison", "json"]}}, "required": ["graph_id", "data"]}),
    Tool(name="graph_load_file", description="Load graph from file.",
         inputSchema={"type": "object", "properties": {"path": {"type": "string"}, "graph_id": {"type": "string"}}, "required": ["path"]}),

    # Export To
    Tool(name="to_graphml", description="Export to GraphML (Gephi, yEd).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "include_properties": {"type": "boolean", "default": True}}}),
    Tool(name="to_rdf_turtle", description="Export to RDF/Turtle.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "base_uri": {"type": "string", "default": "http://example.org/"}}}),
    Tool(name="to_rdf_ntriples", description="Export to N-Triples.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}}}),
    Tool(name="to_csv", description="Export to CSV (nodes.csv, edges.csv).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}}}),
    Tool(name="to_cypher", description="Export to Neo4j Cypher statements (for migration).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "batch_size": {"type": "integer", "default": 100}}}),
    Tool(name="to_dot", description="Export to Graphviz DOT.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "layout": {"type": "string", "default": "dot"}, "max_nodes": {"type": "integer", "default": 500}}}),
    Tool(name="to_json", description="Export to standard JSON.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "pretty": {"type": "boolean", "default": True}}}),
    Tool(name="to_ison", description="Export to ISON format.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}}}),

    # Import From
    Tool(name="from_graphml", description="Import from GraphML.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "content": {"type": "string"}}, "required": ["graph_id", "content"]}),
    Tool(name="from_rdf", description="Import from RDF/Turtle.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "content": {"type": "string"}, "format": {"type": "string", "enum": ["turtle", "n3", "ntriples"]}}, "required": ["graph_id", "content"]}),
    Tool(name="from_csv", description="Import from CSV.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "nodes_csv": {"type": "string"}, "edges_csv": {"type": "string"}}, "required": ["graph_id", "nodes_csv"]}),
    Tool(name="from_json", description="Import from JSON.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "content": {"type": "string"}}, "required": ["graph_id", "content"]}),
    Tool(name="from_cypher", description="Import from Cypher dump (Neo4j migration).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "content": {"type": "string"}}, "required": ["graph_id", "content"]}),

    # Render
    Tool(name="render_svg", description="Render graph to SVG.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "layout": {"type": "string", "default": "dot"}, "max_nodes": {"type": "integer", "default": 200}}}),
    Tool(name="render_png", description="Render graph to PNG (requires Graphviz).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "output_path": {"type": "string"}, "dpi": {"type": "integer", "default": 150}}}),
]


@server.list_tools()
async def list_tools() -> List[Tool]:
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    try:
        result = await handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


def get_graph(graph_id: Optional[str] = None) -> ISONGraph:
    gid = graph_id or state.default_graph
    if not gid or gid not in state.graphs:
        raise ValueError(f"Graph not found: {gid}")
    return state.graphs[gid]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "graph_load":
        graph_id = args["graph_id"]
        data = args["data"]
        graph = ISONGraph.from_dict(data, name=graph_id)
        state.graphs[graph_id] = graph
        state.default_graph = graph_id
        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    elif name == "graph_load_file":
        from pathlib import Path
        path = Path(args["path"])
        graph_id = args.get("graph_id", path.stem)
        graph = ISONGraph.load(path)
        state.graphs[graph_id] = graph
        state.default_graph = graph_id
        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    # Export handlers
    elif name == "to_graphml":
        graph = get_graph(args.get("graph_id"))
        converter = GraphMLConverter()
        result = converter.export(graph, include_properties=args.get("include_properties", True))
        return {"graphml": result}

    elif name == "to_rdf_turtle":
        graph = get_graph(args.get("graph_id"))
        converter = RDFConverter()
        result = converter.to_turtle(graph, base_uri=args.get("base_uri", "http://example.org/"))
        return {"turtle": result}

    elif name == "to_rdf_ntriples":
        graph = get_graph(args.get("graph_id"))
        converter = RDFConverter()
        result = converter.to_ntriples(graph)
        return {"ntriples": result}

    elif name == "to_csv":
        graph = get_graph(args.get("graph_id"))
        converter = CSVConverter()
        nodes_csv, edges_csv = converter.export(graph)
        return {"nodes_csv": nodes_csv, "edges_csv": edges_csv}

    elif name == "to_cypher":
        graph = get_graph(args.get("graph_id"))
        converter = CypherConverter()
        statements = converter.export(graph, batch_size=args.get("batch_size", 100))
        return {"cypher": statements, "statement_count": len(statements.split(";"))}

    elif name == "to_dot":
        graph = get_graph(args.get("graph_id"))
        converter = DOTConverter()
        result = converter.export(graph, layout=args.get("layout", "dot"), max_nodes=args.get("max_nodes", 500))
        return {"dot": result}

    elif name == "to_json":
        graph = get_graph(args.get("graph_id"))
        data = graph.to_dict()
        if args.get("pretty", True):
            return {"json": json.dumps(data, indent=2)}
        return {"json": json.dumps(data)}

    elif name == "to_ison":
        graph = get_graph(args.get("graph_id"))
        return {"ison": graph.to_ison()}

    # Import handlers
    elif name == "from_graphml":
        graph_id = args["graph_id"]
        converter = GraphMLConverter()
        graph = converter.import_graph(args["content"])
        graph.name = graph_id
        state.graphs[graph_id] = graph
        state.default_graph = graph_id
        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    elif name == "from_rdf":
        graph_id = args["graph_id"]
        converter = RDFConverter()
        graph = converter.from_rdf(args["content"], format=args.get("format", "turtle"))
        graph.name = graph_id
        state.graphs[graph_id] = graph
        state.default_graph = graph_id
        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    elif name == "from_csv":
        graph_id = args["graph_id"]
        converter = CSVConverter()
        graph = converter.import_graph(args["nodes_csv"], args.get("edges_csv"))
        graph.name = graph_id
        state.graphs[graph_id] = graph
        state.default_graph = graph_id
        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    elif name == "from_json":
        graph_id = args["graph_id"]
        data = json.loads(args["content"])
        graph = ISONGraph.from_dict(data, name=graph_id)
        state.graphs[graph_id] = graph
        state.default_graph = graph_id
        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    elif name == "from_cypher":
        graph_id = args["graph_id"]
        converter = CypherConverter()
        graph = converter.import_graph(args["content"])
        graph.name = graph_id
        state.graphs[graph_id] = graph
        state.default_graph = graph_id
        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    # Render handlers
    elif name == "render_svg":
        graph = get_graph(args.get("graph_id"))
        converter = DOTConverter()
        dot = converter.export(graph, max_nodes=args.get("max_nodes", 200))
        # Would need graphviz library to render
        return {"dot": dot, "note": "Use Graphviz to render DOT to SVG"}

    elif name == "render_png":
        graph = get_graph(args.get("graph_id"))
        output_path = args.get("output_path", "graph.png")
        return {"note": f"Render to {output_path} requires Graphviz installation"}

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_server():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
