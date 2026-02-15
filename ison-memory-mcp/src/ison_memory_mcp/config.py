"""
Configuration Management for ISON Memory MCP Server

Supports multiple configuration sources with priority:
1. Environment variables (highest priority)
2. Config file (~/.ison-memory/config.toml)
3. Default values (lowest priority)

Environment Variables:
    ISON_MEMORY_PATH       - Path to memory database
    ISON_MEMORY_FORMAT     - Storage format (sqlite, ison, isongraph)
    ISON_MEMORY_LOG_LEVEL  - Logging level
    ISON_MEMORY_MAX_ENTITIES - Maximum entities allowed
    ISON_MEMORY_COMPACTION_THRESHOLD - Trigger compaction threshold
    ISON_MEMORY_BACKUP_ENABLED - Enable automatic backups
    ISON_MEMORY_BACKUP_INTERVAL - Backup interval in minutes
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Literal, Optional
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageFormat(str, Enum):
    """Supported storage formats"""
    SQLITE = "sqlite"
    ISON = "ison"
    ISONGRAPH = "isongraph"
    HYBRID = "hybrid"  # SQLite + ISON export


class LogLevel(str, Enum):
    """Log levels"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class CompactionStrategy(str, Enum):
    """Memory compaction strategies"""
    NONE = "none"
    TIME_BASED = "time_based"      # Remove old observations
    RELEVANCE = "relevance"        # Remove low-confidence items
    AGGRESSIVE = "aggressive"      # Both time and relevance
    SMART = "smart"                # ML-based relevance scoring


def get_default_memory_path() -> Path:
    """Get platform-specific default memory path"""
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        return base / "ison-memory" / "memory.db"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ison-memory" / "memory.db"
    else:
        return Path.home() / ".local" / "share" / "ison-memory" / "memory.db"


def get_default_config_path() -> Path:
    """Get platform-specific config path"""
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
        return base / "ison-memory" / "config.toml"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "ison-memory" / "config.toml"
    else:
        return Path.home() / ".config" / "ison-memory" / "config.toml"


