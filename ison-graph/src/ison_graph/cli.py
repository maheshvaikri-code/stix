#!/usr/bin/env python3
"""
ISONGraph CLI

A comprehensive command-line interface for ISONGraph operations.

Usage:
    isongraph <command> [options]

Commands:
    init          Create a new graph file
    info          Display graph statistics
    node          Node operations (add, get, list, update, remove)
    edge          Edge operations (add, get, list, remove)
    query         Query the graph
    traverse      Traverse from a node
    path          Find paths between nodes
    export        Export to various formats
    import        Import from various formats
    repl          Start interactive REPL
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

# Import core ISONGraph
from .core import ISONGraph, Node, Edge, NodeRef, Direction

# Import export functions
from .export import (
    export_to_cypher,
    export_to_cypher_merge,
    export_to_sql,
    export_to_graphml,
    export_to_gexf,
    export_to_rdf,
    export_to_dot,
    export_to_json,
    export_to_json_compact,
    export_to_json_ultra_compact,
    export_to_json_rpc,
    export_to_yaml,
    export_to_toml,
    export_to_xml,
    export_to_csv,
    export_to_d3,
    export_to_visjs,
    export_to_mermaid,
    export_to_adjacency_list,
    export_to_adjacency_matrix,
    export_to_edge_list
)

# =============================================================================
# Constants & Configuration
# =============================================================================

VERSION = '1.0.0'
DEFAULT_GRAPH_FILE = 'graph.ison'

# ANSI color codes
class Colors:
    RESET = '\033[0m'
    BRIGHT = '\033[1m'
    DIM = '\033[2m'
    RED = '\033[31m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    BLUE = '\033[34m'
    MAGENTA = '\033[35m'
    CYAN = '\033[36m'
    WHITE = '\033[37m'

# Check if colors should be disabled
NO_COLOR = os.environ.get('NO_COLOR', '') or not sys.stdout.isatty()

# =============================================================================
# Utility Functions
# =============================================================================

def color(text: str, color_code: str) -> str:
    """Apply color to text if colors are enabled."""
    if NO_COLOR:
        return text
    return f"{color_code}{text}{Colors.RESET}"


def success(msg: str) -> None:
    """Print success message."""
    print(color('✓ ', Colors.GREEN) + msg)


def error(msg: str) -> None:
    """Print error message."""
    print(color('✗ ', Colors.RED) + msg, file=sys.stderr)


def info(msg: str) -> None:
    """Print info message."""
    print(color('ℹ ', Colors.BLUE) + msg)


def warn(msg: str) -> None:
    """Print warning message."""
    print(color('⚠ ', Colors.YELLOW) + msg)


def heading(msg: str) -> None:
    """Print a heading."""
    print('\n' + color(msg, Colors.BRIGHT + Colors.CYAN))
    print(color('─' * len(msg), Colors.DIM))


def print_table(headers: List[str], rows: List[List[str]]) -> None:
    """Print a formatted table."""
    if not rows:
        return

    # Calculate column widths
    col_widths = [
        max(len(str(h)), max((len(str(row[i])) if i < len(row) else 0) for row in rows))
        for i, h in enumerate(headers)
    ]

    # Build separator
    separator = '┼'.join('─' * (w + 2) for w in col_widths)

    # Print top border
    print('┌' + separator.replace('┼', '┬') + '┐')

    # Print header
    header_row = '│'.join(f' {h.ljust(col_widths[i])} ' for i, h in enumerate(headers))
    print('│' + header_row + '│')

    # Print separator
    print('├' + separator + '┤')

    # Print data rows
    for row in rows:
        data_row = '│'.join(
            f' {str(row[i] if i < len(row) else "").ljust(col_widths[i])} '
            for i in range(len(headers))
        )
        print('│' + data_row + '│')

    # Print bottom border
    print('└' + separator.replace('┼', '┴') + '┘')


def parse_node_ref(ref_str: str) -> NodeRef:
    """Parse a node reference string like 'type:id' or ':type:id'."""
    normalized = ref_str[1:] if ref_str.startswith(':') else ref_str
    parts = normalized.split(':', 1)

    if len(parts) < 2:
        raise ValueError(f'Invalid node reference: {ref_str}. Use format "type:id"')

    node_type, node_id = parts[0], parts[1]

    # Try to parse ID as number if possible
    try:
        if node_id.isdigit():
            return (node_type, int(node_id))
    except ValueError:
        pass

    return (node_type, node_id)


def format_node_ref(ref: NodeRef) -> str:
    """Format a node reference as a string."""
    return f':{ref[0]}:{ref[1]}'


def parse_properties(props_str: str) -> Dict[str, Any]:
    """Parse property string like 'key=value,key2=value2' or JSON."""
    if not props_str:
        return {}

    # Try JSON first
    if props_str.startswith('{'):
        try:
            return json.loads(props_str)
        except json.JSONDecodeError:
            pass

    props: Dict[str, Any] = {}
    pairs = props_str.split(',')

    for pair in pairs:
        if '=' not in pair:
            continue

        key, value = pair.split('=', 1)
        key = key.strip()
        value = value.strip()

        # Try to parse value as JSON
        try:
            props[key] = json.loads(value)
        except json.JSONDecodeError:
            props[key] = value

    return props


def load_graph(file_path: str) -> ISONGraph:
    """Load a graph from a file."""
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f'Graph file not found: {file_path}')

    content = path.read_text(encoding='utf-8')
    ext = path.suffix.lower()

    if ext == '.isonl':
        return ISONGraph.from_isonl(content, path.stem)
    else:
        return ISONGraph.from_ison(content, path.stem)


def save_graph(graph: ISONGraph, file_path: str) -> None:
    """Save a graph to a file."""
    path = Path(file_path)
    ext = path.suffix.lower()

    content = graph.to_isonl() if ext == '.isonl' else graph.to_ison()
    path.write_text(content, encoding='utf-8')


def load_graph_or_create(file_path: str) -> ISONGraph:
    """Load a graph or create a new one if it doesn't exist."""
    try:
        return load_graph(file_path)
    except FileNotFoundError:
        return ISONGraph(Path(file_path).stem)


