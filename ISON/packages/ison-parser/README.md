<p align="center">
  <img src="https://raw.githubusercontent.com/somewheresystems/ison/main/ison-logo.png" alt="ISON Logo" width="120" height="120">
</p>

# ISON Parser

**ISON (Interchange Simple Object Notation)** - A token-efficient data format optimized for AI/LLM workflows.

[![PyPI version](https://badge.fury.io/py/ison-parser.svg)](https://badge.fury.io/py/ison-parser)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Features

- **30-70% fewer tokens** than JSON for structured data
- **ISONL streaming format** for fine-tuning datasets and event streams
- **Native references** for relational data (`:`-prefixed IDs)
- **Type inference** for clean, minimal syntax
- **Zero dependencies** - pure Python implementation

## Installation

```bash
pip install ison-parser
```

## Quick Start

### Basic Usage

```python
import ison_parser

# Parse ISON
ison_text = """
table.users
id name email
1 Alice alice@example.com
2 Bob bob@example.com
"""

doc = ison_parser.loads(ison_text)

# Access data
users = doc['users']
print(users.rows[0]['name'])  # Alice

# Convert to JSON
json_data = doc.to_dict()
```

### ISONL Streaming Format

ISONL is perfect for fine-tuning datasets, event streams, and logs:

```python
from ison_parser import loads_isonl, dumps_isonl, isonl_stream

# Parse ISONL
isonl_text = """table.examples|instruction response|"Summarize this" "Brief summary..."
table.examples|instruction response|"Translate to Spanish" "Hola mundo" """

doc = loads_isonl(isonl_text)

# Stream large files (constant memory)
with open("large_dataset.isonl", "r") as f:
    for record in isonl_stream(f):
        process(record)
```

### Format Conversion

```python
from ison_parser import ison_to_isonl, isonl_to_ison

# ISON to ISONL (one line per record)
isonl = ison_to_isonl(ison_text)

# ISONL to ISON (grouped blocks)
ison = isonl_to_ison(isonl_text)
```

## ISON Format

### Tables (Structured Data)

```
table.users
id name email active
1 Alice alice@example.com true
2 Bob bob@example.com false
```

### Objects (Key-Value)

```
object.config
timeout 30
debug true
api_key "sk-xxx"
```

### References

```
table.orders
id customer_id total
O1 :C1 99.99
O2 :C2 149.50
```

## ISONL Format

Each line is a self-contained record:

```
kind.name|field1 field2 field3|value1 value2 value3
```

Example:
```
table.users|id name email|1 Alice alice@example.com
table.users|id name email|2 Bob bob@example.com
table.orders|id user total|O1 :1 99.99
```

## Token Efficiency

| Records | JSON Tokens | ISON Tokens | Savings |
|---------|-------------|-------------|---------|
| 10 | ~200 | ~60-140 | 30-70% |
| 100 | ~2000 | ~600-1400 | 30-70% |
| 1000 | ~20000 | ~6000-14000 | 30-70% |

## API Reference

### Core Functions

- `loads(text)` - Parse ISON string to Document
- `dumps(doc)` - Serialize Document to ISON string
- `load(path)` - Load ISON from file
- `dump(doc, path)` - Save Document to file

### ISONL Functions

- `loads_isonl(text)` - Parse ISONL string to Document
- `dumps_isonl(doc)` - Serialize Document to ISONL
- `load_isonl(path)` - Load ISONL from file
- `dump_isonl(doc, path)` - Save Document to ISONL file
- `isonl_stream(file)` - Stream ISONL records (generator)
- `ison_to_isonl(text)` - Convert ISON to ISONL
- `isonl_to_ison(text)` - Convert ISONL to ISON

### Classes

- `Document` - Container for ISON blocks
- `Block` - Single data block (table/object)
- `Reference` - Reference to another record
- `ISONLRecord` - Single ISONL record

## CLI Usage

```bash
# Convert JSON to ISON
ison input.json -o output.ison

# Convert ISON to JSON
ison input.ison --to-json -o output.json

# Validate ISON file
ison input.ison --validate
```

## Database Plugins

Export database tables directly to ISON for LLM workflows:

### SQLite (Zero Dependencies)

```python
from ison_parser.plugins import SQLiteToISON

# Export entire database
with SQLiteToISON('mydb.sqlite') as db:
    ison_text = db.export_all()

# Export specific tables
    ison_text = db.export_tables(['users', 'orders'])

# Stream large tables as ISONL
    for line in db.stream_table('logs'):
        print(line)

# Foreign keys auto-convert to ISON references (:id)
```

### PostgreSQL

```bash
pip install psycopg2-binary
```

```python
from ison_parser.plugins import PostgreSQLToISON

with PostgreSQLToISON('postgresql://user:pass@localhost/mydb') as db:
    # Export all tables
    ison_text = db.export_all()

    # Export with related tables (follows foreign keys)
    ison_text = db.export_with_relations('orders')

    # Stream for large datasets
    for line in db.stream_table('events', batch_size=5000):
        process(line)
```

### SQLAlchemy (Any Database)

Works with MySQL, MariaDB, Oracle, MS SQL Server, and more:

```bash
pip install sqlalchemy pymysql  # For MySQL
```

```python
from ison_parser.plugins import SQLAlchemyToISON

# MySQL
with SQLAlchemyToISON('mysql+pymysql://user:pass@localhost/db') as db:
    ison_text = db.export_all()

# Export ORM models directly
from myapp.models import User, Order
    ison_text = db.export_models([User, Order], session)

# Custom queries
    ison_text = db.export_query(
        "SELECT * FROM users WHERE active = true",
        block_name="active_users"
    )
```

## Vector Database Plugins

Export vector search results directly to ISON for RAG pipelines:

### ChromaDB

```bash
pip install chromadb
```

```python
from ison_parser.plugins import ChromaToISON

with ChromaToISON() as db:
    # Export RAG context (optimized for LLM prompts)
    ison_context = db.export_for_rag(
        collection='documents',
        query='What is ISON?',
        n_results=5
    )

    # Export search results with scores
    ison_text = db.export_query_results(
        collection='documents',
        query_texts=['semantic search query'],
        n_results=10
    )

    # Stream large collections as ISONL
    for line in db.stream_collection('documents'):
        process(line)
```

### Pinecone

```bash
pip install pinecone-client
```

```python
from ison_parser.plugins import PineconeToISON

exporter = PineconeToISON(api_key='your-key')

# Export search results
ison_text = exporter.export_query_results(
    index='my-index',
    query_vector=embedding,
    top_k=10
)

# RAG context with custom embedding function
ison_context = exporter.export_for_rag(
    index='my-index',
    query='What is ISON?',
    embedding_fn=my_embed_function,
    top_k=5
)
```

### Qdrant

```bash
pip install qdrant-client
```

```python
from ison_parser.plugins import QdrantToISON

exporter = QdrantToISON(host='localhost', port=6333)

# Export search results
ison_text = exporter.export_search_results(
    collection='documents',
    query_vector=embedding,
    limit=10
)

# RAG context
ison_context = exporter.export_for_rag(
    collection='documents',
    query='What is ISON?',
    embedding_fn=my_embed_function,
    limit=5
)
```

## Use Cases

- **LLM Fine-tuning datasets** - 30-70% smaller training files
- **RAG pipelines** - Token-efficient context from vector DBs
- **Database-to-LLM** - Direct export with SQL plugins
- **Vector search** - Export results in compact format
- **Event streaming** - Append-only logs
- **Configuration** - Human-readable configs
- **API responses** - Reduced bandwidth

## Links

- [Documentation](https://somewheresystems.github.io/ison)
- [Specification](https://somewheresystems.github.io/ison/spec.html)
- [ISONL Spec](https://somewheresystems.github.io/ison/isonl.html)
- [GitHub](https://github.com/somewheresystems/ison)

## License

MIT License - see [LICENSE](LICENSE) for details.
