#!/usr/bin/env python3
"""
Agent Workflow Example
======================

This example demonstrates the complete lifecycle of how a coding agent
adopts and uses the memory system across multiple sessions.

Phases:
1. BOOTSTRAP - First encounter with a project
2. SESSION 1 - Initial coding session
3. SESSION 2 - Continuation, building on prior session
4. SESSION N - Progressive learning over time
"""

from agent_memory import AgentMemory
from agent_memory.integration import AgentIntegration, prepare_for_project


def phase1_bootstrap(project_path: str):
    """
    Phase 1: BOOTSTRAP
    ==================
    First time the agent encounters a project.
    Scans codebase and builds initial memory.
    """
    print("\n" + "="*60)
    print("PHASE 1: BOOTSTRAP")
    print("="*60)

    # Prepare memory for the project (auto-bootstraps if new)
    agent = prepare_for_project(project_path)

    # The bootstrap already scanned:
    # - Module structure
    # - Code conventions
    # - Dependencies
    # - Patterns
    # - Initial skills

    # Agent can also manually add known information
    agent.memory.decisions.add_decision(
        title="Use async/await",
        context="Need high concurrency for API handlers",
        consequences_positive=["Better throughput", "Non-blocking"],
        consequences_negative=["Complexity"]
    )

    agent.memory.bugs.add_pattern(
        name="race_condition",
        signature="shared_state_without_lock",
        modules_affected=["cache", "session"]
    )
    agent.memory.bugs.add_fix_pattern(
        "race_condition",
        "Use asyncio.Lock or threading.Lock",
        caveats="Check for reentrant needs"
    )

    # Save the bootstrapped memory
    agent.memory.save(agent.memory_path)

    print("\nBootstrap complete!")
    print(f"Memory saved to: {agent.memory_path}")

    return agent


def phase2_session1(agent: AgentIntegration):
    """
    Phase 2: FIRST SESSION
    ======================
    Agent's first coding session on the project.
    """
    print("\n" + "="*60)
    print("PHASE 2: SESSION 1 - Add caching feature")
    print("="*60)

    # Start a new session
    session_id, context = agent.start_session("Add Redis caching layer")

    print(f"\nSession started: {session_id}")
    print("\n--- Context Retrieved ---")
    print(context.to_prompt())

    # Before coding, check if approach is okay
    warnings = agent.check_before_coding("Use global dict for cache")
    if warnings:
        print("\n--- WARNINGS ---")
        for w in warnings:
            print(f"  ! {w}")

    # During coding, record decisions
    agent.record_decision(
        "Use Redis over in-memory dict",
        "Need persistence and sharing across workers",
        sticky=True  # Carries forward to next session
    )

    # Note an open question
    agent.record_question("What should be the default TTL?")

    # Record some partial work (didn't finish everything)
    agent.record_partial_work(
        work_type="code",
        location="src/cache/redis_client.py",
        state="skeleton_only, needs error handling"
    )

    agent.record_partial_work(
        work_type="test",
        location="tests/test_cache.py",
        state="2 of 8 test cases written"
    )

    # End session (not fully complete)
    summary = agent.end_session(
        completion=0.6,
        outcome="partial",
        lessons=["Redis connection pooling is important"]
    )

    print("\n--- Session Summary ---")
    print(f"Completion: 60%")
    print(f"Partial work: {len(summary.get('partial_work', []))} items")
    print(f"Open questions: {len(summary.get('open_questions', []))} items")

    return agent


def phase3_session2(agent: AgentIntegration):
    """
    Phase 3: SECOND SESSION
    =======================
    Agent continues from where it left off.
    """
    print("\n" + "="*60)
    print("PHASE 3: SESSION 2 - Continue caching feature")
    print("="*60)

    # Load fresh (simulating new session)
    agent = AgentIntegration(agent.project_path)

    # Get handoff from previous session
    handoff = agent.get_session_handoff()
    print("\n--- Session Handoff ---")
    print(handoff)

    # Start new session (auto-links to previous)
    session_id, context = agent.start_session("Complete Redis caching implementation")

    print(f"\nSession started: {session_id}")

    # Answer the open question from last session
    agent.answer_question(
        "What should be the default TTL?",
        "5 minutes (300 seconds)"
    )

    # Resolve a blocker (if any)
    # agent.resolve_blocker("...", "...")

    # During coding, successfully prevented a bug!
    agent.prevent_bug("race_condition", "src/cache/redis_client.py:45")
    print("\nPrevented race_condition bug!")

    # Learn a new convention from the codebase
    agent.learn_convention(
        category="error_handling",
        rule="Always use RedisError for cache failures",
        example="raise RedisError(code='CONN_FAILED', msg='...')"
    )

    # Complete the session
    summary = agent.end_session(
        completion=1.0,
        outcome="success",
        lessons=[
            "Redis connection needs timeout config",
            "Cache invalidation pattern: delete on write"
        ]
    )

    print("\n--- Session Complete ---")
    print("Feature completed successfully!")

    return agent


