"""
Resource Governance Store
=========================

Manages resource types, budgets, spending, and allocation policies.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import ResourceType, Budget, SpendEvent, AllocationPolicy

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class ResourceStore(BaseStore):
    """Store for resource governance and budget control"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "resource")

    # =========================================================================
    # Resource Type Management
    # =========================================================================

    def add_resource_type(
        self,
        name: str,
        unit: str,
        cost_per_unit: float,
        scarcity: str = "low",
        resource_id: Optional[str] = None
    ) -> str:
        """Add a resource type"""
        rid = resource_id or self._generate_id("rt")
        props = {
            "name": name,
            "unit": unit,
            "cost_per_unit": cost_per_unit,
            "scarcity": scarcity
        }
        return self._add_node("resource_type", rid, props)

    def get_resource_type(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """Get resource type by ID"""
        return self._get_node("resource_type", resource_id)

    def list_resource_types(self) -> List[Dict[str, Any]]:
        """List all resource types"""
        return self._find_nodes("resource_type")

    # =========================================================================
    # Budget Management
    # =========================================================================

    def create_budget(
        self,
        owner: str,
        resource_id: str,
        allocated: float,
        period: str,
        alert_threshold: float = 0.8,
        budget_id: Optional[str] = None
    ) -> str:
        """Create a budget allocation"""
        bid = budget_id or self._generate_id("b")
        props = {
            "owner": owner,
            "resource_id": resource_id,
            "allocated": allocated,
            "consumed": 0.0,
            "period": period,
            "alert_threshold": alert_threshold,
            "status": "active"
        }
        self._add_node("budget", bid, props)

        self._add_edge(
            "budget", bid,
            "BUDGET_FOR",
            "resource_type", resource_id,
            {}
        )

        return bid

    def get_budget(self, budget_id: str) -> Optional[Dict[str, Any]]:
        """Get budget by ID"""
        return self._get_node("budget", budget_id)

    def list_budgets(self, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        """List budgets"""
        budgets = self._find_nodes("budget")
        if owner:
            budgets = [b for b in budgets if b.get("owner") == owner]
        return budgets

    def get_budget_status(self, budget_id: str) -> Dict[str, Any]:
        """Get detailed budget status"""
        budget = self.get_budget(budget_id)
        if not budget:
            return {"error": "Budget not found"}

        allocated = budget.get("allocated", 0)
        consumed = budget.get("consumed", 0)
        threshold = budget.get("alert_threshold", 0.8)

        utilization = consumed / allocated if allocated > 0 else 0
        remaining = allocated - consumed

        return {
            "budget_id": budget_id,
            "owner": budget.get("owner"),
            "resource_id": budget.get("resource_id"),
            "allocated": allocated,
            "consumed": consumed,
            "remaining": remaining,
            "utilization": utilization,
            "alert_threshold": threshold,
            "threshold_breached": utilization >= threshold,
            "exhausted": remaining <= 0
        }

    # =========================================================================
    # Spending
    # =========================================================================

    def record_spend(
        self,
        agent_id: str,
        budget_id: str,
        amount: float,
        task: str,
        spend_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Record a spend event and update budget"""
        # Check budget
        budget = self.get_budget(budget_id)
        if not budget:
            return {"approved": False, "reason": "Budget not found"}

        current_consumed = budget.get("consumed", 0)
        allocated = budget.get("allocated", 0)
        new_consumed = current_consumed + amount

        # Check if spend would exceed budget
        if new_consumed > allocated:
            return {
                "approved": False,
                "reason": "Would exceed budget",
                "current": current_consumed,
                "requested": amount,
                "available": allocated - current_consumed
            }

        # Record spend
        sid = spend_id or self._generate_id("se")
        props = {
            "agent_id": agent_id,
            "budget_id": budget_id,
            "resource_id": budget.get("resource_id"),
            "amount": amount,
            "task": task,
            "timestamp": self._now(),
            "approved": True
        }
        self._add_node("spend_event", sid, props)

        self._add_edge(
            "spend_event", sid,
            "SPEND_FROM",
            "budget", budget_id,
            {}
        )

        # Update budget consumed
        self._update_node("budget", budget_id, {"consumed": new_consumed})

        # Check if threshold breached
        threshold = budget.get("alert_threshold", 0.8)
        utilization = new_consumed / allocated if allocated > 0 else 0
        threshold_breached = utilization >= threshold

        return {
            "approved": True,
            "spend_id": sid,
            "new_consumed": new_consumed,
            "utilization": utilization,
            "threshold_breached": threshold_breached
        }

    def get_spend_history(
        self,
        budget_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get spending history"""
        spends = self._find_nodes("spend_event")

        if budget_id:
            spends = [s for s in spends if s.get("budget_id") == budget_id]
        if agent_id:
            spends = [s for s in spends if s.get("agent_id") == agent_id]

        spends = sorted(spends, key=lambda s: s.get("timestamp", ""), reverse=True)
        return spends[:limit]

    # =========================================================================
    # Allocation Policies
    # =========================================================================

    def add_allocation_policy(
        self,
        name: str,
        priority: str,
        conditions: str,
        description: str = "",
        policy_id: Optional[str] = None
    ) -> str:
        """Add an allocation policy"""
        pid = policy_id or self._generate_id("ap")
        props = {
            "name": name,
            "priority": priority,
            "conditions": conditions,
            "description": description,
            "active": True
        }
        return self._add_node("allocation_policy", pid, props)

    def get_allocation_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get allocation policy by ID"""
        return self._get_node("allocation_policy", policy_id)

    def list_allocation_policies(self) -> List[Dict[str, Any]]:
        """List allocation policies"""
        return self._find_nodes("allocation_policy")

    def evaluate_allocation(
        self,
        agent_id: str,
        resource_id: str,
        amount: float,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Evaluate allocation request against policies"""
        policies = self.list_allocation_policies()
        active_policies = [p for p in policies if p.get("active")]

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "default": 3}
        active_policies.sort(key=lambda p: priority_order.get(p.get("priority", "default"), 99))

        for policy in active_policies:
            condition = policy.get("conditions", "")
            try:
                # Simple evaluation
                result = eval(condition, {"__builtins__": {}}, context)
                if result:
                    return {
                        "approved": True,
                        "policy_applied": policy["id"],
                        "policy_name": policy.get("name")
                    }
            except:
                pass

        return {"approved": True, "policy_applied": "default"}

    # =========================================================================
    # Budget Hierarchy
    # =========================================================================

    def set_budget_hierarchy(
        self,
        parent_budget_id: str,
        child_budget_id: str,
        inheritance: str,
        override_allowed: bool = True
    ):
        """Set budget hierarchy relationship"""
        self._add_edge(
            "budget", parent_budget_id,
            "BUDGET_HIERARCHY",
            "budget", child_budget_id,
            {"inheritance": inheritance, "override_allowed": override_allowed}
        )

    # =========================================================================
    # Consumption Tracking
    # =========================================================================

    def get_consumption_rate(
        self,
        budget_id: str
    ) -> Dict[str, Any]:
        """Calculate consumption rate for a budget"""
        spends = self.get_spend_history(budget_id=budget_id)

        if not spends:
            return {"rate_24h": 0, "rate_7d": 0, "trend": "stable"}

        # Calculate rates (simplified)
        total = sum(s.get("amount", 0) for s in spends)
        recent = sum(s.get("amount", 0) for s in spends[:10])

        return {
            "total_consumed": total,
            "recent_consumed": recent,
            "rate_24h": recent / 10 if len(spends) >= 10 else total / len(spends),
            "trend": "stable"  # Would need timestamps for real trend
        }

    # =========================================================================
    # Cost Tracking
    # =========================================================================

    def calculate_cost(
        self,
        budget_id: str
    ) -> Dict[str, Any]:
        """Calculate actual cost for a budget"""
        budget = self.get_budget(budget_id)
        if not budget:
            return {"error": "Budget not found"}

        resource = self.get_resource_type(budget.get("resource_id", ""))
        if not resource:
            return {"error": "Resource type not found"}

        consumed = budget.get("consumed", 0)
        cost_per_unit = resource.get("cost_per_unit", 0)
        total_cost = consumed * cost_per_unit

        return {
            "budget_id": budget_id,
            "resource": resource.get("name"),
            "consumed": consumed,
            "unit": resource.get("unit"),
            "cost_per_unit": cost_per_unit,
            "total_cost": total_cost
        }

    # =========================================================================
    # Budget Alerts
    # =========================================================================

    def check_budget_alerts(self) -> List[Dict[str, Any]]:
        """Check all budgets for alerts"""
        budgets = self.list_budgets()
        alerts = []

        for budget in budgets:
            status = self.get_budget_status(budget["id"])
            if status.get("threshold_breached"):
                alerts.append({
                    "budget_id": budget["id"],
                    "owner": budget.get("owner"),
                    "utilization": status.get("utilization"),
                    "severity": "critical" if status.get("exhausted") else "warning"
                })

        return alerts

    def get_stats(self) -> Dict[str, Any]:
        """Get resource store statistics"""
        base_stats = super().get_stats()
        resource_types = self._find_nodes("resource_type")
        budgets = self._find_nodes("budget")
        spends = self._find_nodes("spend_event")
        policies = self._find_nodes("allocation_policy")

        return {
            **base_stats,
            "resource_types": len(resource_types),
            "budgets": len(budgets),
            "spend_events": len(spends),
            "allocation_policies": len(policies),
            "budget_alerts": len(self.check_budget_alerts())
        }
