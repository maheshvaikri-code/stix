"""
Agent Memory - Persistent Memory System for Coding Agents

This library provides a graph-based memory system for AI coding agents,
enabling them to maintain context across sessions, learn from past interactions,
and build project-specific knowledge.

Memory Types:
    - CodebaseModel: Architecture and module understanding
    - Decisions: Architectural Decision Records (ADRs)
    - Conventions: Code style and patterns
    - BugPatterns: Historical bugs and fixes
    - Dependencies: Library quirks and workarounds
    - TestPatterns: Testing conventions
    - Performance: Hot paths and constraints
    - TechDebt: Refactoring history
    - TeamKnowledge: Who knows what
    - Sessions: Continuity between sessions
    - Templates: Code generation patterns
    - Skills: Agent learning progression

Usage:
    from agent_memory import AgentMemory

    # Initialize memory for a project
    memory = AgentMemory("my-project")

    # Record a convention
    memory.conventions.add(
        category="naming",
        rule="snake_case_functions",
        enforced_by="ruff"
    )

    # Query before coding
    context = memory.get_coding_context(
        task="modify traversal module",
        files=["graph/traverse.py"]
    )

    # Save memory
    memory.save("project-memory.ison")

Author: Mahesh Vaikri
"""

__version__ = "1.0.0"

from .memory import AgentMemory
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
    # New stores for task/goal/issue tracking
    TodoStore,
    TaskStatus,
    TaskPriority,
    GoalStore,
    GoalStatus,
    MilestoneStatus,
    IssueStore,
    IssueStatus,
    IssueSeverity,
    IssueType,
)
from .context import CodingContext, ContextBuilder
from .integration import AgentIntegration, prepare_for_project, quick_context
from .code_flow_integration import CodeFlowIntegration, enrich_memory_with_code_flow
from .greenfield import (
    GreenfieldProject,
    new_python_project,
    new_typescript_project,
    new_rust_project,
)

# ISONCache integration (optional - requires ison-cache package)
try:
    from .cache_integration import (
        CachedAgentMemory,
        SemanticMemory,
        MemoryGraphCache,
        CachedContext,
        SemanticResult,
        create_cached_memory,
        create_semantic_memory,
        get_context_with_budget,
    )
    _cache_integration_available = True
except ImportError:
    _cache_integration_available = False
    CachedAgentMemory = None
    SemanticMemory = None
    MemoryGraphCache = None
    CachedContext = None
    SemanticResult = None
    create_cached_memory = None
    create_semantic_memory = None
    get_context_with_budget = None

# Governed Memory integration (optional - requires agent-governance package)
try:
    from .governed_memory import (
        GovernedAgentMemory,
        create_governed_agent,
        quick_work_session,
    )
    _governed_memory_available = True
except ImportError:
    _governed_memory_available = False
    GovernedAgentMemory = None
    create_governed_agent = None
    quick_work_session = None

__all__ = [
    "__version__",
    "AgentMemory",
    "AgentIntegration",
    "prepare_for_project",
    "quick_context",
    "CodeFlowIntegration",
    "enrich_memory_with_code_flow",
    "GreenfieldProject",
    "new_python_project",
    "new_typescript_project",
    "new_rust_project",
    "CodebaseStore",
    "DecisionStore",
    "ConventionStore",
    "BugPatternStore",
    "DependencyStore",
    "TestPatternStore",
    "PerformanceStore",
    "TechDebtStore",
    "TeamStore",
    "SessionStore",
    "TemplateStore",
    "SkillStore",
    # New stores for task/goal/issue tracking
    "TodoStore",
    "TaskStatus",
    "TaskPriority",
    "GoalStore",
    "GoalStatus",
    "MilestoneStatus",
    "IssueStore",
    "IssueStatus",
    "IssueSeverity",
    "IssueType",
    "CodingContext",
    "ContextBuilder",
    # ISONCache integration (optional)
    "CachedAgentMemory",
    "SemanticMemory",
    "MemoryGraphCache",
    "CachedContext",
    "SemanticResult",
    "create_cached_memory",
    "create_semantic_memory",
    "get_context_with_budget",
    # Governed Memory integration (optional)
    "GovernedAgentMemory",
    "create_governed_agent",
    "quick_work_session",
]
