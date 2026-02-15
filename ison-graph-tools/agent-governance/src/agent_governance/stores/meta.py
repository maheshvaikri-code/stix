"""
Meta-Governance Store
=====================

Governance of governance itself - rules about rules, change management, audits.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import GovernanceRule, GovernanceChange, GovernanceReview, GovernanceAuthority

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class MetaGovernanceStore(BaseStore):
    """Store for meta-governance (governing the governance)"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "meta")

    # =========================================================================
    # Governance Rules
    # =========================================================================

    def add_governance_rule(
        self,
        domain: str,
        rule: str,
        description: str = "",
        rule_id: Optional[str] = None
    ) -> str:
        """Add a governance rule"""
        gid = rule_id or self._generate_id("gr")
        props = {
            "domain": domain,
            "rule": rule,
            "version": "v1",
            "effective_date": self._now(),
            "description": description,
            "active": True
        }
        return self._add_node("governance_rule", gid, props)

    def get_governance_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get governance rule by ID"""
        return self._get_node("governance_rule", rule_id)

    def list_governance_rules(self, domain: Optional[str] = None) -> List[Dict[str, Any]]:
        """List governance rules"""
        rules = self._find_nodes("governance_rule")
        if domain:
            rules = [r for r in rules if r.get("domain") == domain]
        return [r for r in rules if r.get("active")]

    def update_governance_rule(
        self,
        rule_id: str,
        new_rule: str,
        rationale: str
    ):
        """Update a governance rule"""
        current = self.get_governance_rule(rule_id)
        if not current:
            return

        # Increment version
        version = current.get("version", "v1")
        version_num = int(version[1:]) + 1 if version.startswith("v") else 2
        new_version = f"v{version_num}"

        self._update_node("governance_rule", rule_id, {
            "rule": new_rule,
            "version": new_version,
            "updated_at": self._now(),
            "update_rationale": rationale
        })

    # =========================================================================
    # Governance Changes
    # =========================================================================

    def propose_change(
        self,
        rule_id: str,
        change_type: str,
        proposed_by: str,
        rationale: str,
        change_id: Optional[str] = None
    ) -> str:
        """Propose a governance change"""
        cid = change_id or self._generate_id("gc")
        props = {
            "rule_id": rule_id,
            "change_type": change_type,  # "amendment", "threshold", "new_level"
            "proposed_by": proposed_by,
            "rationale": rationale,
            "status": "pending",
            "proposed_at": self._now()
        }
        self._add_node("governance_change", cid, props)

        self._add_edge(
            "governance_change", cid,
            "GOVERNANCE_CHANGE",
            "governance_rule", rule_id,
            {}
        )

        return cid

    def review_change(
        self,
        change_id: str,
        reviewer: str,
        decision: str,
        comments: str = ""
    ):
        """Review a governance change"""
        self._update_node("governance_change", change_id, {
            "status": decision,  # "approved", "rejected"
            "reviewed_by": reviewer,
            "reviewed_at": self._now(),
            "review_comments": comments
        })

        # If approved, apply the change
        if decision == "approved":
            change = self._get_node("governance_change", change_id)
            if change:
                self._update_node("governance_rule", change.get("rule_id"), {
                    "last_change_id": change_id
                })

    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """Get all pending governance changes"""
        changes = self._find_nodes("governance_change", status="pending")
        return changes

    # =========================================================================
    # Governance Authority
    # =========================================================================

    def add_governance_authority(
        self,
        name: str,
        scope: str,
        members: List[str],
        decision_process: str = "",
        authority_id: Optional[str] = None
    ) -> str:
        """Add a governance authority body"""
        aid = authority_id or self._generate_id("ga")
        props = {
            "name": name,
            "scope": scope,  # "all_rules", "security_rules", etc.
            "members": members,
            "decision_process": decision_process
        }
        return self._add_node("governance_authority", aid, props)

    def get_governance_authority(self, authority_id: str) -> Optional[Dict[str, Any]]:
        """Get governance authority by ID"""
        return self._get_node("governance_authority", authority_id)

    def list_governance_authorities(self) -> List[Dict[str, Any]]:
        """List all governance authorities"""
        return self._find_nodes("governance_authority")

    def set_rule_authority(
        self,
        authority_id: str,
        rule_id: str,
        authority_type: str,
        change_requires: str
    ):
        """Set which authority governs a rule"""
        self._add_edge(
            "governance_authority", authority_id,
            "RULE_AUTHORITY",
            "governance_rule", rule_id,
            {"authority_type": authority_type, "change_requires": change_requires}
        )

    def get_rule_authority(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get the authority for a rule"""
        edges = self._find_edges(
            rel_type="RULE_AUTHORITY",
            target_type="governance_rule", target_id=rule_id
        )
        if edges:
            authority = self.get_governance_authority(edges[0]["source"][1])
            return {
                "authority": authority,
                "authority_type": edges[0]["properties"].get("authority_type"),
                "change_requires": edges[0]["properties"].get("change_requires")
            }
        return None

    # =========================================================================
    # Governance Reviews
    # =========================================================================

    def schedule_review(
        self,
        review_type: str,
        frequency: str,
        next_review: str,
        review_id: Optional[str] = None
    ) -> str:
        """Schedule a governance review"""
        rid = review_id or self._generate_id("rv")
        props = {
            "type": review_type,
            "frequency": frequency,
            "last_review": None,
            "next_review": next_review,
            "findings": []
        }
        return self._add_node("governance_review", rid, props)

    def complete_review(
        self,
        review_id: str,
        findings: List[str],
        compliance_rate: float
    ):
        """Complete a governance review"""
        review = self._get_node("governance_review", review_id)
        if not review:
            return

        self._update_node("governance_review", review_id, {
            "last_review": self._now(),
            "findings": findings,
            "compliance_rate": compliance_rate
        })

    def get_upcoming_reviews(self) -> List[Dict[str, Any]]:
        """Get upcoming governance reviews"""
        reviews = self._find_nodes("governance_review")
        return sorted(reviews, key=lambda r: r.get("next_review", ""))

    # =========================================================================
    # Governance Metrics
    # =========================================================================

    def record_governance_metric(
        self,
        metric_name: str,
        current: float,
        target: float
    ) -> str:
        """Record a governance metric"""
        mid = self._generate_id("gm")
        props = {
            "name": metric_name,
            "current": current,
            "target": target,
            "trend": "stable",
            "recorded_at": self._now()
        }
        return self._add_node("governance_metric", mid, props)

    def get_governance_metrics(self) -> List[Dict[str, Any]]:
        """Get all governance metrics"""
        return self._find_nodes("governance_metric")

    # =========================================================================
    # Governance Exceptions
    # =========================================================================

    def grant_exception(
        self,
        rule_id: str,
        grantee: str,
        exception: str,
        granted_by: str,
        valid_until: str
    ) -> str:
        """Grant a governance exception"""
        eid = self._generate_id("ge")
        props = {
            "rule_id": rule_id,
            "grantee": grantee,
            "exception": exception,
            "granted_by": granted_by,
            "granted_at": self._now(),
            "valid_until": valid_until,
            "audit_required": True
        }
        self._add_node("governance_exception", eid, props)

        self._add_edge(
            "governance_exception", eid,
            "GOVERNANCE_EXCEPTION",
            "governance_rule", rule_id,
            {}
        )

        return eid

    def get_active_exceptions(self) -> List[Dict[str, Any]]:
        """Get all active governance exceptions"""
        exceptions = self._find_nodes("governance_exception")
        now = self._now()
        return [e for e in exceptions if e.get("valid_until", "") > now]

    # =========================================================================
    # Governance Audit
    # =========================================================================

    def record_audit(
        self,
        audit_type: str,
        auditor: str,
        findings: List[str],
        compliance_rate: float
    ) -> str:
        """Record a governance audit"""
        aid = self._generate_id("aud")
        props = {
            "type": audit_type,  # "internal", "external"
            "auditor": auditor,
            "findings": findings,
            "compliance_rate": compliance_rate,
            "completed_at": self._now()
        }
        return self._add_node("governance_audit", aid, props)

    def get_audits(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent governance audits"""
        audits = self._find_nodes("governance_audit")
        return sorted(audits, key=lambda a: a.get("completed_at", ""), reverse=True)[:limit]

    # =========================================================================
    # Governance Improvement
    # =========================================================================

    def propose_improvement(
        self,
        source: str,
        target_rule_id: str,
        improvement: str,
        status: str = "researching"
    ) -> str:
        """Propose a governance improvement"""
        iid = self._generate_id("gi")
        props = {
            "source": source,
            "target_rule_id": target_rule_id,
            "improvement": improvement,
            "status": status,  # "researching", "implementing", "completed"
            "proposed_at": self._now()
        }
        return self._add_node("governance_improvement", iid, props)

    def get_improvements(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get governance improvements"""
        improvements = self._find_nodes("governance_improvement")
        if status:
            improvements = [i for i in improvements if i.get("status") == status]
        return improvements

    def get_stats(self) -> Dict[str, Any]:
        """Get meta-governance store statistics"""
        base_stats = super().get_stats()
        rules = self._find_nodes("governance_rule")
        changes = self._find_nodes("governance_change")
        authorities = self._find_nodes("governance_authority")
        reviews = self._find_nodes("governance_review")

        return {
            **base_stats,
            "governance_rules": len(rules),
            "active_rules": len([r for r in rules if r.get("active")]),
            "pending_changes": len([c for c in changes if c.get("status") == "pending"]),
            "authorities": len(authorities),
            "scheduled_reviews": len(reviews)
        }
