"""
AI PHI Governance Store
=======================

Manages AI system registration, model inventory, PHI access governance, and AI-specific
HIPAA compliance requirements for medical AI systems.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import AISystemType, AIGovernanceRequirement, RiskTier, SensitivityLevel

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class AIGovernanceStore(BaseStore):
    """Store for AI-specific PHI governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "ai_governance")

    # =========================================================================
    # AI System Registration
    # =========================================================================

    def register_ai_system(
        self,
        name: str,
        system_type: AISystemType,
        purpose: str,
        vendor: str,
        version: str,
        risk_tier: RiskTier,
        phi_access_required: bool = False,
        system_id: Optional[str] = None
    ) -> str:
        """Register an AI system for PHI governance"""
        sid = system_id or self._generate_id("ai")
        props = {
            "name": name,
            "system_type": system_type.value,
            "purpose": purpose,
            "vendor": vendor,
            "version": version,
            "risk_tier": risk_tier.value,
            "phi_access_required": phi_access_required,
            "registered_at": self._now(),
            "status": "pending_approval",
            "description": f"AI system: {name}"
        }
        return self._add_node("ai_system", sid, props)

    def get_ai_system(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get AI system by ID"""
        return self._get_node("ai_system", system_id)

    def list_ai_systems(
        self,
        system_type: Optional[AISystemType] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List AI systems with optional filters"""
        systems = self._find_nodes("ai_system")

        if system_type:
            systems = [s for s in systems if s.get("system_type") == system_type.value]
        if status:
            systems = [s for s in systems if s.get("status") == status]

        return systems

    def approve_ai_system(
        self,
        system_id: str,
        approved_by: str,
        conditions: Optional[List[str]] = None
    ):
        """Approve AI system for PHI access"""
        self._update_node("ai_system", system_id, {
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": self._now(),
            "approval_conditions": conditions or []
        })

    def suspend_ai_system(self, system_id: str, reason: str, suspended_by: str):
        """Suspend AI system PHI access"""
        self._update_node("ai_system", system_id, {
            "status": "suspended",
            "suspension_reason": reason,
            "suspended_by": suspended_by,
            "suspended_at": self._now()
        })

    # =========================================================================
    # AI Model Inventory
    # =========================================================================

    def register_model(
        self,
        system_id: str,
        model_name: str,
        model_type: str,  # llm, classification, regression, etc.
        training_data_source: str,
        phi_in_training: bool,
        model_id: Optional[str] = None
    ) -> str:
        """Register an AI model"""
        mid = model_id or self._generate_id("mdl")
        props = {
            "system_id": system_id,
            "model_name": model_name,
            "model_type": model_type,
            "training_data_source": training_data_source,
            "phi_in_training": phi_in_training,
            "registered_at": self._now(),
            "status": "active",
            "description": f"AI model: {model_name}"
        }
        self._add_node("ai_model", mid, props)

        # Link to system
        self._add_edge(
            "ai_system", system_id,
            "HAS_MODEL",
            "ai_model", mid,
            {}
        )

        return mid

    def get_system_models(self, system_id: str) -> List[Dict[str, Any]]:
        """Get models for an AI system"""
        return self._find_nodes("ai_model", system_id=system_id)

    def update_model_status(self, model_id: str, status: str, notes: str = ""):
        """Update model status"""
        self._update_node("ai_model", model_id, {
            "status": status,
            "status_notes": notes,
            "status_updated_at": self._now()
        })

    # =========================================================================
    # PHI Access Scope
    # =========================================================================

    def define_phi_scope(
        self,
        system_id: str,
        phi_categories: List[str],
        sensitivity_levels: List[str],
        purposes: List[str],
        retention_days: int = 0,
        scope_id: Optional[str] = None
    ) -> str:
        """Define PHI access scope for an AI system"""
        sid = scope_id or self._generate_id("scope")
        props = {
            "system_id": system_id,
            "phi_categories": phi_categories,
            "sensitivity_levels": sensitivity_levels,
            "purposes": purposes,
            "retention_days": retention_days,
            "created_at": self._now(),
            "active": True,
            "description": f"PHI scope for {system_id}"
        }
        self._add_node("ai_phi_scope", sid, props)

        # Link to system
        self._add_edge(
            "ai_system", system_id,
            "HAS_PHI_SCOPE",
            "ai_phi_scope", sid,
            {}
        )

        return sid

    def get_phi_scope(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get PHI scope for an AI system"""
        scopes = self._find_nodes("ai_phi_scope", system_id=system_id, active=True)
        return scopes[0] if scopes else None

    def check_phi_access(
        self,
        system_id: str,
        phi_category: str,
        sensitivity_level: str,
        purpose: str
    ) -> Dict[str, Any]:
        """Check if AI system can access specific PHI"""
        system = self.get_ai_system(system_id)
        if not system:
            return {
                "allowed": False,
                "reason": "system_not_found"
            }

        if system.get("status") != "approved":
            return {
                "allowed": False,
                "reason": f"system_status_{system.get('status')}"
            }

        scope = self.get_phi_scope(system_id)
        if not scope:
            return {
                "allowed": False,
                "reason": "no_phi_scope_defined"
            }

        # Check category
        if phi_category not in scope.get("phi_categories", []):
            return {
                "allowed": False,
                "reason": "phi_category_not_in_scope",
                "requested": phi_category,
                "allowed_categories": scope.get("phi_categories")
            }

        # Check sensitivity
        if sensitivity_level not in scope.get("sensitivity_levels", []):
            return {
                "allowed": False,
                "reason": "sensitivity_level_not_in_scope",
                "requested": sensitivity_level,
                "allowed_levels": scope.get("sensitivity_levels")
            }

        # Check purpose
        if purpose not in scope.get("purposes", []):
            return {
                "allowed": False,
                "reason": "purpose_not_in_scope",
                "requested": purpose,
                "allowed_purposes": scope.get("purposes")
            }

        return {
            "allowed": True,
            "scope_id": scope.get("id"),
            "retention_days": scope.get("retention_days", 0)
        }

    # =========================================================================
    # AI Access Logging
    # =========================================================================

    def log_ai_phi_access(
        self,
        system_id: str,
        patient_id: str,
        phi_accessed: List[str],
        purpose: str,
        query_type: str,  # read, inference, training, etc.
        session_id: str = "",
        log_id: Optional[str] = None
    ) -> str:
        """Log AI system PHI access"""
        lid = log_id or self._generate_id("alog")
        props = {
            "system_id": system_id,
            "patient_id": patient_id,
            "phi_accessed": phi_accessed,
            "purpose": purpose,
            "query_type": query_type,
            "session_id": session_id,
            "timestamp": self._now(),
            "description": f"AI PHI access: {system_id}"
        }
        return self._add_node("ai_access_log", lid, props)

    def get_ai_access_logs(
        self,
        system_id: Optional[str] = None,
        patient_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get AI access logs"""
        logs = self._find_nodes("ai_access_log")

        if system_id:
            logs = [l for l in logs if l.get("system_id") == system_id]
        if patient_id:
            logs = [l for l in logs if l.get("patient_id") == patient_id]

        logs.sort(key=lambda l: l.get("timestamp", ""), reverse=True)
        return logs[:limit]

    # =========================================================================
    # AI Governance Requirements
    # =========================================================================

    def add_governance_requirement(
        self,
        system_id: str,
        requirement: AIGovernanceRequirement,
        status: str = "pending",
        due_date: Optional[str] = None,
        req_id: Optional[str] = None
    ) -> str:
        """Add a governance requirement to an AI system"""
        rid = req_id or self._generate_id("req")
        props = {
            "system_id": system_id,
            "requirement": requirement.value,
            "status": status,
            "due_date": due_date,
            "created_at": self._now(),
            "description": f"Requirement: {requirement.value}"
        }
        self._add_node("ai_requirement", rid, props)

        return rid

    def complete_requirement(
        self,
        requirement_id: str,
        completed_by: str,
        evidence: str
    ):
        """Mark a requirement as complete"""
        self._update_node("ai_requirement", requirement_id, {
            "status": "complete",
            "completed_by": completed_by,
            "completed_at": self._now(),
            "evidence": evidence
        })

    def get_system_requirements(
        self,
        system_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get requirements for an AI system"""
        reqs = self._find_nodes("ai_requirement", system_id=system_id)

        if status:
            reqs = [r for r in reqs if r.get("status") == status]

        return reqs

    def check_compliance_status(self, system_id: str) -> Dict[str, Any]:
        """Check AI system compliance status"""
        reqs = self.get_system_requirements(system_id)

        total = len(reqs)
        complete = len([r for r in reqs if r.get("status") == "complete"])
        pending = len([r for r in reqs if r.get("status") == "pending"])
        overdue = []

        now = self._now()
        for r in reqs:
            if r.get("status") == "pending" and r.get("due_date"):
                if r.get("due_date") < now:
                    overdue.append(r)

        return {
            "system_id": system_id,
            "total_requirements": total,
            "complete": complete,
            "pending": pending,
            "overdue": len(overdue),
            "compliance_rate": complete / total if total > 0 else 1.0,
            "overdue_requirements": overdue
        }

    # =========================================================================
    # AI Risk Assessment
    # =========================================================================

    def add_risk_assessment(
        self,
        system_id: str,
        assessor: str,
        risk_factors: Dict[str, Any],
        overall_risk: RiskTier,
        recommendations: List[str]
    ) -> str:
        """Add AI system risk assessment"""
        raid = self._generate_id("ra")
        props = {
            "system_id": system_id,
            "assessment_date": self._now(),
            "assessor": assessor,
            "risk_factors": risk_factors,
            "overall_risk": overall_risk.value,
            "recommendations": recommendations,
            "description": f"Risk assessment for {system_id}"
        }
        self._add_node("ai_risk_assessment", raid, props)

        # Update system risk tier
        self._update_node("ai_system", system_id, {
            "risk_tier": overall_risk.value,
            "last_risk_assessment": self._now()
        })

        return raid

    def get_risk_assessments(self, system_id: str) -> List[Dict[str, Any]]:
        """Get risk assessments for an AI system"""
        assessments = self._find_nodes("ai_risk_assessment", system_id=system_id)
        return sorted(
            assessments,
            key=lambda a: a.get("assessment_date", ""),
            reverse=True
        )

    # =========================================================================
    # AI Output Monitoring
    # =========================================================================

    def log_ai_output(
        self,
        system_id: str,
        output_type: str,  # recommendation, diagnosis, alert, etc.
        patient_id: str,
        output_summary: str,
        confidence: float,
        phi_in_output: bool = False,
        output_id: Optional[str] = None
    ) -> str:
        """Log AI system output"""
        oid = output_id or self._generate_id("out")
        props = {
            "system_id": system_id,
            "output_type": output_type,
            "patient_id": patient_id,
            "output_summary": output_summary,
            "confidence": confidence,
            "phi_in_output": phi_in_output,
            "timestamp": self._now(),
            "reviewed": False,
            "description": f"AI output: {output_type}"
        }
        return self._add_node("ai_output", oid, props)

    def review_ai_output(
        self,
        output_id: str,
        reviewer: str,
        review_outcome: str,  # approved, flagged, rejected
        notes: str = ""
    ):
        """Review an AI output"""
        self._update_node("ai_output", output_id, {
            "reviewed": True,
            "reviewer": reviewer,
            "review_outcome": review_outcome,
            "review_notes": notes,
            "reviewed_at": self._now()
        })

    def get_outputs_for_review(self, system_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get AI outputs pending review"""
        outputs = self._find_nodes("ai_output", reviewed=False)

        if system_id:
            outputs = [o for o in outputs if o.get("system_id") == system_id]

        return outputs

    # =========================================================================
    # De-identification for AI Training
    # =========================================================================

    def create_training_dataset(
        self,
        name: str,
        source_system: str,
        deidentification_method: str,  # safe_harbor, expert_determination
        phi_categories_removed: List[str],
        record_count: int,
        dataset_id: Optional[str] = None
    ) -> str:
        """Create a training dataset record"""
        did = dataset_id or self._generate_id("ds")
        props = {
            "name": name,
            "source_system": source_system,
            "deidentification_method": deidentification_method,
            "phi_categories_removed": phi_categories_removed,
            "record_count": record_count,
            "created_at": self._now(),
            "status": "pending_verification",
            "description": f"Training dataset: {name}"
        }
        return self._add_node("training_dataset", did, props)

    def verify_deidentification(
        self,
        dataset_id: str,
        verifier: str,
        verification_method: str,
        passed: bool,
        findings: str = ""
    ):
        """Verify de-identification of training dataset"""
        status = "verified" if passed else "verification_failed"
        self._update_node("training_dataset", dataset_id, {
            "status": status,
            "verified_by": verifier,
            "verification_method": verification_method,
            "verification_date": self._now(),
            "verification_findings": findings
        })

    def get_training_datasets(
        self,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get training datasets"""
        datasets = self._find_nodes("training_dataset")

        if status:
            datasets = [d for d in datasets if d.get("status") == status]

        return datasets

    # =========================================================================
    # AI Incident Tracking
    # =========================================================================

    def report_ai_incident(
        self,
        system_id: str,
        incident_type: str,  # phi_exposure, wrong_output, bias_detected, etc.
        severity: str,
        description: str,
        affected_patients: int = 0,
        incident_id: Optional[str] = None
    ) -> str:
        """Report an AI-related incident"""
        iid = incident_id or self._generate_id("inc")
        props = {
            "system_id": system_id,
            "incident_type": incident_type,
            "severity": severity,
            "description": description,
            "affected_patients": affected_patients,
            "reported_at": self._now(),
            "status": "open",
            "description": f"AI incident: {incident_type}"
        }
        return self._add_node("ai_incident", iid, props)

    def resolve_ai_incident(
        self,
        incident_id: str,
        resolution: str,
        resolved_by: str,
        corrective_actions: List[str]
    ):
        """Resolve an AI incident"""
        self._update_node("ai_incident", incident_id, {
            "status": "resolved",
            "resolution": resolution,
            "resolved_by": resolved_by,
            "resolved_at": self._now(),
            "corrective_actions": corrective_actions
        })

    def get_ai_incidents(
        self,
        system_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get AI incidents"""
        incidents = self._find_nodes("ai_incident")

        if system_id:
            incidents = [i for i in incidents if i.get("system_id") == system_id]
        if status:
            incidents = [i for i in incidents if i.get("status") == status]

        return incidents

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get AI governance statistics"""
        base_stats = super().get_stats()
        systems = self._find_nodes("ai_system")
        models = self._find_nodes("ai_model")
        access_logs = self._find_nodes("ai_access_log")
        requirements = self._find_nodes("ai_requirement")
        incidents = self._find_nodes("ai_incident")
        datasets = self._find_nodes("training_dataset")

        approved = len([s for s in systems if s.get("status") == "approved"])
        suspended = len([s for s in systems if s.get("status") == "suspended"])

        # By risk tier
        by_risk = {}
        for s in systems:
            tier = s.get("risk_tier", "unknown")
            by_risk[tier] = by_risk.get(tier, 0) + 1

        return {
            **base_stats,
            "ai_systems": len(systems),
            "approved_systems": approved,
            "suspended_systems": suspended,
            "models": len(models),
            "access_logs": len(access_logs),
            "requirements": len(requirements),
            "pending_requirements": len([r for r in requirements if r.get("status") == "pending"]),
            "incidents": len(incidents),
            "open_incidents": len([i for i in incidents if i.get("status") == "open"]),
            "training_datasets": len(datasets),
            "by_risk_tier": by_risk
        }