# =============================================================================
# Command Handlers
# =============================================================================

def cmd_init(args: argparse.Namespace) -> int:
    """Create a new graph file."""
    name = args.name or 'graph'
    file_path = args.file or f'{name}.ison'

    if Path(file_path).exists() and not args.force:
        error(f'File already exists: {file_path}. Use --force to overwrite.')
        return 1

    graph = ISONGraph(name)

    # Add sample data if requested
    if args.sample:
        graph.add_node('person', 'alice', {'name': 'Alice', 'role': 'Engineer'})
        graph.add_node('person', 'bob', {'name': 'Bob', 'role': 'Manager'})
        graph.add_node('company', 'acme', {'name': 'ACME Corp', 'industry': 'Technology'})
        graph.add_edge('WORKS_AT', ('person', 'alice'), ('company', 'acme'))
        graph.add_edge('WORKS_AT', ('person', 'bob'), ('company', 'acme'))
        graph.add_edge('KNOWS', ('person', 'alice'), ('person', 'bob'), {'since': 2020})

    save_graph(graph, file_path)
    success(f'Created graph file: {file_path}')

    if args.sample:
        info('Added sample data (2 persons, 1 company, 3 relationships)')

    return 0


def cmd_info(args: argparse.Namespace) -> int:
    """Display graph statistics."""
    try:
        graph = load_graph(args.file)
    except FileNotFoundError as e:
        error(str(e))
        return 1

    if args.json:
        data = {
            'name': graph.name,
            'nodes': graph.node_count(),
            'edges': graph.edge_count(),
            'nodeTypes': graph.node_types(),
            'edgeTypes': graph.edge_types(),
            'directed': graph.directed
        }
        print(json.dumps(data, indent=2))
        return 0

    heading(f'Graph: {graph.name}')

    print(f'''
  Nodes:      {color(str(graph.node_count()), Colors.GREEN)}
  Edges:      {color(str(graph.edge_count()), Colors.GREEN)}
  Directed:   {'Yes' if graph.directed else 'No'}
  ''')

    node_types = graph.node_types()
    if node_types:
        print(color('  Node Types:', Colors.BRIGHT))
        for t in node_types:
            print(f'    - {t}: {graph.node_count(t)} nodes')

    edge_types = graph.edge_types()
    if edge_types:
        print(color('\n  Edge Types:', Colors.BRIGHT))
        for t in edge_types:
            print(f'    - {t}: {graph.edge_count(t)} edges')

    # Token efficiency stats
    ison_size = len(graph.to_ison())
    json_size = len(export_to_json(graph))
    savings = round((1 - ison_size / json_size) * 100) if json_size > 0 else 0

    print(color('\n  Token Efficiency:', Colors.BRIGHT))
    print(f'    ISON size:  {ison_size} chars')
    print(f'    JSON size:  {json_size} chars')
    print(f'    Savings:    {color(f"{savings}%", Colors.GREEN)}')

    return 0


