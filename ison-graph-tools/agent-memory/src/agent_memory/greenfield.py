"""
Greenfield Project Support
==========================

For NEW projects where no code exists yet, the agent needs to:
1. Initialize memory with project intent
2. Record architecture decisions as they're made
3. Set conventions before writing code
4. Build templates as patterns emerge
5. Track everything from day 1

This is different from bootstrapping an existing codebase.
"""

import os
from typing import Any, Dict, List, Optional
from datetime import datetime

from .memory import AgentMemory
from .context import CodingContext


class GreenfieldProject:
    """
    Memory manager for new/fresh projects.

    Usage:
        # Starting a brand new project
        project = GreenfieldProject(
            name="my-new-api",
            path="/path/to/my-new-api",
            language="python",
            description="REST API for user management"
        )

        # Define architecture upfront
        project.set_architecture(
            style="layered",
            layers=["api", "services", "repositories", "models"]
        )

        # Set conventions before coding
        project.set_conventions(
            naming="snake_case",
            typing="strict",
            testing="pytest",
            formatting="black"
        )

        # Record initial decisions
        project.decide(
            "Use FastAPI",
            "Need async support and auto OpenAPI docs",
            alternatives={"Flask": "No async", "Django": "Too heavy"}
        )

        # Start first session
        session_id, context = project.start_session("Set up project structure")
    """

    def __init__(
        self,
        name: str,
        path: str,
        language: str = "python",
        description: str = "",
    ):
        """
        Initialize a new greenfield project.

        Args:
            name: Project name
            path: Path where project will be created
            language: Primary language (python, typescript, rust, etc.)
            description: Brief project description
        """
        self.name = name
        self.path = os.path.abspath(path)
        self.language = language
        self.description = description
        self.memory_path = os.path.join(self.path, ".agent-memory")

        # Create project directory if needed
        os.makedirs(self.path, exist_ok=True)

        # Initialize fresh memory
        self.memory = AgentMemory(name=name)

        # Record project metadata
        self.memory.graph.add_node(
            "project",
            "main",
            name=name,
            language=language,
            description=description,
            created=datetime.now().isoformat(),
            status="greenfield"
        )

        # Initialize language-specific skills
        self._init_language_skills()

        self._current_session: Optional[str] = None
        self._architecture: Dict[str, Any] = {}

    def _init_language_skills(self) -> None:
        """Initialize skills based on project language"""
        lang_skills = {
            "python": [
                ("python", "language", 0.5),
                ("python_async", "language", 0.3),
                ("pytest", "testing", 0.4),
                ("pip", "tooling", 0.5),
            ],
            "typescript": [
                ("typescript", "language", 0.5),
                ("node", "runtime", 0.4),
                ("npm", "tooling", 0.5),
                ("jest", "testing", 0.4),
            ],
            "javascript": [
                ("javascript", "language", 0.5),
                ("node", "runtime", 0.4),
                ("npm", "tooling", 0.5),
            ],
            "rust": [
                ("rust", "language", 0.4),
                ("cargo", "tooling", 0.5),
            ],
        }

        skills = lang_skills.get(self.language, [])
        for skill_name, category, proficiency in skills:
            self.memory.skills.add_skill(skill_name, category, proficiency)

        # Common skills
        self.memory.skills.add_skill("git", "tooling", 0.7)
        self.memory.skills.add_skill("debugging", "general", 0.5)

    # =========================================================================
    # Architecture Setup
    # =========================================================================

    def set_architecture(
        self,
        style: str,
        layers: Optional[List[str]] = None,
        patterns: Optional[List[str]] = None,
        description: str = ""
    ) -> None:
        """
        Define project architecture upfront.

        Args:
            style: Architecture style (layered, hexagonal, microservices, monolith)
            layers: List of layers/modules to create
            patterns: Design patterns to use
            description: Architecture description
        """
        self._architecture = {
            "style": style,
            "layers": layers or [],
            "patterns": patterns or [],
        }

        # Record as a decision
        self.memory.decisions.add_decision(
            title=f"Architecture: {style}",
            context=description or f"Using {style} architecture",
            consequences_positive=[f"Clear {style} structure"],
            consequences_negative=[]
        )

        # Pre-create module entries
        for layer in (layers or []):
            self.memory.codebase.add_module(
                path=f"src/{layer}",
                purpose=f"{layer.title()} layer",
                complexity="low",  # New, so low complexity
                stability="evolving"
            )

        # Record patterns
        for pattern in (patterns or []):
            self.memory.codebase.add_pattern(
                name=pattern,
                modules=[],
                why_chosen="Architectural decision"
            )

        self._save()

    def add_layer(self, name: str, purpose: str, depends_on: Optional[List[str]] = None) -> None:
        """Add a layer/module to the architecture"""
        self.memory.codebase.add_module(
            path=f"src/{name}",
            purpose=purpose,
            complexity="low",
            stability="evolving"
        )

        # Add dependencies
        for dep in (depends_on or []):
            self.memory.codebase.add_dependency(
                from_module=f"src/{name}",
                to_module=f"src/{dep}",
                coupling="designed"
            )

        self._save()

    # =========================================================================
    # Conventions Setup
    # =========================================================================

    def set_conventions(
        self,
        naming: str = "snake_case",
        typing: str = "optional",
        testing: str = "pytest",
        formatting: str = "black",
        linting: str = "ruff",
        docstrings: str = "google",
        **custom
    ) -> None:
        """
        Set project conventions before writing code.

        Args:
            naming: Naming convention (snake_case, camelCase, PascalCase)
            typing: Type hints (strict, optional, none)
            testing: Test framework
            formatting: Code formatter
            linting: Linter
            docstrings: Docstring style (google, numpy, sphinx)
            **custom: Additional custom conventions
        """
        conventions = {
            "naming": f"Use {naming} for functions and variables",
            "typing": f"Type hints: {typing}",
            "testing": f"Use {testing} for testing",
            "formatting": f"Use {formatting} for formatting",
            "linting": f"Use {linting} for linting",
            "docstrings": f"Use {docstrings} style docstrings",
        }
        conventions.update(custom)

        for category, rule in conventions.items():
            enforced_by = "manual"
            if category == "formatting":
                enforced_by = formatting
            elif category == "linting":
                enforced_by = linting
            elif category == "typing" and typing == "strict":
                enforced_by = "mypy"

            self.memory.conventions.add_convention(
                category=category,
                rule=rule,
                enforced_by=enforced_by
            )

        # Add common idioms based on language
        if self.language == "python":
            self._add_python_idioms()
        elif self.language in ("typescript", "javascript"):
            self._add_js_idioms()

        self._save()

    def _add_python_idioms(self) -> None:
        """Add Python idioms"""
        idioms = [
            ("null_check", "if x is None", "if not x"),
            ("dict_access", "dict.get(key, default)", "dict[key] if key in dict"),
            ("list_comp", "[x for x in items]", "list(map(lambda...))"),
            ("context_manager", "with open() as f", "f = open(); try/finally"),
            ("f_strings", "f'Hello {name}'", "'Hello ' + name"),
        ]
        for pattern, preferred, avoid in idioms:
            self.memory.conventions.add_idiom(pattern, preferred, avoid)

    def _add_js_idioms(self) -> None:
        """Add JavaScript/TypeScript idioms"""
        idioms = [
            ("null_check", "x ?? default", "x || default"),
            ("array_methods", "arr.map()", "for loop"),
            ("async_await", "async/await", "Promise.then()"),
            ("destructuring", "const { a, b } = obj", "const a = obj.a"),
            ("template_literal", "`Hello ${name}`", "'Hello ' + name"),
        ]
        for pattern, preferred, avoid in idioms:
            self.memory.conventions.add_idiom(pattern, preferred, avoid)

    def add_convention(self, category: str, rule: str, enforced_by: str = "manual") -> None:
        """Add a custom convention"""
        self.memory.conventions.add_convention(category, rule, enforced_by)
        self._save()

    # =========================================================================
    # Decision Making
    # =========================================================================

    def decide(
        self,
        title: str,
        reason: str,
        alternatives: Optional[Dict[str, str]] = None,
        constraints: Optional[List[str]] = None
    ) -> str:
        """
        Record an architectural/technical decision.

        Args:
            title: Decision title (e.g., "Use FastAPI")
            reason: Why this decision was made
            alternatives: Dict of {alternative: why_rejected}
            constraints: What this decision constrains

        Returns:
            Decision ID
        """
        dec_id = self.memory.decisions.add_decision(
            title=title,
            context=reason,
        )

        # Record alternatives
        for alt, rejection in (alternatives or {}).items():
            self.memory.decisions.add_alternative(title, alt, rejection)

        # Record constraints
        for module in (constraints or []):
            self.memory.decisions.add_constraint(
                title,
                module,
                how=f"Must follow {title}"
            )

        self._save()
        return dec_id

    # =========================================================================
    # Template Setup
    # =========================================================================

    def add_template(
        self,
        name: str,
        category: str,
        code: str,
        usage: str
    ) -> str:
        """
        Add a code template for the project.

        Args:
            name: Template name
            category: Template category (model, handler, service, etc.)
            code: Template code
            usage: When to use this template

        Returns:
            Template ID
        """
        self.memory.templates.add_snippet(name, code, usage)
        self._save()
        return name

    def add_project_pattern(self, name: str, template: str, usage: str) -> None:
        """Add a project-specific pattern"""
        self.memory.conventions.add_project_pattern(name, template, usage)
        self._save()

    # =========================================================================
    # Bug Pattern Setup (Preventive)
    # =========================================================================

    def watch_for(
        self,
        bug_name: str,
        signature: str,
        fix: str,
        modules: Optional[List[str]] = None
    ) -> None:
        """
        Pre-register bug patterns to watch for.

        Based on common issues in this type of project.

        Args:
            bug_name: Bug pattern name
            signature: How to recognize it
            fix: How to fix it
            modules: Modules where this is likely
        """
        self.memory.bugs.add_pattern(bug_name, signature, modules or [])
        self.memory.bugs.add_fix_pattern(bug_name, fix)
        self._save()

    def setup_common_bug_patterns(self) -> None:
        """Set up common bug patterns based on language"""
        if self.language == "python":
            patterns = [
                ("mutable_default", "def func(x=[])", "Use None, assign in body", ["all"]),
                ("late_binding_closure", "lambda in loop", "Use default arg: lambda x=x", ["all"]),
                ("import_cycle", "circular import", "Move import inside function or restructure", ["all"]),
                ("async_not_awaited", "async func called without await", "Add await keyword", ["all"]),
            ]
        elif self.language in ("typescript", "javascript"):
            patterns = [
                ("undefined_access", "accessing undefined property", "Use optional chaining ?.", ["all"]),
                ("async_no_catch", "unhandled promise rejection", "Add .catch() or try/catch", ["all"]),
                ("mutation_in_map", "mutating in map/filter", "Return new object instead", ["all"]),
            ]
        elif self.language == "rust":
            patterns = [
                ("ownership_move", "use after move", "Clone or use reference", ["all"]),
                ("lifetime_mismatch", "lifetime errors", "Add explicit lifetime annotations", ["all"]),
            ]
        else:
            patterns = []

        for name, sig, fix, mods in patterns:
            self.memory.bugs.add_pattern(name, sig, mods)
            self.memory.bugs.add_fix_pattern(name, fix)

        self._save()

    # =========================================================================
    # Session Management
    # =========================================================================

    def start_session(self, task: str) -> tuple:
        """Start a coding session"""
        self._current_session = self.memory.start_session(task)
        context = self.memory.get_context(task=task)
        return self._current_session, context

    def end_session(self, completion: float = 1.0, outcome: str = "success") -> None:
        """End the current session"""
        if self._current_session:
            self.memory.end_session(self._current_session, completion)
            self._current_session = None
        self._save()

    def record_decision(self, decision: str, rationale: str) -> None:
        """Record a decision made during session"""
        if self._current_session:
            self.memory.sessions.add_decision(
                self._current_session, decision, rationale, sticky=True
            )

    def record_learning(self, skill: str, lesson: str) -> None:
        """Record something learned during development"""
        self.memory.skills.record_learning_event(
            skill, "discovery", self._current_session or "", lesson
        )
        self._save()

    # =========================================================================
    # Context
    # =========================================================================

    def get_context(self, task: str = "", files: Optional[List[str]] = None) -> CodingContext:
        """Get coding context"""
        return self.memory.get_context(task=task, files=files or [])

    def get_setup_prompt(self) -> str:
        """
        Get a prompt summarizing project setup.

        Useful at the start of each session.
        """
        lines = [
            f"# Project: {self.name}",
            f"Language: {self.language}",
            f"Description: {self.description}",
            ""
        ]

        if self._architecture:
            lines.append("## Architecture")
            lines.append(f"Style: {self._architecture.get('style', 'not set')}")
            if self._architecture.get("layers"):
                lines.append(f"Layers: {', '.join(self._architecture['layers'])}")
            lines.append("")

        # Add conventions summary
        conventions = []
        for node in self.memory.graph.nodes():
            if node.type == "convention":
                conventions.append(f"- [{node.properties.get('category')}] {node.properties.get('rule')}")

        if conventions:
            lines.append("## Conventions")
            lines.extend(conventions[:10])  # Limit
            lines.append("")

        # Add key decisions
        decisions = []
        for node in self.memory.graph.nodes():
            if node.type == "decision":
                decisions.append(f"- {node.properties.get('title')}: {node.properties.get('context', '')[:50]}")

        if decisions:
            lines.append("## Key Decisions")
            lines.extend(decisions[:5])
            lines.append("")

        return "\n".join(lines)

    # =========================================================================
    # Persistence
    # =========================================================================

    def _save(self) -> None:
        """Save memory to disk"""
        self.memory.save(self.memory_path)

    def save(self) -> None:
        """Explicitly save memory"""
        self._save()

    @classmethod
    def load(cls, path: str) -> "GreenfieldProject":
        """Load an existing greenfield project"""
        memory_path = os.path.join(path, ".agent-memory")
        if not os.path.exists(memory_path):
            raise FileNotFoundError(f"No memory found at {memory_path}")

        memory = AgentMemory.load(memory_path)

        # Extract project info
        project_node = memory.graph.get_node("project", "main")
        if project_node:
            name = project_node.properties.get("name", "unknown")
            language = project_node.properties.get("language", "python")
            description = project_node.properties.get("description", "")
        else:
            name = os.path.basename(path)
            language = "python"
            description = ""

        # Create instance without reinitializing
        project = cls.__new__(cls)
        project.name = name
        project.path = path
        project.language = language
        project.description = description
        project.memory_path = memory_path
        project.memory = memory
        project._current_session = None
        project._architecture = {}

        return project


