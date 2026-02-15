"""
Memory Compaction and Optimization

Handles automatic cleanup of old, low-relevance, and duplicate data
to keep the memory store efficient and within size limits.

Strategies:
- TIME_BASED: Remove observations older than threshold
- RELEVANCE: Remove low-confidence items
- AGGRESSIVE: Both time and relevance
- SMART: ML-based relevance scoring (uses access patterns)
"""

from __future__ import annotations

import asyncio
import gzip
import shutil
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from ison_memory_mcp.config import MemoryConfig, CompactionStrategy
from ison_memory_mcp.models import utc_now, format_timestamp, parse_timestamp


@dataclass
class CompactionResult:
    """Result of a compaction operation"""
    success: bool = True
    started_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    strategy: str = ""

    # Counts
    entities_before: int = 0
    entities_after: int = 0
    entities_removed: int = 0

    observations_before: int = 0
    observations_after: int = 0
    observations_removed: int = 0

    relations_before: int = 0
    relations_after: int = 0
    relations_removed: int = 0

    # Size
    size_before_bytes: int = 0
    size_after_bytes: int = 0
    size_saved_bytes: int = 0

    # Errors
    errors: list[str] = field(default_factory=list)

    @property
    def duration_seconds(self) -> float:
        """Get duration of compaction"""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return 0.0

    @property
    def total_removed(self) -> int:
        """Total items removed"""
        return self.entities_removed + self.observations_removed + self.relations_removed

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "started_at": format_timestamp(self.started_at),
            "completed_at": format_timestamp(self.completed_at) if self.completed_at else None,
            "duration_seconds": self.duration_seconds,
            "strategy": self.strategy,
            "entities": {
                "before": self.entities_before,
                "after": self.entities_after,
                "removed": self.entities_removed,
            },
            "observations": {
                "before": self.observations_before,
                "after": self.observations_after,
                "removed": self.observations_removed,
            },
            "relations": {
                "before": self.relations_before,
                "after": self.relations_after,
                "removed": self.relations_removed,
            },
            "size": {
                "before_bytes": self.size_before_bytes,
                "after_bytes": self.size_after_bytes,
                "saved_bytes": self.size_saved_bytes,
                "saved_percent": round(
                    (self.size_saved_bytes / self.size_before_bytes * 100)
                    if self.size_before_bytes > 0 else 0, 2
                ),
            },
            "errors": self.errors,
        }

    def to_ison(self) -> str:
        """Convert to ISON format"""
        lines = [
            "# Compaction Report",
            f"# Strategy: {self.strategy}",
            f"# Duration: {self.duration_seconds:.2f}s",
            "",
            "object.summary",
            "success started_at duration_seconds total_removed size_saved_mb",
            f"{str(self.success).lower()} {format_timestamp(self.started_at)} "
            f"{self.duration_seconds:.2f} {self.total_removed} "
            f"{round(self.size_saved_bytes / (1024 * 1024), 2)}",
            "",
            "table.counts",
            "type before after removed",
            f"entities {self.entities_before} {self.entities_after} {self.entities_removed}",
            f"observations {self.observations_before} {self.observations_after} {self.observations_removed}",
            f"relations {self.relations_before} {self.relations_after} {self.relations_removed}",
        ]
        return "\n".join(lines)


