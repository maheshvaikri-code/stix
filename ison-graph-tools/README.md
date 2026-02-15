# ISONGraph Tools

A collection of tools for working with ISONGraph, including format converters, schema generation, and visualization utilities.

## Tools Overview

| Tool | Description |
|------|-------------|
| **Converters** | Convert between ISONGraph and GraphML, RDF, CSV, Cypher, DOT formats |
| **Schema Generator** | Automatically generate schemas from JSON graph data |
| **Formatter** | Format schemas for Python, TypeScript, JSON, ISON |

## Installation

```bash
pip install ison-graph[tools]
```

---

## Format Converters

Convert between ISONGraph and various popular graph formats.

### Supported Formats

| Format | Import | Export | Description |
|--------|--------|--------|-------------|
| GraphML | Yes | Yes | XML-based graph format (yEd, Gephi compatible) |
| RDF/Turtle | Yes | Yes | Semantic web format |
| N-Triples | No | Yes | Line-based RDF format |
| CSV | Yes | Yes | Tabular node/edge files |
| Neo4j Cypher | No | Yes | Graph database import statements |
| DOT/Graphviz | No | Yes | Visualization format (SVG, PNG) |

### Quick Usage

```python
from tools.converters import (
    GraphMLConverter,
    RDFConverter,
    CSVConverter,
    CypherConverter,
    DOTConverter
)
from ison_graph import ISONGraph

# Create a graph
graph = ISONGraph("social")
graph.add_node("person", "alice", {"name": "Alice", "age": 30})
graph.add_node("person", "bob", {"name": "Bob", "age": 25})
graph.add_edge("KNOWS", ("person", "alice"), ("person", "bob"), {"since": 2020})

# Export to GraphML
graphml = GraphMLConverter().to_graphml(graph)

# Export to RDF Turtle
turtle = RDFConverter(base_uri="http://example.org/").to_turtle(graph)

# Export to CSV
nodes_csv, edges_csv = CSVConverter().to_csv(graph)

# Export to Neo4j Cypher
cypher = CypherConverter().to_cypher(graph, mode="merge")

# Export to DOT (and render to SVG/PNG)
dot = DOTConverter().to_dot(graph)
DOTConverter().save_svg(graph, "graph.svg")
```

### GraphML Converter

```python
from tools.converters import GraphMLConverter

converter = GraphMLConverter(include_properties=True)

# Export
graphml = converter.to_graphml(graph)
converter.save(graph, "graph.graphml")

# Import
graph = converter.from_graphml(graphml)
graph = converter.load("graph.graphml")
```

### RDF Converter

```python
from tools.converters import RDFConverter

converter = RDFConverter(
    base_uri="http://example.org/",
    include_properties=True
)

# Export to Turtle
turtle = converter.to_turtle(graph)

# Export to N-Triples
ntriples = converter.to_ntriples(graph)

# Import from Turtle
graph = converter.from_turtle(turtle)

# Save/Load
converter.save(graph, "graph.ttl", format="turtle")
graph = converter.load("graph.ttl")
```

### CSV Converter

```python
from tools.converters import CSVConverter, Neo4jCSVConverter

converter = CSVConverter(
    delimiter=",",
    quotechar='"',
    include_headers=True
)

# Export
nodes_csv, edges_csv = converter.to_csv(graph)
converter.save(graph, "nodes.csv", "edges.csv")

# Import
graph = converter.from_csv(nodes_csv, edges_csv)
graph = converter.load("nodes.csv", "edges.csv")

# Neo4j-compatible format
neo4j = Neo4jCSVConverter()
nodes_csv, rels_csv = neo4j.to_neo4j_csv(graph)
```

### Cypher Converter

```python
from tools.converters import CypherConverter

converter = CypherConverter(use_labels=True, batch_size=1000)

# CREATE statements
cypher = converter.to_cypher(graph, mode="create")

# MERGE statements (idempotent)
cypher = converter.to_cypher(graph, mode="merge")

# Batched Cypher with UNWIND (efficient for large graphs)
cypher = converter.to_cypher_batch(graph, mode="merge")

# APOC-based import (best performance, requires APOC)
cypher = converter.to_cypher_apoc(graph, mode="merge")

# Save to file
converter.save(graph, "import.cypher", mode="merge")
converter.save_batch(graph, "import_batch.cypher", mode="merge")
```

### DOT/Graphviz Converter

```python
from tools.converters import DOTConverter

converter = DOTConverter(
    label_property="name",      # Property for node labels
    show_properties=False,      # Show all props in label
    rankdir="TB",               # Layout: TB, BT, LR, RL
    shapes={
        "person": "ellipse",
        "company": "box",
    },
    colors={
        "person": "#a8d5ba",
        "company": "#f4a460",
    }
)

# Generate DOT
dot = converter.to_dot(graph)

# Clustered DOT (groups nodes by type)
dot = converter.to_dot_clustered(graph)

# Save as files
converter.save(graph, "graph.dot")
converter.save_svg(graph, "graph.svg")    # Requires Graphviz
converter.save_png(graph, "graph.png")    # Requires Graphviz
```

---

## Schema Generator

Automatically generate ISONGraph schemas from JSON graph data by analyzing the structure and inferring types, constraints, and patterns.

### Features

- Type inference (string, int, float, bool)
- Constraint detection (min/max values, string lengths)
- Enum detection for low-cardinality fields
- Pattern recognition (email, URL, date, UUID)
- Multi-format output (Python, TypeScript, JSON, ISON)

