"""
Conformity Assessment Store
===========================

Manages conformity assessment procedures for high-risk AI systems per Articles 43-49.
Handles internal control, third-party assessment, CE marking, and EU database registration.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import (
    ConformityRoute, ConformityStatus, CEMarkingStatus,
    HighRiskCategory, AIRiskLevel
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


# Conformity assessment routes by category per Annex III
CONFORMITY_ROUTES = {
    HighRiskCategory.BIOMETRICS: ConformityRoute.NOTIFIED_BODY,
    HighRiskCategory.CRITICAL_INFRASTRUCTURE: ConformityRoute.INTERNAL_CONTROL_QMS,
    HighRiskCategory.EDUCATION_VOCATIONAL: ConformityRoute.INTERNAL_CONTROL_QMS,
    HighRiskCategory.EMPLOYMENT_WORKERS: ConformityRoute.INTERNAL_CONTROL_QMS,
    HighRiskCategory.ESSENTIAL_SERVICES: ConformityRoute.INTERNAL_CONTROL_QMS,
    HighRiskCategory.LAW_ENFORCEMENT: ConformityRoute.NOTIFIED_BODY,
    HighRiskCategory.MIGRATION_ASYLUM: ConformityRoute.NOTIFIED_BODY,
    HighRiskCategory.JUSTICE_DEMOCRACY: ConformityRoute.NOTIFIED_BODY,
}


class ConformityAssessmentStore(BaseStore):
    """Store for conformity assessment management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "conformity_assessment")

    # =========================================================================
    # Assessment Process
    # =========================================================================

    def initiate_assessment(
        self,
        system_id: str,
        provider: str,
        high_risk_category: HighRiskCategory,
        intended_purpose: str,
        assessment_id: Optional[str] = None
    ) -> str:
        """Initiate conformity assessment for a high-risk AI system"""
        aid = assessment_id or self._generate_id("ca")

        # Determine conformity route based on category
        route = CONFORMITY_ROUTES.get(
            high_risk_category,
            ConformityRoute.INTERNAL_CONTROL_QMS
        )

        props = {
            "system_id": system_id,
            "provider": provider,
            "high_risk_category": high_risk_category.value,
            "intended_purpose": intended_purpose,
            "conformity_route": route.value,
            "status": ConformityStatus.NOT_STARTED.value,
            "initiated_at": self._now(),
            "steps_completed": [],
            "checklist": self._get_assessment_checklist(route),
            "description": f"Conformity assessment for {system_id}"
        }
        return self._add_node("conformity_assessment", aid, props)

    def _get_assessment_checklist(self, route: ConformityRoute) -> List[Dict[str, Any]]:
        """Get assessment checklist based on route"""
        base_checklist = [
            {"item": "technical_documentation", "status": "pending", "article": "Art. 11"},
            {"item": "risk_management_system", "status": "pending", "article": "Art. 9"},
            {"item": "data_governance", "status": "pending", "article": "Art. 10"},
            {"item": "record_keeping", "status": "pending", "article": "Art. 12"},
            {"item": "transparency_info", "status": "pending", "article": "Art. 13"},
            {"item": "human_oversight", "status": "pending", "article": "Art. 14"},
            {"item": "accuracy_robustness", "status": "pending", "article": "Art. 15"},
        ]

        if route == ConformityRoute.INTERNAL_CONTROL_QMS:
            base_checklist.append(
                {"item": "qms_documentation", "status": "pending", "article": "Art. 17"}
            )
        elif route == ConformityRoute.NOTIFIED_BODY:
            base_checklist.extend([
                {"item": "qms_documentation", "status": "pending", "article": "Art. 17"},
                {"item": "notified_body_review", "status": "pending", "article": "Art. 43"},
            ])

        return base_checklist

    def get_assessment(self, assessment_id: str) -> Optional[Dict[str, Any]]:
        """Get assessment by ID"""
        return self._get_node("conformity_assessment", assessment_id)

    def get_system_assessment(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get current assessment for a system"""
        assessments = self._find_nodes("conformity_assessment", system_id=system_id)
        # Return most recent active assessment
        active = [a for a in assessments if a.get("status") != ConformityStatus.WITHDRAWN.value]
        if active:
            active.sort(key=lambda x: x.get("initiated_at", ""), reverse=True)
            return active[0]
        return None

    def update_checklist_item(
        self,
        assessment_id: str,
        item: str,
        status: str,  # pending, in_progress, completed, failed
        evidence_ref: Optional[str] = None,
        notes: str = ""
    ):
        """Update a checklist item status"""
        assessment = self.get_assessment(assessment_id)
        if not assessment:
            return

        checklist = assessment.get("checklist", [])
        for item_dict in checklist:
            if item_dict["item"] == item:
                item_dict["status"] = status
                item_dict["evidence_ref"] = evidence_ref
                item_dict["notes"] = notes
                item_dict["updated_at"] = self._now()
                break

        completed = [i["item"] for i in checklist if i["status"] == "completed"]

        self._update_node("conformity_assessment", assessment_id, {
            "checklist": checklist,
            "steps_completed": completed
        })

    def update_assessment_status(
        self,
        assessment_id: str,
        status: ConformityStatus,
        notes: str = ""
    ):
        """Update overall assessment status"""
        self._update_node("conformity_assessment", assessment_id, {
            "status": status.value,
            "status_notes": notes,
            "status_updated_at": self._now()
        })

    # =========================================================================
    # Notified Body Involvement
    # =========================================================================

    def register_notified_body(
        self,
        name: str,
        identification_number: str,
        member_state: str,
        scope: List[str],
        body_id: Optional[str] = None
    ) -> str:
        """Register a notified body"""
        bid = body_id or self._generate_id("nb")
        props = {
            "name": name,
            "identification_number": identification_number,
            "member_state": member_state,
            "scope": scope,
            "status": "active",
            "registered_at": self._now(),
            "description": f"Notified Body: {name}"
        }
        return self._add_node("notified_body", bid, props)

    def get_notified_body(self, body_id: str) -> Optional[Dict[str, Any]]:
        """Get notified body by ID"""
        return self._get_node("notified_body", body_id)

    def list_notified_bodies(
        self,
        member_state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List notified bodies"""
        bodies = self._find_nodes("notified_body", status="active")
        if member_state:
            bodies = [b for b in bodies if b.get("member_state") == member_state]
        return bodies

    def assign_notified_body(
        self,
        assessment_id: str,
        body_id: str,
        assignment_date: Optional[str] = None
    ):
        """Assign a notified body to an assessment"""
        self._update_node("conformity_assessment", assessment_id, {
            "notified_body_id": body_id,
            "notified_body_assigned_at": assignment_date or self._now()
        })

        self._add_edge(
            "conformity_assessment", assessment_id,
            "ASSESSED_BY",
            "notified_body", body_id,
            {"assigned_at": self._now()}
        )

    def submit_to_notified_body(
        self,
        assessment_id: str,
        documentation_refs: List[str],
        submitted_by: str
    ) -> str:
        """Submit assessment to notified body"""
        sid = self._generate_id("nbs")
        props = {
            "assessment_id": assessment_id,
            "documentation_refs": documentation_refs,
            "submitted_by": submitted_by,
            "submitted_at": self._now(),
            "status": "submitted",
            "description": f"NB submission for {assessment_id}"
        }
        self._add_node("nb_submission", sid, props)

        self._update_node("conformity_assessment", assessment_id, {
            "status": ConformityStatus.UNDER_REVIEW.value,
            "nb_submission_id": sid
        })

        return sid

    def record_nb_decision(
        self,
        submission_id: str,
        decision: str,  # approved, rejected, conditional
        reviewer: str,
        findings: List[str],
        conditions: Optional[List[str]] = None,
        certificate_id: Optional[str] = None
    ):
        """Record notified body decision"""
        self._update_node("nb_submission", submission_id, {
            "status": "decided",
            "decision": decision,
            "reviewer": reviewer,
            "findings": findings,
            "conditions": conditions or [],
            "certificate_id": certificate_id,
            "decided_at": self._now()
        })

        # Get assessment ID and update status
        submission = self._get_node("nb_submission", submission_id)
        if submission:
            assessment_id = submission.get("assessment_id")
            if decision == "approved":
                status = ConformityStatus.PASSED.value
            elif decision == "conditional":
                status = ConformityStatus.CONDITIONAL.value
            else:
                status = ConformityStatus.FAILED.value

            self._update_node("conformity_assessment", assessment_id, {
                "status": status,
                "nb_decision": decision,
                "nb_conditions": conditions
            })

    # =========================================================================
    # EU Declaration of Conformity
    # =========================================================================

    def create_declaration(
        self,
        assessment_id: str,
        provider_name: str,
        provider_address: str,
        system_name: str,
        system_version: str,
        declaration_id: Optional[str] = None
    ) -> str:
        """Create EU Declaration of Conformity"""
        did = declaration_id or self._generate_id("doc")
        props = {
            "assessment_id": assessment_id,
            "provider_name": provider_name,
            "provider_address": provider_address,
            "system_name": system_name,
            "system_version": system_version,
            "status": "draft",
            "created_at": self._now(),
            "articles_referenced": [
                "Art. 9 - Risk Management",
                "Art. 10 - Data Governance",
                "Art. 11 - Technical Documentation",
                "Art. 12 - Record-keeping",
                "Art. 13 - Transparency",
                "Art. 14 - Human Oversight",
                "Art. 15 - Accuracy, Robustness, Cybersecurity"
            ],
            "description": f"EU Declaration of Conformity for {system_name}"
        }
        return self._add_node("eu_declaration", did, props)

    def sign_declaration(
        self,
        declaration_id: str,
        signatory_name: str,
        signatory_role: str,
        signature_date: Optional[str] = None
    ):
        """Sign the declaration of conformity"""
        self._update_node("eu_declaration", declaration_id, {
            "status": "signed",
            "signatory_name": signatory_name,
            "signatory_role": signatory_role,
            "signature_date": signature_date or self._now(),
            "signed_at": self._now()
        })

    def get_declaration(self, declaration_id: str) -> Optional[Dict[str, Any]]:
        """Get declaration by ID"""
        return self._get_node("eu_declaration", declaration_id)

    # =========================================================================
    # CE Marking
    # =========================================================================

    def apply_ce_marking(
        self,
        system_id: str,
        assessment_id: str,
        declaration_id: str,
        applied_by: str,
        notified_body_number: Optional[str] = None
    ) -> str:
        """Apply CE marking to the system"""
        mid = self._generate_id("ce")
        props = {
            "system_id": system_id,
            "assessment_id": assessment_id,
            "declaration_id": declaration_id,
            "applied_by": applied_by,
            "notified_body_number": notified_body_number,
            "status": CEMarkingStatus.APPLIED.value,
            "applied_at": self._now(),
            "valid_until": None,  # CE marking doesn't expire but can be withdrawn
            "description": f"CE marking for {system_id}"
        }
        self._add_node("ce_marking", mid, props)

        # Update system
        self._add_edge(
            "ai_system", system_id,
            "HAS_CE_MARKING",
            "ce_marking", mid,
            {}
        )

        return mid

    def suspend_ce_marking(
        self,
        marking_id: str,
        reason: str,
        authority: str
    ):
        """Suspend CE marking"""
        self._update_node("ce_marking", marking_id, {
            "status": CEMarkingStatus.SUSPENDED.value,
            "suspension_reason": reason,
            "suspended_by": authority,
            "suspended_at": self._now()
        })

    def withdraw_ce_marking(
        self,
        marking_id: str,
        reason: str,
        authority: str
    ):
        """Withdraw CE marking"""
        self._update_node("ce_marking", marking_id, {
            "status": CEMarkingStatus.WITHDRAWN.value,
            "withdrawal_reason": reason,
            "withdrawn_by": authority,
            "withdrawn_at": self._now()
        })

    def get_ce_marking(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get CE marking for a system"""
        markings = self._find_nodes("ce_marking", system_id=system_id)
        active = [m for m in markings if m.get("status") == CEMarkingStatus.APPLIED.value]
        return active[0] if active else None

    # =========================================================================
    # EU Database Registration
    # =========================================================================

    def register_in_eu_database(
        self,
        system_id: str,
        provider: str,
        system_name: str,
        risk_level: AIRiskLevel,
        high_risk_category: Optional[HighRiskCategory],
        intended_purpose: str,
        member_states: List[str],
        registration_id: Optional[str] = None
    ) -> str:
        """Register system in EU database (Art. 71)"""
        rid = registration_id or self._generate_id("eudb")
        props = {
            "system_id": system_id,
            "provider": provider,
            "system_name": system_name,
            "risk_level": risk_level.value,
            "high_risk_category": high_risk_category.value if high_risk_category else None,
            "intended_purpose": intended_purpose,
            "member_states": member_states,
            "status": "active",
            "registered_at": self._now(),
            "last_updated": self._now(),
            "description": f"EU Database registration: {system_name}"
        }
        return self._add_node("eu_db_registration", rid, props)

    def update_registration(
        self,
        registration_id: str,
        **updates
    ):
        """Update EU database registration"""
        updates["last_updated"] = self._now()
        self._update_node("eu_db_registration", registration_id, updates)

    def get_registration(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get EU database registration for a system"""
        registrations = self._find_nodes("eu_db_registration", system_id=system_id)
        active = [r for r in registrations if r.get("status") == "active"]
        return active[0] if active else None

    def search_eu_database(
        self,
        provider: Optional[str] = None,
        risk_level: Optional[AIRiskLevel] = None,
        category: Optional[HighRiskCategory] = None,
        member_state: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search EU database registrations"""
        registrations = self._find_nodes("eu_db_registration", status="active")

        if provider:
            registrations = [r for r in registrations if r.get("provider") == provider]
        if risk_level:
            registrations = [r for r in registrations if r.get("risk_level") == risk_level.value]
        if category:
            registrations = [r for r in registrations if r.get("high_risk_category") == category.value]
        if member_state:
            registrations = [
                r for r in registrations
                if member_state in r.get("member_states", [])
            ]

        return registrations

    # =========================================================================
    # Certificates
    # =========================================================================

    def issue_certificate(
        self,
        assessment_id: str,
        certificate_type: str,  # qms, technical_documentation, full_conformity
        issuer: str,
        valid_from: str,
        valid_until: str,
        scope: str,
        certificate_id: Optional[str] = None
    ) -> str:
        """Issue a conformity certificate"""
        cid = certificate_id or self._generate_id("cert")
        props = {
            "assessment_id": assessment_id,
            "certificate_type": certificate_type,
            "issuer": issuer,
            "valid_from": valid_from,
            "valid_until": valid_until,
            "scope": scope,
            "status": "valid",
            "issued_at": self._now(),
            "description": f"Certificate: {certificate_type}"
        }
        return self._add_node("conformity_certificate", cid, props)

    def revoke_certificate(
        self,
        certificate_id: str,
        reason: str,
        revoked_by: str
    ):
        """Revoke a certificate"""
        self._update_node("conformity_certificate", certificate_id, {
            "status": "revoked",
            "revocation_reason": reason,
            "revoked_by": revoked_by,
            "revoked_at": self._now()
        })

    def get_certificates(
        self,
        assessment_id: str,
        valid_only: bool = True
    ) -> List[Dict[str, Any]]:
        """Get certificates for an assessment"""
        certs = self._find_nodes("conformity_certificate", assessment_id=assessment_id)
        if valid_only:
            certs = [c for c in certs if c.get("status") == "valid"]
        return certs

    # =========================================================================
    # Assessment Summary
    # =========================================================================

    def get_assessment_summary(self, system_id: str) -> Dict[str, Any]:
        """Get comprehensive assessment summary for a system"""
        assessment = self.get_system_assessment(system_id)
        if not assessment:
            return {
                "system_id": system_id,
                "status": "no_assessment",
                "market_ready": False
            }

        checklist = assessment.get("checklist", [])
        completed = len([i for i in checklist if i["status"] == "completed"])
        total = len(checklist)

        ce_marking = self.get_ce_marking(system_id)
        registration = self.get_registration(system_id)

        market_ready = (
            assessment.get("status") == ConformityStatus.PASSED.value and
            ce_marking is not None and
            ce_marking.get("status") == CEMarkingStatus.APPLIED.value
        )

        return {
            "system_id": system_id,
            "assessment_id": assessment["id"],
            "conformity_route": assessment.get("conformity_route"),
            "status": assessment.get("status"),
            "checklist_progress": f"{completed}/{total}",
            "checklist_percentage": round((completed / total) * 100) if total > 0 else 0,
            "ce_marking": ce_marking.get("status") if ce_marking else None,
            "eu_database_registered": registration is not None,
            "market_ready": market_ready
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get conformity assessment statistics"""
        base_stats = super().get_stats()
        assessments = self._find_nodes("conformity_assessment")
        declarations = self._find_nodes("eu_declaration")
        ce_markings = self._find_nodes("ce_marking")
        registrations = self._find_nodes("eu_db_registration")
        certificates = self._find_nodes("conformity_certificate")
        notified_bodies = self._find_nodes("notified_body")

        # Count by status
        by_status = {}
        for status in ConformityStatus:
            count = len([a for a in assessments if a.get("status") == status.value])
            by_status[status.value] = count

        return {
            **base_stats,
            "total_assessments": len(assessments),
            "assessments_by_status": by_status,
            "passed_assessments": by_status.get(ConformityStatus.PASSED.value, 0),
            "declarations": len(declarations),
            "signed_declarations": len([d for d in declarations if d.get("status") == "signed"]),
            "ce_markings": len(ce_markings),
            "active_ce_markings": len([m for m in ce_markings if m.get("status") == CEMarkingStatus.APPLIED.value]),
            "eu_registrations": len(registrations),
            "certificates": len(certificates),
            "valid_certificates": len([c for c in certificates if c.get("status") == "valid"]),
            "notified_bodies": len(notified_bodies)
        }
