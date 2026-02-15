"""
Observability Store
===================

Manages governance metrics, telemetry, patterns, and dashboards.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import GovernanceMetric, DecisionPattern, TelemetryStream, Dashboard, Alert

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class ObservabilityStore(BaseStore):
    """Store for governance observability and telemetry"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "observability")

    # =========================================================================
    # Metrics Management
    # =========================================================================

    def add_metric(
        self,
        name: str,
        metric_type: str,
        threshold: float,
        description: str = "",
        metric_id: Optional[str] = None
    ) -> str:
        """Add a governance metric"""
        mid = metric_id or self._generate_id("gm")
        props = {
            "name": name,
            "type": metric_type,  # "throughput", "latency", "accuracy", "resource"
            "current": 0.0,
            "threshold": threshold,
            "status": "healthy",
            "description": description
        }
        return self._add_node("governance_metric", mid, props)

    def update_metric(self, metric_id: str, value: float):
        """Update a metric value"""
        metric = self._get_node("governance_metric", metric_id)
        if not metric:
            return

        threshold = metric.get("threshold", 0)
        status = "healthy"

        # Determine status based on metric type
        metric_type = metric.get("type", "")
        if metric_type in ["latency", "error_rate"]:
            # Higher is worse
            if value > threshold:
                status = "critical" if value > threshold * 1.5 else "warning"
        else:
            # Lower is worse (e.g., throughput, accuracy)
            if value < threshold:
                status = "critical" if value < threshold * 0.5 else "warning"

        self._update_node("governance_metric", metric_id, {
            "current": value,
            "status": status,
            "updated_at": self._now()
        })

    def get_metric(self, metric_id: str) -> Optional[Dict[str, Any]]:
        """Get metric by ID"""
        return self._get_node("governance_metric", metric_id)

    def list_metrics(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List all metrics"""
        metrics = self._find_nodes("governance_metric")
        if status:
            metrics = [m for m in metrics if m.get("status") == status]
        return metrics

    def record_metric_history(self, metric_id: str, value: float):
        """Record historical metric value"""
        hid = self._generate_id("mh")
        props = {
            "metric_id": metric_id,
            "value": value,
            "timestamp": self._now()
        }
        self._add_node("metric_history", hid, props)

    def get_metric_history(
        self,
        metric_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get metric history"""
        history = self._find_nodes("metric_history", metric_id=metric_id)
        return sorted(history, key=lambda h: h.get("timestamp", ""), reverse=True)[:limit]

    # =========================================================================
    # Alert Management
    # =========================================================================

    def configure_alert(
        self,
        metric_id: str,
        condition: str,
        severity: str,
        notification_channel: str,
        alert_id: Optional[str] = None
    ) -> str:
        """Configure an alert for a metric"""
        aid = alert_id or self._generate_id("al")
        props = {
            "metric_id": metric_id,
            "condition": condition,
            "severity": severity,
            "notification_channel": notification_channel,
            "enabled": True
        }
        self._add_node("alert_config", aid, props)

        self._add_edge(
            "alert_config", aid,
            "METRIC_ALERT",
            "governance_metric", metric_id,
            {}
        )

        return aid

    def trigger_alert(
        self,
        config_id: str,
        metric_value: float
    ) -> str:
        """Trigger an alert"""
        tid = self._generate_id("at")
        props = {
            "config_id": config_id,
            "metric_value": metric_value,
            "triggered_at": self._now(),
            "acknowledged": False
        }
        return self._add_node("alert_trigger", tid, props)

    def acknowledge_alert(self, trigger_id: str, acknowledged_by: str):
        """Acknowledge an alert"""
        self._update_node("alert_trigger", trigger_id, {
            "acknowledged": True,
            "acknowledged_by": acknowledged_by,
            "acknowledged_at": self._now()
        })

    def get_active_alerts(self) -> List[Dict[str, Any]]:
        """Get unacknowledged alerts"""
        alerts = self._find_nodes("alert_trigger", acknowledged=False)
        return alerts

    # =========================================================================
    # Pattern Detection
    # =========================================================================

    def register_pattern(
        self,
        pattern_name: str,
        frequency: str,
        expected: float,
        description: str = "",
        pattern_id: Optional[str] = None
    ) -> str:
        """Register a decision pattern to monitor"""
        pid = pattern_id or self._generate_id("dp")
        props = {
            "pattern": pattern_name,
            "frequency": frequency,  # "hourly", "daily", "rare"
            "expected": expected,
            "anomaly_score": 0.0,
            "description": description
        }
        return self._add_node("decision_pattern", pid, props)

    def update_pattern(
        self,
        pattern_id: str,
        observed: float,
        anomaly_score: float
    ):
        """Update pattern observation"""
        self._update_node("decision_pattern", pattern_id, {
            "observed": observed,
            "anomaly_score": anomaly_score,
            "updated_at": self._now()
        })

    def get_patterns(
        self,
        anomaly_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Get patterns, optionally filtered by anomaly score"""
        patterns = self._find_nodes("decision_pattern")
        if anomaly_threshold is not None:
            patterns = [p for p in patterns if p.get("anomaly_score", 0) >= anomaly_threshold]
        return patterns

    def record_pattern_detection(
        self,
        pattern_id: str,
        context: str
    ) -> str:
        """Record a pattern detection event"""
        did = self._generate_id("pd")
        props = {
            "pattern_id": pattern_id,
            "context": context,
            "detected_at": self._now(),
            "investigation": None
        }
        self._add_node("pattern_detection", did, props)

        self._add_edge(
            "pattern_detection", did,
            "PATTERN_DETECTED",
            "decision_pattern", pattern_id,
            {}
        )

        return did

    # =========================================================================
    # Telemetry Streams
    # =========================================================================

    def configure_telemetry_stream(
        self,
        source: str,
        data_type: str,
        retention: str,
        sampling: str,
        stream_id: Optional[str] = None
    ) -> str:
        """Configure a telemetry stream"""
        sid = stream_id or self._generate_id("ts")
        props = {
            "source": source,
            "data_type": data_type,
            "retention": retention,
            "sampling": sampling,
            "active": True
        }
        return self._add_node("telemetry_stream", sid, props)

    def list_telemetry_streams(self) -> List[Dict[str, Any]]:
        """List all telemetry streams"""
        return self._find_nodes("telemetry_stream")

    # =========================================================================
    # Dashboards
    # =========================================================================

    def create_dashboard(
        self,
        name: str,
        audience: str,
        refresh_rate: str,
        metrics: List[str],
        dashboard_id: Optional[str] = None
    ) -> str:
        """Create a dashboard"""
        did = dashboard_id or self._generate_id("db")
        props = {
            "name": name,
            "audience": audience,
            "refresh_rate": refresh_rate,
            "metrics": metrics
        }
        self._add_node("dashboard", did, props)

        for metric_id in metrics:
            self._add_edge(
                "dashboard", did,
                "DASHBOARD_SHOWS",
                "governance_metric", metric_id,
                {}
            )

        return did

    def get_dashboard(self, dashboard_id: str) -> Optional[Dict[str, Any]]:
        """Get dashboard by ID"""
        return self._get_node("dashboard", dashboard_id)

    def get_dashboard_data(self, dashboard_id: str) -> Dict[str, Any]:
        """Get data for a dashboard"""
        dashboard = self.get_dashboard(dashboard_id)
        if not dashboard:
            return {"error": "Dashboard not found"}

        metrics = dashboard.get("metrics", [])
        metric_data = []

        for metric_id in metrics:
            metric = self.get_metric(metric_id)
            if metric:
                metric_data.append({
                    "id": metric_id,
                    "name": metric.get("name"),
                    "current": metric.get("current"),
                    "threshold": metric.get("threshold"),
                    "status": metric.get("status")
                })

        return {
            "dashboard": dashboard.get("name"),
            "metrics": metric_data,
            "generated_at": self._now()
        }

    # =========================================================================
    # Trend Analysis
    # =========================================================================

    def analyze_trend(self, metric_id: str, period: str = "30d") -> Dict[str, Any]:
        """Analyze trend for a metric"""
        history = self.get_metric_history(metric_id, limit=100)

        if len(history) < 5:
            return {"metric_id": metric_id, "trend": "insufficient_data"}

        # Simple trend analysis
        recent = history[:10]
        older = history[10:30]

        recent_avg = sum(h.get("value", 0) for h in recent) / len(recent)
        older_avg = sum(h.get("value", 0) for h in older) / len(older) if older else recent_avg

        if recent_avg > older_avg * 1.1:
            trend = "increasing"
            projection = f"{recent_avg * 1.1:.2f} projected"
        elif recent_avg < older_avg * 0.9:
            trend = "decreasing"
            projection = f"{recent_avg * 0.9:.2f} projected"
        else:
            trend = "stable"
            projection = f"{recent_avg:.2f} maintained"

        return {
            "metric_id": metric_id,
            "period": period,
            "trend": trend,
            "recent_avg": recent_avg,
            "older_avg": older_avg,
            "projection": projection
        }

    # =========================================================================
    # Anomaly Correlation
    # =========================================================================

    def correlate_anomalies(
        self,
        pattern_ids: List[str]
    ) -> Dict[str, Any]:
        """Analyze correlation between anomalies"""
        detections = []
        for pid in pattern_ids:
            pattern_detections = self._find_nodes("pattern_detection", pattern_id=pid)
            detections.extend(pattern_detections)

        # Simple correlation: check if detections are close in time
        correlations = []
        for i, d1 in enumerate(detections):
            for d2 in detections[i+1:]:
                t1 = d1.get("detected_at", "")
                t2 = d2.get("detected_at", "")
                # Simplified: just check if same day
                if t1[:10] == t2[:10]:
                    correlations.append({
                        "pattern_1": d1.get("pattern_id"),
                        "pattern_2": d2.get("pattern_id"),
                        "correlation": 0.85,
                        "likely_cause": "same_incident"
                    })

        return {
            "patterns_analyzed": pattern_ids,
            "correlations": correlations
        }

    # =========================================================================
    # Governance Health Score
    # =========================================================================

    def calculate_health_score(self) -> Dict[str, Any]:
        """Calculate overall governance health score"""
        metrics = self.list_metrics()

        if not metrics:
            return {"health_score": 1.0, "status": "unknown", "components": {}}

        total_weight = 0
        weighted_score = 0
        components = {}

        # Weight by metric type
        weights = {
            "accuracy": 0.3,
            "latency": 0.2,
            "throughput": 0.15,
            "error_rate": 0.25,
            "resource": 0.1
        }

        for metric in metrics:
            metric_type = metric.get("type", "other")
            weight = weights.get(metric_type, 0.1)

            # Convert to float (may be stored as strings)
            current = float(metric.get("current", 0))
            threshold = float(metric.get("threshold", 1))

            # Calculate component score (0-1)
            if metric_type in ["latency", "error_rate"]:
                # Lower is better
                if current <= threshold:
                    score = 1.0
                else:
                    score = max(0, 1 - (current - threshold) / threshold)
            else:
                # Higher is better
                if current >= threshold:
                    score = 1.0
                else:
                    score = current / threshold if threshold > 0 else 1.0

            components[metric.get("name", metric["id"])] = {
                "score": score,
                "weight": weight,
                "contribution": score * weight
            }

            weighted_score += score * weight
            total_weight += weight

        health_score = weighted_score / total_weight if total_weight > 0 else 1.0

        # Determine status
        if health_score >= 0.9:
            status = "healthy"
        elif health_score >= 0.7:
            status = "warning"
        else:
            status = "critical"

        return {
            "health_score": health_score,
            "status": status,
            "components": components,
            "calculated_at": self._now()
        }

    # =========================================================================
    # Reporting
    # =========================================================================

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate a summary report"""
        health = self.calculate_health_score()
        alerts = self.get_active_alerts()
        anomalies = self.get_patterns(anomaly_threshold=0.5)

        return {
            "report_type": "governance_summary",
            "health": health,
            "active_alerts": len(alerts),
            "anomalies_detected": len(anomalies),
            "generated_at": self._now()
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get observability store statistics"""
        base_stats = super().get_stats()
        metrics = self._find_nodes("governance_metric")
        alerts = self._find_nodes("alert_trigger")
        patterns = self._find_nodes("decision_pattern")
        dashboards = self._find_nodes("dashboard")

        return {
            **base_stats,
            "metrics": len(metrics),
            "healthy_metrics": len([m for m in metrics if m.get("status") == "healthy"]),
            "active_alerts": len([a for a in alerts if not a.get("acknowledged")]),
            "patterns_monitored": len(patterns),
            "dashboards": len(dashboards)
        }
