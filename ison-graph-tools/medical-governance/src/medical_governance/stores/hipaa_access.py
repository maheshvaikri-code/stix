"""
HIPAA Access Control Store
==========================

Manages role-based and purpose-based PHI access control per 45 CFR 164.312(a).
Implements workforce roles, access policies, and break-glass procedures.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import (
    WorkforceRole, AccessPurpose, AccessContext, SensitivityLevel,
    UserRole, AccessPolicy, AccessDecision
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class HIPAAAccessStore(BaseStore):
    """Store for HIPAA-compliant access control"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "hipaa_access")

    # =========================================================================
    # Role Management
    # =========================================================================

    def add_role(
        self,
        name: str,
        workforce_type: WorkforceRole,
        is_covered_entity: bool,
        default_purpose: AccessPurpose,
        description: str = "",
        role_id: Optional[str] = None
    ) -> str:
        """Add a workforce role"""
        rid = role_id or name
        props = {
            "name": name,
            "workforce_type": workforce_type.value,
            "is_covered_entity": is_covered_entity,
            "default_purpose": default_purpose.value,
            "active": True,
            "description": description or f"Role: {name}"
        }
        return self._add_node("hipaa_role", rid, props)

    def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get role by ID"""
        return self._get_node("hipaa_role", role_id)

    def list_roles(self, workforce_type: Optional[WorkforceRole] = None) -> List[Dict[str, Any]]:
        """List all roles"""
        roles = self._find_nodes("hipaa_role")
        if workforce_type:
            roles = [r for r in roles if r.get("workforce_type") == workforce_type.value]
        return roles

    # =========================================================================
    # User Management
    # =========================================================================

    def add_user(
        self,
        user_id: str,
        name: str,
        role_id: str,
        department: str = "",
        supervisor: Optional[str] = None
    ) -> str:
        """Add a user with role assignment"""
        props = {
            "name": name,
            "role_id": role_id,
            "department": department,
            "supervisor": supervisor,
            "active": True,
            "description": f"User: {name}"
        }
        self._add_node("hipaa_user", user_id, props)

        # Link user to role
        self._add_edge(
            "hipaa_user", user_id,
            "HAS_ROLE",
            "hipaa_role", role_id,
            {"assigned_at": self._now()}
        )

        return user_id

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        return self._get_node("hipaa_user", user_id)

    def get_user_role(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's current role"""
        edges = self._find_edges(
            source_type="hipaa_user", source_id=user_id,
            rel_type="HAS_ROLE"
        )
        if edges:
            role_id = edges[0]["target"][1]
            return self.get_role(role_id)
        return None

    def assign_patient(self, user_id: str, patient_id: str, relationship: str = "care_team"):
        """Assign a patient to a user's care"""
        # Store assignment as a node instead of edge (more flexible)
        aid = self._generate_id("pa")
        props = {
            "user_id": user_id,
            "patient_id": patient_id,
            "relationship": relationship,
            "assigned_at": self._now(),
            "active": True,
            "description": f"Patient assignment: {user_id} -> {patient_id}"
        }
        self._add_node("patient_assignment", aid, props)

    def get_assigned_patients(self, user_id: str) -> List[str]:
        """Get patients assigned to a user"""
        assignments = self._find_nodes("patient_assignment", user_id=user_id, active=True)
        return [a.get("patient_id") for a in assignments if a.get("patient_id")]

    # =========================================================================
    # Access Policy Management
    # =========================================================================

    def add_access_policy(
        self,
        role_id: str,
        purpose: AccessPurpose,
        data_scope: str,
        time_limit: str,
        conditions: str,
        minimum_necessary_profile: Optional[str] = None,
        policy_id: Optional[str] = None
    ) -> str:
        """Add an access policy for a role"""
        pid = policy_id or self._generate_id("ap")
        props = {
            "role_id": role_id,
            "purpose": purpose.value,
            "data_scope": data_scope,
            "time_limit": time_limit,
            "conditions": conditions,
            "minimum_necessary_profile": minimum_necessary_profile,
            "active": True,
            "description": f"Access policy for {role_id} - {purpose.value}"
        }
        self._add_node("access_policy", pid, props)

        # Link policy to role
        self._add_edge(
            "hipaa_role", role_id,
            "HAS_POLICY",
            "access_policy", pid,
            {}
        )

        return pid

    def get_policies_for_role(self, role_id: str) -> List[Dict[str, Any]]:
        """Get all access policies for a role"""
        return self._find_nodes("access_policy", role_id=role_id, active=True)

    def get_policy_for_purpose(
        self,
        role_id: str,
        purpose: AccessPurpose
    ) -> Optional[Dict[str, Any]]:
        """Get specific policy for role and purpose"""
        policies = self._find_nodes(
            "access_policy",
            role_id=role_id,
            purpose=purpose.value,
            active=True
        )
        return policies[0] if policies else None

    # =========================================================================
    # Access Decision
    # =========================================================================

    def check_access(
        self,
        user_id: str,
        patient_id: str,
        purpose: AccessPurpose,
        fields_requested: List[str],
        context: AccessContext = AccessContext.NORMAL_HOURS
    ) -> Dict[str, Any]:
        """Check if access should be granted"""
        user = self.get_user(user_id)
        if not user:
            return self._record_decision(
                user_id, patient_id, "denied", None, context,
                [], "user_not_found"
            )

        if not user.get("active"):
            return self._record_decision(
                user_id, patient_id, "denied", None, context,
                [], "user_inactive"
            )

        role = self.get_user_role(user_id)
        if not role:
            return self._record_decision(
                user_id, patient_id, "denied", None, context,
                [], "no_role_assigned"
            )

        # Get applicable policy
        policy = self.get_policy_for_purpose(role["id"], purpose)
        if not policy:
            return self._record_decision(
                user_id, patient_id, "denied", None, context,
                [], f"no_policy_for_purpose_{purpose.value}"
            )

        # Check patient assignment if required
        conditions = policy.get("conditions", "")
        if "assigned_patient" in conditions:
            assigned = self.get_assigned_patients(user_id)
            if patient_id not in assigned:
                return self._record_decision(
                    user_id, patient_id, "denied", policy["id"], context,
                    [], "patient_not_assigned"
                )

        # Apply context risk modifier
        risk_modifier = self._get_context_risk(context)
        if risk_modifier > 1.5 and purpose != AccessPurpose.TREATMENT:
            return self._record_decision(
                user_id, patient_id, "denied", policy["id"], context,
                [], "high_risk_context"
            )

        # Access granted
        return self._record_decision(
            user_id, patient_id, "granted", policy["id"], context,
            fields_requested, ""
        )

    def _get_context_risk(self, context: AccessContext) -> float:
        """Get risk modifier for access context"""
        risk_map = {
            AccessContext.NORMAL_HOURS: 1.0,
            AccessContext.AFTER_HOURS: 1.2,
            AccessContext.REMOTE_VPN: 1.3,
            AccessContext.REMOTE_PUBLIC: 2.0,
            AccessContext.EMERGENCY: 0.5,
            AccessContext.BREAK_GLASS: 0.8
        }
        return risk_map.get(context, 1.0)

    def _record_decision(
        self,
        user_id: str,
        patient_id: str,
        decision: str,
        policy_id: Optional[str],
        context: AccessContext,
        phi_accessed: List[str],
        reason: str
    ) -> Dict[str, Any]:
        """Record an access decision"""
        did = self._generate_id("ad")
        props = {
            "user_id": user_id,
            "patient_id": patient_id,
            "decision": decision,
            "policy_id": policy_id,
            "context": context.value,
            "phi_accessed": phi_accessed,
            "reason": reason,
            "timestamp": self._now(),
            "description": f"Access decision: {decision}"
        }
        self._add_node("access_decision", did, props)

        # No edge linking - the decision node stores the user_id directly

        return {
            "decision_id": did,
            "granted": decision == "granted",
            "decision": decision,
            "reason": reason,
            "policy_applied": policy_id,
            "context": context.value,
            "phi_accessed": phi_accessed if decision == "granted" else []
        }

    # =========================================================================
    # Break Glass (Emergency Access)
    # =========================================================================

    def break_glass(
        self,
        user_id: str,
        patient_id: str,
        reason: str,
        emergency_type: str = "clinical_emergency"
    ) -> Dict[str, Any]:
        """Invoke break-glass emergency access"""
        user = self.get_user(user_id)
        if not user:
            return {"success": False, "reason": "user_not_found"}

        # Record break-glass event
        bgid = self._generate_id("bg")
        props = {
            "user_id": user_id,
            "patient_id": patient_id,
            "reason": reason,
            "emergency_type": emergency_type,
            "timestamp": self._now(),
            "reviewed": False,
            "description": f"Break-glass access by {user_id}"
        }
        self._add_node("break_glass_event", bgid, props)

        # Grant temporary elevated access
        self._add_edge(
            "hipaa_user", user_id,
            "BREAK_GLASS_ACCESS",
            "patient", patient_id,
            {
                "event_id": bgid,
                "granted_at": self._now(),
                "expires_at": None,  # Must be reviewed
                "emergency_type": emergency_type
            }
        )

        return {
            "success": True,
            "event_id": bgid,
            "user_id": user_id,
            "patient_id": patient_id,
            "requires_review": True,
            "audit_level": "enhanced"
        }

    def review_break_glass(
        self,
        event_id: str,
        reviewer_id: str,
        appropriate: bool,
        notes: str = ""
    ):
        """Review a break-glass event"""
        self._update_node("break_glass_event", event_id, {
            "reviewed": True,
            "reviewed_by": reviewer_id,
            "reviewed_at": self._now(),
            "appropriate": appropriate,
            "review_notes": notes or "Break-glass event reviewed"
        })

    def get_pending_break_glass_reviews(self) -> List[Dict[str, Any]]:
        """Get break-glass events pending review"""
        events = self._find_nodes("break_glass_event", reviewed=False)
        return events

    # =========================================================================
    # Access Elevation
    # =========================================================================

    def elevate_access(
        self,
        user_id: str,
        to_role_id: str,
        approved_by: str,
        duration_hours: int,
        reason: str
    ) -> str:
        """Temporarily elevate user's access level"""
        eid = self._generate_id("ae")
        from datetime import datetime, timedelta

        expires_at = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) +
            timedelta(hours=duration_hours)
        ).isoformat() + "+00:00"

        props = {
            "user_id": user_id,
            "original_role": self.get_user(user_id).get("role_id"),
            "elevated_role": to_role_id,
            "approved_by": approved_by,
            "reason": reason,
            "granted_at": self._now(),
            "expires_at": expires_at,
            "active": True,
            "description": f"Access elevation for {user_id}"
        }
        self._add_node("access_elevation", eid, props)

        return eid

    def get_active_elevations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get active access elevations for a user"""
        elevations = self._find_nodes("access_elevation", user_id=user_id, active=True)
        now = self._now()

        # Filter out expired
        active = []
        for e in elevations:
            if e.get("expires_at", "") > now:
                active.append(e)
            else:
                # Mark as inactive
                self._update_node("access_elevation", e["id"], {"active": False})

        return active

    # =========================================================================
    # Access Audit
    # =========================================================================

    def get_access_history(
        self,
        patient_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get access decision history"""
        decisions = self._find_nodes("access_decision")

        if patient_id:
            decisions = [d for d in decisions if d.get("patient_id") == patient_id]
        if user_id:
            decisions = [d for d in decisions if d.get("user_id") == user_id]

        # Sort by timestamp descending
        decisions.sort(key=lambda d: d.get("timestamp", ""), reverse=True)

        return decisions[:limit]

    def get_denied_access(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get denied access attempts"""
        decisions = self._find_nodes("access_decision", decision="denied")

        if since:
            decisions = [d for d in decisions if d.get("timestamp", "") >= since]

        return decisions

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get access control statistics"""
        base_stats = super().get_stats()
        roles = self._find_nodes("hipaa_role")
        users = self._find_nodes("hipaa_user")
        policies = self._find_nodes("access_policy")
        decisions = self._find_nodes("access_decision")
        break_glass = self._find_nodes("break_glass_event")

        granted = len([d for d in decisions if d.get("decision") == "granted"])
        denied = len([d for d in decisions if d.get("decision") == "denied"])

        return {
            **base_stats,
            "roles": len(roles),
            "users": len(users),
            "active_users": len([u for u in users if u.get("active")]),
            "policies": len(policies),
            "decisions": len(decisions),
            "granted": granted,
            "denied": denied,
            "break_glass_events": len(break_glass),
            "pending_bg_reviews": len([bg for bg in break_glass if not bg.get("reviewed")])
        }
