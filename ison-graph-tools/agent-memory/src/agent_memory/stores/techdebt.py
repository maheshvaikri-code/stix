"""
Tech Debt Store - Technical debt and refactoring history
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class TechDebtStore(BaseStore):
    """
    Manages technical debt memory.

    Tracks:
    - Technical debt items
    - Past refactoring attempts
    - Planned refactoring
    - Blockers and dependencies
    """

    def add_debt(
        self,
        location: str,
        description: str,
        severity: str = "medium",
        caused_by: Optional[str] = None
    ) -> str:
        """Add a technical debt item"""
        debt_id = self._make_id("td", location[:30])

        self.graph.add_node(
            "tech_debt",
            debt_id,
            location=location,
            description=self._sanitize(description),
            severity=severity,
            caused_by=caused_by or "",
            age_days="0",
            added=self._now(),
        )

        return debt_id

    def add_refactoring_attempt(
        self,
        debt_location: str,
        approach: str,
        outcome: str,
        reason_failed: Optional[str] = None
    ) -> str:
        """Record a refactoring attempt"""
        debt_id = self._make_id("td", debt_location[:30])
        attempt_id = self._make_id("ra", f"{debt_location[:15]}_{approach[:15]}")

        self.graph.add_node(
            "refactoring_attempt",
            attempt_id,
            debt_id=debt_id,
            when=self._now(),
            approach=self._sanitize(approach),
            outcome=outcome,
            reason_failed=self._sanitize(reason_failed or ""),
        )

        if self.graph.has_node("tech_debt", debt_id):
            self.graph.add_edge(
                "ATTEMPTED_ON",
                ("refactoring_attempt", attempt_id),
                ("tech_debt", debt_id)
            )

        return attempt_id

    def add_planned_refactoring(
        self,
        debt_location: str,
        approach: str,
        priority: str = "medium",
        blocked_by: Optional[str] = None
    ) -> str:
        """Add a planned refactoring"""
        debt_id = self._make_id("td", debt_location[:30])
        plan_id = self._make_id("pr", debt_location[:30])

        self.graph.add_node(
            "planned_refactoring",
            plan_id,
            debt_id=debt_id,
            approach=self._sanitize(approach),
            priority=priority,
            blocked_by=blocked_by or "",
        )

        return plan_id

    def add_blocker(
        self,
        blocked_debt: str,
        blocking_debt: str,
        reason: str
    ) -> None:
        """Record that one debt blocks another's resolution"""
        blocked_id = self._make_id("td", blocked_debt[:30])
        blocking_id = self._make_id("td", blocking_debt[:30])

        if (self.graph.has_node("tech_debt", blocked_id) and
            self.graph.has_node("tech_debt", blocking_id)):
            self.graph.add_edge(
                "BLOCKED_BY",
                ("tech_debt", blocked_id),
                ("tech_debt", blocking_id),
                reason=self._sanitize(reason)
            )

    def record_agent_suggestion(
        self,
        debt_location: str,
        suggestion: str,
        response: str
    ) -> None:
        """Record when agent suggests already-tried approach"""
        debt_id = self._make_id("td", debt_location[:30])

        if self.graph.has_node("tech_debt", debt_id):
            self.graph.add_edge(
                "AGENT_SUGGESTED",
                ("agent", "self"),
                ("tech_debt", debt_id),
                when=self._now(),
                suggestion=self._sanitize(suggestion),
                response=self._sanitize(response)
            )

    def get_debt_by_severity(self, severity: str) -> List[Dict[str, Any]]:
        """Get all debt items of a severity"""
        return [
            {"id": node.id, **node.properties}
            for node in self.graph.nodes()
            if node.type == "tech_debt" and node.properties.get("severity") == severity
        ]

    def get_failed_attempts(self, debt_location: str) -> List[Dict[str, Any]]:
        """Get failed refactoring attempts for a debt item"""
        debt_id = self._make_id("td", debt_location[:30])
        attempts = []

        for edge in self.graph.edges():
            if edge.rel_type == "ATTEMPTED_ON" and edge.target == ("tech_debt", debt_id):
                attempt = self.graph.get_node(*edge.source)
                if attempt and attempt.properties.get("outcome") == "failed":
                    attempts.append(attempt.properties)

        return attempts

    def check_suggestion(self, debt_location: str, suggestion: str) -> Optional[Dict[str, Any]]:
        """Check if suggestion was already tried and failed"""
        failed = self.get_failed_attempts(debt_location)
        suggestion_lower = suggestion.lower()

        for attempt in failed:
            approach = attempt.get("approach", "").lower()
            if approach and approach in suggestion_lower:
                return {
                    "warning": "This approach was already tried and failed",
                    "attempt": attempt
                }

        return None

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant tech debt info for context"""
        results = []

        files = context.get("files", [])
        for file_path in files:
            # Find debt in this file
            for node in self.graph.nodes():
                if node.type == "tech_debt":
                    if file_path in node.properties.get("location", ""):
                        failed = self.get_failed_attempts(node.properties["location"])
                        results.append({
                            "type": "tech_debt",
                            "file": file_path,
                            "debt": node.properties,
                            "failed_attempts": failed
                        })

        # Check task for refactoring suggestions
        task = context.get("task", "")
        if "refactor" in task.lower():
            for file_path in files:
                warning = self.check_suggestion(file_path, task)
                if warning:
                    results.append({
                        "type": "refactoring_warning",
                        "file": file_path,
                        **warning
                    })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get tech debt store statistics"""
        debt_items = 0
        attempts = 0
        planned = 0
        failed = 0

        for node in self.graph.nodes():
            if node.type == "tech_debt":
                debt_items += 1
            elif node.type == "refactoring_attempt":
                attempts += 1
                if node.properties.get("outcome") == "failed":
                    failed += 1
            elif node.type == "planned_refactoring":
                planned += 1

        return {
            "debt_items": debt_items,
            "attempts": attempts,
            "failed": failed,
            "planned": planned,
        }
