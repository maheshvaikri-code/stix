"""
Governance Memory Integration
=============================

Integrates unified-governance with agent-memory and ISONCache for:
- Compliance decision memory and learning
- Cached governance context with token budgeting
- Session continuity for governance workflows
- Pattern detection and proactive warnings
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
import uuid

from ison_graph import ISONGraph

from .schema import (
    GovernanceDomain,
    ComplianceStatus,
    CrossDomainRiskLevel,
    IntegrationEventType,
)


# =============================================================================
# Data Classes for Governance Memory
# =============================================================================

@dataclass
class ComplianceDecisionMemory:
    """Memory of a compliance decision for learning."""
    decision_id: str
    agent_id: str
    action: str
    pii_types: List[str]
    outcome: str  # permitted, blocked, warning
    reason: str
    regulations_involved: List[str]
    context_hash: str  # For finding similar situations
    timestamp: str
    feedback: Optional[str] = None  # Was decision correct?
    learned_pattern: Optional[str] = None


@dataclass
class GovernancePattern:
    """Learned pattern from governance decisions."""
    pattern_id: str
    name: str
    pattern_type: str  # blocking, warning, permission
    signature: Dict[str, Any]  # What triggers this pattern
    frequency: int
    confidence: float
    last_seen: str
    examples: List[str] = field(default_factory=list)


@dataclass
class GovernanceSession:
    """Session state for governance workflows."""
    session_id: str
    started_at: str
    task: str
    checks_performed: List[Dict[str, Any]] = field(default_factory=list)
    decisions_made: List[str] = field(default_factory=list)
    open_issues: List[str] = field(default_factory=list)
    context_cache_key: Optional[str] = None


@dataclass
class CachedGovernanceContext:
    """Cached governance context for LLM injection."""
    context_id: str
    ison_output: str
    tokens_used: int
    token_budget: int
    categories_included: List[str]
    categories_truncated: List[str]
    cache_hit: bool
    generated_at: str


# =============================================================================
# Governance Memory Store
# =============================================================================

class GovernanceMemoryStore:
    """
    Store for governance-related memories.

    Provides:
    - Compliance decision memory
    - Pattern learning from decisions
    - Governance conventions
    - Warning patterns
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph
        self.domain = "governance_memory"

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _add_node(self, node_type: str, node_id: str, properties: Dict[str, Any]) -> str:
        props = {**properties, "_domain": self.domain, "_created_at": self._now()}
        self.graph.add_node(node_type, node_id, props)
        return node_id

    def _get_node(self, node_type: str, node_id: str) -> Optional[Dict[str, Any]]:
        node = self.graph.get_node(node_type, node_id)
        if node:
            return {"id": node.id, "type": node.type, **node.properties}
        return None

    def _find_nodes(self, node_type: str, **filters) -> List[Dict[str, Any]]:
        results = []
        for node in self.graph.nodes():
            if node.type != node_type:
                continue
            match = True
            for key, value in filters.items():
                if node.properties.get(key) != value:
                    match = False
                    break
            if match:
                results.append({"id": node.id, "type": node.type, **node.properties})
        return results

    # =========================================================================
    # Compliance Decision Memory
    # =========================================================================

    def record_decision(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        outcome: str,
        reason: str,
        regulations_involved: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record a compliance decision for learning."""
        decision_id = self._generate_id("gov_decision")

        # Create context hash for similarity matching
        context_hash = self._hash_context(agent_id, action, pii_types)

        self._add_node("governance_decision_memory", decision_id, {
            "agent_id": agent_id,
            "action": action,
            "pii_types": pii_types,
            "outcome": outcome,
            "reason": reason,
            "regulations_involved": regulations_involved,
            "context_hash": context_hash,
            "context": context or {},
            "feedback": None,
            "learned_pattern": None,
        })

        # Check if this creates a pattern
        self._detect_pattern(agent_id, action, pii_types, outcome)

        return decision_id

    def _hash_context(self, agent_id: str, action: str, pii_types: List[str]) -> str:
        """Create a hash for context similarity matching."""
        # Simple hash based on action and sorted PII types
        pii_key = ",".join(sorted(pii_types))
        return f"{action}:{pii_key}"

    def add_feedback(
        self,
        decision_id: str,
        feedback: str,
        was_correct: bool,
    ) -> Dict[str, Any]:
        """Add feedback to a decision (reinforcement learning)."""
        decision = self._get_node("governance_decision_memory", decision_id)
        if not decision:
            return {"error": "Decision not found"}

        # Update decision with feedback
        decision["feedback"] = feedback
        decision["was_correct"] = was_correct
        decision["feedback_at"] = self._now()

        self.graph.add_node("governance_decision_memory", decision_id, decision)

        # If incorrect, record as learning opportunity
        if not was_correct:
            self._record_learning(decision, feedback)

        return {"updated": True, "decision_id": decision_id}

    def _record_learning(self, decision: Dict[str, Any], feedback: str) -> None:
        """Record a learning from incorrect decision."""
        learning_id = self._generate_id("gov_learning")

        self._add_node("governance_learning", learning_id, {
            "decision_id": decision.get("id"),
            "action": decision.get("action"),
            "pii_types": decision.get("pii_types"),
            "original_outcome": decision.get("outcome"),
            "feedback": feedback,
            "learning_type": "correction",
        })

    def get_similar_decisions(
        self,
        action: str,
        pii_types: List[str],
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find similar past decisions for context."""
        context_hash = self._hash_context("", action, pii_types)

        all_decisions = self._find_nodes("governance_decision_memory")

        # Find decisions with matching or similar context
        similar = []
        for decision in all_decisions:
            if decision.get("context_hash") == context_hash:
                similar.append(decision)
            elif decision.get("action") == action:
                # Partial match on action
                pii_overlap = set(pii_types) & set(decision.get("pii_types", []))
                if pii_overlap:
                    similar.append(decision)

        # Sort by recency
        similar.sort(key=lambda x: x.get("_created_at", ""), reverse=True)

        return similar[:limit]

    # =========================================================================
    # Pattern Detection and Learning
    # =========================================================================

    def _detect_pattern(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        outcome: str,
    ) -> Optional[str]:
        """Detect if this decision forms a pattern."""
        # Find similar decisions
        similar = self.get_similar_decisions(action, pii_types, limit=10)

        # Count outcomes
        outcome_counts = {}
        for dec in similar:
            out = dec.get("outcome")
            outcome_counts[out] = outcome_counts.get(out, 0) + 1

        # If we have 3+ similar outcomes, it's a pattern
        if outcome_counts.get(outcome, 0) >= 3:
            pattern_id = self._create_or_update_pattern(
                action=action,
                pii_types=pii_types,
                outcome=outcome,
                frequency=outcome_counts[outcome],
            )
            return pattern_id

        return None

    def _create_or_update_pattern(
        self,
        action: str,
        pii_types: List[str],
        outcome: str,
        frequency: int,
    ) -> str:
        """Create or update a governance pattern."""
        # Check for existing pattern
        signature = {"action": action, "pii_types": sorted(pii_types)}
        existing = self._find_patterns_by_signature(signature)

        if existing:
            # Update existing pattern
            pattern = existing[0]
            pattern["frequency"] = frequency
            pattern["last_seen"] = self._now()
            pattern["confidence"] = min(1.0, frequency / 10.0)
            self.graph.add_node("governance_pattern", pattern["id"], pattern)
            return pattern["id"]
        else:
            # Create new pattern
            pattern_id = self._generate_id("gov_pattern")
            self._add_node("governance_pattern", pattern_id, {
                "name": f"{outcome}_{action}_pattern",
                "pattern_type": outcome,
                "signature": signature,
                "frequency": frequency,
                "confidence": min(1.0, frequency / 10.0),
                "last_seen": self._now(),
                "examples": [],
            })
            return pattern_id

    def _find_patterns_by_signature(
        self,
        signature: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Find patterns matching a signature."""
        all_patterns = self._find_nodes("governance_pattern")

        matching = []
        for pattern in all_patterns:
            pat_sig = pattern.get("signature", {})
            if (pat_sig.get("action") == signature.get("action") and
                set(pat_sig.get("pii_types", [])) == set(signature.get("pii_types", []))):
                matching.append(pattern)

        return matching

    def get_patterns_for_action(
        self,
        action: str,
        pii_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get learned patterns for an action."""
        all_patterns = self._find_nodes("governance_pattern")

        matching = []
        for pattern in all_patterns:
            sig = pattern.get("signature", {})
            if sig.get("action") == action:
                if pii_types is None:
                    matching.append(pattern)
                elif set(sig.get("pii_types", [])) & set(pii_types):
                    matching.append(pattern)

        # Sort by confidence
        matching.sort(key=lambda x: x.get("confidence", 0), reverse=True)

        return matching

    # =========================================================================
    # Governance Conventions
    # =========================================================================

    def add_convention(
        self,
        category: str,
        rule: str,
        description: str,
        regulations: Optional[List[str]] = None,
        enforced: bool = True,
    ) -> str:
        """Add a governance convention."""
        conv_id = self._generate_id("gov_convention")

        self._add_node("governance_convention", conv_id, {
            "category": category,
            "rule": rule,
            "description": description,
            "regulations": regulations or [],
            "enforced": enforced,
            "violations": 0,
        })

        return conv_id

    def record_violation(
        self,
        convention_id: str,
        agent_id: str,
        context: str,
    ) -> Dict[str, Any]:
        """Record a convention violation."""
        convention = self._get_node("governance_convention", convention_id)
        if not convention:
            return {"error": "Convention not found"}

        # Increment violation count
        convention["violations"] = convention.get("violations", 0) + 1
        convention["last_violation"] = self._now()
        self.graph.add_node("governance_convention", convention_id, convention)

        # Record violation event
        violation_id = self._generate_id("violation")
        self._add_node("governance_violation", violation_id, {
            "convention_id": convention_id,
            "agent_id": agent_id,
            "context": context,
        })

        return {
            "recorded": True,
            "convention_id": convention_id,
            "total_violations": convention["violations"],
        }

    def get_conventions(
        self,
        category: Optional[str] = None,
        enforced_only: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get governance conventions."""
        conventions = self._find_nodes("governance_convention")

        if category:
            conventions = [c for c in conventions if c.get("category") == category]

        if enforced_only:
            conventions = [c for c in conventions if c.get("enforced", True)]

        return conventions

    # =========================================================================
    # Warning Patterns
    # =========================================================================

    def add_warning_pattern(
        self,
        name: str,
        trigger: Dict[str, Any],
        warning_message: str,
        severity: str = "medium",
        auto_block: bool = False,
    ) -> str:
        """Add a proactive warning pattern."""
        pattern_id = self._generate_id("warning_pattern")

        self._add_node("governance_warning_pattern", pattern_id, {
            "name": name,
            "trigger": trigger,
            "warning_message": warning_message,
            "severity": severity,
            "auto_block": auto_block,
            "triggered_count": 0,
        })

        return pattern_id

    def check_warnings(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Check for applicable warning patterns."""
        warnings = []

        # Get all warning patterns
        patterns = self._find_nodes("governance_warning_pattern")

        for pattern in patterns:
            trigger = pattern.get("trigger", {})

            # Check if trigger matches
            if self._matches_trigger(trigger, action, pii_types, context):
                warnings.append({
                    "pattern_id": pattern.get("id"),
                    "name": pattern.get("name"),
                    "message": pattern.get("warning_message"),
                    "severity": pattern.get("severity"),
                    "auto_block": pattern.get("auto_block", False),
                })

                # Update triggered count
                pattern["triggered_count"] = pattern.get("triggered_count", 0) + 1
                pattern["last_triggered"] = self._now()
                self.graph.add_node("governance_warning_pattern", pattern["id"], pattern)

        # Also check learned patterns
        learned = self.get_patterns_for_action(action, pii_types)
        for lp in learned:
            if lp.get("pattern_type") == "blocked" and lp.get("confidence", 0) > 0.7:
                warnings.append({
                    "pattern_id": lp.get("id"),
                    "name": f"Learned: {lp.get('name')}",
                    "message": f"This action was blocked {lp.get('frequency', 0)} times before",
                    "severity": "high",
                    "auto_block": False,
                    "learned": True,
                })

        return warnings

    def _matches_trigger(
        self,
        trigger: Dict[str, Any],
        action: str,
        pii_types: List[str],
        context: Optional[Dict[str, Any]],
    ) -> bool:
        """Check if a trigger matches the current situation."""
        # Action match
        if "action" in trigger and trigger["action"] != action:
            return False

        # PII type match
        if "pii_types" in trigger:
            required_pii = set(trigger["pii_types"])
            if not required_pii & set(pii_types):
                return False

        # Any PII type match
        if "any_pii_type" in trigger:
            if trigger["any_pii_type"] not in pii_types:
                return False

        # Context conditions
        if "context_contains" in trigger and context:
            for key, value in trigger["context_contains"].items():
                if context.get(key) != value:
                    return False

        return True

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get governance memory statistics."""
        decisions = self._find_nodes("governance_decision_memory")
        patterns = self._find_nodes("governance_pattern")
        conventions = self._find_nodes("governance_convention")
        warnings = self._find_nodes("governance_warning_pattern")
        learnings = self._find_nodes("governance_learning")

        # Count by outcome
        outcome_counts = {}
        for dec in decisions:
            outcome = dec.get("outcome", "unknown")
            outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1

        # Count by pattern confidence
        high_confidence_patterns = len([p for p in patterns if p.get("confidence", 0) > 0.7])

        return {
            "total_decisions": len(decisions),
            "total_patterns": len(patterns),
            "high_confidence_patterns": high_confidence_patterns,
            "total_conventions": len(conventions),
            "total_warning_patterns": len(warnings),
            "total_learnings": len(learnings),
            "decisions_by_outcome": outcome_counts,
        }


# =============================================================================
# Cached Governance Context
# =============================================================================

class CachedGovernanceContext:
    """
    Token-efficient cached context for governance decisions.

    Uses ISONCache patterns for:
    - Caching compliance check results
    - Token-budgeted context retrieval
    - ISON-formatted output for LLM injection
    """

    # Priority of governance context categories (higher = more important)
    CATEGORY_PRIORITIES = {
        "active_blocks": 100,       # Always include
        "warning_patterns": 95,      # Critical warnings
        "recent_violations": 90,     # Recent issues
        "conventions": 80,           # Rules to follow
        "learned_patterns": 75,      # Learned behaviors
        "subject_status": 70,        # Subject consent/opt-out
        "pii_requirements": 65,      # PII-specific requirements
        "agent_access": 60,          # Agent permissions
        "recent_decisions": 50,      # Recent decisions
        "regulations": 40,           # Regulation details
    }

    def __init__(
        self,
        governance_engine,
        memory_store: GovernanceMemoryStore,
        cache=None,  # ISONCache instance
    ):
        self.engine = governance_engine
        self.memory = memory_store
        self.cache = cache
        self._context_cache: Dict[str, Dict[str, Any]] = {}

    def get_context(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_subject_id: Optional[str] = None,
        token_budget: int = 2000,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        force_refresh: bool = False,
    ) -> Dict[str, Any]:
        """
        Get governance context within token budget.

        Returns ISON-formatted context ready for LLM injection.
        """
        cache_key = self._make_cache_key(agent_id, action, pii_types, data_subject_id)

        # Check cache
        if not force_refresh and cache_key in self._context_cache:
            cached = self._context_cache[cache_key]
            if self._is_cache_valid(cached):
                cached["cache_hit"] = True
                return cached

        # Build context
        context = self._build_context(
            agent_id, action, pii_types, data_subject_id,
            token_budget, include, exclude
        )

        # Cache it
        self._context_cache[cache_key] = context

        return context

    def _make_cache_key(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_subject_id: Optional[str],
    ) -> str:
        """Create cache key."""
        pii_key = ",".join(sorted(pii_types))
        subject_key = data_subject_id or "none"
        return f"{agent_id}:{action}:{pii_key}:{subject_key}"

    def _is_cache_valid(self, cached: Dict[str, Any], max_age_seconds: int = 60) -> bool:
        """Check if cached context is still valid."""
        generated_at = cached.get("generated_at", "")
        if not generated_at:
            return False

        try:
            gen_time = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - gen_time).total_seconds()
            return age < max_age_seconds
        except Exception:
            return False

    def _build_context(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_subject_id: Optional[str],
        token_budget: int,
        include: Optional[List[str]],
        exclude: Optional[List[str]],
    ) -> Dict[str, Any]:
        """Build governance context."""
        context_id = self.memory._generate_id("gov_ctx")
        categories_included = []
        categories_truncated = []
        tokens_used = 0

        # Determine which categories to include
        categories = list(self.CATEGORY_PRIORITIES.keys())
        if include:
            categories = [c for c in categories if c in include]
        if exclude:
            categories = [c for c in categories if c not in exclude]

        # Sort by priority
        categories.sort(key=lambda c: self.CATEGORY_PRIORITIES.get(c, 0), reverse=True)

        # Build context sections
        sections = []

        for category in categories:
            section = self._build_section(
                category, agent_id, action, pii_types, data_subject_id
            )

            if not section:
                continue

            # Estimate tokens (rough: 4 chars per token)
            section_tokens = len(str(section)) // 4

            if tokens_used + section_tokens <= token_budget:
                sections.append(section)
                tokens_used += section_tokens
                categories_included.append(category)
            else:
                categories_truncated.append(category)

        # Format as ISON
        ison_output = self._format_as_ison(sections)

        return {
            "context_id": context_id,
            "ison_output": ison_output,
            "tokens_used": tokens_used,
            "token_budget": token_budget,
            "categories_included": categories_included,
            "categories_truncated": categories_truncated,
            "cache_hit": False,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    def _build_section(
        self,
        category: str,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_subject_id: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Build a single context section."""
        if category == "active_blocks":
            blocks = self.engine.agent_integration.is_action_blocked(agent_id, action)
            if blocks.get("blocked"):
                return {"category": "active_blocks", "data": blocks}

        elif category == "warning_patterns":
            warnings = self.memory.check_warnings(agent_id, action, pii_types)
            if warnings:
                return {"category": "warnings", "data": warnings}

        elif category == "conventions":
            conventions = self.memory.get_conventions(enforced_only=True)
            if conventions:
                return {"category": "conventions", "data": conventions[:5]}

        elif category == "learned_patterns":
            patterns = self.memory.get_patterns_for_action(action, pii_types)
            if patterns:
                return {"category": "learned_patterns", "data": patterns[:3]}

        elif category == "subject_status":
            if data_subject_id:
                status = self.engine.subjects.get_cross_regulation_status(data_subject_id)
                if not status.get("error"):
                    return {"category": "subject_status", "data": status}

        elif category == "pii_requirements":
            reqs = self.engine.regulatory.get_cross_regulation_requirements(pii_types)
            if reqs.get("applicable_regulations"):
                return {"category": "pii_requirements", "data": reqs}

        elif category == "agent_access":
            access_info = []
            for pii_type in pii_types:
                access = self.engine.agent_integration.check_agent_pii_access(agent_id, pii_type)
                access_info.append({"pii_type": pii_type, **access})
            if access_info:
                return {"category": "agent_access", "data": access_info}

        elif category == "recent_decisions":
            decisions = self.memory.get_similar_decisions(action, pii_types, limit=3)
            if decisions:
                return {"category": "recent_decisions", "data": decisions}

        return None

    def _format_as_ison(self, sections: List[Dict[str, Any]]) -> str:
        """Format sections as ISON for LLM context."""
        lines = ["[GOVERNANCE_CONTEXT]"]

        for section in sections:
            category = section.get("category", "unknown")
            data = section.get("data", {})

            lines.append(f"\n<{category}>")

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        for key, value in item.items():
                            if not key.startswith("_"):
                                lines.append(f"  {key}: {value}")
                        lines.append("")
                    else:
                        lines.append(f"  - {item}")
            elif isinstance(data, dict):
                for key, value in data.items():
                    if not key.startswith("_"):
                        lines.append(f"  {key}: {value}")

            lines.append(f"</{category}>")

        lines.append("\n[/GOVERNANCE_CONTEXT]")

        return "\n".join(lines)

    def invalidate(self, pattern: Optional[str] = None) -> int:
        """Invalidate cached contexts."""
        if pattern is None:
            count = len(self._context_cache)
            self._context_cache.clear()
            return count

        # Pattern-based invalidation
        to_remove = [k for k in self._context_cache if pattern in k]
        for key in to_remove:
            del self._context_cache[key]
        return len(to_remove)


# =============================================================================
# Governance Session Manager
# =============================================================================

class GovernanceSessionManager:
    """
    Manages governance workflow sessions for continuity.

    Tracks:
    - Checks performed during session
    - Decisions made
    - Open issues requiring follow-up
    - Session handoff data
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph
        self.domain = "governance_session"
        self._current_session: Optional[str] = None

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _add_node(self, node_type: str, node_id: str, properties: Dict[str, Any]) -> str:
        props = {**properties, "_domain": self.domain, "_created_at": self._now()}
        self.graph.add_node(node_type, node_id, props)
        return node_id

    def _get_node(self, node_type: str, node_id: str) -> Optional[Dict[str, Any]]:
        node = self.graph.get_node(node_type, node_id)
        if node:
            return {"id": node.id, "type": node.type, **node.properties}
        return None

    def start_session(self, task: str) -> str:
        """Start a new governance session."""
        session_id = self._generate_id("gov_session")

        self._add_node("governance_session", session_id, {
            "task": task,
            "status": "active",
            "checks_performed": [],
            "decisions_made": [],
            "open_issues": [],
        })

        self._current_session = session_id
        return session_id

    def get_current_session(self) -> Optional[Dict[str, Any]]:
        """Get current active session."""
        if self._current_session:
            return self._get_node("governance_session", self._current_session)
        return None

    def record_check(
        self,
        check_type: str,
        target: str,
        result: Dict[str, Any],
    ) -> None:
        """Record a compliance check in current session."""
        session = self.get_current_session()
        if not session:
            return

        checks = session.get("checks_performed", [])
        checks.append({
            "check_type": check_type,
            "target": target,
            "result_summary": {
                "permitted": result.get("permitted"),
                "status": result.get("overall_status") or result.get("status"),
                "issues_count": len(result.get("blocking_issues", [])) + len(result.get("warnings", [])),
            },
            "timestamp": self._now(),
        })

        session["checks_performed"] = checks
        self.graph.add_node("governance_session", self._current_session, session)

    def record_decision(
        self,
        decision: str,
        rationale: str,
    ) -> None:
        """Record a decision made during session."""
        session = self.get_current_session()
        if not session:
            return

        decisions = session.get("decisions_made", [])
        decisions.append({
            "decision": decision,
            "rationale": rationale,
            "timestamp": self._now(),
        })

        session["decisions_made"] = decisions
        self.graph.add_node("governance_session", self._current_session, session)

    def add_open_issue(self, issue: str, priority: str = "medium") -> None:
        """Add an open issue requiring follow-up."""
        session = self.get_current_session()
        if not session:
            return

        issues = session.get("open_issues", [])
        issues.append({
            "issue": issue,
            "priority": priority,
            "added_at": self._now(),
        })

        session["open_issues"] = issues
        self.graph.add_node("governance_session", self._current_session, session)

    def end_session(
        self,
        outcome: str,
        summary: str = "",
    ) -> Dict[str, Any]:
        """End the current session."""
        session = self.get_current_session()
        if not session:
            return {"error": "No active session"}

        session["status"] = "completed"
        session["outcome"] = outcome
        session["summary"] = summary
        session["ended_at"] = self._now()

        self.graph.add_node("governance_session", self._current_session, session)

        result = {
            "session_id": self._current_session,
            "checks_count": len(session.get("checks_performed", [])),
            "decisions_count": len(session.get("decisions_made", [])),
            "open_issues_count": len(session.get("open_issues", [])),
            "outcome": outcome,
        }

        self._current_session = None
        return result

    def get_session_handoff(self) -> Dict[str, Any]:
        """Get handoff data for session continuity."""
        # Find most recent completed session
        sessions = []
        for node in self.graph.nodes():
            if node.type == "governance_session":
                sessions.append({"id": node.id, **node.properties})

        if not sessions:
            return {"previous_session": None}

        # Sort by creation time
        sessions.sort(key=lambda x: x.get("_created_at", ""), reverse=True)

        # Get most recent completed session
        for session in sessions:
            if session.get("status") == "completed":
                return {
                    "previous_session": session.get("id"),
                    "previous_task": session.get("task"),
                    "previous_outcome": session.get("outcome"),
                    "open_issues": session.get("open_issues", []),
                    "last_decisions": session.get("decisions_made", [])[-3:],
                }

        return {"previous_session": None}

    def get_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        sessions = []
        for node in self.graph.nodes():
            if node.type == "governance_session":
                sessions.append(node.properties)

        completed = len([s for s in sessions if s.get("status") == "completed"])
        total_checks = sum(len(s.get("checks_performed", [])) for s in sessions)
        total_decisions = sum(len(s.get("decisions_made", [])) for s in sessions)
        open_issues = sum(len(s.get("open_issues", [])) for s in sessions if s.get("status") == "completed")

        return {
            "total_sessions": len(sessions),
            "completed_sessions": completed,
            "total_checks": total_checks,
            "total_decisions": total_decisions,
            "total_open_issues": open_issues,
        }
