"""
International Transfer Store
============================

Cross-border data transfer management (Articles 44-49).
"""

from typing import Any, Dict, List, Optional

from .base import BaseGDPRStore
from ..schema import (
    TransferMechanism, TransferStatus, ActorRole, PersonalDataCategory
)


# Countries with adequacy decisions (as of 2024)
ADEQUACY_COUNTRIES = {
    "andorra", "argentina", "canada", "faroe islands", "guernsey",
    "israel", "isle of man", "japan", "jersey", "new zealand",
    "republic of korea", "switzerland", "united kingdom", "uruguay",
    "eu", "eea",  # EU/EEA internal
}


class InternationalTransferStore(BaseGDPRStore):
    """
    International Data Transfer Management (GDPR Articles 44-49).

    Tracks:
    - Transfer destinations and mechanisms
    - Adequacy decisions
    - Standard Contractual Clauses (SCCs)
    - Binding Corporate Rules (BCRs)
    - Transfer Impact Assessments (TIAs)
    """

    def register_transfer(
        self,
        name: str,
        source_country: str,
        destination_country: str,
        recipient_name: str,
        recipient_type: ActorRole,
        mechanism: TransferMechanism,
        data_categories: List[PersonalDataCategory],
        processing_activity_id: str,
        purpose: str,
    ) -> str:
        """
        Register an international data transfer.

        Args:
            name: Name/description of the transfer
            source_country: Origin country (usually EEA)
            destination_country: Destination country
            recipient_name: Name of data recipient
            recipient_type: Role of recipient (processor, controller)
            mechanism: Legal mechanism for transfer
            data_categories: Categories of data transferred
            processing_activity_id: Related processing activity
            purpose: Purpose of the transfer

        Returns:
            Transfer ID
        """
        transfer_id = self._make_id("transfer", name)

        # Check if adequacy decision exists
        has_adequacy = destination_country.lower() in ADEQUACY_COUNTRIES

        # Determine if TIA required (for non-adequacy countries)
        tia_required = not has_adequacy and mechanism in {
            TransferMechanism.STANDARD_CLAUSES,
            TransferMechanism.BINDING_RULES,
        }

        self.graph.add_node(
            "international_transfer",
            transfer_id,
            name=name,
            source_country=source_country,
            destination_country=destination_country,
            recipient_name=recipient_name,
            recipient_type=recipient_type.value,
            mechanism=mechanism.value,
            status=TransferStatus.PENDING_ASSESSMENT.value,
            data_categories=self._list_to_str([c.value for c in data_categories]),
            processing_activity_id=processing_activity_id,
            purpose=self._sanitize(purpose),
            has_adequacy=str(has_adequacy),
            tia_required=str(tia_required),
            tia_completed=str(False),
            safeguards="",
            scc_version="",
            bcr_reference="",
            created_at=self._now(),
            updated_at=self._now(),
            approved_at="",
            suspended_at="",
            terminated_at="",
        )

        # Link to processing activity
        if self.graph.has_node("processing_activity", processing_activity_id):
            self.graph.add_edge(
                "TRANSFER_FOR",
                ("international_transfer", transfer_id),
                ("processing_activity", processing_activity_id),
            )

        self._record_transfer_event(
            transfer_id,
            "transfer_registered",
            f"To: {destination_country}, Mechanism: {mechanism.value}"
        )

        return transfer_id

    def record_scc(
        self,
        transfer_id: str,
        scc_version: str,
        signed_date: str,
        scc_module: str,  # Module 1-4
        annex_details: str = "",
    ) -> Dict[str, Any]:
        """
        Record Standard Contractual Clauses details.

        Uses EU Commission approved SCCs (2021 version).
        """
        node = self.graph.get_node("international_transfer", transfer_id)
        if not node:
            return {"error": "Transfer not found"}

        self.graph.update_node(
            "international_transfer",
            transfer_id,
            scc_version=scc_version,
            scc_signed_date=signed_date,
            scc_module=scc_module,
            scc_annex_details=self._sanitize(annex_details),
            updated_at=self._now(),
        )

        self._record_transfer_event(
            transfer_id,
            "scc_recorded",
            f"Version: {scc_version}, Module: {scc_module}"
        )

        return {
            "transfer_id": transfer_id,
            "scc_recorded": True,
        }

    def record_bcr(
        self,
        transfer_id: str,
        bcr_reference: str,
        approved_by_dpa: str,
        approval_date: str,
    ) -> Dict[str, Any]:
        """Record Binding Corporate Rules details"""
        node = self.graph.get_node("international_transfer", transfer_id)
        if not node:
            return {"error": "Transfer not found"}

        self.graph.update_node(
            "international_transfer",
            transfer_id,
            bcr_reference=bcr_reference,
            bcr_approved_by_dpa=approved_by_dpa,
            bcr_approval_date=approval_date,
            updated_at=self._now(),
        )

        self._record_transfer_event(
            transfer_id,
            "bcr_recorded",
            f"Reference: {bcr_reference}, Approved by: {approved_by_dpa}"
        )

        return {
            "transfer_id": transfer_id,
            "bcr_recorded": True,
        }

    def complete_tia(
        self,
        transfer_id: str,
        assessment_summary: str,
        third_country_laws: str,
        supplementary_measures: List[str],
        risk_level: str,
        assessor: str,
    ) -> Dict[str, Any]:
        """
        Complete Transfer Impact Assessment.

        Required after Schrems II ruling for transfers relying on SCCs/BCRs.
        """
        node = self.graph.get_node("international_transfer", transfer_id)
        if not node:
            return {"error": "Transfer not found"}

        self.graph.update_node(
            "international_transfer",
            transfer_id,
            tia_completed=str(True),
            tia_summary=self._sanitize(assessment_summary),
            tia_third_country_laws=self._sanitize(third_country_laws),
            tia_supplementary_measures=self._list_to_str(supplementary_measures),
            tia_risk_level=risk_level,
            tia_assessor=assessor,
            tia_completed_at=self._now(),
            updated_at=self._now(),
        )

        self._record_transfer_event(
            transfer_id,
            "tia_completed",
            f"Risk level: {risk_level}, Assessor: {assessor}"
        )

        return {
            "transfer_id": transfer_id,
            "tia_completed": True,
            "risk_level": risk_level,
        }

    def add_safeguards(
        self,
        transfer_id: str,
        safeguards: List[str],
    ) -> Dict[str, Any]:
        """Add supplementary safeguards to transfer"""
        node = self.graph.get_node("international_transfer", transfer_id)
        if not node:
            return {"error": "Transfer not found"}

        existing = self._str_to_list(node.properties.get("safeguards", ""))
        combined = list(set(existing + safeguards))

        self.graph.update_node(
            "international_transfer",
            transfer_id,
            safeguards=self._list_to_str(combined),
            updated_at=self._now(),
        )

        self._record_transfer_event(
            transfer_id,
            "safeguards_added",
            ", ".join(safeguards)
        )

        return {
            "transfer_id": transfer_id,
            "safeguards": combined,
        }

    def approve_transfer(
        self,
        transfer_id: str,
        approved_by: str,
        conditions: str = "",
    ) -> Dict[str, Any]:
        """Approve a transfer"""
        node = self.graph.get_node("international_transfer", transfer_id)
        if not node:
            return {"error": "Transfer not found"}

        self.graph.update_node(
            "international_transfer",
            transfer_id,
            status=TransferStatus.APPROVED.value,
            approved_at=self._now(),
            approved_by=approved_by,
            approval_conditions=self._sanitize(conditions),
            updated_at=self._now(),
        )

        self._record_transfer_event(
            transfer_id,
            "transfer_approved",
            f"Approved by: {approved_by}"
        )

        return {
            "transfer_id": transfer_id,
            "status": "approved",
        }

    def activate_transfer(
        self,
        transfer_id: str,
    ) -> Dict[str, Any]:
        """Mark transfer as active"""
        node = self.graph.get_node("international_transfer", transfer_id)
        if not node:
            return {"error": "Transfer not found"}

        self.graph.update_node(
            "international_transfer",
            transfer_id,
            status=TransferStatus.ACTIVE.value,
            activated_at=self._now(),
            updated_at=self._now(),
        )

        self._record_transfer_event(transfer_id, "transfer_activated", "")

        return {
            "transfer_id": transfer_id,
            "status": "active",
        }

    def suspend_transfer(
        self,
        transfer_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Suspend a transfer"""
        node = self.graph.get_node("international_transfer", transfer_id)
        if not node:
            return {"error": "Transfer not found"}

        self.graph.update_node(
            "international_transfer",
            transfer_id,
            status=TransferStatus.SUSPENDED.value,
            suspended_at=self._now(),
            suspension_reason=reason,
            updated_at=self._now(),
        )

        self._record_transfer_event(transfer_id, "transfer_suspended", reason)

        return {
            "transfer_id": transfer_id,
            "status": "suspended",
        }

    def terminate_transfer(
        self,
        transfer_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Terminate a transfer"""
        node = self.graph.get_node("international_transfer", transfer_id)
        if not node:
            return {"error": "Transfer not found"}

        self.graph.update_node(
            "international_transfer",
            transfer_id,
            status=TransferStatus.TERMINATED.value,
            terminated_at=self._now(),
            termination_reason=reason,
            updated_at=self._now(),
        )

        self._record_transfer_event(transfer_id, "transfer_terminated", reason)

        return {
            "transfer_id": transfer_id,
            "status": "terminated",
        }

    def get_transfer(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get transfer details"""
        node = self.graph.get_node("international_transfer", transfer_id)
        if node:
            return {
                "id": transfer_id,
                **node.properties,
                "data_categories": self._str_to_list(
                    node.properties.get("data_categories", "")
                ),
                "safeguards": self._str_to_list(
                    node.properties.get("safeguards", "")
                ),
            }
        return None

    def get_transfers_by_country(
        self,
        destination_country: str,
    ) -> List[Dict[str, Any]]:
        """Get all transfers to a specific country"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "international_transfer" and
                node.properties.get("destination_country", "").lower() ==
                destination_country.lower()):
                results.append(self.get_transfer(node.id))
        return results

    def get_transfers_by_mechanism(
        self,
        mechanism: TransferMechanism,
    ) -> List[Dict[str, Any]]:
        """Get transfers by legal mechanism"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "international_transfer" and
                node.properties.get("mechanism") == mechanism.value):
                results.append(self.get_transfer(node.id))
        return results

    def get_transfers_pending_tia(self) -> List[Dict[str, Any]]:
        """Get transfers requiring TIA that haven't completed one"""
        results = []
        for node in self.graph.nodes():
            if node.type == "international_transfer":
                if (node.properties.get("tia_required") == "True" and
                    node.properties.get("tia_completed") != "True"):
                    results.append(self.get_transfer(node.id))
        return results

    def get_active_transfers(self) -> List[Dict[str, Any]]:
        """Get all active transfers"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "international_transfer" and
                node.properties.get("status") == TransferStatus.ACTIVE.value):
                results.append(self.get_transfer(node.id))
        return results

    def check_adequacy(self, country: str) -> Dict[str, Any]:
        """Check if a country has an adequacy decision"""
        has_adequacy = country.lower() in ADEQUACY_COUNTRIES
        return {
            "country": country,
            "has_adequacy_decision": has_adequacy,
            "adequacy_countries": list(ADEQUACY_COUNTRIES),
        }

    def _record_transfer_event(
        self,
        transfer_id: str,
        event_type: str,
        details: str,
    ) -> None:
        """Record transfer audit event"""
        event_id = self._make_id("transfer_event", transfer_id)
        self.graph.add_node(
            "transfer_event",
            event_id,
            transfer_id=transfer_id,
            event_type=event_type,
            details=self._sanitize(details),
            timestamp=self._now(),
        )

        if self.graph.has_node("international_transfer", transfer_id):
            self.graph.add_edge(
                "TRANSFER_EVENT",
                ("international_transfer", transfer_id),
                ("transfer_event", event_id),
            )

    def get_transfer_history(self, transfer_id: str) -> List[Dict[str, Any]]:
        """Get audit history for a transfer"""
        events = []
        for node in self.graph.nodes():
            if (node.type == "transfer_event" and
                node.properties.get("transfer_id") == transfer_id):
                events.append({"id": node.id, **node.properties})
        return sorted(events, key=lambda x: x.get("timestamp", ""))

    def get_stats(self) -> Dict[str, Any]:
        """Get transfer statistics"""
        total = 0
        active = 0
        by_mechanism = {}
        by_destination = {}
        pending_tia = 0
        with_adequacy = 0

        for node in self.graph.nodes():
            if node.type == "international_transfer":
                total += 1

                if node.properties.get("status") == TransferStatus.ACTIVE.value:
                    active += 1

                mechanism = node.properties.get("mechanism", "unknown")
                by_mechanism[mechanism] = by_mechanism.get(mechanism, 0) + 1

                destination = node.properties.get("destination_country", "unknown")
                by_destination[destination] = by_destination.get(destination, 0) + 1

                if (node.properties.get("tia_required") == "True" and
                    node.properties.get("tia_completed") != "True"):
                    pending_tia += 1

                if node.properties.get("has_adequacy") == "True":
                    with_adequacy += 1

        return {
            "total_transfers": total,
            "active_transfers": active,
            "by_mechanism": by_mechanism,
            "by_destination": by_destination,
            "pending_tia": pending_tia,
            "with_adequacy": with_adequacy,
        }
