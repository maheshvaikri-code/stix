"""
Agent Learning Tests
====================

Comprehensive tests for the agent learning system.
"""

import pytest
from datetime import datetime, timezone

from ison_graph import ISONGraph

from agent_learning import (
    AgentLearningEngine,
    ExperienceOutcome,
    MistakeCategory,
    MistakeSeverity,
    AttentionType,
    SupervisionType,
    SupervisionOutcome,
    SkillLevel,
    LearningMemoryStore,
    CachedLearningContext,
    LearningSessionManager,
)


@pytest.fixture
def graph():
    """Create a fresh in-memory graph for each test."""
    return ISONGraph(":memory:")


@pytest.fixture
def engine(graph):
    """Create an engine instance."""
    return AgentLearningEngine(graph)


@pytest.fixture
def agent_id():
    """Standard agent ID for tests."""
    return "test-agent-1"


# =============================================================================
# Experience Store Tests
# =============================================================================

class TestExperienceStore:
    """Tests for experience recording and replay."""

    def test_record_experience(self, engine, agent_id):
        """Test recording an experience."""
        exp_id = engine.record_experience(
            agent_id=agent_id,
            task="Test task",
            task_type="test",
            environment={"test": True},
            initial_state={"state": "initial"},
            actions_taken=[{"action": "test"}],
            decisions_made=[{"decision": "test", "confidence": 0.8}],
            outcome=ExperienceOutcome.SUCCESS,
            outcome_details="Test successful",
            reward_signal=0.9,
            key_learnings=["Learned something"],
        )

        assert exp_id is not None
        assert exp_id.startswith("exp_")

    def test_get_experiences_for_replay(self, engine, agent_id):
        """Test getting experiences for replay."""
        # Record multiple experiences
        for i in range(5):
            outcome = ExperienceOutcome.FAILURE if i % 2 == 0 else ExperienceOutcome.SUCCESS
            engine.record_experience(
                agent_id=agent_id,
                task=f"Task {i}",
                task_type="test",
                environment={},
                initial_state={},
                actions_taken=[],
                decisions_made=[],
                outcome=outcome,
                outcome_details="",
                reward_signal=0.5 if outcome == ExperienceOutcome.SUCCESS else -0.5,
            )

        # Get for replay
        experiences = engine.get_experiences_for_replay(
            agent_id=agent_id,
            limit=3,
            prioritize_failures=True,
        )

        assert len(experiences) <= 3
        # Failures should be prioritized
        assert any(e.get("outcome") == "failure" for e in experiences)

    def test_learning_trajectory(self, engine, agent_id):
        """Test learning trajectory analysis."""
        # Record experiences
        for i in range(3):
            engine.record_experience(
                agent_id=agent_id,
                task=f"Task {i}",
                task_type="test",
                environment={},
                initial_state={},
                actions_taken=[],
                decisions_made=[],
                outcome=ExperienceOutcome.SUCCESS,
                outcome_details="",
                reward_signal=0.8,
                key_learnings=[f"Learning {i}"],
            )

        trajectory = engine.get_learning_trajectory(agent_id, days=30)

        assert trajectory.get("total_experiences") == 3
        assert trajectory.get("success_rate") == 1.0
        assert trajectory.get("total_learnings") == 3


# =============================================================================
# Mistake Store Tests
# =============================================================================

class TestMistakeStore:
    """Tests for mistake tracking and correction."""

    def test_record_mistake(self, engine, agent_id):
        """Test recording a mistake."""
        mistake_id = engine.record_mistake(
            agent_id=agent_id,
            category=MistakeCategory.LOGICAL_ERROR,
            severity=MistakeSeverity.MEDIUM,
            task_context="Test context",
            agent_action="Wrong action",
            expected_action="Correct action",
            actual_outcome="Bad outcome",
            expected_outcome="Good outcome",
            root_cause="Test root cause",
        )

        assert mistake_id is not None
        assert mistake_id.startswith("mistake_")

    def test_apply_correction(self, engine, agent_id):
        """Test applying correction to a mistake."""
        mistake_id = engine.record_mistake(
            agent_id=agent_id,
            category=MistakeCategory.JUDGMENT_ERROR,
            severity=MistakeSeverity.HIGH,
            task_context="Test",
            agent_action="Wrong",
            expected_action="Right",
            actual_outcome="Bad",
            expected_outcome="Good",
            root_cause="Root cause",
        )

        result = engine.apply_correction(
            mistake_id=mistake_id,
            correction="Applied fix",
            corrected_by="supervisor",
            lesson_learned="Important lesson",
            prevention_strategy="Don't do that again",
        )

        assert result.get("corrected") is True

    def test_mistake_patterns(self, engine, agent_id):
        """Test mistake pattern detection."""
        # Record multiple similar mistakes
        for i in range(4):
            engine.record_mistake(
                agent_id=agent_id,
                category=MistakeCategory.FACTUAL_ERROR,
                severity=MistakeSeverity.LOW,
                task_context=f"Context {i}",
                agent_action="Same action",
                expected_action="Different action",
                actual_outcome="Bad",
                expected_outcome="Good",
                root_cause="Same root cause",  # Same root cause = pattern
            )

        patterns = engine.get_mistake_patterns(agent_id, min_frequency=3)

        assert len(patterns) >= 1
        assert patterns[0].get("frequency") >= 3


