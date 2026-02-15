"""
Agent Memory MCP Server - Persistent Memory for Coding Agents
=============================================================

MCP server providing 12+ memory stores for AI coding agents.
Enables context persistence across sessions and project-specific knowledge.

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
- Todos: Task tracking
- Goals: Goal management
"""

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

# Import AgentMemory
from agent_memory import (
    AgentMemory,
    AgentIntegration,
    CodingContext,
    ContextBuilder,
    # Stores
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
    TaskStatus,
    TaskPriority,
    GoalStore,
    GoalStatus,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent-memory-mcp")


# =============================================================================
# Server State
# =============================================================================

@dataclass
class ServerState:
    """Shared state for the MCP server."""
    memories: Dict[str, AgentMemory] = field(default_factory=dict)
    default_project: Optional[str] = None
    data_dir: Path = field(default_factory=lambda: Path("./memory_data"))

    def get_memory(self, project_id: Optional[str] = None) -> AgentMemory:
        """Get memory for a project."""
        pid = project_id or self.default_project
        if not pid:
            raise ValueError("No project specified and no default project set")
        if pid not in self.memories:
            raise ValueError(f"Memory not found for project: {pid}")
        return self.memories[pid]

    def ensure_data_dir(self):
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)


# Initialize server and state
server = Server("agent-memory-mcp")
state = ServerState()


# =============================================================================
# Tool Definitions
# =============================================================================

