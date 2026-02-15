"""
SQLite Backend
==============

SQLite-based persistent storage backend for ISONCache.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

from ..schema import CacheEntry, ValueType


class SQLiteBackend:
    """
    SQLite storage backend for cache persistence.

    Stores entries in SQLite database with JSON serialization.
    """

    def __init__(self, path: str = ":memory:"):
        """
        Initialize SQLite backend.

        Args:
            path: Database file path or ":memory:" for in-memory
        """
        self.path = path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _init_db(self):
        """Initialize database schema"""
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS cache_entries (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                value_type TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                accessed_at TEXT NOT NULL,
                expires_at TEXT,
                hits INTEGER DEFAULT 0,
                priority INTEGER DEFAULT 0,
                tags TEXT,
                metadata TEXT
            )
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at ON cache_entries(expires_at)
        """)

        self._conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_accessed_at ON cache_entries(accessed_at)
        """)

        self._conn.commit()

    def _entry_from_row(self, row: sqlite3.Row) -> CacheEntry:
        """Convert database row to CacheEntry"""
        expires_at = None
        if row["expires_at"]:
            expires_at = datetime.fromisoformat(row["expires_at"])

        return CacheEntry(
            key=row["key"],
            value=json.loads(row["value"]),
            value_type=ValueType(row["value_type"]),
            tokens=row["tokens"],
            created_at=datetime.fromisoformat(row["created_at"]),
            accessed_at=datetime.fromisoformat(row["accessed_at"]),
            expires_at=expires_at,
            hits=row["hits"],
            priority=row["priority"],
            tags=json.loads(row["tags"]) if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )

    def get(self, key: str) -> Optional[CacheEntry]:
        """Get an entry by key"""
        cursor = self._conn.execute(
            "SELECT * FROM cache_entries WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()

        if row is None:
            return None

        entry = self._entry_from_row(row)

        if entry.is_expired:
            self.delete(key)
            return None

        # Update access time and hits
        self._conn.execute(
            "UPDATE cache_entries SET accessed_at = ?, hits = hits + 1 WHERE key = ?",
            (datetime.now(timezone.utc).isoformat(), key)
        )
        self._conn.commit()

        entry.touch()
        return entry

    def set(self, key: str, entry: CacheEntry) -> None:
        """Store an entry"""
        self._conn.execute("""
            INSERT OR REPLACE INTO cache_entries
            (key, value, value_type, tokens, created_at, accessed_at,
             expires_at, hits, priority, tags, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            key,
            json.dumps(entry.value),
            entry.value_type.value,
            entry.tokens,
            entry.created_at.isoformat(),
            entry.accessed_at.isoformat(),
            entry.expires_at.isoformat() if entry.expires_at else None,
            entry.hits,
            entry.priority,
            json.dumps(entry.tags) if entry.tags else None,
            json.dumps(entry.metadata) if entry.metadata else None,
        ))
        self._conn.commit()

    def delete(self, key: str) -> bool:
        """Delete an entry"""
        cursor = self._conn.execute(
            "DELETE FROM cache_entries WHERE key = ?",
            (key,)
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def exists(self, key: str) -> bool:
        """Check if key exists and is not expired"""
        cursor = self._conn.execute(
            "SELECT expires_at FROM cache_entries WHERE key = ?",
            (key,)
        )
        row = cursor.fetchone()

        if row is None:
            return False

        if row["expires_at"]:
            expires_at = datetime.fromisoformat(row["expires_at"])
            if expires_at < datetime.now(timezone.utc):
                self.delete(key)
                return False

        return True

    def keys(self, pattern: str = "*") -> List[str]:
        """Get keys matching pattern"""
        # Convert glob to SQL LIKE
        sql_pattern = pattern.replace("*", "%").replace("?", "_")

        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """SELECT key FROM cache_entries
               WHERE key LIKE ?
               AND (expires_at IS NULL OR expires_at > ?)""",
            (sql_pattern, now)
        )

        return [row["key"] for row in cursor.fetchall()]

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
        cursor = self._conn.execute("SELECT COUNT(*) as count FROM cache_entries")
        count = cursor.fetchone()["count"]

        self._conn.execute("DELETE FROM cache_entries")
        self._conn.commit()

        return count

    def size(self) -> int:
        """Get number of entries"""
        cursor = self._conn.execute(
            """SELECT COUNT(*) as count FROM cache_entries
               WHERE expires_at IS NULL OR expires_at > ?""",
            (datetime.now(timezone.utc).isoformat(),)
        )
        return cursor.fetchone()["count"]

    def items(self) -> Iterator[Tuple[str, CacheEntry]]:
        """Iterate over entries"""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            """SELECT * FROM cache_entries
               WHERE expires_at IS NULL OR expires_at > ?
               ORDER BY accessed_at DESC""",
            (now,)
        )

        for row in cursor:
            yield row["key"], self._entry_from_row(row)

    def cleanup_expired(self) -> int:
        """Remove expired entries"""
        now = datetime.now(timezone.utc).isoformat()
        cursor = self._conn.execute(
            "DELETE FROM cache_entries WHERE expires_at IS NOT NULL AND expires_at < ?",
            (now,)
        )
        self._conn.commit()
        return cursor.rowcount

    def vacuum(self) -> None:
        """Optimize database"""
        self._conn.execute("VACUUM")

    def close(self) -> None:
        """Close database connection"""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
