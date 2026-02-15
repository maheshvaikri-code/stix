"""
PII Compliance Store
====================

Integrates PII detection with GDPR/CCPA compliance requirements.
"""

from typing import Any, Dict, List, Optional

from .base import BaseUnifiedStore
from ..schema import (
    GovernanceDomain,
    ComplianceStatus,
    CrossDomainRiskLevel,
    IntegrationEventType,
    PII_REGULATION_REQUIREMENTS,
)


class PIIComplianceStore(BaseUnifiedStore):
    """
    Store for linking PII detections to compliance requirements.

    Provides:
    - PII detection to compliance requirement mapping
    - Cross-regulation compliance checking for PII
    - Automated compliance gap identification
    - PII-triggered compliance workflows
    """

    def __init__(self, graph):
        super().__init__(graph, "pii_compliance")

    # =========================================================================
    # PII Compliance Linking
    # =========================================================================

    def link_pii_to_compliance(
        self,
        pii_inventory_item_id: str,
        pii_type: str,
        source_id: str,
        field_location: str,
        sensitivity_level: str,
        protection_status: str,
    ) -> Dict[str, Any]:
        """
        Link a PII inventory item to applicable compliance requirements.

        Returns compliance requirements from GDPR, CCPA, and other regulations.
        """
        link_id = self._generate_id("pii_comp")

        # Get applicable regulations
        requirements = PII_REGULATION_REQUIREMENTS.get(pii_type, {})

        # Determine compliance gaps based on protection status
        gaps = self._identify_compliance_gaps(
            pii_type, sensitivity_level, protection_status, requirements
        )

        # Calculate risk level
        risk_level = self._calculate_pii_compliance_risk(
            sensitivity_level, protection_status, len(gaps)
        )

        self._add_node("pii_compliance_link", link_id, {
            "pii_inventory_item_id": pii_inventory_item_id,
            "pii_type": pii_type,
            "source_id": source_id,
            "field_location": field_location,
            "sensitivity_level": sensitivity_level,
            "protection_status": protection_status,
            "applicable_regulations": list(requirements.keys()),
            "requirements": requirements,
            "compliance_gaps": gaps,
            "risk_level": risk_level,
            "status": "active",
        })

        # Create edges to regulations
        for reg in requirements.keys():
            self._add_edge(
                "pii_compliance_link", link_id,
                "REQUIRES_COMPLIANCE_WITH",
                "regulation", reg,
                {"requirements": requirements[reg]}
            )

        return {
            "link_id": link_id,
            "pii_type": pii_type,
            "applicable_regulations": list(requirements.keys()),
            "compliance_gaps": gaps,
            "risk_level": risk_level,
        }

    def _identify_compliance_gaps(
        self,
        pii_type: str,
        sensitivity_level: str,
        protection_status: str,
        requirements: Dict[str, List[str]],
    ) -> List[Dict[str, Any]]:
        """Identify compliance gaps based on PII characteristics."""
        gaps = []

        # Check encryption requirements
        if protection_status in ["unprotected", "access_controlled"]:
            for reg, reqs in requirements.items():
                if "encryption" in reqs or "encrypted" in " ".join(reqs).lower():
                    gaps.append({
                        "regulation": reg,
                        "requirement": "encryption",
                        "issue": f"PII type '{pii_type}' requires encryption but is {protection_status}",
                        "severity": "high" if sensitivity_level in ["top_secret", "restricted"] else "medium",
                    })

        # Check consent requirements for sensitive data
        if sensitivity_level in ["top_secret", "restricted"]:
            for reg, reqs in requirements.items():
                if any("consent" in r.lower() for r in reqs):
                    gaps.append({
                        "regulation": reg,
                        "requirement": "explicit_consent",
                        "issue": f"High-sensitivity PII '{pii_type}' may require explicit consent verification",
                        "severity": "medium",
                    })

        # Check GDPR-specific requirements
        if "gdpr" in requirements:
            if "dpia" in requirements.get("gdpr", []):
                gaps.append({
                    "regulation": "gdpr",
                    "requirement": "dpia",
                    "issue": f"PII type '{pii_type}' may require Data Protection Impact Assessment",
                    "severity": "medium",
                })

        return gaps

    def _calculate_pii_compliance_risk(
        self,
        sensitivity_level: str,
        protection_status: str,
        gap_count: int,
    ) -> str:
        """Calculate compliance risk level."""
        sensitivity_scores = {
            "top_secret": 5,
            "restricted": 4,
            "confidential": 3,
            "internal": 2,
            "public": 1,
        }

        protection_scores = {
            "fully_protected": 1,
            "encrypted_in_transit_and_rest": 1,
            "tokenized": 1,
            "encrypted_at_rest": 2,
            "encrypted_in_transit": 2,
            "pseudonymized": 2,
            "access_controlled": 3,
            "masked": 3,
            "unprotected": 5,
        }

        sens_score = sensitivity_scores.get(sensitivity_level, 3)
        prot_score = protection_scores.get(protection_status, 3)

        risk_score = sens_score * prot_score + (gap_count * 2)

        if risk_score >= 20:
            return CrossDomainRiskLevel.CRITICAL.value
        elif risk_score >= 15:
            return CrossDomainRiskLevel.HIGH.value
        elif risk_score >= 10:
            return CrossDomainRiskLevel.MEDIUM.value
        elif risk_score >= 5:
            return CrossDomainRiskLevel.LOW.value
        else:
            return CrossDomainRiskLevel.MINIMAL.value

    # =========================================================================
    # GDPR Integration
    # =========================================================================

    def check_gdpr_compliance(
        self,
        pii_type: str,
        processing_purpose: str,
        has_consent: bool,
        has_legal_basis: bool,
        data_minimized: bool = False,
        retention_defined: bool = False,
    ) -> Dict[str, Any]:
        """Check GDPR compliance for PII processing."""
        check_id = self._generate_id("gdpr_check")

        issues = []
        status = ComplianceStatus.COMPLIANT

        # Check lawful basis
        if not has_consent and not has_legal_basis:
            issues.append({
                "article": "Article 6",
                "issue": "No lawful basis for processing",
                "severity": "critical",
            })
            status = ComplianceStatus.NON_COMPLIANT

        # Check data minimization
        if not data_minimized:
            issues.append({
                "article": "Article 5(1)(c)",
                "issue": "Data minimization not confirmed",
                "severity": "medium",
            })
            if status == ComplianceStatus.COMPLIANT:
                status = ComplianceStatus.PARTIAL

        # Check retention
        if not retention_defined:
            issues.append({
                "article": "Article 5(1)(e)",
                "issue": "Storage limitation not defined",
                "severity": "medium",
            })
            if status == ComplianceStatus.COMPLIANT:
                status = ComplianceStatus.PARTIAL

        # Special category check
        special_categories = ["health_record", "biometric", "genetic", "race", "religion", "political"]
        if pii_type in special_categories and not has_consent:
            issues.append({
                "article": "Article 9",
                "issue": "Special category data requires explicit consent",
                "severity": "critical",
            })
            status = ComplianceStatus.NON_COMPLIANT

        self._add_node("gdpr_compliance_check", check_id, {
            "pii_type": pii_type,
            "processing_purpose": processing_purpose,
            "has_consent": has_consent,
            "has_legal_basis": has_legal_basis,
            "data_minimized": data_minimized,
            "retention_defined": retention_defined,
            "status": status.value,
            "issues": issues,
        })

        return {
            "check_id": check_id,
            "status": status.value,
            "issues": issues,
            "compliant": status == ComplianceStatus.COMPLIANT,
        }

    # =========================================================================
    # CCPA Integration
    # =========================================================================

    def check_ccpa_compliance(
        self,
        pii_type: str,
        has_notice: bool,
        opt_out_honored: bool,
        sale_disclosed: bool = True,
        sensitive_pi: bool = False,
        has_spi_consent: bool = False,
    ) -> Dict[str, Any]:
        """Check CCPA/CPRA compliance for PII processing."""
        check_id = self._generate_id("ccpa_check")

        issues = []
        status = ComplianceStatus.COMPLIANT

        # Check notice at collection
        if not has_notice:
            issues.append({
                "section": "1798.100",
                "issue": "Notice at collection not provided",
                "severity": "high",
            })
            status = ComplianceStatus.NON_COMPLIANT

        # Check opt-out
        if not opt_out_honored:
            issues.append({
                "section": "1798.120",
                "issue": "Consumer opt-out not honored",
                "severity": "critical",
            })
            status = ComplianceStatus.NON_COMPLIANT

        # Check sale disclosure
        if not sale_disclosed:
            issues.append({
                "section": "1798.115",
                "issue": "Sale of personal information not disclosed",
                "severity": "high",
            })
            if status == ComplianceStatus.COMPLIANT:
                status = ComplianceStatus.PARTIAL

        # Check sensitive PI (CPRA)
        if sensitive_pi and not has_spi_consent:
            issues.append({
                "section": "1798.121",
                "issue": "Sensitive PI processing without consent",
                "severity": "critical",
            })
            status = ComplianceStatus.NON_COMPLIANT

        self._add_node("ccpa_compliance_check", check_id, {
            "pii_type": pii_type,
            "has_notice": has_notice,
            "opt_out_honored": opt_out_honored,
            "sale_disclosed": sale_disclosed,
            "sensitive_pi": sensitive_pi,
            "has_spi_consent": has_spi_consent,
            "status": status.value,
            "issues": issues,
        })

        return {
            "check_id": check_id,
            "status": status.value,
            "issues": issues,
            "compliant": status == ComplianceStatus.COMPLIANT,
        }

    # =========================================================================
    # Cross-Regulation Compliance Check
    # =========================================================================

    def check_all_regulations(
        self,
        pii_type: str,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Check compliance across all applicable regulations.

        Args:
            pii_type: Type of PII being processed
            context: Dictionary with compliance context:
                - gdpr: GDPR-specific context
                - ccpa: CCPA-specific context
                - hipaa: HIPAA-specific context (if applicable)
        """
        results = {}
        overall_status = ComplianceStatus.COMPLIANT
        all_issues = []

        # Get applicable regulations
        applicable = PII_REGULATION_REQUIREMENTS.get(pii_type, {})

        # GDPR check
        if "gdpr" in applicable and "gdpr" in context:
            gdpr_ctx = context["gdpr"]
            gdpr_result = self.check_gdpr_compliance(
                pii_type=pii_type,
                processing_purpose=gdpr_ctx.get("processing_purpose", ""),
                has_consent=gdpr_ctx.get("has_consent", False),
                has_legal_basis=gdpr_ctx.get("has_legal_basis", False),
                data_minimized=gdpr_ctx.get("data_minimized", False),
                retention_defined=gdpr_ctx.get("retention_defined", False),
            )
            results["gdpr"] = gdpr_result
            all_issues.extend([{"regulation": "gdpr", **i} for i in gdpr_result["issues"]])
            if gdpr_result["status"] == ComplianceStatus.NON_COMPLIANT.value:
                overall_status = ComplianceStatus.NON_COMPLIANT
            elif gdpr_result["status"] == ComplianceStatus.PARTIAL.value and overall_status != ComplianceStatus.NON_COMPLIANT:
                overall_status = ComplianceStatus.PARTIAL

        # CCPA check
        if "ccpa" in applicable and "ccpa" in context:
            ccpa_ctx = context["ccpa"]
            ccpa_result = self.check_ccpa_compliance(
                pii_type=pii_type,
                has_notice=ccpa_ctx.get("has_notice", False),
                opt_out_honored=ccpa_ctx.get("opt_out_honored", True),
                sale_disclosed=ccpa_ctx.get("sale_disclosed", True),
                sensitive_pi=ccpa_ctx.get("sensitive_pi", False),
                has_spi_consent=ccpa_ctx.get("has_spi_consent", False),
            )
            results["ccpa"] = ccpa_result
            all_issues.extend([{"regulation": "ccpa", **i} for i in ccpa_result["issues"]])
            if ccpa_result["status"] == ComplianceStatus.NON_COMPLIANT.value:
                overall_status = ComplianceStatus.NON_COMPLIANT
            elif ccpa_result["status"] == ComplianceStatus.PARTIAL.value and overall_status != ComplianceStatus.NON_COMPLIANT:
                overall_status = ComplianceStatus.PARTIAL

        return {
            "pii_type": pii_type,
            "applicable_regulations": list(applicable.keys()),
            "regulation_results": results,
            "overall_status": overall_status.value,
            "total_issues": len(all_issues),
            "issues": all_issues,
            "compliant": overall_status == ComplianceStatus.COMPLIANT,
        }

    # =========================================================================
    # Compliance Events
    # =========================================================================

    def record_pii_compliance_event(
        self,
        event_type: IntegrationEventType,
        pii_type: str,
        source_id: str,
        affected_regulations: List[str],
        description: str,
        triggered_actions: Optional[List[str]] = None,
    ) -> str:
        """Record a PII-related compliance event."""
        event_id = self._generate_id("pii_event")

        self._add_node("pii_compliance_event", event_id, {
            "event_type": event_type.value if isinstance(event_type, IntegrationEventType) else event_type,
            "pii_type": pii_type,
            "source_id": source_id,
            "affected_regulations": affected_regulations,
            "description": description,
            "triggered_actions": triggered_actions or [],
            "status": "recorded",
        })

        return event_id

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get PII compliance statistics."""
        links = self._find_nodes("pii_compliance_link")
        gdpr_checks = self._find_nodes("gdpr_compliance_check")
        ccpa_checks = self._find_nodes("ccpa_compliance_check")
        events = self._find_nodes("pii_compliance_event")

        # Count by risk level
        risk_breakdown = {}
        for link in links:
            risk = link.get("risk_level", "unknown")
            risk_breakdown[risk] = risk_breakdown.get(risk, 0) + 1

        # Count compliance status
        gdpr_status = {}
        for check in gdpr_checks:
            status = check.get("status", "unknown")
            gdpr_status[status] = gdpr_status.get(status, 0) + 1

        ccpa_status = {}
        for check in ccpa_checks:
            status = check.get("status", "unknown")
            ccpa_status[status] = ccpa_status.get(status, 0) + 1

        # Count gaps
        total_gaps = sum(len(link.get("compliance_gaps", [])) for link in links)

        return {
            "total_pii_compliance_links": len(links),
            "total_gdpr_checks": len(gdpr_checks),
            "total_ccpa_checks": len(ccpa_checks),
            "total_compliance_events": len(events),
            "risk_level_breakdown": risk_breakdown,
            "gdpr_compliance_breakdown": gdpr_status,
            "ccpa_compliance_breakdown": ccpa_status,
            "total_compliance_gaps": total_gaps,
        }
