"""
Regulatory Bridge Store
=======================

Bridges PII types to regulatory requirements across GDPR, CCPA, HIPAA, etc.
"""

from typing import Any, Dict, List, Optional, Set

from .base import BaseUnifiedStore
from ..schema import (
    GovernanceDomain,
    ComplianceStatus,
    CrossDomainRiskLevel,
    RegulationJurisdiction,
    PII_REGULATION_REQUIREMENTS,
)


class RegulatoryBridgeStore(BaseUnifiedStore):
    """
    Store for mapping PII to regulatory requirements.

    Provides:
    - PII type to regulation mapping
    - Cross-regulation requirement tracking
    - Compliance gap identification
    - Regulatory obligation management
    """

    def __init__(self, graph):
        super().__init__(graph, "regulatory_bridge")

    # =========================================================================
    # Regulatory Requirement Management
    # =========================================================================

    def register_regulation(
        self,
        regulation_id: str,
        name: str,
        jurisdiction: RegulationJurisdiction,
        description: str = "",
        effective_date: str = "",
        pii_types_covered: Optional[List[str]] = None,
        key_articles: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """Register a regulation in the unified system."""
        self._add_node("regulation", regulation_id, {
            "name": name,
            "jurisdiction": jurisdiction.value if isinstance(jurisdiction, RegulationJurisdiction) else jurisdiction,
            "description": description,
            "effective_date": effective_date,
            "pii_types_covered": pii_types_covered or [],
            "key_articles": key_articles or [],
            "status": "active",
        })
        return regulation_id

    def add_regulatory_requirement(
        self,
        requirement_id: str,
        regulation_id: str,
        name: str,
        description: str,
        article_reference: str = "",
        applies_to_pii_types: Optional[List[str]] = None,
        control_objectives: Optional[List[str]] = None,
        enforcement_level: str = "mandatory",
    ) -> str:
        """Add a specific requirement from a regulation."""
        req_id = requirement_id or self._generate_id("req")

        self._add_node("regulatory_requirement", req_id, {
            "regulation_id": regulation_id,
            "name": name,
            "description": description,
            "article_reference": article_reference,
            "applies_to_pii_types": applies_to_pii_types or [],
            "control_objectives": control_objectives or [],
            "enforcement_level": enforcement_level,
        })

        # Link to regulation
        self._add_edge(
            "regulatory_requirement", req_id,
            "REQUIREMENT_OF",
            "regulation", regulation_id,
            {}
        )

        return req_id

    def map_pii_to_regulation(
        self,
        pii_type: str,
        regulation_id: str,
        requirements: List[str],
        sensitivity_override: Optional[str] = None,
        notes: str = "",
    ) -> str:
        """Map a PII type to a regulation with specific requirements."""
        mapping_id = self._generate_id("pii_reg")

        self._add_node("pii_regulation_mapping", mapping_id, {
            "pii_type": pii_type,
            "regulation_id": regulation_id,
            "requirements": requirements,
            "sensitivity_override": sensitivity_override,
            "notes": notes,
        })

        # Create edges
        self._add_edge(
            "pii_regulation_mapping", mapping_id,
            "MAPS_PII",
            "pii_type", pii_type,
            {}
        )
        self._add_edge(
            "pii_regulation_mapping", mapping_id,
            "TO_REGULATION",
            "regulation", regulation_id,
            {}
        )

        return mapping_id

    # =========================================================================
    # Cross-Regulation Analysis
    # =========================================================================

    def get_regulations_for_pii(self, pii_type: str) -> Dict[str, Any]:
        """Get all regulations applicable to a PII type."""
        # Check built-in mappings first
        built_in = PII_REGULATION_REQUIREMENTS.get(pii_type, {})

        # Get custom mappings from graph
        custom_mappings = self._find_nodes("pii_regulation_mapping", pii_type=pii_type)

        regulations = {}

        # Add built-in
        for reg, reqs in built_in.items():
            regulations[reg] = {
                "source": "built_in",
                "requirements": reqs,
            }

        # Add custom
        for mapping in custom_mappings:
            reg_id = mapping.get("regulation_id")
            if reg_id:
                regulations[reg_id] = {
                    "source": "custom",
                    "requirements": mapping.get("requirements", []),
                    "mapping_id": mapping.get("id"),
                }

        return {
            "pii_type": pii_type,
            "applicable_regulations": regulations,
            "total_regulations": len(regulations),
        }

    def get_pii_for_regulation(self, regulation_id: str) -> Dict[str, Any]:
        """Get all PII types covered by a regulation."""
        # Get regulation
        regulation = self._get_node("regulation", regulation_id)

        # Built-in PII types for this regulation
        built_in_pii = []
        for pii_type, regs in PII_REGULATION_REQUIREMENTS.items():
            if regulation_id.lower() in [r.lower() for r in regs.keys()]:
                built_in_pii.append(pii_type)

        # Custom mappings
        custom_mappings = self._find_nodes("pii_regulation_mapping", regulation_id=regulation_id)
        custom_pii = [m.get("pii_type") for m in custom_mappings]

        all_pii = list(set(built_in_pii + custom_pii))

        return {
            "regulation_id": regulation_id,
            "regulation_name": regulation.get("name") if regulation else None,
            "pii_types": all_pii,
            "total_pii_types": len(all_pii),
        }

    def get_cross_regulation_requirements(
        self,
        pii_types: List[str],
    ) -> Dict[str, Any]:
        """Get all requirements across regulations for given PII types."""
        all_regulations = set()
        all_requirements = {}
        pii_coverage = {}

        for pii_type in pii_types:
            result = self.get_regulations_for_pii(pii_type)
            pii_coverage[pii_type] = []

            for reg_id, reg_info in result["applicable_regulations"].items():
                all_regulations.add(reg_id)
                pii_coverage[pii_type].append(reg_id)

                if reg_id not in all_requirements:
                    all_requirements[reg_id] = set()
                all_requirements[reg_id].update(reg_info.get("requirements", []))

        # Convert sets to lists
        for reg_id in all_requirements:
            all_requirements[reg_id] = list(all_requirements[reg_id])

        return {
            "pii_types_analyzed": pii_types,
            "applicable_regulations": list(all_regulations),
            "requirements_by_regulation": all_requirements,
            "pii_regulation_coverage": pii_coverage,
        }

    # =========================================================================
    # Compliance Status Tracking
    # =========================================================================

    def record_compliance_status(
        self,
        entity_id: str,
        entity_type: str,
        regulation_id: str,
        status: ComplianceStatus,
        assessed_by: str,
        evidence: Optional[List[str]] = None,
        gaps: Optional[List[str]] = None,
        remediation_plan: Optional[str] = None,
        next_review_date: str = "",
    ) -> str:
        """Record compliance status for an entity against a regulation."""
        status_id = self._generate_id("compliance")

        self._add_node("compliance_status", status_id, {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "regulation_id": regulation_id,
            "status": status.value if isinstance(status, ComplianceStatus) else status,
            "assessed_by": assessed_by,
            "evidence": evidence or [],
            "gaps": gaps or [],
            "remediation_plan": remediation_plan,
            "next_review_date": next_review_date,
        })

        # Link to entity and regulation
        self._add_edge(
            "compliance_status", status_id,
            "COMPLIANCE_FOR",
            entity_type, entity_id,
            {}
        )
        self._add_edge(
            "compliance_status", status_id,
            "AGAINST_REGULATION",
            "regulation", regulation_id,
            {}
        )

        return status_id

    def get_entity_compliance(
        self,
        entity_id: str,
        entity_type: str,
    ) -> Dict[str, Any]:
        """Get compliance status for an entity across all regulations."""
        statuses = self._find_nodes("compliance_status", entity_id=entity_id, entity_type=entity_type)

        compliance_map = {}
        gaps = []

        for status in statuses:
            reg_id = status.get("regulation_id")
            compliance_map[reg_id] = {
                "status": status.get("status"),
                "assessed_at": status.get("_created_at"),
                "assessed_by": status.get("assessed_by"),
                "gaps": status.get("gaps", []),
            }
            gaps.extend(status.get("gaps", []))

        # Determine overall status
        statuses_list = [c["status"] for c in compliance_map.values()]
        if not statuses_list:
            overall = ComplianceStatus.PENDING_REVIEW.value
        elif ComplianceStatus.NON_COMPLIANT.value in statuses_list:
            overall = ComplianceStatus.NON_COMPLIANT.value
        elif ComplianceStatus.PARTIAL.value in statuses_list:
            overall = ComplianceStatus.PARTIAL.value
        else:
            overall = ComplianceStatus.COMPLIANT.value

        return {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "regulations_assessed": list(compliance_map.keys()),
            "compliance_by_regulation": compliance_map,
            "overall_status": overall,
            "total_gaps": len(gaps),
            "gaps": gaps,
        }

    # =========================================================================
    # Obligation Management
    # =========================================================================

    def create_obligation(
        self,
        obligation_id: str,
        name: str,
        regulation_id: str,
        obligation_type: str,
        description: str,
        deadline: str = "",
        responsible_party: str = "",
        pii_types_affected: Optional[List[str]] = None,
        actions_required: Optional[List[str]] = None,
    ) -> str:
        """Create a regulatory obligation."""
        obl_id = obligation_id or self._generate_id("obl")

        self._add_node("regulatory_obligation", obl_id, {
            "name": name,
            "regulation_id": regulation_id,
            "obligation_type": obligation_type,
            "description": description,
            "deadline": deadline,
            "responsible_party": responsible_party,
            "pii_types_affected": pii_types_affected or [],
            "actions_required": actions_required or [],
            "status": "active",
        })

        self._add_edge(
            "regulatory_obligation", obl_id,
            "OBLIGATION_FROM",
            "regulation", regulation_id,
            {}
        )

        return obl_id

    def get_obligations_for_pii(self, pii_type: str) -> List[Dict[str, Any]]:
        """Get all obligations related to a specific PII type."""
        obligations = []

        for node in self.graph.nodes():
            if node.type == "regulatory_obligation":
                affected = node.properties.get("pii_types_affected", [])
                if pii_type in affected:
                    obligations.append({
                        "id": node.id,
                        **node.properties,
                    })

        return obligations

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get regulatory bridge statistics."""
        regulations = self._find_nodes("regulation")
        requirements = self._find_nodes("regulatory_requirement")
        mappings = self._find_nodes("pii_regulation_mapping")
        statuses = self._find_nodes("compliance_status")
        obligations = self._find_nodes("regulatory_obligation")

        # Compliance breakdown
        compliance_breakdown = {}
        for status in statuses:
            s = status.get("status", "unknown")
            compliance_breakdown[s] = compliance_breakdown.get(s, 0) + 1

        return {
            "total_regulations": len(regulations),
            "total_requirements": len(requirements),
            "total_pii_mappings": len(mappings),
            "total_compliance_records": len(statuses),
            "total_obligations": len(obligations),
            "compliance_breakdown": compliance_breakdown,
            "regulations_by_jurisdiction": self._count_by_field(regulations, "jurisdiction"),
        }

    def _count_by_field(
        self,
        items: List[Dict[str, Any]],
        field: str,
    ) -> Dict[str, int]:
        """Count items by field value."""
        counts = {}
        for item in items:
            value = item.get(field, "unknown")
            counts[value] = counts.get(value, 0) + 1
        return counts
