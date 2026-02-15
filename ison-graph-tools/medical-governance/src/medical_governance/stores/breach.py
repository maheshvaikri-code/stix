"""
Breach Notification Store
=========================

Manages breach detection, assessment, and notification per HIPAA 45 CFR 164.400-414.
Implements the 60-day notification rule and harm assessment.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import BreachStatus, BreachSeverity, NotificationRecipient

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class BreachStore(BaseStore):
    """Store for breach notification governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "breach")

    # =========================================================================
    # Potential Breach Management
    # =========================================================================

    def report_potential_breach(
        self,
        discovered_by: str,
        description: str,
        affected_count: int = 0,
        phi_types: Optional[List[str]] = None,
        breach_id: Optional[str] = None
    ) -> str:
        """Report a potential breach"""
        bid = breach_id or self._generate_id("pb")
        props = {
            "discovered_date": self._now(),
            "discovered_by": discovered_by,
            "description": description,
            "affected_count": affected_count,
            "phi_types": phi_types or [],
            "status": BreachStatus.REPORTED.value,
            "notification_deadline": self._calculate_deadline(60),
            "description": f"Potential breach: {description[:50]}"
        }
        return self._add_node("potential_breach", bid, props)

    def _calculate_deadline(self, days: int) -> str:
        """Calculate deadline from now"""
        from datetime import datetime, timedelta
        deadline = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) +
            timedelta(days=days)
        )
        return deadline.isoformat() + "+00:00"

    def get_breach(self, breach_id: str) -> Optional[Dict[str, Any]]:
        """Get breach by ID"""
        return self._get_node("potential_breach", breach_id)

    def update_breach_status(self, breach_id: str, status: BreachStatus):
        """Update breach status"""
        self._update_node("potential_breach", breach_id, {
            "status": status.value
        })

    def list_breaches(
        self,
        status: Optional[BreachStatus] = None
    ) -> List[Dict[str, Any]]:
        """List breaches with optional status filter"""
        breaches = self._find_nodes("potential_breach")
        if status:
            breaches = [b for b in breaches if b.get("status") == status.value]
        return breaches

    # =========================================================================
    # Breach Assessment
    # =========================================================================

    def add_assessment(
        self,
        breach_id: str,
        assessor: str,
        is_breach: bool,
        risk_level: BreachSeverity,
        factors: Dict[str, Any]
    ) -> str:
        """Add breach risk assessment"""
        aid = self._generate_id("ba")
        props = {
            "breach_id": breach_id,
            "assessment_date": self._now(),
            "assessor": assessor,
            "is_breach": is_breach,
            "risk_level": risk_level.value,
            "factors": factors,
            "description": f"Breach assessment for {breach_id}"
        }
        self._add_node("breach_assessment", aid, props)

        # Update breach status
        self.update_breach_status(
            breach_id,
            BreachStatus.CONFIRMED if is_breach else BreachStatus.NOT_BREACH
        )

        return aid

    def get_assessment(self, breach_id: str) -> Optional[Dict[str, Any]]:
        """Get assessment for a breach"""
        assessments = self._find_nodes("breach_assessment", breach_id=breach_id)
        return assessments[0] if assessments else None

    def add_harm_analysis(
        self,
        breach_id: str,
        harm_factor: str,
        probability: str,
        impact: str
    ) -> str:
        """Add harm factor analysis"""
        hid = self._generate_id("ha")
        props = {
            "breach_id": breach_id,
            "harm_factor": harm_factor,
            "probability": probability,
            "impact": impact,
            "description": f"Harm analysis: {harm_factor}"
        }
        return self._add_node("harm_analysis", hid, props)

    def get_harm_analyses(self, breach_id: str) -> List[Dict[str, Any]]:
        """Get harm analyses for a breach"""
        return self._find_nodes("harm_analysis", breach_id=breach_id)

    # =========================================================================
    # Four-Factor Risk Assessment
    # =========================================================================

    def perform_four_factor_assessment(
        self,
        breach_id: str,
        phi_nature: Dict[str, Any],
        unauthorized_person: Dict[str, Any],
        acquired_viewed: Dict[str, Any],
        risk_mitigated: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Perform HIPAA four-factor risk assessment:
        1. Nature and extent of PHI involved
        2. Unauthorized person who used/received PHI
        3. Whether PHI was actually acquired or viewed
        4. Extent to which risk has been mitigated
        """
        # Store factor analysis
        self.add_breach_factor(breach_id, "phi_nature", phi_nature)
        self.add_breach_factor(breach_id, "unauthorized_person", unauthorized_person)
        self.add_breach_factor(breach_id, "acquired_viewed", acquired_viewed)
        self.add_breach_factor(breach_id, "risk_mitigated", risk_mitigated)

        # Calculate risk score
        risk_score = 0.0

        # Factor 1: PHI nature (higher score = higher risk)
        if phi_nature.get("includes_financial"):
            risk_score += 0.3
        if phi_nature.get("includes_clinical"):
            risk_score += 0.2
        if phi_nature.get("includes_identifiers"):
            risk_score += 0.3

        # Factor 2: Unauthorized person
        if unauthorized_person.get("known"):
            risk_score -= 0.1
        if unauthorized_person.get("has_obligation"):
            risk_score -= 0.1

        # Factor 3: Acquired/viewed
        if not acquired_viewed.get("evidence_of_access"):
            risk_score -= 0.2
        if acquired_viewed.get("encryption_protected"):
            risk_score -= 0.3

        # Factor 4: Mitigation
        mitigation = float(risk_mitigated.get("effectiveness", 0))
        risk_score -= mitigation * 0.3

        # Determine if breach notification required
        # Per HIPAA: "low probability of compromise" = no notification
        notification_required = risk_score > 0.2

        return {
            "breach_id": breach_id,
            "risk_score": max(0, min(1, risk_score)),
            "notification_required": notification_required,
            "determination": "breach" if notification_required else "not_breach",
            "factors_analyzed": 4
        }

    def add_breach_factor(
        self,
        breach_id: str,
        factor_type: str,
        analysis: Dict[str, Any]
    ) -> str:
        """Add a factor analysis to breach assessment"""
        fid = self._generate_id("bf")
        props = {
            "breach_id": breach_id,
            "factor_type": factor_type,
            "analysis": analysis,
            "weight": analysis.get("weight", 0.25),
            "description": f"Breach factor: {factor_type}"
        }
        return self._add_node("breach_factor", fid, props)

    # =========================================================================
    # Affected Individuals
    # =========================================================================

    def add_affected_individuals(
        self,
        breach_id: str,
        count: int,
        identification_method: str,
        phi_types_exposed: List[str]
    ) -> str:
        """Record affected individuals"""
        aiid = self._generate_id("ai")
        props = {
            "breach_id": breach_id,
            "count": count,
            "identification_method": identification_method,
            "phi_types_exposed": phi_types_exposed,
            "description": f"Affected individuals: {count}"
        }
        self._add_node("affected_individuals", aiid, props)

        # Update breach record
        self._update_node("potential_breach", breach_id, {
            "affected_count": count
        })

        return aiid

    # =========================================================================
    # Notification Management
    # =========================================================================

    def add_notification_requirement(
        self,
        breach_id: str,
        recipient: NotificationRecipient,
        deadline: str,
        required: bool = True
    ) -> str:
        """Add a notification requirement"""
        nid = self._generate_id("nr")
        props = {
            "breach_id": breach_id,
            "recipient": recipient.value,
            "deadline": deadline,
            "required": required,
            "status": "pending" if required else "not_required",
            "description": f"Notification to {recipient.value}"
        }
        return self._add_node("notification_requirement", nid, props)

    def complete_notification(
        self,
        notification_id: str,
        notification_date: str,
        method: str
    ):
        """Record notification completion"""
        self._update_node("notification_requirement", notification_id, {
            "status": "complete",
            "notification_date": notification_date,
            "method": method
        })

    def get_notification_requirements(self, breach_id: str) -> List[Dict[str, Any]]:
        """Get notification requirements for a breach"""
        return self._find_nodes("notification_requirement", breach_id=breach_id)

    def get_pending_notifications(self) -> List[Dict[str, Any]]:
        """Get all pending notifications"""
        return self._find_nodes("notification_requirement", status="pending")

    def check_notification_deadlines(self) -> List[Dict[str, Any]]:
        """Check for overdue notifications"""
        pending = self.get_pending_notifications()
        now = self._now()

        overdue = []
        upcoming = []

        for n in pending:
            deadline = n.get("deadline", "")
            if deadline < now:
                overdue.append(n)
            elif deadline < self._calculate_deadline(7):
                upcoming.append(n)

        return {
            "overdue": overdue,
            "upcoming_7_days": upcoming
        }

    # =========================================================================
    # Notification Content
    # =========================================================================

    def add_notification_content(
        self,
        notification_id: str,
        content_element: str,
        included: bool
    ):
        """Record notification content element"""
        ncid = self._generate_id("nc")
        props = {
            "notification_id": notification_id,
            "content_element": content_element,
            "included": included,
            "description": f"Notification content: {content_element}"
        }
        self._add_node("notification_content", ncid, props)

    def verify_notification_content(self, notification_id: str) -> Dict[str, Any]:
        """Verify notification has all required content"""
        required_elements = [
            "description_of_breach",
            "phi_types_involved",
            "steps_to_protect",
            "our_mitigation_steps",
            "contact_information"
        ]

        contents = self._find_nodes("notification_content", notification_id=notification_id)
        included = [c.get("content_element") for c in contents if c.get("included")]

        missing = [e for e in required_elements if e not in included]

        return {
            "complete": len(missing) == 0,
            "required_elements": required_elements,
            "included_elements": included,
            "missing_elements": missing
        }

    # =========================================================================
    # Mitigation Actions
    # =========================================================================

    def add_mitigation_action(
        self,
        breach_id: str,
        action: str,
        effectiveness: str,
        date: Optional[str] = None
    ) -> str:
        """Record a mitigation action"""
        mid = self._generate_id("ma")
        props = {
            "breach_id": breach_id,
            "action": action,
            "effectiveness": effectiveness,
            "date": date or self._now(),
            "description": f"Mitigation: {action}"
        }
        return self._add_node("mitigation_action", mid, props)

    def get_mitigation_actions(self, breach_id: str) -> List[Dict[str, Any]]:
        """Get mitigation actions for a breach"""
        return self._find_nodes("mitigation_action", breach_id=breach_id)

    # =========================================================================
    # Root Cause Analysis
    # =========================================================================

    def add_root_cause(
        self,
        breach_id: str,
        cause_type: str,  # policy, training, technical, etc.
        root_cause: str,
        corrective_action: str
    ) -> str:
        """Add root cause analysis"""
        rcid = self._generate_id("rc")
        props = {
            "breach_id": breach_id,
            "cause_type": cause_type,
            "root_cause": root_cause,
            "corrective_action": corrective_action,
            "status": "identified",
            "description": f"Root cause: {cause_type}"
        }
        return self._add_node("root_cause", rcid, props)

    def complete_corrective_action(self, root_cause_id: str, completion_notes: str):
        """Mark corrective action as complete"""
        self._update_node("root_cause", root_cause_id, {
            "status": "corrected",
            "completed_at": self._now(),
            "completion_notes": completion_notes
        })

    # =========================================================================
    # Documentation
    # =========================================================================

    def add_documentation(
        self,
        breach_id: str,
        document_type: str,
        location: str,
        retention: str = "6_years"
    ) -> str:
        """Add breach documentation reference"""
        did = self._generate_id("doc")
        props = {
            "breach_id": breach_id,
            "document_type": document_type,
            "location": location,
            "retention": retention,
            "created_at": self._now(),
            "description": f"Documentation: {document_type}"
        }
        return self._add_node("breach_documentation", did, props)

    def get_documentation(self, breach_id: str) -> List[Dict[str, Any]]:
        """Get documentation for a breach"""
        return self._find_nodes("breach_documentation", breach_id=breach_id)

    # =========================================================================
    # HHS Reporting
    # =========================================================================

    def submit_to_hhs(
        self,
        breach_id: str,
        submission_date: str,
        affected_count: int
    ) -> str:
        """Record HHS submission"""
        submission_type = "annual" if affected_count < 500 else "immediate"

        sid = self._generate_id("hhs")
        props = {
            "breach_id": breach_id,
            "submission_date": submission_date,
            "submission_type": submission_type,
            "affected_count": affected_count,
            "status": "submitted",
            "description": f"HHS submission: {submission_type}"
        }
        return self._add_node("hhs_submission", sid, props)

    def get_hhs_submissions(self, year: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get HHS submissions"""
        submissions = self._find_nodes("hhs_submission")
        if year:
            submissions = [s for s in submissions if s.get("submission_date", "").startswith(year)]
        return submissions

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get breach statistics"""
        base_stats = super().get_stats()
        breaches = self._find_nodes("potential_breach")
        assessments = self._find_nodes("breach_assessment")
        notifications = self._find_nodes("notification_requirement")

        by_status = {}
        for b in breaches:
            status = b.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        confirmed = len([a for a in assessments if a.get("is_breach")])
        total_affected = sum(int(b.get("affected_count", 0)) for b in breaches)

        return {
            **base_stats,
            "total_breaches": len(breaches),
            "by_status": by_status,
            "confirmed_breaches": confirmed,
            "total_affected": total_affected,
            "notifications": len(notifications),
            "pending_notifications": len([n for n in notifications if n.get("status") == "pending"])
        }
