# ISON Memory MCP - API Reference

Complete API documentation for all tools, resources, and prompts provided by the ISON Memory MCP server.

## Table of Contents

- [Overview](#overview)
- [Tools](#tools)
  - [Entity Management](#entity-management)
  - [Observation Management](#observation-management)
  - [Relation Management](#relation-management)
  - [Search & Query](#search--query)
  - [Maintenance](#maintenance)
- [Resources](#resources)
- [Prompts](#prompts)
- [Data Types](#data-types)
- [Error Handling](#error-handling)
- [Response Formats](#response-formats)

---

## Overview

The ISON Memory MCP server exposes its functionality through the Model Context Protocol (MCP):

| Component | Count | Purpose |
|-----------|-------|---------|
| **Tools** | 12 | CRUD operations, search, maintenance |
| **Resources** | 3 | System prompts, live graph data |
| **Prompts** | 3 | Context injection for conversations |

All responses are formatted in ISON for token efficiency.

---

## Tools

### Entity Management

#### `create_entities`

Create one or more entities in the knowledge graph with optional initial observations.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "entities": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "name": {
            "type": "string",
            "description": "Human-readable name for the entity",
            "maxLength": 500
          },
          "entityType": {
            "type": "string",
            "description": "Classification type",
            "enum": [
              "person", "project", "organization", "tool", "concept",
              "location", "event", "document", "code", "task", "preference"
            ]
          },
          "observations": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Initial observations (atomic facts) about the entity",
            "maxItems": 100
          }
        },
        "required": ["name", "entityType"]
      },
      "minItems": 1,
      "maxItems": 50
    }
  },
  "required": ["entities"]
}
```

**Example Request:**

```json
{
  "entities": [
    {
      "name": "John Smith",
      "entityType": "person",
      "observations": [
        "Senior software engineer",
        "Prefers TypeScript over JavaScript",
        "Works remotely from Seattle"
      ]
    },
    {
      "name": "E-commerce Platform",
      "entityType": "project",
      "observations": [
        "Target launch Q2 2025",
        "Using React and Node.js"
      ]
    }
  ]
}
```

**Response (ISON):**

```ison
# Entity Creation Result
# Created: 2 entities

table.created
id name type status observations_added
:e_a1b2c3d4 "John Smith" person created 3
:e_e5f6g7h8 "E-commerce Platform" project created 2

# Tip: Reference these entities as :id in future responses
```

**Behavior Notes:**

- If an entity with the same name exists, observations are added to it
- Status will be `existing` for duplicate names, `created` for new entities
- Entity IDs are generated as `e_<uuid8>`

---

#### `update_entity`

Modify an existing entity's name or type.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "entityName": {
      "type": "string",
      "description": "Current name of the entity to update"
    },
    "newName": {
      "type": "string",
      "description": "New name for the entity (optional)"
    },
    "newType": {
      "type": "string",
      "description": "New entity type (optional)",
      "enum": [
        "person", "project", "organization", "tool", "concept",
        "location", "event", "document", "code", "task", "preference"
      ]
    }
  },
  "required": ["entityName"]
}
```

**Example Request:**

```json
{
  "entityName": "John Smith",
  "newName": "John Smith-Anderson",
  "newType": "person"
}
```

**Response (ISON):**

```ison
# Entity Updated

object.entity
id name type updated_at
:e_a1b2c3d4 "John Smith-Anderson" person 2025-01-15T10:30:45Z
```

**Behavior Notes:**

- At least one of `newName` or `newType` should be provided
- Returns error if entity not found
- Updates cascade to search indexes

---

#### `delete_entities`

Remove entities and all their associated observations and relations.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "entityNames": {
      "type": "array",
      "items": {"type": "string"},
      "description": "Names of entities to delete",
      "minItems": 1,
      "maxItems": 100
    }
  },
  "required": ["entityNames"]
}
```

**Example Request:**

```json
{
  "entityNames": ["Old Project", "Deprecated Tool"]
}
```

**Response (ISON):**

```ison
# Entities Deleted
# Count: 2

table.deleted
id name
:e_xyz123 "Old Project"
:e_abc456 "Deprecated Tool"
```

**Behavior Notes:**

- Deletes cascade to observations and relations
- Non-existent entities are reported in errors table
- **This action is irreversible**

---

### Observation Management

#### `create_observations`

Add atomic facts to existing entities.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "observations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "entityName": {
            "type": "string",
            "description": "Name of the entity to add observation to"
          },
          "content": {
            "type": "string",
            "description": "The observation (atomic fact)",
            "maxLength": 10000
          },
          "source": {
            "type": "string",
            "description": "Source of the observation",
            "enum": ["chat", "code", "manual", "import", "inference"],
            "default": "chat"
          },
          "confidence": {
            "type": "number",
            "description": "Confidence score",
            "minimum": 0.0,
            "maximum": 1.0,
            "default": 1.0
          }
        },
        "required": ["entityName", "content"]
      },
      "minItems": 1,
      "maxItems": 100
    }
  },
  "required": ["observations"]
}
```

**Example Request:**

```json
{
  "observations": [
    {
      "entityName": "John Smith",
      "content": "Promoted to Tech Lead in January 2025",
      "source": "chat",
      "confidence": 1.0
    },
    {
      "entityName": "John Smith",
      "content": "Prefers async communication",
      "source": "inference",
      "confidence": 0.85
    }
  ]
}
```

**Response (ISON):**

```ison
# Observations Added
# Count: 2

table.added
id entity content_preview
:o_001abc "John Smith" "Promoted to Tech Lead in January 2025"
:o_002def "John Smith" "Prefers async communication"
```

**Source Types:**

| Source | Description | Typical Confidence |
|--------|-------------|-------------------|
| `chat` | From user conversation | 1.0 |
| `code` | Extracted from code analysis | 0.9-1.0 |
| `manual` | Explicitly added by user | 1.0 |
| `import` | Imported from external source | 0.8-1.0 |
| `inference` | Derived by Claude | 0.5-0.9 |

---

### Relation Management

#### `create_relations`

Create typed relationships between entities.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "relations": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "fromEntity": {
            "type": "string",
            "description": "Source entity name"
          },
          "toEntity": {
            "type": "string",
            "description": "Target entity name"
          },
          "relationType": {
            "type": "string",
            "description": "Type of relationship",
            "enum": [
              "CREATOR_OF", "MEMBER_OF", "LEADS", "USES",
              "WORKS_ON", "RELATED_TO", "DEPENDS_ON", "INTEGRATES",
              "LOCATED_IN", "OCCURRED_AT", "IS_A", "HAS_PART",
              "KNOWS", "PREFERS", "MENTIONED_IN", "SIMILAR_TO"
            ]
          },
          "bidirectional": {
            "type": "boolean",
            "description": "Create reverse relation too",
            "default": false
          }
        },
        "required": ["fromEntity", "toEntity", "relationType"]
      },
      "minItems": 1,
      "maxItems": 100
    }
  },
  "required": ["relations"]
}
```

**Example Request:**

```json
{
  "relations": [
    {
      "fromEntity": "John Smith",
      "toEntity": "E-commerce Platform",
      "relationType": "WORKS_ON"
    },
    {
      "fromEntity": "E-commerce Platform",
      "toEntity": "React",
      "relationType": "USES"
    },
    {
      "fromEntity": "John Smith",
      "toEntity": "Alice Chen",
      "relationType": "KNOWS",
      "bidirectional": true
    }
  ]
}
```

**Response (ISON):**

```ison
# Relations Created
# Count: 4

