"""
PII Classification Store
========================

PII detection, classification, and pattern matching.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from .base import BasePIIStore
from ..schema import (
    PIIType, PIICategory, SensitivityLevel, DetectionMethod,
    DetectionConfidence, Regulation, PII_SENSITIVITY_MAP, PII_REGULATION_MAP
)


# Detection patterns for common PII types
PII_PATTERNS: Dict[PIIType, Dict[str, Any]] = {
    PIIType.SSN: {
        "pattern": r"\b\d{3}-\d{2}-\d{4}\b",
        "category": PIICategory.GOVERNMENT_ID,
        "sensitivity": SensitivityLevel.TOP_SECRET,
    },
    PIIType.SSN_LAST4: {
        "pattern": r"\bXXX-XX-\d{4}\b|\b\*{5}\d{4}\b",
        "category": PIICategory.GOVERNMENT_ID,
        "sensitivity": SensitivityLevel.CONFIDENTIAL,
    },
    PIIType.EMAIL: {
        "pattern": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "category": PIICategory.DIRECT_IDENTIFIERS,
        "sensitivity": SensitivityLevel.INTERNAL,
    },
    PIIType.PHONE_NUMBER: {
        "pattern": r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        "category": PIICategory.DIRECT_IDENTIFIERS,
        "sensitivity": SensitivityLevel.INTERNAL,
    },
    PIIType.CREDIT_CARD: {
        "pattern": r"\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b",
        "category": PIICategory.FINANCIAL,
        "sensitivity": SensitivityLevel.RESTRICTED,
    },
    PIIType.IP_ADDRESS: {
        "pattern": r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b",
        "category": PIICategory.ONLINE,
        "sensitivity": SensitivityLevel.INTERNAL,
    },
    PIIType.DATE_OF_BIRTH: {
        "pattern": r"\b(?:0[1-9]|1[0-2])[/-](?:0[1-9]|[12][0-9]|3[01])[/-](?:19|20)\d{2}\b",
        "category": PIICategory.QUASI_IDENTIFIERS,
        "sensitivity": SensitivityLevel.CONFIDENTIAL,
    },
    PIIType.POSTAL_CODE: {
        "pattern": r"\b\d{5}(?:-\d{4})?\b",
        "category": PIICategory.QUASI_IDENTIFIERS,
        "sensitivity": SensitivityLevel.INTERNAL,
    },
    PIIType.PASSPORT_NUMBER: {
        "pattern": r"\b[A-Z]{1,2}[0-9]{6,9}\b",
        "category": PIICategory.GOVERNMENT_ID,
        "sensitivity": SensitivityLevel.CONFIDENTIAL,
    },
    PIIType.IBAN: {
        "pattern": r"\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}(?:[A-Z0-9]?){0,16}\b",
        "category": PIICategory.FINANCIAL,
        "sensitivity": SensitivityLevel.RESTRICTED,
    },
}

# Column name patterns that suggest PII
COLUMN_NAME_PATTERNS: Dict[str, PIIType] = {
    r"(?i)ssn|social.?security": PIIType.SSN,
    r"(?i)email|e.?mail": PIIType.EMAIL,
    r"(?i)phone|telephone|mobile|cell": PIIType.PHONE_NUMBER,
    r"(?i)credit.?card|cc.?num|card.?number": PIIType.CREDIT_CARD,
    r"(?i)first.?name|fname|given.?name": PIIType.FIRST_NAME,
    r"(?i)last.?name|lname|surname|family.?name": PIIType.LAST_NAME,
    r"(?i)full.?name|name": PIIType.FULL_NAME,
    r"(?i)address|street|addr": PIIType.STREET_ADDRESS,
    r"(?i)city": PIIType.CITY,
    r"(?i)state|province": PIIType.STATE_PROVINCE,
    r"(?i)zip|postal": PIIType.POSTAL_CODE,
    r"(?i)dob|birth.?date|date.?of.?birth|birthday": PIIType.DATE_OF_BIRTH,
    r"(?i)ip.?addr|ip.?address|ipaddr": PIIType.IP_ADDRESS,
    r"(?i)passport": PIIType.PASSPORT_NUMBER,
    r"(?i)driver|license|dl.?num": PIIType.DRIVERS_LICENSE,
    r"(?i)bank.?account|account.?num": PIIType.BANK_ACCOUNT,
    r"(?i)salary|income|wage": PIIType.SALARY,
    r"(?i)password|passwd|pwd": PIIType.PASSWORD,
    r"(?i)user.?name|username|login": PIIType.USERNAME,
    r"(?i)medical|mrn|patient.?id": PIIType.MEDICAL_RECORD_NUMBER,
    r"(?i)diagnosis|condition": PIIType.DIAGNOSIS,
}


class ClassificationStore(BasePIIStore):
    """
    PII Detection and Classification Store.

    Provides:
    - Pattern-based PII detection
    - Column name inference
    - Manual classification
    - Sensitivity mapping
    - Regulation mapping
    """

    def classify_field(
        self,
        field_name: str,
        field_id: str,
        source_id: str,
        sample_values: Optional[List[str]] = None,
        manual_type: Optional[PIIType] = None,
    ) -> str:
        """
        Classify a data field for PII.

        Args:
            field_name: Name of the field/column
            field_id: Unique field identifier
            source_id: ID of the data source
            sample_values: Sample values for pattern detection
            manual_type: Manually specified PII type

        Returns:
            Classification record ID
        """
        detected_type = None
        detection_method = DetectionMethod.MANUAL_CLASSIFICATION
        confidence = DetectionConfidence.CONFIRMED

        if manual_type:
            detected_type = manual_type
        else:
            # Try column name inference first
            detected_type, method = self._detect_from_column_name(field_name)
            if detected_type:
                detection_method = method
                confidence = DetectionConfidence.MEDIUM

            # Then try pattern matching on sample values
            if sample_values and not detected_type:
                detected_type, method, conf = self._detect_from_values(sample_values)
                if detected_type:
                    detection_method = method
                    confidence = conf

        if not detected_type:
            # Not classified as PII
            return ""

        # Get sensitivity and regulations
        sensitivity = self._get_sensitivity(detected_type)
        category = self._get_category(detected_type)
        regulations = self._get_regulations(detected_type)

        classification_id = self._make_id("pii_field", f"{source_id}_{field_name}")

        self.graph.add_node(
            "pii_classification",
            classification_id,
            field_name=field_name,
            field_id=field_id,
            source_id=source_id,
            pii_type=detected_type.value,
            category=category.value,
            sensitivity=sensitivity.value,
            detection_method=detection_method.value,
            confidence=confidence.value,
            regulations=self._list_to_str([r.value for r in regulations]),
            sample_count=len(sample_values) if sample_values else 0,
            verified=str(manual_type is not None),
            classified_at=self._now(),
            last_scanned=self._now(),
        )

        # Link to data source
        if self.graph.has_node("data_source", source_id):
            self.graph.add_edge(
                "HAS_PII_FIELD",
                ("data_source", source_id),
                ("pii_classification", classification_id),
            )

        return classification_id

    def _detect_from_column_name(
        self,
        field_name: str
    ) -> Tuple[Optional[PIIType], DetectionMethod]:
        """Detect PII type from column/field name"""
        for pattern, pii_type in COLUMN_NAME_PATTERNS.items():
            if re.search(pattern, field_name):
                return pii_type, DetectionMethod.COLUMN_NAME
        return None, DetectionMethod.COLUMN_NAME

    def _detect_from_values(
        self,
        values: List[str]
    ) -> Tuple[Optional[PIIType], DetectionMethod, DetectionConfidence]:
        """Detect PII type from sample values using regex patterns"""
        if not values:
            return None, DetectionMethod.REGEX_PATTERN, DetectionConfidence.LOW

        # Count matches for each PII type
        match_counts: Dict[PIIType, int] = {}
        total_values = len([v for v in values if v])

        for pii_type, pattern_info in PII_PATTERNS.items():
            pattern = pattern_info["pattern"]
            matches = sum(1 for v in values if v and re.search(pattern, str(v)))
            if matches > 0:
                match_counts[pii_type] = matches

        if not match_counts:
            return None, DetectionMethod.REGEX_PATTERN, DetectionConfidence.LOW

        # Find best match
        best_type = max(match_counts, key=match_counts.get)
        match_ratio = match_counts[best_type] / total_values if total_values > 0 else 0

        # Determine confidence
        if match_ratio >= 0.95:
            confidence = DetectionConfidence.HIGH
        elif match_ratio >= 0.80:
            confidence = DetectionConfidence.MEDIUM
        else:
            confidence = DetectionConfidence.LOW

        return best_type, DetectionMethod.REGEX_PATTERN, confidence

    def _get_sensitivity(self, pii_type: PIIType) -> SensitivityLevel:
        """Get sensitivity level for PII type"""
        return PII_SENSITIVITY_MAP.get(pii_type, SensitivityLevel.CONFIDENTIAL)

    def _get_category(self, pii_type: PIIType) -> PIICategory:
        """Get category for PII type"""
        if pii_type in PII_PATTERNS:
            return PII_PATTERNS[pii_type]["category"]

        # Default mapping
        type_str = pii_type.value.lower()
        if "id" in type_str or "number" in type_str:
            return PIICategory.GOVERNMENT_ID
        if "card" in type_str or "bank" in type_str or "financial" in type_str:
            return PIICategory.FINANCIAL
        if "medical" in type_str or "health" in type_str:
            return PIICategory.HEALTH
        if "password" in type_str or "key" in type_str or "token" in type_str:
            return PIICategory.AUTHENTICATION
        if "ip" in type_str or "cookie" in type_str or "device" in type_str:
            return PIICategory.ONLINE

        return PIICategory.DIRECT_IDENTIFIERS

    def _get_regulations(self, pii_type: PIIType) -> List[Regulation]:
        """Get applicable regulations for PII type"""
        return list(PII_REGULATION_MAP.get(pii_type, {Regulation.GDPR, Regulation.CCPA}))

    def verify_classification(
        self,
        classification_id: str,
        verified_type: PIIType,
        verified_by: str,
    ) -> Dict[str, Any]:
        """Manually verify/correct a classification"""
        node = self.graph.get_node("pii_classification", classification_id)
        if not node:
            return {"error": "Classification not found"}

        sensitivity = self._get_sensitivity(verified_type)
        category = self._get_category(verified_type)
        regulations = self._get_regulations(verified_type)

        self.graph.update_node(
            "pii_classification",
            classification_id,
            pii_type=verified_type.value,
            category=category.value,
            sensitivity=sensitivity.value,
            regulations=self._list_to_str([r.value for r in regulations]),
            verified=str(True),
            verified_by=verified_by,
            verified_at=self._now(),
            confidence=DetectionConfidence.CONFIRMED.value,
        )

        return {
            "classification_id": classification_id,
            "pii_type": verified_type.value,
            "verified": True,
        }

    def get_classification(self, classification_id: str) -> Optional[Dict[str, Any]]:
        """Get classification details"""
        node = self.graph.get_node("pii_classification", classification_id)
        if node:
            return {
                "id": classification_id,
                **node.properties,
                "regulations": self._str_to_list(node.properties.get("regulations", "")),
            }
        return None

    def get_classifications_by_type(
        self,
        pii_type: PIIType
    ) -> List[Dict[str, Any]]:
        """Get all classifications of a specific PII type"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pii_classification" and
                node.properties.get("pii_type") == pii_type.value):
                results.append(self.get_classification(node.id))
        return results

    def get_classifications_by_sensitivity(
        self,
        sensitivity: SensitivityLevel
    ) -> List[Dict[str, Any]]:
        """Get all classifications at a sensitivity level"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pii_classification" and
                node.properties.get("sensitivity") == sensitivity.value):
                results.append(self.get_classification(node.id))
        return results

    def get_unverified_classifications(self) -> List[Dict[str, Any]]:
        """Get classifications that haven't been verified"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pii_classification" and
                node.properties.get("verified") != "True"):
                results.append(self.get_classification(node.id))
        return results

    def detect_pii_in_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in free-form text.

        Returns list of detected PII with locations.
        """
        detections = []

        for pii_type, pattern_info in PII_PATTERNS.items():
            pattern = pattern_info["pattern"]
            for match in re.finditer(pattern, text):
                detections.append({
                    "pii_type": pii_type.value,
                    "category": pattern_info["category"].value,
                    "sensitivity": pattern_info["sensitivity"].value,
                    "start": match.start(),
                    "end": match.end(),
                    "matched_text": match.group(),
                })

        return detections

    def get_stats(self) -> Dict[str, Any]:
        """Get classification statistics"""
        total = 0
        verified = 0
        by_type = {}
        by_sensitivity = {}
        by_category = {}

        for node in self.graph.nodes():
            if node.type == "pii_classification":
                total += 1

                if node.properties.get("verified") == "True":
                    verified += 1

                pii_type = node.properties.get("pii_type", "unknown")
                by_type[pii_type] = by_type.get(pii_type, 0) + 1

                sensitivity = node.properties.get("sensitivity", "unknown")
                by_sensitivity[sensitivity] = by_sensitivity.get(sensitivity, 0) + 1

                category = node.properties.get("category", "unknown")
                by_category[category] = by_category.get(category, 0) + 1

        return {
            "total_classifications": total,
            "verified_classifications": verified,
            "unverified_classifications": total - verified,
            "by_type": by_type,
            "by_sensitivity": by_sensitivity,
            "by_category": by_category,
        }
