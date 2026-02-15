"""
Risk Assessment Store
=====================

Manages risks, threats, controls, and risk incidents.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import RiskLevel, ControlType, Risk, Threat, RiskControl, RiskIncident

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class RiskStore(BaseStore):
    """Store for risk assessment and mitigation"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "risk")

    # =========================================================================
    # Risk Management
    # =========================================================================

    def add_risk(
        self,
        category: str,
        name: str,
        inherent_score: float,
        appetite_threshold: float,
        description: str = "",
        risk_id: Optional[str] = None
    ) -> str:
        """Add a risk to track"""
        rid = risk_id or self._generate_id("rk")
        props = {
            "category": category,
            "name": name,
            "inherent_score": inherent_score,
            "residual_score": inherent_score,  # Initially same as inherent
            "appetite_threshold": appetite_threshold,
            "description": description
        }
        return self._add_node("risk", rid, props)

    def update_residual_score(self, risk_id: str, residual_score: float):
        """Update the residual risk score after controls"""
        self._update_node("risk", risk_id, {"residual_score": residual_score})

    def get_risk(self, risk_id: str) -> Optional[Dict[str, Any]]:
        """Get risk by ID"""
        return self._get_node("risk", risk_id)

    def list_risks(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all risks"""
        risks = self._find_nodes("risk")
        if category:
            risks = [r for r in risks if r.get("category") == category]
        return risks

    # =========================================================================
    # Threat Management
    # =========================================================================

    def add_threat(
        self,
        name: str,
        likelihood: str,
        impact: str,
        risks_affected: List[str],
        description: str = "",
        threat_id: Optional[str] = None
    ) -> str:
        """Add a threat"""
        tid = threat_id or self._generate_id("th")
        props = {
            "name": name,
            "likelihood": likelihood,
            "impact": impact,
            "risks_affected": risks_affected,
            "description": description
        }
        self._add_node("threat", tid, props)

        # Link to affected risks
        for risk_id in risks_affected:
            self._add_edge(
                "threat", tid,
                "THREAT_TO",
                "risk", risk_id,
                {}
            )

        return tid

    def get_threat(self, threat_id: str) -> Optional[Dict[str, Any]]:
        """Get threat by ID"""
        return self._get_node("threat", threat_id)

    def list_threats(self, likelihood: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all threats"""
        threats = self._find_nodes("threat")
        if likelihood:
            threats = [t for t in threats if t.get("likelihood") == likelihood]
        return threats

    # =========================================================================
    # Control Management
    # =========================================================================

    def add_control(
        self,
        name: str,
        control_type: ControlType,
        effectiveness: float,
        cost: str,
        threats_mitigated: List[str],
        control_id: Optional[str] = None
    ) -> str:
        """Add a risk control"""
        cid = control_id or self._generate_id("cl")
        props = {
            "name": name,
            "type": control_type.value,
            "effectiveness": effectiveness,
            "cost": cost,
            "threats_mitigated": threats_mitigated,
            "active": True
        }
        self._add_node("risk_control", cid, props)

        # Link to mitigated threats
        for threat_id in threats_mitigated:
            self._add_edge(
                "risk_control", cid,
                "MITIGATES",
                "threat", threat_id,
                {"effectiveness": effectiveness}
            )

        return cid

    def get_control(self, control_id: str) -> Optional[Dict[str, Any]]:
        """Get control by ID"""
        return self._get_node("risk_control", control_id)

    def list_controls(self, control_type: Optional[ControlType] = None) -> List[Dict[str, Any]]:
        """List all controls"""
        controls = self._find_nodes("risk_control")
        if control_type:
            controls = [c for c in controls if c.get("type") == control_type.value]
        return controls

    # =========================================================================
    # Risk Reduction Tracking
    # =========================================================================

    def record_risk_reduction(
        self,
        risk_id: str,
        control_ids: List[str],
        before_score: float,
        after_score: float,
        confidence: float
    ):
        """Record risk reduction from controls"""
        self._add_edge(
            "risk", risk_id,
            "RISK_REDUCED_BY",
            "risk", risk_id,  # Self-edge with metadata
            {
                "controls": control_ids,
                "before": before_score,
                "after": after_score,
                "confidence": confidence,
                "recorded_at": self._now()
            }
        )

        # Update residual score
        self.update_residual_score(risk_id, after_score)

    # =========================================================================
    # Risk Assessment
    # =========================================================================

    def assess_risk(self, risk_id: str) -> Dict[str, Any]:
        """Perform risk assessment"""
        risk = self.get_risk(risk_id)
        if not risk:
            return {"error": "Risk not found"}

        # Find threats affecting this risk
        threat_edges = self._find_edges(
            rel_type="THREAT_TO",
            target_type="risk", target_id=risk_id
        )

        threats = []
        for edge in threat_edges:
            threat = self.get_threat(edge["source"][1])
            if threat:
                # Find controls mitigating this threat
                control_edges = self._find_edges(
                    rel_type="MITIGATES",
                    target_type="threat", target_id=edge["source"][1]
                )
                controls = [self.get_control(e["source"][1]) for e in control_edges]
                controls = [c for c in controls if c]

                total_effectiveness = sum(c.get("effectiveness", 0) for c in controls)
                total_effectiveness = min(total_effectiveness, 0.95)  # Cap at 95%

                threats.append({
                    "threat_id": edge["source"][1],
                    "name": threat.get("name"),
                    "likelihood": threat.get("likelihood"),
                    "impact": threat.get("impact"),
                    "controls": len(controls),
                    "mitigation_effectiveness": total_effectiveness
                })

        # Calculate residual score (convert to float - may be stored as strings)
        inherent = float(risk.get("inherent_score", 0))
        if threats:
            avg_mitigation = sum(t["mitigation_effectiveness"] for t in threats) / len(threats)
            residual = inherent * (1 - avg_mitigation)
        else:
            residual = inherent

        appetite = float(risk.get("appetite_threshold", 0.5))
        within_appetite = residual <= appetite

        return {
            "risk_id": risk_id,
            "name": risk.get("name"),
            "category": risk.get("category"),
            "inherent_score": inherent,
            "residual_score": residual,
            "appetite_threshold": appetite,
            "within_appetite": within_appetite,
            "threats": threats,
            "risk_level": self._score_to_level(residual),
            "assessed_at": self._now()
        }

    def _score_to_level(self, score: float) -> str:
        """Convert risk score to level"""
        if score >= 0.8:
            return "critical"
        elif score >= 0.6:
            return "high"
        elif score >= 0.4:
            return "medium"
        return "low"

    # =========================================================================
    # Risk Incidents
    # =========================================================================

    def record_incident(
        self,
        risk_id: str,
        threat_id: str,
        severity: str,
        root_cause: str = "",
        incident_id: Optional[str] = None
    ) -> str:
        """Record a risk incident"""
        iid = incident_id or self._generate_id("in")
        props = {
            "risk_id": risk_id,
            "threat_id": threat_id,
            "severity": severity,
            "root_cause": root_cause,
            "timestamp": self._now(),
            "resolved": False
        }
        self._add_node("risk_incident", iid, props)

        self._add_edge(
            "risk_incident", iid,
            "INCIDENT_FOR",
            "risk", risk_id,
            {}
        )

        return iid

    def resolve_incident(
        self,
        incident_id: str,
        resolution: str,
        lessons_learned: str = ""
    ):
        """Resolve a risk incident"""
        self._update_node("risk_incident", incident_id, {
            "resolved": True,
            "resolved_at": self._now(),
            "resolution": resolution,
            "lessons_learned": lessons_learned
        })

    def get_incidents(
        self,
        risk_id: Optional[str] = None,
        resolved: Optional[bool] = None
    ) -> List[Dict[str, Any]]:
        """Get risk incidents"""
        incidents = self._find_nodes("risk_incident")

        if risk_id:
            incidents = [i for i in incidents if i.get("risk_id") == risk_id]
        if resolved is not None:
            incidents = [i for i in incidents if i.get("resolved") == resolved]

        return incidents

    # =========================================================================
    # Risk Trending
    # =========================================================================

    def record_risk_trend(
        self,
        risk_id: str,
        period: str,
        direction: str,
        driver: str
    ):
        """Record risk trend"""
        self._add_node("risk_trend", self._generate_id("rt"), {
            "risk_id": risk_id,
            "period": period,
            "direction": direction,  # "increasing", "decreasing", "stable"
            "driver": driver,
            "recorded_at": self._now()
        })

    def get_risk_trends(self, risk_id: str) -> List[Dict[str, Any]]:
        """Get trend history for a risk"""
        trends = self._find_nodes("risk_trend", risk_id=risk_id)
        return sorted(trends, key=lambda t: t.get("recorded_at", ""), reverse=True)

    # =========================================================================
    # Risk Appetite
    # =========================================================================

    def set_risk_appetite(
        self,
        risk_id: str,
        threshold: float,
        breach_action: str
    ):
        """Set risk appetite boundary"""
        self._add_edge(
            "risk", risk_id,
            "RISK_APPETITE_BOUNDARY",
            "risk", risk_id,
            {"threshold": threshold, "breach_action": breach_action}
        )

    def check_appetite_breach(self, risk_id: str) -> Dict[str, Any]:
        """Check if risk is within appetite"""
        risk = self.get_risk(risk_id)
        if not risk:
            return {"error": "Risk not found"}

        residual = risk.get("residual_score", 0)
        appetite = risk.get("appetite_threshold", 0.5)

        breached = residual > appetite

        return {
            "risk_id": risk_id,
            "residual_score": residual,
            "appetite_threshold": appetite,
            "breached": breached,
            "severity": "critical" if residual - appetite > 0.2 else "warning" if breached else "ok"
        }

    # =========================================================================
    # Overall Risk Posture
    # =========================================================================

    def get_risk_posture(self) -> Dict[str, Any]:
        """Get overall risk posture summary"""
        risks = self.list_risks()

        assessments = [self.assess_risk(r["id"]) for r in risks]
        assessments = [a for a in assessments if "error" not in a]

        critical = len([a for a in assessments if a["risk_level"] == "critical"])
        high = len([a for a in assessments if a["risk_level"] == "high"])
        medium = len([a for a in assessments if a["risk_level"] == "medium"])
        low = len([a for a in assessments if a["risk_level"] == "low"])

        within_appetite = len([a for a in assessments if a["within_appetite"]])
        breached = len(assessments) - within_appetite

        avg_residual = sum(a["residual_score"] for a in assessments) / len(assessments) if assessments else 0

        return {
            "total_risks": len(assessments),
            "by_level": {
                "critical": critical,
                "high": high,
                "medium": medium,
                "low": low
            },
            "within_appetite": within_appetite,
            "appetite_breached": breached,
            "average_residual_score": avg_residual,
            "posture": "critical" if critical > 0 else "elevated" if high > 0 else "normal",
            "assessed_at": self._now()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get risk store statistics"""
        base_stats = super().get_stats()
        risks = self._find_nodes("risk")
        threats = self._find_nodes("threat")
        controls = self._find_nodes("risk_control")
        incidents = self._find_nodes("risk_incident")

        return {
            **base_stats,
            "risks": len(risks),
            "threats": len(threats),
            "controls": len(controls),
            "incidents": len(incidents),
            "open_incidents": len([i for i in incidents if not i.get("resolved")])
        }
