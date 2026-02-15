"""
HIPAA Governance Engine
=======================

Main orchestration engine for HIPAA-compliant medical data governance.
Provides unified access to all governance stores and cross-cutting workflows.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .schema import (
    PHICategory, SensitivityLevel, WorkforceRole, AccessPurpose,
    ConsentType, ConsentStatus, BreachStatus, BreachSeverity,
    AISystemType, AIGovernanceRequirement, PatientRight,
    RightRequestStatus, TrainingType, ViolationSeverity
)
from .stores import (
    PHIClassificationStore,
    HIPAAAccessStore,
    MinimumNecessaryStore,
    ConsentStore,
    DisclosureStore,
    BusinessAssociateStore,
    BreachStore,
    PatientRightsStore,
    AIGovernanceStore,
    WorkforceStore,
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class HIPAAGovernanceEngine:
    """
    Main orchestration engine for HIPAA-compliant medical governance.

    Provides:
    - Unified access to all governance stores
    - Cross-cutting governance workflows
    - Compliance checking and reporting
    - PHI access authorization
    - Audit trail management
    """

    def __init__(self, graph: "ISONGraph"):
        """Initialize HIPAA Governance Engine with ISONGraph backend"""
        self.graph = graph

        # Initialize all stores
        self.phi = PHIClassificationStore(graph)
        self.access = HIPAAAccessStore(graph)
        self.minimum_necessary = MinimumNecessaryStore(graph)
        self.consent = ConsentStore(graph)
        self.disclosure = DisclosureStore(graph)
        self.business_associate = BusinessAssociateStore(graph)
        self.breach = BreachStore(graph)
        self.patient_rights = PatientRightsStore(graph)
        self.ai_governance = AIGovernanceStore(graph)
        self.workforce = WorkforceStore(graph)

    # =========================================================================
    # Unified PHI Access Authorization
    # =========================================================================

    def authorize_phi_access(
        self,
        actor_id: str,
        actor_type: str,  # workforce, ai_system, external
        patient_id: str,
        phi_elements: List[str],
        purpose: AccessPurpose,
        session_id: str = ""
    ) -> Dict[str, Any]:
        """
        Comprehensive PHI access authorization check.

        Checks:
        1. Actor's access rights
        2. Patient consent status
        3. Patient restrictions
        4. Minimum necessary filtering
        5. Break-glass status

        Returns authorization decision with allowed elements.
        """
        result = {
            "authorized": False,
            "actor_id": actor_id,
            "patient_id": patient_id,
            "requested_elements": phi_elements,
            "allowed_elements": [],
            "denied_elements": [],
            "denial_reasons": [],
            "requires_audit": True
        }

        # 1. Check actor access rights
        if actor_type == "workforce":
            from .schema import AccessContext
            access_check = self.access.check_access(
                actor_id, patient_id, purpose, phi_elements, AccessContext.NORMAL_HOURS
            )
            # Map store result to expected format
            access_check = {"allowed": access_check.get("granted", False), "reason": access_check.get("reason", "")}
        elif actor_type == "ai_system":
            # For AI systems, check each PHI element against scope
            access_check = {"allowed": True}
            for element in phi_elements:
                phi_check = self.ai_governance.check_phi_access(
                    actor_id,
                    element,
                    "standard",  # Would need to map element to sensitivity
                    purpose.value
                )
                if not phi_check.get("allowed"):
                    access_check = {"allowed": False, "reason": phi_check.get("reason")}
                    break
        else:
            access_check = {"allowed": False, "reason": "unknown_actor_type"}

        if not access_check.get("allowed"):
            result["denial_reasons"].append({
                "check": "access_rights",
                "reason": access_check.get("reason", "access_denied")
            })
            self._log_access_denied(actor_id, patient_id, "access_denied", session_id)
            return result

        # 2. Check patient consent (for non-TPO purposes)
        if purpose not in [AccessPurpose.TREATMENT, AccessPurpose.PAYMENT,
                          AccessPurpose.HEALTHCARE_OPERATIONS]:
            consent_check = self.consent.check_consent(
                patient_id,
                ConsentType.RESEARCH if purpose == AccessPurpose.RESEARCH else ConsentType.GENERAL,
                purpose
            )
            if not consent_check.get("has_consent"):
                result["denial_reasons"].append({
                    "check": "consent",
                    "reason": consent_check.get("reason", "no_consent")
                })
                self._log_access_denied(actor_id, patient_id, "no_consent", session_id)
                return result

        # 3. Check patient restrictions
        restrictions = self.consent.get_patient_restrictions(patient_id)
        for restriction in restrictions:
            scope = restriction.get("scope", "")
            # Check if any requested elements are restricted
            for element in phi_elements:
                if element in scope:
                    result["denied_elements"].append(element)
                    result["denial_reasons"].append({
                        "check": "restriction",
                        "element": element,
                        "reason": "patient_restriction"
                    })

        # 4. Apply minimum necessary filtering
        allowed_elements = [e for e in phi_elements if e not in result["denied_elements"]]

        if actor_type == "workforce":
            member = self.workforce.get_workforce_member(actor_id)
            role = member.get("role", "") if member else ""
            filtered = self.minimum_necessary.filter_request(
                role, purpose.value, allowed_elements
            )
            allowed_elements = filtered.get("allowed_fields", allowed_elements)

            denied_by_min_nec = [
                e for e in phi_elements
                if e not in allowed_elements and e not in result["denied_elements"]
            ]
            result["denied_elements"].extend(denied_by_min_nec)
            for element in denied_by_min_nec:
                result["denial_reasons"].append({
                    "check": "minimum_necessary",
                    "element": element,
                    "reason": "not_in_allowed_scope"
                })

        # 5. Set final authorization
        result["allowed_elements"] = allowed_elements

        if allowed_elements:
            result["authorized"] = True
            # Log successful access
            self.disclosure.log_access(
                actor_id, actor_type, patient_id,
                "view", allowed_elements, purpose,
                session_id=session_id
            )
        else:
            self._log_access_denied(actor_id, patient_id, "no_elements_allowed", session_id)

        return result

    def _log_access_denied(
        self,
        actor_id: str,
        patient_id: str,
        reason: str,
        session_id: str
    ):
        """Log an access denial"""
        self.disclosure.log_access_denied(actor_id, patient_id, "access", reason)

    # =========================================================================
    # Break-Glass Emergency Access
    # =========================================================================

    def activate_break_glass(
        self,
        actor_id: str,
        patient_id: str,
        emergency_reason: str
    ) -> Dict[str, Any]:
        """Activate emergency break-glass access"""
        # Create break-glass record using store's break_glass method
        bg_result = self.access.break_glass(
            actor_id, patient_id, emergency_reason, "clinical_emergency"
        )

        if not bg_result.get("success"):
            return {
                "success": False,
                "reason": bg_result.get("reason", "break_glass_failed")
            }

        # Grant temporary elevated access
        elevation_id = self.access.elevate_access(
            actor_id,
            "emergency_full",
            "system",
            4,  # duration_hours
            f"Break-glass: {emergency_reason}"
        )

        return {
            "break_glass_id": bg_result.get("event_id"),
            "elevation_id": elevation_id,
            "patient_id": patient_id,
            "actor_id": actor_id,
            "expires_in_hours": 4,
            "requires_review": True
        }

    def review_break_glass(
        self,
        break_glass_id: str,
        reviewer: str,
        appropriate: bool,
        notes: str
    ):
        """Review a break-glass access event"""
        self.access.review_break_glass(
            break_glass_id, reviewer, appropriate, notes
        )

        if not appropriate:
            # Report as potential violation
            bg = self.access._get_node("break_glass_event", break_glass_id)
            if bg:
                self.workforce.report_violation(
                    bg.get("user_id"),
                    "inappropriate_break_glass",
                    ViolationSeverity.HIGH,
                    f"Inappropriate break-glass access: {notes}",
                    reviewer
                )

    # =========================================================================
    # Breach Management Workflow
    # =========================================================================

    def report_breach(
        self,
        discovered_by: str,
        description: str,
        affected_count: int = 0,
        phi_types: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Report a potential breach and initiate workflow"""
        from .schema import NotificationRecipient

        breach_id = self.breach.report_potential_breach(
            discovered_by, description, affected_count, phi_types
        )

        # Create notification requirements
        deadline = self.breach._calculate_deadline(60)

        # Individual notification always required
        self.breach.add_notification_requirement(
            breach_id,
            NotificationRecipient.INDIVIDUALS,
            deadline,
            required=True
        )

        # HHS notification required
        hhs_type = "immediate" if affected_count >= 500 else "annual"
        self.breach.add_notification_requirement(
            breach_id,
            NotificationRecipient.HHS_OCR,
            deadline if affected_count >= 500 else "annual_deadline",
            required=True
        )

        # Media notification if > 500 in a state
        if affected_count >= 500:
            self.breach.add_notification_requirement(
                breach_id,
                NotificationRecipient.MEDIA,
                deadline,
                required=True
            )

        return {
            "breach_id": breach_id,
            "status": "reported",
            "notification_deadline": deadline,
            "hhs_submission_type": hhs_type,
            "next_steps": [
                "Perform risk assessment",
                "Identify affected individuals",
                "Prepare notification content"
            ]
        }

    def assess_breach_risk(
        self,
        breach_id: str,
        assessor: str,
        phi_nature: Dict[str, Any],
        unauthorized_person: Dict[str, Any],
        acquired_viewed: Dict[str, Any],
        risk_mitigated: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform four-factor breach risk assessment"""
        result = self.breach.perform_four_factor_assessment(
            breach_id,
            phi_nature,
            unauthorized_person,
            acquired_viewed,
            risk_mitigated
        )

        # Determine breach status based on assessment
        if result.get("notification_required"):
            severity = BreachSeverity.HIGH if result.get("risk_score", 0) > 0.5 else BreachSeverity.MEDIUM
            self.breach.add_assessment(
                breach_id, assessor, True, severity,
                {"four_factor_result": result}
            )
        else:
            self.breach.add_assessment(
                breach_id, assessor, False, BreachSeverity.LOW,
                {"four_factor_result": result}
            )

        return result

    # =========================================================================
    # Patient Rights Workflow
    # =========================================================================

    def handle_patient_right_request(
        self,
        patient_id: str,
        right_type: PatientRight,
        request_details: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Handle a patient rights request"""
        if right_type == PatientRight.ACCESS:
            request_id = self.patient_rights.request_access(
                patient_id,
                request_details.get("format", "electronic"),
                request_details.get("scope", "full_record")
            )
            deadline_days = 30
        elif right_type == PatientRight.AMENDMENT:
            request_id = self.patient_rights.request_amendment(
                patient_id,
                request_details.get("element"),
                request_details.get("proposed_change"),
                request_details.get("reason")
            )
            deadline_days = 60
        elif right_type == PatientRight.ACCOUNTING:
            request_id = self.patient_rights.request_accounting(
                patient_id,
                request_details.get("period", "6_years")
            )
            deadline_days = 60
        elif right_type == PatientRight.RESTRICTION:
            request_id = self.patient_rights.request_restriction(
                patient_id,
                request_details.get("restriction_type"),
                request_details.get("scope")
            )
            deadline_days = 0  # No deadline, but must respond
        elif right_type == PatientRight.CONFIDENTIAL_COMM:
            request_id = self.patient_rights.request_confidential_comm(
                patient_id,
                request_details.get("comm_type"),
                request_details.get("alternative")
            )
            deadline_days = 0
        else:
            return {"error": "unsupported_right_type"}

        return {
            "request_id": request_id,
            "right_type": right_type.value,
            "patient_id": patient_id,
            "deadline_days": deadline_days,
            "status": "pending"
        }

    # =========================================================================
    # AI System Governance Workflow
    # =========================================================================

    def onboard_ai_system(
        self,
        name: str,
        system_type: AISystemType,
        purpose: str,
        vendor: str,
        version: str,
        phi_access_required: bool,
        phi_scope: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Onboard a new AI system with governance requirements"""
        from .schema import RiskTier

        # Determine risk tier based on PHI access
        risk_tier = RiskTier.HIGH if phi_access_required else RiskTier.MEDIUM

        # Register system
        system_id = self.ai_governance.register_ai_system(
            name, system_type, purpose, vendor, version,
            risk_tier, phi_access_required
        )

        # Add governance requirements
        requirements = [
            AIGovernanceRequirement.RISK_ASSESSMENT,
            AIGovernanceRequirement.DATA_GOVERNANCE,
        ]

        if phi_access_required:
            requirements.extend([
                AIGovernanceRequirement.PHI_MINIMIZATION,
                AIGovernanceRequirement.OUTPUT_MONITORING,
                AIGovernanceRequirement.AUDIT_LOGGING,
            ])

        for req in requirements:
            self.ai_governance.add_governance_requirement(
                system_id, req, "pending"
            )

        # Define PHI scope if provided
        if phi_scope and phi_access_required:
            self.ai_governance.define_phi_scope(
                system_id,
                phi_scope.get("categories", []),
                phi_scope.get("sensitivity_levels", []),
                phi_scope.get("purposes", []),
                phi_scope.get("retention_days", 0)
            )

        return {
            "system_id": system_id,
            "name": name,
            "risk_tier": risk_tier.value,
            "requirements_count": len(requirements),
            "status": "pending_approval",
            "next_steps": [
                "Complete risk assessment",
                "Define PHI scope (if applicable)",
                "Complete all governance requirements",
                "Submit for approval"
            ]
        }

    # =========================================================================
    # Workforce Onboarding Workflow
    # =========================================================================

    def onboard_workforce_member(
        self,
        name: str,
        employee_id: str,
        role: WorkforceRole,
        department: str,
        supervisor: Optional[str] = None
    ) -> Dict[str, Any]:
        """Onboard a new workforce member"""
        from datetime import datetime

        hire_date = datetime.utcnow().isoformat() + "+00:00"

        # Add member
        member_id = self.workforce.add_workforce_member(
            name, employee_id, role, department, hire_date, supervisor
        )

        # Add required training
        required_training = [
            TrainingType.HIPAA_BASICS,
            TrainingType.PRIVACY_PRACTICES,
            TrainingType.SECURITY_AWARENESS,
        ]

        # Role-specific training
        if role in [WorkforceRole.PHYSICIAN, WorkforceRole.NURSE,
                    WorkforceRole.MEDICAL_ASSISTANT]:
            required_training.append(TrainingType.PHI_HANDLING)
        if role == WorkforceRole.PRIVACY_OFFICER:
            required_training.append(TrainingType.BREACH_RESPONSE)

        return {
            "member_id": member_id,
            "name": name,
            "role": role.value,
            "department": department,
            "required_training": [t.value for t in required_training],
            "next_steps": [
                "Complete required HIPAA training",
                "Sign confidentiality attestation",
                "Complete background check",
                "Obtain PHI access level approval"
            ]
        }

    # =========================================================================
    # Compliance Dashboard
    # =========================================================================

    def get_compliance_dashboard(self) -> Dict[str, Any]:
        """Get comprehensive compliance dashboard"""
        dashboard = {
            "generated_at": self._now(),
            "summary": {},
            "phi_governance": {},
            "workforce": {},
            "patient_rights": {},
            "breaches": {},
            "ai_systems": {},
            "business_associates": {},
            "alerts": []
        }

        # PHI Classification stats
        phi_stats = self.phi.get_stats()
        dashboard["phi_governance"] = {
            "total_elements": phi_stats.get("total_elements", 0),
            "deidentification_sessions": phi_stats.get("deidentification_sessions", 0)
        }

        # Workforce compliance
        workforce_stats = self.workforce.get_stats()
        dashboard["workforce"] = {
            "total_members": workforce_stats.get("workforce_members", 0),
            "active_members": workforce_stats.get("active_members", 0),
            "open_violations": workforce_stats.get("open_violations", 0)
        }

        # Check training compliance
        expiring = self.workforce.get_expiring_training(30)
        if expiring:
            dashboard["alerts"].append({
                "type": "training_expiring",
                "severity": "medium",
                "count": len(expiring),
                "message": f"{len(expiring)} training records expiring in 30 days"
            })

        # Patient rights stats
        rights_stats = self.patient_rights.get_stats()
        dashboard["patient_rights"] = {
            "total_requests": rights_stats.get("total_requests", 0),
            "pending_requests": rights_stats.get("pending_requests", 0),
            "overdue_requests": rights_stats.get("overdue_requests", 0)
        }

        if rights_stats.get("overdue_requests", 0) > 0:
            dashboard["alerts"].append({
                "type": "overdue_patient_requests",
                "severity": "high",
                "count": rights_stats.get("overdue_requests", 0),
                "message": "Patient rights requests past deadline"
            })

        # Breach stats
        breach_stats = self.breach.get_stats()
        dashboard["breaches"] = {
            "total_breaches": breach_stats.get("total_breaches", 0),
            "confirmed_breaches": breach_stats.get("confirmed_breaches", 0),
            "pending_notifications": breach_stats.get("pending_notifications", 0)
        }

        notification_check = self.breach.check_notification_deadlines()
        if notification_check.get("overdue"):
            dashboard["alerts"].append({
                "type": "overdue_breach_notifications",
                "severity": "critical",
                "count": len(notification_check.get("overdue", [])),
                "message": "Breach notifications past 60-day deadline"
            })

        # AI systems stats
        ai_stats = self.ai_governance.get_stats()
        dashboard["ai_systems"] = {
            "total_systems": ai_stats.get("ai_systems", 0),
            "approved_systems": ai_stats.get("approved_systems", 0),
            "open_incidents": ai_stats.get("open_incidents", 0)
        }

        # Business associate stats
        ba_stats = self.business_associate.get_stats()
        dashboard["business_associates"] = {
            "total_bas": ba_stats.get("business_associates", 0),
            "active_baas": ba_stats.get("active_baas", 0),
            "open_incidents": ba_stats.get("open_incidents", 0)
        }

        # Check for expiring BAAs
        baa_check = self.business_associate.check_baa_expiration()
        if baa_check.get("expired"):
            dashboard["alerts"].append({
                "type": "expired_baas",
                "severity": "critical",
                "count": len(baa_check.get("expired", [])),
                "message": "Business Associate Agreements have expired"
            })
        if baa_check.get("expiring_90_days"):
            dashboard["alerts"].append({
                "type": "expiring_baas",
                "severity": "medium",
                "count": len(baa_check.get("expiring_90_days", [])),
                "message": "BAAs expiring within 90 days"
            })

        # Calculate overall compliance score
        alerts_by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
        for alert in dashboard["alerts"]:
            sev = alert.get("severity", "low")
            alerts_by_severity[sev] = alerts_by_severity.get(sev, 0) + 1

        # Simple scoring: deduct points for alerts
        score = 100
        score -= alerts_by_severity["critical"] * 20
        score -= alerts_by_severity["high"] * 10
        score -= alerts_by_severity["medium"] * 5
        score -= alerts_by_severity["low"] * 2
        score = max(0, score)

        dashboard["summary"] = {
            "compliance_score": score,
            "total_alerts": len(dashboard["alerts"]),
            "critical_alerts": alerts_by_severity["critical"],
            "high_alerts": alerts_by_severity["high"]
        }

        return dashboard

    def _now(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    # =========================================================================
    # Export and Reporting
    # =========================================================================

    def export_all_stats(self) -> Dict[str, Any]:
        """Export statistics from all governance stores"""
        return {
            "phi_classification": self.phi.get_stats(),
            "access_control": self.access.get_stats(),
            "minimum_necessary": self.minimum_necessary.get_stats(),
            "consent": self.consent.get_stats(),
            "disclosure": self.disclosure.get_stats(),
            "business_associate": self.business_associate.get_stats(),
            "breach": self.breach.get_stats(),
            "patient_rights": self.patient_rights.get_stats(),
            "ai_governance": self.ai_governance.get_stats(),
            "workforce": self.workforce.get_stats()
        }

    def generate_compliance_report(self) -> Dict[str, Any]:
        """Generate a comprehensive HIPAA compliance report"""
        dashboard = self.get_compliance_dashboard()
        stats = self.export_all_stats()

        return {
            "report_type": "hipaa_compliance",
            "generated_at": self._now(),
            "compliance_score": dashboard["summary"]["compliance_score"],
            "executive_summary": {
                "overall_status": "compliant" if dashboard["summary"]["compliance_score"] >= 80 else "needs_attention",
                "critical_issues": dashboard["summary"]["critical_alerts"],
                "total_alerts": dashboard["summary"]["total_alerts"]
            },
            "sections": {
                "phi_governance": {
                    "description": "PHI Classification and De-identification",
                    "stats": stats["phi_classification"]
                },
                "access_control": {
                    "description": "HIPAA Access Control (45 CFR 164.312(a))",
                    "stats": stats["access_control"]
                },
                "minimum_necessary": {
                    "description": "Minimum Necessary Standard (45 CFR 164.502(b))",
                    "stats": stats["minimum_necessary"]
                },
                "consent_management": {
                    "description": "Consent Management (45 CFR 164.508/164.522)",
                    "stats": stats["consent"]
                },
                "audit_disclosure": {
                    "description": "Audit Trail & Accounting (45 CFR 164.312(b), 164.528)",
                    "stats": stats["disclosure"]
                },
                "business_associates": {
                    "description": "Business Associate Governance (45 CFR 164.308(b))",
                    "stats": stats["business_associate"]
                },
                "breach_notification": {
                    "description": "Breach Notification (45 CFR 164.400-414)",
                    "stats": stats["breach"]
                },
                "patient_rights": {
                    "description": "Patient Rights (45 CFR 164.520-528)",
                    "stats": stats["patient_rights"]
                },
                "ai_governance": {
                    "description": "AI-Specific PHI Governance",
                    "stats": stats["ai_governance"]
                },
                "workforce": {
                    "description": "Workforce Training & Sanctions (45 CFR 164.308(a)(3), 164.530(e))",
                    "stats": stats["workforce"]
                }
            },
            "alerts": dashboard["alerts"],
            "recommendations": self._generate_recommendations(dashboard)
        }

    def _generate_recommendations(self, dashboard: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on compliance status"""
        recommendations = []

        for alert in dashboard.get("alerts", []):
            alert_type = alert.get("type")
            if alert_type == "overdue_patient_requests":
                recommendations.append(
                    "Address overdue patient rights requests immediately to avoid HIPAA violations"
                )
            elif alert_type == "overdue_breach_notifications":
                recommendations.append(
                    "URGENT: Complete breach notifications - 60-day deadline has passed"
                )
            elif alert_type == "expired_baas":
                recommendations.append(
                    "Renew or terminate expired Business Associate Agreements immediately"
                )
            elif alert_type == "training_expiring":
                recommendations.append(
                    "Schedule workforce training renewals to maintain compliance"
                )

        if not recommendations:
            recommendations.append(
                "Continue monitoring compliance metrics and addressing alerts proactively"
            )

        return recommendations
