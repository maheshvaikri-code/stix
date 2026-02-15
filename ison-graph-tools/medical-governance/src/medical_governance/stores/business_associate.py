"""
Business Associate Store
========================

Manages business associate agreements, compliance monitoring, and data flows per HIPAA 45 CFR 164.308(b).
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import BAType, BAAStatus, RiskTier

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class BusinessAssociateStore(BaseStore):
    """Store for business associate governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "business_associate")

    # =========================================================================
    # Business Associate Management
    # =========================================================================

    def add_business_associate(
        self,
        name: str,
        ba_type: BAType,
        service: str,
        risk_tier: RiskTier,
        contact_email: str = "",
        contact_phone: str = "",
        ba_id: Optional[str] = None
    ) -> str:
        """Add a business associate"""
        bid = ba_id or self._generate_id("ba")
        props = {
            "name": name,
            "ba_type": ba_type.value,
            "service": service,
            "risk_tier": risk_tier.value,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            "active": True,
            "description": f"Business associate: {name}"
        }
        return self._add_node("business_associate", bid, props)

    def get_business_associate(self, ba_id: str) -> Optional[Dict[str, Any]]:
        """Get business associate by ID"""
        return self._get_node("business_associate", ba_id)

    def list_business_associates(
        self,
        ba_type: Optional[BAType] = None,
        risk_tier: Optional[RiskTier] = None
    ) -> List[Dict[str, Any]]:
        """List business associates with optional filters"""
        bas = self._find_nodes("business_associate", active=True)

        if ba_type:
            bas = [b for b in bas if b.get("ba_type") == ba_type.value]
        if risk_tier:
            bas = [b for b in bas if b.get("risk_tier") == risk_tier.value]

        return bas

    # =========================================================================
    # BAA Management
    # =========================================================================

    def add_baa(
        self,
        ba_id: str,
        effective_date: str,
        expiration_date: Optional[str],
        version: str,
        phi_scope: List[str],
        baa_id: Optional[str] = None
    ) -> str:
        """Add a business associate agreement"""
        bid = baa_id or self._generate_id("baa")
        props = {
            "ba_id": ba_id,
            "effective_date": effective_date,
            "expiration_date": expiration_date,
            "version": version,
            "phi_scope": phi_scope,
            "status": BAAStatus.ACTIVE.value,
            "description": f"BAA for {ba_id}"
        }
        self._add_node("baa_agreement", bid, props)

        # Link BAA to BA
        self._add_edge(
            "business_associate", ba_id,
            "HAS_BAA",
            "baa_agreement", bid,
            {}
        )

        return bid

    def get_baa(self, baa_id: str) -> Optional[Dict[str, Any]]:
        """Get BAA by ID"""
        return self._get_node("baa_agreement", baa_id)

    def get_active_baa(self, ba_id: str) -> Optional[Dict[str, Any]]:
        """Get active BAA for a business associate"""
        baas = self._find_nodes(
            "baa_agreement",
            ba_id=ba_id,
            status=BAAStatus.ACTIVE.value
        )
        return baas[0] if baas else None

    def update_baa_status(self, baa_id: str, status: BAAStatus):
        """Update BAA status"""
        self._update_node("baa_agreement", baa_id, {
            "status": status.value
        })

    def check_baa_expiration(self) -> List[Dict[str, Any]]:
        """Check for expiring BAAs"""
        from datetime import datetime, timedelta

        warning_date = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) +
            timedelta(days=90)
        ).isoformat()

        baas = self._find_nodes("baa_agreement", status=BAAStatus.ACTIVE.value)

        expiring = []
        expired = []

        for baa in baas:
            exp = baa.get("expiration_date")
            if exp:
                if exp < self._now():
                    expired.append(baa)
                    self.update_baa_status(baa["id"], BAAStatus.EXPIRED)
                elif exp < warning_date:
                    expiring.append(baa)

        return {
            "expired": expired,
            "expiring_90_days": expiring
        }

    # =========================================================================
    # BAA Provisions
    # =========================================================================

    def add_baa_provision(
        self,
        baa_id: str,
        provision_type: str,
        requirement: str,
        compliance_method: str
    ) -> str:
        """Add a provision to a BAA"""
        pid = self._generate_id("bp")
        props = {
            "baa_id": baa_id,
            "provision_type": provision_type,
            "requirement": requirement,
            "compliance_method": compliance_method,
            "description": f"BAA provision: {provision_type}"
        }
        return self._add_node("baa_provision", pid, props)

    def get_baa_provisions(self, baa_id: str) -> List[Dict[str, Any]]:
        """Get provisions for a BAA"""
        return self._find_nodes("baa_provision", baa_id=baa_id)

    # =========================================================================
    # Data Flow Management
    # =========================================================================

    def add_data_flow(
        self,
        ba_id: str,
        direction: str,  # inbound, outbound, bidirectional
        phi_categories: List[str],
        volume: str,
        frequency: str,
        encryption_required: bool = True
    ) -> str:
        """Add a data flow definition"""
        dfid = self._generate_id("df")
        props = {
            "ba_id": ba_id,
            "direction": direction,
            "phi_categories": phi_categories,
            "volume": volume,
            "frequency": frequency,
            "encryption_required": encryption_required,
            "active": True,
            "description": f"Data flow: {direction}"
        }
        self._add_node("ba_data_flow", dfid, props)

        # Link to BA
        self._add_edge(
            "business_associate", ba_id,
            "HAS_DATA_FLOW",
            "ba_data_flow", dfid,
            {}
        )

        return dfid

    def get_data_flows(self, ba_id: str) -> List[Dict[str, Any]]:
        """Get data flows for a business associate"""
        return self._find_nodes("ba_data_flow", ba_id=ba_id, active=True)

    # =========================================================================
    # Compliance Assessment
    # =========================================================================

    def add_compliance_assessment(
        self,
        ba_id: str,
        assessor: str,
        score: float,
        findings: List[str]
    ) -> str:
        """Add a compliance assessment"""
        caid = self._generate_id("ca")
        props = {
            "ba_id": ba_id,
            "assessment_date": self._now(),
            "assessor": assessor,
            "score": score,
            "findings": findings,
            "description": f"Compliance assessment for {ba_id}"
        }
        self._add_node("ba_compliance_assessment", caid, props)

        return caid

    def get_latest_assessment(self, ba_id: str) -> Optional[Dict[str, Any]]:
        """Get latest compliance assessment"""
        assessments = self._find_nodes("ba_compliance_assessment", ba_id=ba_id)
        if assessments:
            return sorted(
                assessments,
                key=lambda a: a.get("assessment_date", ""),
                reverse=True
            )[0]
        return None

    # =========================================================================
    # Incident Management
    # =========================================================================

    def add_ba_incident(
        self,
        ba_id: str,
        incident_type: str,
        phi_affected: int,
        description: str
    ) -> str:
        """Add a BA incident"""
        iid = self._generate_id("bi")
        props = {
            "ba_id": ba_id,
            "incident_date": self._now(),
            "incident_type": incident_type,
            "phi_affected": phi_affected,
            "status": "open",
            "description": description
        }
        self._add_node("ba_incident", iid, props)

        return iid

    def resolve_ba_incident(self, incident_id: str, resolution: str):
        """Resolve a BA incident"""
        self._update_node("ba_incident", incident_id, {
            "status": "resolved",
            "resolved_at": self._now(),
            "resolution": resolution
        })

    def get_ba_incidents(
        self,
        ba_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get BA incidents"""
        incidents = self._find_nodes("ba_incident")

        if ba_id:
            incidents = [i for i in incidents if i.get("ba_id") == ba_id]
        if status:
            incidents = [i for i in incidents if i.get("status") == status]

        return incidents

    # =========================================================================
    # Subcontractor Management
    # =========================================================================

    def add_subcontractor(
        self,
        ba_id: str,
        subcontractor_name: str,
        sub_baa_status: str  # active, pending, none
    ) -> str:
        """Add a subcontractor to a BA"""
        sid = self._generate_id("sub")
        props = {
            "ba_id": ba_id,
            "subcontractor_name": subcontractor_name,
            "sub_baa_status": sub_baa_status,
            "added_at": self._now(),
            "description": f"Subcontractor: {subcontractor_name}"
        }
        self._add_node("ba_subcontractor", sid, props)

        # Link to parent BA
        self._add_edge(
            "business_associate", ba_id,
            "HAS_SUBCONTRACTOR",
            "ba_subcontractor", sid,
            {}
        )

        return sid

    def get_subcontractors(self, ba_id: str) -> List[Dict[str, Any]]:
        """Get subcontractors for a BA"""
        return self._find_nodes("ba_subcontractor", ba_id=ba_id)

    def check_subcontractor_compliance(self, ba_id: str) -> Dict[str, Any]:
        """Check subcontractor BAA compliance"""
        subs = self.get_subcontractors(ba_id)

        compliant = [s for s in subs if s.get("sub_baa_status") == "active"]
        non_compliant = [s for s in subs if s.get("sub_baa_status") != "active"]

        return {
            "total_subcontractors": len(subs),
            "compliant": len(compliant),
            "non_compliant": len(non_compliant),
            "non_compliant_list": [s.get("subcontractor_name") for s in non_compliant]
        }

    # =========================================================================
    # Risk Monitoring
    # =========================================================================

    def add_risk_metric(
        self,
        ba_id: str,
        metric_name: str,
        current_value: Any,
        threshold: Any,
        alert: bool = False
    ):
        """Add a risk monitoring metric"""
        mid = self._generate_id("rm")
        props = {
            "ba_id": ba_id,
            "metric_name": metric_name,
            "current_value": str(current_value),
            "threshold": str(threshold),
            "alert": alert,
            "recorded_at": self._now(),
            "description": f"Risk metric: {metric_name}"
        }
        self._add_node("ba_risk_metric", mid, props)

    def get_risk_alerts(self) -> List[Dict[str, Any]]:
        """Get BA risk alerts"""
        metrics = self._find_nodes("ba_risk_metric", alert=True)
        return metrics

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get business associate statistics"""
        base_stats = super().get_stats()
        bas = self._find_nodes("business_associate")
        baas = self._find_nodes("baa_agreement")
        incidents = self._find_nodes("ba_incident")
        assessments = self._find_nodes("ba_compliance_assessment")

        active_bas = len([b for b in bas if b.get("active")])
        active_baas = len([b for b in baas if b.get("status") == BAAStatus.ACTIVE.value])
        open_incidents = len([i for i in incidents if i.get("status") == "open"])

        # Risk tier distribution
        by_risk = {}
        for ba in bas:
            tier = ba.get("risk_tier", "unknown")
            by_risk[tier] = by_risk.get(tier, 0) + 1

        return {
            **base_stats,
            "business_associates": len(bas),
            "active_bas": active_bas,
            "baa_agreements": len(baas),
            "active_baas": active_baas,
            "incidents": len(incidents),
            "open_incidents": open_incidents,
            "assessments": len(assessments),
            "by_risk_tier": by_risk
        }