def cmd_node(args: argparse.Namespace) -> int:
    """Handle node operations."""
    subcommand = args.node_command

    try:
        if subcommand == 'add':
            graph = load_graph_or_create(args.file)

            if not args.type or not args.id:
                error('Usage: isongraph node add <type> <id> [props]')
                return 1

            props = parse_properties(args.props) if args.props else {}
            node_id: Union[str, int] = int(args.id) if args.id.isdigit() else args.id

            graph.add_node(args.type, node_id, props)
            save_graph(graph, args.file)
            success(f'Added node {format_node_ref((args.type, node_id))}')

            if props:
                info(f'Properties: {json.dumps(props)}')

        elif subcommand == 'get':
            graph = load_graph(args.file)
            ref = parse_node_ref(args.ref)
            node = graph.get_node_by_ref(ref)

            if args.json:
                data = {
                    'type': node.type,
                    'id': node.id,
                    'properties': node.properties
                }
                print(json.dumps(data, indent=2))
            else:
                heading(f'Node: {format_node_ref(ref)}')
                print(f'  Type: {node.type}')
                print(f'  ID:   {node.id}')
                print('  Properties:')
                for key, value in node.properties.items():
                    print(f'    {key}: {json.dumps(value)}')

                # Show connections
                out_edges = list(graph.edges(source=ref))
                in_edges = list(graph.edges(target=ref))

                if out_edges:
                    print(color('\n  Outgoing Edges:', Colors.BRIGHT))
                    for edge in out_edges:
                        print(f'    -[{edge.rel_type}]-> {format_node_ref(edge.target)}')

                if in_edges:
                    print(color('\n  Incoming Edges:', Colors.BRIGHT))
                    for edge in in_edges:
                        print(f'    <-[{edge.rel_type}]- {format_node_ref(edge.source)}')

        elif subcommand == 'list':
            graph = load_graph(args.file)
            nodes = list(graph.nodes(args.type))
            limit = args.limit or 50

            if args.json:
                data = [
                    {'type': n.type, 'id': n.id, 'properties': n.properties}
                    for n in nodes[:limit]
                ]
                print(json.dumps(data, indent=2))
                return 0

            if not nodes:
                info('No nodes found')
                return 0

            type_filter = f' (type: {args.type})' if args.type else ''
            heading(f'Nodes{type_filter}')

            rows = [
                [n.type, str(n.id), json.dumps(n.properties)[:50]]
                for n in nodes[:limit]
            ]

            print_table(['Type', 'ID', 'Properties'], rows)

            if len(nodes) > limit:
                info(f'Showing {limit} of {len(nodes)} nodes. Use --limit to show more.')

        elif subcommand == 'update':
            graph = load_graph(args.file)
            ref = parse_node_ref(args.ref)
            props = parse_properties(args.props) if args.props else {}

            graph.update_node(ref[0], ref[1], props)
            save_graph(graph, args.file)
            success(f'Updated node {format_node_ref(ref)}')
            info(f'New properties: {json.dumps(props)}')

        elif subcommand == 'remove':
            graph = load_graph(args.file)
            ref = parse_node_ref(args.ref)

            graph.remove_node(ref[0], ref[1])
            save_graph(graph, args.file)
            success(f'Removed node {format_node_ref(ref)}')

        elif subcommand == 'types':
            graph = load_graph(args.file)
            types = graph.node_types()

            if args.json:
                data = [{'type': t, 'count': graph.node_count(t)} for t in types]
                print(json.dumps(data, indent=2))
                return 0

            heading('Node Types')
            for t in types:
                print(f'  {t}: {graph.node_count(t)} nodes')

        else:
            error(f'Unknown node subcommand: {subcommand}')
            print('Available: add, get, list, update, remove, types')
            return 1

    except Exception as e:
        error(str(e))
        return 1

    return 0


def cmd_edge(args: argparse.Namespace) -> int:
    """Handle edge operations."""
    subcommand = args.edge_command

    try:
        if subcommand == 'add':
            graph = load_graph_or_create(args.file)

            rel_type = args.rel_type
            source = parse_node_ref(args.source)
            target = parse_node_ref(args.target)
            props = parse_properties(args.props) if args.props else {}

            graph.add_edge(rel_type, source, target, props)
            save_graph(graph, args.file)
            success(f'Added edge {format_node_ref(source)} -[{rel_type}]-> {format_node_ref(target)}')

        elif subcommand == 'get':
            graph = load_graph(args.file)

            rel_type = args.rel_type
            source = parse_node_ref(args.source)
            target = parse_node_ref(args.target)

            edge = graph.get_edge(rel_type, source, target)

            if args.json:
                data = {
                    'type': edge.rel_type,
                    'source': {'type': edge.source[0], 'id': edge.source[1]},
                    'target': {'type': edge.target[0], 'id': edge.target[1]},
                    'properties': edge.properties
                }
                print(json.dumps(data, indent=2))
            else:
                heading(f'Edge: {format_node_ref(source)} -[{rel_type}]-> {format_node_ref(target)}')
                print('  Properties:')
                for key, value in edge.properties.items():
                    print(f'    {key}: {json.dumps(value)}')

        elif subcommand == 'list':
            graph = load_graph(args.file)
            edges = list(graph.edges(args.rel_type))
            limit = args.limit or 50

            if args.json:
                data = [
                    {
                        'type': e.rel_type,
                        'source': {'type': e.source[0], 'id': e.source[1]},
                        'target': {'type': e.target[0], 'id': e.target[1]},
                        'properties': e.properties
                    }
                    for e in edges[:limit]
                ]
                print(json.dumps(data, indent=2))
                return 0

            if not edges:
                info('No edges found')
                return 0

            type_filter = f' (type: {args.rel_type})' if args.rel_type else ''
            heading(f'Edges{type_filter}')

            rows = [
                [e.rel_type, format_node_ref(e.source), format_node_ref(e.target),
                 json.dumps(e.properties)[:30]]
                for e in edges[:limit]
            ]

            print_table(['Type', 'Source', 'Target', 'Properties'], rows)

            if len(edges) > limit:
                info(f'Showing {limit} of {len(edges)} edges. Use --limit to show more.')

        elif subcommand == 'remove':
            graph = load_graph(args.file)

            rel_type = args.rel_type
            source = parse_node_ref(args.source)
            target = parse_node_ref(args.target)

            graph.remove_edge(rel_type, source, target)
            save_graph(graph, args.file)
            success(f'Removed edge {format_node_ref(source)} -[{rel_type}]-> {format_node_ref(target)}')

        elif subcommand == 'types':
            graph = load_graph(args.file)
            types = graph.edge_types()

            if args.json:
                data = [{'type': t, 'count': graph.edge_count(t)} for t in types]
                print(json.dumps(data, indent=2))
                return 0

            heading('Edge Types')
            for t in types:
                print(f'  {t}: {graph.edge_count(t)} edges')

        else:
            error(f'Unknown edge subcommand: {subcommand}')
            print('Available: add, get, list, remove, types')
            return 1

    except Exception as e:
        error(str(e))
        return 1

    return 0


