# ISONL v1.0 Specification

**ISON Lines - Streaming Format for ISON**

Version: 1.0
Status: Draft
Author: Mahesh Vaikri
Date: November 2025

---

## Abstract

ISONL (ISON Lines) is a line-based streaming format derived from ISON. It encodes each ISON block as a single line, enabling incremental parsing, streaming workflows, and efficient append-only storage. ISONL maintains ISON's token efficiency while adding support for streaming use cases critical to LLM applications.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Design Principles](#2-design-principles)
3. [Format Specification](#3-format-specification)
4. [Data Types](#4-data-types)
5. [Parsing Rules](#5-parsing-rules)
6. [Conversion](#6-conversion)
7. [Grammar](#7-grammar)
8. [Examples](#8-examples)
9. [Comparison with JSONL](#9-comparison-with-jsonl)
10. [Implementation Notes](#10-implementation-notes)

---

## 1. Introduction

### 1.1 Purpose

ISONL is designed for scenarios where:

- **Streaming data**: Records arrive incrementally and must be processed line-by-line
- **Append-only logs**: New records are appended without rewriting the file
- **Fine-tuning datasets**: Training data stored as individual examples
- **Event streams**: Real-time data pipelines processing one event at a time
- **Large datasets**: Files too large to parse entirely into memory

### 1.2 Relationship to ISON

ISONL is to ISON what JSONL is to JSON:

| Format | Structure | Use Case |
|--------|-----------|----------|
| ISON | Multi-line blocks | Documents, configurations |
| ISONL | Single-line records | Streams, datasets, logs |

ISONL preserves all ISON semantics (types, references, field names) while enabling line-by-line processing.

### 1.3 Goals

- **Streaming**: Process records without loading entire document
- **Append-friendly**: Add new records without modifying existing data
- **Token-efficient**: Maintain ISON's token advantages over JSON
- **Interoperable**: Easy conversion to/from standard ISON

---

## 2. Design Principles

1. **One record per line**: Each line is self-contained and independently parseable
2. **Pipe-delimited sections**: Clear separation between header, fields, and values
3. **ISON value semantics**: Same type inference and escaping rules as ISON
4. **No cross-line dependencies**: Each line can be processed in isolation

---

## 3. Format Specification

### 3.1 Line Structure

Each ISONL line consists of three pipe-separated sections:

```
kind.name|field1 field2 field3|value1 value2 value3
```

| Section | Description | Required |
|---------|-------------|----------|
| Header | Block kind and name (`kind.name`) | Yes |
| Fields | Space-separated field names | Yes |
| Values | Space-separated values | Yes |

### 3.2 Section Separator

The pipe character `|` (U+007C) separates sections. Each line MUST contain exactly two pipe characters.

### 3.3 Field and Value Separators

Within the fields and values sections, items are separated by one or more spaces (U+0020) or tabs (U+0009), following ISON conventions.

### 3.4 Line Terminator

Lines are terminated by LF (U+000A) or CRLF (U+000D U+000A).

### 3.5 Empty Lines and Comments

- Empty lines are ignored
- Lines starting with `#` are comments and ignored

```
# This is a comment
table.users|id name|1 Alice

# Another comment
table.users|id name|2 Bob
```

---

## 4. Data Types

ISONL uses the same type system as ISON:

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text value | `Alice`, `"New York"` |
| `integer` | Whole number | `42`, `-7` |
| `float` | Decimal number | `3.14`, `-0.5` |
| `boolean` | True/false | `true`, `false` |
| `null` | Absent value | `null` |
| `reference` | Pointer to another record | `:10`, `:user:101` |

### 4.1 Type Inference

Same rules as ISON apply:

1. `true` / `false` → boolean
2. `null` → null
3. Integer pattern → integer
4. Float pattern → float
5. Starts with `:` → reference
6. Otherwise → string

### 4.2 Quoting Rules

Values MUST be quoted if they contain:

- Spaces
- Pipe characters (`|`)
- Double quotes (escaped as `\"`)

```
table.messages|id text|1 "Hello, World!"
table.data|id value|1 "Contains | pipe"
table.quotes|id text|1 "He said \"hello\""
```

---

## 5. Parsing Rules

### 5.1 Basic Parsing Algorithm

```
1. Read line
2. Skip if empty or starts with #
3. Split by '|' into exactly 3 parts
4. Parse header (kind.name)
5. Parse fields (space-separated identifiers)
6. Parse values (space-separated, respecting quotes)
7. Zip fields and values into record
8. Emit record
```

### 5.2 Field/Value Count Mismatch

If fewer values than fields:
- Missing values are `null`

If more values than fields:
- Extra values are ignored (with warning)

### 5.3 Escape Sequences

Same as ISON:

| Sequence | Meaning |
|----------|---------|
| `\"` | Double quote |
| `\\` | Backslash |
| `\n` | Newline |
| `\t` | Tab |
| `\r` | Carriage return |
| `\|` | Literal pipe (inside quotes) |

---

## 6. Conversion

### 6.1 ISON to ISONL

Each ISON block becomes one or more ISONL lines:

**ISON:**
```
table.users
id name email
1 Alice alice@example.com
2 Bob bob@example.com
```

**ISONL:**
```
table.users|id name email|1 Alice alice@example.com
table.users|id name email|2 Bob bob@example.com
```

### 6.2 ISONL to ISON

Lines with the same header can be grouped into a single ISON block:

**ISONL:**
```
table.users|id name|1 Alice
table.users|id name|2 Bob
object.config|timeout debug|30 true
```

**ISON:**
```
table.users
id name
1 Alice
2 Bob

object.config
timeout debug
30 true
```

### 6.3 Preserving Field Order

When converting to ISON, field order from the first encountered line of each block type is used. Subsequent lines with different field orders are reordered to match.

---

## 7. Grammar

### 7.1 ABNF Grammar

```abnf
document      = *line
line          = (record / comment / empty-line) LF
record        = header "|" fields "|" values
header        = kind "." name
kind          = identifier
name          = identifier
fields        = field *(WS field)
field         = identifier *("." identifier)
values        = value *(WS value)
value         = quoted-string / reference / literal
quoted-string = DQUOTE *qchar DQUOTE
qchar         = unescaped / escaped
escaped       = "\" (DQUOTE / "\" / "n" / "t" / "r" / "|")
unescaped     = any character except DQUOTE, "\", and "|"
reference     = ":" identifier *(":" identifier)
literal       = 1*non-delim-char
identifier    = (ALPHA / "_") *(ALPHA / DIGIT / "_" / "-")
comment       = "#" *any-char
empty-line    = *WS
WS            = 1*(SP / HTAB)
LF            = %x0A / %x0D.0A
DQUOTE        = %x22
SP            = %x20
HTAB          = %x09
ALPHA         = %x41-5A / %x61-7A
DIGIT         = %x30-39
non-delim-char = any character except SP, HTAB, LF, CR, "|"
```

---

## 8. Examples

### 8.1 Simple Records

```
table.users|id name email|1 Alice alice@example.com
table.users|id name email|2 Bob bob@example.com
table.users|id name email|3 "Charlie Brown" charlie@example.com
```

### 8.2 Mixed Block Types

```
object.config|timeout debug|30 true
table.users|id name|1 Alice
table.users|id name|2 Bob
table.orders|id user_id total|101 :1 99.99
table.orders|id user_id total|102 :2 149.50
```

### 8.3 Fine-Tuning Dataset

```
table.examples|instruction input output|"Summarize this text" "Long article text..." "Brief summary"
table.examples|instruction input output|"Translate to Spanish" "Hello, world" "Hola, mundo"
table.examples|instruction input output|"Extract entities" "Apple announced..." "[Apple, Tim Cook]"
```

### 8.4 Preference Learning (DPO/RLHF)

```
table.preferences|prompt chosen rejected|"Explain AI" "Detailed answer..." "Vague response..."
table.preferences|prompt chosen rejected|"Write code" "Clean Python..." "Messy code..."
```

### 8.5 Event Stream

```
table.events|timestamp type user_id data|2025-01-15T10:30:00Z click :1 "button=submit"
table.events|timestamp type user_id data|2025-01-15T10:30:05Z pageview :1 "/dashboard"
table.events|timestamp type user_id data|2025-01-15T10:30:10Z click :2 "button=login"
```

### 8.6 Log Entries

```
table.logs|timestamp level service message|10:15:32 ERROR api "Connection timeout to database"
table.logs|timestamp level service message|10:15:33 WARN db "Pool exhausted, creating new connection"
table.logs|timestamp level service message|10:15:34 INFO api "Retry successful"
```

### 8.7 With References

```
table.customers|id name|C1 "Acme Corp"
table.customers|id name|C2 "TechStart Inc"
table.orders|id customer total|O1 :C1 5000.00
table.orders|id customer total|O2 :C1 3500.00
table.orders|id customer total|O3 :C2 1200.00
```

---

## 9. Comparison with JSONL

### 9.1 Format Comparison

**JSONL:**
```
{"id": 1, "name": "Alice", "email": "alice@example.com"}
{"id": 2, "name": "Bob", "email": "bob@example.com"}
{"id": 3, "name": "Charlie", "email": "charlie@example.com"}
```

**ISONL:**
```
table.users|id name email|1 Alice alice@example.com
table.users|id name email|2 Bob bob@example.com
table.users|id name email|3 Charlie charlie@example.com
```

### 9.2 Token Efficiency

| Records | JSONL Tokens | ISONL Tokens | Savings |
|---------|--------------|--------------|---------|
| 3 | ~60 | ~40 | 33% |
| 100 | ~2000 | ~1200 | 40% |
| 1000 | ~20000 | ~11000 | 45% |

Token savings increase with record count due to:
- No repeated `{}` braces per record
- No repeated `""` around keys
- No `:` and `,` delimiters

### 9.3 Feature Comparison

| Feature | JSONL | ISONL |
|---------|-------|-------|
| Self-describing | Yes | Yes (header per line) |
| Type information | Inferred | Explicit inference rules |
| References | No | Yes (`:ID` syntax) |
| Block types | No | Yes (`table.`, `object.`) |
| Streaming | Yes | Yes |
| Token efficiency | Lower | Higher |

---

## 10. Implementation Notes

### 10.1 Parser Requirements

A conforming ISONL parser MUST:

1. Process input line-by-line
2. Handle UTF-8 encoding
3. Split lines by `|` into exactly 3 sections
4. Apply ISON type inference rules
5. Handle quoted strings with escape sequences
6. Treat missing values as null

### 10.2 Streaming Implementation

```python
def parse_isonl_stream(file_handle):
    for line in file_handle:
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        yield parse_isonl_line(line)
```

### 10.3 Memory Efficiency

Unlike ISON (which may require loading entire document), ISONL allows constant-memory processing regardless of file size.

### 10.4 Error Handling

Parsers SHOULD report:

- Lines without exactly 2 pipe characters
- Malformed headers
- Mismatched quotes
- Invalid escape sequences

Parsers MAY continue processing after errors (skip invalid lines).

### 10.5 Serializer Recommendations

When generating ISONL:

1. Include header on every line (even for same block type)
2. Quote values containing spaces, pipes, or quotes
3. Maintain consistent field order within block types
4. Use comments sparingly (prefer separate metadata)

---

## Appendix A: Media Type

Proposed media type: `application/isonl`

File extension: `.isonl`

---

## Appendix B: Use Cases

### B.1 LLM Fine-Tuning

ISONL is ideal for fine-tuning datasets:

```
table.sft|instruction response|"Explain quantum computing" "Quantum computing uses..."
table.sft|instruction response|"Write a haiku about spring" "Cherry blossoms fall..."
```

### B.2 RAG Chunk Storage

Store document chunks for retrieval:

```
table.chunks|id doc_id content embedding_ref|C1 :D1 "First paragraph..." :E1
table.chunks|id doc_id content embedding_ref|C2 :D1 "Second paragraph..." :E2
```

### B.3 Agent Message Logs

Log multi-agent communications:

```
table.messages|timestamp from to content|10:00:00 planner coder "Implement login API"
table.messages|timestamp from to content|10:05:00 coder planner "Need clarification on auth method"
```

### B.4 Incremental Data Export

Append new records without rewriting:

```bash
# Initial export
ison2isonl data.ison >> stream.isonl

# Later updates (append only)
ison2isonl new_data.ison >> stream.isonl
```

---

*End of ISONL v1.0 Specification*
