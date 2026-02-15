# ISON Memory MCP - Architecture Documentation

This document provides a comprehensive overview of the ISON Memory MCP system architecture, design decisions, and implementation details.

## Table of Contents

- [System Overview](#system-overview)
- [Component Architecture](#component-architecture)
- [Data Flow](#data-flow)
- [Storage Architecture](#storage-architecture)
- [MCP Protocol Integration](#mcp-protocol-integration)
- [Memory Management](#memory-management)
- [Security Model](#security-model)
- [Performance Considerations](#performance-considerations)
- [Scalability](#scalability)

---

## System Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          CLAUDE APPLICATIONS                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐ │
│  │   Claude    │  │   Claude    │  │   VSCode    │  │   Custom Agents     │ │
│  │   Desktop   │  │  Code CLI   │  │  Extension  │  │   (MCP Client)      │ │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘ │
└─────────┼────────────────┼────────────────┼─────────────────────┼───────────┘
          │                │                │                     │
          └────────────────┴────────────────┴─────────────────────┘
                                    │
                          MCP Protocol (JSON-RPC 2.0)
                          Transport: stdio / HTTP
                                    │
┌───────────────────────────────────▼─────────────────────────────────────────┐
│                        ISON MEMORY MCP SERVER                                │
│                                                                              │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         MCP PROTOCOL LAYER                              │ │
│  │  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │ │
│  │  │    12 Tools      │  │   3 Resources    │  │      3 Prompts       │  │ │
│  │  │  Entity CRUD     │  │  System Prompts  │  │  Context Injection   │  │ │
│  │  │  Search/Query    │  │  Graph Snapshot  │  │  Output Formatting   │  │ │
│  │  │  Maintenance     │  │  Reference Guide │  │  Entity References   │  │ │
│  │  └──────────────────┘  └──────────────────┘  └──────────────────────┘  │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│                                    │                                         │
│  ┌─────────────────────────────────▼────────────────────────────────────┐   │
│  │                        BUSINESS LOGIC LAYER                           │   │
│  │  ┌──────────────────────┐  ┌──────────────────────────────────────┐  │   │
│  │  │    Memory Store      │  │         ISON Formatter               │  │   │
│  │  │  - Entity Management │  │  - Table serialization               │  │   │
│  │  │  - Observation CRUD  │  │  - Reference generation              │  │   │
│  │  │  - Relation Graph    │  │  - Compact output                    │  │   │
│  │  │  - Search/Traverse   │  │  - Response formatting               │  │   │
│  │  └──────────────────────┘  └──────────────────────────────────────┘  │   │
│  │  ┌──────────────────────┐  ┌──────────────────────────────────────┐  │   │
│  │  │   Compaction Engine  │  │        Backup Manager                │  │   │
│  │  │  - Time-based        │  │  - Scheduled backups                 │  │   │
│  │  │  - Relevance-based   │  │  - Compression                       │  │   │
│  │  │  - Smart (ML-based)  │  │  - ISON export                       │  │   │
│  │  │  - Access tracking   │  │  - Rotation policy                   │  │   │
│  │  └──────────────────────┘  └──────────────────────────────────────┘  │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                    │                                         │
│  ┌─────────────────────────────────▼────────────────────────────────────┐   │
│  │                        PERSISTENCE LAYER                              │   │
│  │  ┌──────────────────────────────────────────────────────────────────┐│   │
│  │  │                      SQLite Database                              ││   │
│  │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐ ││   │
│  │  │  │  entities  │  │observations│  │  relations │  │ obs_fts    │ ││   │
│  │  │  │  table     │  │   table    │  │   table    │  │ (FTS5)     │ ││   │
│  │  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘ ││   │
│  │  │                                                                   ││   │
│  │  │  Features: WAL Mode | ACID | Auto-vacuum | Busy Timeout          ││   │
│  │  └──────────────────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────────────────────┘   │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

### Design Principles

1. **Token Efficiency First**: Every output is optimized for minimal token consumption
2. **Reliability**: ACID-compliant storage with automatic recovery
3. **Simplicity**: Single-file SQLite database, no external dependencies
4. **Portability**: Cross-platform support with platform-aware paths
5. **Extensibility**: Modular design for easy feature additions
6. **Privacy**: Local-first storage, no cloud dependencies

---

## Component Architecture

### 1. Server Component (`server.py`)

The MCP server is the main entry point, handling protocol communication and routing.

```python
class ISONMemoryServer:
    """
    Main server class orchestrating all components.

    Responsibilities:
    - MCP protocol handling (tools, resources, prompts)
    - Request routing to appropriate handlers
    - Response formatting in ISON
    - Lifecycle management (init, shutdown)
    """

    def __init__(self, config: MemoryConfig):
        self.server = Server("ison-memory")
        self.store: MemoryStore
        self.compactor: MemoryCompactor
        self.backup_manager: BackupManager

        self._register_tools()      # 12 tools
        self._register_resources()  # 3 resources
        self._register_prompts()    # 3 prompts
```

**Key Methods:**

| Method | Purpose |
|--------|---------|
| `_register_tools()` | Register all 12 MCP tools |
| `_register_resources()` | Register system context resources |
| `_register_prompts()` | Register context injection prompts |
| `initialize()` | Initialize store, compactor, backup manager |
| `shutdown()` | Cleanup and close connections |
| `run()` | Start server event loop |

### 2. Memory Store (`store.py`)

The core storage engine managing all persistent data.

```python
class MemoryStore:
    """
    SQLite-backed memory storage with ISON export capabilities.

    Responsibilities:
    - Entity CRUD operations
    - Observation management
    - Relation graph operations
    - Full-text search (FTS5)
    - Multi-hop graph traversal
    - ISON/ISONL/ISONGraph export
    """

    def __init__(self, config: MemoryConfig):
        self.db_path = config.storage.path
        self.connection: aiosqlite.Connection
```

**Core Operations:**

```
Entity Operations:
├── create_entity(name, type) → Entity
├── get_entity(id) → Entity
├── find_entity_by_name(name) → Entity
├── update_entity(id, name?, type?) → Entity
├── delete_entity(id) → bool
└── list_entities(type?) → List[Entity]

Observation Operations:
├── create_observation(entity_id, content, source, confidence) → Observation
├── get_observations(entity_id) → List[Observation]
├── delete_observation(id) → bool
└── search_observations(query) → List[Observation]

Relation Operations:
├── create_relation(from_id, to_id, type, bidirectional) → Relation
├── get_relations(entity_id, type?) → List[Relation]
├── delete_relation(id) → bool
└── get_connected_entities(entity_id, hops) → List[Entity]

Search Operations:
├── search(query, max_results) → SearchResult
├── multi_hop_search(entity_id, max_hops, type?) → SearchResult
└── fts_search(query) → List[Observation]

Export Operations:
├── export_to_ison() → str
├── export_to_isonl() → str
└── export_to_isongraph() → str
```

### 3. Data Models (`models.py`)

Dataclass definitions with ISON serialization.

```python
@dataclass
class Entity:
    id: str                    # e_<uuid8>
    name: str                  # Human-readable name
    entity_type: str           # person, project, tool, etc.
    created_at: datetime       # UTC timestamp
    updated_at: Optional[datetime]
    access_count: int = 0      # For compaction scoring
    last_accessed: Optional[datetime]

    def to_ison_row(self) -> str:
        """Serialize to ISON table row"""
        return f':{self.id} "{self.name}" {self.entity_type}'

@dataclass
class Observation:
    id: str                    # o_<uuid8>
    entity_id: str             # Parent entity reference
    content: str               # The atomic fact
    source: str                # chat, code, manual, import, inference
    confidence: float          # 0.0-1.0
    created_at: datetime
    access_count: int = 0

    def to_ison_row(self) -> str:
        """Serialize to ISON table row"""
        return f':{self.id} :{self.entity_id} "{self.content}" {self.confidence}'

@dataclass
class Relation:
    id: str                    # r_<uuid8>
    from_entity_id: str        # Source entity
    to_entity_id: str          # Target entity
    relation_type: str         # WORKS_ON, USES, etc.
    created_at: datetime

    def to_ison_row(self) -> str:
        """Serialize to ISON table row"""
        return f':{self.from_entity_id} :{self.to_entity_id} {self.relation_type}'
```

### 4. Configuration (`config.py`)

Hierarchical configuration management.

```python
@dataclass
class MemoryConfig:
    storage: StorageConfig      # Database settings
    compaction: CompactionConfig # Cleanup policies
    backup: BackupConfig        # Backup settings
    index: IndexConfig          # Search index settings
    server: ServerConfig        # Server settings
    logging: LoggingConfig      # Logging configuration

# Configuration priority (highest to lowest):
# 1. Environment variables (ISON_MEMORY_*)
# 2. Project config file (.ison-memory.toml)
# 3. User config file (~/.ison-memory/config.toml)
# 4. Default values
```

### 5. Compaction Engine (`compaction.py`)

Memory cleanup and optimization.

```python
class MemoryCompactor:
    """
    Manages memory growth through various compaction strategies.

    Strategies:
    - time_based: Remove old items
    - relevance: Remove low-access items
    - aggressive: Both time + relevance
    - smart: ML-based adaptive cleanup
    """

    async def compact(
        self,
        store: MemoryStore,
        strategy: CompactionStrategy,
        dry_run: bool = False
    ) -> CompactionResult
```

### 6. ISON Protocol (`ison_protocol.py`)

ISON parsing and serialization utilities.

```python
class ISONParser:
    """Parse ISON text to Python dicts"""
    @classmethod
    def parse(cls, text: str) -> dict[str, Any]

class ISONSerializer:
    """Serialize Python dicts to ISON format"""
    @classmethod
    def dumps(cls, data: dict[str, Any], name: str) -> str

class ISONResponse:
    """Builder for constructing ISON responses"""
    def add_table(self, name: str, rows: list[dict]) -> 'ISONResponse'
    def add_object(self, name: str, data: dict) -> 'ISONResponse'
    def add_comment(self, text: str) -> 'ISONResponse'
    def build(self) -> str
```

### 7. System Prompts (`prompts.py`)

ISON-aware prompts for Claude's context.

```python
ISON_MEMORY_SYSTEM_PROMPT = """
## ISON Memory System

You have access to a persistent knowledge graph using ISON format.
ISON is a token-efficient format - use it for both reading AND writing.

### Reading ISON (Input)
Memory data comes in ISON table format:
table.entities
id name type
:e_123 "Alice" person

### Writing ISON (Output)
When referencing memory entities, use compact :ref syntax:
INSTEAD OF: "The user Alice (entity ID e_123)"
USE: "Alice (:e_123)"
"""
```

---

## Data Flow

### Request Flow (Tool Call)

```
┌─────────────────────────────────────────────────────────────────────┐
│                        REQUEST FLOW                                  │
└─────────────────────────────────────────────────────────────────────┘

Claude Application
       │
       │ 1. Tool Call: create_entities({entities: [...]})
       ▼
┌──────────────────┐
│   MCP Protocol   │ ← JSON-RPC 2.0 over stdio
│   (Transport)    │
└────────┬─────────┘
         │ 2. Parse JSON-RPC request
         ▼
┌──────────────────┐
│  ISONMemoryServer│
│  call_tool()     │ ← Route to appropriate handler
└────────┬─────────┘
         │ 3. Dispatch to handler
         ▼
┌──────────────────┐
│ _handle_create_  │
│    entities()    │ ← Validate input, process logic
└────────┬─────────┘
         │ 4. Database operations
         ▼
┌──────────────────┐
│  MemoryStore     │
│  create_entity() │ ← SQLite transactions
└────────┬─────────┘
         │ 5. Format response
         ▼
┌──────────────────┐
│  ISON Formatter  │
│  format_entity_  │ ← Convert to ISON table format
│    created()     │
└────────┬─────────┘
         │ 6. Return ISON response
         ▼
┌──────────────────┐
│   MCP Protocol   │
│   TextContent    │ ← Wrap in MCP response
└────────┬─────────┘
         │
         ▼
Claude Application
(Receives ISON-formatted response)
```

### Search Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SEARCH FLOW                                   │
└─────────────────────────────────────────────────────────────────────┘

search_memory({query: "TypeScript engineer"})
       │
       ▼
┌──────────────────┐
│ _handle_search_  │
│    memory()      │
└────────┬─────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ Entity │ │  FTS5  │
│ Name   │ │ Search │
│ Search │ │        │
└────┬───┘ └────┬───┘
     │          │
     └────┬─────┘
          │
          ▼ Merge & Rank Results
┌──────────────────┐
│ Get Related:     │
│ - Observations   │
│ - Relations      │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ SearchResult     │
│   .to_ison()     │
└────────┬─────────┘
         │
         ▼
# Memory Search Results
# Use :refs when discussing these entities

table.entities
id name type relevance
:e_001 "John Smith" person 0.95

table.observations
id entity_id content
:o_001 :e_001 "Senior TypeScript developer"

table.relations
from to type
:e_001 :e_002 WORKS_ON
```

### Multi-Hop Traversal Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│                   MULTI-HOP TRAVERSAL FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

multi_hop_search({entityName: "John", maxHops: 2})
       │
       ▼
┌──────────────────────────────────────────────────────────────────┐
│                     BFS TRAVERSAL                                 │
│                                                                   │
│   Start: John (hop 0)                                            │
│          │                                                        │
│   ┌──────┴──────┐                                                │
│   │             │                                                 │
│   ▼             ▼                                                 │
│ Project A    React        (hop 1)                                │
│   │             │                                                 │
│   └──────┬──────┘                                                │
│          │                                                        │
│   ┌──────┴──────┐                                                │
│   │             │                                                 │
│   ▼             ▼                                                 │
│ Alice      TypeScript     (hop 2) ← max_hops reached            │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
       │
       ▼
# Multi-Hop Search from 'John'
# Max hops: 2

table.entities
id name type hop
:e_001 "John" person 0
:e_002 "Project A" project 1
:e_003 "React" tool 1
:e_004 "Alice" person 2
:e_005 "TypeScript" tool 2

table.paths
from relation to hop
:e_001 WORKS_ON :e_002 1
:e_001 USES :e_003 1
:e_002 MEMBER_OF :e_004 2
:e_003 SIMILAR_TO :e_005 2
```

---

## Storage Architecture

### SQLite Schema

```sql
-- =====================================================
-- ENTITIES TABLE
-- =====================================================
CREATE TABLE entities (
    id TEXT PRIMARY KEY,           -- e_<uuid8>
    name TEXT NOT NULL UNIQUE,     -- Human-readable name
    entity_type TEXT NOT NULL,     -- person, project, tool, etc.
    created_at TEXT NOT NULL,      -- ISO 8601 UTC timestamp
    updated_at TEXT,               -- Last modification
    access_count INTEGER DEFAULT 0, -- Usage tracking
    last_accessed TEXT             -- Last access timestamp
);

-- Indexes for common queries
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_name ON entities(name);
CREATE INDEX idx_entities_access ON entities(access_count DESC);

-- =====================================================
-- OBSERVATIONS TABLE
-- =====================================================
CREATE TABLE observations (
    id TEXT PRIMARY KEY,           -- o_<uuid8>
    entity_id TEXT NOT NULL,       -- FK to entities
    content TEXT NOT NULL,         -- The atomic fact
    source TEXT DEFAULT 'chat',    -- Origin: chat, code, manual, etc.
    confidence REAL DEFAULT 1.0,   -- 0.0-1.0 certainty score
    created_at TEXT NOT NULL,
    access_count INTEGER DEFAULT 0,

    FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
);

CREATE INDEX idx_observations_entity ON observations(entity_id);
CREATE INDEX idx_observations_source ON observations(source);

-- =====================================================
-- FULL-TEXT SEARCH INDEX (FTS5)
-- =====================================================
CREATE VIRTUAL TABLE observations_fts USING fts5(
    content,
    content='observations',
    content_rowid='rowid',
    tokenize='porter unicode61'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER observations_ai AFTER INSERT ON observations BEGIN
    INSERT INTO observations_fts(rowid, content)
    VALUES (new.rowid, new.content);
END;

CREATE TRIGGER observations_ad AFTER DELETE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content)
    VALUES('delete', old.rowid, old.content);
END;

CREATE TRIGGER observations_au AFTER UPDATE ON observations BEGIN
    INSERT INTO observations_fts(observations_fts, rowid, content)
    VALUES('delete', old.rowid, old.content);
    INSERT INTO observations_fts(rowid, content)
    VALUES (new.rowid, new.content);
END;

-- =====================================================
-- RELATIONS TABLE
-- =====================================================
CREATE TABLE relations (
    id TEXT PRIMARY KEY,           -- r_<uuid8>
    from_entity_id TEXT NOT NULL,  -- Source entity FK
    to_entity_id TEXT NOT NULL,    -- Target entity FK
    relation_type TEXT NOT NULL,   -- WORKS_ON, USES, etc.
    created_at TEXT NOT NULL,

    FOREIGN KEY (from_entity_id) REFERENCES entities(id) ON DELETE CASCADE,
    FOREIGN KEY (to_entity_id) REFERENCES entities(id) ON DELETE CASCADE,

    UNIQUE(from_entity_id, to_entity_id, relation_type)
);

CREATE INDEX idx_relations_from ON relations(from_entity_id);
CREATE INDEX idx_relations_to ON relations(to_entity_id);
CREATE INDEX idx_relations_type ON relations(relation_type);

-- =====================================================
-- METADATA TABLE
-- =====================================================
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Store schema version, last compaction, etc.
INSERT INTO metadata (key, value, updated_at) VALUES
    ('schema_version', '1', datetime('now')),
    ('created_at', datetime('now'), datetime('now'));
```

### WAL Mode Benefits

```
┌─────────────────────────────────────────────────────────────────────┐
│                    WRITE-AHEAD LOGGING (WAL)                         │
└─────────────────────────────────────────────────────────────────────┘

Traditional (Rollback Journal):
┌─────────┐    ┌─────────┐    ┌─────────┐
│  Read   │ ── │ BLOCKED │ ── │  Write  │
└─────────┘    └─────────┘    └─────────┘
              Readers wait for writers

WAL Mode:
┌─────────┐                   ┌─────────┐
│  Read   │ ───────────────── │  Write  │
└─────────┘  Concurrent!      └─────────┘
         Both can proceed simultaneously

Benefits:
✓ Concurrent reads during writes
✓ Faster write performance
✓ Better crash recovery
✓ Reduced fsync operations
```

### ID Generation

```python
def generate_id(prefix: str) -> str:
    """
    Generate a unique ID with type prefix.

    Format: {prefix}_{uuid8}

    Examples:
    - e_a1b2c3d4 (entity)
    - o_e5f6g7h8 (observation)
    - r_i9j0k1l2 (relation)

    UUID8 = first 8 chars of UUID4 = 2^32 possibilities
    Collision probability: < 0.01% for < 100K items
    """
    return f"{prefix}_{uuid.uuid4().hex[:8]}"
```

---

## MCP Protocol Integration

### Tool Registration

```python
def _register_tools(self) -> None:
    """Register all MCP tools with the server."""

    @self.server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="create_entities",
                description="Create entities in the knowledge graph...",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "entities": {
                            "type": "array",
                            "items": {...}
                        }
                    },
                    "required": ["entities"]
                }
            ),
            # ... 11 more tools
        ]

    @self.server.call_tool()
    async def call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
        # Route to appropriate handler
        handlers = {
            "create_entities": self._handle_create_entities,
            "search_memory": self._handle_search_memory,
            # ... etc
        }
        return await handlers[name](arguments)
```

### Resource Registration

```python
def _register_resources(self) -> None:
    """Register MCP resources for context injection."""

    @self.server.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="ison-memory://system/prompt",
                name="ISON Memory System Prompt",
                description="System prompt teaching Claude ISON I/O",
                mimeType="text/plain",
            ),
            Resource(
                uri="ison-memory://system/reference",
                name="ISON Quick Reference",
                mimeType="text/plain",
            ),
            Resource(
                uri="ison-memory://graph/current",
                name="Current Knowledge Graph",
                mimeType="text/plain",
            ),
        ]

    @self.server.read_resource()
    async def read_resource(uri: str) -> str:
        if uri == "ison-memory://system/prompt":
            return get_system_prompt()
        elif uri == "ison-memory://graph/current":
            return await self.store.export_to_ison()
        # ...
```

### Prompt Registration

```python
def _register_prompts(self) -> None:
    """Register MCP prompts for context initialization."""

    @self.server.list_prompts()
    async def list_prompts() -> list[Prompt]:
        return [
            Prompt(
                name="ison-memory-context",
                description="Initialize with full memory context",
                arguments=[
                    PromptArgument(name="include_graph", required=False),
                    PromptArgument(name="topic", required=False),
                ],
            ),
            # ...
        ]

    @self.server.get_prompt()
    async def get_prompt(name: str, arguments: dict) -> GetPromptResult:
        if name == "ison-memory-context":
            content = get_system_prompt()
            if arguments.get("include_graph"):
                content += await self.store.export_to_ison()
            return GetPromptResult(
                messages=[PromptMessage(role="user", content=content)]
            )
```

---

## Memory Management

### Compaction Strategies

```
┌─────────────────────────────────────────────────────────────────────┐
│                    COMPACTION STRATEGIES                             │
└─────────────────────────────────────────────────────────────────────┘

1. TIME-BASED
   ─────────────────────────────────────────────────
   Policy: Remove items older than N days

   Timeline:
   ├── 180 days ago ──── 90 days ago ──── Today
   │   [REMOVE]          [REMOVE]         [KEEP]

   Use case: Regular maintenance, prevent unbounded growth

2. RELEVANCE-BASED
   ─────────────────────────────────────────────────
   Policy: Remove items with access_count < threshold

   Access Pattern:
   Entity A: ████████████ (12 accesses) → KEEP
   Entity B: ██ (2 accesses)            → REMOVE
   Entity C: ████████ (8 accesses)      → KEEP

   Use case: Prioritize frequently-used information

3. AGGRESSIVE
   ─────────────────────────────────────────────────
   Policy: Combine time + relevance with stricter thresholds

   Remove if: (age > 30 days) AND (access_count < 3)

   Use case: Major cleanup, storage constraints

4. SMART (Recommended)
   ─────────────────────────────────────────────────
   Policy: Adaptive cleanup based on multiple factors

   Scoring factors:
   ├── Age factor: newer = higher score
   ├── Access frequency: more access = higher score
   ├── Connectivity: more relations = higher score
   ├── Source confidence: higher confidence = higher score
   └── Entity importance: entities preserved over observations

   Keep if: score > dynamic_threshold

   Use case: Default strategy, balances all factors
```

### Access Tracking

```python
async def record_access(self, entity_id: str) -> None:
    """
    Track entity access for compaction scoring.
    Called on every search hit and explicit read.
    """
    await self.db.execute("""
        UPDATE entities
        SET access_count = access_count + 1,
            last_accessed = ?
        WHERE id = ?
    """, (utc_now().isoformat(), entity_id))
```

### Backup Strategy

```
┌─────────────────────────────────────────────────────────────────────┐
│                      BACKUP STRATEGY                                 │
└─────────────────────────────────────────────────────────────────────┘

Backup Types:
├── SQLite Backup (full database copy)
│   └── Compressed with gzip (~70% size reduction)
│
└── ISON Export (human-readable)
    └── Version controllable, portable

Rotation Policy:
├── Keep last N backups (configurable)
├── Delete oldest when limit reached
└── Never delete if backup failed

Schedule:
├── Daily: Full backup + ISON export
├── Weekly: Verify backup integrity
└── Monthly: Archive to long-term storage (optional)

Recovery:
├── Automatic: Load from most recent valid backup
├── Manual: Restore specific backup via CLI
└── Import: Load from ISON export file
```

---

## Security Model

### Data Security

```
┌─────────────────────────────────────────────────────────────────────┐
│                      SECURITY MODEL                                  │
└─────────────────────────────────────────────────────────────────────┘

1. LOCAL-FIRST STORAGE
   ─────────────────────────────────────────────────
   ✓ All data stored on local filesystem
   ✓ No cloud sync by default
   ✓ User controls data location

   Default paths:
   ├── ~/.ison-memory/memory.db      (database)
   ├── ~/.ison-memory/backups/       (backups)
   └── ~/.ison-memory/config.toml    (configuration)

2. NO SENSITIVE DATA STORAGE
   ─────────────────────────────────────────────────
   Built-in checks prevent storing:
   ✗ Passwords, API keys, tokens
   ✗ Credit card numbers
   ✗ Social security numbers
   ✗ Private keys

   Claude is instructed to:
   - Never store credentials
   - Ask before storing sensitive personal info
   - Respect deletion requests

3. FILE PERMISSIONS
   ─────────────────────────────────────────────────
   Database: 0600 (owner read/write only)
   Backups: 0600
   Config: 0644

4. TRANSPORT SECURITY
   ─────────────────────────────────────────────────
   stdio: Process-level isolation (most common)
   HTTP: Localhost only (127.0.0.1), optional TLS
```

### Input Validation

```python
# Entity name validation
def validate_entity_name(name: str) -> str:
    if not name or not name.strip():
        raise ValueError("Entity name cannot be empty")
    if len(name) > 500:
        raise ValueError("Entity name too long (max 500 chars)")
    # Sanitize but preserve Unicode
    return name.strip()

# Entity type validation
VALID_ENTITY_TYPES = {
    "person", "project", "organization", "tool", "concept",
    "location", "event", "document", "code", "task", "preference"
}

def validate_entity_type(entity_type: str) -> str:
    if entity_type not in VALID_ENTITY_TYPES:
        raise ValueError(f"Invalid entity type: {entity_type}")
    return entity_type

# Observation content validation
def validate_observation(content: str) -> str:
    if not content or not content.strip():
        raise ValueError("Observation content cannot be empty")
    if len(content) > 10000:
        raise ValueError("Observation too long (max 10000 chars)")
    return content.strip()
```

---

## Performance Considerations

### Query Optimization

```sql
-- Optimized search query with FTS5
SELECT e.*,
       bm25(observations_fts) as relevance
FROM entities e
JOIN observations o ON e.id = o.entity_id
JOIN observations_fts ON observations_fts.rowid = o.rowid
WHERE observations_fts MATCH ?
ORDER BY relevance
LIMIT ?;

-- Optimized multi-hop traversal
WITH RECURSIVE connected(id, depth) AS (
    SELECT id, 0 FROM entities WHERE id = ?
    UNION ALL
    SELECT
        CASE WHEN r.from_entity_id = c.id
             THEN r.to_entity_id
             ELSE r.from_entity_id
        END,
        c.depth + 1
    FROM connected c
    JOIN relations r ON r.from_entity_id = c.id OR r.to_entity_id = c.id
    WHERE c.depth < ?
)
SELECT DISTINCT e.*
FROM entities e
JOIN connected c ON e.id = c.id;
```

### Connection Pooling

```python
class MemoryStore:
    def __init__(self, config: MemoryConfig):
        self._connection_pool: list[aiosqlite.Connection] = []
        self._pool_size = 5

    async def get_connection(self) -> aiosqlite.Connection:
        """Get connection from pool or create new one."""
        if self._connection_pool:
            return self._connection_pool.pop()
        return await aiosqlite.connect(self.db_path)

    async def release_connection(self, conn: aiosqlite.Connection):
        """Return connection to pool."""
        if len(self._connection_pool) < self._pool_size:
            self._connection_pool.append(conn)
        else:
            await conn.close()
```

### Caching Strategy

```python
from functools import lru_cache

class MemoryStore:
    @lru_cache(maxsize=1000)
    def _get_entity_cached(self, entity_id: str) -> Optional[Entity]:
        """Cache frequently accessed entities."""
        pass

    def invalidate_cache(self, entity_id: str = None):
        """Clear cache on write operations."""
        if entity_id:
            self._get_entity_cached.cache_clear()
        else:
            self._get_entity_cached.cache_clear()
```

---

## Scalability

### Current Limits

| Metric | Soft Limit | Hard Limit | Notes |
|--------|------------|------------|-------|
| Entities | 50,000 | 100,000 | Configurable |
| Observations/Entity | 1,000 | 5,000 | Compaction helps |
| Relations | 100,000 | 500,000 | Index optimized |
| Database Size | 100 MB | 1 GB | SQLite limit: 281 TB |
| Search Results | 100 | 1,000 | Pagination available |

### Scaling Strategies

```
┌─────────────────────────────────────────────────────────────────────┐
│                    SCALING STRATEGIES                                │
└─────────────────────────────────────────────────────────────────────┘

VERTICAL SCALING (Current Approach):
├── Increase cache_size for better read performance
├── Use SSD storage for faster I/O
├── Increase memory for larger working sets
└── Optimize queries with EXPLAIN QUERY PLAN

HORIZONTAL SCALING (Future Options):
├── Sharding by entity type or user
├── Read replicas for search-heavy workloads
├── Distributed cache (Redis) for hot data
└── Event sourcing for write-heavy scenarios

DATA LIFECYCLE:
├── Archive old data to cold storage
├── Summarize observations (reduce granularity)
├── Export to data warehouse for analytics
└── Federated queries across multiple stores
```

### Memory Growth Projection

```
Assumptions:
- 10 entities/day
- 30 observations/entity
- 5 relations/entity

Monthly Growth:
- Entities: ~300
- Observations: ~9,000
- Relations: ~1,500
- Storage: ~5 MB

Annual Growth:
- Entities: ~3,600
- Observations: ~108,000
- Relations: ~18,000
- Storage: ~60 MB

With Smart Compaction (20% reduction):
- Annual storage: ~48 MB
- 5-year projection: ~240 MB
```

---

## Future Architecture Considerations

### Planned Enhancements

1. **Vector Embeddings**: Semantic search using embeddings
2. **Incremental Sync**: Efficient updates for large graphs
3. **Multi-User Support**: User-scoped memory isolation
4. **Graph Analytics**: Centrality, clustering, path analysis
5. **Memory Sharing**: Export/import between instances

### Extension Points

```python
# Plugin architecture (future)
class MemoryPlugin(ABC):
    @abstractmethod
    async def on_entity_created(self, entity: Entity) -> None: ...

    @abstractmethod
    async def on_search(self, query: str, results: list) -> list: ...

class EmbeddingPlugin(MemoryPlugin):
    """Add vector embeddings for semantic search."""
    async def on_entity_created(self, entity: Entity) -> None:
        embedding = await self.embed(entity.name)
        await self.store_embedding(entity.id, embedding)
```

---

This architecture provides a solid foundation for Claude's persistent memory needs while maintaining simplicity, reliability, and token efficiency. The modular design allows for future enhancements without disrupting the core functionality.