def cmd_query(args: argparse.Namespace) -> int:
    """Execute a graph query pattern."""
    try:
        graph = load_graph(args.file)
        pattern = args.pattern

        if not pattern:
            error('Usage: isongraph query <pattern>')
            print('Example: isongraph query ":person:1 -[:KNOWS*2]-> *"')
            return 1

        results = graph.query(pattern)

        if args.json:
            data = [{'type': r[0], 'id': r[1]} for r in results]
            print(json.dumps(data, indent=2))
            return 0

        heading('Query Results')
        info(f'Pattern: {pattern}')
        print(f'Found {len(results)} nodes:\n')

        for ref in results:
            node = graph.get_node_by_ref(ref)
            print(f'  {format_node_ref(ref)}: {json.dumps(node.properties)}')

    except Exception as e:
        error(str(e))
        return 1

    return 0


def cmd_neighbors(args: argparse.Namespace) -> int:
    """Get neighbors of a node."""
    try:
        graph = load_graph(args.file)
        node_ref = parse_node_ref(args.node)
        rel_type = args.rel_type
        direction = (args.direction or 'out').lower()

        dir_map = {'in': Direction.IN, 'out': Direction.OUT, 'both': Direction.BOTH}
        dir_enum = dir_map.get(direction, Direction.OUT)

        neighbors = graph.neighbors(node_ref, rel_type, dir_enum)

        if args.json:
            data = [{'type': r[0], 'id': r[1]} for r in neighbors]
            print(json.dumps(data, indent=2))
            return 0

        heading(f'Neighbors of {format_node_ref(node_ref)}')
        if rel_type:
            info(f'Relationship: {rel_type}')
        info(f'Direction: {direction}')
        print(f'Found {len(neighbors)} neighbors:\n')

        for ref in neighbors:
            node = graph.get_node_by_ref(ref)
            print(f'  {format_node_ref(ref)}: {json.dumps(node.properties)}')

    except Exception as e:
        error(str(e))
        return 1

    return 0


def cmd_path(args: argparse.Namespace) -> int:
    """Find shortest path between nodes."""
    try:
        graph = load_graph(args.file)
        from_ref = parse_node_ref(args.from_node)
        to_ref = parse_node_ref(args.to_node)
        rel_type = args.rel_type
        max_hops = args.max_hops or 10

        path = graph.shortest_path(from_ref, to_ref, rel_type, max_hops)

        if not path:
            warn('No path found')
            return 0

        if args.json:
            data = {
                'length': path.length,
                'nodes': [{'type': r[0], 'id': r[1]} for r in path.nodes],
                'edges': [
                    {
                        'type': e.rel_type,
                        'source': {'type': e.source[0], 'id': e.source[1]},
                        'target': {'type': e.target[0], 'id': e.target[1]}
                    }
                    for e in path.edges
                ]
            }
            print(json.dumps(data, indent=2))
            return 0

        heading('Shortest Path')
        info(f'From: {format_node_ref(from_ref)}')
        info(f'To: {format_node_ref(to_ref)}')
        print(f'Length: {path.length} hops\n')

        print('Path:')
        for i, node_ref in enumerate(path.nodes):
            print(f'  {format_node_ref(node_ref)}')
            if i < len(path.edges):
                print(f'    ↓ [{path.edges[i].rel_type}]')

    except Exception as e:
        error(str(e))
        return 1

    return 0


