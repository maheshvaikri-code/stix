"""
Supervision Store
=================

Tracks supervision events, corrections, and human oversight.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta

from .base import BaseLearningStore
from ..schema import (
    SupervisionType,
    SupervisionOutcome,
)


class SupervisionStore(BaseLearningStore):
    """
    Store for agent supervision tracking.

    Provides:
    - Supervision event recording
    - Correction tracking
    - Supervisor feedback analysis
    - Escalation management
    - Learning from supervision
    """

    def __init__(self, graph):
        super().__init__(graph, "supervision")

    # =========================================================================
    # Supervision Recording
    # =========================================================================

    def record_supervision(
        self,
        agent_id: str,
        supervisor_id: str,
        supervisor_type: str,  # human, system, peer
        supervision_type: SupervisionType,
        supervised_action: str,
        supervised_output: str,
        context: Dict[str, Any],
        outcome: SupervisionOutcome,
        feedback: str,
        required_changes: Optional[List[str]] = None,
        learning_points: Optional[List[str]] = None,
        severity: str = "medium",
    ) -> str:
        """Record a supervision event."""
        supervision_id = self._generate_id("supervision")

        self._add_node("supervision_record", supervision_id, {
            "agent_id": agent_id,
            "supervisor_id": supervisor_id,
            "supervisor_type": supervisor_type,
            "supervision_type": supervision_type.value if isinstance(supervision_type, SupervisionType) else supervision_type,
            "supervised_action": supervised_action,
            "supervised_output": supervised_output,
            "context": context,
            "outcome": outcome.value if isinstance(outcome, SupervisionOutcome) else outcome,
            "feedback": feedback,
            "required_changes": required_changes or [],
            "learning_points": learning_points or [],
            "severity": severity,
            "agent_acknowledged": False,
            "changes_applied": False,
            "effectiveness_verified": False,
        })

        # Track supervisor activity
        self._update_supervisor_stats(supervisor_id, supervisor_type, outcome)

        # Create learning events from learning points
        for point in (learning_points or []):
            self._create_learning_from_supervision(agent_id, supervision_id, point, outcome)

        # Check for patterns requiring escalation
        if outcome in [SupervisionOutcome.REJECTED, SupervisionOutcome.ESCALATED]:
            self._check_escalation_pattern(agent_id, supervision_type)

        return supervision_id

    def _update_supervisor_stats(
        self,
        supervisor_id: str,
        supervisor_type: str,
        outcome: SupervisionOutcome,
    ) -> None:
        """Update supervisor statistics."""
        outcome_val = outcome.value if isinstance(outcome, SupervisionOutcome) else outcome

        existing = self._find_nodes("supervisor_stats", supervisor_id=supervisor_id)

        if existing:
            stats = existing[0]
            total = stats.get("total_supervisions", 0) + 1
            by_outcome = stats.get("by_outcome", {})
            by_outcome[outcome_val] = by_outcome.get(outcome_val, 0) + 1

            self._update_node("supervisor_stats", stats["id"], {
                "total_supervisions": total,
                "by_outcome": by_outcome,
                "last_supervision": self._now(),
            })
        else:
            stats_id = self._generate_id("sup_stats")
            self._add_node("supervisor_stats", stats_id, {
                "supervisor_id": supervisor_id,
                "supervisor_type": supervisor_type,
                "total_supervisions": 1,
                "by_outcome": {outcome_val: 1},
                "last_supervision": self._now(),
            })

    def _create_learning_from_supervision(
        self,
        agent_id: str,
        supervision_id: str,
        learning_point: str,
        outcome: SupervisionOutcome,
    ) -> str:
        """Create a learning event from supervision feedback."""
        event_id = self._generate_id("sup_learning")

        outcome_val = outcome.value if isinstance(outcome, SupervisionOutcome) else outcome

        # Determine confidence based on outcome
        confidence = 0.9 if outcome_val == "approved" else 0.8

        self._add_node("supervision_learning", event_id, {
            "agent_id": agent_id,
            "learning_content": learning_point,
            "source": f"supervision:{supervision_id}",
            "outcome_context": outcome_val,
            "confidence": confidence,
            "reinforcement_count": 0,
            "applied_count": 0,
        })

        self._add_edge(
            "supervision_learning", event_id,
            "LEARNED_FROM",
            "supervision_record", supervision_id,
            {}
        )

        return event_id

    def _check_escalation_pattern(
        self,
        agent_id: str,
        supervision_type: SupervisionType,
    ) -> Optional[str]:
        """Check if there's a pattern requiring escalation."""
        type_val = supervision_type.value if isinstance(supervision_type, SupervisionType) else supervision_type

        # Get recent supervisions
        records = self._find_nodes("supervision_record", agent_id=agent_id)

        # Filter to recent (last 7 days)
        cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
        recent = [r for r in records if r.get("_created_at", "") >= cutoff]

        # Count rejections/escalations
        problem_count = sum(
            1 for r in recent
            if r.get("outcome") in ["rejected", "escalated"]
        )

        if problem_count >= 3:
            return self._create_escalation_alert(agent_id, type_val, problem_count)

        return None

    def _create_escalation_alert(
        self,
        agent_id: str,
        supervision_type: str,
        problem_count: int,
    ) -> str:
        """Create an escalation alert."""
        alert_id = self._generate_id("escalation")

        self._add_node("escalation_alert", alert_id, {
            "agent_id": agent_id,
            "supervision_type": supervision_type,
            "problem_count": problem_count,
            "status": "pending",
            "requires_attention": True,
            "recommended_action": "Review agent behavior and consider retraining",
        })

        return alert_id

    def get_supervision(self, supervision_id: str) -> Optional[Dict[str, Any]]:
        """Get a supervision record by ID."""
        return self._get_node("supervision_record", supervision_id)

    # =========================================================================
    # Acknowledgment and Resolution
    # =========================================================================

    def acknowledge_supervision(
        self,
        supervision_id: str,
        agent_id: str,
        acknowledgment_notes: str = "",
    ) -> Dict[str, Any]:
        """Agent acknowledges supervision feedback."""
        record = self._get_node("supervision_record", supervision_id)
        if not record:
            return {"error": "Supervision record not found"}

        if record.get("agent_id") != agent_id:
            return {"error": "Agent ID mismatch"}

        self._update_node("supervision_record", supervision_id, {
            "agent_acknowledged": True,
            "acknowledged_at": self._now(),
            "acknowledgment_notes": acknowledgment_notes,
        })

        return {"acknowledged": True, "supervision_id": supervision_id}

    def apply_changes(
        self,
        supervision_id: str,
        changes_description: str,
        applied_by: str,
    ) -> Dict[str, Any]:
        """Record that required changes were applied."""
        record = self._get_node("supervision_record", supervision_id)
        if not record:
            return {"error": "Supervision record not found"}

        self._update_node("supervision_record", supervision_id, {
            "changes_applied": True,
            "changes_applied_at": self._now(),
            "changes_description": changes_description,
            "applied_by": applied_by,
        })

        return {"applied": True, "supervision_id": supervision_id}

    def verify_effectiveness(
        self,
        supervision_id: str,
        verified_by: str,
        effective: bool,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Verify if supervision feedback was effective."""
        record = self._get_node("supervision_record", supervision_id)
        if not record:
            return {"error": "Supervision record not found"}

        self._update_node("supervision_record", supervision_id, {
            "effectiveness_verified": True,
            "verified_at": self._now(),
            "verified_by": verified_by,
            "was_effective": effective,
            "verification_notes": notes,
        })

        # Update learning confidence based on effectiveness
        learnings = self._find_edges(
            target_type="supervision_record",
            target_id=supervision_id,
            rel_type="LEARNED_FROM"
        )

        for learning_edge in learnings:
            learning = self._get_node("supervision_learning", learning_edge.get("source_id"))
            if learning:
                current_confidence = learning.get("confidence", 0.8)
                new_confidence = min(1.0, current_confidence + 0.1) if effective else max(0.3, current_confidence - 0.2)
                self._update_node("supervision_learning", learning["id"], {
                    "confidence": new_confidence,
                })

        return {
            "verified": True,
            "supervision_id": supervision_id,
            "effective": effective,
        }

    # =========================================================================
    # Analysis
    # =========================================================================

    def get_supervision_by_type(
        self,
        agent_id: str,
        supervision_type: SupervisionType,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get supervision records by type."""
        type_val = supervision_type.value if isinstance(supervision_type, SupervisionType) else supervision_type
        records = self._find_nodes("supervision_record", agent_id=agent_id, supervision_type=type_val)

        records.sort(key=lambda x: x.get("_created_at", ""), reverse=True)
        return records[:limit]

    def get_supervision_by_outcome(
        self,
        agent_id: str,
        outcome: SupervisionOutcome,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get supervision records by outcome."""
        outcome_val = outcome.value if isinstance(outcome, SupervisionOutcome) else outcome
        records = self._find_nodes("supervision_record", agent_id=agent_id, outcome=outcome_val)

        records.sort(key=lambda x: x.get("_created_at", ""), reverse=True)
        return records[:limit]

    def get_pending_acknowledgments(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get supervision records pending acknowledgment."""
        records = self._find_nodes("supervision_record", agent_id=agent_id)

        pending = [r for r in records if not r.get("agent_acknowledged")]
        pending.sort(key=lambda x: x.get("_created_at", ""))

        return pending

    def get_pending_changes(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get supervision records with pending changes."""
        records = self._find_nodes("supervision_record", agent_id=agent_id)

        pending = [
            r for r in records
            if r.get("agent_acknowledged")
            and r.get("required_changes")
            and not r.get("changes_applied")
        ]

        pending.sort(key=lambda x: x.get("_created_at", ""))
        return pending

    def get_supervision_summary(
        self,
        agent_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get summary of supervision for an agent."""
        records = self._find_nodes("supervision_record", agent_id=agent_id)

        # Filter by date
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        records = [r for r in records if r.get("_created_at", "") >= cutoff]

        if not records:
            return {"agent_id": agent_id, "period_days": days, "total_supervisions": 0}

        by_type = {}
        by_outcome = {}
        by_supervisor_type = {}
        acknowledged = 0
        changes_applied = 0
        effective = 0
        verified = 0

        for r in records:
            stype = r.get("supervision_type", "unknown")
            by_type[stype] = by_type.get(stype, 0) + 1

            outcome = r.get("outcome", "unknown")
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1

            sup_type = r.get("supervisor_type", "unknown")
            by_supervisor_type[sup_type] = by_supervisor_type.get(sup_type, 0) + 1

            if r.get("agent_acknowledged"):
                acknowledged += 1
            if r.get("changes_applied"):
                changes_applied += 1
            if r.get("effectiveness_verified"):
                verified += 1
                if r.get("was_effective"):
                    effective += 1

        return {
            "agent_id": agent_id,
            "period_days": days,
            "total_supervisions": len(records),
            "by_supervision_type": by_type,
            "by_outcome": by_outcome,
            "by_supervisor_type": by_supervisor_type,
            "acknowledgment_rate": acknowledged / len(records),
            "changes_application_rate": changes_applied / max(1, sum(1 for r in records if r.get("required_changes"))),
            "verified_count": verified,
            "effectiveness_rate": effective / verified if verified else None,
        }

    def get_learnings_from_supervision(
        self,
        agent_id: str,
        min_confidence: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Get learnings derived from supervision."""
        learnings = self._find_nodes("supervision_learning", agent_id=agent_id)

        filtered = [l for l in learnings if l.get("confidence", 0) >= min_confidence]
        filtered.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return filtered

    def get_escalation_alerts(
        self,
        agent_id: Optional[str] = None,
        status: str = "pending",
    ) -> List[Dict[str, Any]]:
        """Get escalation alerts."""
        if agent_id:
            alerts = self._find_nodes("escalation_alert", agent_id=agent_id, status=status)
        else:
            alerts = self._find_nodes("escalation_alert", status=status)

        alerts.sort(key=lambda x: x.get("_created_at", ""), reverse=True)
        return alerts

    def resolve_escalation(
        self,
        alert_id: str,
        resolved_by: str,
        resolution: str,
        action_taken: str,
    ) -> Dict[str, Any]:
        """Resolve an escalation alert."""
        alert = self._get_node("escalation_alert", alert_id)
        if not alert:
            return {"error": "Alert not found"}

        self._update_node("escalation_alert", alert_id, {
            "status": "resolved",
            "resolved_at": self._now(),
            "resolved_by": resolved_by,
            "resolution": resolution,
            "action_taken": action_taken,
            "requires_attention": False,
        })

        return {"resolved": True, "alert_id": alert_id}

    # =========================================================================
    # Supervisor Analysis
    # =========================================================================

    def get_supervisor_performance(
        self,
        supervisor_id: str,
    ) -> Dict[str, Any]:
        """Analyze supervisor performance."""
        stats = self._find_nodes("supervisor_stats", supervisor_id=supervisor_id)

        if not stats:
            return {"error": "Supervisor not found"}

        stats = stats[0]

        # Get detailed records
        records = self._find_nodes("supervision_record", supervisor_id=supervisor_id)

        # Calculate effectiveness
        verified = [r for r in records if r.get("effectiveness_verified")]
        effective = [r for r in verified if r.get("was_effective")]

        return {
            "supervisor_id": supervisor_id,
            "supervisor_type": stats.get("supervisor_type"),
            "total_supervisions": stats.get("total_supervisions", 0),
            "by_outcome": stats.get("by_outcome", {}),
            "verified_count": len(verified),
            "effective_count": len(effective),
            "effectiveness_rate": len(effective) / len(verified) if verified else None,
            "last_supervision": stats.get("last_supervision"),
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get supervision store statistics."""
        records = self._find_nodes("supervision_record")
        learnings = self._find_nodes("supervision_learning")
        alerts = self._find_nodes("escalation_alert")
        supervisors = self._find_nodes("supervisor_stats")

        by_type = {}
        by_outcome = {}
        acknowledged = 0
        changes_applied = 0

        for r in records:
            stype = r.get("supervision_type", "unknown")
            by_type[stype] = by_type.get(stype, 0) + 1

            outcome = r.get("outcome", "unknown")
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1

            if r.get("agent_acknowledged"):
                acknowledged += 1
            if r.get("changes_applied"):
                changes_applied += 1

        pending_alerts = sum(1 for a in alerts if a.get("status") == "pending")

        return {
            "total_supervision_records": len(records),
            "total_learnings": len(learnings),
            "total_alerts": len(alerts),
            "pending_alerts": pending_alerts,
            "unique_supervisors": len(supervisors),
            "by_supervision_type": by_type,
            "by_outcome": by_outcome,
            "acknowledgment_rate": acknowledged / len(records) if records else 0,
            "changes_application_rate": changes_applied / len(records) if records else 0,
        }
