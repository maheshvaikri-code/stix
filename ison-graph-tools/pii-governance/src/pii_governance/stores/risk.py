"""
Risk Assessment Store
=====================

PII risk assessment and compliance gap analysis.
"""

from typing import Any, Dict, List, Optional

from .base import BasePIIStore
from ..schema import (
    RiskLevel, SensitivityLevel, ProtectionStatus, Regulation
)


class RiskAssessmentStore(BasePIIStore):
    """
    PII Risk Assessment Store.

    Provides:
    - Risk scoring and assessment
    - Compliance gap analysis
    - Remediation recommendations
    - Risk trending
    """

    def create_assessment(
        self,
        name: str,
        scope: str,
        assessor: str,
        data_sources: List[str] = None,
    ) -> str:
        """
        Create a new risk assessment.

        Args:
            name: Assessment name
            scope: What is being assessed
            assessor: Who is performing the assessment
            data_sources: List of data source IDs to assess

        Returns:
            Assessment ID
        """
        assessment_id = self._make_id("assessment", name)

        self.graph.add_node(
            "risk_assessment",
            assessment_id,
            name=name,
            scope=self._sanitize(scope),
            assessor=assessor,
            data_sources=self._list_to_str(data_sources or []),
            status="in_progress",
            sensitivity_score="0",
            exposure_score="0",
            protection_score="0",
            overall_risk_level="",
            compliance_gaps="",
            recommendations="",
            created_at=self._now(),
            completed_at="",
            next_review="",
        )

        return assessment_id

    def calculate_risk_scores(
        self,
        assessment_id: str,
    ) -> Dict[str, Any]:
        """
        Calculate risk scores for an assessment.

        Analyzes linked data sources and inventory items.
        """
        node = self.graph.get_node("risk_assessment", assessment_id)
        if not node:
            return {"error": "Assessment not found"}

        data_sources = self._str_to_list(node.properties.get("data_sources", ""))

        # Gather inventory items for assessment
        items = []
        for source_id in data_sources:
            for n in self.graph.nodes():
                if (n.type == "pii_inventory_item" and
                    n.properties.get("source_id") == source_id):
                    items.append(n.properties)

        if not items:
            # Check all inventory if no specific sources
            for n in self.graph.nodes():
                if n.type == "pii_inventory_item":
                    items.append(n.properties)

        # Calculate sensitivity score (0-100)
        sensitivity_score = self._calculate_sensitivity_score(items)

        # Calculate exposure score (0-100)
        exposure_score = self._calculate_exposure_score(items)

        # Calculate protection score (0-100, higher is better)
        protection_score = self._calculate_protection_score(items)

        # Overall risk level
        overall_risk = self._determine_overall_risk(
            sensitivity_score, exposure_score, protection_score
        )

        self.graph.update_node(
            "risk_assessment",
            assessment_id,
            sensitivity_score=str(round(sensitivity_score, 2)),
            exposure_score=str(round(exposure_score, 2)),
            protection_score=str(round(protection_score, 2)),
            overall_risk_level=overall_risk.value,
            items_assessed=str(len(items)),
        )

        return {
            "assessment_id": assessment_id,
            "sensitivity_score": round(sensitivity_score, 2),
            "exposure_score": round(exposure_score, 2),
            "protection_score": round(protection_score, 2),
            "overall_risk_level": overall_risk.value,
            "items_assessed": len(items),
        }

    def _calculate_sensitivity_score(self, items: List[Dict]) -> float:
        """Calculate sensitivity score based on data sensitivity levels"""
        if not items:
            return 0

        sensitivity_weights = {
            SensitivityLevel.PUBLIC.value: 10,
            SensitivityLevel.INTERNAL.value: 30,
            SensitivityLevel.CONFIDENTIAL.value: 60,
            SensitivityLevel.RESTRICTED.value: 80,
            SensitivityLevel.TOP_SECRET.value: 100,
        }

        total_weight = sum(
            sensitivity_weights.get(item.get("sensitivity"), 50)
            for item in items
        )

        return total_weight / len(items)

    def _calculate_exposure_score(self, items: List[Dict]) -> float:
        """Calculate exposure score based on volume and risk levels"""
        if not items:
            return 0

        risk_weights = {
            RiskLevel.LOW.value: 10,
            RiskLevel.MEDIUM.value: 40,
            RiskLevel.HIGH.value: 70,
            RiskLevel.CRITICAL.value: 100,
        }

        total_weight = sum(
            risk_weights.get(item.get("risk_level"), 50)
            for item in items
        )

        return total_weight / len(items)

    def _calculate_protection_score(self, items: List[Dict]) -> float:
        """Calculate protection score (higher = better protected)"""
        if not items:
            return 100

        protection_weights = {
            ProtectionStatus.ANONYMIZED.value: 100,
            ProtectionStatus.PSEUDONYMIZED.value: 90,
            ProtectionStatus.TOKENIZED.value: 90,
            ProtectionStatus.FULLY_ENCRYPTED.value: 85,
            ProtectionStatus.ENCRYPTED_AT_REST.value: 70,
            ProtectionStatus.ENCRYPTED_IN_TRANSIT.value: 60,
            ProtectionStatus.MASKED.value: 70,
            ProtectionStatus.REDACTED.value: 95,
            ProtectionStatus.UNPROTECTED.value: 0,
        }

        total_weight = sum(
            protection_weights.get(item.get("protection_status"), 50)
            for item in items
        )

        return total_weight / len(items)

    def _determine_overall_risk(
        self,
        sensitivity: float,
        exposure: float,
        protection: float
    ) -> RiskLevel:
        """Determine overall risk level from scores"""
        # Risk increases with sensitivity and exposure, decreases with protection
        risk_score = (sensitivity + exposure) / 2 - (protection / 2)

        if risk_score >= 60:
            return RiskLevel.CRITICAL
        elif risk_score >= 40:
            return RiskLevel.HIGH
        elif risk_score >= 20:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def analyze_compliance_gaps(
        self,
        assessment_id: str,
        regulations: List[Regulation],
    ) -> Dict[str, Any]:
        """
        Analyze compliance gaps for specified regulations.
        """
        node = self.graph.get_node("risk_assessment", assessment_id)
        if not node:
            return {"error": "Assessment not found"}

        gaps = []

        # Gather inventory items
        items = []
        for n in self.graph.nodes():
            if n.type == "pii_inventory_item":
                items.append(n.properties)

        for reg in regulations:
            reg_gaps = self._check_regulation_compliance(items, reg)
            gaps.extend(reg_gaps)

        self.graph.update_node(
            "risk_assessment",
            assessment_id,
            compliance_gaps=str(len(gaps)),
            compliance_gaps_details=str(gaps)[:1000],  # Truncate for storage
        )

        return {
            "assessment_id": assessment_id,
            "regulations_checked": [r.value for r in regulations],
            "total_gaps": len(gaps),
            "gaps": gaps,
        }

    def _check_regulation_compliance(
        self,
        items: List[Dict],
        regulation: Regulation
    ) -> List[Dict[str, Any]]:
        """Check compliance with a specific regulation"""
        gaps = []

        for item in items:
            regs = self._str_to_list(item.get("regulations", ""))
            if regulation.value in regs:
                # Check protection requirements
                protection = item.get("protection_status")
                sensitivity = item.get("sensitivity")

                # High sensitivity + unprotected = gap
                if (sensitivity in [SensitivityLevel.RESTRICTED.value,
                                   SensitivityLevel.TOP_SECRET.value] and
                    protection == ProtectionStatus.UNPROTECTED.value):
                    gaps.append({
                        "regulation": regulation.value,
                        "item_id": item.get("source_id"),
                        "pii_type": item.get("pii_type"),
                        "issue": "High sensitivity data unprotected",
                        "severity": "critical",
                        "recommendation": "Implement encryption or tokenization",
                    })

                # Check retention
                if not item.get("retention_period"):
                    gaps.append({
                        "regulation": regulation.value,
                        "item_id": item.get("source_id"),
                        "pii_type": item.get("pii_type"),
                        "issue": "No retention period defined",
                        "severity": "medium",
                        "recommendation": "Define and document retention period",
                    })

        return gaps

    def add_recommendation(
        self,
        assessment_id: str,
        recommendation: str,
        priority: str,
        affected_items: List[str] = None,
    ) -> str:
        """Add a recommendation to an assessment"""
        node = self.graph.get_node("risk_assessment", assessment_id)
        if not node:
            return ""

        rec_id = self._make_id("recommendation", assessment_id)

        self.graph.add_node(
            "risk_recommendation",
            rec_id,
            assessment_id=assessment_id,
            recommendation=self._sanitize(recommendation),
            priority=priority,
            affected_items=self._list_to_str(affected_items or []),
            status="pending",
            created_at=self._now(),
        )

        self.graph.add_edge(
            "HAS_RECOMMENDATION",
            ("risk_assessment", assessment_id),
            ("risk_recommendation", rec_id),
        )

        return rec_id

    def complete_assessment(
        self,
        assessment_id: str,
        summary: str,
        next_review_days: int = 90,
    ) -> Dict[str, Any]:
        """Complete an assessment"""
        node = self.graph.get_node("risk_assessment", assessment_id)
        if not node:
            return {"error": "Assessment not found"}

        self.graph.update_node(
            "risk_assessment",
            assessment_id,
            status="completed",
            summary=self._sanitize(summary),
            completed_at=self._now(),
            next_review=self._future(next_review_days),
        )

        return {
            "assessment_id": assessment_id,
            "status": "completed",
            "next_review": self._future(next_review_days),
        }

    def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get assessment details"""
        node = self.graph.get_node("risk_assessment", assessment_id)
        if node:
            # Get recommendations
            recommendations = []
            for n in self.graph.nodes():
                if (n.type == "risk_recommendation" and
                    n.properties.get("assessment_id") == assessment_id):
                    recommendations.append({"id": n.id, **n.properties})

            return {
                "id": assessment_id,
                **node.properties,
                "data_sources": self._str_to_list(node.properties.get("data_sources", "")),
                "recommendations": recommendations,
            }
        return None

    def get_assessments_due_for_review(self) -> List[Dict[str, Any]]:
        """Get assessments past their review date"""
        now = self._now()
        results = []
        for node in self.graph.nodes():
            if node.type == "risk_assessment":
                next_review = node.properties.get("next_review", "")
                if next_review and next_review < now:
                    results.append(self.get_assessment(node.id))
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get risk assessment statistics"""
        total = 0
        completed = 0
        by_risk_level = {}
        avg_sensitivity = 0
        avg_protection = 0

        sensitivity_sum = 0
        protection_sum = 0
        scored_count = 0

        for node in self.graph.nodes():
            if node.type == "risk_assessment":
                total += 1

                if node.properties.get("status") == "completed":
                    completed += 1

                risk = node.properties.get("overall_risk_level", "unknown")
                by_risk_level[risk] = by_risk_level.get(risk, 0) + 1

                try:
                    sens = float(node.properties.get("sensitivity_score", "0"))
                    prot = float(node.properties.get("protection_score", "0"))
                    if sens > 0 or prot > 0:
                        sensitivity_sum += sens
                        protection_sum += prot
                        scored_count += 1
                except ValueError:
                    pass

        if scored_count > 0:
            avg_sensitivity = sensitivity_sum / scored_count
            avg_protection = protection_sum / scored_count

        return {
            "total_assessments": total,
            "completed_assessments": completed,
            "by_risk_level": by_risk_level,
            "average_sensitivity_score": round(avg_sensitivity, 2),
            "average_protection_score": round(avg_protection, 2),
        }
