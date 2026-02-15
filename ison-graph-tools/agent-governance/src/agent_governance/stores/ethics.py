"""
Ethics & Values Store
=====================

Manages values, ethical principles, dilemmas, and value alignment.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import ValuePriority, Value, EthicalPrinciple, EthicalDilemma, ValueMeasurement

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class EthicsStore(BaseStore):
    """Store for ethics and value alignment governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "ethics")

    # =========================================================================
    # Value Management
    # =========================================================================

    def add_value(
        self,
        name: str,
        priority: ValuePriority,
        measurable: bool,
        source: str,
        description: str = "",
        value_id: Optional[str] = None
    ) -> str:
        """Add a core value"""
        # Use name as default ID for easy reference
        vid = value_id or name
        props = {
            "name": name,
            "priority": priority.value,
            "measurable": measurable,
            "source": source,  # "mission", "principle", "operational"
            "description": description
        }
        return self._add_node("value", vid, props)

    def get_value(self, value_id: str) -> Optional[Dict[str, Any]]:
        """Get value by ID"""
        return self._get_node("value", value_id)

    def list_values(self, priority: Optional[ValuePriority] = None) -> List[Dict[str, Any]]:
        """List all values"""
        values = self._find_nodes("value")
        if priority:
            values = [v for v in values if v.get("priority") == priority.value]
        return values

    def set_value_hierarchy(
        self,
        dominant_value_id: str,
        subordinate_value_id: str,
        relationship: str,
        in_conflict_resolution: str
    ):
        """Set hierarchy between values"""
        self._add_edge(
            "value", dominant_value_id,
            "VALUE_HIERARCHY",
            "value", subordinate_value_id,
            {"relationship": relationship, "in_conflict_resolution": in_conflict_resolution}
        )

    def get_value_hierarchy(self, value_id: str) -> Dict[str, Any]:
        """Get value's position in hierarchy"""
        # Find what this value dominates
        dominates = self._find_edges(
            source_type="value", source_id=value_id,
            rel_type="VALUE_HIERARCHY"
        )

        # Find what dominates this value
        dominated_by = self._find_edges(
            rel_type="VALUE_HIERARCHY",
            target_type="value", target_id=value_id
        )

        return {
            "value_id": value_id,
            "dominates": [e["target"][1] for e in dominates],
            "dominated_by": [e["source"][1] for e in dominated_by]
        }

    # =========================================================================
    # Ethical Principles
    # =========================================================================

    def add_principle(
        self,
        name: str,
        derived_from: List[str],
        operationalization: str,
        description: str = "",
        principle_id: Optional[str] = None
    ) -> str:
        """Add an ethical principle"""
        pid = principle_id or self._generate_id("ep")
        props = {
            "name": name,
            "derived_from": derived_from,
            "operationalization": operationalization,
            "description": description
        }
        self._add_node("ethical_principle", pid, props)

        # Link to source values
        for value_id in derived_from:
            self._add_edge(
                "ethical_principle", pid,
                "PRINCIPLE_FROM",
                "value", value_id,
                {}
            )

        return pid

    def get_principle(self, principle_id: str) -> Optional[Dict[str, Any]]:
        """Get principle by ID"""
        return self._get_node("ethical_principle", principle_id)

    def list_principles(self) -> List[Dict[str, Any]]:
        """List all principles"""
        return self._find_nodes("ethical_principle")

    def evaluate_principle(
        self,
        principle_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate if a principle is satisfied in a context"""
        principle = self.get_principle(principle_id)
        if not principle:
            return {"error": "Principle not found"}

        operationalization = principle.get("operationalization", "")

        try:
            # Simple evaluation
            result = eval(operationalization, {"__builtins__": {}}, context)
            return {
                "principle_id": principle_id,
                "name": principle.get("name"),
                "satisfied": bool(result),
                "operationalization": operationalization
            }
        except Exception as e:
            return {
                "principle_id": principle_id,
                "name": principle.get("name"),
                "satisfied": None,
                "error": str(e)
            }

    # =========================================================================
    # Ethical Dilemmas
    # =========================================================================

    def add_dilemma(
        self,
        situation: str,
        values_in_tension: List[str],
        resolution_principle: str,
        examples: Optional[List[str]] = None,
        dilemma_id: Optional[str] = None
    ) -> str:
        """Add an ethical dilemma definition"""
        did = dilemma_id or self._generate_id("ed")
        props = {
            "situation": situation,
            "values_in_tension": values_in_tension,
            "resolution_principle": resolution_principle,
            "examples": examples or []
        }
        self._add_node("ethical_dilemma", did, props)

        # Link to involved values
        for value_id in values_in_tension:
            self._add_edge(
                "ethical_dilemma", did,
                "DILEMMA_INVOLVES",
                "value", value_id,
                {}
            )

        return did

    def get_dilemma(self, dilemma_id: str) -> Optional[Dict[str, Any]]:
        """Get dilemma by ID"""
        return self._get_node("ethical_dilemma", dilemma_id)

    def list_dilemmas(self) -> List[Dict[str, Any]]:
        """List all dilemmas"""
        return self._find_nodes("ethical_dilemma")

    def resolve_dilemma(
        self,
        situation: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find applicable dilemma and resolution for a situation"""
        dilemmas = self.list_dilemmas()

        for dilemma in dilemmas:
            # Simple situation matching
            if dilemma.get("situation", "").lower() in situation.lower():
                values = dilemma.get("values_in_tension", [])

                # Get value hierarchy to determine resolution
                hierarchy_info = []
                for v in values:
                    h = self.get_value_hierarchy(v)
                    value = self.get_value(v)
                    hierarchy_info.append({
                        "value": v,
                        "name": value.get("name") if value else "",
                        "priority": value.get("priority") if value else "",
                        "dominates_count": len(h.get("dominates", []))
                    })

                # Sort by priority and dominance
                priority_order = {"highest": 0, "high": 1, "medium": 2, "low": 3}
                hierarchy_info.sort(
                    key=lambda x: (priority_order.get(x["priority"], 99), -x["dominates_count"])
                )

                return {
                    "dilemma_matched": dilemma["id"],
                    "situation": dilemma.get("situation"),
                    "values_in_tension": hierarchy_info,
                    "resolution_principle": dilemma.get("resolution_principle"),
                    "dominant_value": hierarchy_info[0] if hierarchy_info else None
                }

        return {"dilemma_matched": None, "message": "No matching dilemma found"}

    # =========================================================================
    # Value Measurements
    # =========================================================================

    def record_measurement(
        self,
        value_id: str,
        metric: str,
        current: float,
        target: float
    ) -> str:
        """Record a value alignment measurement"""
        mid = self._generate_id("vm")
        props = {
            "value_id": value_id,
            "metric": metric,
            "current": current,
            "target": target,
            "timestamp": self._now()
        }
        self._add_node("value_measurement", mid, props)

        self._add_edge(
            "value_measurement", mid,
            "VALUE_MEASUREMENT",
            "value", value_id,
            {}
        )

        return mid

    def get_measurements(
        self,
        value_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get measurements for a value"""
        measurements = self._find_nodes("value_measurement", value_id=value_id)
        return sorted(measurements, key=lambda m: m.get("timestamp", ""), reverse=True)[:limit]

    def get_value_trend(self, value_id: str) -> Dict[str, Any]:
        """Get trend for a value's measurements"""
        measurements = self.get_measurements(value_id, limit=10)

        if len(measurements) < 2:
            return {"value_id": value_id, "trend": "insufficient_data"}

        # Compare recent to older
        recent = measurements[:3]
        older = measurements[3:]

        recent_avg = sum(m.get("current", 0) for m in recent) / len(recent)
        older_avg = sum(m.get("current", 0) for m in older) / len(older) if older else recent_avg

        if recent_avg > older_avg + 0.05:
            trend = "improving"
        elif recent_avg < older_avg - 0.05:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "value_id": value_id,
            "recent_avg": recent_avg,
            "older_avg": older_avg,
            "trend": trend
        }

    # =========================================================================
    # Value Violations
    # =========================================================================

    def record_violation(
        self,
        value_id: str,
        agent_id: str,
        context: str,
        severity: str,
        remediation: str
    ) -> str:
        """Record a value violation"""
        vid = self._generate_id("vv")
        props = {
            "value_id": value_id,
            "agent_id": agent_id,
            "context": context,
            "severity": severity,
            "remediation": remediation,
            "timestamp": self._now()
        }
        self._add_node("value_violation", vid, props)

        self._add_edge(
            "value_violation", vid,
            "VALUE_VIOLATION",
            "value", value_id,
            {}
        )

        return vid

    def get_violations(
        self,
        value_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get value violations"""
        violations = self._find_nodes("value_violation")

        if value_id:
            violations = [v for v in violations if v.get("value_id") == value_id]
        if agent_id:
            violations = [v for v in violations if v.get("agent_id") == agent_id]

        return violations

    # =========================================================================
    # Value Alignment Score
    # =========================================================================

    def calculate_alignment_score(
        self,
        agent_id: str
    ) -> Dict[str, Any]:
        """Calculate overall value alignment score for an agent"""
        values = self.list_values()
        violations = self.get_violations(agent_id=agent_id)

        scores = {}
        for value in values:
            vid = value["id"]
            measurements = self.get_measurements(vid, limit=1)

            base_score = 1.0
            if measurements:
                current = measurements[0].get("current", 0)
                target = measurements[0].get("target", 1)
                base_score = current / target if target > 0 else 1.0

            # Deduct for violations
            value_violations = [v for v in violations if v.get("value_id") == vid]
            violation_penalty = len(value_violations) * 0.1

            scores[value.get("name", vid)] = max(0, base_score - violation_penalty)

        overall_score = sum(scores.values()) / len(scores) if scores else 1.0

        return {
            "agent_id": agent_id,
            "overall_score": overall_score,
            "value_scores": scores,
            "violation_count": len(violations)
        }

    # =========================================================================
    # Ethical Override
    # =========================================================================

    def record_ethical_override(
        self,
        principle_id: str,
        overridden_value_id: str,
        override_type: str,
        requires: str,
        context: str
    ) -> str:
        """Record an ethical override"""
        oid = self._generate_id("eo")
        props = {
            "principle_id": principle_id,
            "overridden_value_id": overridden_value_id,
            "override_type": override_type,
            "requires": requires,
            "context": context,
            "timestamp": self._now()
        }
        return self._add_node("ethical_override", oid, props)

    def get_stats(self) -> Dict[str, Any]:
        """Get ethics store statistics"""
        base_stats = super().get_stats()
        values = self._find_nodes("value")
        principles = self._find_nodes("ethical_principle")
        dilemmas = self._find_nodes("ethical_dilemma")
        violations = self._find_nodes("value_violation")

        return {
            **base_stats,
            "values": len(values),
            "principles": len(principles),
            "dilemmas": len(dilemmas),
            "violations": len(violations)
        }
