"""
Compliance Framework Store
==========================

Maps regulatory requirements to controls and tracks compliance gaps.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import ComplianceFramework, ComplianceRequirement, ComplianceControl, ComplianceGap

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class ComplianceStore(BaseStore):
    """Store for compliance framework governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "compliance")

    # =========================================================================
    # Framework Management
    # =========================================================================

    def add_framework(
        self,
        name: str,
        jurisdiction: str,
        effective_date: str,
        applies_to: str,
        description: str = "",
        framework_id: Optional[str] = None
    ) -> str:
        """Add a compliance framework (GDPR, HIPAA, SOX, EU AI Act, etc.)"""
        fid = framework_id or self._generate_id("f")
        props = {
            "name": name,
            "jurisdiction": jurisdiction,
            "effective_date": effective_date,
            "applies_to": applies_to,
            "description": description,
            "active": True
        }
        return self._add_node("framework", fid, props)

    def get_framework(self, framework_id: str) -> Optional[Dict[str, Any]]:
        """Get framework by ID"""
        return self._get_node("framework", framework_id)

    def list_frameworks(self, jurisdiction: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all frameworks"""
        frameworks = self._find_nodes("framework")
        if jurisdiction:
            frameworks = [f for f in frameworks if f.get("jurisdiction") == jurisdiction]
        return frameworks

    # =========================================================================
    # Requirement Management
    # =========================================================================

    def add_requirement(
        self,
        framework_id: str,
        article: str,
        description: str,
        risk_if_violated: str,
        mandatory: bool = True,
        requirement_id: Optional[str] = None
    ) -> str:
        """Add a compliance requirement"""
        rid = requirement_id or self._generate_id("rq")
        props = {
            "framework_id": framework_id,
            "article": article,
            "description": description,
            "risk_if_violated": risk_if_violated,
            "mandatory": mandatory
        }
        self._add_node("requirement", rid, props)

        # Link to framework
        self._add_edge(
            "framework", framework_id,
            "REQUIREMENT_FROM",
            "requirement", rid,
            {}
        )

        return rid

    def get_requirement(self, requirement_id: str) -> Optional[Dict[str, Any]]:
        """Get requirement by ID"""
        return self._get_node("requirement", requirement_id)

    def list_requirements(self, framework_id: str) -> List[Dict[str, Any]]:
        """List requirements for a framework"""
        return self._find_nodes("requirement", framework_id=framework_id)

    # =========================================================================
    # Control Management
    # =========================================================================

    def add_control(
        self,
        name: str,
        control_type: str,
        automated: bool,
        description: str = "",
        evidence_location: str = "",
        control_id: Optional[str] = None
    ) -> str:
        """Add a compliance control"""
        cid = control_id or self._generate_id("ct")
        props = {
            "name": name,
            "type": control_type,
            "automated": automated,
            "description": description,
            "evidence_location": evidence_location,
            "active": True
        }
        return self._add_node("control", cid, props)

    def get_control(self, control_id: str) -> Optional[Dict[str, Any]]:
        """Get control by ID"""
        return self._get_node("control", control_id)

    def list_controls(self, control_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all controls"""
        controls = self._find_nodes("control")
        if control_type:
            controls = [c for c in controls if c.get("type") == control_type]
        return controls

    # =========================================================================
    # Requirement-Control Mapping
    # =========================================================================

    def map_control_to_requirement(
        self,
        requirement_id: str,
        control_id: str,
        coverage: float,
        gap: Optional[str] = None,
        evidence: str = ""
    ):
        """Map a control to a requirement"""
        self._add_edge(
            "control", control_id,
            "SATISFIED_BY",
            "requirement", requirement_id,
            {"coverage": coverage, "gap": gap, "evidence": evidence}
        )

    def get_requirement_coverage(self, requirement_id: str) -> Dict[str, Any]:
        """Get coverage details for a requirement"""
        edges = self._find_edges(
            rel_type="SATISFIED_BY",
            target_type="requirement", target_id=requirement_id
        )

        controls = []
        total_coverage = 0.0
        gaps = []

        for edge in edges:
            control = self._get_node("control", edge["source"][1])
            coverage = edge["properties"].get("coverage", 0)
            gap = edge["properties"].get("gap")

            controls.append({
                "control_id": edge["source"][1],
                "control_name": control.get("name") if control else "",
                "coverage": coverage
            })

            total_coverage = max(total_coverage, coverage)
            if gap:
                gaps.append(gap)

        return {
            "requirement_id": requirement_id,
            "controls": controls,
            "total_coverage": total_coverage,
            "gaps": gaps,
            "compliant": total_coverage >= 0.9
        }

    # =========================================================================
    # Behavior-Compliance Mapping
    # =========================================================================

    def add_behavior(
        self,
        agent_id: str,
        behavior: str,
        data_touched: List[str],
        behavior_id: Optional[str] = None
    ) -> str:
        """Add an agent behavior that needs compliance mapping"""
        bid = behavior_id or self._generate_id("ab")
        props = {
            "agent_id": agent_id,
            "behavior": behavior,
            "data_touched": data_touched
        }
        return self._add_node("agent_behavior", bid, props)

    def require_compliance(
        self,
        behavior_id: str,
        requirement_ids: List[str],
        reason: str
    ):
        """Mark a behavior as requiring compliance with certain requirements"""
        for req_id in requirement_ids:
            self._add_edge(
                "agent_behavior", behavior_id,
                "REQUIRES_COMPLIANCE",
                "requirement", req_id,
                {"reason": reason}
            )

    # =========================================================================
    # Gap Analysis
    # =========================================================================

    def add_gap(
        self,
        requirement_id: str,
        behavior_id: str,
        gap_description: str,
        remediation: str,
        priority: str,
        due_date: Optional[str] = None,
        gap_id: Optional[str] = None
    ) -> str:
        """Add a compliance gap"""
        gid = gap_id or self._generate_id("cg")
        props = {
            "requirement_id": requirement_id,
            "behavior_id": behavior_id,
            "gap_description": gap_description,
            "remediation": remediation,
            "priority": priority,
            "due_date": due_date,
            "status": "open"
        }
        self._add_node("compliance_gap", gid, props)

        self._add_edge(
            "agent_behavior", behavior_id,
            "COMPLIANCE_GAP",
            "requirement", requirement_id,
            {"gap_id": gid}
        )

        return gid

    def get_gaps(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get all compliance gaps"""
        gaps = self._find_nodes("compliance_gap")
        if status:
            gaps = [g for g in gaps if g.get("status") == status]
        return gaps

    def close_gap(self, gap_id: str, resolution: str):
        """Close a compliance gap"""
        self._update_node("compliance_gap", gap_id, {
            "status": "closed",
            "resolution": resolution,
            "closed_at": self._now()
        })

    # =========================================================================
    # Compliance Assessment
    # =========================================================================

    def assess_behavior_compliance(self, behavior_id: str) -> Dict[str, Any]:
        """Assess compliance status for a behavior"""
        behavior = self._get_node("agent_behavior", behavior_id)
        if not behavior:
            return {"error": "Behavior not found"}

        # Find required compliance
        required_edges = self._find_edges(
            source_type="agent_behavior", source_id=behavior_id,
            rel_type="REQUIRES_COMPLIANCE"
        )

        requirements = []
        gaps = []
        overall_compliant = True

        for edge in required_edges:
            req_id = edge["target"][1]
            req = self.get_requirement(req_id)
            coverage = self.get_requirement_coverage(req_id)

            req_info = {
                "requirement_id": req_id,
                "framework": req.get("framework_id") if req else "",
                "article": req.get("article") if req else "",
                "coverage": coverage["total_coverage"],
                "compliant": coverage["compliant"]
            }
            requirements.append(req_info)

            if not coverage["compliant"]:
                overall_compliant = False
                gaps.extend(coverage["gaps"])

        return {
            "behavior_id": behavior_id,
            "behavior": behavior.get("behavior"),
            "requirements": requirements,
            "gaps": gaps,
            "compliant": overall_compliant,
            "assessed_at": self._now()
        }

    def get_framework_compliance_summary(self, framework_id: str) -> Dict[str, Any]:
        """Get compliance summary for a framework"""
        requirements = self.list_requirements(framework_id)

        total = len(requirements)
        compliant = 0
        gaps = []

        for req in requirements:
            coverage = self.get_requirement_coverage(req["id"])
            if coverage["compliant"]:
                compliant += 1
            else:
                gaps.append({
                    "requirement": req["article"],
                    "coverage": coverage["total_coverage"],
                    "gaps": coverage["gaps"]
                })

        return {
            "framework_id": framework_id,
            "total_requirements": total,
            "compliant": compliant,
            "non_compliant": total - compliant,
            "compliance_rate": compliant / total if total > 0 else 1.0,
            "gaps": gaps
        }

    # =========================================================================
    # Audit Evidence
    # =========================================================================

    def add_evidence(
        self,
        control_id: str,
        requirement_id: str,
        evidence_type: str,
        location: str,
        retention: str
    ):
        """Add audit evidence linking control to requirement"""
        self._add_edge(
            "control", control_id,
            "AUDIT_EVIDENCE",
            "requirement", requirement_id,
            {
                "evidence_type": evidence_type,
                "location": location,
                "retention": retention,
                "collected_at": self._now()
            }
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get compliance store statistics"""
        base_stats = super().get_stats()
        frameworks = self._find_nodes("framework")
        requirements = self._find_nodes("requirement")
        controls = self._find_nodes("control")
        gaps = self._find_nodes("compliance_gap")

        return {
            **base_stats,
            "frameworks": len(frameworks),
            "requirements": len(requirements),
            "controls": len(controls),
            "gaps": len(gaps),
            "open_gaps": len([g for g in gaps if g.get("status") == "open"])
        }
