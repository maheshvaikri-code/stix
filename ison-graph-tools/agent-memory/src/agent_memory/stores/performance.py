"""
Performance Store - Performance characteristics and constraints
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class PerformanceStore(BaseStore):
    """
    Manages performance memory.

    Tracks:
    - Performance baselines
    - Hot paths
    - Known bottlenecks
    - Regression history
    """

    def add_baseline(
        self,
        operation: str,
        p50_ms: float,
        p99_ms: float,
        throughput: str
    ) -> str:
        """Add a performance baseline"""
        base_id = self._make_id("pb", operation[:30])

        self.graph.add_node(
            "performance_baseline",
            base_id,
            operation=operation,
            p50_ms=str(p50_ms),
            p99_ms=str(p99_ms),
            throughput=throughput,
            measured_at=self._now(),
        )

        return base_id

    def add_hot_path(
        self,
        name: str,
        frequency: str,
        optimization_level: str = "low",
        untouchable: bool = False
    ) -> str:
        """Add a hot path"""
        hp_id = self._make_id("hp", name)

        self.graph.add_node(
            "hot_path",
            hp_id,
            name=name,
            frequency=frequency,
            optimization_level=optimization_level,
            untouchable=str(untouchable),
        )

        return hp_id

    def add_constraint(
        self,
        operation: str,
        constraint: str,
        reason: str
    ) -> str:
        """Add a performance constraint"""
        const_id = self._make_id("pc", operation[:20])

        self.graph.add_node(
            "performance_constraint",
            const_id,
            operation=operation,
            constraint=constraint,
            reason=self._sanitize(reason),
        )

        return const_id

    def add_bottleneck(
        self,
        location: str,
        cause: str,
        mitigation: Optional[str] = None
    ) -> str:
        """Add a known bottleneck"""
        bn_id = self._make_id("bn", location[:30])

        self.graph.add_node(
            "bottleneck",
            bn_id,
            location=location,
            cause=self._sanitize(cause),
            mitigation=self._sanitize(mitigation or ""),
        )

        return bn_id

    def record_optimization_attempt(
        self,
        hot_path_name: str,
        technique: str,
        result: str,
        kept: bool
    ) -> None:
        """Record an optimization attempt"""
        hp_id = self._make_id("hp", hot_path_name)

        if self.graph.has_node("hot_path", hp_id):
            self.graph.add_edge(
                "OPTIMIZATION_ATTEMPTED",
                ("hot_path", hp_id),
                ("technique", technique),
                technique=technique,
                result=result,
                kept=str(kept),
                when=self._now()
            )

    def record_regression(
        self,
        baseline_operation: str,
        change: str,
        detected_by: str
    ) -> None:
        """Record a performance regression"""
        base_id = self._make_id("pb", baseline_operation[:30])

        self.graph.add_edge(
            "REGRESSION_HISTORY",
            ("agent", "self"),
            ("performance_baseline", base_id),
            when=self._now(),
            change=self._sanitize(change),
            detected_by=detected_by
        )

    def get_hot_paths(self) -> List[Dict[str, Any]]:
        """Get all hot paths"""
        return [
            {"id": node.id, **node.properties}
            for node in self.graph.nodes()
            if node.type == "hot_path"
        ]

    def get_constraints_for_operation(self, operation: str) -> List[Dict[str, Any]]:
        """Get performance constraints for an operation"""
        constraints = []

        for node in self.graph.nodes():
            if node.type == "performance_constraint":
                if operation in node.properties.get("operation", ""):
                    constraints.append(node.properties)

        return constraints

    def check_hot_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Check if file contains a hot path"""
        for node in self.graph.nodes():
            if node.type == "hot_path":
                # Simple check - in real implementation would use code analysis
                if node.properties.get("untouchable") == "True":
                    return {
                        "warning": "This file may contain an untouchable hot path",
                        "hot_path": node.properties
                    }
        return None

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant performance info for context"""
        results = []

        files = context.get("files", [])
        for file_path in files:
            warning = self.check_hot_path(file_path)
            if warning:
                results.append({
                    "type": "hot_path_warning",
                    "file": file_path,
                    **warning
                })

        # Add general hot paths
        for hp in self.get_hot_paths():
            if hp.get("untouchable") == "True":
                results.append({
                    "type": "hot_path",
                    **hp
                })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get performance store statistics"""
        baselines = 0
        hot_paths = 0
        constraints = 0
        bottlenecks = 0
        regressions = 0

        for node in self.graph.nodes():
            if node.type == "performance_baseline":
                baselines += 1
            elif node.type == "hot_path":
                hot_paths += 1
            elif node.type == "performance_constraint":
                constraints += 1
            elif node.type == "bottleneck":
                bottlenecks += 1

        for edge in self.graph.edges():
            if edge.rel_type == "REGRESSION_HISTORY":
                regressions += 1

        return {
            "baselines": baselines,
            "hot_paths": hot_paths,
            "constraints": constraints,
            "bottlenecks": bottlenecks,
            "regressions": regressions,
        }
