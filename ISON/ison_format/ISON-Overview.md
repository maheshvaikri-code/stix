# ISON: Interchange Simple Object Notation

### The LLM-Native Data Format

---

## What is ISON?

ISON (Interchange Simple Object Notation) is a minimal, token-efficient data serialization format designed specifically for Large Language Model (LLM) workflows. It serves as the preferred alternative to JSON wherever structured data flows to or from language models.

```
table.users
id name email active
101 Mahesh mahesh@example.com true
102 "Priya Sharma" priya@example.com true
103 Ravi ravi@example.com false
```

**No braces. No brackets. No repeated field names. Just data.**

---

## Why ISON?

### The Problem with JSON for LLMs

JSON was designed for web APIs in 2001. It's verbose, repetitive, and wastes precious context window tokens:

```json
{
  "users": [
    {"id": 101, "name": "Mahesh", "email": "mahesh@example.com", "active": true},
    {"id": 102, "name": "Priya Sharma", "email": "priya@example.com", "active": true},
    {"id": 103, "name": "Ravi", "email": "ravi@example.com", "active": false}
  ]
}
```

**Problems:**
- Field names repeat for every row (`"id"`, `"name"`, `"email"`, `"active"` × 3)
- Punctuation overhead: `{}[]"":,,` everywhere
- ~280 tokens for 3 simple rows

### The ISON Solution

```
table.users
id name email active
101 Mahesh mahesh@example.com true
102 "Priya Sharma" priya@example.com true
103 Ravi ravi@example.com false
```

**Benefits:**
- Field names appear once (in header)
- Minimal punctuation
- ~140 tokens for the same data
- **30-70% fewer tokens = more data in context**

---

## Quick Comparison

| Aspect | JSON | ISON |
|--------|------|------|
| Field name repetition | Every row | Once in header |
| Punctuation | `{}[]"":,,` | Minimal |
| Table support | Verbose | Native |
| References/relationships | None | Native (`:ID`) |
| Nested fields | Deep nesting | Dot-paths |
| Token efficiency | Baseline | 30-60% better |
| LLM comprehension | Parse brackets mentally | Scan table visually |

---

## Core Syntax

### 1. Blocks

Every ISON document consists of blocks:

```
kind.name
field1 field2 field3
value1 value2 value3
```

**Block kinds:**
- `object` — Single record
- `table` — Multiple rows

### 2. Tables

```
table.products
id name price in_stock
1 Widget 29.99 true
2 Gadget 49.99 false
3 "Super Gizmo" 99.99 true
```

### 3. Objects

```
object.config
timeout debug max_retries
30 true 3
```

### 4. References

Link records with `:ID` notation:

```
table.teams
id name
10 "AI Research"

table.users
id name team
101 Mahesh :10
102 Priya :10
```

`:10` is a reference to the team with `id = 10`.

### 5. Dot-Path Fields (Nested Data)

Flatten hierarchies without deep nesting:

```
object.order
id customer.name customer.city total
5001 Mahesh Dallas 125.50
```

Equivalent JSON:
```json
{
  "id": 5001,
  "customer": {"name": "Mahesh", "city": "Dallas"},
  "total": 125.50
}
```

### 6. Type Inference

Unquoted values are automatically typed:

| Value | Type |
|-------|------|
| `true` / `false` | Boolean |
| `null` | Null |
| `42`, `-7` | Integer |
| `3.14` | Float |
| `:10` | Reference |
| `Alice` | String |
| `"New York"` | String (quoted for spaces) |

### 7. Comments

```
# This is a comment
table.users
id name
1 Alice  # Inline comments NOT supported
2 Bob
```

---

## Use Cases

ISON is designed for **any system exchanging structured data with LLMs**:

| Use Case | Example |
|----------|---------|
| **LLM Prompts** | Structured context in system prompts |
| **RAG Pipelines** | Retrieved chunks with metadata |
| **Multi-Agent Systems** | Agent state and message exchange |
| **Tool Results** | Search results, API responses, query outputs |
| **Database Outputs** | Relational, vector, graph, or hybrid queries |
| **Knowledge Bases** | Ontologies, taxonomies, domain knowledge |
| **Agentic Workflows** | Task queues, execution logs, decision trees |
| **Multimodal AI** | Object detection, transcription, OCR results |

---

## LLM Compatibility

### Zero-Shot Understanding

LLMs understand ISON **natively** because it looks like patterns they've seen billions of times:

- Markdown tables
- CSV/TSV files
- SQL query results
- Configuration files

**No special training required.**

### Test It Yourself

Give any LLM this:

```
table.employees
id name department manager
101 Alice Engineering null
102 Bob Engineering :101
103 Carol Sales null
```

Ask: *"Who manages Bob?"*

The LLM will correctly answer **Alice** without any explanation of the format.

### Generation Reliability

LLMs generate valid ISON more reliably than JSON because:

- No braces to match
- No commas to forget
- Quotes only when needed
- Whitespace-delimited (hard to get wrong)

---

## Complete Example

