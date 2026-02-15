"""
Skill Store - Agent skill progression and learning
"""

from typing import Any, Dict, List, Optional
from .base import BaseStore


class SkillStore(BaseStore):
    """
    Manages agent skill memory.

    Tracks:
    - Skill proficiency levels
    - Learning events
    - Skill application history
    - Milestone achievements
    """

    def add_skill(
        self,
        name: str,
        category: str,
        proficiency: float = 0.0,
        examples_seen: int = 0
    ) -> str:
        """Add a skill"""
        skill_id = self._make_id("skill", name)

        self.graph.add_node(
            "skill",
            skill_id,
            name=name,
            category=category,
            proficiency=str(proficiency),
            examples_seen=str(examples_seen),
            last_practiced=self._now(),
        )

        return skill_id

    def update_proficiency(
        self,
        skill_name: str,
        new_proficiency: float,
        examples_added: int = 0
    ) -> None:
        """Update skill proficiency"""
        skill_id = self._make_id("skill", skill_name)

        if self.graph.has_node("skill", skill_id):
            node = self.graph.get_node("skill", skill_id)
            if node:
                current_examples = int(node.properties.get("examples_seen", 0))
                self.graph.update_node(
                    "skill",
                    skill_id,
                    proficiency=str(new_proficiency),
                    examples_seen=str(current_examples + examples_added),
                    last_practiced=self._now()
                )

    _event_counter = 0

    def record_learning_event(
        self,
        skill_name: str,
        event_type: str,
        context: str,
        lesson: Optional[str] = None
    ) -> str:
        """Record a learning event"""
        SkillStore._event_counter += 1
        skill_id = self._make_id("skill", skill_name)
        event_id = self._make_id("le", f"{skill_name}_{SkillStore._event_counter}")

        self.graph.add_node(
            "learning_event",
            event_id,
            skill_id=skill_id,
            event_type=event_type,
            context=self._sanitize(context),
            lesson=self._sanitize(lesson or ""),
            when=self._now(),
        )

        if self.graph.has_node("skill", skill_id):
            self.graph.add_edge(
                "LEARNED_IN",
                ("skill", skill_id),
                ("learning_event", event_id)
            )

        return event_id

    def record_skill_application(
        self,
        skill_name: str,
        session_id: str,
        success: bool,
        notes: str = ""
    ) -> None:
        """Record skill being applied in a session"""
        skill_id = self._make_id("skill", skill_name)

        if self.graph.has_node("skill", skill_id) and self.graph.has_node("session", session_id):
            self.graph.add_edge(
                "SKILL_APPLIED",
                ("skill", skill_id),
                ("session", session_id),
                success=str(success),
                notes=self._sanitize(notes),
                when=self._now()
            )

    def add_milestone(
        self,
        skill_name: str,
        milestone: str,
        proficiency_required: float
    ) -> str:
        """Add a skill milestone"""
        skill_id = self._make_id("skill", skill_name)
        mile_id = self._make_id("mile", f"{skill_name}_{milestone[:20]}")

        self.graph.add_node(
            "milestone",
            mile_id,
            skill_id=skill_id,
            milestone=milestone,
            proficiency_required=str(proficiency_required),
            achieved="False",
            achieved_at="",
        )

        if self.graph.has_node("skill", skill_id):
            self.graph.add_edge(
                "HAS_MILESTONE",
                ("skill", skill_id),
                ("milestone", mile_id)
            )

        return mile_id

    def achieve_milestone(self, skill_name: str, milestone: str) -> None:
        """Mark a milestone as achieved"""
        mile_id = self._make_id("mile", f"{skill_name}_{milestone[:20]}")

        if self.graph.has_node("milestone", mile_id):
            self.graph.update_node(
                "milestone",
                mile_id,
                achieved="True",
                achieved_at=self._now()
            )

    def get_skill(self, name: str) -> Optional[Dict[str, Any]]:
        """Get skill with milestones and recent events"""
        skill_id = self._make_id("skill", name)

        if not self.graph.has_node("skill", skill_id):
            return None

        node = self.graph.get_node("skill", skill_id)
        if not node:
            return None

        result = {
            "skill": node.properties,
            "milestones": [],
            "recent_events": [],
        }

        # Get milestones
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_MILESTONE" and edge.source == ("skill", skill_id):
                mile = self.graph.get_node(*edge.target)
                if mile:
                    result["milestones"].append(mile.properties)

        # Get recent learning events
        for edge in self.graph.edges():
            if edge.rel_type == "LEARNED_IN" and edge.source == ("skill", skill_id):
                event = self.graph.get_node(*edge.target)
                if event:
                    result["recent_events"].append(event.properties)

        # Sort events by time (most recent first)
        result["recent_events"].sort(
            key=lambda x: x.get("when", ""),
            reverse=True
        )
        result["recent_events"] = result["recent_events"][:5]  # Keep 5 most recent

        return result

    def get_proficient_skills(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Get skills above proficiency threshold"""
        skills = []

        for node in self.graph.nodes():
            if node.type == "skill":
                proficiency = float(node.properties.get("proficiency", 0))
                if proficiency >= threshold:
                    skills.append(node.properties)

        return sorted(skills, key=lambda x: float(x.get("proficiency", 0)), reverse=True)

    def get_skills_needing_practice(self, threshold: float = 0.5) -> List[Dict[str, Any]]:
        """Get skills below threshold that need practice"""
        skills = []

        for node in self.graph.nodes():
            if node.type == "skill":
                proficiency = float(node.properties.get("proficiency", 0))
                if proficiency < threshold:
                    skills.append(node.properties)

        return sorted(skills, key=lambda x: float(x.get("proficiency", 0)))

    def get_skills_by_category(self, category: str) -> List[Dict[str, Any]]:
        """Get skills in a category"""
        return [
            node.properties
            for node in self.graph.nodes()
            if node.type == "skill" and node.properties.get("category") == category
        ]

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant skill info for context"""
        results = []

        # Get proficient skills
        proficient = self.get_proficient_skills()
        if proficient:
            results.append({
                "type": "proficient_skills",
                "skills": proficient[:5]  # Top 5
            })

        # Get skills needing practice relevant to task
        task = context.get("task", "")
        if task:
            task_lower = task.lower()
            for node in self.graph.nodes():
                if node.type == "skill":
                    name = node.properties.get("name", "").lower()
                    if name in task_lower or any(kw in task_lower for kw in name.split("_")):
                        proficiency = float(node.properties.get("proficiency", 0))
                        if proficiency < 0.7:
                            results.append({
                                "type": "skill_needs_practice",
                                "skill": node.properties
                            })

        return results

    def get_stats(self) -> Dict[str, int]:
        """Get skill store statistics"""
        skills = 0
        events = 0
        milestones = 0
        achieved = 0
        avg_proficiency = 0.0
        total_prof = 0.0

        for node in self.graph.nodes():
            if node.type == "skill":
                skills += 1
                total_prof += float(node.properties.get("proficiency", 0))
            elif node.type == "learning_event":
                events += 1
            elif node.type == "milestone":
                milestones += 1
                if node.properties.get("achieved") == "True":
                    achieved += 1

        if skills > 0:
            avg_proficiency = total_prof / skills

        return {
            "skills": skills,
            "learning_events": events,
            "milestones": milestones,
            "milestones_achieved": achieved,
            "avg_proficiency": round(avg_proficiency, 2),
        }