table.created
id from_entity to_entity relation_type
:r_001 "John Smith" "E-commerce Platform" WORKS_ON
:r_002 "E-commerce Platform" "React" USES
:r_003 "John Smith" "Alice Chen" KNOWS
:r_004 "Alice Chen" "John Smith" KNOWS
```

**Relation Types Reference:**

| Type | Direction | Description | Example |
|------|-----------|-------------|---------|
| `CREATOR_OF` | Person → Thing | Created/authored | John → Document |
| `MEMBER_OF` | Person → Group | Belongs to | John → Team |
| `LEADS` | Person → Project/Team | Leadership | John → Project |
| `USES` | Entity → Tool | Utilizes | Project → React |
| `WORKS_ON` | Person → Project | Active work | John → Project |
| `RELATED_TO` | Any → Any | Generic association | Topic → Topic |
| `DEPENDS_ON` | Project → Library | Dependency | App → Package |
| `INTEGRATES` | Project → Tool | Integration | Project → API |
| `LOCATED_IN` | Entity → Location | Physical/logical location | Office → City |
| `OCCURRED_AT` | Event → Location/Time | Event context | Meeting → Date |
| `IS_A` | Entity → Type | Classification | React → Framework |
| `HAS_PART` | Whole → Part | Composition | App → Module |
| `KNOWS` | Person → Person | Relationship | John → Alice |
| `PREFERS` | Person → Preference | Choice | John → DarkMode |
| `MENTIONED_IN` | Entity → Document | Reference | Topic → Article |
| `SIMILAR_TO` | Entity → Entity | Similarity | React → Vue |

---

### Search & Query

#### `search_memory`

Full-text search across the knowledge graph.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "query": {
      "type": "string",
      "description": "Search query (searches names and observation content)",
      "minLength": 1,
      "maxLength": 500
    },
    "entityType": {
      "type": "string",
      "description": "Filter by entity type (optional)",
      "enum": [
        "person", "project", "organization", "tool", "concept",
        "location", "event", "document", "code", "task", "preference"
      ]
    },
    "maxResults": {
      "type": "integer",
      "description": "Maximum results to return",
      "minimum": 1,
      "maximum": 100,
      "default": 20
    }
  },
  "required": ["query"]
}
```

