# ISON Memory MCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![MCP Protocol](https://img.shields.io/badge/MCP-1.0-green.svg)](https://modelcontextprotocol.io)

A production-ready **persistent memory system** for Claude AI applications. ISON Memory MCP provides Claude with long-term memory capabilities using the token-efficient ISON format, achieving **50-72% token savings** compared to JSON while maintaining full semantic fidelity.

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Quick Start](#quick-start)
- [Platform Integration](#platform-integration)
- [Available Tools](#available-tools)
- [ISON Format](#ison-format)
- [Configuration](#configuration)
- [CLI Reference](#cli-reference)
- [Documentation](#documentation)
- [Development](#development)
- [License](#license)

---

## Overview

ISON Memory MCP solves the **ephemeral memory problem** in Claude applications. Without persistent memory, Claude forgets everything between conversations - user preferences, project context, team information, and important decisions.

### The Problem

```
Session 1: "I'm John, I prefer TypeScript and work on the E-commerce project"
Session 2: "Who am I and what am I working on?" → Claude doesn't know
```

### The Solution

```
Session 1: Claude stores entities, observations, and relations
Session 2: Claude retrieves context → "You're John (:e_001), working on E-commerce (:e_002)"
```

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Claude Applications                              │
│         (Desktop, Code CLI, VSCode, Custom Agents)                  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ MCP Protocol (JSON-RPC 2.0)
┌────────────────────────────▼────────────────────────────────────────┐
│                    ISON Memory MCP Server                            │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────┐ │
│  │   12 Tools     │  │  3 Resources   │  │     3 Prompts          │ │
│  │ CRUD + Search  │  │ System Context │  │ Context Injection      │ │
│  └────────────────┘  └────────────────┘  └────────────────────────┘ │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    Memory Store (SQLite)                      │   │
│  │  Entities │ Observations │ Relations │ FTS5 Index │ WAL Mode │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌────────────────────────┐  ┌──────────────────────────────────┐   │
│  │   Smart Compaction     │  │    Backup & Recovery              │   │
│  │  Time/Relevance/Smart  │  │   Compressed + ISON Export        │   │
│  └────────────────────────┘  └──────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                             │
                             ▼ All responses in ISON format
                    ┌─────────────────┐
                    │  50-72% Token   │
                    │    Savings      │
                    └─────────────────┘
```

---

## Key Features

### Token-Efficient ISON Format

All memory data uses ISON (Indexed Structured Object Notation) format, specifically designed for LLM context efficiency.

| Format | 10 Entities | 50 Entities + Relations | Savings |
|--------|-------------|------------------------|---------|
| JSON   | 450 tokens  | 5,800 tokens           | -       |
| ISON   | 180 tokens  | 1,740 tokens           | **70%** |

### Robust SQLite Backend

- **WAL Mode**: Concurrent reads during writes
- **FTS5 Index**: Fast full-text search on observations
- **ACID Compliance**: Guaranteed data integrity
- **Automatic Vacuuming**: Self-maintaining storage

### Smart Memory Management

- **Compaction Strategies**: Time-based, relevance-based, aggressive, and smart (ML-based)
- **Access Tracking**: Prioritizes frequently-used entities
- **Automatic Cleanup**: Scheduled maintenance with configurable policies

### Cross-Platform Support

| Platform | Configuration | Status |
|----------|--------------|--------|
| Claude Desktop | `claude_desktop_config.json` | Full Support |
| Claude Code CLI | `~/.claude/settings.json` | Full Support |
| VSCode Extension | `.vscode/mcp.json` | Full Support |
| Custom Agents | MCP Client SDK | Full Support |

### Round-Trip Token Savings

ISON saves tokens in **both directions**:

```
INPUT (Context → Claude):
├── Tool responses return ISON tables
├── MCP Resources inject system prompts
└── Memory data is ~70% smaller

OUTPUT (Claude → User):
├── Claude uses :ref syntax in responses
├── Structured data as ISON tables
└── Compact entity references
```

---

## Quick Start

### Installation

```bash
# Install from PyPI
pip install ison-memory-mcp

# Or install from source
git clone https://github.com/anthropics/ison-memory-mcp
cd ison-memory-mcp
pip install -e .
```

### Verify Installation

```bash
# Check version
ison-memory --version

# Initialize configuration
ison-memory init

# View configuration
ison-memory config
```

### Start the Server

```bash
# Start MCP server (stdio mode for Claude integration)
ison-memory serve

# Start with debug logging
ison-memory serve --log-level debug
```

---

## Platform Integration

### Claude Desktop

**Configuration File Locations:**
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ison-memory": {
      "command": "ison-memory",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE_PATH": "~/.ison-memory/memory.db"
      }
    }
  }
}
```

### Claude Code CLI

**Global Configuration** (`~/.claude/settings.json`):

```json
{
  "mcpServers": {
    "ison-memory": {
      "command": "ison-memory",
      "args": ["serve"]
    }
  }
}
```

**Or use the CLI:**

```bash
claude mcp add ison-memory -- ison-memory serve
```

**Project-Level Configuration** (`.mcp.json` in project root):

```json
{
  "mcpServers": {
    "project-memory": {
      "command": "ison-memory",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE_PATH": "./.ison-memory/project.db"
      }
    }
  }
}
```

### VSCode Extension

Create `.vscode/mcp.json` in your workspace:

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

## Available Tools

ISON Memory MCP provides **12 tools** for memory operations:

### Entity Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_entities` | Create entities with optional observations | `entities[]` with `name`, `entityType`, `observations[]` |
| `update_entity` | Modify entity name or type | `entityName`, `newName`, `newType` |
| `delete_entities` | Remove entities and related data | `entityNames[]` |

### Observation Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_observations` | Add atomic facts to entities | `observations[]` with `entityName`, `content`, `source`, `confidence` |

### Relation Management

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `create_relations` | Create typed relationships | `relations[]` with `fromEntity`, `toEntity`, `relationType`, `bidirectional` |

### Search & Query

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `search_memory` | Full-text search across memory | `query`, `entityType`, `maxResults` |
| `read_graph` | Export entire knowledge graph | `format` (ison/isonl/isongraph), `includeStats` |
| `multi_hop_search` | Graph traversal from entity | `entityName`, `maxHops`, `relationType` |

### Maintenance

| Tool | Description | Key Parameters |
|------|-------------|----------------|
| `memory_stats` | Get memory statistics | - |
| `compact_memory` | Run memory compaction | `strategy`, `dryRun` |
| `backup_memory` | Create backup | `includeIson` |
| `list_backups` | List available backups | - |

### Example Usage

```python
# Create an entity with observations
create_entities({
  "entities": [{
    "name": "John Smith",
    "entityType": "person",
    "observations": [
      "Senior software engineer",
      "Prefers TypeScript over JavaScript",
      "Works remotely from Seattle"
    ]
  }]
})

# Search memory
search_memory({
  "query": "TypeScript engineer",
  "maxResults": 10
})

# Create a relationship
create_relations({
  "relations": [{
    "fromEntity": "John Smith",
    "toEntity": "E-commerce Platform",
    "relationType": "WORKS_ON"
  }]
})
```

---

## ISON Format

### Why ISON?

ISON (Indexed Structured Object Notation) is specifically designed for LLM context efficiency:

```json
// JSON: 87 tokens
{
  "entities": [
    {"id": "e_123", "name": "Alice", "type": "person"},
    {"id": "e_456", "name": "Project X", "type": "project"}
  ],
  "relations": [
    {"from": "e_123", "to": "e_456", "type": "WORKS_ON"}
  ]
}
```

```ison
# ISON: 32 tokens (63% savings)
table.entities
id name type
:e_123 "Alice" person
:e_456 "Project X" project

table.relations
from to type
:e_123 :e_456 WORKS_ON
```

### Syntax Reference

```ison
# Comments start with #

# Tables - lists of similar items
table.entities
id name type
:e_001 "Alice" person
:e_002 "Bob" person

# Objects - single items with named fields
object.config
key1 key2 key3
value1 value2 value3

# References
:e_001          # Simple reference
:person:001     # Typed reference

# Values
"quoted string" # String with spaces
unquoted        # Simple string
42              # Integer
3.14            # Float
true            # Boolean
null            # Null value
```

### Reference Syntax in Responses

Claude is taught to use `:ref` syntax for token efficiency:

```
Instead of: "The user Alice (entity ID e_123) works on Project X (entity ID e_456)"
Claude says: "Alice (:e_123) works on Project X (:e_456)"

Token savings: ~40% in prose responses
```

---

## Configuration

### Environment Variables

```bash
# Storage Configuration
ISON_MEMORY_STORAGE_PATH=~/.ison-memory/memory.db
ISON_MEMORY_STORAGE_WAL_MODE=true
ISON_MEMORY_STORAGE_CACHE_SIZE=2000

# Compaction Configuration
ISON_MEMORY_COMPACTION_ENABLED=true
ISON_MEMORY_COMPACTION_STRATEGY=smart
ISON_MEMORY_COMPACTION_MAX_AGE_DAYS=180
ISON_MEMORY_COMPACTION_SCHEDULE="0 0 * * 0"

# Backup Configuration
ISON_MEMORY_BACKUP_ENABLED=true
ISON_MEMORY_BACKUP_DIR=~/.ison-memory/backups
ISON_MEMORY_BACKUP_MAX_BACKUPS=10
ISON_MEMORY_BACKUP_COMPRESS=true

# Server Configuration
ISON_MEMORY_SERVER_LOG_LEVEL=info
```

### Configuration File

Create `~/.ison-memory/config.toml`:

```toml
[storage]
path = "~/.ison-memory/memory.db"
wal_mode = true
cache_size = 2000
busy_timeout = 5000

[compaction]
enabled = true
strategy = "smart"
schedule = "0 0 * * 0"  # Weekly on Sunday
max_age_days = 180
min_access_count = 2

[backup]
enabled = true
backup_dir = "~/.ison-memory/backups"
max_backups = 10
compress = true
include_ison_export = true
schedule = "0 0 * * *"  # Daily

[index]
fts_enabled = true
auto_reindex = true

[server]
log_level = "info"

[logging]
level = "info"
file = "~/.ison-memory/logs/server.log"
```

---

## CLI Reference

```bash
# Server Commands
ison-memory serve                    # Start MCP server
ison-memory serve --log-level debug  # Start with debug logging

# Memory Operations
ison-memory stats                    # Show memory statistics
ison-memory search "query"           # Search memory
ison-memory search "query" --type person  # Search with type filter

# Maintenance
ison-memory compact                  # Run smart compaction
ison-memory compact --strategy aggressive  # Aggressive cleanup
ison-memory compact --dry-run        # Preview without changes

# Backup & Export
ison-memory backup                   # Create backup
ison-memory backups                  # List backups
ison-memory export --format ison     # Export to ISON file
ison-memory export --format isongraph --output graph.ison

# Configuration
ison-memory config                   # Show current config
ison-memory init                     # Initialize configuration
ison-memory init --force             # Reinitialize (overwrites)
```

---

## Documentation

Comprehensive documentation is available in the `docs/` directory:

| Document | Description |
|----------|-------------|
| [Architecture](docs/ARCHITECTURE.md) | System architecture and design |
| [API Reference](docs/API-REFERENCE.md) | Complete tool and API documentation |
| [Configuration](docs/CONFIGURATION.md) | Configuration options guide |
| [ISON Format](docs/ISON-FORMAT.md) | ISON format specification |
| [Use Cases](docs/USE-CASES.md) | Common use cases and examples |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and solutions |
| [CLAUDE.md](CLAUDE.md) | Instructions for Claude |

---

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/anthropics/ison-memory-mcp
cd ison-memory-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install with dev dependencies
pip install -e ".[dev]"
```

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=ison_memory_mcp

# Run specific test file
pytest tests/test_store.py
```

### Code Quality

```bash
# Type checking
mypy src

# Linting
ruff check src

# Format code
ruff format src
```

### Project Structure

```
ison-memory-mcp/
├── src/
│   └── ison_memory_mcp/
│       ├── __init__.py        # Package entry point
│       ├── server.py          # MCP server implementation
│       ├── store.py           # SQLite memory store
│       ├── models.py          # Data models
│       ├── config.py          # Configuration management
│       ├── compaction.py      # Memory compaction
│       ├── prompts.py         # System prompts for ISON
│       ├── ison_protocol.py   # ISON parser/serializer
│       └── cli.py             # CLI interface
├── tests/
│   ├── test_store.py
│   ├── test_server.py
│   └── conftest.py
├── docs/
│   ├── ARCHITECTURE.md
│   ├── API-REFERENCE.md
│   └── ...
├── configs/                   # Example configurations
├── scripts/                   # Installation scripts
├── pyproject.toml
├── README.md
├── CLAUDE.md
└── LICENSE
```

---

## Data Model

### Entities

Primary objects in the knowledge graph:

| Type | Description | Example |
|------|-------------|---------|
| `person` | People, users, contacts | "John Smith" |
| `project` | Work projects | "E-commerce Platform" |
| `organization` | Companies, teams | "Acme Corp" |
| `tool` | Software, frameworks | "React", "PostgreSQL" |
| `concept` | Ideas, patterns | "Clean Architecture" |
| `location` | Places | "San Francisco" |
| `event` | Meetings, milestones | "Q4 Planning" |
| `document` | Files, specs | "API Spec v2" |
| `code` | Repositories, modules | "auth-service" |
| `task` | Action items | "Fix login bug" |
| `preference` | User preferences | "Dark Mode" |

### Relations

Typed relationships between entities:

| Type | Description | Example |
|------|-------------|---------|
| `CREATOR_OF` | Created something | Person → Project |
| `MEMBER_OF` | Belongs to | Person → Organization |
| `LEADS` | Leadership | Person → Team |
| `USES` | Utilizes | Project → Tool |
| `WORKS_ON` | Active work | Person → Project |
| `DEPENDS_ON` | Dependency | Project → Library |
| `KNOWS` | Personal relation | Person → Person |
| `PREFERS` | Preference | Person → Preference |

---

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

**Mahesh Vaikri** - [ISON Project](https://www.ison.dev)

## Links

- [ISON Format Specification](https://www.ison.dev/spec)
- [ISONGraph Documentation](https://www.ison.dev/isongraph)
- [MCP Protocol](https://modelcontextprotocol.io)
- [GitHub Repository](https://github.com/anthropics/ison-memory-mcp)

---

## Support

- **Issues**: [GitHub Issues](https://github.com/anthropics/ison-memory-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/anthropics/ison-memory-mcp/discussions)

