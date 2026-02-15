"""
Dependency Store - Library quirks and workarounds
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class DependencyStore(BaseStore):
    """
    Manages dependency quirk memory.

    Tracks:
    - External dependencies and versions
    - Undocumented quirks
    - Workarounds discovered
    - Agent's knowledge of workarounds
    """

    def add_dependency(
        self,
        name: str,
        version: str,
        category: str,
        stability: str = "stable"
    ) -> str:
        """Add an external dependency"""
        dep_id = self._make_id("dep", name)

        self.graph.add_node(
            "dependency",
            dep_id,
            name=name,
            version=version,
            category=category,
            stability=stability,
        )

        return dep_id

    def add_quirk(
        self,
        dependency_name: str,
        description: str,
        severity: str = "medium",
        documented: bool = False
    ) -> str:
        """Add a quirk for a dependency"""
        dep_id = self._make_id("dep", dependency_name)
        quirk_id = self._make_id("quirk", description[:30])

        self.graph.add_node(
            "quirk",
            quirk_id,
            dependency_id=dep_id,
            description=self._sanitize(description),
            severity=severity,
            documented=str(documented),
            discovered=self._now(),
        )

        if self.graph.has_node("dependency", dep_id):
            self.graph.add_edge(
                "HAS_QUIRK",
                ("dependency", dep_id),
                ("quirk", quirk_id)
            )

        return quirk_id

    def add_workaround(
        self,
        quirk_description: str,
        solution: str,
        performance_impact: str = "none",
        time_to_find: Optional[str] = None
    ) -> str:
        """Add a workaround for a quirk"""
        quirk_id = self._make_id("quirk", quirk_description[:30])
        work_id = self._make_id("work", solution[:30])

        self.graph.add_node(
            "workaround",
            work_id,
            quirk_id=quirk_id,
            solution=self._sanitize(solution),
            performance_impact=performance_impact,
            time_to_find=time_to_find or "",
        )

        if self.graph.has_node("quirk", quirk_id):
            self.graph.add_edge(
                "WORKAROUND_FOR",
                ("workaround", work_id),
                ("quirk", quirk_id)
            )

        return work_id

    def record_agent_knows(
        self,
        workaround_solution: str,
        confidence: float,
        times_applied: int = 0
    ) -> None:
        """Record that agent knows a workaround"""
        work_id = self._make_id("work", workaround_solution[:30])

        if self.graph.has_node("workaround", work_id):
            self.graph.add_edge(
                "AGENT_KNOWS",
                ("agent", "self"),
                ("workaround", work_id),
                confidence=str(confidence),
                times_applied=str(times_applied),
                last_applied=self._now()
            )

    def mark_upgrade_invalidates(
        self,
        dependency_name: str,
        new_version: str,
        workaround_solution: str,
        notes: str = ""
    ) -> None:
        """Mark that an upgrade might invalidate a workaround"""
        work_id = self._make_id("work", workaround_solution[:30])

        self.graph.add_edge(
            "UPGRADE_INVALIDATES",
            ("version", f"{dependency_name}>{new_version}"),
            ("workaround", work_id),
            check_version=new_version,
            notes=notes
        )

    def get_quirks_for_dependency(self, dep_name: str) -> List[Dict[str, Any]]:
        """Get all quirks and workarounds for a dependency"""
        dep_id = self._make_id("dep", dep_name)
        results = []

        for edge in self.graph.edges():
            if edge.rel_type == "HAS_QUIRK" and edge.source == ("dependency", dep_id):
                quirk = self.graph.get_node(*edge.target)
                if quirk:
                    # Find workaround
                    workaround = None
                    for e2 in self.graph.edges():
                        if e2.rel_type == "WORKAROUND_FOR" and e2.target == edge.target:
                            w = self.graph.get_node(*e2.source)
                            if w:
                                workaround = w.properties
                            break

                    results.append({
                        "quirk": quirk.properties,
                        "workaround": workaround,
                    })

        return results

    def get_workarounds_for_context(self, code: str) -> List[Dict[str, Any]]:
        """Find workarounds relevant to code being written"""
        results = []

        for node in self.graph.nodes():
            if node.type == "dependency":
                dep_name = node.properties.get("name", "")
                if dep_name and dep_name.lower() in code.lower():
                    quirks = self.get_quirks_for_dependency(dep_name)
                    for q in quirks:
                        results.append({
                            "type": "dependency_quirk",
                            "dependency": node.properties,
                            **q
                        })

        return results

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant dependency knowledge for context"""
        results = []

        # Check task description for dependency mentions
        task = context.get("task", "")
        if task:
            results.extend(self.get_workarounds_for_context(task))

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get dependency store statistics"""
        dependencies = 0
        quirks = 0
        workarounds = 0
        known = 0

        for node in self.graph.nodes():
            if node.type == "dependency":
                dependencies += 1
            elif node.type == "quirk":
                quirks += 1
            elif node.type == "workaround":
                workarounds += 1

        for edge in self.graph.edges():
            if edge.rel_type == "AGENT_KNOWS":
                known += 1

        return {
            "dependencies": dependencies,
            "quirks": quirks,
            "workarounds": workarounds,
            "agent_knows": known,
        }
