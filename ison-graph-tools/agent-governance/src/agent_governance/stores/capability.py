"""
Capability Governance Store
===========================

Manages capabilities, feature flags, grants, and capability requests.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import RiskLevel, CapabilityMaturity, Capability, FeatureFlag, CapabilityGrant

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class CapabilityStore(BaseStore):
    """Store for capability governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "capability")

    # =========================================================================
    # Capability Management
    # =========================================================================

    def add_capability(
        self,
        name: str,
        risk_level: RiskLevel,
        maturity: CapabilityMaturity,
        default_state: str = "disabled",
        description: str = "",
        capability_id: Optional[str] = None
    ) -> str:
        """Add a capability"""
        # Use name as default ID for easy reference
        cid = capability_id or name
        props = {
            "name": name,
            "risk_level": risk_level.value,
            "maturity": maturity.value,
            "default_state": default_state,
            "description": description
        }
        return self._add_node("capability", cid, props)

    def get_capability(self, capability_id: str) -> Optional[Dict[str, Any]]:
        """Get capability by ID"""
        return self._get_node("capability", capability_id)

    def list_capabilities(
        self,
        risk_level: Optional[RiskLevel] = None,
        maturity: Optional[CapabilityMaturity] = None
    ) -> List[Dict[str, Any]]:
        """List capabilities"""
        capabilities = self._find_nodes("capability")

        if risk_level:
            capabilities = [c for c in capabilities if c.get("risk_level") == risk_level.value]
        if maturity:
            capabilities = [c for c in capabilities if c.get("maturity") == maturity.value]

        return capabilities

    def set_capability_dependency(
        self,
        capability_id: str,
        depends_on: str,
        dependency_type: str,
        constraint: str = ""
    ):
        """Set dependency between capabilities"""
        self._add_edge(
            "capability", capability_id,
            "CAPABILITY_DEPENDENCY",
            "capability", depends_on,
            {"type": dependency_type, "constraint": constraint}
        )

    def get_capability_dependencies(self, capability_id: str) -> List[Dict[str, Any]]:
        """Get dependencies for a capability"""
        deps = self._find_edges(
            source_type="capability", source_id=capability_id,
            rel_type="CAPABILITY_DEPENDENCY"
        )
        return [{"depends_on": e["target"][1], **e["properties"]} for e in deps]

    # =========================================================================
    # Feature Flags
    # =========================================================================

    def add_feature_flag(
        self,
        capability_id: str,
        name: str,
        state: str,
        conditions: str,
        flag_id: Optional[str] = None
    ) -> str:
        """Add a feature flag for a capability"""
        fid = flag_id or self._generate_id("ff")
        props = {
            "capability_id": capability_id,
            "name": name,
            "state": state,  # "enabled", "disabled"
            "conditions": conditions
        }
        self._add_node("feature_flag", fid, props)

        self._add_edge(
            "feature_flag", fid,
            "FEATURE_FLAG",
            "capability", capability_id,
            {}
        )

        return fid

    def get_feature_flag(self, flag_id: str) -> Optional[Dict[str, Any]]:
        """Get feature flag by ID"""
        return self._get_node("feature_flag", flag_id)

    def update_feature_flag(self, flag_id: str, state: str):
        """Update feature flag state"""
        self._update_node("feature_flag", flag_id, {"state": state})

    def get_capability_flags(self, capability_id: str) -> List[Dict[str, Any]]:
        """Get all flags for a capability"""
        return self._find_nodes("feature_flag", capability_id=capability_id)

    # =========================================================================
    # Capability Grants
    # =========================================================================

    def grant_capability(
        self,
        capability_id: str,
        principal_id: str,
        granted_by: str,
        conditions: str,
        expires_at: Optional[str] = None,
        grant_id: Optional[str] = None
    ) -> str:
        """Grant a capability to a principal"""
        gid = grant_id or self._generate_id("cg")
        props = {
            "capability_id": capability_id,
            "principal_id": principal_id,
            "granted_by": granted_by,
            "conditions": conditions,
            "granted_at": self._now(),
            "expires_at": expires_at,
            "active": True,
            "usage_count": 0
        }
        self._add_node("capability_grant", gid, props)

        self._add_edge(
            "capability_grant", gid,
            "CAPABILITY_GRANT",
            "capability", capability_id,
            {}
        )

        return gid

    def revoke_capability(self, grant_id: str, reason: str):
        """Revoke a capability grant"""
        self._update_node("capability_grant", grant_id, {
            "active": False,
            "revoked_at": self._now(),
            "revoke_reason": reason
        })

    def get_grant(self, grant_id: str) -> Optional[Dict[str, Any]]:
        """Get grant by ID"""
        return self._get_node("capability_grant", grant_id)

    def get_principal_capabilities(self, principal_id: str) -> List[Dict[str, Any]]:
        """Get all capabilities granted to a principal"""
        grants = self._find_nodes("capability_grant", principal_id=principal_id)
        active_grants = [g for g in grants if g.get("active")]

        result = []
        for grant in active_grants:
            # Check expiration
            if grant.get("expires_at") and grant["expires_at"] < self._now():
                continue

            capability = self.get_capability(grant.get("capability_id", ""))
            if capability:
                result.append({
                    "grant_id": grant["id"],
                    "capability_id": grant.get("capability_id"),
                    "capability_name": capability.get("name"),
                    "conditions": grant.get("conditions"),
                    "expires_at": grant.get("expires_at")
                })

        return result

    def record_capability_usage(self, grant_id: str):
        """Record usage of a capability"""
        grant = self.get_grant(grant_id)
        if grant:
            self._update_node("capability_grant", grant_id, {
                "usage_count": grant.get("usage_count", 0) + 1,
                "last_used": self._now()
            })

    # =========================================================================
    # Capability Requests
    # =========================================================================

    def request_capability(
        self,
        capability_id: str,
        requester_id: str,
        reason: str,
        request_id: Optional[str] = None
    ) -> str:
        """Request a capability"""
        rid = request_id or self._generate_id("rq")
        props = {
            "capability_id": capability_id,
            "requester_id": requester_id,
            "reason": reason,
            "status": "pending",
            "requested_at": self._now()
        }
        return self._add_node("capability_request", rid, props)

    def approve_request(
        self,
        request_id: str,
        reviewer: str,
        conditions: str,
        expires_at: Optional[str] = None
    ) -> str:
        """Approve a capability request"""
        request = self._get_node("capability_request", request_id)
        if not request:
            return ""

        self._update_node("capability_request", request_id, {
            "status": "approved",
            "reviewer": reviewer,
            "reviewed_at": self._now()
        })

        # Create grant
        grant_id = self.grant_capability(
            request.get("capability_id"),
            request.get("requester_id"),
            reviewer,
            conditions,
            expires_at
        )

        return grant_id

    def deny_request(self, request_id: str, reviewer: str, reason: str):
        """Deny a capability request"""
        self._update_node("capability_request", request_id, {
            "status": "denied",
            "reviewer": reviewer,
            "reviewed_at": self._now(),
            "deny_reason": reason
        })

    def get_pending_requests(self) -> List[Dict[str, Any]]:
        """Get all pending capability requests"""
        requests = self._find_nodes("capability_request", status="pending")
        return requests

    # =========================================================================
    # Capability Checks
    # =========================================================================

    def check_capability(
        self,
        principal_id: str,
        capability_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Check if a principal has a capability"""
        # Find capability by name
        capabilities = self._find_nodes("capability", name=capability_name)
        if not capabilities:
            return {"has_capability": False, "reason": "Capability not found"}

        capability = capabilities[0]

        # Check grants
        grants = self._find_nodes("capability_grant", principal_id=principal_id)
        active_grants = [
            g for g in grants
            if g.get("active") and g.get("capability_id") == capability["id"]
        ]

        if not active_grants:
            return {"has_capability": False, "reason": "No active grant"}

        grant = active_grants[0]

        # Check expiration
        if grant.get("expires_at") and grant["expires_at"] < self._now():
            return {"has_capability": False, "reason": "Grant expired"}

        # Check conditions
        conditions = grant.get("conditions", "")
        if conditions and context:
            try:
                result = eval(conditions, {"__builtins__": {}}, context)
                if not result:
                    return {"has_capability": False, "reason": "Conditions not met"}
            except:
                pass

        # Check feature flags
        flags = self.get_capability_flags(capability["id"])
        for flag in flags:
            if flag.get("state") == "disabled":
                return {
                    "has_capability": False,
                    "reason": f"Feature flag {flag.get('name')} is disabled"
                }

        return {
            "has_capability": True,
            "grant_id": grant["id"],
            "conditions": conditions
        }

    # =========================================================================
    # Grant Authority
    # =========================================================================

    def set_grant_authority(
        self,
        grantor_type: str,
        can_grant: List[str],
        cannot_grant: List[str]
    ):
        """Set what capabilities a grantor type can grant"""
        self._add_node("grant_authority", grantor_type, {
            "grantor_type": grantor_type,
            "can_grant": can_grant,
            "cannot_grant": cannot_grant
        })

    def check_grant_authority(
        self,
        grantor_type: str,
        capability_id: str
    ) -> Dict[str, Any]:
        """Check if a grantor type can grant a capability"""
        authority = self._get_node("grant_authority", grantor_type)
        if not authority:
            return {"can_grant": False, "reason": "No authority record"}

        can_grant = authority.get("can_grant", [])
        cannot_grant = authority.get("cannot_grant", [])

        if capability_id in cannot_grant:
            return {"can_grant": False, "reason": "Explicitly not allowed"}

        if capability_id in can_grant or "*" in can_grant:
            return {"can_grant": True}

        return {"can_grant": False, "reason": "Not in allowed list"}

    # =========================================================================
    # Capability Audit
    # =========================================================================

    def get_capability_audit(self, capability_id: str) -> Dict[str, Any]:
        """Get audit information for a capability"""
        capability = self.get_capability(capability_id)
        if not capability:
            return {"error": "Capability not found"}

        grants = self._find_nodes("capability_grant", capability_id=capability_id)

        total_usage = sum(g.get("usage_count", 0) for g in grants)
        violations = len([g for g in grants if not g.get("active") and g.get("revoke_reason")])

        return {
            "capability_id": capability_id,
            "name": capability.get("name"),
            "total_grants": len(grants),
            "active_grants": len([g for g in grants if g.get("active")]),
            "total_usage": total_usage,
            "violations": violations
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get capability store statistics"""
        base_stats = super().get_stats()
        capabilities = self._find_nodes("capability")
        flags = self._find_nodes("feature_flag")
        grants = self._find_nodes("capability_grant")
        requests = self._find_nodes("capability_request")

        return {
            **base_stats,
            "capabilities": len(capabilities),
            "feature_flags": len(flags),
            "grants": len(grants),
            "active_grants": len([g for g in grants if g.get("active")]),
            "pending_requests": len([r for r in requests if r.get("status") == "pending"])
        }
