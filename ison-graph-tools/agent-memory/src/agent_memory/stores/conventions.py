"""
Convention Store - Code style and project patterns
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class ConventionStore(BaseStore):
    """
    Manages code convention memory.

    Tracks:
    - Naming conventions
    - Code idioms
    - Project-specific patterns
    - Agent's learning and violations
    """

    def add_convention(
        self,
        category: str,
        rule: str,
        enforced_by: str = "manual",
        exceptions: Optional[List[str]] = None,
        applies_to: str = "*"
    ) -> str:
        """Add a code convention"""
        conv_id = self._make_id("conv", f"{category}_{rule[:20]}")

        self.graph.add_node(
            "convention",
            conv_id,
            category=category,
            rule=self._sanitize(rule),
            enforced_by=enforced_by,
            exceptions=",".join(exceptions or []),
            applies_to=applies_to,
        )

        return conv_id

    def add_idiom(
        self,
        pattern: str,
        preferred_form: str,
        avoid: str
    ) -> str:
        """Add a code idiom"""
        idiom_id = self._make_id("idiom", pattern[:30])

        self.graph.add_node(
            "idiom",
            idiom_id,
            pattern=pattern,
            preferred_form=self._sanitize(preferred_form),
            avoid=self._sanitize(avoid),
        )

        return idiom_id

    def add_project_pattern(
        self,
        name: str,
        template: str,
        usage_context: str
    ) -> str:
        """Add a project-specific pattern"""
        pattern_id = self._make_id("proj_pattern", name)

        self.graph.add_node(
            "project_pattern",
            pattern_id,
            name=name,
            template=self._sanitize(template),
            usage_context=self._sanitize(usage_context),
        )

        return pattern_id

    def record_learning(
        self,
        convention_id: str,
        examples_seen: int,
        confidence: float
    ) -> None:
        """Record agent learning a convention"""
        self.graph.add_edge(
            "LEARNED_FROM",
            ("agent", "self"),
            ("convention", convention_id),
            examples_seen=str(examples_seen),
            confidence=str(confidence),
            last_reinforced=self._now()
        )

    def record_violation(
        self,
        convention_id: str,
        pattern: str
    ) -> None:
        """Record a convention violation"""
        # Get existing violation count
        count = 1
        for edge in self.graph.edges():
            if (edge.rel_type == "VIOLATION_HISTORY" and
                edge.source == ("agent", "self") and
                edge.target == ("convention", convention_id)):
                count = int(edge.properties.get("count", 0)) + 1
                break

        self.graph.add_edge(
            "VIOLATION_HISTORY",
            ("agent", "self"),
            ("convention", convention_id),
            count=str(count),
            last_occurred=self._now(),
            pattern=pattern
        )

    def get_conventions_for_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Get conventions that apply to a file"""
        conventions = []

        for node in self.graph.nodes():
            if node.type == "convention":
                applies_to = node.properties.get("applies_to", "*")
                # Simple pattern matching
                if applies_to == "*" or applies_to in file_path:
                    conventions.append({
                        "id": node.id,
                        **node.properties
                    })

        return conventions

    def get_idioms(self) -> List[Dict[str, Any]]:
        """Get all idioms"""
        return [
            {"id": node.id, **node.properties}
            for node in self.graph.nodes()
            if node.type == "idiom"
        ]

    def get_project_patterns(self) -> List[Dict[str, Any]]:
        """Get all project patterns"""
        return [
            {"id": node.id, **node.properties}
            for node in self.graph.nodes()
            if node.type == "project_pattern"
        ]

    def get_violation_history(self) -> List[Dict[str, Any]]:
        """Get agent's violation history"""
        violations = []

        for edge in self.graph.edges():
            if edge.rel_type == "VIOLATION_HISTORY" and edge.source == ("agent", "self"):
                conv = self.graph.get_node(*edge.target)
                if conv:
                    violations.append({
                        "convention": conv.properties,
                        **edge.properties
                    })

        return sorted(violations, key=lambda x: int(x.get("count", 0)), reverse=True)

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant conventions for context"""
        results = []

        # Get conventions for files being modified
        files = context.get("files", [])
        for file_path in files:
            convs = self.get_conventions_for_file(file_path)
            for conv in convs:
                results.append({
                    "type": "convention",
                    "file": file_path,
                    **conv
                })

        # Always include idioms and patterns
        for idiom in self.get_idioms():
            results.append({
                "type": "idiom",
                **idiom
            })

        for pattern in self.get_project_patterns():
            results.append({
                "type": "project_pattern",
                **pattern
            })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get convention store statistics"""
        conventions = 0
        idioms = 0
        patterns = 0
        violations = 0

        for node in self.graph.nodes():
            if node.type == "convention":
                conventions += 1
            elif node.type == "idiom":
                idioms += 1
            elif node.type == "project_pattern":
                patterns += 1

        for edge in self.graph.edges():
            if edge.rel_type == "VIOLATION_HISTORY":
                violations += int(edge.properties.get("count", 1))

        return {
            "conventions": conventions,
            "idioms": idioms,
            "patterns": patterns,
            "total_violations": violations,
        }
