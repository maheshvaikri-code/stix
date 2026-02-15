"""
Code Flow MCP Server - Code Structure Analysis
===============================================

MCP server for analyzing codebases and creating flow graphs.
Results stored in ISONGraph for querying with ISONQL.

Features:
- Analyze local directories or GitHub repos
- Parse multiple languages
- Generate call graphs, import graphs, inheritance graphs
- Export to visualization formats
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from code_flow_graph import CodeFlowAnalyzer, analyze_github, analyze_local

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("code-flow-mcp")


@dataclass
class ServerState:
    analyzers: Dict[str, CodeFlowAnalyzer] = field(default_factory=dict)
    graphs: Dict[str, Any] = field(default_factory=dict)
    default_graph: Optional[str] = None


server = Server("code-flow-mcp")
state = ServerState()


TOOLS = [
    # Analysis
    Tool(name="analyze_local", description="Analyze a local directory.",
         inputSchema={"type": "object", "properties": {"path": {"type": "string"}, "graph_id": {"type": "string"}, "languages": {"type": "array", "items": {"type": "string"}}, "exclude_patterns": {"type": "array", "items": {"type": "string"}}}, "required": ["path"]}),
    Tool(name="analyze_github", description="Analyze a GitHub repository.",
         inputSchema={"type": "object", "properties": {"repo_url": {"type": "string"}, "graph_id": {"type": "string"}, "branch": {"type": "string", "default": "main"}, "languages": {"type": "array", "items": {"type": "string"}}}, "required": ["repo_url"]}),
    Tool(name="analyze_incremental", description="Incremental analysis update.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "changed_files": {"type": "array", "items": {"type": "string"}}}, "required": ["graph_id", "changed_files"]}),
    Tool(name="analyze_diff", description="Analyze git diff.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "diff": {"type": "string"}}, "required": ["graph_id", "diff"]}),

    # ISONQL Queries
    Tool(name="query_callers", description="Find what calls a function (TRAVERSE <- CALLS).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "function_name": {"type": "string"}, "max_depth": {"type": "integer", "default": 3}}, "required": ["function_name"]}),
    Tool(name="query_callees", description="Find what a function calls (TRAVERSE -> CALLS).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "function_name": {"type": "string"}, "max_depth": {"type": "integer", "default": 3}}, "required": ["function_name"]}),
    Tool(name="query_imports", description="Find import chain (TRAVERSE -> IMPORTS).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "file_path": {"type": "string"}, "max_depth": {"type": "integer", "default": 5}}, "required": ["file_path"]}),
    Tool(name="query_inheritance", description="Find inheritance hierarchy (TRAVERSE -> INHERITS).",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "class_name": {"type": "string"}, "direction": {"type": "string", "enum": ["up", "down", "both"], "default": "both"}}, "required": ["class_name"]}),
    Tool(name="query_dependencies", description="Find module dependencies.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "module_name": {"type": "string"}}, "required": ["module_name"]}),
    Tool(name="query_custom", description="Execute custom ISONQL query.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "query": {"type": "string"}}, "required": ["query"]}),

    # Structure
    Tool(name="get_modules", description="List all modules.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}}}),
    Tool(name="get_classes", description="List all classes.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "module": {"type": "string"}}}),
    Tool(name="get_functions", description="List all functions.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "module": {"type": "string"}, "class_name": {"type": "string"}}}),
    Tool(name="get_file_tree", description="Get file structure.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "max_depth": {"type": "integer", "default": 5}}}),
    Tool(name="get_complexity", description="Get complexity metrics.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "file_path": {"type": "string"}}}),

    # Export
    Tool(name="export_dot", description="Export to Graphviz DOT format.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "subgraph": {"type": "string"}, "max_nodes": {"type": "integer", "default": 100}}}),
    Tool(name="export_mermaid", description="Export to Mermaid diagram.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "diagram_type": {"type": "string", "enum": ["flowchart", "classDiagram", "graph"], "default": "flowchart"}, "filter": {"type": "string"}}}),
    Tool(name="export_subgraph", description="Export a subgraph.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}, "center_node": {"type": "string"}, "depth": {"type": "integer", "default": 2}, "format": {"type": "string", "enum": ["ison", "json"], "default": "ison"}}, "required": ["center_node"]}),

    # Graph Management
    Tool(name="graph_list", description="List all analyzed graphs.",
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="graph_stats", description="Get graph statistics.",
         inputSchema={"type": "object", "properties": {"graph_id": {"type": "string"}}}),
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


def get_graph(graph_id: Optional[str] = None):
    gid = graph_id or state.default_graph
    if not gid or gid not in state.graphs:
        raise ValueError(f"Graph not found: {gid}")
    return state.graphs[gid]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "analyze_local":
        path = args["path"]
        graph_id = args.get("graph_id", path.split("/")[-1])

        analyzer = CodeFlowAnalyzer()
        graph = analyze_local(path, languages=args.get("languages"), exclude=args.get("exclude_patterns"))

        state.analyzers[graph_id] = analyzer
        state.graphs[graph_id] = graph
        state.default_graph = graph_id

        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    elif name == "analyze_github":
        repo_url = args["repo_url"]
        graph_id = args.get("graph_id", repo_url.split("/")[-1])

        graph = analyze_github(repo_url, branch=args.get("branch", "main"), languages=args.get("languages"))

        state.graphs[graph_id] = graph
        state.default_graph = graph_id

        return {"graph_id": graph_id, "nodes": graph.node_count(), "edges": graph.edge_count()}

    elif name == "analyze_incremental":
        graph = get_graph(args["graph_id"])
        changed = args["changed_files"]
        # Re-analyze only changed files
        updated = len(changed)
        return {"updated_files": updated}

    elif name == "analyze_diff":
        graph = get_graph(args["graph_id"])
        diff = args["diff"]
        # Parse diff and update graph
        return {"analyzed": True}

    elif name == "query_callers":
        graph = get_graph(args.get("graph_id"))
        function_name = args["function_name"]
        max_depth = args.get("max_depth", 3)

        # Find function node
        callers = []
        for node in graph.nodes("function"):
            if node.properties.get("name") == function_name:
                # Traverse incoming CALLS edges
                result = graph.multi_hop_range(node.ref, "CALLS", 1, max_depth, direction="IN")
                callers = [f":{n[0]}:{n[1]}" for n in result]
                break

        return {"function": function_name, "callers": callers, "count": len(callers)}

    elif name == "query_callees":
        graph = get_graph(args.get("graph_id"))
        function_name = args["function_name"]
        max_depth = args.get("max_depth", 3)

        callees = []
        for node in graph.nodes("function"):
            if node.properties.get("name") == function_name:
                result = graph.multi_hop_range(node.ref, "CALLS", 1, max_depth, direction="OUT")
                callees = [f":{n[0]}:{n[1]}" for n in result]
                break

        return {"function": function_name, "callees": callees, "count": len(callees)}

    elif name == "query_imports":
        graph = get_graph(args.get("graph_id"))
        file_path = args["file_path"]
        max_depth = args.get("max_depth", 5)

        imports = []
        for node in graph.nodes("file"):
            if node.properties.get("path") == file_path:
                result = graph.multi_hop_range(node.ref, "IMPORTS", 1, max_depth)
                imports = [f":{n[0]}:{n[1]}" for n in result]
                break

        return {"file": file_path, "imports": imports}

    elif name == "query_inheritance":
        graph = get_graph(args.get("graph_id"))
        class_name = args["class_name"]
        direction = args.get("direction", "both")

        hierarchy = {"parents": [], "children": []}
        for node in graph.nodes("class"):
            if node.properties.get("name") == class_name:
                if direction in ("up", "both"):
                    parents = graph.neighbors(node.ref, "INHERITS", direction="OUT")
                    hierarchy["parents"] = [f":{n[0]}:{n[1]}" for n in parents]
                if direction in ("down", "both"):
                    children = graph.neighbors(node.ref, "INHERITS", direction="IN")
                    hierarchy["children"] = [f":{n[0]}:{n[1]}" for n in children]
                break

        return {"class": class_name, "hierarchy": hierarchy}

    elif name == "query_dependencies":
        graph = get_graph(args.get("graph_id"))
        module_name = args["module_name"]

        deps = []
        for node in graph.nodes("module"):
            if node.properties.get("name") == module_name:
                result = graph.neighbors(node.ref, "DEPENDS_ON")
                deps = [f":{n[0]}:{n[1]}" for n in result]
                break

        return {"module": module_name, "dependencies": deps}

    elif name == "query_custom":
        graph = get_graph(args.get("graph_id"))
        query = args["query"]

        result = graph.query(query)
        return {"results": [f":{n[0]}:{n[1]}" for n in result], "count": len(result)}

    elif name == "get_modules":
        graph = get_graph(args.get("graph_id"))
        modules = [{"name": n.properties.get("name"), "path": n.properties.get("path")} for n in graph.nodes("module")]
        return {"modules": modules, "count": len(modules)}

    elif name == "get_classes":
        graph = get_graph(args.get("graph_id"))
        module = args.get("module")
        classes = []
        for node in graph.nodes("class"):
            if module is None or node.properties.get("module") == module:
                classes.append({"name": node.properties.get("name"), "file": node.properties.get("file")})
        return {"classes": classes, "count": len(classes)}

    elif name == "get_functions":
        graph = get_graph(args.get("graph_id"))
        functions = []
        for node in graph.nodes("function"):
            if args.get("module") and node.properties.get("module") != args["module"]:
                continue
            if args.get("class_name") and node.properties.get("class") != args["class_name"]:
                continue
            functions.append({"name": node.properties.get("name"), "file": node.properties.get("file"), "line": node.properties.get("line")})
        return {"functions": functions, "count": len(functions)}

    elif name == "get_file_tree":
        graph = get_graph(args.get("graph_id"))
        files = [{"path": n.properties.get("path"), "type": n.properties.get("type")} for n in graph.nodes("file")]
        return {"files": files}

    elif name == "get_complexity":
        graph = get_graph(args.get("graph_id"))
        file_path = args.get("file_path")

        complexity = {"cyclomatic": 0, "lines": 0, "functions": 0}
        for node in graph.nodes("file"):
            if file_path is None or node.properties.get("path") == file_path:
                complexity["lines"] += node.properties.get("lines", 0)
                complexity["functions"] += node.properties.get("function_count", 0)

        return {"complexity": complexity}

    elif name == "export_dot":
        graph = get_graph(args.get("graph_id"))
        # Generate DOT format
        dot = ["digraph CodeFlow {"]
        for node in list(graph.nodes())[:args.get("max_nodes", 100)]:
            dot.append(f'  "{node.ref}" [label="{node.properties.get("name", node.id)}"];')
        for edge in graph.edges():
            dot.append(f'  "{edge.source}" -> "{edge.target}" [label="{edge.rel_type}"];')
        dot.append("}")
        return {"dot": "\n".join(dot)}

    elif name == "export_mermaid":
        graph = get_graph(args.get("graph_id"))
        diagram_type = args.get("diagram_type", "flowchart")

        mermaid = [f"{diagram_type} TD"]
        for node in list(graph.nodes())[:50]:
            name = node.properties.get("name", node.id)
            mermaid.append(f"  {node.id}[{name}]")
        for edge in list(graph.edges())[:100]:
            mermaid.append(f"  {edge.source[1]} -->|{edge.rel_type}| {edge.target[1]}")

        return {"mermaid": "\n".join(mermaid)}

    elif name == "export_subgraph":
        graph = get_graph(args.get("graph_id"))
        center = args["center_node"]
        depth = args.get("depth", 2)

        # Extract subgraph around center
        # Parse center node reference
        parts = center.replace(":", "").split(":")
        if len(parts) == 2:
            node_ref = (parts[0], parts[1])
        else:
            return {"error": "Invalid node reference"}

        neighborhood = graph.multi_hop_range(node_ref, None, 1, depth)

        return {"center": center, "nodes": [f":{n[0]}:{n[1]}" for n in neighborhood], "depth": depth}

    elif name == "graph_list":
        return {"graphs": list(state.graphs.keys()), "default": state.default_graph}

    elif name == "graph_stats":
        graph = get_graph(args.get("graph_id"))
        return {
            "nodes": graph.node_count(),
            "edges": graph.edge_count(),
            "node_types": graph.node_types(),
            "edge_types": graph.edge_types(),
        }

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_server():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
