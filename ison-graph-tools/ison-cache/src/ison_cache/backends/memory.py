"""
Memory Backend
==============

In-memory storage backend for ISONCache.
"""

from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Optional, Tuple
from datetime import datetime, timezone
import json

from ..schema import CacheEntry, ValueType


class MemoryBackend:
    """
    In-memory storage backend.

    Uses OrderedDict for LRU ordering support.
    """

    def __init__(self, max_entries: int = 100000):
        self.max_entries = max_entries
        self._data: OrderedDict[str, CacheEntry] = OrderedDict()

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get an entry by key"""
        entry = self._data.get(key)
        if entry and not entry.is_expired:
            # Move to end for LRU
            self._data.move_to_end(key)
            return entry
        elif entry and entry.is_expired:
            self.delete(key)
        return None

    def set(self, key: str, entry: CacheEntry) -> None:
        """Store an entry"""
        if key in self._data:
            del self._data[key]
        self._data[key] = entry
        self._data.move_to_end(key)

        # Evict if over limit
        while len(self._data) > self.max_entries:
            oldest_key = next(iter(self._data))
            del self._data[oldest_key]

    def delete(self, key: str) -> bool:
        """Delete an entry"""
        if key in self._data:
            del self._data[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        entry = self._data.get(key)
        if entry is None:
            return False
        if entry.is_expired:
            self.delete(key)
            return False
        return True

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        import fnmatch
        result = []
        for key, entry in list(self._data.items()):
            if entry.is_expired:
                self.delete(key)
                continue
            if fnmatch.fnmatch(key, pattern):
                result.append(key)
        return result

    def scan(self, cursor: int, count: int, pattern: str = "*") -> Tuple[int, List[str]]:
        """Scan keys with cursor"""
        all_keys = self.keys(pattern)
        if cursor >= len(all_keys):
            return 0, []

        end = min(cursor + count, len(all_keys))
        keys = all_keys[cursor:end]
        next_cursor = end if end < len(all_keys) else 0
        return next_cursor, keys

    def clear(self) -> int:
        """Clear all entries"""
        count = len(self._data)
        self._data.clear()
        return count

    def size(self) -> int:
        """Get number of entries"""
        return len(self._data)

    def items(self) -> Iterator[Tuple[str, CacheEntry]]:
        """Iterate over entries"""
        for key, entry in self._data.items():
            if not entry.is_expired:
                yield key, entry

    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        expired = [k for k, e in self._data.items() if e.is_expired]
        for key in expired:
            del self._data[key]
        return len(expired)

    def to_dict(self) -> Dict[str, Any]:
        """Export to dict for persistence"""
        return {
            key: {
                "value": entry.value,
                "value_type": entry.value_type.value,
                "tokens": entry.tokens,
                "created_at": entry.created_at.isoformat(),
                "accessed_at": entry.accessed_at.isoformat(),
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                "hits": entry.hits,
                "priority": entry.priority,
                "tags": entry.tags,
                "metadata": entry.metadata,
            }
            for key, entry in self._data.items()
            if not entry.is_expired
        }

    def from_dict(self, data: Dict[str, Any]) -> int:
        """Import from dict"""
        count = 0
        for key, entry_data in data.items():
            expires_at = None
            if entry_data.get("expires_at"):
                expires_at = datetime.fromisoformat(entry_data["expires_at"])
                if expires_at < datetime.now(timezone.utc):
                    continue  # Skip expired

            entry = CacheEntry(
                key=key,
                value=entry_data["value"],
                value_type=ValueType(entry_data["value_type"]),
                tokens=entry_data["tokens"],
                created_at=datetime.fromisoformat(entry_data["created_at"]),
                accessed_at=datetime.fromisoformat(entry_data["accessed_at"]),
                expires_at=expires_at,
                hits=entry_data.get("hits", 0),
                priority=entry_data.get("priority", 0),
                tags=entry_data.get("tags", []),
                metadata=entry_data.get("metadata", {}),
            )
            self._data[key] = entry
            count += 1
        return count

    def save(self, path: str) -> None:
        """Save to file"""
        data = self.to_dict()
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def load(self, path: str) -> int:
        """Load from file"""
        with open(path, 'r') as f:
            data = json.load(f)
        return self.from_dict(data)
