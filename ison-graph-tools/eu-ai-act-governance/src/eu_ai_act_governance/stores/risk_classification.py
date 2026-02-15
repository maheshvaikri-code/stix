"""
Risk Classification Store
=========================

Manages AI system risk classification per EU AI Act Articles 5-7.
Handles risk assessment, categorization, and ongoing risk evaluation.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import (
    AIRiskLevel, HighRiskCategory, ProhibitedPractice,
    AIActRole, ProviderObligation, DeployerObligation
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class RiskClassificationStore(BaseStore):
    """Store for AI system risk classification and management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "risk_classification")

    # =========================================================================
    # AI System Registration
    # =========================================================================

    def register_ai_system(
        self,
        name: str,
        version: str,
        provider: str,
        intended_purpose: str,
        technical_description: str,
        system_id: Optional[str] = None,
        deployment_context: str = "",
        target_users: str = "",
        geographic_scope: str = "EU"
    ) -> str:
        """Register a new AI system for risk assessment"""
        sid = system_id or self._generate_id("ais")
        props = {
            "name": name,
            "version": version,
            "provider": provider,
            "intended_purpose": intended_purpose,
            "technical_description": technical_description,
            "deployment_context": deployment_context,
            "target_users": target_users,
            "geographic_scope": geographic_scope,
            "risk_level": None,  # To be determined
            "classification_status": "pending",
            "registered_at": self._now(),
            "description": f"AI System: {name} v{version}"
        }
        return self._add_node("ai_system", sid, props)

    def get_ai_system(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get AI system by ID"""
        return self._get_node("ai_system", system_id)

    def list_ai_systems(
        self,
        risk_level: Optional[AIRiskLevel] = None,
        provider: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List AI systems with optional filters"""
        systems = self._find_nodes("ai_system")

        if risk_level:
            systems = [s for s in systems if s.get("risk_level") == risk_level.value]
        if provider:
            systems = [s for s in systems if s.get("provider") == provider]
        if status:
            systems = [s for s in systems if s.get("classification_status") == status]

        return systems

    def update_ai_system(
        self,
        system_id: str,
        **updates
    ):
        """Update AI system details"""
        self._update_node("ai_system", system_id, updates)

    # =========================================================================
    # Risk Assessment
    # =========================================================================

    def create_risk_assessment(
        self,
        system_id: str,
        assessor: str,
        assessment_type: str = "initial",  # initial, periodic, change_triggered
        assessment_id: Optional[str] = None
    ) -> str:
        """Create a new risk assessment for an AI system"""
        aid = assessment_id or self._generate_id("ra")
        props = {
            "system_id": system_id,
            "assessor": assessor,
            "assessment_type": assessment_type,
            "status": "in_progress",
            "started_at": self._now(),
            "prohibited_practice_checks": [],
            "high_risk_indicators": [],
            "risk_factors": [],
            "preliminary_risk_level": None,
            "final_risk_level": None,
            "description": f"Risk assessment for {system_id}"
        }
        self._add_node("risk_assessment", aid, props)

        # Link to AI system
        self._add_edge(
            "ai_system", system_id,
            "HAS_ASSESSMENT",
            "risk_assessment", aid,
            {"assessment_type": assessment_type}
        )

        return aid

    def get_risk_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get risk assessment by ID"""
        return self._get_node("risk_assessment", assessment_id)

    def get_system_assessments(
        self,
        system_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all assessments for a system"""
        assessments = self._find_nodes("risk_assessment", system_id=system_id)
        if status:
            assessments = [a for a in assessments if a.get("status") == status]
        return assessments

    # =========================================================================
    # Prohibited Practice Checks (Art. 5)
    # =========================================================================

    def check_prohibited_practice(
        self,
        assessment_id: str,
        practice: ProhibitedPractice,
        applies: bool,
        evidence: str,
        checked_by: str
    ) -> str:
        """Record a prohibited practice check"""
        pid = self._generate_id("ppc")
        props = {
            "assessment_id": assessment_id,
            "practice": practice.value,
            "practice_name": practice.name,
            "applies": applies,
            "evidence": evidence,
            "checked_by": checked_by,
            "checked_at": self._now(),
            "description": f"Prohibited practice check: {practice.name}"
        }
        self._add_node("prohibited_check", pid, props)

        # Link to assessment
        self._add_edge(
            "risk_assessment", assessment_id,
            "HAS_PROHIBITED_CHECK",
            "prohibited_check", pid,
            {}
        )

        # If prohibited practice applies, flag the assessment
        if applies:
            assessment = self.get_risk_assessment(assessment_id)
            if assessment:
                checks = assessment.get("prohibited_practice_checks", [])
                checks.append(practice.value)
                self._update_node("risk_assessment", assessment_id, {
                    "prohibited_practice_checks": checks,
                    "preliminary_risk_level": AIRiskLevel.UNACCEPTABLE.value
                })

        return pid

    def get_prohibited_checks(self, assessment_id: str) -> List[Dict[str, Any]]:
        """Get all prohibited practice checks for an assessment"""
        return self._find_nodes("prohibited_check", assessment_id=assessment_id)

    # =========================================================================
    # High-Risk Category Evaluation (Art. 6, Annex III)
    # =========================================================================

    def evaluate_high_risk_category(
        self,
        assessment_id: str,
        category: HighRiskCategory,
        applies: bool,
        rationale: str,
        specific_use_case: str,
        evaluated_by: str
    ) -> str:
        """Evaluate if an AI system falls under a high-risk category"""
        eid = self._generate_id("hrc")
        props = {
            "assessment_id": assessment_id,
            "category": category.value,
            "category_name": category.name,
            "applies": applies,
            "rationale": rationale,
            "specific_use_case": specific_use_case,
            "evaluated_by": evaluated_by,
            "evaluated_at": self._now(),
            "description": f"High-risk category evaluation: {category.name}"
        }
        self._add_node("high_risk_evaluation", eid, props)

        # Link to assessment
        self._add_edge(
            "risk_assessment", assessment_id,
            "HAS_HIGH_RISK_EVAL",
            "high_risk_evaluation", eid,
            {}
        )

        # Update assessment if high-risk applies
        if applies:
            assessment = self.get_risk_assessment(assessment_id)
            if assessment:
                indicators = assessment.get("high_risk_indicators", [])
                indicators.append(category.value)
                self._update_node("risk_assessment", assessment_id, {
                    "high_risk_indicators": indicators
                })

        return eid

    def get_high_risk_evaluations(self, assessment_id: str) -> List[Dict[str, Any]]:
        """Get all high-risk category evaluations for an assessment"""
        return self._find_nodes("high_risk_evaluation", assessment_id=assessment_id)

    # =========================================================================
    # Risk Factor Analysis
    # =========================================================================

    def add_risk_factor(
        self,
        assessment_id: str,
        factor_type: str,  # technical, operational, contextual, data, user
        factor_name: str,
        severity: str,  # low, medium, high, critical
        description: str,
        mitigation_possible: bool,
        mitigation_approach: Optional[str] = None
    ) -> str:
        """Add a risk factor to the assessment"""
        fid = self._generate_id("rf")
        props = {
            "assessment_id": assessment_id,
            "factor_type": factor_type,
            "factor_name": factor_name,
            "severity": severity,
            "description": description,
            "mitigation_possible": mitigation_possible,
            "mitigation_approach": mitigation_approach,
            "status": "identified",
            "added_at": self._now()
        }
        self._add_node("risk_factor", fid, props)

        # Link to assessment
        self._add_edge(
            "risk_assessment", assessment_id,
            "HAS_RISK_FACTOR",
            "risk_factor", fid,
            {"severity": severity}
        )

        return fid

    def get_risk_factors(
        self,
        assessment_id: str,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get risk factors for an assessment"""
        factors = self._find_nodes("risk_factor", assessment_id=assessment_id)
        if severity:
            factors = [f for f in factors if f.get("severity") == severity]
        return factors

    def mitigate_risk_factor(
        self,
        factor_id: str,
        mitigation_implemented: str,
        residual_severity: str,
        mitigated_by: str
    ):
        """Record mitigation of a risk factor"""
        self._update_node("risk_factor", factor_id, {
            "status": "mitigated",
            "mitigation_implemented": mitigation_implemented,
            "residual_severity": residual_severity,
            "mitigated_by": mitigated_by,
            "mitigated_at": self._now()
        })

    # =========================================================================
    # Risk Level Determination
    # =========================================================================

    def determine_risk_level(
        self,
        assessment_id: str,
        determined_by: str,
        notes: str = ""
    ) -> Dict[str, Any]:
        """Determine the final risk level based on assessment"""
        assessment = self.get_risk_assessment(assessment_id)
        if not assessment:
            return {"error": "Assessment not found"}

        # Check for prohibited practices first
        prohibited_checks = assessment.get("prohibited_practice_checks", [])
        if prohibited_checks:
            risk_level = AIRiskLevel.UNACCEPTABLE
            rationale = f"Prohibited practice(s) detected: {', '.join(prohibited_checks)}"
        else:
            # Check for high-risk indicators
            high_risk = assessment.get("high_risk_indicators", [])
            if high_risk:
                risk_level = AIRiskLevel.HIGH
                rationale = f"High-risk category(s): {', '.join(high_risk)}"
            else:
                # Check risk factors for limited risk
                factors = self.get_risk_factors(assessment_id)
                critical_factors = [f for f in factors if f.get("severity") == "critical"]
                high_factors = [f for f in factors if f.get("severity") == "high"]

                if critical_factors:
                    risk_level = AIRiskLevel.HIGH
                    rationale = "Critical risk factors present"
                elif high_factors:
                    risk_level = AIRiskLevel.LIMITED
                    rationale = "High severity risk factors present"
                else:
                    risk_level = AIRiskLevel.MINIMAL
                    rationale = "No significant risk indicators"

        # Update assessment
        self._update_node("risk_assessment", assessment_id, {
            "final_risk_level": risk_level.value,
            "risk_rationale": rationale,
            "determined_by": determined_by,
            "determined_at": self._now(),
            "status": "completed",
            "notes": notes
        })

        # Update the AI system
        system_id = assessment.get("system_id")
        if system_id:
            self._update_node("ai_system", system_id, {
                "risk_level": risk_level.value,
                "classification_status": "classified",
                "last_assessment_id": assessment_id,
                "last_assessed_at": self._now()
            })

        return {
            "assessment_id": assessment_id,
            "system_id": system_id,
            "risk_level": risk_level.value,
            "rationale": rationale,
            "prohibited_practices": prohibited_checks,
            "high_risk_categories": assessment.get("high_risk_indicators", []),
            "requires_conformity_assessment": risk_level == AIRiskLevel.HIGH,
            "market_prohibited": risk_level == AIRiskLevel.UNACCEPTABLE
        }

    # =========================================================================
    # Operator Registration
    # =========================================================================

    def register_operator(
        self,
        name: str,
        role: AIActRole,
        organization_type: str,  # company, public_body, sme, startup
        eu_representative: Optional[str] = None,
        contact_info: str = "",
        operator_id: Optional[str] = None
    ) -> str:
        """Register an operator (provider, deployer, etc.)"""
        oid = operator_id or self._generate_id("op")
        props = {
            "name": name,
            "role": role.value,
            "organization_type": organization_type,
            "eu_representative": eu_representative,
            "contact_info": contact_info,
            "registered_at": self._now(),
            "description": f"Operator: {name} ({role.value})"
        }
        return self._add_node("operator", oid, props)

    def get_operator(self, operator_id: str) -> Optional[Dict[str, Any]]:
        """Get operator by ID"""
        return self._get_node("operator", operator_id)

    def assign_operator_to_system(
        self,
        operator_id: str,
        system_id: str,
        role: AIActRole
    ):
        """Assign an operator to an AI system"""
        self._add_edge(
            "operator", operator_id,
            f"IS_{role.value.upper()}",
            "ai_system", system_id,
            {"assigned_at": self._now()}
        )

    # =========================================================================
    # Obligation Tracking
    # =========================================================================

    def add_provider_obligation(
        self,
        system_id: str,
        obligation: ProviderObligation,
        article_reference: str,
        due_date: Optional[str] = None
    ) -> str:
        """Track a provider obligation for a high-risk system"""
        oid = self._generate_id("po")
        props = {
            "system_id": system_id,
            "obligation": obligation.value,
            "article_reference": article_reference,
            "due_date": due_date,
            "status": "pending",
            "description": f"Provider obligation: {obligation.value}"
        }
        self._add_node("provider_obligation", oid, props)

        self._add_edge(
            "ai_system", system_id,
            "HAS_OBLIGATION",
            "provider_obligation", oid,
            {}
        )

        return oid

    def add_deployer_obligation(
        self,
        system_id: str,
        obligation: DeployerObligation,
        article_reference: str,
        deployer_id: str,
        due_date: Optional[str] = None
    ) -> str:
        """Track a deployer obligation"""
        oid = self._generate_id("do")
        props = {
            "system_id": system_id,
            "deployer_id": deployer_id,
            "obligation": obligation.value,
            "article_reference": article_reference,
            "due_date": due_date,
            "status": "pending",
            "description": f"Deployer obligation: {obligation.value}"
        }
        self._add_node("deployer_obligation", oid, props)

        self._add_edge(
            "ai_system", system_id,
            "HAS_DEPLOYER_OBLIGATION",
            "deployer_obligation", oid,
            {}
        )

        return oid

    def fulfill_obligation(
        self,
        obligation_id: str,
        obligation_type: str,  # provider, deployer
        evidence: str,
        fulfilled_by: str
    ):
        """Mark an obligation as fulfilled"""
        node_type = f"{obligation_type}_obligation"
        self._update_node(node_type, obligation_id, {
            "status": "fulfilled",
            "evidence": evidence,
            "fulfilled_by": fulfilled_by,
            "fulfilled_at": self._now()
        })

    def get_system_obligations(
        self,
        system_id: str,
        status: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Get all obligations for a system"""
        provider_obs = self._find_nodes("provider_obligation", system_id=system_id)
        deployer_obs = self._find_nodes("deployer_obligation", system_id=system_id)

        if status:
            provider_obs = [o for o in provider_obs if o.get("status") == status]
            deployer_obs = [o for o in deployer_obs if o.get("status") == status]

        return {
            "provider_obligations": provider_obs,
            "deployer_obligations": deployer_obs
        }

    # =========================================================================
    # Classification Exception (Art. 6(3))
    # =========================================================================

    def request_exception(
        self,
        system_id: str,
        exception_type: str,  # non_safety_component, non_profiling, non_decision_making
        justification: str,
        requested_by: str
    ) -> str:
        """Request an exception from high-risk classification"""
        eid = self._generate_id("ex")
        props = {
            "system_id": system_id,
            "exception_type": exception_type,
            "justification": justification,
            "requested_by": requested_by,
            "requested_at": self._now(),
            "status": "pending",
            "description": f"Exception request: {exception_type}"
        }
        return self._add_node("classification_exception", eid, props)

    def review_exception(
        self,
        exception_id: str,
        approved: bool,
        reviewer: str,
        review_notes: str
    ):
        """Review an exception request"""
        self._update_node("classification_exception", exception_id, {
            "status": "approved" if approved else "rejected",
            "reviewed_by": reviewer,
            "reviewed_at": self._now(),
            "review_notes": review_notes
        })

        # If approved, update the system risk level
        if approved:
            exception = self._get_node("classification_exception", exception_id)
            if exception:
                system_id = exception.get("system_id")
                if system_id:
                    self._update_node("ai_system", system_id, {
                        "risk_level": AIRiskLevel.LIMITED.value,
                        "exception_applied": exception_id
                    })

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get risk classification statistics"""
        base_stats = super().get_stats()
        systems = self._find_nodes("ai_system")
        assessments = self._find_nodes("risk_assessment")
        operators = self._find_nodes("operator")

        # Count by risk level
        by_risk = {}
        for level in AIRiskLevel:
            count = len([s for s in systems if s.get("risk_level") == level.value])
            by_risk[level.value] = count

        return {
            **base_stats,
            "total_systems": len(systems),
            "systems_by_risk_level": by_risk,
            "pending_classification": len([s for s in systems if s.get("classification_status") == "pending"]),
            "classified_systems": len([s for s in systems if s.get("classification_status") == "classified"]),
            "total_assessments": len(assessments),
            "completed_assessments": len([a for a in assessments if a.get("status") == "completed"]),
            "operators": len(operators),
            "providers": len([o for o in operators if o.get("role") == AIActRole.PROVIDER.value]),
            "deployers": len([o for o in operators if o.get("role") == AIActRole.DEPLOYER.value])
        }
