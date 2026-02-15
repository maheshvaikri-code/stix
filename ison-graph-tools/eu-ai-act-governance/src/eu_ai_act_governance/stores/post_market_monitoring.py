"""
Post-Market Monitoring Store
============================

Manages post-market monitoring requirements per Article 72.
Tracks system performance, user feedback, and compliance monitoring after deployment.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import MonitoringActivity, MonitoringFrequency, AIRiskLevel

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class PostMarketMonitoringStore(BaseStore):
    """Store for post-market monitoring management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "post_market_monitoring")

    # =========================================================================
    # Monitoring Plan
    # =========================================================================

    def create_monitoring_plan(
        self,
        system_id: str,
        provider: str,
        risk_level: AIRiskLevel,
        plan_id: Optional[str] = None
    ) -> str:
        """Create a post-market monitoring plan"""
        pid = plan_id or self._generate_id("pmp")

        # Define activities based on risk level
        activities = self._get_default_activities(risk_level)

        props = {
            "system_id": system_id,
            "provider": provider,
            "risk_level": risk_level.value,
            "activities": activities,
            "status": "draft",
            "created_at": self._now(),
            "last_reviewed": None,
            "description": f"Post-market monitoring plan for {system_id}"
        }
        return self._add_node("monitoring_plan", pid, props)

    def _get_default_activities(self, risk_level: AIRiskLevel) -> List[Dict[str, Any]]:
        """Get default monitoring activities based on risk level"""
        base_activities = [
            {
                "activity": MonitoringActivity.PERFORMANCE_TRACKING.value,
                "frequency": MonitoringFrequency.CONTINUOUS.value,
                "enabled": True
            },
            {
                "activity": MonitoringActivity.ERROR_ANALYSIS.value,
                "frequency": MonitoringFrequency.WEEKLY.value,
                "enabled": True
            },
            {
                "activity": MonitoringActivity.USER_FEEDBACK.value,
                "frequency": MonitoringFrequency.CONTINUOUS.value,
                "enabled": True
            },
        ]

        if risk_level == AIRiskLevel.HIGH:
            base_activities.extend([
                {
                    "activity": MonitoringActivity.BIAS_MONITORING.value,
                    "frequency": MonitoringFrequency.MONTHLY.value,
                    "enabled": True
                },
                {
                    "activity": MonitoringActivity.COMPLIANCE_AUDIT.value,
                    "frequency": MonitoringFrequency.QUARTERLY.value,
                    "enabled": True
                },
                {
                    "activity": MonitoringActivity.SECURITY_MONITORING.value,
                    "frequency": MonitoringFrequency.CONTINUOUS.value,
                    "enabled": True
                },
            ])

        return base_activities

    def get_monitoring_plan(self, plan_id: str) -> Optional[Dict[str, Any]]:
        """Get monitoring plan by ID"""
        return self._get_node("monitoring_plan", plan_id)

    def get_system_plan(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get monitoring plan for a system"""
        plans = self._find_nodes("monitoring_plan", system_id=system_id)
        active = [p for p in plans if p.get("status") in ["active", "draft"]]
        return active[0] if active else None

    def activate_plan(
        self,
        plan_id: str,
        activated_by: str
    ):
        """Activate a monitoring plan"""
        self._update_node("monitoring_plan", plan_id, {
            "status": "active",
            "activated_by": activated_by,
            "activated_at": self._now()
        })

    def update_activity(
        self,
        plan_id: str,
        activity: MonitoringActivity,
        frequency: MonitoringFrequency,
        enabled: bool
    ):
        """Update a monitoring activity configuration"""
        plan = self.get_monitoring_plan(plan_id)
        if not plan:
            return

        activities = plan.get("activities", [])
        found = False
        for act in activities:
            if act["activity"] == activity.value:
                act["frequency"] = frequency.value
                act["enabled"] = enabled
                found = True
                break

        if not found:
            activities.append({
                "activity": activity.value,
                "frequency": frequency.value,
                "enabled": enabled
            })

        self._update_node("monitoring_plan", plan_id, {
            "activities": activities,
            "updated_at": self._now()
        })

    # =========================================================================
    # Monitoring Execution
    # =========================================================================

    def schedule_monitoring_run(
        self,
        plan_id: str,
        activity: MonitoringActivity,
        scheduled_for: str,
        assigned_to: str,
        run_id: Optional[str] = None
    ) -> str:
        """Schedule a monitoring run"""
        rid = run_id or self._generate_id("mr")
        props = {
            "plan_id": plan_id,
            "activity": activity.value,
            "scheduled_for": scheduled_for,
            "assigned_to": assigned_to,
            "status": "scheduled",
            "created_at": self._now(),
            "description": f"Monitoring run: {activity.value}"
        }
        return self._add_node("monitoring_run", rid, props)

    def start_monitoring_run(
        self,
        run_id: str,
        started_by: str
    ):
        """Start a monitoring run"""
        self._update_node("monitoring_run", run_id, {
            "status": "in_progress",
            "started_by": started_by,
            "started_at": self._now()
        })

    def complete_monitoring_run(
        self,
        run_id: str,
        findings: List[str],
        metrics: Dict[str, Any],
        issues_found: int,
        recommendations: List[str],
        completed_by: str
    ) -> Dict[str, Any]:
        """Complete a monitoring run"""
        self._update_node("monitoring_run", run_id, {
            "status": "completed",
            "findings": findings,
            "metrics": metrics,
            "issues_found": issues_found,
            "recommendations": recommendations,
            "completed_by": completed_by,
            "completed_at": self._now()
        })

        return {
            "run_id": run_id,
            "issues_found": issues_found,
            "requires_action": issues_found > 0
        }

    def get_monitoring_runs(
        self,
        plan_id: str,
        activity: Optional[MonitoringActivity] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get monitoring runs for a plan"""
        runs = self._find_nodes("monitoring_run", plan_id=plan_id)
        if activity:
            runs = [r for r in runs if r.get("activity") == activity.value]
        if status:
            runs = [r for r in runs if r.get("status") == status]
        return runs

    # =========================================================================
    # Performance Metrics Tracking
    # =========================================================================

    def record_performance_metric(
        self,
        system_id: str,
        metric_name: str,
        metric_value: float,
        threshold_min: Optional[float] = None,
        threshold_max: Optional[float] = None,
        context: str = "",
        metric_id: Optional[str] = None
    ) -> str:
        """Record a performance metric"""
        mid = metric_id or self._generate_id("pm")

        within_threshold = True
        if threshold_min is not None and metric_value < threshold_min:
            within_threshold = False
        if threshold_max is not None and metric_value > threshold_max:
            within_threshold = False

        props = {
            "system_id": system_id,
            "metric_name": metric_name,
            "metric_value": metric_value,
            "threshold_min": threshold_min,
            "threshold_max": threshold_max,
            "within_threshold": within_threshold,
            "context": context,
            "recorded_at": self._now(),
            "description": f"Performance metric: {metric_name}"
        }
        return self._add_node("performance_metric", mid, props)

    def get_performance_metrics(
        self,
        system_id: str,
        metric_name: Optional[str] = None,
        since: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get performance metrics for a system"""
        metrics = self._find_nodes("performance_metric", system_id=system_id)
        if metric_name:
            metrics = [m for m in metrics if m.get("metric_name") == metric_name]
        if since:
            metrics = [m for m in metrics if m.get("recorded_at", "") >= since]
        return metrics

    def detect_performance_drift(
        self,
        system_id: str,
        metric_name: str,
        window_size: int = 10
    ) -> Dict[str, Any]:
        """Detect performance drift for a metric"""
        metrics = self.get_performance_metrics(system_id, metric_name)
        metrics.sort(key=lambda x: x.get("recorded_at", ""))

        if len(metrics) < window_size:
            return {
                "drift_detected": False,
                "reason": "insufficient_data",
                "data_points": len(metrics)
            }

        recent = metrics[-window_size:]
        out_of_threshold = [m for m in recent if not m.get("within_threshold")]

        drift_detected = len(out_of_threshold) > window_size / 2

        return {
            "drift_detected": drift_detected,
            "metric_name": metric_name,
            "window_size": window_size,
            "out_of_threshold_count": len(out_of_threshold),
            "latest_value": recent[-1].get("metric_value") if recent else None
        }

    # =========================================================================
    # User Feedback
    # =========================================================================

    def record_user_feedback(
        self,
        system_id: str,
        feedback_type: str,  # complaint, suggestion, praise, bug_report
        feedback_content: str,
        user_id: Optional[str] = None,
        severity: str = "normal",  # low, normal, high, critical
        feedback_id: Optional[str] = None
    ) -> str:
        """Record user feedback"""
        fid = feedback_id or self._generate_id("uf")
        props = {
            "system_id": system_id,
            "feedback_type": feedback_type,
            "content": feedback_content,
            "user_id": user_id,
            "severity": severity,
            "status": "received",
            "received_at": self._now(),
            "description": f"User feedback: {feedback_type}"
        }
        return self._add_node("user_feedback", fid, props)

    def categorize_feedback(
        self,
        feedback_id: str,
        category: str,  # safety, performance, usability, bias, other
        requires_action: bool,
        assigned_to: Optional[str] = None
    ):
        """Categorize user feedback"""
        self._update_node("user_feedback", feedback_id, {
            "status": "categorized",
            "category": category,
            "requires_action": requires_action,
            "assigned_to": assigned_to,
            "categorized_at": self._now()
        })

    def resolve_feedback(
        self,
        feedback_id: str,
        resolution: str,
        resolved_by: str,
        system_updated: bool
    ):
        """Resolve user feedback"""
        self._update_node("user_feedback", feedback_id, {
            "status": "resolved",
            "resolution": resolution,
            "resolved_by": resolved_by,
            "system_updated": system_updated,
            "resolved_at": self._now()
        })

    def get_feedback(
        self,
        system_id: str,
        feedback_type: Optional[str] = None,
        status: Optional[str] = None,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get user feedback"""
        feedback = self._find_nodes("user_feedback", system_id=system_id)
        if feedback_type:
            feedback = [f for f in feedback if f.get("feedback_type") == feedback_type]
        if status:
            feedback = [f for f in feedback if f.get("status") == status]
        if category:
            feedback = [f for f in feedback if f.get("category") == category]
        return feedback

    def get_feedback_summary(self, system_id: str) -> Dict[str, Any]:
        """Get feedback summary for a system"""
        feedback = self.get_feedback(system_id)

        by_type = {}
        by_severity = {}
        by_status = {}

        for f in feedback:
            ft = f.get("feedback_type", "unknown")
            by_type[ft] = by_type.get(ft, 0) + 1

            sev = f.get("severity", "normal")
            by_severity[sev] = by_severity.get(sev, 0) + 1

            status = f.get("status", "unknown")
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "system_id": system_id,
            "total_feedback": len(feedback),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_status": by_status,
            "pending_action": len([f for f in feedback if f.get("requires_action") and f.get("status") != "resolved"])
        }

    # =========================================================================
    # Issue Tracking
    # =========================================================================

    def create_issue(
        self,
        system_id: str,
        issue_type: str,  # performance, safety, bias, compliance, security
        title: str,
        description: str,
        severity: str,  # low, medium, high, critical
        source: str,  # monitoring, feedback, audit, incident
        source_ref: Optional[str] = None,
        issue_id: Optional[str] = None
    ) -> str:
        """Create a post-market issue"""
        iid = issue_id or self._generate_id("iss")
        props = {
            "system_id": system_id,
            "issue_type": issue_type,
            "title": title,
            "description": description,
            "severity": severity,
            "source": source,
            "source_ref": source_ref,
            "status": "open",
            "created_at": self._now(),
            "node_description": f"Issue: {title}"
        }
        return self._add_node("pmm_issue", iid, props)

    def assign_issue(
        self,
        issue_id: str,
        assigned_to: str,
        due_date: Optional[str] = None
    ):
        """Assign an issue"""
        self._update_node("pmm_issue", issue_id, {
            "status": "assigned",
            "assigned_to": assigned_to,
            "due_date": due_date,
            "assigned_at": self._now()
        })

    def resolve_issue(
        self,
        issue_id: str,
        resolution: str,
        resolved_by: str,
        root_cause: Optional[str] = None,
        corrective_action: Optional[str] = None
    ):
        """Resolve an issue"""
        self._update_node("pmm_issue", issue_id, {
            "status": "resolved",
            "resolution": resolution,
            "resolved_by": resolved_by,
            "root_cause": root_cause,
            "corrective_action": corrective_action,
            "resolved_at": self._now()
        })

    def get_issues(
        self,
        system_id: str,
        status: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get issues for a system"""
        issues = self._find_nodes("pmm_issue", system_id=system_id)
        if status:
            issues = [i for i in issues if i.get("status") == status]
        if severity:
            issues = [i for i in issues if i.get("severity") == severity]
        return issues

    # =========================================================================
    # Reporting
    # =========================================================================

    def generate_monitoring_report(
        self,
        system_id: str,
        period_start: str,
        period_end: str,
        generated_by: str,
        report_id: Optional[str] = None
    ) -> str:
        """Generate a monitoring report"""
        rid = report_id or self._generate_id("rep")

        # Gather data
        plan = self.get_system_plan(system_id)
        runs = self._find_nodes("monitoring_run", plan_id=plan["id"] if plan else None)
        metrics = self.get_performance_metrics(system_id, since=period_start)
        feedback = self.get_feedback(system_id)
        issues = self.get_issues(system_id)

        # Filter by period
        runs_in_period = [
            r for r in runs
            if period_start <= r.get("completed_at", r.get("scheduled_for", "")) <= period_end
        ]

        props = {
            "system_id": system_id,
            "period_start": period_start,
            "period_end": period_end,
            "generated_by": generated_by,
            "generated_at": self._now(),
            "monitoring_runs": len(runs_in_period),
            "metrics_recorded": len(metrics),
            "feedback_received": len(feedback),
            "issues_created": len([i for i in issues if period_start <= i.get("created_at", "") <= period_end]),
            "issues_resolved": len([i for i in issues if period_start <= i.get("resolved_at", "") <= period_end]),
            "open_issues": len([i for i in issues if i.get("status") != "resolved"]),
            "description": f"Monitoring report for {system_id}"
        }
        return self._add_node("monitoring_report", rid, props)

    def get_monitoring_reports(
        self,
        system_id: str
    ) -> List[Dict[str, Any]]:
        """Get monitoring reports for a system"""
        reports = self._find_nodes("monitoring_report", system_id=system_id)
        reports.sort(key=lambda x: x.get("generated_at", ""), reverse=True)
        return reports

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get post-market monitoring statistics"""
        base_stats = super().get_stats()
        plans = self._find_nodes("monitoring_plan")
        runs = self._find_nodes("monitoring_run")
        metrics = self._find_nodes("performance_metric")
        feedback = self._find_nodes("user_feedback")
        issues = self._find_nodes("pmm_issue")
        reports = self._find_nodes("monitoring_report")

        return {
            **base_stats,
            "monitoring_plans": len(plans),
            "active_plans": len([p for p in plans if p.get("status") == "active"]),
            "monitoring_runs": len(runs),
            "completed_runs": len([r for r in runs if r.get("status") == "completed"]),
            "metrics_recorded": len(metrics),
            "out_of_threshold_metrics": len([m for m in metrics if not m.get("within_threshold")]),
            "total_feedback": len(feedback),
            "unresolved_feedback": len([f for f in feedback if f.get("status") != "resolved" and f.get("requires_action")]),
            "total_issues": len(issues),
            "open_issues": len([i for i in issues if i.get("status") != "resolved"]),
            "critical_issues": len([i for i in issues if i.get("severity") == "critical" and i.get("status") != "resolved"]),
            "monitoring_reports": len(reports)
        }