class MemoryCompactor:
    """
    Handles memory compaction and optimization.

    Compaction reduces database size by removing:
    - Old observations beyond retention period
    - Low-confidence data
    - Orphaned relations
    - Duplicate observations
    """

    def __init__(self, config: MemoryConfig) -> None:
        self.config = config
        self._running = False

    async def compact(
        self,
        store: Any,  # MemoryStore, avoiding circular import
        strategy: Optional[CompactionStrategy] = None,
        dry_run: bool = False
    ) -> CompactionResult:
        """
        Run compaction on the memory store.

        Args:
            store: MemoryStore instance
            strategy: Override configured strategy
            dry_run: If True, only simulate compaction

        Returns:
            CompactionResult with statistics
        """
        if self._running:
            return CompactionResult(
                success=False,
                errors=["Compaction already running"]
            )

        self._running = True
        strategy = strategy or self.config.compaction.strategy
        result = CompactionResult(strategy=strategy.value)

        try:
            # Get initial stats
            stats = await store.get_stats()
            result.entities_before = stats.entity_count
            result.observations_before = stats.observation_count
            result.relations_before = stats.relation_count
            result.size_before_bytes = stats.database_size_bytes

            if strategy == CompactionStrategy.NONE:
                result.completed_at = utc_now()
                return result

            # Run compaction based on strategy
            if strategy in (CompactionStrategy.TIME_BASED, CompactionStrategy.AGGRESSIVE, CompactionStrategy.SMART):
                await self._compact_by_time(store, result, dry_run)

            if strategy in (CompactionStrategy.RELEVANCE, CompactionStrategy.AGGRESSIVE, CompactionStrategy.SMART):
                await self._compact_by_relevance(store, result, dry_run)

            if strategy == CompactionStrategy.SMART:
                await self._compact_smart(store, result, dry_run)

            # Always clean up orphaned relations
            await self._remove_orphaned_relations(store, result, dry_run)

            # Always remove exact duplicates
            await self._remove_duplicate_observations(store, result, dry_run)

            # Vacuum database if not dry run
            if not dry_run and store._db:
                await store._db.execute("VACUUM")
                await store._db.commit()

            # Update metadata
            if not dry_run and store._db:
                await store._db.execute(
                    "INSERT OR REPLACE INTO store_metadata (key, value) VALUES (?, ?)",
                    ("last_compaction", format_timestamp(utc_now()))
                )
                await store._db.commit()

            # Get final stats
            final_stats = await store.get_stats()
            result.entities_after = final_stats.entity_count
            result.observations_after = final_stats.observation_count
            result.relations_after = final_stats.relation_count
            result.size_after_bytes = final_stats.database_size_bytes

            result.entities_removed = result.entities_before - result.entities_after
            result.observations_removed = result.observations_before - result.observations_after
            result.relations_removed = result.relations_before - result.relations_after
            result.size_saved_bytes = result.size_before_bytes - result.size_after_bytes

            result.completed_at = utc_now()

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            result.completed_at = utc_now()

        finally:
            self._running = False

        return result

    async def _compact_by_time(
        self,
        store: Any,
        result: CompactionResult,
        dry_run: bool
    ) -> None:
        """Remove observations older than retention period"""
        cutoff_date = utc_now() - timedelta(days=self.config.compaction.max_observation_age_days)
        cutoff_str = format_timestamp(cutoff_date)

        if dry_run:
            async with store._db.execute(
                "SELECT COUNT(*) FROM observations WHERE timestamp < ?",
                (cutoff_str,)
            ) as cursor:
                row = await cursor.fetchone()
                result.observations_removed += row[0]
        else:
            cursor = await store._db.execute(
                "DELETE FROM observations WHERE timestamp < ?",
                (cutoff_str,)
            )
            await store._db.commit()
            result.observations_removed += cursor.rowcount

        # Also remove old relations if configured
        relation_cutoff = utc_now() - timedelta(days=self.config.compaction.max_relation_age_days)
        relation_cutoff_str = format_timestamp(relation_cutoff)

        if dry_run:
            async with store._db.execute(
                "SELECT COUNT(*) FROM relations WHERE created_at < ? AND access_count = 0",
                (relation_cutoff_str,)
            ) as cursor:
                row = await cursor.fetchone()
                result.relations_removed += row[0]
        else:
            cursor = await store._db.execute(
                "DELETE FROM relations WHERE created_at < ? AND access_count = 0",
                (relation_cutoff_str,)
            )
            await store._db.commit()
            result.relations_removed += cursor.rowcount

    async def _compact_by_relevance(
        self,
        store: Any,
        result: CompactionResult,
        dry_run: bool
    ) -> None:
        """Remove low-confidence observations"""
        min_confidence = self.config.compaction.min_confidence_threshold

        if dry_run:
            async with store._db.execute(
                "SELECT COUNT(*) FROM observations WHERE confidence < ?",
                (min_confidence,)
            ) as cursor:
                row = await cursor.fetchone()
                result.observations_removed += row[0]
        else:
            cursor = await store._db.execute(
                "DELETE FROM observations WHERE confidence < ?",
                (min_confidence,)
            )
            await store._db.commit()
            result.observations_removed += cursor.rowcount

        # Remove low-confidence relations
        if dry_run:
            async with store._db.execute(
                "SELECT COUNT(*) FROM relations WHERE confidence < ?",
                (min_confidence,)
            ) as cursor:
                row = await cursor.fetchone()
                result.relations_removed += row[0]
        else:
            cursor = await store._db.execute(
                "DELETE FROM relations WHERE confidence < ?",
                (min_confidence,)
            )
            await store._db.commit()
            result.relations_removed += cursor.rowcount

    async def _compact_smart(
        self,
        store: Any,
        result: CompactionResult,
        dry_run: bool
    ) -> None:
        """
        Smart compaction using access patterns.

        Removes observations that are:
        - Old (>90 days)
        - Low confidence (<0.5)
        - Never accessed (access_count = 0)
        """
        cutoff_date = utc_now() - timedelta(days=90)
        cutoff_str = format_timestamp(cutoff_date)

        if dry_run:
            async with store._db.execute(
                """
                SELECT COUNT(*) FROM observations
                WHERE timestamp < ?
                  AND confidence < 0.5
                  AND access_count = 0
                """,
                (cutoff_str,)
            ) as cursor:
                row = await cursor.fetchone()
                result.observations_removed += row[0]
        else:
            cursor = await store._db.execute(
                """
                DELETE FROM observations
                WHERE timestamp < ?
                  AND confidence < 0.5
                  AND access_count = 0
                """,
                (cutoff_str,)
            )
            await store._db.commit()
            result.observations_removed += cursor.rowcount

        # Remove entities with no observations and no relations
        if not dry_run:
            cursor = await store._db.execute(
                """
                DELETE FROM entities
                WHERE id NOT IN (SELECT DISTINCT entity_id FROM observations)
                  AND id NOT IN (SELECT DISTINCT from_entity FROM relations)
                  AND id NOT IN (SELECT DISTINCT to_entity FROM relations)
                  AND access_count = 0
                """
            )
            await store._db.commit()
            result.entities_removed += cursor.rowcount

    async def _remove_orphaned_relations(
        self,
        store: Any,
        result: CompactionResult,
        dry_run: bool
    ) -> None:
        """Remove relations pointing to non-existent entities"""
        if dry_run:
            async with store._db.execute(
                """
                SELECT COUNT(*) FROM relations
                WHERE from_entity NOT IN (SELECT id FROM entities)
                   OR to_entity NOT IN (SELECT id FROM entities)
                """
            ) as cursor:
                row = await cursor.fetchone()
                result.relations_removed += row[0]
        else:
            cursor = await store._db.execute(
                """
                DELETE FROM relations
                WHERE from_entity NOT IN (SELECT id FROM entities)
                   OR to_entity NOT IN (SELECT id FROM entities)
                """
            )
            await store._db.commit()
            result.relations_removed += cursor.rowcount

    async def _remove_duplicate_observations(
        self,
        store: Any,
        result: CompactionResult,
        dry_run: bool
    ) -> None:
        """Remove duplicate observations keeping the highest confidence one"""
        if dry_run:
            async with store._db.execute(
                """
                SELECT COUNT(*) FROM observations o1
                WHERE EXISTS (
                    SELECT 1 FROM observations o2
                    WHERE o2.entity_id = o1.entity_id
                      AND o2.content_hash = o1.content_hash
                      AND o2.id != o1.id
                      AND o2.confidence > o1.confidence
                )
                """
            ) as cursor:
                row = await cursor.fetchone()
                result.observations_removed += row[0]
        else:
            cursor = await store._db.execute(
                """
                DELETE FROM observations
                WHERE id IN (
                    SELECT o1.id FROM observations o1
                    WHERE EXISTS (
                        SELECT 1 FROM observations o2
                        WHERE o2.entity_id = o1.entity_id
                          AND o2.content_hash = o1.content_hash
                          AND o2.id != o1.id
                          AND (o2.confidence > o1.confidence
                               OR (o2.confidence = o1.confidence AND o2.timestamp > o1.timestamp))
                    )
                )
                """
            )
            await store._db.commit()
            result.observations_removed += cursor.rowcount


