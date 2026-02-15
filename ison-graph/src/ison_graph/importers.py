#!/usr/bin/env python3
"""
ISONGraph Importers Module

Provides import functionality from various formats:
- HTML: Convert HTML DOM to graph structure
- JSON: Import from various JSON formats
- CSV: Import from CSV files
- Markdown: Extract structure from Markdown

Usage:
    from ison_graph import ISONGraph
    from ison_graph.importers import (
        import_from_html,
        import_from_json,
        import_from_csv,
        HTMLImportOptions
    )

    # Import HTML to graph
    graph = import_from_html(html_string)

    # Import with options
    graph = import_from_html(
        html_string,
        options=HTMLImportOptions(
            extract_links=True,
            extract_text=True,
            include_attributes=True
        )
    )
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse

from . import ISONGraph, NodeRef


# =============================================================================
# HTML Import Options
# =============================================================================

@dataclass
class HTMLImportOptions:
    """Options for HTML to graph import"""

    # Structure options
    include_attributes: bool = True
    include_text: bool = True
    include_comments: bool = False
    include_doctype: bool = False

    # Element filtering
    skip_tags: Set[str] = field(default_factory=lambda: {
        'script', 'style', 'noscript', 'svg', 'path'
    })
    include_only_tags: Optional[Set[str]] = None

    # Text handling
    collapse_whitespace: bool = True
    min_text_length: int = 1
    max_text_length: int = 1000

    # Link extraction
    extract_links: bool = True
    extract_images: bool = True
    base_url: Optional[str] = None

    # ID generation
    id_prefix: str = "el_"
    use_element_id: bool = True  # Use HTML id attribute if available

    # Semantic grouping
    semantic_tags: Set[str] = field(default_factory=lambda: {
        'article', 'section', 'nav', 'aside', 'header', 'footer',
        'main', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'ul', 'ol',
        'li', 'table', 'tr', 'td', 'th', 'form', 'input', 'button',
        'a', 'img', 'div', 'span', 'figure', 'figcaption'
    })
    only_semantic: bool = False  # Only include semantic tags


@dataclass
class HTMLImportResult:
    """Result of HTML import"""
    graph: ISONGraph
    root_id: str
    element_count: int
    link_count: int
    image_count: int
    text_nodes: int
    errors: List[str] = field(default_factory=list)


# =============================================================================
# HTML Parser
# =============================================================================

class ISONGraphHTMLParser(HTMLParser):
    """HTML parser that builds an ISONGraph"""

    def __init__(self, options: HTMLImportOptions):
        super().__init__()
        self.options = options
        self.graph = ISONGraph("html_document")

        # State tracking
        self._id_counter = 0
        self._stack: List[str] = []  # Stack of node IDs
        self._root_id: Optional[str] = None
        self._links: List[Dict[str, str]] = []
        self._images: List[Dict[str, str]] = []
        self._text_nodes = 0
        self._errors: List[str] = []

    def _generate_id(self, tag: str, attrs: Dict[str, str]) -> str:
        """Generate a unique ID for an element"""
        # Use HTML id attribute if available and option enabled
        if self.options.use_element_id and 'id' in attrs:
            html_id = attrs['id']
            # Ensure uniqueness
            base_id = f"{self.options.id_prefix}{html_id}"
            if not self.graph.has_node('element', base_id):
                return base_id

        # Generate sequential ID
        self._id_counter += 1
        return f"{self.options.id_prefix}{self._id_counter}"

    def _should_include_tag(self, tag: str) -> bool:
        """Check if tag should be included"""
        tag_lower = tag.lower()

        # Skip excluded tags
        if tag_lower in self.options.skip_tags:
            return False

        # Only include specific tags if configured
        if self.options.include_only_tags:
            return tag_lower in self.options.include_only_tags

        # Only semantic tags if configured
        if self.options.only_semantic:
            return tag_lower in self.options.semantic_tags

        return True

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text content"""
        if self.options.collapse_whitespace:
            text = re.sub(r'\s+', ' ', text).strip()

        if len(text) > self.options.max_text_length:
            text = text[:self.options.max_text_length] + '...'

        return text

    def _extract_url(self, url: str) -> str:
        """Extract and normalize URL"""
        if self.options.base_url and not urlparse(url).netloc:
            return urljoin(self.options.base_url, url)
        return url

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        """Handle opening tag"""
        if not self._should_include_tag(tag):
            # Push placeholder to maintain stack consistency
            self._stack.append(None)
            return

        # Convert attrs to dict
        attrs_dict = {k: v or '' for k, v in attrs}

        # Generate node ID
        node_id = self._generate_id(tag, attrs_dict)

        # Build node properties
        props: Dict[str, Any] = {'tag': tag}

        if self.options.include_attributes:
            for key, value in attrs_dict.items():
                if key not in ('id',):  # Don't duplicate id
                    props[f'attr_{key}'] = value

        # Extract links
        if self.options.extract_links and tag.lower() == 'a' and 'href' in attrs_dict:
            href = self._extract_url(attrs_dict['href'])
            props['href'] = href
            self._links.append({
                'element_id': node_id,
                'url': href,
                'text': ''  # Will be filled when text is encountered
            })

        # Extract images
        if self.options.extract_images and tag.lower() == 'img':
            if 'src' in attrs_dict:
                src = self._extract_url(attrs_dict['src'])
                props['src'] = src
                self._images.append({
                    'element_id': node_id,
                    'url': src,
                    'alt': attrs_dict.get('alt', '')
                })

        # Add node to graph
        try:
            self.graph.add_node('element', node_id, **props)
        except Exception as e:
            self._errors.append(f"Error adding node {node_id}: {e}")
            self._stack.append(None)
            return

        # Set root if first element
        if self._root_id is None:
            self._root_id = node_id

        # Connect to parent
        if self._stack:
            parent_id = self._stack[-1]
            if parent_id is not None:
                try:
                    self.graph.add_edge(
                        'CONTAINS',
                        ('element', parent_id),
                        ('element', node_id)
                    )
                except Exception as e:
                    self._errors.append(f"Error adding edge: {e}")

        # Push to stack
        self._stack.append(node_id)

    def handle_endtag(self, tag: str):
        """Handle closing tag"""
        if self._stack:
            self._stack.pop()

    def handle_data(self, data: str):
        """Handle text content"""
        if not self.options.include_text:
            return

        text = self._clean_text(data)
        if len(text) < self.options.min_text_length:
            return

        # Add text to current element
        if self._stack:
            current_id = self._stack[-1]
            if current_id is not None:
                try:
                    node = self.graph.get_node('element', current_id)
                    existing_text = node.properties.get('text', '')
                    if existing_text:
                        text = existing_text + ' ' + text
                    self.graph.update_node('element', current_id, text=text)
                    self._text_nodes += 1

                    # Update link text if this is an anchor
                    if node.properties.get('tag') == 'a':
                        for link in self._links:
                            if link['element_id'] == current_id:
                                link['text'] = text
                                break
                except Exception as e:
                    self._errors.append(f"Error updating text: {e}")

    def handle_comment(self, data: str):
        """Handle HTML comments"""
        if not self.options.include_comments:
            return

        if self._stack:
            current_id = self._stack[-1]
            if current_id is not None:
                self._id_counter += 1
                comment_id = f"comment_{self._id_counter}"
                try:
                    self.graph.add_node('comment', comment_id, content=data.strip())
                    self.graph.add_edge(
                        'HAS_COMMENT',
                        ('element', current_id),
                        ('comment', comment_id)
                    )
                except Exception as e:
                    self._errors.append(f"Error adding comment: {e}")

    def handle_decl(self, decl: str):
        """Handle DOCTYPE declaration"""
        if self.options.include_doctype:
            try:
                self.graph.add_node('doctype', 'doctype', declaration=decl)
            except Exception as e:
                self._errors.append(f"Error adding doctype: {e}")

    def get_result(self) -> HTMLImportResult:
        """Get the import result"""
        return HTMLImportResult(
            graph=self.graph,
            root_id=self._root_id or '',
            element_count=self.graph.node_count('element') if self.graph.has_node else 0,
            link_count=len(self._links),
            image_count=len(self._images),
            text_nodes=self._text_nodes,
            errors=self._errors
        )

    def get_links(self) -> List[Dict[str, str]]:
        """Get extracted links"""
        return self._links

    def get_images(self) -> List[Dict[str, str]]:
        """Get extracted images"""
        return self._images


