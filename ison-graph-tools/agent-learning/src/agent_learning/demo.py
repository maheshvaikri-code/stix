"""
Agent Learning Demo
===================

Comprehensive demonstration of agent learning capabilities.
"""

from ison_graph import ISONGraph

from .engine import AgentLearningEngine
from .memory_integration import (
    LearningMemoryStore,
    CachedLearningContext,
    LearningSessionManager,
)
from .schema import (
    ExperienceOutcome,
    MistakeCategory,
    MistakeSeverity,
    AttentionType,
    SupervisionType,
    SupervisionOutcome,
    SkillLevel,
)


def run_demo(db_path: str = ":memory:"):
    """
    Run a comprehensive demonstration of the agent learning system.

    Args:
        db_path: Path to database (default: in-memory)
    """
    print("=" * 70)
    print("Agent Learning System - Comprehensive Demonstration")
    print("=" * 70)

    # Initialize
    graph = ISONGraph(db_path)
    engine = AgentLearningEngine(graph, "demo-learning-system")
    memory = LearningMemoryStore(graph)
    sessions = LearningSessionManager(memory)

    agent_id = "demo-agent-alpha"

    # =========================================================================
    # Part 1: Skill Registration
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 1: Skill Registration")
    print("-" * 50)

    skills = [
        ("Code Analysis", "programming", "Ability to analyze and understand code"),
        ("Error Handling", "programming", "Ability to handle and recover from errors"),
        ("User Communication", "communication", "Ability to communicate clearly with users"),
        ("Task Planning", "reasoning", "Ability to plan and execute complex tasks"),
        ("Safety Awareness", "safety", "Awareness of safety considerations"),
    ]

    skill_ids = {}
    for name, category, description in skills:
        skill_id = engine.register_skill(
            agent_id=agent_id,
            name=name,
            category=category,
            description=description,
            initial_level=SkillLevel.NOVICE,
        )
        skill_ids[name] = skill_id
        print(f"  Registered skill: {name} (ID: {skill_id})")

    # =========================================================================
    # Part 2: Experience Recording
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 2: Experience Recording")
    print("-" * 50)

    experiences = [
        {
            "task": "Debug a Python function with infinite loop",
            "task_type": "debugging",
            "outcome": ExperienceOutcome.SUCCESS,
            "reward": 0.9,
            "learnings": ["Check loop termination conditions", "Use print statements for tracing"],
        },
        {
            "task": "Explain API endpoints to user",
            "task_type": "explanation",
            "outcome": ExperienceOutcome.SUCCESS,
            "reward": 0.85,
            "learnings": ["Use concrete examples", "Check for user understanding"],
        },
        {
            "task": "Refactor large code file",
            "task_type": "refactoring",
            "outcome": ExperienceOutcome.PARTIAL_SUCCESS,
            "reward": 0.5,
            "learnings": ["Break into smaller steps", "Test after each change"],
            "challenges": ["File too large to process at once"],
        },
        {
            "task": "Handle user's sensitive data request",
            "task_type": "data_handling",
            "outcome": ExperienceOutcome.BLOCKED,
            "reward": -0.3,
            "learnings": ["Always check data sensitivity", "Follow privacy guidelines"],
            "challenges": ["Unclear privacy requirements"],
        },
        {
            "task": "Optimize database query",
            "task_type": "optimization",
            "outcome": ExperienceOutcome.SUCCESS,
            "reward": 0.95,
            "learnings": ["Profile before optimizing", "Use indexes effectively"],
        },
    ]

    for exp in experiences:
        exp_id = engine.record_experience(
            agent_id=agent_id,
            task=exp["task"],
            task_type=exp["task_type"],
            environment={"platform": "production", "version": "1.0"},
            initial_state={"complexity": "medium"},
            actions_taken=[{"action": "analyze"}, {"action": "implement"}],
            decisions_made=[{"decision": "approach", "confidence": 0.8}],
            outcome=exp["outcome"],
            outcome_details=f"Task: {exp['task']}",
            reward_signal=exp["reward"],
            key_learnings=exp.get("learnings", []),
            challenges_faced=exp.get("challenges", []),
            duration_seconds=300,
        )
        print(f"  Experience: {exp['task'][:40]}... ({exp['outcome'].value})")

    # =========================================================================
    # Part 3: Mistake Recording and Correction
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 3: Mistake Recording and Correction")
    print("-" * 50)

    mistakes = [
        {
            "category": MistakeCategory.JUDGMENT_ERROR,
            "severity": MistakeSeverity.HIGH,
            "context": "User asked to delete important files",
            "action": "Deleted without confirmation",
            "expected": "Ask for confirmation first",
            "root_cause": "Missing confirmation step",
        },
        {
            "category": MistakeCategory.HALLUCINATION,
            "severity": MistakeSeverity.CRITICAL,
            "context": "User asked about API documentation",
            "action": "Made up non-existent endpoint",
            "expected": "Check documentation first",
            "root_cause": "Overconfidence without verification",
        },
        {
            "category": MistakeCategory.PROCEDURAL_ERROR,
            "severity": MistakeSeverity.MEDIUM,
            "context": "Building a project",
            "action": "Skipped test step",
            "expected": "Run tests before completion",
            "root_cause": "Incomplete checklist following",
        },
        {
            "category": MistakeCategory.CONTEXT_MISUNDERSTANDING,
            "severity": MistakeSeverity.LOW,
            "context": "User asked for help with 'Python'",
            "action": "Assumed programming language",
            "expected": "Clarify if animal or language",
            "root_cause": "Assumed context without asking",
        },
    ]

    mistake_ids = []
    for m in mistakes:
        mistake_id = engine.record_mistake(
            agent_id=agent_id,
            category=m["category"],
            severity=m["severity"],
            task_context=m["context"],
            agent_action=m["action"],
            expected_action=m["expected"],
            actual_outcome="Incorrect result",
            expected_outcome="Correct result",
            root_cause=m["root_cause"],
            contributing_factors=["Insufficient attention", "Time pressure"],
        )
        mistake_ids.append(mistake_id)
        print(f"  Mistake: {m['category'].value} ({m['severity'].value})")

    # Apply corrections
    for i, mistake_id in enumerate(mistake_ids[:2]):
        engine.apply_correction(
            mistake_id=mistake_id,
            correction=f"Applied correction for mistake {i+1}",
            corrected_by="supervisor-1",
            lesson_learned=f"Lesson from mistake {i+1}",
            prevention_strategy=f"Prevention strategy {i+1}",
        )
        print(f"  Correction applied to: {mistake_id}")

    # =========================================================================
    # Part 4: Attention Tracking
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 4: Attention Tracking")
    print("-" * 50)

    attention_events = [
        (AttentionType.USER_INTENT, "user_request", 0.9, []),
        (AttentionType.TASK_FOCUS, "main_task", 0.7, ["edge_case"]),
        (AttentionType.SAFETY_CHECK, "sensitive_data", 0.6, ["privacy_flag"]),
        (AttentionType.ERROR_CHECKING, "output", 0.8, ["format_issue"]),
        (AttentionType.CONTEXT_GATHERING, "requirements", 0.5, ["implicit_requirement", "deadline"]),
    ]

    for atype, target, quality, missed in attention_events:
        engine.record_attention(
            agent_id=agent_id,
            attention_type=atype,
            focus_target=target,
            focus_context={"context": "demo"},
            attention_duration_ms=500,
            attention_quality=quality,
            missed_elements=missed,
        )
        if missed:
            print(f"  Attention: {atype.value} - quality {quality:.0%}, missed: {missed}")
        else:
            print(f"  Attention: {atype.value} - quality {quality:.0%}")

    # Record same missed element multiple times to trigger pattern
    for _ in range(3):
        engine.record_attention(
            agent_id=agent_id,
            attention_type=AttentionType.SAFETY_CHECK,
            focus_target="input_validation",
            focus_context={},
            attention_duration_ms=200,
            attention_quality=0.4,
            missed_elements=["input_sanitization"],
        )

    # =========================================================================
    # Part 5: Supervision
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 5: Supervision Recording")
    print("-" * 50)

    supervisions = [
        (SupervisionOutcome.APPROVED, "Good code review response"),
        (SupervisionOutcome.NEEDS_REVISION, "Missing error handling"),
        (SupervisionOutcome.APPROVED_WITH_CHANGES, "Good but needs formatting"),
        (SupervisionOutcome.REJECTED, "Incorrect approach"),
    ]

    for outcome, feedback in supervisions:
        sup_id = engine.record_supervision(
            agent_id=agent_id,
            supervisor_id="human-reviewer-1",
            supervisor_type="human",
            supervision_type=SupervisionType.HUMAN_REVIEW,
            supervised_action="Code generation",
            supervised_output="Generated code",
            context={"task": "programming"},
            outcome=outcome,
            feedback=feedback,
            learning_points=[f"Learning from: {feedback}"],
        )

        if outcome in [SupervisionOutcome.APPROVED, SupervisionOutcome.APPROVED_WITH_CHANGES]:
            engine.acknowledge_supervision(sup_id, agent_id, "Understood")

        print(f"  Supervision: {outcome.value} - {feedback[:40]}")

    # =========================================================================
    # Part 6: Skill Practice
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 6: Skill Practice")
    print("-" * 50)

    practices = [
        ("Code Analysis", True, 0.85),
        ("Code Analysis", True, 0.90),
        ("Error Handling", True, 0.75),
        ("Error Handling", False, 0.40),
        ("User Communication", True, 0.95),
        ("Task Planning", True, 0.80),
        ("Safety Awareness", False, 0.50),
    ]

    for skill_name, success, score in practices:
        result = engine.record_practice(
            skill_id=skill_ids[skill_name],
            success=success,
            performance_score=score,
            notes=f"Practice session for {skill_name}",
        )
        status = "PASS" if success else "FAIL"
        print(f"  {skill_name}: {status} ({score:.0%}) -> Level: {result.get('new_level')}")

    # =========================================================================
    # Part 7: Memory Integration
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 7: Memory Integration")
    print("-" * 50)

    # Store semantic knowledge
    semantic_id = memory.store_semantic(
        agent_id=agent_id,
        concept="confirmation_before_destructive",
        category="best_practices",
        content="Always ask for confirmation before destructive operations",
        confidence=0.95,
    )
    print(f"  Stored semantic memory: confirmation_before_destructive")

    # Store procedure
    procedure_id = memory.store_procedure(
        agent_id=agent_id,
        name="code_review",
        category="programming",
        steps=[
            {"step": 1, "action": "Read code thoroughly"},
            {"step": 2, "action": "Check for errors"},
            {"step": 3, "action": "Verify logic"},
            {"step": 4, "action": "Provide feedback"},
        ],
    )
    print(f"  Stored procedure: code_review")

    # Execute procedure
    memory.record_procedure_execution(procedure_id, success=True, execution_time_ms=5000)
    print(f"  Executed procedure: code_review")

    # Use cached context
    cached = CachedLearningContext(
        memory_store=memory,
        mistake_store=engine.mistake,
        attention_store=engine.attention,
        supervision_store=engine.supervision,
        skill_store=engine.skill,
    )

    context = cached.get_context(
        agent_id=agent_id,
        task_type="programming",
        token_budget=1500,
    )
    print(f"  Cached context: {context['items_included']} items ({context['tokens_used']} tokens)")

    # =========================================================================
    # Part 8: Session Management
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 8: Session Management")
    print("-" * 50)

    session_id = sessions.start_session(
        agent_id=agent_id,
        task="Complete complex refactoring",
        task_type="refactoring",
    )
    print(f"  Started session: {session_id}")

    sessions.add_event(session_id, "analysis", {"files_analyzed": 5})
    sessions.add_learning(session_id, "Breaking changes require migration guide", 0.85)
    sessions.add_mistake(session_id, "Forgot to update imports", "low")

    result = sessions.end_session(
        session_id=session_id,
        outcome="success",
        summary="Refactoring completed with minor issues",
        reward_signal=0.7,
    )
    print(f"  Ended session - Episode: {result['episode_id']}")
    print(f"    Learnings: {result['learnings_recorded']}, Mistakes: {result['mistakes_recorded']}")

    # =========================================================================
    # Part 9: Analysis
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 9: Analysis")
    print("-" * 50)

    # Learning trajectory
    trajectory = engine.get_learning_trajectory(agent_id, days=30)
    print(f"\n  Learning Trajectory:")
    print(f"    Total experiences: {trajectory.get('total_experiences', 0)}")
    print(f"    Success rate: {trajectory.get('success_rate', 0):.1%}")
    print(f"    Average reward: {trajectory.get('average_reward', 0):.2f}")

    # Mistake patterns
    patterns = engine.get_mistake_patterns(agent_id, min_frequency=1)
    print(f"\n  Mistake Patterns: {len(patterns)} detected")
    for p in patterns[:3]:
        print(f"    - {p.get('name', 'Unknown')}: {p.get('frequency', 0)} occurrences")

    # Attention recommendations
    attention_recs = engine.get_attention_recommendations(agent_id)
    print(f"\n  Attention Recommendations: {len(attention_recs)}")
    for rec in attention_recs[:3]:
        print(f"    - {rec.get('recommendation', 'N/A')[:60]}")

    # Skill summary
    skill_summary = engine.get_skill_summary(agent_id)
    print(f"\n  Skill Summary:")
    print(f"    Total skills: {skill_summary.get('total_skills', 0)}")
    print(f"    Average proficiency: {skill_summary.get('average_proficiency', 0):.1f}%")
    print(f"    Due for practice: {skill_summary.get('skills_due_for_practice', 0)}")

    # =========================================================================
    # Part 10: Retraining
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 10: Retraining Identification")
    print("-" * 50)

    needs = engine.identify_retraining_needs(agent_id, days=30)
    print(f"\n  Retraining Needs Identified: {needs.get('needs_identified', 0)}")

    for need in needs.get("needs", [])[:3]:
        print(f"    - {need.get('skill_area')}: {need.get('specific_issue')[:40]}...")
        print(f"      Priority: {need.get('priority')}, Type: {need.get('curriculum_type')}")

    if needs.get("needs"):
        print("\n  Generating curriculum for top need...")
        curriculum = engine.generate_curriculum(agent_id, needs["needs"][0]["need_id"])
        print(f"    Title: {curriculum.get('title')}")
        print(f"    Modules: {curriculum.get('modules')}")
        print(f"    Objectives: {len(curriculum.get('objectives', []))}")

    # =========================================================================
    # Part 11: Learning Profile
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 11: Agent Learning Profile")
    print("-" * 50)

    profile = engine.get_agent_learning_profile(agent_id)

    print(f"\n  Agent: {profile.get('agent_id')}")
    print(f"  Overall Health Score: {profile.get('overall_health_score', 0):.2f}")
    print(f"  Active Mistake Patterns: {profile.get('active_mistake_patterns', 0)}")
    print(f"  Attention Recommendations: {profile.get('attention_recommendations', 0)}")

    print(f"\n  Profile Recommendations:")
    for rec in profile.get("recommendations", [])[:5]:
        print(f"    [{rec.get('priority').upper()}] {rec.get('area')}: {rec.get('recommendation')}")

    # =========================================================================
    # Part 12: Statistics
    # =========================================================================
    print("\n" + "-" * 50)
    print("PART 12: Overall Statistics")
    print("-" * 50)

    stats = engine.get_stats()

    print(f"\n  Experience Store:")
    print(f"    Total experiences: {stats.get('experience', {}).get('total_experiences', 0)}")
    print(f"    Total patterns: {stats.get('experience', {}).get('total_patterns', 0)}")

    print(f"\n  Mistake Store:")
    print(f"    Total mistakes: {stats.get('mistake', {}).get('total_mistakes', 0)}")
    print(f"    Correction rate: {stats.get('mistake', {}).get('correction_rate', 0):.1%}")

    print(f"\n  Skill Store:")
    print(f"    Total skills: {stats.get('skill', {}).get('total_skills', 0)}")
    print(f"    Practice success rate: {stats.get('skill', {}).get('practice_success_rate', 0):.1%}")

    print(f"\n  Supervision Store:")
    print(f"    Total records: {stats.get('supervision', {}).get('total_supervision_records', 0)}")
    print(f"    Acknowledgment rate: {stats.get('supervision', {}).get('acknowledgment_rate', 0):.1%}")

    print("\n" + "=" * 70)
    print("Demonstration Complete!")
    print("=" * 70)

    return engine, profile


if __name__ == "__main__":
    run_demo()