TOOLS = [
    # --- Memory Management ---
    Tool(
        name="memory_init",
        description="Initialize memory for a project.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string", "description": "Unique project identifier"},
                "project_path": {"type": "string", "description": "Path to project root"},
                "set_as_default": {"type": "boolean", "default": True},
            },
            "required": ["project_id"],
        },
    ),
    Tool(
        name="memory_load",
        description="Load saved memory from file.",
        inputSchema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to memory file (.ison)"},
                "project_id": {"type": "string"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="memory_save",
        description="Save memory to file.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "path": {"type": "string"},
            },
            "required": ["path"],
        },
    ),
    Tool(
        name="memory_list",
        description="List all loaded project memories.",
        inputSchema={"type": "object", "properties": {}},
    ),
    Tool(
        name="memory_bootstrap",
        description="Auto-scan project and bootstrap memory.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "scan_depth": {"type": "integer", "default": 3},
            },
            "required": ["project_id"],
        },
    ),

    # --- Context Retrieval ---
    Tool(
        name="context_get",
        description="Get coding context for current task.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "task": {"type": "string", "description": "Task description"},
                "files": {"type": "array", "items": {"type": "string"}, "description": "Files being worked on"},
                "token_budget": {"type": "integer"},
            },
        },
    ),
    Tool(
        name="context_for_task",
        description="Get task-specific context.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "task_type": {"type": "string", "enum": ["bug_fix", "feature", "refactor", "test", "review"]},
                "description": {"type": "string"},
            },
            "required": ["task_type"],
        },
    ),
    Tool(
        name="context_for_files",
        description="Get context specific to files.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["files"],
        },
    ),

    # --- Conventions ---
    Tool(
        name="convention_add",
        description="Add a code convention.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "category": {"type": "string", "description": "e.g., naming, formatting, patterns"},
                "rule": {"type": "string"},
                "description": {"type": "string"},
                "examples": {"type": "array", "items": {"type": "string"}},
                "enforced_by": {"type": "string", "description": "Tool that enforces it"},
                "applies_to": {"type": "array", "items": {"type": "string"}, "description": "File patterns"},
            },
            "required": ["category", "rule"],
        },
    ),
    Tool(
        name="convention_query",
        description="Query conventions.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "category": {"type": "string"},
                "file_pattern": {"type": "string"},
            },
        },
    ),
    Tool(
        name="convention_for_file",
        description="Get conventions for a specific file.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["file_path"],
        },
    ),

    # --- Decisions (ADRs) ---
    Tool(
        name="decision_add",
        description="Record an architectural decision.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "title": {"type": "string"},
                "context": {"type": "string"},
                "decision": {"type": "string"},
                "consequences": {"type": "array", "items": {"type": "string"}},
                "alternatives": {"type": "array", "items": {"type": "string"}},
                "status": {"type": "string", "enum": ["proposed", "accepted", "deprecated", "superseded"]},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title", "decision"],
        },
    ),
    Tool(
        name="decision_query",
        description="Query decisions.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "status": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
                "search": {"type": "string"},
            },
        },
    ),
    Tool(
        name="decision_related",
        description="Find related decisions.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "decision_id": {"type": "string"},
            },
            "required": ["decision_id"],
        },
    ),

    # --- Bug Patterns ---
    Tool(
        name="bug_pattern_add",
        description="Record a bug pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "pattern_name": {"type": "string"},
                "description": {"type": "string"},
                "symptoms": {"type": "array", "items": {"type": "string"}},
                "root_cause": {"type": "string"},
                "affected_files": {"type": "array", "items": {"type": "string"}},
                "frequency": {"type": "string", "enum": ["rare", "occasional", "common"]},
            },
            "required": ["pattern_name", "description"],
        },
    ),
    Tool(
        name="bug_fix_add",
        description="Add a fix template for a bug pattern.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "pattern_id": {"type": "string"},
                "fix_description": {"type": "string"},
                "code_template": {"type": "string"},
                "prevention_tips": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["pattern_id", "fix_description"],
        },
    ),
    Tool(
        name="bug_check",
        description="Check for known bug patterns in code.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "file_path": {"type": "string"},
                "code_snippet": {"type": "string"},
            },
        },
    ),
    Tool(
        name="bug_prevent",
        description="Get prevention advice for potential bugs.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "task_description": {"type": "string"},
            },
            "required": ["task_description"],
        },
    ),

    # --- Dependencies ---
    Tool(
        name="dependency_add",
        description="Track a dependency.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "name": {"type": "string"},
                "version": {"type": "string"},
                "purpose": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="dependency_quirk",
        description="Record a dependency quirk/workaround.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "dependency_name": {"type": "string"},
                "quirk_description": {"type": "string"},
                "workaround": {"type": "string"},
                "version_affected": {"type": "string"},
            },
            "required": ["dependency_name", "quirk_description"],
        },
    ),
    Tool(
        name="dependency_query",
        description="Query dependencies.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "name": {"type": "string"},
                "has_quirks": {"type": "boolean"},
            },
        },
    ),

    # --- Sessions ---
    Tool(
        name="session_start",
        description="Start a new coding session.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "goal": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["goal"],
        },
    ),
    Tool(
        name="session_end",
        description="End current session with summary.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "summary": {"type": "string"},
                "completed_tasks": {"type": "array", "items": {"type": "string"}},
                "pending_tasks": {"type": "array", "items": {"type": "string"}},
                "learnings": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary"],
        },
    ),
    Tool(
        name="session_handoff",
        description="Get handoff context for session continuation.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "session_id": {"type": "string", "description": "Previous session ID"},
            },
        },
    ),
    Tool(
        name="session_history",
        description="Get session history.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
        },
    ),

    # --- Team Knowledge ---
    Tool(
        name="team_add_expertise",
        description="Record team member expertise.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "person": {"type": "string"},
                "area": {"type": "string"},
                "level": {"type": "string", "enum": ["novice", "intermediate", "expert"]},
                "notes": {"type": "string"},
            },
            "required": ["person", "area"],
        },
    ),
    Tool(
        name="team_who_knows",
        description="Find expert for a topic.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "topic": {"type": "string"},
            },
            "required": ["topic"],
        },
    ),
    Tool(
        name="team_ownership",
        description="Get code ownership information.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["file_path"],
        },
    ),

    # --- Tasks/Todos ---
    Tool(
        name="todo_add",
        description="Add a task.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"]},
                "tags": {"type": "array", "items": {"type": "string"}},
                "related_files": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="todo_update",
        description="Update task status.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "task_id": {"type": "string"},
                "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "blocked"]},
                "notes": {"type": "string"},
            },
            "required": ["task_id", "status"],
        },
    ),
    Tool(
        name="todo_query",
        description="Query tasks.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "status": {"type": "string"},
                "priority": {"type": "string"},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
        },
    ),

    # --- Goals ---
    Tool(
        name="goal_add",
        description="Add a goal.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "title": {"type": "string"},
                "description": {"type": "string"},
                "milestones": {"type": "array", "items": {"type": "string"}},
                "deadline": {"type": "string"},
            },
            "required": ["title"],
        },
    ),
    Tool(
        name="goal_track",
        description="Track goal progress.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "goal_id": {"type": "string"},
                "milestone_completed": {"type": "string"},
                "notes": {"type": "string"},
            },
            "required": ["goal_id"],
        },
    ),

    # --- Skills ---
    Tool(
        name="skill_record",
        description="Record skill usage.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "skill": {"type": "string"},
                "success": {"type": "boolean"},
                "context": {"type": "string"},
            },
            "required": ["skill", "success"],
        },
    ),
    Tool(
        name="skill_progression",
        description="Get skill progression.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "skill": {"type": "string"},
            },
        },
    ),

    # --- Codebase Model ---
    Tool(
        name="codebase_add_module",
        description="Add module information.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "name": {"type": "string"},
                "path": {"type": "string"},
                "description": {"type": "string"},
                "dependencies": {"type": "array", "items": {"type": "string"}},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["name", "path"],
        },
    ),
    Tool(
        name="codebase_query",
        description="Query codebase structure.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_id": {"type": "string"},
                "module": {"type": "string"},
                "tag": {"type": "string"},
            },
        },
    ),
]


