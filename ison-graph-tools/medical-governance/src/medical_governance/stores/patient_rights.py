"""
Patient Rights Store
====================

Manages patient rights per HIPAA 45 CFR 164.520-528.
Handles access, amendment, restriction, and accounting requests.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import PatientRight, RightRequestStatus

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class PatientRightsStore(BaseStore):
    """Store for patient rights management"""

    # Response deadlines in days
    DEADLINES = {
        PatientRight.ACCESS: 30,         # 30 days, extendable by 30
        PatientRight.AMENDMENT: 60,      # 60 days, extendable by 30
        PatientRight.ACCOUNTING: 60,     # 60 days, extendable by 30
        PatientRight.RESTRICTION: 0,     # No deadline (must respond)
        PatientRight.CONFIDENTIAL_COMM: 0,  # Reasonable accommodation
        PatientRight.NOTICE_PRIVACY: 0,  # At registration
        PatientRight.COMPLAINT: 0        # No deadline
    }

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "patient_rights")

    # =========================================================================
    # Access Request (164.524)
    # =========================================================================

    def request_access(
        self,
        patient_id: str,
        format_requested: str,  # electronic, paper
        scope: str,  # full_record, last_2_years, specific_provider
        request_id: Optional[str] = None
    ) -> str:
        """Patient requests access to their PHI"""
        rid = request_id or self._generate_id("ar")
        deadline = self._calculate_deadline(self.DEADLINES[PatientRight.ACCESS])

        props = {
            "patient_id": patient_id,
            "right_type": PatientRight.ACCESS.value,
            "format_requested": format_requested,
            "scope": scope,
            "request_date": self._now(),
            "status": RightRequestStatus.PENDING.value,
            "deadline": deadline,
            "description": f"Access request from {patient_id}"
        }
        return self._add_node("right_request", rid, props)

    def fulfill_access_request(
        self,
        request_id: str,
        delivery_method: str,
        phi_provided: str
    ):
        """Fulfill an access request"""
        self._update_node("right_request", request_id, {
            "status": RightRequestStatus.COMPLETE.value,
            "fulfilled_date": self._now(),
            "delivery_method": delivery_method,
            "phi_provided": phi_provided
        })

    def deny_access_request(
        self,
        request_id: str,
        denial_basis: str,
        reviewable: bool,
        review_process: Optional[str] = None
    ):
        """Deny an access request"""
        self._update_node("right_request", request_id, {
            "status": RightRequestStatus.DENIED.value,
            "denial_date": self._now(),
            "denial_basis": denial_basis,
            "reviewable": reviewable,
            "review_process": review_process
        })

    # =========================================================================
    # Amendment Request (164.526)
    # =========================================================================

    def request_amendment(
        self,
        patient_id: str,
        element_to_amend: str,
        proposed_change: str,
        reason: str,
        request_id: Optional[str] = None
    ) -> str:
        """Patient requests amendment to their PHI"""
        rid = request_id or self._generate_id("amr")
        deadline = self._calculate_deadline(self.DEADLINES[PatientRight.AMENDMENT])

        props = {
            "patient_id": patient_id,
            "right_type": PatientRight.AMENDMENT.value,
            "element_to_amend": element_to_amend,
            "proposed_change": proposed_change,
            "reason": reason,
            "request_date": self._now(),
            "status": RightRequestStatus.PENDING.value,
            "deadline": deadline,
            "description": f"Amendment request: {element_to_amend}"
        }
        return self._add_node("right_request", rid, props)

    def accept_amendment(
        self,
        request_id: str,
        linked_records: List[str]
    ):
        """Accept an amendment request"""
        self._update_node("right_request", request_id, {
            "status": RightRequestStatus.GRANTED.value,
            "response_date": self._now(),
            "action": "accepted",
            "linked_records": linked_records,
            "appended": True
        })

    def deny_amendment(
        self,
        request_id: str,
        reason: str
    ):
        """Deny an amendment request (patient can submit statement)"""
        self._update_node("right_request", request_id, {
            "status": RightRequestStatus.DENIED.value,
            "response_date": self._now(),
            "action": "denied",
            "denial_reason": reason,
            "appended": True,  # Denial + patient statement appended
            "patient_statement_allowed": True
        })

    def add_patient_statement(
        self,
        request_id: str,
        statement: str
    ):
        """Add patient's disagreement statement to denied amendment"""
        sid = self._generate_id("ps")
        props = {
            "request_id": request_id,
            "statement": statement,
            "submitted_date": self._now(),
            "description": "Patient disagreement statement"
        }
        self._add_node("patient_statement", sid, props)

    # =========================================================================
    # Accounting of Disclosures (164.528)
    # =========================================================================

    def request_accounting(
        self,
        patient_id: str,
        period: str = "6_years",
        request_id: Optional[str] = None
    ) -> str:
        """Patient requests accounting of disclosures"""
        rid = request_id or self._generate_id("acr")
        deadline = self._calculate_deadline(self.DEADLINES[PatientRight.ACCOUNTING])

        props = {
            "patient_id": patient_id,
            "right_type": PatientRight.ACCOUNTING.value,
            "period_requested": period,
            "request_date": self._now(),
            "status": RightRequestStatus.PENDING.value,
            "deadline": deadline,
            "description": f"Accounting request from {patient_id}"
        }
        return self._add_node("right_request", rid, props)

    # =========================================================================
    # Restriction Request (164.522(a))
    # =========================================================================

    def request_restriction(
        self,
        patient_id: str,
        restriction_type: str,  # disclosure_restriction, self_pay
        scope: str,
        request_id: Optional[str] = None
    ) -> str:
        """Patient requests restriction on PHI use/disclosure"""
        rid = request_id or self._generate_id("rr")

        # Self-pay restrictions are mandatory
        required = restriction_type == "self_pay"

        props = {
            "patient_id": patient_id,
            "right_type": PatientRight.RESTRICTION.value,
            "restriction_type": restriction_type,
            "scope": scope,
            "request_date": self._now(),
            "status": RightRequestStatus.PENDING.value,
            "required_by_law": required,
            "description": f"Restriction request: {restriction_type}"
        }
        return self._add_node("right_request", rid, props)

    def respond_to_restriction(
        self,
        request_id: str,
        agreed: bool,
        implementation_notes: str = ""
    ):
        """Respond to a restriction request"""
        status = RightRequestStatus.GRANTED if agreed else RightRequestStatus.DENIED
        self._update_node("right_request", request_id, {
            "status": status.value,
            "response_date": self._now(),
            "agreed": agreed,
            "implementation_notes": implementation_notes
        })

        if agreed:
            # Create active restriction
            request = self._get_node("right_request", request_id)
            self._create_active_restriction(request)

    def _create_active_restriction(self, request: Dict[str, Any]):
        """Create an active restriction from approved request"""
        arid = self._generate_id("rest")
        props = {
            "patient_id": request.get("patient_id"),
            "restriction_type": request.get("restriction_type"),
            "scope": request.get("scope"),
            "request_id": request.get("id"),
            "active": True,
            "created_at": self._now(),
            "description": f"Active restriction: {request.get('restriction_type')}"
        }
        self._add_node("active_restriction", arid, props)

    def get_patient_restrictions(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get active restrictions for a patient"""
        return self._find_nodes("active_restriction", patient_id=patient_id, active=True)

    def terminate_restriction(self, restriction_id: str, reason: str):
        """Terminate an active restriction"""
        self._update_node("active_restriction", restriction_id, {
            "active": False,
            "terminated_at": self._now(),
            "termination_reason": reason
        })

    # =========================================================================
    # Confidential Communications (164.522(b))
    # =========================================================================

    def request_confidential_comm(
        self,
        patient_id: str,
        comm_type: str,  # alternate_address, alternate_phone, portal_only
        alternative: str,
        request_id: Optional[str] = None
    ) -> str:
        """Patient requests confidential communication method"""
        rid = request_id or self._generate_id("cc")
        props = {
            "patient_id": patient_id,
            "right_type": PatientRight.CONFIDENTIAL_COMM.value,
            "comm_type": comm_type,
            "alternative": alternative,
            "request_date": self._now(),
            "status": RightRequestStatus.PENDING.value,
            "description": f"Confidential comm: {comm_type}"
        }
        return self._add_node("right_request", rid, props)

    def implement_confidential_comm(
        self,
        request_id: str,
        system_flag: str
    ):
        """Implement confidential communication preference"""
        self._update_node("right_request", request_id, {
            "status": RightRequestStatus.COMPLETE.value,
            "implemented_date": self._now(),
            "system_flag": system_flag
        })

    # =========================================================================
    # Notice of Privacy Practices (164.520)
    # =========================================================================

    def record_npp_provision(
        self,
        patient_id: str,
        version: str,
        acknowledgment_received: bool
    ) -> str:
        """Record Notice of Privacy Practices provision"""
        nid = self._generate_id("npp")
        props = {
            "patient_id": patient_id,
            "right_type": PatientRight.NOTICE_PRIVACY.value,
            "version": version,
            "provided_date": self._now(),
            "acknowledgment_received": acknowledgment_received,
            "description": f"NPP provision for {patient_id}"
        }
        return self._add_node("npp_provision", nid, props)

    def get_patient_npp(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get NPP record for a patient"""
        npps = self._find_nodes("npp_provision", patient_id=patient_id)
        if npps:
            return sorted(npps, key=lambda n: n.get("provided_date", ""), reverse=True)[0]
        return None

    # =========================================================================
    # Complaint (164.530(d))
    # =========================================================================

    def file_complaint(
        self,
        patient_id: str,
        complaint_type: str,
        description: str,
        complaint_id: Optional[str] = None
    ) -> str:
        """File a patient complaint"""
        cid = complaint_id or self._generate_id("comp")
        props = {
            "patient_id": patient_id,
            "right_type": PatientRight.COMPLAINT.value,
            "complaint_type": complaint_type,
            "description": description,
            "filed_date": self._now(),
            "status": "open",
            "description": f"Complaint: {complaint_type}"
        }
        return self._add_node("complaint", cid, props)

    def resolve_complaint(
        self,
        complaint_id: str,
        resolution: str,
        resolved_by: str
    ):
        """Resolve a complaint"""
        self._update_node("complaint", complaint_id, {
            "status": "resolved",
            "resolution": resolution,
            "resolved_by": resolved_by,
            "resolved_date": self._now()
        })

    def get_open_complaints(self) -> List[Dict[str, Any]]:
        """Get open complaints"""
        return self._find_nodes("complaint", status="open")

    # =========================================================================
    # Request Management
    # =========================================================================

    def get_request(self, request_id: str) -> Optional[Dict[str, Any]]:
        """Get request by ID"""
        return self._get_node("right_request", request_id)

    def get_patient_requests(
        self,
        patient_id: str,
        right_type: Optional[PatientRight] = None,
        status: Optional[RightRequestStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get all requests for a patient"""
        requests = self._find_nodes("right_request", patient_id=patient_id)

        if right_type:
            requests = [r for r in requests if r.get("right_type") == right_type.value]
        if status:
            requests = [r for r in requests if r.get("status") == status.value]

        return requests

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending requests"""
        return self._find_nodes("right_request", status=RightRequestStatus.PENDING.value)

    def get_overdue_requests(self) -> List[Dict[str, Any]]:
        """Get requests past their deadline"""
        pending = self.get_pending_requests()
        now = self._now()

        return [r for r in pending if r.get("deadline", "") < now]

    def extend_deadline(
        self,
        request_id: str,
        extension_days: int,
        reason: str
    ):
        """Extend deadline for a request (max 30 days)"""
        request = self.get_request(request_id)
        if not request:
            return

        extension_days = min(extension_days, 30)  # Max 30 day extension
        new_deadline = self._calculate_deadline(extension_days)

        self._update_node("right_request", request_id, {
            "deadline": new_deadline,
            "extended": True,
            "extension_reason": reason,
            "extension_date": self._now()
        })

    def _calculate_deadline(self, days: int) -> str:
        """Calculate deadline from now"""
        from datetime import datetime, timedelta
        deadline = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) +
            timedelta(days=days)
        )
        return deadline.isoformat() + "+00:00"

    # =========================================================================
    # Compliance Tracking
    # =========================================================================

    def get_compliance_metrics(self) -> Dict[str, Any]:
        """Get patient rights compliance metrics"""
        requests = self._find_nodes("right_request")

        total = len(requests)
        by_type = {}
        by_status = {}
        on_time = 0
        late = 0

        for r in requests:
            # By type
            rtype = r.get("right_type", "unknown")
            by_type[rtype] = by_type.get(rtype, 0) + 1

            # By status
            status = r.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

            # Timeliness
            if status in [RightRequestStatus.COMPLETE.value, RightRequestStatus.GRANTED.value]:
                deadline = r.get("deadline", "")
                fulfilled = r.get("fulfilled_date") or r.get("response_date", "")
                if fulfilled and deadline:
                    if fulfilled <= deadline:
                        on_time += 1
                    else:
                        late += 1

        completed = on_time + late
        timeliness_rate = on_time / completed if completed > 0 else 1.0

        return {
            "total_requests": total,
            "by_type": by_type,
            "by_status": by_status,
            "on_time_completions": on_time,
            "late_completions": late,
            "timeliness_rate": timeliness_rate
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get patient rights statistics"""
        base_stats = super().get_stats()
        requests = self._find_nodes("right_request")
        restrictions = self._find_nodes("active_restriction")
        complaints = self._find_nodes("complaint")

        pending = len([r for r in requests if r.get("status") == RightRequestStatus.PENDING.value])
        overdue = len(self.get_overdue_requests())

        return {
            **base_stats,
            "total_requests": len(requests),
            "pending_requests": pending,
            "overdue_requests": overdue,
            "active_restrictions": len([r for r in restrictions if r.get("active")]),
            "total_complaints": len(complaints),
            "open_complaints": len([c for c in complaints if c.get("status") == "open"])
        }
