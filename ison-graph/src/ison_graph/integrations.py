#!/usr/bin/env python3
"""
ISONGraph Integrations Module

Provides framework adapters for popular AI/ML frameworks:
- LangChain integration
- LlamaIndex integration
- AutoGen integration
- Prompt templates for LLM applications

Usage:
    from ison_graph import ISONGraph
    from ison_graph.integrations import (
        create_langchain_adapter,
        create_llamaindex_adapter,
        create_autogen_adapter,
        PromptTemplates
    )

    graph = ISONGraph()

    # Create framework-specific adapters
    langchain_store = create_langchain_adapter(graph)
    llama_store = create_llamaindex_adapter(graph)
    autogen_memory = create_autogen_adapter(graph)

    # Use optimized prompt templates
    prompt = PromptTemplates.graph_context(graph, "Find related entities")
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Optional, Set, Tuple,
    Callable, Union, Protocol, runtime_checkable
)
from collections import defaultdict

from . import ISONGraph, Node, Edge, NodeRef, Direction
from .llm import ContextRetriever, RetrievedContext, ContextOptions


# =============================================================================
# Common Interfaces
# =============================================================================

@runtime_checkable
class GraphAdapter(Protocol):
    """Base interface for all framework adapters"""

    def get_graph(self) -> ISONGraph:
        """Get the underlying graph"""
        ...

    def add_node(
        self,
        node_type: str,
        node_id: Union[int, str],
        **properties: Any
    ) -> None:
        """Add a node to the graph"""
        ...

    def add_edge(
        self,
        rel_type: str,
        source: NodeRef,
        target: NodeRef,
        **properties: Any
    ) -> None:
        """Add an edge to the graph"""
        ...

    async def query(self, text: str) -> Any:
        """Query the graph with natural language"""
        ...

    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        """Get context for a prompt"""
        ...

    def serialize(self) -> str:
        """Serialize to token-efficient format"""
        ...


@dataclass
class GraphDocument:
    """Document interface for RAG systems"""
    id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@runtime_checkable
class GraphMemory(Protocol):
    """Memory interface for agent systems"""

    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Store a memory"""
        ...

    def get(self, query: str, k: int = 5) -> List[GraphDocument]:
        """Retrieve relevant memories"""
        ...

    def clear(self) -> None:
        """Clear all memories"""
        ...

    def size(self) -> int:
        """Get memory count"""
        ...


@runtime_checkable
class GraphRetriever(Protocol):
    """Retriever interface for RAG"""

    async def retrieve(self, query: str, k: int = 5) -> List[GraphDocument]:
        """Retrieve relevant documents"""
        ...

    def get_config(self) -> Dict[str, Any]:
        """Get retriever configuration"""
        ...


# =============================================================================
# LangChain Adapter
# =============================================================================

