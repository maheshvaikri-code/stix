# ISON Memory MCP - Configuration Guide

Complete guide to configuring ISON Memory MCP for your environment.

## Table of Contents

- [Configuration Overview](#configuration-overview)
- [Configuration Sources](#configuration-sources)
- [Environment Variables](#environment-variables)
- [Configuration File](#configuration-file)
- [Storage Configuration](#storage-configuration)
- [Compaction Configuration](#compaction-configuration)
- [Backup Configuration](#backup-configuration)
- [Index Configuration](#index-configuration)
- [Server Configuration](#server-configuration)
- [Logging Configuration](#logging-configuration)
- [Platform-Specific Configuration](#platform-specific-configuration)
- [Advanced Configuration](#advanced-configuration)

---

## Configuration Overview

ISON Memory MCP uses a layered configuration system with multiple sources:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    CONFIGURATION PRIORITY                            │
│                    (Highest to Lowest)                               │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  1. Environment Variables    ISON_MEMORY_*                          │
│     ↓                                                                │
│  2. Project Config File      ./.ison-memory.toml                    │
│     ↓                                                                │
│  3. User Config File         ~/.ison-memory/config.toml             │
│     ↓                                                                │
│  4. Default Values           Built into package                     │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

Higher priority sources override lower priority ones. This allows:
- **Environment variables** for deployment-specific overrides
- **Project config** for project-specific settings
- **User config** for personal defaults
- **Defaults** as fallback for everything else

---

## Configuration Sources

### 1. Environment Variables

Set environment variables with the `ISON_MEMORY_` prefix:

```bash
# Unix/Linux/macOS
export ISON_MEMORY_STORAGE_PATH=~/.ison-memory/memory.db
export ISON_MEMORY_COMPACTION_STRATEGY=smart

# Windows (PowerShell)
$env:ISON_MEMORY_STORAGE_PATH = "$env:USERPROFILE\.ison-memory\memory.db"
$env:ISON_MEMORY_COMPACTION_STRATEGY = "smart"

# Windows (CMD)
set ISON_MEMORY_STORAGE_PATH=%USERPROFILE%\.ison-memory\memory.db
```

### 2. Project Configuration File

Create `.ison-memory.toml` in your project root:

```toml
# .ison-memory.toml - Project-specific settings

[storage]
path = "./.ison-memory/project.db"

[compaction]
strategy = "smart"
max_age_days = 90  # Shorter retention for project memory
```

### 3. User Configuration File

Create `~/.ison-memory/config.toml`:

```toml
# ~/.ison-memory/config.toml - User defaults

[storage]
path = "~/.ison-memory/memory.db"
wal_mode = true

[backup]
enabled = true
compress = true
```

### 4. Initialize Default Configuration

Use the CLI to create a default configuration:

```bash
# Create default config file
ison-memory init

# Force overwrite existing config
ison-memory init --force

# View current effective config
ison-memory config
```

---

## Environment Variables

### Complete Reference

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| **Storage** |
| `ISON_MEMORY_STORAGE_PATH` | path | `~/.ison-memory/memory.db` | Database file path |
| `ISON_MEMORY_STORAGE_WAL_MODE` | bool | `true` | Enable WAL mode |
| `ISON_MEMORY_STORAGE_CACHE_SIZE` | int | `2000` | SQLite cache pages |
| `ISON_MEMORY_STORAGE_BUSY_TIMEOUT` | int | `5000` | Lock wait timeout (ms) |
| `ISON_MEMORY_STORAGE_JOURNAL_SIZE_LIMIT` | int | `67108864` | WAL size limit (bytes) |
| **Compaction** |
| `ISON_MEMORY_COMPACTION_ENABLED` | bool | `true` | Enable compaction |
| `ISON_MEMORY_COMPACTION_STRATEGY` | string | `smart` | Compaction strategy |
| `ISON_MEMORY_COMPACTION_SCHEDULE` | cron | `0 0 * * 0` | Compaction schedule |
| `ISON_MEMORY_COMPACTION_MAX_AGE_DAYS` | int | `180` | Max observation age |
| `ISON_MEMORY_COMPACTION_MIN_ACCESS_COUNT` | int | `2` | Min access count |
| **Backup** |
| `ISON_MEMORY_BACKUP_ENABLED` | bool | `true` | Enable backups |
| `ISON_MEMORY_BACKUP_DIR` | path | `~/.ison-memory/backups` | Backup directory |
| `ISON_MEMORY_BACKUP_MAX_BACKUPS` | int | `10` | Max backup count |
| `ISON_MEMORY_BACKUP_COMPRESS` | bool | `true` | Compress backups |
| `ISON_MEMORY_BACKUP_INCLUDE_ISON` | bool | `true` | Include ISON export |
| `ISON_MEMORY_BACKUP_SCHEDULE` | cron | `0 0 * * *` | Backup schedule |
| **Index** |
| `ISON_MEMORY_INDEX_FTS_ENABLED` | bool | `true` | Enable FTS5 |
| `ISON_MEMORY_INDEX_AUTO_REINDEX` | bool | `true` | Auto-rebuild index |
| `ISON_MEMORY_INDEX_REINDEX_THRESHOLD` | int | `1000` | Reindex after N changes |
| **Server** |
| `ISON_MEMORY_SERVER_NAME` | string | `ison-memory` | Server name |
| `ISON_MEMORY_SERVER_LOG_LEVEL` | string | `info` | Log level |
| **Logging** |
| `ISON_MEMORY_LOGGING_LEVEL` | string | `info` | Log level |
| `ISON_MEMORY_LOGGING_FILE` | path | `~/.ison-memory/logs/server.log` | Log file |
| `ISON_MEMORY_LOGGING_FORMAT` | string | `%(asctime)s...` | Log format |

### Boolean Values

Boolean environment variables accept:
- **True**: `true`, `1`, `yes`, `on`
- **False**: `false`, `0`, `no`, `off`

```bash
ISON_MEMORY_BACKUP_ENABLED=true   # Enabled
ISON_MEMORY_BACKUP_ENABLED=1      # Enabled
ISON_MEMORY_BACKUP_ENABLED=false  # Disabled
ISON_MEMORY_BACKUP_ENABLED=0      # Disabled
```

---

## Configuration File

### Complete Template

```toml
# ISON Memory MCP Configuration
# Location: ~/.ison-memory/config.toml

# =============================================================================
# STORAGE CONFIGURATION
# =============================================================================
[storage]
# Path to SQLite database file
# Supports ~ for home directory
path = "~/.ison-memory/memory.db"

# Enable Write-Ahead Logging for better concurrent access
# Recommended: true for production
wal_mode = true

# SQLite page cache size (in pages, default page = 4KB)
# Higher values improve read performance but use more memory
# 2000 pages = ~8MB cache
cache_size = 2000

# Maximum time to wait for database lock (milliseconds)
# Increase if you see "database is locked" errors
busy_timeout = 5000

# Maximum WAL file size before checkpoint (bytes)
# Default: 64MB
journal_size_limit = 67108864

# =============================================================================
# COMPACTION CONFIGURATION
# =============================================================================
[compaction]
# Enable automatic compaction
enabled = true

# Compaction strategy:
# - time_based: Remove items older than max_age_days
# - relevance: Remove items with access_count < min_access_count
# - aggressive: Both time and relevance with stricter thresholds
# - smart: Adaptive cleanup based on access patterns (recommended)
strategy = "smart"

# Cron schedule for automatic compaction
# Format: minute hour day_of_month month day_of_week
# Default: Weekly on Sunday at midnight
schedule = "0 0 * * 0"

# Maximum age for observations (time_based and aggressive strategies)
max_age_days = 180

# Minimum access count to keep (relevance and aggressive strategies)
min_access_count = 2

# Aggressive strategy settings
aggressive_age_days = 30
aggressive_min_access = 3

# Smart strategy settings
target_reduction_pct = 0.2  # Target 20% reduction
preserve_high_connectivity = true  # Keep highly connected entities
min_entity_relations = 3  # Preserve entities with 3+ relations

# =============================================================================
# BACKUP CONFIGURATION
# =============================================================================
[backup]
# Enable automatic backups
enabled = true

# Backup directory
backup_dir = "~/.ison-memory/backups"

# Maximum number of backups to keep (oldest deleted first)
max_backups = 10

# Compress backups with gzip (~70% size reduction)
compress = true

# Also export to ISON file (human-readable, version controllable)
include_ison_export = true

# Cron schedule for automatic backups
# Default: Daily at midnight
schedule = "0 0 * * *"

# =============================================================================
# INDEX CONFIGURATION
# =============================================================================
[index]
# Enable FTS5 full-text search index
fts_enabled = true

# Automatically rebuild index after corruption or major changes
auto_reindex = true

# Rebuild index after this many write operations
reindex_threshold = 1000

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
[server]
# Server name (used in MCP protocol)
name = "ison-memory"

# Log level for server: debug, info, warning, error
log_level = "info"

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================
[logging]
# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"

# Log format string
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Log file path (optional, set to empty string to disable file logging)
file = "~/.ison-memory/logs/server.log"

# Maximum log file size before rotation (bytes)
max_file_size = 10485760  # 10MB

# Number of backup log files to keep
backup_count = 5
```

---

## Storage Configuration

### Path Resolution

Paths support:
- `~` - User home directory
- `$VAR` or `${VAR}` - Environment variables
- Relative paths - Relative to current working directory
- Absolute paths - Used as-is

```toml
[storage]
# These are all valid:
path = "~/.ison-memory/memory.db"              # Home directory
path = "$HOME/.ison-memory/memory.db"          # Environment variable
path = "./.ison-memory/project.db"             # Relative path
path = "/var/data/ison-memory/memory.db"       # Absolute path
path = "${ISON_DATA_DIR}/memory.db"            # Custom env var
```

### Platform-Specific Defaults

| Platform | Default Path |
|----------|--------------|
| Linux | `~/.ison-memory/memory.db` |
| macOS | `~/.ison-memory/memory.db` |
| Windows | `%USERPROFILE%\.ison-memory\memory.db` |

### WAL Mode

Write-Ahead Logging (WAL) provides:
- Concurrent reads during writes
- Better write performance
- Improved crash recovery

```toml
[storage]
wal_mode = true  # Recommended for production

# Note: WAL mode creates two additional files:
# - memory.db-wal (write-ahead log)
# - memory.db-shm (shared memory)
```

### Cache Tuning

```toml
[storage]
# Small cache (low memory usage, slower reads)
cache_size = 500  # ~2MB

# Default cache (balanced)
cache_size = 2000  # ~8MB

# Large cache (high memory usage, faster reads)
cache_size = 10000  # ~40MB
```

---

## Compaction Configuration

### Strategy Selection

```toml
[compaction]
# Choose based on your use case:

# time_based - Simple age-based cleanup
# Good for: Regular maintenance, bounded storage
strategy = "time_based"
max_age_days = 180

# relevance - Access pattern based
# Good for: Prioritizing frequently used data
strategy = "relevance"
min_access_count = 2

# aggressive - Strict cleanup
# Good for: Storage constraints, major cleanup
strategy = "aggressive"
aggressive_age_days = 30
aggressive_min_access = 3

# smart (recommended) - Adaptive cleanup
# Good for: Most use cases, balances all factors
strategy = "smart"
target_reduction_pct = 0.2
preserve_high_connectivity = true
```

### Schedule Format (Cron)

```
┌───────────── minute (0-59)
│ ┌───────────── hour (0-23)
│ │ ┌───────────── day of month (1-31)
│ │ │ ┌───────────── month (1-12)
│ │ │ │ ┌───────────── day of week (0-6, 0=Sunday)
│ │ │ │ │
* * * * *
```

**Examples:**

```toml
[compaction]
# Weekly on Sunday at midnight
schedule = "0 0 * * 0"

# Daily at 3 AM
schedule = "0 3 * * *"

# Every 6 hours
schedule = "0 */6 * * *"

# First day of each month at midnight
schedule = "0 0 1 * *"
```

---

## Backup Configuration

### Backup Directory Structure

```
~/.ison-memory/backups/
├── backup_20250115_103045.db.gz      # Compressed SQLite backup
├── backup_20250115_103045.ison       # ISON export
├── backup_20250114_180000.db.gz
├── backup_20250114_180000.ison
└── ...
```

### Backup Retention

```toml
[backup]
# Keep last 10 backups
max_backups = 10

# When 11th backup is created:
# - Oldest backup (11th from now) is deleted
# - New backup is added
```

### Compression

```toml
[backup]
compress = true  # Uses gzip, ~70% size reduction

# Compressed: backup_20250115.db.gz (1.2 MB)
# Uncompressed: backup_20250115.db (4.0 MB)
```

---

## Index Configuration

### FTS5 Settings

```toml
[index]
# Enable full-text search on observations
fts_enabled = true

# Automatically rebuild if index is corrupted
auto_reindex = true

# Rebuild index periodically for optimization
reindex_threshold = 1000  # After 1000 write operations
```

### Manual Reindexing

```bash
# Rebuild FTS index via CLI
ison-memory compact --strategy smart

# The compaction process includes index optimization
```

---

## Server Configuration

### Log Levels

```toml
[server]
# Available levels (from most to least verbose):
log_level = "debug"    # All messages including debug info
log_level = "info"     # Normal operation messages (default)
log_level = "warning"  # Warnings and errors only
log_level = "error"    # Errors only
```

### MCP Protocol Settings

The server name is used in MCP protocol identification:

```toml
[server]
name = "ison-memory"  # Default

# Custom name for multiple instances
name = "project-memory"
```

---

## Logging Configuration

### Log Format

```toml
[logging]
# Default format
format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# JSON format for log aggregation
format = '{"time": "%(asctime)s", "level": "%(levelname)s", "message": "%(message)s"}'

# Minimal format
format = "%(levelname)s: %(message)s"
```

### Log Rotation

```toml
[logging]
# Rotate when file reaches 10MB
max_file_size = 10485760

# Keep 5 backup files
backup_count = 5

# Results in:
# server.log        (current)
# server.log.1      (previous)
# server.log.2
# server.log.3
# server.log.4
# server.log.5      (oldest, deleted when new rotation occurs)
```

### Disable File Logging

```toml
[logging]
# Set empty string to disable file logging (stdout only)
file = ""
```

---

## Platform-Specific Configuration

### Claude Desktop

**macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ison-memory": {
      "command": "ison-memory",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE_PATH": "~/Library/Application Support/ISON-Memory/memory.db",
        "ISON_MEMORY_BACKUP_DIR": "~/Library/Application Support/ISON-Memory/backups"
      }
    }
  }
}
```

**Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ison-memory": {
      "command": "ison-memory",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE_PATH": "%APPDATA%\\ISON-Memory\\memory.db",
        "ISON_MEMORY_BACKUP_DIR": "%APPDATA%\\ISON-Memory\\backups"
      }
    }
  }
}
```

**Linux:** `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ison-memory": {
      "command": "ison-memory",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE_PATH": "~/.local/share/ison-memory/memory.db"
      }
    }
  }
}
```

### Claude Code CLI

**Global Config:** `~/.claude/settings.json`

```json
{
  "mcpServers": {
    "ison-memory": {
      "command": "ison-memory",
      "args": ["serve", "--log-level", "info"]
    }
  }
}
```

**Project Config:** `.mcp.json` in project root

```json
{
  "mcpServers": {
    "project-memory": {
      "command": "ison-memory",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE_PATH": "./.ison-memory/project.db",
        "ISON_MEMORY_COMPACTION_MAX_AGE_DAYS": "90"
      }
    }
  }
}
```

### VSCode Extension

**Workspace Config:** `.vscode/mcp.json`

```json
{
  "servers": {
    "ison-memory": {
      "command": "ison-memory",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE_PATH": "${workspaceFolder}/.ison-memory/memory.db"
      }
    }
  }
}
```

---

## Advanced Configuration

### Multiple Memory Stores

Run separate memory stores for different purposes:

```bash
# Personal memory
ISON_MEMORY_STORAGE_PATH=~/.ison-memory/personal.db ison-memory serve

# Work memory
ISON_MEMORY_STORAGE_PATH=~/.ison-memory/work.db ison-memory serve

# Project memory
ISON_MEMORY_STORAGE_PATH=./project-memory.db ison-memory serve
```

### High-Performance Configuration

For large memory stores or high-traffic usage:

```toml
[storage]
wal_mode = true
cache_size = 10000      # 40MB cache
busy_timeout = 10000    # 10 second timeout

[compaction]
enabled = true
strategy = "smart"
schedule = "0 2 * * *"  # Run at 2 AM when idle

[index]
fts_enabled = true
auto_reindex = true
reindex_threshold = 5000  # Less frequent reindexing

[backup]
enabled = true
compress = true
schedule = "0 3 * * *"  # Backup at 3 AM
```

### Low-Resource Configuration

For limited memory or storage environments:

```toml
[storage]
wal_mode = false        # Simpler journaling
cache_size = 500        # 2MB cache

[compaction]
enabled = true
strategy = "aggressive"
max_age_days = 30       # Short retention
schedule = "0 0 * * *"  # Daily cleanup

[backup]
enabled = true
compress = true
max_backups = 3         # Fewer backups
include_ison_export = false  # Skip ISON export
```

### Debug Configuration

For troubleshooting:

```toml
[server]
log_level = "debug"

[logging]
level = "DEBUG"
format = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
file = "~/.ison-memory/logs/debug.log"
max_file_size = 52428800  # 50MB for more logs
backup_count = 10
```

### Configuration Validation

Validate your configuration:

```bash
# Show current effective configuration
ison-memory config

# Output includes:
# - Active settings
# - Source of each setting (env, file, default)
# - Validation warnings
```

---

## Configuration Examples

### Minimal Configuration

```toml
# Just the essentials
[storage]
path = "~/.ison-memory/memory.db"
```

### Development Configuration

```toml
[storage]
path = "./.ison-memory/dev.db"

[server]
log_level = "debug"

[compaction]
enabled = false  # Manual compaction only

[backup]
enabled = false  # No automatic backups
```

### Production Configuration

```toml
[storage]
path = "/var/data/ison-memory/memory.db"
wal_mode = true
cache_size = 5000

[compaction]
enabled = true
strategy = "smart"
schedule = "0 2 * * 0"

[backup]
enabled = true
backup_dir = "/var/backups/ison-memory"
max_backups = 30
compress = true
schedule = "0 3 * * *"

[logging]
level = "INFO"
file = "/var/log/ison-memory/server.log"
```

---

This configuration guide covers all aspects of configuring ISON Memory MCP. For architecture details, see [Architecture](ARCHITECTURE.md). For troubleshooting configuration issues, see [Troubleshooting](TROUBLESHOOTING.md).
