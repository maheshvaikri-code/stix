"""
PHI Classification Store
========================

Manages PHI categories, data elements, sensitivity levels, and safe harbor compliance.
Implements 45 CFR 164.501 definitions and 164.514 de-identification requirements.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import (
    PHICategory, SensitivityLevel, SafeHarborAction,
    PHICategoryDef, DataElement
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class PHIClassificationStore(BaseStore):
    """Store for PHI classification and data element governance"""

    # The 18 HIPAA Safe Harbor identifiers
    SAFE_HARBOR_IDENTIFIERS = [
        "name", "geographic_subdivisions", "dates", "phone_numbers",
        "fax_numbers", "email_addresses", "ssn", "mrn", "health_plan_beneficiary",
        "account_numbers", "certificate_numbers", "vehicle_identifiers",
        "device_identifiers", "web_urls", "ip_addresses", "biometric_identifiers",
        "full_face_photos", "unique_identifying_numbers"
    ]

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "phi_classification")

    # =========================================================================
    # PHI Category Management
    # =========================================================================

    def add_category(
        self,
        name: str,
        hipaa_designation: str,
        sensitivity: SensitivityLevel,
        examples: List[str],
        safe_harbor_action: SafeHarborAction,
        description: str = "",
        category_id: Optional[str] = None
    ) -> str:
        """Add a PHI category definition"""
        cid = category_id or name
        props = {
            "name": name,
            "hipaa_designation": hipaa_designation,
            "sensitivity": sensitivity.value,
            "examples": examples,
            "safe_harbor_action": safe_harbor_action.value,
            "description": description or f"PHI category: {name}"
        }
        return self._add_node("phi_category", cid, props)

    def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Get PHI category by ID"""
        return self._get_node("phi_category", category_id)

    def list_categories(
        self,
        sensitivity: Optional[SensitivityLevel] = None
    ) -> List[Dict[str, Any]]:
        """List all PHI categories"""
        categories = self._find_nodes("phi_category")
        if sensitivity:
            categories = [c for c in categories if c.get("sensitivity") == sensitivity.value]
        return categories

    # =========================================================================
    # Data Element Management
    # =========================================================================

    def add_data_element(
        self,
        field_name: str,
        phi_category: PHICategory,
        hipaa_identifier: bool,
        safe_harbor_action: SafeHarborAction,
        sensitivity_level: SensitivityLevel,
        description: str = "",
        element_id: Optional[str] = None
    ) -> str:
        """Add a data element classification"""
        eid = element_id or f"de_{field_name}"
        props = {
            "field_name": field_name,
            "phi_category": phi_category.value,
            "hipaa_identifier": hipaa_identifier,
            "safe_harbor_action": safe_harbor_action.value,
            "sensitivity_level": sensitivity_level.value,
            "description": description or f"Data element: {field_name}"
        }
        self._add_node("data_element", eid, props)

        # Try to link to category if it exists
        try:
            category_node = self._get_node("phi_category", phi_category.value)
            if category_node:
                self._add_edge(
                    "data_element", eid,
                    "ELEMENT_CLASSIFICATION",
                    "phi_category", phi_category.value,
                    {}
                )
        except Exception:
            # Category doesn't exist, that's ok
            pass

        return eid

    def get_data_element(self, element_id: str) -> Optional[Dict[str, Any]]:
        """Get data element by ID"""
        return self._get_node("data_element", element_id)

    def get_element_by_field(self, field_name: str) -> Optional[Dict[str, Any]]:
        """Get data element by field name"""
        elements = self._find_nodes("data_element", field_name=field_name)
        return elements[0] if elements else None

    def list_data_elements(
        self,
        phi_category: Optional[PHICategory] = None,
        hipaa_identifier: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """List data elements with optional filters"""
        elements = self._find_nodes("data_element")

        if phi_category:
            elements = [e for e in elements if e.get("phi_category") == phi_category.value]
        if hipaa_identifier is not None:
            elements = [e for e in elements if e.get("hipaa_identifier") == hipaa_identifier]

        return elements

    def list_identifiers(self) -> List[Dict[str, Any]]:
        """List all HIPAA identifiers (18 Safe Harbor elements)"""
        return self.list_data_elements(hipaa_identifier=True)

    # =========================================================================
    # Safe Harbor Compliance
    # =========================================================================

    def get_safe_harbor_action(self, field_name: str) -> Dict[str, Any]:
        """Get safe harbor action required for a field"""
        element = self.get_element_by_field(field_name)

        if not element:
            # Unknown field - treat as potential PHI
            return {
                "field": field_name,
                "action": SafeHarborAction.REMOVE.value,
                "reason": "unknown_field_conservative"
            }

        return {
            "field": field_name,
            "action": element.get("safe_harbor_action"),
            "is_identifier": element.get("hipaa_identifier", False),
            "category": element.get("phi_category"),
            "sensitivity": element.get("sensitivity_level")
        }

    def apply_safe_harbor(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply safe harbor de-identification to data"""
        result = {}
        removed = []
        transformed = []

        for field, value in data.items():
            action_info = self.get_safe_harbor_action(field)
            action = action_info.get("action")

            if action == SafeHarborAction.REMOVE.value:
                removed.append(field)
                continue
            elif action == SafeHarborAction.REMOVE_OR_REKEY.value:
                # Generate pseudonym
                result[field] = f"PSEUDO_{hash(str(value)) % 100000:05d}"
                transformed.append(field)
            elif action == SafeHarborAction.GENERALIZE_YEAR.value:
                # Extract year only
                if value and len(str(value)) >= 4:
                    result[field] = str(value)[:4]
                else:
                    result[field] = None
                transformed.append(field)
            elif action == SafeHarborAction.TRUNCATE_3.value:
                # Truncate to first 3 characters (ZIP)
                if value and len(str(value)) >= 3:
                    result[field] = str(value)[:3] + "00"
                else:
                    result[field] = "00000"
                transformed.append(field)
            elif action == SafeHarborAction.AGGREGATE_90.value:
                # Age 90+ becomes "90+"
                try:
                    age = int(value)
                    result[field] = "90+" if age >= 90 else str(age)
                except (ValueError, TypeError):
                    result[field] = value
                transformed.append(field)
            elif action == SafeHarborAction.RETAIN.value:
                result[field] = value
            else:
                # Default: remove unknown
                removed.append(field)

        return {
            "data": result,
            "removed_fields": removed,
            "transformed_fields": transformed,
            "is_de_identified": len(removed) > 0 or len(transformed) > 0
        }

    def check_safe_harbor_compliance(
        self,
        fields: List[str]
    ) -> Dict[str, Any]:
        """Check if a set of fields is safe harbor compliant"""
        violations = []
        warnings = []

        for field in fields:
            element = self.get_element_by_field(field)

            if element and element.get("hipaa_identifier"):
                violations.append({
                    "field": field,
                    "issue": "identifier_present",
                    "action_required": element.get("safe_harbor_action")
                })
            elif not element:
                warnings.append({
                    "field": field,
                    "issue": "unclassified_field"
                })

        return {
            "compliant": len(violations) == 0,
            "violations": violations,
            "warnings": warnings,
            "fields_checked": len(fields)
        }

    # =========================================================================
    # Expert Determination Alternative
    # =========================================================================

    def add_expert_determination(
        self,
        dataset_id: str,
        expert_name: str,
        method: str,  # k_anonymity, l_diversity, differential_privacy
        re_identification_risk: float,
        certification_date: str,
        expires: Optional[str] = None
    ) -> str:
        """Record expert determination for de-identification"""
        eid = self._generate_id("ed")
        props = {
            "dataset_id": dataset_id,
            "expert_name": expert_name,
            "method": method,
            "re_identification_risk": re_identification_risk,
            "certification_date": certification_date,
            "expires": expires,
            "compliant": re_identification_risk < 0.05,
            "description": f"Expert determination for dataset {dataset_id}"
        }
        return self._add_node("expert_determination", eid, props)

    def get_expert_determination(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get expert determination for a dataset"""
        determinations = self._find_nodes("expert_determination", dataset_id=dataset_id)
        if determinations:
            # Return most recent
            return sorted(
                determinations,
                key=lambda d: d.get("certification_date", ""),
                reverse=True
            )[0]
        return None

    def is_dataset_de_identified(self, dataset_id: str) -> Dict[str, Any]:
        """Check if dataset has valid de-identification"""
        determination = self.get_expert_determination(dataset_id)

        if not determination:
            return {
                "de_identified": False,
                "method": None,
                "reason": "no_expert_determination"
            }

        # Check expiration
        expires = determination.get("expires")
        if expires and expires < self._now():
            return {
                "de_identified": False,
                "method": determination.get("method"),
                "reason": "determination_expired"
            }

        return {
            "de_identified": determination.get("compliant", False),
            "method": determination.get("method"),
            "risk": determination.get("re_identification_risk"),
            "expert": determination.get("expert_name"),
            "certified": determination.get("certification_date")
        }

    # =========================================================================
    # Sensitivity Level Management
    # =========================================================================

    def add_sensitivity_level(
        self,
        level: str,
        description: str,
        access_restriction: str,
        encryption_required: bool,
        level_id: Optional[str] = None
    ) -> str:
        """Add a sensitivity level definition"""
        lid = level_id or level
        props = {
            "level": level,
            "description": description,
            "access_restriction": access_restriction,
            "encryption_required": encryption_required
        }
        return self._add_node("sensitivity_level", lid, props)

    def get_sensitivity_level(self, level_id: str) -> Optional[Dict[str, Any]]:
        """Get sensitivity level by ID"""
        return self._get_node("sensitivity_level", level_id)

    def list_sensitivity_levels(self) -> List[Dict[str, Any]]:
        """List all sensitivity levels"""
        return self._find_nodes("sensitivity_level")

    # =========================================================================
    # Field Classification Review
    # =========================================================================

    def schedule_classification_review(
        self,
        element_id: str,
        review_due: str,
        reviewer: str
    ):
        """Schedule a classification review"""
        self._update_node("data_element", element_id, {
            "review_due": review_due,
            "reviewer": reviewer
        })

    def get_pending_reviews(self) -> List[Dict[str, Any]]:
        """Get elements with pending classification reviews"""
        elements = self._find_nodes("data_element")
        now = self._now()

        pending = []
        for element in elements:
            review_due = element.get("review_due")
            if review_due and review_due <= now:
                pending.append(element)

        return pending

    def complete_classification_review(
        self,
        element_id: str,
        reviewer: str,
        changes_made: bool,
        notes: str = ""
    ):
        """Complete a classification review"""
        review_id = self._generate_id("cr")
        props = {
            "element_id": element_id,
            "reviewer": reviewer,
            "review_date": self._now(),
            "changes_made": changes_made,
            "notes": notes or "Classification review completed"
        }
        self._add_node("classification_review", review_id, props)

        # Clear review due date
        self._update_node("data_element", element_id, {
            "last_reviewed": self._now(),
            "last_reviewer": reviewer,
            "review_due": None
        })

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get PHI classification statistics"""
        base_stats = super().get_stats()
        categories = self._find_nodes("phi_category")
        elements = self._find_nodes("data_element")
        identifiers = [e for e in elements if e.get("hipaa_identifier")]
        determinations = self._find_nodes("expert_determination")

        # Count by sensitivity
        by_sensitivity = {}
        for elem in elements:
            sens = elem.get("sensitivity_level", "unknown")
            by_sensitivity[sens] = by_sensitivity.get(sens, 0) + 1

        return {
            **base_stats,
            "categories": len(categories),
            "data_elements": len(elements),
            "hipaa_identifiers": len(identifiers),
            "expert_determinations": len(determinations),
            "by_sensitivity": by_sensitivity
        }
