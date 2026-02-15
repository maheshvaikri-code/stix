"""
Code Flow Graph - Generate code flow graphs from GitHub repositories using ISONGraph

This tool analyzes source code repositories and creates a property graph
representing the code structure and relationships:

- Files, classes, functions, modules as nodes
- Imports, calls, definitions, inheritance as edges

Usage:
    from code_flow_graph import CodeFlowAnalyzer

    analyzer = CodeFlowAnalyzer()
    graph = analyzer.analyze_repo("https://github.com/user/repo")

    # Query the graph
    from ison_graph.query import QueryEngine
    engine = QueryEngine(graph)

    # Find what calls a function
    result = engine.execute("TRAVERSE function:main <- CALLS <- function")

    # Find import chain
    result = engine.execute("TRAVERSE file:main.py -> IMPORTS -> file MAX 5")

Author: Mahesh Vaikri
"""

__version__ = "1.0.0"

from .analyzer import CodeFlowAnalyzer, analyze_github, analyze_local
from .graph_builder import CodeFlowGraphBuilder
from .github_loader import GitHubLoader

__all__ = [
    "__version__",
    "CodeFlowAnalyzer",
    "CodeFlowGraphBuilder",
    "GitHubLoader",
    "analyze_github",
    "analyze_local",
]
