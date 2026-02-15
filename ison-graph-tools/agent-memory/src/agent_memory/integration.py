"""
Agent Integration - How coding agents adopt and use the memory system

This module provides the integration layer for coding agents to:
1. Bootstrap memory for a new project
2. Learn from the codebase automatically
3. Use memory during coding sessions
4. Update memory based on outcomes

Workflow:
=========

Phase 1: BOOTSTRAP (First encounter with project)
    - Scan codebase structure
    - Extract conventions from existing code
    - Load existing documentation (ADRs, READMEs)
    - Initialize skill baseline

Phase 2: SESSION START (Each coding session)
    - Load memory
    - Start session with task
    - Get relevant context
    - Apply context to coding

Phase 3: DURING SESSION (While coding)
    - Check suggestions against memory
    - Record decisions made
    - Track partial work
    - Note open questions

Phase 4: SESSION END (After coding)
    - Record outcomes (success/failure)
    - Update skill proficiency
    - Save memory
    - Run consolidation

Phase 5: CONTINUOUS LEARNING (Over time)
    - Reinforce successful patterns
    - Decay unused memories
    - Merge similar items
    - Track skill progression
"""

import os
import ast
import re
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path

from .memory import AgentMemory
from .context import CodingContext


class AgentIntegration:
    """
    Integration layer for coding agents.

    Provides high-level methods for the complete agent lifecycle.
    """

    def __init__(self, project_path: str, memory_path: Optional[str] = None):
        """
        Initialize agent integration.

        Args:
            project_path: Path to the project directory
            memory_path: Path to memory file (default: .agent-memory in project)
        """
        self.project_path = os.path.abspath(project_path)
        self.project_name = os.path.basename(self.project_path)
        self.memory_path = memory_path or os.path.join(
            self.project_path, ".agent-memory"
        )

        # Load or create memory
        if os.path.exists(self.memory_path):
            self.memory = AgentMemory.load(self.memory_path)
            self._is_new = False
        else:
            self.memory = AgentMemory(name=self.project_name)
            self._is_new = True

        self._current_session: Optional[str] = None

    # =========================================================================
    # Phase 1: BOOTSTRAP
    # =========================================================================

    def bootstrap(self, deep_scan: bool = True, code_flow: bool = True) -> Dict[str, Any]:
        """
        Bootstrap memory for a new project.

        This should be called once when first encountering a project.
        Scans the codebase and extracts initial knowledge.

        Args:
            deep_scan: If True, performs deep analysis of code
            code_flow: If True, uses code-flow-graph for deep structural analysis

        Returns:
            Summary of what was learned
        """
        summary = {
            "modules": 0,
            "conventions": 0,
            "patterns": 0,
            "decisions": 0,
            "dependencies": 0,
            "code_flow": {},
        }

        # 1. Scan directory structure for modules
        summary["modules"] = self._scan_modules()

        # 2. Detect conventions from existing code
        summary["conventions"] = self._detect_conventions()

        # 3. Load pyproject.toml / package.json for dependencies
        summary["dependencies"] = self._scan_dependencies()

        # 4. Look for ADRs or decision docs
        summary["decisions"] = self._scan_decisions()

        # 5. Detect common patterns
        if deep_scan:
            summary["patterns"] = self._detect_patterns()

        # 6. Initialize baseline skills
        self._initialize_skills()

        # 7. Deep code flow analysis (if code-flow-graph is available)
        if code_flow:
            summary["code_flow"] = self._analyze_code_flow()

        # Save bootstrapped memory
        self.memory.save(self.memory_path)

        return summary

    def _analyze_code_flow(self) -> Dict[str, int]:
        """Analyze code structure using code-flow-graph"""
        try:
            from .code_flow_integration import CodeFlowIntegration
            flow = CodeFlowIntegration(self.memory)
            return flow.analyze_and_enrich(self.project_path)
        except ImportError:
            return {"error": "code-flow-graph not installed"}
        except Exception as e:
            return {"error": str(e)}

    def _scan_modules(self) -> int:
        """Scan project structure for modules"""
        count = 0

        for root, dirs, files in os.walk(self.project_path):
            # Skip hidden and common non-code directories
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in (
                'node_modules', 'venv', 'env', '__pycache__', 'dist', 'build',
                '.git', '.venv', 'target'
            )]

            rel_path = os.path.relpath(root, self.project_path)
            if rel_path == '.':
                continue

            # Determine module purpose from directory name
            purpose = self._infer_purpose(os.path.basename(root))

            # Check complexity by file count
            code_files = [f for f in files if f.endswith(('.py', '.ts', '.js', '.rs'))]
            complexity = "low"
            if len(code_files) > 10:
                complexity = "high"
            elif len(code_files) > 5:
                complexity = "medium"

            self.memory.codebase.add_module(
                path=rel_path,
                purpose=purpose,
                complexity=complexity
            )
            count += 1

        return count

    def _infer_purpose(self, dirname: str) -> str:
        """Infer module purpose from directory name"""
        purpose_map = {
            'api': 'HTTP API handlers',
            'handlers': 'Request handlers',
            'routes': 'URL routing',
            'models': 'Data models',
            'schemas': 'Data schemas/validation',
            'services': 'Business logic services',
            'utils': 'Utility functions',
            'helpers': 'Helper functions',
            'core': 'Core functionality',
            'lib': 'Library code',
            'tests': 'Test suite',
            'test': 'Test suite',
            'config': 'Configuration',
            'db': 'Database layer',
            'database': 'Database layer',
            'storage': 'Data storage',
            'cache': 'Caching layer',
            'auth': 'Authentication',
            'middleware': 'Middleware',
            'cli': 'Command-line interface',
            'commands': 'CLI commands',
            'migrations': 'Database migrations',
            'static': 'Static assets',
            'templates': 'Template files',
            'views': 'View layer',
            'components': 'UI components',
        }
        return purpose_map.get(dirname.lower(), f'{dirname} module')

    def _detect_conventions(self) -> int:
        """Detect code conventions from existing code"""
        count = 0

        # Find Python files
        py_files = list(Path(self.project_path).rglob('*.py'))[:10]  # Sample 10 files

        if py_files:
            # Detect naming conventions
            uses_snake_case = True
            uses_type_hints = False

            for py_file in py_files:
                try:
                    with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()

                    # Check for type hints
                    if ': ' in content and '->' in content:
                        uses_type_hints = True

                    # Check function naming
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            if not node.name.startswith('_'):
                                if not re.match(r'^[a-z][a-z0-9_]*$', node.name):
                                    uses_snake_case = False
                except:
                    continue

            if uses_snake_case:
                self.memory.conventions.add_convention(
                    category="naming",
                    rule="snake_case for functions",
                    enforced_by="detected"
                )
                count += 1

            if uses_type_hints:
                self.memory.conventions.add_convention(
                    category="typing",
                    rule="use type annotations",
                    enforced_by="detected"
                )
                count += 1

        # Check for config files that indicate conventions
        if os.path.exists(os.path.join(self.project_path, 'pyproject.toml')):
            with open(os.path.join(self.project_path, 'pyproject.toml'), 'r') as f:
                content = f.read()
                if 'ruff' in content.lower():
                    self.memory.conventions.add_convention(
                        category="linting",
                        rule="use ruff for linting",
                        enforced_by="ruff"
                    )
                    count += 1
                if 'black' in content.lower():
                    self.memory.conventions.add_convention(
                        category="formatting",
                        rule="use black for formatting",
                        enforced_by="black"
                    )
                    count += 1
                if 'mypy' in content.lower():
                    self.memory.conventions.add_convention(
                        category="typing",
                        rule="use mypy for type checking",
                        enforced_by="mypy"
                    )
                    count += 1

        return count

    def _scan_dependencies(self) -> int:
        """Scan for project dependencies"""
        count = 0

        # Python: pyproject.toml or requirements.txt
        pyproject = os.path.join(self.project_path, 'pyproject.toml')
        if os.path.exists(pyproject):
            with open(pyproject, 'r') as f:
                content = f.read()
                # Simple extraction of dependencies
                if 'dependencies' in content:
                    # Extract common dependencies
                    common_deps = [
                        ('pydantic', 'validation'),
                        ('fastapi', 'http'),
                        ('flask', 'http'),
                        ('django', 'http'),
                        ('sqlalchemy', 'database'),
                        ('pytest', 'testing'),
                        ('requests', 'http'),
                        ('httpx', 'http'),
                        ('redis', 'cache'),
                        ('celery', 'tasks'),
                    ]
                    for dep, category in common_deps:
                        if dep in content.lower():
                            self.memory.dependencies.add_dependency(
                                name=dep,
                                version="*",
                                category=category
                            )
                            count += 1

        # Node: package.json
        package_json = os.path.join(self.project_path, 'package.json')
        if os.path.exists(package_json):
            import json
            with open(package_json, 'r') as f:
                pkg = json.load(f)
                deps = {**pkg.get('dependencies', {}), **pkg.get('devDependencies', {})}
                for dep in list(deps.keys())[:20]:  # Limit to 20
                    self.memory.dependencies.add_dependency(
                        name=dep,
                        version=deps[dep],
                        category="npm"
                    )
                    count += 1

        return count

    def _scan_decisions(self) -> int:
        """Scan for architectural decision documents"""
        count = 0

        # Look for ADR directory
        adr_dirs = ['adr', 'adrs', 'docs/adr', 'docs/adrs', 'docs/decisions']
        for adr_dir in adr_dirs:
            full_path = os.path.join(self.project_path, adr_dir)
            if os.path.isdir(full_path):
                for file in os.listdir(full_path):
                    if file.endswith('.md'):
                        # Extract title from filename
                        title = file.replace('.md', '').replace('-', ' ').replace('_', ' ')
                        self.memory.decisions.add_decision(
                            title=title,
                            context=f"ADR from {adr_dir}/{file}"
                        )
                        count += 1

        return count

    def _detect_patterns(self) -> int:
        """Detect common patterns in the codebase"""
        count = 0

        # Look for common Python patterns
        py_files = list(Path(self.project_path).rglob('*.py'))[:20]

        patterns_found = set()

        for py_file in py_files:
            try:
                with open(py_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                # Singleton pattern
                if '@singleton' in content or '__new__' in content:
                    patterns_found.add('singleton')

                # Factory pattern
                if 'Factory' in content or 'create_' in content:
                    patterns_found.add('factory')

                # Repository pattern
                if 'Repository' in content:
                    patterns_found.add('repository')

                # Decorator pattern
                if '@' in content and 'def ' in content:
                    patterns_found.add('decorator')

                # Context manager
                if '__enter__' in content or 'with ' in content:
                    patterns_found.add('context_manager')

            except:
                continue

        for pattern in patterns_found:
            self.memory.codebase.add_pattern(
                name=pattern,
                modules=[],
                why_chosen="detected in codebase"
            )
            count += 1

        return count

    def _initialize_skills(self) -> None:
        """Initialize baseline skills based on project language"""
        # Detect primary language
        py_files = len(list(Path(self.project_path).rglob('*.py')))
        ts_files = len(list(Path(self.project_path).rglob('*.ts')))
        js_files = len(list(Path(self.project_path).rglob('*.js')))
        rs_files = len(list(Path(self.project_path).rglob('*.rs')))

        if py_files > 0:
            self.memory.skills.add_skill('python', 'language', proficiency=0.5)
            self.memory.skills.add_skill('python_async', 'language', proficiency=0.3)

        if ts_files > 0:
            self.memory.skills.add_skill('typescript', 'language', proficiency=0.5)

        if js_files > 0:
            self.memory.skills.add_skill('javascript', 'language', proficiency=0.5)

        if rs_files > 0:
            self.memory.skills.add_skill('rust', 'language', proficiency=0.5)

        # Add general skills
        self.memory.skills.add_skill('git', 'tooling', proficiency=0.7)
        self.memory.skills.add_skill('debugging', 'general', proficiency=0.5)
        self.memory.skills.add_skill('testing', 'general', proficiency=0.5)

    # =========================================================================
    # Phase 2: SESSION START
    # =========================================================================

    def start_session(self, task: str) -> Tuple[str, CodingContext]:
        """
        Start a coding session.

        Args:
            task: Description of what will be worked on

        Returns:
            Tuple of (session_id, relevant context)
        """
        # Start session in memory
        self._current_session = self.memory.start_session(task)

        # Get relevant context for the task
        context = self.memory.get_context(task=task)

        return self._current_session, context

    def get_context_for_files(self, files: List[str]) -> CodingContext:
        """
        Get context for specific files being modified.

        Call this when starting to work on specific files.
        """
        task = self.memory.sessions.get_session_context(self._current_session).get(
            "session", {}
        ).get("task", "")

        return self.memory.get_context(task=task, files=files)

    # =========================================================================
    # Phase 3: DURING SESSION
    # =========================================================================

    def check_before_coding(self, suggestion: str) -> List[Dict[str, Any]]:
        """
        Check a suggestion/approach before implementing.

        Returns warnings if the suggestion conflicts with memory.
        """
        return self.memory.check_suggestion(suggestion)

    def record_decision(self, decision: str, rationale: str, sticky: bool = True) -> None:
        """Record a decision made during the session"""
        if self._current_session:
            self.memory.sessions.add_decision(
                self._current_session,
                decision,
                rationale,
                sticky
            )

    def record_question(self, question: str) -> None:
        """Record an open question that needs answering"""
        if self._current_session:
            self.memory.sessions.add_open_question(self._current_session, question)

    def answer_question(self, question: str, answer: str) -> None:
        """Answer a previously recorded question"""
        self.memory.sessions.answer_question(question, answer, self._current_session or "")

    def record_partial_work(self, work_type: str, location: str, state: str) -> None:
        """Record incomplete work for later continuation"""
        if self._current_session:
            self.memory.sessions.add_partial_work(
                self._current_session,
                work_type,
                location,
                state
            )

    def record_blocker(self, description: str) -> None:
        """Record a blocker encountered"""
        if self._current_session:
            self.memory.sessions.add_blocker(self._current_session, description)

    def resolve_blocker(self, description: str, resolution: str) -> None:
        """Mark a blocker as resolved"""
        self.memory.sessions.resolve_blocker(
            description,
            self._current_session or "",
            resolution
        )

    # =========================================================================
    # Phase 4: SESSION END
    # =========================================================================

    def end_session(
        self,
        completion: float = 1.0,
        outcome: str = "success",
        lessons: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        End the current session.

        Args:
            completion: How much of the task was completed (0.0-1.0)
            outcome: 'success', 'partial', or 'failed'
            lessons: List of lessons learned

        Returns:
            Session summary
        """
        if not self._current_session:
            return {}

        # End session
        self.memory.end_session(self._current_session, completion)

        # Record lessons as learning events
        if lessons:
            for lesson in lessons:
                # Try to associate with a skill
                self.memory.skills.record_learning_event(
                    skill_name="general",
                    event_type=outcome,
                    context=self._current_session,
                    lesson=lesson
                )

        # Update skill proficiency based on outcome
        if outcome == "success":
            self._reinforce_skills(0.02)
        elif outcome == "failed":
            self._reinforce_skills(-0.01)

        # Save memory
        self.memory.save(self.memory_path)

        # Get session summary
        summary = self.memory.sessions.get_session_context(self._current_session)

        self._current_session = None

        return summary

    def _reinforce_skills(self, delta: float) -> None:
        """Adjust skill proficiency based on session outcome"""
        for node in self.memory.graph.nodes():
            if node.type == "skill":
                current = float(node.properties.get("proficiency", 0.5))
                new_prof = max(0.0, min(1.0, current + delta))
                self.memory.skills.update_proficiency(
                    node.properties.get("name", ""),
                    new_prof
                )

    # =========================================================================
    # Phase 5: CONTINUOUS LEARNING
    # =========================================================================

    def learn_from_feedback(
        self,
        feedback_type: str,
        context: str,
        correction: Optional[str] = None
    ) -> None:
        """
        Learn from user feedback.

        Args:
            feedback_type: 'bug_caught', 'convention_violated', 'good_pattern', etc.
            context: What the feedback was about
            correction: What the correct approach should be
        """
        if feedback_type == "bug_caught":
            # Record that we missed a bug
            self.memory.bugs.record_miss(
                pattern_name=context,
                consequence="User had to catch it",
                post_mortem=correction or "Need to watch for this"
            )

        elif feedback_type == "convention_violated":
            # Find or create the convention
            conv_id = self.memory.conventions.add_convention(
                category="learned",
                rule=correction or context,
                enforced_by="user_feedback"
            )
            self.memory.conventions.record_violation(conv_id, context)

        elif feedback_type == "good_pattern":
            # Reinforce the pattern
            self.memory.templates.add_snippet(
                name=f"pattern_{len(context)%100}",
                code=context,
                usage_context=correction or "learned pattern"
            )

        # Save after learning
        self.memory.save(self.memory_path)

    def learn_convention(
        self,
        category: str,
        rule: str,
        example: str,
        enforced_by: str = "learned"
    ) -> None:
        """Learn a new convention from observation"""
        conv_id = self.memory.conventions.add_convention(
            category=category,
            rule=rule,
            enforced_by=enforced_by
        )
        self.memory.conventions.record_learning(conv_id, examples_seen=1, confidence=0.7)
        self.memory.save(self.memory_path)

    def learn_bug_pattern(
        self,
        name: str,
        signature: str,
        fix_template: str,
        modules: Optional[List[str]] = None
    ) -> None:
        """Learn a new bug pattern from experience"""
        self.memory.bugs.add_pattern(name, signature, modules or [])
        self.memory.bugs.add_fix_pattern(name, fix_template)
        self.memory.save(self.memory_path)

    def prevent_bug(self, pattern_name: str, location: str) -> None:
        """Record that we successfully prevented a bug"""
        self.memory.bugs.record_prevention(pattern_name, location)
        # Boost skill confidence
        self._reinforce_skills(0.01)
        self.memory.save(self.memory_path)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_session_handoff(self) -> str:
        """
        Get a handoff summary for the next session.

        Returns a formatted string suitable for including in a prompt.
        """
        last_session = self.memory.sessions.get_last_session()
        if not last_session:
            return "No previous session found."

        context = self.memory.sessions.get_session_context(last_session)

        lines = ["## Session Handoff\n"]

        if context.get("session"):
            session = context["session"]
            lines.append(f"Last task: {session.get('task', 'Unknown')}")
            lines.append(f"Completion: {float(session.get('completion', 0)):.0%}")

        if context.get("decisions"):
            lines.append("\n### Decisions Made:")
            for d in context["decisions"]:
                lines.append(f"- {d.get('decision', '')}: {d.get('rationale', '')}")

        if context.get("partial_work"):
            lines.append("\n### Incomplete Work:")
            for pw in context["partial_work"]:
                lines.append(f"- [{pw.get('work_type', '')}] {pw.get('location', '')}: {pw.get('state', '')}")

        if context.get("open_questions"):
            lines.append("\n### Open Questions:")
            for q in context["open_questions"]:
                lines.append(f"- {q.get('question', '')}")

        if context.get("blockers"):
            lines.append("\n### Unresolved Blockers:")
            for b in context["blockers"]:
                lines.append(f"- {b.get('description', '')}")

        return "\n".join(lines)

    def get_skill_summary(self) -> str:
        """Get a summary of current skill levels"""
        lines = ["## Skill Summary\n"]

        proficient = self.memory.skills.get_proficient_skills(0.7)
        learning = self.memory.skills.get_skills_needing_practice(0.5)

        if proficient:
            lines.append("### Proficient:")
            for s in proficient[:5]:
                lines.append(f"- {s.get('name', '')}: {float(s.get('proficiency', 0)):.0%}")

        if learning:
            lines.append("\n### Needs Practice:")
            for s in learning[:5]:
                lines.append(f"- {s.get('name', '')}: {float(s.get('proficiency', 0)):.0%}")

        return "\n".join(lines)

    @property
    def is_new_project(self) -> bool:
        """Check if this is a new project (no prior memory)"""
        return self._is_new


# =============================================================================
# Convenience Functions
# =============================================================================

def prepare_for_project(project_path: str) -> AgentIntegration:
    """
    Prepare agent memory for a project.

    If new project, bootstraps memory.
    If existing, loads and returns integration.
    """
    integration = AgentIntegration(project_path)

    if integration.is_new_project:
        print(f"Bootstrapping memory for new project: {integration.project_name}")
        summary = integration.bootstrap()
        print(f"  Modules: {summary['modules']}")
        print(f"  Conventions: {summary['conventions']}")
        print(f"  Dependencies: {summary['dependencies']}")
        print(f"  Patterns: {summary['patterns']}")
    else:
        print(f"Loaded existing memory for: {integration.project_name}")
        stats = integration.memory.get_stats()
        print(f"  Nodes: {stats['total_nodes']}, Edges: {stats['total_edges']}")

    return integration


def quick_context(project_path: str, task: str, files: Optional[List[str]] = None) -> str:
    """
    Quick one-shot context for a task.

    Use this for simple queries without full session management.
    """
    integration = AgentIntegration(project_path)
    context = integration.memory.get_context(task=task, files=files or [])
    return context.to_prompt()
