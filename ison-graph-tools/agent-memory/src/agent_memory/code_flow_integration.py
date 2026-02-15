"""
Code Flow Graph Integration
===========================

Integrates the code-flow-graph tool with agent-memory to provide
deep structural understanding of the codebase.

The code-flow-graph provides:
- Function call graphs
- Class hierarchies
- Import dependencies
- Module relationships

This feeds into agent-memory to:
- Enrich mental model with actual code structure
- Identify hot paths from call frequency
- Detect coupled modules
- Track function relationships for impact analysis
"""

import os
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .memory import AgentMemory


class CodeFlowIntegration:
    """
    Integrates code-flow-graph analysis with agent memory.

    Usage:
        from agent_memory import AgentMemory
        from agent_memory.code_flow_integration import CodeFlowIntegration

        memory = AgentMemory("my-project")
        flow = CodeFlowIntegration(memory)

        # Analyze codebase and enrich memory
        flow.analyze_and_enrich("/path/to/project")

        # Get call context for a function
        context = flow.get_function_context("src/api/handler.py", "handle_request")
    """

    def __init__(self, memory: "AgentMemory"):
        self.memory = memory
        self._code_graph = None

    def analyze_and_enrich(
        self,
        project_path: str,
        languages: Optional[List[str]] = None
    ) -> Dict[str, int]:
        """
        Analyze codebase with code-flow-graph and enrich memory.

        Args:
            project_path: Path to the project
            languages: Languages to analyze (default: auto-detect)

        Returns:
            Summary of what was enriched
        """
        try:
            from code_flow_graph import CodeFlowAnalyzer
        except ImportError:
            return {"error": "code-flow-graph not installed"}

        # Analyze the codebase
        analyzer = CodeFlowAnalyzer(name=f"{self.memory.name}-flow")
        self._code_graph = analyzer.analyze_path(project_path, languages=languages)

        summary = {
            "modules": 0,
            "functions": 0,
            "classes": 0,
            "calls": 0,
            "imports": 0,
        }

        # Enrich memory from code graph
        summary["modules"] = self._enrich_modules()
        summary["functions"] = self._enrich_functions()
        summary["classes"] = self._enrich_classes()
        summary["calls"] = self._enrich_call_graph()
        summary["imports"] = self._enrich_imports()

        return summary

    def _enrich_modules(self) -> int:
        """Enrich memory with module information from code graph"""
        count = 0

        for node in self._code_graph.nodes():
            if node.type == "file":
                path = node.properties.get("path", "")
                name = node.properties.get("name", "")

                # Add as module in memory
                self.memory.codebase.add_module(
                    path=path,
                    purpose=f"Source file: {name}",
                    complexity=self._estimate_complexity(node),
                    stability="stable"
                )
                count += 1

        return count

    def _enrich_functions(self) -> int:
        """Enrich memory with function information"""
        count = 0

        for node in self._code_graph.nodes():
            if node.type == "function":
                name = node.properties.get("name", "")
                path = node.properties.get("path", "")
                is_async = node.properties.get("is_async") == "True"

                # Track async functions for skill building
                if is_async:
                    self.memory.skills.update_proficiency("python_async", 0.0, examples_added=1)

                # Check if it's a hot path candidate (many callers)
                callers = self._count_callers(node)
                if callers > 5:
                    self.memory.performance.add_hot_path(
                        name=f"{path}:{name}",
                        frequency="high" if callers > 10 else "medium",
                        untouchable=callers > 20
                    )

                count += 1

        return count

    def _enrich_classes(self) -> int:
        """Enrich memory with class information"""
        count = 0

        for node in self._code_graph.nodes():
            if node.type == "class":
                name = node.properties.get("name", "")
                path = node.properties.get("path", "")
                is_abstract = node.properties.get("is_abstract") == "True"
                decorators = node.properties.get("decorators", "")

                # Detect patterns from class structure
                if is_abstract or "ABC" in decorators:
                    self.memory.codebase.add_pattern(
                        name="abstract_base",
                        modules=[path],
                        why_chosen="Detected abstract class"
                    )

                if "dataclass" in decorators:
                    self.memory.codebase.add_pattern(
                        name="dataclass",
                        modules=[path],
                        why_chosen="Using Python dataclasses"
                    )

                count += 1

        return count

    def _enrich_call_graph(self) -> int:
        """Enrich memory with call relationships"""
        count = 0

        # Build call frequency map
        call_counts = {}

        for edge in self._code_graph.edges():
            if edge.rel_type == "CALLS":
                target = edge.target
                target_key = f"{target[0]}:{target[1]}"
                call_counts[target_key] = call_counts.get(target_key, 0) + 1
                count += 1

        # Identify highly-called functions as potential hot paths
        for func_key, call_count in call_counts.items():
            if call_count > 3:
                parts = func_key.split(":")
                if len(parts) >= 2:
                    self.memory.performance.add_hot_path(
                        name=parts[1],
                        frequency="high" if call_count > 10 else "medium",
                        optimization_level="low"
                    )

        return count

    def _enrich_imports(self) -> int:
        """Enrich memory with import relationships"""
        count = 0

        # Track module dependencies
        for edge in self._code_graph.edges():
            if edge.rel_type == "IMPORTS":
                source = edge.source
                target = edge.target

                source_path = source[1] if len(source) > 1 else ""
                target_path = target[1] if len(target) > 1 else ""

                # Add dependency in codebase model
                self.memory.codebase.add_dependency(
                    from_module=source_path,
                    to_module=target_path,
                    coupling="import"
                )
                count += 1

        return count

    def _estimate_complexity(self, node) -> str:
        """Estimate complexity from node properties"""
        lines = 0
        try:
            start = int(node.properties.get("line_start", 0))
            end = int(node.properties.get("line_end", 0))
            lines = end - start
        except:
            pass

        if lines > 500:
            return "very_high"
        elif lines > 200:
            return "high"
        elif lines > 50:
            return "medium"
        return "low"

    def _count_callers(self, node) -> int:
        """Count how many functions call this one"""
        count = 0
        node_ref = (node.type, node.id)

        for edge in self._code_graph.edges():
            if edge.rel_type == "CALLS" and edge.target == node_ref:
                count += 1

        return count

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_function_context(self, file_path: str, function_name: str) -> Dict[str, Any]:
        """
        Get comprehensive context for a function.

        Returns:
        - What calls this function
        - What this function calls
        - Related classes
        - Potential impact of changes
        """
        if not self._code_graph:
            return {"error": "No code graph loaded. Call analyze_and_enrich first."}

        context = {
            "function": None,
            "callers": [],
            "callees": [],
            "parent_class": None,
            "impact_score": 0,
        }

        # Find the function node
        func_id = None
        for node in self._code_graph.nodes():
            if node.type == "function":
                if (node.properties.get("name") == function_name and
                    file_path in node.properties.get("path", "")):
                    context["function"] = node.properties
                    func_id = node.id
                    context["parent_class"] = node.properties.get("parent_class")
                    break

        if not func_id:
            return context

        # Find callers and callees
        for edge in self._code_graph.edges():
            if edge.rel_type == "CALLS":
                if edge.target == ("function", func_id):
                    caller = self._code_graph.get_node(*edge.source)
                    if caller:
                        context["callers"].append(caller.properties.get("name", ""))

                if edge.source == ("function", func_id):
                    callee = self._code_graph.get_node(*edge.target)
                    if callee:
                        context["callees"].append(callee.properties.get("name", ""))

        # Calculate impact score (how risky is it to change this function)
        context["impact_score"] = len(context["callers"]) * 2 + len(context["callees"])

        return context

    def get_module_dependencies(self, module_path: str) -> Dict[str, List[str]]:
        """
        Get import dependencies for a module.

        Returns:
        - imports: What this module imports
        - imported_by: What imports this module
        """
        if not self._code_graph:
            return {"error": "No code graph loaded"}

        result = {
            "imports": [],
            "imported_by": [],
        }

        # Find module node ID
        module_id = None
        for node in self._code_graph.nodes():
            if node.type == "file":
                if module_path in node.properties.get("path", ""):
                    module_id = node.id
                    break

        if not module_id:
            return result

        for edge in self._code_graph.edges():
            if edge.rel_type == "IMPORTS":
                if edge.source == ("file", module_id):
                    target = self._code_graph.get_node(*edge.target)
                    if target:
                        result["imports"].append(target.properties.get("path", ""))

                if edge.target == ("file", module_id):
                    source = self._code_graph.get_node(*edge.source)
                    if source:
                        result["imported_by"].append(source.properties.get("path", ""))

        return result

    def get_class_hierarchy(self, class_name: str) -> Dict[str, Any]:
        """
        Get class inheritance hierarchy.

        Returns:
        - class: The class info
        - bases: Parent classes
        - subclasses: Child classes
        - methods: Methods defined in this class
        """
        if not self._code_graph:
            return {"error": "No code graph loaded"}

        result = {
            "class": None,
            "bases": [],
            "subclasses": [],
            "methods": [],
        }

        # Find the class node
        class_id = None
        for node in self._code_graph.nodes():
            if node.type == "class" and node.properties.get("name") == class_name:
                result["class"] = node.properties
                class_id = node.id
                break

        if not class_id:
            return result

        # Find inheritance relationships
        for edge in self._code_graph.edges():
            if edge.rel_type == "INHERITS":
                if edge.source == ("class", class_id):
                    parent = self._code_graph.get_node(*edge.target)
                    if parent:
                        result["bases"].append(parent.properties.get("name", ""))

                if edge.target == ("class", class_id):
                    child = self._code_graph.get_node(*edge.source)
                    if child:
                        result["subclasses"].append(child.properties.get("name", ""))

        # Find methods
        for edge in self._code_graph.edges():
            if edge.rel_type == "DEFINES" and edge.source == ("class", class_id):
                method = self._code_graph.get_node(*edge.target)
                if method and method.type == "function":
                    result["methods"].append(method.properties.get("name", ""))

        return result

    def find_impact(self, file_path: str) -> Dict[str, Any]:
        """
        Find the potential impact of changing a file.

        Returns:
        - files_affected: Files that depend on this file
        - functions_affected: Functions that call functions in this file
        - risk_level: low, medium, high, critical
        """
        if not self._code_graph:
            return {"error": "No code graph loaded"}

        result = {
            "files_affected": [],
            "functions_affected": 0,
            "risk_level": "low",
        }

        # Get modules that import this file
        deps = self.get_module_dependencies(file_path)
        result["files_affected"] = deps.get("imported_by", [])

        # Count functions that call functions in this file
        file_functions = set()
        for node in self._code_graph.nodes():
            if node.type == "function" and file_path in node.properties.get("path", ""):
                file_functions.add(node.id)

        for edge in self._code_graph.edges():
            if edge.rel_type == "CALLS":
                if edge.target[1] in file_functions:
                    result["functions_affected"] += 1

        # Determine risk level
        total_impact = len(result["files_affected"]) + result["functions_affected"]
        if total_impact > 20:
            result["risk_level"] = "critical"
        elif total_impact > 10:
            result["risk_level"] = "high"
        elif total_impact > 3:
            result["risk_level"] = "medium"

        return result


def enrich_memory_with_code_flow(
    memory: "AgentMemory",
    project_path: str,
    languages: Optional[List[str]] = None
) -> Dict[str, int]:
    """
    Convenience function to enrich memory with code flow analysis.

    Args:
        memory: AgentMemory instance
        project_path: Path to project
        languages: Languages to analyze

    Returns:
        Summary of enrichment
    """
    integration = CodeFlowIntegration(memory)
    return integration.analyze_and_enrich(project_path, languages)
