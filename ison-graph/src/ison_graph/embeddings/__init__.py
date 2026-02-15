#!/usr/bin/env python3
"""
ISONGraph Embeddings - Semantic Graph Extension

Extends ISONGraph with embedding-based similarity search and semantic traversal.
Bridges the gap between vector similarity and graph structure.

Usage:
    from ison_graph.embeddings import SemanticGraph, EmbeddingStore

    # Create semantic graph
    graph = SemanticGraph()

    # Add nodes with auto-embedding
    graph.add_node('person', 1, name='Alice', description='Software engineer')
    graph.add_node('person', 2, name='Bob', description='Data scientist')

    # Semantic similarity search
    similar = graph.similarity_search("engineering roles", top_k=5)

    # Semantic multi-hop: combines embedding similarity with graph traversal
    results = graph.semantic_multi_hop(
        query="Who knows engineers?",
        start_type='person',
        rel_type='KNOWS',
        max_hops=2
    )

Dependencies:
    - ison-graph (required)
    - sentence-transformers (required for SentenceTransformerEncoder)
    - numpy (required)

Author: AceIQ360 Team
Version: 1.0.0
"""

from __future__ import annotations

import sqlite3
import struct
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Optional, Set, Tuple,
    Union, Callable, Iterator
)
from pathlib import Path as FilePath
import json

# Import from ison-graph
from ison_graph import (
    ISONGraph, Node, Edge, Path, NodeRef,
    Direction, GraphError
)

__version__ = "1.0.0"
__author__ = "AceIQ360 Team"


# =============================================================================
# Embedding Encoder Interface
# =============================================================================

class EmbeddingEncoder(ABC):
    """Abstract base class for embedding encoders."""

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return embedding dimension."""
        pass

    @abstractmethod
    def encode(self, text: str) -> List[float]:
        """Encode text to embedding vector."""
        pass

    @abstractmethod
    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts to embedding vectors."""
        pass


class SentenceTransformerEncoder(EmbeddingEncoder):
    """
    Embedding encoder using sentence-transformers.

    Default model: all-MiniLM-L6-v2 (384 dimensions)
    Same model used by AceIQ360 for benchmark consistency.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize encoder with a sentence-transformers model.

        Args:
            model_name: HuggingFace model name
        """
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self._dimension = self.model.get_sentence_embedding_dimension()
            self.model_name = model_name
        except ImportError:
            raise ImportError(
                "sentence-transformers is required. "
                "Install with: pip install sentence-transformers"
            )

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, text: str) -> List[float]:
        """Encode single text."""
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        """Encode multiple texts efficiently."""
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()


class MockEncoder(EmbeddingEncoder):
    """
    Mock encoder for testing (no dependencies).
    Generates deterministic pseudo-embeddings based on text hash.
    """

    def __init__(self, dimension: int = 384):
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def encode(self, text: str) -> List[float]:
        """Generate deterministic pseudo-embedding."""
        import hashlib
        # Create deterministic "embedding" from text hash
        h = hashlib.sha384(text.encode()).digest()
        # Convert bytes to floats in [-1, 1]
        values = []
        for i in range(0, len(h), 2):
            val = struct.unpack('h', h[i:i+2])[0] / 32768.0
            values.append(val)
        # Pad or truncate to dimension
        while len(values) < self._dimension:
            values.extend(values[:self._dimension - len(values)])
        return values[:self._dimension]

    def encode_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.encode(t) for t in texts]


# =============================================================================
# Embedding Store
# =============================================================================

@dataclass
class EmbeddingRecord:
    """A stored embedding with metadata."""
    id: str
    node_ref: NodeRef
    vector: List[float]
    text: str
    model: str = "all-MiniLM-L6-v2"


@dataclass
class SimilarityResult:
    """Result of similarity search."""
    node_ref: NodeRef
    score: float
    text: str

    def __repr__(self) -> str:
        return f"SimilarityResult(:{self.node_ref[0]}:{self.node_ref[1]}, score={self.score:.4f})"