class StorageConfig(BaseModel):
    """Storage configuration"""
    format: StorageFormat = StorageFormat.SQLITE
    path: Path = Field(default_factory=get_default_memory_path)
    ison_export_path: Optional[Path] = None  # For hybrid mode
    max_entities: int = Field(default=50000, ge=100, le=1000000)
    max_observations_per_entity: int = Field(default=1000, ge=10, le=10000)
    max_relations: int = Field(default=200000, ge=1000, le=5000000)

    # SQLite specific
    sqlite_journal_mode: Literal["DELETE", "WAL", "MEMORY"] = "WAL"
    sqlite_cache_size: int = Field(default=10000, ge=1000)  # Pages
    sqlite_busy_timeout: int = Field(default=30000, ge=1000)  # ms

    @field_validator("path", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Path:
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v


class CompactionConfig(BaseModel):
    """Memory compaction configuration"""
    enabled: bool = True
    strategy: CompactionStrategy = CompactionStrategy.SMART

    # Time-based settings
    max_observation_age_days: int = Field(default=365, ge=7)
    max_relation_age_days: int = Field(default=730, ge=30)

    # Relevance-based settings
    min_confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    min_access_count: int = Field(default=0, ge=0)

    # Trigger settings
    trigger_threshold_mb: float = Field(default=100.0, ge=1.0)
    trigger_entity_count: int = Field(default=10000, ge=100)

    # Schedule
    auto_compact_enabled: bool = True
    auto_compact_interval_hours: int = Field(default=24, ge=1)


class BackupConfig(BaseModel):
    """Backup configuration"""
    enabled: bool = True
    path: Optional[Path] = None  # Auto-generated if not set
    interval_minutes: int = Field(default=60, ge=5)
    max_backups: int = Field(default=10, ge=1, le=100)
    compress: bool = True

    # Export formats
    export_ison: bool = True
    export_json: bool = False

    @field_validator("path", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Optional[Path]:
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v


class IndexConfig(BaseModel):
    """Index configuration for fast lookups"""
    entity_name_index: bool = True
    entity_type_index: bool = True
    observation_content_fts: bool = True  # Full-text search
    relation_type_index: bool = True
    timestamp_index: bool = True

    # Advanced indexing
    embedding_index: bool = False  # Vector similarity (requires extra deps)
    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 256


class ServerConfig(BaseModel):
    """MCP Server configuration"""
    name: str = "ison-memory"
    transport: Literal["stdio", "http", "sse"] = "stdio"

    # HTTP/SSE settings
    host: str = "127.0.0.1"
    port: int = Field(default=8765, ge=1024, le=65535)

    # Timeouts
    request_timeout_seconds: int = Field(default=30, ge=5)

    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_requests_per_minute: int = Field(default=100, ge=10)


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    file_enabled: bool = True
    file_path: Optional[Path] = None  # Auto-generated if not set
    max_file_size_mb: int = Field(default=10, ge=1)
    backup_count: int = Field(default=5, ge=1)

    @field_validator("file_path", mode="before")
    @classmethod
    def expand_path(cls, v: Any) -> Optional[Path]:
        if isinstance(v, str):
            return Path(v).expanduser().resolve()
        return v


class MemoryConfig(BaseSettings):
    """
    Main configuration class for ISON Memory MCP Server

    All settings can be overridden via environment variables with ISON_MEMORY_ prefix.
    """
    model_config = SettingsConfigDict(
        env_prefix="ISON_MEMORY_",
        env_nested_delimiter="__",
        case_sensitive=False,
        extra="ignore",
    )

    # Sub-configurations
    storage: StorageConfig = Field(default_factory=StorageConfig)
    compaction: CompactionConfig = Field(default_factory=CompactionConfig)
    backup: BackupConfig = Field(default_factory=BackupConfig)
    index: IndexConfig = Field(default_factory=IndexConfig)
    server: ServerConfig = Field(default_factory=ServerConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Global settings
    debug: bool = False
    dry_run: bool = False  # Don't persist changes (for testing)

    def ensure_directories(self) -> None:
        """Create necessary directories"""
        self.storage.path.parent.mkdir(parents=True, exist_ok=True)

        if self.backup.enabled:
            backup_path = self.backup.path or self.storage.path.parent / "backups"
            backup_path.mkdir(parents=True, exist_ok=True)
            self.backup.path = backup_path

        if self.logging.file_enabled:
            log_path = self.logging.file_path or self.storage.path.parent / "logs"
            log_path.mkdir(parents=True, exist_ok=True)
            self.logging.file_path = log_path / "ison-memory.log"

        if self.storage.format == StorageFormat.HYBRID:
            export_path = self.storage.ison_export_path or self.storage.path.parent / "export"
            export_path.mkdir(parents=True, exist_ok=True)
            self.storage.ison_export_path = export_path

    def to_toml(self) -> str:
        """Export configuration to TOML format"""
        lines = [
            "# ISON Memory MCP Server Configuration",
            f"# Generated: {datetime.now().isoformat()}",
            "",
            "[storage]",
            f'format = "{self.storage.format.value}"',
            f'path = "{self.storage.path}"',
            f"max_entities = {self.storage.max_entities}",
            f"max_observations_per_entity = {self.storage.max_observations_per_entity}",
            f"max_relations = {self.storage.max_relations}",
            f'sqlite_journal_mode = "{self.storage.sqlite_journal_mode}"',
            "",
            "[compaction]",
            f"enabled = {str(self.compaction.enabled).lower()}",
            f'strategy = "{self.compaction.strategy.value}"',
            f"max_observation_age_days = {self.compaction.max_observation_age_days}",
            f"min_confidence_threshold = {self.compaction.min_confidence_threshold}",
            f"auto_compact_enabled = {str(self.compaction.auto_compact_enabled).lower()}",
            f"auto_compact_interval_hours = {self.compaction.auto_compact_interval_hours}",
            "",
            "[backup]",
            f"enabled = {str(self.backup.enabled).lower()}",
            f"interval_minutes = {self.backup.interval_minutes}",
            f"max_backups = {self.backup.max_backups}",
            f"compress = {str(self.backup.compress).lower()}",
            "",
            "[index]",
            f"entity_name_index = {str(self.index.entity_name_index).lower()}",
            f"observation_content_fts = {str(self.index.observation_content_fts).lower()}",
            "",
            "[server]",
            f'name = "{self.server.name}"',
            f'transport = "{self.server.transport}"',
            f'host = "{self.server.host}"',
            f"port = {self.server.port}",
            "",
            "[logging]",
            f'level = "{self.logging.level.value}"',
            f"file_enabled = {str(self.logging.file_enabled).lower()}",
            "",
            f"debug = {str(self.debug).lower()}",
        ]
        return "\n".join(lines)


# Global config instance
_config: Optional[MemoryConfig] = None


def get_config() -> MemoryConfig:
    """Get or create the global configuration instance"""
    global _config
    if _config is None:
        _config = MemoryConfig()
        _config.ensure_directories()
    return _config


def load_config(config_path: Optional[Path] = None) -> MemoryConfig:
    """Load configuration from file and environment"""
    global _config

    # Try to load from config file
    if config_path is None:
        config_path = get_default_config_path()

    config_dict: dict[str, Any] = {}

    if config_path.exists():
        try:
            import tomllib
            with open(config_path, "rb") as f:
                config_dict = tomllib.load(f)
        except ImportError:
            # Python < 3.11
            try:
                import tomli
                with open(config_path, "rb") as f:
                    config_dict = tomli.load(f)
            except ImportError:
                pass
        except Exception:
            pass

    # Create config with file values, env vars will override
    _config = MemoryConfig(**config_dict)
    _config.ensure_directories()

    return _config


def save_config(config: MemoryConfig, config_path: Optional[Path] = None) -> None:
    """Save configuration to file"""
    if config_path is None:
        config_path = get_default_config_path()

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(config.to_toml())