# =============================================================================
# Import Functions
# =============================================================================

def import_from_html(
    html: str,
    options: Optional[HTMLImportOptions] = None,
    graph_name: str = "html_document"
) -> ISONGraph:
    """
    Import HTML string to ISONGraph.

    Converts HTML DOM structure into a graph where:
    - Each HTML element becomes a node of type 'element'
    - Parent-child relationships become CONTAINS edges
    - Attributes become node properties (prefixed with 'attr_')
    - Text content becomes 'text' property
    - Links become nodes with 'href' property
    - Images become nodes with 'src' property

    Args:
        html: HTML string to parse
        options: Import options
        graph_name: Name for the resulting graph

    Returns:
        ISONGraph with DOM structure

    Example:
        >>> html = '''
        ... <html>
        ...   <body>
        ...     <h1>Title</h1>
        ...     <p>Hello <a href="/about">world</a></p>
        ...   </body>
        ... </html>
        ... '''
        >>> graph = import_from_html(html)
        >>> print(graph.to_ison())
    """
    options = options or HTMLImportOptions()

    parser = ISONGraphHTMLParser(options)
    parser.graph.name = graph_name

    try:
        parser.feed(html)
    except Exception as e:
        parser._errors.append(f"Parse error: {e}")

    return parser.graph