### Quick Usage

```python
from tools.schema_generator import SchemaGenerator, generate_schema

# Sample graph data
data = {
    "nodes": [
        {"type": "person", "id": "1", "name": "Alice", "age": 30, "email": "alice@example.com"},
        {"type": "person", "id": "2", "name": "Bob", "age": 25, "email": "bob@example.com"},
        {"type": "company", "id": "acme", "name": "Acme Corp", "size": "large"}
    ],
    "edges": [
        {
            "rel_type": "WORKS_AT",
            "source": {"type": "person", "id": "1"},
            "target": {"type": "company", "id": "acme"},
            "properties": {"role": "Engineer"}
        }
    ]
}

# Generate schema
generator = SchemaGenerator(
    infer_constraints=True,
    infer_enums=True,
    infer_patterns=True
)
schema = generator.generate(data, name="organization")

# Output as Python code
print(generator.to_python(schema))

# Output as dictionary
print(generator.to_dict(schema))
```

### Schema Formatter

Generate schemas in multiple output formats:

```python
from tools.schema_generator import SchemaFormatter

# Python code for ison_graph.schema
python_code = SchemaFormatter.to_python(schema)

# TypeScript code for ison-graph-ts
ts_code = SchemaFormatter.to_typescript(schema)

# JSON Schema format
json_schema = SchemaFormatter.to_json(schema)

# ISON Schema format
ison_schema = SchemaFormatter.to_ison_schema(schema)
```

### Data Analyzer

Analyze graph data structure before generating schema:

```python
from tools.schema_generator import DataAnalyzer

analyzer = DataAnalyzer()
analyzer.analyze(data)

# Get statistics
node_stats = analyzer.get_node_stats()
edge_stats = analyzer.get_edge_stats()
summary = analyzer.summary()

print(f"Node types: {summary['node_type_names']}")
print(f"Edge types: {summary['edge_type_names']}")
print(f"Total nodes: {summary['total_nodes']}")
```

### Pattern Detection

The analyzer detects common string patterns:

| Pattern | Example |
|---------|---------|
| email | user@example.com |
| url | https://example.com |
| uuid | 550e8400-e29b-41d4-a716-446655440000 |
| date | 2024-01-15 |
| datetime | 2024-01-15T10:30:00 |
| phone | +1-555-123-4567 |

---

## Command Line Interface

### Convert Formats

```bash
# Convert JSON to ISON
ison-convert input.json output.ison

# Convert to GraphML
ison-convert graph.ison graph.graphml

# Convert to Cypher with MERGE
ison-convert graph.ison import.cypher --cypher-mode merge

# Convert to DOT with clustering
ison-convert graph.ison graph.dot --clustered

# Convert to RDF with custom URI
ison-convert graph.ison graph.ttl --base-uri https://myproject.org/
```

### Generate Schema

```bash
# Generate Python schema
python -m schema_generator graph.json -o schema.py

# Generate TypeScript schema
python -m schema_generator graph.json --format typescript -o schema.ts

# Generate JSON schema
python -m schema_generator graph.json --format json -o schema.json

# Analyze data structure
python -m schema_generator graph.json --analyze

# From stdin
cat graph.json | python -m schema_generator -
```

### Options

| Option | Description |
|--------|-------------|
| `--format` | Output format: python, typescript, json, ison |
| `--name` | Schema name |
| `--no-constraints` | Don't infer min/max constraints |
| `--no-enums` | Don't detect enum fields |
| `--strict` | Make all fields required |
| `--analyze` | Show data analysis only |

---

## Token Efficiency

ISON format provides significant token savings compared to other formats:

| Format | Tokens (relative) | Notes |
|--------|------------------|-------|
| JSON | 100% | Standard baseline |
| ISON | 31% | 69% savings |
| CSV | 40% | 60% savings |
| GraphML | 150% | XML overhead |
| Turtle | 80% | 20% savings |
| Cypher | 200% | Verbose statements |

When working with LLMs, use ISON format to fit more graph data in context windows.

---

## Integration Examples

### Export for Neo4j Import

```python
from tools.converters import CypherConverter
from ison_graph import ISONGraph

# Load your graph
graph = ISONGraph.load("data.ison")

# Generate efficient import script
converter = CypherConverter()
cypher = converter.to_cypher_batch(graph, mode="merge")

# Save and run in Neo4j
with open("import.cypher", "w") as f:
    f.write(cypher)
```

### Export for Visualization

```python
from tools.converters import DOTConverter

converter = DOTConverter(
    label_property="name",
    shapes={"person": "ellipse", "company": "box"},
    colors={"person": "#90EE90", "company": "#FFB6C1"}
)

# Generate SVG for web display
converter.save_svg(graph, "network.svg")

# Generate PNG for documents
converter.save_png(graph, "network.png")
```

### Generate Schema from Sample Data

```python
from tools.schema_generator import SchemaGenerator, SchemaFormatter
import json

# Load sample data
with open("sample_graph.json") as f:
    data = json.load(f)

# Generate schema
generator = SchemaGenerator()
schema = generator.generate(data, name="my_schema")

# Save Python schema
with open("my_schema.py", "w") as f:
    f.write(SchemaFormatter.to_python(schema))

# Save TypeScript schema
with open("my_schema.ts", "w") as f:
    f.write(SchemaFormatter.to_typescript(schema))
```

---

## License

MIT License - see [LICENSE](../LICENSE) for details.
