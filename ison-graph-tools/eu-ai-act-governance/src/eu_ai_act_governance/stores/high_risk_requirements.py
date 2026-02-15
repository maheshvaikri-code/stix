"""
High-Risk Requirements Store
============================

Manages compliance requirements for high-risk AI systems per Articles 8-15.
Tracks risk management, data quality, accuracy, robustness, and cybersecurity.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import (
    QMSElement, QMSStatus, DataGovernanceRequirement,
    BiasType, AIRiskLevel
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


# Article references for high-risk requirements
HIGH_RISK_ARTICLES = {
    "risk_management": {
        "article": "Art. 9",
        "title": "Risk Management System",
        "requirements": [
            "Establish and maintain risk management system",
            "Identify and analyze known and foreseeable risks",
            "Estimate and evaluate risks from intended use and misuse",
            "Evaluate risks from post-market monitoring data",
            "Adopt suitable risk management measures",
            "Test to identify appropriate risk management measures"
        ]
    },
    "data_governance": {
        "article": "Art. 10",
        "title": "Data and Data Governance",
        "requirements": [
            "Training, validation, and testing datasets subject to governance",
            "Appropriate data management practices",
            "Relevant, representative, free of errors, complete datasets",
            "Appropriate statistical properties",
            "Consider characteristics of persons/groups",
            "Bias examination and correction"
        ]
    },
    "technical_documentation": {
        "article": "Art. 11",
        "title": "Technical Documentation",
        "requirements": [
            "Draw up technical documentation before market placement",
            "Keep documentation up to date",
            "Demonstrate conformity with requirements",
            "Provide authorities information to assess conformity"
        ]
    },
    "record_keeping": {
        "article": "Art. 12",
        "title": "Record-keeping (Logs)",
        "requirements": [
            "Automatic recording of events (logs)",
            "Traceability of functioning throughout lifecycle",
            "Enable monitoring of operation",
            "Facilitate post-market monitoring"
        ]
    },
    "transparency": {
        "article": "Art. 13",
        "title": "Transparency and Information",
        "requirements": [
            "Transparent operation for deployers",
            "Instructions for use accompanying the system",
            "Concise, correct, clear, relevant information",
            "Include capabilities and limitations"
        ]
    },
    "human_oversight": {
        "article": "Art. 14",
        "title": "Human Oversight",
        "requirements": [
            "Design for effective human oversight",
            "Enable understanding of system capacities",
            "Enable awareness of automation bias",
            "Enable correct interpretation of output",
            "Enable decision to override, not use, or disregard"
        ]
    },
    "accuracy_robustness": {
        "article": "Art. 15",
        "title": "Accuracy, Robustness, Cybersecurity",
        "requirements": [
            "Achieve appropriate levels of accuracy",
            "Robustness against errors, faults, inconsistencies",
            "Resilient against manipulation by third parties",
            "Cybersecurity measures appropriate to risks"
        ]
    }
}


class HighRiskRequirementsStore(BaseStore):
    """Store for high-risk AI system requirements management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "high_risk_requirements")

    # =========================================================================
    # Requirement Tracking
    # =========================================================================

    def initialize_requirements(
        self,
        system_id: str,
        responsible_party: str
    ) -> List[str]:
        """Initialize all high-risk requirements for a system"""
        requirement_ids = []

        for req_type, details in HIGH_RISK_ARTICLES.items():
            rid = self._generate_id("hr")
            props = {
                "system_id": system_id,
                "requirement_type": req_type,
                "article": details["article"],
                "title": details["title"],
                "sub_requirements": details["requirements"],
                "status": "not_started",
                "responsible_party": responsible_party,
                "compliance_score": 0,
                "initialized_at": self._now(),
                "description": f"High-risk requirement: {details['title']}"
            }
            self._add_node("high_risk_requirement", rid, props)

            self._add_edge(
                "ai_system", system_id,
                "HAS_REQUIREMENT",
                "high_risk_requirement", rid,
                {"article": details["article"]}
            )

            requirement_ids.append(rid)

        return requirement_ids

    def get_system_requirements(
        self,
        system_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all high-risk requirements for a system"""
        reqs = self._find_nodes("high_risk_requirement", system_id=system_id)
        if status:
            reqs = [r for r in reqs if r.get("status") == status]
        return reqs

    def get_requirement(self, requirement_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific requirement"""
        return self._get_node("high_risk_requirement", requirement_id)

    def update_requirement_status(
        self,
        requirement_id: str,
        status: str,  # not_started, in_progress, implemented, verified, non_compliant
        compliance_score: int,  # 0-100
        notes: str = ""
    ):
        """Update requirement compliance status"""
        self._update_node("high_risk_requirement", requirement_id, {
            "status": status,
            "compliance_score": compliance_score,
            "notes": notes,
            "last_updated": self._now()
        })

    # =========================================================================
    # Risk Management System (Art. 9)
    # =========================================================================

    def create_risk_management_system(
        self,
        system_id: str,
        owner: str,
        methodology: str,
        rms_id: Optional[str] = None
    ) -> str:
        """Create a risk management system for an AI system"""
        rid = rms_id or self._generate_id("rms")
        props = {
            "system_id": system_id,
            "owner": owner,
            "methodology": methodology,
            "status": "active",
            "created_at": self._now(),
            "last_review": None,
            "next_review": None,
            "identified_risks": [],
            "residual_risks": [],
            "description": f"Risk management system for {system_id}"
        }
        return self._add_node("risk_management_system", rid, props)

    def identify_risk(
        self,
        rms_id: str,
        risk_category: str,  # technical, operational, ethical, legal, safety
        risk_description: str,
        likelihood: str,  # low, medium, high
        impact: str,  # low, medium, high, critical
        affected_parties: List[str],
        risk_id: Optional[str] = None
    ) -> str:
        """Identify and document a risk"""
        rid = risk_id or self._generate_id("risk")
        risk_score = self._calculate_risk_score(likelihood, impact)

        props = {
            "rms_id": rms_id,
            "risk_category": risk_category,
            "description": risk_description,
            "likelihood": likelihood,
            "impact": impact,
            "risk_score": risk_score,
            "affected_parties": affected_parties,
            "status": "identified",
            "identified_at": self._now(),
            "node_description": f"Identified risk: {risk_category}"
        }
        self._add_node("identified_risk", rid, props)

        self._add_edge(
            "risk_management_system", rms_id,
            "CONTAINS_RISK",
            "identified_risk", rid,
            {"risk_score": risk_score}
        )

        return rid

    def _calculate_risk_score(self, likelihood: str, impact: str) -> int:
        """Calculate risk score from likelihood and impact"""
        likelihood_scores = {"low": 1, "medium": 2, "high": 3}
        impact_scores = {"low": 1, "medium": 2, "high": 3, "critical": 4}

        l_score = likelihood_scores.get(likelihood, 1)
        i_score = impact_scores.get(impact, 1)

        return l_score * i_score

    def add_risk_mitigation(
        self,
        risk_id: str,
        mitigation_type: str,  # eliminate, reduce, transfer, accept
        measures: List[str],
        responsible: str,
        target_date: Optional[str] = None
    ) -> str:
        """Add mitigation measures for a risk"""
        mid = self._generate_id("mit")
        props = {
            "risk_id": risk_id,
            "mitigation_type": mitigation_type,
            "measures": measures,
            "responsible": responsible,
            "target_date": target_date,
            "status": "planned",
            "created_at": self._now(),
            "description": f"Risk mitigation: {mitigation_type}"
        }
        self._add_node("risk_mitigation", mid, props)

        self._add_edge(
            "identified_risk", risk_id,
            "HAS_MITIGATION",
            "risk_mitigation", mid,
            {}
        )

        return mid

    def complete_mitigation(
        self,
        mitigation_id: str,
        residual_likelihood: str,
        residual_impact: str,
        verification: str,
        completed_by: str
    ):
        """Mark mitigation as completed and record residual risk"""
        residual_score = self._calculate_risk_score(residual_likelihood, residual_impact)

        self._update_node("risk_mitigation", mitigation_id, {
            "status": "completed",
            "residual_likelihood": residual_likelihood,
            "residual_impact": residual_impact,
            "residual_score": residual_score,
            "verification": verification,
            "completed_by": completed_by,
            "completed_at": self._now()
        })

    def get_system_risks(
        self,
        system_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all risks for a system"""
        # First get the RMS
        rms_list = self._find_nodes("risk_management_system", system_id=system_id)
        if not rms_list:
            return []

        risks = []
        for rms in rms_list:
            rms_risks = self._find_nodes("identified_risk", rms_id=rms["id"])
            if status:
                rms_risks = [r for r in rms_risks if r.get("status") == status]
            risks.extend(rms_risks)

        return risks

    # =========================================================================
    # Quality Management System (QMS)
    # =========================================================================

    def create_qms(
        self,
        system_id: str,
        provider: str,
        scope: str,
        qms_id: Optional[str] = None
    ) -> str:
        """Create a Quality Management System"""
        qid = qms_id or self._generate_id("qms")
        props = {
            "system_id": system_id,
            "provider": provider,
            "scope": scope,
            "status": QMSStatus.DRAFT.value,
            "elements": [],
            "created_at": self._now(),
            "description": f"QMS for {system_id}"
        }
        return self._add_node("qms", qid, props)

    def add_qms_element(
        self,
        qms_id: str,
        element: QMSElement,
        documentation_ref: str,
        responsible: str,
        status: QMSStatus = QMSStatus.DRAFT
    ) -> str:
        """Add a QMS element"""
        eid = self._generate_id("qe")
        props = {
            "qms_id": qms_id,
            "element": element.value,
            "documentation_ref": documentation_ref,
            "responsible": responsible,
            "status": status.value,
            "created_at": self._now(),
            "description": f"QMS element: {element.value}"
        }
        self._add_node("qms_element", eid, props)

        self._add_edge(
            "qms", qms_id,
            "HAS_ELEMENT",
            "qms_element", eid,
            {}
        )

        return eid

    def update_qms_element_status(
        self,
        element_id: str,
        status: QMSStatus,
        evidence: str = ""
    ):
        """Update QMS element status"""
        self._update_node("qms_element", element_id, {
            "status": status.value,
            "evidence": evidence,
            "updated_at": self._now()
        })

    def get_qms_status(self, qms_id: str) -> Dict[str, Any]:
        """Get overall QMS compliance status"""
        elements = self._find_nodes("qms_element", qms_id=qms_id)

        total = len(elements)
        if total == 0:
            return {"qms_id": qms_id, "status": "not_started", "compliance": 0}

        implemented = len([
            e for e in elements
            if e.get("status") in [QMSStatus.IMPLEMENTED.value, QMSStatus.CERTIFIED.value]
        ])

        compliance = round((implemented / total) * 100)

        return {
            "qms_id": qms_id,
            "total_elements": total,
            "implemented_elements": implemented,
            "compliance_percentage": compliance,
            "status": "compliant" if compliance == 100 else "in_progress"
        }

    # =========================================================================
    # Accuracy & Performance Testing (Art. 15)
    # =========================================================================

    def create_performance_test(
        self,
        system_id: str,
        test_type: str,  # accuracy, robustness, bias, security
        methodology: str,
        tester: str,
        test_id: Optional[str] = None
    ) -> str:
        """Create a performance test record"""
        tid = test_id or self._generate_id("pt")
        props = {
            "system_id": system_id,
            "test_type": test_type,
            "methodology": methodology,
            "tester": tester,
            "status": "planned",
            "created_at": self._now(),
            "description": f"Performance test: {test_type}"
        }
        return self._add_node("performance_test", tid, props)

    def record_test_results(
        self,
        test_id: str,
        metrics: Dict[str, Any],
        passed: bool,
        findings: List[str],
        recommendations: List[str]
    ):
        """Record test results"""
        self._update_node("performance_test", test_id, {
            "status": "completed",
            "metrics": metrics,
            "passed": passed,
            "findings": findings,
            "recommendations": recommendations,
            "completed_at": self._now()
        })

    def get_performance_tests(
        self,
        system_id: str,
        test_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get performance tests for a system"""
        tests = self._find_nodes("performance_test", system_id=system_id)
        if test_type:
            tests = [t for t in tests if t.get("test_type") == test_type]
        return tests

    # =========================================================================
    # Bias Testing (Art. 10, 15)
    # =========================================================================

    def create_bias_assessment(
        self,
        system_id: str,
        assessor: str,
        protected_attributes: List[str],
        assessment_id: Optional[str] = None
    ) -> str:
        """Create a bias assessment"""
        aid = assessment_id or self._generate_id("ba")
        props = {
            "system_id": system_id,
            "assessor": assessor,
            "protected_attributes": protected_attributes,
            "status": "in_progress",
            "bias_types_checked": [],
            "biases_found": [],
            "created_at": self._now(),
            "description": f"Bias assessment for {system_id}"
        }
        return self._add_node("bias_assessment", aid, props)

    def check_bias_type(
        self,
        assessment_id: str,
        bias_type: BiasType,
        metric_used: str,
        threshold: float,
        result: float,
        passed: bool,
        affected_groups: List[str],
        notes: str = ""
    ) -> str:
        """Check for a specific type of bias"""
        cid = self._generate_id("bc")
        props = {
            "assessment_id": assessment_id,
            "bias_type": bias_type.value,
            "metric_used": metric_used,
            "threshold": threshold,
            "result": result,
            "passed": passed,
            "affected_groups": affected_groups,
            "notes": notes,
            "checked_at": self._now(),
            "description": f"Bias check: {bias_type.value}"
        }
        self._add_node("bias_check", cid, props)

        # Update assessment
        assessment = self._get_node("bias_assessment", assessment_id)
        if assessment:
            checked = assessment.get("bias_types_checked", [])
            checked.append(bias_type.value)
            updates = {"bias_types_checked": checked}

            if not passed:
                found = assessment.get("biases_found", [])
                found.append({
                    "type": bias_type.value,
                    "affected_groups": affected_groups,
                    "severity": result - threshold if result > threshold else threshold - result
                })
                updates["biases_found"] = found

            self._update_node("bias_assessment", assessment_id, updates)

        return cid

    def complete_bias_assessment(
        self,
        assessment_id: str,
        overall_result: str,  # passed, failed, conditional
        remediation_required: bool,
        summary: str
    ) -> Dict[str, Any]:
        """Complete the bias assessment"""
        assessment = self._get_node("bias_assessment", assessment_id)
        if not assessment:
            return {"error": "Assessment not found"}

        self._update_node("bias_assessment", assessment_id, {
            "status": "completed",
            "overall_result": overall_result,
            "remediation_required": remediation_required,
            "summary": summary,
            "completed_at": self._now()
        })

        return {
            "assessment_id": assessment_id,
            "result": overall_result,
            "biases_found": assessment.get("biases_found", []),
            "remediation_required": remediation_required
        }

    # =========================================================================
    # Cybersecurity Requirements (Art. 15)
    # =========================================================================

    def create_security_assessment(
        self,
        system_id: str,
        assessor: str,
        scope: str,
        assessment_id: Optional[str] = None
    ) -> str:
        """Create a cybersecurity assessment"""
        aid = assessment_id or self._generate_id("sa")
        props = {
            "system_id": system_id,
            "assessor": assessor,
            "scope": scope,
            "status": "in_progress",
            "vulnerabilities_found": [],
            "controls_assessed": [],
            "created_at": self._now(),
            "description": f"Security assessment for {system_id}"
        }
        return self._add_node("security_assessment", aid, props)

    def add_vulnerability(
        self,
        assessment_id: str,
        vulnerability_type: str,
        severity: str,  # low, medium, high, critical
        description: str,
        attack_vector: str,
        remediation: str
    ) -> str:
        """Add a discovered vulnerability"""
        vid = self._generate_id("vuln")
        props = {
            "assessment_id": assessment_id,
            "vulnerability_type": vulnerability_type,
            "severity": severity,
            "description": description,
            "attack_vector": attack_vector,
            "remediation": remediation,
            "status": "open",
            "found_at": self._now(),
            "node_description": f"Vulnerability: {vulnerability_type}"
        }
        self._add_node("vulnerability", vid, props)

        return vid

    def remediate_vulnerability(
        self,
        vulnerability_id: str,
        remediation_applied: str,
        verified_by: str,
        verification_method: str
    ):
        """Mark vulnerability as remediated"""
        self._update_node("vulnerability", vulnerability_id, {
            "status": "remediated",
            "remediation_applied": remediation_applied,
            "verified_by": verified_by,
            "verification_method": verification_method,
            "remediated_at": self._now()
        })

    def assess_security_control(
        self,
        assessment_id: str,
        control_name: str,
        control_category: str,  # access_control, encryption, integrity, availability
        implemented: bool,
        effectiveness: str,  # effective, partially_effective, ineffective
        evidence: str
    ) -> str:
        """Assess a security control"""
        cid = self._generate_id("sc")
        props = {
            "assessment_id": assessment_id,
            "control_name": control_name,
            "control_category": control_category,
            "implemented": implemented,
            "effectiveness": effectiveness,
            "evidence": evidence,
            "assessed_at": self._now(),
            "description": f"Security control: {control_name}"
        }
        self._add_node("security_control", cid, props)

        return cid

    def complete_security_assessment(
        self,
        assessment_id: str,
        overall_rating: str,  # secure, conditionally_secure, insecure
        critical_findings: int,
        high_findings: int,
        recommendations: List[str]
    ) -> Dict[str, Any]:
        """Complete security assessment"""
        self._update_node("security_assessment", assessment_id, {
            "status": "completed",
            "overall_rating": overall_rating,
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "recommendations": recommendations,
            "completed_at": self._now()
        })

        return {
            "assessment_id": assessment_id,
            "rating": overall_rating,
            "critical_findings": critical_findings,
            "high_findings": high_findings,
            "compliant": overall_rating in ["secure", "conditionally_secure"]
        }

    # =========================================================================
    # Compliance Summary
    # =========================================================================

    def get_compliance_summary(self, system_id: str) -> Dict[str, Any]:
        """Get overall high-risk compliance summary"""
        requirements = self.get_system_requirements(system_id)

        if not requirements:
            return {
                "system_id": system_id,
                "status": "not_initialized",
                "compliance_score": 0
            }

        total_score = 0
        by_article = {}

        for req in requirements:
            score = req.get("compliance_score", 0)
            total_score += score
            by_article[req.get("article")] = {
                "title": req.get("title"),
                "status": req.get("status"),
                "score": score
            }

        avg_score = round(total_score / len(requirements)) if requirements else 0

        # Determine overall status
        if avg_score >= 100:
            status = "fully_compliant"
        elif avg_score >= 80:
            status = "substantially_compliant"
        elif avg_score >= 50:
            status = "partially_compliant"
        else:
            status = "non_compliant"

        return {
            "system_id": system_id,
            "overall_status": status,
            "compliance_score": avg_score,
            "by_article": by_article,
            "requirements_count": len(requirements),
            "fully_compliant_count": len([r for r in requirements if r.get("compliance_score") == 100])
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get high-risk requirements statistics"""
        base_stats = super().get_stats()
        requirements = self._find_nodes("high_risk_requirement")
        rms = self._find_nodes("risk_management_system")
        risks = self._find_nodes("identified_risk")
        qms = self._find_nodes("qms")
        tests = self._find_nodes("performance_test")
        bias_assessments = self._find_nodes("bias_assessment")
        security_assessments = self._find_nodes("security_assessment")

        return {
            **base_stats,
            "total_requirements": len(requirements),
            "compliant_requirements": len([r for r in requirements if r.get("compliance_score", 0) >= 80]),
            "risk_management_systems": len(rms),
            "identified_risks": len(risks),
            "mitigated_risks": len([r for r in risks if r.get("status") == "mitigated"]),
            "qms_count": len(qms),
            "performance_tests": len(tests),
            "passed_tests": len([t for t in tests if t.get("passed")]),
            "bias_assessments": len(bias_assessments),
            "security_assessments": len(security_assessments)
        }
