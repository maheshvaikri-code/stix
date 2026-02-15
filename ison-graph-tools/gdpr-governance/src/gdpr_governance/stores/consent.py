"""
Consent Management Store
========================

GDPR consent management (Article 7).
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta

from .base import BaseGDPRStore
from ..schema import (
    ConsentType, ConsentStatus, LawfulBasis
)


class ConsentStore(BaseGDPRStore):
    """
    GDPR Consent Management (Article 7).

    Tracks:
    - Consent records per data subject and purpose
    - Consent given/withdrawn timestamps
    - Consent evidence and audit trail
    - Consent expiry and renewal
    """

    def record_consent(
        self,
        data_subject_id: str,
        purpose: str,
        consent_type: ConsentType = ConsentType.STANDARD,
        evidence: str = "",
        privacy_policy_version: str = "",
        expires_in_days: Optional[int] = None,
        processing_activity_id: Optional[str] = None,
    ) -> str:
        """
        Record consent given by a data subject.

        Args:
            data_subject_id: ID of the data subject
            purpose: Purpose for which consent is given
            consent_type: Type of consent
            evidence: How consent was obtained (e.g., "web form", "checkbox")
            privacy_policy_version: Version of privacy policy consented to
            expires_in_days: Days until consent expires (None = no expiry)
            processing_activity_id: Related processing activity

        Returns:
            Consent record ID
        """
        consent_id = self._make_id("consent", f"{data_subject_id}_{purpose}")

        expires_at = ""
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

        self.graph.add_node(
            "consent",
            consent_id,
            data_subject_id=data_subject_id,
            purpose=self._sanitize(purpose),
            consent_type=consent_type.value,
            status=ConsentStatus.GIVEN.value,
            lawful_basis=LawfulBasis.CONSENT.value,
            given_at=self._now(),
            withdrawn_at="",
            expires_at=expires_at,
            evidence=self._sanitize(evidence),
            privacy_policy_version=privacy_policy_version,
            processing_activity_id=processing_activity_id or "",
        )

        # Link to data subject
        subject_node_id = f"subject_{data_subject_id}"
        if self.graph.has_node("data_subject", subject_node_id):
            self.graph.add_edge(
                "HAS_CONSENT",
                ("data_subject", subject_node_id),
                ("consent", consent_id),
            )

        # Link to processing activity
        if processing_activity_id and self.graph.has_node(
            "processing_activity", processing_activity_id
        ):
            self.graph.add_edge(
                "CONSENT_FOR",
                ("consent", consent_id),
                ("processing_activity", processing_activity_id),
            )

        # Record audit event
        self._record_consent_event(consent_id, "consent_given", evidence)

        return consent_id

    def withdraw_consent(
        self,
        consent_id: str,
        reason: str = "",
        requested_by: str = "data_subject",
    ) -> Dict[str, Any]:
        """
        Withdraw consent (Article 7(3)).

        Withdrawal must be as easy as giving consent.

        Args:
            consent_id: ID of the consent record
            reason: Reason for withdrawal
            requested_by: Who requested withdrawal

        Returns:
            Withdrawal confirmation
        """
        node = self.graph.get_node("consent", consent_id)
        if not node:
            return {"error": "Consent record not found"}

        self.graph.update_node(
            "consent",
            consent_id,
            status=ConsentStatus.WITHDRAWN.value,
            withdrawn_at=self._now(),
            withdrawal_reason=reason,
            withdrawal_requested_by=requested_by,
        )

        # Record audit event
        self._record_consent_event(consent_id, "consent_withdrawn", reason)

        return {
            "consent_id": consent_id,
            "status": "withdrawn",
            "withdrawn_at": self._now(),
            "data_subject_id": node.properties.get("data_subject_id"),
            "purpose": node.properties.get("purpose"),
        }

    def check_consent(
        self,
        data_subject_id: str,
        purpose: str,
    ) -> Dict[str, Any]:
        """
        Check if valid consent exists for a purpose.

        Args:
            data_subject_id: Data subject ID
            purpose: Purpose to check

        Returns:
            Consent status with details
        """
        for node in self.graph.nodes():
            if node.type == "consent":
                if (node.properties.get("data_subject_id") == data_subject_id and
                    node.properties.get("purpose") == purpose):
                    status = node.properties.get("status")

                    # Check expiry
                    expires_at = node.properties.get("expires_at")
                    if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
                        self.graph.update_node(
                            "consent",
                            node.id,
                            status=ConsentStatus.EXPIRED.value,
                        )
                        status = ConsentStatus.EXPIRED.value

                    return {
                        "consent_id": node.id,
                        "has_consent": status == ConsentStatus.GIVEN.value,
                        "status": status,
                        "given_at": node.properties.get("given_at"),
                        "expires_at": expires_at,
                        "consent_type": node.properties.get("consent_type"),
                    }

        return {
            "consent_id": None,
            "has_consent": False,
            "status": "not_found",
        }

    def get_subject_consents(
        self,
        data_subject_id: str,
        status: Optional[ConsentStatus] = None,
    ) -> List[Dict[str, Any]]:
        """Get all consents for a data subject"""
        results = []
        for node in self.graph.nodes():
            if node.type == "consent":
                if node.properties.get("data_subject_id") == data_subject_id:
                    if status and node.properties.get("status") != status.value:
                        continue
                    results.append({
                        "id": node.id,
                        **node.properties
                    })
        return results

    def get_consents_for_activity(
        self,
        processing_activity_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all consents for a processing activity"""
        results = []
        for node in self.graph.nodes():
            if node.type == "consent":
                if node.properties.get("processing_activity_id") == processing_activity_id:
                    results.append({
                        "id": node.id,
                        **node.properties
                    })
        return results

    def renew_consent(
        self,
        consent_id: str,
        new_evidence: str,
        expires_in_days: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Renew an existing consent"""
        node = self.graph.get_node("consent", consent_id)
        if not node:
            return {"error": "Consent record not found"}

        expires_at = ""
        if expires_in_days:
            expires_at = (datetime.now() + timedelta(days=expires_in_days)).isoformat()

        self.graph.update_node(
            "consent",
            consent_id,
            status=ConsentStatus.GIVEN.value,
            renewed_at=self._now(),
            renewal_evidence=new_evidence,
            expires_at=expires_at,
            withdrawn_at="",
        )

        self._record_consent_event(consent_id, "consent_renewed", new_evidence)

        return {
            "consent_id": consent_id,
            "status": "renewed",
            "renewed_at": self._now(),
            "expires_at": expires_at,
        }

    def get_expiring_consents(
        self,
        days_until_expiry: int = 30,
    ) -> List[Dict[str, Any]]:
        """Get consents expiring within specified days"""
        threshold = (datetime.now() + timedelta(days=days_until_expiry)).isoformat()
        results = []

        for node in self.graph.nodes():
            if node.type == "consent":
                if node.properties.get("status") == ConsentStatus.GIVEN.value:
                    expires_at = node.properties.get("expires_at")
                    if expires_at and expires_at <= threshold:
                        results.append({
                            "id": node.id,
                            **node.properties
                        })

        return results

    def _record_consent_event(
        self,
        consent_id: str,
        event_type: str,
        details: str,
    ) -> None:
        """Record consent audit event"""
        event_id = self._make_id("consent_event", consent_id)
        self.graph.add_node(
            "consent_event",
            event_id,
            consent_id=consent_id,
            event_type=event_type,
            details=self._sanitize(details),
            timestamp=self._now(),
        )

        if self.graph.has_node("consent", consent_id):
            self.graph.add_edge(
                "CONSENT_EVENT",
                ("consent", consent_id),
                ("consent_event", event_id),
            )

    def get_consent_history(
        self,
        consent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get audit history for a consent record"""
        events = []
        for node in self.graph.nodes():
            if (node.type == "consent_event" and
                node.properties.get("consent_id") == consent_id):
                events.append({
                    "id": node.id,
                    **node.properties
                })
        return sorted(events, key=lambda x: x.get("timestamp", ""))

    def get_stats(self) -> Dict[str, Any]:
        """Get consent statistics"""
        total = 0
        active = 0
        withdrawn = 0
        expired = 0
        by_type = {}

        for node in self.graph.nodes():
            if node.type == "consent":
                total += 1
                status = node.properties.get("status")
                if status == ConsentStatus.GIVEN.value:
                    active += 1
                elif status == ConsentStatus.WITHDRAWN.value:
                    withdrawn += 1
                elif status == ConsentStatus.EXPIRED.value:
                    expired += 1

                consent_type = node.properties.get("consent_type", "unknown")
                by_type[consent_type] = by_type.get(consent_type, 0) + 1

        return {
            "total_consents": total,
            "active_consents": active,
            "withdrawn_consents": withdrawn,
            "expired_consents": expired,
            "by_type": by_type,
        }
