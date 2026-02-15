"""
Consumer Rights Store
=====================

CCPA/CPRA Consumer Rights request management.
"""

from typing import Any, Dict, List, Optional

from .base import BaseCCPAStore
from ..schema import (
    ConsumerRight, RequestStatus, DenialReason
)


class ConsumerRightsStore(BaseCCPAStore):
    """
    Consumer Rights Request Management.

    Handles:
    - Right to Know (categories and specific pieces)
    - Right to Delete
    - Right to Correct (CPRA)
    - Right to Opt-Out (handled by ConsumerStore)
    - Right to Limit Sensitive PI (CPRA)
    - Right to Data Portability

    Response deadlines:
    - 45 days from receipt (can extend additional 45 days)
    """

    def submit_request(
        self,
        consumer_id: str,
        right_type: ConsumerRight,
        details: str = "",
        submitted_via: str = "website",
        authorized_agent: bool = False,
        agent_authorization: str = "",
    ) -> str:
        """
        Submit a consumer rights request.

        Args:
            consumer_id: Consumer ID
            right_type: Type of right being exercised
            details: Additional request details
            submitted_via: Submission method
            authorized_agent: Whether submitted via authorized agent
            agent_authorization: Agent authorization documentation

        Returns:
            Request ID
        """
        request_id = self._make_id("request", f"{consumer_id}_{right_type.value}")

        self.graph.add_node(
            "consumer_request",
            request_id,
            consumer_id=consumer_id,
            right_type=right_type.value,
            status=RequestStatus.RECEIVED.value,
            details=self._sanitize(details),
            submitted_via=submitted_via,
            authorized_agent=str(authorized_agent),
            agent_authorization=agent_authorization,
            received_at=self._now(),
            deadline=self._deadline(45),  # 45 days per CCPA
            verification_method="",
            verified_at="",
            extended=str(False),
            extension_deadline="",
            extension_reason="",
            completed_at="",
            response="",
            denial_reason="",
            denial_explanation="",
        )

        # Link to consumer
        consumer_node_id = f"consumer_{consumer_id}"
        if self.graph.has_node("consumer", consumer_node_id):
            self.graph.add_edge(
                "HAS_REQUEST",
                ("consumer", consumer_node_id),
                ("consumer_request", request_id),
            )

        self._record_request_event(request_id, "request_received", details)

        return request_id

    def verify_consumer(
        self,
        request_id: str,
        verification_method: str,
        verified_by: str,
        verification_details: str = "",
    ) -> Dict[str, Any]:
        """
        Verify consumer identity for a request.

        Verification required before fulfilling requests.
        Higher standard for sensitive data or authorized agents.
        """
        node = self.graph.get_node("consumer_request", request_id)
        if not node:
            return {"error": "Request not found"}

        self.graph.update_node(
            "consumer_request",
            request_id,
            status=RequestStatus.IN_PROGRESS.value,
            verification_method=verification_method,
            verified_at=self._now(),
            verified_by=verified_by,
            verification_details=self._sanitize(verification_details),
        )

        self._record_request_event(
            request_id,
            "identity_verified",
            f"Method: {verification_method}"
        )

        return {
            "request_id": request_id,
            "status": "verified",
            "verification_method": verification_method,
        }

    def fail_verification(
        self,
        request_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Record failed identity verification"""
        node = self.graph.get_node("consumer_request", request_id)
        if not node:
            return {"error": "Request not found"}

        self.graph.update_node(
            "consumer_request",
            request_id,
            status=RequestStatus.VERIFICATION_FAILED.value,
            verification_failed_reason=reason,
            completed_at=self._now(),
        )

        self._record_request_event(request_id, "verification_failed", reason)

        return {
            "request_id": request_id,
            "status": "verification_failed",
            "reason": reason,
        }

    def extend_deadline(
        self,
        request_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """
        Extend deadline by additional 45 days.

        CCPA allows one extension when reasonably necessary.
        Consumer must be notified within original 45 days.
        """
        node = self.graph.get_node("consumer_request", request_id)
        if not node:
            return {"error": "Request not found"}

        if node.properties.get("extended") == "True":
            return {"error": "Already extended"}

        new_deadline = self._deadline(90)  # 45 + 45 days from original receipt

        self.graph.update_node(
            "consumer_request",
            request_id,
            extended=str(True),
            extension_deadline=new_deadline,
            extension_reason=reason,
            extension_notified_at=self._now(),
            status=RequestStatus.EXTENDED.value,
        )

        self._record_request_event(request_id, "deadline_extended", reason)

        return {
            "request_id": request_id,
            "original_deadline": node.properties.get("deadline"),
            "new_deadline": new_deadline,
            "reason": reason,
        }

    def complete_request(
        self,
        request_id: str,
        response: str,
        actions_taken: List[str],
        data_provided: bool = False,
    ) -> Dict[str, Any]:
        """
        Complete a consumer request.

        Args:
            request_id: Request ID
            response: Response provided to consumer
            actions_taken: List of actions taken
            data_provided: Whether data was provided (for access/portability)
        """
        node = self.graph.get_node("consumer_request", request_id)
        if not node:
            return {"error": "Request not found"}

        self.graph.update_node(
            "consumer_request",
            request_id,
            status=RequestStatus.COMPLETED.value,
            completed_at=self._now(),
            response=self._sanitize(response),
            actions_taken=self._list_to_str(actions_taken),
            data_provided=str(data_provided),
        )

        self._record_request_event(request_id, "request_completed", response)

        return {
            "request_id": request_id,
            "status": "completed",
            "completed_at": self._now(),
        }

    def deny_request(
        self,
        request_id: str,
        denial_reason: DenialReason,
        explanation: str,
    ) -> Dict[str, Any]:
        """
        Deny a consumer request.

        Must provide reason for denial per CCPA.
        """
        node = self.graph.get_node("consumer_request", request_id)
        if not node:
            return {"error": "Request not found"}

        self.graph.update_node(
            "consumer_request",
            request_id,
            status=RequestStatus.DENIED.value,
            denial_reason=denial_reason.value,
            denial_explanation=self._sanitize(explanation),
            completed_at=self._now(),
        )

        self._record_request_event(
            request_id,
            "request_denied",
            f"{denial_reason.value}: {explanation}"
        )

        return {
            "request_id": request_id,
            "status": "denied",
            "reason": denial_reason.value,
            "explanation": explanation,
        }

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get request details"""
        node = self.graph.get_node("consumer_request", request_id)
        if node:
            return {"id": request_id, **node.properties}
        return None

    def get_consumer_requests(
        self,
        consumer_id: str,
        status: Optional[RequestStatus] = None,
    ) -> List[Dict[str, Any]]:
        """Get all requests for a consumer"""
        results = []
        for node in self.graph.nodes():
            if node.type == "consumer_request":
                if node.properties.get("consumer_id") == consumer_id:
                    if status and node.properties.get("status") != status.value:
                        continue
                    results.append({"id": node.id, **node.properties})
        return results

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending requests"""
        pending = {
            RequestStatus.RECEIVED.value,
            RequestStatus.VERIFICATION_PENDING.value,
            RequestStatus.IN_PROGRESS.value,
            RequestStatus.EXTENDED.value,
        }
        results = []
        for node in self.graph.nodes():
            if (node.type == "consumer_request" and
                node.properties.get("status") in pending):
                results.append({"id": node.id, **node.properties})
        return results

    def get_overdue_requests(self) -> List[Dict[str, Any]]:
        """Get requests past their deadline"""
        now = self._now()
        results = []
        for node in self.graph.nodes():
            if node.type == "consumer_request":
                status = node.properties.get("status")
                if status in [RequestStatus.COMPLETED.value,
                             RequestStatus.DENIED.value,
                             RequestStatus.VERIFICATION_FAILED.value]:
                    continue

                deadline = node.properties.get("extension_deadline") or \
                          node.properties.get("deadline", "")
                if deadline and deadline < now:
                    results.append({"id": node.id, **node.properties})
        return results

    def get_requests_by_type(
        self,
        right_type: ConsumerRight
    ) -> List[Dict[str, Any]]:
        """Get all requests of a specific type"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "consumer_request" and
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
        event_id = self._make_id("request_event", request_id)
        self.graph.add_node(
            "request_event",
            event_id,
            request_id=request_id,
            event_type=event_type,
            details=self._sanitize(details),
            timestamp=self._now(),
        )

        if self.graph.has_node("consumer_request", request_id):
            self.graph.add_edge(
                "REQUEST_EVENT",
                ("consumer_request", request_id),
                ("request_event", event_id),
            )

    def get_request_history(self, request_id: str) -> List[Dict[str, Any]]:
        """Get audit history for a request"""
        events = []
        for node in self.graph.nodes():
            if (node.type == "request_event" and
                node.properties.get("request_id") == request_id):
                events.append({"id": node.id, **node.properties})
        return sorted(events, key=lambda x: x.get("timestamp", ""))

    def get_stats(self) -> Dict[str, Any]:
        """Get request statistics"""
        total = 0
        pending = 0
        completed = 0
        denied = 0
        overdue = 0
        by_type = {}
        by_status = {}

        now = self._now()

        for node in self.graph.nodes():
            if node.type == "consumer_request":
                total += 1
                status = node.properties.get("status")

                by_status[status] = by_status.get(status, 0) + 1

                if status == RequestStatus.COMPLETED.value:
                    completed += 1
                elif status == RequestStatus.DENIED.value:
                    denied += 1
                elif status not in [RequestStatus.VERIFICATION_FAILED.value]:
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
            "denied_requests": denied,
            "overdue_requests": overdue,
            "by_type": by_type,
            "by_status": by_status,
        }
