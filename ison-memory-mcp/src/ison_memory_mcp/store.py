"""
SQLite Memory Store with ISON Export

A robust, persistent storage backend for ISON Memory using SQLite.
Features:
- Full ACID transactions
- WAL mode for concurrent reads
- Full-text search on observations
- Automatic schema migrations
- ISON/ISONL/ISONGraph export support
"""

from __future__ import annotations

import asyncio
import json
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Optional, Union

import aiosqlite

from ison_memory_mcp.config import MemoryConfig, StorageFormat
from ison_memory_mcp.models import (
    Entity, Observation, Relation, SearchResult, MemoryStats,
    generate_id, utc_now, format_timestamp, parse_timestamp
)


# Schema version for migrations
SCHEMA_VERSION = 1

# SQL Schema
SCHEMA_SQL = """
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_info (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

-- Entities table
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT,
    metadata TEXT DEFAULT '{}',
    access_count INTEGER DEFAULT 0,
    last_accessed TEXT,

    -- Constraints
    CHECK (json_valid(metadata))
);

-- Observations table
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    source TEXT DEFAULT 'chat',
    confidence REAL DEFAULT 1.0,
    metadata TEXT DEFAULT '{}',
    content_hash TEXT,
    access_count INTEGER DEFAULT 0,

    -- Foreign key
    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,

    -- Constraints
    CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CHECK (json_valid(metadata))
);

-- Relations table
CREATE TABLE IF NOT EXISTS relations (
    id TEXT PRIMARY KEY,
    from_entity TEXT NOT NULL,
    to_entity TEXT NOT NULL,
    relation_type TEXT NOT NULL,
    created_at TEXT NOT NULL,
    confidence REAL DEFAULT 1.0,
    metadata TEXT DEFAULT '{}',
    bidirectional INTEGER DEFAULT 0,
    access_count INTEGER DEFAULT 0,

    -- Foreign keys
    FOREIGN KEY (from_entity) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (to_entity) REFERENCES entities(id) ON DELETE CASCADE,

    -- Constraints
    CHECK (confidence >= 0.0 AND confidence <= 1.0),
    CHECK (json_valid(metadata)),

    -- Unique constraint for relation
    UNIQUE (from_entity, to_entity, relation_type)
);

-- Indexes for fast lookups
CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(entity_type);
CREATE INDEX IF NOT EXISTS idx_entities_created ON entities(created_at);
CREATE INDEX IF NOT EXISTS idx_entities_accessed ON entities(last_accessed);

CREATE INDEX IF NOT EXISTS idx_observations_entity ON observations(entity_id);
CREATE INDEX IF NOT EXISTS idx_observations_timestamp ON observations(timestamp);
CREATE INDEX IF NOT EXISTS idx_observations_source ON observations(source);
CREATE INDEX IF NOT EXISTS idx_observations_hash ON observations(content_hash);

CREATE INDEX IF NOT EXISTS idx_relations_from ON relations(from_entity);
CREATE INDEX IF NOT EXISTS idx_relations_to ON relations(to_entity);
CREATE INDEX IF NOT EXISTS idx_relations_type ON relations(relation_type);
CREATE INDEX IF NOT EXISTS idx_relations_created ON relations(created_at);

-- Full-text search for observations
CREATE VIRTUAL TABLE IF NOT EXISTS observations_fts USING fts5(
    content,
    content='observations',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER IF NOT EXISTS observations_ai AFTER INSERT ON observations BEGIN
    INSERT INTO observations_fts(rowid, content) VALUES (new.rowid, new.content);
END;

CREATE TRIGGER IF NOT EXISTS observations_ad AFTER DELETE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content) VALUES('delete', old.rowid, old.content);
END;

CREATE TRIGGER IF NOT EXISTS observations_au AFTER UPDATE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content) VALUES('delete', old.rowid, old.content);
    INSERT INTO observations_fts(rowid, content) VALUES (new.rowid, new.content);
END;

-- Metadata table for store info
CREATE TABLE IF NOT EXISTS store_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class MemoryStore:
    """
    SQLite-backed memory store with ISON export support.

    Thread-safe for async operations using aiosqlite.
    """

    def __init__(self, config: MemoryConfig) -> None:
        self.config = config
        self.db_path = config.storage.path
        self._db: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the database connection and schema"""
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            # Ensure directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Connect to database
            self._db = await aiosqlite.connect(
                str(self.db_path),
                timeout=self.config.storage.sqlite_busy_timeout / 1000
            )

            # Configure SQLite
            await self._db.execute(f"PRAGMA journal_mode = {self.config.storage.sqlite_journal_mode}")
            await self._db.execute(f"PRAGMA cache_size = {self.config.storage.sqlite_cache_size}")
            await self._db.execute("PRAGMA foreign_keys = ON")
            await self._db.execute("PRAGMA synchronous = NORMAL")

            # Enable row factory for dict-like access
            self._db.row_factory = aiosqlite.Row

            # Create schema
            await self._db.executescript(SCHEMA_SQL)

            # Set schema version
            await self._db.execute(
                "INSERT OR REPLACE INTO schema_info (key, value) VALUES (?, ?)",
                ("version", str(SCHEMA_VERSION))
            )

            # Set created timestamp if new
            await self._db.execute(
                "INSERT OR IGNORE INTO store_metadata (key, value) VALUES (?, ?)",
                ("created_at", format_timestamp(utc_now()))
            )

            await self._db.commit()
            self._initialized = True

    async def close(self) -> None:
        """Close the database connection"""
        if self._db:
            await self._db.close()
            self._db = None
            self._initialized = False

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[aiosqlite.Connection, None]:
        """Context manager for database transactions"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        async with self._lock:
            try:
                yield self._db
                await self._db.commit()
            except Exception:
                await self._db.rollback()
                raise

    # =========================================================================
    # Entity Operations
    # =========================================================================

    async def create_entity(
        self,
        name: str,
        entity_type: str,
        metadata: Optional[dict[str, Any]] = None,
        entity_id: Optional[str] = None
    ) -> Entity:
        """Create a new entity"""
        entity = Entity(
            id=entity_id or generate_id("e_"),
            name=name,
            entity_type=entity_type,
            metadata=metadata or {}
        )

        async with self.transaction() as db:
            # Check limits
            count = await self._count_entities(db)
            if count >= self.config.storage.max_entities:
                raise ValueError(f"Maximum entity limit ({self.config.storage.max_entities}) reached")

            await db.execute(
                """
                INSERT INTO entities (id, name, entity_type, created_at, metadata, access_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    entity.id,
                    entity.name,
                    entity.entity_type,
                    format_timestamp(entity.created_at),
                    json.dumps(entity.metadata),
                    0
                )
            )

        return entity

    async def get_entity(self, entity_id: str) -> Optional[Entity]:
        """Get entity by ID"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        async with self._db.execute(
            "SELECT * FROM entities WHERE id = ?",
            (entity_id,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                # Update access tracking
                await self._db.execute(
                    "UPDATE entities SET access_count = access_count + 1, last_accessed = ? WHERE id = ?",
                    (format_timestamp(utc_now()), entity_id)
                )
                await self._db.commit()
                return self._row_to_entity(row)
        return None

    async def find_entity_by_name(self, name: str) -> Optional[Entity]:
        """Find entity by name (case-insensitive)"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        async with self._db.execute(
            "SELECT * FROM entities WHERE LOWER(name) = LOWER(?)",
            (name,)
        ) as cursor:
            row = await cursor.fetchone()
            if row:
                return self._row_to_entity(row)
        return None

    async def search_entities(
        self,
        query: str,
        entity_type: Optional[str] = None,
        limit: int = 50
    ) -> list[Entity]:
        """Search entities by name pattern"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        sql = "SELECT * FROM entities WHERE name LIKE ?"
        params: list[Any] = [f"%{query}%"]

        if entity_type:
            sql += " AND entity_type = ?"
            params.append(entity_type)

        sql += " ORDER BY access_count DESC, created_at DESC LIMIT ?"
        params.append(limit)

        entities = []
        async with self._db.execute(sql, params) as cursor:
            async for row in cursor:
                entities.append(self._row_to_entity(row))

        return entities

    async def get_all_entities(
        self,
        entity_type: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0
    ) -> list[Entity]:
        """Get all entities with optional filtering"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        if entity_type:
            sql = "SELECT * FROM entities WHERE entity_type = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (entity_type, limit, offset)
        else:
            sql = "SELECT * FROM entities ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (limit, offset)

        entities = []
        async with self._db.execute(sql, params) as cursor:
            async for row in cursor:
                entities.append(self._row_to_entity(row))

        return entities

    async def update_entity(
        self,
        entity_id: str,
        name: Optional[str] = None,
        entity_type: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None
    ) -> Optional[Entity]:
        """Update an existing entity"""
        async with self.transaction() as db:
            updates = []
            params = []

            if name is not None:
                updates.append("name = ?")
                params.append(name)
            if entity_type is not None:
                updates.append("entity_type = ?")
                params.append(entity_type)
            if metadata is not None:
                updates.append("metadata = ?")
                params.append(json.dumps(metadata))

            if not updates:
                return await self.get_entity(entity_id)

            updates.append("updated_at = ?")
            params.append(format_timestamp(utc_now()))
            params.append(entity_id)

            await db.execute(
                f"UPDATE entities SET {', '.join(updates)} WHERE id = ?",
                params
            )

        return await self.get_entity(entity_id)

    async def delete_entity(self, entity_id: str) -> bool:
        """Delete entity and all related data (cascades)"""
        async with self.transaction() as db:
            cursor = await db.execute(
                "DELETE FROM entities WHERE id = ?",
                (entity_id,)
            )
            return cursor.rowcount > 0

    # =========================================================================
    # Observation Operations
    # =========================================================================

    async def create_observation(
        self,
        entity_id: str,
        content: str,
        source: str = "chat",
        confidence: float = 1.0,
        metadata: Optional[dict[str, Any]] = None,
        deduplicate: bool = True
    ) -> Observation:
        """Add an observation to an entity"""
        observation = Observation(
            id=generate_id("o_"),
            entity_id=entity_id,
            content=content,
            source=source,
            confidence=confidence,
            metadata=metadata or {}
        )

        async with self.transaction() as db:
            # Check entity exists
            async with db.execute(
                "SELECT COUNT(*) FROM entities WHERE id = ?",
                (entity_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row[0] == 0:
                    raise ValueError(f"Entity not found: {entity_id}")

            # Check for duplicate
            if deduplicate:
                async with db.execute(
                    "SELECT id FROM observations WHERE entity_id = ? AND content_hash = ?",
                    (entity_id, observation.content_hash)
                ) as cursor:
                    existing = await cursor.fetchone()
                    if existing:
                        # Update confidence if higher
                        await db.execute(
                            "UPDATE observations SET confidence = MAX(confidence, ?) WHERE id = ?",
                            (confidence, existing[0])
                        )
                        observation.id = existing[0]
                        return observation

            # Check observation limit per entity
            async with db.execute(
                "SELECT COUNT(*) FROM observations WHERE entity_id = ?",
                (entity_id,)
            ) as cursor:
                row = await cursor.fetchone()
                if row[0] >= self.config.storage.max_observations_per_entity:
                    # Remove oldest low-confidence observation
                    await db.execute(
                        """
                        DELETE FROM observations WHERE id = (
                            SELECT id FROM observations
                            WHERE entity_id = ?
                            ORDER BY confidence ASC, timestamp ASC
                            LIMIT 1
                        )
                        """,
                        (entity_id,)
                    )

            await db.execute(
                """
                INSERT INTO observations
                (id, entity_id, content, timestamp, source, confidence, metadata, content_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    observation.id,
                    observation.entity_id,
                    observation.content,
                    format_timestamp(observation.timestamp),
                    observation.source,
                    observation.confidence,
                    json.dumps(observation.metadata),
                    observation.content_hash
                )
            )

        return observation

    async def get_observations(
        self,
        entity_id: str,
        limit: int = 100
    ) -> list[Observation]:
        """Get observations for an entity"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        observations = []
        async with self._db.execute(
            """
            SELECT * FROM observations
            WHERE entity_id = ?
            ORDER BY confidence DESC, timestamp DESC
            LIMIT ?
            """,
            (entity_id, limit)
        ) as cursor:
            async for row in cursor:
                observations.append(self._row_to_observation(row))

        return observations

    async def search_observations(
        self,
        query: str,
        entity_id: Optional[str] = None,
        limit: int = 50
    ) -> list[Observation]:
        """Full-text search on observations"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        observations = []

        if entity_id:
            sql = """
                SELECT o.* FROM observations o
                JOIN observations_fts fts ON o.rowid = fts.rowid
                WHERE fts.content MATCH ? AND o.entity_id = ?
                ORDER BY rank
                LIMIT ?
            """
            params = (query, entity_id, limit)
        else:
            sql = """
                SELECT o.* FROM observations o
                JOIN observations_fts fts ON o.rowid = fts.rowid
                WHERE fts.content MATCH ?
                ORDER BY rank
                LIMIT ?
            """
            params = (query, limit)

        try:
            async with self._db.execute(sql, params) as cursor:
                async for row in cursor:
                    observations.append(self._row_to_observation(row))
        except aiosqlite.OperationalError:
            # FTS query syntax error, fall back to LIKE
            if entity_id:
                sql = "SELECT * FROM observations WHERE content LIKE ? AND entity_id = ? LIMIT ?"
                params = (f"%{query}%", entity_id, limit)
            else:
                sql = "SELECT * FROM observations WHERE content LIKE ? LIMIT ?"
                params = (f"%{query}%", limit)

            async with self._db.execute(sql, params) as cursor:
                async for row in cursor:
                    observations.append(self._row_to_observation(row))

        return observations

    async def delete_observation(self, observation_id: str) -> bool:
        """Delete an observation"""
        async with self.transaction() as db:
            cursor = await db.execute(
                "DELETE FROM observations WHERE id = ?",
                (observation_id,)
            )
            return cursor.rowcount > 0

    # =========================================================================
    # Relation Operations
    # =========================================================================

    async def create_relation(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str,
        confidence: float = 1.0,
        metadata: Optional[dict[str, Any]] = None,
        bidirectional: bool = False
    ) -> Relation:
        """Create a relation between entities"""
        relation = Relation(
            id=generate_id("r_"),
            from_entity=from_entity,
            to_entity=to_entity,
            relation_type=relation_type,
            confidence=confidence,
            metadata=metadata or {},
            bidirectional=bidirectional
        )

        async with self.transaction() as db:
            # Verify both entities exist
            for eid in (from_entity, to_entity):
                async with db.execute(
                    "SELECT COUNT(*) FROM entities WHERE id = ?",
                    (eid,)
                ) as cursor:
                    row = await cursor.fetchone()
                    if row[0] == 0:
                        raise ValueError(f"Entity not found: {eid}")

            # Check relation limit
            async with db.execute("SELECT COUNT(*) FROM relations") as cursor:
                row = await cursor.fetchone()
                if row[0] >= self.config.storage.max_relations:
                    raise ValueError(f"Maximum relation limit ({self.config.storage.max_relations}) reached")

            # Insert or update relation
            await db.execute(
                """
                INSERT INTO relations
                (id, from_entity, to_entity, relation_type, created_at, confidence, metadata, bidirectional)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (from_entity, to_entity, relation_type) DO UPDATE SET
                    confidence = MAX(confidence, excluded.confidence),
                    metadata = excluded.metadata
                """,
                (
                    relation.id,
                    relation.from_entity,
                    relation.to_entity,
                    relation.relation_type,
                    format_timestamp(relation.created_at),
                    relation.confidence,
                    json.dumps(relation.metadata),
                    1 if relation.bidirectional else 0
                )
            )

            # Create reverse relation if bidirectional
            if bidirectional:
                await db.execute(
                    """
                    INSERT INTO relations
                    (id, from_entity, to_entity, relation_type, created_at, confidence, metadata, bidirectional)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT (from_entity, to_entity, relation_type) DO NOTHING
                    """,
                    (
                        generate_id("r_"),
                        relation.to_entity,
                        relation.from_entity,
                        relation.relation_type,
                        format_timestamp(relation.created_at),
                        relation.confidence,
                        json.dumps(relation.metadata),
                        1
                    )
                )

        return relation

    async def get_relations(
        self,
        entity_id: str,
        direction: str = "both",
        relation_type: Optional[str] = None
    ) -> list[Relation]:
        """Get relations for an entity"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        relations = []

        if direction in ("out", "both"):
            sql = "SELECT * FROM relations WHERE from_entity = ?"
            params: list[Any] = [entity_id]
            if relation_type:
                sql += " AND relation_type = ?"
                params.append(relation_type)

            async with self._db.execute(sql, params) as cursor:
                async for row in cursor:
                    relations.append(self._row_to_relation(row))

        if direction in ("in", "both"):
            sql = "SELECT * FROM relations WHERE to_entity = ?"
            params = [entity_id]
            if relation_type:
                sql += " AND relation_type = ?"
                params.append(relation_type)

            async with self._db.execute(sql, params) as cursor:
                async for row in cursor:
                    rel = self._row_to_relation(row)
                    if rel not in relations:
                        relations.append(rel)

        return relations

    async def delete_relation(
        self,
        from_entity: str,
        to_entity: str,
        relation_type: str
    ) -> bool:
        """Delete a specific relation"""
        async with self.transaction() as db:
            cursor = await db.execute(
                """
                DELETE FROM relations
                WHERE from_entity = ? AND to_entity = ? AND relation_type = ?
                """,
                (from_entity, to_entity, relation_type)
            )
            return cursor.rowcount > 0

    # =========================================================================
    # Graph Traversal
    # =========================================================================

    async def multi_hop_search(
        self,
        start_entity: str,
        max_hops: int = 2,
        relation_type: Optional[str] = None
    ) -> SearchResult:
        """Traverse graph from starting entity"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        start_time = time.perf_counter()

        visited: set[str] = set()
        to_visit: set[str] = {start_entity}

        for _ in range(max_hops):
            next_visit: set[str] = set()

            for entity_id in to_visit:
                if entity_id in visited:
                    continue
                visited.add(entity_id)

                # Get connected entities
                relations = await self.get_relations(entity_id, relation_type=relation_type)
                for rel in relations:
                    if rel.from_entity == entity_id:
                        next_visit.add(rel.to_entity)
                    if rel.to_entity == entity_id:
                        next_visit.add(rel.from_entity)

            to_visit = next_visit - visited

        visited.update(to_visit)

        # Collect results
        entities = []
        observations = []
        relations = []

        for entity_id in visited:
            entity = await self.get_entity(entity_id)
            if entity:
                entities.append(entity)
                obs = await self.get_observations(entity_id, limit=10)
                observations.extend(obs)

        # Get relations between visited entities
        entity_ids = tuple(visited)
        if entity_ids:
            placeholders = ",".join("?" * len(entity_ids))
            async with self._db.execute(
                f"""
                SELECT * FROM relations
                WHERE from_entity IN ({placeholders}) AND to_entity IN ({placeholders})
                """,
                entity_ids + entity_ids
            ) as cursor:
                async for row in cursor:
                    relations.append(self._row_to_relation(row))

        elapsed = (time.perf_counter() - start_time) * 1000

        return SearchResult(
            entities=entities,
            observations=observations,
            relations=relations,
            total_count=len(entities),
            query=f"multi_hop from {start_entity}",
            search_time_ms=elapsed
        )

    # =========================================================================
    # Search
    # =========================================================================

    async def search(
        self,
        query: str,
        max_results: int = 20
    ) -> SearchResult:
        """Search across entities and observations"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        start_time = time.perf_counter()

        # Search entities
        entities = await self.search_entities(query, limit=max_results)

        # Search observations
        observations = await self.search_observations(query, limit=max_results)

        # Get entities from matching observations
        entity_ids = set(o.entity_id for o in observations)
        for eid in entity_ids:
            entity = await self.get_entity(eid)
            if entity and entity not in entities:
                entities.append(entity)

        # Get relations between found entities
        relations = []
        all_entity_ids = tuple(e.id for e in entities)
        if all_entity_ids:
            placeholders = ",".join("?" * len(all_entity_ids))
            async with self._db.execute(
                f"""
                SELECT * FROM relations
                WHERE from_entity IN ({placeholders}) OR to_entity IN ({placeholders})
                LIMIT ?
                """,
                all_entity_ids + all_entity_ids + (max_results,)
            ) as cursor:
                async for row in cursor:
                    relations.append(self._row_to_relation(row))

        elapsed = (time.perf_counter() - start_time) * 1000

        return SearchResult(
            entities=entities,
            observations=observations,
            relations=relations,
            total_count=len(entities) + len(observations),
            query=query,
            search_time_ms=elapsed
        )

    # =========================================================================
    # Statistics
    # =========================================================================

    async def get_stats(self) -> MemoryStats:
        """Get memory store statistics"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        stats = MemoryStats()

        # Count entities
        async with self._db.execute("SELECT COUNT(*) FROM entities") as cursor:
            row = await cursor.fetchone()
            stats.entity_count = row[0]

        # Count observations
        async with self._db.execute("SELECT COUNT(*) FROM observations") as cursor:
            row = await cursor.fetchone()
            stats.observation_count = row[0]

        # Count relations
        async with self._db.execute("SELECT COUNT(*) FROM relations") as cursor:
            row = await cursor.fetchone()
            stats.relation_count = row[0]

        # Database size
        stats.database_size_bytes = self.db_path.stat().st_size if self.db_path.exists() else 0

        # Entity type breakdown
        async with self._db.execute(
            "SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type"
        ) as cursor:
            async for row in cursor:
                stats.entity_types[row[0]] = row[1]

        # Relation type breakdown
        async with self._db.execute(
            "SELECT relation_type, COUNT(*) FROM relations GROUP BY relation_type"
        ) as cursor:
            async for row in cursor:
                stats.relation_types[row[0]] = row[1]

        # Date range
        async with self._db.execute(
            "SELECT MIN(created_at), MAX(created_at) FROM entities"
        ) as cursor:
            row = await cursor.fetchone()
            if row[0]:
                stats.oldest_entity = parse_timestamp(row[0])
            if row[1]:
                stats.newest_entity = parse_timestamp(row[1])

        # Last compaction/backup from metadata
        async with self._db.execute(
            "SELECT key, value FROM store_metadata WHERE key IN ('last_compaction', 'last_backup')"
        ) as cursor:
            async for row in cursor:
                if row[0] == "last_compaction" and row[1]:
                    stats.last_compaction = parse_timestamp(row[1])
                if row[0] == "last_backup" and row[1]:
                    stats.last_backup = parse_timestamp(row[1])

        return stats

    # =========================================================================
    # ISON Export
    # =========================================================================

    async def export_to_ison(self) -> str:
        """Export entire memory to ISON format"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        lines = [
            "# ISON Memory Export",
            f"# Exported: {format_timestamp(utc_now())}",
            f"# Database: {self.db_path}",
            "",
            "meta.memory",
            "version format exported_at entity_count observation_count relation_count",
        ]

        stats = await self.get_stats()
        lines.append(
            f"1.0 ison {format_timestamp(utc_now())} "
            f"{stats.entity_count} {stats.observation_count} {stats.relation_count}"
        )
        lines.append("")

        # Export entities
        lines.append("table.entities")
        lines.append("id:ref name type created_at access_count")

        async with self._db.execute("SELECT * FROM entities ORDER BY created_at") as cursor:
            async for row in cursor:
                entity = self._row_to_entity(row)
                name_escaped = entity.name.replace('"', '\\"')
                lines.append(
                    f":{entity.id} \"{name_escaped}\" {entity.entity_type} "
                    f"{format_timestamp(entity.created_at)} {entity.access_count}"
                )

        lines.append("")

        # Export observations
        lines.append("table.observations")
        lines.append("id:ref entity_id:ref content timestamp source confidence:float")

        async with self._db.execute("SELECT * FROM observations ORDER BY timestamp") as cursor:
            async for row in cursor:
                obs = self._row_to_observation(row)
                content_escaped = obs.content.replace('"', '\\"').replace('\n', '\\n')
                lines.append(
                    f":{obs.id} :{obs.entity_id} \"{content_escaped}\" "
                    f"{format_timestamp(obs.timestamp)} {obs.source} {obs.confidence}"
                )

        lines.append("")

        # Export relations
        lines.append("table.relations")
        lines.append("id:ref from_entity:ref to_entity:ref relation_type created_at confidence:float")

        async with self._db.execute("SELECT * FROM relations ORDER BY created_at") as cursor:
            async for row in cursor:
                rel = self._row_to_relation(row)
                lines.append(
                    f":{rel.id} :{rel.from_entity} :{rel.to_entity} "
                    f"{rel.relation_type} {format_timestamp(rel.created_at)} {rel.confidence}"
                )

        return "\n".join(lines)

    async def export_to_isonl(self) -> str:
        """Export entire memory to ISONL streaming format"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        lines = []

        # Export entities
        async with self._db.execute("SELECT * FROM entities ORDER BY created_at") as cursor:
            async for row in cursor:
                entity = self._row_to_entity(row)
                name_escaped = entity.name.replace('"', '\\"')
                lines.append(
                    f"entities|id name type created_at|"
                    f":{entity.id} \"{name_escaped}\" {entity.entity_type} "
                    f"{format_timestamp(entity.created_at)}"
                )

        # Export observations
        async with self._db.execute("SELECT * FROM observations ORDER BY timestamp") as cursor:
            async for row in cursor:
                obs = self._row_to_observation(row)
                content_escaped = obs.content.replace('"', '\\"').replace('\n', '\\n')
                lines.append(
                    f"observations|id entity_id content timestamp source confidence|"
                    f":{obs.id} :{obs.entity_id} \"{content_escaped}\" "
                    f"{format_timestamp(obs.timestamp)} {obs.source} {obs.confidence}"
                )

        # Export relations
        async with self._db.execute("SELECT * FROM relations ORDER BY created_at") as cursor:
            async for row in cursor:
                rel = self._row_to_relation(row)
                lines.append(
                    f"relations|id from_entity to_entity relation_type created_at confidence|"
                    f":{rel.id} :{rel.from_entity} :{rel.to_entity} "
                    f"{rel.relation_type} {format_timestamp(rel.created_at)} {rel.confidence}"
                )

        return "\n".join(lines)

    async def export_to_isongraph(self) -> str:
        """Export to ISONGraph format with enhanced semantics"""
        if not self._db:
            raise RuntimeError("Store not initialized")

        lines = [
            "# ISONGraph Memory Export",
            f"# Exported: {format_timestamp(utc_now())}",
            "",
            "meta.memory",
            "version format graph_type",
            "1.0 isongraph property_graph",
            "",
        ]

        # Export nodes by type
        entity_types: dict[str, list[Entity]] = {}
        async with self._db.execute("SELECT * FROM entities ORDER BY entity_type, created_at") as cursor:
            async for row in cursor:
                entity = self._row_to_entity(row)
                if entity.entity_type not in entity_types:
                    entity_types[entity.entity_type] = []
                entity_types[entity.entity_type].append(entity)

        for etype, entities in entity_types.items():
            lines.append(f"nodes.{etype}")
            lines.append("id name created_at access_count")
            for entity in entities:
                name_escaped = entity.name.replace('"', '\\"')
                lines.append(
                    f":{entity.id} \"{name_escaped}\" "
                    f"{format_timestamp(entity.created_at)} {entity.access_count}"
                )
            lines.append("")

        # Export edges by type
        relation_types: dict[str, list[Relation]] = {}
        async with self._db.execute("SELECT * FROM relations ORDER BY relation_type, created_at") as cursor:
            async for row in cursor:
                rel = self._row_to_relation(row)
                if rel.relation_type not in relation_types:
                    relation_types[rel.relation_type] = []
                relation_types[rel.relation_type].append(rel)

        for rtype, relations in relation_types.items():
            lines.append(f"edges.{rtype}")
            lines.append("source:ref target:ref created_at confidence:float")
            for rel in relations:
                lines.append(
                    f":{rel.from_entity} :{rel.to_entity} "
                    f"{format_timestamp(rel.created_at)} {rel.confidence}"
                )
            lines.append("")

        # Export observations as node properties
        lines.append("# Observations (attached to nodes)")
        lines.append("table.observations")
        lines.append("node:ref content timestamp source confidence:float")

        async with self._db.execute("SELECT * FROM observations ORDER BY entity_id, timestamp") as cursor:
            async for row in cursor:
                obs = self._row_to_observation(row)
                content_escaped = obs.content.replace('"', '\\"').replace('\n', '\\n')
                lines.append(
                    f":{obs.entity_id} \"{content_escaped}\" "
                    f"{format_timestamp(obs.timestamp)} {obs.source} {obs.confidence}"
                )

        return "\n".join(lines)

    # =========================================================================
    # Internal Helpers
    # =========================================================================

    async def _count_entities(self, db: aiosqlite.Connection) -> int:
        """Count total entities"""
        async with db.execute("SELECT COUNT(*) FROM entities") as cursor:
            row = await cursor.fetchone()
            return row[0]

    def _row_to_entity(self, row: aiosqlite.Row) -> Entity:
        """Convert database row to Entity"""
        return Entity(
            id=row["id"],
            name=row["name"],
            entity_type=row["entity_type"],
            created_at=parse_timestamp(row["created_at"]),
            updated_at=parse_timestamp(row["updated_at"]) if row["updated_at"] else None,
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            access_count=row["access_count"] or 0,
            last_accessed=parse_timestamp(row["last_accessed"]) if row["last_accessed"] else None,
        )

    def _row_to_observation(self, row: aiosqlite.Row) -> Observation:
        """Convert database row to Observation"""
        return Observation(
            id=row["id"],
            entity_id=row["entity_id"],
            content=row["content"],
            timestamp=parse_timestamp(row["timestamp"]),
            source=row["source"],
            confidence=row["confidence"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            content_hash=row["content_hash"],
            access_count=row["access_count"] or 0,
        )

    def _row_to_relation(self, row: aiosqlite.Row) -> Relation:
        """Convert database row to Relation"""
        return Relation(
            id=row["id"],
            from_entity=row["from_entity"],
            to_entity=row["to_entity"],
            relation_type=row["relation_type"],
            created_at=parse_timestamp(row["created_at"]),
            confidence=row["confidence"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            bidirectional=bool(row["bidirectional"]),
            access_count=row["access_count"] or 0,
        )
