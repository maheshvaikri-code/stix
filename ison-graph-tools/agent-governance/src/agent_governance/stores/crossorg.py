"""
Cross-Organizational Governance Store
=====================================

Manages trust relationships, agreements, and cross-org policies.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import TrustLevel, Organization, ExternalAgent, TrustAgreement

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class CrossOrgStore(BaseStore):
    """Store for cross-organizational governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "crossorg")

    # =========================================================================
    # Organization Management
    # =========================================================================

    def add_organization(
        self,
        name: str,
        trust_level: TrustLevel,
        jurisdiction: str,
        agreement_status: str = "none",
        org_id: Optional[str] = None
    ) -> str:
        """Add an organization"""
        oid = org_id or self._generate_id("o")
        props = {
            "name": name,
            "trust_level": trust_level.value,
            "jurisdiction": jurisdiction,
            "agreement_status": agreement_status
        }
        return self._add_node("organization", oid, props)

    def get_organization(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get organization by ID"""
        return self._get_node("organization", org_id)

    def list_organizations(
        self,
        trust_level: Optional[TrustLevel] = None
    ) -> List[Dict[str, Any]]:
        """List organizations"""
        orgs = self._find_nodes("organization")
        if trust_level:
            orgs = [o for o in orgs if o.get("trust_level") == trust_level.value]
        return orgs

    def update_trust_level(self, org_id: str, trust_level: TrustLevel):
        """Update organization trust level"""
        self._update_node("organization", org_id, {
            "trust_level": trust_level.value,
            "trust_updated_at": self._now()
        })

    # =========================================================================
    # External Agents
    # =========================================================================

    def add_external_agent(
        self,
        org_id: str,
        name: str,
        capabilities: List[str],
        certified: bool = False,
        agent_id: Optional[str] = None
    ) -> str:
        """Add an external agent"""
        aid = agent_id or self._generate_id("ea")
        props = {
            "org_id": org_id,
            "name": name,
            "capabilities": capabilities,
            "certified": certified
        }
        return self._add_node("external_agent", aid, props)

    def get_external_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get external agent by ID"""
        return self._get_node("external_agent", agent_id)

    def list_external_agents(self, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List external agents"""
        agents = self._find_nodes("external_agent")
        if org_id:
            agents = [a for a in agents if a.get("org_id") == org_id]
        return agents

    def certify_agent(self, agent_id: str, certifier: str):
        """Certify an external agent"""
        self._update_node("external_agent", agent_id, {
            "certified": True,
            "certified_by": certifier,
            "certified_at": self._now()
        })

    # =========================================================================
    # Trust Agreements
    # =========================================================================

    def create_agreement(
        self,
        org_a: str,
        org_b: str,
        agreement_type: str,
        expires_date: str,
        terms: Optional[Dict[str, Any]] = None,
        agreement_id: Optional[str] = None
    ) -> str:
        """Create a trust agreement"""
        aid = agreement_id or self._generate_id("ta")
        props = {
            "org_a": org_a,
            "org_b": org_b,
            "type": agreement_type,  # "data_processing", "service_level", "nda"
            "signed_date": self._now(),
            "expires_date": expires_date,
            "terms": terms or {},
            "status": "active"
        }
        self._add_node("trust_agreement", aid, props)

        self._add_edge(
            "trust_agreement", aid,
            "AGREEMENT_BETWEEN",
            "organization", org_a,
            {}
        )
        self._add_edge(
            "trust_agreement", aid,
            "AGREEMENT_BETWEEN",
            "organization", org_b,
            {}
        )

        # Update org agreement status
        self._update_node("organization", org_a, {"agreement_status": "active"})
        self._update_node("organization", org_b, {"agreement_status": "active"})

        return aid

    def get_agreement(self, agreement_id: str) -> Optional[Dict[str, Any]]:
        """Get agreement by ID"""
        return self._get_node("trust_agreement", agreement_id)

    def get_agreements_for_org(self, org_id: str) -> List[Dict[str, Any]]:
        """Get all agreements for an organization"""
        agreements = self._find_nodes("trust_agreement")
        return [a for a in agreements if a.get("org_a") == org_id or a.get("org_b") == org_id]

    def terminate_agreement(self, agreement_id: str, reason: str):
        """Terminate an agreement"""
        self._update_node("trust_agreement", agreement_id, {
            "status": "terminated",
            "terminated_at": self._now(),
            "termination_reason": reason
        })

    # =========================================================================
    # Trust Relationships
    # =========================================================================

    def set_trust_relationship(
        self,
        from_org: str,
        to_org: str,
        trust_score: float,
        basis: str
    ):
        """Set trust relationship between organizations"""
        self._add_edge(
            "organization", from_org,
            "TRUST_RELATIONSHIP",
            "organization", to_org,
            {
                "trust_score": trust_score,
                "basis": basis,
                "last_verified": self._now()
            }
        )

    def get_trust_score(self, from_org: str, to_org: str) -> Optional[float]:
        """Get trust score between organizations"""
        edges = self._find_edges(
            source_type="organization", source_id=from_org,
            rel_type="TRUST_RELATIONSHIP",
            target_type="organization", target_id=to_org
        )
        return edges[0]["properties"].get("trust_score") if edges else None

    # =========================================================================
    # Cross-Org Policies
    # =========================================================================

    def add_cross_org_policy(
        self,
        organizations: List[str],
        policy: str,
        enforcement: str,
        policy_id: Optional[str] = None
    ) -> str:
        """Add a cross-organizational policy"""
        pid = policy_id or self._generate_id("cop")
        props = {
            "organizations": organizations,
            "policy": policy,
            "enforcement": enforcement,  # "both_sides", "our_side", "hard_block"
            "active": True
        }
        return self._add_node("cross_org_policy", pid, props)

    def list_cross_org_policies(self, org_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List cross-org policies"""
        policies = self._find_nodes("cross_org_policy")
        if org_id:
            policies = [p for p in policies if org_id in p.get("organizations", [])]
        return [p for p in policies if p.get("active")]

    # =========================================================================
    # Agent Interaction Rules
    # =========================================================================

    def set_interaction_rules(
        self,
        our_agent: str,
        external_agent: str,
        interaction_type: str,
        data_allowed: List[str],
        requires: str
    ):
        """Set rules for agent-to-agent interaction"""
        self._add_edge(
            "principal", our_agent,
            "AGENT_INTERACTION_ALLOWED",
            "external_agent", external_agent,
            {
                "interaction_type": interaction_type,
                "data_allowed": data_allowed,
                "requires": requires
            }
        )

    def check_interaction_allowed(
        self,
        our_agent: str,
        external_agent: str,
        data_classification: str
    ) -> Dict[str, Any]:
        """Check if interaction is allowed"""
        edges = self._find_edges(
            source_type="principal", source_id=our_agent,
            rel_type="AGENT_INTERACTION_ALLOWED",
            target_type="external_agent", target_id=external_agent
        )

        if not edges:
            return {"allowed": False, "reason": "No interaction rules defined"}

        rules = edges[0]["properties"]
        allowed_data = rules.get("data_allowed", [])

        if data_classification not in allowed_data:
            return {
                "allowed": False,
                "reason": f"Data classification {data_classification} not allowed",
                "allowed_classifications": allowed_data
            }

        return {
            "allowed": True,
            "interaction_type": rules.get("interaction_type"),
            "requires": rules.get("requires")
        }

    # =========================================================================
    # Liability Boundaries
    # =========================================================================

    def set_liability_boundary(
        self,
        agreement_id: str,
        our_liability: str,
        their_liability: str,
        dispute_resolution: str
    ):
        """Set liability boundaries for an agreement"""
        self._update_node("trust_agreement", agreement_id, {
            "our_liability": our_liability,
            "their_liability": their_liability,
            "dispute_resolution": dispute_resolution
        })

    # =========================================================================
    # Cross-Org Incidents
    # =========================================================================

    def record_cross_org_incident(
        self,
        organizations: List[str],
        incident_type: str,
        notification_required: str,
        sla: str
    ) -> str:
        """Record a cross-org incident requirement"""
        iid = self._generate_id("coi")
        props = {
            "organizations": organizations,
            "incident_type": incident_type,
            "notification_required": notification_required,
            "sla": sla,
            "created_at": self._now()
        }
        return self._add_node("cross_org_incident", iid, props)

    # =========================================================================
    # Compliance Verification
    # =========================================================================

    def verify_cross_org_compliance(
        self,
        agreement_id: str,
        requirement: str,
        verified: bool,
        gap: Optional[str] = None
    ) -> str:
        """Verify compliance for a cross-org agreement"""
        vid = self._generate_id("cov")
        props = {
            "agreement_id": agreement_id,
            "requirement": requirement,
            "verified": verified,
            "gap": gap,
            "verified_at": self._now()
        }
        self._add_node("cross_org_compliance", vid, props)

        self._add_edge(
            "cross_org_compliance", vid,
            "COMPLIANCE_REQUIREMENT_CROSS_ORG",
            "trust_agreement", agreement_id,
            {}
        )

        return vid

    def get_compliance_status(self, agreement_id: str) -> Dict[str, Any]:
        """Get compliance status for an agreement"""
        verifications = self._find_nodes("cross_org_compliance", agreement_id=agreement_id)

        verified = len([v for v in verifications if v.get("verified")])
        gaps = [v.get("gap") for v in verifications if v.get("gap")]

        return {
            "agreement_id": agreement_id,
            "total_requirements": len(verifications),
            "verified": verified,
            "gaps": gaps,
            "compliant": len(gaps) == 0
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get cross-org store statistics"""
        base_stats = super().get_stats()
        orgs = self._find_nodes("organization")
        agents = self._find_nodes("external_agent")
        agreements = self._find_nodes("trust_agreement")
        policies = self._find_nodes("cross_org_policy")

        return {
            **base_stats,
            "organizations": len(orgs),
            "external_agents": len(agents),
            "certified_agents": len([a for a in agents if a.get("certified")]),
            "agreements": len(agreements),
            "active_agreements": len([a for a in agreements if a.get("status") == "active"]),
            "cross_org_policies": len(policies)
        }