class LangChainAdapter:
    """
    Adapter for LangChain integration.

    Compatible with:
    - LangChain GraphStore interface
    - LangChain Memory interface
    - LangChain Retriever interface
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph
        self.context_retriever = ContextRetriever(graph)
        self._memories: Dict[str, GraphDocument] = {}
        self._id_counter = 0

    def get_graph(self) -> ISONGraph:
        return self.graph

    def add_node(
        self,
        node_type: str,
        node_id: Union[int, str],
        **properties: Any
    ) -> None:
        if not self.graph.has_node(node_type, node_id):
            self.graph.add_node(node_type, node_id, **properties)
        else:
            self.graph.update_node(node_type, node_id, **properties)

    def add_edge(
        self,
        rel_type: str,
        source: NodeRef,
        target: NodeRef,
        **properties: Any
    ) -> None:
        if not self.graph.has_edge(rel_type, source, target):
            self.graph.add_edge(rel_type, source, target, **properties)

    async def query(self, text: str) -> List[NodeRef]:
        """Simple pattern-based query"""
        words = text.lower().split()
        results = []

        for node in self.graph.nodes():
            node_str = json.dumps(node.properties).lower()
            if any(w in node_str for w in words):
                results.append(node.ref)

        return results

    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        options = ContextOptions(max_tokens=max_tokens)
        context = self.context_retriever.get_context(query, options)
        return context.ison

    def serialize(self) -> str:
        return self.graph.to_ison()

    # Memory interface
    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        self._id_counter += 1
        doc_id = f"mem-{self._id_counter}"
        metadata = metadata or {}

        # Add to graph
        self.graph.add_node('memory', doc_id, content=content, **metadata)

        self._memories[doc_id] = GraphDocument(
            id=doc_id,
            content=content,
            metadata=metadata
        )

    def get(self, query: str, k: int = 5) -> List[GraphDocument]:
        query_words = query.lower().split()
        scored = []

        for doc in self._memories.values():
            score = sum(1 for w in query_words if w in doc.content.lower())
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: -x[0])
        return [doc for _, doc in scored[:k]]

    def clear(self) -> None:
        for doc_id in list(self._memories.keys()):
            if self.graph.has_node('memory', doc_id):
                self.graph.remove_node('memory', doc_id)
        self._memories.clear()

    def size(self) -> int:
        return len(self._memories)

    # Retriever interface
    async def retrieve(self, query: str, k: int = 5) -> List[GraphDocument]:
        return self.get(query, k)

    def get_config(self) -> Dict[str, Any]:
        return {
            'type': 'ISONGraph',
            'node_count': self.graph.node_count(),
            'edge_count': self.graph.edge_count(),
            'memory_count': len(self._memories)
        }

    def to_langchain_format(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convert to LangChain-compatible format"""
        nodes = [
            {
                'id': f"{n.type}:{n.id}",
                'type': n.type,
                'properties': n.properties
            }
            for n in self.graph.nodes()
        ]

        edges = [
            {
                'source': f"{e.source[0]}:{e.source[1]}",
                'target': f"{e.target[0]}:{e.target[1]}",
                'type': e.rel_type,
                'properties': e.properties
            }
            for e in self.graph.edges()
        ]

        return {'nodes': nodes, 'edges': edges}


# =============================================================================
# LlamaIndex Adapter
# =============================================================================

