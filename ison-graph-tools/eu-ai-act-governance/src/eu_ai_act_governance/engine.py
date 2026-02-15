"""
EU AI Act Governance Engine
===========================

Unified governance engine for EU AI Act compliance.
Provides high-level workflows combining multiple stores.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .schema import (
    AIRiskLevel, HighRiskCategory, ProhibitedPractice,
    GPAICategory, ConformityRoute, ConformityStatus,
    OversightLevel, OversightMeasure, IncidentSeverity, IncidentType,
    TransparencyObligation, MonitoringActivity, AIActRole
)
from .stores import (
    RiskClassificationStore,
    ProhibitedPracticesStore,
    HighRiskRequirementsStore,
    ConformityAssessmentStore,
    TechnicalDocumentationStore,
    DataGovernanceStore,
    HumanOversightStore,
    TransparencyStore,
    PostMarketMonitoringStore,
    IncidentReportingStore,
    GPAIGovernanceStore,
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class EUAIActGovernanceEngine:
    """
    Unified engine for EU AI Act compliance governance.

    Provides high-level workflows that coordinate multiple stores
    to implement complete compliance processes.
    """

    def __init__(self, graph: "ISONGraph"):
        self.graph = graph

        # Initialize all stores
        self.risk = RiskClassificationStore(graph)
        self.prohibited = ProhibitedPracticesStore(graph)
        self.high_risk = HighRiskRequirementsStore(graph)
        self.conformity = ConformityAssessmentStore(graph)
        self.documentation = TechnicalDocumentationStore(graph)
        self.data_governance = DataGovernanceStore(graph)
        self.oversight = HumanOversightStore(graph)
        self.transparency = TransparencyStore(graph)
        self.monitoring = PostMarketMonitoringStore(graph)
        self.incidents = IncidentReportingStore(graph)
        self.gpai = GPAIGovernanceStore(graph)

    # =========================================================================
    # Complete AI System Onboarding
    # =========================================================================

    def onboard_ai_system(
        self,
        name: str,
        version: str,
        provider: str,
        intended_purpose: str,
        technical_description: str,
        deployment_context: str = "",
        responsible_party: str = ""
    ) -> Dict[str, Any]:
        """
        Complete onboarding workflow for a new AI system.

        Returns system ID and initial assessment requirements.
        """
        # Register the system
        system_id = self.risk.register_ai_system(
            name=name,
            version=version,
            provider=provider,
            intended_purpose=intended_purpose,
            technical_description=technical_description,
            deployment_context=deployment_context
        )

        # Register provider as operator
        operator_id = self.risk.register_operator(
            name=provider,
            role=AIActRole.PROVIDER,
            organization_type="company"
        )

        # Create initial risk assessment
        assessment_id = self.risk.create_risk_assessment(
            system_id=system_id,
            assessor=responsible_party or provider,
            assessment_type="initial"
        )

        # Create prohibited practices screening
        screening_id = self.prohibited.create_screening(
            system_id=system_id,
            screener=responsible_party or provider,
            screening_type="pre_market"
        )

        return {
            "system_id": system_id,
            "operator_id": operator_id,
            "risk_assessment_id": assessment_id,
            "prohibited_screening_id": screening_id,
            "next_steps": [
                "Complete prohibited practices screening",
                "Evaluate high-risk categories",
                "Determine final risk classification"
            ]
        }

    # =========================================================================
    # Risk Classification Workflow
    # =========================================================================

    def classify_system_risk(
        self,
        system_id: str,
        assessor: str,
        high_risk_category: Optional[HighRiskCategory] = None,
        prohibited_practices_clear: bool = True
    ) -> Dict[str, Any]:
        """
        Complete risk classification for an AI system.
        """
        # Get or create assessment
        assessments = self.risk.get_system_assessments(system_id)
        if assessments:
            assessment_id = assessments[0]["id"]
        else:
            assessment_id = self.risk.create_risk_assessment(
                system_id=system_id,
                assessor=assessor,
                assessment_type="initial"
            )

        # Determine risk level
        if not prohibited_practices_clear:
            risk_level = AIRiskLevel.UNACCEPTABLE
            rationale = "Prohibited practice identified"
        elif high_risk_category:
            risk_level = AIRiskLevel.HIGH
            rationale = f"High-risk category: {high_risk_category.value}"

            # Evaluate the high-risk category
            self.risk.evaluate_high_risk_category(
                assessment_id=assessment_id,
                category=high_risk_category,
                applies=True,
                rationale=rationale,
                specific_use_case="",
                evaluated_by=assessor
            )
        else:
            risk_level = AIRiskLevel.LIMITED
            rationale = "No prohibited practices or high-risk categories identified"

        # Finalize classification
        result = self.risk.determine_risk_level(
            assessment_id=assessment_id,
            determined_by=assessor
        )

        # Initialize requirements based on risk level
        if risk_level == AIRiskLevel.HIGH:
            self._initialize_high_risk_requirements(system_id, assessor)

        return {
            **result,
            "classification_complete": True,
            "next_steps": self._get_next_steps_for_risk_level(risk_level)
        }

    def _initialize_high_risk_requirements(
        self,
        system_id: str,
        responsible_party: str
    ):
        """Initialize all requirements for a high-risk system."""
        # High-risk requirements
        self.high_risk.initialize_requirements(system_id, responsible_party)

        # Data governance requirements
        self.data_governance.initialize_governance_requirements(system_id, responsible_party)

        # Technical documentation
        system = self.risk.get_ai_system(system_id)
        if system:
            self.documentation.create_documentation_package(
                system_id=system_id,
                version=system.get("version", "1.0"),
                author=responsible_party
            )

    def _get_next_steps_for_risk_level(
        self,
        risk_level: AIRiskLevel
    ) -> List[str]:
        """Get next steps based on risk level."""
        if risk_level == AIRiskLevel.UNACCEPTABLE:
            return [
                "System cannot be placed on EU market",
                "Consider modifications to remove prohibited practices",
                "Re-assess after modifications"
            ]
        elif risk_level == AIRiskLevel.HIGH:
            return [
                "Complete technical documentation",
                "Implement risk management system",
                "Establish data governance",
                "Configure human oversight",
                "Complete conformity assessment",
                "Obtain CE marking",
                "Register in EU database"
            ]
        elif risk_level == AIRiskLevel.LIMITED:
            return [
                "Implement transparency requirements",
                "Ensure AI interaction disclosure",
                "Maintain documentation"
            ]
        else:
            return [
                "Consider voluntary compliance measures",
                "Maintain basic documentation"
            ]

    # =========================================================================
    # High-Risk Compliance Workflow
    # =========================================================================

    def prepare_for_market(
        self,
        system_id: str,
        provider: str,
        high_risk_category: HighRiskCategory,
        responsible_party: str
    ) -> Dict[str, Any]:
        """
        Complete market preparation workflow for high-risk AI system.
        """
        # Initialize conformity assessment
        assessment_id = self.conformity.initiate_assessment(
            system_id=system_id,
            provider=provider,
            high_risk_category=high_risk_category,
            intended_purpose=""
        )

        # Create monitoring plan
        plan_id = self.monitoring.create_monitoring_plan(
            system_id=system_id,
            provider=provider,
            risk_level=AIRiskLevel.HIGH
        )

        # Configure transparency
        self.transparency.configure_transparency(
            system_id=system_id,
            risk_level=AIRiskLevel.HIGH,
            applicable_obligations=[
                TransparencyObligation.DEPLOYER_INFORMATION,
                TransparencyObligation.INSTRUCTIONS_FOR_USE,
                TransparencyObligation.CAPABILITY_DISCLOSURE,
                TransparencyObligation.LIMITATION_DISCLOSURE
            ]
        )

        # Create instructions for use
        instructions_id = self.transparency.create_instructions(
            system_id=system_id,
            version="1.0",
            author=responsible_party
        )

        return {
            "system_id": system_id,
            "conformity_assessment_id": assessment_id,
            "monitoring_plan_id": plan_id,
            "instructions_id": instructions_id,
            "checklist": [
                "Complete technical documentation",
                "Implement risk management system",
                "Establish data governance",
                "Configure human oversight",
                "Complete conformity assessment",
                "Sign EU Declaration of Conformity",
                "Apply CE marking",
                "Register in EU database"
            ]
        }

    def complete_conformity_assessment(
        self,
        system_id: str,
        provider: str,
        signatory_name: str,
        signatory_role: str
    ) -> Dict[str, Any]:
        """
        Complete conformity assessment and prepare for market placement.
        """
        # Get assessment
        assessment = self.conformity.get_system_assessment(system_id)
        if not assessment:
            return {"error": "No conformity assessment found"}

        # Update status
        self.conformity.update_assessment_status(
            assessment["id"],
            ConformityStatus.PASSED
        )

        # Create and sign declaration
        declaration_id = self.conformity.create_declaration(
            assessment_id=assessment["id"],
            provider_name=provider,
            provider_address="",
            system_name=system_id,
            system_version="1.0"
        )

        self.conformity.sign_declaration(
            declaration_id=declaration_id,
            signatory_name=signatory_name,
            signatory_role=signatory_role
        )

        # Apply CE marking
        ce_id = self.conformity.apply_ce_marking(
            system_id=system_id,
            assessment_id=assessment["id"],
            declaration_id=declaration_id,
            applied_by=signatory_name
        )

        # Register in EU database
        registration_id = self.conformity.register_in_eu_database(
            system_id=system_id,
            provider=provider,
            system_name=system_id,
            risk_level=AIRiskLevel.HIGH,
            high_risk_category=None,
            intended_purpose="",
            member_states=["EU"]
        )

        return {
            "system_id": system_id,
            "declaration_id": declaration_id,
            "ce_marking_id": ce_id,
            "eu_registration_id": registration_id,
            "market_ready": True
        }

    # =========================================================================
    # Incident Management Workflow
    # =========================================================================

    def report_incident(
        self,
        system_id: str,
        incident_type: IncidentType,
        severity: IncidentSeverity,
        title: str,
        description: str,
        detected_by: str,
        affected_users: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Report and manage a serious incident.
        """
        # Register incident
        incident_id = self.incidents.register_incident(
            system_id=system_id,
            incident_type=incident_type,
            severity=severity,
            title=title,
            description=description,
            detected_by=detected_by,
            detection_method="manual",
            affected_users_estimate=affected_users
        )

        incident = self.incidents.get_incident(incident_id)

        # Prepare authority notification if required
        notification_id = None
        if incident and incident.get("requires_authority_notification"):
            notification_id = self.incidents.create_authority_notification(
                incident_id=incident_id,
                authority_name="National AI Authority",
                authority_type="national_authority"
            )

        return {
            "incident_id": incident_id,
            "requires_notification": incident.get("requires_authority_notification") if incident else False,
            "notification_id": notification_id,
            "reporting_deadline": incident.get("reporting_deadline") if incident else None,
            "next_steps": [
                "Start investigation",
                "Assess impact",
                "Prepare authority notification (within 72 hours)",
                "Implement corrective actions"
            ]
        }

    # =========================================================================
    # GPAI Model Governance Workflow
    # =========================================================================

    def onboard_gpai_model(
        self,
        name: str,
        version: str,
        provider: str,
        training_compute_flops: float,
        parameters_count: Optional[int] = None,
        capabilities: List[str] = None
    ) -> Dict[str, Any]:
        """
        Onboard a General-Purpose AI model.
        """
        # Determine category based on compute
        if training_compute_flops >= 1e25:
            category = GPAICategory.SYSTEMIC_RISK
        else:
            category = GPAICategory.GENERAL

        # Register model
        model_id = self.gpai.register_gpai_model(
            name=name,
            version=version,
            provider=provider,
            category=category,
            training_compute_flops=training_compute_flops,
            parameters_count=parameters_count,
            capabilities=capabilities or []
        )

        # Initialize obligations
        obligation_ids = self.gpai.initialize_provider_obligations(
            model_id=model_id,
            provider=provider
        )

        # Create documentation
        doc_id = self.gpai.create_model_documentation(
            model_id=model_id,
            author=provider
        )

        # Create risk assessment if systemic
        risk_assessment_id = None
        if category == GPAICategory.SYSTEMIC_RISK:
            risk_assessment_id = self.gpai.assess_systemic_risk(
                model_id=model_id,
                assessor=provider
            )

        return {
            "model_id": model_id,
            "category": category.value,
            "has_systemic_risk": category == GPAICategory.SYSTEMIC_RISK,
            "documentation_id": doc_id,
            "risk_assessment_id": risk_assessment_id,
            "obligations_count": len(obligation_ids),
            "next_steps": self._get_gpai_next_steps(category)
        }

    def _get_gpai_next_steps(self, category: GPAICategory) -> List[str]:
        """Get next steps for GPAI model based on category."""
        base_steps = [
            "Complete technical documentation",
            "Provide instructions for downstream providers",
            "Implement copyright compliance policy",
            "Designate EU representative"
        ]

        if category == GPAICategory.SYSTEMIC_RISK:
            base_steps.extend([
                "Complete systemic risk assessment",
                "Perform model evaluation",
                "Conduct adversarial testing",
                "Implement enhanced cybersecurity",
                "Report energy consumption"
            ])

        return base_steps

    # =========================================================================
    # Compliance Dashboard
    # =========================================================================

    def get_system_compliance_status(self, system_id: str) -> Dict[str, Any]:
        """
        Get comprehensive compliance status for an AI system.
        """
        system = self.risk.get_ai_system(system_id)
        if not system:
            return {"error": "System not found"}

        risk_level = system.get("risk_level")

        # Base status
        status = {
            "system_id": system_id,
            "system_name": system.get("name"),
            "risk_level": risk_level,
            "classification_status": system.get("classification_status"),
            "compliance_areas": {}
        }

        # Get compliance for each area
        if risk_level == AIRiskLevel.HIGH.value:
            # High-risk requirements
            status["compliance_areas"]["high_risk_requirements"] = (
                self.high_risk.get_compliance_summary(system_id)
            )

            # Conformity assessment
            status["compliance_areas"]["conformity_assessment"] = (
                self.conformity.get_assessment_summary(system_id)
            )

            # Data governance
            status["compliance_areas"]["data_governance"] = (
                self.data_governance.get_governance_status(system_id)
            )

        # Transparency (all levels)
        status["compliance_areas"]["transparency"] = (
            self.transparency.get_obligations_status(system_id)
        )

        # Post-market monitoring
        plan = self.monitoring.get_system_plan(system_id)
        if plan:
            status["compliance_areas"]["post_market_monitoring"] = {
                "plan_status": plan.get("status"),
                "active": plan.get("status") == "active"
            }

        # Incidents
        incidents = self.incidents.get_system_incidents(system_id)
        status["compliance_areas"]["incidents"] = {
            "total_incidents": len(incidents),
            "open_incidents": len([i for i in incidents if i.get("status") != "closed"])
        }

        # Calculate overall score
        status["overall_compliance"] = self._calculate_overall_compliance(status)

        return status

    def _calculate_overall_compliance(self, status: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall compliance score."""
        scores = []

        for area, data in status.get("compliance_areas", {}).items():
            if isinstance(data, dict):
                if "compliance_percentage" in data:
                    scores.append(data["compliance_percentage"])
                elif "compliance_rate" in data:
                    scores.append(data["compliance_rate"])
                elif "compliance_score" in data:
                    scores.append(data["compliance_score"])

        if not scores:
            return {"score": 0, "status": "not_assessed"}

        avg_score = round(sum(scores) / len(scores))

        if avg_score >= 90:
            compliance_status = "fully_compliant"
        elif avg_score >= 70:
            compliance_status = "substantially_compliant"
        elif avg_score >= 50:
            compliance_status = "partially_compliant"
        else:
            compliance_status = "non_compliant"

        return {
            "score": avg_score,
            "status": compliance_status,
            "areas_assessed": len(scores)
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_governance_stats(self) -> Dict[str, Any]:
        """Get comprehensive governance statistics."""
        return {
            "risk_classification": self.risk.get_stats(),
            "prohibited_practices": self.prohibited.get_stats(),
            "high_risk_requirements": self.high_risk.get_stats(),
            "conformity_assessment": self.conformity.get_stats(),
            "technical_documentation": self.documentation.get_stats(),
            "data_governance": self.data_governance.get_stats(),
            "human_oversight": self.oversight.get_stats(),
            "transparency": self.transparency.get_stats(),
            "post_market_monitoring": self.monitoring.get_stats(),
            "incident_reporting": self.incidents.get_stats(),
            "gpai_governance": self.gpai.get_stats()
        }
