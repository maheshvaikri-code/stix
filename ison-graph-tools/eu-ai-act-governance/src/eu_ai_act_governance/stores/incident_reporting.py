"""
Incident Reporting Store
========================

Manages incident reporting requirements per Article 73.
Handles serious incident detection, reporting to authorities, and corrective actions.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
from datetime import datetime, timedelta

from .base import BaseStore
from ..schema import IncidentSeverity, IncidentType, IncidentStatus

if TYPE_CHECKING:
    from ison_graph import ISONGraph


# 72-hour reporting deadline per Art. 73
REPORTING_DEADLINE_HOURS = 72


class IncidentReportingStore(BaseStore):
    """Store for incident reporting management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "incident_reporting")

    # =========================================================================
    # Incident Registration
    # =========================================================================

    def register_incident(
        self,
        system_id: str,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        title: str,
        description: str,
        detected_by: str,
        detection_method: str,  # automated, user_report, audit, monitoring
        affected_users_estimate: Optional[int] = None,
        incident_id: Optional[str] = None
    ) -> str:
        """Register a new incident"""
        iid = incident_id or self._generate_id("inc")

        # Calculate reporting deadline (72 hours from detection)
        now = datetime.fromisoformat(self._now().replace("+00:00", "").replace("Z", ""))
        deadline = (now + timedelta(hours=REPORTING_DEADLINE_HOURS)).isoformat() + "+00:00"

        # Determine if authority notification required
        requires_notification = severity in [
            IncidentSeverity.MAJOR,
            IncidentSeverity.CRITICAL
        ] or incident_type in [
            IncidentType.DEATH,
            IncidentType.SERIOUS_INJURY,
            IncidentType.FUNDAMENTAL_RIGHTS_VIOLATION
        ]

        props = {
            "system_id": system_id,
            "incident_type": incident_type.value,
            "severity": severity.value,
            "title": title,
            "description": description,
            "detected_by": detected_by,
            "detection_method": detection_method,
            "affected_users_estimate": affected_users_estimate,
            "status": IncidentStatus.DETECTED.value,
            "detected_at": self._now(),
            "reporting_deadline": deadline,
            "requires_authority_notification": requires_notification,
            "authority_notified": False,
            "node_description": f"Incident: {title}"
        }
        return self._add_node("incident", iid, props)

    def get_incident(self, incident_id: str) -> Optional[Dict[str, Any]]:
        """Get incident by ID"""
        return self._get_node("incident", incident_id)

    def get_system_incidents(
        self,
        system_id: str,
        status: Optional[IncidentStatus] = None,
        severity: Optional[IncidentSeverity] = None
    ) -> List[Dict[str, Any]]:
        """Get incidents for a system"""
        incidents = self._find_nodes("incident", system_id=system_id)
        if status:
            incidents = [i for i in incidents if i.get("status") == status.value]
        if severity:
            incidents = [i for i in incidents if i.get("severity") == severity.value]
        return incidents

    def update_incident_status(
        self,
        incident_id: str,
        status: IncidentStatus,
        updated_by: str,
        notes: str = ""
    ):
        """Update incident status"""
        self._update_node("incident", incident_id, {
            "status": status.value,
            "status_updated_by": updated_by,
            "status_notes": notes,
            "status_updated_at": self._now()
        })

    # =========================================================================
    # Investigation
    # =========================================================================

    def start_investigation(
        self,
        incident_id: str,
        investigator: str,
        investigation_scope: str,
        investigation_id: Optional[str] = None
    ) -> str:
        """Start incident investigation"""
        iid = investigation_id or self._generate_id("inv")
        props = {
            "incident_id": incident_id,
            "investigator": investigator,
            "scope": investigation_scope,
            "status": "in_progress",
            "started_at": self._now(),
            "findings": [],
            "root_causes": [],
            "description": f"Investigation for incident {incident_id}"
        }
        self._add_node("investigation", iid, props)

        # Update incident status
        self.update_incident_status(incident_id, IncidentStatus.INVESTIGATING, investigator)

        return iid

    def add_investigation_finding(
        self,
        investigation_id: str,
        finding_type: str,  # evidence, witness, technical, timeline
        finding: str,
        source: str
    ):
        """Add a finding to the investigation"""
        investigation = self._get_node("investigation", investigation_id)
        if investigation:
            findings = investigation.get("findings", [])
            findings.append({
                "type": finding_type,
                "finding": finding,
                "source": source,
                "added_at": self._now()
            })
            self._update_node("investigation", investigation_id, {
                "findings": findings
            })

    def identify_root_cause(
        self,
        investigation_id: str,
        root_cause: str,
        cause_category: str,  # technical, human, process, external
        contributing_factors: List[str]
    ):
        """Identify a root cause"""
        investigation = self._get_node("investigation", investigation_id)
        if investigation:
            causes = investigation.get("root_causes", [])
            causes.append({
                "cause": root_cause,
                "category": cause_category,
                "contributing_factors": contributing_factors,
                "identified_at": self._now()
            })
            self._update_node("investigation", investigation_id, {
                "root_causes": causes
            })

    def complete_investigation(
        self,
        investigation_id: str,
        conclusion: str,
        recommendations: List[str],
        completed_by: str
    ) -> Dict[str, Any]:
        """Complete the investigation"""
        investigation = self._get_node("investigation", investigation_id)
        if not investigation:
            return {"error": "Investigation not found"}

        self._update_node("investigation", investigation_id, {
            "status": "completed",
            "conclusion": conclusion,
            "recommendations": recommendations,
            "completed_by": completed_by,
            "completed_at": self._now()
        })

        return {
            "investigation_id": investigation_id,
            "incident_id": investigation.get("incident_id"),
            "conclusion": conclusion,
            "root_causes": investigation.get("root_causes", []),
            "recommendations": recommendations
        }

    # =========================================================================
    # Authority Notification (Art. 73)
    # =========================================================================

    def create_authority_notification(
        self,
        incident_id: str,
        authority_name: str,
        authority_type: str,  # national_authority, commission, notified_body
        notification_id: Optional[str] = None
    ) -> str:
        """Create an authority notification"""
        nid = notification_id or self._generate_id("an")

        incident = self.get_incident(incident_id)

        props = {
            "incident_id": incident_id,
            "authority_name": authority_name,
            "authority_type": authority_type,
            "system_id": incident.get("system_id") if incident else None,
            "incident_type": incident.get("incident_type") if incident else None,
            "incident_severity": incident.get("severity") if incident else None,
            "status": "draft",
            "created_at": self._now(),
            "description": f"Authority notification for {incident_id}"
        }
        return self._add_node("authority_notification", nid, props)

    def prepare_notification_content(
        self,
        notification_id: str,
        provider_name: str,
        provider_address: str,
        system_name: str,
        incident_date: str,
        incident_description: str,
        affected_persons: str,
        immediate_actions: str,
        prepared_by: str
    ):
        """Prepare notification content per Art. 73 requirements"""
        self._update_node("authority_notification", notification_id, {
            "status": "prepared",
            "provider_name": provider_name,
            "provider_address": provider_address,
            "system_name": system_name,
            "incident_date": incident_date,
            "incident_description": incident_description,
            "affected_persons": affected_persons,
            "immediate_actions": immediate_actions,
            "prepared_by": prepared_by,
            "prepared_at": self._now()
        })

    def submit_notification(
        self,
        notification_id: str,
        submitted_by: str,
        submission_method: str,  # portal, email, official_channel
        reference_number: Optional[str] = None
    ):
        """Submit notification to authority"""
        notification = self._get_node("authority_notification", notification_id)
        if not notification:
            return

        self._update_node("authority_notification", notification_id, {
            "status": "submitted",
            "submitted_by": submitted_by,
            "submitted_at": self._now(),
            "submission_method": submission_method,
            "reference_number": reference_number
        })

        # Update incident
        incident_id = notification.get("incident_id")
        if incident_id:
            self._update_node("incident", incident_id, {
                "authority_notified": True,
                "notification_submitted_at": self._now()
            })

    def record_authority_response(
        self,
        notification_id: str,
        response_type: str,  # acknowledgment, request_info, investigation, no_action
        response_content: str,
        response_date: str
    ):
        """Record authority response"""
        self._update_node("authority_notification", notification_id, {
            "status": "responded",
            "authority_response_type": response_type,
            "authority_response": response_content,
            "authority_response_date": response_date
        })

    def get_notifications(
        self,
        incident_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get authority notifications"""
        notifications = self._find_nodes("authority_notification")
        if incident_id:
            notifications = [n for n in notifications if n.get("incident_id") == incident_id]
        if status:
            notifications = [n for n in notifications if n.get("status") == status]
        return notifications

    # =========================================================================
    # Corrective Actions
    # =========================================================================

    def create_corrective_action(
        self,
        incident_id: str,
        action_type: str,  # immediate, short_term, long_term, preventive
        description: str,
        responsible: str,
        due_date: str,
        action_id: Optional[str] = None
    ) -> str:
        """Create a corrective action"""
        aid = action_id or self._generate_id("ca")
        props = {
            "incident_id": incident_id,
            "action_type": action_type,
            "description": description,
            "responsible": responsible,
            "due_date": due_date,
            "status": "planned",
            "created_at": self._now(),
            "node_description": f"Corrective action: {action_type}"
        }
        return self._add_node("corrective_action", aid, props)

    def start_corrective_action(
        self,
        action_id: str,
        started_by: str
    ):
        """Start a corrective action"""
        self._update_node("corrective_action", action_id, {
            "status": "in_progress",
            "started_by": started_by,
            "started_at": self._now()
        })

    def complete_corrective_action(
        self,
        action_id: str,
        completion_evidence: str,
        completed_by: str,
        effectiveness_verified: bool
    ):
        """Complete a corrective action"""
        self._update_node("corrective_action", action_id, {
            "status": "completed",
            "completion_evidence": completion_evidence,
            "completed_by": completed_by,
            "completed_at": self._now(),
            "effectiveness_verified": effectiveness_verified
        })

    def get_corrective_actions(
        self,
        incident_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get corrective actions for an incident"""
        actions = self._find_nodes("corrective_action", incident_id=incident_id)
        if status:
            actions = [a for a in actions if a.get("status") == status]
        return actions

    # =========================================================================
    # Impact Assessment
    # =========================================================================

    def assess_impact(
        self,
        incident_id: str,
        assessor: str,
        assessment_id: Optional[str] = None
    ) -> str:
        """Create an impact assessment"""
        aid = assessment_id or self._generate_id("ia")
        props = {
            "incident_id": incident_id,
            "assessor": assessor,
            "status": "in_progress",
            "started_at": self._now(),
            "impacts": [],
            "description": f"Impact assessment for {incident_id}"
        }
        return self._add_node("impact_assessment", aid, props)

    def add_impact(
        self,
        assessment_id: str,
        impact_category: str,  # safety, rights, financial, reputational, operational
        description: str,
        severity: str,  # low, medium, high, critical
        affected_count: Optional[int] = None,
        reversible: bool = True
    ):
        """Add an identified impact"""
        assessment = self._get_node("impact_assessment", assessment_id)
        if assessment:
            impacts = assessment.get("impacts", [])
            impacts.append({
                "category": impact_category,
                "description": description,
                "severity": severity,
                "affected_count": affected_count,
                "reversible": reversible,
                "added_at": self._now()
            })
            self._update_node("impact_assessment", assessment_id, {
                "impacts": impacts
            })

    def complete_impact_assessment(
        self,
        assessment_id: str,
        overall_impact_level: str,  # minimal, moderate, significant, severe
        summary: str,
        completed_by: str
    ) -> Dict[str, Any]:
        """Complete impact assessment"""
        self._update_node("impact_assessment", assessment_id, {
            "status": "completed",
            "overall_impact_level": overall_impact_level,
            "summary": summary,
            "completed_by": completed_by,
            "completed_at": self._now()
        })

        assessment = self._get_node("impact_assessment", assessment_id)
        return {
            "assessment_id": assessment_id,
            "overall_impact": overall_impact_level,
            "impacts_count": len(assessment.get("impacts", [])) if assessment else 0,
            "summary": summary
        }

    # =========================================================================
    # Deadline Monitoring
    # =========================================================================

    def get_approaching_deadlines(
        self,
        hours_ahead: int = 24
    ) -> List[Dict[str, Any]]:
        """Get incidents with approaching notification deadlines"""
        incidents = self._find_nodes("incident")
        now = datetime.fromisoformat(self._now().replace("+00:00", "").replace("Z", ""))
        threshold = (now + timedelta(hours=hours_ahead)).isoformat() + "+00:00"

        approaching = []
        for incident in incidents:
            if not incident.get("authority_notified") and incident.get("requires_authority_notification"):
                deadline = incident.get("reporting_deadline", "")
                if deadline and deadline <= threshold:
                    approaching.append(incident)

        return approaching

    def get_overdue_notifications(self) -> List[Dict[str, Any]]:
        """Get incidents with overdue notifications"""
        incidents = self._find_nodes("incident")
        now = self._now()

        overdue = []
        for incident in incidents:
            if not incident.get("authority_notified") and incident.get("requires_authority_notification"):
                deadline = incident.get("reporting_deadline", "")
                if deadline and deadline < now:
                    overdue.append(incident)

        return overdue

    # =========================================================================
    # Close Incident
    # =========================================================================

    def close_incident(
        self,
        incident_id: str,
        closure_reason: str,
        lessons_learned: List[str],
        closed_by: str
    ) -> Dict[str, Any]:
        """Close an incident"""
        incident = self.get_incident(incident_id)
        if not incident:
            return {"error": "Incident not found"}

        # Check all corrective actions are complete
        actions = self.get_corrective_actions(incident_id)
        incomplete = [a for a in actions if a.get("status") != "completed"]

        if incomplete:
            return {
                "success": False,
                "reason": "incomplete_actions",
                "incomplete_count": len(incomplete)
            }

        self._update_node("incident", incident_id, {
            "status": IncidentStatus.CLOSED.value,
            "closure_reason": closure_reason,
            "lessons_learned": lessons_learned,
            "closed_by": closed_by,
            "closed_at": self._now()
        })

        return {
            "success": True,
            "incident_id": incident_id,
            "status": IncidentStatus.CLOSED.value
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get incident reporting statistics"""
        base_stats = super().get_stats()
        incidents = self._find_nodes("incident")
        investigations = self._find_nodes("investigation")
        notifications = self._find_nodes("authority_notification")
        actions = self._find_nodes("corrective_action")

        # Count by severity
        by_severity = {}
        for sev in IncidentSeverity:
            count = len([i for i in incidents if i.get("severity") == sev.value])
            by_severity[sev.value] = count

        # Count by status
        by_status = {}
        for status in IncidentStatus:
            count = len([i for i in incidents if i.get("status") == status.value])
            by_status[status.value] = count

        return {
            **base_stats,
            "total_incidents": len(incidents),
            "incidents_by_severity": by_severity,
            "incidents_by_status": by_status,
            "open_incidents": len([i for i in incidents if i.get("status") != IncidentStatus.CLOSED.value]),
            "investigations": len(investigations),
            "completed_investigations": len([i for i in investigations if i.get("status") == "completed"]),
            "authority_notifications": len(notifications),
            "submitted_notifications": len([n for n in notifications if n.get("status") == "submitted"]),
            "overdue_notifications": len(self.get_overdue_notifications()),
            "corrective_actions": len(actions),
            "pending_actions": len([a for a in actions if a.get("status") != "completed"])
        }
