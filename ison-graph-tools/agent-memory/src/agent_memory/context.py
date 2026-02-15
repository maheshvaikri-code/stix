"""
Context Builder - Builds coding context from memory
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .memory import AgentMemory


@dataclass
class CodingContext:
    """
    Context package for a coding task.

    Contains relevant memories organized by type and priority.
    """
    task: str
    files: List[str] = field(default_factory=list)

    # High priority - must know
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    constraints: List[Dict[str, Any]] = field(default_factory=list)
    hot_paths: List[Dict[str, Any]] = field(default_factory=list)

    # Medium priority - should know
    conventions: List[Dict[str, Any]] = field(default_factory=list)
    patterns: List[Dict[str, Any]] = field(default_factory=list)
    bug_risks: List[Dict[str, Any]] = field(default_factory=list)
    dependencies: List[Dict[str, Any]] = field(default_factory=list)

    # Low priority - nice to know
    module_context: List[Dict[str, Any]] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    team_experts: List[Dict[str, Any]] = field(default_factory=list)

    # Session continuity
    session_context: Dict[str, Any] = field(default_factory=dict)

    # Metadata
    estimated_tokens: int = 0

    def to_prompt(self) -> str:
        """Convert context to a prompt-ready string"""
        sections = []

        # High priority
        if self.warnings:
            sections.append("## WARNINGS")
            for w in self.warnings:
                sections.append(f"- {w.get('type', 'warning')}: {w.get('message', str(w))}")

        if self.constraints:
            sections.append("\n## CONSTRAINTS")
            for c in self.constraints:
                sections.append(f"- {c.get('decision', '')}: {c.get('how', '')}")

        if self.hot_paths:
            sections.append("\n## HOT PATHS (Performance Critical)")
            for hp in self.hot_paths:
                sections.append(f"- {hp.get('name', '')}: {hp.get('warning', 'untouchable')}")

        # Medium priority
        if self.conventions:
            sections.append("\n## CODE CONVENTIONS")
            for c in self.conventions:
                category = c.get('category', '')
                rule = c.get('rule', '') or c.get('preferred_form', '') or c.get('template', '')
                if rule:
                    sections.append(f"- [{category}] {rule}")

        if self.patterns:
            sections.append("\n## PROJECT PATTERNS")
            for p in self.patterns:
                sections.append(f"- {p.get('name', '')}: {p.get('template', '')}")

        if self.bug_risks:
            sections.append("\n## BUG RISKS")
            for b in self.bug_risks:
                pattern = b.get('pattern', {})
                sections.append(f"- {pattern.get('name', '')}: {pattern.get('signature', '')}")
                if b.get('fix'):
                    sections.append(f"  Fix: {b.get('fix', {}).get('fix_template', '')}")

        if self.dependencies:
            sections.append("\n## DEPENDENCY NOTES")
            for d in self.dependencies:
                quirk = d.get('quirk', {})
                sections.append(f"- {quirk.get('description', '')}")
                if d.get('workaround'):
                    sections.append(f"  Workaround: {d.get('workaround', {}).get('solution', '')}")

        # Session continuity
        if self.session_context:
            if self.session_context.get("open_questions"):
                sections.append("\n## OPEN QUESTIONS")
                for q in self.session_context["open_questions"]:
                    sections.append(f"- {q.get('question', '')}")

            if self.session_context.get("decisions"):
                sections.append("\n## SESSION DECISIONS")
                for d in self.session_context["decisions"]:
                    sections.append(f"- {d.get('decision', '')}: {d.get('rationale', '')}")

        return "\n".join(sections)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task": self.task,
            "files": self.files,
            "warnings": self.warnings,
            "constraints": self.constraints,
            "hot_paths": self.hot_paths,
            "conventions": self.conventions,
            "patterns": self.patterns,
            "bug_risks": self.bug_risks,
            "dependencies": self.dependencies,
            "module_context": self.module_context,
            "decisions": self.decisions,
            "team_experts": self.team_experts,
            "session_context": self.session_context,
            "estimated_tokens": self.estimated_tokens,
        }


class ContextBuilder:
    """
    Builds coding context from memory stores.

    Prioritizes information based on relevance and token budget.
    """

    # Store names and their priority weights
    STORES = [
        ("warnings", 1.0),      # Always include
        ("constraints", 0.95),  # Almost always
        ("hot_paths", 0.9),
        ("conventions", 0.8),
        ("patterns", 0.75),
        ("bug_risks", 0.7),
        ("dependencies", 0.65),
        ("module_context", 0.5),
        ("decisions", 0.4),
        ("team_experts", 0.3),
    ]

    # Estimated tokens per item type
    TOKEN_ESTIMATES = {
        "warning": 50,
        "constraint": 40,
        "hot_path": 30,
        "convention": 25,
        "pattern": 60,
        "bug_risk": 80,
        "dependency": 70,
        "module": 100,
        "decision": 60,
        "expert": 40,
        "session": 50,
    }

    def __init__(self, memory: "AgentMemory"):
        self.memory = memory

    def build(
        self,
        task: str,
        files: List[str],
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        max_tokens: int = 4000,
    ) -> CodingContext:
        """Build context for a task"""
        context = CodingContext(task=task, files=files)
        raw_context = {"task": task, "files": files}
        token_count = 0

        # Determine which stores to query
        store_names = include or [s[0] for s in self.STORES]
        if exclude:
            store_names = [s for s in store_names if s not in exclude]

        # Gather from each store
        all_items = []

        # Get session context first (always included)
        session_context = self.memory.sessions.get_relevant(raw_context)
        if session_context:
            last_session = self.memory.sessions.get_last_session()
            if last_session:
                context.session_context = self.memory.sessions.get_session_context(last_session)

        # Gather items from each store
        for store_name, priority in self.STORES:
            if store_name not in store_names:
                continue

            items = self._get_from_store(store_name, raw_context)
            for item in items:
                all_items.append((store_name, priority, item))

        # Sort by priority
        all_items.sort(key=lambda x: x[1], reverse=True)

        # Add items within token budget
        for store_name, priority, item in all_items:
            item_tokens = self._estimate_tokens(store_name, item)
            if token_count + item_tokens > max_tokens:
                break

            self._add_to_context(context, store_name, item)
            token_count += item_tokens

        context.estimated_tokens = token_count
        return context

    def _get_from_store(self, store_name: str, raw_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant items from a store"""
        store_map = {
            "warnings": lambda: self._get_warnings(raw_context),
            "constraints": lambda: self.memory.decisions.get_relevant(raw_context),
            "hot_paths": lambda: self.memory.performance.get_relevant(raw_context),
            "conventions": lambda: self.memory.conventions.get_relevant(raw_context),
            "patterns": lambda: self.memory.templates.get_relevant(raw_context),
            "bug_risks": lambda: self.memory.bugs.get_relevant(raw_context),
            "dependencies": lambda: self.memory.dependencies.get_relevant(raw_context),
            "module_context": lambda: self.memory.codebase.get_relevant(raw_context),
            "decisions": lambda: self._get_decision_context(raw_context),
            "team_experts": lambda: self.memory.team.get_relevant(raw_context),
        }

        getter = store_map.get(store_name)
        if getter:
            return getter()
        return []

    def _get_warnings(self, raw_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get warnings (combined from multiple sources)"""
        warnings = []

        # Check for decision conflicts
        task = raw_context.get("task", "")
        if task:
            conflict = self.memory.decisions.check_decision(task)
            if conflict:
                warnings.append({
                    "type": "decision_conflict",
                    "message": conflict.get("conflict", ""),
                    **conflict
                })

        # Check for tech debt warnings
        for item in self.memory.techdebt.get_relevant(raw_context):
            if item.get("type") == "refactoring_warning":
                warnings.append({
                    "type": "refactoring_failed",
                    "message": f"Approach already tried: {item.get('attempt', {}).get('approach', '')}",
                    **item
                })

        return warnings

    def _get_decision_context(self, raw_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get decision context (non-constraint decisions)"""
        decisions = []
        for node in self.memory.graph.nodes():
            if node.type == "decision":
                decisions.append({"type": "decision", **node.properties})
        return decisions[:5]  # Limit to 5

    def _estimate_tokens(self, store_name: str, item: Dict[str, Any]) -> int:
        """Estimate tokens for an item"""
        type_map = {
            "warnings": "warning",
            "constraints": "constraint",
            "hot_paths": "hot_path",
            "conventions": "convention",
            "patterns": "pattern",
            "bug_risks": "bug_risk",
            "dependencies": "dependency",
            "module_context": "module",
            "decisions": "decision",
            "team_experts": "expert",
        }
        item_type = type_map.get(store_name, "session")
        return self.TOKEN_ESTIMATES.get(item_type, 50)

    def _add_to_context(self, context: CodingContext, store_name: str, item: Dict[str, Any]) -> None:
        """Add an item to the appropriate context list"""
        attr_map = {
            "warnings": "warnings",
            "constraints": "constraints",
            "hot_paths": "hot_paths",
            "conventions": "conventions",
            "patterns": "patterns",
            "bug_risks": "bug_risks",
            "dependencies": "dependencies",
            "module_context": "module_context",
            "decisions": "decisions",
            "team_experts": "team_experts",
        }
        attr = attr_map.get(store_name)
        if attr:
            getattr(context, attr).append(item)
