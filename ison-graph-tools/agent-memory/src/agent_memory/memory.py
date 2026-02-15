"""
Agent Memory - Main memory manager coordinating all stores
"""

from typing import Any, Dict, List, Optional
from pathlib import Path as FilePath

from ison_graph import ISONGraph

from .stores import (
    CodebaseStore,
    DecisionStore,
    ConventionStore,
    BugPatternStore,
    DependencyStore,
    TestPatternStore,
    PerformanceStore,
    TechDebtStore,
    TeamStore,
    SessionStore,
    TemplateStore,
    SkillStore,
    TodoStore,
    GoalStore,
    IssueStore,
)
from .context import ContextBuilder, CodingContext
from .consolidation import MemoryConsolidator


class AgentMemory:
    """
    Main entry point for the Agent Memory System.

    Provides unified access to all memory stores and context building.

    Usage:
        memory = AgentMemory("my-project")

        # Access stores directly
        memory.conventions.add("naming", "snake_case", "ruff")
        memory.bugs.add_pattern("race_condition", "shared_state_no_lock")

        # Get coding context
        context = memory.get_context(
            task="modify the cache module",
            files=["src/cache.py"]
        )

        # Save/load memory
        memory.save("project.memory")
        memory = AgentMemory.load("project.memory")
    """

    def __init__(self, name: str = "project"):
        self.name = name
        self.graph = ISONGraph(name=name)

        # Ensure agent node exists
        self.graph.add_node("agent", "self", name="agent")

        # Initialize stores
        self.codebase = CodebaseStore(self.graph)
        self.decisions = DecisionStore(self.graph)
        self.conventions = ConventionStore(self.graph)
        self.bugs = BugPatternStore(self.graph)
        self.dependencies = DependencyStore(self.graph)
        self.tests = TestPatternStore(self.graph)
        self.performance = PerformanceStore(self.graph)
        self.techdebt = TechDebtStore(self.graph)
        self.team = TeamStore(self.graph)
        self.sessions = SessionStore(self.graph)
        self.templates = TemplateStore(self.graph)
        self.skills = SkillStore(self.graph)
        # New stores for task/goal/issue tracking
        self.todos = TodoStore(self.graph)
        self.goals = GoalStore(self.graph)
        self.issues = IssueStore(self.graph)

        # Context builder
        self._context_builder = ContextBuilder(self)

        # Memory consolidator
        self._consolidator = MemoryConsolidator(self)

    # =========================================================================
    # Session Management
    # =========================================================================

    def start_session(self, task: str) -> str:
        """Start a new coding session"""
        session_id = self.sessions.start_session(task)

        # Link to previous session if exists
        last = self.sessions.get_last_session()
        if last and last != session_id:
            self.sessions.continue_session(session_id, last)

        return session_id

    def end_session(self, session_id: str, completion: float = 1.0) -> None:
        """End the current session"""
        self.sessions.end_session(session_id, completion)

        # Consolidate memory after session
        self._consolidator.consolidate()

    # =========================================================================
    # Context Building
    # =========================================================================

    def get_context(
        self,
        task: str,
        files: Optional[List[str]] = None,
        include: Optional[List[str]] = None,
        exclude: Optional[List[str]] = None,
        max_tokens: int = 4000,
    ) -> CodingContext:
        """
        Get relevant context for a coding task.

        Args:
            task: Description of the task
            files: Files being modified
            include: Memory types to include (default: all)
            exclude: Memory types to exclude
            max_tokens: Maximum estimated tokens for context

        Returns:
            CodingContext with relevant memories
        """
        return self._context_builder.build(
            task=task,
            files=files or [],
            include=include,
            exclude=exclude,
            max_tokens=max_tokens,
        )

    def get_quick_context(self, task: str, files: Optional[List[str]] = None) -> str:
        """Get a quick summary context string"""
        context = self.get_context(task, files, max_tokens=1000)
        return context.to_prompt()

    # =========================================================================
    # Memory Recording (convenience methods)
    # =========================================================================

    def record(self, event_type: str, **kwargs) -> None:
        """
        Generic event recording.

        Automatically routes to appropriate store based on event type.
        """
        if event_type == "bug_prevented":
            self.bugs.record_prevention(
                kwargs.get("pattern", ""),
                kwargs.get("location", "")
            )
        elif event_type == "bug_missed":
            self.bugs.record_miss(
                kwargs.get("pattern", ""),
                kwargs.get("consequence", ""),
                kwargs.get("post_mortem", "")
            )
        elif event_type == "decision_violated":
            self.decisions.record_violation(
                kwargs.get("decision", ""),
                kwargs.get("suggestion", ""),
                kwargs.get("correction", "")
            )
        elif event_type == "convention_violated":
            self.conventions.record_violation(
                kwargs.get("convention_id", ""),
                kwargs.get("pattern", "")
            )
        elif event_type == "skill_applied":
            self.skills.record_skill_application(
                kwargs.get("skill", ""),
                kwargs.get("session_id", ""),
                kwargs.get("success", True),
                kwargs.get("notes", "")
            )
        elif event_type == "learning":
            self.skills.record_learning_event(
                kwargs.get("skill", ""),
                kwargs.get("type", "success"),
                kwargs.get("context", ""),
                kwargs.get("lesson", "")
            )

    # =========================================================================
    # Queries
    # =========================================================================

    def check_suggestion(self, suggestion: str) -> List[Dict[str, Any]]:
        """
        Check a suggestion against memory for potential issues.

        Returns warnings if suggestion conflicts with decisions,
        matches failed refactoring attempts, etc.
        """
        warnings = []

        # Check decisions
        decision_conflict = self.decisions.check_decision(suggestion)
        if decision_conflict:
            warnings.append({
                "type": "decision_conflict",
                **decision_conflict
            })

        # Check tech debt (failed refactoring)
        for node in self.graph.nodes():
            if node.type == "tech_debt":
                check = self.techdebt.check_suggestion(
                    node.properties.get("location", ""),
                    suggestion
                )
                if check:
                    warnings.append(check)

        return warnings

    def who_knows(self, topic: str) -> Optional[Dict[str, Any]]:
        """Find who has expertise on a topic"""
        return self.team.find_expert(topic)

    # =========================================================================
    # Persistence
    # =========================================================================

    def save(self, path: str) -> None:
        """Save memory to file"""
        self.graph.save(path)

    @classmethod
    def load(cls, path: str) -> "AgentMemory":
        """Load memory from file"""
        graph = ISONGraph.load(path)
        memory = cls(name=graph.name)
        memory.graph = graph

        # Reinitialize stores with loaded graph
        memory.codebase = CodebaseStore(graph)
        memory.decisions = DecisionStore(graph)
        memory.conventions = ConventionStore(graph)
        memory.bugs = BugPatternStore(graph)
        memory.dependencies = DependencyStore(graph)
        memory.tests = TestPatternStore(graph)
        memory.performance = PerformanceStore(graph)
        memory.techdebt = TechDebtStore(graph)
        memory.team = TeamStore(graph)
        memory.sessions = SessionStore(graph)
        memory.templates = TemplateStore(graph)
        memory.skills = SkillStore(graph)
        memory.todos = TodoStore(graph)
        memory.goals = GoalStore(graph)
        memory.issues = IssueStore(graph)

        memory._context_builder = ContextBuilder(memory)
        memory._consolidator = MemoryConsolidator(memory)

        return memory

    def export_json(self, path: str) -> None:
        """Export memory as JSON"""
        import json
        data = self.graph.to_dict()
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive memory statistics"""
        return {
            "name": self.name,
            "total_nodes": self.graph.node_count(),
            "total_edges": self.graph.edge_count(),
            "stores": {
                "codebase": self.codebase.get_stats(),
                "decisions": self.decisions.get_stats(),
                "conventions": self.conventions.get_stats(),
                "bugs": self.bugs.get_stats(),
                "dependencies": self.dependencies.get_stats(),
                "tests": self.tests.get_stats(),
                "performance": self.performance.get_stats(),
                "techdebt": self.techdebt.get_stats(),
                "team": self.team.get_stats(),
                "sessions": self.sessions.get_stats(),
                "templates": self.templates.get_stats(),
                "skills": self.skills.get_stats(),
                "todos": self.todos.get_stats(),
                "goals": self.goals.get_stats(),
                "issues": self.issues.get_stats(),
            }
        }

    def __repr__(self) -> str:
        return f"AgentMemory(name={self.name}, nodes={self.graph.node_count()}, edges={self.graph.edge_count()})"