# =============================================================================
# Tool Handlers
# =============================================================================

@server.list_tools()
async def list_tools() -> List[Tool]:
    """List all available tools."""
    return TOOLS


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> List[TextContent]:
    """Handle tool calls."""
    try:
        result = await handle_tool(name, arguments)
        return [TextContent(type="text", text=json.dumps(result, indent=2, default=str))]
    except Exception as e:
        logger.error(f"Tool {name} failed: {e}")
        return [TextContent(type="text", text=json.dumps({"error": str(e)}))]


async def handle_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Route tool calls to handlers."""

    # --- Memory Management ---
    if name == "memory_init":
        project_id = args["project_id"]
        project_path = args.get("project_path")

        memory = AgentMemory(project_id, project_path=project_path)
        state.memories[project_id] = memory

        if args.get("set_as_default", True):
            state.default_project = project_id

        return {"project_id": project_id, "initialized": True}

    elif name == "memory_load":
        path = Path(args["path"])
        project_id = args.get("project_id", path.stem)

        memory = AgentMemory(project_id)
        memory.load(path)
        state.memories[project_id] = memory

        return {"project_id": project_id, "loaded": True}

    elif name == "memory_save":
        memory = state.get_memory(args.get("project_id"))
        path = Path(args["path"])

        state.ensure_data_dir()
        memory.save(path)

        return {"path": str(path), "saved": True}

    elif name == "memory_list":
        return {
            "projects": list(state.memories.keys()),
            "default": state.default_project,
        }

    elif name == "memory_bootstrap":
        memory = state.get_memory(args["project_id"])
        depth = args.get("scan_depth", 3)

        # Trigger bootstrap scan
        if hasattr(memory, "bootstrap"):
            memory.bootstrap(scan_depth=depth)

        return {"project_id": args["project_id"], "bootstrapped": True}

    # --- Context Retrieval ---
    elif name == "context_get":
        memory = state.get_memory(args.get("project_id"))
        task = args.get("task", "")
        files = args.get("files", [])
        budget = args.get("token_budget")

        context = memory.get_coding_context(task=task, files=files)

        return {
            "conventions": context.conventions[:10] if hasattr(context, "conventions") else [],
            "decisions": context.decisions[:5] if hasattr(context, "decisions") else [],
            "bug_patterns": context.bug_patterns[:5] if hasattr(context, "bug_patterns") else [],
            "dependencies": context.dependencies[:10] if hasattr(context, "dependencies") else [],
        }

    elif name == "context_for_task":
        memory = state.get_memory(args.get("project_id"))
        task_type = args["task_type"]
        description = args.get("description", "")

        # Get task-specific context
        context = {}
        if task_type == "bug_fix":
            context["bug_patterns"] = list(memory.bug_patterns.query())[:5]
        elif task_type == "feature":
            context["conventions"] = list(memory.conventions.query())[:10]
            context["decisions"] = list(memory.decisions.query())[:5]
        elif task_type == "refactor":
            context["tech_debt"] = list(memory.tech_debt.query())[:5] if hasattr(memory, "tech_debt") else []
        elif task_type == "test":
            context["test_patterns"] = list(memory.test_patterns.query())[:5] if hasattr(memory, "test_patterns") else []

        return context

    elif name == "context_for_files":
        memory = state.get_memory(args.get("project_id"))
        files = args["files"]

        # Get file-specific context
        conventions = []
        for file_path in files:
            conventions.extend(memory.conventions.for_file(file_path))

        return {
            "files": files,
            "conventions": conventions[:20],
        }

    # --- Conventions ---
    elif name == "convention_add":
        memory = state.get_memory(args.get("project_id"))

        conv_id = memory.conventions.add(
            category=args["category"],
            rule=args["rule"],
            description=args.get("description", ""),
            examples=args.get("examples", []),
            enforced_by=args.get("enforced_by"),
            applies_to=args.get("applies_to", []),
        )

        return {"convention_id": conv_id}

    elif name == "convention_query":
        memory = state.get_memory(args.get("project_id"))
        category = args.get("category")
        file_pattern = args.get("file_pattern")

        results = list(memory.conventions.query(category=category))

        return {"conventions": results, "count": len(results)}

    elif name == "convention_for_file":
        memory = state.get_memory(args.get("project_id"))
        file_path = args["file_path"]

        conventions = memory.conventions.for_file(file_path)

        return {"file": file_path, "conventions": list(conventions)}

    # --- Decisions ---
    elif name == "decision_add":
        memory = state.get_memory(args.get("project_id"))

        decision_id = memory.decisions.add(
            title=args["title"],
            context=args.get("context", ""),
            decision=args["decision"],
            consequences=args.get("consequences", []),
            alternatives=args.get("alternatives", []),
            status=args.get("status", "accepted"),
            tags=args.get("tags", []),
        )

        return {"decision_id": decision_id}

    elif name == "decision_query":
        memory = state.get_memory(args.get("project_id"))

        results = list(memory.decisions.query(
            status=args.get("status"),
            tags=args.get("tags"),
        ))

        if args.get("search"):
            search = args["search"].lower()
            results = [d for d in results if search in str(d).lower()]

        return {"decisions": results, "count": len(results)}

    elif name == "decision_related":
        memory = state.get_memory(args.get("project_id"))
        decision_id = args["decision_id"]

        related = memory.decisions.find_related(decision_id)

        return {"decision_id": decision_id, "related": list(related)}

    # --- Bug Patterns ---
    elif name == "bug_pattern_add":
        memory = state.get_memory(args.get("project_id"))

        pattern_id = memory.bug_patterns.add(
            pattern_name=args["pattern_name"],
            description=args["description"],
            symptoms=args.get("symptoms", []),
            root_cause=args.get("root_cause", ""),
            affected_files=args.get("affected_files", []),
            frequency=args.get("frequency", "occasional"),
        )

        return {"pattern_id": pattern_id}

    elif name == "bug_fix_add":
        memory = state.get_memory(args.get("project_id"))

        memory.bug_patterns.add_fix(
            pattern_id=args["pattern_id"],
            fix_description=args["fix_description"],
            code_template=args.get("code_template"),
            prevention_tips=args.get("prevention_tips", []),
        )

        return {"pattern_id": args["pattern_id"], "fix_added": True}

    elif name == "bug_check":
        memory = state.get_memory(args.get("project_id"))

        patterns = list(memory.bug_patterns.query())
        matches = []

        # Simple pattern matching
        code = args.get("code_snippet", "")
        file_path = args.get("file_path", "")

        for pattern in patterns:
            if hasattr(pattern, "affected_files"):
                for affected in pattern.affected_files:
                    if affected in file_path:
                        matches.append(pattern)
                        break

        return {"potential_bugs": matches[:5]}

    elif name == "bug_prevent":
        memory = state.get_memory(args.get("project_id"))
        task = args["task_description"]

        patterns = list(memory.bug_patterns.query())
        tips = []

        for pattern in patterns:
            if hasattr(pattern, "prevention_tips"):
                tips.extend(pattern.prevention_tips)

        return {"prevention_tips": tips[:10]}

    # --- Dependencies ---
    elif name == "dependency_add":
        memory = state.get_memory(args.get("project_id"))

        dep_id = memory.dependencies.add(
            name=args["name"],
            version=args.get("version"),
            purpose=args.get("purpose"),
            notes=args.get("notes"),
        )

        return {"dependency_id": dep_id}

    elif name == "dependency_quirk":
        memory = state.get_memory(args.get("project_id"))

        memory.dependencies.add_quirk(
            dependency_name=args["dependency_name"],
            quirk_description=args["quirk_description"],
            workaround=args.get("workaround"),
            version_affected=args.get("version_affected"),
        )

        return {"dependency": args["dependency_name"], "quirk_added": True}

    elif name == "dependency_query":
        memory = state.get_memory(args.get("project_id"))

        results = list(memory.dependencies.query(
            name=args.get("name"),
        ))

        return {"dependencies": results, "count": len(results)}

    # --- Sessions ---
    elif name == "session_start":
        memory = state.get_memory(args.get("project_id"))

        session_id = memory.sessions.start(
            goal=args["goal"],
            files=args.get("files", []),
        )

        return {"session_id": session_id, "started": datetime.now().isoformat()}

    elif name == "session_end":
        memory = state.get_memory(args.get("project_id"))

        memory.sessions.end(
            summary=args["summary"],
            completed_tasks=args.get("completed_tasks", []),
            pending_tasks=args.get("pending_tasks", []),
            learnings=args.get("learnings", []),
        )

        return {"ended": datetime.now().isoformat()}

    elif name == "session_handoff":
        memory = state.get_memory(args.get("project_id"))
        session_id = args.get("session_id")

        handoff = memory.sessions.get_handoff(session_id)

        return {"handoff": handoff}

    elif name == "session_history":
        memory = state.get_memory(args.get("project_id"))
        limit = args.get("limit", 10)

        history = list(memory.sessions.history(limit=limit))

        return {"sessions": history, "count": len(history)}

    # --- Team Knowledge ---
    elif name == "team_add_expertise":
        memory = state.get_memory(args.get("project_id"))

        memory.team.add_expertise(
            person=args["person"],
            area=args["area"],
            level=args.get("level", "intermediate"),
            notes=args.get("notes"),
        )

        return {"person": args["person"], "expertise_added": args["area"]}

    elif name == "team_who_knows":
        memory = state.get_memory(args.get("project_id"))
        topic = args["topic"]

        experts = memory.team.who_knows(topic)

        return {"topic": topic, "experts": list(experts)}

    elif name == "team_ownership":
        memory = state.get_memory(args.get("project_id"))
        file_path = args["file_path"]

        owners = memory.team.get_owners(file_path)

        return {"file": file_path, "owners": list(owners)}

    # --- Tasks/Todos ---
    elif name == "todo_add":
        memory = state.get_memory(args.get("project_id"))

        task_id = memory.todos.add(
            title=args["title"],
            description=args.get("description", ""),
            priority=args.get("priority", "medium"),
            tags=args.get("tags", []),
            related_files=args.get("related_files", []),
        )

        return {"task_id": task_id}

    elif name == "todo_update":
        memory = state.get_memory(args.get("project_id"))

        memory.todos.update_status(
            task_id=args["task_id"],
            status=args["status"],
            notes=args.get("notes"),
        )

        return {"task_id": args["task_id"], "status": args["status"]}

    elif name == "todo_query":
        memory = state.get_memory(args.get("project_id"))

        results = list(memory.todos.query(
            status=args.get("status"),
            priority=args.get("priority"),
            tags=args.get("tags"),
        ))

        return {"tasks": results, "count": len(results)}

    # --- Goals ---
    elif name == "goal_add":
        memory = state.get_memory(args.get("project_id"))

        goal_id = memory.goals.add(
            title=args["title"],
            description=args.get("description", ""),
            milestones=args.get("milestones", []),
            deadline=args.get("deadline"),
        )

        return {"goal_id": goal_id}

    elif name == "goal_track":
        memory = state.get_memory(args.get("project_id"))

        memory.goals.track_progress(
            goal_id=args["goal_id"],
            milestone_completed=args.get("milestone_completed"),
            notes=args.get("notes"),
        )

        return {"goal_id": args["goal_id"], "progress_updated": True}

    # --- Skills ---
    elif name == "skill_record":
        memory = state.get_memory(args.get("project_id"))

        memory.skills.record(
            skill=args["skill"],
            success=args["success"],
            context=args.get("context"),
        )

        return {"skill": args["skill"], "recorded": True}

    elif name == "skill_progression":
        memory = state.get_memory(args.get("project_id"))
        skill = args.get("skill")

        if skill:
            progression = memory.skills.get_progression(skill)
        else:
            progression = memory.skills.all_progressions()

        return {"progression": progression}

    # --- Codebase Model ---
    elif name == "codebase_add_module":
        memory = state.get_memory(args.get("project_id"))

        module_id = memory.codebase.add_module(
            name=args["name"],
            path=args["path"],
            description=args.get("description", ""),
            dependencies=args.get("dependencies", []),
            tags=args.get("tags", []),
        )

        return {"module_id": module_id}

    elif name == "codebase_query":
        memory = state.get_memory(args.get("project_id"))

        results = list(memory.codebase.query(
            module=args.get("module"),
            tag=args.get("tag"),
        ))

        return {"modules": results, "count": len(results)}

    else:
        raise ValueError(f"Unknown tool: {name}")


# =============================================================================
# Main Entry Point
# =============================================================================

async def run_server():
    """Run the MCP server."""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


def main():
    """Main entry point."""
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