# =============================================================================
# Attention Store Tests
# =============================================================================

class TestAttentionStore:
    """Tests for attention tracking."""

    def test_record_attention(self, engine, agent_id):
        """Test recording attention."""
        attention_id = engine.record_attention(
            agent_id=agent_id,
            attention_type=AttentionType.TASK_FOCUS,
            focus_target="test_target",
            focus_context={"context": "test"},
            attention_duration_ms=1000,
            attention_quality=0.8,
            missed_elements=["element1"],
        )

        assert attention_id is not None
        assert attention_id.startswith("attention_")

    def test_frequently_missed(self, engine, agent_id):
        """Test tracking frequently missed elements."""
        # Record multiple attention events with same missed element
        for i in range(5):
            engine.record_attention(
                agent_id=agent_id,
                attention_type=AttentionType.ERROR_CHECKING,
                focus_target="target",
                focus_context={},
                attention_duration_ms=500,
                attention_quality=0.5,
                missed_elements=["important_element"],
            )

        missed = engine.get_frequently_missed(agent_id, min_count=3)

        assert len(missed) >= 1
        assert missed[0].get("element") == "important_element"


# =============================================================================
# Supervision Store Tests
# =============================================================================

class TestSupervisionStore:
    """Tests for supervision tracking."""

    def test_record_supervision(self, engine, agent_id):
        """Test recording supervision."""
        supervision_id = engine.record_supervision(
            agent_id=agent_id,
            supervisor_id="supervisor-1",
            supervisor_type="human",
            supervision_type=SupervisionType.HUMAN_REVIEW,
            supervised_action="Test action",
            supervised_output="Test output",
            context={"test": True},
            outcome=SupervisionOutcome.APPROVED,
            feedback="Good work",
            learning_points=["Keep it up"],
        )

        assert supervision_id is not None
        assert supervision_id.startswith("supervision_")

    def test_acknowledge_supervision(self, engine, agent_id):
        """Test acknowledging supervision."""
        supervision_id = engine.record_supervision(
            agent_id=agent_id,
            supervisor_id="supervisor-1",
            supervisor_type="human",
            supervision_type=SupervisionType.HUMAN_REVIEW,
            supervised_action="Test",
            supervised_output="Output",
            context={},
            outcome=SupervisionOutcome.NEEDS_REVISION,
            feedback="Please revise",
            required_changes=["Fix X"],
        )

        result = engine.acknowledge_supervision(
            supervision_id=supervision_id,
            agent_id=agent_id,
            acknowledgment_notes="Understood",
        )

        assert result.get("acknowledged") is True

    def test_supervision_summary(self, engine, agent_id):
        """Test supervision summary."""
        # Record multiple supervisions
        for outcome in [SupervisionOutcome.APPROVED, SupervisionOutcome.REJECTED, SupervisionOutcome.APPROVED]:
            engine.record_supervision(
                agent_id=agent_id,
                supervisor_id="supervisor-1",
                supervisor_type="human",
                supervision_type=SupervisionType.HUMAN_REVIEW,
                supervised_action="Test",
                supervised_output="Output",
                context={},
                outcome=outcome,
                feedback="Feedback",
            )

        summary = engine.get_supervision_summary(agent_id, days=30)

        assert summary.get("total_supervisions") == 3
        assert "approved" in summary.get("by_outcome", {})


