"""
Authority & Delegation Store
============================

Manages hierarchical authority, delegation chains, and permission grants.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import (
    AuthorityLevel, RiskLevel,
    Principal, AuthorityScope, Delegation, DelegationChain
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class AuthorityStore(BaseStore):
    """Store for authority and delegation governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "authority")

    # =========================================================================
    # Principal Management
    # =========================================================================

    def add_principal(
        self,
        principal_type: str,
        name: str,
        authority_level: AuthorityLevel,
        principal_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Add a principal (human, agent, or system)"""
        pid = principal_id or self._generate_id("p")
        props = {
            "type": principal_type,
            "name": name,
            "authority_level": authority_level.value,
            "active": True,
            **(metadata or {})
        }
        return self._add_node("principal", pid, props)

    def deactivate_principal(self, principal_id: str):
        """Deactivate a principal"""
        self._update_node("principal", principal_id, {"active": False})

    def get_principal(self, principal_id: str) -> Optional[Dict[str, Any]]:
        """Get principal by ID"""
        return self._get_node("principal", principal_id)

    def list_principals(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """List all principals"""
        principals = self._find_nodes("principal")
        if active_only:
            principals = [p for p in principals if p.get("active", True)]
        return principals

    # =========================================================================
    # Authority Scope Management
    # =========================================================================

    def add_scope(
        self,
        name: str,
        risk_level: RiskLevel,
        requires_human: bool = False,
        conditions: Optional[str] = None,
        description: str = "",
        scope_id: Optional[str] = None
    ) -> str:
        """Add an authority scope"""
        # Use name as default ID for easy reference
        sid = scope_id or name
        props = {
            "name": name,
            "risk_level": risk_level.value,
            "requires_human": requires_human,
            "conditions": conditions or "",
            "description": description
        }
        return self._add_node("authority_scope", sid, props)

    def get_scope(self, scope_id: str) -> Optional[Dict[str, Any]]:
        """Get scope by ID"""
        return self._get_node("authority_scope", scope_id)

    def list_scopes(self, risk_level: Optional[RiskLevel] = None) -> List[Dict[str, Any]]:
        """List all scopes, optionally filtered by risk level"""
        scopes = self._find_nodes("authority_scope")
        if risk_level:
            scopes = [s for s in scopes if s.get("risk_level") == risk_level.value]
        return scopes

    # =========================================================================
    # Delegation Management
    # =========================================================================

    def delegate(
        self,
        from_principal: str,
        to_principal: str,
        scopes: List[str],
        conditions: str = "",
        expires_at: Optional[str] = None,
        revocable: bool = True
    ) -> str:
        """Create a delegation of authority"""
        # Validate principals exist
        from_p = self.get_principal(from_principal)
        to_p = self.get_principal(to_principal)
        if not from_p or not to_p:
            raise ValueError("Both principals must exist")

        # Create delegation node
        did = self._generate_id("d")
        props = {
            "from_principal": from_principal,
            "to_principal": to_principal,
            "scopes": scopes,
            "conditions": conditions,
            "granted_at": self._now(),
            "expires_at": expires_at,
            "revocable": revocable,
            "active": True
        }
        self._add_node("delegation", did, props)

        # Create edge
        self._add_edge(
            "principal", from_principal,
            "DELEGATES",
            "principal", to_principal,
            {"delegation_id": did, "scopes": scopes}
        )

        return did

    def revoke_delegation(self, delegation_id: str):
        """Revoke a delegation"""
        delegation = self._get_node("delegation", delegation_id)
        if delegation and delegation.get("revocable", True):
            self._update_node("delegation", delegation_id, {
                "active": False,
                "revoked_at": self._now()
            })
        elif delegation and not delegation.get("revocable"):
            raise ValueError("This delegation is not revocable")

    def get_delegations(self, principal_id: str) -> Dict[str, List[Dict[str, Any]]]:
        """Get delegations for a principal (both granted and received)"""
        all_delegations = self._find_nodes("delegation", active=True)

        granted = [d for d in all_delegations if d.get("from_principal") == principal_id]
        received = [d for d in all_delegations if d.get("to_principal") == principal_id]

        return {"granted": granted, "received": received}

    # =========================================================================
    # Authority Grants
    # =========================================================================

    def grant_authority(
        self,
        principal_id: str,
        scope_id: str,
        constraints: str = "",
        revocable: bool = True
    ):
        """Grant authority scope to a principal"""
        self._add_edge(
            "principal", principal_id,
            "GRANTS",
            "authority_scope", scope_id,
            {"constraints": constraints, "revocable": revocable, "active": True}
        )

    def revoke_authority(self, principal_id: str, scope_id: str):
        """Revoke authority from a principal"""
        # Find and update the edge
        edges = self._find_edges(
            source_type="principal", source_id=principal_id,
            rel_type="GRANTS",
            target_type="authority_scope", target_id=scope_id
        )
        # Mark as revoked (edges don't have direct update, would need to re-add)
        # For now, we track via separate revocation node
        self._add_node("authority_revocation", self._generate_id("ar"), {
            "principal_id": principal_id,
            "scope_id": scope_id,
            "revoked_at": self._now()
        })

    # =========================================================================
    # Permission Checks
    # =========================================================================

    def check_permission(
        self,
        principal_id: str,
        scope_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Check if a principal has permission for a scope.

        Returns:
            {
                "permitted": bool,
                "reason": str,
                "conditions": str,
                "via_delegation": bool,
                "delegation_chain": List[str]
            }
        """
        # Check direct grants
        direct_grants = self._find_edges(
            source_type="principal", source_id=principal_id,
            rel_type="GRANTS"
        )

        for grant in direct_grants:
            scope = self._get_node("authority_scope", grant["target"][1])
            if scope and scope.get("name") == scope_name:
                # Check if scope requires human
                if scope.get("requires_human"):
                    principal = self.get_principal(principal_id)
                    if principal and principal.get("type") != "human":
                        return {
                            "permitted": False,
                            "reason": "Scope requires human authority",
                            "conditions": "",
                            "via_delegation": False,
                            "delegation_chain": []
                        }

                return {
                    "permitted": True,
                    "reason": "Direct grant",
                    "conditions": grant["properties"].get("constraints", ""),
                    "via_delegation": False,
                    "delegation_chain": []
                }

        # Check delegated authority
        delegations = self.get_delegations(principal_id)["received"]
        for delegation in delegations:
            if not delegation.get("active"):
                continue

            # Check if expired
            if delegation.get("expires_at"):
                if delegation["expires_at"] < self._now():
                    continue

            # Check if scope is in delegated scopes
            if scope_name in delegation.get("scopes", []):
                # Recursively check if delegator has permission
                delegator_check = self.check_permission(
                    delegation["from_principal"], scope_name, context
                )
                if delegator_check["permitted"]:
                    return {
                        "permitted": True,
                        "reason": "Via delegation",
                        "conditions": delegation.get("conditions", ""),
                        "via_delegation": True,
                        "delegation_chain": [delegation["from_principal"]] + delegator_check.get("delegation_chain", [])
                    }

        return {
            "permitted": False,
            "reason": "No authority found",
            "conditions": "",
            "via_delegation": False,
            "delegation_chain": []
        }

    def get_authority_chain(self, principal_id: str) -> List[Dict[str, Any]]:
        """Get the full authority chain for a principal"""
        chain = []
        visited = set()

        def trace_chain(pid: str, depth: int = 0):
            if pid in visited or depth > 10:
                return
            visited.add(pid)

            delegations = self.get_delegations(pid)["received"]
            for d in delegations:
                if d.get("active"):
                    chain.append({
                        "depth": depth,
                        "from": d["from_principal"],
                        "to": pid,
                        "scopes": d.get("scopes", []),
                        "conditions": d.get("conditions", "")
                    })
                    trace_chain(d["from_principal"], depth + 1)

        trace_chain(principal_id)
        return chain

    # =========================================================================
    # Restrictions
    # =========================================================================

    def add_delegation_restriction(
        self,
        principal_id: str,
        scope_id: str,
        reason: str,
        exception: Optional[str] = None
    ):
        """Add a restriction preventing delegation of a scope"""
        self._add_edge(
            "principal", principal_id,
            "CANNOT_DELEGATE",
            "authority_scope", scope_id,
            {"reason": reason, "exception": exception}
        )

    def check_delegation_allowed(
        self,
        from_principal: str,
        scope_id: str
    ) -> Dict[str, Any]:
        """Check if a principal can delegate a scope"""
        restrictions = self._find_edges(
            source_type="principal", source_id=from_principal,
            rel_type="CANNOT_DELEGATE",
            target_type="authority_scope", target_id=scope_id
        )

        if restrictions:
            restriction = restrictions[0]
            return {
                "allowed": False,
                "reason": restriction["properties"].get("reason", "Restricted"),
                "exception": restriction["properties"].get("exception")
            }

        return {"allowed": True, "reason": "", "exception": None}

    def get_stats(self) -> Dict[str, Any]:
        """Get authority store statistics"""
        base_stats = super().get_stats()
        principals = self._find_nodes("principal")
        scopes = self._find_nodes("authority_scope")
        delegations = self._find_nodes("delegation")

        return {
            **base_stats,
            "principals": len(principals),
            "active_principals": len([p for p in principals if p.get("active")]),
            "scopes": len(scopes),
            "delegations": len(delegations),
            "active_delegations": len([d for d in delegations if d.get("active")])
        }
