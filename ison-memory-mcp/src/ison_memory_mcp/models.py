"""
Data Models for ISON Memory MCP Server

Defines the core data structures for entities, observations, and relations
with full validation and serialization support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional, Union
from enum import Enum
import hashlib
import json


class EntityType(str, Enum):
    """Standard entity types"""
    PERSON = "person"
    PROJECT = "project"
    ORGANIZATION = "organization"
    TOOL = "tool"
    CONCEPT = "concept"
    LOCATION = "location"
    EVENT = "event"
    DOCUMENT = "document"
    CODE = "code"
    TASK = "task"
    PREFERENCE = "preference"
    CUSTOM = "custom"


class RelationType(str, Enum):
    """Standard relation types"""
    CREATOR_OF = "CREATOR_OF"
    MEMBER_OF = "MEMBER_OF"
    LEADS = "LEADS"
    USES = "USES"
    WORKS_ON = "WORKS_ON"
    RELATED_TO = "RELATED_TO"
    DEPENDS_ON = "DEPENDS_ON"
    INTEGRATES = "INTEGRATES"
    LOCATED_IN = "LOCATED_IN"
    OCCURRED_AT = "OCCURRED_AT"
    IS_A = "IS_A"
    HAS_PART = "HAS_PART"
    KNOWS = "KNOWS"
    PREFERS = "PREFERS"
    MENTIONED_IN = "MENTIONED_IN"
    SUCCESSOR_OF = "SUCCESSOR_OF"
    SIMILAR_TO = "SIMILAR_TO"


class ObservationSource(str, Enum):
    """Source of observations"""
    CHAT = "chat"
    CODE = "code"
    MANUAL = "manual"
    IMPORT = "import"
    INFERENCE = "inference"
    SYSTEM = "system"


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID"""
    import uuid
    short_uuid = uuid.uuid4().hex[:12]
    return f"{prefix}{short_uuid}" if prefix else short_uuid


def utc_now() -> datetime:
    """Get current UTC timestamp"""
    return datetime.now(timezone.utc)


def format_timestamp(dt: datetime) -> str:
    """Format datetime to ISO 8601"""
    return dt.isoformat()


def parse_timestamp(s: str) -> datetime:
    """Parse ISO 8601 timestamp"""
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


@dataclass
class Entity:
    """
    Represents a node in the knowledge graph.

    Entities are the primary objects that Claude remembers, such as
    people, projects, tools, concepts, etc.
    """
    id: str
    name: str
    entity_type: str
    created_at: datetime = field(default_factory=utc_now)
    updated_at: Optional[datetime] = None
    metadata: dict[str, Any] = field(default_factory=dict)

    # Tracking fields
    access_count: int = 0
    last_accessed: Optional[datetime] = None

    def __post_init__(self) -> None:
        if not self.id:
            self.id = generate_id("e_")
        if isinstance(self.created_at, str):
            self.created_at = parse_timestamp(self.created_at)
        if isinstance(self.updated_at, str):
            self.updated_at = parse_timestamp(self.updated_at)
        if isinstance(self.last_accessed, str):
            self.last_accessed = parse_timestamp(self.last_accessed)

    @property
    def ref(self) -> str:
        """Get ISON reference string"""
        return f":{self.entity_type}:{self.id}"

    @property
    def ref_tuple(self) -> tuple[str, str]:
        """Get reference as tuple (type, id)"""
        return (self.entity_type, self.id)

    def touch(self) -> None:
        """Update access tracking"""
        self.access_count += 1
        self.last_accessed = utc_now()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "entity_type": self.entity_type,
            "created_at": format_timestamp(self.created_at),
            "updated_at": format_timestamp(self.updated_at) if self.updated_at else None,
            "metadata": self.metadata,
            "access_count": self.access_count,
            "last_accessed": format_timestamp(self.last_accessed) if self.last_accessed else None,
        }

    def to_ison_row(self) -> str:
        """Convert to ISON table row"""
        meta_json = json.dumps(self.metadata) if self.metadata else "{}"
        return (
            f":{self.id} "
            f'"{self.name}" '
            f"{self.entity_type} "
            f"{format_timestamp(self.created_at)} "
            f"{self.access_count}"
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Entity":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            name=data["name"],
            entity_type=data.get("entity_type", data.get("type", "concept")),
            created_at=data.get("created_at", utc_now()),
            updated_at=data.get("updated_at"),
            metadata=data.get("metadata", {}),
            access_count=data.get("access_count", 0),
            last_accessed=data.get("last_accessed"),
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Entity):
            return self.id == other.id
        return False