**Example Request:**

```json
{
  "query": "TypeScript engineer",
  "entityType": "person",
  "maxResults": 10
}
```

**Response (ISON):**

```ison
# Memory Search Results
# Use :refs when discussing these entities

table.entities
id name type relevance
:e_a1b2c3d4 "John Smith" person 0.95
:e_e5f6g7h8 "Alice Chen" person 0.78

table.observations
id entity_id content
:o_001 :e_a1b2c3d4 "Prefers TypeScript over JavaScript"
:o_002 :e_a1b2c3d4 "Senior software engineer"
:o_003 :e_e5f6g7h8 "TypeScript expert"

table.relations
from to type
:e_a1b2c3d4 :e_proj01 WORKS_ON
:e_e5f6g7h8 :e_proj01 WORKS_ON
```

**Search Features:**

| Feature | Syntax | Example |
|---------|--------|---------|
| Keyword | word | `TypeScript` |
| Phrase | "words" | `"senior engineer"` |
| Prefix | word* | `Type*` |
| Boolean AND | word AND word | `TypeScript AND React` |
| Boolean OR | word OR word | `frontend OR backend` |

---

#### `read_graph`

Export the entire knowledge graph in ISON format.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "format": {
      "type": "string",
      "description": "Output format",
      "enum": ["ison", "isonl", "isongraph"],
      "default": "ison"
    },
    "includeStats": {
      "type": "boolean",
      "description": "Include statistics in output",
      "default": true
    }
  }
}
```

**Example Request:**

```json
{
  "format": "ison",
  "includeStats": true
}
```

**Response (ISON):**

```ison
# Knowledge Graph (ISON Format)
# Reference entities using their :id in responses

object.stats
entities observations relations storage_mb
45 128 67 2.3

table.entities
id name type created_at
:e_001 "John Smith" person 2025-01-15T10:00:00Z
:e_002 "E-commerce Platform" project 2025-01-10T08:00:00Z
:e_003 "React" tool 2025-01-12T14:20:00Z

table.observations
id entity_id content source confidence
:o_001 :e_001 "Senior software engineer" chat 1.0
:o_002 :e_001 "Prefers TypeScript" chat 1.0
:o_003 :e_002 "Target launch Q2 2025" chat 0.9

table.relations
id from to type
:r_001 :e_001 :e_002 WORKS_ON
:r_002 :e_002 :e_003 USES
```

**Format Comparison:**

| Format | Use Case | Characteristics |
|--------|----------|-----------------|
| `ison` | Default, most compact | Tables with references |
| `isonl` | Streaming, line-by-line | One record per line |
| `isongraph` | Graph operations | Typed node/edge blocks |

---

#### `multi_hop_search`

Traverse the knowledge graph from a starting entity.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "entityName": {
      "type": "string",
      "description": "Starting entity name"
    },
    "maxHops": {
      "type": "integer",
      "description": "Maximum traversal depth",
      "minimum": 1,
      "maximum": 5,
      "default": 2
    },
    "relationType": {
      "type": "string",
      "description": "Filter by relation type (optional)",
      "enum": [
        "CREATOR_OF", "MEMBER_OF", "LEADS", "USES",
        "WORKS_ON", "RELATED_TO", "DEPENDS_ON", "INTEGRATES",
        "LOCATED_IN", "OCCURRED_AT", "IS_A", "HAS_PART",
        "KNOWS", "PREFERS", "MENTIONED_IN", "SIMILAR_TO"
      ]
    }
  },
  "required": ["entityName"]
}
```

