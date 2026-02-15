"""
Agent Learning CLI
==================

Command-line interface for agent learning management.
"""

import argparse
import json
import sys
from pathlib import Path

from ison_graph import ISONGraph

from .engine import AgentLearningEngine
from .schema import (
    ExperienceOutcome,
    MistakeCategory,
    MistakeSeverity,
    AttentionType,
    SupervisionType,
    SupervisionOutcome,
    SkillLevel,
)


def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Agent Learning CLI - Manage agent learning and retraining",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Show statistics
  agent-learning stats --db ./learning.db

  # Get agent learning profile
  agent-learning profile --db ./learning.db --agent agent-1

  # Identify retraining needs
  agent-learning needs --db ./learning.db --agent agent-1

  # Get experiences for replay
  agent-learning replay --db ./learning.db --agent agent-1 --limit 5

  # Get mistake patterns
  agent-learning patterns --db ./learning.db --agent agent-1
        """,
    )

    parser.add_argument(
        "--db",
        default="./agent_learning.db",
        help="Path to ISONGraph database",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show learning statistics")

    # Profile command
    profile_parser = subparsers.add_parser("profile", help="Get agent learning profile")
    profile_parser.add_argument("--agent", required=True, help="Agent ID")

    # Needs command
    needs_parser = subparsers.add_parser("needs", help="Identify retraining needs")
    needs_parser.add_argument("--agent", required=True, help="Agent ID")
    needs_parser.add_argument("--days", type=int, default=30, help="Analysis period in days")

    # Replay command
    replay_parser = subparsers.add_parser("replay", help="Get experiences for replay")
    replay_parser.add_argument("--agent", required=True, help="Agent ID")
    replay_parser.add_argument("--limit", type=int, default=10, help="Maximum experiences")
    replay_parser.add_argument("--prioritize-failures", action="store_true", default=True)

    # Patterns command
    patterns_parser = subparsers.add_parser("patterns", help="Get mistake patterns")
    patterns_parser.add_argument("--agent", required=True, help="Agent ID")
    patterns_parser.add_argument("--min-frequency", type=int, default=2, help="Minimum frequency")

    # Skills command
    skills_parser = subparsers.add_parser("skills", help="Get skill summary")
    skills_parser.add_argument("--agent", required=True, help="Agent ID")

    # Trajectory command
    trajectory_parser = subparsers.add_parser("trajectory", help="Get learning trajectory")
    trajectory_parser.add_argument("--agent", required=True, help="Agent ID")
    trajectory_parser.add_argument("--days", type=int, default=30, help="Analysis period in days")
    trajectory_parser.add_argument("--task-type", help="Filter by task type")

    # Supervision command
    supervision_parser = subparsers.add_parser("supervision", help="Get supervision summary")
    supervision_parser.add_argument("--agent", required=True, help="Agent ID")
    supervision_parser.add_argument("--days", type=int, default=30, help="Analysis period in days")

    # Attention command
    attention_parser = subparsers.add_parser("attention", help="Get attention recommendations")
    attention_parser.add_argument("--agent", required=True, help="Agent ID")

    # Curriculum command
    curriculum_parser = subparsers.add_parser("curriculum", help="Generate curriculum for a need")
    curriculum_parser.add_argument("--agent", required=True, help="Agent ID")
    curriculum_parser.add_argument("--need-id", required=True, help="Retraining need ID")

    # Progress command
    progress_parser = subparsers.add_parser("progress", help="Get retraining progress")
    progress_parser.add_argument("--agent", required=True, help="Agent ID")

    # Decay command
    decay_parser = subparsers.add_parser("decay", help="Apply skill decay")
    decay_parser.add_argument("--agent", required=True, help="Agent ID")

    # Demo command
    demo_parser = subparsers.add_parser("demo", help="Run demonstration")

    return parser


def output_result(result, as_json=False):
    """Output result in appropriate format."""
    if as_json:
        print(json.dumps(result, indent=2, default=str))
    else:
        if isinstance(result, dict):
            for key, value in result.items():
                if isinstance(value, (dict, list)):
                    print(f"{key}:")
                    print(f"  {json.dumps(value, indent=4, default=str)}")
                else:
                    print(f"{key}: {value}")
        else:
            print(result)


def run_demo(engine: AgentLearningEngine):
    """Run demonstration of agent learning features."""
    print("=" * 60)
    print("Agent Learning Demonstration")
    print("=" * 60)

    agent_id = "demo-agent-1"

    # Record some experiences
    print("\n1. Recording experiences...")

    exp1 = engine.record_experience(
        agent_id=agent_id,
        task="Process user file upload request",
        task_type="file_processing",
        environment={"platform": "production", "version": "1.0"},
        initial_state={"files_pending": 1},
        actions_taken=[
            {"action": "validate_file", "result": "valid"},
            {"action": "process_file", "result": "success"},
        ],
        decisions_made=[
            {"decision": "use_async_processing", "confidence": 0.8},
        ],
        outcome=ExperienceOutcome.SUCCESS,
        outcome_details="File processed successfully",
        reward_signal=0.9,
        key_learnings=["Async processing improves throughput"],
        duration_seconds=120,
    )
    print(f"  Recorded experience: {exp1}")

    exp2 = engine.record_experience(
        agent_id=agent_id,
        task="Handle error recovery",
        task_type="error_handling",
        environment={"platform": "production"},
        initial_state={"error_type": "timeout"},
        actions_taken=[
            {"action": "retry", "result": "failed"},
            {"action": "escalate", "result": "success"},
        ],
        decisions_made=[
            {"decision": "max_retries_3", "confidence": 0.6},
        ],
        outcome=ExperienceOutcome.CORRECTED,
        outcome_details="Error resolved after escalation",
        reward_signal=0.3,
        key_learnings=["Escalation sometimes better than retrying"],
        challenges_faced=["Timeout persisted across retries"],
        duration_seconds=300,
    )
    print(f"  Recorded experience: {exp2}")

    # Record some mistakes
    print("\n2. Recording mistakes...")

    mistake1 = engine.record_mistake(
        agent_id=agent_id,
        category=MistakeCategory.JUDGMENT_ERROR,
        severity=MistakeSeverity.MEDIUM,
        task_context="User asked to delete a file",
        agent_action="Deleted file without confirmation",
        expected_action="Ask for confirmation before deleting",
        actual_outcome="File deleted without user consent",
        expected_outcome="User confirms deletion first",
        root_cause="Missing confirmation step in workflow",
        contributing_factors=["Rushed execution", "No safeguard check"],
    )
    print(f"  Recorded mistake: {mistake1}")

    # Apply correction
    engine.apply_correction(
        mistake_id=mistake1,
        correction="Added confirmation step",
        corrected_by="supervisor-1",
        lesson_learned="Always confirm destructive operations",
        prevention_strategy="Add confirmation for all delete/modify operations",
    )
    print(f"  Applied correction to mistake: {mistake1}")

    # Record attention
    print("\n3. Recording attention events...")

    attention1 = engine.record_attention(
        agent_id=agent_id,
        attention_type=AttentionType.USER_INTENT,
        focus_target="user_request",
        focus_context={"request_type": "file_operation"},
        attention_duration_ms=500,
        attention_quality=0.7,
        missed_elements=["confirmation_requirement"],
        influenced_decision=True,
    )
    print(f"  Recorded attention: {attention1}")

    # Record supervision
    print("\n4. Recording supervision...")

    supervision1 = engine.record_supervision(
        agent_id=agent_id,
        supervisor_id="human-supervisor-1",
        supervisor_type="human",
        supervision_type=SupervisionType.HUMAN_REVIEW,
        supervised_action="File deletion",
        supervised_output="File deleted",
        context={"file": "important.txt"},
        outcome=SupervisionOutcome.NEEDS_REVISION,
        feedback="Must include confirmation step",
        required_changes=["Add confirmation dialog"],
        learning_points=["Destructive operations require confirmation"],
    )
    print(f"  Recorded supervision: {supervision1}")

    # Acknowledge supervision
    engine.acknowledge_supervision(
        supervision_id=supervision1,
        agent_id=agent_id,
        acknowledgment_notes="Understood, will add confirmation step",
    )
    print(f"  Acknowledged supervision: {supervision1}")

    # Register and practice skills
    print("\n5. Managing skills...")

    skill1 = engine.register_skill(
        agent_id=agent_id,
        name="Error Handling",
        category="resilience",
        description="Ability to handle and recover from errors",
        initial_level=SkillLevel.BEGINNER,
    )
    print(f"  Registered skill: {skill1}")

    # Practice the skill
    practice_result = engine.record_practice(
        skill_id=skill1,
        success=True,
        performance_score=0.75,
        context={"task": "timeout_recovery"},
        notes="Successfully recovered from timeout",
    )
    print(f"  Practiced skill, new proficiency: {practice_result.get('new_proficiency', 0):.1f}")

    # Get learning profile
    print("\n6. Getting learning profile...")
    profile = engine.get_agent_learning_profile(agent_id)
    print(f"  Overall health score: {profile.get('overall_health_score', 0):.2f}")
    print(f"  Active mistake patterns: {profile.get('active_mistake_patterns', 0)}")
    print(f"  Recommendations: {len(profile.get('recommendations', []))}")

    # Identify retraining needs
    print("\n7. Identifying retraining needs...")
    needs = engine.identify_retraining_needs(agent_id, days=30)
    print(f"  Needs identified: {needs.get('needs_identified', 0)}")

    if needs.get("needs"):
        need = needs["needs"][0]
        print(f"  Top need: {need.get('skill_area')} - {need.get('priority')}")

        # Generate curriculum
        print("\n8. Generating curriculum...")
        curriculum = engine.generate_curriculum(agent_id, need.get("need_id"))
        print(f"  Curriculum: {curriculum.get('title')}")
        print(f"  Modules: {curriculum.get('modules')}")

    # Get statistics
    print("\n9. Overall statistics:")
    stats = engine.get_stats()
    print(f"  Total experiences: {stats.get('experience', {}).get('total_experiences', 0)}")
    print(f"  Total mistakes: {stats.get('mistake', {}).get('total_mistakes', 0)}")
    print(f"  Total skills: {stats.get('skill', {}).get('total_skills', 0)}")

    print("\n" + "=" * 60)
    print("Demonstration complete!")
    print("=" * 60)


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Initialize engine
    graph = ISONGraph(args.db)
    engine = AgentLearningEngine(graph)

    try:
        if args.command == "stats":
            result = engine.get_stats()

        elif args.command == "profile":
            result = engine.get_agent_learning_profile(args.agent)

        elif args.command == "needs":
            result = engine.identify_retraining_needs(args.agent, args.days)

        elif args.command == "replay":
            result = engine.get_experiences_for_replay(
                args.agent,
                limit=args.limit,
                prioritize_failures=args.prioritize_failures,
            )

        elif args.command == "patterns":
            result = engine.get_mistake_patterns(args.agent, args.min_frequency)

        elif args.command == "skills":
            result = engine.get_skill_summary(args.agent)

        elif args.command == "trajectory":
            result = engine.get_learning_trajectory(args.agent, args.task_type, args.days)

        elif args.command == "supervision":
            result = engine.get_supervision_summary(args.agent, args.days)

        elif args.command == "attention":
            result = engine.get_attention_recommendations(args.agent)

        elif args.command == "curriculum":
            result = engine.generate_curriculum(args.agent, args.need_id)

        elif args.command == "progress":
            result = engine.get_retraining_progress(args.agent)

        elif args.command == "decay":
            result = engine.apply_skill_decay(args.agent)

        elif args.command == "demo":
            run_demo(engine)
            return

        else:
            parser.print_help()
            return

        output_result(result, args.json)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
