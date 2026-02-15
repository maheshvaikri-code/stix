# Code Flow Graph

Generate code flow graphs from GitHub repositories using ISONGraph.

## Installation

```bash
pip install code-flow-graph
```

## Usage

### Command Line

```bash
# Analyze a GitHub repository
cfg analyze https://github.com/user/repo

# Analyze a local directory
cfg analyze ./my-project -o graph.ison

# Specify output format
cfg analyze ./my-project -o graph.json -f json

# Analyze specific languages
cfg analyze ./my-project -l python

# Query a graph
cfg query graph.ison "MATCH (function) RETURN *"

# View graph statistics
cfg stats graph.ison

# Export for visualization
cfg export graph.ison -o graph.dot -f dot
cfg export graph.ison -o graph.md -f mermaid
```

### Python API

```python
from code_flow_graph import CodeFlowAnalyzer, analyze_github

# Quick analysis
graph = analyze_github("https://github.com/user/repo")

# Or use the analyzer class
analyzer = CodeFlowAnalyzer()
graph = analyzer.analyze_repo("https://github.com/user/repo")

# Analyze local code
graph = analyzer.analyze_path("./my-project")

# Get statistics
stats = analyzer.get_stats()
print(f"Found {stats['functions']} functions")

# Export
analyzer.export_ison("graph.ison")
analyzer.export_json("graph.json")
```

### Query the Graph

```python
from ison_graph.query import QueryEngine

engine = QueryEngine(graph)

# Find all functions that call a specific function
result = engine.execute("TRAVERSE function:main <- CALLS <- function")

# Find import chains
result = engine.execute("TRAVERSE file:app_py -> IMPORTS -> file MAX 5")

# Find class inheritance
result = engine.execute("MATCH (class)-[INHERITS]->(class) RETURN *")
```

## Graph Schema

### Node Types

| Type | Description |
|------|-------------|
| file | Source files |
| module | Packages/modules |
| class | Classes/structs/interfaces |
| function | Functions/methods |
| variable | Global variables/constants |

### Edge Types

| Type | Description |
|------|-------------|
| IMPORTS | File/module imports another |
| CALLS | Function calls another function |
| DEFINES | File/class defines a function/class |
| CONTAINS | Module contains file/submodule |
| INHERITS | Class extends/implements another |
| USES | Function uses a variable/type |
| RETURNS | Function returns a type |
| DECORATES | Decorator applied to function/class |

## Supported Languages

- Python (built-in)
- TypeScript/JavaScript (requires `tree-sitter` extras)
- Rust (requires `tree-sitter` extras)

Install language support:

```bash
pip install code-flow-graph[typescript]
pip install code-flow-graph[rust]
pip install code-flow-graph[all]
```

## License

MIT