class EmbeddingStore:
    """
    SQLite-backed embedding storage with similarity search.

    Uses brute-force cosine similarity by default.
    Can be extended with sqlite-vec for faster search on large datasets.
    """

    def __init__(
        self,
        db_path: Union[str, FilePath] = ":memory:",
        encoder: Optional[EmbeddingEncoder] = None
    ):
        """
        Initialize embedding store.

        Args:
            db_path: SQLite database path (":memory:" for in-memory)
            encoder: Embedding encoder (default: SentenceTransformerEncoder)
        """
        self.db_path = str(db_path)
        self.encoder = encoder
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        conn = self._get_conn()
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                node_id TEXT NOT NULL,
                vector BLOB NOT NULL,
                text TEXT NOT NULL,
                model TEXT DEFAULT 'all-MiniLM-L6-v2',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(node_type, node_id)
            );

            CREATE INDEX IF NOT EXISTS idx_embeddings_node
                ON embeddings(node_type, node_id);
        """)
        conn.commit()

    def _get_conn(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _vector_to_bytes(self, vector: List[float]) -> bytes:
        """Convert vector to bytes for storage."""
        return struct.pack(f'{len(vector)}f', *vector)

    def _bytes_to_vector(self, data: bytes) -> List[float]:
        """Convert bytes back to vector."""
        n = len(data) // 4  # 4 bytes per float
        return list(struct.unpack(f'{n}f', data))

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def add(
        self,
        node_ref: NodeRef,
        text: str,
        vector: Optional[List[float]] = None
    ) -> str:
        """
        Add embedding for a node.

        Args:
            node_ref: Node reference (type, id)
            text: Text to embed (or pre-computed if vector provided)
            vector: Pre-computed vector (optional, will encode if not provided)

        Returns:
            Embedding ID
        """
        if vector is None:
            if self.encoder is None:
                raise ValueError("No encoder provided and no vector given")
            vector = self.encoder.encode(text)

        # Generate ID
        emb_id = hashlib.md5(f"{node_ref[0]}:{node_ref[1]}".encode()).hexdigest()[:16]

        conn = self._get_conn()
        conn.execute("""
            INSERT OR REPLACE INTO embeddings
            (id, node_type, node_id, vector, text, model)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            emb_id,
            node_ref[0],
            str(node_ref[1]),
            self._vector_to_bytes(vector),
            text,
            getattr(self.encoder, 'model_name', 'unknown') if self.encoder else 'provided'
        ))
        conn.commit()
        return emb_id

    def get(self, node_ref: NodeRef) -> Optional[EmbeddingRecord]:
        """Get embedding for a node."""
        conn = self._get_conn()
        row = conn.execute("""
            SELECT id, node_type, node_id, vector, text, model
            FROM embeddings
            WHERE node_type = ? AND node_id = ?
        """, (node_ref[0], str(node_ref[1]))).fetchone()

        if row is None:
            return None

        return EmbeddingRecord(
            id=row['id'],
            node_ref=(row['node_type'], row['node_id']),
            vector=self._bytes_to_vector(row['vector']),
            text=row['text'],
            model=row['model']
        )

    def remove(self, node_ref: NodeRef) -> bool:
        """Remove embedding for a node."""
        conn = self._get_conn()
        cursor = conn.execute("""
            DELETE FROM embeddings
            WHERE node_type = ? AND node_id = ?
        """, (node_ref[0], str(node_ref[1])))
        conn.commit()
        return cursor.rowcount > 0

    def similarity_search(
        self,
        query: Union[str, List[float]],
        top_k: int = 10,
        node_type: Optional[str] = None,
        threshold: float = 0.0
    ) -> List[SimilarityResult]:
        """
        Find most similar nodes by embedding.

        Args:
            query: Query text or vector
            top_k: Number of results to return
            node_type: Filter by node type (optional)
            threshold: Minimum similarity score

        Returns:
            List of SimilarityResult sorted by score descending
        """
        # Get query vector
        if isinstance(query, str):
            if self.encoder is None:
                raise ValueError("No encoder provided for text query")
            query_vector = self.encoder.encode(query)
        else:
            query_vector = query

        # Fetch all embeddings (brute force)
        conn = self._get_conn()
        if node_type:
            rows = conn.execute("""
                SELECT node_type, node_id, vector, text
                FROM embeddings
                WHERE node_type = ?
            """, (node_type,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT node_type, node_id, vector, text
                FROM embeddings
            """).fetchall()

        # Compute similarities
        results = []
        for row in rows:
            vector = self._bytes_to_vector(row['vector'])
            score = self._cosine_similarity(query_vector, vector)
            if score >= threshold:
                node_id = row['node_id']
                # Try to convert to int if possible
                try:
                    node_id = int(node_id)
                except ValueError:
                    pass
                results.append(SimilarityResult(
                    node_ref=(row['node_type'], node_id),
                    score=score,
                    text=row['text']
                ))

        # Sort by score descending
        results.sort(key=lambda x: x.score, reverse=True)
        return results[:top_k]

    def count(self) -> int:
        """Count total embeddings."""
        conn = self._get_conn()
        return conn.execute("SELECT COUNT(*) FROM embeddings").fetchone()[0]

    def clear(self) -> None:
        """Clear all embeddings."""
        conn = self._get_conn()
        conn.execute("DELETE FROM embeddings")
        conn.commit()

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None


# =============================================================================
# Semantic Graph
# =============================================================================

@dataclass
class SemanticSearchResult:
    """Result of semantic multi-hop search."""
    node_ref: NodeRef
    node: Optional[Node]
    score: float
    hop_count: int
    path: List[NodeRef]

    def __repr__(self) -> str:
        path_str = " -> ".join([f":{n[0]}:{n[1]}" for n in self.path])
        return f"SemanticSearchResult(score={self.score:.4f}, hops={self.hop_count}, path=[{path_str}])"


class SemanticGraph(ISONGraph):
    """
    ISONGraph extended with embedding-based semantic search.

    Combines vector similarity with graph traversal for semantic multi-hop queries.

    Usage:
        graph = SemanticGraph(embedding_db="memory.db")

        # Add nodes with embedding text
        graph.add_node('person', 1, name='Alice', _embed_text='Alice is a software engineer')

        # Or embed manually
        graph.embed_node(('person', 1), 'Alice is a software engineer')

        # Semantic search
        results = graph.semantic_search("engineering", top_k=5)

        # Semantic multi-hop
        results = graph.semantic_multi_hop(
            query="Who are the engineers?",
            rel_type='KNOWS',
            max_hops=2
        )
    """

    def __init__(
        self,
        name: str = "semantic_graph",
        directed: bool = True,
        embedding_db: Union[str, FilePath] = ":memory:",
        encoder: Optional[EmbeddingEncoder] = None,
        auto_embed: bool = True,
        embed_fields: List[str] = None
    ):
        """
        Initialize semantic graph.

        Args:
            name: Graph name
            directed: Whether edges are directed
            embedding_db: Path to embedding database
            encoder: Embedding encoder (default: SentenceTransformerEncoder)
            auto_embed: Auto-embed nodes on add (using embed_fields)
            embed_fields: Fields to concatenate for auto-embedding
        """
        super().__init__(name=name, directed=directed)

        # Lazy-load encoder to avoid import errors if not needed
        self._encoder = encoder
        self._encoder_loaded = encoder is not None

        self.embedding_store = EmbeddingStore(
            db_path=embedding_db,
            encoder=None  # Set later when needed
        )

        self.auto_embed = auto_embed
        self.embed_fields = embed_fields or ['name', 'description', 'content', 'text']

    def _get_encoder(self) -> EmbeddingEncoder:
        """Lazy-load encoder."""
        if not self._encoder_loaded:
            self._encoder = SentenceTransformerEncoder()
            self._encoder_loaded = True
            self.embedding_store.encoder = self._encoder
        return self._encoder

    def add_node(
        self,
        node_type: str,
        node_id: Union[int, str],
        _embed_text: Optional[str] = None,
        **properties: Any
    ) -> Node:
        """
        Add a node, optionally with embedding.

        Args:
            node_type: Node type
            node_id: Node ID
            _embed_text: Text to embed (overrides auto-embed)
            **properties: Node properties

        Returns:
            Created node
        """
        node = super().add_node(node_type, node_id, **properties)

        # Handle embedding
        if _embed_text:
            self.embed_node(node.ref, _embed_text)
        elif self.auto_embed:
            # Auto-generate embed text from properties
            embed_parts = []
            for field in self.embed_fields:
                if field in properties:
                    embed_parts.append(str(properties[field]))
            if embed_parts:
                self.embed_node(node.ref, " ".join(embed_parts))

        return node

    def embed_node(self, node_ref: NodeRef, text: str) -> str:
        """
        Add or update embedding for a node.

        Args:
            node_ref: Node reference
            text: Text to embed

        Returns:
            Embedding ID
        """
        encoder = self._get_encoder()
        self.embedding_store.encoder = encoder
        return self.embedding_store.add(node_ref, text)

    def get_embedding(self, node_ref: NodeRef) -> Optional[EmbeddingRecord]:
        """Get embedding for a node."""
        return self.embedding_store.get(node_ref)

    def remove_node(self, node_type: str, node_id: Union[int, str]) -> None:
        """Remove node and its embedding."""
        ref = (node_type, node_id)
        self.embedding_store.remove(ref)
        super().remove_node(node_type, node_id)

    def similarity_search(
        self,
        query: str,
        top_k: int = 10,
        node_type: Optional[str] = None,
        threshold: float = 0.0
    ) -> List[SimilarityResult]:
        """
        Find similar nodes by embedding.

        Args:
            query: Query text
            top_k: Number of results
            node_type: Filter by type
            threshold: Minimum similarity

        Returns:
            List of SimilarityResult
        """
        encoder = self._get_encoder()
        self.embedding_store.encoder = encoder
        return self.embedding_store.similarity_search(
            query, top_k, node_type, threshold
        )

    def semantic_multi_hop(
        self,
        query: str,
        rel_type: Optional[str] = None,
        max_hops: int = 2,
        top_k_seeds: int = 5,
        top_k_results: int = 10,
        direction: Direction = Direction.OUT,
        decay: float = 0.8,
        threshold: float = 0.3
    ) -> List[SemanticSearchResult]:
        """
        Semantic multi-hop search.

        Combines embedding similarity with graph traversal:
        1. Find top-k similar nodes as seeds (hop 0)
        2. Traverse graph following relationships
        3. Score paths by: seed_similarity * decay^hop_count

        Args:
            query: Query text
            rel_type: Relationship type to follow (None = any)
            max_hops: Maximum hops from seeds
            top_k_seeds: Number of seed nodes from similarity search
            top_k_results: Number of results to return
            direction: Traversal direction
            decay: Score decay per hop (0-1)
            threshold: Minimum seed similarity

        Returns:
            List of SemanticSearchResult sorted by score
        """
        # Step 1: Find seed nodes via similarity
        seeds = self.similarity_search(query, top_k_seeds, threshold=threshold)

        if not seeds:
            return []

        # Step 2: Traverse from each seed
        results: Dict[NodeRef, SemanticSearchResult] = {}

        for seed in seeds:
            # Add seed itself
            if seed.node_ref not in results:
                try:
                    node = self.get_node_by_ref(seed.node_ref)
                except GraphError:
                    node = None
                results[seed.node_ref] = SemanticSearchResult(
                    node_ref=seed.node_ref,
                    node=node,
                    score=seed.score,
                    hop_count=0,
                    path=[seed.node_ref]
                )

            # BFS traversal
            current = [(seed.node_ref, [seed.node_ref], seed.score, 0)]
            visited = {seed.node_ref}

            while current:
                node_ref, path, base_score, hop = current.pop(0)

                if hop >= max_hops:
                    continue

                # Get neighbors
                neighbors = self.neighbors(node_ref, rel_type, direction)

                for neighbor in neighbors:
                    if neighbor in visited:
                        continue

                    visited.add(neighbor)
                    new_path = path + [neighbor]
                    new_hop = hop + 1
                    new_score = base_score * (decay ** new_hop)

                    # Update if better score
                    if neighbor not in results or results[neighbor].score < new_score:
                        try:
                            node = self.get_node_by_ref(neighbor)
                        except GraphError:
                            node = None
                        results[neighbor] = SemanticSearchResult(
                            node_ref=neighbor,
                            node=node,
                            score=new_score,
                            hop_count=new_hop,
                            path=new_path
                        )

                    current.append((neighbor, new_path, base_score, new_hop))

        # Sort by score
        sorted_results = sorted(results.values(), key=lambda x: x.score, reverse=True)
        return sorted_results[:top_k_results]

    def semantic_path(
        self,
        query: str,
        target_ref: NodeRef,
        rel_type: Optional[str] = None,
        max_hops: int = 5,
        top_k_seeds: int = 3
    ) -> Optional[SemanticSearchResult]:
        """
        Find semantically-rooted path to a target node.

        Starts from semantically similar nodes and finds path to target.

        Args:
            query: Query text to find starting point
            target_ref: Target node reference
            rel_type: Relationship type
            max_hops: Maximum path length
            top_k_seeds: Number of seed nodes

        Returns:
            SemanticSearchResult if path found, None otherwise
        """
        seeds = self.similarity_search(query, top_k_seeds)

        for seed in seeds:
            path = self.shortest_path(
                seed.node_ref, target_ref,
                rel_type=rel_type,
                max_hops=max_hops
            )
            if path:
                try:
                    node = self.get_node_by_ref(target_ref)
                except GraphError:
                    node = None
                return SemanticSearchResult(
                    node_ref=target_ref,
                    node=node,
                    score=seed.score * (0.9 ** path.length),
                    hop_count=path.length,
                    path=path.nodes
                )

        return None

    def embed_all_nodes(self, text_fn: Callable[[Node], str] = None) -> int:
        """
        Embed all nodes in the graph.

        Args:
            text_fn: Function to generate embed text from node
                     (default: concatenate embed_fields)

        Returns:
            Number of nodes embedded
        """
        count = 0

        if text_fn is None:
            def default_text_fn(node: Node) -> str:
                parts = []
                for field in self.embed_fields:
                    if field in node.properties:
                        parts.append(str(node.properties[field]))
                return " ".join(parts) if parts else str(node.ref)
            text_fn = default_text_fn

        for node in self.nodes():
            text = text_fn(node)
            if text:
                self.embed_node(node.ref, text)
                count += 1

        return count

    def save(self, path: Union[str, FilePath], format: str = "auto") -> None:
        """
        Save graph to file.

        Note: Embeddings are stored separately in the embedding database.
        """
        super().save(path, format)

    @classmethod
    def load(
        cls,
        path: Union[str, FilePath],
        embedding_db: Union[str, FilePath] = ":memory:",
        format: str = "auto"
    ) -> 'SemanticGraph':
        """
        Load graph from file.

        Args:
            path: Graph file path
            embedding_db: Embedding database path
            format: File format

        Returns:
            SemanticGraph instance
        """
        # Load base graph
        base = ISONGraph.load(path, format)

        # Create semantic graph and copy data
        graph = cls(
            name=base.name,
            directed=base.directed,
            embedding_db=embedding_db
        )

        # Copy nodes
        for node in base.nodes():
            graph._nodes[node.type][node.id] = node

        # Copy edges
        for rel_type in base.edge_types():
            for edge in base.edges(rel_type):
                graph._edges[rel_type].append(edge)
                graph._out_edges[edge.source].append(edge)
                graph._in_edges[edge.target].append(edge)
                graph._edge_set.add(edge.key)

        return graph

    def __repr__(self) -> str:
        emb_count = self.embedding_store.count()
        return f"SemanticGraph(name={self.name}, nodes={self.node_count()}, edges={self.edge_count()}, embeddings={emb_count})"


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Version
    '__version__',

    # Encoders
    'EmbeddingEncoder',
    'SentenceTransformerEncoder',
    'MockEncoder',

    # Store
    'EmbeddingStore',
    'EmbeddingRecord',
    'SimilarityResult',

    # Graph
    'SemanticGraph',
    'SemanticSearchResult',
]
