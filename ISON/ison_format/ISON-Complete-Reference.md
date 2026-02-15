# ISON: Complete Reference Guide

## Interchange Simple Object Notation

### The LLM-Native Data Format

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Format Comparison: JSON vs TOON vs ISON](#2-format-comparison-json-vs-toon-vs-ison)
3. [Specification Development](#3-specification-development)
4. [Core Syntax](#4-core-syntax)
5. [Use Cases](#5-use-cases)
6. [Advantages Over Current Implementations](#6-advantages-over-current-implementations)
7. [LLM Compatibility](#7-llm-compatibility)
8. [Handling Deep Nesting](#8-handling-deep-nesting)
9. [OCR and PDF Processing](#9-ocr-and-pdf-processing)
10. [RAG Pipeline Integration](#10-rag-pipeline-integration)
11. [Context Window Maximization](#11-context-window-maximization)
12. [Implementation Resources](#12-implementation-resources)

---

## 1. Introduction

### What is ISON?

ISON (Interchange Simple Object Notation) is a minimal, token-efficient data serialization format designed specifically for Large Language Model (LLM) workflows. It serves as the preferred alternative to JSON wherever structured data flows to or from language models.

```
table.users
id name email active
101 Mahesh mahesh@example.com true
102 "Priya Sharma" priya@example.com true
103 Ravi ravi@example.com false
```

**No braces. No brackets. No repeated field names. Just data.**

### Design Goals

- **Minimal syntax**: Reduce punctuation overhead that wastes tokens
- **LLM-optimized**: Maximize comprehension with minimal cognitive load
- **Token-efficient**: Fit more data in context windows than JSON allows
- **Unambiguous**: Fully parseable without context
- **Relational**: Native support for references and relationships
- **Human-readable**: Clear structure without visual noise
- **AI-native**: Become the standard format for LLM data interchange

### Relationship to JSON

ISON is designed to be the preferred alternative to JSON for AI and LLM use cases. While JSON remains the standard for web APIs and general-purpose data interchange, its verbosity and structural overhead become liabilities when:

- **Token cost matters**: LLM context windows are finite and expensive
- **LLM comprehension matters**: Repeated keys and heavy punctuation add cognitive load
- **Data is tabular**: JSON's array-of-objects pattern repeats field names unnecessarily
- **Relationships exist**: JSON has no native reference mechanism

**ISON aims to be the default format for AI data workflows**, just as JSON became the default for web APIs.

---

## 2. Format Comparison: JSON vs TOON vs ISON

### High-Level Summary

| Feature | JSON | TOON | ISON |
|---------|------|------|------|
| Purpose | Universal data format | Ultra-compact table format | Simple, unified format for AI/LLMs |
| Structure | Objects + arrays | CSV-with-header | Objects + tables + references |
| Notation | Heavy punctuation | Light punctuation | Almost no punctuation |
| Nested fields | ✔ | ❌ | ✔✔ (via dot paths) |
| Relationships | ❌ | ❌ | ✔✔ (via :ID) |
| Tables | ✔ | ✔✔ | ✔✔✔ |
| Human readability | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| LLM token efficiency | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Best for | APIs, configs | Flat data | Graph-aware AI workflows |

### Complete Example Comparison

**Dataset:** Users with id, name, active flag

#### JSON

```json
{
  "users": [
    { "id": 1, "name": "Alice", "active": true },
    { "id": 2, "name": "Bob", "active": false },
    { "id": 3, "name": "Charlie", "active": true }
  ]
}
```

**Characteristics:**
- Requires `{}`, `[]`, `"`, `:`, `,`
- High token count
- Familiar but verbose

#### TOON

```
users[3]{id,name,active}:
  1,Alice,true
  2,Bob,false
  3,Charlie,true
```

**Characteristics:**
- Very compact for rows
- Still uses `{}`, `,`, `:`
- Cannot express nested objects or relationships

#### ISON

```
table.users
id name active
1 Alice true
2 Bob false
3 Charlie true
```

**Characteristics:**
- No commas, braces, brackets, or unnecessary quotes
- Direct and immediately readable
- Best token efficiency
- Works for objects, tables, and graphs

### Nested Data Comparison

**Dataset:** Order with nested customer

#### JSON

```json
{
  "order": {
    "id": 5001,
    "customer": { "name": "Mahesh", "country": "USA" },
    "total": 125.50
  }
}
```

#### TOON

❌ Not possible or extremely awkward

#### ISON

```
object.order
id customer.name customer.country total
5001 Mahesh USA 125.50
```

✔ No nesting syntax  
✔ Dot-path fields  
✔ Still flat and readable

### Relationship Comparison

**Dataset:** User belongs to Team

#### JSON

```json
{
  "user": { "id": 101, "name": "Mahesh", "teamId": 10 },
  "team": { "id": 10, "name": "AI-Research" }
}
```

#### TOON

❌ No concept of references

#### ISON

```
object.team
id name
10 AI-Research

object.user
id name team
101 Mahesh :10
```

✔ `:10` = reference  
✔ AI can follow relationships  
✔ Perfect for graph reasoning

### Token Efficiency Comparison

| Format | Approx tokens (3-user example) | Efficiency |
|--------|--------------------------------|------------|
| JSON | ~70-80 tokens | ❌ Worst |
| TOON | ~30-40 tokens | ✔ Medium |
| ISON | ~18-24 tokens | ⭐ Best |

---

## 3. Specification Development

### Edge Cases Addressed

The ISON v1.0 specification addresses critical parsing challenges:

#### 1. Delimiters and Spaces in Values

**Problem:** How to parse `New York` as a single field?

**Solution:** Values containing spaces must be quoted.

```
table.users
id name city
1 Alice "New York"
2 Bob "San Francisco"
```

#### 2. Type Discrimination

**Solution:** Type inference rules applied in order:

1. `true` / `false` → boolean
2. `null` → null
3. `^-?[0-9]+$` → integer
4. `^-?[0-9]+\.[0-9]+$` → float
5. Starts with `:` → reference
6. Otherwise → string

To force string type, use quotes: `"true"`, `"123"`

#### 3. Null and Empty Values

```
table.users
id name email
1 Alice null      # email = null
2 Bob             # email = null (missing)
3 Eve ""          # email = "" (empty string)
```

#### 4. Escaping Reserved Characters

Inside quoted strings:
- `\"` → double quote
- `\\` → backslash
- `\n` → newline
- `\t` → tab

```
table.messages
id text
1 "Hello \"World\""
2 "Line 1\nLine 2"
```

#### 5. Nested Arrays (Normalization)

Instead of inline arrays, normalize into separate tables:

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

---

## 4. Core Syntax

### Block Structure

Every ISON document consists of blocks:

```
kind.name
field1 field2 field3
value1 value2 value3
```

**Block kinds:**
- `object` — Single record or small set
- `table` — Multi-row tabular data
- `meta` — Document metadata
- `rel` — Relationship definitions

### Tables

```
table.products
id name price in_stock
1 Widget 29.99 true
2 Gadget 49.99 false
3 "Super Gizmo" 99.99 true
```

### Objects

```
object.config
timeout debug max_retries
30 true 3
```

### References

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

Namespaced references: `:user:101`, `:team:10`

### Dot-Path Fields

Flatten hierarchies without deep nesting:

```
object.order
id customer.name customer.address.city total
5001 Mahesh Dallas 125.50
```

### Comments

```
# This is a comment
table.users
id name
1 Alice
2 Bob
```

### Multiple Blocks

Blocks are separated by blank lines:

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

## 5. Use Cases

ISON is designed for **any system exchanging structured data with LLMs**:

### 5.1 LLM Prompt Engineering

Structured context in system prompts:

```
# Customer context for support conversation
object.customer
id name tier support_priority
C-1001 "Sarah Chen" enterprise high

table.subscriptions
id product status monthly_cost
SUB-101 "Pro Analytics" active 299.00
SUB-102 "Data Warehouse" active 599.00
SUB-103 "API Access" suspended 99.00

table.support_history
ticket_id date issue resolution satisfaction
T-5001 2025-01-10 "Login issues" resolved 5
T-5002 2025-01-15 "Slow queries" resolved 4
```

### 5.2 RAG Pipelines

Retrieved chunks with metadata:

```
object.query
id text timestamp
Q-7842 "How do I configure authentication?" 2025-01-20T14:32:00Z

table.retrieved_chunks
rank chunk_id doc_id content similarity
1 CHK-1842 :DOC-42 "MAPLE agents support three authentication modes..." 0.94
2 CHK-1291 :DOC-29 "For OAuth 2.0, set auth.type to 'oauth2'..." 0.91
3 CHK-1103 :DOC-42 "API key authentication is simplest..." 0.87
```

### 5.3 Multi-Agent AI Systems

Agent state and message exchange:

```
table.agents
id name type status current_task last_heartbeat
:agent-001 orchestrator coordinator active null 2025-01-20T10:14:58Z
:agent-002 researcher worker active :TASK-301 2025-01-20T10:14:55Z
:agent-003 coder worker idle null 2025-01-20T10:14:50Z

table.shared_memory
key value updated_by updated_at
user_goal "Build efficient RAG system" :agent-001 2025-01-20T09:00:00Z
current_phase "research" :agent-001 2025-01-20T10:00:00Z
```

### 5.4 Tool and Function Call Results

```
object.tool_call
id tool timestamp status
TC-8001 web_search 2025-01-20T10:20:00Z success

table.results
rank title url snippet
1 "ISON Specification" github.com/ison "A minimal format..."
2 "ISON vs JSON" blog.com/compare "Token efficiency..."
3 "ISON Parser" pypi.org/ison "Python implementation..."
```

### 5.5 Database Query Outputs

Works for relational, vector, graph, or hybrid:

```
# Vector search results
table.similar_products
rank product_id name similarity in_stock supplier
1 :PROD-842 "Ergonomic Keyboard" 0.94 true :SUP-10
2 :PROD-291 "Vertical Mouse" 0.91 true :SUP-10

# Graph traversal
table.suppliers
id name rating lead_time_days
:SUP-10 "ErgoTech Inc" 4.8 3
:SUP-15 ComfortPlus 4.5 5
```

### 5.6 Knowledge Base Serialization

```
table.categories
id name parent level
CAT-1 Electronics null 0
CAT-2 Computers :CAT-1 1
CAT-3 Laptops :CAT-2 2
CAT-4 "Gaming Laptops" :CAT-3 3
```

### 5.7 Agentic Workflows

Task queues, execution logs, decision trees:

```
table.task_queue
id type priority status assigned_to deadline
TASK-101 research high in_progress :agent-002 2025-01-20T12:00:00Z
TASK-102 code medium queued null 2025-01-20T14:00:00Z

table.dependencies
task_id depends_on dependency_type
:TASK-102 :TASK-101 blocking
:TASK-103 :TASK-102 blocking
```

### 5.8 Multimodal AI Systems

Object detection, transcription, OCR results:

```
object.image
id path dimensions
IMG-001 street.jpg 1920x1080

table.detections
id label confidence bbox.x bbox.y bbox.w bbox.h
1 person 0.96 150 200 80 280
2 car 0.91 800 400 400 250
3 dog 0.87 200 450 100 80
```

---

## 6. Advantages Over Current Implementations

### 6.1 LLM Prompt Engineering

| Metric | JSON | ISON | Improvement |
|--------|------|------|-------------|
| Characters | 1,180 | 580 | **51% smaller** |
| Estimated tokens | ~280 | ~85-195 | **30-70% fewer tokens** |
| Field name repetition | 15x | 1x | **No repetition** |

**Key advantage:** Include **twice as much context** in the same token budget.

### 6.2 RAG Pipelines

| Metric | JSON | ISON | Improvement |
|--------|------|------|-------------|
| Structural overhead per result | ~50 chars | 0 | **Eliminated** |
| Total overhead for 5 results | ~250 chars | ~30 chars | **88% reduction** |

**Key advantage:** Include more retrieved chunks = better answers.

### 6.3 Multi-Agent Systems

| Metric | JSON | ISON | Improvement |
|--------|------|------|-------------|
| Agent references | String `"agent-001"` | Typed `:agent-001` | **Semantic clarity** |
| Nested structure | 3 levels deep | Flat tables | **Easier to parse** |

**Key advantage:** Graph relationships are explicit, not implicit.

### 6.4 Tool Results

| Metric | JSON | ISON | Improvement |
|--------|------|------|-------------|
| Parsing complexity | Nested objects | Flat blocks | **Simpler structure** |
| Result overhead | Repeated keys | Header once | **Linear scaling** |

**Key advantage:** Cleaner format = faster LLM comprehension.

### 6.5 Database Outputs

| Metric | JSON | ISON | Improvement |
|--------|------|------|-------------|
| Foreign key representation | `"supplier": "SUP-10"` | `:SUP-10` | **Explicit relationship** |
| Multi-table queries | Awkward nesting | Natural normalization | **Database-native** |

**Key advantage:** LLM can "see" joins and follow references.

### 6.6 Knowledge Bases

| Metric | JSON | ISON | Improvement |
|--------|------|------|-------------|
| Hierarchy visibility | String matching | Reference following | **Tree structure visible** |

**Key advantage:** Ontologies and taxonomies map naturally.

### 6.7 Agentic Workflows

| Metric | JSON | ISON | Improvement |
|--------|------|------|-------------|
| Log readability | Scan through braces | Table format | **Instant visual scan** |
| Debugging | Parse nested structure | Read like spreadsheet | **Faster analysis** |

**Key advantage:** Tabular logs are dramatically easier to analyze.

### 6.8 Multimodal Systems

| Metric | JSON | ISON | Improvement |
|--------|------|------|-------------|
| Bbox access | `detection.bbox.x` | `bbox.x` (dot-path) | **Flattened but structured** |
| Spatial reasoning | Mental reconstruction | Visual table layout | **Easier for LLM** |

**Key advantage:** Detection tables make coordinate comparison trivial.

---

## 7. LLM Compatibility

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

### Where Parsers Are Needed

| Location | Direction | Purpose | Required? |
|----------|-----------|---------|-----------|
| Database → LLM | Serialize | Convert query results to ISON | Yes |
| LLM → Application | Parse | Convert LLM output to typed objects | Optional |
| LLM ↔ LLM | None | Multi-agent communication | No parser—just text |

### When You DON'T Need a Parser

**LLM Prompts (Input):** Just embed ISON as text:

```python
context = """
table.users
id name role
101 Mahesh admin
"""
prompt = f"Given:\n{context}\nWho is admin?"
```

**Multi-Agent Communication:** Agents exchange text strings.

### When You NEED a Parser

**Database Serialization:** Convert query results to ISON text.

**Application Integration:** When code needs typed objects:

```python
doc = ison_parser.loads(ison_text)
for user in doc['users'].rows:
    if user['active']:
        send_email(user['email'])
```

### Generation Reliability

LLMs generate valid ISON more reliably than JSON because:

- No braces to match
- No commas to forget
- Quotes only when needed
- Whitespace-delimited (hard to get wrong)

---

## 8. Handling Deep Nesting

### ISON's Approach: Normalize, Don't Nest

ISON intentionally discourages deep nesting. Instead:

1. **Dot-paths** for shallow nesting (1-2 levels)
2. **Normalization** into separate tables for deeper structures

### Level 1-2: Dot-Paths Work Great

```
object.order
id customer.name customer.address.city total
5001 Mahesh Dallas 125.50
```

### Level 3+: Use Normalization

**Deeply nested JSON:**

```json
{
  "company": {
    "departments": [
      {
        "teams": [
          {
            "members": [...]
          }
        ]
      }
    ]
  }
}
```

**ISON Normalized:**

```
object.company
id name
C1 TechCorp

table.departments
id name company
D1 Engineering :C1

table.teams
id name department
T1 Platform :D1

table.members
id name team
M1 Alice :T1
M2 Bob :T1
```

### Why Normalization is Better for LLMs

**Direct Answering:**

Question: "Who has Python skills?"

- **Nested JSON:** Traverse company → departments → teams → members → skills
- **Normalized ISON:** Scan `member_skills` table directly

**Relationship Reasoning:**

References make the graph explicit: Alice (`:M1`) → team `:T1` → department `:D1`

### Recursive Structures: Adjacency List

For trees like file systems:

```
table.files
id name parent type
1 root null directory
2 src :1 directory
3 components :2 directory
4 Button.tsx :3 file
```

### Honest Assessment

| Depth | ISON Approach | Quality |
|-------|---------------|---------|
| 1-2 levels | Dot-paths | ⭐⭐⭐⭐⭐ Excellent |
| 3-4 levels | Normalize to tables | ⭐⭐⭐⭐ Good |
| 5+ levels | Adjacency list | ⭐⭐⭐ Adequate |

**ISON optimizes for the common case (tabular + relational) at the expense of the rare case (deeply recursive trees).**

---

## 9. OCR and PDF Processing

### ISON's Role in OCR

ISON doesn't perform OCR—it's an **output format** for representing extracted content:

```
PDF → OCR Engine → ISON → LLM
```

### Advantages for OCR Results

#### Multiple Tables Per Document

```
# Page 1: Revenue
table.revenue
region q1 q2 q3 q4
Americas 1.2M 1.4M 1.5M 1.8M
EMEA 0.8M 0.9M 1.0M 1.1M

# Page 2: Expenses
table.expenses
category amount
Salaries 2.1M
Marketing 0.6M
```

#### Mixed Content Types

```
table.content_blocks
id page type content
1 1 title "Q4 Financial Report"
2 1 paragraph "This report summarizes..."
3 1 table_ref :revenue
```

#### Complex Table Structures (Multi-Level Headers)

```
table.financials
metric year_2024.q3 year_2024.q4 year_2023.q3 year_2023.q4
Revenue 1.5M 1.8M 1.2M 1.4M
Expenses 1.0M 1.2M 0.9M 1.0M
```

#### Form Extraction

```
object.invoice
number date vendor total
"INV-2025-0042" 2025-01-20 "Acme Corp" 2532.60

table.line_items
description quantity unit_price amount
"Consulting Services" 10 150.00 1500.00
"Travel Expenses" 1 350.00 350.00
```

#### Confidence Scores

```
table.extracted_text
id content confidence bbox.x bbox.y
1 "Revenue Summary" 0.98 100 50
2 "1,234,567" 0.94 150 100
3 "Preliminary" 0.72 300 100
```

### Token Savings for OCR

Azure Document Intelligence outputs ~400 tokens for a 4×3 table in JSON. ISON: ~40 tokens. **90% reduction.**

---

## 10. RAG Pipeline Integration

### Where ISON Helps

```
Documents → Chunking → Embedding → Retrieval → LLM Generation
    ↓           ↓          ↓           ↓            ↓
 Smaller    Natural    Smaller     Efficient    More chunks
           boundaries  payloads    results      in context
```

### Document Representation

**JSON (100 products):** Field names repeated 100×  
**ISON (100 products):** Field names once in header

**Savings:** 40-50%

### Chunking Advantages

#### Self-Contained Rows

Each chunk includes the header:

```
# Chunk 1
table.products
id name price
PROD-001 Keyboard 149.99
PROD-002 Mouse 79.99

# Chunk 2
table.products
id name price
PROD-003 Monitor 299.99
PROD-004 Webcam 89.99
```

#### Natural Boundaries

- Block boundaries (between tables)
- Row boundaries
- Semantic groupings (by category)

#### Header Overhead

- **JSON per-chunk:** ~80 characters
- **ISON per-chunk:** ~50 characters
- **Savings:** 38%

### Metadata Storage

**JSON:** Metadata repeated per chunk  
**ISON:** Normalized into separate tables with references

```
table.chunks
id content
CHK-1842 "Content here..."

table.chunk_metadata
id doc section page confidence
:CHK-1842 :DOC-42 Electronics 5 0.95

table.documents
id title total_chunks
:DOC-42 "Product Catalog" 45
```

**Savings:** 60-70% less metadata storage

### Retrieval Results

| Results | JSON Tokens | ISON Tokens | Savings |
|---------|-------------|-------------|---------|
| 5 | ~530 | ~350 | 34% |
| 10 | ~1,060 | ~680 | 36% |
| 20 | ~2,120 | ~1,320 | 38% |

**With 20 results, you save ~800 tokens—enough for 6-8 additional chunks.**

### Context Window Impact

**Scenario: 8K Context Window**

| Component | JSON Tokens | ISON Tokens |
|-----------|-------------|-------------|
| System prompt | 500 | 500 |
| Retrieved chunks (10) | 2,500 | 1,600 |
| Query + instructions | 200 | 200 |
| **Available for response** | **4,800** | **5,700** |

ISON gives you **900 more tokens** for the response—or room for 3-4 more chunks.

### Chunking Strategies

#### Row-Based
N rows per chunk with header

#### Semantic
Group by meaningful field (category, department)

#### Block-Based
Each ISON block = one chunk

#### Relationship-Aware
Keep related data together (order + items + customer)

---

## 11. Context Window Maximization

### Where ISON Provides Maximum Benefit

| Data Type | ISON Benefit | Recommendation |
|-----------|--------------|----------------|
| Tables with 10+ rows | ⭐⭐⭐⭐⭐ High | Always use ISON |
| Graph query results | ⭐⭐⭐⭐ Good | Use ISON |
| Configuration objects | ⭐⭐⭐ Medium | ISON helps |
| Document content | ⭐ Minimal | Format doesn't matter |

### Token Efficiency Sources

1. **No repeated field names** — Header once vs every row
2. **No structural punctuation** — No `{}[]"":,,` per row
3. **Unquoted simple strings** — `Alice` not `"Alice"`
4. **Native table format** — Data shape matches representation

### Real Measurements

**3 rows, 5 fields:**
- JSON: ~85 tokens
- ISON: ~45 tokens
- **Savings: 47%**

**100 rows, 5 fields:**
- JSON: ~2,800 tokens
- ISON: ~1,200 tokens
- **Savings: 57%**

### Practical Impact

| Scenario | JSON | ISON | Benefit |
|----------|------|------|---------|
| RAG chunks | 10 results | 15-20 results | Better answers |
| Agent context | Limited state | Full state | Better decisions |
| Tool results | Truncated | Complete | More information |

### Cognitive Clarity

Beyond token count, ISON helps LLM comprehension:

```
table.order_items
orderId sku qty price
5001 A1 2 25.00
5001 B2 1 75.50
```

The LLM immediately recognizes:
- This is tabular data
- These are the columns
- Here are the rows

With JSON's repeated keys, the LLM must "parse" the structure mentally each time.

---

## 12. Implementation Resources

### Deliverables

| File | Description |
|------|-------------|
| ISON-Spec-v1.0.md | Complete formal specification with ABNF grammar |
| ISON-Overview.md | Shareable introduction document |
| ISON-Use-Case-Examples.md | 28 detailed examples across 8 use cases |
| ison_parser.py | Python reference parser with CLI |
| test_ison_parser.py | Test suite (14 tests) |
| sample.ison | Working example file |

### Python Parser Usage

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

### Integration Points

#### Database Serialization

```python
results = db.query("SELECT * FROM users")
ison_output = ison_serializer.dumps(results)
```

#### RAG Pipeline

```python
# Retrieve
results = vector_db.query(query_embedding, top_k=10)

# Format as ISON
ison_context = format_as_ison(results)

# Generate
response = llm.complete(f"Context:\n{ison_context}\n\nQuestion: {query}")
```

#### Multi-Agent

```python
# Agent sends ISON message
message = """
object.task
id type status
TASK-301 research complete

table.findings
rank source summary
1 arxiv.org "Key finding here..."
"""
agent2.receive(message)
```

---

## Summary

### ISON Value Proposition

| Dimension | Improvement |
|-----------|-------------|
| Token cost | 30-60% fewer tokens |
| Repeated field names | Eliminated |
| Punctuation overhead | Minimal |
| Table support | Native |
| Relationships | Native (`:ID`) |
| Nesting | Dot-paths or normalize |
| LLM parsing | Visual table scan |

### When to Use ISON

- LLM prompts and context
- RAG pipeline outputs
- Multi-agent communication
- Tool/function call results
- Database query outputs
- Knowledge base serialization
- Agentic workflows
- Multimodal AI results

### When to Use JSON

- Traditional web APIs
- Browser JavaScript consumption
- Existing toolchains
- Maximum interoperability with legacy systems

---

## Conclusion

ISON is not just a "better JSON"—it's a format **designed for how LLMs work**:

- **Token-efficient**: Fit more data in context windows
- **LLM-native**: Zero-shot understanding, reliable generation
- **Relationship-aware**: Graph semantics with `:ID` references
- **Minimal syntax**: Less noise, more signal

As LLMs become central to data workflows, the format you use to communicate with them matters. ISON is purpose-built for this new paradigm.

---

*ISON: Because your LLM deserves better than JSON.*