@dataclass
class Observation:
    """
    Represents an atomic fact about an entity.

    Observations are individual pieces of information that Claude
    learns about entities over time.
    """
    id: str
    entity_id: str
    content: str
    timestamp: datetime = field(default_factory=utc_now)
    source: str = ObservationSource.CHAT.value
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Content hash for deduplication
    content_hash: Optional[str] = None

    # Tracking
    access_count: int = 0

    def __post_init__(self) -> None:
        if not self.id:
            self.id = generate_id("o_")
        if isinstance(self.timestamp, str):
            self.timestamp = parse_timestamp(self.timestamp)
        if not self.content_hash:
            self.content_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute content hash for deduplication"""
        normalized = self.content.strip().lower()
        return hashlib.md5(normalized.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "entity_id": self.entity_id,
            "content": self.content,
            "timestamp": format_timestamp(self.timestamp),
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "content_hash": self.content_hash,
            "access_count": self.access_count,
        }

    def to_ison_row(self) -> str:
        """Convert to ISON table row"""
        content_escaped = self.content.replace('"', '\\"')
        return (
            f":{self.id} "
            f":{self.entity_id} "
            f'"{content_escaped}" '
            f"{format_timestamp(self.timestamp)} "
            f"{self.source} "
            f"{self.confidence}"
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Observation":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            entity_id=data["entity_id"],
            content=data["content"],
            timestamp=data.get("timestamp", utc_now()),
            source=data.get("source", ObservationSource.CHAT.value),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
            content_hash=data.get("content_hash"),
            access_count=data.get("access_count", 0),
        )

    def is_duplicate_of(self, other: "Observation") -> bool:
        """Check if this is a duplicate of another observation"""
        return (
            self.entity_id == other.entity_id and
            self.content_hash == other.content_hash
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Observation):
            return self.id == other.id
        return False


@dataclass
class Relation:
    """
    Represents a typed connection between two entities.

    Relations define how entities are connected in the knowledge graph,
    such as "person WORKS_ON project" or "tool DEPENDS_ON library".
    """
    id: str
    from_entity: str
    to_entity: str
    relation_type: str
    created_at: datetime = field(default_factory=utc_now)
    confidence: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)

    # Bidirectional support
    bidirectional: bool = False

    # Tracking
    access_count: int = 0

    def __post_init__(self) -> None:
        if not self.id:
            self.id = generate_id("r_")
        if isinstance(self.created_at, str):
            self.created_at = parse_timestamp(self.created_at)

    @property
    def key(self) -> tuple[str, str, str]:
        """Get unique key for this relation"""
        return (self.relation_type, self.from_entity, self.to_entity)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "from_entity": self.from_entity,
            "to_entity": self.to_entity,
            "relation_type": self.relation_type,
            "created_at": format_timestamp(self.created_at),
            "confidence": self.confidence,
            "metadata": self.metadata,
            "bidirectional": self.bidirectional,
            "access_count": self.access_count,
        }

    def to_ison_row(self) -> str:
        """Convert to ISON table row"""
        return (
            f":{self.id} "
            f":{self.from_entity} "
            f":{self.to_entity} "
            f"{self.relation_type} "
            f"{format_timestamp(self.created_at)} "
            f"{self.confidence}"
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Relation":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            from_entity=data["from_entity"],
            to_entity=data["to_entity"],
            relation_type=data.get("relation_type", data.get("type", "RELATED_TO")),
            created_at=data.get("created_at", utc_now()),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {}),
            bidirectional=data.get("bidirectional", False),
            access_count=data.get("access_count", 0),
        )

    def __hash__(self) -> int:
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Relation):
            return self.id == other.id
        return False


@dataclass
class SearchResult:
    """Result from a memory search"""
    entities: list[Entity] = field(default_factory=list)
    observations: list[Observation] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)
    total_count: int = 0
    query: str = ""
    search_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entities": [e.to_dict() for e in self.entities],
            "observations": [o.to_dict() for o in self.observations],
            "relations": [r.to_dict() for r in self.relations],
            "total_count": self.total_count,
            "query": self.query,
            "search_time_ms": self.search_time_ms,
        }

    def to_ison(self) -> str:
        """Convert to ISON format"""
        lines = [
            "# Search Results",
            f"# Query: {self.query}",
            f"# Found: {self.total_count} items in {self.search_time_ms:.2f}ms",
            "",
        ]

        if self.entities:
            lines.append("table.entities")
            lines.append("id name type created_at access_count")
            for e in self.entities:
                lines.append(e.to_ison_row())
            lines.append("")

        if self.observations:
            lines.append("table.observations")
            lines.append("id entity_id content timestamp source confidence")
            for o in self.observations:
                lines.append(o.to_ison_row())
            lines.append("")

        if self.relations:
            lines.append("table.relations")
            lines.append("id from_entity to_entity relation_type created_at confidence")
            for r in self.relations:
                lines.append(r.to_ison_row())

        return "\n".join(lines)


@dataclass
class MemoryStats:
    """Statistics about the memory store"""
    entity_count: int = 0
    observation_count: int = 0
    relation_count: int = 0
    database_size_bytes: int = 0
    last_compaction: Optional[datetime] = None
    last_backup: Optional[datetime] = None
    oldest_entity: Optional[datetime] = None
    newest_entity: Optional[datetime] = None

    # Entity type breakdown
    entity_types: dict[str, int] = field(default_factory=dict)

    # Relation type breakdown
    relation_types: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "entity_count": self.entity_count,
            "observation_count": self.observation_count,
            "relation_count": self.relation_count,
            "database_size_bytes": self.database_size_bytes,
            "database_size_mb": round(self.database_size_bytes / (1024 * 1024), 2),
            "last_compaction": format_timestamp(self.last_compaction) if self.last_compaction else None,
            "last_backup": format_timestamp(self.last_backup) if self.last_backup else None,
            "oldest_entity": format_timestamp(self.oldest_entity) if self.oldest_entity else None,
            "newest_entity": format_timestamp(self.newest_entity) if self.newest_entity else None,
            "entity_types": self.entity_types,
            "relation_types": self.relation_types,
        }

    def to_ison(self) -> str:
        """Convert to ISON format"""
        lines = [
            "object.stats",
            "entity_count observation_count relation_count database_size_mb",
            f"{self.entity_count} {self.observation_count} {self.relation_count} "
            f"{round(self.database_size_bytes / (1024 * 1024), 2)}",
            "",
            "table.entity_types",
            "type count",
        ]
        for etype, count in sorted(self.entity_types.items()):
            lines.append(f"{etype} {count}")

        lines.append("")
        lines.append("table.relation_types")
        lines.append("type count")
        for rtype, count in sorted(self.relation_types.items()):
            lines.append(f"{rtype} {count}")

        return "\n".join(lines)