# =============================================================================
# Quick Setup Functions
# =============================================================================

def new_python_project(
    name: str,
    path: str,
    style: str = "layered",
    framework: str = "fastapi"
) -> GreenfieldProject:
    """
    Quick setup for a new Python project.

    Args:
        name: Project name
        path: Project path
        style: Architecture style
        framework: Web framework (fastapi, flask, django, none)

    Returns:
        Configured GreenfieldProject
    """
    project = GreenfieldProject(name, path, "python", f"{framework} project")

    # Set architecture
    if style == "layered":
        project.set_architecture(
            style="layered",
            layers=["api", "services", "repositories", "models"],
            patterns=["repository", "dependency_injection"]
        )
    elif style == "hexagonal":
        project.set_architecture(
            style="hexagonal",
            layers=["adapters", "ports", "domain", "application"],
            patterns=["ports_and_adapters"]
        )

    # Set conventions
    project.set_conventions(
        naming="snake_case",
        typing="strict",
        testing="pytest",
        formatting="black",
        linting="ruff",
        docstrings="google"
    )

    # Framework-specific decisions
    if framework == "fastapi":
        project.decide(
            "Use FastAPI",
            "Async support, auto OpenAPI, type hints",
            alternatives={
                "Flask": "No native async",
                "Django": "Too heavy for API-only"
            }
        )
        project.decide(
            "Use Pydantic for validation",
            "Native FastAPI integration, excellent type support",
            alternatives={"marshmallow": "Not as well integrated"}
        )
    elif framework == "flask":
        project.decide("Use Flask", "Simple, flexible, well-documented")

    # Common Python bug patterns
    project.setup_common_bug_patterns()

    return project


