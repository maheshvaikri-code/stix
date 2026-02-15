"""
GPAI Governance Store
=====================

Manages General-Purpose AI (GPAI) model governance per Articles 51-56.
Handles model registration, systemic risk assessment, and GPAI provider obligations.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import (
    GPAICategory, GPAIRequirement, SystemicRiskIndicator,
    DocumentationType
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


# FLOP threshold for systemic risk (10^25 as per Art. 51)
SYSTEMIC_RISK_FLOP_THRESHOLD = 1e25


class GPAIGovernanceStore(BaseStore):
    """Store for GPAI model governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "gpai_governance")

    # =========================================================================
    # Model Registration
    # =========================================================================

    def register_gpai_model(
        self,
        name: str,
        version: str,
        provider: str,
        category: GPAICategory,
        training_compute_flops: float,
        parameters_count: Optional[int] = None,
        training_data_size: Optional[str] = None,
        capabilities: List[str] = None,
        intended_uses: List[str] = None,
        model_id: Optional[str] = None
    ) -> str:
        """Register a GPAI model"""
        mid = model_id or self._generate_id("gpai")

        # Determine if model has systemic risk
        has_systemic_risk = training_compute_flops >= SYSTEMIC_RISK_FLOP_THRESHOLD
        if category == GPAICategory.SYSTEMIC_RISK:
            has_systemic_risk = True

        props = {
            "name": name,
            "version": version,
            "provider": provider,
            "category": category.value,
            "training_compute_flops": training_compute_flops,
            "parameters_count": parameters_count,
            "training_data_size": training_data_size,
            "capabilities": capabilities or [],
            "intended_uses": intended_uses or [],
            "has_systemic_risk": has_systemic_risk,
            "systemic_risk_indicators": [],
            "status": "registered",
            "registered_at": self._now(),
            "description": f"GPAI Model: {name} v{version}"
        }
        return self._add_node("gpai_model", mid, props)

    def get_gpai_model(self, model_id: str) -> Optional[Dict[str, Any]]:
        """Get GPAI model by ID"""
        return self._get_node("gpai_model", model_id)

    def list_gpai_models(
        self,
        provider: Optional[str] = None,
        category: Optional[GPAICategory] = None,
        has_systemic_risk: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """List GPAI models"""
        models = self._find_nodes("gpai_model")
        if provider:
            models = [m for m in models if m.get("provider") == provider]
        if category:
            models = [m for m in models if m.get("category") == category.value]
        if has_systemic_risk is not None:
            models = [m for m in models if m.get("has_systemic_risk") == has_systemic_risk]
        return models

    def update_model(
        self,
        model_id: str,
        **updates
    ):
        """Update GPAI model details"""
        updates["updated_at"] = self._now()
        self._update_node("gpai_model", model_id, updates)

    # =========================================================================
    # Systemic Risk Assessment
    # =========================================================================

    def assess_systemic_risk(
        self,
        model_id: str,
        assessor: str,
        assessment_id: Optional[str] = None
    ) -> str:
        """Create a systemic risk assessment"""
        aid = assessment_id or self._generate_id("sra")
        props = {
            "model_id": model_id,
            "assessor": assessor,
            "status": "in_progress",
            "indicators_checked": [],
            "risk_indicators_present": [],
            "started_at": self._now(),
            "description": f"Systemic risk assessment for {model_id}"
        }
        return self._add_node("systemic_risk_assessment", aid, props)

    def check_risk_indicator(
        self,
        assessment_id: str,
        indicator: SystemicRiskIndicator,
        present: bool,
        evidence: str,
        impact_if_present: str,
        checked_by: str
    ) -> str:
        """Check for a systemic risk indicator"""
        cid = self._generate_id("sri")
        props = {
            "assessment_id": assessment_id,
            "indicator": indicator.value,
            "present": present,
            "evidence": evidence,
            "impact_if_present": impact_if_present,
            "checked_by": checked_by,
            "checked_at": self._now(),
            "description": f"Risk indicator check: {indicator.value}"
        }
        self._add_node("risk_indicator_check", cid, props)

        # Update assessment
        assessment = self._get_node("systemic_risk_assessment", assessment_id)
        if assessment:
            checked = assessment.get("indicators_checked", [])
            checked.append(indicator.value)
            updates = {"indicators_checked": checked}

            if present:
                present_list = assessment.get("risk_indicators_present", [])
                present_list.append(indicator.value)
                updates["risk_indicators_present"] = present_list

            self._update_node("systemic_risk_assessment", assessment_id, updates)

        return cid

    def complete_risk_assessment(
        self,
        assessment_id: str,
        has_systemic_risk: bool,
        risk_level: str,  # none, low, medium, high
        summary: str,
        mitigation_required: bool,
        completed_by: str
    ) -> Dict[str, Any]:
        """Complete systemic risk assessment"""
        assessment = self._get_node("systemic_risk_assessment", assessment_id)
        if not assessment:
            return {"error": "Assessment not found"}

        self._update_node("systemic_risk_assessment", assessment_id, {
            "status": "completed",
            "has_systemic_risk": has_systemic_risk,
            "risk_level": risk_level,
            "summary": summary,
            "mitigation_required": mitigation_required,
            "completed_by": completed_by,
            "completed_at": self._now()
        })

        # Update model
        model_id = assessment.get("model_id")
        if model_id and has_systemic_risk:
            self._update_node("gpai_model", model_id, {
                "has_systemic_risk": True,
                "systemic_risk_indicators": assessment.get("risk_indicators_present", []),
                "category": GPAICategory.SYSTEMIC_RISK.value
            })

        return {
            "assessment_id": assessment_id,
            "model_id": model_id,
            "has_systemic_risk": has_systemic_risk,
            "risk_level": risk_level,
            "indicators_found": assessment.get("risk_indicators_present", [])
        }

    # =========================================================================
    # GPAI Provider Obligations (Art. 53)
    # =========================================================================

    def initialize_provider_obligations(
        self,
        model_id: str,
        provider: str
    ) -> List[str]:
        """Initialize provider obligations for a GPAI model"""
        model = self.get_gpai_model(model_id)
        if not model:
            return []

        # Base obligations for all GPAI
        obligations = [
            GPAIRequirement.TECHNICAL_DOCUMENTATION,
            GPAIRequirement.INSTRUCTIONS_FOR_USE,
            GPAIRequirement.COPYRIGHT_COMPLIANCE,
            GPAIRequirement.EU_REPRESENTATIVE,
        ]

        # Additional obligations for systemic risk models
        if model.get("has_systemic_risk"):
            obligations.extend([
                GPAIRequirement.MODEL_EVALUATION,
                GPAIRequirement.ADVERSARIAL_TESTING,
                GPAIRequirement.RISK_ASSESSMENT,
                GPAIRequirement.INCIDENT_REPORTING,
                GPAIRequirement.CYBERSECURITY_MEASURES,
                GPAIRequirement.ENERGY_REPORTING,
            ])

        obligation_ids = []
        for req in obligations:
            oid = self._generate_id("gpo")
            props = {
                "model_id": model_id,
                "provider": provider,
                "requirement": req.value,
                "status": "pending",
                "mandatory": True,
                "created_at": self._now(),
                "description": f"GPAI obligation: {req.value}"
            }
            self._add_node("gpai_obligation", oid, props)
            obligation_ids.append(oid)

        return obligation_ids

    def fulfill_obligation(
        self,
        obligation_id: str,
        evidence: str,
        fulfilled_by: str,
        documentation_ref: Optional[str] = None
    ):
        """Mark an obligation as fulfilled"""
        self._update_node("gpai_obligation", obligation_id, {
            "status": "fulfilled",
            "evidence": evidence,
            "fulfilled_by": fulfilled_by,
            "documentation_ref": documentation_ref,
            "fulfilled_at": self._now()
        })

    def get_provider_obligations(
        self,
        model_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get provider obligations for a model"""
        obligations = self._find_nodes("gpai_obligation", model_id=model_id)
        if status:
            obligations = [o for o in obligations if o.get("status") == status]
        return obligations

    def get_obligations_summary(self, model_id: str) -> Dict[str, Any]:
        """Get obligations summary for a model"""
        obligations = self.get_provider_obligations(model_id)
        total = len(obligations)
        fulfilled = len([o for o in obligations if o.get("status") == "fulfilled"])

        return {
            "model_id": model_id,
            "total_obligations": total,
            "fulfilled": fulfilled,
            "pending": total - fulfilled,
            "compliance_rate": round((fulfilled / total) * 100) if total > 0 else 0
        }

    # =========================================================================
    # Technical Documentation (Art. 53(1)(a))
    # =========================================================================

    def create_model_documentation(
        self,
        model_id: str,
        author: str,
        doc_id: Optional[str] = None
    ) -> str:
        """Create technical documentation for a GPAI model"""
        did = doc_id or self._generate_id("gmd")

        # Required sections for GPAI models per Annex XI
        sections = [
            {"name": "model_description", "status": "pending"},
            {"name": "training_methodology", "status": "pending"},
            {"name": "training_data", "status": "pending"},
            {"name": "computational_resources", "status": "pending"},
            {"name": "model_capabilities", "status": "pending"},
            {"name": "model_limitations", "status": "pending"},
            {"name": "evaluation_results", "status": "pending"},
            {"name": "risk_assessment", "status": "pending"},
        ]

        props = {
            "model_id": model_id,
            "author": author,
            "sections": sections,
            "status": "draft",
            "completeness": 0,
            "created_at": self._now(),
            "description": f"GPAI documentation for {model_id}"
        }
        return self._add_node("gpai_documentation", did, props)

    def update_documentation_section(
        self,
        doc_id: str,
        section_name: str,
        content: str,
        updated_by: str
    ):
        """Update a documentation section"""
        doc = self._get_node("gpai_documentation", doc_id)
        if not doc:
            return

        sections = doc.get("sections", [])
        for section in sections:
            if section["name"] == section_name:
                section["status"] = "completed"
                section["content"] = content
                section["updated_at"] = self._now()
                break

        completed = len([s for s in sections if s["status"] == "completed"])
        completeness = round((completed / len(sections)) * 100) if sections else 0

        self._update_node("gpai_documentation", doc_id, {
            "sections": sections,
            "completeness": completeness,
            "last_updated": self._now()
        })

    def finalize_documentation(
        self,
        doc_id: str,
        finalized_by: str
    ) -> Dict[str, Any]:
        """Finalize GPAI documentation"""
        doc = self._get_node("gpai_documentation", doc_id)
        if not doc:
            return {"error": "Documentation not found"}

        incomplete = [s for s in doc.get("sections", []) if s["status"] != "completed"]
        if incomplete:
            return {
                "success": False,
                "reason": "incomplete_sections",
                "incomplete": [s["name"] for s in incomplete]
            }

        self._update_node("gpai_documentation", doc_id, {
            "status": "finalized",
            "finalized_by": finalized_by,
            "finalized_at": self._now()
        })

        return {"success": True, "doc_id": doc_id}

    # =========================================================================
    # Model Evaluation (Art. 55(1)(a))
    # =========================================================================

    def create_model_evaluation(
        self,
        model_id: str,
        evaluator: str,
        evaluation_type: str,  # capability, safety, bias, adversarial
        evaluation_id: Optional[str] = None
    ) -> str:
        """Create a model evaluation"""
        eid = evaluation_id or self._generate_id("gme")
        props = {
            "model_id": model_id,
            "evaluator": evaluator,
            "evaluation_type": evaluation_type,
            "status": "planned",
            "benchmarks": [],
            "results": [],
            "created_at": self._now(),
            "description": f"GPAI evaluation: {evaluation_type}"
        }
        return self._add_node("gpai_evaluation", eid, props)

    def add_benchmark_result(
        self,
        evaluation_id: str,
        benchmark_name: str,
        score: float,
        max_score: float,
        notes: str = ""
    ):
        """Add a benchmark result"""
        evaluation = self._get_node("gpai_evaluation", evaluation_id)
        if evaluation:
            results = evaluation.get("results", [])
            results.append({
                "benchmark": benchmark_name,
                "score": score,
                "max_score": max_score,
                "percentage": round((score / max_score) * 100) if max_score > 0 else 0,
                "notes": notes,
                "recorded_at": self._now()
            })

            benchmarks = evaluation.get("benchmarks", [])
            if benchmark_name not in benchmarks:
                benchmarks.append(benchmark_name)

            self._update_node("gpai_evaluation", evaluation_id, {
                "status": "in_progress",
                "results": results,
                "benchmarks": benchmarks
            })

    def complete_evaluation(
        self,
        evaluation_id: str,
        summary: str,
        recommendations: List[str],
        passed: bool,
        completed_by: str
    ) -> Dict[str, Any]:
        """Complete model evaluation"""
        self._update_node("gpai_evaluation", evaluation_id, {
            "status": "completed",
            "summary": summary,
            "recommendations": recommendations,
            "passed": passed,
            "completed_by": completed_by,
            "completed_at": self._now()
        })

        evaluation = self._get_node("gpai_evaluation", evaluation_id)
        return {
            "evaluation_id": evaluation_id,
            "evaluation_type": evaluation.get("evaluation_type") if evaluation else None,
            "passed": passed,
            "summary": summary
        }

    def get_model_evaluations(
        self,
        model_id: str,
        evaluation_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get evaluations for a model"""
        evaluations = self._find_nodes("gpai_evaluation", model_id=model_id)
        if evaluation_type:
            evaluations = [e for e in evaluations if e.get("evaluation_type") == evaluation_type]
        return evaluations

    # =========================================================================
    # Adversarial Testing (Art. 55(1)(a))
    # =========================================================================

    def create_adversarial_test(
        self,
        model_id: str,
        test_type: str,  # jailbreak, prompt_injection, data_extraction, harmful_output
        tester: str,
        test_id: Optional[str] = None
    ) -> str:
        """Create an adversarial test"""
        tid = test_id or self._generate_id("gat")
        props = {
            "model_id": model_id,
            "test_type": test_type,
            "tester": tester,
            "status": "planned",
            "test_cases": [],
            "vulnerabilities_found": [],
            "created_at": self._now(),
            "description": f"Adversarial test: {test_type}"
        }
        return self._add_node("adversarial_test", tid, props)

    def add_test_case(
        self,
        test_id: str,
        test_case_name: str,
        input_data: str,
        expected_behavior: str,
        actual_behavior: str,
        passed: bool,
        severity_if_failed: Optional[str] = None
    ):
        """Add an adversarial test case"""
        test = self._get_node("adversarial_test", test_id)
        if test:
            cases = test.get("test_cases", [])
            cases.append({
                "name": test_case_name,
                "input": input_data,
                "expected": expected_behavior,
                "actual": actual_behavior,
                "passed": passed,
                "severity": severity_if_failed,
                "tested_at": self._now()
            })

            vulnerabilities = test.get("vulnerabilities_found", [])
            if not passed and severity_if_failed:
                vulnerabilities.append({
                    "test_case": test_case_name,
                    "severity": severity_if_failed,
                    "description": f"Unexpected behavior: {actual_behavior}"
                })

            self._update_node("adversarial_test", test_id, {
                "status": "in_progress",
                "test_cases": cases,
                "vulnerabilities_found": vulnerabilities
            })

    def complete_adversarial_test(
        self,
        test_id: str,
        summary: str,
        mitigations_required: List[str],
        completed_by: str
    ) -> Dict[str, Any]:
        """Complete adversarial test"""
        test = self._get_node("adversarial_test", test_id)
        if not test:
            return {"error": "Test not found"}

        vulnerabilities = test.get("vulnerabilities_found", [])
        passed = len(vulnerabilities) == 0

        self._update_node("adversarial_test", test_id, {
            "status": "completed",
            "summary": summary,
            "mitigations_required": mitigations_required,
            "passed": passed,
            "completed_by": completed_by,
            "completed_at": self._now()
        })

        return {
            "test_id": test_id,
            "passed": passed,
            "vulnerabilities_count": len(vulnerabilities),
            "mitigations_required": mitigations_required
        }

    # =========================================================================
    # Downstream Provider Management
    # =========================================================================

    def register_downstream_provider(
        self,
        model_id: str,
        provider_name: str,
        provider_type: str,  # integrator, deployer, fine_tuner
        use_case: str,
        provider_id: Optional[str] = None
    ) -> str:
        """Register a downstream provider"""
        pid = provider_id or self._generate_id("dp")
        props = {
            "model_id": model_id,
            "provider_name": provider_name,
            "provider_type": provider_type,
            "use_case": use_case,
            "status": "active",
            "registered_at": self._now(),
            "description": f"Downstream provider: {provider_name}"
        }
        return self._add_node("downstream_provider", pid, props)

    def provide_documentation_to_downstream(
        self,
        model_id: str,
        downstream_id: str,
        documentation_refs: List[str],
        provided_by: str
    ) -> str:
        """Record provision of documentation to downstream provider"""
        did = self._generate_id("dd")
        props = {
            "model_id": model_id,
            "downstream_id": downstream_id,
            "documentation_refs": documentation_refs,
            "provided_by": provided_by,
            "provided_at": self._now(),
            "description": f"Documentation delivery"
        }
        return self._add_node("documentation_delivery", did, props)

    def get_downstream_providers(self, model_id: str) -> List[Dict[str, Any]]:
        """Get downstream providers for a model"""
        return self._find_nodes("downstream_provider", model_id=model_id)

    # =========================================================================
    # Copyright Compliance (Art. 53(1)(c))
    # =========================================================================

    def record_copyright_policy(
        self,
        model_id: str,
        policy_type: str,  # opt_out_mechanism, training_data_disclosure, licensing
        policy_content: str,
        policy_url: Optional[str] = None,
        policy_id: Optional[str] = None
    ) -> str:
        """Record copyright compliance policy"""
        pid = policy_id or self._generate_id("cp")
        props = {
            "model_id": model_id,
            "policy_type": policy_type,
            "policy_content": policy_content,
            "policy_url": policy_url,
            "created_at": self._now(),
            "description": f"Copyright policy: {policy_type}"
        }
        return self._add_node("copyright_policy", pid, props)

    def get_copyright_policies(self, model_id: str) -> List[Dict[str, Any]]:
        """Get copyright policies for a model"""
        return self._find_nodes("copyright_policy", model_id=model_id)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get GPAI governance statistics"""
        base_stats = super().get_stats()
        models = self._find_nodes("gpai_model")
        assessments = self._find_nodes("systemic_risk_assessment")
        obligations = self._find_nodes("gpai_obligation")
        evaluations = self._find_nodes("gpai_evaluation")
        adversarial_tests = self._find_nodes("adversarial_test")
        downstream = self._find_nodes("downstream_provider")

        return {
            **base_stats,
            "total_models": len(models),
            "systemic_risk_models": len([m for m in models if m.get("has_systemic_risk")]),
            "models_by_category": {
                cat.value: len([m for m in models if m.get("category") == cat.value])
                for cat in GPAICategory
            },
            "risk_assessments": len(assessments),
            "completed_assessments": len([a for a in assessments if a.get("status") == "completed"]),
            "total_obligations": len(obligations),
            "fulfilled_obligations": len([o for o in obligations if o.get("status") == "fulfilled"]),
            "evaluations": len(evaluations),
            "passed_evaluations": len([e for e in evaluations if e.get("passed")]),
            "adversarial_tests": len(adversarial_tests),
            "tests_with_vulnerabilities": len([t for t in adversarial_tests if t.get("vulnerabilities_found")]),
            "downstream_providers": len(downstream)
        }
