"""
Workforce & Training Store
==========================

Manages workforce members, HIPAA training compliance, access provisioning,
and sanction tracking per HIPAA 45 CFR 164.308(a)(3) and 164.530(e).
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import WorkforceRole, TrainingType, ViolationSeverity, SanctionType

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class WorkforceStore(BaseStore):
    """Store for workforce and training management"""

    # Training validity periods in days
    TRAINING_VALIDITY = {
        TrainingType.HIPAA_BASICS: 365,
        TrainingType.SECURITY_AWARENESS: 365,
        TrainingType.PRIVACY_PRACTICES: 365,
        TrainingType.PHI_HANDLING: 365,
        TrainingType.BREACH_RESPONSE: 365,
        TrainingType.ROLE_SPECIFIC: 365,
    }

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "workforce")

    # =========================================================================
    # Workforce Member Management
    # =========================================================================

    def add_workforce_member(
        self,
        name: str,
        employee_id: str,
        role: WorkforceRole,
        department: str,
        hire_date: str,
        supervisor: Optional[str] = None,
        member_id: Optional[str] = None
    ) -> str:
        """Add a workforce member"""
        mid = member_id or employee_id
        props = {
            "name": name,
            "employee_id": employee_id,
            "role": role.value,
            "department": department,
            "hire_date": hire_date,
            "supervisor": supervisor,
            "status": "active",
            "phi_access_level": "none",
            "description": f"Workforce member: {name}"
        }
        return self._add_node("workforce_member", mid, props)

    def get_workforce_member(self, member_id: str) -> Optional[Dict[str, Any]]:
        """Get workforce member by ID"""
        return self._get_node("workforce_member", member_id)

    def list_workforce_members(
        self,
        role: Optional[WorkforceRole] = None,
        department: Optional[str] = None,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """List workforce members with optional filters"""
        members = self._find_nodes("workforce_member", status=status)

        if role:
            members = [m for m in members if m.get("role") == role.value]
        if department:
            members = [m for m in members if m.get("department") == department]

        return members

    def update_member_status(self, member_id: str, status: str, reason: str = ""):
        """Update workforce member status"""
        self._update_node("workforce_member", member_id, {
            "status": status,
            "status_reason": reason,
            "status_updated_at": self._now()
        })

    def terminate_member(
        self,
        member_id: str,
        termination_date: str,
        reason: str,
        access_revoked: bool = True
    ):
        """Terminate a workforce member"""
        self._update_node("workforce_member", member_id, {
            "status": "terminated",
            "termination_date": termination_date,
            "termination_reason": reason,
            "access_revoked": access_revoked,
            "phi_access_level": "none"
        })

        # Revoke all access assignments
        if access_revoked:
            self._revoke_all_access(member_id)

    def _revoke_all_access(self, member_id: str):
        """Revoke all PHI access for a member"""
        assignments = self._find_nodes(
            "access_assignment",
            member_id=member_id,
            active=True
        )
        for assignment in assignments:
            self._update_node("access_assignment", assignment["id"], {
                "active": False,
                "revoked_at": self._now(),
                "revocation_reason": "termination"
            })

    # =========================================================================
    # PHI Access Level Management
    # =========================================================================

    def set_phi_access_level(
        self,
        member_id: str,
        access_level: str,  # none, limited, standard, full, administrative
        approved_by: str,
        justification: str
    ):
        """Set PHI access level for a workforce member"""
        self._update_node("workforce_member", member_id, {
            "phi_access_level": access_level,
            "access_level_approved_by": approved_by,
            "access_level_approved_at": self._now(),
            "access_level_justification": justification
        })

        # Record access level change
        self._record_access_change(member_id, access_level, approved_by, justification)

    def _record_access_change(
        self,
        member_id: str,
        new_level: str,
        approved_by: str,
        justification: str
    ):
        """Record access level change for audit"""
        acid = self._generate_id("ac")
        props = {
            "member_id": member_id,
            "new_level": new_level,
            "approved_by": approved_by,
            "justification": justification,
            "changed_at": self._now(),
            "description": f"Access level change: {new_level}"
        }
        self._add_node("access_level_change", acid, props)

    def add_access_assignment(
        self,
        member_id: str,
        resource_type: str,  # patient_records, department_records, system, etc.
        resource_id: str,
        access_type: str,  # read, write, full
        expires: Optional[str] = None,
        assignment_id: Optional[str] = None
    ) -> str:
        """Add a specific access assignment"""
        aid = assignment_id or self._generate_id("aa")
        props = {
            "member_id": member_id,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "access_type": access_type,
            "assigned_at": self._now(),
            "expires": expires,
            "active": True,
            "description": f"Access assignment: {resource_type}"
        }
        self._add_node("access_assignment", aid, props)

        # Link to member
        self._add_edge(
            "workforce_member", member_id,
            "HAS_ACCESS",
            "access_assignment", aid,
            {}
        )

        return aid

    def revoke_access_assignment(self, assignment_id: str, reason: str):
        """Revoke an access assignment"""
        self._update_node("access_assignment", assignment_id, {
            "active": False,
            "revoked_at": self._now(),
            "revocation_reason": reason
        })

    def get_member_access(self, member_id: str) -> List[Dict[str, Any]]:
        """Get all active access assignments for a member"""
        return self._find_nodes(
            "access_assignment",
            member_id=member_id,
            active=True
        )

    # =========================================================================
    # Training Management
    # =========================================================================

    def add_training_requirement(
        self,
        training_type: TrainingType,
        roles: List[str],
        frequency_days: int,
        required: bool = True,
        req_id: Optional[str] = None
    ) -> str:
        """Add a training requirement"""
        rid = req_id or training_type.value
        props = {
            "training_type": training_type.value,
            "applicable_roles": roles,
            "frequency_days": frequency_days,
            "required": required,
            "description": f"Training requirement: {training_type.value}"
        }
        return self._add_node("training_requirement", rid, props)

    def get_training_requirements(
        self,
        role: Optional[WorkforceRole] = None
    ) -> List[Dict[str, Any]]:
        """Get training requirements"""
        reqs = self._find_nodes("training_requirement")

        if role:
            reqs = [r for r in reqs if role.value in r.get("applicable_roles", [])]

        return reqs

    def record_training(
        self,
        member_id: str,
        training_type: TrainingType,
        completion_date: str,
        score: Optional[float] = None,
        instructor: Optional[str] = None,
        training_id: Optional[str] = None
    ) -> str:
        """Record training completion"""
        tid = training_id or self._generate_id("tr")

        # Calculate expiration
        validity_days = self.TRAINING_VALIDITY.get(training_type, 365)
        expiration = self._calculate_expiration(completion_date, validity_days)

        props = {
            "member_id": member_id,
            "training_type": training_type.value,
            "completion_date": completion_date,
            "expiration_date": expiration,
            "score": score,
            "instructor": instructor,
            "status": "valid",
            "description": f"Training: {training_type.value}"
        }
        self._add_node("training_record", tid, props)

        # Link to member
        self._add_edge(
            "workforce_member", member_id,
            "COMPLETED_TRAINING",
            "training_record", tid,
            {}
        )

        return tid

    def _calculate_expiration(self, start_date: str, days: int) -> str:
        """Calculate expiration date"""
        from datetime import datetime, timedelta
        start = datetime.fromisoformat(start_date.replace("+00:00", ""))
        expiration = start + timedelta(days=days)
        return expiration.isoformat() + "+00:00"

    def get_member_training(
        self,
        member_id: str,
        training_type: Optional[TrainingType] = None
    ) -> List[Dict[str, Any]]:
        """Get training records for a member"""
        records = self._find_nodes("training_record", member_id=member_id)

        if training_type:
            records = [r for r in records if r.get("training_type") == training_type.value]

        return records

    def check_training_compliance(self, member_id: str) -> Dict[str, Any]:
        """Check training compliance for a member"""
        member = self.get_workforce_member(member_id)
        if not member:
            return {"error": "member_not_found"}

        role = member.get("role")
        requirements = self.get_training_requirements()
        applicable = [r for r in requirements if role in r.get("applicable_roles", [])]

        training_records = self.get_member_training(member_id)
        now = self._now()

        compliant = []
        expired = []
        missing = []

        for req in applicable:
            training_type = req.get("training_type")
            # Find valid training for this type
            records = [
                t for t in training_records
                if t.get("training_type") == training_type
                and t.get("expiration_date", "") > now
            ]

            if records:
                compliant.append({
                    "training_type": training_type,
                    "expires": records[0].get("expiration_date")
                })
            else:
                # Check if expired vs never completed
                expired_records = [
                    t for t in training_records
                    if t.get("training_type") == training_type
                ]
                if expired_records:
                    expired.append({
                        "training_type": training_type,
                        "last_completed": expired_records[0].get("completion_date")
                    })
                else:
                    missing.append({"training_type": training_type})

        total_required = len(applicable)
        total_compliant = len(compliant)

        return {
            "member_id": member_id,
            "role": role,
            "total_requirements": total_required,
            "compliant": total_compliant,
            "compliance_rate": total_compliant / total_required if total_required > 0 else 1.0,
            "compliant_training": compliant,
            "expired_training": expired,
            "missing_training": missing,
            "is_compliant": len(expired) == 0 and len(missing) == 0
        }

    def get_expiring_training(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get training expiring within specified days"""
        from datetime import datetime, timedelta

        cutoff = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) +
            timedelta(days=days)
        ).isoformat()

        records = self._find_nodes("training_record", status="valid")
        now = self._now()

        expiring = [
            r for r in records
            if r.get("expiration_date", "") > now
            and r.get("expiration_date", "") < cutoff
        ]

        return expiring

    # =========================================================================
    # Violation & Sanction Management
    # =========================================================================

    def report_violation(
        self,
        member_id: str,
        violation_type: str,
        severity: ViolationSeverity,
        description: str,
        reporter: str,
        violation_id: Optional[str] = None
    ) -> str:
        """Report a HIPAA violation"""
        vid = violation_id or self._generate_id("vio")
        props = {
            "member_id": member_id,
            "violation_type": violation_type,
            "severity": severity.value,
            "description": description,
            "reporter": reporter,
            "reported_at": self._now(),
            "status": "open",
            "description": f"Violation: {violation_type}"
        }
        return self._add_node("violation", vid, props)

    def investigate_violation(
        self,
        violation_id: str,
        investigator: str,
        findings: str
    ):
        """Update violation with investigation findings"""
        self._update_node("violation", violation_id, {
            "status": "investigated",
            "investigator": investigator,
            "findings": findings,
            "investigated_at": self._now()
        })

    def close_violation(
        self,
        violation_id: str,
        resolution: str,
        closed_by: str
    ):
        """Close a violation"""
        self._update_node("violation", violation_id, {
            "status": "closed",
            "resolution": resolution,
            "closed_by": closed_by,
            "closed_at": self._now()
        })

    def get_member_violations(
        self,
        member_id: str,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get violations for a member"""
        violations = self._find_nodes("violation", member_id=member_id)

        if status:
            violations = [v for v in violations if v.get("status") == status]

        return violations

    def apply_sanction(
        self,
        member_id: str,
        violation_id: str,
        sanction_type: SanctionType,
        details: str,
        effective_date: str,
        applied_by: str,
        sanction_id: Optional[str] = None
    ) -> str:
        """Apply a sanction to a workforce member"""
        sid = sanction_id or self._generate_id("san")
        props = {
            "member_id": member_id,
            "violation_id": violation_id,
            "sanction_type": sanction_type.value,
            "details": details,
            "effective_date": effective_date,
            "applied_by": applied_by,
            "applied_at": self._now(),
            "status": "active",
            "description": f"Sanction: {sanction_type.value}"
        }
        self._add_node("sanction", sid, props)

        # Link to violation
        self._add_edge(
            "violation", violation_id,
            "RESULTED_IN",
            "sanction", sid,
            {}
        )

        # Apply sanction effects
        self._apply_sanction_effects(member_id, sanction_type)

        return sid

    def _apply_sanction_effects(self, member_id: str, sanction_type: SanctionType):
        """Apply effects of a sanction"""
        if sanction_type == SanctionType.TERMINATION:
            self.terminate_member(
                member_id,
                self._now(),
                "HIPAA violation sanction"
            )
        elif sanction_type == SanctionType.ACCESS_REVOCATION:
            self._revoke_all_access(member_id)
            self._update_node("workforce_member", member_id, {
                "phi_access_level": "none"
            })
        elif sanction_type == SanctionType.SUSPENSION:
            self.update_member_status(member_id, "suspended", "HIPAA violation sanction")

    def get_member_sanctions(self, member_id: str) -> List[Dict[str, Any]]:
        """Get sanctions for a member"""
        return self._find_nodes("sanction", member_id=member_id)

    # =========================================================================
    # Attestations
    # =========================================================================

    def add_attestation(
        self,
        member_id: str,
        attestation_type: str,  # confidentiality, policy_acknowledgment, etc.
        version: str,
        signed_date: str,
        attestation_id: Optional[str] = None
    ) -> str:
        """Record an attestation"""
        aid = attestation_id or self._generate_id("att")
        props = {
            "member_id": member_id,
            "attestation_type": attestation_type,
            "version": version,
            "signed_date": signed_date,
            "description": f"Attestation: {attestation_type}"
        }
        self._add_node("attestation", aid, props)

        # Link to member
        self._add_edge(
            "workforce_member", member_id,
            "SIGNED",
            "attestation", aid,
            {}
        )

        return aid

    def get_member_attestations(self, member_id: str) -> List[Dict[str, Any]]:
        """Get attestations for a member"""
        return self._find_nodes("attestation", member_id=member_id)

    def check_attestation(
        self,
        member_id: str,
        attestation_type: str
    ) -> Optional[Dict[str, Any]]:
        """Check if member has signed an attestation"""
        attestations = self._find_nodes(
            "attestation",
            member_id=member_id,
            attestation_type=attestation_type
        )
        if attestations:
            return sorted(
                attestations,
                key=lambda a: a.get("signed_date", ""),
                reverse=True
            )[0]
        return None

    # =========================================================================
    # Background Checks
    # =========================================================================

    def add_background_check(
        self,
        member_id: str,
        check_type: str,  # criminal, reference, credential, etc.
        result: str,  # passed, failed, pending
        performed_by: str,
        performed_date: str,
        check_id: Optional[str] = None
    ) -> str:
        """Record a background check"""
        cid = check_id or self._generate_id("bg")
        props = {
            "member_id": member_id,
            "check_type": check_type,
            "result": result,
            "performed_by": performed_by,
            "performed_date": performed_date,
            "description": f"Background check: {check_type}"
        }
        return self._add_node("background_check", cid, props)

    def get_member_background_checks(self, member_id: str) -> List[Dict[str, Any]]:
        """Get background checks for a member"""
        return self._find_nodes("background_check", member_id=member_id)

    # =========================================================================
    # Compliance Reporting
    # =========================================================================

    def get_department_compliance(self, department: str) -> Dict[str, Any]:
        """Get compliance summary for a department"""
        members = self.list_workforce_members(department=department)

        training_compliant = 0
        attestation_missing = 0
        violations_open = 0

        for member in members:
            mid = member.get("id")

            # Check training
            compliance = self.check_training_compliance(mid)
            if compliance.get("is_compliant"):
                training_compliant += 1

            # Check confidentiality attestation
            att = self.check_attestation(mid, "confidentiality")
            if not att:
                attestation_missing += 1

            # Check violations
            violations = self.get_member_violations(mid, status="open")
            violations_open += len(violations)

        total = len(members)
        return {
            "department": department,
            "total_members": total,
            "training_compliant": training_compliant,
            "training_compliance_rate": training_compliant / total if total > 0 else 1.0,
            "attestation_missing": attestation_missing,
            "open_violations": violations_open
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get workforce statistics"""
        base_stats = super().get_stats()
        members = self._find_nodes("workforce_member")
        training = self._find_nodes("training_record")
        violations = self._find_nodes("violation")
        sanctions = self._find_nodes("sanction")

        active = len([m for m in members if m.get("status") == "active"])
        terminated = len([m for m in members if m.get("status") == "terminated"])

        # By role
        by_role = {}
        for m in members:
            role = m.get("role", "unknown")
            by_role[role] = by_role.get(role, 0) + 1

        # By department
        by_dept = {}
        for m in members:
            dept = m.get("department", "unknown")
            by_dept[dept] = by_dept.get(dept, 0) + 1

        return {
            **base_stats,
            "workforce_members": len(members),
            "active_members": active,
            "terminated_members": terminated,
            "training_records": len(training),
            "violations": len(violations),
            "open_violations": len([v for v in violations if v.get("status") == "open"]),
            "sanctions": len(sanctions),
            "by_role": by_role,
            "by_department": by_dept
        }
