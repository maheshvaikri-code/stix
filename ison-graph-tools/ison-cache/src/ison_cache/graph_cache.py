"""
ISONGraphCache - Graph-Aware Cache
===================================

Caches knowledge graphs with multi-hop traversal support.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from collections import defaultdict
from threading import RLock

from .schema import (
    GraphEntry, TraversalResult, CacheConfig, Priority
)
from .token_manager import TokenManager, TokenBudget
from .serializer import ISONSerializer


class ISONGraphCache:
    """
    Cache for knowledge graphs with traversal capabilities.

    Features:
    - Store entities and relations as graphs
    - Multi-hop traversal from any entity
    - Token-budgeted subgraph extraction
    - Integration with ISONGraph for full graph features
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        default_ttl: int = 3600,
        token_model: str = "cl100k_base",
    ):
        """
        Initialize ISONGraphCache.

        Args:
            config: Cache configuration
            default_ttl: Default TTL in seconds
            token_model: Tokenizer model
        """
        self.config = config or CacheConfig(default_ttl_seconds=default_ttl)
        self._graphs: Dict[str, GraphEntry] = {}
        self._token_manager = TokenManager(token_model)
        self._serializer = ISONSerializer()
        self._lock = RLock()

        # Entity index: entity_id -> list of graph keys containing it
        self._entity_index: Dict[str, Set[str]] = defaultdict(set)

        # Relation index: (from_id, rel_type) -> list of (to_id, graph_key)
        self._relation_index: Dict[Tuple[str, str], List[Tuple[str, str]]] = defaultdict(list)

    # =========================================================================
    # Core Operations
    # =========================================================================

    def set_graph(
        self,
        key: str,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        observations: Optional[List[Dict[str, Any]]] = None,
        ttl: Optional[int] = None,
    ) -> GraphEntry:
        """
        Store a graph in the cache.

        Args:
            key: Cache key for the graph
            entities: List of entity dicts with 'id', 'type', 'name', etc.
            relations: List of relation dicts with 'from', 'to', 'type'
            observations: Optional list of observations
            ttl: Time-to-live in seconds

        Returns:
            The created GraphEntry
        """
        with self._lock:
            # Calculate tokens
            ison_text = self._serializer.serialize_graph(entities, relations, key)
            tokens = self._token_manager.count_ison_tokens(ison_text)

            # Calculate expiry
            ttl_seconds = ttl if ttl is not None else self.config.default_ttl_seconds
            expires_at = None
            if ttl_seconds > 0:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

            now = datetime.now(timezone.utc)

            entry = GraphEntry(
                key=key,
                entities=entities,
                relations=relations,
                observations=observations or [],
                tokens=tokens,
                created_at=now,
                accessed_at=now,
                expires_at=expires_at,
            )

            # Remove old entry if exists
            if key in self._graphs:
                self._remove_from_indexes(key)

            # Store and index
            self._graphs[key] = entry
            self._build_indexes(key, entities, relations)

            return entry

    def get_graph(
        self,
        key: str,
        max_tokens: Optional[int] = None
    ) -> Optional[str]:
        """
        Get a cached graph as ISON format.

        Args:
            key: Graph key
            max_tokens: Maximum tokens (truncates if exceeded)

        Returns:
            ISON-formatted graph or None
        """
        with self._lock:
            entry = self._graphs.get(key)
            if entry is None:
                return None

            # Check expiry
            if entry.expires_at and datetime.now(timezone.utc) > entry.expires_at:
                self.delete(key)
                return None

            entry.touch()

            # Serialize
            ison_text = self._serializer.serialize_graph(
                entry.entities,
                entry.relations,
                key
            )

            if max_tokens and entry.tokens > max_tokens:
                ison_text, _ = self._token_manager.truncate_to_budget(
                    ison_text, max_tokens
                )

            return ison_text

    def get_graph_raw(self, key: str) -> Optional[GraphEntry]:
        """Get raw graph entry"""
        with self._lock:
            return self._graphs.get(key)

    def delete(self, key: str) -> bool:
        """Delete a graph from cache"""
        with self._lock:
            if key in self._graphs:
                self._remove_from_indexes(key)
                del self._graphs[key]
                return True
            return False

    # =========================================================================
    # Traversal Operations
    # =========================================================================

    def traverse(
        self,
        start_entity: str,
        max_hops: int = 2,
        relation_types: Optional[List[str]] = None,
        token_budget: Optional[int] = None,
        direction: str = "out"  # "out", "in", or "both"
    ) -> TraversalResult:
        """
        Traverse from an entity and return connected subgraph.

        Args:
            start_entity: Starting entity ID (e.g., "user:101")
            max_hops: Maximum traversal depth
            relation_types: Filter by relation types (None = all)
            token_budget: Maximum tokens for result
            direction: Traversal direction

        Returns:
            TraversalResult with ISON output and metadata
        """
        with self._lock:
            # Find graphs containing the entity
            graph_keys = self._entity_index.get(start_entity, set())

            if not graph_keys:
                return TraversalResult(
                    ison="",
                    tokens_used=0,
                    entities_included=[],
                    relations_included=0,
                    hops_traversed=0,
                    truncated=False
                )

            # Collect all entities and relations across graphs
            all_entities: Dict[str, Dict[str, Any]] = {}
            all_relations: List[Dict[str, Any]] = []

            for graph_key in graph_keys:
                entry = self._graphs.get(graph_key)
                if entry and not (entry.expires_at and datetime.now(timezone.utc) > entry.expires_at):
                    for e in entry.entities:
                        eid = e.get("id", str(e))
                        all_entities[eid] = e
                    all_relations.extend(entry.relations)

            # BFS traversal
            visited = {start_entity}
            current_level = {start_entity}
            included_entities = [start_entity]
            included_relations = []
            hops = 0

            budget = TokenBudget(token_budget) if token_budget else None

            while current_level and hops < max_hops:
                next_level = set()

                for entity_id in current_level:
                    # Find relations from this entity
                    for rel in all_relations:
                        from_id = rel.get("from", "")
                        to_id = rel.get("to", "")
                        rel_type = rel.get("type", "")

                        # Check direction
                        target = None
                        if direction in ("out", "both") and from_id == entity_id:
                            target = to_id
                        if direction in ("in", "both") and to_id == entity_id:
                            target = from_id

                        if target is None:
                            continue

                        # Check relation type filter
                        if relation_types and rel_type not in relation_types:
                            continue

                        # Check if already visited
                        if target in visited:
                            continue

                        # Add relation
                        included_relations.append(rel)

                        # Check token budget
                        if budget:
                            rel_tokens = self._token_manager.count_value_tokens(rel)
                            entity_data = all_entities.get(target, {"id": target})
                            entity_tokens = self._token_manager.count_value_tokens(entity_data)

                            if not budget.can_fit(rel_tokens + entity_tokens):
                                continue

                            budget.consume(rel_tokens + entity_tokens)

                        visited.add(target)
                        next_level.add(target)
                        included_entities.append(target)

                current_level = next_level
                hops += 1

            # Build result entities
            result_entities = []
            for eid in included_entities:
                if eid in all_entities:
                    result_entities.append(all_entities[eid])
                else:
                    result_entities.append({"id": eid})

            # Serialize to ISON
            ison_text = self._serializer.serialize_graph(
                result_entities,
                included_relations,
                "subgraph"
            )

            tokens_used = self._token_manager.count_ison_tokens(ison_text)

            return TraversalResult(
                ison=ison_text,
                tokens_used=tokens_used,
                entities_included=included_entities,
                relations_included=len(included_relations),
                hops_traversed=hops,
                truncated=budget.used >= budget.total if budget else False
            )

    def get_neighbors(
        self,
        entity_id: str,
        relation_types: Optional[List[str]] = None,
        direction: str = "out"
    ) -> List[Dict[str, Any]]:
        """
        Get immediate neighbors of an entity.

        Args:
            entity_id: Entity ID
            relation_types: Filter by relation types
            direction: "out", "in", or "both"

        Returns:
            List of neighbor entity dicts
        """
        result = self.traverse(
            entity_id,
            max_hops=1,
            relation_types=relation_types,
            direction=direction
        )

        # Parse the entities from the result
        from .serializer import from_ison
        parsed = from_ison(result.ison)

        entities = parsed.get("subgraph.entities", [])
        # Filter out the start entity
        return [e for e in entities if e.get("id") != entity_id]

    def find_path(
        self,
        from_entity: str,
        to_entity: str,
        max_hops: int = 5,
        relation_types: Optional[List[str]] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Find shortest path between two entities.

        Args:
            from_entity: Starting entity ID
            to_entity: Target entity ID
            max_hops: Maximum path length
            relation_types: Relation types to traverse

        Returns:
            List of path steps or None if no path found
        """
        with self._lock:
            # Collect all relations
            all_relations = []
            for entry in self._graphs.values():
                all_relations.extend(entry.relations)

            # BFS for shortest path
            visited = {from_entity}
            queue = [(from_entity, [])]

            while queue:
                current, path = queue.pop(0)

                if len(path) > max_hops:
                    continue

                for rel in all_relations:
                    from_id = rel.get("from", "")
                    to_id = rel.get("to", "")
                    rel_type = rel.get("type", "")

                    if from_id != current:
                        continue

                    if relation_types and rel_type not in relation_types:
                        continue

                    new_path = path + [rel]

                    if to_id == to_entity:
                        return new_path

                    if to_id not in visited:
                        visited.add(to_id)
                        queue.append((to_id, new_path))

            return None

    # =========================================================================
    # Entity Operations
    # =========================================================================

    def get_entity(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """Get an entity by ID from any cached graph"""
        with self._lock:
            graph_keys = self._entity_index.get(entity_id, set())

            for graph_key in graph_keys:
                entry = self._graphs.get(graph_key)
                if entry:
                    for e in entry.entities:
                        if e.get("id") == entity_id:
                            return e

            return None

    def find_entities(
        self,
        entity_type: Optional[str] = None,
        name_pattern: Optional[str] = None,
        **properties
    ) -> List[Dict[str, Any]]:
        """
        Find entities matching criteria.

        Args:
            entity_type: Filter by entity type
            name_pattern: Filter by name (supports * wildcards)
            **properties: Additional property filters

        Returns:
            List of matching entities
        """
        import fnmatch

        with self._lock:
            results = []

            for entry in self._graphs.values():
                for entity in entry.entities:
                    # Type filter
                    if entity_type and entity.get("type") != entity_type:
                        continue

                    # Name pattern filter
                    if name_pattern:
                        name = entity.get("name", "")
                        if not fnmatch.fnmatch(name, name_pattern):
                            continue

                    # Property filters
                    match = True
                    for key, value in properties.items():
                        if entity.get(key) != value:
                            match = False
                            break

                    if match:
                        results.append(entity)

            return results

    # =========================================================================
    # Merge Operations
    # =========================================================================

    def merge_graph(
        self,
        key: str,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
    ) -> GraphEntry:
        """
        Merge new entities/relations into existing graph.

        Args:
            key: Graph key
            entities: New entities to merge
            relations: New relations to merge

        Returns:
            Updated GraphEntry
        """
        with self._lock:
            existing = self._graphs.get(key)

            if existing:
                # Merge entities (by ID)
                entity_map = {e.get("id"): e for e in existing.entities}
                for e in entities:
                    eid = e.get("id")
                    if eid in entity_map:
                        entity_map[eid].update(e)
                    else:
                        entity_map[eid] = e

                # Merge relations (avoid duplicates)
                rel_keys = {
                    (r.get("from"), r.get("type"), r.get("to"))
                    for r in existing.relations
                }
                merged_relations = list(existing.relations)
                for r in relations:
                    key_tuple = (r.get("from"), r.get("type"), r.get("to"))
                    if key_tuple not in rel_keys:
                        merged_relations.append(r)
                        rel_keys.add(key_tuple)

                return self.set_graph(
                    key,
                    list(entity_map.values()),
                    merged_relations,
                    existing.observations,
                    existing.ttl_seconds if hasattr(existing, 'ttl_seconds') else None
                )
            else:
                return self.set_graph(key, entities, relations)

    # =========================================================================
    # Statistics
    # =========================================================================

    def stats(self) -> Dict[str, Any]:
        """Get graph cache statistics"""
        with self._lock:
            total_entities = 0
            total_relations = 0
            total_tokens = 0

            for entry in self._graphs.values():
                total_entities += len(entry.entities)
                total_relations += len(entry.relations)
                total_tokens += entry.tokens

            return {
                "graphs": len(self._graphs),
                "entities": total_entities,
                "relations": total_relations,
                "tokens": total_tokens,
                "indexed_entities": len(self._entity_index),
            }

    def clear(self) -> int:
        """Clear all cached graphs"""
        with self._lock:
            count = len(self._graphs)
            self._graphs.clear()
            self._entity_index.clear()
            self._relation_index.clear()
            return count

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _build_indexes(
        self,
        graph_key: str,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]]
    ):
        """Build indexes for a graph"""
        for entity in entities:
            eid = entity.get("id", str(entity))
            self._entity_index[eid].add(graph_key)

        for rel in relations:
            from_id = rel.get("from", "")
            rel_type = rel.get("type", "")
            to_id = rel.get("to", "")

            if from_id and rel_type:
                self._relation_index[(from_id, rel_type)].append((to_id, graph_key))

    def _remove_from_indexes(self, graph_key: str):
        """Remove a graph from indexes"""
        entry = self._graphs.get(graph_key)
        if not entry:
            return

        for entity in entry.entities:
            eid = entity.get("id", str(entity))
            if eid in self._entity_index:
                self._entity_index[eid].discard(graph_key)
                if not self._entity_index[eid]:
                    del self._entity_index[eid]

        # Clean up relation index
        keys_to_remove = []
        for key, entries in self._relation_index.items():
            self._relation_index[key] = [
                (to_id, gk) for to_id, gk in entries if gk != graph_key
            ]
            if not self._relation_index[key]:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            del self._relation_index[key]

    def __len__(self) -> int:
        return len(self._graphs)

    def __repr__(self) -> str:
        stats = self.stats()
        return f"ISONGraphCache(graphs={stats['graphs']}, entities={stats['entities']})"