class LlamaIndexAdapter:
    """
    Adapter for LlamaIndex integration.

    Compatible with:
    - LlamaIndex GraphStore interface
    - LlamaIndex QueryEngine interface
    - LlamaIndex Reader interface
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph
        self.context_retriever = ContextRetriever(graph)
        self._index: Dict[str, Set[str]] = defaultdict(set)
        self._build_index()

    def _build_index(self) -> None:
        """Build keyword index"""
        self._index.clear()

        for node in self.graph.nodes():
            node_key = f"{node.type}:{node.id}"

            # Index by type
            self._add_to_index(node.type.lower(), node_key)

            # Index by properties
            for key, value in node.properties.items():
                if isinstance(value, str):
                    words = value.lower().split()
                    for word in words:
                        if len(word) > 2:
                            self._add_to_index(word, node_key)

    def _add_to_index(self, keyword: str, node_key: str) -> None:
        self._index[keyword].add(node_key)

    def get_graph(self) -> ISONGraph:
        return self.graph

    def add_node(
        self,
        node_type: str,
        node_id: Union[int, str],
        **properties: Any
    ) -> None:
        if not self.graph.has_node(node_type, node_id):
            self.graph.add_node(node_type, node_id, **properties)
        else:
            self.graph.update_node(node_type, node_id, **properties)
        self._build_index()

    def add_edge(
        self,
        rel_type: str,
        source: NodeRef,
        target: NodeRef,
        **properties: Any
    ) -> None:
        if not self.graph.has_edge(rel_type, source, target):
            self.graph.add_edge(rel_type, source, target, **properties)

    async def query(self, text: str) -> Dict[str, Any]:
        """Query with automatic response generation"""
        keywords = [w for w in text.lower().split() if len(w) > 2]
        matched_keys: Set[str] = set()

        for keyword in keywords:
            if keyword in self._index:
                matched_keys.update(self._index[keyword])

        nodes = []
        for key in matched_keys:
            parts = key.split(':')
            if len(parts) >= 2:
                node_type = parts[0]
                node_id = ':'.join(parts[1:])
                try:
                    node_id = int(node_id) if node_id.isdigit() else node_id
                    if self.graph.has_node(node_type, node_id):
                        nodes.append(self.graph.get_node(node_type, node_id))
                except Exception:
                    pass

        context = self.get_context(text)
        response = f"Found {len(nodes)} relevant nodes.\n\nContext:\n{context}"

        return {'nodes': nodes, 'response': response}

    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        options = ContextOptions(max_tokens=max_tokens)
        context = self.context_retriever.get_context(query, options)
        return context.ison

    def serialize(self) -> str:
        return self.graph.to_ison()

    async def retrieve(self, query: str, k: int = 5) -> List[GraphDocument]:
        result = await self.query(query)
        nodes = result.get('nodes', [])[:k]

        return [
            GraphDocument(
                id=f"{n.type}:{n.id}",
                content=json.dumps(n.properties),
                metadata={'type': n.type, 'id': n.id, **n.properties}
            )
            for n in nodes
        ]

    def get_config(self) -> Dict[str, Any]:
        return {
            'type': 'ISONGraph',
            'node_count': self.graph.node_count(),
            'edge_count': self.graph.edge_count(),
            'index_size': len(self._index)
        }

    def load_documents(self, documents: List[GraphDocument]) -> None:
        """Load documents into graph as nodes"""
        for doc in documents:
            node_type = doc.metadata.get('type', 'document')
            node_id = doc.id

            self.add_node(node_type, node_id, content=doc.content, **doc.metadata)

    def get_subgraph(
        self,
        node_refs: List[NodeRef],
        hops: int = 1
    ) -> ISONGraph:
        """Get subgraph around specific nodes"""
        subgraph = ISONGraph('subgraph')
        visited: Set[NodeRef] = set()

        def add_node(ref: NodeRef) -> None:
            if ref in visited:
                return
            visited.add(ref)

            if self.graph.has_node(ref[0], ref[1]):
                node = self.graph.get_node_by_ref(ref)
                if not subgraph.has_node(node.type, node.id):
                    subgraph.add_node(node.type, node.id, **node.properties)

        def expand(ref: NodeRef, remaining_hops: int) -> None:
            if remaining_hops <= 0:
                return

            for edge in self.graph.edges(source=ref):
                add_node(edge.target)
                if not subgraph.has_edge(edge.rel_type, edge.source, edge.target):
                    try:
                        subgraph.add_edge(
                            edge.rel_type, edge.source, edge.target,
                            **edge.properties
                        )
                    except Exception:
                        pass
                expand(edge.target, remaining_hops - 1)

            for edge in self.graph.edges(target=ref):
                add_node(edge.source)
                if not subgraph.has_edge(edge.rel_type, edge.source, edge.target):
                    try:
                        subgraph.add_edge(
                            edge.rel_type, edge.source, edge.target,
                            **edge.properties
                        )
                    except Exception:
                        pass
                expand(edge.source, remaining_hops - 1)

        for ref in node_refs:
            add_node(ref)
            expand(ref, hops)

        return subgraph


# =============================================================================
# AutoGen Adapter
# =============================================================================

class AutoGenAdapter:
    """
    Adapter for AutoGen (multi-agent) integration.

    Compatible with:
    - AutoGen memory interface
    - AutoGen agent tools
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph
        self.context_retriever = ContextRetriever(graph)
        self._agent_memories: Dict[str, List[GraphDocument]] = defaultdict(list)

    def get_graph(self) -> ISONGraph:
        return self.graph

    def add_node(
        self,
        node_type: str,
        node_id: Union[int, str],
        **properties: Any
    ) -> None:
        if not self.graph.has_node(node_type, node_id):
            self.graph.add_node(node_type, node_id, **properties)
        else:
            self.graph.update_node(node_type, node_id, **properties)

    def add_edge(
        self,
        rel_type: str,
        source: NodeRef,
        target: NodeRef,
        **properties: Any
    ) -> None:
        if not self.graph.has_edge(rel_type, source, target):
            self.graph.add_edge(rel_type, source, target, **properties)

    async def query(self, text: str) -> str:
        context = self.get_context(text)
        return context

    def get_context(self, query: str, max_tokens: int = 2000) -> str:
        options = ContextOptions(max_tokens=max_tokens)
        context = self.context_retriever.get_context(query, options)
        return context.ison

    def serialize(self) -> str:
        return self.graph.to_ison()

    # Memory interface for agents
    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        metadata = metadata or {}
        agent_id = metadata.get('agent_id', 'default')
        import time
        doc = GraphDocument(
            id=f"{agent_id}-{int(time.time() * 1000)}",
            content=content,
            metadata={**metadata, 'timestamp': time.time()}
        )

        self._agent_memories[agent_id].append(doc)

        # Store in graph
        self.add_node('agent_memory', doc.id, agent_id=agent_id, content=content, **metadata)

    def get(self, query: str, k: int = 5) -> List[GraphDocument]:
        query_words = query.lower().split()
        scored = []

        for memories in self._agent_memories.values():
            for doc in memories:
                score = sum(1 for w in query_words if w in doc.content.lower())
                if score > 0:
                    scored.append((score, doc))

        scored.sort(key=lambda x: -x[0])
        return [doc for _, doc in scored[:k]]

    def clear(self) -> None:
        self._agent_memories.clear()

    def size(self) -> int:
        return sum(len(m) for m in self._agent_memories.values())

    def get_agent_memories(self, agent_id: str, k: Optional[int] = None) -> List[GraphDocument]:
        """Get memories for a specific agent"""
        memories = self._agent_memories.get(agent_id, [])
        if k:
            return memories[-k:]
        return list(memories)

    def share_memory(self, from_agent: str, to_agent: str, memory_id: str) -> None:
        """Share memory between agents via graph relationship"""
        if not self.graph.has_node('agent', from_agent):
            self.add_node('agent', from_agent, name=from_agent)
        if not self.graph.has_node('agent', to_agent):
            self.add_node('agent', to_agent, name=to_agent)

        import time
        self.add_edge(
            'SHARED_MEMORY',
            ('agent', from_agent),
            ('agent', to_agent),
            memory_id=memory_id,
            timestamp=time.time()
        )

    def get_tools(self) -> Dict[str, Callable]:
        """Get tools for AutoGen agents"""
        return {
            'add_entity': lambda node_type, node_id, **props: (
                self.add_node(node_type, node_id, **props),
                f"Added {node_type}:{node_id}"
            )[1],

            'add_relationship': lambda rel_type, src_type, src_id, tgt_type, tgt_id, **props: (
                self.add_edge(rel_type, (src_type, src_id), (tgt_type, tgt_id), **props),
                f"Added {rel_type} from {src_type}:{src_id} to {tgt_type}:{tgt_id}"
            )[1],

            'query_graph': lambda query: self.get_context(query),

            'get_neighbors': lambda node_type, node_id, rel_type=None: [
                f"{n[0]}:{n[1]}"
                for n in self.graph.neighbors((node_type, node_id), rel_type)
            ],

            'find_path': lambda from_type, from_id, to_type, to_id: (
                lambda p: ' -> '.join(f"{n[0]}:{n[1]}" for n in p.nodes) if p else 'No path found'
            )(self.graph.shortest_path((from_type, from_id), (to_type, to_id)))
        }


