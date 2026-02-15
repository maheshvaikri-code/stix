"""
Retraining Engine
=================

Identifies retraining needs and generates curricula for agent improvement.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field

from .stores.base import BaseLearningStore
from .stores.experience import ExperienceStore
from .stores.mistake import MistakeStore
from .stores.attention import AttentionStore
from .stores.supervision import SupervisionStore
from .stores.skill import SkillStore
from .schema import (
    RetrainingPriority,
    CurriculumType,
    MistakeSeverity,
    SkillLevel,
    MISTAKE_SEVERITY_WEIGHTS,
    SKILL_LEVEL_THRESHOLDS,
)


class RetrainingNeedStore(BaseLearningStore):
    """Store for retraining needs."""

    def __init__(self, graph):
        super().__init__(graph, "retraining")

    def create_need(
        self,
        agent_id: str,
        skill_area: str,
        specific_issue: str,
        priority: RetrainingPriority,
        curriculum_type: CurriculumType,
        evidence: List[str],
        recommended_exercises: Optional[List[Dict[str, Any]]] = None,
        estimated_duration_hours: float = 1.0,
    ) -> str:
        """Create a retraining need."""
        need_id = self._generate_id("need")

        self._add_node("retraining_need", need_id, {
            "agent_id": agent_id,
            "skill_area": skill_area,
            "specific_issue": specific_issue,
            "priority": priority.value if isinstance(priority, RetrainingPriority) else priority,
            "curriculum_type": curriculum_type.value if isinstance(curriculum_type, CurriculumType) else curriculum_type,
            "evidence": evidence,
            "recommended_exercises": recommended_exercises or [],
            "estimated_duration_hours": estimated_duration_hours,
            "status": "pending",
            "started_at": None,
            "completed_at": None,
            "effectiveness_score": None,
        })

        return need_id

    def get_need(self, need_id: str) -> Optional[Dict[str, Any]]:
        """Get a retraining need."""
        return self._get_node("retraining_need", need_id)

    def get_pending_needs(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Get pending retraining needs."""
        needs = self._find_nodes("retraining_need", agent_id=agent_id, status="pending")

        # Sort by priority
        priority_order = [p.value for p in RetrainingPriority]
        needs.sort(key=lambda x: priority_order.index(x.get("priority", "medium")))

        return needs

    def start_retraining(
        self,
        need_id: str,
    ) -> Dict[str, Any]:
        """Start working on a retraining need."""
        need = self._get_node("retraining_need", need_id)
        if not need:
            return {"error": "Need not found"}

        self._update_node("retraining_need", need_id, {
            "status": "in_progress",
            "started_at": self._now(),
        })

        return {"started": True, "need_id": need_id}

    def complete_retraining(
        self,
        need_id: str,
        effectiveness_score: float,
        completion_notes: str = "",
    ) -> Dict[str, Any]:
        """Mark retraining as completed."""
        need = self._get_node("retraining_need", need_id)
        if not need:
            return {"error": "Need not found"}

        self._update_node("retraining_need", need_id, {
            "status": "completed",
            "completed_at": self._now(),
            "effectiveness_score": effectiveness_score,
            "completion_notes": completion_notes,
        })

        return {"completed": True, "need_id": need_id}

    def get_stats(self) -> Dict[str, Any]:
        """Get retraining need statistics."""
        needs = self._find_nodes("retraining_need")

        by_status = {}
        by_priority = {}
        by_curriculum = {}

        for need in needs:
            status = need.get("status", "pending")
            by_status[status] = by_status.get(status, 0) + 1

            priority = need.get("priority", "medium")
            by_priority[priority] = by_priority.get(priority, 0) + 1

            ctype = need.get("curriculum_type", "unknown")
            by_curriculum[ctype] = by_curriculum.get(ctype, 0) + 1

        return {
            "total_needs": len(needs),
            "by_status": by_status,
            "by_priority": by_priority,
            "by_curriculum_type": by_curriculum,
        }