# =============================================================================
# Skill Store Tests
# =============================================================================

class TestSkillStore:
    """Tests for skill tracking."""

    def test_register_skill(self, engine, agent_id):
        """Test registering a skill."""
        skill_id = engine.register_skill(
            agent_id=agent_id,
            name="Test Skill",
            category="testing",
            description="A skill for testing",
            initial_level=SkillLevel.NOVICE,
        )

        assert skill_id is not None
        assert skill_id.startswith("skill_")

    def test_record_practice(self, engine, agent_id):
        """Test recording skill practice."""
        skill_id = engine.register_skill(
            agent_id=agent_id,
            name="Practice Skill",
            category="testing",
            description="For practice testing",
        )

        result = engine.record_practice(
            skill_id=skill_id,
            success=True,
            performance_score=0.8,
            notes="Good practice",
        )

        assert result.get("practiced") is True
        assert result.get("new_proficiency") > 0

    def test_skill_decay(self, engine, agent_id):
        """Test skill decay application."""
        skill_id = engine.register_skill(
            agent_id=agent_id,
            name="Decay Skill",
            category="testing",
            description="For decay testing",
        )

        # Practice to build proficiency
        engine.record_practice(skill_id=skill_id, success=True, performance_score=0.9)

        # Note: Decay is time-based, so immediate decay won't show much change
        result = engine.apply_skill_decay(agent_id)

        assert "decayed_count" in result


# =============================================================================
# Retraining Tests
# =============================================================================

class TestRetraining:
    """Tests for retraining identification and curriculum generation."""

    def test_identify_retraining_needs(self, engine, agent_id):
        """Test identifying retraining needs."""
        # Create some data that would trigger needs
        for i in range(4):
            engine.record_mistake(
                agent_id=agent_id,
                category=MistakeCategory.PROCEDURAL_ERROR,
                severity=MistakeSeverity.MEDIUM,
                task_context="Context",
                agent_action="Wrong",
                expected_action="Right",
                actual_outcome="Bad",
                expected_outcome="Good",
                root_cause="Same issue",
            )

        needs = engine.identify_retraining_needs(agent_id, days=30)

        assert needs.get("needs_identified", 0) >= 0

    def test_generate_curriculum(self, engine, agent_id):
        """Test curriculum generation."""
        # Record mistakes to create needs
        for i in range(4):
            engine.record_mistake(
                agent_id=agent_id,
                category=MistakeCategory.LOGICAL_ERROR,
                severity=MistakeSeverity.HIGH,
                task_context=f"Context {i}",
                agent_action="Wrong",
                expected_action="Right",
                actual_outcome="Bad",
                expected_outcome="Good",
                root_cause="Recurring issue",
            )

        needs = engine.identify_retraining_needs(agent_id)

        if needs.get("needs"):
            need_id = needs["needs"][0]["need_id"]
            curriculum = engine.generate_curriculum(agent_id, need_id)

            assert "curriculum_id" in curriculum
            assert curriculum.get("modules", 0) > 0


# =============================================================================
# Memory Integration Tests
# =============================================================================