# =============================================================================
# Prompt Templates
# =============================================================================

class PromptTemplates:
    """Optimized prompt templates for graph-augmented LLM applications"""

    @staticmethod
    def graph_context(graph: ISONGraph, query: str, max_tokens: int = 2000) -> str:
        """Generate context prompt with graph data"""
        retriever = ContextRetriever(graph)
        options = ContextOptions(max_tokens=max_tokens)
        context = retriever.get_context(query, options)

        return f"""You have access to a knowledge graph with the following relevant context:

{context.ison}

Based on this graph data, answer the following question:
{query}

Provide a clear and concise answer using the information from the graph."""

    @staticmethod
    def entity_extraction(text: str, entity_types: List[str]) -> str:
        """Generate extraction prompt for building graph from text"""
        types_str = ", ".join(entity_types)

        return f"""Extract entities and relationships from the following text.

Entity types to look for: {types_str}

Text:
\"\"\"
{text}
\"\"\"

Return the result in this ISON format:
nodes.entity
id\ttype\tname\tproperties

edges.RELATES_TO
source\ttarget\trelation_type

Extract all entities and their relationships."""

    @staticmethod
    def graph_query(graph: ISONGraph, question: str) -> str:
        """Generate graph query prompt"""
        node_types = ", ".join(graph.node_types())
        edge_types = ", ".join(graph.edge_types())

        return f"""You are querying a knowledge graph with:
- Node types: {node_types}
- Edge types: {edge_types}
- {graph.node_count()} nodes, {graph.edge_count()} edges

Question: {question}

Translate this into a graph traversal pattern and explain what you're looking for."""

    @staticmethod
    def graph_summary(graph: ISONGraph) -> str:
        """Generate summarization prompt for graph"""
        sample_nodes = list(graph.nodes())[:5]
        sample_str = "\n".join([
            f"- {n.type}:{n.id}: {json.dumps(n.properties)}"
            for n in sample_nodes
        ])

        return f"""Summarize the following knowledge graph:

Statistics:
- Total nodes: {graph.node_count()}
- Total edges: {graph.edge_count()}
- Node types: {", ".join(graph.node_types())}
- Edge types: {", ".join(graph.edge_types())}

Sample nodes:
{sample_str}

Provide a brief summary of what this graph represents and its key entities."""

    @staticmethod
    def graph_comparison(graph1: ISONGraph, graph2: ISONGraph) -> str:
        """Generate comparison prompt for two graphs"""
        return f"""Compare these two knowledge graphs:

Graph 1 ({graph1.name}):
- Nodes: {graph1.node_count()}
- Edges: {graph1.edge_count()}
- Types: {", ".join(graph1.node_types())}

Graph 2 ({graph2.name}):
- Nodes: {graph2.node_count()}
- Edges: {graph2.edge_count()}
- Types: {", ".join(graph2.node_types())}

Identify similarities, differences, and potential ways to merge them."""


# =============================================================================
# Factory Functions
# =============================================================================

def create_langchain_adapter(graph: ISONGraph) -> LangChainAdapter:
    """Create a LangChain adapter"""
    return LangChainAdapter(graph)


def create_llamaindex_adapter(graph: ISONGraph) -> LlamaIndexAdapter:
    """Create a LlamaIndex adapter"""
    return LlamaIndexAdapter(graph)


def create_autogen_adapter(graph: ISONGraph) -> AutoGenAdapter:
    """Create an AutoGen adapter"""
    return AutoGenAdapter(graph)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Interfaces
    'GraphAdapter',
    'GraphDocument',
    'GraphMemory',
    'GraphRetriever',

    # Adapters
    'LangChainAdapter',
    'LlamaIndexAdapter',
    'AutoGenAdapter',

    # Templates
    'PromptTemplates',

    # Factory Functions
    'create_langchain_adapter',
    'create_llamaindex_adapter',
    'create_autogen_adapter',
]
