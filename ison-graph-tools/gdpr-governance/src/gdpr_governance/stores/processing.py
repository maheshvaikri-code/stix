"""
Processing Activities Store
============================

Records of Processing Activities (Article 30).
"""

from typing import Any, Dict, List, Optional

from .base import BaseGDPRStore
from ..schema import (
    LawfulBasis, SpecialCategoryBasis, PersonalDataCategory,
    ProcessingPurpose, TransferMechanism, DPIATrigger
)


class ProcessingActivityStore(BaseGDPRStore):
    """
    Records of Processing Activities (GDPR Article 30).

    Tracks:
    - Processing activities and their purposes
    - Lawful bases for processing
    - Data categories processed
    - Recipients and transfers
    - Retention periods
    """

    def register_activity(
        self,
        name: str,
        purpose: str,
        lawful_basis: LawfulBasis,
        data_categories: List[PersonalDataCategory],
        data_subjects: List[str],
        recipients: List[str],
        retention_period: str,
        security_measures: List[str],
        controller_id: str,
        processor_id: Optional[str] = None,
        special_category_basis: Optional[SpecialCategoryBasis] = None,
        description: str = "",
    ) -> str:
        """
        Register a processing activity (Article 30 record).

        Args:
            name: Name of the processing activity
            purpose: Purpose of processing
            lawful_basis: Legal basis under Article 6
            data_categories: Categories of personal data
            data_subjects: Categories of data subjects
            recipients: Recipients of data
            retention_period: How long data is retained
            security_measures: Technical/organizational measures
            controller_id: ID of the controller
            processor_id: ID of processor (if applicable)
            special_category_basis: Article 9 basis if special category data
            description: Additional description

        Returns:
            Processing activity ID
        """
        activity_id = self._make_id("proc", name)

        # Determine if DPIA might be required
        dpia_triggers = self._assess_dpia_triggers(data_categories, purpose)

        self.graph.add_node(
            "processing_activity",
            activity_id,
            name=name,
            purpose=self._sanitize(purpose),
            description=self._sanitize(description),
            lawful_basis=lawful_basis.value,
            special_category_basis=special_category_basis.value if special_category_basis else "",
            data_categories=self._list_to_str([c.value for c in data_categories]),
            data_subjects=self._list_to_str(data_subjects),
            recipients=self._list_to_str(recipients),
            retention_period=retention_period,
            security_measures=self._list_to_str(security_measures),
            controller_id=controller_id,
            processor_id=processor_id or "",
            dpia_triggers=self._list_to_str([t.value for t in dpia_triggers]),
            dpia_required=str(len(dpia_triggers) > 0),
            transfer_countries="",
            created_at=self._now(),
            updated_at=self._now(),
            status="active",
        )

        # Link to controller
        if self.graph.has_node("controller", controller_id):
            self.graph.add_edge(
                "CONTROLLED_BY",
                ("processing_activity", activity_id),
                ("controller", controller_id),
            )

        # Link to processor if provided
        if processor_id and self.graph.has_node("processor", processor_id):
            self.graph.add_edge(
                "PROCESSED_BY",
                ("processing_activity", activity_id),
                ("processor", processor_id),
            )

        return activity_id

    def _assess_dpia_triggers(
        self,
        data_categories: List[PersonalDataCategory],
        purpose: str
    ) -> List[DPIATrigger]:
        """Assess if processing triggers DPIA requirement"""
        triggers = []

        # Check for special category data
        special = {
            PersonalDataCategory.BIOMETRIC,
            PersonalDataCategory.GENETIC,
            PersonalDataCategory.HEALTH,
            PersonalDataCategory.RACIAL_ETHNIC,
            PersonalDataCategory.POLITICAL,
            PersonalDataCategory.RELIGIOUS,
            PersonalDataCategory.TRADE_UNION,
            PersonalDataCategory.SEXUAL_ORIENTATION,
        }
        if any(c in special for c in data_categories):
            triggers.append(DPIATrigger.LARGE_SCALE_SPECIAL)

        if PersonalDataCategory.BIOMETRIC in data_categories:
            triggers.append(DPIATrigger.BIOMETRIC)
        if PersonalDataCategory.GENETIC in data_categories:
            triggers.append(DPIATrigger.GENETIC)

        # Check purpose keywords
        purpose_lower = purpose.lower()
        if "profiling" in purpose_lower or "automated" in purpose_lower:
            triggers.append(DPIATrigger.PROFILING)
        if "monitoring" in purpose_lower or "tracking" in purpose_lower:
            triggers.append(DPIATrigger.SYSTEMATIC_MONITORING)

        return triggers

    def update_activity(
        self,
        activity_id: str,
        **updates
    ) -> None:
        """Update a processing activity"""
        node = self.graph.get_node("processing_activity", activity_id)
        if node:
            updates["updated_at"] = self._now()
            self.graph.update_node("processing_activity", activity_id, **updates)

    def add_transfer(
        self,
        activity_id: str,
        country: str,
        mechanism: TransferMechanism,
        recipient: str,
    ) -> None:
        """Record an international transfer for this activity"""
        node = self.graph.get_node("processing_activity", activity_id)
        if node:
            current = self._str_to_list(node.properties.get("transfer_countries", ""))
            if country not in current:
                current.append(country)
            self.graph.update_node(
                "processing_activity",
                activity_id,
                transfer_countries=self._list_to_str(current),
                updated_at=self._now(),
            )

    def link_to_dpia(self, activity_id: str, dpia_id: str) -> None:
        """Link processing activity to a DPIA"""
        if (self.graph.has_node("processing_activity", activity_id) and
            self.graph.has_node("dpia", dpia_id)):
            self.graph.add_edge(
                "HAS_DPIA",
                ("processing_activity", activity_id),
                ("dpia", dpia_id),
            )
            self.graph.update_node(
                "processing_activity",
                activity_id,
                dpia_id=dpia_id,
                updated_at=self._now(),
            )

    def get_activity(self, activity_id: str) -> Optional[Dict[str, Any]]:
        """Get a processing activity record"""
        node = self.graph.get_node("processing_activity", activity_id)
        if node:
            return {
                "id": activity_id,
                **node.properties,
                "data_categories": self._str_to_list(
                    node.properties.get("data_categories", "")
                ),
                "data_subjects": self._str_to_list(
                    node.properties.get("data_subjects", "")
                ),
                "recipients": self._str_to_list(
                    node.properties.get("recipients", "")
                ),
                "security_measures": self._str_to_list(
                    node.properties.get("security_measures", "")
                ),
                "dpia_required": node.properties.get("dpia_required") == "True",
            }
        return None

    def list_activities(
        self,
        controller_id: Optional[str] = None,
        lawful_basis: Optional[LawfulBasis] = None,
        status: str = "active",
    ) -> List[Dict[str, Any]]:
        """List processing activities with optional filters"""
        results = []
        for node in self.graph.nodes():
            if node.type == "processing_activity":
                if status and node.properties.get("status") != status:
                    continue
                if controller_id and node.properties.get("controller_id") != controller_id:
                    continue
                if lawful_basis and node.properties.get("lawful_basis") != lawful_basis.value:
                    continue
                results.append(self.get_activity(node.id))
        return results

    def get_activities_by_data_category(
        self,
        category: PersonalDataCategory
    ) -> List[Dict[str, Any]]:
        """Find all activities processing a specific data category"""
        results = []
        for node in self.graph.nodes():
            if node.type == "processing_activity":
                categories = self._str_to_list(
                    node.properties.get("data_categories", "")
                )
                if category.value in categories:
                    results.append(self.get_activity(node.id))
        return results

    def get_activities_requiring_dpia(self) -> List[Dict[str, Any]]:
        """Get all activities that require DPIA"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "processing_activity" and
                node.properties.get("dpia_required") == "True"):
                results.append(self.get_activity(node.id))
        return results

    def archive_activity(self, activity_id: str, reason: str) -> None:
        """Archive a processing activity"""
        self.update_activity(
            activity_id,
            status="archived",
            archived_at=self._now(),
            archive_reason=reason,
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get processing activity statistics"""
        total = 0
        active = 0
        by_lawful_basis = {}
        dpia_required = 0
        with_transfers = 0

        for node in self.graph.nodes():
            if node.type == "processing_activity":
                total += 1
                if node.properties.get("status") == "active":
                    active += 1

                basis = node.properties.get("lawful_basis", "unknown")
                by_lawful_basis[basis] = by_lawful_basis.get(basis, 0) + 1

                if node.properties.get("dpia_required") == "True":
                    dpia_required += 1

                if node.properties.get("transfer_countries"):
                    with_transfers += 1

        return {
            "total_activities": total,
            "active_activities": active,
            "by_lawful_basis": by_lawful_basis,
            "dpia_required": dpia_required,
            "with_international_transfers": with_transfers,
        }
