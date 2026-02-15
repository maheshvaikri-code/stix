"""
Data Subject Rights Store
=========================

GDPR Data Subject Rights management (Articles 15-22).
"""

from typing import Any, Dict, List, Optional

from .base import BaseGDPRStore
from ..schema import (
    DataSubjectRight, RightRequestStatus, RefusalReason
)


class DataSubjectRightsStore(BaseGDPRStore):
    """
    Data Subject Rights Management (GDPR Articles 15-22).

    Tracks:
    - Right of access requests (Art 15)
    - Right to rectification (Art 16)
    - Right to erasure (Art 17)
    - Right to restriction (Art 18)
    - Right to data portability (Art 20)
    - Right to object (Art 21)
    - Rights related to automated decision-making (Art 22)
    """

    def submit_request(
        self,
        data_subject_id: str,
        right_type: DataSubjectRight,
        details: str = "",
        submitted_via: str = "online_form",
    ) -> str:
        """
        Submit a data subject rights request.

        Under Article 12, controller must respond within 1 month.

        Args:
            data_subject_id: ID of the data subject
            right_type: Type of right being exercised
            details: Additional details about the request
            submitted_via: How the request was submitted

        Returns:
            Request ID
        """
        request_id = self._make_id("dsr", f"{data_subject_id}_{right_type.value}")

        self.graph.add_node(
            "right_request",
            request_id,
            data_subject_id=data_subject_id,
            right_type=right_type.value,
            status=RightRequestStatus.RECEIVED.value,
            details=self._sanitize(details),
            submitted_via=submitted_via,
            received_at=self._now(),
            deadline=self._deadline(30),  # Art 12(3) - 1 month
            identity_verified=str(False),
            extended=str(False),
            extension_deadline="",
            completed_at="",
            response="",
            refused_reason="",
        )

        # Link to data subject
        subject_node_id = f"subject_{data_subject_id}"
        if self.graph.has_node("data_subject", subject_node_id):
            self.graph.add_edge(
                "HAS_REQUEST",
                ("data_subject", subject_node_id),
                ("right_request", request_id),
            )

        # Record event
        self._record_request_event(request_id, "request_received", details)

        return request_id

    def verify_identity(
        self,
        request_id: str,
        verification_method: str,
        verified_by: str,
    ) -> Dict[str, Any]:
        """
        Verify identity of data subject for a request.

        Required before processing most requests.
        """
        node = self.graph.get_node("right_request", request_id)
        if not node:
            return {"error": "Request not found"}

        self.graph.update_node(
            "right_request",
            request_id,
            identity_verified=str(True),
            verification_method=verification_method,
            verified_by=verified_by,
            verified_at=self._now(),
            status=RightRequestStatus.IN_PROGRESS.value,
        )

        self._record_request_event(
            request_id,
            "identity_verified",
            f"Method: {verification_method}, By: {verified_by}"
        )

        return {
            "request_id": request_id,
            "status": "identity_verified",
            "next_step": "process_request",
        }

    def extend_deadline(
        self,
        request_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Extend deadline by 2 months (Article 12(3)).

        Can only be done once due to complexity of request.
        """
        node = self.graph.get_node("right_request", request_id)
        if not node:
            return {"error": "Request not found"}

        if node.properties.get("extended") == "True":
            return {"error": "Deadline already extended"}

        new_deadline = self._deadline(60)  # Additional 2 months

        self.graph.update_node(
            "right_request",
            request_id,
            extended=str(True),
            extension_reason=reason,
            extension_deadline=new_deadline,
            status=RightRequestStatus.EXTENDED.value,
        )

        self._record_request_event(request_id, "deadline_extended", reason)

        return {
            "request_id": request_id,
            "new_deadline": new_deadline,
            "reason": reason,
        }

    def complete_request(
        self,
        request_id: str,
        response: str,
        actions_taken: List[str],
    ) -> Dict[str, Any]:
        """
        Complete a data subject request.

        Args:
            request_id: Request ID
            response: Response provided to data subject
            actions_taken: List of actions taken to fulfill request
        """
        node = self.graph.get_node("right_request", request_id)
        if not node:
            return {"error": "Request not found"}

        self.graph.update_node(
            "right_request",
            request_id,
            status=RightRequestStatus.COMPLETED.value,
            completed_at=self._now(),
            response=self._sanitize(response),
            actions_taken=self._list_to_str(actions_taken),
        )

        self._record_request_event(request_id, "request_completed", response)

        return {
            "request_id": request_id,
            "status": "completed",
            "completed_at": self._now(),
            "right_type": node.properties.get("right_type"),
        }

    def refuse_request(
        self,
        request_id: str,
        reason: RefusalReason,
        explanation: str,
    ) -> Dict[str, Any]:
        """
        Refuse a data subject request.

        Must provide reasons for refusal (Article 12(4)).
        """
        node = self.graph.get_node("right_request", request_id)
        if not node:
            return {"error": "Request not found"}

        self.graph.update_node(
            "right_request",
            request_id,
            status=RightRequestStatus.REFUSED.value,
            refused_reason=reason.value,
            refused_explanation=self._sanitize(explanation),
            completed_at=self._now(),
        )

        self._record_request_event(
            request_id,
            "request_refused",
            f"{reason.value}: {explanation}"
        )

        return {
            "request_id": request_id,
            "status": "refused",
            "reason": reason.value,
            "explanation": explanation,
        }

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a request"""
        node = self.graph.get_node("right_request", request_id)
        if node:
            return {"id": request_id, **node.properties}
        return None

    def get_subject_requests(
        self,
        data_subject_id: str,
        status: Optional[RightRequestStatus] = None,
    ) -> List[Dict[str, Any]]:
        """Get all requests for a data subject"""
        results = []
        for node in self.graph.nodes():
            if node.type == "right_request":
                if node.properties.get("data_subject_id") == data_subject_id:
                    if status and node.properties.get("status") != status.value:
                        continue
                    results.append({"id": node.id, **node.properties})
        return results

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending requests (not completed or refused)"""
        pending_statuses = {
            RightRequestStatus.RECEIVED.value,
            RightRequestStatus.IDENTITY_VERIFICATION.value,
            RightRequestStatus.IN_PROGRESS.value,
            RightRequestStatus.EXTENDED.value,
        }
        results = []
        for node in self.graph.nodes():
            if (node.type == "right_request" and
                node.properties.get("status") in pending_statuses):
                results.append({"id": node.id, **node.properties})
        return results

    def get_overdue_requests(self) -> List[Dict[str, Any]]:
        """Get requests past their deadline"""
        now = self._now()
        results = []
        for node in self.graph.nodes():
            if node.type == "right_request":
                status = node.properties.get("status")
                if status in [RightRequestStatus.COMPLETED.value,
                             RightRequestStatus.REFUSED.value]:
                    continue

                deadline = node.properties.get("extension_deadline") or \
                          node.properties.get("deadline", "")
                if deadline and deadline < now:
                    results.append({"id": node.id, **node.properties})
        return results

    def get_requests_by_type(
        self,
        right_type: DataSubjectRight
    ) -> List[Dict[str, Any]]:
        """Get all requests of a specific type"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "right_request" and
                node.properties.get("right_type") == right_type.value):
                results.append({"id": node.id, **node.properties})
        return results

    def _record_request_event(
        self,
        request_id: str,
        event_type: str,
        details: str,
    ) -> None:
        """Record request audit event"""
        event_id = self._make_id("dsr_event", request_id)
        self.graph.add_node(
            "right_request_event",
            event_id,
            request_id=request_id,
            event_type=event_type,
            details=self._sanitize(details),
            timestamp=self._now(),
        )

        if self.graph.has_node("right_request", request_id):
            self.graph.add_edge(
                "REQUEST_EVENT",
                ("right_request", request_id),
                ("right_request_event", event_id),
            )

    def get_request_history(self, request_id: str) -> List[Dict[str, Any]]:
        """Get audit history for a request"""
        events = []
        for node in self.graph.nodes():
            if (node.type == "right_request_event" and
                node.properties.get("request_id") == request_id):
                events.append({"id": node.id, **node.properties})
        return sorted(events, key=lambda x: x.get("timestamp", ""))

    def get_stats(self) -> Dict[str, Any]:
        """Get data subject rights statistics"""
        total = 0
        pending = 0
        completed = 0
        refused = 0
        overdue = 0
        by_type = {}
        avg_completion_days = []

        now = self._now()

        for node in self.graph.nodes():
            if node.type == "right_request":
                total += 1
                status = node.properties.get("status")

                if status == RightRequestStatus.COMPLETED.value:
                    completed += 1
                    # Calculate completion time
                    received = node.properties.get("received_at", "")
                    completed_at = node.properties.get("completed_at", "")
                    if received and completed_at:
                        # Simplified - just count as completed
                        pass
                elif status == RightRequestStatus.REFUSED.value:
                    refused += 1
                else:
                    pending += 1
                    deadline = node.properties.get("extension_deadline") or \
                              node.properties.get("deadline", "")
                    if deadline and deadline < now:
                        overdue += 1

                right_type = node.properties.get("right_type", "unknown")
                by_type[right_type] = by_type.get(right_type, 0) + 1

        return {
            "total_requests": total,
            "pending_requests": pending,
            "completed_requests": completed,
            "refused_requests": refused,
            "overdue_requests": overdue,
            "by_type": by_type,
        }
