"""
Human Oversight & Escalation Store
===================================

Manages escalation triggers, paths, human reviewers, and oversight events.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import EscalationLevel, EscalationTrigger, HumanReviewer, EscalationEvent

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class EscalationStore(BaseStore):
    """Store for human oversight and escalation"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "escalation")
        self._setup_default_levels()

    def _setup_default_levels(self):
        """Set up default escalation levels"""
        levels = [
            ("L1_auto", "immediate", "system", "automated"),
            ("L2_agent", "<5min", "senior_agent", "agent_queue"),
            ("L3_operator", "<30min", "human_ops", "ops_dashboard"),
            ("L4_manager", "<2hr", "management", "pager"),
            ("L5_executive", "<24hr", "executive", "direct_call"),
            ("L6_board", "<48hr", "board", "emergency_meeting"),
        ]

        for name, response_time, authority, channel in levels:
            existing = self._find_nodes("escalation_level", name=name)
            if not existing:
                self._add_node("escalation_level", name, {
                    "name": name,
                    "response_time": response_time,
                    "authority": authority,
                    "channel": channel
                })

    # =========================================================================
    # Escalation Trigger Management
    # =========================================================================

    def add_trigger(
        self,
        condition: str,
        level: EscalationLevel,
        cooldown: str,
        context: str,
        description: str = "",
        trigger_id: Optional[str] = None
    ) -> str:
        """Add an escalation trigger"""
        tid = trigger_id or self._generate_id("et")
        props = {
            "condition": condition,
            "level": level.value,
            "cooldown": cooldown,
            "context": context,
            "description": description,
            "active": True
        }
        return self._add_node("escalation_trigger", tid, props)

    def get_trigger(self, trigger_id: str) -> Optional[Dict[str, Any]]:
        """Get trigger by ID"""
        return self._get_node("escalation_trigger", trigger_id)

    def list_triggers(self, level: Optional[EscalationLevel] = None) -> List[Dict[str, Any]]:
        """List all triggers"""
        triggers = self._find_nodes("escalation_trigger")
        if level:
            triggers = [t for t in triggers if t.get("level") == level.value]
        return triggers

    def deactivate_trigger(self, trigger_id: str):
        """Deactivate a trigger"""
        self._update_node("escalation_trigger", trigger_id, {"active": False})

    # =========================================================================
    # Human Reviewer Management
    # =========================================================================

    def add_reviewer(
        self,
        name: str,
        expertise: List[str],
        availability: str,
        reviewer_id: Optional[str] = None
    ) -> str:
        """Add a human reviewer"""
        rid = reviewer_id or self._generate_id("hr")
        props = {
            "name": name,
            "expertise": expertise,
            "availability": availability,
            "fatigue_score": 0.0,
            "current_load": 0,
            "active": True
        }
        return self._add_node("human_reviewer", rid, props)

    def get_reviewer(self, reviewer_id: str) -> Optional[Dict[str, Any]]:
        """Get reviewer by ID"""
        return self._get_node("human_reviewer", reviewer_id)

    def list_reviewers(self, available: bool = True) -> List[Dict[str, Any]]:
        """List reviewers"""
        reviewers = self._find_nodes("human_reviewer")
        if available:
            reviewers = [r for r in reviewers if r.get("active")]
        return reviewers

    def update_reviewer_load(self, reviewer_id: str, delta: int):
        """Update reviewer's current load"""
        reviewer = self.get_reviewer(reviewer_id)
        if reviewer:
            new_load = max(0, reviewer.get("current_load", 0) + delta)
            # Update fatigue based on load
            fatigue = min(1.0, new_load / 20)  # Max fatigue at 20 items
            self._update_node("human_reviewer", reviewer_id, {
                "current_load": new_load,
                "fatigue_score": fatigue
            })

    # =========================================================================
    # Escalation Path Configuration
    # =========================================================================

    def set_escalation_path(
        self,
        from_level: EscalationLevel,
        to_level: EscalationLevel,
        condition: str,
        auto_escalate_after: str
    ):
        """Set escalation path between levels"""
        self._add_edge(
            "escalation_level", from_level.value,
            "ESCALATION_PATH",
            "escalation_level", to_level.value,
            {
                "condition": condition,
                "auto_escalate_after": auto_escalate_after
            }
        )

    def get_escalation_path(self, level: EscalationLevel) -> List[Dict[str, Any]]:
        """Get escalation path from a level"""
        path = []
        current = level.value

        while True:
            edges = self._find_edges(
                source_type="escalation_level", source_id=current,
                rel_type="ESCALATION_PATH"
            )
            if not edges:
                break

            next_level = edges[0]["target"][1]
            path.append({
                "from": current,
                "to": next_level,
                "condition": edges[0]["properties"].get("condition"),
                "auto_escalate_after": edges[0]["properties"].get("auto_escalate_after")
            })
            current = next_level

            if len(path) > 10:  # Prevent infinite loops
                break

        return path

    # =========================================================================
    # Escalation Events
    # =========================================================================

    def create_escalation(
        self,
        trigger_id: str,
        level: EscalationLevel,
        context: Dict[str, Any],
        escalation_id: Optional[str] = None
    ) -> str:
        """Create an escalation event"""
        eid = escalation_id or self._generate_id("ee")

        # Find best reviewer for this level
        reviewer_id = self._find_best_reviewer(level, context)

        props = {
            "trigger_id": trigger_id,
            "level": level.value,
            "assigned_to": reviewer_id,
            "status": "pending" if not reviewer_id else "assigned",
            "created_at": self._now(),
            "context": context
        }
        self._add_node("escalation_event", eid, props)

        # Update reviewer load
        if reviewer_id:
            self.update_reviewer_load(reviewer_id, 1)

        return eid

    def _find_best_reviewer(
        self,
        level: EscalationLevel,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """Find the best available reviewer for an escalation"""
        reviewers = self.list_reviewers(available=True)

        if not reviewers:
            return None

        # Score reviewers based on expertise match and fatigue
        context_expertise = context.get("expertise_needed", [])
        scored = []

        for r in reviewers:
            expertise_match = len(set(r.get("expertise", [])) & set(context_expertise))
            fatigue = r.get("fatigue_score", 0)
            load = r.get("current_load", 0)

            # Score: higher is better
            score = expertise_match * 10 - fatigue * 5 - load * 0.5
            scored.append((r["id"], score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0] if scored else None

    def get_escalation(self, escalation_id: str) -> Optional[Dict[str, Any]]:
        """Get escalation event by ID"""
        return self._get_node("escalation_event", escalation_id)

    def list_escalations(
        self,
        status: Optional[str] = None,
        level: Optional[EscalationLevel] = None
    ) -> List[Dict[str, Any]]:
        """List escalation events"""
        escalations = self._find_nodes("escalation_event")

        if status:
            escalations = [e for e in escalations if e.get("status") == status]
        if level:
            escalations = [e for e in escalations if e.get("level") == level.value]

        return sorted(escalations, key=lambda e: e.get("created_at", ""), reverse=True)

    def resolve_escalation(
        self,
        escalation_id: str,
        resolution: str,
        action_taken: str
    ):
        """Resolve an escalation"""
        escalation = self.get_escalation(escalation_id)
        if not escalation:
            return

        self._update_node("escalation_event", escalation_id, {
            "status": "resolved",
            "resolution": resolution,
            "action_taken": action_taken,
            "resolved_at": self._now()
        })

        # Update reviewer load
        if escalation.get("assigned_to"):
            self.update_reviewer_load(escalation["assigned_to"], -1)

    def escalate_further(self, escalation_id: str):
        """Escalate to next level"""
        escalation = self.get_escalation(escalation_id)
        if not escalation:
            return

        current_level = escalation.get("level")
        path = self.get_escalation_path(EscalationLevel(current_level))

        if path:
            next_level = path[0]["to"]

            # Update status
            self._update_node("escalation_event", escalation_id, {
                "status": "escalated",
                "escalated_at": self._now(),
                "escalated_to": next_level
            })

            # Create new escalation at higher level
            self.create_escalation(
                escalation.get("trigger_id"),
                EscalationLevel(next_level),
                escalation.get("context", {})
            )

    # =========================================================================
    # Human Decision Feedback
    # =========================================================================

    def record_feedback(
        self,
        escalation_id: str,
        human_action: str,
        agent_would_have: str,
        learning: str
    ) -> str:
        """Record feedback from human decision"""
        fid = self._generate_id("hf")
        props = {
            "escalation_id": escalation_id,
            "human_action": human_action,
            "agent_would_have": agent_would_have,
            "learning": learning,
            "timestamp": self._now()
        }
        self._add_node("human_feedback", fid, props)

        self._add_edge(
            "human_feedback", fid,
            "FEEDBACK_FROM",
            "escalation_event", escalation_id,
            {}
        )

        return fid

    def get_feedback(self, escalation_id: str) -> List[Dict[str, Any]]:
        """Get feedback for an escalation"""
        return self._find_nodes("human_feedback", escalation_id=escalation_id)

    # =========================================================================
    # Trigger Evaluation
    # =========================================================================

    def evaluate_triggers(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Evaluate all triggers against context and return matched ones"""
        triggers = self.list_triggers()
        active_triggers = [t for t in triggers if t.get("active")]

        matched = []
        for trigger in active_triggers:
            condition = trigger.get("condition", "")

            # Simple condition evaluation
            try:
                # Replace context references
                expr = condition
                for key, value in context.items():
                    expr = expr.replace(key, repr(value) if isinstance(value, str) else str(value))

                result = eval(expr, {"__builtins__": {}}, {})
                if result:
                    matched.append(trigger)
            except:
                pass

        return matched

    def trigger_escalation(
        self,
        context: Dict[str, Any]
    ) -> List[str]:
        """Evaluate triggers and create escalations for matches"""
        matched = self.evaluate_triggers(context)
        escalation_ids = []

        for trigger in matched:
            eid = self.create_escalation(
                trigger["id"],
                EscalationLevel(trigger["level"]),
                context
            )
            escalation_ids.append(eid)

        return escalation_ids

    # =========================================================================
    # Fatigue Management
    # =========================================================================

    def check_reviewer_fatigue(self) -> List[Dict[str, Any]]:
        """Check for fatigued reviewers"""
        reviewers = self.list_reviewers()
        fatigued = []

        for r in reviewers:
            fatigue = r.get("fatigue_score", 0)
            if fatigue > 0.7:
                fatigued.append({
                    "reviewer_id": r["id"],
                    "name": r.get("name"),
                    "fatigue_score": fatigue,
                    "current_load": r.get("current_load"),
                    "action": "redistribute" if fatigue > 0.9 else "warn"
                })

        return fatigued

    # =========================================================================
    # Escalation Metrics
    # =========================================================================

    def get_escalation_metrics(self) -> Dict[str, Any]:
        """Get escalation metrics"""
        escalations = self._find_nodes("escalation_event")

        pending = len([e for e in escalations if e.get("status") == "pending"])
        assigned = len([e for e in escalations if e.get("status") == "assigned"])
        resolved = len([e for e in escalations if e.get("status") == "resolved"])
        escalated = len([e for e in escalations if e.get("status") == "escalated"])

        # Calculate average resolution time
        resolution_times = []
        for e in escalations:
            if e.get("resolved_at") and e.get("created_at"):
                # Simple time diff calculation
                resolution_times.append(1)  # Placeholder

        by_level = {}
        for e in escalations:
            level = e.get("level", "unknown")
            by_level[level] = by_level.get(level, 0) + 1

        return {
            "total": len(escalations),
            "pending": pending,
            "assigned": assigned,
            "resolved": resolved,
            "escalated_further": escalated,
            "by_level": by_level,
            "fatigued_reviewers": len(self.check_reviewer_fatigue())
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get escalation store statistics"""
        base_stats = super().get_stats()
        triggers = self._find_nodes("escalation_trigger")
        reviewers = self._find_nodes("human_reviewer")
        escalations = self._find_nodes("escalation_event")

        return {
            **base_stats,
            "triggers": len(triggers),
            "active_triggers": len([t for t in triggers if t.get("active")]),
            "reviewers": len(reviewers),
            "escalations": len(escalations),
            "pending_escalations": len([e for e in escalations if e.get("status") == "pending"])
        }