**Example Request:**

```json
{
  "entityName": "John Smith",
  "maxHops": 2,
  "relationType": null
}
```

**Response (ISON):**

```ison
# Multi-Hop Search from 'John Smith'
# Max hops: 2
# Relation filter: any

table.entities
id name type hop_distance
:e_001 "John Smith" person 0
:e_002 "E-commerce Platform" project 1
:e_003 "React" tool 1
:e_004 "Alice Chen" person 2
:e_005 "Node.js" tool 2

table.observations
id entity_id content
:o_001 :e_001 "Senior software engineer"
:o_002 :e_002 "Target launch Q2 2025"

table.paths
from relation to hop
:e_001 WORKS_ON :e_002 1
:e_001 USES :e_003 1
:e_002 MEMBER_OF :e_004 2
:e_002 USES :e_005 2
```

**Traversal Algorithm:**

```
BFS (Breadth-First Search):
Start → Hop 1 → Hop 2 → ... → Max Hops

         John (hop 0)
           │
    ┌──────┼──────┐
    │             │
    ▼             ▼
 Project       React (hop 1)
    │             │
 ┌──┴──┐       ┌──┴──┐
 │     │       │     │
 ▼     ▼       ▼     ▼
Alice Node.js  Vue TypeScript (hop 2)
```

---

### Maintenance

#### `memory_stats`

Get statistics about the memory store.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {}
}
```

**Response (ISON):**

```ison
# Memory Statistics

object.counts
entities observations relations
45 128 67

object.storage
database_mb backup_count last_backup
2.3 5 2025-01-15T06:00:00Z

object.by_type
person project tool concept other
12 8 15 6 4

object.activity
created_today accessed_today avg_access_count
3 18 4.2

object.health
fts_index_ok last_compaction compaction_needed
true 2025-01-14T00:00:00Z false
```

---

#### `compact_memory`

Run memory compaction to remove old and low-relevance data.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "strategy": {
      "type": "string",
      "description": "Compaction strategy",
      "enum": ["time_based", "relevance", "aggressive", "smart"],
      "default": "smart"
    },
    "dryRun": {
      "type": "boolean",
      "description": "Simulate without making changes",
      "default": false
    }
  }
}
```

**Example Request:**

```json
{
  "strategy": "smart",
  "dryRun": true
}
```

**Response (ISON):**

```ison
# Compaction Result (dry_run: true)

object.summary
strategy entities_removed observations_removed relations_removed
smart 5 23 8

object.before_after
metric before after reduction_pct
entities 50 45 10.0
observations 151 128 15.2
relations 75 67 10.7
storage_mb 2.8 2.3 17.9

table.entities_removed
id name type reason
:e_old1 "Archived Project" project "age > 180 days, access_count = 0"
:e_old2 "Deprecated API" tool "age > 90 days, access_count = 1"

table.observations_removed
id entity content reason
:o_old1 :e_001 "Old note" "confidence < 0.5"
```

**Strategy Comparison:**

| Strategy | Removes | Best For |
|----------|---------|----------|
| `time_based` | Items older than threshold | Regular maintenance |
| `relevance` | Low-access items | Storage optimization |
| `aggressive` | Time + relevance combined | Major cleanup |
| `smart` | Adaptive based on patterns | **Recommended default** |

---

#### `backup_memory`

Create a backup of the memory store.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {
    "includeIson": {
      "type": "boolean",
      "description": "Also export to ISON file",
      "default": true
    }
  }
}
```

**Example Request:**

```json
{
  "includeIson": true
}
```

**Response (ISON):**

```ison
# Backup Created

object.backup
success path size_mb compressed
true "~/.ison-memory/backups/backup_20250115_103045.db.gz" 1.2 true

