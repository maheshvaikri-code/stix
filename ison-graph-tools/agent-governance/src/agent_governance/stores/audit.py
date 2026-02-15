"""
Audit Trail Store
=================

Tracks decisions, provenance, rationale, and effects for accountability.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING
import hashlib

from .base import BaseStore
from ..schema import Decision, DecisionInput, DecisionRationale, DecisionEffect, Counterfactual

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class AuditStore(BaseStore):
    """Store for decision audit trail"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "audit")

    # =========================================================================
    # Decision Recording
    # =========================================================================

    def record_decision(
        self,
        agent_id: str,
        decision_type: str,
        outcome: str,
        confidence: float,
        reversible: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        decision_id: Optional[str] = None
    ) -> str:
        """Record a decision made by an agent"""
        did = decision_id or self._generate_id("dc")
        props = {
            "agent_id": agent_id,
            "type": decision_type,
            "outcome": outcome,
            "confidence": confidence,
            "reversible": reversible,
            "timestamp": self._now(),
            **(metadata or {})
        }
        return self._add_node("decision", did, props)

    def get_decision(self, decision_id: str) -> Optional[Dict[str, Any]]:
        """Get decision by ID"""
        return self._get_node("decision", decision_id)

    def list_decisions(
        self,
        agent_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """List decisions with optional filters"""
        decisions = self._find_nodes("decision")

        if agent_id:
            decisions = [d for d in decisions if d.get("agent_id") == agent_id]
        if decision_type:
            decisions = [d for d in decisions if d.get("type") == decision_type]

        # Sort by timestamp descending
        decisions = sorted(decisions, key=lambda d: d.get("timestamp", ""), reverse=True)
        return decisions[:limit]

    # =========================================================================
    # Decision Inputs
    # =========================================================================

    def add_input(
        self,
        decision_id: str,
        input_type: str,
        source: str,
        content: Any,
        sensitivity: str = "low",
        input_id: Optional[str] = None
    ) -> str:
        """Record an input that influenced a decision"""
        iid = input_id or self._generate_id("di")

        # Hash the content for privacy
        content_hash = hashlib.sha256(str(content).encode()).hexdigest()[:16]

        props = {
            "decision_id": decision_id,
            "input_type": input_type,
            "source": source,
            "content_hash": content_hash,
            "sensitivity": sensitivity,
            "timestamp": self._now()
        }
        self._add_node("decision_input", iid, props)

        # Link to decision
        self._add_edge(
            "decision_input", iid,
            "DECISION_INPUT",
            "decision", decision_id,
            {"weight": 1.0}
        )

        return iid

    def get_inputs(self, decision_id: str) -> List[Dict[str, Any]]:
        """Get all inputs for a decision"""
        return self._find_nodes("decision_input", decision_id=decision_id)

    # =========================================================================
    # Decision Rationale
    # =========================================================================

    def add_rationale(
        self,
        decision_id: str,
        reasoning_type: str,
        explanation: str,
        verifiable: bool = True,
        rationale_id: Optional[str] = None
    ) -> str:
        """Record the rationale for a decision"""
        rid = rationale_id or self._generate_id("dr")
        props = {
            "decision_id": decision_id,
            "reasoning_type": reasoning_type,
            "explanation": explanation,
            "verifiable": verifiable,
            "timestamp": self._now()
        }
        self._add_node("decision_rationale", rid, props)

        self._add_edge(
            "decision_rationale", rid,
            "DECISION_RATIONALE",
            "decision", decision_id,
            {}
        )

        return rid

    def get_rationale(self, decision_id: str) -> List[Dict[str, Any]]:
        """Get rationale for a decision"""
        return self._find_nodes("decision_rationale", decision_id=decision_id)

    # =========================================================================
    # Decision Effects
    # =========================================================================

    def add_effect(
        self,
        decision_id: str,
        effect_type: str,
        target: str,
        reversible: bool = True,
        effect_id: Optional[str] = None
    ) -> str:
        """Record an effect of a decision"""
        eid = effect_id or self._generate_id("de")
        props = {
            "decision_id": decision_id,
            "effect_type": effect_type,
            "target": target,
            "reversible": reversible,
            "reversed": False,
            "timestamp": self._now()
        }
        self._add_node("decision_effect", eid, props)

        self._add_edge(
            "decision", decision_id,
            "DECISION_EFFECT",
            "decision_effect", eid,
            {}
        )

        return eid

    def reverse_effect(self, effect_id: str, reversal_reason: str):
        """Mark an effect as reversed"""
        self._update_node("decision_effect", effect_id, {
            "reversed": True,
            "reversed_at": self._now(),
            "reversal_reason": reversal_reason
        })

    def get_effects(self, decision_id: str) -> List[Dict[str, Any]]:
        """Get effects of a decision"""
        return self._find_nodes("decision_effect", decision_id=decision_id)

    # =========================================================================
    # Decision Chains
    # =========================================================================

    def link_decisions(
        self,
        source_decision_id: str,
        target_decision_id: str,
        relationship: str,
        causality: str = "indirect"
    ):
        """Link related decisions in a chain"""
        self._add_edge(
            "decision", source_decision_id,
            "DECISION_CHAIN",
            "decision", target_decision_id,
            {"relationship": relationship, "causality": causality}
        )

    def get_decision_chain(
        self,
        decision_id: str,
        direction: str = "both",
        max_depth: int = 5
    ) -> List[Dict[str, Any]]:
        """Get the chain of related decisions"""
        chain = []
        visited = set()

        def trace(did: str, depth: int, dir_type: str):
            if did in visited or depth > max_depth:
                return
            visited.add(did)

            if dir_type in ["forward", "both"]:
                forward_edges = self._find_edges(
                    source_type="decision", source_id=did,
                    rel_type="DECISION_CHAIN"
                )
                for edge in forward_edges:
                    target_id = edge["target"][1]
                    decision = self.get_decision(target_id)
                    if decision:
                        chain.append({
                            "direction": "forward",
                            "depth": depth,
                            "relationship": edge["properties"].get("relationship"),
                            **decision
                        })
                        trace(target_id, depth + 1, "forward")

            if dir_type in ["backward", "both"]:
                backward_edges = self._find_edges(
                    rel_type="DECISION_CHAIN",
                    target_type="decision", target_id=did
                )
                for edge in backward_edges:
                    source_id = edge["source"][1]
                    decision = self.get_decision(source_id)
                    if decision:
                        chain.append({
                            "direction": "backward",
                            "depth": depth,
                            "relationship": edge["properties"].get("relationship"),
                            **decision
                        })
                        trace(source_id, depth + 1, "backward")

        trace(decision_id, 1, direction)
        return chain

    # =========================================================================
    # Counterfactuals
    # =========================================================================

    def add_counterfactual(
        self,
        decision_id: str,
        if_different: str,
        would_result: str,
        counterfactual_id: Optional[str] = None
    ) -> str:
        """Record a counterfactual (what would have happened)"""
        cid = counterfactual_id or self._generate_id("cf")
        props = {
            "decision_id": decision_id,
            "if_different": if_different,
            "would_result": would_result,
            "timestamp": self._now()
        }
        self._add_node("counterfactual", cid, props)

        self._add_edge(
            "counterfactual", cid,
            "COUNTERFACTUAL",
            "decision", decision_id,
            {}
        )

        return cid

    def get_counterfactuals(self, decision_id: str) -> List[Dict[str, Any]]:
        """Get counterfactuals for a decision"""
        return self._find_nodes("counterfactual", decision_id=decision_id)

    # =========================================================================
    # Full Decision Trace
    # =========================================================================

    def get_full_trace(self, decision_id: str) -> Dict[str, Any]:
        """Get complete provenance trace for a decision"""
        decision = self.get_decision(decision_id)
        if not decision:
            return {"error": "Decision not found"}

        return {
            "decision": decision,
            "inputs": self.get_inputs(decision_id),
            "rationale": self.get_rationale(decision_id),
            "effects": self.get_effects(decision_id),
            "counterfactuals": self.get_counterfactuals(decision_id),
            "chain": self.get_decision_chain(decision_id, max_depth=3),
            "traced_at": self._now()
        }

    def explain_decision(self, decision_id: str) -> str:
        """Generate human-readable explanation of a decision"""
        trace = self.get_full_trace(decision_id)

        if "error" in trace:
            return f"Could not explain: {trace['error']}"

        decision = trace["decision"]
        parts = [
            f"Decision {decision_id} by {decision.get('agent_id')}:",
            f"  Type: {decision.get('type')}",
            f"  Outcome: {decision.get('outcome')}",
            f"  Confidence: {decision.get('confidence', 0):.2%}",
            f"  Timestamp: {decision.get('timestamp')}",
            ""
        ]

        if trace["inputs"]:
            parts.append("Inputs:")
            for inp in trace["inputs"]:
                parts.append(f"  - {inp.get('input_type')} from {inp.get('source')}")

        if trace["rationale"]:
            parts.append("\nRationale:")
            for rat in trace["rationale"]:
                parts.append(f"  - [{rat.get('reasoning_type')}] {rat.get('explanation')}")

        if trace["effects"]:
            parts.append("\nEffects:")
            for eff in trace["effects"]:
                status = "reversed" if eff.get("reversed") else "active"
                parts.append(f"  - {eff.get('effect_type')} on {eff.get('target')} ({status})")

        if trace["counterfactuals"]:
            parts.append("\nCounterfactuals:")
            for cf in trace["counterfactuals"]:
                parts.append(f"  - If {cf.get('if_different')}: would {cf.get('would_result')}")

        return "\n".join(parts)

    # =========================================================================
    # Audit Queries
    # =========================================================================

    def query_decisions(
        self,
        query_type: str,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """Query decisions by various criteria"""
        decisions = self._find_nodes("decision")

        if query_type == "by_agent":
            agent_id = kwargs.get("agent_id")
            return [d for d in decisions if d.get("agent_id") == agent_id]

        elif query_type == "by_type":
            decision_type = kwargs.get("decision_type")
            return [d for d in decisions if d.get("type") == decision_type]

        elif query_type == "by_outcome":
            outcome = kwargs.get("outcome")
            return [d for d in decisions if d.get("outcome") == outcome]

        elif query_type == "low_confidence":
            threshold = kwargs.get("threshold", 0.7)
            return [d for d in decisions if d.get("confidence", 1.0) < threshold]

        elif query_type == "reversible":
            return [d for d in decisions if d.get("reversible", True)]

        return decisions

    def get_stats(self) -> Dict[str, Any]:
        """Get audit store statistics"""
        base_stats = super().get_stats()
        decisions = self._find_nodes("decision")
        inputs = self._find_nodes("decision_input")
        rationales = self._find_nodes("decision_rationale")
        effects = self._find_nodes("decision_effect")

        return {
            **base_stats,
            "decisions": len(decisions),
            "inputs": len(inputs),
            "rationales": len(rationales),
            "effects": len(effects),
            "reversed_effects": len([e for e in effects if e.get("reversed")])
        }
