"""
Experience Store
================

Stores and manages agent experiences for replay learning.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
import math

from .base import BaseLearningStore
from ..schema import (
    ExperienceOutcome,
    LearningEventType,
)


class ExperienceStore(BaseLearningStore):
    """
    Store for agent experiences.

    Provides:
    - Experience recording with full context
    - Experience replay for learning
    - Outcome-based filtering
    - Priority-based retrieval
    - Experience consolidation
    """

    def __init__(self, graph):
        super().__init__(graph, "experience")

    # =========================================================================
    # Experience Recording
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
        """Record a new experience."""
        exp_id = self._generate_id("exp")

        self._add_node("experience", exp_id, {
            "agent_id": agent_id,
            "task": task,
            "task_type": task_type,
            "environment": environment,
            "initial_state": initial_state,
            "actions_taken": actions_taken,
            "decisions_made": decisions_made,
            "outcome": outcome.value if isinstance(outcome, ExperienceOutcome) else outcome,
            "outcome_details": outcome_details,
            "reward_signal": reward_signal,
            "key_learnings": key_learnings or [],
            "attention_points": attention_points or [],
            "challenges_faced": challenges_faced or [],
            "duration_seconds": duration_seconds,
            "tokens_used": tokens_used,
            "replay_count": 0,
            "last_replayed": None,
            "importance_score": self._calculate_importance(outcome, reward_signal),
        })

        # Create learning events from key learnings
        for learning in (key_learnings or []):
            self._create_learning_event(agent_id, exp_id, learning, outcome)

        return exp_id

    def _calculate_importance(
        self,
        outcome: ExperienceOutcome,
        reward_signal: float,
    ) -> float:
        """Calculate importance score for experience."""
        outcome_val = outcome.value if isinstance(outcome, ExperienceOutcome) else outcome

        # Failures and corrections are more important for learning
        outcome_weights = {
            "success": 0.5,
            "partial_success": 0.6,
            "failure": 1.0,
            "blocked": 0.8,
            "timeout": 0.7,
            "corrected": 0.9,
        }

        base_score = outcome_weights.get(outcome_val, 0.5)

        # Extreme rewards are more important
        reward_importance = abs(reward_signal)

        return (base_score + reward_importance) / 2

    def _create_learning_event(
        self,
        agent_id: str,
        experience_id: str,
        learning: str,
        outcome: ExperienceOutcome,
    ) -> str:
        """Create a learning event from experience."""
        event_id = self._generate_id("learn_event")

        outcome_val = outcome.value if isinstance(outcome, ExperienceOutcome) else outcome

        event_type = LearningEventType.INSIGHT_GAINED
        if outcome_val == "failure":
            event_type = LearningEventType.MISTAKE_CORRECTED
        elif outcome_val == "success":
            event_type = LearningEventType.PATTERN_LEARNED

        self._add_node("learning_event", event_id, {
            "agent_id": agent_id,
            "event_type": event_type.value,
            "learning_content": learning,
            "source": f"experience:{experience_id}",
            "confidence": 0.7,
            "reinforcement_count": 0,
            "decay_factor": 1.0,
        })

        self._add_edge(
            "learning_event", event_id,
            "LEARNED_FROM",
            "experience", experience_id,
            {}
        )

        return event_id

    def get_experience(self, experience_id: str) -> Optional[Dict[str, Any]]:
        """Get an experience by ID."""
        return self._get_node("experience", experience_id)

    # =========================================================================
    # Experience Replay
    # =========================================================================

    def get_experiences_for_replay(
        self,
        agent_id: str,
        limit: int = 10,
        prioritize_failures: bool = True,
        min_importance: float = 0.0,
        task_types: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Get experiences for replay learning."""
        experiences = self._find_nodes("experience", agent_id=agent_id)

        # Filter by importance
        experiences = [e for e in experiences if e.get("importance_score", 0) >= min_importance]

        # Filter by task type
        if task_types:
            experiences = [e for e in experiences if e.get("task_type") in task_types]

        # Score for replay priority
        for exp in experiences:
            exp["replay_priority"] = self._calculate_replay_priority(exp, prioritize_failures)

        # Sort by replay priority
        experiences.sort(key=lambda x: x.get("replay_priority", 0), reverse=True)

        return experiences[:limit]

    def _calculate_replay_priority(
        self,
        experience: Dict[str, Any],
        prioritize_failures: bool,
    ) -> float:
        """Calculate replay priority for an experience."""
        importance = experience.get("importance_score", 0.5)
        replay_count = experience.get("replay_count", 0)
        outcome = experience.get("outcome", "success")

        # Base priority from importance
        priority = importance

        # Reduce priority for frequently replayed
        replay_decay = math.exp(-0.1 * replay_count)
        priority *= replay_decay

        # Boost failures if prioritized
        if prioritize_failures and outcome in ["failure", "blocked", "corrected"]:
            priority *= 1.5

        # Boost recent experiences slightly
        created_at = experience.get("_created_at", "")
        if created_at:
            try:
                created = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                age_days = (datetime.now(timezone.utc) - created).days
                recency_boost = math.exp(-0.05 * age_days)
                priority *= (0.5 + 0.5 * recency_boost)
            except Exception:
                pass

        return priority

    def mark_replayed(self, experience_id: str) -> Dict[str, Any]:
        """Mark an experience as replayed."""
        experience = self._get_node("experience", experience_id)
        if not experience:
            return {"error": "Experience not found"}

        replay_count = experience.get("replay_count", 0) + 1

        self._update_node("experience", experience_id, {
            "replay_count": replay_count,
            "last_replayed": self._now(),
        })

        return {"replayed": True, "replay_count": replay_count}

    # =========================================================================
    # Experience Analysis
    # =========================================================================

    def get_experiences_by_outcome(
        self,
        agent_id: str,
        outcome: ExperienceOutcome,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get experiences filtered by outcome."""
        outcome_val = outcome.value if isinstance(outcome, ExperienceOutcome) else outcome
        experiences = self._find_nodes("experience", agent_id=agent_id, outcome=outcome_val)

        # Sort by recency
        experiences.sort(key=lambda x: x.get("_created_at", ""), reverse=True)

        return experiences[:limit]

    def get_similar_experiences(
        self,
        experience_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Find similar experiences based on task type and context."""
        experience = self._get_node("experience", experience_id)
        if not experience:
            return []

        agent_id = experience.get("agent_id")
        task_type = experience.get("task_type")

        # Find experiences with same task type
        similar = self._find_nodes("experience", agent_id=agent_id, task_type=task_type)

        # Exclude self
        similar = [e for e in similar if e.get("id") != experience_id]

        # Score by similarity
        for exp in similar:
            exp["similarity_score"] = self._calculate_similarity(experience, exp)

        similar.sort(key=lambda x: x.get("similarity_score", 0), reverse=True)

        return similar[:limit]

    def _calculate_similarity(
        self,
        exp1: Dict[str, Any],
        exp2: Dict[str, Any],
    ) -> float:
        """Calculate similarity between two experiences."""
        score = 0.0

        # Task type match
        if exp1.get("task_type") == exp2.get("task_type"):
            score += 0.3

        # Outcome similarity
        if exp1.get("outcome") == exp2.get("outcome"):
            score += 0.2

        # Challenge overlap
        challenges1 = set(exp1.get("challenges_faced", []))
        challenges2 = set(exp2.get("challenges_faced", []))
        if challenges1 and challenges2:
            overlap = len(challenges1 & challenges2) / len(challenges1 | challenges2)
            score += 0.2 * overlap

        # Learning overlap
        learnings1 = set(exp1.get("key_learnings", []))
        learnings2 = set(exp2.get("key_learnings", []))
        if learnings1 and learnings2:
            overlap = len(learnings1 & learnings2) / len(learnings1 | learnings2)
            score += 0.3 * overlap

        return score

    def get_learning_trajectory(
        self,
        agent_id: str,
        task_type: Optional[str] = None,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Analyze learning trajectory over time."""
        experiences = self._find_nodes("experience", agent_id=agent_id)

        if task_type:
            experiences = [e for e in experiences if e.get("task_type") == task_type]

        # Filter by date
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        experiences = [e for e in experiences if e.get("_created_at", "") >= cutoff]

        if not experiences:
            return {"error": "No experiences found", "agent_id": agent_id}

        # Sort by date
        experiences.sort(key=lambda x: x.get("_created_at", ""))

        # Calculate metrics over time
        success_count = 0
        failure_count = 0
        total_reward = 0.0
        learnings_count = 0

        for exp in experiences:
            outcome = exp.get("outcome")
            if outcome == "success":
                success_count += 1
            elif outcome in ["failure", "blocked"]:
                failure_count += 1

            total_reward += exp.get("reward_signal", 0)
            learnings_count += len(exp.get("key_learnings", []))

        total = len(experiences)
        success_rate = success_count / total if total > 0 else 0

        return {
            "agent_id": agent_id,
            "task_type": task_type,
            "period_days": days,
            "total_experiences": total,
            "success_count": success_count,
            "failure_count": failure_count,
            "success_rate": success_rate,
            "average_reward": total_reward / total if total > 0 else 0,
            "total_learnings": learnings_count,
            "learnings_per_experience": learnings_count / total if total > 0 else 0,
        }

    # =========================================================================
    # Experience Consolidation
    # =========================================================================

    def consolidate_experiences(
        self,
        agent_id: str,
        task_type: str,
        min_similarity: float = 0.7,
    ) -> Dict[str, Any]:
        """Consolidate similar experiences into generalized patterns."""
        experiences = self._find_nodes("experience", agent_id=agent_id, task_type=task_type)

        if len(experiences) < 3:
            return {"consolidated": False, "reason": "Not enough experiences"}

        # Group by outcome
        by_outcome = {}
        for exp in experiences:
            outcome = exp.get("outcome")
            if outcome not in by_outcome:
                by_outcome[outcome] = []
            by_outcome[outcome].append(exp)

        consolidated_patterns = []

        for outcome, exps in by_outcome.items():
            if len(exps) < 2:
                continue

            # Find common learnings
            all_learnings = []
            for exp in exps:
                all_learnings.extend(exp.get("key_learnings", []))

            # Count frequency
            learning_counts = {}
            for learning in all_learnings:
                learning_counts[learning] = learning_counts.get(learning, 0) + 1

            # Keep learnings that appear in at least 50% of experiences
            threshold = len(exps) * 0.5
            common_learnings = [l for l, c in learning_counts.items() if c >= threshold]

            if common_learnings:
                pattern_id = self._generate_id("exp_pattern")

                self._add_node("experience_pattern", pattern_id, {
                    "agent_id": agent_id,
                    "task_type": task_type,
                    "outcome": outcome,
                    "common_learnings": common_learnings,
                    "source_experience_count": len(exps),
                    "confidence": len(common_learnings) / max(len(all_learnings), 1),
                })

                consolidated_patterns.append({
                    "pattern_id": pattern_id,
                    "outcome": outcome,
                    "learnings": common_learnings,
                })

        return {
            "consolidated": True,
            "patterns_created": len(consolidated_patterns),
            "patterns": consolidated_patterns,
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get experience store statistics."""
        experiences = self._find_nodes("experience")
        patterns = self._find_nodes("experience_pattern")
        events = self._find_nodes("learning_event")

        # Count by outcome
        by_outcome = {}
        total_reward = 0.0
        total_replays = 0

        for exp in experiences:
            outcome = exp.get("outcome", "unknown")
            by_outcome[outcome] = by_outcome.get(outcome, 0) + 1
            total_reward += exp.get("reward_signal", 0)
            total_replays += exp.get("replay_count", 0)

        return {
            "total_experiences": len(experiences),
            "total_patterns": len(patterns),
            "total_learning_events": len(events),
            "experiences_by_outcome": by_outcome,
            "average_reward": total_reward / len(experiences) if experiences else 0,
            "total_replays": total_replays,
        }
