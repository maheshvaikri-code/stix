"""
Data Breach Store
=================

GDPR Data Breach notification and management (Articles 33-34).
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from .base import BaseGDPRStore
from ..schema import (
    BreachSeverity, BreachStatus, BreachType, PersonalDataCategory
)


class DataBreachStore(BaseGDPRStore):
    """
    Data Breach Management (GDPR Articles 33-34).

    Tracks:
    - Breach detection and investigation
    - Risk assessment
    - DPA notification (72 hours - Art 33)
    - Data subject notification (Art 34)
    - Remediation and lessons learned
    """

    def report_breach(
        self,
        description: str,
        breach_type: BreachType,
        detected_at: Optional[str] = None,
        detected_by: str = "",
        initial_assessment: str = "",
    ) -> str:
        """
        Report a data breach.

        72-hour clock starts from awareness of breach.

        Args:
            description: Description of the breach
            breach_type: Type of breach (confidentiality, integrity, availability)
            detected_at: When breach was detected (defaults to now)
            detected_by: Who detected the breach
            initial_assessment: Initial assessment of impact

        Returns:
            Breach ID
        """
        breach_id = self._make_id("breach", breach_type.value)

        detected = detected_at or self._now()
        # Art 33 - 72 hours to notify DPA
        dpa_deadline = (
            datetime.fromisoformat(detected) + timedelta(hours=72)
        ).isoformat()

        self.graph.add_node(
            "data_breach",
            breach_id,
            description=self._sanitize(description),
            breach_type=breach_type.value,
            status=BreachStatus.DETECTED.value,
            severity="",  # To be assessed
            detected_at=detected,
            detected_by=detected_by,
            initial_assessment=self._sanitize(initial_assessment),
            dpa_deadline=dpa_deadline,
            data_categories_affected="",
            subjects_affected_count="0",
            subjects_affected_estimated=str(False),
            cause="",
            containment_measures="",
            dpa_notification_required="",
            dpa_notified_at="",
            dpa_reference="",
            subject_notification_required="",
            subjects_notified_at="",
            remediation_actions="",
            lessons_learned="",
            closed_at="",
        )

        self._record_breach_event(breach_id, "breach_reported", description)

        return breach_id

    def update_investigation(
        self,
        breach_id: str,
        data_categories: List[PersonalDataCategory],
        subjects_affected_count: int,
        estimated: bool = False,
        cause: str = "",
        systems_affected: List[str] = None,
    ) -> Dict[str, Any]:
        """
        Update breach investigation findings.
        """
        node = self.graph.get_node("data_breach", breach_id)
        if not node:
            return {"error": "Breach not found"}

        categories = [c.value for c in data_categories]

        self.graph.update_node(
            "data_breach",
            breach_id,
            status=BreachStatus.INVESTIGATING.value,
            data_categories_affected=self._list_to_str(categories),
            subjects_affected_count=str(subjects_affected_count),
            subjects_affected_estimated=str(estimated),
            cause=self._sanitize(cause),
            systems_affected=self._list_to_str(systems_affected or []),
        )

        self._record_breach_event(
            breach_id,
            "investigation_updated",
            f"Affected: {subjects_affected_count} subjects, Categories: {categories}"
        )

        return {
            "breach_id": breach_id,
            "status": "investigation_updated",
        }

    def assess_severity(
        self,
        breach_id: str,
        severity: BreachSeverity,
        risk_assessment: str,
        dpa_notification_required: bool,
        subject_notification_required: bool,
    ) -> Dict[str, Any]:
        """
        Assess breach severity and notification requirements.

        Art 33: Notify DPA unless unlikely to result in risk
        Art 34: Notify subjects if high risk to rights/freedoms
        """
        node = self.graph.get_node("data_breach", breach_id)
        if not node:
            return {"error": "Breach not found"}

        self.graph.update_node(
            "data_breach",
            breach_id,
            status=BreachStatus.ASSESSED.value,
            severity=severity.value,
            risk_assessment=self._sanitize(risk_assessment),
            dpa_notification_required=str(dpa_notification_required),
            subject_notification_required=str(subject_notification_required),
            assessed_at=self._now(),
        )

        self._record_breach_event(
            breach_id,
            "severity_assessed",
            f"Severity: {severity.value}, DPA notify: {dpa_notification_required}"
        )

        return {
            "breach_id": breach_id,
            "severity": severity.value,
            "dpa_notification_required": dpa_notification_required,
            "subject_notification_required": subject_notification_required,
            "dpa_deadline": node.properties.get("dpa_deadline"),
        }

    def record_containment(
        self,
        breach_id: str,
        measures: List[str],
    ) -> Dict[str, Any]:
        """Record containment measures taken"""
        node = self.graph.get_node("data_breach", breach_id)
        if not node:
            return {"error": "Breach not found"}

        self.graph.update_node(
            "data_breach",
            breach_id,
            status=BreachStatus.CONTAINED.value,
            containment_measures=self._list_to_str(measures),
            contained_at=self._now(),
        )

        self._record_breach_event(
            breach_id,
            "breach_contained",
            ", ".join(measures)
        )

        return {
            "breach_id": breach_id,
            "status": "contained",
        }

    def notify_dpa(
        self,
        breach_id: str,
        notification_content: str,
        reference_number: str = "",
        notified_by: str = "",
    ) -> Dict[str, Any]:
        """
        Record DPA notification (Article 33).

        Must be done within 72 hours of becoming aware.
        """
        node = self.graph.get_node("data_breach", breach_id)
        if not node:
            return {"error": "Breach not found"}

        notified_at = self._now()
        deadline = node.properties.get("dpa_deadline", "")
        within_deadline = notified_at <= deadline if deadline else True

        self.graph.update_node(
            "data_breach",
            breach_id,
            status=BreachStatus.NOTIFIED_DPA.value,
            dpa_notified_at=notified_at,
            dpa_reference=reference_number,
            dpa_notification_content=self._sanitize(notification_content),
            dpa_notified_by=notified_by,
            dpa_within_deadline=str(within_deadline),
        )

        self._record_breach_event(
            breach_id,
            "dpa_notified",
            f"Reference: {reference_number}, Within deadline: {within_deadline}"
        )

        return {
            "breach_id": breach_id,
            "notified_at": notified_at,
            "within_deadline": within_deadline,
            "reference_number": reference_number,
        }

    def notify_subjects(
        self,
        breach_id: str,
        notification_method: str,
        notification_content: str,
        subjects_notified_count: int,
    ) -> Dict[str, Any]:
        """
        Record data subject notification (Article 34).

        Required when breach is likely to result in high risk.
        """
        node = self.graph.get_node("data_breach", breach_id)
        if not node:
            return {"error": "Breach not found"}

        self.graph.update_node(
            "data_breach",
            breach_id,
            status=BreachStatus.NOTIFIED_SUBJECTS.value,
            subjects_notified_at=self._now(),
            subject_notification_method=notification_method,
            subject_notification_content=self._sanitize(notification_content),
            subjects_notified_count=str(subjects_notified_count),
        )

        self._record_breach_event(
            breach_id,
            "subjects_notified",
            f"Method: {notification_method}, Count: {subjects_notified_count}"
        )

        return {
            "breach_id": breach_id,
            "status": "subjects_notified",
            "count": subjects_notified_count,
        }

    def record_remediation(
        self,
        breach_id: str,
        actions: List[str],
    ) -> Dict[str, Any]:
        """Record remediation actions"""
        node = self.graph.get_node("data_breach", breach_id)
        if not node:
            return {"error": "Breach not found"}

        self.graph.update_node(
            "data_breach",
            breach_id,
            status=BreachStatus.REMEDIATED.value,
            remediation_actions=self._list_to_str(actions),
            remediated_at=self._now(),
        )

        self._record_breach_event(
            breach_id,
            "remediation_completed",
            ", ".join(actions)
        )

        return {
            "breach_id": breach_id,
            "status": "remediated",
        }

    def close_breach(
        self,
        breach_id: str,
        lessons_learned: str,
        preventive_measures: List[str],
    ) -> Dict[str, Any]:
        """Close a breach record with lessons learned"""
        node = self.graph.get_node("data_breach", breach_id)
        if not node:
            return {"error": "Breach not found"}

        self.graph.update_node(
            "data_breach",
            breach_id,
            status=BreachStatus.CLOSED.value,
            lessons_learned=self._sanitize(lessons_learned),
            preventive_measures=self._list_to_str(preventive_measures),
            closed_at=self._now(),
        )

        self._record_breach_event(
            breach_id,
            "breach_closed",
            lessons_learned
        )

        return {
            "breach_id": breach_id,
            "status": "closed",
            "closed_at": self._now(),
        }

    def get_breach(self, breach_id: str) -> Optional[Dict[str, Any]]:
        """Get breach details"""
        node = self.graph.get_node("data_breach", breach_id)
        if node:
            return {
                "id": breach_id,
                **node.properties,
                "data_categories_affected": self._str_to_list(
                    node.properties.get("data_categories_affected", "")
                ),
                "containment_measures": self._str_to_list(
                    node.properties.get("containment_measures", "")
                ),
                "remediation_actions": self._str_to_list(
                    node.properties.get("remediation_actions", "")
                ),
            }
        return None

    def get_open_breaches(self) -> List[Dict[str, Any]]:
        """Get all open (non-closed) breaches"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "data_breach" and
                node.properties.get("status") != BreachStatus.CLOSED.value):
                results.append(self.get_breach(node.id))
        return results

    def get_breaches_pending_dpa_notification(self) -> List[Dict[str, Any]]:
        """Get breaches that need DPA notification"""
        results = []
        for node in self.graph.nodes():
            if node.type == "data_breach":
                if (node.properties.get("dpa_notification_required") == "True" and
                    not node.properties.get("dpa_notified_at")):
                    results.append(self.get_breach(node.id))
        return results

    def get_breaches_past_deadline(self) -> List[Dict[str, Any]]:
        """Get breaches past 72-hour DPA notification deadline"""
        now = self._now()
        results = []
        for node in self.graph.nodes():
            if node.type == "data_breach":
                deadline = node.properties.get("dpa_deadline", "")
                notified = node.properties.get("dpa_notified_at", "")
                required = node.properties.get("dpa_notification_required")

                if deadline and deadline < now and not notified and required == "True":
                    results.append(self.get_breach(node.id))
        return results

    def _record_breach_event(
        self,
        breach_id: str,
        event_type: str,
        details: str,
    ) -> None:
        """Record breach audit event"""
        event_id = self._make_id("breach_event", breach_id)
        self.graph.add_node(
            "breach_event",
            event_id,
            breach_id=breach_id,
            event_type=event_type,
            details=self._sanitize(details),
            timestamp=self._now(),
        )

        if self.graph.has_node("data_breach", breach_id):
            self.graph.add_edge(
                "BREACH_EVENT",
                ("data_breach", breach_id),
                ("breach_event", event_id),
            )

    def get_breach_history(self, breach_id: str) -> List[Dict[str, Any]]:
        """Get audit history for a breach"""
        events = []
        for node in self.graph.nodes():
            if (node.type == "breach_event" and
                node.properties.get("breach_id") == breach_id):
                events.append({"id": node.id, **node.properties})
        return sorted(events, key=lambda x: x.get("timestamp", ""))

    def get_stats(self) -> Dict[str, Any]:
        """Get breach statistics"""
        total = 0
        open_breaches = 0
        by_severity = {}
        by_type = {}
        dpa_notified = 0
        subjects_notified = 0
        total_subjects_affected = 0

        for node in self.graph.nodes():
            if node.type == "data_breach":
                total += 1

                if node.properties.get("status") != BreachStatus.CLOSED.value:
                    open_breaches += 1

                severity = node.properties.get("severity", "unassessed")
                by_severity[severity] = by_severity.get(severity, 0) + 1

                breach_type = node.properties.get("breach_type", "unknown")
                by_type[breach_type] = by_type.get(breach_type, 0) + 1

                if node.properties.get("dpa_notified_at"):
                    dpa_notified += 1

                if node.properties.get("subjects_notified_at"):
                    subjects_notified += 1

                count = node.properties.get("subjects_affected_count", "0")
                try:
                    total_subjects_affected += int(count)
                except ValueError:
                    pass

        return {
            "total_breaches": total,
            "open_breaches": open_breaches,
            "by_severity": by_severity,
            "by_type": by_type,
            "dpa_notifications": dpa_notified,
            "subject_notifications": subjects_notified,
            "total_subjects_affected": total_subjects_affected,
        }