@dataclass
class BackupResult:
    """Result of a backup operation"""
    success: bool = True
    backup_path: Optional[Path] = None
    size_bytes: int = 0
    compressed: bool = False
    started_at: datetime = field(default_factory=utc_now)
    completed_at: Optional[datetime] = None
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary"""
        return {
            "success": self.success,
            "backup_path": str(self.backup_path) if self.backup_path else None,
            "size_bytes": self.size_bytes,
            "size_mb": round(self.size_bytes / (1024 * 1024), 2),
            "compressed": self.compressed,
            "started_at": format_timestamp(self.started_at),
            "completed_at": format_timestamp(self.completed_at) if self.completed_at else None,
            "errors": self.errors,
        }


class BackupManager:
    """
    Manages memory backups and restoration.

    Supports:
    - SQLite database backups
    - ISON format exports
    - Compressed backups (.gz)
    - Automatic backup rotation
    """

    def __init__(self, config: MemoryConfig) -> None:
        self.config = config

    def _get_backup_dir(self) -> Path:
        """Get backup directory"""
        if self.config.backup.path:
            return self.config.backup.path
        return self.config.storage.path.parent / "backups"

    def _generate_backup_name(self, extension: str) -> str:
        """Generate timestamped backup filename"""
        timestamp = utc_now().strftime("%Y%m%d_%H%M%S")
        return f"memory_backup_{timestamp}.{extension}"

    async def create_backup(
        self,
        store: Any,  # MemoryStore
        include_ison: bool = True
    ) -> BackupResult:
        """
        Create a backup of the memory store.

        Args:
            store: MemoryStore instance
            include_ison: Also export to ISON format

        Returns:
            BackupResult with backup details
        """
        result = BackupResult()
        backup_dir = self._get_backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Backup SQLite database
            db_backup_name = self._generate_backup_name("db")
            if self.config.backup.compress:
                db_backup_name += ".gz"

            db_backup_path = backup_dir / db_backup_name

            if self.config.backup.compress:
                # Compressed backup
                with open(store.db_path, "rb") as f_in:
                    with gzip.open(db_backup_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
                result.compressed = True
            else:
                # Direct copy
                shutil.copy2(store.db_path, db_backup_path)

            result.backup_path = db_backup_path
            result.size_bytes = db_backup_path.stat().st_size

            # Export to ISON if requested
            if include_ison and self.config.backup.export_ison:
                ison_backup_name = self._generate_backup_name("ison")
                if self.config.backup.compress:
                    ison_backup_name += ".gz"

                ison_backup_path = backup_dir / ison_backup_name
                ison_content = await store.export_to_ison()

                if self.config.backup.compress:
                    with gzip.open(ison_backup_path, "wt", encoding="utf-8") as f:
                        f.write(ison_content)
                else:
                    ison_backup_path.write_text(ison_content, encoding="utf-8")

            # Update store metadata
            if store._db:
                await store._db.execute(
                    "INSERT OR REPLACE INTO store_metadata (key, value) VALUES (?, ?)",
                    ("last_backup", format_timestamp(utc_now()))
                )
                await store._db.commit()

            # Rotate old backups
            await self._rotate_backups(backup_dir)

            result.success = True
            result.completed_at = utc_now()

        except Exception as e:
            result.success = False
            result.errors.append(str(e))
            result.completed_at = utc_now()

        return result

    async def _rotate_backups(self, backup_dir: Path) -> None:
        """Remove old backups exceeding max_backups limit"""
        # Get all backup files sorted by modification time
        backup_files = sorted(
            backup_dir.glob("memory_backup_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )

        # Keep only the newest max_backups files
        for old_backup in backup_files[self.config.backup.max_backups:]:
            old_backup.unlink()

    async def restore_backup(
        self,
        store: Any,
        backup_path: Path
    ) -> bool:
        """
        Restore from a backup file.

        Args:
            store: MemoryStore instance
            backup_path: Path to backup file

        Returns:
            True if successful
        """
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup not found: {backup_path}")

        # Close current connection
        await store.close()

        try:
            # Backup current database before restore
            current_backup = store.db_path.with_suffix(".db.pre_restore")
            if store.db_path.exists():
                shutil.copy2(store.db_path, current_backup)

            # Restore based on file type
            if backup_path.suffix == ".gz":
                with gzip.open(backup_path, "rb") as f_in:
                    with open(store.db_path, "wb") as f_out:
                        shutil.copyfileobj(f_in, f_out)
            else:
                shutil.copy2(backup_path, store.db_path)

            # Reinitialize store
            await store.initialize()

            # Remove pre-restore backup on success
            if current_backup.exists():
                current_backup.unlink()

            return True

        except Exception:
            # Restore original on failure
            if current_backup.exists():
                shutil.copy2(current_backup, store.db_path)
            await store.initialize()
            raise

    def list_backups(self) -> list[dict[str, Any]]:
        """List available backups"""
        backup_dir = self._get_backup_dir()
        if not backup_dir.exists():
            return []

        backups = []
        for backup_file in sorted(
            backup_dir.glob("memory_backup_*"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        ):
            stat = backup_file.stat()
            backups.append({
                "path": str(backup_file),
                "name": backup_file.name,
                "size_bytes": stat.st_size,
                "size_mb": round(stat.st_size / (1024 * 1024), 2),
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "compressed": backup_file.suffix == ".gz",
            })

        return backups
