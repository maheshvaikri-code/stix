"""
ISONCache Schema
================

Data structures for the cache system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Union


class EvictionPolicy(Enum):
    """Cache eviction policies"""
    LRU = "lru"           # Least Recently Used
    LFU = "lfu"           # Least Frequently Used
    FIFO = "fifo"         # First In First Out
    TTL = "ttl"           # Time To Live (expire only)
    RANDOM = "random"     # Random eviction
    PRIORITY = "priority" # Based on priority score


class ValueType(Enum):
    """Types of cached values"""
    OBJECT = "object"     # Single object/dict
    TABLE = "table"       # List of objects with same schema
    GRAPH = "graph"       # Graph with entities and relations
    RAW = "raw"           # Raw ISON string
    EMBEDDING = "embedding"  # Vector embedding


class Priority(Enum):
    """Retrieval priority for budget operations"""
    HITS = "hits"         # Most accessed first
    RECENT = "recent"     # Most recently accessed first
    OLDEST = "oldest"     # Oldest first
    TOKENS = "tokens"     # Smallest token count first
    PRIORITY = "priority" # Explicit priority value


@dataclass
class CacheEntry:
    """A cached entry with metadata"""
    key: str
    value: Any
    value_type: ValueType
    tokens: int
    created_at: datetime
    accessed_at: datetime
    expires_at: Optional[datetime] = None
    hits: int = 0
    priority: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if entry has expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def ttl_seconds(self) -> Optional[int]:
        """Remaining TTL in seconds"""
        if self.expires_at is None:
            return None
        remaining = (self.expires_at - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))

    def touch(self) -> None:
        """Update access time and increment hits"""
        self.accessed_at = datetime.now(timezone.utc)
        self.hits += 1


@dataclass
class CacheStats:
    """Cache statistics"""
    total_entries: int = 0
    total_tokens: int = 0
    total_hits: int = 0
    total_misses: int = 0
    total_evictions: int = 0
    memory_bytes: int = 0
    max_memory_bytes: int = 0
    entries_by_type: Dict[str, int] = field(default_factory=dict)
    oldest_entry: Optional[datetime] = None
    newest_entry: Optional[datetime] = None

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as percentage"""
        total = self.total_hits + self.total_misses
        if total == 0:
            return 0.0
        return (self.total_hits / total) * 100

    @property
    def memory_usage_percent(self) -> float:
        """Memory usage as percentage"""
        if self.max_memory_bytes == 0:
            return 0.0
        return (self.memory_bytes / self.max_memory_bytes) * 100


@dataclass
class CacheConfig:
    """Cache configuration"""
    # Memory limits
    max_memory_mb: int = 1024
    max_entries: int = 100000

    # TTL settings
    default_ttl_seconds: int = 3600  # 1 hour
    min_ttl_seconds: int = 1
    max_ttl_seconds: int = 86400 * 30  # 30 days

    # Eviction
    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    eviction_batch_size: int = 100

    # Token settings
    default_token_budget: int = 4000
    token_model: str = "cl100k_base"  # GPT-4/Claude tokenizer

    # Persistence
    persist_path: Optional[str] = None
    persist_interval_seconds: int = 300

    # Server settings
    host: str = "127.0.0.1"
    port: int = 6380  # Different from Redis default
    enable_mcp: bool = True
    enable_http: bool = False
    enable_resp: bool = False


@dataclass
class BudgetResult:
    """Result of token-budgeted retrieval"""
    ison: str                          # ISON-formatted output
    tokens_used: int                   # Total tokens used
    tokens_budget: int                 # Original budget
    keys_included: List[str]           # Keys that fit in budget
    keys_excluded: List[str]           # Keys that didn't fit
    entries_count: int                 # Number of entries returned
    truncated: bool                    # Whether results were truncated

    @property
    def tokens_remaining(self) -> int:
        """Remaining token budget"""
        return max(0, self.tokens_budget - self.tokens_used)

    @property
    def utilization(self) -> float:
        """Budget utilization percentage"""
        if self.tokens_budget == 0:
            return 0.0
        return (self.tokens_used / self.tokens_budget) * 100


@dataclass
class GraphEntry:
    """A cached graph with entities and relations"""
    key: str
    entities: List[Dict[str, Any]]
    relations: List[Dict[str, Any]]
    observations: List[Dict[str, Any]] = field(default_factory=list)
    tokens: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    hits: int = 0

    @property
    def entity_count(self) -> int:
        return len(self.entities)

    @property
    def relation_count(self) -> int:
        return len(self.relations)

    def touch(self) -> None:
        """Update access time and increment hits"""
        self.accessed_at = datetime.now(timezone.utc)
        self.hits += 1


@dataclass
class EmbeddingEntry:
    """A cached embedding vector"""
    key: str
    text: str
    vector: List[float]
    dimension: int
    model: str
    tokens: int
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def vector_norm(self) -> float:
        """L2 norm of the vector"""
        import math
        return math.sqrt(sum(x * x for x in self.vector))


@dataclass
class SimilarityResult:
    """Result of similarity search"""
    key: str
    text: str
    score: float
    distance: float
    tokens: int
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TraversalResult:
    """Result of graph traversal"""
    ison: str                          # ISON-formatted output
    tokens_used: int
    entities_included: List[str]       # Entity IDs included
    relations_included: int            # Number of relations
    hops_traversed: int               # Actual hops performed
    truncated: bool                    # Whether results were truncated


# Type aliases
Key = str
Value = Union[Dict[str, Any], List[Dict[str, Any]], str]
Vector = List[float]
NodeRef = tuple[str, Union[int, str]]
