"""
Agent Learning
==============

A comprehensive agent learning and retraining system built on ISONGraph.

Features:
- Experience recording and replay learning
- Mistake tracking with pattern detection
- Attention monitoring and improvement
- Supervision integration
- Skill development with spaced repetition
- Automated retraining curriculum generation
- Memory integration following agent-memory patterns
- Token-budgeted context following ISONCache patterns

Quick Start:
    from ison_graph import ISONGraph
    from agent_learning import AgentLearningEngine

    # Initialize
    graph = ISONGraph("my-learning-db")
    engine = AgentLearningEngine(graph)

    # Record an experience
    exp_id = engine.record_experience(
        agent_id="agent-1",
        task="Complete user request",
        task_type="task_completion",
        environment={"platform": "production"},
        initial_state={"context_length": 1000},
        actions_taken=[{"action": "analyze", "result": "success"}],
        decisions_made=[{"decision": "use_tool", "confidence": 0.9}],
        outcome=ExperienceOutcome.SUCCESS,
        outcome_details="Task completed successfully",
        reward_signal=0.8,
        key_learnings=["Tool selection improved outcome"],
    )

    # Record a mistake
    mistake_id = engine.record_mistake(
        agent_id="agent-1",
        category=MistakeCategory.JUDGMENT_ERROR,
        severity=MistakeSeverity.MEDIUM,
        task_context="User asked for file edit",
        agent_action="Edited wrong file",
        expected_action="Edit specified file",
        actual_outcome="Wrong file modified",
        expected_outcome="Correct file modified",
        root_cause="Misread file path",
    )

    # Identify retraining needs
    needs = engine.identify_retraining_needs("agent-1")

    # Generate curriculum
    curriculum = engine.generate_curriculum("agent-1", needs["needs"][0]["need_id"])
"""

from .schema import (
    # Event types
    LearningEventType,
    MistakeCategory,
    MistakeSeverity,
    ExperienceOutcome,
    AttentionType,
    SupervisionType,
    SupervisionOutcome,
    SkillLevel,
    RetrainingPriority,
    CurriculumType,
    # Data classes
    LearningEvent,
    Mistake,
    Experience,
    AttentionRecord,
    SupervisionRecord,
    Skill,
    RetrainingNeed,
    RetrainingCurriculum,
    MistakePattern,
    LearningProgress,
    # Constants
    LEARNING_EDGE_TYPES,
    FORGETTING_CURVE,
    SPACED_REPETITION_INTERVALS,
    SKILL_LEVEL_THRESHOLDS,
    MISTAKE_SEVERITY_WEIGHTS,
)

from .stores import (
    BaseLearningStore,
    ExperienceStore,
    MistakeStore,
    AttentionStore,
    SupervisionStore,
    SkillStore,
)

from .retraining import (
    RetrainingNeedStore,
    CurriculumStore,
    RetrainingEngine,
)

from .memory_integration import (
    LearningMemoryStore,
    CachedLearningContext,
    LearningSessionManager,
)

from .engine import AgentLearningEngine

__version__ = "0.1.0"

__all__ = [
    # Main engine
    "AgentLearningEngine",
    # Enums
    "LearningEventType",
    "MistakeCategory",
    "MistakeSeverity",
    "ExperienceOutcome",
    "AttentionType",
    "SupervisionType",
    "SupervisionOutcome",
    "SkillLevel",
    "RetrainingPriority",
    "CurriculumType",
    # Data classes
    "LearningEvent",
    "Mistake",
    "Experience",
    "AttentionRecord",
    "SupervisionRecord",
    "Skill",
    "RetrainingNeed",
    "RetrainingCurriculum",
    "MistakePattern",
    "LearningProgress",
    # Stores
    "BaseLearningStore",
    "ExperienceStore",
    "MistakeStore",
    "AttentionStore",
    "SupervisionStore",
    "SkillStore",
    "RetrainingNeedStore",
    "CurriculumStore",
    # Engines
    "RetrainingEngine",
    # Memory integration
    "LearningMemoryStore",
    "CachedLearningContext",
    "LearningSessionManager",
    # Constants
    "LEARNING_EDGE_TYPES",
    "FORGETTING_CURVE",
    "SPACED_REPETITION_INTERVALS",
    "SKILL_LEVEL_THRESHOLDS",
    "MISTAKE_SEVERITY_WEIGHTS",
]
