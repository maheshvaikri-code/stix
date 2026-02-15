"""
Schema MCP Server - Schema Generation & Validation
===================================================

MCP server for generating and validating ISONGraph schemas.
Supports multiple output formats.
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from schema_generator import SchemaGenerator, generate_schema, DataAnalyzer, SchemaFormatter

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("schema-mcp")


@dataclass
class ServerState:
    schemas: Dict[str, Any] = field(default_factory=dict)
    default_schema: Optional[str] = None


server = Server("schema-mcp")
state = ServerState()


TOOLS = [
    # Generation
    Tool(name="generate_from_data", description="Infer schema from data.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "data": {"type": "object"}, "strict": {"type": "boolean", "default": False}}, "required": ["schema_id", "data"]}),
    Tool(name="generate_from_samples", description="Infer schema from multiple samples.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "samples": {"type": "array", "items": {"type": "object"}}, "merge_strategy": {"type": "string", "enum": ["union", "intersection"], "default": "union"}}, "required": ["schema_id", "samples"]}),
    Tool(name="analyze_structure", description="Analyze data structure without generating schema.",
         inputSchema={"type": "object", "properties": {"data": {"type": "object"}}, "required": ["data"]}),

    # Formatting
    Tool(name="format_python", description="Output schema as Python code.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "class_name": {"type": "string"}}}),
    Tool(name="format_typescript", description="Output schema as TypeScript.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "interface_name": {"type": "string"}}}),
    Tool(name="format_json_schema", description="Output as JSON Schema.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "draft": {"type": "string", "default": "2020-12"}}}),
    Tool(name="format_ison_schema", description="Output as ISON Schema.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}}}),

    # Validation
    Tool(name="validate_node", description="Validate a node against schema.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "node_type": {"type": "string"}, "node": {"type": "object"}}, "required": ["schema_id", "node_type", "node"]}),
    Tool(name="validate_edge", description="Validate an edge against schema.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "edge_type": {"type": "string"}, "edge": {"type": "object"}}, "required": ["schema_id", "edge_type", "edge"]}),
    Tool(name="validate_graph", description="Validate entire graph against schema.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "graph": {"type": "object"}}, "required": ["schema_id", "graph"]}),
    Tool(name="get_violations", description="Get all schema violations.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}, "graph": {"type": "object"}}, "required": ["schema_id", "graph"]}),

    # Evolution
    Tool(name="diff_schemas", description="Compare two schemas.",
         inputSchema={"type": "object", "properties": {"schema_a_id": {"type": "string"}, "schema_b_id": {"type": "string"}}, "required": ["schema_a_id", "schema_b_id"]}),
    Tool(name="migrate_schema", description="Generate migration between schemas.",
         inputSchema={"type": "object", "properties": {"from_schema_id": {"type": "string"}, "to_schema_id": {"type": "string"}}, "required": ["from_schema_id", "to_schema_id"]}),
    Tool(name="check_compatibility", description="Check backwards compatibility.",
         inputSchema={"type": "object", "properties": {"old_schema_id": {"type": "string"}, "new_schema_id": {"type": "string"}}, "required": ["old_schema_id", "new_schema_id"]}),

    # Management
    Tool(name="schema_list", description="List all schemas.",
         inputSchema={"type": "object", "properties": {}}),
    Tool(name="schema_get", description="Get a schema.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}}, "required": ["schema_id"]}),
    Tool(name="schema_delete", description="Delete a schema.",
         inputSchema={"type": "object", "properties": {"schema_id": {"type": "string"}}, "required": ["schema_id"]}),
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


def get_schema(schema_id: Optional[str] = None):
    sid = schema_id or state.default_schema
    if not sid or sid not in state.schemas:
        raise ValueError(f"Schema not found: {sid}")
    return state.schemas[sid]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if name == "generate_from_data":
        schema_id = args["schema_id"]
        data = args["data"]
        strict = args.get("strict", False)

        generator = SchemaGenerator()
        schema = generator.generate(data, strict=strict)
        state.schemas[schema_id] = schema
        state.default_schema = schema_id

        return {"schema_id": schema_id, "node_types": len(schema.get("node_types", {})), "edge_types": len(schema.get("edge_types", {}))}

    elif name == "generate_from_samples":
        schema_id = args["schema_id"]
        samples = args["samples"]
        strategy = args.get("merge_strategy", "union")

        generator = SchemaGenerator()
        schema = generator.generate_from_samples(samples, merge_strategy=strategy)
        state.schemas[schema_id] = schema
        state.default_schema = schema_id

        return {"schema_id": schema_id, "samples_analyzed": len(samples)}

    elif name == "analyze_structure":
        data = args["data"]
        analyzer = DataAnalyzer()
        analysis = analyzer.analyze(data)
        return {"analysis": analysis}

    elif name == "format_python":
        schema = get_schema(args.get("schema_id"))
        class_name = args.get("class_name", "GraphSchema")
        formatter = SchemaFormatter()
        code = formatter.to_python(schema, class_name)
        return {"python": code}

    elif name == "format_typescript":
        schema = get_schema(args.get("schema_id"))
        interface_name = args.get("interface_name", "GraphSchema")
        formatter = SchemaFormatter()
        code = formatter.to_typescript(schema, interface_name)
        return {"typescript": code}

    elif name == "format_json_schema":
        schema = get_schema(args.get("schema_id"))
        draft = args.get("draft", "2020-12")
        formatter = SchemaFormatter()
        json_schema = formatter.to_json_schema(schema, draft)
        return {"json_schema": json_schema}

    elif name == "format_ison_schema":
        schema = get_schema(args.get("schema_id"))
        formatter = SchemaFormatter()
        ison_schema = formatter.to_ison_schema(schema)
        return {"ison_schema": ison_schema}

    elif name == "validate_node":
        schema = get_schema(args["schema_id"])
        node_type = args["node_type"]
        node = args["node"]

        node_schema = schema.get("node_types", {}).get(node_type, {})
        errors = []

        for field, spec in node_schema.get("properties", {}).items():
            if spec.get("required", False) and field not in node:
                errors.append(f"Missing required field: {field}")
            if field in node:
                expected_type = spec.get("type")
                actual_type = type(node[field]).__name__
                if expected_type and actual_type != expected_type:
                    errors.append(f"Type mismatch for {field}: expected {expected_type}, got {actual_type}")

        return {"valid": len(errors) == 0, "errors": errors}

    elif name == "validate_edge":
        schema = get_schema(args["schema_id"])
        edge_type = args["edge_type"]
        edge = args["edge"]

        edge_schema = schema.get("edge_types", {}).get(edge_type, {})
        errors = []

        if "source_types" in edge_schema:
            allowed = edge_schema["source_types"]
            source_type = edge.get("source", {}).get("type")
            if source_type and source_type not in allowed:
                errors.append(f"Invalid source type: {source_type}")

        if "target_types" in edge_schema:
            allowed = edge_schema["target_types"]
            target_type = edge.get("target", {}).get("type")
            if target_type and target_type not in allowed:
                errors.append(f"Invalid target type: {target_type}")

        return {"valid": len(errors) == 0, "errors": errors}

    elif name == "validate_graph":
        schema = get_schema(args["schema_id"])
        graph = args["graph"]

        errors = []
        for node in graph.get("nodes", []):
            node_type = node.get("type")
            if node_type not in schema.get("node_types", {}):
                errors.append(f"Unknown node type: {node_type}")

        for edge in graph.get("edges", []):
            edge_type = edge.get("rel_type", edge.get("type"))
            if edge_type not in schema.get("edge_types", {}):
                errors.append(f"Unknown edge type: {edge_type}")

        return {"valid": len(errors) == 0, "errors": errors, "error_count": len(errors)}

    elif name == "get_violations":
        schema = get_schema(args["schema_id"])
        graph = args["graph"]

        violations = []
        # Check nodes
        for i, node in enumerate(graph.get("nodes", [])):
            node_type = node.get("type")
            node_schema = schema.get("node_types", {}).get(node_type, {})
            for field, spec in node_schema.get("properties", {}).items():
                if spec.get("required", False) and field not in node:
                    violations.append({"type": "missing_field", "node_index": i, "field": field})

        return {"violations": violations, "count": len(violations)}

    elif name == "diff_schemas":
        schema_a = get_schema(args["schema_a_id"])
        schema_b = get_schema(args["schema_b_id"])

        diff = {
            "added_node_types": [],
            "removed_node_types": [],
            "added_edge_types": [],
            "removed_edge_types": [],
            "modified_types": []
        }

        a_nodes = set(schema_a.get("node_types", {}).keys())
        b_nodes = set(schema_b.get("node_types", {}).keys())
        diff["added_node_types"] = list(b_nodes - a_nodes)
        diff["removed_node_types"] = list(a_nodes - b_nodes)

        a_edges = set(schema_a.get("edge_types", {}).keys())
        b_edges = set(schema_b.get("edge_types", {}).keys())
        diff["added_edge_types"] = list(b_edges - a_edges)
        diff["removed_edge_types"] = list(a_edges - b_edges)

        return {"diff": diff}

    elif name == "migrate_schema":
        from_schema = get_schema(args["from_schema_id"])
        to_schema = get_schema(args["to_schema_id"])

        migrations = []
        # Generate migration steps
        for node_type in set(to_schema.get("node_types", {}).keys()) - set(from_schema.get("node_types", {}).keys()):
            migrations.append({"action": "add_node_type", "type": node_type})
        for node_type in set(from_schema.get("node_types", {}).keys()) - set(to_schema.get("node_types", {}).keys()):
            migrations.append({"action": "remove_node_type", "type": node_type})

        return {"migrations": migrations, "step_count": len(migrations)}

    elif name == "check_compatibility":
        old_schema = get_schema(args["old_schema_id"])
        new_schema = get_schema(args["new_schema_id"])

        breaking_changes = []

        # Removed types are breaking
        for node_type in set(old_schema.get("node_types", {}).keys()) - set(new_schema.get("node_types", {}).keys()):
            breaking_changes.append(f"Removed node type: {node_type}")
        for edge_type in set(old_schema.get("edge_types", {}).keys()) - set(new_schema.get("edge_types", {}).keys()):
            breaking_changes.append(f"Removed edge type: {edge_type}")

        return {"compatible": len(breaking_changes) == 0, "breaking_changes": breaking_changes}

    elif name == "schema_list":
        return {"schemas": list(state.schemas.keys()), "default": state.default_schema}

    elif name == "schema_get":
        schema = get_schema(args["schema_id"])
        return {"schema_id": args["schema_id"], "schema": schema}

    elif name == "schema_delete":
        schema_id = args["schema_id"]
        if schema_id in state.schemas:
            del state.schemas[schema_id]
            if state.default_schema == schema_id:
                state.default_schema = None
        return {"deleted": schema_id}

    else:
        raise ValueError(f"Unknown tool: {name}")


async def run_server():
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main():
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
