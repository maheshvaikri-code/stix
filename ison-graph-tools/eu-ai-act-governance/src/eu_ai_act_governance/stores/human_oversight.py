"""
Human Oversight Store
=====================

Manages human oversight requirements per Article 14.
Tracks oversight mechanisms, operator capabilities, and intervention records.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import OversightMeasure, OversightLevel, OversightStatus

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class HumanOversightStore(BaseStore):
    """Store for human oversight management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "human_oversight")

    # =========================================================================
    # Oversight Configuration
    # =========================================================================

    def configure_oversight(
        self,
        system_id: str,
        oversight_level: OversightLevel,
        measures: List[OversightMeasure],
        rationale: str,
        config_id: Optional[str] = None
    ) -> str:
        """Configure human oversight for an AI system"""
        cid = config_id or self._generate_id("ho")

        props = {
            "system_id": system_id,
            "oversight_level": oversight_level.value,
            "measures": [m.value for m in measures],
            "rationale": rationale,
            "status": OversightStatus.DESIGNED.value,
            "created_at": self._now(),
            "description": f"Human oversight config for {system_id}"
        }
        return self._add_node("oversight_config", cid, props)

    def get_oversight_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get oversight configuration by ID"""
        return self._get_node("oversight_config", config_id)

    def get_system_oversight(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get current oversight configuration for a system"""
        configs = self._find_nodes("oversight_config", system_id=system_id)
        active = [c for c in configs if c.get("status") != OversightStatus.DISABLED.value]
        if active:
            active.sort(key=lambda x: x.get("created_at", ""), reverse=True)
            return active[0]
        return None

    def update_oversight_status(
        self,
        config_id: str,
        status: OversightStatus,
        notes: str = ""
    ):
        """Update oversight configuration status"""
        self._update_node("oversight_config", config_id, {
            "status": status.value,
            "status_notes": notes,
            "updated_at": self._now()
        })

    # =========================================================================
    # Oversight Measures Implementation
    # =========================================================================

    def implement_measure(
        self,
        config_id: str,
        measure: OversightMeasure,
        implementation_details: str,
        technical_specs: Dict[str, Any],
        implemented_by: str,
        measure_id: Optional[str] = None
    ) -> str:
        """Record implementation of an oversight measure"""
        mid = measure_id or self._generate_id("om")
        props = {
            "config_id": config_id,
            "measure": measure.value,
            "implementation_details": implementation_details,
            "technical_specs": technical_specs,
            "implemented_by": implemented_by,
            "status": "implemented",
            "implemented_at": self._now(),
            "description": f"Oversight measure: {measure.value}"
        }
        return self._add_node("oversight_measure", mid, props)

    def verify_measure(
        self,
        measure_id: str,
        verified_by: str,
        test_results: str,
        effective: bool
    ):
        """Verify an oversight measure is effective"""
        self._update_node("oversight_measure", measure_id, {
            "status": "verified" if effective else "needs_improvement",
            "verified_by": verified_by,
            "test_results": test_results,
            "effective": effective,
            "verified_at": self._now()
        })

    def get_implemented_measures(
        self,
        config_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get implemented measures for a configuration"""
        measures = self._find_nodes("oversight_measure", config_id=config_id)
        if status:
            measures = [m for m in measures if m.get("status") == status]
        return measures

    # =========================================================================
    # Operator Training & Competency
    # =========================================================================

    def register_operator(
        self,
        system_id: str,
        operator_name: str,
        role: str,  # primary_operator, supervisor, administrator
        organization: str,
        operator_id: Optional[str] = None
    ) -> str:
        """Register a human operator for the system"""
        oid = operator_id or self._generate_id("op")
        props = {
            "system_id": system_id,
            "name": operator_name,
            "role": role,
            "organization": organization,
            "competency_verified": False,
            "training_completed": [],
            "active": True,
            "registered_at": self._now(),
            "description": f"Operator: {operator_name}"
        }
        return self._add_node("human_operator", oid, props)

    def record_training(
        self,
        operator_id: str,
        training_type: str,  # system_capabilities, limitations, intervention, bias_awareness
        training_date: str,
        duration_hours: float,
        trainer: str,
        assessment_score: Optional[int] = None,
        training_id: Optional[str] = None
    ) -> str:
        """Record operator training"""
        tid = training_id or self._generate_id("ot")
        props = {
            "operator_id": operator_id,
            "training_type": training_type,
            "training_date": training_date,
            "duration_hours": duration_hours,
            "trainer": trainer,
            "assessment_score": assessment_score,
            "passed": assessment_score >= 70 if assessment_score else None,
            "description": f"Training: {training_type}"
        }
        self._add_node("operator_training", tid, props)

        # Update operator training record
        operator = self._get_node("human_operator", operator_id)
        if operator:
            completed = operator.get("training_completed", [])
            if assessment_score and assessment_score >= 70:
                completed.append(training_type)
            self._update_node("human_operator", operator_id, {
                "training_completed": completed
            })

        return tid

    def verify_competency(
        self,
        operator_id: str,
        verified_by: str,
        competency_areas: List[str],
        verification_method: str,
        passed: bool
    ):
        """Verify operator competency"""
        self._update_node("human_operator", operator_id, {
            "competency_verified": passed,
            "competency_areas": competency_areas,
            "verification_method": verification_method,
            "verified_by": verified_by,
            "verified_at": self._now()
        })

    def get_operator(self, operator_id: str) -> Optional[Dict[str, Any]]:
        """Get operator by ID"""
        return self._get_node("human_operator", operator_id)

    def get_system_operators(
        self,
        system_id: str,
        active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get operators for a system"""
        operators = self._find_nodes("human_operator", system_id=system_id)
        if active_only:
            operators = [o for o in operators if o.get("active")]
        return operators

    # =========================================================================
    # Intervention & Override Records
    # =========================================================================

    def record_intervention(
        self,
        system_id: str,
        operator_id: str,
        intervention_type: str,  # override, correction, stop, escalation
        reason: str,
        original_output: str,
        action_taken: str,
        outcome: str,
        intervention_id: Optional[str] = None
    ) -> str:
        """Record a human intervention"""
        iid = intervention_id or self._generate_id("iv")
        props = {
            "system_id": system_id,
            "operator_id": operator_id,
            "intervention_type": intervention_type,
            "reason": reason,
            "original_output": original_output,
            "action_taken": action_taken,
            "outcome": outcome,
            "timestamp": self._now(),
            "reviewed": False,
            "description": f"Intervention: {intervention_type}"
        }
        return self._add_node("intervention_record", iid, props)

    def review_intervention(
        self,
        intervention_id: str,
        reviewer: str,
        appropriate: bool,
        feedback: str,
        system_update_needed: bool
    ):
        """Review an intervention"""
        self._update_node("intervention_record", intervention_id, {
            "reviewed": True,
            "reviewer": reviewer,
            "appropriate": appropriate,
            "feedback": feedback,
            "system_update_needed": system_update_needed,
            "reviewed_at": self._now()
        })

    def get_interventions(
        self,
        system_id: Optional[str] = None,
        operator_id: Optional[str] = None,
        intervention_type: Optional[str] = None,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get intervention records"""
        interventions = self._find_nodes("intervention_record")

        if system_id:
            interventions = [i for i in interventions if i.get("system_id") == system_id]
        if operator_id:
            interventions = [i for i in interventions if i.get("operator_id") == operator_id]
        if intervention_type:
            interventions = [i for i in interventions if i.get("intervention_type") == intervention_type]
        if since:
            interventions = [i for i in interventions if i.get("timestamp", "") >= since]

        return interventions

    # =========================================================================
    # Automation Bias Monitoring
    # =========================================================================

    def record_bias_incident(
        self,
        system_id: str,
        operator_id: str,
        incident_type: str,  # over_reliance, under_reliance, complacency
        description: str,
        detected_by: str,
        incident_id: Optional[str] = None
    ) -> str:
        """Record an automation bias incident"""
        iid = incident_id or self._generate_id("ab")
        props = {
            "system_id": system_id,
            "operator_id": operator_id,
            "incident_type": incident_type,
            "description": description,
            "detected_by": detected_by,
            "detected_at": self._now(),
            "mitigated": False,
            "node_description": f"Automation bias incident: {incident_type}"
        }
        return self._add_node("automation_bias_incident", iid, props)

    def mitigate_bias_incident(
        self,
        incident_id: str,
        mitigation_action: str,
        additional_training: bool,
        mitigated_by: str
    ):
        """Record mitigation of automation bias incident"""
        self._update_node("automation_bias_incident", incident_id, {
            "mitigated": True,
            "mitigation_action": mitigation_action,
            "additional_training": additional_training,
            "mitigated_by": mitigated_by,
            "mitigated_at": self._now()
        })

    def get_bias_incidents(
        self,
        system_id: Optional[str] = None,
        mitigated: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get automation bias incidents"""
        incidents = self._find_nodes("automation_bias_incident")

        if system_id:
            incidents = [i for i in incidents if i.get("system_id") == system_id]
        if mitigated is not None:
            incidents = [i for i in incidents if i.get("mitigated") == mitigated]

        return incidents

    # =========================================================================
    # Oversight Effectiveness Assessment
    # =========================================================================

    def assess_oversight_effectiveness(
        self,
        config_id: str,
        assessor: str,
        period_start: str,
        period_end: str,
        assessment_id: Optional[str] = None
    ) -> str:
        """Create oversight effectiveness assessment"""
        aid = assessment_id or self._generate_id("oe")

        config = self.get_oversight_config(config_id)
        system_id = config.get("system_id") if config else None

        # Gather metrics
        interventions = self.get_interventions(system_id=system_id, since=period_start)
        bias_incidents = self.get_bias_incidents(system_id=system_id)

        props = {
            "config_id": config_id,
            "system_id": system_id,
            "assessor": assessor,
            "period_start": period_start,
            "period_end": period_end,
            "total_interventions": len(interventions),
            "appropriate_interventions": len([i for i in interventions if i.get("appropriate")]),
            "bias_incidents": len(bias_incidents),
            "status": "in_progress",
            "created_at": self._now(),
            "description": f"Oversight effectiveness assessment"
        }
        return self._add_node("oversight_assessment", aid, props)

    def complete_oversight_assessment(
        self,
        assessment_id: str,
        effectiveness_score: int,  # 0-100
        findings: List[str],
        recommendations: List[str],
        compliant: bool
    ) -> Dict[str, Any]:
        """Complete oversight effectiveness assessment"""
        self._update_node("oversight_assessment", assessment_id, {
            "status": "completed",
            "effectiveness_score": effectiveness_score,
            "findings": findings,
            "recommendations": recommendations,
            "compliant": compliant,
            "completed_at": self._now()
        })

        return {
            "assessment_id": assessment_id,
            "effectiveness_score": effectiveness_score,
            "compliant": compliant,
            "findings": findings,
            "recommendations": recommendations
        }

    # =========================================================================
    # Stop/Shutdown Capability
    # =========================================================================

    def register_stop_mechanism(
        self,
        system_id: str,
        mechanism_type: str,  # emergency_stop, graceful_shutdown, pause
        trigger_method: str,
        response_time_ms: int,
        authorized_users: List[str],
        mechanism_id: Optional[str] = None
    ) -> str:
        """Register a stop/shutdown mechanism"""
        mid = mechanism_id or self._generate_id("sm")
        props = {
            "system_id": system_id,
            "mechanism_type": mechanism_type,
            "trigger_method": trigger_method,
            "response_time_ms": response_time_ms,
            "authorized_users": authorized_users,
            "tested": False,
            "active": True,
            "registered_at": self._now(),
            "description": f"Stop mechanism: {mechanism_type}"
        }
        return self._add_node("stop_mechanism", mid, props)

    def test_stop_mechanism(
        self,
        mechanism_id: str,
        tester: str,
        actual_response_time_ms: int,
        successful: bool,
        notes: str = ""
    ):
        """Test a stop mechanism"""
        self._update_node("stop_mechanism", mechanism_id, {
            "tested": True,
            "last_tested_by": tester,
            "last_tested_at": self._now(),
            "actual_response_time_ms": actual_response_time_ms,
            "test_successful": successful,
            "test_notes": notes
        })

    def record_stop_activation(
        self,
        mechanism_id: str,
        activated_by: str,
        reason: str,
        system_state_before: str,
        system_state_after: str
    ) -> str:
        """Record activation of stop mechanism"""
        aid = self._generate_id("sa")
        props = {
            "mechanism_id": mechanism_id,
            "activated_by": activated_by,
            "reason": reason,
            "system_state_before": system_state_before,
            "system_state_after": system_state_after,
            "activated_at": self._now(),
            "description": f"Stop mechanism activation"
        }
        return self._add_node("stop_activation", aid, props)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get human oversight statistics"""
        base_stats = super().get_stats()
        configs = self._find_nodes("oversight_config")
        measures = self._find_nodes("oversight_measure")
        operators = self._find_nodes("human_operator")
        interventions = self._find_nodes("intervention_record")
        bias_incidents = self._find_nodes("automation_bias_incident")
        assessments = self._find_nodes("oversight_assessment")

        return {
            **base_stats,
            "oversight_configs": len(configs),
            "active_configs": len([c for c in configs if c.get("status") == OversightStatus.OPERATIONAL.value]),
            "implemented_measures": len(measures),
            "verified_measures": len([m for m in measures if m.get("status") == "verified"]),
            "registered_operators": len(operators),
            "competent_operators": len([o for o in operators if o.get("competency_verified")]),
            "total_interventions": len(interventions),
            "appropriate_interventions": len([i for i in interventions if i.get("appropriate")]),
            "automation_bias_incidents": len(bias_incidents),
            "unmitigated_incidents": len([i for i in bias_incidents if not i.get("mitigated")]),
            "effectiveness_assessments": len(assessments)
        }
