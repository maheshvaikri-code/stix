"""
ISONCache - Core Cache Implementation
=====================================

Token-efficient in-memory cache with ISON serialization.
"""

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Set, Union, Pattern
from collections import OrderedDict
from threading import RLock
import fnmatch
import re
import random

from .schema import (
    CacheEntry, CacheStats, CacheConfig, BudgetResult,
    EvictionPolicy, ValueType, Priority
)
from .token_manager import TokenManager, TokenBudget
from .serializer import ISONSerializer


class ISONCache:
    """
    Token-efficient cache for LLM applications.

    Features:
    - Automatic token counting and budgeting
    - ISON-formatted output ready for LLM context
    - Multiple eviction policies (LRU, LFU, TTL, etc.)
    - Pattern-based key matching
    - Batch operations with token budgets
    """

    def __init__(
        self,
        config: Optional[CacheConfig] = None,
        max_memory_mb: int = 1024,
        default_ttl: int = 3600,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        token_model: str = "cl100k_base",
    ):
        """
        Initialize ISONCache.

        Args:
            config: Full configuration object (overrides other params)
            max_memory_mb: Maximum memory in MB
            default_ttl: Default TTL in seconds
            eviction_policy: Cache eviction policy
            token_model: Tokenizer model for counting
        """
        if config:
            self.config = config
        else:
            self.config = CacheConfig(
                max_memory_mb=max_memory_mb,
                default_ttl_seconds=default_ttl,
                eviction_policy=eviction_policy,
                token_model=token_model,
            )

        self._entries: OrderedDict[str, CacheEntry] = OrderedDict()
        self._token_manager = TokenManager(self.config.token_model)
        self._serializer = ISONSerializer()
        self._lock = RLock()

        # Stats tracking
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._memory_bytes = 0

    # =========================================================================
    # Core Operations
    # =========================================================================

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        tags: Optional[List[str]] = None,
        priority: int = 0,
        value_type: Optional[ValueType] = None,
    ) -> CacheEntry:
        """
        Store a value in the cache.

        Args:
            key: Cache key
            value: Value to cache (dict, list, or primitive)
            ttl: Time-to-live in seconds (uses default if None)
            tags: Optional tags for grouping
            priority: Priority for eviction (higher = kept longer)
            value_type: Type of value (auto-detected if None)

        Returns:
            The created cache entry
        """
        with self._lock:
            # Auto-detect value type
            if value_type is None:
                if isinstance(value, dict):
                    value_type = ValueType.OBJECT
                elif isinstance(value, list):
                    value_type = ValueType.TABLE
                elif isinstance(value, str):
                    value_type = ValueType.RAW
                else:
                    value_type = ValueType.OBJECT

            # Calculate tokens
            tokens = self._token_manager.count_value_tokens(value)

            # Calculate expiry
            ttl_seconds = ttl if ttl is not None else self.config.default_ttl_seconds
            expires_at = None
            if ttl_seconds > 0:
                expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)

            now = datetime.now(timezone.utc)

            # Create entry
            entry = CacheEntry(
                key=key,
                value=value,
                value_type=value_type,
                tokens=tokens,
                created_at=now,
                accessed_at=now,
                expires_at=expires_at,
                hits=0,
                priority=priority,
                tags=tags or [],
            )

            # Evict if needed before adding
            self._maybe_evict()

            # Store entry (remove old one first if exists)
            if key in self._entries:
                old_entry = self._entries[key]
                self._memory_bytes -= self._estimate_memory(old_entry)
                del self._entries[key]

            self._entries[key] = entry
            self._memory_bytes += self._estimate_memory(entry)

            # Move to end for LRU
            self._entries.move_to_end(key)

            return entry

    def get(
        self,
        key: str,
        max_tokens: Optional[int] = None,
        format: str = "ison"
    ) -> Optional[str]:
        """
        Retrieve a value from cache.

        Args:
            key: Cache key
            max_tokens: Maximum tokens to return (truncates if exceeded)
            format: Output format - "ison" (default), "raw", or "json"

        Returns:
            ISON-formatted string or None if not found/expired
        """
        with self._lock:
            entry = self._entries.get(key)

            if entry is None:
                self._misses += 1
                return None

            # Check expiry
            if entry.is_expired:
                self._delete_entry(key)
                self._misses += 1
                return None

            # Update access stats
            entry.touch()
            self._hits += 1

            # Move to end for LRU
            self._entries.move_to_end(key)

            # Serialize based on format
            if format == "raw":
                return entry.value
            elif format == "json":
                import json
                return json.dumps(entry.value)
            else:
                # ISON format
                ison_text = self._serializer.serialize(entry.value, key.replace(":", "_"))

                # Truncate if needed
                if max_tokens and entry.tokens > max_tokens:
                    ison_text, _ = self._token_manager.truncate_to_budget(
                        ison_text, max_tokens
                    )

                return ison_text

    def get_raw(self, key: str) -> Optional[Any]:
        """Get raw Python value without serialization"""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None or entry.is_expired:
                return None
            entry.touch()
            self._entries.move_to_end(key)
            return entry.value

    def delete(self, key: str) -> bool:
        """Delete a key from cache"""
        with self._lock:
            return self._delete_entry(key)

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            if entry.is_expired:
                self._delete_entry(key)
                return False
            return True

    def ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for a key"""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            return entry.ttl_seconds

    def expire(self, key: str, ttl: int) -> bool:
        """Set TTL for an existing key"""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            entry.expires_at = datetime.now(timezone.utc) + timedelta(seconds=ttl)
            return True

    def persist(self, key: str) -> bool:
        """Remove TTL from a key (make it persistent)"""
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return False
            entry.expires_at = None
            return True

    # =========================================================================
    # Batch Operations
    # =========================================================================

    def mset(self, items: Dict[str, Any], ttl: Optional[int] = None) -> int:
        """
        Set multiple keys at once.

        Args:
            items: Dict of key -> value pairs
            ttl: TTL for all items

        Returns:
            Number of items set
        """
        count = 0
        for key, value in items.items():
            self.set(key, value, ttl=ttl)
            count += 1
        return count

    def mget(
        self,
        keys: List[str],
        max_tokens: Optional[int] = None,
        merge: bool = True
    ) -> Optional[str]:
        """
        Get multiple keys as combined ISON output.

        Args:
            keys: List of keys to retrieve
            max_tokens: Total token budget
            merge: If True, merge similar schemas into tables

        Returns:
            Combined ISON string or None if no keys found
        """
        with self._lock:
            values = {}
            for key in keys:
                entry = self._entries.get(key)
                if entry and not entry.is_expired:
                    entry.touch()
                    values[key] = entry.value

            if not values:
                return None

            # Serialize
            ison_text = self._serializer.serialize_multiple(values, merge_tables=merge)

            # Truncate if needed
            if max_tokens:
                tokens = self._token_manager.count_ison_tokens(ison_text)
                if tokens > max_tokens:
                    ison_text, _ = self._token_manager.truncate_to_budget(
                        ison_text, max_tokens
                    )

            return ison_text

    def mdelete(self, keys: List[str]) -> int:
        """Delete multiple keys"""
        count = 0
        for key in keys:
            if self.delete(key):
                count += 1
        return count

    # =========================================================================
    # Pattern Matching
    # =========================================================================

    def keys(self, pattern: str = "*") -> List[str]:
        """
        Get keys matching pattern.

        Args:
            pattern: Glob pattern (e.g., "user:*", "*.cache")

        Returns:
            List of matching keys
        """
        with self._lock:
            # Remove expired entries first
            self._cleanup_expired()

            matching = []
            for key in self._entries.keys():
                if fnmatch.fnmatch(key, pattern):
                    matching.append(key)
            return matching

    def scan(
        self,
        pattern: str = "*",
        count: int = 100,
        cursor: int = 0
    ) -> tuple[int, List[str]]:
        """
        Scan keys incrementally (Redis-compatible).

        Args:
            pattern: Glob pattern
            count: Approximate number of keys to return
            cursor: Starting cursor (0 for start)

        Returns:
            Tuple of (next_cursor, keys)
        """
        with self._lock:
            all_keys = self.keys(pattern)

            if cursor >= len(all_keys):
                return 0, []

            end = min(cursor + count, len(all_keys))
            keys = all_keys[cursor:end]

            next_cursor = end if end < len(all_keys) else 0
            return next_cursor, keys

    # =========================================================================
    # Token-Budgeted Operations
    # =========================================================================

    def get_within_budget(
        self,
        patterns: Union[str, List[str]],
        token_budget: int,
        priority: Priority = Priority.HITS,
        exclude_keys: Optional[Set[str]] = None
    ) -> BudgetResult:
        """
        Get as many values as fit within token budget.

        Args:
            patterns: Key pattern(s) to match
            token_budget: Maximum total tokens
            priority: Order preference for selection
            exclude_keys: Keys to exclude

        Returns:
            BudgetResult with ISON output and metadata
        """
        with self._lock:
            if isinstance(patterns, str):
                patterns = [patterns]

            # Collect matching entries
            candidates = []
            for pattern in patterns:
                for key in self.keys(pattern):
                    if exclude_keys and key in exclude_keys:
                        continue
                    entry = self._entries.get(key)
                    if entry and not entry.is_expired:
                        candidates.append(entry)

            if not candidates:
                return BudgetResult(
                    ison="",
                    tokens_used=0,
                    tokens_budget=token_budget,
                    keys_included=[],
                    keys_excluded=[],
                    entries_count=0,
                    truncated=False
                )

            # Sort by priority
            if priority == Priority.HITS:
                candidates.sort(key=lambda e: e.hits, reverse=True)
            elif priority == Priority.RECENT:
                candidates.sort(key=lambda e: e.accessed_at, reverse=True)
            elif priority == Priority.OLDEST:
                candidates.sort(key=lambda e: e.created_at)
            elif priority == Priority.TOKENS:
                candidates.sort(key=lambda e: e.tokens)
            elif priority == Priority.PRIORITY:
                candidates.sort(key=lambda e: e.priority, reverse=True)

            # Select within budget
            budget = TokenBudget(token_budget)
            included = []
            excluded = []

            for entry in candidates:
                if budget.can_fit(entry.tokens):
                    budget.consume(entry.tokens)
                    included.append(entry)
                    entry.touch()
                else:
                    excluded.append(entry.key)

            # Generate ISON output
            if included:
                values = {e.key: e.value for e in included}
                ison_text = self._serializer.serialize_multiple(values, merge_tables=True)
            else:
                ison_text = ""

            return BudgetResult(
                ison=ison_text,
                tokens_used=budget.used,
                tokens_budget=token_budget,
                keys_included=[e.key for e in included],
                keys_excluded=excluded,
                entries_count=len(included),
                truncated=len(excluded) > 0
            )

    # =========================================================================
    # Tags Operations
    # =========================================================================

    def get_by_tag(self, tag: str) -> List[str]:
        """Get all keys with a specific tag"""
        with self._lock:
            matching = []
            for key, entry in self._entries.items():
                if tag in entry.tags and not entry.is_expired:
                    matching.append(key)
            return matching

    def delete_by_tag(self, tag: str) -> int:
        """Delete all keys with a specific tag"""
        keys = self.get_by_tag(tag)
        return self.mdelete(keys)

    # =========================================================================
    # Cache Management
    # =========================================================================

    def clear(self) -> int:
        """Clear all entries from cache"""
        with self._lock:
            count = len(self._entries)
            self._entries.clear()
            self._memory_bytes = 0
            return count

    def stats(self) -> CacheStats:
        """Get cache statistics"""
        with self._lock:
            entries_by_type: Dict[str, int] = {}
            total_tokens = 0
            oldest = None
            newest = None

            for entry in self._entries.values():
                type_name = entry.value_type.value
                entries_by_type[type_name] = entries_by_type.get(type_name, 0) + 1
                total_tokens += entry.tokens

                if oldest is None or entry.created_at < oldest:
                    oldest = entry.created_at
                if newest is None or entry.created_at > newest:
                    newest = entry.created_at

            return CacheStats(
                total_entries=len(self._entries),
                total_tokens=total_tokens,
                total_hits=self._hits,
                total_misses=self._misses,
                total_evictions=self._evictions,
                memory_bytes=self._memory_bytes,
                max_memory_bytes=self.config.max_memory_mb * 1024 * 1024,
                entries_by_type=entries_by_type,
                oldest_entry=oldest,
                newest_entry=newest,
            )

    def info(self) -> Dict[str, Any]:
        """Get cache info as dict (for CLI/API)"""
        stats = self.stats()
        return {
            "entries": stats.total_entries,
            "tokens": stats.total_tokens,
            "memory_mb": round(stats.memory_bytes / 1024 / 1024, 2),
            "max_memory_mb": self.config.max_memory_mb,
            "hit_rate": round(stats.hit_rate, 2),
            "evictions": stats.total_evictions,
            "eviction_policy": self.config.eviction_policy.value,
        }

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _delete_entry(self, key: str) -> bool:
        """Delete an entry by key"""
        if key in self._entries:
            entry = self._entries[key]
            self._memory_bytes -= self._estimate_memory(entry)
            del self._entries[key]
            return True
        return False

    def _cleanup_expired(self) -> int:
        """Remove expired entries"""
        expired = []
        for key, entry in self._entries.items():
            if entry.is_expired:
                expired.append(key)

        for key in expired:
            self._delete_entry(key)

        return len(expired)

    def _maybe_evict(self) -> int:
        """Evict entries if memory limit exceeded"""
        max_bytes = self.config.max_memory_mb * 1024 * 1024
        max_entries = self.config.max_entries

        evicted = 0

        # First cleanup expired
        evicted += self._cleanup_expired()

        # Then evict based on policy
        while (self._memory_bytes > max_bytes or
               len(self._entries) >= max_entries):

            if not self._entries:
                break

            key_to_evict = self._select_eviction_candidate()
            if key_to_evict:
                self._delete_entry(key_to_evict)
                evicted += 1
                self._evictions += 1
            else:
                break

        return evicted

    def _select_eviction_candidate(self) -> Optional[str]:
        """Select entry to evict based on policy"""
        if not self._entries:
            return None

        policy = self.config.eviction_policy

        if policy == EvictionPolicy.LRU:
            # First item in OrderedDict is least recently used
            return next(iter(self._entries))

        elif policy == EvictionPolicy.LFU:
            # Least frequently used (lowest hits)
            return min(self._entries.keys(),
                      key=lambda k: self._entries[k].hits)

        elif policy == EvictionPolicy.FIFO:
            # Oldest created
            return min(self._entries.keys(),
                      key=lambda k: self._entries[k].created_at)

        elif policy == EvictionPolicy.TTL:
            # Closest to expiry
            candidates = [(k, e) for k, e in self._entries.items()
                         if e.expires_at is not None]
            if candidates:
                return min(candidates, key=lambda x: x[1].expires_at)[0]
            return next(iter(self._entries))

        elif policy == EvictionPolicy.RANDOM:
            return random.choice(list(self._entries.keys()))

        elif policy == EvictionPolicy.PRIORITY:
            # Lowest priority
            return min(self._entries.keys(),
                      key=lambda k: self._entries[k].priority)

        return next(iter(self._entries))

    def _estimate_memory(self, entry: CacheEntry) -> int:
        """Estimate memory usage of an entry"""
        # Base object size
        size = 200  # Approximate CacheEntry overhead

        # Key
        size += len(entry.key) * 2  # Unicode chars

        # Value (rough estimate)
        if isinstance(entry.value, dict):
            size += len(str(entry.value)) * 2
        elif isinstance(entry.value, list):
            size += len(str(entry.value)) * 2
        elif isinstance(entry.value, str):
            size += len(entry.value) * 2
        else:
            size += 50

        # Tags
        size += sum(len(t) * 2 for t in entry.tags)

        return size

    # =========================================================================
    # Context Manager Support
    # =========================================================================

    def __enter__(self) -> "ISONCache":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        pass

    def __len__(self) -> int:
        return len(self._entries)

    def __contains__(self, key: str) -> bool:
        return self.exists(key)

    def __repr__(self) -> str:
        return f"ISONCache(entries={len(self._entries)}, tokens={sum(e.tokens for e in self._entries.values())})"
