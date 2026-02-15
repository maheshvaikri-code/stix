"""
Agent Learning Engine
=====================

Main engine that coordinates all learning stores and retraining.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from ison_graph import ISONGraph

from .stores.experience import ExperienceStore
from .stores.mistake import MistakeStore
from .stores.attention import AttentionStore
from .stores.supervision import SupervisionStore
from .stores.skill import SkillStore
from .retraining import RetrainingEngine
from .schema import (
    ExperienceOutcome,
    MistakeCategory,
    MistakeSeverity,
    AttentionType,
    SupervisionType,
    SupervisionOutcome,
    SkillLevel,
)


class AgentLearningEngine:
    """
    Main engine for agent learning and retraining.

    Coordinates:
    - Experience recording and replay
    - Mistake tracking and correction
    - Attention monitoring
    - Supervision integration
    - Skill development
    - Retraining curriculum generation

    Usage:
        graph = ISONGraph("learning-db")
        engine = AgentLearningEngine(graph, "my-learning-system")

        # Record experience
        exp_id = engine.record_experience(
            agent_id="agent-1",
            task="Complete user request",
            ...
        )

        # Record mistake
        mistake_id = engine.record_mistake(
            agent_id="agent-1",
            category=MistakeCategory.LOGICAL_ERROR,
            ...
        )

        # Identify retraining needs
        needs = engine.identify_retraining_needs("agent-1")
    """

    def __init__(self, graph: ISONGraph, name: str = "agent-learning"):
        """Initialize the agent learning engine.

        Args:
            graph: ISONGraph instance for storage
            name: Name for this learning system
        """
        self.graph = graph
        self.name = name

        # Initialize stores
        self.experience = ExperienceStore(graph)
        self.mistake = MistakeStore(graph)
        self.attention = AttentionStore(graph)
        self.supervision = SupervisionStore(graph)
        self.skill = SkillStore(graph)

        # Initialize retraining engine
        self.retraining = RetrainingEngine(
            graph=graph,
            experience_store=self.experience,
            mistake_store=self.mistake,
            attention_store=self.attention,
            supervision_store=self.supervision,
            skill_store=self.skill,
        )

    # =========================================================================
    # Experience API
    # =========================================================================

    def record_experience(
        self,
        agent_id: str,
        task: str,
        task_type: str,
        environment: Dict[str, Any],
        initial_state: Dict[str, Any],
        actions_taken: List[Dict[str, Any]],
        decisions_made: List[Dict[str, Any]],
        outcome: ExperienceOutcome,
        outcome_details: str,
        reward_signal: float,
        key_learnings: Optional[List[str]] = None,
        attention_points: Optional[List[str]] = None,
        challenges_faced: Optional[List[str]] = None,
        duration_seconds: int = 0,
        tokens_used: int = 0,
    ) -> str:
        """Record an agent experience."""
        return self.experience.record_experience(
            agent_id=agent_id,
            task=task,
            task_type=task_type,
            environment=environment,
            initial_state=initial_state,
            actions_taken=actions_taken,
            decisions_made=decisions_made,
            outcome=outcome,
            outcome_details=outcome_details,
            reward_signal=reward_signal,
            key_learnings=key_learnings,
            attention_points=attention_points,
            challenges_faced=challenges_faced,
            duration_seconds=duration_seconds,
            tokens_used=tokens_used,
        )

    def get_experiences_for_replay(
        self,
        agent_id: str,
        limit: int = 10,
        prioritize_failures: bool = True,
    ) -> List[Dict[str, Any]]:
        """Get experiences prioritized for replay learning."""
        return self.experience.get_experiences_for_replay(
            agent_id=agent_id,
            limit=limit,
            prioritize_failures=prioritize_failures,
        )

    def mark_experience_replayed(self, experience_id: str) -> Dict[str, Any]:
        """Mark an experience as replayed."""
        return self.experience.mark_replayed(experience_id)

    def get_learning_trajectory(
        self,
        agent_id: str,
        task_type: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get learning trajectory over time."""
        return self.experience.get_learning_trajectory(agent_id, task_type, days)

    # =========================================================================
    # Mistake API
    # =========================================================================

    def record_mistake(
        self,
        agent_id: str,
        category: MistakeCategory,
        severity: MistakeSeverity,
        task_context: str,
        agent_action: str,
        expected_action: str,
        actual_outcome: str,
        expected_outcome: str,
        root_cause: str,
        contributing_factors: Optional[List[str]] = None,
        correction_applied: str = "",
        corrected_by: str = "",
    ) -> str:
        """Record an agent mistake."""
        return self.mistake.record_mistake(
            agent_id=agent_id,
            category=category,
            severity=severity,
            task_context=task_context,
            agent_action=agent_action,
            expected_action=expected_action,
            actual_outcome=actual_outcome,
            expected_outcome=expected_outcome,
            root_cause=root_cause,
            contributing_factors=contributing_factors,
            correction_applied=correction_applied,
            corrected_by=corrected_by,
        )

    def apply_correction(
        self,
        mistake_id: str,
        correction: str,
        corrected_by: str,
        lesson_learned: str,
        prevention_strategy: str,
    ) -> Dict[str, Any]:
        """Apply a correction to a mistake."""
        return self.mistake.apply_correction(
            mistake_id=mistake_id,
            correction=correction,
            corrected_by=corrected_by,
            lesson_learned=lesson_learned,
            prevention_strategy=prevention_strategy,
        )

    def get_mistake_patterns(
        self,
        agent_id: str,
        min_frequency: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get detected mistake patterns."""
        return self.mistake.get_mistake_patterns(agent_id, min_frequency)

    def analyze_root_causes(self, agent_id: str) -> Dict[str, Any]:
        """Analyze root causes across all mistakes."""
        return self.mistake.analyze_root_causes(agent_id)

    # =========================================================================
    # Attention API
    # =========================================================================

    def record_attention(
        self,
        agent_id: str,
        attention_type: AttentionType,
        focus_target: str,
        focus_context: Dict[str, Any],
        attention_duration_ms: int,
        attention_quality: float,
        missed_elements: Optional[List[str]] = None,
        over_focused_elements: Optional[List[str]] = None,
        influenced_decision: bool = False,
        decision_id: Optional[str] = None,
    ) -> str:
        """Record an attention event."""
        return self.attention.record_attention(
            agent_id=agent_id,
            attention_type=attention_type,
            focus_target=focus_target,
            focus_context=focus_context,
            attention_duration_ms=attention_duration_ms,
            attention_quality=attention_quality,
            missed_elements=missed_elements,
            over_focused_elements=over_focused_elements,
            influenced_decision=influenced_decision,
            decision_id=decision_id,
        )

    def get_attention_recommendations(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get recommendations for improving attention."""
        return self.attention.get_attention_recommendations(agent_id)

    def get_frequently_missed(
        self,
        agent_id: str,
        min_count: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get frequently missed elements."""
        return self.attention.get_frequently_missed(agent_id, min_count)

    # =========================================================================
    # Supervision API
    # =========================================================================

    def record_supervision(
        self,
        agent_id: str,
        supervisor_id: str,
        supervisor_type: str,
        supervision_type: SupervisionType,
        supervised_action: str,
        supervised_output: str,
        context: Dict[str, Any],
        outcome: SupervisionOutcome,
        feedback: str,
        required_changes: Optional[List[str]] = None,
        learning_points: Optional[List[str]] = None,
        severity: str = "medium",
    ) -> str:
        """Record a supervision event."""
        return self.supervision.record_supervision(
            agent_id=agent_id,
            supervisor_id=supervisor_id,
            supervisor_type=supervisor_type,
            supervision_type=supervision_type,
            supervised_action=supervised_action,
            supervised_output=supervised_output,
            context=context,
            outcome=outcome,
            feedback=feedback,
            required_changes=required_changes,
            learning_points=learning_points,
            severity=severity,
        )

    def acknowledge_supervision(
        self,
        supervision_id: str,
        agent_id: str,
        acknowledgment_notes: str = "",
    ) -> Dict[str, Any]:
        """Agent acknowledges supervision feedback."""
        return self.supervision.acknowledge_supervision(
            supervision_id=supervision_id,
            agent_id=agent_id,
            acknowledgment_notes=acknowledgment_notes,
        )

    def get_pending_acknowledgments(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get supervision records pending acknowledgment."""
        return self.supervision.get_pending_acknowledgments(agent_id)

    def get_supervision_summary(
        self,
        agent_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get summary of supervision for an agent."""
        return self.supervision.get_supervision_summary(agent_id, days)

    # =========================================================================
    # Skill API
    # =========================================================================

    def register_skill(
        self,
        agent_id: str,
        name: str,
        category: str,
        description: str,
        prerequisites: Optional[List[str]] = None,
        initial_level: SkillLevel = SkillLevel.NOVICE,
    ) -> str:
        """Register a new skill for an agent."""
        return self.skill.register_skill(
            agent_id=agent_id,
            name=name,
            category=category,
            description=description,
            prerequisites=prerequisites,
            initial_level=initial_level,
        )

    def record_practice(
        self,
        skill_id: str,
        success: bool,
        performance_score: float,
        context: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record a practice session for a skill."""
        return self.skill.record_practice(
            skill_id=skill_id,
            success=success,
            performance_score=performance_score,
            context=context,
            notes=notes,
        )

    def get_skills_due_for_practice(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get skills that are due for practice."""
        return self.skill.get_skills_due_for_practice(agent_id, limit)

    def get_skill_summary(self, agent_id: str) -> Dict[str, Any]:
        """Get summary of all skills for an agent."""
        return self.skill.get_agent_skill_summary(agent_id)

    def apply_skill_decay(self, agent_id: str) -> Dict[str, Any]:
        """Apply forgetting curve decay to all skills."""
        return self.skill.apply_decay_all(agent_id)

    # =========================================================================
    # Retraining API
    # =========================================================================

    def identify_retraining_needs(
        self,
        agent_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Identify all retraining needs for an agent."""
        return self.retraining.identify_retraining_needs(agent_id, days)

    def generate_curriculum(
        self,
        agent_id: str,
        need_id: str,
    ) -> Dict[str, Any]:
        """Generate a curriculum for a specific need."""
        return self.retraining.generate_curriculum(agent_id, need_id)

    def start_curriculum(
        self,
        curriculum_id: str,
        pre_assessment_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Start a curriculum."""
        return self.retraining.start_curriculum(curriculum_id, pre_assessment_score)

    def complete_curriculum_module(
        self,
        curriculum_id: str,
        module_score: float,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Complete a module in the curriculum."""
        return self.retraining.complete_module(curriculum_id, module_score, notes)

    def complete_curriculum(
        self,
        curriculum_id: str,
        post_assessment_score: float,
        final_notes: str = "",
    ) -> Dict[str, Any]:
        """Complete a curriculum with final assessment."""
        return self.retraining.complete_curriculum(
            curriculum_id,
            post_assessment_score,
            final_notes,
        )

    def get_retraining_progress(self, agent_id: str) -> Dict[str, Any]:
        """Get overall retraining progress for an agent."""
        return self.retraining.get_retraining_progress(agent_id)

    # =========================================================================
    # Unified Analysis
    # =========================================================================

    def get_agent_learning_profile(self, agent_id: str) -> Dict[str, Any]:
        """Get comprehensive learning profile for an agent."""
        trajectory = self.get_learning_trajectory(agent_id)
        skill_summary = self.get_skill_summary(agent_id)
        supervision_summary = self.get_supervision_summary(agent_id)
        retraining_progress = self.get_retraining_progress(agent_id)
        mistake_patterns = self.get_mistake_patterns(agent_id)
        attention_recs = self.get_attention_recommendations(agent_id)

        # Calculate overall health score
        health_factors = []

        if trajectory.get("success_rate") is not None:
            health_factors.append(trajectory["success_rate"])

        if skill_summary.get("average_proficiency") is not None:
            health_factors.append(skill_summary["average_proficiency"] / 100)

        if supervision_summary.get("effectiveness_rate") is not None:
            health_factors.append(supervision_summary["effectiveness_rate"])

        overall_health = sum(health_factors) / len(health_factors) if health_factors else 0.5

        return {
            "agent_id": agent_id,
            "overall_health_score": overall_health,
            "learning_trajectory": trajectory,
            "skill_summary": skill_summary,
            "supervision_summary": supervision_summary,
            "retraining_progress": retraining_progress,
            "active_mistake_patterns": len(mistake_patterns),
            "attention_recommendations": len(attention_recs),
            "recommendations": self._generate_profile_recommendations(
                trajectory,
                skill_summary,
                supervision_summary,
                retraining_progress,
                mistake_patterns,
                attention_recs,
            ),
        }

    def _generate_profile_recommendations(
        self,
        trajectory: Dict[str, Any],
        skill_summary: Dict[str, Any],
        supervision_summary: Dict[str, Any],
        retraining_progress: Dict[str, Any],
        mistake_patterns: List[Dict[str, Any]],
        attention_recs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate recommendations based on learning profile."""
        recommendations = []

        # Check success rate
        success_rate = trajectory.get("success_rate", 1.0)
        if success_rate < 0.7:
            recommendations.append({
                "priority": "high",
                "area": "task_success",
                "recommendation": "Review failed experiences and identify common failure patterns",
            })

        # Check skills due for practice
        skills_due = skill_summary.get("skills_due_for_practice", 0)
        if skills_due > 3:
            recommendations.append({
                "priority": "medium",
                "area": "skill_maintenance",
                "recommendation": f"Practice {skills_due} overdue skills to prevent decay",
            })

        # Check pending needs
        pending_needs = retraining_progress.get("pending_needs", 0)
        high_priority = retraining_progress.get("high_priority_needs", 0)
        if high_priority > 0:
            recommendations.append({
                "priority": "high",
                "area": "retraining",
                "recommendation": f"Address {high_priority} high-priority retraining needs",
            })
        elif pending_needs > 3:
            recommendations.append({
                "priority": "medium",
                "area": "retraining",
                "recommendation": f"Review {pending_needs} pending retraining needs",
            })

        # Check mistake patterns
        if len(mistake_patterns) > 2:
            recommendations.append({
                "priority": "high",
                "area": "mistake_prevention",
                "recommendation": f"Address {len(mistake_patterns)} recurring mistake patterns",
            })

        # Check attention
        if len(attention_recs) > 0:
            recommendations.append({
                "priority": "medium",
                "area": "attention",
                "recommendation": f"Improve attention based on {len(attention_recs)} recommendations",
            })

        return recommendations

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get overall statistics for the learning engine."""
        return {
            "engine_name": self.name,
            "experience": self.experience.get_stats(),
            "mistake": self.mistake.get_stats(),
            "attention": self.attention.get_stats(),
            "supervision": self.supervision.get_stats(),
            "skill": self.skill.get_stats(),
            "retraining": self.retraining.get_stats(),
        }
