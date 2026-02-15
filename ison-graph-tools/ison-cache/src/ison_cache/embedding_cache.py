"""
Embedding Cache
===============

Vector embedding storage with similarity search.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple, Callable
from threading import RLock
import math

from .schema import EmbeddingEntry, SimilarityResult, CacheConfig
from .token_manager import TokenManager
from .serializer import ISONSerializer


class EmbeddingCache:
    """
    Cache for text embeddings with vector similarity search.

    Features:
    - Store text with associated embeddings
    - Cosine and Euclidean similarity search
    - Token-budgeted retrieval
    - Pluggable embedding models
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        embedding_model: Optional[str] = None,
        embedding_dim: int = 384,
        default_ttl: int = 86400,
    ):
        """
        Initialize EmbeddingCache.

        Args:
            config: Cache configuration
            embedding_model: Sentence-transformers model name
            embedding_dim: Embedding dimension (if no model)
            default_ttl: Default TTL in seconds
        """
        self.config = config or CacheConfig(default_ttl_seconds=default_ttl)
        self.embedding_model = embedding_model
        self.embedding_dim = embedding_dim
        self._entries: Dict[str, EmbeddingEntry] = {}
        self._token_manager = TokenManager()
        self._serializer = ISONSerializer()
        self._lock = RLock()

        # Lazy-loaded embedding model
        self._model = None

    @property
    def model(self):
        """Lazy load embedding model"""
        if self._model is None and self.embedding_model:
            try:
                from sentence_transformers import SentenceTransformer
                self._model = SentenceTransformer(self.embedding_model)
                self.embedding_dim = self._model.get_sentence_embedding_dimension()
            except ImportError:
                pass
        return self._model

    # =========================================================================
    # Core Operations
    # =========================================================================

    def set(
        self,
        key: str,
        text: str,
        vector: Optional[List[float]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> EmbeddingEntry:
        """
        Store text with its embedding.

        Args:
            key: Cache key
            text: Text content
            vector: Pre-computed embedding (computed if None)
            metadata: Additional metadata
            ttl: Time-to-live in seconds

        Returns:
            The created EmbeddingEntry
        """
        with self._lock:
            # Compute embedding if not provided
            if vector is None:
                vector = self._compute_embedding(text)

            # Count tokens
            tokens = self._token_manager.count_tokens(text)

            # Calculate expiry
            ttl_seconds = ttl if ttl is not None else self.config.default_ttl_seconds
            expires_at = None
            if ttl_seconds > 0:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

            entry = EmbeddingEntry(
                key=key,
                text=text,
                vector=vector,
                dimension=len(vector),
                model=self.embedding_model or "custom",
                tokens=tokens,
                created_at=datetime.now(timezone.utc),
                metadata=metadata or {},
            )

            self._entries[key] = entry
            return entry

    def get(self, key: str) -> Optional[EmbeddingEntry]:
        """Get an embedding entry by key"""
        with self._lock:
            return self._entries.get(key)

    def delete(self, key: str) -> bool:
        """Delete an entry"""
        with self._lock:
            if key in self._entries:
                del self._entries[key]
                return True
            return False

    def exists(self, key: str) -> bool:
        """Check if key exists"""
        return key in self._entries

    # =========================================================================
    # Similarity Search
    # =========================================================================

    def search(
        self,
        query: str,
        k: int = 10,
        metric: str = "cosine",
        token_budget: Optional[int] = None,
        filter_fn: Optional[Callable[[EmbeddingEntry], bool]] = None,
    ) -> List[SimilarityResult]:
        """
        Search for similar texts.

        Args:
            query: Query text
            k: Number of results
            metric: "cosine" or "euclidean"
            token_budget: Maximum tokens in results
            filter_fn: Optional filter function

        Returns:
            List of SimilarityResult sorted by score
        """
        with self._lock:
            # Compute query embedding
            query_vector = self._compute_embedding(query)

            # Calculate similarities
            results = []
            for key, entry in self._entries.items():
                if filter_fn and not filter_fn(entry):
                    continue

                if metric == "cosine":
                    score = self._cosine_similarity(query_vector, entry.vector)
                    distance = 1.0 - score
                else:  # euclidean
                    distance = self._euclidean_distance(query_vector, entry.vector)
                    score = 1.0 / (1.0 + distance)

                results.append(SimilarityResult(
                    key=key,
                    text=entry.text,
                    score=score,
                    distance=distance,
                    tokens=entry.tokens,
                    metadata=entry.metadata,
                ))

            # Sort by score (descending)
            results.sort(key=lambda x: x.score, reverse=True)

            # Apply k limit
            results = results[:k]

            # Apply token budget
            if token_budget:
                budgeted = []
                remaining = token_budget
                for r in results:
                    if r.tokens <= remaining:
                        budgeted.append(r)
                        remaining -= r.tokens
                results = budgeted

            return results

    def search_by_vector(
        self,
        vector: List[float],
        k: int = 10,
        metric: str = "cosine",
    ) -> List[SimilarityResult]:
        """
        Search using a pre-computed vector.

        Args:
            vector: Query embedding vector
            k: Number of results
            metric: Distance metric

        Returns:
            List of SimilarityResult
        """
        with self._lock:
            results = []
            for key, entry in self._entries.items():
                if metric == "cosine":
                    score = self._cosine_similarity(vector, entry.vector)
                    distance = 1.0 - score
                else:
                    distance = self._euclidean_distance(vector, entry.vector)
                    score = 1.0 / (1.0 + distance)

                results.append(SimilarityResult(
                    key=key,
                    text=entry.text,
                    score=score,
                    distance=distance,
                    tokens=entry.tokens,
                    metadata=entry.metadata,
                ))

            results.sort(key=lambda x: x.score, reverse=True)
            return results[:k]

    def search_to_ison(
        self,
        query: str,
        k: int = 10,
        token_budget: Optional[int] = None,
    ) -> str:
        """
        Search and return results as ISON format.

        Args:
            query: Query text
            k: Number of results
            token_budget: Maximum tokens

        Returns:
            ISON-formatted search results
        """
        results = self.search(query, k=k, token_budget=token_budget)

        if not results:
            return ""

        # Convert to table format
        items = [
            {
                "key": r.key,
                "text": r.text,
                "score": round(r.score, 4),
                "tokens": r.tokens,
            }
            for r in results
        ]

        return self._serializer.serialize(items, "search_results")

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def mset(
        self,
        items: Dict[str, str],
        vectors: Optional[Dict[str, List[float]]] = None,
        ttl: Optional[int] = None,
    ) -> int:
        """
        Set multiple text entries.

        Args:
            items: Dict of key -> text
            vectors: Optional dict of key -> vector
            ttl: TTL for all items

        Returns:
            Number of items set
        """
        vectors = vectors or {}
        count = 0
        for key, text in items.items():
            vector = vectors.get(key)
            self.set(key, text, vector=vector, ttl=ttl)
            count += 1
        return count

    def batch_embed(
        self,
        texts: List[str],
    ) -> List[List[float]]:
        """
        Compute embeddings for multiple texts efficiently.

        Args:
            texts: List of texts

        Returns:
            List of embedding vectors
        """
        if self.model:
            return self.model.encode(texts).tolist()
        else:
            return [self._compute_embedding(t) for t in texts]

    # =========================================================================
    # Index Operations
    # =========================================================================

    def reindex(self):
        """Recompute all embeddings (useful if model changed)"""
        with self._lock:
            for entry in self._entries.values():
                entry.vector = self._compute_embedding(entry.text)
                entry.dimension = len(entry.vector)
                entry.model = self.embedding_model or "custom"

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        with self._lock:
            total_tokens = sum(e.tokens for e in self._entries.values())
            return {
                "entries": len(self._entries),
                "dimension": self.embedding_dim,
                "model": self.embedding_model or "none",
                "total_tokens": total_tokens,
            }

    def clear(self) -> int:
        """Clear all entries"""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            return count

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _compute_embedding(self, text: str) -> List[float]:
        """Compute embedding for text"""
        if self.model:
            return self.model.encode(text).tolist()
        else:
            # Fallback: simple hash-based pseudo-embedding
            # NOT suitable for real similarity search!
            import hashlib
            h = hashlib.sha256(text.encode()).hexdigest()
            # Convert hex to floats
            vector = []
            for i in range(0, min(len(h), self.embedding_dim * 2), 2):
                byte_val = int(h[i:i+2], 16)
                vector.append((byte_val - 128) / 128.0)

            # Pad if needed
            while len(vector) < self.embedding_dim:
                vector.append(0.0)

            return vector[:self.embedding_dim]

    def _cosine_similarity(self, v1: List[float], v2: List[float]) -> float:
        """Compute cosine similarity between two vectors"""
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return dot / (norm1 * norm2)

    def _euclidean_distance(self, v1: List[float], v2: List[float]) -> float:
        """Compute Euclidean distance between two vectors"""
        return math.sqrt(sum((a - b) ** 2 for a, b in zip(v1, v2)))

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"EmbeddingCache(entries={len(self._entries)}, dim={self.embedding_dim})"
