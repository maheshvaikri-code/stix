"""
Multi-Agent Coordination Store
==============================

Manages agent groups, coordination roles, protocols, and shared state.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import AgentGroup, CoordinationRole, CoordinationProtocol, SharedState

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class CoordinationStore(BaseStore):
    """Store for multi-agent coordination governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "coordination")

    # =========================================================================
    # Agent Group Management
    # =========================================================================

    def create_group(
        self,
        name: str,
        purpose: str,
        formation: str = "dynamic",
        group_id: Optional[str] = None
    ) -> str:
        """Create an agent group"""
        gid = group_id or self._generate_id("ag")
        props = {
            "name": name,
            "purpose": purpose,
            "formation": formation,  # "dynamic", "static", "fixed"
            "status": "active",
            "created_at": self._now()
        }
        return self._add_node("agent_group", gid, props)

    def get_group(self, group_id: str) -> Optional[Dict[str, Any]]:
        """Get group by ID"""
        return self._get_node("agent_group", group_id)

    def list_groups(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List agent groups"""
        groups = self._find_nodes("agent_group")
        if status:
            groups = [g for g in groups if g.get("status") == status]
        return groups

    def dissolve_group(self, group_id: str):
        """Dissolve an agent group"""
        self._update_node("agent_group", group_id, {
            "status": "dissolved",
            "dissolved_at": self._now()
        })

    # =========================================================================
    # Role Management
    # =========================================================================

    def assign_role(
        self,
        group_id: str,
        agent_id: str,
        role: str,
        authority: str,
        duration: str = "session",
        role_id: Optional[str] = None
    ) -> str:
        """Assign a role to an agent in a group"""
        rid = role_id or self._generate_id("cr")
        props = {
            "group_id": group_id,
            "agent_id": agent_id,
            "role": role,  # "coordinator", "worker", "chair", etc.
            "authority": authority,
            "duration": duration,  # "session", "permanent", "task"
            "assigned_at": self._now(),
            "active": True
        }
        self._add_node("coordination_role", rid, props)

        self._add_edge(
            "coordination_role", rid,
            "ROLE_IN",
            "agent_group", group_id,
            {}
        )

        return rid

    def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get role by ID"""
        return self._get_node("coordination_role", role_id)

    def get_agent_roles(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all roles for an agent"""
        roles = self._find_nodes("coordination_role", agent_id=agent_id)
        return [r for r in roles if r.get("active")]

    def get_group_members(self, group_id: str) -> List[Dict[str, Any]]:
        """Get all members of a group"""
        roles = self._find_nodes("coordination_role", group_id=group_id)
        return [r for r in roles if r.get("active")]

    def revoke_role(self, role_id: str):
        """Revoke a role"""
        self._update_node("coordination_role", role_id, {
            "active": False,
            "revoked_at": self._now()
        })

    # =========================================================================
    # Protocol Management
    # =========================================================================

    def add_protocol(
        self,
        group_id: str,
        protocol_type: str,
        rules: str,
        enforced_by: str = "",
        protocol_id: Optional[str] = None
    ) -> str:
        """Add a coordination protocol"""
        pid = protocol_id or self._generate_id("cp")
        props = {
            "group_id": group_id,
            "type": protocol_type,  # "task_distribution", "voting", "conflict", etc.
            "rules": rules,
            "enforced_by": enforced_by,
            "active": True
        }
        self._add_node("coordination_protocol", pid, props)

        self._add_edge(
            "coordination_protocol", pid,
            "PROTOCOL_FOR",
            "agent_group", group_id,
            {}
        )

        return pid

    def get_protocol(self, protocol_id: str) -> Optional[Dict[str, Any]]:
        """Get protocol by ID"""
        return self._get_node("coordination_protocol", protocol_id)

    def get_group_protocols(self, group_id: str) -> List[Dict[str, Any]]:
        """Get all protocols for a group"""
        protocols = self._find_nodes("coordination_protocol", group_id=group_id)
        return [p for p in protocols if p.get("active")]

    # =========================================================================
    # Shared State Management
    # =========================================================================

    def create_shared_state(
        self,
        group_id: str,
        state_type: str,
        owner: str,
        access: str,
        initial_value: Any = None,
        state_id: Optional[str] = None
    ) -> str:
        """Create shared state for a group"""
        sid = state_id or self._generate_id("ss")
        props = {
            "group_id": group_id,
            "state_type": state_type,
            "owner": owner,
            "access": access,  # Access control specification
            "value": initial_value,
            "version": 1,
            "last_modified": self._now()
        }
        self._add_node("shared_state", sid, props)

        self._add_edge(
            "shared_state", sid,
            "SHARED_STATE",
            "agent_group", group_id,
            {}
        )

        return sid

    def get_shared_state(self, state_id: str) -> Optional[Dict[str, Any]]:
        """Get shared state by ID"""
        return self._get_node("shared_state", state_id)

    def update_shared_state(
        self,
        state_id: str,
        agent_id: str,
        new_value: Any
    ) -> Dict[str, Any]:
        """Update shared state (with access check)"""
        state = self.get_shared_state(state_id)
        if not state:
            return {"success": False, "reason": "State not found"}

        # Check access (simplified)
        access = state.get("access", "")
        owner = state.get("owner", "")

        if "write_" in access and owner != agent_id and owner != "collective":
            if f"write_{agent_id}" not in access and "write_all" not in access:
                return {"success": False, "reason": "Access denied"}

        version = state.get("version", 1)
        self._update_node("shared_state", state_id, {
            "value": new_value,
            "version": version + 1,
            "last_modified": self._now(),
            "last_modified_by": agent_id
        })

        return {"success": True, "new_version": version + 1}

    def get_group_shared_states(self, group_id: str) -> List[Dict[str, Any]]:
        """Get all shared states for a group"""
        return self._find_nodes("shared_state", group_id=group_id)

    # =========================================================================
    # Coordination Authority
    # =========================================================================

    def check_coordination_authority(
        self,
        agent_id: str,
        group_id: str,
        action: str
    ) -> Dict[str, Any]:
        """Check if an agent has authority for an action in a group"""
        roles = self.get_agent_roles(agent_id)
        group_roles = [r for r in roles if r.get("group_id") == group_id]

        if not group_roles:
            return {"authorized": False, "reason": "Not a member of group"}

        for role in group_roles:
            authority = role.get("authority", "")
            if action in authority or authority == "full":
                return {
                    "authorized": True,
                    "role": role.get("role"),
                    "authority": authority
                }

        return {"authorized": False, "reason": "Action not in role authority"}

    # =========================================================================
    # Violation Tracking
    # =========================================================================

    def record_violation(
        self,
        agent_id: str,
        protocol_id: str,
        violation: str,
        action_taken: str
    ) -> str:
        """Record a coordination protocol violation"""
        vid = self._generate_id("cv")
        props = {
            "agent_id": agent_id,
            "protocol_id": protocol_id,
            "violation": violation,
            "action_taken": action_taken,
            "timestamp": self._now()
        }
        self._add_node("coordination_violation", vid, props)

        self._add_edge(
            "coordination_violation", vid,
            "COORDINATION_VIOLATION",
            "coordination_protocol", protocol_id,
            {}
        )

        return vid

    def get_violations(
        self,
        agent_id: Optional[str] = None,
        group_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get coordination violations"""
        violations = self._find_nodes("coordination_violation")

        if agent_id:
            violations = [v for v in violations if v.get("agent_id") == agent_id]

        if group_id:
            group_protocols = [p["id"] for p in self.get_group_protocols(group_id)]
            violations = [v for v in violations if v.get("protocol_id") in group_protocols]

        return violations

    # =========================================================================
    # Conflict Resolution
    # =========================================================================

    def resolve_conflict(
        self,
        group_id: str,
        conflict_type: str,
        parties: List[str],
        resolution: str
    ) -> str:
        """Record a conflict resolution"""
        cid = self._generate_id("cf")
        props = {
            "group_id": group_id,
            "conflict_type": conflict_type,
            "parties": parties,
            "resolution": resolution,
            "resolved_at": self._now()
        }
        return self._add_node("conflict_resolution", cid, props)

    # =========================================================================
    # Coordination Metrics
    # =========================================================================

    def get_coordination_metrics(self, group_id: str) -> Dict[str, Any]:
        """Get coordination metrics for a group"""
        group = self.get_group(group_id)
        if not group:
            return {"error": "Group not found"}

        members = self.get_group_members(group_id)
        protocols = self.get_group_protocols(group_id)
        violations = self.get_violations(group_id=group_id)

        return {
            "group_id": group_id,
            "name": group.get("name"),
            "status": group.get("status"),
            "member_count": len(members),
            "protocol_count": len(protocols),
            "violation_count": len(violations),
            "health": "good" if len(violations) == 0 else "degraded"
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get coordination store statistics"""
        base_stats = super().get_stats()
        groups = self._find_nodes("agent_group")
        roles = self._find_nodes("coordination_role")
        protocols = self._find_nodes("coordination_protocol")
        violations = self._find_nodes("coordination_violation")

        return {
            **base_stats,
            "groups": len(groups),
            "active_groups": len([g for g in groups if g.get("status") == "active"]),
            "roles": len(roles),
            "active_roles": len([r for r in roles if r.get("active")]),
            "protocols": len(protocols),
            "violations": len(violations)
        }
