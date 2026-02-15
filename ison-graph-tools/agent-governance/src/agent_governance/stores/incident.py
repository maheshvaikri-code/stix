"""
Incident Response Store
=======================

Manages incidents, phases, response actions, and post-mortems.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import IncidentSeverity, IncidentStatus, Incident, IncidentPhase, ResponseAction

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class IncidentStore(BaseStore):
    """Store for incident response governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "incident")
        self._setup_default_phases()

    def _setup_default_phases(self):
        """Set up default incident phases"""
        phases = [
            ("detection", "<5min", "automated"),
            ("triage", "<15min", "l2_operator"),
            ("containment", "<30min", "l3_manager"),
            ("eradication", "<4hr", "l3_manager"),
            ("recovery", "<24hr", "l3_manager"),
            ("post_mortem", "<7d", "l4_director"),
        ]

        for name, duration, authority in phases:
            existing = self._find_nodes("incident_phase", name=name)
            if not existing:
                self._add_node("incident_phase", name, {
                    "name": name,
                    "typical_duration": duration,
                    "authority_level": authority
                })

    # =========================================================================
    # Incident Management
    # =========================================================================

    def create_incident(
        self,
        severity: IncidentSeverity,
        category: str,
        description: str = "",
        incident_id: Optional[str] = None
    ) -> str:
        """Create a new incident"""
        iid = incident_id or self._generate_id("ic")
        props = {
            "severity": severity.value,
            "category": category,  # "safety", "data_breach", "service", etc.
            "status": IncidentStatus.ACTIVE.value,
            "description": description,
            "detected_at": self._now(),
            "current_phase": "detection"
        }
        return self._add_node("incident", iid, props)

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident by ID"""
        return self._get_node("incident", incident_id)

    def list_incidents(
        self,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None
    ) -> List[Dict[str, Any]]:
        """List incidents"""
        incidents = self._find_nodes("incident")

        if status:
            incidents = [i for i in incidents if i.get("status") == status.value]
        if severity:
            incidents = [i for i in incidents if i.get("severity") == severity.value]

        return sorted(incidents, key=lambda i: i.get("detected_at", ""), reverse=True)

    def update_incident_status(self, incident_id: str, status: IncidentStatus):
        """Update incident status"""
        updates = {"status": status.value}
        if status == IncidentStatus.RESOLVED:
            updates["resolved_at"] = self._now()
        self._update_node("incident", incident_id, updates)

    def advance_phase(self, incident_id: str, new_phase: str):
        """Advance incident to next phase"""
        self._update_node("incident", incident_id, {
            "current_phase": new_phase,
            f"{new_phase}_started_at": self._now()
        })

    # =========================================================================
    # Response Actions
    # =========================================================================

    def record_action(
        self,
        incident_id: str,
        phase: str,
        action: str,
        executed_by: str,
        result: str = "",
        action_id: Optional[str] = None
    ) -> str:
        """Record a response action"""
        aid = action_id or self._generate_id("ra")
        props = {
            "incident_id": incident_id,
            "phase": phase,
            "action": action,
            "executed_by": executed_by,
            "result": result,
            "timestamp": self._now()
        }
        self._add_node("response_action", aid, props)

        self._add_edge(
            "response_action", aid,
            "RESPONSE_ACTION",
            "incident", incident_id,
            {}
        )

        return aid

    def get_actions(self, incident_id: str) -> List[Dict[str, Any]]:
        """Get all actions for an incident"""
        actions = self._find_nodes("response_action", incident_id=incident_id)
        return sorted(actions, key=lambda a: a.get("timestamp", ""))

    # =========================================================================
    # Incident Communications
    # =========================================================================

    def record_communication(
        self,
        incident_id: str,
        comm_type: str,
        audience: str,
        content_summary: str,
        comm_id: Optional[str] = None
    ) -> str:
        """Record incident communication"""
        cid = comm_id or self._generate_id("cm")
        import hashlib
        content_hash = hashlib.md5(content_summary.encode()).hexdigest()[:8]

        props = {
            "incident_id": incident_id,
            "type": comm_type,  # "alert", "status", "escalation"
            "audience": audience,
            "content_hash": content_hash,
            "sent_at": self._now()
        }
        self._add_node("incident_communication", cid, props)

        return cid

    def get_communications(self, incident_id: str) -> List[Dict[str, Any]]:
        """Get communications for an incident"""
        return self._find_nodes("incident_communication", incident_id=incident_id)

    # =========================================================================
    # Playbook Execution
    # =========================================================================

    def add_playbook(
        self,
        name: str,
        category: str,
        steps: List[str],
        playbook_id: Optional[str] = None
    ) -> str:
        """Add an incident response playbook"""
        pid = playbook_id or self._generate_id("pb")
        props = {
            "name": name,
            "category": category,
            "steps": steps,
            "version": "1.0"
        }
        return self._add_node("playbook", pid, props)

    def execute_playbook(
        self,
        incident_id: str,
        playbook_id: str
    ) -> str:
        """Start playbook execution for an incident"""
        eid = self._generate_id("pe")
        props = {
            "incident_id": incident_id,
            "playbook_id": playbook_id,
            "started_at": self._now(),
            "steps_completed": 0,
            "status": "in_progress"
        }
        self._add_node("playbook_execution", eid, props)

        self._add_edge(
            "playbook_execution", eid,
            "PLAYBOOK_EXECUTION",
            "incident", incident_id,
            {}
        )

        return eid

    def update_playbook_progress(
        self,
        execution_id: str,
        steps_completed: int,
        deviation: Optional[str] = None
    ):
        """Update playbook execution progress"""
        updates = {"steps_completed": steps_completed}
        if deviation:
            updates["deviation"] = deviation
        self._update_node("playbook_execution", execution_id, updates)

    # =========================================================================
    # Root Cause Analysis
    # =========================================================================

    def add_root_cause(
        self,
        incident_id: str,
        cause: str,
        relationship: str,
        confidence: float
    ) -> str:
        """Add root cause to incident"""
        rid = self._generate_id("rc")
        props = {
            "incident_id": incident_id,
            "cause": cause,
            "relationship": relationship,  # "direct", "enabled", "introduced"
            "confidence": confidence,
            "identified_at": self._now()
        }
        self._add_node("root_cause", rid, props)

        self._add_edge(
            "root_cause", rid,
            "ROOT_CAUSE_CHAIN",
            "incident", incident_id,
            {"confidence": confidence}
        )

        return rid

    def get_root_causes(self, incident_id: str) -> List[Dict[str, Any]]:
        """Get root causes for an incident"""
        return self._find_nodes("root_cause", incident_id=incident_id)

    # =========================================================================
    # Post-Mortem
    # =========================================================================

    def create_post_mortem(
        self,
        incident_id: str,
        findings: List[str],
        root_causes: List[str],
        actions: List[str],
        post_mortem_id: Optional[str] = None
    ) -> str:
        """Create post-mortem for an incident"""
        pid = post_mortem_id or self._generate_id("pm")
        props = {
            "incident_id": incident_id,
            "findings": findings,
            "root_causes": root_causes,
            "actions": actions,
            "completed_at": self._now()
        }
        self._add_node("post_mortem", pid, props)

        self._add_edge(
            "post_mortem", pid,
            "POST_MORTEM",
            "incident", incident_id,
            {}
        )

        return pid

    def get_post_mortem(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get post-mortem for an incident"""
        post_mortems = self._find_nodes("post_mortem", incident_id=incident_id)
        return post_mortems[0] if post_mortems else None

    def add_post_mortem_action(
        self,
        post_mortem_id: str,
        finding: str,
        action: str,
        owner: str,
        due_date: str
    ) -> str:
        """Add action item from post-mortem"""
        aid = self._generate_id("pma")
        props = {
            "post_mortem_id": post_mortem_id,
            "finding": finding,
            "action": action,
            "owner": owner,
            "due_date": due_date,
            "status": "open"
        }
        return self._add_node("post_mortem_action", aid, props)

    # =========================================================================
    # Incident Timeline
    # =========================================================================

    def get_incident_timeline(self, incident_id: str) -> List[Dict[str, Any]]:
        """Get full timeline for an incident"""
        incident = self.get_incident(incident_id)
        if not incident:
            return []

        timeline = []

        # Detection
        timeline.append({
            "type": "detection",
            "timestamp": incident.get("detected_at"),
            "description": f"Incident detected: {incident.get('description')}"
        })

        # Actions
        for action in self.get_actions(incident_id):
            timeline.append({
                "type": "action",
                "timestamp": action.get("timestamp"),
                "description": f"[{action.get('phase')}] {action.get('action')}"
            })

        # Communications
        for comm in self.get_communications(incident_id):
            timeline.append({
                "type": "communication",
                "timestamp": comm.get("sent_at"),
                "description": f"{comm.get('type')} to {comm.get('audience')}"
            })

        # Resolution
        if incident.get("resolved_at"):
            timeline.append({
                "type": "resolution",
                "timestamp": incident.get("resolved_at"),
                "description": "Incident resolved"
            })

        return sorted(timeline, key=lambda t: t.get("timestamp", ""))

    # =========================================================================
    # Incident Metrics
    # =========================================================================

    def get_incident_metrics(self) -> Dict[str, Any]:
        """Get incident metrics"""
        incidents = self._find_nodes("incident")

        by_severity = {}
        by_category = {}
        by_status = {}

        for inc in incidents:
            severity = inc.get("severity", "unknown")
            category = inc.get("category", "unknown")
            status = inc.get("status", "unknown")

            by_severity[severity] = by_severity.get(severity, 0) + 1
            by_category[category] = by_category.get(category, 0) + 1
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_incidents": len(incidents),
            "active_incidents": by_status.get("active", 0),
            "by_severity": by_severity,
            "by_category": by_category,
            "by_status": by_status
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get incident store statistics"""
        base_stats = super().get_stats()
        incidents = self._find_nodes("incident")
        actions = self._find_nodes("response_action")
        post_mortems = self._find_nodes("post_mortem")

        return {
            **base_stats,
            "incidents": len(incidents),
            "active_incidents": len([i for i in incidents if i.get("status") == "active"]),
            "response_actions": len(actions),
            "post_mortems": len(post_mortems)
        }