def new_typescript_project(
    name: str,
    path: str,
    style: str = "layered",
    framework: str = "express"
) -> GreenfieldProject:
    """
    Quick setup for a new TypeScript project.
    """
    project = GreenfieldProject(name, path, "typescript", f"{framework} project")

    project.set_architecture(
        style=style,
        layers=["routes", "controllers", "services", "models"],
        patterns=["dependency_injection", "repository"]
    )

    project.set_conventions(
        naming="camelCase",
        typing="strict",
        testing="jest",
        formatting="prettier",
        linting="eslint"
    )

    if framework == "express":
        project.decide(
            "Use Express.js",
            "Mature, flexible, large ecosystem",
            alternatives={"Fastify": "Less mature ecosystem"}
        )

    project.setup_common_bug_patterns()

    return project


def new_rust_project(
    name: str,
    path: str,
    project_type: str = "cli"
) -> GreenfieldProject:
    """
    Quick setup for a new Rust project.
    """
    project = GreenfieldProject(name, path, "rust", f"Rust {project_type}")

    project.set_architecture(
        style="modular",
        layers=["lib", "bin"] if project_type == "cli" else ["src"],
        patterns=["builder", "newtype"]
    )

    project.set_conventions(
        naming="snake_case",
        typing="strict",  # Rust is always strict
        testing="cargo_test",
        formatting="rustfmt",
        linting="clippy"
    )

    project.setup_common_bug_patterns()

    return project
