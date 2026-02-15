"""
Attention Store
===============

Tracks and analyzes agent attention patterns.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from .base import BaseLearningStore
from ..schema import AttentionType


class AttentionStore(BaseLearningStore):
    """
    Store for agent attention tracking.

    Provides:
    - Attention recording
    - Missed element tracking
    - Attention quality analysis
    - Focus pattern detection
    """

    def __init__(self, graph):
        super().__init__(graph, "attention")

    # =========================================================================
    # Attention Recording
    # =========================================================================

    def record_attention(
        self,
        agent_id: str,
        attention_type: AttentionType,
        focus_target: str,
        focus_context: Dict[str, Any],
        attention_duration_ms: int,
        attention_quality: float,
        missed_elements: Optional[List[str]] = None,
        over_focused_elements: Optional[List[str]] = None,
        influenced_decision: bool = False,
        decision_id: Optional[str] = None,
    ) -> str:
        """Record an attention event."""
        attention_id = self._generate_id("attention")

        self._add_node("attention_record", attention_id, {
            "agent_id": agent_id,
            "attention_type": attention_type.value if isinstance(attention_type, AttentionType) else attention_type,
            "focus_target": focus_target,
            "focus_context": focus_context,
            "attention_duration_ms": attention_duration_ms,
            "attention_quality": attention_quality,
            "missed_elements": missed_elements or [],
            "over_focused_elements": over_focused_elements or [],
            "influenced_decision": influenced_decision,
            "decision_id": decision_id,
        })

        # Link to decision if influenced
        if influenced_decision and decision_id:
            self._add_edge(
                "attention_record", attention_id,
                "INFLUENCED",
                "decision", decision_id,
                {}
            )

        # Track missed elements
        for missed in (missed_elements or []):
            self._record_missed_element(agent_id, attention_type, missed)

        return attention_id

    def _record_missed_element(
        self,
        agent_id: str,
        attention_type: AttentionType,
        element: str,
    ) -> None:
        """Track a missed element for pattern detection."""
        attention_type_val = attention_type.value if isinstance(attention_type, AttentionType) else attention_type

        # Check if we already track this
        existing = self._find_nodes(
            "missed_element_pattern",
            agent_id=agent_id,
            element=element,
        )

        if existing:
            pattern = existing[0]
            count = pattern.get("miss_count", 0) + 1
            self._update_node("missed_element_pattern", pattern["id"], {
                "miss_count": count,
                "last_missed": self._now(),
            })
        else:
            pattern_id = self._generate_id("missed_pattern")
            self._add_node("missed_element_pattern", pattern_id, {
                "agent_id": agent_id,
                "element": element,
                "attention_type": attention_type_val,
                "miss_count": 1,
                "last_missed": self._now(),
            })

    def get_attention(self, attention_id: str) -> Optional[Dict[str, Any]]:
        """Get an attention record by ID."""
        return self._get_node("attention_record", attention_id)

    # =========================================================================
    # Analysis
    # =========================================================================

    def get_attention_by_type(
        self,
        agent_id: str,
        attention_type: AttentionType,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get attention records by type."""
        type_val = attention_type.value if isinstance(attention_type, AttentionType) else attention_type
        records = self._find_nodes("attention_record", agent_id=agent_id, attention_type=type_val)

        records.sort(key=lambda x: x.get("_created_at", ""), reverse=True)
        return records[:limit]

    def get_frequently_missed(
        self,
        agent_id: str,
        min_count: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get elements that are frequently missed."""
        patterns = self._find_nodes("missed_element_pattern", agent_id=agent_id)

        filtered = [p for p in patterns if p.get("miss_count", 0) >= min_count]
        filtered.sort(key=lambda x: x.get("miss_count", 0), reverse=True)

        return filtered

    def get_attention_quality_by_type(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Analyze attention quality by type."""
        records = self._find_nodes("attention_record", agent_id=agent_id)

        by_type = {}
        for record in records:
            atype = record.get("attention_type", "unknown")
            quality = record.get("attention_quality", 0)
            missed = len(record.get("missed_elements", []))

            if atype not in by_type:
                by_type[atype] = {
                    "count": 0,
                    "total_quality": 0,
                    "total_missed": 0,
                    "total_duration_ms": 0,
                }

            by_type[atype]["count"] += 1
            by_type[atype]["total_quality"] += quality
            by_type[atype]["total_missed"] += missed
            by_type[atype]["total_duration_ms"] += record.get("attention_duration_ms", 0)

        # Calculate averages
        for atype, data in by_type.items():
            count = data["count"]
            data["avg_quality"] = data["total_quality"] / count if count else 0
            data["avg_missed"] = data["total_missed"] / count if count else 0
            data["avg_duration_ms"] = data["total_duration_ms"] / count if count else 0

        return {
            "agent_id": agent_id,
            "by_type": by_type,
        }

    def get_attention_recommendations(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get recommendations for improving attention."""
        recommendations = []

        # Check frequently missed elements
        missed = self.get_frequently_missed(agent_id, min_count=3)
        for m in missed[:5]:
            recommendations.append({
                "type": "frequently_missed",
                "element": m.get("element"),
                "miss_count": m.get("miss_count"),
                "attention_type": m.get("attention_type"),
                "recommendation": f"Pay more attention to '{m.get('element')}' during {m.get('attention_type')}",
            })

        # Check low quality attention types
        quality = self.get_attention_quality_by_type(agent_id)
        for atype, data in quality.get("by_type", {}).items():
            if data.get("avg_quality", 1) < 0.5:
                recommendations.append({
                    "type": "low_quality",
                    "attention_type": atype,
                    "avg_quality": data.get("avg_quality"),
                    "recommendation": f"Improve attention quality for {atype}",
                })

        return recommendations

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get attention store statistics."""
        records = self._find_nodes("attention_record")
        patterns = self._find_nodes("missed_element_pattern")

        total_missed = sum(len(r.get("missed_elements", [])) for r in records)
        avg_quality = sum(r.get("attention_quality", 0) for r in records) / len(records) if records else 0

        by_type = {}
        for r in records:
            atype = r.get("attention_type", "unknown")
            by_type[atype] = by_type.get(atype, 0) + 1

        return {
            "total_attention_records": len(records),
            "total_missed_patterns": len(patterns),
            "total_missed_elements": total_missed,
            "average_attention_quality": avg_quality,
            "by_attention_type": by_type,
        }