def phase4_progressive_learning(agent: AgentIntegration):
    """
    Phase 4: PROGRESSIVE LEARNING
    =============================
    Over time, the agent builds up knowledge.
    """
    print("\n" + "="*60)
    print("PHASE 4: PROGRESSIVE LEARNING")
    print("="*60)

    # Simulate learning from multiple sessions
    agent = AgentIntegration(agent.project_path)

    # Session 3: Bug fix
    session_id, _ = agent.start_session("Fix cache timeout bug")
    agent.learn_bug_pattern(
        name="timeout_not_propagated",
        signature="timeout param ignored in nested calls",
        fix_template="Pass timeout through all layers",
        modules=["cache", "api"]
    )
    agent.end_session(1.0, "success", ["Always check timeout propagation"])

    # Session 4: Feature
    agent = AgentIntegration(agent.project_path)
    session_id, _ = agent.start_session("Add cache metrics")
    agent.record_decision(
        "Use Prometheus for metrics",
        "Already using it for API metrics"
    )
    agent.end_session(1.0, "success")

    # Session 5: Code review feedback
    agent = AgentIntegration(agent.project_path)
    session_id, _ = agent.start_session("Address code review")
    agent.learn_from_feedback(
        feedback_type="convention_violated",
        context="Used print() instead of logger",
        correction="Always use logging.getLogger(__name__)"
    )
    agent.end_session(1.0, "success")

    # Show accumulated knowledge
    print("\n--- Accumulated Knowledge ---")
    stats = agent.memory.get_stats()
    print(f"Total nodes: {stats['total_nodes']}")
    print(f"Total edges: {stats['total_edges']}")
    print(f"\nBy store:")
    for store, store_stats in stats['stores'].items():
        total = sum(v for v in store_stats.values() if isinstance(v, int))
        if total > 0:
            print(f"  {store}: {total}")

    # Show skill progression
    print("\n" + agent.get_skill_summary())

    return agent


def phase5_using_memory(agent: AgentIntegration):
    """
    Phase 5: USING ACCUMULATED MEMORY
    ==================================
    How the agent uses its accumulated knowledge.
    """
    print("\n" + "="*60)
    print("PHASE 5: USING ACCUMULATED MEMORY")
    print("="*60)

    agent = AgentIntegration(agent.project_path)

    # When starting new work, get context
    _, context = agent.start_session("Refactor cache module")

    print("\n--- Full Context for New Task ---")
    print(context.to_prompt())

    # Check approach before implementing
    print("\n--- Checking Approaches ---")

    approaches = [
        "Use in-memory dict instead of Redis",
        "Add SQLite for persistence",
        "Use asyncio.Lock for thread safety"
    ]

    for approach in approaches:
        warnings = agent.check_before_coding(approach)
        if warnings:
            print(f"\n'{approach}':")
            for w in warnings:
                print(f"  ! {w.get('type', 'warning')}: {w}")
        else:
            print(f"\n'{approach}': OK")

    # Find expert for help
    expert = agent.memory.who_knows("caching")
    if expert:
        print(f"\n--- Expert Available ---")
        print(f"Contact: {expert}")

    agent.end_session(0.5, "partial")


def main():
    """Run the complete workflow example"""
    import tempfile
    import os

    # Create a temporary project directory
    with tempfile.TemporaryDirectory() as tmpdir:
        project_path = os.path.join(tmpdir, "example-project")
        os.makedirs(project_path)

        # Create some fake project structure
        os.makedirs(os.path.join(project_path, "src", "cache"))
        os.makedirs(os.path.join(project_path, "src", "api"))
        os.makedirs(os.path.join(project_path, "tests"))

        # Create a pyproject.toml
        with open(os.path.join(project_path, "pyproject.toml"), "w") as f:
            f.write("""
[project]
name = "example-project"
dependencies = ["redis", "pydantic", "fastapi"]

[tool.ruff]
line-length = 100

[tool.mypy]
strict = true
""")

        # Create a Python file
        with open(os.path.join(project_path, "src", "cache", "__init__.py"), "w") as f:
            f.write("""
from typing import Optional

def get_cached(key: str) -> Optional[str]:
    '''Get a cached value'''
    return None

def set_cached(key: str, value: str, ttl: int = 300) -> None:
    '''Set a cached value'''
    pass
""")

        # Run all phases
        agent = phase1_bootstrap(project_path)
        agent = phase2_session1(agent)
        agent = phase3_session2(agent)
        agent = phase4_progressive_learning(agent)
        phase5_using_memory(agent)

        print("\n" + "="*60)
        print("WORKFLOW COMPLETE")
        print("="*60)
        print(f"\nMemory file: {agent.memory_path}")
        print("This memory can be loaded in future sessions to continue learning!")


if __name__ == "__main__":
    main()
