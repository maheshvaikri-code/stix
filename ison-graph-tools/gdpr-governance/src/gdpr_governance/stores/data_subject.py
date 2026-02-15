"""
Data Subject Store
==================

Manages data subject records and their personal data inventory.
"""

from typing import Any, Dict, List, Optional

from .base import BaseGDPRStore
from ..schema import (
    PersonalDataCategory, DataSensitivity, DataSubject
)


class DataSubjectStore(BaseGDPRStore):
    """
    Manages data subject records.

    Tracks:
    - Data subject registration
    - Personal data inventory per subject
    - Data categories held
    - Processing activities affecting subject
    """

    def register_subject(
        self,
        subject_id: str,
        external_id: Optional[str] = None,
        email: Optional[str] = None,
        data_categories: Optional[List[PersonalDataCategory]] = None,
    ) -> str:
        """Register a new data subject"""
        node_id = f"subject_{subject_id}"

        categories = [c.value for c in (data_categories or [])]

        self.graph.add_node(
            "data_subject",
            node_id,
            subject_id=subject_id,
            external_id=external_id or "",
            email=email or "",
            data_categories=self._list_to_str(categories),
            created_at=self._now(),
            last_activity=self._now(),
        )

        return node_id

    def update_subject(
        self,
        subject_id: str,
        email: Optional[str] = None,
        data_categories: Optional[List[PersonalDataCategory]] = None,
    ) -> None:
        """Update data subject information"""
        node_id = f"subject_{subject_id}"
        node = self.graph.get_node("data_subject", node_id)
        if node:
            updates = {"last_activity": self._now()}
            if email:
                updates["email"] = email
            if data_categories:
                updates["data_categories"] = self._list_to_str(
                    [c.value for c in data_categories]
                )
            self.graph.update_node("data_subject", node_id, **updates)

    def add_data_category(
        self,
        subject_id: str,
        category: PersonalDataCategory,
        source: str,
        purpose: str,
    ) -> str:
        """Record a data category held for a subject"""
        node_id = f"subject_{subject_id}"
        cat_id = self._make_id("data_cat", f"{subject_id}_{category.value}")

        # Create data category node
        self.graph.add_node(
            "personal_data_category",
            cat_id,
            subject_id=subject_id,
            category=category.value,
            sensitivity=self._get_sensitivity(category).value,
            source=source,
            purpose=purpose,
            collected_at=self._now(),
        )

        # Link to subject
        if self.graph.has_node("data_subject", node_id):
            self.graph.add_edge(
                "HAS_DATA",
                ("data_subject", node_id),
                ("personal_data_category", cat_id),
            )

        return cat_id

    def _get_sensitivity(self, category: PersonalDataCategory) -> DataSensitivity:
        """Determine sensitivity level for a category"""
        special_categories = {
            PersonalDataCategory.BIOMETRIC,
            PersonalDataCategory.GENETIC,
            PersonalDataCategory.HEALTH,
            PersonalDataCategory.RACIAL_ETHNIC,
            PersonalDataCategory.POLITICAL,
            PersonalDataCategory.RELIGIOUS,
            PersonalDataCategory.TRADE_UNION,
            PersonalDataCategory.SEXUAL_ORIENTATION,
        }
        if category == PersonalDataCategory.CRIMINAL:
            return DataSensitivity.CRIMINAL
        if category in special_categories:
            return DataSensitivity.SPECIAL_CATEGORY
        return DataSensitivity.STANDARD

    def get_subject(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """Get data subject record"""
        node_id = f"subject_{subject_id}"
        node = self.graph.get_node("data_subject", node_id)
        if node:
            return {
                "id": node_id,
                **node.properties,
                "data_categories": self._str_to_list(
                    node.properties.get("data_categories", "")
                ),
            }
        return None

    def get_subject_data_inventory(
        self,
        subject_id: str
    ) -> List[Dict[str, Any]]:
        """Get all personal data held for a subject"""
        inventory = []
        for node in self.graph.nodes():
            if (node.type == "personal_data_category" and
                node.properties.get("subject_id") == subject_id):
                inventory.append({
                    "id": node.id,
                    **node.properties
                })
        return inventory

    def delete_subject_data(
        self,
        subject_id: str,
        categories: Optional[List[PersonalDataCategory]] = None,
        reason: str = "erasure_request",
    ) -> Dict[str, Any]:
        """
        Delete personal data for a subject (Article 17 erasure).

        Args:
            subject_id: Data subject ID
            categories: Specific categories to delete (None = all)
            reason: Reason for deletion

        Returns:
            Summary of deleted data
        """
        deleted = []

        for node in list(self.graph.nodes()):
            if (node.type == "personal_data_category" and
                node.properties.get("subject_id") == subject_id):
                if categories is None or PersonalDataCategory(
                    node.properties.get("category")
                ) in categories:
                    deleted.append({
                        "category": node.properties.get("category"),
                        "deleted_at": self._now(),
                    })
                    self.graph.remove_node("personal_data_category", node.id)

        # Record deletion
        deletion_id = self._make_id("deletion", subject_id)
        self.graph.add_node(
            "data_deletion",
            deletion_id,
            subject_id=subject_id,
            reason=reason,
            categories_deleted=self._list_to_str([d["category"] for d in deleted]),
            deleted_at=self._now(),
        )

        return {
            "subject_id": subject_id,
            "deleted_count": len(deleted),
            "deleted_categories": deleted,
            "deletion_id": deletion_id,
        }

    def search_subjects(
        self,
        email: Optional[str] = None,
        external_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search for data subjects"""
        results = []
        for node in self.graph.nodes():
            if node.type == "data_subject":
                if email and node.properties.get("email") == email:
                    results.append({"id": node.id, **node.properties})
                elif external_id and node.properties.get("external_id") == external_id:
                    results.append({"id": node.id, **node.properties})
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get data subject statistics"""
        subjects = 0
        data_categories = 0
        special_category_subjects = 0

        for node in self.graph.nodes():
            if node.type == "data_subject":
                subjects += 1
                categories = self._str_to_list(
                    node.properties.get("data_categories", "")
                )
                for cat in categories:
                    if cat in ["biometric", "genetic", "health", "racial_ethnic",
                              "political", "religious", "trade_union", "sexual_orientation"]:
                        special_category_subjects += 1
                        break
            elif node.type == "personal_data_category":
                data_categories += 1

        return {
            "total_subjects": subjects,
            "data_category_records": data_categories,
            "special_category_subjects": special_category_subjects,
        }
