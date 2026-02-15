"""
Temporal Governance Store
=========================

Manages time-bound authorities, rule versions, and governance history.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import TemporalAuthority, RuleVersion, TemporalContext, ScheduledChange

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class TemporalStore(BaseStore):
    """Store for temporal governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "temporal")

    # =========================================================================
    # Temporal Authority
    # =========================================================================

    def grant_temporal_authority(
        self,
        principal_id: str,
        authority_id: str,
        expires_at: str,
        renewable: bool = False,
        grant_id: Optional[str] = None
    ) -> str:
        """Grant time-bound authority"""
        tid = grant_id or self._generate_id("ta")
        props = {
            "principal_id": principal_id,
            "authority_id": authority_id,
            "granted_at": self._now(),
            "expires_at": expires_at,
            "renewable": renewable,
            "status": "active"
        }
        self._add_node("temporal_authority", tid, props)

        self._add_edge(
            "temporal_authority", tid,
            "TEMPORAL_AUTHORITY",
            "principal", principal_id,
            {}
        )

        return tid

    def check_temporal_authority(
        self,
        principal_id: str,
        authority_id: str
    ) -> Dict[str, Any]:
        """Check if a temporal authority is still valid"""
        authorities = self._find_nodes(
            "temporal_authority",
            principal_id=principal_id,
            authority_id=authority_id
        )

        active = [a for a in authorities if a.get("status") == "active"]
        if not active:
            return {"valid": False, "reason": "No active authority"}

        now = self._now()
        for auth in active:
            if auth.get("expires_at", "") > now:
                return {
                    "valid": True,
                    "expires_at": auth.get("expires_at"),
                    "renewable": auth.get("renewable")
                }

        return {"valid": False, "reason": "All authorities expired"}

    def renew_temporal_authority(
        self,
        grant_id: str,
        new_expires_at: str
    ):
        """Renew a temporal authority"""
        auth = self._get_node("temporal_authority", grant_id)
        if auth and auth.get("renewable"):
            self._update_node("temporal_authority", grant_id, {
                "expires_at": new_expires_at,
                "renewed_at": self._now()
            })

    def revoke_temporal_authority(self, grant_id: str):
        """Revoke a temporal authority early"""
        self._update_node("temporal_authority", grant_id, {
            "status": "revoked",
            "revoked_at": self._now()
        })

    def get_expiring_authorities(self, within_hours: int = 24) -> List[Dict[str, Any]]:
        """Get authorities expiring soon"""
        from datetime import datetime, timedelta, timezone

        cutoff = (datetime.now(timezone.utc) + timedelta(hours=within_hours)).isoformat()
        now = self._now()

        authorities = self._find_nodes("temporal_authority", status="active")
        expiring = [
            a for a in authorities
            if a.get("expires_at", "") <= cutoff and a.get("expires_at", "") > now
        ]

        return expiring

    # =========================================================================
    # Rule Versions
    # =========================================================================

    def create_rule_version(
        self,
        rule_id: str,
        version: str,
        effective_from: str,
        changes: str,
        effective_until: Optional[str] = None,
        version_id: Optional[str] = None
    ) -> str:
        """Create a new version of a rule"""
        vid = version_id or self._generate_id("rv")
        props = {
            "rule_id": rule_id,
            "version": version,
            "effective_from": effective_from,
            "effective_until": effective_until,
            "changes": changes,
            "created_at": self._now()
        }
        self._add_node("rule_version", vid, props)

        self._add_edge(
            "rule_version", vid,
            "RULE_VERSION",
            "governance_rule", rule_id,
            {}
        )

        return vid

    def get_rule_versions(self, rule_id: str) -> List[Dict[str, Any]]:
        """Get all versions of a rule"""
        versions = self._find_nodes("rule_version", rule_id=rule_id)
        return sorted(versions, key=lambda v: v.get("effective_from", ""), reverse=True)

    def get_active_rule_version(
        self,
        rule_id: str,
        at_time: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get the active version of a rule at a given time"""
        timestamp = at_time or self._now()
        versions = self.get_rule_versions(rule_id)

        for version in versions:
            effective_from = version.get("effective_from", "")
            effective_until = version.get("effective_until")

            if effective_from <= timestamp:
                if effective_until is None or effective_until > timestamp:
                    return version

        return None

    def sunset_rule_version(
        self,
        version_id: str,
        sunset_date: str,
        replacement_version_id: Optional[str] = None
    ):
        """Schedule sunset for a rule version"""
        self._update_node("rule_version", version_id, {
            "effective_until": sunset_date,
            "replacement": replacement_version_id
        })

    # =========================================================================
    # Temporal Context
    # =========================================================================

    def snapshot_context(
        self,
        timestamp: Optional[str] = None,
        context_id: Optional[str] = None
    ) -> str:
        """Create a snapshot of governance context at a point in time"""
        ts = timestamp or self._now()
        cid = context_id or self._generate_id("tc")

        # Collect active rules
        rule_versions = self._find_nodes("rule_version")
        active_rules = []
        for rv in rule_versions:
            effective_from = rv.get("effective_from", "")
            effective_until = rv.get("effective_until")
            if effective_from <= ts:
                if effective_until is None or effective_until > ts:
                    active_rules.append(rv["id"])

        # Collect active authorities
        authorities = self._find_nodes("temporal_authority", status="active")
        active_authorities = [
            a["id"] for a in authorities
            if a.get("granted_at", "") <= ts and a.get("expires_at", "") > ts
        ]

        props = {
            "timestamp": ts,
            "active_rules": active_rules,
            "active_authorities": active_authorities,
            "created_at": self._now()
        }
        return self._add_node("temporal_context", cid, props)

    def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get a temporal context snapshot"""
        return self._get_node("temporal_context", context_id)

    def get_context_at_time(self, timestamp: str) -> Dict[str, Any]:
        """Get or create context for a specific timestamp"""
        # Try to find existing context
        contexts = self._find_nodes("temporal_context")
        for ctx in contexts:
            if ctx.get("timestamp") == timestamp:
                return ctx

        # Create new context
        context_id = self.snapshot_context(timestamp)
        return self.get_context(context_id)

    # =========================================================================
    # Scheduled Changes
    # =========================================================================

    def schedule_change(
        self,
        change_type: str,
        target_id: str,
        scheduled_for: str,
        change_details: Optional[Dict[str, Any]] = None,
        schedule_id: Optional[str] = None
    ) -> str:
        """Schedule a governance change"""
        sid = schedule_id or self._generate_id("sc")
        props = {
            "type": change_type,  # "rule_update", "authority_exp", "review"
            "target_id": target_id,
            "scheduled_for": scheduled_for,
            "details": change_details or {},
            "status": "pending",
            "created_at": self._now()
        }
        return self._add_node("scheduled_change", sid, props)

    def get_scheduled_changes(
        self,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get scheduled changes"""
        changes = self._find_nodes("scheduled_change")
        if status:
            changes = [c for c in changes if c.get("status") == status]
        return sorted(changes, key=lambda c: c.get("scheduled_for", ""))

    def execute_scheduled_change(self, schedule_id: str):
        """Mark a scheduled change as executed"""
        self._update_node("scheduled_change", schedule_id, {
            "status": "executed",
            "executed_at": self._now()
        })

    def cancel_scheduled_change(self, schedule_id: str, reason: str):
        """Cancel a scheduled change"""
        self._update_node("scheduled_change", schedule_id, {
            "status": "cancelled",
            "cancelled_at": self._now(),
            "cancel_reason": reason
        })

    # =========================================================================
    # Authority Timeline
    # =========================================================================

    def record_authority_event(
        self,
        authority_id: str,
        event: str,
        actor: str
    ) -> str:
        """Record an event in authority timeline"""
        eid = self._generate_id("ae")
        props = {
            "authority_id": authority_id,
            "event": event,  # "granted", "used", "extended", "revoked"
            "actor": actor,
            "timestamp": self._now()
        }
        self._add_node("authority_event", eid, props)

        self._add_edge(
            "authority_event", eid,
            "AUTHORITY_TIMELINE",
            "temporal_authority", authority_id,
            {}
        )

        return eid

    def get_authority_timeline(self, authority_id: str) -> List[Dict[str, Any]]:
        """Get timeline of events for an authority"""
        events = self._find_nodes("authority_event", authority_id=authority_id)
        return sorted(events, key=lambda e: e.get("timestamp", ""))

    # =========================================================================
    # Historical Decision Context
    # =========================================================================

    def link_decision_to_context(
        self,
        decision_id: str,
        context_id: str
    ):
        """Link a decision to its temporal context"""
        self._add_edge(
            "decision", decision_id,
            "HISTORICAL_DECISION_CONTEXT",
            "temporal_context", context_id,
            {}
        )

    def get_decision_context(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get the temporal context for a historical decision"""
        edges = self._find_edges(
            source_type="decision", source_id=decision_id,
            rel_type="HISTORICAL_DECISION_CONTEXT"
        )
        if edges:
            return self.get_context(edges[0]["target"][1])
        return None

    # =========================================================================
    # Retroactive Audit
    # =========================================================================

    def retroactive_audit(
        self,
        target_id: str,
        audit_period: str,
        findings: List[str]
    ) -> str:
        """Record a retroactive audit"""
        aid = self._generate_id("ra")
        props = {
            "target_id": target_id,
            "audit_period": audit_period,
            "findings": findings,
            "completed_at": self._now()
        }
        return self._add_node("retroactive_audit", aid, props)

    def get_stats(self) -> Dict[str, Any]:
        """Get temporal store statistics"""
        base_stats = super().get_stats()
        authorities = self._find_nodes("temporal_authority")
        versions = self._find_nodes("rule_version")
        contexts = self._find_nodes("temporal_context")
        scheduled = self._find_nodes("scheduled_change")

        return {
            **base_stats,
            "temporal_authorities": len(authorities),
            "active_authorities": len([a for a in authorities if a.get("status") == "active"]),
            "rule_versions": len(versions),
            "context_snapshots": len(contexts),
            "scheduled_changes": len(scheduled),
            "pending_changes": len([s for s in scheduled if s.get("status") == "pending"])
        }