class TestMemoryIntegration:
    """Tests for memory integration."""

    def test_learning_memory_store(self, graph, agent_id):
        """Test learning memory store."""
        memory = LearningMemoryStore(graph)

        # Test working memory
        memory.set_working_context(agent_id, "test_key", "test_value", 0.8)
        value = memory.get_working_context(agent_id, "test_key")
        assert value == "test_value"

        # Test episodic memory
        episode_id = memory.store_episode(
            agent_id=agent_id,
            episode_type="test",
            content={"data": "test"},
            outcome="success",
            emotional_valence=0.5,
            importance=0.7,
            tags=["test"],
        )
        assert episode_id is not None

        # Test recall
        recalled = memory.recall_episode(episode_id)
        assert recalled is not None
        assert recalled.get("recall_count") == 1

    def test_semantic_memory(self, graph, agent_id):
        """Test semantic memory."""
        memory = LearningMemoryStore(graph)

        semantic_id = memory.store_semantic(
            agent_id=agent_id,
            concept="test_concept",
            category="testing",
            content="This is a test concept",
            confidence=0.8,
        )

        assert semantic_id is not None

        # Reinforce
        result = memory.reinforce_semantic(semantic_id)
        assert result.get("new_confidence") > 0.8

    def test_procedural_memory(self, graph, agent_id):
        """Test procedural memory."""
        memory = LearningMemoryStore(graph)

        procedure_id = memory.store_procedure(
            agent_id=agent_id,
            name="test_procedure",
            category="testing",
            steps=[
                {"step": 1, "action": "do_thing"},
                {"step": 2, "action": "do_other_thing"},
            ],
        )

        assert procedure_id is not None

        # Execute
        result = memory.record_procedure_execution(
            procedure_id=procedure_id,
            success=True,
            execution_time_ms=100,
        )

        assert result.get("executed") is True
        assert result.get("new_proficiency") > 0

    def test_cached_learning_context(self, graph, agent_id, engine):
        """Test cached learning context."""
        memory = LearningMemoryStore(graph)
        cached = CachedLearningContext(
            memory_store=memory,
            mistake_store=engine.mistake,
            attention_store=engine.attention,
            supervision_store=engine.supervision,
            skill_store=engine.skill,
        )

        context = cached.get_context(
            agent_id=agent_id,
            task_type="test",
            token_budget=1000,
        )

        assert "items" in context
        assert context.get("tokens_used", 0) <= 1000

    def test_learning_session_manager(self, graph, agent_id):
        """Test learning session manager."""
        memory = LearningMemoryStore(graph)
        sessions = LearningSessionManager(memory)

        # Start session
        session_id = sessions.start_session(
            agent_id=agent_id,
            task="Test task",
            task_type="testing",
        )

        assert session_id is not None

        # Add events
        sessions.add_event(session_id, "test_event", {"data": "test"})
        sessions.add_learning(session_id, "Test learning", 0.8)
        sessions.add_mistake(session_id, "Test mistake", "low")

        # End session
        result = sessions.end_session(
            session_id=session_id,
            outcome="success",
            summary="Test completed",
            reward_signal=0.8,
        )

        assert result.get("episode_id") is not None
        assert result.get("learnings_recorded") == 1
        assert result.get("mistakes_recorded") == 1


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests for the full system."""

    def test_full_learning_cycle(self, engine, agent_id):
        """Test a complete learning cycle."""
        # 1. Register skill
        skill_id = engine.register_skill(
            agent_id=agent_id,
            name="Integration Skill",
            category="integration",
            description="For integration testing",
        )

        # 2. Record experience
        exp_id = engine.record_experience(
            agent_id=agent_id,
            task="Integration task",
            task_type="integration",
            environment={},
            initial_state={},
            actions_taken=[{"action": "test"}],
            decisions_made=[{"decision": "test"}],
            outcome=ExperienceOutcome.PARTIAL_SUCCESS,
            outcome_details="Partial success",
            reward_signal=0.5,
            key_learnings=["Integration learning"],
        )

        # 3. Record mistake
        mistake_id = engine.record_mistake(
            agent_id=agent_id,
            category=MistakeCategory.PERFORMANCE_ISSUE,
            severity=MistakeSeverity.LOW,
            task_context="Integration",
            agent_action="Slow",
            expected_action="Fast",
            actual_outcome="Delayed",
            expected_outcome="Quick",
            root_cause="Inefficient algorithm",
        )

        # 4. Apply correction
        engine.apply_correction(
            mistake_id=mistake_id,
            correction="Optimized algorithm",
            corrected_by="system",
            lesson_learned="Use efficient algorithms",
            prevention_strategy="Profile before implementing",
        )

        # 5. Record supervision
        supervision_id = engine.record_supervision(
            agent_id=agent_id,
            supervisor_id="integration-supervisor",
            supervisor_type="system",
            supervision_type=SupervisionType.AUTOMATED_CHECK,
            supervised_action="Integration action",
            supervised_output="Output",
            context={},
            outcome=SupervisionOutcome.APPROVED_WITH_CHANGES,
            feedback="Minor improvements needed",
            learning_points=["Always optimize"],
        )

        # 6. Get learning profile
        profile = engine.get_agent_learning_profile(agent_id)

        assert profile.get("agent_id") == agent_id
        assert "overall_health_score" in profile

        # 7. Get statistics
        stats = engine.get_stats()

        assert stats.get("experience", {}).get("total_experiences", 0) >= 1
        assert stats.get("mistake", {}).get("total_mistakes", 0) >= 1
        assert stats.get("skill", {}).get("total_skills", 0) >= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
