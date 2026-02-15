"""
ISONCache Integration for Agent Memory
=======================================

Integrates ISONCache with AgentMemory to provide:
- Token-efficient context retrieval
- Embedding-based semantic memory search
- Cached context building
- ISON-formatted output for LLM context injection

Usage:
    from agent_memory import AgentMemory
    from agent_memory.cache_integration import CachedAgentMemory, SemanticMemory

    # Wrap existing memory with cache
    memory = AgentMemory("my-project")
    cached = CachedAgentMemory(memory)

    # Get context with token budget
    context = cached.get_cached_context(
        task="modify the cache module",
        token_budget=2000
    )

    # Semantic search over memories
    semantic = SemanticMemory(memory)
    results = semantic.search("database connection pooling", k=5)
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import hashlib

if TYPE_CHECKING:
    from .memory import AgentMemory

# Try to import ISONCache - provide fallback if not installed
try:
    from ison_cache import ISONCache, ISONGraphCache, EmbeddingCache
    from ison_cache.schema import Priority, CacheEntry, BudgetResult
    from ison_cache.token_manager import TokenManager, TokenBudget
    from ison_cache.serializer import to_ison
    ISONCACHE_AVAILABLE = True
except ImportError:
    ISONCACHE_AVAILABLE = False
    ISONCache = None
    ISONGraphCache = None
    EmbeddingCache = None
    Priority = None


@dataclass
class CachedContext:
    """Context retrieved from cache with token budget."""
    task: str
    ison_output: str
    tokens_used: int
    tokens_budget: int
    utilization: float
    categories_included: List[str]
    categories_truncated: List[str]
    from_cache: bool
    cache_key: str


@dataclass
class SemanticResult:
    """Result from semantic memory search."""
    key: str
    memory_type: str
    content: str
    score: float
    metadata: Dict[str, Any]


class CachedAgentMemory:
    """
    Wrapper around AgentMemory that adds ISONCache integration.

    Provides:
    - Token-efficient context retrieval
    - Automatic caching of context builds
    - ISON-formatted output ready for LLM context injection
    - Token budgeting across memory categories
    """

    # Memory categories and their priorities (higher = more important)
    CATEGORY_PRIORITIES = {
        "warnings": 100,      # Always include
        "constraints": 95,    # Almost always
        "hot_paths": 90,      # Performance critical
        "bug_risks": 85,      # Potential issues
        "conventions": 80,    # Code style
        "patterns": 75,       # Project patterns
        "dependencies": 70,   # Library notes
        "decisions": 60,      # ADRs
        "module_context": 50, # Module info
        "team_experts": 40,   # Who knows what
        "session": 30,        # Session continuity
    }

    def __init__(
        self,
        memory: "AgentMemory",
        cache_max_mb: int = 100,
        cache_ttl: int = 3600,
        enable_context_cache: bool = True,
    ):
        """
        Initialize cached memory.

        Args:
            memory: AgentMemory instance to wrap
            cache_max_mb: Maximum cache size in MB
            cache_ttl: Default TTL for cached items in seconds
            enable_context_cache: Whether to cache context builds
        """
        if not ISONCACHE_AVAILABLE:
            raise ImportError(
                "ISONCache not installed. Install with: "
                "pip install -e tools/ison-cache"
            )

        self.memory = memory
        self.enable_context_cache = enable_context_cache

        # Initialize caches
        self._kv_cache = ISONCache(
            max_memory_mb=cache_max_mb,
            default_ttl=cache_ttl
        )
        self._graph_cache = ISONGraphCache()
        self._token_manager = TokenManager()

        # Context cache TTL (shorter for dynamic context)
        self._context_ttl = 300  # 5 minutes

    def _context_key(self, task: str, files: List[str]) -> str:
        """Generate cache key for a context request."""
        content = f"{task}|{'|'.join(sorted(files))}"
        return f"context:{hashlib.md5(content.encode()).hexdigest()[:12]}"

    def get_cached_context(
        self,
        task: str,
        files: Optional[List[str]] = None,
        token_budget: int = 4000,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> CachedContext:
        """
        Get context for a task with token budget.

        Returns ISON-formatted context optimized for LLM injection.

        Args:
            task: Description of the task
            files: Files being modified
            token_budget: Maximum tokens for context
            include: Memory categories to include
            exclude: Memory categories to exclude
            force_refresh: Force rebuild even if cached

        Returns:
            CachedContext with ISON output and metadata
        """
        files = files or []
        cache_key = self._context_key(task, files)

        # Check cache first
        if self.enable_context_cache and not force_refresh:
            cached = self._kv_cache.get(cache_key, max_tokens=token_budget)
            if cached:
                # Parse cached context info
                return CachedContext(
                    task=task,
                    ison_output=cached,
                    tokens_used=self._token_manager.count_tokens(cached),
                    tokens_budget=token_budget,
                    utilization=100 * self._token_manager.count_tokens(cached) / token_budget,
                    categories_included=["cached"],
                    categories_truncated=[],
                    from_cache=True,
                    cache_key=cache_key,
                )

        # Build context with budget
        return self._build_budgeted_context(
            task=task,
            files=files,
            token_budget=token_budget,
            include=include,
            exclude=exclude,
            cache_key=cache_key,
        )

    def _build_budgeted_context(
        self,
        task: str,
        files: List[str],
        token_budget: int,
        include: Optional[List[str]],
        exclude: Optional[List[str]],
        cache_key: str,
    ) -> CachedContext:
        """Build context respecting token budget."""
        raw_context = {"task": task, "files": files}
        budget = TokenBudget(total=token_budget)

        # Determine categories
        categories = list(self.CATEGORY_PRIORITIES.keys())
        if include:
            categories = [c for c in categories if c in include]
        if exclude:
            categories = [c for c in categories if c not in exclude]

        # Sort by priority
        categories.sort(key=lambda c: self.CATEGORY_PRIORITIES.get(c, 0), reverse=True)

        # Gather memories by category
        gathered: Dict[str, List[Dict[str, Any]]] = {}
        for category in categories:
            items = self._get_category_items(category, raw_context)
            if items:
                gathered[category] = items

        # Build ISON output within budget
        ison_sections = []
        included_categories = []
        truncated_categories = []

        # Header
        header = f"# Memory Context for: {task}\n"
        header_tokens = self._token_manager.count_tokens(header)
        if not budget.can_fit(header_tokens):
            return CachedContext(
                task=task,
                ison_output="",
                tokens_used=0,
                tokens_budget=token_budget,
                utilization=0,
                categories_included=[],
                categories_truncated=list(gathered.keys()),
                from_cache=False,
                cache_key=cache_key,
            )
        budget.consume(header_tokens)
        ison_sections.append(header)

        # Add each category in priority order
        for category in categories:
            if category not in gathered:
                continue

            items = gathered[category]
            section_ison = self._format_category_ison(category, items)
            section_tokens = self._token_manager.count_tokens(section_ison)

            if budget.can_fit(section_tokens):
                ison_sections.append(section_ison)
                budget.consume(section_tokens)
                included_categories.append(category)
            else:
                # Try to fit partial
                partial = self._truncate_category(category, items, budget.remaining)
                if partial:
                    ison_sections.append(partial)
                    budget.consume(self._token_manager.count_tokens(partial))
                    included_categories.append(f"{category}*")  # * indicates partial
                truncated_categories.append(category)

        # Combine output
        ison_output = "\n".join(ison_sections)
        tokens_used = token_budget - budget.remaining

        # Cache the result
        if self.enable_context_cache:
            self._kv_cache.set(
                cache_key,
                {"ison": ison_output, "categories": included_categories},
                ttl=self._context_ttl,
                tags=["context", task[:20]]
            )

        return CachedContext(
            task=task,
            ison_output=ison_output,
            tokens_used=tokens_used,
            tokens_budget=token_budget,
            utilization=100 * tokens_used / token_budget if token_budget > 0 else 0,
            categories_included=included_categories,
            categories_truncated=truncated_categories,
            from_cache=False,
            cache_key=cache_key,
        )

    def _get_category_items(
        self,
        category: str,
        raw_context: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Get items from memory for a category."""
        store_map = {
            "warnings": lambda: self._get_warnings(raw_context),
            "constraints": lambda: self.memory.decisions.get_relevant(raw_context),
            "hot_paths": lambda: self.memory.performance.get_relevant(raw_context),
            "conventions": lambda: self.memory.conventions.get_relevant(raw_context),
            "patterns": lambda: self.memory.templates.get_relevant(raw_context),
            "bug_risks": lambda: self.memory.bugs.get_relevant(raw_context),
            "dependencies": lambda: self.memory.dependencies.get_relevant(raw_context),
            "decisions": lambda: self._get_decisions(raw_context),
            "module_context": lambda: self.memory.codebase.get_relevant(raw_context),
            "team_experts": lambda: self.memory.team.get_relevant(raw_context),
            "session": lambda: self._get_session_context(raw_context),
        }

        getter = store_map.get(category)
        if getter:
            try:
                return getter()
            except Exception:
                return []
        return []

    def _get_warnings(self, raw_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get warnings from various sources."""
        warnings = []
        task = raw_context.get("task", "")

        if task:
            conflict = self.memory.decisions.check_decision(task)
            if conflict:
                warnings.append({
                    "type": "decision_conflict",
                    "message": conflict.get("conflict", ""),
                    **conflict
                })

        for item in self.memory.techdebt.get_relevant(raw_context):
            if item.get("type") == "refactoring_warning":
                warnings.append({
                    "type": "refactoring_failed",
                    "message": f"Approach tried: {item.get('attempt', {}).get('approach', '')}",
                    **item
                })

        return warnings

    def _get_decisions(self, raw_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant decisions."""
        decisions = []
        for node in self.memory.graph.nodes():
            if node.type == "decision":
                decisions.append(node.properties)
        return decisions[:5]

    def _get_session_context(self, raw_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get session continuity context."""
        last_session = self.memory.sessions.get_last_session()
        if last_session:
            ctx = self.memory.sessions.get_session_context(last_session)
            if ctx:
                return [ctx]
        return []

    def _format_category_ison(
        self,
        category: str,
        items: List[Dict[str, Any]]
    ) -> str:
        """Format category items as ISON."""
        # Determine block type based on category
        if len(items) == 1 and category in ("session",):
            # Single object
            return to_ison(items[0], f"memory.{category}")
        else:
            # Table of items
            return to_ison(items, f"memory.{category}")

    def _truncate_category(
        self,
        category: str,
        items: List[Dict[str, Any]],
        remaining_tokens: int
    ) -> Optional[str]:
        """Try to fit partial category within remaining tokens."""
        if remaining_tokens < 50:
            return None

        # Try progressively fewer items
        for count in range(len(items), 0, -1):
            partial = items[:count]
            ison = self._format_category_ison(category, partial)
            if self._token_manager.count_tokens(ison) <= remaining_tokens:
                return ison

        return None

    def cache_memory_item(
        self,
        key: str,
        value: Any,
        memory_type: str,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
    ) -> "CacheEntry":
        """
        Cache a memory item for fast retrieval.

        Args:
            key: Cache key
            value: Value to cache
            memory_type: Type of memory (convention, decision, etc.)
            ttl: Time-to-live in seconds
            tags: Tags for grouping

        Returns:
            CacheEntry with metadata
        """
        all_tags = [memory_type] + (tags or [])
        return self._kv_cache.set(key, value, ttl=ttl, tags=all_tags)

    def get_cached_item(
        self,
        key: str,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """Get cached memory item in ISON format."""
        return self._kv_cache.get(key, max_tokens=max_tokens)

    def get_memories_within_budget(
        self,
        pattern: str,
        token_budget: int,
        priority: str = "hits",
    ) -> "BudgetResult":
        """
        Get multiple cached memories within token budget.

        Args:
            pattern: Key pattern (e.g., "convention:*")
            token_budget: Maximum tokens
            priority: Priority for selection (hits, recent, tokens)

        Returns:
            BudgetResult with ISON output and metadata
        """
        priority_enum = Priority.HITS
        if priority == "recent":
            priority_enum = Priority.RECENT
        elif priority == "tokens":
            priority_enum = Priority.TOKENS

        return self._kv_cache.get_within_budget(
            patterns=pattern,
            token_budget=token_budget,
            priority=priority_enum,
        )

    def invalidate_context_cache(self) -> int:
        """Invalidate all cached contexts."""
        count = 0
        for key in self._kv_cache.keys("context:*"):
            if self._kv_cache.delete(key):
                count += 1
        return count

    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        cache_stats = self._kv_cache.stats()
        return {
            "memory_name": self.memory.name,
            "cache": {
                "entries": cache_stats.total_entries,
                "tokens": cache_stats.total_tokens,
                "hits": cache_stats.total_hits,
                "misses": cache_stats.total_misses,
                "hit_rate": cache_stats.hit_rate,
                "memory_bytes": cache_stats.memory_bytes,
            }
        }


class SemanticMemory:
    """
    Semantic search over agent memories using embeddings.

    Enables finding relevant memories by meaning rather than exact match.

    Usage:
        semantic = SemanticMemory(memory)

        # Index memories
        semantic.index_all()

        # Search by meaning
        results = semantic.search("database connection issues", k=5)
    """

    def __init__(
        self,
        memory: "AgentMemory",
        embedding_dim: int = 384,
        embedding_model: Optional[str] = None,
    ):
        """
        Initialize semantic memory.

        Args:
            memory: AgentMemory instance
            embedding_dim: Embedding dimension (used if no model specified)
            embedding_model: Sentence-transformers model name (e.g., 'all-MiniLM-L6-v2')
        """
        if not ISONCACHE_AVAILABLE:
            raise ImportError(
                "ISONCache not installed. Install with: "
                "pip install -e tools/ison-cache[embeddings]"
            )

        self.memory = memory
        self._embedding_cache = EmbeddingCache(
            embedding_dim=embedding_dim,
            embedding_model=embedding_model,
        )
        self._indexed = False

    def index_all(self, force: bool = False) -> Dict[str, int]:
        """
        Index all memories for semantic search.

        Args:
            force: Re-index even if already indexed

        Returns:
            Dict with counts by memory type
        """
        if self._indexed and not force:
            return {"status": "already_indexed"}

        counts = {}

        # Index conventions
        for node in self.memory.graph.nodes():
            if node.type == "convention":
                text = self._format_for_indexing("convention", node.properties)
                self._embedding_cache.set(f"convention:{node.id}", text, metadata={"type": "convention"})
                counts["conventions"] = counts.get("conventions", 0) + 1

            elif node.type == "decision":
                text = self._format_for_indexing("decision", node.properties)
                self._embedding_cache.set(f"decision:{node.id}", text, metadata={"type": "decision"})
                counts["decisions"] = counts.get("decisions", 0) + 1

            elif node.type == "bug_pattern":
                text = self._format_for_indexing("bug_pattern", node.properties)
                self._embedding_cache.set(f"bug:{node.id}", text, metadata={"type": "bug_pattern"})
                counts["bugs"] = counts.get("bugs", 0) + 1

            elif node.type == "dependency":
                text = self._format_for_indexing("dependency", node.properties)
                self._embedding_cache.set(f"dep:{node.id}", text, metadata={"type": "dependency"})
                counts["dependencies"] = counts.get("dependencies", 0) + 1

            elif node.type == "template":
                text = self._format_for_indexing("template", node.properties)
                self._embedding_cache.set(f"template:{node.id}", text, metadata={"type": "template"})
                counts["templates"] = counts.get("templates", 0) + 1

            elif node.type == "module":
                text = self._format_for_indexing("module", node.properties)
                self._embedding_cache.set(f"module:{node.id}", text, metadata={"type": "module"})
                counts["modules"] = counts.get("modules", 0) + 1

        self._indexed = True
        counts["total"] = sum(counts.values())
        return counts

    def _format_for_indexing(self, memory_type: str, props: Dict[str, Any]) -> str:
        """Format memory properties for embedding."""
        parts = []

        if memory_type == "convention":
            parts.append(props.get("category", ""))
            parts.append(props.get("rule", ""))
            parts.append(props.get("pattern", ""))

        elif memory_type == "decision":
            parts.append(props.get("what", ""))
            parts.append(props.get("why", ""))
            parts.append(props.get("how", ""))

        elif memory_type == "bug_pattern":
            parts.append(props.get("name", ""))
            parts.append(props.get("signature", ""))
            parts.append(props.get("description", ""))

        elif memory_type == "dependency":
            parts.append(props.get("name", ""))
            parts.append(props.get("description", ""))

        elif memory_type == "template":
            parts.append(props.get("name", ""))
            parts.append(props.get("pattern", ""))
            parts.append(props.get("template", ""))

        elif memory_type == "module":
            parts.append(props.get("name", ""))
            parts.append(props.get("purpose", ""))
            parts.append(props.get("description", ""))

        return " ".join(p for p in parts if p)

    def search(
        self,
        query: str,
        k: int = 5,
        memory_types: Optional[List[str]] = None,
        token_budget: Optional[int] = None,
    ) -> List[SemanticResult]:
        """
        Search memories by semantic similarity.

        Args:
            query: Search query
            k: Number of results
            memory_types: Filter by memory types
            token_budget: Optional token budget

        Returns:
            List of SemanticResult ordered by relevance
        """
        if not self._indexed:
            self.index_all()

        # Filter function
        filter_fn = None
        if memory_types:
            filter_fn = lambda entry: entry.metadata.get("type") in memory_types

        # Search
        results = self._embedding_cache.search(
            query=query,
            k=k,
            token_budget=token_budget,
            filter_fn=filter_fn,
        )

        return [
            SemanticResult(
                key=r.key,
                memory_type=r.metadata.get("type", "unknown"),
                content=r.text,
                score=r.score,
                metadata=r.metadata,
            )
            for r in results
        ]

    def search_to_ison(
        self,
        query: str,
        k: int = 5,
        token_budget: int = 1000,
    ) -> str:
        """
        Search and return results as ISON.

        Args:
            query: Search query
            k: Number of results
            token_budget: Maximum tokens for output

        Returns:
            ISON-formatted search results
        """
        return self._embedding_cache.search_to_ison(
            query=query,
            k=k,
            token_budget=token_budget,
        )

    def find_similar_memories(
        self,
        memory_key: str,
        k: int = 5,
    ) -> List[SemanticResult]:
        """
        Find memories similar to a given memory.

        Args:
            memory_key: Key of the memory to find similar to
            k: Number of results

        Returns:
            List of similar memories
        """
        # Get the text for the memory
        entry = self._embedding_cache._entries.get(memory_key)
        if not entry:
            return []

        # Search excluding self
        results = self._embedding_cache.search(
            query=entry.text,
            k=k + 1,
        )

        return [
            SemanticResult(
                key=r.key,
                memory_type=r.metadata.get("type", "unknown"),
                content=r.text,
                score=r.score,
                metadata=r.metadata,
            )
            for r in results if r.key != memory_key
        ][:k]

    def stats(self) -> Dict[str, Any]:
        """Get semantic memory statistics."""
        return {
            "indexed": self._indexed,
            "embedding_cache": self._embedding_cache.stats(),
        }


class MemoryGraphCache:
    """
    Cache memory as a graph for efficient traversal queries.

    Useful for exploring relationships between memories.
    """

    def __init__(self, memory: "AgentMemory"):
        """Initialize graph cache."""
        if not ISONCACHE_AVAILABLE:
            raise ImportError("ISONCache not installed")

        self.memory = memory
        self._graph_cache = ISONGraphCache()
        self._synced = False

    def sync(self) -> Dict[str, int]:
        """
        Sync memory graph to cache.

        Returns:
            Dict with entity and relation counts
        """
        entities = []
        relations = []

        # Export nodes as entities
        for node in self.memory.graph.nodes():
            entities.append({
                "id": node.id,
                "type": node.type,
                **node.properties
            })

        # Export edges as relations
        for edge in self.memory.graph.edges():
            relations.append({
                "from": edge.source,
                "to": edge.target,
                "type": edge.rel_type,
                **edge.properties
            })

        # Store in graph cache
        self._graph_cache.set_graph(
            f"memory:{self.memory.name}",
            entities,
            relations,
        )

        self._synced = True
        return {
            "entities": len(entities),
            "relations": len(relations),
        }

    def traverse(
        self,
        start_entity: str,
        max_hops: int = 2,
        relation_types: Optional[List[str]] = None,
        token_budget: int = 1000,
    ) -> str:
        """
        Traverse from an entity with token budget.

        Args:
            start_entity: Starting entity ID
            max_hops: Maximum traversal depth
            relation_types: Filter by relation types
            token_budget: Maximum tokens for output

        Returns:
            ISON-formatted subgraph
        """
        if not self._synced:
            self.sync()

        result = self._graph_cache.traverse(
            start_entity=start_entity,
            max_hops=max_hops,
            relation_types=relation_types,
            token_budget=token_budget,
        )

        return result.ison

    def find_related(
        self,
        entity_id: str,
        relation_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find entities related to a given entity."""
        if not self._synced:
            self.sync()

        result = self._graph_cache.traverse(
            start_entity=entity_id,
            max_hops=1,
            relation_types=[relation_type] if relation_type else None,
        )

        return [
            {"id": eid, "relation": relation_type}
            for eid in result.entities_included
            if eid != entity_id
        ]


# Convenience functions

def create_cached_memory(
    memory: "AgentMemory",
    **cache_options
) -> CachedAgentMemory:
    """
    Create a cached wrapper for AgentMemory.

    Args:
        memory: AgentMemory instance
        **cache_options: Options for CachedAgentMemory

    Returns:
        CachedAgentMemory instance
    """
    return CachedAgentMemory(memory, **cache_options)


def create_semantic_memory(
    memory: "AgentMemory",
    index_immediately: bool = True,
    **options
) -> SemanticMemory:
    """
    Create a semantic search interface for AgentMemory.

    Args:
        memory: AgentMemory instance
        index_immediately: Index all memories on creation
        **options: Options for SemanticMemory

    Returns:
        SemanticMemory instance
    """
    semantic = SemanticMemory(memory, **options)
    if index_immediately:
        semantic.index_all()
    return semantic


def get_context_with_budget(
    memory: "AgentMemory",
    task: str,
    files: Optional[List[str]] = None,
    token_budget: int = 2000,
) -> str:
    """
    Get ISON-formatted context within token budget.

    Convenience function for quick context retrieval.

    Args:
        memory: AgentMemory instance
        task: Task description
        files: Files being modified
        token_budget: Maximum tokens

    Returns:
        ISON-formatted context string
    """
    cached = CachedAgentMemory(memory)
    result = cached.get_cached_context(
        task=task,
        files=files,
        token_budget=token_budget,
    )
    return result.ison_output
