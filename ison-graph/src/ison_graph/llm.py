#!/usr/bin/env python3
"""
ISONGraph LLM Module

Provides LLM-native graph operations:
- Natural language graph queries
- Automatic graph construction from text
- Graph-aware RAG (context retrieval)

Usage:
    from ison_graph import ISONGraph
    from ison_graph.llm import GraphQueryEngine, GraphBuilder, ContextRetriever

    graph = ISONGraph()

    # Natural language queries
    engine = GraphQueryEngine(graph)
    result = await engine.query("Who works at ACME?")

    # Build graph from text
    builder = GraphBuilder(graph)
    result = await builder.from_text("Alice works at ACME Corp as an engineer.")

    # Get context for RAG
    retriever = ContextRetriever(graph)
    context = retriever.get_context("Alice's projects", max_tokens=2000)
"""

from __future__ import annotations

import re
import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Optional, Set, Tuple,
    Iterator, Callable, Union, Protocol
)
from enum import Enum

from . import ISONGraph, Node, Edge, NodeRef, Direction, Path


# =============================================================================
# Token Estimation
# =============================================================================

def estimate_tokens(text: str) -> int:
    """
    Estimate token count for text.
    Uses a simple heuristic: ~4 characters per token for English text.
    """
    if not text:
        return 0
    # Rough estimate: 4 chars per token, adjusted for whitespace
    return max(1, len(text) // 4)


# =============================================================================
# LLM Provider Interface
# =============================================================================

class LLMProvider(Protocol):
    """Protocol for LLM providers"""

    async def complete(self, prompt: str) -> str:
        """Generate completion for a prompt"""
        ...


class MockLLMProvider:
    """Mock LLM provider for testing"""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        self.responses = responses or {}
        self.calls: List[str] = []

    async def complete(self, prompt: str) -> str:
        self.calls.append(prompt)
        # Return matching response or default
        for pattern, response in self.responses.items():
            if pattern.lower() in prompt.lower():
                return response
        return "No response configured"


# =============================================================================
# Query Result
# =============================================================================

@dataclass
class QueryResult:
    """Result of a graph query"""
    nodes: List[NodeRef] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    paths: List[Path] = field(default_factory=list)
    raw_query: str = ""
    parsed_pattern: str = ""
    confidence: float = 1.0


# =============================================================================
# Graph Query Engine
# =============================================================================

class GraphQueryEngine:
    """
    Natural language to graph query translator.

    Supports:
    - Pattern-based local queries (no LLM needed)
    - LLM-assisted query translation for complex queries
    """

    # Common query patterns
    PATTERNS = {
        r'who\s+knows\s+(\w+)': lambda g, m: g.edges(rel_type='KNOWS'),
        r'who\s+works\s+at\s+(\w+)': lambda g, m: g.edges(rel_type='WORKS_AT'),
        r'neighbors?\s+of\s+:?(\w+):(\w+)': lambda g, m: g.neighbors((m.group(1), m.group(2))),
        r'connected\s+to\s+:?(\w+):(\w+)': lambda g, m: g.neighbors((m.group(1), m.group(2)), direction=Direction.BOTH),
    }

    def __init__(
        self,
        graph: ISONGraph,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.graph = graph
        self.llm_provider = llm_provider

    async def query(self, natural_language: str) -> QueryResult:
        """
        Execute a natural language query on the graph.

        Args:
            natural_language: Query in plain English

        Returns:
            QueryResult with matching nodes, edges, paths
        """
        # Try local pattern matching first
        local_result = self._try_local_query(natural_language)
        if local_result:
            return local_result

        # Fall back to LLM if available
        if self.llm_provider:
            return await self._llm_query(natural_language)

        # Return empty result if no matches
        return QueryResult(raw_query=natural_language)

    def _try_local_query(self, query: str) -> Optional[QueryResult]:
        """Try to execute query using local pattern matching"""
        query_lower = query.lower().strip()

        # Check for node type queries
        for node_type in self.graph.node_types():
            if f"all {node_type}" in query_lower or f"list {node_type}" in query_lower:
                nodes = [n.ref for n in self.graph.nodes(node_type)]
                return QueryResult(
                    nodes=nodes,
                    raw_query=query,
                    parsed_pattern=f"nodes({node_type})",
                    confidence=0.9
                )

        # Check for relationship queries
        for edge_type in self.graph.edge_types():
            if edge_type.lower() in query_lower:
                edges = list(self.graph.edges(edge_type))
                nodes = list(set(
                    [e.source for e in edges] + [e.target for e in edges]
                ))
                return QueryResult(
                    nodes=nodes,
                    edges=edges,
                    raw_query=query,
                    parsed_pattern=f"edges({edge_type})",
                    confidence=0.8
                )

        # Check for property-based queries
        for node in self.graph.nodes():
            for prop_value in node.properties.values():
                if isinstance(prop_value, str) and prop_value.lower() in query_lower:
                    return QueryResult(
                        nodes=[node.ref],
                        raw_query=query,
                        parsed_pattern=f"property_match({prop_value})",
                        confidence=0.7
                    )

        return None

    async def _llm_query(self, query: str) -> QueryResult:
        """Use LLM to translate and execute query"""
        prompt = self._build_query_prompt(query)
        response = await self.llm_provider.complete(prompt)

        # Parse LLM response and execute
        # This is a simplified implementation
        return QueryResult(
            raw_query=query,
            parsed_pattern=response,
            confidence=0.6
        )

    def _build_query_prompt(self, query: str) -> str:
        """Build prompt for LLM query translation"""
        node_types = ", ".join(self.graph.node_types())
        edge_types = ", ".join(self.graph.edge_types())

        return f"""Translate this natural language query into a graph traversal pattern.

Graph schema:
- Node types: {node_types}
- Edge types: {edge_types}
- Node count: {self.graph.node_count()}
- Edge count: {self.graph.edge_count()}

Query: {query}

Return a traversal pattern in the format:
:type:id -[:REL]-> :type:id
or
nodes(type) or edges(type)
"""


# =============================================================================
# Extraction Result
# =============================================================================

@dataclass
class ExtractionResult:
    """Result of entity/relationship extraction"""
    entities: List[Dict[str, Any]] = field(default_factory=list)
    relations: List[Dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.0
    source_text: str = ""


# =============================================================================
# Graph Builder
# =============================================================================

class GraphBuilder:
    """
    Automatic graph construction from unstructured text.

    Features:
    - Entity extraction
    - Relationship detection
    - Property inference
    """

    def __init__(
        self,
        graph: ISONGraph,
        llm_provider: Optional[LLMProvider] = None
    ):
        self.graph = graph
        self.llm_provider = llm_provider

    async def from_text(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        relation_types: Optional[List[str]] = None
    ) -> ExtractionResult:
        """
        Extract entities and relationships from text and add to graph.

        Args:
            text: Unstructured text to process
            entity_types: Expected entity types (optional)
            relation_types: Expected relationship types (optional)

        Returns:
            ExtractionResult with extracted entities and relations
        """
        # Try simple extraction first
        result = self._simple_extraction(text, entity_types)

        # Use LLM for more sophisticated extraction if available
        if self.llm_provider and result.confidence < 0.5:
            result = await self._llm_extraction(text, entity_types, relation_types)

        # Add extracted entities to graph
        self._add_to_graph(result)

        return result

    def _simple_extraction(
        self,
        text: str,
        entity_types: Optional[List[str]] = None
    ) -> ExtractionResult:
        """Simple pattern-based extraction"""
        entities = []
        relations = []

        # Extract capitalized words as potential entities
        words = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', text)
        seen = set()

        for word in words:
            if word not in seen:
                seen.add(word)
                entity_type = 'entity'

                # Try to infer type from context
                if entity_types:
                    for et in entity_types:
                        if et.lower() in text.lower():
                            entity_type = et
                            break

                # Check for common patterns
                if re.search(rf'{word}\s+(Corp|Inc|LLC|Company)', text):
                    entity_type = 'company'
                elif re.search(rf'(Mr|Ms|Dr|Mrs)\.?\s+{word}', text):
                    entity_type = 'person'

                entities.append({
                    'type': entity_type,
                    'id': word.lower().replace(' ', '_'),
                    'properties': {'name': word}
                })

        # Extract relationships based on patterns
        relation_patterns = [
            (r'(\w+)\s+works\s+(?:at|for)\s+(\w+)', 'WORKS_AT'),
            (r'(\w+)\s+knows\s+(\w+)', 'KNOWS'),
            (r'(\w+)\s+manages?\s+(\w+)', 'MANAGES'),
            (r'(\w+)\s+reports?\s+to\s+(\w+)', 'REPORTS_TO'),
            (r'(\w+)\s+is\s+(?:a\s+)?(?:friend|colleague)\s+of\s+(\w+)', 'KNOWS'),
        ]

        for pattern, rel_type in relation_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                source_name = match.group(1)
                target_name = match.group(2)

                # Find corresponding entities
                source_id = source_name.lower().replace(' ', '_')
                target_id = target_name.lower().replace(' ', '_')

                relations.append({
                    'type': rel_type,
                    'source': source_id,
                    'target': target_id,
                    'properties': {}
                })

        confidence = 0.3 if entities else 0.0
        if relations:
            confidence += 0.3

        return ExtractionResult(
            entities=entities,
            relations=relations,
            confidence=confidence,
            source_text=text
        )

    async def _llm_extraction(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        relation_types: Optional[List[str]] = None
    ) -> ExtractionResult:
        """Use LLM for entity/relationship extraction"""
        prompt = self._build_extraction_prompt(text, entity_types, relation_types)
        response = await self.llm_provider.complete(prompt)

        # Parse LLM response
        # This is a simplified implementation
        return ExtractionResult(
            entities=[],
            relations=[],
            confidence=0.7,
            source_text=text
        )

    def _build_extraction_prompt(
        self,
        text: str,
        entity_types: Optional[List[str]] = None,
        relation_types: Optional[List[str]] = None
    ) -> str:
        """Build prompt for LLM extraction"""
        types_str = ", ".join(entity_types) if entity_types else "person, company, location, etc."
        rels_str = ", ".join(relation_types) if relation_types else "KNOWS, WORKS_AT, LOCATED_IN, etc."

        return f"""Extract entities and relationships from the following text.

Entity types to look for: {types_str}
Relationship types to look for: {rels_str}

Text:
\"\"\"{text}\"\"\"

Return in this format:
ENTITIES:
- type: <type>, id: <id>, name: <name>

RELATIONSHIPS:
- <source_id> -[<REL_TYPE>]-> <target_id>
"""

    def _add_to_graph(self, result: ExtractionResult) -> None:
        """Add extracted entities and relations to graph"""
        entity_map = {}

        # Add entities as nodes
        for entity in result.entities:
            node_type = entity.get('type', 'entity')
            node_id = entity.get('id')
            properties = entity.get('properties', {})

            if not self.graph.has_node(node_type, node_id):
                self.graph.add_node(node_type, node_id, **properties)

            entity_map[node_id] = (node_type, node_id)

        # Add relations as edges
        for relation in result.relations:
            rel_type = relation.get('type')
            source_id = relation.get('source')
            target_id = relation.get('target')
            properties = relation.get('properties', {})

            # Find source and target refs
            source_ref = entity_map.get(source_id)
            target_ref = entity_map.get(target_id)

            # Try to find in existing graph if not in extraction
            if not source_ref:
                for node in self.graph.nodes():
                    if node.id == source_id or node.properties.get('name', '').lower() == source_id:
                        source_ref = node.ref
                        break

            if not target_ref:
                for node in self.graph.nodes():
                    if node.id == target_id or node.properties.get('name', '').lower() == target_id:
                        target_ref = node.ref
                        break

            if source_ref and target_ref:
                if not self.graph.has_edge(rel_type, source_ref, target_ref):
                    try:
                        self.graph.add_edge(rel_type, source_ref, target_ref, **properties)
                    except Exception:
                        pass  # Skip if edge can't be added


# =============================================================================
# Retrieved Context
# =============================================================================

@dataclass
class RetrievedContext:
    """Context retrieved for RAG applications"""
    ison: str  # ISON-formatted context
    nodes: List[Node] = field(default_factory=list)
    edges: List[Edge] = field(default_factory=list)
    token_estimate: int = 0
    depth: int = 0


@dataclass
class ContextOptions:
    """Options for context retrieval"""
    max_tokens: int = 2000
    max_depth: int = 2
    include_edges: bool = True
    include_properties: bool = True


# =============================================================================
# Context Retriever
# =============================================================================

class ContextRetriever:
    """
    Graph-aware context retrieval for RAG applications.

    Features:
    - Relationship-aware context extraction
    - Token budget management
    - Progressive detail levels
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph

    def get_context(
        self,
        query: str,
        options: Optional[ContextOptions] = None
    ) -> RetrievedContext:
        """
        Get context relevant to a query.

        Args:
            query: Query string to find relevant context for
            options: Context retrieval options

        Returns:
            RetrievedContext with ISON-formatted graph data
        """
        if options is None:
            options = ContextOptions()

        # Find seed nodes based on query
        seed_nodes = self._find_seed_nodes(query)

        if not seed_nodes:
            # Return full graph if no specific matches, within token budget
            return self._get_full_context(options)

        # Expand from seed nodes
        relevant_nodes: Set[NodeRef] = set()
        relevant_edges: List[Edge] = []

        for seed in seed_nodes:
            self._expand_context(
                seed,
                relevant_nodes,
                relevant_edges,
                options.max_depth
            )

        # Build context within token budget
        return self._build_context(
            list(relevant_nodes),
            relevant_edges,
            options
        )

    def get_progressive_context(
        self,
        query: str,
        levels: List[int]
    ) -> List[RetrievedContext]:
        """
        Get context at multiple detail levels.

        Args:
            query: Query string
            levels: List of token budgets for each level

        Returns:
            List of RetrievedContext at increasing detail levels
        """
        results = []

        for max_tokens in sorted(levels):
            options = ContextOptions(
                max_tokens=max_tokens,
                max_depth=1 if max_tokens < 500 else 2 if max_tokens < 1500 else 3
            )
            context = self.get_context(query, options)
            results.append(context)

        return results

    def _find_seed_nodes(self, query: str) -> List[NodeRef]:
        """Find nodes relevant to query"""
        seeds = []
        query_lower = query.lower()
        query_words = set(query_lower.split())

        for node in self.graph.nodes():
            score = 0

            # Check node type
            if node.type.lower() in query_lower:
                score += 1

            # Check properties
            for key, value in node.properties.items():
                if isinstance(value, str):
                    value_lower = value.lower()
                    if value_lower in query_lower:
                        score += 2
                    elif any(w in value_lower for w in query_words):
                        score += 1

            if score > 0:
                seeds.append((score, node.ref))

        # Sort by score and return top nodes
        seeds.sort(key=lambda x: -x[0])
        return [ref for _, ref in seeds[:10]]

    def _expand_context(
        self,
        node_ref: NodeRef,
        relevant_nodes: Set[NodeRef],
        relevant_edges: List[Edge],
        remaining_depth: int
    ) -> None:
        """Expand context from a seed node"""
        if remaining_depth <= 0 or node_ref in relevant_nodes:
            return

        relevant_nodes.add(node_ref)

        # Add connected edges and nodes
        for edge in self.graph.edges(source=node_ref):
            if edge not in relevant_edges:
                relevant_edges.append(edge)
            self._expand_context(
                edge.target,
                relevant_nodes,
                relevant_edges,
                remaining_depth - 1
            )

        for edge in self.graph.edges(target=node_ref):
            if edge not in relevant_edges:
                relevant_edges.append(edge)
            self._expand_context(
                edge.source,
                relevant_nodes,
                relevant_edges,
                remaining_depth - 1
            )

    def _get_full_context(self, options: ContextOptions) -> RetrievedContext:
        """Get full graph context within token budget"""
        nodes = list(self.graph.nodes())
        edges = list(self.graph.edges())

        return self._build_context(
            [n.ref for n in nodes],
            edges,
            options
        )

    def _build_context(
        self,
        node_refs: List[NodeRef],
        edges: List[Edge],
        options: ContextOptions
    ) -> RetrievedContext:
        """Build ISON context within token budget"""
        # Get actual nodes
        nodes = []
        for ref in node_refs:
            try:
                nodes.append(self.graph.get_node_by_ref(ref))
            except Exception:
                pass

        # Filter edges to only those connecting our nodes
        node_set = set(node_refs)
        filtered_edges = [
            e for e in edges
            if e.source in node_set and e.target in node_set
        ] if options.include_edges else []

        # Build ISON string
        ison_parts = []
        current_tokens = 0
        included_nodes = []
        included_edges = []

        # Group nodes by type
        nodes_by_type: Dict[str, List[Node]] = {}
        for node in nodes:
            if node.type not in nodes_by_type:
                nodes_by_type[node.type] = []
            nodes_by_type[node.type].append(node)

        # Build node blocks
        for node_type, type_nodes in nodes_by_type.items():
            block_lines = [f"nodes.{node_type}"]

            # Collect property keys
            prop_keys = set()
            for node in type_nodes:
                prop_keys.update(node.properties.keys())
            prop_keys = sorted(prop_keys)

            if options.include_properties and prop_keys:
                block_lines.append("id " + " ".join(prop_keys))
            else:
                block_lines.append("id")

            for node in type_nodes:
                if options.include_properties:
                    values = [str(node.id)]
                    for key in prop_keys:
                        val = node.properties.get(key, "")
                        values.append(self._format_value(val))
                    line = " ".join(values)
                else:
                    line = str(node.id)

                line_tokens = estimate_tokens(line)
                if current_tokens + line_tokens > options.max_tokens:
                    break

                block_lines.append(line)
                included_nodes.append(node)
                current_tokens += line_tokens

            if len(block_lines) > 2:  # Has actual data
                ison_parts.append("\n".join(block_lines))

        # Build edge blocks
        if options.include_edges and filtered_edges:
            edges_by_type: Dict[str, List[Edge]] = {}
            for edge in filtered_edges:
                if edge.rel_type not in edges_by_type:
                    edges_by_type[edge.rel_type] = []
                edges_by_type[edge.rel_type].append(edge)

            for rel_type, type_edges in edges_by_type.items():
                block_lines = [f"edges.{rel_type}"]

                # Collect property keys
                prop_keys = set()
                for edge in type_edges:
                    prop_keys.update(edge.properties.keys())
                prop_keys = sorted(prop_keys)

                if options.include_properties and prop_keys:
                    block_lines.append("source target " + " ".join(prop_keys))
                else:
                    block_lines.append("source target")

                for edge in type_edges:
                    source_ref = f":{edge.source[0]}:{edge.source[1]}"
                    target_ref = f":{edge.target[0]}:{edge.target[1]}"

                    if options.include_properties:
                        values = [source_ref, target_ref]
                        for key in prop_keys:
                            val = edge.properties.get(key, "")
                            values.append(self._format_value(val))
                        line = " ".join(values)
                    else:
                        line = f"{source_ref} {target_ref}"

                    line_tokens = estimate_tokens(line)
                    if current_tokens + line_tokens > options.max_tokens:
                        break

                    block_lines.append(line)
                    included_edges.append(edge)
                    current_tokens += line_tokens

                if len(block_lines) > 2:
                    ison_parts.append("\n".join(block_lines))

        ison = "\n\n".join(ison_parts)

        return RetrievedContext(
            ison=ison,
            nodes=included_nodes,
            edges=included_edges,
            token_estimate=current_tokens,
            depth=options.max_depth
        )

    def _format_value(self, value: Any) -> str:
        """Format a value for ISON output"""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            if " " in value or '"' in value:
                escaped = value.replace('"', '\\"')
                return f'"{escaped}"'
            return value
        return str(value)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Functions
    'estimate_tokens',

    # Providers
    'LLMProvider',
    'MockLLMProvider',

    # Query Engine
    'GraphQueryEngine',
    'QueryResult',

    # Graph Builder
    'GraphBuilder',
    'ExtractionResult',

    # Context Retriever
    'ContextRetriever',
    'RetrievedContext',
    'ContextOptions',
]
