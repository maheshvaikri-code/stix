#!/usr/bin/env python3
"""
Greenfield Project Workflow
===========================

This example shows how a coding agent starts with a BRAND NEW project
where no code exists yet. The agent:

1. Sets up project memory with architecture decisions
2. Defines conventions BEFORE writing code
3. Creates templates as patterns emerge
4. Builds knowledge from day 1
"""

import tempfile
import os

from agent_memory import (
    GreenfieldProject,
    new_python_project,
)


def example_manual_setup():
    """
    Example: Manual greenfield project setup
    """
    print("\n" + "="*60)
    print("MANUAL GREENFIELD SETUP")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = os.path.join(tmpdir, "my-api")

        # Create new project
        project = GreenfieldProject(
            name="my-api",
            path=project_path,
            language="python",
            description="User management REST API"
        )

        print(f"\nCreated project: {project.name}")
        print(f"Path: {project_path}")

        # Step 1: Define architecture BEFORE writing code
        print("\n--- Step 1: Define Architecture ---")
        project.set_architecture(
            style="layered",
            layers=["api", "services", "repositories", "models", "schemas"],
            patterns=["repository", "dependency_injection", "factory"],
            description="Clean layered architecture with clear separation"
        )
        print("Architecture set: layered with 5 layers")

        # Step 2: Set conventions BEFORE writing code
        print("\n--- Step 2: Set Conventions ---")
        project.set_conventions(
            naming="snake_case",
            typing="strict",
            testing="pytest",
            formatting="black",
            linting="ruff",
            docstrings="google"
        )
        print("Conventions set: snake_case, strict typing, pytest, black, ruff")

        # Step 3: Make initial decisions
        print("\n--- Step 3: Record Decisions ---")

        project.decide(
            "Use FastAPI",
            "Need async support and automatic OpenAPI documentation",
            alternatives={
                "Flask": "No native async support",
                "Django": "Too heavy for API-only service",
                "Starlette": "Lower level, FastAPI adds nice features"
            },
            constraints=["api"]
        )
        print("Decision: Use FastAPI")

        project.decide(
            "Use SQLAlchemy 2.0",
            "Mature ORM with good async support in 2.0",
            alternatives={
                "Tortoise ORM": "Less mature",
                "Raw SQL": "Too low level"
            },
            constraints=["repositories", "models"]
        )
        print("Decision: Use SQLAlchemy 2.0")

        project.decide(
            "Use Pydantic for schemas",
            "Native FastAPI integration, excellent validation",
            constraints=["schemas", "api"]
        )
        print("Decision: Use Pydantic")

        # Step 4: Set up bug patterns to watch for
        print("\n--- Step 4: Set Up Bug Patterns ---")
        project.setup_common_bug_patterns()

        project.watch_for(
            "n_plus_one",
            "Query in loop without eager loading",
            "Use joinedload() or selectinload()",
            modules=["repositories"]
        )
        project.watch_for(
            "unvalidated_input",
            "User input used without Pydantic validation",
            "Always use Pydantic schemas for input",
            modules=["api"]
        )
        print("Bug patterns registered: mutable_default, n_plus_one, unvalidated_input, ...")

        # Step 5: Add project templates
        print("\n--- Step 5: Add Templates ---")

        project.add_project_pattern(
            "api_endpoint",
            '''
@router.get("/{id}", response_model=ResponseSchema)
async def get_item(id: int, service: Service = Depends(get_service)):
    return await service.get_by_id(id)
''',
            "Use for all GET endpoints"
        )

        project.add_project_pattern(
            "repository_method",
            '''
async def get_by_id(self, id: int) -> Optional[Model]:
    stmt = select(Model).where(Model.id == id)
    result = await self.session.execute(stmt)
    return result.scalar_one_or_none()
''',
            "Use for all repository methods"
        )
        print("Templates added: api_endpoint, repository_method")

        # Show the setup prompt
        print("\n--- Project Setup Summary ---")
        print(project.get_setup_prompt())

        # Step 6: Start first coding session
        print("\n--- Step 6: First Coding Session ---")
        session_id, context = project.start_session("Create project structure and base models")

        print(f"Session started: {session_id}")
        print("\nContext for coding:")
        print(context.to_prompt() or "(Initial context - conventions and decisions)")

        # Simulate work
        project.record_decision(
            "Use UUID for primary keys",
            "Better for distributed systems and security"
        )

        project.record_learning(
            "python_async",
            "SQLAlchemy async requires async session context manager"
        )

        project.end_session(completion=0.3, outcome="success")
        print("\nSession ended: 30% complete")

        # Show final stats
        print("\n--- Memory Stats ---")
        stats = project.memory.get_stats()
        print(f"Nodes: {stats['total_nodes']}")
        print(f"Edges: {stats['total_edges']}")
        print(f"Decisions: {stats['stores']['decisions']['decisions']}")
        print(f"Conventions: {stats['stores']['conventions']['conventions']}")
        print(f"Bug patterns: {stats['stores']['bugs']['patterns']}")

        return project


