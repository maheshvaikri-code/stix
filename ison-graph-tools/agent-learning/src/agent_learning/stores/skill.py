"""
Skill Store
===========

Tracks agent skills, proficiency, and development over time.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
import math

from .base import BaseLearningStore
from ..schema import (
    SkillLevel,
    SKILL_LEVEL_THRESHOLDS,
    SPACED_REPETITION_INTERVALS,
    FORGETTING_CURVE,
)


class SkillStore(BaseLearningStore):
    """
    Store for agent skill tracking.

    Provides:
    - Skill registration and tracking
    - Proficiency measurement
    - Practice scheduling (spaced repetition)
    - Skill decay modeling
    - Prerequisite management
    """

    def __init__(self, graph):
        super().__init__(graph, "skill")

    # =========================================================================
    # Skill Management
    # =========================================================================

    def register_skill(
        self,
        agent_id: str,
        name: str,
        category: str,
        description: str,
        prerequisites: Optional[List[str]] = None,
        initial_level: SkillLevel = SkillLevel.NOVICE,
        initial_proficiency: float = 0.0,
    ) -> str:
        """Register a new skill for an agent."""
        skill_id = self._generate_id("skill")

        self._add_node("skill", skill_id, {
            "agent_id": agent_id,
            "name": name,
            "category": category,
            "description": description,
            "level": initial_level.value if isinstance(initial_level, SkillLevel) else initial_level,
            "proficiency_score": initial_proficiency,
            "confidence_score": 0.5,  # Initial confidence
            "practice_count": 0,
            "success_count": 0,
            "failure_count": 0,
            "last_practiced": None,
            "last_success": None,
            "next_practice_due": self._now(),  # Due immediately
            "spaced_repetition_stage": 0,
            "decay_factor": 1.0,
            "prerequisites": prerequisites or [],
            "learning_events": [],
            "related_mistakes": [],
        })

        # Create prerequisite edges
        for prereq_name in (prerequisites or []):
            prereq = self._find_skill_by_name(agent_id, prereq_name)
            if prereq:
                self._add_edge(
                    "skill", skill_id,
                    "REQUIRES",
                    "skill", prereq["id"],
                    {}
                )

        return skill_id

    def _find_skill_by_name(
        self,
        agent_id: str,
        skill_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Find a skill by name for an agent."""
        skills = self._find_nodes("skill", agent_id=agent_id, name=skill_name)
        return skills[0] if skills else None

    def get_skill(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """Get a skill by ID."""
        return self._get_node("skill", skill_id)

    def get_skill_by_name(
        self,
        agent_id: str,
        skill_name: str,
    ) -> Optional[Dict[str, Any]]:
        """Get a skill by name."""
        return self._find_skill_by_name(agent_id, skill_name)

    # =========================================================================
    # Practice and Proficiency
    # =========================================================================

    def record_practice(
        self,
        skill_id: str,
        success: bool,
        performance_score: float,  # 0-1
        context: Optional[Dict[str, Any]] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Record a practice session for a skill."""
        skill = self._get_node("skill", skill_id)
        if not skill:
            return {"error": "Skill not found"}

        practice_count = skill.get("practice_count", 0) + 1
        success_count = skill.get("success_count", 0) + (1 if success else 0)
        failure_count = skill.get("failure_count", 0) + (0 if success else 1)

        # Update proficiency using exponential moving average
        current_proficiency = skill.get("proficiency_score", 0)
        alpha = 0.3  # Learning rate
        new_proficiency = current_proficiency + alpha * (performance_score * 100 - current_proficiency)

        # Update confidence based on consistency
        success_rate = success_count / practice_count if practice_count > 0 else 0
        confidence = min(1.0, success_rate * (1 - math.exp(-practice_count / 10)))

        # Determine skill level from proficiency
        new_level = self._proficiency_to_level(new_proficiency)

        # Update spaced repetition stage
        sr_stage = skill.get("spaced_repetition_stage", 0)
        if success and performance_score >= 0.7:
            sr_stage = min(sr_stage + 1, len(SPACED_REPETITION_INTERVALS) - 1)
        elif not success:
            sr_stage = max(0, sr_stage - 2)

        # Calculate next practice due date
        days_until_next = SPACED_REPETITION_INTERVALS[sr_stage]
        next_due = (datetime.now(timezone.utc) + timedelta(days=days_until_next)).isoformat()

        self._update_node("skill", skill_id, {
            "practice_count": practice_count,
            "success_count": success_count,
            "failure_count": failure_count,
            "proficiency_score": new_proficiency,
            "confidence_score": confidence,
            "level": new_level,
            "last_practiced": self._now(),
            "last_success": self._now() if success else skill.get("last_success"),
            "spaced_repetition_stage": sr_stage,
            "next_practice_due": next_due,
            "decay_factor": 1.0,  # Reset decay after practice
        })

        # Record practice event
        practice_id = self._generate_id("practice")
        self._add_node("practice_record", practice_id, {
            "skill_id": skill_id,
            "agent_id": skill.get("agent_id"),
            "success": success,
            "performance_score": performance_score,
            "context": context or {},
            "notes": notes,
            "proficiency_before": current_proficiency,
            "proficiency_after": new_proficiency,
        })

        return {
            "practiced": True,
            "skill_id": skill_id,
            "new_proficiency": new_proficiency,
            "new_level": new_level,
            "next_practice_due": next_due,
            "level_changed": new_level != skill.get("level"),
        }

    def _proficiency_to_level(self, proficiency: float) -> str:
        """Convert proficiency score to skill level."""
        for level in reversed(list(SkillLevel)):
            if proficiency >= SKILL_LEVEL_THRESHOLDS[level]:
                return level.value
        return SkillLevel.NOVICE.value

    def apply_decay(
        self,
        skill_id: str,
    ) -> Dict[str, Any]:
        """Apply forgetting curve decay to a skill."""
        skill = self._get_node("skill", skill_id)
        if not skill:
            return {"error": "Skill not found"}

        last_practiced = skill.get("last_practiced")
        if not last_practiced:
            return {"decayed": False, "reason": "Never practiced"}

        try:
            last = datetime.fromisoformat(last_practiced.replace("Z", "+00:00"))
            days_since = (datetime.now(timezone.utc) - last).days
        except Exception:
            return {"decayed": False, "reason": "Invalid date"}

        if days_since <= 0:
            return {"decayed": False, "reason": "Practiced today"}

        # Apply Ebbinghaus forgetting curve
        decay_rate = FORGETTING_CURVE["decay_rate"]
        min_retention = FORGETTING_CURVE["min_retention"]

        decay_factor = max(min_retention, math.exp(-days_since / decay_rate))

        current_proficiency = skill.get("proficiency_score", 0)
        decayed_proficiency = current_proficiency * decay_factor

        # Update confidence too
        current_confidence = skill.get("confidence_score", 0.5)
        decayed_confidence = max(0.1, current_confidence * decay_factor)

        new_level = self._proficiency_to_level(decayed_proficiency)

        self._update_node("skill", skill_id, {
            "proficiency_score": decayed_proficiency,
            "confidence_score": decayed_confidence,
            "decay_factor": decay_factor,
            "level": new_level,
        })

        return {
            "decayed": True,
            "skill_id": skill_id,
            "days_since_practice": days_since,
            "decay_factor": decay_factor,
            "proficiency_before": current_proficiency,
            "proficiency_after": decayed_proficiency,
            "level_changed": new_level != skill.get("level"),
        }

    def apply_decay_all(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Apply decay to all skills for an agent."""
        skills = self._find_nodes("skill", agent_id=agent_id)

        decayed = []
        for skill in skills:
            result = self.apply_decay(skill["id"])
            if result.get("decayed"):
                decayed.append({
                    "skill_id": skill["id"],
                    "name": skill.get("name"),
                    "decay_factor": result.get("decay_factor"),
                })

        return {
            "agent_id": agent_id,
            "total_skills": len(skills),
            "decayed_count": len(decayed),
            "decayed_skills": decayed,
        }

    # =========================================================================
    # Skill Queries
    # =========================================================================

    def get_skills_by_level(
        self,
        agent_id: str,
        level: SkillLevel,
    ) -> List[Dict[str, Any]]:
        """Get skills at a specific level."""
        level_val = level.value if isinstance(level, SkillLevel) else level
        skills = self._find_nodes("skill", agent_id=agent_id, level=level_val)

        skills.sort(key=lambda x: x.get("proficiency_score", 0), reverse=True)
        return skills

    def get_skills_by_category(
        self,
        agent_id: str,
        category: str,
    ) -> List[Dict[str, Any]]:
        """Get skills in a category."""
        skills = self._find_nodes("skill", agent_id=agent_id, category=category)

        skills.sort(key=lambda x: x.get("proficiency_score", 0), reverse=True)
        return skills

    def get_skills_due_for_practice(
        self,
        agent_id: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get skills that are due for practice."""
        skills = self._find_nodes("skill", agent_id=agent_id)

        now = datetime.now(timezone.utc).isoformat()

        due = [s for s in skills if s.get("next_practice_due", "") <= now]

        # Sort by how overdue
        due.sort(key=lambda x: x.get("next_practice_due", ""))

        return due[:limit]

    def get_weakest_skills(
        self,
        agent_id: str,
        limit: int = 5,
    ) -> List[Dict[str, Any]]:
        """Get skills with lowest proficiency."""
        skills = self._find_nodes("skill", agent_id=agent_id)

        skills.sort(key=lambda x: x.get("proficiency_score", 0))
        return skills[:limit]

    def get_skill_prerequisites(
        self,
        skill_id: str,
    ) -> List[Dict[str, Any]]:
        """Get prerequisite skills."""
        edges = self._find_edges(
            source_type="skill",
            source_id=skill_id,
            rel_type="REQUIRES",
        )

        prerequisites = []
        for edge in edges:
            prereq = self._get_node("skill", edge.get("target_id"))
            if prereq:
                prerequisites.append(prereq)

        return prerequisites

    def check_prerequisites_met(
        self,
        skill_id: str,
        min_level: SkillLevel = SkillLevel.INTERMEDIATE,
    ) -> Dict[str, Any]:
        """Check if prerequisites are met for a skill."""
        prerequisites = self.get_skill_prerequisites(skill_id)

        if not prerequisites:
            return {"met": True, "prerequisites": [], "missing": []}

        level_val = min_level.value if isinstance(min_level, SkillLevel) else min_level
        level_threshold = SKILL_LEVEL_THRESHOLDS[SkillLevel(level_val)]

        met = []
        missing = []

        for prereq in prerequisites:
            if prereq.get("proficiency_score", 0) >= level_threshold:
                met.append(prereq.get("name"))
            else:
                missing.append({
                    "name": prereq.get("name"),
                    "current_level": prereq.get("level"),
                    "current_proficiency": prereq.get("proficiency_score"),
                    "required_proficiency": level_threshold,
                })

        return {
            "met": len(missing) == 0,
            "prerequisites": [p.get("name") for p in prerequisites],
            "satisfied": met,
            "missing": missing,
        }

    # =========================================================================
    # Skill Analysis
    # =========================================================================

    def get_skill_progress(
        self,
        skill_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Get progress history for a skill."""
        skill = self._get_node("skill", skill_id)
        if not skill:
            return {"error": "Skill not found"}

        # Get practice records
        practices = self._find_nodes("practice_record", skill_id=skill_id)

        # Filter by date
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        practices = [p for p in practices if p.get("_created_at", "") >= cutoff]

        practices.sort(key=lambda x: x.get("_created_at", ""))

        return {
            "skill_id": skill_id,
            "skill_name": skill.get("name"),
            "period_days": days,
            "current_level": skill.get("level"),
            "current_proficiency": skill.get("proficiency_score"),
            "practice_count": len(practices),
            "practices": [
                {
                    "date": p.get("_created_at"),
                    "success": p.get("success"),
                    "score": p.get("performance_score"),
                    "proficiency_after": p.get("proficiency_after"),
                }
                for p in practices
            ],
        }

    def get_agent_skill_summary(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Get summary of all skills for an agent."""
        skills = self._find_nodes("skill", agent_id=agent_id)

        by_level = {}
        by_category = {}
        total_proficiency = 0
        practice_due = 0
        now = datetime.now(timezone.utc).isoformat()

        for skill in skills:
            level = skill.get("level", "novice")
            by_level[level] = by_level.get(level, 0) + 1

            category = skill.get("category", "uncategorized")
            by_category[category] = by_category.get(category, 0) + 1

            total_proficiency += skill.get("proficiency_score", 0)

            if skill.get("next_practice_due", "") <= now:
                practice_due += 1

        return {
            "agent_id": agent_id,
            "total_skills": len(skills),
            "by_level": by_level,
            "by_category": by_category,
            "average_proficiency": total_proficiency / len(skills) if skills else 0,
            "skills_due_for_practice": practice_due,
        }

    def get_learning_path(
        self,
        agent_id: str,
        target_skill: str,
    ) -> Dict[str, Any]:
        """Get recommended learning path to acquire a skill."""
        # Find or suggest the target skill
        skill = self._find_skill_by_name(agent_id, target_skill)

        if not skill:
            return {
                "error": "Skill not found",
                "suggestion": f"Register skill '{target_skill}' first",
            }

        # Build prerequisite tree
        path = []
        visited = set()

        def add_prereqs(s):
            if s["id"] in visited:
                return
            visited.add(s["id"])

            prereqs = self.get_skill_prerequisites(s["id"])
            for prereq in prereqs:
                add_prereqs(prereq)

            # Add skill if not mastered
            if s.get("proficiency_score", 0) < SKILL_LEVEL_THRESHOLDS[SkillLevel.INTERMEDIATE]:
                path.append({
                    "skill_id": s["id"],
                    "name": s.get("name"),
                    "current_level": s.get("level"),
                    "current_proficiency": s.get("proficiency_score"),
                    "target_proficiency": SKILL_LEVEL_THRESHOLDS[SkillLevel.INTERMEDIATE],
                })

        add_prereqs(skill)

        return {
            "agent_id": agent_id,
            "target_skill": target_skill,
            "learning_path": path,
            "total_skills_to_develop": len(path),
        }

    # =========================================================================
    # Skill-Learning Integration
    # =========================================================================

    def link_learning_event(
        self,
        skill_id: str,
        learning_event_id: str,
    ) -> Dict[str, Any]:
        """Link a learning event to a skill."""
        skill = self._get_node("skill", skill_id)
        if not skill:
            return {"error": "Skill not found"}

        events = skill.get("learning_events", [])
        if learning_event_id not in events:
            events.append(learning_event_id)

        self._update_node("skill", skill_id, {
            "learning_events": events,
        })

        self._add_edge(
            "skill", skill_id,
            "DEVELOPED_BY",
            "learning_event", learning_event_id,
            {}
        )

        return {"linked": True, "skill_id": skill_id}

    def link_mistake(
        self,
        skill_id: str,
        mistake_id: str,
    ) -> Dict[str, Any]:
        """Link a mistake to a skill (indicates area needing improvement)."""
        skill = self._get_node("skill", skill_id)
        if not skill:
            return {"error": "Skill not found"}

        mistakes = skill.get("related_mistakes", [])
        if mistake_id not in mistakes:
            mistakes.append(mistake_id)

        # Reduce confidence when mistakes occur
        current_confidence = skill.get("confidence_score", 0.5)
        new_confidence = max(0.1, current_confidence - 0.1)

        self._update_node("skill", skill_id, {
            "related_mistakes": mistakes,
            "confidence_score": new_confidence,
        })

        self._add_edge(
            "skill", skill_id,
            "IMPACTED_BY",
            "mistake", mistake_id,
            {}
        )

        return {"linked": True, "skill_id": skill_id, "new_confidence": new_confidence}

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get skill store statistics."""
        skills = self._find_nodes("skill")
        practices = self._find_nodes("practice_record")

        by_level = {}
        by_category = {}
        total_proficiency = 0
        total_practice = 0

        for skill in skills:
            level = skill.get("level", "novice")
            by_level[level] = by_level.get(level, 0) + 1

            category = skill.get("category", "uncategorized")
            by_category[category] = by_category.get(category, 0) + 1

            total_proficiency += skill.get("proficiency_score", 0)
            total_practice += skill.get("practice_count", 0)

        success_practices = sum(1 for p in practices if p.get("success"))

        return {
            "total_skills": len(skills),
            "total_practice_records": len(practices),
            "by_level": by_level,
            "by_category": by_category,
            "average_proficiency": total_proficiency / len(skills) if skills else 0,
            "total_practice_sessions": total_practice,
            "practice_success_rate": success_practices / len(practices) if practices else 0,
        }