def cmd_paths(args: argparse.Namespace) -> int:
    """Find all paths between nodes."""
    try:
        graph = load_graph(args.file)
        from_ref = parse_node_ref(args.from_node)
        to_ref = parse_node_ref(args.to_node)
        rel_type = args.rel_type
        max_hops = args.max_hops or 5

        paths = graph.all_paths(from_ref, to_ref, rel_type, max_hops)

        if not paths:
            warn('No paths found')
            return 0

        if args.json:
            data = [
                {
                    'length': p.length,
                    'nodes': [{'type': r[0], 'id': r[1]} for r in p.nodes]
                }
                for p in paths
            ]
            print(json.dumps(data, indent=2))
            return 0

        heading(f'All Paths ({len(paths)} found)')
        info(f'From: {format_node_ref(from_ref)}')
        info(f'To: {format_node_ref(to_ref)}')
        print()

        for i, p in enumerate(paths):
            path_str = ' → '.join(format_node_ref(n) for n in p.nodes)
            print(f'  {i + 1}. [{p.length} hops] {path_str}')

    except Exception as e:
        error(str(e))
        return 1

    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export graph to various formats."""
    try:
        graph = load_graph(args.file)
        fmt = args.format.lower()
        output_file = args.output
        output: str = ''

        # Database formats
        if fmt == 'cypher':
            if args.merge:
                output = export_to_cypher_merge(graph)
            else:
                output = export_to_cypher(graph)

        elif fmt == 'sql':
            output = export_to_sql(
                graph,
                dialect=args.dialect or 'postgres',
                table_prefix=args.prefix or '',
                include_drops=args.drop
            )

        # Graph formats
        elif fmt == 'graphml':
            output = export_to_graphml(graph)

        elif fmt == 'gexf':
            output = export_to_gexf(graph)

        elif fmt == 'rdf':
            output = export_to_rdf(graph, fmt=args.rdf_format or 'turtle')

        elif fmt in ('dot', 'graphviz'):
            output = export_to_dot(graph, rankdir=args.rankdir or 'TB')

        # Data formats
        elif fmt == 'json':
            output = export_to_json(graph)

        elif fmt in ('json-compact', 'jsoncompact'):
            output = export_to_json_compact(graph)

        elif fmt in ('json-ultra', 'jsonultra'):
            output = export_to_json_ultra_compact(graph)

        elif fmt in ('json-rpc', 'jsonrpc'):
            output = export_to_json_rpc(
                graph,
                method_prefix=args.prefix or 'graph',
                single=args.single,
                method=args.method or 'graph.import'
            )

        elif fmt in ('yaml', 'yml'):
            output = export_to_yaml(graph, flow_style=args.flow)

        elif fmt == 'toml':
            output = export_to_toml(graph)

        elif fmt == 'xml':
            output = export_to_xml(graph, flat=args.flat)

        elif fmt == 'csv':
            csv_result = export_to_csv(graph, separate_files=args.separate)

            if args.separate:
                # Write separate files
                base_name = output_file or 'graph'
                Path(f'{base_name}_nodes.csv').write_text(csv_result['nodes'])
                Path(f'{base_name}_edges.csv').write_text(csv_result['edges'])

                if 'nodes_by_type' in csv_result:
                    for node_type, content in csv_result['nodes_by_type'].items():
                        Path(f'{base_name}_nodes_{node_type}.csv').write_text(content)

                if 'edges_by_type' in csv_result:
                    for edge_type, content in csv_result['edges_by_type'].items():
                        Path(f'{base_name}_edges_{edge_type}.csv').write_text(content)

                success('Exported CSV files')
                return 0

            output = f"# Nodes\n{csv_result['nodes']}\n\n# Edges\n{csv_result['edges']}"

        # Visualization formats
        elif fmt == 'd3':
            output = json.dumps(export_to_d3(graph), indent=2)

        elif fmt == 'visjs':
            output = json.dumps(export_to_visjs(graph), indent=2)

        elif fmt == 'mermaid':
            output = export_to_mermaid(graph, direction=args.direction or 'TB')

        # Analysis formats
        elif fmt in ('adjlist', 'adjacency-list'):
            output = export_to_adjacency_list(graph, fmt=args.adj_format or 'simple')

        elif fmt in ('adjmatrix', 'adjacency-matrix'):
            output = export_to_adjacency_matrix(graph)

        elif fmt in ('edgelist', 'edge-list'):
            output = export_to_edge_list(
                graph,
                fmt=args.edge_format or 'simple',
                include_headers=args.headers
            )

        # Native formats
        elif fmt == 'ison':
            output = graph.to_ison()

        elif fmt == 'isonl':
            output = graph.to_isonl()

        else:
            error(f'Unknown export format: {fmt}')
            print('''
Available formats:

  Database:      cypher, sql
  Graph:         graphml, gexf, rdf, dot
  Data:          json, json-compact, json-ultra, json-rpc, yaml, toml, xml, csv
  Visualization: d3, visjs, mermaid
  Analysis:      adjlist, adjmatrix, edgelist
  Native:        ison, isonl
''')
            return 1

        if output_file:
            Path(output_file).write_text(output, encoding='utf-8')
            success(f'Exported to {output_file}')
        else:
            print(output)

    except Exception as e:
        error(str(e))
        return 1

    return 0


def cmd_import(args: argparse.Namespace) -> int:
    """Import graph from various formats."""
    try:
        fmt = args.format.lower()
        input_file = args.input_file

        if not Path(input_file).exists():
            error(f'File not found: {input_file}')
            return 1

        if fmt == 'json':
            content = Path(input_file).read_text(encoding='utf-8')
            data = json.loads(content)

            graph = ISONGraph(data.get('name', 'imported'), data.get('directed', True))

            for node in data.get('nodes', []):
                graph.add_node(node['type'], node['id'], node.get('properties', {}))

            for edge in data.get('edges', []):
                source = (edge['source']['type'], edge['source']['id'])
                target = (edge['target']['type'], edge['target']['id'])
                graph.add_edge(edge['type'], source, target, edge.get('properties', {}))

        else:
            error(f'Unknown import format: {fmt}')
            print('Available: json')
            return 1

        save_graph(graph, args.file)
        success(f'Imported {graph.node_count()} nodes and {graph.edge_count()} edges')

    except Exception as e:
        error(str(e))
        return 1

    return 0


def cmd_repl(args: argparse.Namespace) -> int:
    """Start interactive REPL mode."""
    try:
        graph = load_graph(args.file)
        info(f'Loaded graph from {args.file}')
    except FileNotFoundError:
        graph = ISONGraph('repl')
        info('Started with empty graph')

    print(f'''
{color('ISONGraph REPL', Colors.BRIGHT + Colors.CYAN)} v{VERSION}
{color('Type "help" for commands, "exit" to quit', Colors.DIM)}
''')

    def show_repl_help():
        print(f'''
{color('REPL Commands:', Colors.YELLOW)}

  {color('Node Operations', Colors.BRIGHT)}
    add node <type> <id> [props]     Add a node
    get node <type:id>               Get a node
    list nodes [type]                List nodes
    remove node <type:id>            Remove a node

  {color('Edge Operations', Colors.BRIGHT)}
    add edge <rel> <src> <tgt> [p]   Add an edge
    list edges [type]                List edges
    remove edge <rel> <src> <tgt>    Remove an edge

  {color('Query', Colors.BRIGHT)}
    neighbors <node> [rel]           Get neighbors
    path <from> <to>                 Find shortest path
    query <pattern>                  Execute query pattern

  {color('Other', Colors.BRIGHT)}
    info                             Show graph info
    save [file]                      Save graph
    load <file>                      Load graph
    export <format>                  Export graph
    clear                            Clear graph
    help                             Show this help
    exit                             Exit REPL
''')

    graph_file = args.file

    while True:
        try:
            line = input(color('isongraph> ', Colors.GREEN))
            line = line.strip()

            if not line:
                continue

            parts = line.split()
            cmd = parts[0].lower()

            if cmd in ('exit', 'quit', 'q'):
                print('Goodbye!')
                break

            elif cmd == 'help':
                show_repl_help()

            elif cmd == 'info':
                print(f'  Name: {graph.name}')
                print(f'  Nodes: {graph.node_count()}')
                print(f'  Edges: {graph.edge_count()}')
                print(f'  Node types: {", ".join(graph.node_types()) or "(none)"}')
                print(f'  Edge types: {", ".join(graph.edge_types()) or "(none)"}')

            elif cmd == 'add':
                if len(parts) > 1 and parts[1] == 'node':
                    node_type = parts[2]
                    node_id: Union[str, int] = int(parts[3]) if parts[3].isdigit() else parts[3]
                    props = parse_properties(' '.join(parts[4:])) if len(parts) > 4 else {}
                    graph.add_node(node_type, node_id, props)
                    success(f'Added node {format_node_ref((node_type, node_id))}')

                elif len(parts) > 1 and parts[1] == 'edge':
                    rel = parts[2]
                    src = parse_node_ref(parts[3])
                    tgt = parse_node_ref(parts[4])
                    props = parse_properties(' '.join(parts[5:])) if len(parts) > 5 else {}
                    graph.add_edge(rel, src, tgt, props)
                    success('Added edge')

            elif cmd == 'get':
                if len(parts) > 1 and parts[1] == 'node':
                    ref = parse_node_ref(parts[2])
                    node = graph.get_node_by_ref(ref)
                    print(f'  Type: {node.type}')
                    print(f'  ID: {node.id}')
                    print(f'  Properties: {json.dumps(node.properties)}')

            elif cmd == 'list':
                if len(parts) > 1 and parts[1] == 'nodes':
                    filter_type = parts[2] if len(parts) > 2 else None
                    nodes = list(graph.nodes(filter_type))[:20]
                    for n in nodes:
                        print(f'  {format_node_ref(n.ref)}: {json.dumps(n.properties)}')

                elif len(parts) > 1 and parts[1] == 'edges':
                    filter_type = parts[2] if len(parts) > 2 else None
                    edges = list(graph.edges(filter_type))[:20]
                    for e in edges:
                        print(f'  {format_node_ref(e.source)} -[{e.rel_type}]-> {format_node_ref(e.target)}')

            elif cmd == 'remove':
                if len(parts) > 1 and parts[1] == 'node':
                    ref = parse_node_ref(parts[2])
                    graph.remove_node(ref[0], ref[1])
                    success('Removed node')

                elif len(parts) > 1 and parts[1] == 'edge':
                    rel = parts[2]
                    src = parse_node_ref(parts[3])
                    tgt = parse_node_ref(parts[4])
                    graph.remove_edge(rel, src, tgt)
                    success('Removed edge')

            elif cmd == 'neighbors':
                ref = parse_node_ref(parts[1])
                rel_type = parts[2] if len(parts) > 2 else None
                neighbors = graph.neighbors(ref, rel_type)
                for n in neighbors:
                    node = graph.get_node_by_ref(n)
                    print(f'  {format_node_ref(n)}: {json.dumps(node.properties)}')

            elif cmd == 'path':
                from_ref = parse_node_ref(parts[1])
                to_ref = parse_node_ref(parts[2])
                rel_type = parts[3] if len(parts) > 3 else None
                p = graph.shortest_path(from_ref, to_ref, rel_type)
                if p:
                    print(f'  Length: {p.length} hops')
                    print(f'  Path: {" → ".join(format_node_ref(n) for n in p.nodes)}')
                else:
                    warn('No path found')

            elif cmd == 'query':
                pattern = ' '.join(parts[1:])
                results = graph.query(pattern)
                for r in results:
                    print(f'  {format_node_ref(r)}')

            elif cmd == 'save':
                save_file = parts[1] if len(parts) > 1 else graph_file
                save_graph(graph, save_file)
                success(f'Saved to {save_file}')

            elif cmd == 'load':
                graph = load_graph(parts[1])
                graph_file = parts[1]
                success(f'Loaded from {parts[1]}')

            elif cmd == 'export':
                fmt = parts[1] if len(parts) > 1 else 'ison'
                if fmt == 'ison':
                    print(graph.to_ison())
                elif fmt == 'json':
                    print(export_to_json(graph))
                elif fmt == 'cypher':
                    print(export_to_cypher(graph))
                elif fmt == 'mermaid':
                    print(export_to_mermaid(graph))
                else:
                    print(graph.to_ison())

            elif cmd == 'clear':
                graph = ISONGraph(graph.name)
                success('Cleared graph')

            else:
                warn(f'Unknown command: {cmd}. Type "help" for available commands.')

        except KeyboardInterrupt:
            print('\nGoodbye!')
            break
        except EOFError:
            print('\nGoodbye!')
            break
        except Exception as e:
            error(str(e))

    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate a graph file."""
    try:
        graph = load_graph(args.file)
        success(f'Graph is valid: {graph.node_count()} nodes, {graph.edge_count()} edges')
        return 0
    except Exception as e:
        error(str(e))
        return 1