class CurriculumStore(BaseLearningStore):
    """Store for retraining curricula."""

    def __init__(self, graph):
        super().__init__(graph, "curriculum")

    def create_curriculum(
        self,
        agent_id: str,
        curriculum_type: CurriculumType,
        title: str,
        description: str,
        objectives: List[str],
        modules: List[Dict[str, Any]],
        based_on_mistakes: Optional[List[str]] = None,
        based_on_experiences: Optional[List[str]] = None,
        based_on_supervision: Optional[List[str]] = None,
    ) -> str:
        """Create a retraining curriculum."""
        curriculum_id = self._generate_id("curriculum")

        self._add_node("curriculum", curriculum_id, {
            "agent_id": agent_id,
            "curriculum_type": curriculum_type.value if isinstance(curriculum_type, CurriculumType) else curriculum_type,
            "title": title,
            "description": description,
            "objectives": objectives,
            "modules": modules,
            "total_modules": len(modules),
            "completed_modules": 0,
            "current_module": 0,
            "status": "pending",
            "based_on_mistakes": based_on_mistakes or [],
            "based_on_experiences": based_on_experiences or [],
            "based_on_supervision": based_on_supervision or [],
            "pre_assessment_score": None,
            "post_assessment_score": None,
        })

        return curriculum_id

    def get_curriculum(self, curriculum_id: str) -> Optional[Dict[str, Any]]:
        """Get a curriculum."""
        return self._get_node("curriculum", curriculum_id)

    def start_curriculum(
        self,
        curriculum_id: str,
        pre_assessment_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Start a curriculum."""
        curriculum = self._get_node("curriculum", curriculum_id)
        if not curriculum:
            return {"error": "Curriculum not found"}

        self._update_node("curriculum", curriculum_id, {
            "status": "in_progress",
            "started_at": self._now(),
            "pre_assessment_score": pre_assessment_score,
        })

        return {"started": True, "curriculum_id": curriculum_id}

    def complete_module(
        self,
        curriculum_id: str,
        module_score: float,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Complete a module in the curriculum."""
        curriculum = self._get_node("curriculum", curriculum_id)
        if not curriculum:
            return {"error": "Curriculum not found"}

        completed = curriculum.get("completed_modules", 0) + 1
        current = curriculum.get("current_module", 0) + 1
        total = curriculum.get("total_modules", 1)

        # Update module with score
        modules = curriculum.get("modules", [])
        if current - 1 < len(modules):
            modules[current - 1]["score"] = module_score
            modules[current - 1]["completed_at"] = self._now()
            modules[current - 1]["notes"] = notes

        self._update_node("curriculum", curriculum_id, {
            "completed_modules": completed,
            "current_module": current,
            "modules": modules,
        })

        # Check if curriculum is complete
        if completed >= total:
            return {
                "module_completed": True,
                "curriculum_completed": True,
                "completed_modules": completed,
                "total_modules": total,
            }

        return {
            "module_completed": True,
            "curriculum_completed": False,
            "completed_modules": completed,
            "total_modules": total,
            "next_module": current,
        }

    def complete_curriculum(
        self,
        curriculum_id: str,
        post_assessment_score: float,
        final_notes: str = "",
    ) -> Dict[str, Any]:
        """Complete a curriculum with final assessment."""
        curriculum = self._get_node("curriculum", curriculum_id)
        if not curriculum:
            return {"error": "Curriculum not found"}

        pre_score = curriculum.get("pre_assessment_score")
        improvement = (post_assessment_score - pre_score) if pre_score is not None else None

        self._update_node("curriculum", curriculum_id, {
            "status": "completed",
            "completed_at": self._now(),
            "post_assessment_score": post_assessment_score,
            "final_notes": final_notes,
            "improvement": improvement,
        })

        return {
            "completed": True,
            "curriculum_id": curriculum_id,
            "pre_score": pre_score,
            "post_score": post_assessment_score,
            "improvement": improvement,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get curriculum statistics."""
        curricula = self._find_nodes("curriculum")

        by_status = {}
        by_type = {}
        total_improvement = 0
        improvement_count = 0

        for c in curricula:
            status = c.get("status", "pending")
            by_status[status] = by_status.get(status, 0) + 1

            ctype = c.get("curriculum_type", "unknown")
            by_type[ctype] = by_type.get(ctype, 0) + 1

            if c.get("improvement") is not None:
                total_improvement += c.get("improvement")
                improvement_count += 1

        return {
            "total_curricula": len(curricula),
            "by_status": by_status,
            "by_curriculum_type": by_type,
            "average_improvement": total_improvement / improvement_count if improvement_count else None,
        }


class RetrainingEngine:
    """
    Engine for identifying retraining needs and generating curricula.

    Analyzes:
    - Mistake patterns
    - Experience outcomes
    - Supervision feedback
    - Skill gaps
    - Attention issues

    Generates:
    - Prioritized retraining needs
    - Customized curricula
    - Progress tracking
    """

    def __init__(
        self,
        graph,
        experience_store: ExperienceStore,
        mistake_store: MistakeStore,
        attention_store: AttentionStore,
        supervision_store: SupervisionStore,
        skill_store: SkillStore,
    ):
        self.graph = graph
        self.experience = experience_store
        self.mistake = mistake_store
        self.attention = attention_store
        self.supervision = supervision_store
        self.skill = skill_store

        self.need_store = RetrainingNeedStore(graph)
        self.curriculum_store = CurriculumStore(graph)

    # =========================================================================
    # Need Identification
    # =========================================================================

    def identify_retraining_needs(
        self,
        agent_id: str,
        days: int = 30,
    ) -> Dict[str, Any]:
        """Identify all retraining needs for an agent."""
        needs = []

        # Analyze mistakes
        mistake_needs = self._analyze_mistakes_for_needs(agent_id, days)
        needs.extend(mistake_needs)

        # Analyze experiences
        experience_needs = self._analyze_experiences_for_needs(agent_id, days)
        needs.extend(experience_needs)

        # Analyze supervision
        supervision_needs = self._analyze_supervision_for_needs(agent_id, days)
        needs.extend(supervision_needs)

        # Analyze attention
        attention_needs = self._analyze_attention_for_needs(agent_id)
        needs.extend(attention_needs)

        # Analyze skills
        skill_needs = self._analyze_skills_for_needs(agent_id)
        needs.extend(skill_needs)

        # Deduplicate and merge similar needs
        merged_needs = self._merge_similar_needs(needs)

        # Sort by priority
        priority_order = [p.value for p in RetrainingPriority]
        merged_needs.sort(key=lambda x: priority_order.index(x.get("priority", "medium")))

        # Create need records
        created_needs = []
        for need in merged_needs:
            need_id = self.need_store.create_need(
                agent_id=agent_id,
                skill_area=need["skill_area"],
                specific_issue=need["specific_issue"],
                priority=RetrainingPriority(need["priority"]),
                curriculum_type=CurriculumType(need["curriculum_type"]),
                evidence=need.get("evidence", []),
                recommended_exercises=need.get("exercises", []),
                estimated_duration_hours=need.get("estimated_hours", 1.0),
            )
            created_needs.append({
                "need_id": need_id,
                **need,
            })

        return {
            "agent_id": agent_id,
            "analysis_period_days": days,
            "needs_identified": len(created_needs),
            "needs": created_needs,
        }

    def _analyze_mistakes_for_needs(
        self,
        agent_id: str,
        days: int,
    ) -> List[Dict[str, Any]]:
        """Analyze mistakes to identify retraining needs."""
        needs = []

        # Get mistake patterns
        patterns = self.mistake.get_mistake_patterns(agent_id, min_frequency=2)

        for pattern in patterns:
            severity = "critical" if pattern.get("frequency", 0) >= 5 else "high"

            needs.append({
                "skill_area": pattern.get("category", "general"),
                "specific_issue": f"Recurring mistake pattern: {pattern.get('root_cause', 'unknown')}",
                "priority": severity,
                "curriculum_type": "remedial",
                "evidence": [f"pattern:{pattern.get('id')}"],
                "exercises": self._generate_mistake_exercises(pattern),
                "estimated_hours": 2.0 if severity == "critical" else 1.0,
            })

        # Get recurring mistakes
        recurring = self.mistake.get_recurring_mistakes(agent_id, min_recurrences=2)

        for mistake in recurring[:5]:
            needs.append({
                "skill_area": mistake.get("category", "general"),
                "specific_issue": f"Recurring mistake: {mistake.get('root_cause', 'unknown')}",
                "priority": "high",
                "curriculum_type": "remedial",
                "evidence": [f"mistake:{mistake.get('id')}"],
                "exercises": [{
                    "type": "correction_drill",
                    "description": f"Practice avoiding: {mistake.get('root_cause')}",
                    "correct_approach": mistake.get("expected_action", ""),
                }],
                "estimated_hours": 1.0,
            })

        return needs

    def _analyze_experiences_for_needs(
        self,
        agent_id: str,
        days: int,
    ) -> List[Dict[str, Any]]:
        """Analyze experiences to identify retraining needs."""
        needs = []

        # Get learning trajectory
        trajectory = self.experience.get_learning_trajectory(agent_id, days=days)

        if trajectory.get("error"):
            return needs

        # Check for high failure rate
        success_rate = trajectory.get("success_rate", 1.0)
        if success_rate < 0.7:
            needs.append({
                "skill_area": "task_execution",
                "specific_issue": f"Low success rate ({success_rate:.1%}) over last {days} days",
                "priority": "high" if success_rate < 0.5 else "medium",
                "curriculum_type": "reinforcement",
                "evidence": ["trajectory_analysis"],
                "exercises": [
                    {"type": "replay", "description": "Review successful experiences"},
                    {"type": "analysis", "description": "Identify success factors"},
                ],
                "estimated_hours": 2.0,
            })

        # Check for negative reward trend
        avg_reward = trajectory.get("average_reward", 0)
        if avg_reward < -0.3:
            needs.append({
                "skill_area": "decision_quality",
                "specific_issue": f"Negative average reward ({avg_reward:.2f})",
                "priority": "high",
                "curriculum_type": "reinforcement",
                "evidence": ["reward_analysis"],
                "exercises": [
                    {"type": "decision_review", "description": "Analyze decision patterns"},
                    {"type": "outcome_mapping", "description": "Map decisions to outcomes"},
                ],
                "estimated_hours": 1.5,
            })

        return needs

    def _analyze_supervision_for_needs(
        self,
        agent_id: str,
        days: int,
    ) -> List[Dict[str, Any]]:
        """Analyze supervision to identify retraining needs."""
        needs = []

        # Get supervision summary
        summary = self.supervision.get_supervision_summary(agent_id, days=days)

        if summary.get("total_supervisions", 0) == 0:
            return needs

        # Check rejection rate
        by_outcome = summary.get("by_outcome", {})
        rejected = by_outcome.get("rejected", 0) + by_outcome.get("needs_revision", 0)
        total = summary.get("total_supervisions", 1)
        rejection_rate = rejected / total

        if rejection_rate > 0.3:
            needs.append({
                "skill_area": "quality_standards",
                "specific_issue": f"High rejection rate ({rejection_rate:.1%}) in supervision",
                "priority": "high",
                "curriculum_type": "remedial",
                "evidence": ["supervision_analysis"],
                "exercises": [
                    {"type": "standard_review", "description": "Review quality standards"},
                    {"type": "feedback_integration", "description": "Apply supervisor feedback"},
                ],
                "estimated_hours": 1.5,
            })

        # Check for pending acknowledgments
        pending = self.supervision.get_pending_acknowledgments(agent_id)
        if len(pending) > 3:
            needs.append({
                "skill_area": "feedback_responsiveness",
                "specific_issue": f"{len(pending)} unacknowledged supervision records",
                "priority": "medium",
                "curriculum_type": "compliance",
                "evidence": [f"supervision:{p.get('id')}" for p in pending[:5]],
                "exercises": [
                    {"type": "acknowledgment", "description": "Process pending feedback"},
                ],
                "estimated_hours": 0.5,
            })

        return needs

    def _analyze_attention_for_needs(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Analyze attention patterns to identify retraining needs."""
        needs = []

        # Get frequently missed elements
        frequently_missed = self.attention.get_frequently_missed(agent_id, min_count=3)

        if frequently_missed:
            needs.append({
                "skill_area": "attention_focus",
                "specific_issue": f"Frequently missing {len(frequently_missed)} elements",
                "priority": "medium",
                "curriculum_type": "reinforcement",
                "evidence": [f"missed:{m.get('id')}" for m in frequently_missed[:5]],
                "exercises": [
                    {
                        "type": "attention_drill",
                        "element": m.get("element"),
                        "attention_type": m.get("attention_type"),
                    }
                    for m in frequently_missed[:5]
                ],
                "estimated_hours": 1.0,
            })

        # Get attention quality by type
        quality = self.attention.get_attention_quality_by_type(agent_id)
        for atype, data in quality.get("by_type", {}).items():
            if data.get("avg_quality", 1.0) < 0.5:
                needs.append({
                    "skill_area": f"attention_{atype}",
                    "specific_issue": f"Low attention quality ({data.get('avg_quality', 0):.1%}) for {atype}",
                    "priority": "medium",
                    "curriculum_type": "reinforcement",
                    "evidence": ["attention_quality_analysis"],
                    "exercises": [
                        {"type": "focus_training", "attention_type": atype},
                    ],
                    "estimated_hours": 0.5,
                })

        return needs

    def _analyze_skills_for_needs(
        self,
        agent_id: str,
    ) -> List[Dict[str, Any]]:
        """Analyze skills to identify retraining needs."""
        needs = []

        # Get skills due for practice
        due_skills = self.skill.get_skills_due_for_practice(agent_id, limit=10)

        if len(due_skills) > 5:
            needs.append({
                "skill_area": "skill_maintenance",
                "specific_issue": f"{len(due_skills)} skills overdue for practice",
                "priority": "low",
                "curriculum_type": "reinforcement",
                "evidence": [f"skill:{s.get('id')}" for s in due_skills[:5]],
                "exercises": [
                    {"type": "practice", "skill": s.get("name")}
                    for s in due_skills[:5]
                ],
                "estimated_hours": 1.0,
            })

        # Get weakest skills
        weak_skills = self.skill.get_weakest_skills(agent_id, limit=3)

        for skill in weak_skills:
            if skill.get("proficiency_score", 100) < SKILL_LEVEL_THRESHOLDS[SkillLevel.BEGINNER]:
                needs.append({
                    "skill_area": skill.get("category", "general"),
                    "specific_issue": f"Skill '{skill.get('name')}' needs development",
                    "priority": "medium",
                    "curriculum_type": "expansion",
                    "evidence": [f"skill:{skill.get('id')}"],
                    "exercises": [
                        {"type": "skill_building", "skill": skill.get("name")},
                    ],
                    "estimated_hours": 1.5,
                })

        return needs

    def _merge_similar_needs(
        self,
        needs: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Merge similar needs to avoid duplication."""
        if not needs:
            return []

        merged = {}

        for need in needs:
            key = f"{need['skill_area']}_{need['curriculum_type']}"

            if key in merged:
                # Merge evidence
                existing = merged[key]
                existing["evidence"].extend(need.get("evidence", []))
                existing["exercises"].extend(need.get("exercises", []))
                existing["estimated_hours"] = max(
                    existing["estimated_hours"],
                    need.get("estimated_hours", 1.0)
                )
                # Take higher priority
                priority_order = [p.value for p in RetrainingPriority]
                if priority_order.index(need["priority"]) < priority_order.index(existing["priority"]):
                    existing["priority"] = need["priority"]
            else:
                merged[key] = need

        return list(merged.values())

    def _generate_mistake_exercises(
        self,
        pattern: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Generate exercises for a mistake pattern."""
        exercises = []

        root_cause = pattern.get("root_cause", "")
        category = pattern.get("category", "")

        exercises.append({
            "type": "root_cause_analysis",
            "description": f"Analyze why {root_cause} occurs",
            "pattern": pattern.get("name"),
        })

        exercises.append({
            "type": "prevention_drill",
            "description": f"Practice prevention strategies for {category}",
            "strategies": pattern.get("prevention_strategies", []),
        })

        return exercises

    # =========================================================================
    # Curriculum Generation
    # =========================================================================

    def generate_curriculum(
        self,
        agent_id: str,
        need_id: str,
    ) -> Dict[str, Any]:
        """Generate a curriculum for a specific need."""
        need = self.need_store.get_need(need_id)
        if not need:
            return {"error": "Need not found"}

        curriculum_type = CurriculumType(need.get("curriculum_type", "reinforcement"))

        # Build modules based on curriculum type
        modules = self._build_modules(
            curriculum_type,
            need.get("skill_area", "general"),
            need.get("specific_issue", ""),
            need.get("recommended_exercises", []),
        )

        # Generate objectives
        objectives = self._generate_objectives(
            curriculum_type,
            need.get("skill_area", "general"),
            need.get("specific_issue", ""),
        )

        # Create curriculum
        curriculum_id = self.curriculum_store.create_curriculum(
            agent_id=agent_id,
            curriculum_type=curriculum_type,
            title=f"{curriculum_type.value.capitalize()} Training: {need.get('skill_area')}",
            description=f"Address: {need.get('specific_issue')}",
            objectives=objectives,
            modules=modules,
            based_on_mistakes=self._extract_mistakes(need.get("evidence", [])),
            based_on_experiences=self._extract_experiences(need.get("evidence", [])),
            based_on_supervision=self._extract_supervision(need.get("evidence", [])),
        )

        # Link need to curriculum
        self.need_store._add_edge(
            "retraining_need", need_id,
            "ADDRESSED_BY",
            "curriculum", curriculum_id,
            {}
        )

        return {
            "curriculum_id": curriculum_id,
            "need_id": need_id,
            "title": f"{curriculum_type.value.capitalize()} Training: {need.get('skill_area')}",
            "modules": len(modules),
            "objectives": objectives,
        }

    def _build_modules(
        self,
        curriculum_type: CurriculumType,
        skill_area: str,
        issue: str,
        exercises: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build curriculum modules."""
        modules = []

        # Introduction module
        modules.append({
            "title": "Assessment & Overview",
            "type": "introduction",
            "description": f"Understand the issue: {issue}",
            "activities": [
                {"type": "self_assessment", "description": "Assess current understanding"},
                {"type": "goal_setting", "description": "Set improvement goals"},
            ],
            "estimated_minutes": 15,
            "completed_at": None,
            "score": None,
        })

        # Core training modules from exercises
        for i, exercise in enumerate(exercises[:5]):
            modules.append({
                "title": f"Exercise {i + 1}: {exercise.get('type', 'Practice')}",
                "type": "training",
                "description": exercise.get("description", "Complete exercise"),
                "activities": [exercise],
                "estimated_minutes": 20,
                "completed_at": None,
                "score": None,
            })

        # Reflection module
        if curriculum_type in [CurriculumType.REMEDIAL, CurriculumType.REINFORCEMENT]:
            modules.append({
                "title": "Reflection & Integration",
                "type": "reflection",
                "description": "Reflect on learnings and integrate into practice",
                "activities": [
                    {"type": "reflection", "description": "Document key insights"},
                    {"type": "action_plan", "description": "Create action plan"},
                ],
                "estimated_minutes": 10,
                "completed_at": None,
                "score": None,
            })

        # Assessment module
        modules.append({
            "title": "Final Assessment",
            "type": "assessment",
            "description": f"Assess improvement in {skill_area}",
            "activities": [
                {"type": "knowledge_check", "description": "Test understanding"},
                {"type": "practical_test", "description": "Apply learnings"},
            ],
            "estimated_minutes": 20,
            "completed_at": None,
            "score": None,
        })

        return modules

    def _generate_objectives(
        self,
        curriculum_type: CurriculumType,
        skill_area: str,
        issue: str,
    ) -> List[str]:
        """Generate curriculum objectives."""
        objectives = [
            f"Understand the root causes of issues in {skill_area}",
        ]

        if curriculum_type == CurriculumType.REMEDIAL:
            objectives.extend([
                f"Identify and correct specific mistakes related to: {issue}",
                f"Develop prevention strategies for {skill_area} issues",
            ])
        elif curriculum_type == CurriculumType.REINFORCEMENT:
            objectives.extend([
                f"Strengthen existing capabilities in {skill_area}",
                f"Build confidence through successful practice",
            ])
        elif curriculum_type == CurriculumType.EXPANSION:
            objectives.extend([
                f"Acquire new capabilities in {skill_area}",
                f"Apply new skills in varied contexts",
            ])
        elif curriculum_type == CurriculumType.COMPLIANCE:
            objectives.extend([
                f"Understand compliance requirements for {skill_area}",
                f"Implement compliant practices consistently",
            ])
        elif curriculum_type == CurriculumType.SAFETY:
            objectives.extend([
                f"Recognize safety risks in {skill_area}",
                f"Apply safety protocols consistently",
            ])

        return objectives

    def _extract_mistakes(self, evidence: List[str]) -> List[str]:
        """Extract mistake IDs from evidence."""
        return [e.split(":")[1] for e in evidence if e.startswith("mistake:")]

    def _extract_experiences(self, evidence: List[str]) -> List[str]:
        """Extract experience IDs from evidence."""
        return [e.split(":")[1] for e in evidence if e.startswith("experience:")]

    def _extract_supervision(self, evidence: List[str]) -> List[str]:
        """Extract supervision IDs from evidence."""
        return [e.split(":")[1] for e in evidence if e.startswith("supervision:")]

    # =========================================================================
    # Curriculum Execution
    # =========================================================================

    def start_curriculum(
        self,
        curriculum_id: str,
        pre_assessment_score: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Start a curriculum."""
        return self.curriculum_store.start_curriculum(curriculum_id, pre_assessment_score)

    def complete_module(
        self,
        curriculum_id: str,
        module_score: float,
        notes: str = "",
    ) -> Dict[str, Any]:
        """Complete a module in the curriculum."""
        result = self.curriculum_store.complete_module(curriculum_id, module_score, notes)

        # If curriculum is complete, update related skill
        if result.get("curriculum_completed"):
            curriculum = self.curriculum_store.get_curriculum(curriculum_id)
            if curriculum:
                agent_id = curriculum.get("agent_id")
                # Apply skill improvements based on curriculum
                self._apply_curriculum_to_skills(agent_id, curriculum)

        return result

    def complete_curriculum(
        self,
        curriculum_id: str,
        post_assessment_score: float,
        final_notes: str = "",
    ) -> Dict[str, Any]:
        """Complete a curriculum with final assessment."""
        result = self.curriculum_store.complete_curriculum(
            curriculum_id,
            post_assessment_score,
            final_notes
        )

        # Update related need
        edges = self.need_store._find_edges(
            rel_type="ADDRESSED_BY",
            target_id=curriculum_id,
        )

        for edge in edges:
            need_id = edge.get("source_id")
            self.need_store.complete_retraining(
                need_id,
                effectiveness_score=post_assessment_score,
                completion_notes=final_notes,
            )

        return result

    def _apply_curriculum_to_skills(
        self,
        agent_id: str,
        curriculum: Dict[str, Any],
    ) -> None:
        """Apply curriculum learnings to agent skills."""
        # Get average module score
        modules = curriculum.get("modules", [])
        scores = [m.get("score", 0) for m in modules if m.get("score") is not None]
        avg_score = sum(scores) / len(scores) if scores else 0.5

        # This would link to actual skill improvement
        # For now, record a learning event
        event_id = self.need_store._generate_id("curriculum_learning")
        self.need_store._add_node("curriculum_completion", event_id, {
            "agent_id": agent_id,
            "curriculum_id": curriculum.get("id"),
            "average_score": avg_score,
            "objectives_met": curriculum.get("objectives", []),
        })

    # =========================================================================
    # Progress Tracking
    # =========================================================================

    def get_retraining_progress(
        self,
        agent_id: str,
    ) -> Dict[str, Any]:
        """Get overall retraining progress for an agent."""
        pending_needs = self.need_store.get_pending_needs(agent_id)

        # Get all curricula
        curricula = self.curriculum_store._find_nodes("curriculum", agent_id=agent_id)

        in_progress = [c for c in curricula if c.get("status") == "in_progress"]
        completed = [c for c in curricula if c.get("status") == "completed"]

        # Calculate improvement
        improvements = [c.get("improvement") for c in completed if c.get("improvement") is not None]
        avg_improvement = sum(improvements) / len(improvements) if improvements else None

        return {
            "agent_id": agent_id,
            "pending_needs": len(pending_needs),
            "high_priority_needs": sum(1 for n in pending_needs if n.get("priority") in ["critical", "high"]),
            "curricula_in_progress": len(in_progress),
            "curricula_completed": len(completed),
            "average_improvement": avg_improvement,
            "active_curricula": [
                {
                    "id": c.get("id"),
                    "title": c.get("title"),
                    "progress": f"{c.get('completed_modules', 0)}/{c.get('total_modules', 0)}",
                }
                for c in in_progress
            ],
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get retraining engine statistics."""
        need_stats = self.need_store.get_stats()
        curriculum_stats = self.curriculum_store.get_stats()

        return {
            "needs": need_stats,
            "curricula": curriculum_stats,
        }
