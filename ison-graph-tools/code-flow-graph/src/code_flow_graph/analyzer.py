"""
Code Flow Analyzer - Main entry point for code analysis
"""

import os
from typing import Dict, List, Optional, Any

from ison_graph import ISONGraph

from .graph_builder import (
    CodeFlowGraphBuilder,
    FileElement,
    ClassElement,
    FunctionElement,
    VariableElement,
)
from .github_loader import GitHubLoader, is_github_url
from .parsers.python_parser import PythonParser


class CodeFlowAnalyzer:
    """
    Analyzes code repositories and generates flow graphs.

    Usage:
        analyzer = CodeFlowAnalyzer()

        # Analyze a GitHub repo
        graph = analyzer.analyze_repo("https://github.com/user/repo")

        # Analyze a local directory
        graph = analyzer.analyze_path("/path/to/code")

        # Query the graph
        from ison_graph.query import QueryEngine
        engine = QueryEngine(graph)
        result = engine.execute("TRAVERSE function:main <- CALLS <- function")
    """

    def __init__(self, name: str = "code-flow"):
        self.name = name
        self.builder = CodeFlowGraphBuilder(name)
        self.loader = GitHubLoader()

        # Language parsers
        self._parsers = {
            "python": PythonParser(),
        }

    def analyze_repo(
        self,
        url: str,
        branch: Optional[str] = None,
        languages: Optional[List[str]] = None,
    ) -> ISONGraph:
        """
        Analyze a GitHub repository.

        Args:
            url: GitHub repository URL
            branch: Specific branch to analyze
            languages: List of languages to analyze. If None, analyzes all supported languages.

        Returns:
            ISONGraph containing the code flow graph
        """
        if not is_github_url(url):
            raise ValueError(f"Not a valid GitHub URL: {url}")

        # Clone the repository
        repo_path = self.loader.clone(url, branch=branch)

        try:
            return self.analyze_path(repo_path, languages=languages)
        finally:
            self.loader.cleanup()

    def analyze_path(
        self,
        path: str,
        languages: Optional[List[str]] = None,
    ) -> ISONGraph:
        """
        Analyze a local directory.

        Args:
            path: Path to the directory
            languages: List of languages to analyze. If None, analyzes all supported languages.

        Returns:
            ISONGraph containing the code flow graph
        """
        if not os.path.exists(path):
            raise ValueError(f"Path does not exist: {path}")

        # Reset builder for fresh analysis
        self.builder = CodeFlowGraphBuilder(self.name)

        # Determine languages to analyze
        if languages is None:
            languages = list(self._parsers.keys())

        # Analyze each language
        for lang in languages:
            if lang in self._parsers:
                self._analyze_language(path, lang)

        return self.builder.build()

    def _analyze_language(self, path: str, language: str) -> None:
        """Analyze files of a specific language"""
        parser = self._parsers.get(language)
        if not parser:
            return

        if language == "python":
            self._analyze_python(path, parser)

    def _analyze_python(self, path: str, parser: PythonParser) -> None:
        """Analyze Python files in a directory"""
        file_elements, code_elements = parser.parse_directory(path)

        # Add file nodes
        for file_elem in file_elements:
            self.builder.add_file(file_elem)

        # Add other elements
        for elem in code_elements:
            if isinstance(elem, ClassElement):
                self.builder.add_class(elem, parent_file=elem.file_path)
            elif isinstance(elem, FunctionElement):
                self.builder.add_function(elem, parent_file=elem.file_path)
            elif isinstance(elem, VariableElement):
                self.builder.add_variable(elem, parent=elem.file_path)

    def get_stats(self) -> Dict[str, int]:
        """Get analysis statistics"""
        return self.builder.get_stats()

    def export_ison(self, output_path: str) -> None:
        """Export the graph to ISON format"""
        graph = self.builder.build()
        graph.save(output_path)

    def export_json(self, output_path: str) -> None:
        """Export the graph to JSON format"""
        import json
        graph = self.builder.build()
        data = {
            "name": graph.name,
            "nodes": [
                {"type": n.type, "id": n.id, "properties": dict(n.properties)}
                for n in graph.nodes()
            ],
            "edges": [
                {
                    "rel_type": e.rel_type,
                    "source": {"type": e.source[0], "id": e.source[1]},
                    "target": {"type": e.target[0], "id": e.target[1]},
                    "properties": dict(e.properties),
                }
                for e in graph.edges()
            ],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def analyze_github(
    url: str,
    branch: Optional[str] = None,
    languages: Optional[List[str]] = None,
    name: str = "code-flow",
) -> ISONGraph:
    """
    Convenience function to analyze a GitHub repository.

    Args:
        url: GitHub repository URL
        branch: Specific branch to analyze
        languages: List of languages to analyze
        name: Name for the graph

    Returns:
        ISONGraph containing the code flow graph
    """
    analyzer = CodeFlowAnalyzer(name=name)
    return analyzer.analyze_repo(url, branch=branch, languages=languages)


def analyze_local(
    path: str,
    languages: Optional[List[str]] = None,
    name: str = "code-flow",
) -> ISONGraph:
    """
    Convenience function to analyze a local directory.

    Args:
        path: Path to the directory
        languages: List of languages to analyze
        name: Name for the graph

    Returns:
        ISONGraph containing the code flow graph
    """
    analyzer = CodeFlowAnalyzer(name=name)
    return analyzer.analyze_path(path, languages=languages)