```
# E-commerce Order System

# Customer
object.customer
id name email tier
C-1001 "Sarah Chen" sarah@example.com enterprise

# Orders
table.orders
id customer date total status
5001 :C-1001 2025-01-15 234.50 shipped
5002 :C-1001 2025-01-18 89.99 processing

# Order Items
table.order_items
order_id sku name qty price
:5001 A1 Widget 2 25.00
:5001 B2 Gadget 1 75.50
:5001 C3 Adapter 3 44.67
:5002 A1 Widget 1 25.00
:5002 D4 Cable 2 32.50

# Supplier Info
table.suppliers
id name lead_days rating
SUP-10 "TechParts Inc" 3 4.8
SUP-15 "FastShip Co" 1 4.5
```

This entire dataset in JSON would be **~60% larger** with repeated field names and structural punctuation.

---

## Token Efficiency Analysis

### Real-World Comparison

**Dataset:** 100 users with 5 fields each

| Format | Estimated Tokens | Relative Size |
|--------|------------------|---------------|
| JSON | ~2,800 tokens | Baseline |
| ISON | ~1,200 tokens | **57% smaller** |

### Where Savings Come From

1. **No repeated field names** — Header once vs. 100× in JSON
2. **No structural punctuation** — No `{}[]"":,,` per row
3. **Unquoted simple strings** — `Alice` not `"Alice"`
4. **Native table format** — Data shape matches representation

### Practical Impact

| Scenario | JSON | ISON | Benefit |
|----------|------|------|---------|
| RAG chunks | 10 results | 15-20 results | Better answers |
| Agent context | Limited state | Full state | Better decisions |
| Tool results | Truncated | Complete | More information |
| System prompts | Basic context | Rich context | Better grounding |

---

## When to Use ISON vs JSON

### Use ISON

- LLM prompts and context
- RAG pipeline outputs
- Multi-agent communication
- Tool/function call results
- Any data flowing to/from language models
- Token-constrained environments

### Use JSON

- Traditional web APIs (REST, GraphQL)
- Browser JavaScript consumption
- Existing toolchains that expect JSON
- Maximum interoperability with legacy systems

**ISON replaces JSON for AI workflows, not for web APIs.**

---

## Parser Requirements

### Where Parsers Are NOT Needed

**LLM input** — Just embed ISON as text:

```python
context = """
table.users
id name role
101 Mahesh admin
"""
prompt = f"Given:\n{context}\nWho is admin?"
```

**Multi-agent communication** — Agents exchange text strings.

### Where Parsers ARE Needed

**Database serialization** — Convert query results to ISON:

```python
results = db.query("SELECT * FROM users")
ison_output = ison_serializer.dumps(results)
```

**Application integration** — When code needs typed objects:

```python
doc = ison_parser.loads(ison_text)
for user in doc['users'].rows:
    if user['active']:
        send_email(user['email'])
```

---

## Getting Started

### Python Reference Parser

```python
import ison_parser

# Parse ISON
doc = ison_parser.loads("""
table.products
id name price
1 Widget 29.99
2 Gadget 49.99
""")

# Access data
for row in doc['products'].rows:
    print(f"{row['name']}: ${row['price']}")

# Convert to JSON
print(doc.to_json())

# Serialize back to ISON
print(ison_parser.dumps(doc))
```

### CLI Usage

```bash
# Validate
python ison_parser.py data.ison --validate

# Convert to JSON
python ison_parser.py data.ison -f json -o output.json

# ISON to ISON (normalize)
python ison_parser.py data.ison -f ison -o clean.ison
```

---

## Specification Summary

### Block Structure
```
kind.name
field1 field2 field3
value1 value2 value3
...
```

### Type Inference (in order)
1. `true` / `false` → boolean
2. `null` → null
3. `^-?[0-9]+$` → integer
4. `^-?[0-9]+\.[0-9]+$` → float
5. `:...` → reference
6. Otherwise → string

### Quoting Rules
- Quote strings with spaces: `"New York"`
- Quote to force string type: `"true"`, `"123"`
- Escape sequences: `\"`, `\\`, `\n`, `\t`

### Null Handling
- Explicit: `null`
- Missing trailing values → null
- Empty string: `""`

---

## Design Principles

1. **Whitespace as delimiter** — No commas
2. **Quotes only when necessary** — Cleaner defaults
3. **Tables over nesting** — Normalize don't nest
4. **Explicit references** — Graph-aware with `:ID`
5. **Type inference** — Smart defaults, override with quotes

---

## Conclusion

ISON is not just a "better JSON"—it's a format **designed for how LLMs work**:

- **Token-efficient** — Fit more data in context windows
- **LLM-native** — Zero-shot understanding, reliable generation
- **Relationship-aware** — Graph semantics with `:ID` references
- **Minimal syntax** — Less noise, more signal

As LLMs become central to data workflows, the format you use to communicate with them matters. ISON is purpose-built for this new paradigm.

---

## Resources

- **Specification:** ISON v1.0 Spec
- **Python Parser:** `ison_parser.py`
- **Examples:** ISON Use Case Examples

---

*ISON: Because your LLM deserves better than JSON.*
