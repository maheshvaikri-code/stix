"""
Mistake Store
=============

Stores and analyzes agent mistakes for corrective learning.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
import math

from .base import BaseLearningStore
from ..schema import (
    MistakeCategory,
    MistakeSeverity,
    MISTAKE_SEVERITY_WEIGHTS,
)


class MistakeStore(BaseLearningStore):
    """
    Store for agent mistakes and corrections.

    Provides:
    - Mistake recording with full context
    - Root cause analysis
    - Pattern detection across mistakes
    - Correction tracking
    - Prevention strategy generation
    """

    def __init__(self, graph):
        super().__init__(graph, "mistake")

    # =========================================================================
    # Mistake Recording
    # =========================================================================

    def record_mistake(
        self,
        agent_id: str,
        category: MistakeCategory,
        severity: MistakeSeverity,
        task_context: str,
        agent_action: str,
        expected_action: str,
        actual_outcome: str,
        expected_outcome: str,
        root_cause: str,
        contributing_factors: Optional[List[str]] = None,
        correction_applied: str = "",
        corrected_by: str = "",
    ) -> str:
        """Record a new mistake."""
        mistake_id = self._generate_id("mistake")

        self._add_node("mistake", mistake_id, {
            "agent_id": agent_id,
            "category": category.value if isinstance(category, MistakeCategory) else category,
            "severity": severity.value if isinstance(severity, MistakeSeverity) else severity,
            "task_context": task_context,
            "agent_action": agent_action,
            "expected_action": expected_action,
            "actual_outcome": actual_outcome,
            "expected_outcome": expected_outcome,
            "root_cause": root_cause,
            "contributing_factors": contributing_factors or [],
            "correction_applied": correction_applied,
            "corrected_by": corrected_by,
            "correction_verified": False,
            "lesson_learned": "",
            "prevention_strategy": "",
            "recurrence_count": 0,
            "last_recurrence": None,
        })

        # Check for similar mistakes and link
        similar = self._find_similar_mistakes(agent_id, category, root_cause)
        for sim_id in similar[:3]:  # Link to top 3 similar
            self._add_edge(
                "mistake", mistake_id,
                "SIMILAR_TO",
                "mistake", sim_id,
                {}
            )

        # Check for pattern
        self._check_for_pattern(agent_id, category, root_cause)

        return mistake_id

    def _find_similar_mistakes(
        self,
        agent_id: str,
        category: MistakeCategory,
        root_cause: str,
    ) -> List[str]:
        """Find similar past mistakes."""
        category_val = category.value if isinstance(category, MistakeCategory) else category
        mistakes = self._find_nodes("mistake", agent_id=agent_id, category=category_val)

        # Score similarity
        similar = []
        for m in mistakes:
            if m.get("root_cause") == root_cause:
                similar.append((m.get("id"), 1.0))
            elif root_cause.lower() in m.get("root_cause", "").lower():
                similar.append((m.get("id"), 0.7))

        similar.sort(key=lambda x: x[1], reverse=True)
        return [s[0] for s in similar]

    def _check_for_pattern(
        self,
        agent_id: str,
        category: MistakeCategory,
        root_cause: str,
    ) -> Optional[str]:
        """Check if this mistake forms a pattern."""
        category_val = category.value if isinstance(category, MistakeCategory) else category
        mistakes = self._find_nodes("mistake", agent_id=agent_id, category=category_val)

        # Group by root cause
        root_cause_counts = {}
        for m in mistakes:
            rc = m.get("root_cause", "")
            root_cause_counts[rc] = root_cause_counts.get(rc, 0) + 1

        # If 3+ mistakes with similar root cause, create pattern
        if root_cause_counts.get(root_cause, 0) >= 3:
            return self._create_pattern(agent_id, category, root_cause, root_cause_counts[root_cause])

        return None

    def _create_pattern(
        self,
        agent_id: str,
        category: MistakeCategory,
        root_cause: str,
        frequency: int,
    ) -> str:
        """Create a mistake pattern."""
        category_val = category.value if isinstance(category, MistakeCategory) else category

        # Check if pattern already exists
        existing = self._find_nodes(
            "mistake_pattern",
            agent_id=agent_id,
            category=category_val,
            root_cause=root_cause
        )
        if existing:
            # Update frequency
            pattern = existing[0]
            self._update_node("mistake_pattern", pattern["id"], {
                "frequency": frequency,
                "last_seen": self._now(),
            })
            return pattern["id"]

        pattern_id = self._generate_id("mistake_pattern")

        self._add_node("mistake_pattern", pattern_id, {
            "agent_id": agent_id,
            "name": f"{category_val}_{root_cause[:30]}",
            "category": category_val,
            "root_cause": root_cause,
            "frequency": frequency,
            "recency_weighted_score": frequency,  # Will be updated
            "last_seen": self._now(),
            "prevention_strategies": [],
            "mitigation_applied": False,
        })

        return pattern_id

    def get_mistake(self, mistake_id: str) -> Optional[Dict[str, Any]]:
        """Get a mistake by ID."""
        return self._get_node("mistake", mistake_id)

    # =========================================================================
    # Correction Management
    # =========================================================================

    def apply_correction(
        self,
        mistake_id: str,
        correction: str,
        corrected_by: str,
        lesson_learned: str,
        prevention_strategy: str,
    ) -> Dict[str, Any]:
        """Apply a correction to a mistake."""
        mistake = self._get_node("mistake", mistake_id)
        if not mistake:
            return {"error": "Mistake not found"}

        self._update_node("mistake", mistake_id, {
            "correction_applied": correction,
            "corrected_by": corrected_by,
            "lesson_learned": lesson_learned,
            "prevention_strategy": prevention_strategy,
            "corrected_at": self._now(),
        })

        return {
            "corrected": True,
            "mistake_id": mistake_id,
            "lesson_learned": lesson_learned,
        }

    def verify_correction(
        self,
        mistake_id: str,
        verified_by: str,
        verification_notes: str = "",
    ) -> Dict[str, Any]:
        """Verify that a correction was effective."""
        mistake = self._get_node("mistake", mistake_id)
        if not mistake:
            return {"error": "Mistake not found"}

        self._update_node("mistake", mistake_id, {
            "correction_verified": True,
            "verified_by": verified_by,
            "verified_at": self._now(),
            "verification_notes": verification_notes,
        })

        return {"verified": True, "mistake_id": mistake_id}

    def record_recurrence(
        self,
        original_mistake_id: str,
        new_context: str,
    ) -> Dict[str, Any]:
        """Record that a similar mistake recurred."""
        mistake = self._get_node("mistake", original_mistake_id)
        if not mistake:
            return {"error": "Original mistake not found"}

        recurrence_count = mistake.get("recurrence_count", 0) + 1

        self._update_node("mistake", original_mistake_id, {
            "recurrence_count": recurrence_count,
            "last_recurrence": self._now(),
            "last_recurrence_context": new_context,
        })

        # This indicates prevention strategy isn't working
        if recurrence_count >= 3:
            return {
                "recorded": True,
                "recurrence_count": recurrence_count,
                "warning": "Prevention strategy may be ineffective",
                "requires_retraining": True,
            }

        return {"recorded": True, "recurrence_count": recurrence_count}

    # =========================================================================
    # Analysis
    # =========================================================================

    def get_mistakes_by_category(
        self,
        agent_id: str,
        category: MistakeCategory,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get mistakes by category."""
        category_val = category.value if isinstance(category, MistakeCategory) else category
        mistakes = self._find_nodes("mistake", agent_id=agent_id, category=category_val)

        mistakes.sort(key=lambda x: x.get("_created_at", ""), reverse=True)
        return mistakes[:limit]

    def get_mistakes_by_severity(
        self,
        agent_id: str,
        min_severity: MistakeSeverity = MistakeSeverity.MEDIUM,
    ) -> List[Dict[str, Any]]:
        """Get mistakes at or above a severity level."""
        mistakes = self._find_nodes("mistake", agent_id=agent_id)

        severity_order = [s.value for s in MistakeSeverity]
        min_idx = severity_order.index(min_severity.value if isinstance(min_severity, MistakeSeverity) else min_severity)

        filtered = []
        for m in mistakes:
            sev = m.get("severity")
            if sev in severity_order[:min_idx + 1]:
                filtered.append(m)

        return filtered

    def get_unresolved_mistakes(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get mistakes without corrections or unverified corrections."""
        mistakes = self._find_nodes("mistake", agent_id=agent_id)

        unresolved = []
        for m in mistakes:
            if not m.get("correction_applied") or not m.get("correction_verified"):
                unresolved.append(m)

        # Sort by severity
        severity_order = [s.value for s in MistakeSeverity]
        unresolved.sort(key=lambda x: severity_order.index(x.get("severity", "medium")))

        return unresolved

    def get_recurring_mistakes(
        self,
        agent_id: str,
        min_recurrences: int = 2,
    ) -> List[Dict[str, Any]]:
        """Get mistakes that have recurred."""
        mistakes = self._find_nodes("mistake", agent_id=agent_id)

        recurring = [m for m in mistakes if m.get("recurrence_count", 0) >= min_recurrences]

        recurring.sort(key=lambda x: x.get("recurrence_count", 0), reverse=True)

        return recurring

    def get_mistake_patterns(
        self,
        agent_id: str,
        min_frequency: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get detected mistake patterns."""
        patterns = self._find_nodes("mistake_pattern", agent_id=agent_id)

        filtered = [p for p in patterns if p.get("frequency", 0) >= min_frequency]

        filtered.sort(key=lambda x: x.get("frequency", 0), reverse=True)

        return filtered

    def analyze_root_causes(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Analyze root causes across all mistakes."""
        mistakes = self._find_nodes("mistake", agent_id=agent_id)

        root_cause_counts = {}
        root_cause_by_category = {}
        severity_by_root_cause = {}

        for m in mistakes:
            rc = m.get("root_cause", "unknown")
            cat = m.get("category", "unknown")
            sev = m.get("severity", "medium")

            root_cause_counts[rc] = root_cause_counts.get(rc, 0) + 1

            if rc not in root_cause_by_category:
                root_cause_by_category[rc] = {}
            root_cause_by_category[rc][cat] = root_cause_by_category[rc].get(cat, 0) + 1

            if rc not in severity_by_root_cause:
                severity_by_root_cause[rc] = {}
            severity_by_root_cause[rc][sev] = severity_by_root_cause[rc].get(sev, 0) + 1

        # Calculate weighted score per root cause
        weighted_scores = {}
        for rc, severities in severity_by_root_cause.items():
            score = 0
            for sev, count in severities.items():
                weight = MISTAKE_SEVERITY_WEIGHTS.get(MistakeSeverity(sev), 1)
                score += weight * count
            weighted_scores[rc] = score

        # Sort by weighted score
        sorted_causes = sorted(weighted_scores.items(), key=lambda x: x[1], reverse=True)

        return {
            "agent_id": agent_id,
            "total_mistakes": len(mistakes),
            "unique_root_causes": len(root_cause_counts),
            "top_root_causes": sorted_causes[:10],
            "root_cause_counts": root_cause_counts,
            "root_cause_by_category": root_cause_by_category,
        }

    # =========================================================================
    # Prevention
    # =========================================================================

    def add_prevention_strategy(
        self,
        pattern_id: str,
        strategy: str,
        added_by: str,
    ) -> Dict[str, Any]:
        """Add a prevention strategy to a pattern."""
        pattern = self._get_node("mistake_pattern", pattern_id)
        if not pattern:
            return {"error": "Pattern not found"}

        strategies = pattern.get("prevention_strategies", [])
        strategies.append({
            "strategy": strategy,
            "added_by": added_by,
            "added_at": self._now(),
            "effectiveness_score": None,
        })

        self._update_node("mistake_pattern", pattern_id, {
            "prevention_strategies": strategies,
        })

        return {"added": True, "pattern_id": pattern_id}

    def mark_prevention_applied(
        self,
        pattern_id: str,
        applied_by: str,
    ) -> Dict[str, Any]:
        """Mark that prevention has been applied for a pattern."""
        pattern = self._get_node("mistake_pattern", pattern_id)
        if not pattern:
            return {"error": "Pattern not found"}

        self._update_node("mistake_pattern", pattern_id, {
            "mitigation_applied": True,
            "mitigation_applied_by": applied_by,
            "mitigation_applied_at": self._now(),
        })

        return {"applied": True, "pattern_id": pattern_id}

    def get_prevention_recommendations(
        self,
        agent_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get prioritized prevention recommendations."""
        patterns = self._find_nodes("mistake_pattern", agent_id=agent_id)

        # Filter to unmitigated patterns
        unmitigated = [p for p in patterns if not p.get("mitigation_applied")]

        recommendations = []
        for pattern in unmitigated:
            score = pattern.get("frequency", 0) * pattern.get("recency_weighted_score", 1)

            recommendations.append({
                "pattern_id": pattern.get("id"),
                "pattern_name": pattern.get("name"),
                "category": pattern.get("category"),
                "root_cause": pattern.get("root_cause"),
                "frequency": pattern.get("frequency"),
                "priority_score": score,
                "existing_strategies": pattern.get("prevention_strategies", []),
            })

        recommendations.sort(key=lambda x: x.get("priority_score", 0), reverse=True)

        return recommendations[:limit]

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get mistake store statistics."""
        mistakes = self._find_nodes("mistake")
        patterns = self._find_nodes("mistake_pattern")

        # Count by category
        by_category = {}
        by_severity = {}
        corrected = 0
        verified = 0
        total_recurrences = 0

        for m in mistakes:
            cat = m.get("category", "unknown")
            sev = m.get("severity", "unknown")
            by_category[cat] = by_category.get(cat, 0) + 1
            by_severity[sev] = by_severity.get(sev, 0) + 1

            if m.get("correction_applied"):
                corrected += 1
            if m.get("correction_verified"):
                verified += 1
            total_recurrences += m.get("recurrence_count", 0)

        return {
            "total_mistakes": len(mistakes),
            "total_patterns": len(patterns),
            "by_category": by_category,
            "by_severity": by_severity,
            "corrected_count": corrected,
            "verified_count": verified,
            "correction_rate": corrected / len(mistakes) if mistakes else 0,
            "verification_rate": verified / corrected if corrected else 0,
            "total_recurrences": total_recurrences,
        }
