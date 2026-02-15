"""
Policy Engine Store
===================

Manages policies, rules, conditions, and evaluation logic.
"""

import re
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING

from .base import BaseStore
from ..schema import PolicyStatus, Policy, Rule, RuleCondition, PolicyEvaluation

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class PolicyStore(BaseStore):
    """Store for policy engine governance"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "policy")
        self._condition_evaluators: Dict[str, Callable] = {}
        self._register_default_evaluators()

    def _register_default_evaluators(self):
        """Register default condition evaluators"""
        self._condition_evaluators["attribute"] = self._eval_attribute
        self._condition_evaluators["threshold"] = self._eval_threshold
        self._condition_evaluators["function"] = self._eval_function
        self._condition_evaluators["computed"] = self._eval_computed

    # =========================================================================
    # Policy Management
    # =========================================================================

    def add_policy(
        self,
        name: str,
        priority: int = 50,
        description: str = "",
        owner: str = "",
        policy_id: Optional[str] = None
    ) -> str:
        """Add a governance policy"""
        pid = policy_id or self._generate_id("po")
        props = {
            "name": name,
            "priority": priority,
            "status": PolicyStatus.ACTIVE.value,
            "effective_date": self._now(),
            "description": description,
            "owner": owner,
            "version": "1.0"
        }
        return self._add_node("policy", pid, props)

    def update_policy_status(self, policy_id: str, status: PolicyStatus):
        """Update policy status"""
        self._update_node("policy", policy_id, {"status": status.value})

    def get_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get policy by ID"""
        return self._get_node("policy", policy_id)

    def list_policies(self, status: Optional[PolicyStatus] = None) -> List[Dict[str, Any]]:
        """List all policies"""
        policies = self._find_nodes("policy")
        if status:
            policies = [p for p in policies if p.get("status") == status.value]
        return sorted(policies, key=lambda p: p.get("priority", 0), reverse=True)

    # =========================================================================
    # Rule Management
    # =========================================================================

    def add_rule(
        self,
        policy_id: str,
        condition: str,
        action: str,
        exception_allows: Optional[str] = None,
        priority: int = 0,
        description: str = "",
        rule_id: Optional[str] = None
    ) -> str:
        """Add a rule to a policy"""
        rid = rule_id or self._generate_id("r")
        props = {
            "policy_id": policy_id,
            "condition": condition,
            "action": action,
            "exception_allows": exception_allows,
            "priority": priority,
            "description": description,
            "active": True
        }
        self._add_node("rule", rid, props)

        # Link to policy
        self._add_edge(
            "policy", policy_id,
            "POLICY_CONTAINS",
            "rule", rid,
            {}
        )

        return rid

    def get_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        """Get rule by ID"""
        return self._get_node("rule", rule_id)

    def list_rules(self, policy_id: str) -> List[Dict[str, Any]]:
        """List rules for a policy"""
        rules = self._find_nodes("rule", policy_id=policy_id)
        return sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)

    def deactivate_rule(self, rule_id: str):
        """Deactivate a rule"""
        self._update_node("rule", rule_id, {"active": False})

    # =========================================================================
    # Rule Precedence
    # =========================================================================

    def set_rule_precedence(
        self,
        rule_id: str,
        over_rule_id: str,
        when_conflict: str,
        resolution: str
    ):
        """Set precedence between rules"""
        self._add_edge(
            "rule", rule_id,
            "RULE_PRECEDENCE",
            "rule", over_rule_id,
            {"when_conflict": when_conflict, "resolution": resolution}
        )

    # =========================================================================
    # Exception Management
    # =========================================================================

    def add_exception(
        self,
        rule_id: str,
        name: str,
        requires: str,
        valid_for: str
    ) -> str:
        """Add an exception to a rule"""
        eid = self._generate_id("ex")
        props = {
            "rule_id": rule_id,
            "name": name,
            "requires": requires,
            "valid_for": valid_for,
            "active": True
        }
        self._add_node("exception", eid, props)

        self._add_edge(
            "rule", rule_id,
            "EXCEPTION_ALLOWS",
            "exception", eid,
            {}
        )

        return eid

    def grant_exception(
        self,
        exception_id: str,
        grantee: str,
        granted_by: str,
        valid_until: str
    ) -> str:
        """Grant an exception to a principal"""
        gid = self._generate_id("eg")
        props = {
            "exception_id": exception_id,
            "grantee": grantee,
            "granted_by": granted_by,
            "granted_at": self._now(),
            "valid_until": valid_until,
            "used": False
        }
        return self._add_node("exception_grant", gid, props)

    # =========================================================================
    # Policy Evaluation
    # =========================================================================

    def evaluate(
        self,
        context: Dict[str, Any],
        policies: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Evaluate policies against a context.

        Args:
            context: The context to evaluate (contains data to check)
            policies: Optional list of policy IDs to evaluate (default: all active)

        Returns:
            {
                "result": "allow" | "deny" | "escalate",
                "matched_rules": List[Dict],
                "explanation": str,
                "exceptions_available": List[Dict]
            }
        """
        # Get policies to evaluate
        if policies:
            policy_list = [self.get_policy(p) for p in policies]
            policy_list = [p for p in policy_list if p]
        else:
            policy_list = self.list_policies(status=PolicyStatus.ACTIVE)

        # Sort by priority
        policy_list = sorted(policy_list, key=lambda p: p.get("priority", 0), reverse=True)

        matched_rules = []
        exceptions_available = []
        final_result = "allow"
        explanation_parts = []

        for policy in policy_list:
            rules = self.list_rules(policy["id"])

            for rule in rules:
                if not rule.get("active", True):
                    continue

                # Evaluate condition
                match_result = self._evaluate_condition(rule["condition"], context)

                if match_result["matched"]:
                    matched_rules.append({
                        "policy": policy["name"],
                        "rule_id": rule["id"],
                        "condition": rule["condition"],
                        "action": rule["action"]
                    })

                    action = rule["action"]
                    explanation_parts.append(
                        f"Rule {rule['id']} in policy {policy['name']} matched: {rule['condition']} -> {action}"
                    )

                    # Check for exceptions
                    if rule.get("exception_allows"):
                        exceptions_available.append({
                            "rule_id": rule["id"],
                            "exception": rule["exception_allows"]
                        })

                    # Determine result based on action
                    if "deny" in action.lower():
                        final_result = "deny"
                    elif "escalate" in action.lower() or "require" in action.lower():
                        if final_result != "deny":
                            final_result = "escalate"

        # Record evaluation
        eval_id = self._generate_id("e")
        import hashlib
        context_hash = hashlib.md5(str(context).encode()).hexdigest()[:8]
        self._add_node("evaluation", eval_id, {
            "context_hash": context_hash,
            "result": final_result,
            "matched_rules": [r["rule_id"] for r in matched_rules],
            "timestamp": self._now()
        })

        return {
            "result": final_result,
            "matched_rules": matched_rules,
            "explanation": "; ".join(explanation_parts) if explanation_parts else "No rules matched",
            "exceptions_available": exceptions_available,
            "evaluation_id": eval_id
        }

    def _evaluate_condition(self, condition: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Evaluate a condition expression against context"""
        try:
            # Simple expression evaluation
            # Supports: ==, !=, >, <, >=, <=, in, contains

            # Replace context references
            expr = condition
            for key, value in context.items():
                # Handle nested keys
                expr = expr.replace(f"{key}", repr(value) if isinstance(value, str) else str(value))

            # Safe eval with limited builtins
            result = eval(expr, {"__builtins__": {}}, {
                "True": True, "False": False, "None": None,
                "contains": lambda x, y: y in x if x else False
            })

            return {"matched": bool(result), "error": None}
        except Exception as e:
            return {"matched": False, "error": str(e)}

    def _eval_attribute(self, expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate attribute comparison"""
        return self._evaluate_condition(expr, context)["matched"]

    def _eval_threshold(self, expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate threshold comparison"""
        return self._evaluate_condition(expr, context)["matched"]

    def _eval_function(self, expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate function-based condition"""
        # Extract function name and apply to context
        match = re.match(r"(\w+)\((.*)\)", expr)
        if match:
            func_name = match.group(1)
            arg = match.group(2)
            value = context.get(arg.strip())

            # Built-in functions
            if func_name == "contains_pii":
                # Simple PII detection
                if isinstance(value, str):
                    pii_patterns = [
                        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
                    ]
                    for pattern in pii_patterns:
                        if re.search(pattern, value):
                            return True
                return False

            if func_name == "is_sensitive":
                return context.get("classification") in ["secret", "confidential"]

        return False

    def _eval_computed(self, expr: str, context: Dict[str, Any]) -> bool:
        """Evaluate computed condition"""
        return self._evaluate_condition(expr, context)["matched"]

    # =========================================================================
    # Evaluation History
    # =========================================================================

    def get_evaluation_history(
        self,
        rule_id: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get recent evaluations"""
        evaluations = self._find_nodes("evaluation")

        if rule_id:
            evaluations = [
                e for e in evaluations
                if rule_id in e.get("matched_rules", [])
            ]

        # Sort by timestamp descending
        evaluations = sorted(
            evaluations,
            key=lambda e: e.get("timestamp", ""),
            reverse=True
        )[:limit]

        return evaluations

    def get_stats(self) -> Dict[str, Any]:
        """Get policy store statistics"""
        base_stats = super().get_stats()
        policies = self._find_nodes("policy")
        rules = self._find_nodes("rule")
        evaluations = self._find_nodes("evaluation")

        return {
            **base_stats,
            "policies": len(policies),
            "active_policies": len([p for p in policies if p.get("status") == "active"]),
            "rules": len(rules),
            "active_rules": len([r for r in rules if r.get("active")]),
            "evaluations": len(evaluations)
        }
