"""
Disclosure & Audit Store
========================

Manages PHI access audit logging and accounting of disclosures per HIPAA 45 CFR 164.312(b) and 164.528.
Provides tamper-evident audit trails and patient-requestable disclosure accounting.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import AccessPurpose, AuditEvent, DisclosureRecord, AccountingRequest

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class DisclosureStore(BaseStore):
    """Store for audit trail and accounting of disclosures"""

    # Purposes exempt from accounting (TPO)
    TPO_EXEMPT = [
        AccessPurpose.TREATMENT.value,
        AccessPurpose.PAYMENT.value,
        AccessPurpose.HEALTHCARE_OPERATIONS.value
    ]

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "disclosure")

    # =========================================================================
    # Audit Event Management
    # =========================================================================

    def log_access(
        self,
        actor_id: str,
        actor_type: str,
        patient_id: str,
        action: str,  # view, query, transmit, modify
        phi_accessed: List[str],
        purpose: AccessPurpose,
        location: str = "",
        session_id: str = "",
        event_id: Optional[str] = None
    ) -> str:
        """Log a PHI access event"""
        eid = event_id or self._generate_id("ae")
        props = {
            "event_type": "access",
            "actor_id": actor_id,
            "actor_type": actor_type,
            "patient_id": patient_id,
            "action": action,
            "phi_accessed": phi_accessed,
            "purpose": purpose.value,
            "location": location,
            "session_id": session_id,
            "timestamp": self._now(),
            "description": f"PHI access by {actor_id}"
        }
        return self._add_node("audit_event", eid, props)

    def log_disclosure(
        self,
        patient_id: str,
        recipient: str,
        recipient_type: str,
        purpose: AccessPurpose,
        phi_disclosed: List[str],
        transmission_id: str = "",
        event_id: Optional[str] = None
    ) -> str:
        """Log a PHI disclosure event"""
        eid = event_id or self._generate_id("de")
        props = {
            "event_type": "disclosure",
            "patient_id": patient_id,
            "recipient": recipient,
            "recipient_type": recipient_type,
            "purpose": purpose.value,
            "phi_disclosed": phi_disclosed,
            "transmission_id": transmission_id,
            "timestamp": self._now(),
            "requires_accounting": purpose.value not in self.TPO_EXEMPT,
            "description": f"PHI disclosure to {recipient}"
        }
        self._add_node("audit_event", eid, props)

        # If requires accounting, create disclosure record
        if purpose.value not in self.TPO_EXEMPT:
            self._create_disclosure_record(
                patient_id, recipient, recipient_type,
                purpose, phi_disclosed, eid
            )

        return eid

    def log_amendment(
        self,
        actor_id: str,
        patient_id: str,
        field_amended: str,
        previous_value: str,
        new_value: str,
        reason: str
    ) -> str:
        """Log a PHI amendment event"""
        eid = self._generate_id("am")
        props = {
            "event_type": "amendment",
            "actor_id": actor_id,
            "patient_id": patient_id,
            "action": "modify",
            "field_amended": field_amended,
            "previous_value": previous_value,
            "new_value": new_value,
            "reason": reason,
            "timestamp": self._now(),
            "description": f"PHI amendment: {field_amended}"
        }
        return self._add_node("audit_event", eid, props)

    def log_access_denied(
        self,
        actor_id: str,
        patient_id: str,
        action: str,
        reason: str
    ) -> str:
        """Log a denied access attempt"""
        eid = self._generate_id("ad")
        props = {
            "event_type": "access_denied",
            "actor_id": actor_id,
            "patient_id": patient_id,
            "action": action,
            "reason": reason,
            "timestamp": self._now(),
            "description": f"Access denied: {reason}"
        }
        return self._add_node("audit_event", eid, props)

    def get_audit_event(self, event_id: str) -> Optional[Dict[str, Any]]:
        """Get audit event by ID"""
        return self._get_node("audit_event", event_id)

    def get_patient_audit_log(
        self,
        patient_id: str,
        event_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log for a patient"""
        events = self._find_nodes("audit_event", patient_id=patient_id)

        if event_type:
            events = [e for e in events if e.get("event_type") == event_type]

        # Sort by timestamp descending
        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)

        return events[:limit]

    def get_actor_audit_log(
        self,
        actor_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get audit log for an actor"""
        events = self._find_nodes("audit_event", actor_id=actor_id)
        events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return events[:limit]

    # =========================================================================
    # Disclosure Records (for Accounting)
    # =========================================================================

    def _create_disclosure_record(
        self,
        patient_id: str,
        recipient: str,
        recipient_type: str,
        purpose: AccessPurpose,
        phi_disclosed: List[str],
        audit_event_id: str
    ) -> str:
        """Create a disclosure record for accounting"""
        drid = self._generate_id("dr")
        props = {
            "patient_id": patient_id,
            "recipient": recipient,
            "recipient_type": recipient_type,
            "purpose": purpose.value,
            "phi_disclosed": phi_disclosed,
            "disclosure_date": self._now(),
            "audit_event_id": audit_event_id,
            "requires_accounting": True,
            "description": f"Disclosure record: {recipient}"
        }
        self._add_node("disclosure_record", drid, props)

        return drid

    def get_disclosure_records(
        self,
        patient_id: str,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get disclosure records for accounting"""
        records = self._find_nodes(
            "disclosure_record",
            patient_id=patient_id,
            requires_accounting=True
        )

        if since:
            records = [r for r in records if r.get("disclosure_date", "") >= since]

        return records

    def add_disclosure_exception(
        self,
        disclosure_id: str,
        exception_type: str,  # tpo_no_accounting, public_health_exception, etc.
        documentation: str
    ):
        """Add exception to a disclosure (TPO, etc.)"""
        self._update_node("disclosure_record", disclosure_id, {
            "exception_type": exception_type,
            "exception_documentation": documentation,
            "requires_accounting": exception_type == "research_accounting"
        })

    # =========================================================================
    # Accounting of Disclosures Requests
    # =========================================================================

    def request_accounting(
        self,
        patient_id: str,
        period_requested: str = "6_years"
    ) -> str:
        """Patient requests accounting of disclosures"""
        arid = self._generate_id("ar")
        props = {
            "patient_id": patient_id,
            "request_date": self._now(),
            "period_requested": period_requested,
            "status": "pending",
            "deadline": self._calculate_deadline(60),  # 60 days
            "description": f"Accounting request from patient {patient_id}"
        }
        return self._add_node("accounting_request", arid, props)

    def _calculate_deadline(self, days: int) -> str:
        """Calculate deadline from now"""
        from datetime import datetime, timedelta
        deadline = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) +
            timedelta(days=days)
        )
        return deadline.isoformat() + "+00:00"

    def fulfill_accounting(
        self,
        request_id: str,
        disclosures: List[Dict[str, Any]],
        delivery_method: str
    ):
        """Fulfill an accounting of disclosures request"""
        self._update_node("accounting_request", request_id, {
            "status": "complete",
            "fulfilled_date": self._now(),
            "disclosure_count": len(disclosures),
            "delivery_method": delivery_method
        })

    def get_pending_accounting_requests(self) -> List[Dict[str, Any]]:
        """Get pending accounting requests"""
        return self._find_nodes("accounting_request", status="pending")

    def generate_accounting_report(self, patient_id: str) -> Dict[str, Any]:
        """Generate accounting of disclosures report for a patient"""
        # Get disclosures requiring accounting
        from datetime import datetime, timedelta

        # 6 year lookback
        six_years_ago = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) -
            timedelta(days=6*365)
        ).isoformat()

        disclosures = self.get_disclosure_records(patient_id, since=six_years_ago)

        # Group by recipient
        by_recipient = {}
        for d in disclosures:
            recipient = d.get("recipient", "unknown")
            if recipient not in by_recipient:
                by_recipient[recipient] = []
            by_recipient[recipient].append({
                "date": d.get("disclosure_date"),
                "purpose": d.get("purpose"),
                "phi_disclosed": d.get("phi_disclosed", [])
            })

        return {
            "patient_id": patient_id,
            "report_date": self._now(),
            "period": "6_years",
            "total_disclosures": len(disclosures),
            "by_recipient": by_recipient,
            "note": "Excludes TPO (Treatment, Payment, Operations) disclosures per HIPAA"
        }

    # =========================================================================
    # Audit Detail
    # =========================================================================

    def add_audit_detail(
        self,
        audit_event_id: str,
        detail_type: str,
        value: str
    ) -> str:
        """Add detail to an audit event"""
        adid = self._generate_id("ad")
        props = {
            "audit_event_id": audit_event_id,
            "detail_type": detail_type,
            "value": value,
            "description": f"Audit detail: {detail_type}"
        }
        self._add_node("audit_detail", adid, props)

        return adid

    def get_audit_details(self, audit_event_id: str) -> List[Dict[str, Any]]:
        """Get details for an audit event"""
        return self._find_nodes("audit_detail", audit_event_id=audit_event_id)

    # =========================================================================
    # Audit Chain (Tamper Evidence)
    # =========================================================================

    def create_audit_chain(self, event_id: str, previous_event_id: Optional[str] = None):
        """Create tamper-evident chain link"""
        import hashlib

        event = self.get_audit_event(event_id)
        if not event:
            return

        # Create integrity hash
        hash_input = f"{event_id}:{event.get('timestamp')}:{event.get('actor_id')}:{event.get('action')}"
        if previous_event_id:
            prev_event = self.get_audit_event(previous_event_id)
            if prev_event:
                hash_input += f":{prev_event.get('_integrity_hash', '')}"

        integrity_hash = hashlib.sha256(hash_input.encode()).hexdigest()

        self._update_node("audit_event", event_id, {
            "_integrity_hash": integrity_hash,
            "_previous_event": previous_event_id
        })

    def verify_audit_chain(self, event_ids: List[str]) -> Dict[str, Any]:
        """Verify audit chain integrity"""
        import hashlib

        issues = []
        for i, event_id in enumerate(event_ids):
            event = self.get_audit_event(event_id)
            if not event:
                issues.append({"event_id": event_id, "issue": "not_found"})
                continue

            stored_hash = event.get("_integrity_hash")
            if not stored_hash:
                issues.append({"event_id": event_id, "issue": "no_hash"})
                continue

            # Recalculate hash
            prev_id = event.get("_previous_event")
            hash_input = f"{event_id}:{event.get('timestamp')}:{event.get('actor_id')}:{event.get('action')}"
            if prev_id:
                prev_event = self.get_audit_event(prev_id)
                if prev_event:
                    hash_input += f":{prev_event.get('_integrity_hash', '')}"

            calculated_hash = hashlib.sha256(hash_input.encode()).hexdigest()

            if calculated_hash != stored_hash:
                issues.append({"event_id": event_id, "issue": "hash_mismatch"})

        return {
            "verified": len(issues) == 0,
            "events_checked": len(event_ids),
            "issues": issues
        }

    # =========================================================================
    # Anomaly Detection
    # =========================================================================

    def detect_anomalies(
        self,
        actor_id: Optional[str] = None,
        hours: int = 24
    ) -> List[Dict[str, Any]]:
        """Detect audit anomalies"""
        from datetime import datetime, timedelta

        cutoff = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) -
            timedelta(hours=hours)
        ).isoformat()

        events = self._find_nodes("audit_event")
        recent = [e for e in events if e.get("timestamp", "") >= cutoff]

        if actor_id:
            recent = [e for e in recent if e.get("actor_id") == actor_id]

        anomalies = []

        # Check for bulk access
        actor_counts = {}
        for e in recent:
            aid = e.get("actor_id", "unknown")
            actor_counts[aid] = actor_counts.get(aid, 0) + 1

        for aid, count in actor_counts.items():
            if count > 100:  # Threshold
                anomalies.append({
                    "type": "bulk_access",
                    "actor_id": aid,
                    "count": count,
                    "severity": "high"
                })

        # Check for denied access patterns
        denied = [e for e in recent if e.get("event_type") == "access_denied"]
        denied_by_actor = {}
        for d in denied:
            aid = d.get("actor_id", "unknown")
            denied_by_actor[aid] = denied_by_actor.get(aid, 0) + 1

        for aid, count in denied_by_actor.items():
            if count > 5:  # Multiple denials
                anomalies.append({
                    "type": "repeated_denial",
                    "actor_id": aid,
                    "count": count,
                    "severity": "medium"
                })

        return anomalies

    # =========================================================================
    # Retention Management
    # =========================================================================

    def get_retention_status(self) -> Dict[str, Any]:
        """Get audit retention status"""
        events = self._find_nodes("audit_event")

        from datetime import datetime, timedelta

        six_years_ago = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) -
            timedelta(days=6*365)
        ).isoformat()

        eligible_for_destruction = [
            e for e in events
            if e.get("timestamp", "") < six_years_ago
        ]

        return {
            "total_events": len(events),
            "retention_period": "6_years",
            "eligible_for_destruction": len(eligible_for_destruction),
            "note": "Destruction requires legal hold check"
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get disclosure and audit statistics"""
        base_stats = super().get_stats()
        events = self._find_nodes("audit_event")
        disclosures = self._find_nodes("disclosure_record")
        accounting_requests = self._find_nodes("accounting_request")

        by_type = {}
        for e in events:
            etype = e.get("event_type", "unknown")
            by_type[etype] = by_type.get(etype, 0) + 1

        return {
            **base_stats,
            "total_audit_events": len(events),
            "by_event_type": by_type,
            "disclosure_records": len(disclosures),
            "requiring_accounting": len([d for d in disclosures if d.get("requires_accounting")]),
            "accounting_requests": len(accounting_requests),
            "pending_requests": len([a for a in accounting_requests if a.get("status") == "pending"])
        }
