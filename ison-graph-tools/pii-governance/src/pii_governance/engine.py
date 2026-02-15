"""
PII Governance Engine
=====================

Main engine for comprehensive PII governance and management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from ison_graph import ISONGraph

from .stores import (
    ClassificationStore,
    InventoryStore,
    RiskAssessmentStore,
    LineageStore,
)
from .schema import (
    PIIType, PIICategory, SensitivityLevel, ProtectionStatus,
    Regulation, DataSourceType, StorageLocation, RiskLevel,
    PII_REGULATION_MAP, PII_SENSITIVITY_MAP
)


class PIIGovernance:
    """
    PII Governance Engine.

    Provides unified access to all PII governance stores and
    comprehensive PII management capabilities.

    Usage:
        from ison_graph import ISONGraph
        from pii_governance import PIIGovernance

        graph = ISONGraph()
        pii = PIIGovernance(graph)

        # Register data sources
        pii.inventory.register_data_source(...)

        # Classify PII fields
        pii.classification.classify_field(...)

        # Assess risks
        pii.risk.create_assessment(...)

        # Track lineage
        pii.lineage.record_data_flow(...)

        # Get comprehensive report
        report = pii.get_governance_report()
    """

    def __init__(self, graph: ISONGraph):
        """
        Initialize PII Governance engine.

        Args:
            graph: ISONGraph instance to use as backend
        """
        self.graph = graph

        # Initialize all stores
        self.classification = ClassificationStore(graph)
        self.inventory = InventoryStore(graph)
        self.risk = RiskAssessmentStore(graph)
        self.lineage = LineageStore(graph)

    # =========================================================================
    # Quick Operations
    # =========================================================================

    def discover_and_classify(
        self,
        source_id: str,
        fields: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Discover and classify PII in a data source.

        Args:
            source_id: Data source ID
            fields: List of field definitions with name and sample_values

        Returns:
            Discovery results with classifications
        """
        results = {
            "source_id": source_id,
            "fields_analyzed": len(fields),
            "pii_found": 0,
            "classifications": [],
        }

        for field in fields:
            field_name = field.get("name", "")
            field_id = field.get("id", field_name)
            sample_values = field.get("sample_values", [])

            classification_id = self.classification.classify_field(
                field_name=field_name,
                field_id=field_id,
                source_id=source_id,
                sample_values=sample_values,
            )

            if classification_id:
                results["pii_found"] += 1
                classification = self.classification.get_classification(classification_id)
                results["classifications"].append(classification)

        # Update data source with scan results
        if results["pii_found"] > 0:
            highest_sensitivity = max(
                SensitivityLevel(c["sensitivity"])
                for c in results["classifications"]
            )
            self.inventory.record_scan(
                source_id=source_id,
                pii_fields_found=results["pii_found"],
                highest_sensitivity=highest_sensitivity,
            )

        return results

    def scan_text_for_pii(self, text: str) -> Dict[str, Any]:
        """
        Scan text for PII.

        Args:
            text: Text to scan

        Returns:
            Detection results with locations
        """
        detections = self.classification.detect_pii_in_text(text)

        # Group by type
        by_type = {}
        for d in detections:
            pii_type = d["pii_type"]
            if pii_type not in by_type:
                by_type[pii_type] = []
            by_type[pii_type].append(d)

        return {
            "text_length": len(text),
            "total_detections": len(detections),
            "unique_pii_types": len(by_type),
            "by_type": by_type,
            "detections": detections,
        }

    def assess_data_source_risk(
        self,
        source_id: str,
        assessor: str,
        regulations: Optional[List[Regulation]] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive risk assessment of a data source.

        Args:
            source_id: Data source ID
            assessor: Who is performing the assessment
            regulations: Regulations to check compliance against

        Returns:
            Assessment results
        """
        # Create assessment
        assessment_id = self.risk.create_assessment(
            name=f"Assessment for {source_id}",
            scope=f"Data source: {source_id}",
            assessor=assessor,
            data_sources=[source_id],
        )

        # Calculate risk scores
        scores = self.risk.calculate_risk_scores(assessment_id)

        # Check compliance gaps
        regs = regulations or [Regulation.GDPR, Regulation.CCPA]
        gaps = self.risk.analyze_compliance_gaps(assessment_id, regs)

        # Add recommendations based on findings
        if scores.get("protection_score", 100) < 50:
            self.risk.add_recommendation(
                assessment_id=assessment_id,
                recommendation="Implement encryption for sensitive PII fields",
                priority="high",
            )

        if gaps.get("total_gaps", 0) > 0:
            self.risk.add_recommendation(
                assessment_id=assessment_id,
                recommendation="Address compliance gaps identified in assessment",
                priority="critical",
            )

        # Complete assessment
        self.risk.complete_assessment(
            assessment_id=assessment_id,
            summary=f"Assessed {scores.get('items_assessed', 0)} items. "
                   f"Risk level: {scores.get('overall_risk_level', 'unknown')}",
        )

        return {
            "assessment_id": assessment_id,
            "scores": scores,
            "compliance_gaps": gaps,
            "status": "completed",
        }

    def get_pii_map(self, pii_type: Optional[PIIType] = None) -> Dict[str, Any]:
        """
        Get a map of where PII exists across data sources.

        Args:
            pii_type: Optional filter for specific PII type

        Returns:
            Map of PII locations
        """
        pii_map = {}

        for node in self.graph.nodes():
            if node.type == "pii_classification":
                if pii_type and node.properties.get("pii_type") != pii_type.value:
                    continue

                source_id = node.properties.get("source_id", "unknown")
                detected_type = node.properties.get("pii_type")

                if source_id not in pii_map:
                    pii_map[source_id] = {
                        "source": self.inventory.get_data_source(source_id),
                        "pii_types": {},
                    }

                if detected_type not in pii_map[source_id]["pii_types"]:
                    pii_map[source_id]["pii_types"][detected_type] = []

                pii_map[source_id]["pii_types"][detected_type].append({
                    "field": node.properties.get("field_name"),
                    "sensitivity": node.properties.get("sensitivity"),
                    "verified": node.properties.get("verified") == "True",
                })

        return {
            "generated_at": datetime.now().isoformat(),
            "filter": pii_type.value if pii_type else "all",
            "sources_with_pii": len(pii_map),
            "map": pii_map,
        }

    def get_regulation_coverage(
        self,
        regulation: Regulation
    ) -> Dict[str, Any]:
        """
        Get all PII covered by a specific regulation.

        Args:
            regulation: Regulation to check

        Returns:
            Coverage report
        """
        covered_items = []

        for node in self.graph.nodes():
            if node.type == "pii_classification":
                regs = node.properties.get("regulations", "").split(",")
                if regulation.value in regs:
                    covered_items.append({
                        "field": node.properties.get("field_name"),
                        "pii_type": node.properties.get("pii_type"),
                        "source": node.properties.get("source_id"),
                        "sensitivity": node.properties.get("sensitivity"),
                    })

        return {
            "regulation": regulation.value,
            "covered_items": len(covered_items),
            "items": covered_items,
        }

    # =========================================================================
    # Governance Reporting
    # =========================================================================

    def get_governance_report(self) -> Dict[str, Any]:
        """
        Generate comprehensive PII governance report.

        Returns:
            Complete governance status and metrics
        """
        # Gather stats from all stores
        classification_stats = self.classification.get_stats()
        inventory_stats = self.inventory.get_stats()
        risk_stats = self.risk.get_stats()
        lineage_stats = self.lineage.get_stats()

        # Calculate governance score
        governance_score = self._calculate_governance_score(
            classification_stats,
            inventory_stats,
            risk_stats,
        )

        # Identify issues
        issues = self._identify_governance_issues(
            classification_stats,
            inventory_stats,
            risk_stats,
        )

        return {
            "generated_at": datetime.now().isoformat(),
            "governance_score": governance_score,
            "summary": {
                "total_data_sources": inventory_stats["total_data_sources"],
                "total_pii_classifications": classification_stats["total_classifications"],
                "unverified_classifications": classification_stats["unverified_classifications"],
                "total_inventory_items": inventory_stats["total_inventory_items"],
                "unprotected_items": inventory_stats["unprotected_items"],
                "total_assessments": risk_stats["total_assessments"],
                "data_flows_tracked": lineage_stats["total_data_flows"],
            },
            "issues": issues,
            "detailed_stats": {
                "classification": classification_stats,
                "inventory": inventory_stats,
                "risk": risk_stats,
                "lineage": lineage_stats,
            },
        }

    def _calculate_governance_score(
        self,
        classification_stats: Dict,
        inventory_stats: Dict,
        risk_stats: Dict,
    ) -> float:
        """Calculate overall governance score (0-100)"""
        score = 100.0

        # Penalize for unverified classifications
        total_class = classification_stats.get("total_classifications", 0)
        unverified = classification_stats.get("unverified_classifications", 0)
        if total_class > 0:
            unverified_ratio = unverified / total_class
            score -= unverified_ratio * 20  # Up to -20 points

        # Penalize for unprotected items
        total_inv = inventory_stats.get("total_inventory_items", 0)
        unprotected = inventory_stats.get("unprotected_items", 0)
        if total_inv > 0:
            unprotected_ratio = unprotected / total_inv
            score -= unprotected_ratio * 30  # Up to -30 points

        # Penalize for high risk assessments
        risk_levels = risk_stats.get("by_risk_level", {})
        critical = risk_levels.get("critical", 0)
        high = risk_levels.get("high", 0)
        score -= critical * 10  # -10 per critical
        score -= high * 5  # -5 per high

        # Reward for good protection score
        avg_protection = risk_stats.get("average_protection_score", 50)
        if avg_protection > 80:
            score = min(100, score + 10)

        return max(0, round(score, 1))

    def _identify_governance_issues(
        self,
        classification_stats: Dict,
        inventory_stats: Dict,
        risk_stats: Dict,
    ) -> List[Dict[str, Any]]:
        """Identify governance issues"""
        issues = []

        # Check for unverified classifications
        unverified = classification_stats.get("unverified_classifications", 0)
        if unverified > 0:
            issues.append({
                "severity": "medium",
                "area": "classification",
                "issue": f"{unverified} PII classifications need verification",
                "action": "Review and verify automated classifications",
            })

        # Check for unprotected PII
        unprotected = inventory_stats.get("unprotected_items", 0)
        if unprotected > 0:
            issues.append({
                "severity": "high",
                "area": "protection",
                "issue": f"{unprotected} PII items are unprotected",
                "action": "Implement encryption or masking",
            })

        # Check for high sensitivity unprotected
        by_sensitivity = inventory_stats.get("by_sensitivity", {})
        by_protection = inventory_stats.get("by_protection_status", {})
        restricted = by_sensitivity.get("restricted", 0) + by_sensitivity.get("top_secret", 0)
        if restricted > 0 and by_protection.get("unprotected", 0) > 0:
            issues.append({
                "severity": "critical",
                "area": "protection",
                "issue": "High sensitivity data may be unprotected",
                "action": "Immediately review and protect sensitive data",
            })

        # Check for critical risk levels
        risk_levels = risk_stats.get("by_risk_level", {})
        if risk_levels.get("critical", 0) > 0:
            issues.append({
                "severity": "critical",
                "area": "risk",
                "issue": f"{risk_levels['critical']} critical risk assessments",
                "action": "Address critical risk findings immediately",
            })

        return issues

    def get_executive_summary(self) -> str:
        """Generate executive summary text"""
        report = self.get_governance_report()

        summary = f"""
PII GOVERNANCE EXECUTIVE SUMMARY
Generated: {report['generated_at']}

GOVERNANCE SCORE: {report['governance_score']}/100

KEY METRICS:
- Data Sources Tracked: {report['summary']['total_data_sources']}
- PII Fields Classified: {report['summary']['total_pii_classifications']}
- Inventory Items: {report['summary']['total_inventory_items']}
- Data Flows Tracked: {report['summary']['data_flows_tracked']}

ISSUES REQUIRING ATTENTION: {len(report['issues'])}
"""

        for issue in report['issues']:
            summary += f"\n- [{issue['severity'].upper()}] {issue['issue']}"

        return summary