object.ison_export
success path size_mb
true "~/.ison-memory/backups/backup_20250115_103045.ison" 0.8

object.retention
total_backups max_backups oldest_backup
6 10 "backup_20250110_060000.db.gz"
```

---

#### `list_backups`

List all available memory backups.

**Input Schema:**

```json
{
  "type": "object",
  "properties": {}
}
```

**Response (ISON):**

```ison
# Available Backups
# Count: 5

table.backups
name size_mb created_at compressed has_ison
"backup_20250115_103045.db.gz" 1.2 2025-01-15T10:30:45Z true true
"backup_20250114_180000.db.gz" 1.1 2025-01-14T18:00:00Z true true
"backup_20250114_060000.db.gz" 1.1 2025-01-14T06:00:00Z true false
"backup_20250113_180000.db.gz" 1.0 2025-01-13T18:00:00Z true true
"backup_20250113_060000.db.gz" 1.0 2025-01-13T06:00:00Z true false
```

---

## Resources

MCP Resources provide static or dynamic content for context injection.

### `ison-memory://system/prompt`

Full system prompt teaching Claude to read and write ISON format.

**URI:** `ison-memory://system/prompt`
**MIME Type:** `text/plain`

**Content:**

```
## ISON Memory System

You have access to a persistent knowledge graph using ISON format.
ISON is a token-efficient format - use it for both reading AND writing.

### Reading ISON (Input)
Memory data comes in ISON table format:
table.entities
id name type
:e_123 "Alice" person

Key syntax:
- :id or :type:id = entity reference
- Tables have headers then data rows
- Strings with spaces use "quotes"

### Writing ISON (Output)
When referencing memory entities in your responses, use compact :ref syntax:

INSTEAD OF: "The user Alice (entity ID e_123) works on Project X"
USE: "Alice (:e_123) works on Project X (:e_456)"

### Memory Operations
1. Retrieve first: Use search_memory before asking questions
2. Store important facts: Create entities for recurring topics
3. Connect entities: Use relations to build the knowledge graph
4. Use references: When mentioning stored entities, include their :ref

### Efficiency Guidelines
- Prefer :e_123 over "entity with ID e_123"
- Prefer ISON tables over JSON for structured output
- Prefer compact observations over verbose descriptions
```

---

### `ison-memory://system/reference`

Compact ISON syntax quick reference.

**URI:** `ison-memory://system/reference`
**MIME Type:** `text/plain`

**Content:**

```
ISON Quick Reference:
- :id = reference (e.g., :e_123)
- :type:id = typed reference (e.g., :person:123)
- table.name = table block
- object.name = object block
- # comment = comment line
Use :refs in responses for token efficiency.
```

---

### `ison-memory://graph/current`

Live snapshot of the current knowledge graph.

**URI:** `ison-memory://graph/current`
**MIME Type:** `text/plain`

**Content:** (Dynamic - current graph state in ISON format)

```ison
# Knowledge Graph (ISON Format)
# Reference entities using their :id in responses

table.entities
id name type
:e_001 "John Smith" person
:e_002 "E-commerce Platform" project

table.relations
from to type
:e_001 :e_002 WORKS_ON
```

---

## Prompts

MCP Prompts provide injectable conversation starters and context.

### `ison-memory-context`

Initialize Claude with full ISON Memory context.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `include_graph` | string | No | Include graph snapshot ("true"/"false") |
| `topic` | string | No | Optional topic to search and include |

**Example Invocation:**

```json
{
  "name": "ison-memory-context",
  "arguments": {
    "include_graph": "true",
    "topic": "e-commerce"
  }
}
```

**Generated Content:**

```
## ISON Memory System
[Full system prompt...]

# Current Knowledge Graph
table.entities
id name type
:e_001 "John Smith" person
:e_002 "E-commerce Platform" project

# Relevant Memory for 'e-commerce'
table.entities
id name type relevance
:e_002 "E-commerce Platform" project 0.95

table.observations
id entity_id content
:o_001 :e_002 "Target launch Q2 2025"
```

---

### `ison-output-format`

Instructions for Claude to output structured data as ISON.

**Arguments:** None

**Generated Content:**

