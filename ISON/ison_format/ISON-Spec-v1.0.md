# ISON v1.0 Specification

**Interchange Simple Object Notation**

Version: 1.0  
Status: Draft  
Author: Mahesh Vaikri  
Date: November 2025

---

## Abstract

ISON (Interchange Simple Object Notation) is a minimal, human-readable data serialization format optimized for Large Language Model (LLM) comprehension. It serves any system that needs to exchange structured data with language models—databases, agents, APIs, RAG pipelines, and beyond. ISON prioritizes token efficiency, structural clarity, and relational expressiveness while remaining fully parseable by standard tooling.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Design Principles](#2-design-principles)
3. [Lexical Structure](#3-lexical-structure)
4. [Block Structure](#4-block-structure)
5. [Data Types](#5-data-types)
6. [Type Inference Rules](#6-type-inference-rules)
7. [Quoting and Escaping](#7-quoting-and-escaping)
8. [References](#8-references)
9. [Null and Empty Values](#9-null-and-empty-values)
10. [Comments](#10-comments)
11. [Nested Data Modeling](#11-nested-data-modeling)
12. [Grammar](#12-grammar)
13. [Examples](#13-examples)
14. [Comparison with Other Formats](#14-comparison-with-other-formats)
15. [Implementation Notes](#15-implementation-notes)

---

## 1. Introduction

### 1.1 Purpose

ISON is designed to serve as the primary data interchange format for:

- LLM prompt engineering (structured context in system prompts)
- RAG (Retrieval-Augmented Generation) pipelines
- Multi-agent AI systems
- Tool and function call results
- Database query outputs (relational, vector, graph, or hybrid)
- Knowledge base serialization
- Agentic workflows (task queues, execution logs, decision trees)
- Any system exchanging structured data with language models

### 1.2 Goals

- **Minimal syntax**: Reduce punctuation overhead that wastes tokens
- **LLM-optimized**: Maximize comprehension with minimal cognitive load
- **Token-efficient**: Fit more data in context windows than JSON allows
- **Unambiguous**: Fully parseable without context
- **Relational**: Native support for references and relationships
- **Human-readable**: Clear structure without visual noise
- **AI-native**: Become the standard format for LLM data interchange, as JSON is for web APIs

### 1.3 Non-Goals

- Replacing JSON for traditional web APIs (browser ↔ server communication)
- Replacing JSON where universal tooling support is critical
- Binary efficiency

> **Note**: Streaming/incremental parsing is now supported via ISONL (ISON Lines). See [ISONL Specification](./ISONL-Spec-v1.0.md).

### 1.4 Relationship to JSON

ISON is designed to be the preferred alternative to JSON for AI and LLM use cases. While JSON remains the standard for web APIs and general-purpose data interchange, its verbosity and structural overhead become liabilities when:

- **Token cost matters**: LLM context windows are finite and expensive
- **LLM comprehension matters**: Repeated keys and heavy punctuation add cognitive load
- **Data is tabular**: JSON's array-of-objects pattern repeats field names unnecessarily
- **Relationships exist**: JSON has no native reference mechanism

In these contexts, ISON offers:

| Concern | JSON | ISON |
|---------|------|------|
| Token efficiency | ~40-60% more tokens for tables | Baseline |
| Repeated field names | Every row | Once in header |
| Punctuation overhead | `{}[]"":,,` everywhere | Minimal |
| Relationship support | None (manual conventions) | Native (`:ID`) |
| Table representation | Verbose | Natural |

**ISON aims to be the default format for AI data workflows**, just as JSON became the default for web APIs. Systems should use ISON when data is destined for or produced by language models, and JSON when interfacing with traditional web infrastructure.

---

## 2. Design Principles

1. **Whitespace as delimiter**: Fields separated by spaces/tabs, not commas
2. **Quotes only when necessary**: Unquoted values are the default
3. **Tables over nesting**: Prefer normalized tables to deeply nested structures
4. **Explicit references**: Graph edges expressed via `:ID` notation
5. **Type inference**: Parsers infer types from value patterns

---

## 3. Lexical Structure

### 3.1 Character Set

ISON documents MUST be encoded in UTF-8.

### 3.2 Whitespace

- **Field separator**: One or more spaces (U+0020) or tabs (U+0009)
- **Line terminator**: LF (U+000A) or CRLF (U+000D U+000A)
- Leading and trailing whitespace on lines is ignored

### 3.3 Reserved Characters

| Character | Context | Meaning |
|-----------|---------|---------|
| `.` | Block header | Kind/name separator |
| `.` | Field name | Hierarchy separator (dot-path) |
| `:` | Value prefix | Reference indicator |
| `"` | Value wrapper | Quoted string delimiter |
| `#` | Line start | Comment indicator |
| `\` | Inside quotes | Escape character |

---

## 4. Block Structure

An ISON document consists of one or more **blocks**. Each block represents a logical data unit.

### 4.1 Block Syntax

```
kind.name
field1 field2 field3
value1 value2 value3
...
```

### 4.2 Block Kinds

| Kind | Description | Typical Use |
|------|-------------|-------------|
| `object` | Single record or small set | Configuration, metadata |
| `table` | Multi-row tabular data | Lists, collections |
| `meta` | Document metadata | Version info, schemas |
| `rel` | Relationship definitions | Graph edges (future) |

### 4.3 Block Components

1. **Header line**: `kind.name` (required)
2. **Field line**: Space-separated field names (required)
3. **Data lines**: Space-separated values (zero or more)

### 4.4 Multiple Blocks

Blocks are separated by one or more blank lines:

```
object.config
key value
timeout 30

table.users
id name
1 Alice
2 Bob
```

---

## 5. Data Types

ISON supports the following primitive types:

| Type | Description | Example |
|------|-------------|---------|
| `string` | Text value | `Alice`, `"New York"` |
| `integer` | Whole number | `42`, `-7` |
| `float` | Decimal number | `3.14`, `-0.5` |
| `boolean` | True/false | `true`, `false` |
| `null` | Absent value | `null` |
| `reference` | Pointer to another record | `:10`, `:user:101` |

---

## 6. Type Inference Rules

For **unquoted tokens**, parsers MUST apply these rules in order:

1. If token equals `true` → **boolean** (true)
2. If token equals `false` → **boolean** (false)
3. If token equals `null` → **null**
4. If token matches `^-?[0-9]+$` → **integer**
5. If token matches `^-?[0-9]+\.[0-9]+$` → **float**
6. If token starts with `:` → **reference**
7. Otherwise → **string**

### 6.1 Forcing String Type

To represent literal values that match other patterns (e.g., string `"true"`), use quotes:

```
table.flags
name value
enabled true      # boolean
label "true"      # string "true"
code "123"        # string "123"
count 123         # integer 123
```

---

## 7. Quoting and Escaping

### 7.1 When to Quote

Values MUST be quoted if they contain:

- Spaces
- Double quotes
- Characters that would trigger incorrect type inference

Values MAY be quoted for clarity even when not required.

### 7.2 Quoted String Syntax

Quoted strings begin and end with `"` (U+0022):

```
"Hello World"
"Line with \"quotes\" inside"
```

### 7.3 Escape Sequences

Inside quoted strings, the following escape sequences are recognized:

| Sequence | Meaning |
|----------|---------|
| `\"` | Double quote |
| `\\` | Backslash |
| `\n` | Newline (LF) |
| `\t` | Tab |
| `\r` | Carriage return |

### 7.4 Examples

```
table.messages
id sender text
1 Alice "Hello, how are you?"
2 Bob "I said \"hello\" back"
3 Eve "Line 1\nLine 2"
```

---

## 8. References

References express relationships between records, enabling graph semantics.

### 8.1 Basic Reference

A reference is an unquoted token starting with `:` followed by an identifier:

```
:10
:user_101
:abc-123
```

### 8.2 Namespaced Reference (Optional)

For disambiguation, references MAY include a type prefix:

```
:team:10
:user:101
```

Format: `:type:id`

### 8.3 Reference Example

```
object.team
id name
10 "AI Research"

table.users
id name team
101 Mahesh :10
102 Priya :10
```

Here, `:10` refers to the team with `id = 10`.

### 8.4 Multiple References

For multi-valued relationships, use multiple columns or normalize:

```
table.project_members
projectId userId role
1 :101 lead
1 :102 member
1 :103 member
```

---

## 9. Null and Empty Values

### 9.1 Null Values

The unquoted token `null` represents an absent value:

```
table.users
id name email
1 Alice alice@example.com
2 Bob null
```

### 9.2 Missing Trailing Values

If a row has fewer values than fields, missing values are `null`:

```
table.users
id name email phone
1 Alice alice@example.com
```

Result: `email = null`, `phone = null`

### 9.3 Empty Strings

An empty string is represented as `""`:

```
table.users
id name bio
1 Alice ""
2 Bob "Software engineer"
```

### 9.4 Comparison

| Representation | Meaning |
|----------------|---------|
| `null` | No value / absent |
| (missing) | No value / absent |
| `""` | Empty string |
| `" "` | String containing one space |

---

## 10. Comments

### 10.1 Syntax

Lines where the first non-whitespace character is `#` are comments:

```
# This is a comment
table.users
id name
# Another comment
1 Alice
2 Bob
```

### 10.2 Inline Comments

Inline comments (after values on same line) are NOT supported in v1.0:

```
# INVALID - do not use
1 Alice # this breaks parsing
```

### 10.3 Purpose

Comments are useful for:

- Documentation in configuration files
- Context hints in LLM prompts
- Metadata that shouldn't be parsed

---

## 11. Nested Data Modeling

### 11.1 Dot-Path Fields

Hierarchical data is expressed via dot-separated field names:

**JSON:**
```json
{
  "customer": {
    "name": "Mahesh",
    "address": {
      "city": "Dallas",
      "state": "TX"
    }
  }
}
```

**ISON:**
```
object.order
customer.name customer.address.city customer.address.state
Mahesh Dallas TX
```

### 11.2 Arrays of Objects

Arrays of structured objects SHOULD be normalized into separate table blocks with foreign keys.

**JSON:**
```json
{
  "order": {
    "id": 5001,
    "items": [
      {"sku": "A1", "qty": 2},
      {"sku": "B2", "qty": 1}
    ]
  }
}
```

**ISON:**
```
object.order
id total
5001 125.50

table.order_items
orderId sku qty
5001 A1 2
5001 B2 1
```

### 11.3 Scalar Arrays

For simple arrays of primitives, an optional inline syntax MAY be used:

```
object.config
name tags
myapp ["web","api","v2"]
```

This is parsed as a JSON array string. Implementations MAY parse it further.

**Recommendation**: Prefer normalized tables for clarity.

---

## 12. Grammar

### 12.1 ABNF Grammar

```abnf
document      = *block
block         = header LF fields LF *data-row
header        = kind "." name
kind          = identifier
name          = identifier
fields        = field *(WS field)
field         = identifier *("." identifier)
data-row      = value *(WS value) LF
value         = quoted-string / reference / literal
quoted-string = DQUOTE *char DQUOTE
reference     = ":" identifier *(":" identifier)
literal       = 1*non-ws-char
identifier    = (ALPHA / "_") *(ALPHA / DIGIT / "_" / "-")
char          = unescaped / escaped
escaped       = "\" (DQUOTE / "\" / "n" / "t" / "r")
unescaped     = any character except DQUOTE and "\"
WS            = 1*(SP / HTAB)
LF            = %x0A / %x0D.0A
DQUOTE        = %x22
SP            = %x20
HTAB          = %x09
ALPHA         = %x41-5A / %x61-7A
DIGIT         = %x30-39
non-ws-char   = any character except SP, HTAB, LF, CR
```

---

## 13. Examples

### 13.1 Simple Table

```
table.products
id name price inStock
1 Widget 9.99 true
2 Gadget 19.99 false
3 "Super Gizmo" 29.99 true
```

### 13.2 Object with Nested Fields

```
object.user_profile
id name email address.city address.country
101 Mahesh mahesh@example.com Dallas USA
```

### 13.3 Graph with References

```
# Departments
table.departments
id name budget
10 Engineering 500000
20 Marketing 300000

# Employees with department references
table.employees
id name department manager
1 Alice :10 null
2 Bob :10 :1
3 Carol :20 null
4 Dave :20 :3
```

### 13.4 Complete Document

```
# ISON Example: E-commerce Order System
# Version: 1.0

meta.document
version schema author
1.0 ecommerce "Mahesh Vaikri"

# Customer information
object.customer
id name email address.city address.state
1001 "John Smith" john@example.com "New York" NY

# Orders for customer
table.orders
id customerId date total status
5001 :1001 2025-01-15 125.50 completed
5002 :1001 2025-01-20 89.99 processing

# Line items for orders
table.order_items
orderId sku name qty unitPrice
5001 A1 Widget 2 25.00
5001 B2 Gadget 1 75.50
5002 C3 "Deluxe Widget" 3 29.99
```

---

## 14. Comparison with Other Formats

### 14.1 ISON vs JSON

| Aspect | JSON | ISON |
|--------|------|------|
| Delimiters | `,` `:` `{}` `[]` | Whitespace |
| Quotes | Required for strings | Only when needed |
| Nested objects | Native | Dot-paths or normalize |
| References | Not supported | Native (`:ID`) |
| Tables | Verbose (repeated keys) | Native |
| Token efficiency | Lower | Higher |
| Universal support | Excellent | Growing |

**When to use JSON:**
- Traditional web APIs (REST, GraphQL responses)
- Browser JavaScript consumption
- Existing toolchains that expect JSON
- Maximum interoperability with legacy systems

**When to use ISON:**
- LLM prompts and context
- RAG pipeline outputs
- Multi-agent communication
- Tool/function call results
- Any data flowing to or from language models
- Token-constrained environments

### 14.2 ISON vs CSV

| Aspect | CSV | ISON |
|--------|-----|------|
| Structure | Single table | Multiple blocks |
| Types | All strings | Inferred types |
| References | Not supported | Native |
| Hierarchy | Not supported | Dot-paths |
| Comments | Not standardized | Native |

### 14.3 ISON vs YAML

| Aspect | YAML | ISON |
|--------|------|------|
| Complexity | High | Low |
| Indentation sensitivity | Yes | No |
| Tables | Poor | Excellent |
| LLM readability | Medium | High |
| Parsing difficulty | High | Low |

---

## 15. Implementation Notes

### 15.1 Parser Requirements

A conforming ISON parser MUST:

1. Handle UTF-8 encoded documents
2. Apply type inference rules in specified order
3. Parse quoted strings with escape sequences
4. Recognize references starting with `:`
5. Treat missing trailing values as null
6. Ignore comment lines

### 15.2 Serializer Recommendations

When generating ISON:

1. Quote strings containing spaces or special characters
2. Use unquoted form for simple alphanumeric strings
3. Align columns for readability (optional)
4. Include header comments for context
5. Normalize arrays of objects into tables

### 15.3 Error Handling

Parsers SHOULD report:

- Mismatched quote pairs
- Invalid escape sequences
- Malformed block headers
- Field/value count mismatches (as warnings)

### 15.4 Extensions

Future versions may add:

- Schema definitions
- Binary encoding option
- Inline relationship syntax

> **Available Now**: Streaming support is available via [ISONL (ISON Lines)](./ISONL-Spec-v1.0.md) - a line-based format where each record is self-contained on a single line.

---

## Appendix A: Media Type

Proposed media type: `application/ison`

File extension: `.ison`

---

## Appendix B: Reference Implementations

Reference implementations are provided in:

- Python (`ison_parser.py`) - includes ISONL support
- JavaScript (`ison-parser.js`) - includes ISONL support
- TypeScript (planned)
- Rust (planned)

### ISONL Support

Both Python and JavaScript parsers include full ISONL support:

**Python:**
```python
from ison_parser import loads_isonl, dumps_isonl, ison_to_isonl, isonl_to_ison

# Parse ISONL
doc = loads_isonl("table.users|id name|1 Alice\ntable.users|id name|2 Bob")

# Serialize to ISONL
isonl = dumps_isonl(doc)

# Convert between formats
isonl = ison_to_isonl(ison_text)
ison = isonl_to_ison(isonl_text)
```

**JavaScript:**
```javascript
const ISON = require('./ison-parser.js');

// Parse ISONL
const doc = ISON.loadsISONL("table.users|id name|1 Alice");

// Serialize to ISONL
const isonl = ISON.dumpsISONL(doc);

// Convert between formats
const isonl = ISON.isonToISONL(isonText);
const ison = ISON.isonlToISON(isonlText);
```

Repository: (TBD)

---

## Appendix C: Acknowledgments

ISON was designed to address the growing need for an LLM-native data format—one that bridges human readability with machine efficiency. As language models become central to data workflows, the limitations of existing formats (JSON's verbosity, CSV's lack of types, YAML's complexity) become increasingly apparent. ISON aims to be the natural choice whenever structured data flows to or from an LLM.

Example implementations include the RudraDB relational-vector-graph database and the MAPLE multi-agent framework.

---

*End of ISON v1.0 Specification*