# =============================================================================
# Main Entry Point
# =============================================================================

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser."""
    parser = argparse.ArgumentParser(
        prog='isongraph',
        description='ISONGraph CLI - Token-efficient graph operations from the command line',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Create a new graph
  isongraph init my-knowledge-graph

  # Add nodes and edges
  isongraph node add person alice name=Alice,age=30
  isongraph node add person bob name=Bob,age=25
  isongraph edge add KNOWS person:alice person:bob since=2020

  # Query the graph
  isongraph neighbors person:alice KNOWS
  isongraph path person:alice person:bob

  # Export to different formats
  isongraph export cypher > graph.cypher
  isongraph export mermaid > graph.md

  # Start interactive mode
  isongraph repl
'''
    )

    parser.add_argument('-v', '--version', action='version', version=f'isongraph v{VERSION}')
    parser.add_argument('-f', '--file', default=DEFAULT_GRAPH_FILE,
                        help=f'Graph file to use (default: {DEFAULT_GRAPH_FILE})')
    parser.add_argument('--json', action='store_true', help='Output as JSON where applicable')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')

    subparsers = parser.add_subparsers(dest='command', title='commands')

    # Init command
    init_parser = subparsers.add_parser('init', help='Create a new graph file')
    init_parser.add_argument('name', nargs='?', help='Graph name')
    init_parser.add_argument('--sample', action='store_true', help='Add sample data')
    init_parser.add_argument('--force', action='store_true', help='Overwrite existing file')

    # Info command
    subparsers.add_parser('info', help='Display graph statistics')

    # Validate command
    subparsers.add_parser('validate', help='Validate graph structure')

    # Node command
    node_parser = subparsers.add_parser('node', help='Node operations')
    node_subparsers = node_parser.add_subparsers(dest='node_command', title='node commands')

    node_add = node_subparsers.add_parser('add', help='Add a node')
    node_add.add_argument('type', help='Node type')
    node_add.add_argument('id', help='Node ID')
    node_add.add_argument('props', nargs='?', help='Properties (key=value,key2=value2 or JSON)')

    node_get = node_subparsers.add_parser('get', help='Get a node')
    node_get.add_argument('ref', help='Node reference (type:id)')

    node_list = node_subparsers.add_parser('list', help='List nodes')
    node_list.add_argument('type', nargs='?', help='Filter by type')
    node_list.add_argument('--limit', type=int, default=50, help='Maximum nodes to show')

    node_update = node_subparsers.add_parser('update', help='Update node properties')
    node_update.add_argument('ref', help='Node reference (type:id)')
    node_update.add_argument('props', help='Properties (key=value,key2=value2 or JSON)')

    node_remove = node_subparsers.add_parser('remove', help='Remove a node')
    node_remove.add_argument('ref', help='Node reference (type:id)')

    node_subparsers.add_parser('types', help='List all node types')

    # Edge command
    edge_parser = subparsers.add_parser('edge', help='Edge operations')
    edge_subparsers = edge_parser.add_subparsers(dest='edge_command', title='edge commands')

    edge_add = edge_subparsers.add_parser('add', help='Add an edge')
    edge_add.add_argument('rel_type', help='Relationship type')
    edge_add.add_argument('source', help='Source node reference (type:id)')
    edge_add.add_argument('target', help='Target node reference (type:id)')
    edge_add.add_argument('props', nargs='?', help='Properties (key=value,key2=value2 or JSON)')

    edge_get = edge_subparsers.add_parser('get', help='Get an edge')
    edge_get.add_argument('rel_type', help='Relationship type')
    edge_get.add_argument('source', help='Source node reference (type:id)')
    edge_get.add_argument('target', help='Target node reference (type:id)')

    edge_list = edge_subparsers.add_parser('list', help='List edges')
    edge_list.add_argument('rel_type', nargs='?', help='Filter by relationship type')
    edge_list.add_argument('--limit', type=int, default=50, help='Maximum edges to show')

    edge_remove = edge_subparsers.add_parser('remove', help='Remove an edge')
    edge_remove.add_argument('rel_type', help='Relationship type')
    edge_remove.add_argument('source', help='Source node reference (type:id)')
    edge_remove.add_argument('target', help='Target node reference (type:id)')

    edge_subparsers.add_parser('types', help='List all edge types')

    # Query command
    query_parser = subparsers.add_parser('query', help='Execute a graph query pattern')
    query_parser.add_argument('pattern', help='Query pattern')

    # Neighbors command
    neighbors_parser = subparsers.add_parser('neighbors', help='Get neighbors of a node')
    neighbors_parser.add_argument('node', help='Node reference (type:id)')
    neighbors_parser.add_argument('rel_type', nargs='?', help='Filter by relationship type')
    neighbors_parser.add_argument('--direction', choices=['in', 'out', 'both'], default='out',
                                  help='Direction (default: out)')

    # Path command
    path_parser = subparsers.add_parser('path', help='Find shortest path between nodes')
    path_parser.add_argument('from_node', help='Source node reference (type:id)')
    path_parser.add_argument('to_node', help='Target node reference (type:id)')
    path_parser.add_argument('rel_type', nargs='?', help='Filter by relationship type')
    path_parser.add_argument('--max-hops', type=int, default=10, help='Maximum path length')

    # Paths command
    paths_parser = subparsers.add_parser('paths', help='Find all paths between nodes')
    paths_parser.add_argument('from_node', help='Source node reference (type:id)')
    paths_parser.add_argument('to_node', help='Target node reference (type:id)')
    paths_parser.add_argument('rel_type', nargs='?', help='Filter by relationship type')
    paths_parser.add_argument('--max-hops', type=int, default=5, help='Maximum path length')

    # Export command
    export_parser = subparsers.add_parser('export', help='Export to various formats')
    export_parser.add_argument('format', help='Export format')
    export_parser.add_argument('-o', '--output', help='Output file')
    export_parser.add_argument('--merge', action='store_true', help='Use MERGE for Cypher')
    export_parser.add_argument('--dialect', choices=['postgres', 'mysql', 'sqlite'],
                               help='SQL dialect')
    export_parser.add_argument('--prefix', help='Table/method prefix')
    export_parser.add_argument('--drop', action='store_true', help='Include DROP statements')
    export_parser.add_argument('--rdf-format', choices=['turtle', 'ntriples', 'jsonld'],
                               default='turtle', help='RDF format')
    export_parser.add_argument('--rankdir', choices=['TB', 'LR', 'BT', 'RL'],
                               help='DOT graph direction')
    export_parser.add_argument('--flow', action='store_true', help='YAML flow style')
    export_parser.add_argument('--flat', action='store_true', help='Flat XML format')
    export_parser.add_argument('--separate', action='store_true', help='Separate CSV files')
    export_parser.add_argument('--direction', choices=['TB', 'LR'], help='Mermaid direction')
    export_parser.add_argument('--adj-format', choices=['simple', 'weighted', 'typed'],
                               help='Adjacency list format')
    export_parser.add_argument('--edge-format', choices=['simple', 'weighted', 'typed', 'full'],
                               help='Edge list format')
    export_parser.add_argument('--headers', action='store_true', help='Include headers')
    export_parser.add_argument('--single', action='store_true', help='Single JSON-RPC request')
    export_parser.add_argument('--method', help='JSON-RPC method name')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import from various formats')
    import_parser.add_argument('format', help='Import format')
    import_parser.add_argument('input_file', help='Input file')

    # REPL command
    subparsers.add_parser('repl', help='Start interactive REPL mode')

    return parser


def main() -> int:
    """Main entry point."""
    global NO_COLOR

    parser = create_parser()
    args = parser.parse_args()

    # Handle --no-color
    if args.no_color:
        NO_COLOR = True

    if not args.command:
        parser.print_help()
        return 0

    # Route to command handlers
    command_handlers = {
        'init': cmd_init,
        'info': cmd_info,
        'validate': cmd_validate,
        'node': cmd_node,
        'edge': cmd_edge,
        'query': cmd_query,
        'neighbors': cmd_neighbors,
        'path': cmd_path,
        'paths': cmd_paths,
        'export': cmd_export,
        'import': cmd_import,
        'repl': cmd_repl,
    }

    handler = command_handlers.get(args.command)
    if handler:
        return handler(args)
    else:
        error(f'Unknown command: {args.command}')
        parser.print_help()
        return 1


if __name__ == '__main__':
    sys.exit(main())
