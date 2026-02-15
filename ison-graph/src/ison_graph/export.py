#!/usr/bin/env python3
"""
ISONGraph Export Module

Provides universal export to multiple formats:
- Database: Neo4j Cypher, SQL
- Graph: GraphML, GEXF, RDF, DOT
- Data: JSON, YAML, TOML, XML, CSV
- Visualization: D3, vis.js, Mermaid
- Analysis: Adjacency list/matrix, Edge list

Usage:
    from ison_graph import ISONGraph
    from ison_graph.export import (
        export_to_cypher,
        export_to_json,
        export_to_yaml,
        export_to_mermaid
    )

    graph = ISONGraph()
    # ... add nodes and edges ...

    # Export to various formats
    cypher = export_to_cypher(graph)
    json_str = export_to_json(graph)
    mermaid = export_to_mermaid(graph)
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime

from . import ISONGraph, Node, Edge, NodeRef


# =============================================================================
# Export Options
# =============================================================================

@dataclass
class ExportOptions:
    """Common export options"""
    include_properties: bool = True
    include_metadata: bool = True
    pretty_print: bool = True


# =============================================================================
# Helper Functions
# =============================================================================

def _escape_string(s: str) -> str:
    """Escape special characters in strings"""
    return (s
            .replace('\\', '\\\\')
            .replace("'", "\\'")
            .replace('"', '\\"')
            .replace('\n', '\\n')
            .replace('\r', '\\r')
            .replace('\t', '\\t'))


def _escape_xml(s: str) -> str:
    """Escape XML special characters"""
    return (s
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;')
            .replace("'", '&apos;'))


def _sanitize_id(s: str) -> str:
    """Sanitize an ID for use in various formats"""
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(s))


def _capitalize_first(s: str) -> str:
    """Capitalize first letter"""
    return s[0].upper() + s[1:] if s else s


def _cypher_value(value: Any) -> str:
    """Convert value to Cypher literal"""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, str):
        return f"'{_escape_string(value)}'"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return f"[{', '.join(_cypher_value(v) for v in value)}]"
    return f"'{_escape_string(json.dumps(value))}'"


def _yaml_value(value: Any) -> str:
    """Convert value to YAML literal"""
    if value is None:
        return 'null'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        if re.match(r'^[\w-]+$', value) and value.lower() not in ('true', 'false', 'null', 'yes', 'no'):
            return value
        return f'"{value.replace(chr(34), chr(92)+chr(34))}"'
    return json.dumps(value)


def _toml_value(value: Any) -> str:
    """Convert value to TOML literal"""
    if value is None:
        return '""'
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return f'"{_escape_string(value)}"'
    return f'"{_escape_string(json.dumps(value))}"'


# =============================================================================
# Database Exports
# =============================================================================

def export_to_cypher(
    graph: ISONGraph,
    options: Optional[ExportOptions] = None
) -> str:
    """
    Export to Neo4j Cypher CREATE statements.

    Args:
        graph: Graph to export
        options: Export options

    Returns:
        Cypher CREATE statements
    """
    options = options or ExportOptions()
    lines = []

    if options.include_metadata:
        lines.append('// ISONGraph Export')
        lines.append(f'// Graph: {graph.name}')
        lines.append(f'// Nodes: {graph.node_count()}, Edges: {graph.edge_count()}')
        lines.append('')

    # Export nodes
    for node in graph.nodes():
        label = _capitalize_first(node.type)
        var_name = f"n_{_sanitize_id(node.type)}_{_sanitize_id(str(node.id))}"

        if options.include_properties and node.properties:
            props = ', '.join(
                f"{k}: {_cypher_value(v)}"
                for k, v in node.properties.items()
            )
            lines.append(f"CREATE ({var_name}:{label} {{{props}}})")
        else:
            lines.append(f"CREATE ({var_name}:{label})")

    if lines and graph.edge_count() > 0:
        lines.append('')

    # Export edges
    for edge in graph.edges():
        src_var = f"n_{_sanitize_id(edge.source[0])}_{_sanitize_id(str(edge.source[1]))}"
        tgt_var = f"n_{_sanitize_id(edge.target[0])}_{_sanitize_id(str(edge.target[1]))}"

        if options.include_properties and edge.properties:
            props = ', '.join(
                f"{k}: {_cypher_value(v)}"
                for k, v in edge.properties.items()
            )
            lines.append(f"CREATE ({src_var})-[:{edge.rel_type} {{{props}}}]->({tgt_var})")
        else:
            lines.append(f"CREATE ({src_var})-[:{edge.rel_type}]->({tgt_var})")

    return '\n'.join(lines)


def export_to_cypher_merge(
    graph: ISONGraph,
    options: Optional[ExportOptions] = None
) -> str:
    """Export to Neo4j Cypher MERGE statements (idempotent)"""
    options = options or ExportOptions()
    lines = []

    if options.include_metadata:
        lines.append('// ISONGraph Export (MERGE)')
        lines.append(f'// Graph: {graph.name}')
        lines.append('')

    # Export nodes with MERGE
    for node in graph.nodes():
        label = _capitalize_first(node.type)

        props = ', '.join(
            f"n.{k} = {_cypher_value(v)}"
            for k, v in node.properties.items()
        ) if options.include_properties and node.properties else ''

        lines.append(f"MERGE (n:{label} {{id: {_cypher_value(node.id)}}})")
        if props:
            lines.append(f"ON CREATE SET {props}")
            lines.append(f"ON MATCH SET {props}")

    if lines:
        lines.append('')

    # Export edges with MERGE
    for edge in graph.edges():
        src_label = _capitalize_first(edge.source[0])
        tgt_label = _capitalize_first(edge.target[0])

        lines.append(f"MATCH (a:{src_label} {{id: {_cypher_value(edge.source[1])}}})")
        lines.append(f"MATCH (b:{tgt_label} {{id: {_cypher_value(edge.target[1])}}})")
        lines.append(f"MERGE (a)-[r:{edge.rel_type}]->(b)")

    return '\n'.join(lines)


def export_to_sql(
    graph: ISONGraph,
    dialect: str = 'postgres',
    table_prefix: str = '',
    include_drops: bool = False
) -> str:
    """
    Export to SQL CREATE/INSERT statements.

    Args:
        graph: Graph to export
        dialect: SQL dialect ('postgres', 'mysql', 'sqlite')
        table_prefix: Prefix for table names
        include_drops: Include DROP TABLE statements

    Returns:
        SQL statements
    """
    lines = []
    nodes_table = f"{table_prefix}nodes"
    edges_table = f"{table_prefix}edges"
    quote = '`' if dialect == 'mysql' else '"'

    lines.append('-- ISONGraph SQL Export')
    lines.append(f'-- Generated: {datetime.now().isoformat()}')
    lines.append('')

    if include_drops:
        lines.append(f'DROP TABLE IF EXISTS {quote}{edges_table}{quote};')
        lines.append(f'DROP TABLE IF EXISTS {quote}{nodes_table}{quote};')
        lines.append('')

    # Create nodes table
    json_type = 'JSONB' if dialect == 'postgres' else 'JSON' if dialect == 'mysql' else 'TEXT'
    serial_type = 'SERIAL' if dialect == 'postgres' else 'INTEGER'
    auto_inc = ' AUTOINCREMENT' if dialect == 'sqlite' else ''

    lines.append(f'CREATE TABLE {quote}{nodes_table}{quote} (')
    lines.append(f'  {quote}node_type{quote} VARCHAR(255) NOT NULL,')
    lines.append(f'  {quote}node_id{quote} VARCHAR(255) NOT NULL,')
    lines.append(f'  {quote}properties{quote} {json_type},')
    lines.append(f'  PRIMARY KEY ({quote}node_type{quote}, {quote}node_id{quote})')
    lines.append(');')
    lines.append('')

    # Create edges table
    lines.append(f'CREATE TABLE {quote}{edges_table}{quote} (')
    lines.append(f'  {quote}id{quote} {serial_type} PRIMARY KEY{auto_inc},')
    lines.append(f'  {quote}rel_type{quote} VARCHAR(255) NOT NULL,')
    lines.append(f'  {quote}source_type{quote} VARCHAR(255) NOT NULL,')
    lines.append(f'  {quote}source_id{quote} VARCHAR(255) NOT NULL,')
    lines.append(f'  {quote}target_type{quote} VARCHAR(255) NOT NULL,')
    lines.append(f'  {quote}target_id{quote} VARCHAR(255) NOT NULL,')
    lines.append(f'  {quote}properties{quote} {json_type}')
    lines.append(');')
    lines.append('')

    # Insert nodes
    if graph.node_count() > 0:
        lines.append(f'-- Nodes ({graph.node_count()})')
        for node in graph.nodes():
            props_json = json.dumps(node.properties).replace("'", "''")
            lines.append(
                f"INSERT INTO {quote}{nodes_table}{quote} "
                f"({quote}node_type{quote}, {quote}node_id{quote}, {quote}properties{quote}) "
                f"VALUES ('{node.type}', '{node.id}', '{props_json}');"
            )
        lines.append('')

    # Insert edges
    if graph.edge_count() > 0:
        lines.append(f'-- Edges ({graph.edge_count()})')
        for edge in graph.edges():
            props_json = json.dumps(edge.properties).replace("'", "''")
            lines.append(
                f"INSERT INTO {quote}{edges_table}{quote} "
                f"({quote}rel_type{quote}, {quote}source_type{quote}, {quote}source_id{quote}, "
                f"{quote}target_type{quote}, {quote}target_id{quote}, {quote}properties{quote}) "
                f"VALUES ('{edge.rel_type}', '{edge.source[0]}', '{edge.source[1]}', "
                f"'{edge.target[0]}', '{edge.target[1]}', '{props_json}');"
            )

    return '\n'.join(lines)


# =============================================================================
# Graph Format Exports
# =============================================================================

def export_to_graphml(
    graph: ISONGraph,
    options: Optional[ExportOptions] = None
) -> str:
    """Export to GraphML (XML) format"""
    options = options or ExportOptions()
    indent = '  ' if options.pretty_print else ''
    nl = '\n' if options.pretty_print else ''

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<graphml xmlns="http://graphml.graphdrawing.org/xmlns">')

    # Collect property keys
    node_props = set()
    edge_props = set()

    for node in graph.nodes():
        node_props.update(node.properties.keys())
    for edge in graph.edges():
        edge_props.update(edge.properties.keys())

    # Define keys
    lines.append(f'{indent}<key id="n_type" for="node" attr.name="type" attr.type="string"/>')
    for prop in sorted(node_props):
        lines.append(f'{indent}<key id="n_{prop}" for="node" attr.name="{prop}" attr.type="string"/>')

    lines.append(f'{indent}<key id="e_type" for="edge" attr.name="type" attr.type="string"/>')
    for prop in sorted(edge_props):
        lines.append(f'{indent}<key id="e_{prop}" for="edge" attr.name="{prop}" attr.type="string"/>')

    # Graph element
    edge_default = 'directed' if graph.directed else 'undirected'
    lines.append(f'{indent}<graph id="{_escape_xml(graph.name)}" edgedefault="{edge_default}">')

    # Nodes
    for node in graph.nodes():
        node_id = f"{node.type}:{node.id}"
        lines.append(f'{indent}{indent}<node id="{_escape_xml(node_id)}">')
        lines.append(f'{indent}{indent}{indent}<data key="n_type">{_escape_xml(node.type)}</data>')
        if options.include_properties:
            for key, value in node.properties.items():
                lines.append(f'{indent}{indent}{indent}<data key="n_{key}">{_escape_xml(str(value))}</data>')
        lines.append(f'{indent}{indent}</node>')

    # Edges
    edge_id = 0
    for edge in graph.edges():
        source_id = f"{edge.source[0]}:{edge.source[1]}"
        target_id = f"{edge.target[0]}:{edge.target[1]}"
        lines.append(f'{indent}{indent}<edge id="e{edge_id}" source="{_escape_xml(source_id)}" target="{_escape_xml(target_id)}">')
        lines.append(f'{indent}{indent}{indent}<data key="e_type">{_escape_xml(edge.rel_type)}</data>')
        if options.include_properties:
            for key, value in edge.properties.items():
                lines.append(f'{indent}{indent}{indent}<data key="e_{key}">{_escape_xml(str(value))}</data>')
        lines.append(f'{indent}{indent}</edge>')
        edge_id += 1

    lines.append(f'{indent}</graph>')
    lines.append('</graphml>')

    return nl.join(lines)


def export_to_gexf(
    graph: ISONGraph,
    options: Optional[ExportOptions] = None
) -> str:
    """Export to GEXF format (Gephi compatible)"""
    options = options or ExportOptions()
    indent = '  ' if options.pretty_print else ''
    nl = '\n' if options.pretty_print else ''

    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<gexf xmlns="http://www.gexf.net/1.3" version="1.3">')
    lines.append(f'{indent}<meta lastmodifieddate="{datetime.now().strftime("%Y-%m-%d")}">')
    lines.append(f'{indent}{indent}<creator>ISONGraph</creator>')
    lines.append(f'{indent}{indent}<description>{_escape_xml(graph.name)}</description>')
    lines.append(f'{indent}</meta>')

    mode = 'directed' if graph.directed else 'undirected'
    lines.append(f'{indent}<graph mode="static" defaultedgetype="{mode}">')

    # Nodes
    lines.append(f'{indent}{indent}<nodes>')
    for node in graph.nodes():
        node_id = f"{node.type}:{node.id}"
        label = str(node.properties.get('name', node.properties.get('title', node.id)))
        lines.append(f'{indent}{indent}{indent}<node id="{_escape_xml(node_id)}" label="{_escape_xml(label)}"/>')
    lines.append(f'{indent}{indent}</nodes>')

    # Edges
    lines.append(f'{indent}{indent}<edges>')
    edge_id = 0
    for edge in graph.edges():
        source_id = f"{edge.source[0]}:{edge.source[1]}"
        target_id = f"{edge.target[0]}:{edge.target[1]}"
        lines.append(f'{indent}{indent}{indent}<edge id="{edge_id}" source="{_escape_xml(source_id)}" target="{_escape_xml(target_id)}" label="{_escape_xml(edge.rel_type)}"/>')
        edge_id += 1
    lines.append(f'{indent}{indent}</edges>')

    lines.append(f'{indent}</graph>')
    lines.append('</gexf>')

    return nl.join(lines)


def export_to_rdf(
    graph: ISONGraph,
    format: str = 'turtle',
    base_uri: str = 'http://example.org/graph/'
) -> str:
    """
    Export to RDF format.

    Args:
        graph: Graph to export
        format: Output format ('turtle', 'ntriples', 'jsonld')
        base_uri: Base URI for resources

    Returns:
        RDF data in specified format
    """
    if format == 'turtle':
        return _export_to_turtle(graph, base_uri)
    elif format == 'ntriples':
        return _export_to_ntriples(graph, base_uri)
    elif format == 'jsonld':
        return _export_to_jsonld(graph, base_uri)
    else:
        raise ValueError(f"Unknown RDF format: {format}")


def _export_to_turtle(graph: ISONGraph, base_uri: str) -> str:
    """Export to Turtle format"""
    lines = []

    # Prefixes
    lines.append(f'@prefix : <{base_uri}> .')
    lines.append('@prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .')
    lines.append('@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .')
    lines.append('@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .')
    lines.append('')

    # Nodes
    for node in graph.nodes():
        subject = f":{_sanitize_id(node.type)}_{_sanitize_id(str(node.id))}"
        node_class = f":{_capitalize_first(node.type)}"

        lines.append(f'{subject} a {node_class} ;')

        props = []
        for key, value in node.properties.items():
            if isinstance(value, (int, float)):
                literal = f'"{value}"^^xsd:{"integer" if isinstance(value, int) else "decimal"}'
            elif isinstance(value, bool):
                literal = f'"{str(value).lower()}"^^xsd:boolean'
            else:
                literal = f'"{_escape_string(str(value))}"'
            props.append(f':{key} {literal}')

        if props:
            lines.append('    ' + ' ;\n    '.join(props) + ' .')
        else:
            lines[-1] = lines[-1][:-2] + ' .'
        lines.append('')

    # Edges
    for edge in graph.edges():
        subject = f":{_sanitize_id(edge.source[0])}_{_sanitize_id(str(edge.source[1]))}"
        predicate = f":{edge.rel_type}"
        obj = f":{_sanitize_id(edge.target[0])}_{_sanitize_id(str(edge.target[1]))}"
        lines.append(f'{subject} {predicate} {obj} .')

    return '\n'.join(lines)


def _export_to_ntriples(graph: ISONGraph, base_uri: str) -> str:
    """Export to N-Triples format"""
    lines = []
    rdf_type = '<http://www.w3.org/1999/02/22-rdf-syntax-ns#type>'

    for node in graph.nodes():
        subject = f'<{base_uri}{_sanitize_id(node.type)}_{_sanitize_id(str(node.id))}>'
        node_class = f'<{base_uri}{_capitalize_first(node.type)}>'
        lines.append(f'{subject} {rdf_type} {node_class} .')

        for key, value in node.properties.items():
            predicate = f'<{base_uri}{key}>'
            if isinstance(value, int):
                literal = f'"{value}"^^<http://www.w3.org/2001/XMLSchema#integer>'
            elif isinstance(value, float):
                literal = f'"{value}"^^<http://www.w3.org/2001/XMLSchema#decimal>'
            elif isinstance(value, bool):
                literal = f'"{str(value).lower()}"^^<http://www.w3.org/2001/XMLSchema#boolean>'
            else:
                literal = f'"{_escape_string(str(value))}"'
            lines.append(f'{subject} {predicate} {literal} .')

    for edge in graph.edges():
        subject = f'<{base_uri}{_sanitize_id(edge.source[0])}_{_sanitize_id(str(edge.source[1]))}>'
        predicate = f'<{base_uri}{edge.rel_type}>'
        obj = f'<{base_uri}{_sanitize_id(edge.target[0])}_{_sanitize_id(str(edge.target[1]))}>'
        lines.append(f'{subject} {predicate} {obj} .')

    return '\n'.join(lines)


def _export_to_jsonld(graph: ISONGraph, base_uri: str) -> str:
    """Export to JSON-LD format"""
    context = {
        "@base": base_uri,
        "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
        "rdfs": "http://www.w3.org/2000/01/rdf-schema#"
    }

    nodes_data = []
    for node in graph.nodes():
        node_data = {
            "@id": f"{_sanitize_id(node.type)}_{_sanitize_id(str(node.id))}",
            "@type": _capitalize_first(node.type),
            **node.properties
        }
        nodes_data.append(node_data)

    doc = {
        "@context": context,
        "@graph": nodes_data
    }

    return json.dumps(doc, indent=2)


def export_to_dot(
    graph: ISONGraph,
    rankdir: str = 'TB',
    node_colors: Optional[Dict[str, str]] = None
) -> str:
    """
    Export to DOT/Graphviz format.

    Args:
        graph: Graph to export
        rankdir: Graph direction ('TB', 'LR', 'BT', 'RL')
        node_colors: Optional dict of node_type -> color

    Returns:
        DOT format string
    """
    node_colors = node_colors or {}
    graph_type = 'digraph' if graph.directed else 'graph'
    arrow = '->' if graph.directed else '--'

    lines = [f'{graph_type} "{_escape_string(graph.name)}" {{']
    lines.append(f'  rankdir={rankdir};')
    lines.append('  node [shape=box, style=filled, fillcolor=lightgray];')
    lines.append('')

    # Nodes
    for node in graph.nodes():
        node_id = f"{node.type}:{node.id}"
        label = str(node.properties.get('name', node.properties.get('title', node.id)))
        color = node_colors.get(node.type, 'lightgray')
        lines.append(f'  "{node_id}" [label="{_escape_string(label)}", fillcolor="{color}"];')

    lines.append('')

    # Edges
    for edge in graph.edges():
        source_id = f"{edge.source[0]}:{edge.source[1]}"
        target_id = f"{edge.target[0]}:{edge.target[1]}"
        lines.append(f'  "{source_id}" {arrow} "{target_id}" [label="{edge.rel_type}"];')

    lines.append('}')

    return '\n'.join(lines)


# =============================================================================
# Data Format Exports
# =============================================================================

def export_to_json(
    graph: ISONGraph,
    pretty_print: bool = True
) -> str:
    """Export to JSON format"""
    data = {
        'name': graph.name,
        'directed': graph.directed,
        'nodes': [
            {
                'type': n.type,
                'id': n.id,
                'properties': n.properties
            }
            for n in graph.nodes()
        ],
        'edges': [
            {
                'type': e.rel_type,
                'source': {'type': e.source[0], 'id': e.source[1]},
                'target': {'type': e.target[0], 'id': e.target[1]},
                'properties': e.properties
            }
            for e in graph.edges()
        ]
    }

    return json.dumps(data, indent=2 if pretty_print else None)


def export_to_json_compact(graph: ISONGraph) -> str:
    """Export to compact JSON (abbreviated keys)"""
    data = {
        'n': graph.name,
        'd': 1 if graph.directed else 0,
        'v': [{'t': n.type, 'i': n.id, 'p': n.properties} for n in graph.nodes()],
        'e': [
            {
                'r': e.rel_type,
                's': [e.source[0], e.source[1]],
                't': [e.target[0], e.target[1]],
                'p': e.properties if e.properties else None
            }
            for e in graph.edges()
        ]
    }
    return json.dumps(data, separators=(',', ':'))


def export_to_json_ultra_compact(graph: ISONGraph) -> str:
    """Export to ultra-compact JSON (array-based)"""
    nodes = [[n.type, n.id, n.properties] for n in graph.nodes()]
    edges = [
        [e.rel_type, e.source[0], e.source[1], e.target[0], e.target[1], e.properties or None]
        for e in graph.edges()
    ]
    return json.dumps([graph.name, 1 if graph.directed else 0, nodes, edges], separators=(',', ':'))


def export_to_json_rpc(
    graph: ISONGraph,
    base_id: int = 1,
    method_prefix: str = 'graph'
) -> str:
    """Export as JSON-RPC batch requests"""
    requests = []
    req_id = base_id

    # Create graph
    requests.append({
        'jsonrpc': '2.0',
        'method': f'{method_prefix}.create',
        'params': {'name': graph.name, 'directed': graph.directed},
        'id': req_id
    })
    req_id += 1

    # Add nodes
    for node in graph.nodes():
        requests.append({
            'jsonrpc': '2.0',
            'method': f'{method_prefix}.addNode',
            'params': {'type': node.type, 'id': node.id, 'properties': node.properties},
            'id': req_id
        })
        req_id += 1

    # Add edges
    for edge in graph.edges():
        requests.append({
            'jsonrpc': '2.0',
            'method': f'{method_prefix}.addEdge',
            'params': {
                'relType': edge.rel_type,
                'source': {'type': edge.source[0], 'id': edge.source[1]},
                'target': {'type': edge.target[0], 'id': edge.target[1]},
                'properties': edge.properties
            },
            'id': req_id
        })
        req_id += 1

    return json.dumps(requests, indent=2)


def export_to_yaml(
    graph: ISONGraph,
    flow_style: bool = False
) -> str:
    """Export to YAML format"""
    lines = ['# ISONGraph Export']
    lines.append(f'# Generated: {datetime.now().isoformat()}')
    lines.append('')
    lines.append(f'name: {_yaml_value(graph.name)}')
    lines.append(f'directed: {str(graph.directed).lower()}')
    lines.append('')

    lines.append('nodes:')
    for node in graph.nodes():
        if flow_style:
            props = json.dumps(node.properties)
            lines.append(f'  - {{type: {node.type}, id: {_yaml_value(node.id)}, properties: {props}}}')
        else:
            lines.append(f'  - type: {node.type}')
            lines.append(f'    id: {_yaml_value(node.id)}')
            if node.properties:
                lines.append('    properties:')
                for key, value in node.properties.items():
                    lines.append(f'      {key}: {_yaml_value(value)}')

    lines.append('')
    lines.append('edges:')
    for edge in graph.edges():
        if flow_style:
            props = json.dumps(edge.properties)
            lines.append(f'  - {{type: {edge.rel_type}, source: "{edge.source[0]}:{edge.source[1]}", target: "{edge.target[0]}:{edge.target[1]}", properties: {props}}}')
        else:
            lines.append(f'  - type: {edge.rel_type}')
            lines.append(f'    source: "{edge.source[0]}:{edge.source[1]}"')
            lines.append(f'    target: "{edge.target[0]}:{edge.target[1]}"')
            if edge.properties:
                lines.append('    properties:')
                for key, value in edge.properties.items():
                    lines.append(f'      {key}: {_yaml_value(value)}')

    return '\n'.join(lines)


def export_to_toml(graph: ISONGraph) -> str:
    """Export to TOML format"""
    lines = ['# ISONGraph Export']
    lines.append(f'# Generated: {datetime.now().isoformat()}')
    lines.append('')
    lines.append('[graph]')
    lines.append(f'name = {_toml_value(graph.name)}')
    lines.append(f'directed = {str(graph.directed).lower()}')
    lines.append(f'node_count = {graph.node_count()}')
    lines.append(f'edge_count = {graph.edge_count()}')
    lines.append('')

    for node_type in graph.node_types():
        lines.append(f'[[nodes.{node_type}]]')
        for node in graph.nodes(node_type):
            lines.append(f'  [[nodes.{node_type}.items]]')
            lines.append(f'  id = {_toml_value(node.id)}')
            for key, value in node.properties.items():
                lines.append(f'  {key} = {_toml_value(value)}')
            lines.append('')

    for edge_type in graph.edge_types():
        lines.append(f'[[edges.{edge_type}]]')
        for edge in graph.edges(edge_type):
            lines.append(f'  [[edges.{edge_type}.items]]')
            lines.append(f'  source = "{edge.source[0]}:{edge.source[1]}"')
            lines.append(f'  target = "{edge.target[0]}:{edge.target[1]}"')
            for key, value in edge.properties.items():
                lines.append(f'  {key} = {_toml_value(value)}')
            lines.append('')

    return '\n'.join(lines)


def export_to_xml(
    graph: ISONGraph,
    flat: bool = False
) -> str:
    """Export to XML format"""
    if flat:
        return _export_to_xml_flat(graph)
    return _export_to_xml_structured(graph)


def _export_to_xml_structured(graph: ISONGraph) -> str:
    """Export to structured XML"""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append('<!-- ISONGraph Export -->')
    lines.append(f'<graph name="{_escape_xml(graph.name)}" directed="{graph.directed}">')

    lines.append(f'  <nodes count="{graph.node_count()}">')
    for node in graph.nodes():
        if node.properties:
            lines.append(f'    <node type="{_escape_xml(node.type)}" id="{_escape_xml(str(node.id))}">')
            lines.append('      <properties>')
            for key, value in node.properties.items():
                val_type = type(value).__name__
                lines.append(f'        <property name="{_escape_xml(key)}" type="{val_type}">{_escape_xml(str(value))}</property>')
            lines.append('      </properties>')
            lines.append('    </node>')
        else:
            lines.append(f'    <node type="{_escape_xml(node.type)}" id="{_escape_xml(str(node.id))}"/>')
    lines.append('  </nodes>')

    lines.append(f'  <edges count="{graph.edge_count()}">')
    for edge in graph.edges():
        lines.append(f'    <edge type="{_escape_xml(edge.rel_type)}" source-type="{_escape_xml(edge.source[0])}" source-id="{_escape_xml(str(edge.source[1]))}" target-type="{_escape_xml(edge.target[0])}" target-id="{_escape_xml(str(edge.target[1]))}"/>')
    lines.append('  </edges>')

    lines.append('</graph>')

    return '\n'.join(lines)


def _export_to_xml_flat(graph: ISONGraph) -> str:
    """Export to flat XML"""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']
    lines.append(f'<graph name="{_escape_xml(graph.name)}" directed="{graph.directed}" nodes="{graph.node_count()}" edges="{graph.edge_count()}">')

    for node in graph.nodes():
        props = ' '.join(f'{k}="{_escape_xml(str(v))}"' for k, v in node.properties.items())
        lines.append(f'  <node type="{node.type}" id="{node.id}" {props}/>')

    for edge in graph.edges():
        props = ' '.join(f'{k}="{_escape_xml(str(v))}"' for k, v in edge.properties.items())
        lines.append(f'  <edge rel="{edge.rel_type}" from="{edge.source[0]}:{edge.source[1]}" to="{edge.target[0]}:{edge.target[1]}" {props}/>')

    lines.append('</graph>')

    return '\n'.join(lines)


def export_to_csv(
    graph: ISONGraph,
    delimiter: str = ',',
    separate_files: bool = False,
    include_headers: bool = True
) -> Dict[str, str]:
    """
    Export to CSV format.

    Args:
        graph: Graph to export
        delimiter: Field delimiter
        separate_files: Whether to separate by type
        include_headers: Include header row

    Returns:
        Dict with 'nodes', 'edges' keys (and type-specific keys if separate_files)
    """
    result = {}

    # Collect all node property keys
    node_props = set()
    for node in graph.nodes():
        node_props.update(node.properties.keys())
    node_props = sorted(node_props)

    # Build nodes CSV
    node_lines = []
    if include_headers:
        node_lines.append(delimiter.join(['_type', '_id'] + node_props))

    for node in graph.nodes():
        values = [node.type, str(node.id)]
        for prop in node_props:
            val = node.properties.get(prop, '')
            if delimiter in str(val) or '"' in str(val) or '\n' in str(val):
                val = f'"{str(val).replace(chr(34), chr(34)+chr(34))}"'
            values.append(str(val))
        node_lines.append(delimiter.join(values))

    result['nodes'] = '\n'.join(node_lines)

    # Collect all edge property keys
    edge_props = set()
    for edge in graph.edges():
        edge_props.update(edge.properties.keys())
    edge_props = sorted(edge_props)

    # Build edges CSV
    edge_lines = []
    if include_headers:
        edge_lines.append(delimiter.join(['_type', '_source', '_target'] + edge_props))

    for edge in graph.edges():
        values = [
            edge.rel_type,
            f"{edge.source[0]}:{edge.source[1]}",
            f"{edge.target[0]}:{edge.target[1]}"
        ]
        for prop in edge_props:
            val = edge.properties.get(prop, '')
            if delimiter in str(val) or '"' in str(val):
                val = f'"{str(val).replace(chr(34), chr(34)+chr(34))}"'
            values.append(str(val))
        edge_lines.append(delimiter.join(values))

    result['edges'] = '\n'.join(edge_lines)

    # Separate by type if requested
    if separate_files:
        result['nodes_by_type'] = {}
        for node_type in graph.node_types():
            type_lines = []
            type_nodes = list(graph.nodes(node_type))
            if type_nodes:
                type_props = set()
                for n in type_nodes:
                    type_props.update(n.properties.keys())
                type_props = sorted(type_props)

                if include_headers:
                    type_lines.append(delimiter.join(['_id'] + type_props))
                for node in type_nodes:
                    values = [str(node.id)]
                    for prop in type_props:
                        values.append(str(node.properties.get(prop, '')))
                    type_lines.append(delimiter.join(values))

                result['nodes_by_type'][node_type] = '\n'.join(type_lines)

        result['edges_by_type'] = {}
        for edge_type in graph.edge_types():
            type_lines = []
            type_edges = list(graph.edges(edge_type))
            if type_edges:
                if include_headers:
                    type_lines.append(delimiter.join(['_source', '_target']))
                for edge in type_edges:
                    type_lines.append(delimiter.join([
                        f"{edge.source[0]}:{edge.source[1]}",
                        f"{edge.target[0]}:{edge.target[1]}"
                    ]))
                result['edges_by_type'][edge_type] = '\n'.join(type_lines)

    return result


# =============================================================================
# Visualization Exports
# =============================================================================

def export_to_d3(graph: ISONGraph) -> Dict[str, List[Dict]]:
    """Export for D3.js force-directed graph"""
    nodes = [
        {
            'id': f"{n.type}:{n.id}",
            'group': n.type,
            'properties': n.properties
        }
        for n in graph.nodes()
    ]

    links = [
        {
            'source': f"{e.source[0]}:{e.source[1]}",
            'target': f"{e.target[0]}:{e.target[1]}",
            'type': e.rel_type,
            'properties': e.properties
        }
        for e in graph.edges()
    ]

    return {'nodes': nodes, 'links': links}


def export_to_visjs(
    graph: ISONGraph,
    node_colors: Optional[Dict[str, str]] = None
) -> Dict[str, List[Dict]]:
    """Export for vis.js network"""
    node_colors = node_colors or {}

    nodes = [
        {
            'id': f"{n.type}:{n.id}",
            'label': str(n.properties.get('name', n.properties.get('title', n.id))),
            'group': n.type,
            'title': '\n'.join(f"{k}: {v}" for k, v in n.properties.items()),
            'color': node_colors.get(n.type)
        }
        for n in graph.nodes()
    ]

    edges = [
        {
            'from': f"{e.source[0]}:{e.source[1]}",
            'to': f"{e.target[0]}:{e.target[1]}",
            'label': e.rel_type,
            'arrows': 'to' if graph.directed else None
        }
        for e in graph.edges()
    ]

    return {'nodes': nodes, 'edges': edges}


def export_to_mermaid(
    graph: ISONGraph,
    direction: str = 'TB',
    include_labels: bool = True
) -> str:
    """Export to Mermaid diagram format"""
    lines = [f'graph {direction}']

    # Nodes
    for node in graph.nodes():
        node_id = _sanitize_id(f"{node.type}_{node.id}")
        label = str(node.properties.get('name', node.properties.get('title', node.id)))
        lines.append(f'    {node_id}["{_escape_string(label)}"]')

    # Edges
    for edge in graph.edges():
        source_id = _sanitize_id(f"{edge.source[0]}_{edge.source[1]}")
        target_id = _sanitize_id(f"{edge.target[0]}_{edge.target[1]}")
        arrow = '-->' if graph.directed else '---'

        if include_labels:
            lines.append(f'    {source_id} {arrow}|{edge.rel_type}| {target_id}')
        else:
            lines.append(f'    {source_id} {arrow} {target_id}')

    return '\n'.join(lines)


# =============================================================================
# Analysis Format Exports
# =============================================================================

def export_to_adjacency_list(
    graph: ISONGraph,
    format: str = 'simple',
    separator: str = ' '
) -> str:
    """
    Export to adjacency list format.

    Args:
        graph: Graph to export
        format: 'simple', 'weighted', or 'typed'
        separator: Field separator

    Returns:
        Adjacency list string
    """
    adj_map: Dict[str, List[Dict]] = {}

    for node in graph.nodes():
        key = f"{node.type}:{node.id}"
        if key not in adj_map:
            adj_map[key] = []

    for edge in graph.edges():
        source_key = f"{edge.source[0]}:{edge.source[1]}"
        target_key = f"{edge.target[0]}:{edge.target[1]}"
        weight = edge.properties.get('weight', 1)

        if source_key not in adj_map:
            adj_map[source_key] = []
        adj_map[source_key].append({
            'target': target_key,
            'type': edge.rel_type,
            'weight': weight
        })

    lines = []
    for source, targets in adj_map.items():
        if format == 'simple':
            target_list = separator.join(t['target'] for t in targets)
        elif format == 'weighted':
            target_list = separator.join(f"{t['target']}:{t['weight']}" for t in targets)
        elif format == 'typed':
            target_list = separator.join(f"{t['target']}[{t['type']}]" for t in targets)
        else:
            target_list = separator.join(t['target'] for t in targets)

        lines.append(f"{source}{separator}{target_list}")

    return '\n'.join(lines)


def export_to_adjacency_matrix(
    graph: ISONGraph,
    include_headers: bool = True,
    separator: str = ','
) -> str:
    """Export to adjacency matrix format"""
    node_list = list(graph.nodes())
    node_keys = [f"{n.type}:{n.id}" for n in node_list]
    node_index = {k: i for i, k in enumerate(node_keys)}

    # Initialize matrix
    n = len(node_keys)
    matrix = [[0] * n for _ in range(n)]

    # Fill matrix
    for edge in graph.edges():
        source_key = f"{edge.source[0]}:{edge.source[1]}"
        target_key = f"{edge.target[0]}:{edge.target[1]}"
        source_idx = node_index.get(source_key)
        target_idx = node_index.get(target_key)

        if source_idx is not None and target_idx is not None:
            weight = edge.properties.get('weight', 1)
            matrix[source_idx][target_idx] = weight
            if not graph.directed:
                matrix[target_idx][source_idx] = weight

    lines = []
    if include_headers:
        lines.append(separator.join([''] + node_keys))

    for i, key in enumerate(node_keys):
        if include_headers:
            row = [key] + [str(v) for v in matrix[i]]
        else:
            row = [str(v) for v in matrix[i]]
        lines.append(separator.join(row))

    return '\n'.join(lines)


def export_to_edge_list(
    graph: ISONGraph,
    format: str = 'simple',
    separator: str = '\t',
    include_headers: bool = False
) -> str:
    """
    Export to edge list format.

    Args:
        graph: Graph to export
        format: 'simple', 'weighted', 'typed', or 'full'
        separator: Field separator
        include_headers: Include header row

    Returns:
        Edge list string
    """
    lines = []

    if include_headers:
        if format == 'simple':
            lines.append(separator.join(['source', 'target']))
        elif format == 'weighted':
            lines.append(separator.join(['source', 'target', 'weight']))
        elif format == 'typed':
            lines.append(separator.join(['source', 'target', 'type']))
        elif format == 'full':
            lines.append(separator.join(['source', 'target', 'type', 'weight', 'properties']))

    for edge in graph.edges():
        source = f"{edge.source[0]}:{edge.source[1]}"
        target = f"{edge.target[0]}:{edge.target[1]}"
        weight = edge.properties.get('weight', 1)

        if format == 'simple':
            lines.append(separator.join([source, target]))
        elif format == 'weighted':
            lines.append(separator.join([source, target, str(weight)]))
        elif format == 'typed':
            lines.append(separator.join([source, target, edge.rel_type]))
        elif format == 'full':
            lines.append(separator.join([source, target, edge.rel_type, str(weight), json.dumps(edge.properties)]))

    return '\n'.join(lines)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Options
    'ExportOptions',

    # Database
    'export_to_cypher',
    'export_to_cypher_merge',
    'export_to_sql',

    # Graph formats
    'export_to_graphml',
    'export_to_gexf',
    'export_to_rdf',
    'export_to_dot',

    # Data formats
    'export_to_json',
    'export_to_json_compact',
    'export_to_json_ultra_compact',
    'export_to_json_rpc',
    'export_to_yaml',
    'export_to_toml',
    'export_to_xml',
    'export_to_csv',

    # Visualization
    'export_to_d3',
    'export_to_visjs',
    'export_to_mermaid',

    # Analysis
    'export_to_adjacency_list',
    'export_to_adjacency_matrix',
    'export_to_edge_list',
]