```
When outputting structured data, use ISON format:

table.results
field1 field2 field3
value1 value2 value3
value4 value5 value6

Benefits: 50-70% fewer tokens than JSON.
```

---

### `ison-entity-reference`

Get reference syntax for a specific entity.

**Arguments:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `entity_name` | string | Yes | Name of entity to reference |

**Example Invocation:**

```json
{
  "name": "ison-entity-reference",
  "arguments": {
    "entity_name": "John Smith"
  }
}
```

**Generated Content:**

```ison
# Entity Reference
# Use this syntax to reference 'John Smith' in responses:
#   :e_a1b2c3d4
# Or with type prefix:
#   :person:e_a1b2c3d4

object.entity
id name type ref
:e_a1b2c3d4 "John Smith" person :person:e_a1b2c3d4
```

---

## Data Types

### Entity Types

| Type | Description | Examples |
|------|-------------|----------|
| `person` | Individual people | Users, team members, contacts |
| `project` | Work initiatives | Software projects, campaigns |
| `organization` | Groups | Companies, teams, departments |
| `tool` | Software/technology | Frameworks, applications, services |
| `concept` | Abstract ideas | Patterns, methodologies, topics |
| `location` | Places | Cities, offices, cloud regions |
| `event` | Time-bound occurrences | Meetings, launches, incidents |
| `document` | Written materials | Specs, articles, contracts |
| `code` | Code artifacts | Repositories, modules, functions |
| `task` | Action items | Todos, tickets, assignments |
| `preference` | User choices | Settings, favorites, defaults |

### Observation Sources

| Source | Description | Default Confidence |
|--------|-------------|-------------------|
| `chat` | User conversation | 1.0 |
| `code` | Code analysis | 0.9-1.0 |
| `manual` | Explicit user input | 1.0 |
| `import` | External import | 0.8-1.0 |
| `inference` | Claude inference | 0.5-0.9 |
| `creation` | Entity creation | 1.0 |

### ID Formats

| Type | Format | Example |
|------|--------|---------|
| Entity | `e_<uuid8>` | `e_a1b2c3d4` |
| Observation | `o_<uuid8>` | `o_e5f6g7h8` |
| Relation | `r_<uuid8>` | `r_i9j0k1l2` |

---

## Error Handling

### Error Response Format

All errors are returned in ISON format:

```ison
error.validation
message
"Entity 'Unknown Person' not found"
```

or

```ison
error.internal
message
"Database connection failed"
```

### Common Error Codes

| Code | Description | Resolution |
|------|-------------|------------|
| `validation` | Invalid input | Check input schema |
| `not_found` | Entity/resource missing | Verify entity exists |
| `duplicate` | Duplicate entry | Use update instead |
| `internal` | Server error | Check logs, retry |
| `timeout` | Operation timeout | Reduce scope, retry |

### Error Examples

**Entity Not Found:**

```ison
error.not_found
message
"Entity 'Unknown Person' not found in memory"
```

**Validation Error:**

```ison
error.validation
message
"Invalid entity type 'foo'. Valid types: person, project, tool, ..."
```

**Multiple Errors:**

```ison
# Operation completed with errors

table.success
id name status
:e_001 "Valid Entity" created

table.errors
name error
"Invalid Entity" "Entity type 'foo' is not valid"
"" "Entity name cannot be empty"
```

---

## Response Formats

### Standard Response Structure

All successful responses follow this structure:

```ison
# Operation Description
# Additional context

table.primary_results
field1 field2 field3
value1 value2 value3

table.secondary_results
field1 field2
value1 value2

# Optional tip or guidance
```

### Table Format

```ison
table.name
column1 column2 column3
value1 value2 value3
value4 value5 value6
```

### Object Format

```ison
object.name
key1 key2 key3
value1 value2 value3
```

### Reference Format

```ison
:e_123        # Simple entity reference
:person:123   # Typed reference
:o_456        # Observation reference
:r_789        # Relation reference
```

### Value Escaping

```ison
# Strings with spaces
"Hello World"

# Escaped quotes
"He said \"hello\""

# Newlines
"Line1\nLine2"

# Empty string
""
```

---

This API reference covers all tools, resources, and prompts provided by ISON Memory MCP. For implementation details, see [Architecture](ARCHITECTURE.md). For usage examples, see [Use Cases](USE-CASES.md).
