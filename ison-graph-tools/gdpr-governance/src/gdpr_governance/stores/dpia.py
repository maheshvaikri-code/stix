"""
DPIA Store
==========

Data Protection Impact Assessment management (Article 35).
"""

from typing import Any, Dict, List, Optional

from .base import BaseGDPRStore
from ..schema import DPIAStatus, DPIATrigger


class DPIAStore(BaseGDPRStore):
    """
    Data Protection Impact Assessment Management (GDPR Article 35).

    Tracks:
    - DPIA requirement assessment
    - Risk identification and mitigation
    - DPO consultation
    - Supervisory authority consultation (Art 36)
    """

    def create_dpia(
        self,
        processing_activity_id: str,
        name: str,
        triggers: List[DPIATrigger],
        description: str = "",
    ) -> str:
        """
        Create a new DPIA.

        Required when processing is likely to result in high risk.

        Args:
            processing_activity_id: Related processing activity
            name: Name of the DPIA
            triggers: Triggers that require this DPIA
            description: Description of the processing

        Returns:
            DPIA ID
        """
        dpia_id = self._make_id("dpia", name)

        self.graph.add_node(
            "dpia",
            dpia_id,
            name=name,
            processing_activity_id=processing_activity_id,
            status=DPIAStatus.REQUIRED.value,
            triggers=self._list_to_str([t.value for t in triggers]),
            description=self._sanitize(description),
            necessity_assessment="",
            proportionality_assessment="",
            risks_identified="",
            mitigations="",
            residual_risk_level="",
            dpo_consulted=str(False),
            dpo_opinion="",
            consultation_required=str(False),
            consultation_response="",
            created_at=self._now(),
            updated_at=self._now(),
            completed_at="",
            approved_by="",
            next_review="",
        )

        # Link to processing activity
        if self.graph.has_node("processing_activity", processing_activity_id):
            self.graph.add_edge(
                "DPIA_FOR",
                ("dpia", dpia_id),
                ("processing_activity", processing_activity_id),
            )

        self._record_dpia_event(dpia_id, "dpia_created", f"Triggers: {triggers}")

        return dpia_id

    def start_assessment(
        self,
        dpia_id: str,
        assessor: str,
    ) -> Dict[str, Any]:
        """Start the DPIA assessment process"""
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return {"error": "DPIA not found"}

        self.graph.update_node(
            "dpia",
            dpia_id,
            status=DPIAStatus.IN_PROGRESS.value,
            assessor=assessor,
            started_at=self._now(),
            updated_at=self._now(),
        )

        self._record_dpia_event(dpia_id, "assessment_started", f"Assessor: {assessor}")

        return {
            "dpia_id": dpia_id,
            "status": "in_progress",
        }

    def document_necessity(
        self,
        dpia_id: str,
        necessity_assessment: str,
        proportionality_assessment: str,
    ) -> Dict[str, Any]:
        """
        Document necessity and proportionality assessment.

        Required elements under Art 35(7)(a)(b).
        """
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return {"error": "DPIA not found"}

        self.graph.update_node(
            "dpia",
            dpia_id,
            necessity_assessment=self._sanitize(necessity_assessment),
            proportionality_assessment=self._sanitize(proportionality_assessment),
            updated_at=self._now(),
        )

        self._record_dpia_event(
            dpia_id,
            "necessity_documented",
            "Necessity and proportionality assessed"
        )

        return {
            "dpia_id": dpia_id,
            "status": "necessity_documented",
        }

    def add_risk(
        self,
        dpia_id: str,
        risk_description: str,
        likelihood: str,  # low, medium, high
        impact: str,      # low, medium, high
        affected_rights: List[str],
    ) -> str:
        """
        Add an identified risk.

        Art 35(7)(c) - assessment of risks to rights and freedoms.
        """
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return ""

        risk_id = self._make_id("risk", dpia_id)

        self.graph.add_node(
            "dpia_risk",
            risk_id,
            dpia_id=dpia_id,
            description=self._sanitize(risk_description),
            likelihood=likelihood,
            impact=impact,
            risk_level=self._calculate_risk_level(likelihood, impact),
            affected_rights=self._list_to_str(affected_rights),
            mitigated=str(False),
            mitigation_id="",
            created_at=self._now(),
        )

        self.graph.add_edge(
            "HAS_RISK",
            ("dpia", dpia_id),
            ("dpia_risk", risk_id),
        )

        self._record_dpia_event(
            dpia_id,
            "risk_identified",
            f"Risk: {risk_description[:100]}"
        )

        return risk_id

    def _calculate_risk_level(self, likelihood: str, impact: str) -> str:
        """Calculate overall risk level"""
        levels = {"low": 1, "medium": 2, "high": 3}
        score = levels.get(likelihood, 2) * levels.get(impact, 2)
        if score <= 2:
            return "low"
        elif score <= 4:
            return "medium"
        else:
            return "high"

    def add_mitigation(
        self,
        dpia_id: str,
        risk_id: str,
        mitigation_description: str,
        mitigation_type: str,  # technical, organizational, policy
        residual_risk: str,    # low, medium, high
    ) -> str:
        """
        Add mitigation measure for a risk.

        Art 35(7)(d) - measures to address risks.
        """
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return ""

        mitigation_id = self._make_id("mitigation", risk_id)

        self.graph.add_node(
            "dpia_mitigation",
            mitigation_id,
            dpia_id=dpia_id,
            risk_id=risk_id,
            description=self._sanitize(mitigation_description),
            mitigation_type=mitigation_type,
            residual_risk=residual_risk,
            implemented=str(False),
            created_at=self._now(),
        )

        self.graph.add_edge(
            "MITIGATES",
            ("dpia_mitigation", mitigation_id),
            ("dpia_risk", risk_id),
        )

        # Update risk as mitigated
        if self.graph.has_node("dpia_risk", risk_id):
            self.graph.update_node(
                "dpia_risk",
                risk_id,
                mitigated=str(True),
                mitigation_id=mitigation_id,
            )

        self._record_dpia_event(
            dpia_id,
            "mitigation_added",
            f"For risk {risk_id}: {mitigation_description[:100]}"
        )

        return mitigation_id

    def consult_dpo(
        self,
        dpia_id: str,
        dpo_name: str,
        dpo_opinion: str,
        recommendation: str,  # approve, modify, reject
    ) -> Dict[str, Any]:
        """Record DPO consultation"""
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return {"error": "DPIA not found"}

        self.graph.update_node(
            "dpia",
            dpia_id,
            dpo_consulted=str(True),
            dpo_name=dpo_name,
            dpo_opinion=self._sanitize(dpo_opinion),
            dpo_recommendation=recommendation,
            dpo_consulted_at=self._now(),
            updated_at=self._now(),
        )

        self._record_dpia_event(
            dpia_id,
            "dpo_consulted",
            f"DPO: {dpo_name}, Recommendation: {recommendation}"
        )

        return {
            "dpia_id": dpia_id,
            "dpo_recommendation": recommendation,
        }

    def request_consultation(
        self,
        dpia_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Mark DPIA as requiring supervisory authority consultation.

        Art 36 - prior consultation required when high residual risk.
        """
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return {"error": "DPIA not found"}

        self.graph.update_node(
            "dpia",
            dpia_id,
            status=DPIAStatus.CONSULTATION_REQUIRED.value,
            consultation_required=str(True),
            consultation_reason=reason,
            updated_at=self._now(),
        )

        self._record_dpia_event(
            dpia_id,
            "consultation_required",
            reason
        )

        return {
            "dpia_id": dpia_id,
            "status": "consultation_required",
        }

    def record_consultation_response(
        self,
        dpia_id: str,
        response: str,
        reference: str = "",
    ) -> Dict[str, Any]:
        """Record supervisory authority consultation response"""
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return {"error": "DPIA not found"}

        self.graph.update_node(
            "dpia",
            dpia_id,
            consultation_response=self._sanitize(response),
            consultation_reference=reference,
            consultation_response_at=self._now(),
            updated_at=self._now(),
        )

        self._record_dpia_event(
            dpia_id,
            "consultation_response",
            f"Reference: {reference}"
        )

        return {
            "dpia_id": dpia_id,
            "consultation_response": response,
        }

    def complete_dpia(
        self,
        dpia_id: str,
        residual_risk_level: str,
        approved_by: str,
        next_review_days: int = 365,
    ) -> Dict[str, Any]:
        """Complete the DPIA"""
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return {"error": "DPIA not found"}

        self.graph.update_node(
            "dpia",
            dpia_id,
            status=DPIAStatus.COMPLETED.value,
            residual_risk_level=residual_risk_level,
            approved_by=approved_by,
            completed_at=self._now(),
            next_review=self._deadline(next_review_days),
            updated_at=self._now(),
        )

        self._record_dpia_event(
            dpia_id,
            "dpia_completed",
            f"Residual risk: {residual_risk_level}, Approved by: {approved_by}"
        )

        return {
            "dpia_id": dpia_id,
            "status": "completed",
            "residual_risk_level": residual_risk_level,
            "next_review": self._deadline(next_review_days),
        }

    def get_dpia(self, dpia_id: str) -> Optional[Dict[str, Any]]:
        """Get DPIA details"""
        node = self.graph.get_node("dpia", dpia_id)
        if not node:
            return None

        # Get associated risks
        risks = []
        for n in self.graph.nodes():
            if n.type == "dpia_risk" and n.properties.get("dpia_id") == dpia_id:
                risks.append({"id": n.id, **n.properties})

        # Get associated mitigations
        mitigations = []
        for n in self.graph.nodes():
            if n.type == "dpia_mitigation" and n.properties.get("dpia_id") == dpia_id:
                mitigations.append({"id": n.id, **n.properties})

        return {
            "id": dpia_id,
            **node.properties,
            "triggers": self._str_to_list(node.properties.get("triggers", "")),
            "risks": risks,
            "mitigations": mitigations,
        }

    def get_dpias_by_status(
        self,
        status: DPIAStatus
    ) -> List[Dict[str, Any]]:
        """Get DPIAs by status"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "dpia" and
                node.properties.get("status") == status.value):
                results.append(self.get_dpia(node.id))
        return results

    def get_dpias_due_for_review(self) -> List[Dict[str, Any]]:
        """Get DPIAs past their review date"""
        now = self._now()
        results = []
        for node in self.graph.nodes():
            if node.type == "dpia":
                next_review = node.properties.get("next_review", "")
                if next_review and next_review < now:
                    results.append(self.get_dpia(node.id))
        return results

    def _record_dpia_event(
        self,
        dpia_id: str,
        event_type: str,
        details: str,
    ) -> None:
        """Record DPIA audit event"""
        event_id = self._make_id("dpia_event", dpia_id)
        self.graph.add_node(
            "dpia_event",
            event_id,
            dpia_id=dpia_id,
            event_type=event_type,
            details=self._sanitize(details),
            timestamp=self._now(),
        )

        if self.graph.has_node("dpia", dpia_id):
            self.graph.add_edge(
                "DPIA_EVENT",
                ("dpia", dpia_id),
                ("dpia_event", event_id),
            )

    def get_dpia_history(self, dpia_id: str) -> List[Dict[str, Any]]:
        """Get audit history for a DPIA"""
        events = []
        for node in self.graph.nodes():
            if (node.type == "dpia_event" and
                node.properties.get("dpia_id") == dpia_id):
                events.append({"id": node.id, **node.properties})
        return sorted(events, key=lambda x: x.get("timestamp", ""))

    def get_stats(self) -> Dict[str, Any]:
        """Get DPIA statistics"""
        total = 0
        by_status = {}
        high_residual_risk = 0
        consultation_required = 0
        due_for_review = 0

        now = self._now()

        for node in self.graph.nodes():
            if node.type == "dpia":
                total += 1

                status = node.properties.get("status", "unknown")
                by_status[status] = by_status.get(status, 0) + 1

                if node.properties.get("residual_risk_level") == "high":
                    high_residual_risk += 1

                if node.properties.get("consultation_required") == "True":
                    consultation_required += 1

                next_review = node.properties.get("next_review", "")
                if next_review and next_review < now:
                    due_for_review += 1

        return {
            "total_dpias": total,
            "by_status": by_status,
            "high_residual_risk": high_residual_risk,
            "consultation_required": consultation_required,
            "due_for_review": due_for_review,
        }