def import_from_html_file(
    filepath: str,
    options: Optional[HTMLImportOptions] = None,
    encoding: str = 'utf-8'
) -> ISONGraph:
    """
    Import HTML file to ISONGraph.

    Args:
        filepath: Path to HTML file
        options: Import options
        encoding: File encoding

    Returns:
        ISONGraph with DOM structure
    """
    with open(filepath, 'r', encoding=encoding) as f:
        html = f.read()

    options = options or HTMLImportOptions()

    # Set base URL from filepath if not provided
    if not options.base_url:
        options.base_url = f"file://{filepath}"

    return import_from_html(html, options)


def import_from_html_detailed(
    html: str,
    options: Optional[HTMLImportOptions] = None,
    graph_name: str = "html_document"
) -> HTMLImportResult:
    """
    Import HTML with detailed result including statistics.

    Args:
        html: HTML string to parse
        options: Import options
        graph_name: Name for the resulting graph

    Returns:
        HTMLImportResult with graph and statistics
    """
    options = options or HTMLImportOptions()

    parser = ISONGraphHTMLParser(options)
    parser.graph.name = graph_name

    try:
        parser.feed(html)
    except Exception as e:
        parser._errors.append(f"Parse error: {e}")

    return parser.get_result()


def extract_links_from_html(
    html: str,
    base_url: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Extract all links from HTML.

    Args:
        html: HTML string
        base_url: Base URL for resolving relative links

    Returns:
        List of link dictionaries with 'url', 'text', 'element_id'
    """
    options = HTMLImportOptions(
        extract_links=True,
        include_text=True,
        base_url=base_url,
        skip_tags={'script', 'style', 'noscript'},
        include_attributes=False
    )

    parser = ISONGraphHTMLParser(options)
    parser.feed(html)

    return parser.get_links()


def extract_images_from_html(
    html: str,
    base_url: Optional[str] = None
) -> List[Dict[str, str]]:
    """
    Extract all images from HTML.

    Args:
        html: HTML string
        base_url: Base URL for resolving relative image sources

    Returns:
        List of image dictionaries with 'url', 'alt', 'element_id'
    """
    options = HTMLImportOptions(
        extract_images=True,
        include_text=False,
        base_url=base_url,
        skip_tags={'script', 'style', 'noscript'},
        include_attributes=False
    )

    parser = ISONGraphHTMLParser(options)
    parser.feed(html)

    return parser.get_images()


def html_to_link_graph(
    html: str,
    base_url: Optional[str] = None,
    page_id: str = "page"
) -> ISONGraph:
    """
    Create a graph of links from HTML.

    Creates a graph where:
    - The source page is a 'page' node
    - Each link becomes a 'link' node
    - LINKS_TO edges connect page to links

    Args:
        html: HTML string
        base_url: Base URL for the page
        page_id: ID for the source page node

    Returns:
        ISONGraph with link structure
    """
    links = extract_links_from_html(html, base_url)

    graph = ISONGraph("link_graph")
    graph.add_node('page', page_id, url=base_url or '')

    for i, link in enumerate(links):
        link_id = f"link_{i}"
        graph.add_node('link', link_id,
                      url=link['url'],
                      text=link['text'])
        graph.add_edge('LINKS_TO', ('page', page_id), ('link', link_id))

    return graph


def html_to_semantic_graph(
    html: str,
    options: Optional[HTMLImportOptions] = None
) -> ISONGraph:
    """
    Create a semantic structure graph from HTML.

    Focuses on semantic HTML elements (article, section, nav, etc.)
    and creates a graph representing the document structure.

    Args:
        html: HTML string
        options: Import options (only_semantic will be set to True)

    Returns:
        ISONGraph with semantic structure
    """
    options = options or HTMLImportOptions()
    options.only_semantic = True
    options.include_text = True
    options.collapse_whitespace = True

    return import_from_html(html, options, "semantic_structure")


# =============================================================================
# JSON Import Functions
# =============================================================================

def import_from_json(
    json_data: Union[str, Dict, List],
    graph_name: str = "imported"
) -> ISONGraph:
    """
    Import from JSON format.

    Supports multiple JSON formats:
    - ISONGraph JSON format (with nodes/edges arrays)
    - D3 format (with nodes/links arrays)
    - Adjacency list format
    - Generic nested JSON

    Args:
        json_data: JSON string or parsed data
        graph_name: Name for the graph

    Returns:
        ISONGraph
    """
    if isinstance(json_data, str):
        data = json.loads(json_data)
    else:
        data = json_data

    graph = ISONGraph(graph_name)

    # Detect format and import
    if isinstance(data, dict):
        if 'nodes' in data and 'edges' in data:
            # ISONGraph format
            _import_isongraph_json(graph, data)
        elif 'nodes' in data and 'links' in data:
            # D3 format
            _import_d3_json(graph, data)
        elif all(isinstance(v, list) for v in data.values()):
            # Adjacency list format
            _import_adjacency_json(graph, data)
        else:
            # Generic nested JSON
            _import_nested_json(graph, data)
    elif isinstance(data, list):
        # Array of objects
        _import_array_json(graph, data)

    return graph


def _import_isongraph_json(graph: ISONGraph, data: Dict) -> None:
    """Import ISONGraph JSON format"""
    for node in data.get('nodes', []):
        node_type = node.get('type', 'node')
        node_id = node.get('id', str(len(list(graph.nodes()))))
        props = node.get('properties', {})
        graph.add_node(node_type, node_id, **props)

    for edge in data.get('edges', []):
        rel_type = edge.get('type', 'RELATED')
        source = edge.get('source', {})
        target = edge.get('target', {})
        props = edge.get('properties', {})

        if isinstance(source, dict):
            source_ref = (source.get('type', 'node'), source.get('id'))
        else:
            parts = str(source).split(':')
            source_ref = (parts[0], parts[1]) if len(parts) > 1 else ('node', source)

        if isinstance(target, dict):
            target_ref = (target.get('type', 'node'), target.get('id'))
        else:
            parts = str(target).split(':')
            target_ref = (parts[0], parts[1]) if len(parts) > 1 else ('node', target)

        graph.add_edge(rel_type, source_ref, target_ref, **props)


def _import_d3_json(graph: ISONGraph, data: Dict) -> None:
    """Import D3 JSON format"""
    for node in data.get('nodes', []):
        node_id = node.get('id', str(len(list(graph.nodes()))))
        node_type = node.get('group', 'node')
        props = {k: v for k, v in node.items() if k not in ('id', 'group')}
        graph.add_node(node_type, node_id, **props)

    for link in data.get('links', []):
        source = link.get('source')
        target = link.get('target')
        rel_type = link.get('type', 'LINKED')

        # D3 can have string IDs or node objects
        if isinstance(source, dict):
            source = source.get('id')
        if isinstance(target, dict):
            target = target.get('id')

        graph.add_edge(rel_type, ('node', source), ('node', target))


def _import_adjacency_json(graph: ISONGraph, data: Dict) -> None:
    """Import adjacency list JSON format"""
    for source, targets in data.items():
        if not graph.has_node('node', source):
            graph.add_node('node', source)

        for target in targets:
            if not graph.has_node('node', target):
                graph.add_node('node', target)
            graph.add_edge('CONNECTED', ('node', source), ('node', target))


def _import_nested_json(graph: ISONGraph, data: Dict, parent_id: Optional[str] = None, counter: List[int] = None) -> None:
    """Import generic nested JSON"""
    if counter is None:
        counter = [0]

    counter[0] += 1
    node_id = f"obj_{counter[0]}"

    # Separate scalar and nested values
    props = {}
    children = []

    for key, value in data.items():
        if isinstance(value, dict):
            children.append((key, value))
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    children.append((f"{key}[{i}]", item))
                else:
                    props[f"{key}_{i}"] = str(item)
        else:
            props[key] = value

    graph.add_node('object', node_id, **props)

    if parent_id:
        graph.add_edge('CONTAINS', ('object', parent_id), ('object', node_id))

    for key, child in children:
        _import_nested_json(graph, child, node_id, counter)


def _import_array_json(graph: ISONGraph, data: List) -> None:
    """Import array of objects JSON"""
    for i, item in enumerate(data):
        if isinstance(item, dict):
            node_id = item.get('id', str(i))
            node_type = item.get('type', 'item')
            props = {k: v for k, v in item.items() if k not in ('id', 'type') and not isinstance(v, (dict, list))}
            graph.add_node(node_type, node_id, **props)


# =============================================================================
# CSV Import Functions
# =============================================================================

def import_from_csv(
    nodes_csv: str,
    edges_csv: Optional[str] = None,
    delimiter: str = ',',
    type_column: str = '_type',
    id_column: str = '_id',
    source_column: str = '_source',
    target_column: str = '_target',
    graph_name: str = "imported"
) -> ISONGraph:
    """
    Import from CSV format.

    Args:
        nodes_csv: CSV string with nodes
        edges_csv: Optional CSV string with edges
        delimiter: Field delimiter
        type_column: Column name for node type
        id_column: Column name for node ID
        source_column: Column name for edge source
        target_column: Column name for edge target
        graph_name: Name for the graph

    Returns:
        ISONGraph
    """
    graph = ISONGraph(graph_name)

    # Parse nodes
    lines = nodes_csv.strip().split('\n')
    if lines:
        headers = lines[0].split(delimiter)

        for line in lines[1:]:
            values = line.split(delimiter)
            row = dict(zip(headers, values))

            node_type = row.pop(type_column, 'node')
            node_id = row.pop(id_column, str(graph.node_count()))

            # Clean property values
            props = {k: v.strip('"') for k, v in row.items() if v}

            graph.add_node(node_type, node_id, **props)

    # Parse edges
    if edges_csv:
        lines = edges_csv.strip().split('\n')
        if lines:
            headers = lines[0].split(delimiter)

            for line in lines[1:]:
                values = line.split(delimiter)
                row = dict(zip(headers, values))

                rel_type = row.pop(type_column, 'RELATED')
                source = row.pop(source_column, '')
                target = row.pop(target_column, '')

                if source and target:
                    # Parse source/target (format: "type:id")
                    source_parts = source.split(':')
                    target_parts = target.split(':')

                    source_ref = (source_parts[0], source_parts[1]) if len(source_parts) > 1 else ('node', source)
                    target_ref = (target_parts[0], target_parts[1]) if len(target_parts) > 1 else ('node', target)

                    props = {k: v.strip('"') for k, v in row.items() if v}
                    graph.add_edge(rel_type, source_ref, target_ref, **props)

    return graph


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Options and Results
    'HTMLImportOptions',
    'HTMLImportResult',

    # HTML Import
    'import_from_html',
    'import_from_html_file',
    'import_from_html_detailed',
    'extract_links_from_html',
    'extract_images_from_html',
    'html_to_link_graph',
    'html_to_semantic_graph',

    # JSON Import
    'import_from_json',

    # CSV Import
    'import_from_csv',
]
