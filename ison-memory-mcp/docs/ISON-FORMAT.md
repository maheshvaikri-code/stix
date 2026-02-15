# ISON Format Specification

Complete specification for ISON (Indexed Structured Object Notation) format used by ISON Memory MCP.

## Table of Contents

- [Overview](#overview)
- [Design Goals](#design-goals)
- [Syntax Reference](#syntax-reference)
- [Data Types](#data-types)
- [Block Types](#block-types)
- [Reference System](#reference-system)
- [Token Efficiency](#token-efficiency)
- [Comparison with JSON](#comparison-with-json)
- [ISONGraph Extensions](#isongraph-extensions)
- [Best Practices](#best-practices)

---

## Overview

ISON (Indexed Structured Object Notation) is a token-efficient data serialization format specifically designed for Large Language Model (LLM) contexts. It achieves **50-72% token savings** compared to JSON while maintaining full semantic fidelity.

### Key Characteristics

| Feature | Description |
|---------|-------------|
| **Token Efficient** | Minimizes tokens through compact syntax |
| **Human Readable** | Clear table-based structure |
| **Reference System** | Compact entity references with `:id` syntax |
| **Type-Safe** | Optional type hints in references |
| **Streaming** | ISONL variant for line-by-line processing |

### Format Variants

| Variant | Use Case | Characteristics |
|---------|----------|-----------------|
| **ISON** | Default format | Tables, objects, references |
| **ISONL** | Streaming | One record per line |
| **ISONGraph** | Graph data | Typed nodes and edges |

---

## Design Goals

### 1. Minimize Token Count

Every syntax element is designed for minimal tokenization:

```
JSON tokens: "entities" → 3 tokens (", entities, ")
ISON tokens: table.entities → 2 tokens (table, .entities)
```

### 2. Maximize Information Density

Tables pack data efficiently:

```ison
# 5 entities in ~15 tokens
table.entities
id name type
:e1 Alice person
:e2 Bob person
:e3 Project project
:e4 React tool
:e5 Python tool
```

### 3. Support Reference Reuse

References eliminate redundancy:

```
# Instead of repeating "entity with ID e_123" (6 tokens)
# Use :e_123 (2 tokens)
# Savings multiply with each reference
```

### 4. Maintain Readability

Despite compactness, ISON remains human-readable:

```ison
# Clear structure
table.entities
id name type
:e_001 "John Smith" person

# Readable relations
table.relations
from to type
:e_001 :e_002 WORKS_ON
```

---

## Syntax Reference

### Basic Structure

```ison
# Comment - ignored by parser
block_type.block_name
header1 header2 header3
value1 value2 value3
value4 value5 value6

# Blank line separates blocks
block_type.another_block
header1 header2
value1 value2
```

### Lexical Elements

| Element | Syntax | Description |
|---------|--------|-------------|
| Comment | `# text` | Line comment, ignored |
| Block header | `type.name` | Starts a block |
| Column headers | `col1 col2` | Space-separated names |
| Values | `val1 val2` | Space-separated values |
| Blank line | `` | Block separator |

### Value Syntax

```ison
# Unquoted string (no spaces)
simple_word

# Quoted string (with spaces or special chars)
"Hello World"
"Contains \"quotes\""
"Has\nnewline"

# Numbers
42
-17
3.14159
-0.5

# Booleans
true
false

# Null
null

# Reference
:e_123
:person:e_123
```

---

## Data Types

### Strings

```ison
# Simple string (no spaces, no special chars)
hello
world
user123

# Quoted string
"Hello World"
"John's \"nickname\""
"Line 1\nLine 2"
"Path: C:\\Users\\Name"

# Empty string
""
```

**Escape Sequences:**

| Sequence | Meaning |
|----------|---------|
| `\\` | Backslash |
| `\"` | Double quote |
| `\n` | Newline |
| `\t` | Tab |
| `\r` | Carriage return |

### Numbers

```ison
# Integers
0
42
-17
1000000

# Floating point
3.14
-0.5
1.0e10
2.5e-3
```

### Booleans

```ison
# Boolean true
true

# Boolean false
false

# Note: Case-sensitive, only lowercase valid
```

### Null

```ison
# Null value
null

# Note: Case-sensitive, only lowercase valid
```

### References

```ison
# Simple reference (just ID)
:e_123
:o_456
:r_789

# Typed reference (type:id)
:person:e_123
:project:proj_001
:tool:react

# Reference in context
"User :e_123 works on :project:p_001"
```

---

## Block Types

### Table Block

Tables represent lists of similar items with consistent columns.

```ison
table.entities
id name type created_at
:e_001 "John Smith" person 2025-01-15T10:00:00Z
:e_002 "Alice Chen" person 2025-01-14T09:00:00Z
:e_003 "E-commerce" project 2025-01-10T08:00:00Z
```

**Structure:**
```
table.{name}
{header1} {header2} {header3} ...
{value1} {value2} {value3} ...
{value1} {value2} {value3} ...
```

**Use Cases:**
- Entity lists
- Search results
- Observation collections
- Relation lists

### Object Block

Objects represent single items with named fields.

```ison
object.config
database_path max_entities log_level
"~/.ison-memory/memory.db" 50000 info

object.stats
entities observations relations storage_mb
45 128 67 2.3
```

**Structure:**
```
object.{name}
{key1} {key2} {key3} ...
{value1} {value2} {value3} ...
```

**Use Cases:**
- Configuration
- Statistics
- Single entity details
- Metadata

### Meta Block

Meta blocks provide document-level metadata.

```ison
meta.document
version timestamp author
1.0 2025-01-15T10:00:00Z "ISON Memory MCP"

# Rest of document follows
table.entities
...
```

### Comment Block

Comments provide context without affecting data.

```ison
# This is a comment
# It can span multiple lines
# And provide context

# Memory Search Results
# Query: "TypeScript engineer"
# Found: 3 entities

table.entities
id name type
:e_001 "John Smith" person
```

---

## Reference System

### Reference Types

| Syntax | Type | Example | Use Case |
|--------|------|---------|----------|
| `:id` | Simple | `:e_123` | Most common |
| `:type:id` | Typed | `:person:e_123` | Type disambiguation |
| `:prefix_id` | Prefixed | `:e_abc123` | Standard format |

### Reference Patterns

```ison
# Entity references (e_ prefix)
:e_abc123
:e_001
:entity:e_abc123

# Observation references (o_ prefix)
:o_xyz789
:o_001
:observation:o_xyz789

# Relation references (r_ prefix)
:r_def456
:r_001
:relation:r_def456

# Custom type references
:person:john_smith
:project:ecommerce_v2
:tool:react_18
```

### In-Text References

References can be used within string values:

```ison
# In observation content
table.observations
id entity_id content
:o_001 :e_001 "Works with :e_002 on :e_003"

# In descriptions
table.notes
id content
:n_001 "Meeting between :e_001 and :e_002 about :e_003"
```

### Reference Resolution

```
Reference: :e_001
    ↓
Lookup in entities table where id = "e_001"
    ↓
Returns: {id: "e_001", name: "John Smith", type: "person"}
```

---

## Token Efficiency

### Token Comparison

| Content | JSON Tokens | ISON Tokens | Savings |
|---------|-------------|-------------|---------|
| Empty object | `{}` = 2 | - | N/A |
| Simple key-value | `{"name":"John"}` = 7 | `name\nJohn` = 2 | 71% |
| Array of 3 items | `["a","b","c"]` = 9 | `a b c` = 3 | 67% |
| 5 entities | ~45 | ~15 | 67% |
| 10 entities | ~90 | ~30 | 67% |
| 50 entities + relations | ~500 | ~150 | 70% |

### Token Savings Sources

1. **No Structural Punctuation**
   ```
   JSON: { } [ ] , : " "
   ISON: Minimal - just spaces and newlines
   ```

2. **Table Headers vs Repeated Keys**
   ```json
   // JSON: "name" repeated 3 times
   [{"name": "A"}, {"name": "B"}, {"name": "C"}]
   ```
   ```ison
   # ISON: "name" appears once
   table.items
   name
   A
   B
   C
   ```

3. **Compact References**
   ```
   JSON: "entity_id": "e_123"  (~8 tokens)
   ISON: :e_123                (~2 tokens)
   ```

### Real-World Example

**JSON (87 tokens):**
```json
{
  "entities": [
    {
      "id": "e_abc123",
      "name": "John Smith",
      "type": "person",
      "observations": [
        "Senior software engineer",
        "Prefers TypeScript"
      ]
    },
    {
      "id": "e_def456",
      "name": "E-commerce Platform",
      "type": "project"
    }
  ],
  "relations": [
    {
      "from": "e_abc123",
      "to": "e_def456",
      "type": "WORKS_ON"
    }
  ]
}
```

**ISON (32 tokens - 63% savings):**
```ison
table.entities
id name type
:e_abc123 "John Smith" person
:e_def456 "E-commerce Platform" project

table.observations
entity_id content
:e_abc123 "Senior software engineer"
:e_abc123 "Prefers TypeScript"

table.relations
from to type
:e_abc123 :e_def456 WORKS_ON
```

---

## Comparison with JSON

### Structural Differences

| Aspect | JSON | ISON |
|--------|------|------|
| Delimiters | `{}[],:""` | Whitespace/newlines |
| Key repetition | Every object | Header row only |
| Nesting | Unlimited | Flat tables |
| References | Inline values | `:ref` syntax |
| Comments | Not supported | `#` comments |

### When to Use Each

| Use Case | Recommended Format |
|----------|-------------------|
| API responses | JSON (standard) |
| LLM context | ISON (efficient) |
| Configuration | TOML/YAML (human-friendly) |
| Streaming data | ISONL (line-oriented) |
| Graph data | ISONGraph (semantic) |

### Conversion Examples

**JSON Object → ISON Object:**
```json
{"name": "John", "age": 30, "active": true}
```
```ison
object.person
name age active
John 30 true
```

**JSON Array → ISON Table:**
```json
[
  {"id": 1, "name": "A"},
  {"id": 2, "name": "B"}
]
```
```ison
table.items
id name
1 A
2 B
```

**JSON Nested → ISON Flat:**
```json
{
  "user": {"name": "John"},
  "projects": [{"id": 1}]
}
```
```ison
object.user
name
John

table.projects
id
1
```

---

## ISONGraph Extensions

ISONGraph extends ISON with graph-specific semantics.

### Node Blocks

```ison
# Typed node declarations
nodes.person
id name role
:person:001 "John Smith" engineer
:person:002 "Alice Chen" designer

nodes.project
id name status
:project:001 "E-commerce" active
:project:002 "Mobile App" planning
```

### Edge Blocks

```ison
# Typed edge declarations
edges.WORKS_ON
from to since
:person:001 :project:001 2024-01-15
:person:002 :project:001 2024-03-01

edges.MANAGES
from to
:person:001 :person:002
```

### Path Representation

```ison
# Path from A to B
path.route
step from edge to
1 :person:001 WORKS_ON :project:001
2 :project:001 USES :tool:001
3 :tool:001 SIMILAR_TO :tool:002
```

### Graph Metadata

```ison
meta.graph
version nodes edges directed
2.0 45 67 true

nodes.person
...

edges.WORKS_ON
...
```

---

## Best Practices

### 1. Use Consistent ID Formats

```ison
# Good - consistent prefix format
:e_abc123
:o_def456
:r_ghi789

# Avoid - inconsistent formats
:abc123
:entity_123
:E_123
```

### 2. Quote Strings with Spaces

```ison
# Good
"John Smith"
"E-commerce Platform"

# Bad - will parse incorrectly
John Smith
E-commerce Platform
```

### 3. Use Meaningful Table Names

```ison
# Good - clear purpose
table.entities
table.observations
table.search_results

# Avoid - vague names
table.data
table.items
table.list
```

### 4. Order Columns Logically

```ison
# Good - ID first, then name, then metadata
table.entities
id name type created_at access_count

# Less ideal - random order
table.entities
created_at id access_count name type
```

### 5. Add Contextual Comments

```ison
# Search Results for "TypeScript engineer"
# Found: 3 entities, 5 observations
# Relevance threshold: 0.5

table.entities
id name type relevance
:e_001 "John Smith" person 0.95
```

### 6. Keep Observations Atomic

```ison
# Good - one fact per row
table.observations
entity_id content
:e_001 "Senior software engineer"
:e_001 "Prefers TypeScript"
:e_001 "Works remotely"

# Avoid - multiple facts combined
table.observations
entity_id content
:e_001 "Senior software engineer who prefers TypeScript and works remotely"
```

### 7. Use References in Prose

```ison
# Good - compact references
"John (:e_001) works on E-commerce (:e_002) using React (:e_003)"

# Verbose - wastes tokens
"John (entity ID e_001) works on E-commerce (entity ID e_002) using React (entity ID e_003)"
```

---

## Parser Implementation Notes

### Tokenization Rules

1. Split on whitespace (space, tab)
2. Respect quoted strings
3. Handle escape sequences in quotes
4. Recognize block headers (`type.name`)
5. Identify references (`:prefix`)

### Block Detection

```
Line starts with "table." → Table block
Line starts with "object." → Object block
Line starts with "nodes." → Node block (ISONGraph)
Line starts with "edges." → Edge block (ISONGraph)
Line starts with "meta." → Meta block
Line starts with "#" → Comment
Empty line → Block boundary
```

### Value Parsing Priority

1. Check for `null` → null value
2. Check for `true`/`false` → boolean
3. Check for `:` prefix → reference
4. Check for `"` → quoted string
5. Try numeric parse → integer/float
6. Default → unquoted string

---

This specification covers the complete ISON format used by ISON Memory MCP. For implementation details, see [Architecture](ARCHITECTURE.md). For API usage, see [API Reference](API-REFERENCE.md).