def example_quick_setup():
    """
    Example: Quick setup using helper functions
    """
    print("\n" + "="*60)
    print("QUICK GREENFIELD SETUP")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = os.path.join(tmpdir, "quick-api")

        # One-liner setup
        project = new_python_project(
            name="quick-api",
            path=project_path,
            style="layered",
            framework="fastapi"
        )

        print(f"\nCreated project: {project.name}")
        print("\nSetup includes:")
        print("  - Layered architecture (api, services, repositories, models)")
        print("  - Python conventions (snake_case, black, ruff, mypy)")
        print("  - FastAPI + Pydantic decisions")
        print("  - Common Python bug patterns")
        print("  - Python idioms")

        print("\n--- Setup Prompt ---")
        print(project.get_setup_prompt())

        return project


def example_session_continuity():
    """
    Example: Multiple sessions building up knowledge
    """
    print("\n" + "="*60)
    print("SESSION CONTINUITY")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = os.path.join(tmpdir, "growing-project")

        # Session 1: Setup
        print("\n--- Session 1: Initial Setup ---")
        project = new_python_project("growing-project", project_path, framework="fastapi")
        session_id, _ = project.start_session("Set up project structure")

        project.decide("Use PostgreSQL", "Need relational data with strong consistency")
        project.record_learning("python", "FastAPI auto-generates OpenAPI docs")

        project.end_session(1.0, "success")
        project.save()
        print("Session 1 complete")

        # Session 2: Load and continue
        print("\n--- Session 2: Add User Model ---")
        project = GreenfieldProject.load(project_path)
        session_id, context = project.start_session("Create User model and endpoints")

        print("Context from previous session:")
        print(context.to_prompt()[:500] if context.to_prompt() else "(Previous decisions available)")

        project.decide("Use bcrypt for passwords", "Industry standard, well-tested")
        project.watch_for(
            "plain_text_password",
            "Password stored without hashing",
            "Always use bcrypt.hash()",
            modules=["services"]
        )

        project.end_session(1.0, "success")
        project.save()
        print("Session 2 complete")

        # Session 3: Continue building
        print("\n--- Session 3: Add Authentication ---")
        project = GreenfieldProject.load(project_path)
        session_id, context = project.start_session("Implement JWT authentication")

        project.decide("Use python-jose for JWT", "Well-maintained, good docs")
        project.add_project_pattern(
            "protected_endpoint",
            '''
@router.get("/protected")
async def protected(user: User = Depends(get_current_user)):
    return {"user": user.email}
''',
            "Use for all authenticated endpoints"
        )

        project.end_session(1.0, "success")
        project.save()
        print("Session 3 complete")

        # Show accumulated knowledge
        print("\n--- Accumulated Knowledge ---")
        stats = project.memory.get_stats()
        print(f"Total nodes: {stats['total_nodes']}")
        print(f"Sessions: {stats['stores']['sessions']['sessions']}")
        print(f"Decisions: {stats['stores']['decisions']['decisions']}")
        print(f"Patterns: {stats['stores']['conventions']['patterns']}")
        print(f"Bug patterns: {stats['stores']['bugs']['patterns']}")

        return project


def main():
    """Run all examples"""
    example_manual_setup()
    example_quick_setup()
    example_session_continuity()

    print("\n" + "="*60)
    print("ALL EXAMPLES COMPLETE")
    print("="*60)
    print("""
Key Takeaways for Fresh Projects:

1. DEFINE architecture BEFORE writing code
   - Layers, patterns, module structure

2. SET conventions BEFORE writing code
   - Naming, typing, testing, formatting

3. RECORD decisions as you make them
   - Include alternatives considered and why rejected

4. REGISTER bug patterns proactively
   - Common pitfalls for your stack

5. CREATE templates as patterns emerge
   - Consistent code generation

6. TRACK learning continuously
   - Skills improve with each session

7. Memory PERSISTS across sessions
   - Knowledge compounds over time
""")


if __name__ == "__main__":
    main()
