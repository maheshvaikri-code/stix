"""
Goal Store - End-to-end goal tracking and milestone management
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from .base import BaseStore


class GoalStatus(Enum):
    """Goal status values"""
    DRAFT = "draft"
    ACTIVE = "active"
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class MilestoneStatus(Enum):
    """Milestone status values"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"


class GoalStore(BaseStore):
    """
    Manages goal tracking and milestone progress for agents.

    Tracks:
    - Goals with success criteria and acceptance criteria
    - Milestones with progress tracking
    - Goal dependencies and relationships
    - Progress towards comprehensive delivery

    This enables agents to:
    - Define clear end goals with measurable criteria
    - Track progress through milestones
    - Identify risks and blockers to goal completion
    - Verify comprehensive delivery against criteria
    """

    _goal_counter = 0

    def define_goal(
        self,
        name: str,
        description: str,
        success_criteria: List[str],
        acceptance_criteria: Optional[List[str]] = None,
        deadline: Optional[str] = None,
        priority: str = "medium",
        owner: str = "agent",
        parent_goal: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> str:
        """
        Define a new goal with success criteria.

        Args:
            name: Goal name/title
            description: Detailed description of the goal
            success_criteria: List of criteria that define success
            acceptance_criteria: Optional additional acceptance criteria
            deadline: Target completion date
            priority: Goal priority (critical, high, medium, low)
            owner: Who owns this goal
            parent_goal: Parent goal ID for sub-goals
            tags: Optional categorization tags

        Returns:
            Goal ID
        """
        GoalStore._goal_counter += 1
        goal_id = self._make_id("goal", f"{name[:20]}_{GoalStore._goal_counter}")

        self.graph.add_node(
            "goal",
            goal_id,
            name=self._sanitize(name),
            description=self._sanitize(description),
            status=GoalStatus.DRAFT.value,
            priority=priority,
            owner=owner,
            deadline=deadline or "",
            created_at=self._now(),
            started_at="",
            completed_at="",
            parent_goal=parent_goal or "",
            tags=",".join(tags or []),
            progress="0",
            health_score="100",
            notes="",
        )

        # Add success criteria as separate nodes
        for i, criterion in enumerate(success_criteria):
            crit_id = f"{goal_id}_sc_{i}"
            self.graph.add_node(
                "success_criterion",
                crit_id,
                goal_id=goal_id,
                criterion=self._sanitize(criterion),
                met="False",
                evidence="",
                verified_at=""
            )
            self.graph.add_edge(
                "HAS_CRITERION",
                ("goal", goal_id),
                ("success_criterion", crit_id)
            )

        # Add acceptance criteria if provided
        for i, criterion in enumerate(acceptance_criteria or []):
            acc_id = f"{goal_id}_ac_{i}"
            self.graph.add_node(
                "acceptance_criterion",
                acc_id,
                goal_id=goal_id,
                criterion=self._sanitize(criterion),
                met="False",
                evidence="",
                verified_at=""
            )
            self.graph.add_edge(
                "HAS_ACCEPTANCE",
                ("goal", goal_id),
                ("acceptance_criterion", acc_id)
            )

        # Link to parent goal if exists
        if parent_goal and self.graph.has_node("goal", parent_goal):
            self.graph.add_edge(
                "SUBGOAL_OF",
                ("goal", goal_id),
                ("goal", parent_goal)
            )

        return goal_id

    def activate_goal(self, goal_id: str) -> bool:
        """Activate a goal and start tracking"""
        if not self.graph.has_node("goal", goal_id):
            return False

        self.graph.update_node(
            "goal",
            goal_id,
            status=GoalStatus.ACTIVE.value,
            started_at=self._now()
        )
        return True

    def add_milestone(
        self,
        goal_id: str,
        name: str,
        description: str = "",
        target_date: Optional[str] = None,
        order: int = 0,
        deliverables: Optional[List[str]] = None
    ) -> str:
        """
        Add a milestone to a goal.

        Args:
            goal_id: Goal to add milestone to
            name: Milestone name
            description: Milestone description
            target_date: Target completion date
            order: Order in the milestone sequence
            deliverables: List of expected deliverables

        Returns:
            Milestone ID
        """
        mile_id = self._make_id("mile", f"{goal_id[:10]}_{name[:15]}")

        self.graph.add_node(
            "milestone",
            mile_id,
            goal_id=goal_id,
            name=self._sanitize(name),
            description=self._sanitize(description),
            status=MilestoneStatus.PENDING.value,
            target_date=target_date or "",
            order=str(order),
            progress="0",
            started_at="",
            completed_at="",
            deliverables=",".join(deliverables or []),
            notes=""
        )

        if self.graph.has_node("goal", goal_id):
            self.graph.add_edge(
                "HAS_MILESTONE",
                ("goal", goal_id),
                ("milestone", mile_id)
            )

        return mile_id

    def start_milestone(self, milestone_id: str) -> bool:
        """Start working on a milestone"""
        if not self.graph.has_node("milestone", milestone_id):
            return False

        self.graph.update_node(
            "milestone",
            milestone_id,
            status=MilestoneStatus.IN_PROGRESS.value,
            started_at=self._now()
        )

        # Update goal status if this is the first milestone
        milestone = self.graph.get_node("milestone", milestone_id)
        if milestone:
            goal_id = milestone.properties.get("goal_id")
            if goal_id:
                self._update_goal_progress(goal_id)

        return True

    def update_milestone_progress(
        self,
        milestone_id: str,
        progress: int,
        notes: str = ""
    ) -> None:
        """Update milestone progress (0-100)"""
        if self.graph.has_node("milestone", milestone_id):
            update_data = {"progress": str(min(100, max(0, progress)))}
            if notes:
                update_data["notes"] = self._sanitize(notes)

            self.graph.update_node("milestone", milestone_id, **update_data)

            # Update goal progress
            milestone = self.graph.get_node("milestone", milestone_id)
            if milestone:
                goal_id = milestone.properties.get("goal_id")
                if goal_id:
                    self._update_goal_progress(goal_id)

    def complete_milestone(
        self,
        milestone_id: str,
        deliverables_completed: Optional[List[str]] = None,
        notes: str = ""
    ) -> bool:
        """Complete a milestone"""
        if not self.graph.has_node("milestone", milestone_id):
            return False

        self.graph.update_node(
            "milestone",
            milestone_id,
            status=MilestoneStatus.COMPLETED.value,
            completed_at=self._now(),
            progress="100",
            notes=self._sanitize(notes)
        )

        # Update goal progress
        milestone = self.graph.get_node("milestone", milestone_id)
        if milestone:
            goal_id = milestone.properties.get("goal_id")
            if goal_id:
                self._update_goal_progress(goal_id)

        return True

    def meet_criterion(
        self,
        goal_id: str,
        criterion_index: int,
        evidence: str,
        criterion_type: str = "success"
    ) -> bool:
        """
        Mark a success or acceptance criterion as met.

        Args:
            goal_id: Goal ID
            criterion_index: Index of the criterion
            evidence: Evidence that criterion is met
            criterion_type: "success" or "acceptance"

        Returns:
            True if criterion was updated
        """
        prefix = "sc" if criterion_type == "success" else "ac"
        crit_id = f"{goal_id}_{prefix}_{criterion_index}"
        node_type = "success_criterion" if criterion_type == "success" else "acceptance_criterion"

        if not self.graph.has_node(node_type, crit_id):
            return False

        self.graph.update_node(
            node_type,
            crit_id,
            met="True",
            evidence=self._sanitize(evidence),
            verified_at=self._now()
        )

        # Check if goal is now complete
        self._check_goal_completion(goal_id)

        return True

    def _update_goal_progress(self, goal_id: str) -> None:
        """Update goal progress based on milestones"""
        if not self.graph.has_node("goal", goal_id):
            return

        total_progress = 0
        milestone_count = 0

        for edge in self.graph.edges():
            if edge.rel_type == "HAS_MILESTONE" and edge.source == ("goal", goal_id):
                milestone = self.graph.get_node(*edge.target)
                if milestone:
                    milestone_count += 1
                    total_progress += int(milestone.properties.get("progress", 0))

        if milestone_count > 0:
            avg_progress = int(total_progress / milestone_count)
            self.graph.update_node("goal", goal_id, progress=str(avg_progress))

            # Update status based on progress
            goal = self.graph.get_node("goal", goal_id)
            if goal:
                current_status = goal.properties.get("status")
                if current_status not in [GoalStatus.COMPLETED.value, GoalStatus.ABANDONED.value]:
                    if avg_progress >= 100:
                        self._check_goal_completion(goal_id)
                    elif avg_progress > 0:
                        # Check health
                        deadline = goal.properties.get("deadline")
                        if deadline and deadline < self._now() and avg_progress < 100:
                            self.graph.update_node("goal", goal_id, status=GoalStatus.AT_RISK.value)
                        else:
                            self.graph.update_node("goal", goal_id, status=GoalStatus.ON_TRACK.value)

    def _check_goal_completion(self, goal_id: str) -> bool:
        """Check if a goal meets all its criteria"""
        if not self.graph.has_node("goal", goal_id):
            return False

        # Check all success criteria
        all_met = True
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_CRITERION" and edge.source == ("goal", goal_id):
                criterion = self.graph.get_node(*edge.target)
                if criterion and criterion.properties.get("met") != "True":
                    all_met = False
                    break

        # Check acceptance criteria
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_ACCEPTANCE" and edge.source == ("goal", goal_id):
                criterion = self.graph.get_node(*edge.target)
                if criterion and criterion.properties.get("met") != "True":
                    all_met = False
                    break

        if all_met:
            self.graph.update_node(
                "goal",
                goal_id,
                status=GoalStatus.COMPLETED.value,
                completed_at=self._now(),
                progress="100"
            )
            return True

        return False

    def complete_goal(
        self,
        goal_id: str,
        completion_notes: str = "",
        force: bool = False
    ) -> Dict[str, Any]:
        """
        Attempt to complete a goal.

        Args:
            goal_id: Goal to complete
            completion_notes: Notes about completion
            force: Complete even if criteria not met

        Returns:
            Completion status with any unmet criteria
        """
        if not self.graph.has_node("goal", goal_id):
            return {"success": False, "reason": "Goal not found"}

        # Check criteria
        unmet_criteria = []
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_CRITERION" and edge.source == ("goal", goal_id):
                criterion = self.graph.get_node(*edge.target)
                if criterion and criterion.properties.get("met") != "True":
                    unmet_criteria.append({
                        "type": "success_criterion",
                        "criterion": criterion.properties.get("criterion")
                    })

        for edge in self.graph.edges():
            if edge.rel_type == "HAS_ACCEPTANCE" and edge.source == ("goal", goal_id):
                criterion = self.graph.get_node(*edge.target)
                if criterion and criterion.properties.get("met") != "True":
                    unmet_criteria.append({
                        "type": "acceptance_criterion",
                        "criterion": criterion.properties.get("criterion")
                    })

        if unmet_criteria and not force:
            return {
                "success": False,
                "reason": "Not all criteria met",
                "unmet_criteria": unmet_criteria
            }

        self.graph.update_node(
            "goal",
            goal_id,
            status=GoalStatus.COMPLETED.value,
            completed_at=self._now(),
            progress="100",
            notes=self._sanitize(completion_notes)
        )

        return {
            "success": True,
            "completed_at": self._now(),
            "forced": force and len(unmet_criteria) > 0,
            "unmet_criteria": unmet_criteria if force else []
        }

    def block_goal(self, goal_id: str, reason: str, blocked_by: Optional[str] = None) -> None:
        """Mark a goal as blocked"""
        if self.graph.has_node("goal", goal_id):
            self.graph.update_node(
                "goal",
                goal_id,
                status=GoalStatus.BLOCKED.value,
                notes=f"Blocked: {self._sanitize(reason)}"
            )

            if blocked_by:
                self.graph.add_edge(
                    "BLOCKED_BY",
                    ("goal", goal_id),
                    ("blocker", blocked_by),
                    reason=self._sanitize(reason),
                    blocked_at=self._now()
                )

    def add_risk(
        self,
        goal_id: str,
        risk_description: str,
        severity: str = "medium",
        mitigation: str = ""
    ) -> str:
        """Add a risk to a goal"""
        risk_id = self._make_id("risk", f"{goal_id[:10]}_{risk_description[:15]}")

        self.graph.add_node(
            "goal_risk",
            risk_id,
            goal_id=goal_id,
            description=self._sanitize(risk_description),
            severity=severity,
            mitigation=self._sanitize(mitigation),
            status="active",
            identified_at=self._now(),
            resolved_at=""
        )

        if self.graph.has_node("goal", goal_id):
            self.graph.add_edge(
                "HAS_RISK",
                ("goal", goal_id),
                ("goal_risk", risk_id)
            )

        # Update goal health
        self._update_goal_health(goal_id)

        return risk_id

    def resolve_risk(self, risk_id: str, resolution: str) -> None:
        """Resolve a goal risk"""
        if self.graph.has_node("goal_risk", risk_id):
            risk = self.graph.get_node("goal_risk", risk_id)
            self.graph.update_node(
                "goal_risk",
                risk_id,
                status="resolved",
                resolved_at=self._now(),
                mitigation=self._sanitize(resolution)
            )

            if risk:
                goal_id = risk.properties.get("goal_id")
                if goal_id:
                    self._update_goal_health(goal_id)

    def _update_goal_health(self, goal_id: str) -> None:
        """Update goal health score based on risks"""
        if not self.graph.has_node("goal", goal_id):
            return

        health = 100
        severity_impact = {"critical": 30, "high": 20, "medium": 10, "low": 5}

        for edge in self.graph.edges():
            if edge.rel_type == "HAS_RISK" and edge.source == ("goal", goal_id):
                risk = self.graph.get_node(*edge.target)
                if risk and risk.properties.get("status") == "active":
                    severity = risk.properties.get("severity", "medium")
                    health -= severity_impact.get(severity, 10)

        health = max(0, health)
        self.graph.update_node("goal", goal_id, health_score=str(health))

        # Update status based on health
        goal = self.graph.get_node("goal", goal_id)
        if goal:
            status = goal.properties.get("status")
            if status not in [GoalStatus.COMPLETED.value, GoalStatus.ABANDONED.value, GoalStatus.BLOCKED.value]:
                if health < 50:
                    self.graph.update_node("goal", goal_id, status=GoalStatus.AT_RISK.value)

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_goal(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get a goal with all its details"""
        if not self.graph.has_node("goal", goal_id):
            return None

        goal = self.graph.get_node("goal", goal_id)
        if not goal:
            return None

        result = {
            "id": goal_id,
            **goal.properties,
            "success_criteria": [],
            "acceptance_criteria": [],
            "milestones": [],
            "risks": [],
            "subgoals": []
        }

        # Get success criteria
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_CRITERION" and edge.source == ("goal", goal_id):
                criterion = self.graph.get_node(*edge.target)
                if criterion:
                    result["success_criteria"].append(criterion.properties)

        # Get acceptance criteria
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_ACCEPTANCE" and edge.source == ("goal", goal_id):
                criterion = self.graph.get_node(*edge.target)
                if criterion:
                    result["acceptance_criteria"].append(criterion.properties)

        # Get milestones
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_MILESTONE" and edge.source == ("goal", goal_id):
                milestone = self.graph.get_node(*edge.target)
                if milestone:
                    result["milestones"].append({
                        "id": milestone.id,
                        **milestone.properties
                    })

        # Sort milestones by order
        result["milestones"].sort(key=lambda x: int(x.get("order", 0)))

        # Get risks
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_RISK" and edge.source == ("goal", goal_id):
                risk = self.graph.get_node(*edge.target)
                if risk:
                    result["risks"].append(risk.properties)

        # Get subgoals
        for edge in self.graph.edges():
            if edge.rel_type == "SUBGOAL_OF" and edge.target == ("goal", goal_id):
                subgoal = self.graph.get_node(*edge.source)
                if subgoal:
                    result["subgoals"].append({
                        "id": subgoal.id,
                        **subgoal.properties
                    })

        return result

    def get_active_goals(self) -> List[Dict[str, Any]]:
        """Get all active goals"""
        active_statuses = [
            GoalStatus.ACTIVE.value,
            GoalStatus.ON_TRACK.value,
            GoalStatus.AT_RISK.value
        ]

        goals = []
        for node in self.graph.nodes():
            if node.type == "goal" and node.properties.get("status") in active_statuses:
                goals.append({"id": node.id, **node.properties})

        return goals

    def get_at_risk_goals(self) -> List[Dict[str, Any]]:
        """Get goals that are at risk"""
        goals = []
        for node in self.graph.nodes():
            if node.type == "goal" and node.properties.get("status") == GoalStatus.AT_RISK.value:
                goals.append(self.get_goal(node.id))

        return [g for g in goals if g]

    def get_blocked_goals(self) -> List[Dict[str, Any]]:
        """Get blocked goals"""
        goals = []
        for node in self.graph.nodes():
            if node.type == "goal" and node.properties.get("status") == GoalStatus.BLOCKED.value:
                goals.append({"id": node.id, **node.properties})

        return goals

    def get_completed_goals(self) -> List[Dict[str, Any]]:
        """Get completed goals"""
        goals = []
        for node in self.graph.nodes():
            if node.type == "goal" and node.properties.get("status") == GoalStatus.COMPLETED.value:
                goals.append({"id": node.id, **node.properties})

        goals.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
        return goals

    def get_goal_progress_report(self, goal_id: str) -> Dict[str, Any]:
        """Get a detailed progress report for a goal"""
        goal = self.get_goal(goal_id)
        if not goal:
            return {"error": "Goal not found"}

        # Calculate criteria met
        criteria_met = sum(1 for c in goal["success_criteria"] if c.get("met") == "True")
        criteria_total = len(goal["success_criteria"])

        acceptance_met = sum(1 for c in goal["acceptance_criteria"] if c.get("met") == "True")
        acceptance_total = len(goal["acceptance_criteria"])

        # Calculate milestone progress
        milestones_complete = sum(
            1 for m in goal["milestones"]
            if m.get("status") == MilestoneStatus.COMPLETED.value
        )
        milestones_total = len(goal["milestones"])

        # Active risks
        active_risks = [r for r in goal["risks"] if r.get("status") == "active"]

        return {
            "goal_id": goal_id,
            "name": goal.get("name"),
            "status": goal.get("status"),
            "overall_progress": int(goal.get("progress", 0)),
            "health_score": int(goal.get("health_score", 100)),
            "criteria": {
                "success": {"met": criteria_met, "total": criteria_total},
                "acceptance": {"met": acceptance_met, "total": acceptance_total}
            },
            "milestones": {
                "completed": milestones_complete,
                "total": milestones_total,
                "current": next(
                    (m for m in goal["milestones"]
                     if m.get("status") == MilestoneStatus.IN_PROGRESS.value),
                    None
                )
            },
            "risks": {
                "active": len(active_risks),
                "critical": sum(1 for r in active_risks if r.get("severity") == "critical")
            },
            "ready_for_completion": criteria_met == criteria_total and acceptance_met == acceptance_total
        }

    def verify_delivery(self, goal_id: str) -> Dict[str, Any]:
        """
        Verify if a goal has been comprehensively delivered.

        Returns detailed verification of all criteria and deliverables.
        """
        goal = self.get_goal(goal_id)
        if not goal:
            return {"verified": False, "reason": "Goal not found"}

        verification = {
            "verified": True,
            "goal_id": goal_id,
            "goal_name": goal.get("name"),
            "success_criteria": [],
            "acceptance_criteria": [],
            "milestones": [],
            "issues": []
        }

        # Verify success criteria
        for criterion in goal["success_criteria"]:
            status = {
                "criterion": criterion.get("criterion"),
                "met": criterion.get("met") == "True",
                "evidence": criterion.get("evidence", "")
            }
            verification["success_criteria"].append(status)
            if not status["met"]:
                verification["verified"] = False
                verification["issues"].append(f"Success criterion not met: {criterion.get('criterion')}")

        # Verify acceptance criteria
        for criterion in goal["acceptance_criteria"]:
            status = {
                "criterion": criterion.get("criterion"),
                "met": criterion.get("met") == "True",
                "evidence": criterion.get("evidence", "")
            }
            verification["acceptance_criteria"].append(status)
            if not status["met"]:
                verification["verified"] = False
                verification["issues"].append(f"Acceptance criterion not met: {criterion.get('criterion')}")

        # Verify milestones
        for milestone in goal["milestones"]:
            status = {
                "name": milestone.get("name"),
                "completed": milestone.get("status") == MilestoneStatus.COMPLETED.value,
                "progress": int(milestone.get("progress", 0))
            }
            verification["milestones"].append(status)
            if not status["completed"] and milestone.get("status") != MilestoneStatus.SKIPPED.value:
                verification["verified"] = False
                verification["issues"].append(f"Milestone not completed: {milestone.get('name')}")

        # Check for active risks
        active_risks = [r for r in goal["risks"] if r.get("status") == "active"]
        if active_risks:
            verification["issues"].append(f"{len(active_risks)} active risk(s) remaining")
            # Critical risks prevent verification
            if any(r.get("severity") == "critical" for r in active_risks):
                verification["verified"] = False

        return verification

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant goal info for context"""
        results = []

        # Add active goals
        active = self.get_active_goals()
        if active:
            results.append({
                "type": "active_goals",
                "goals": active[:5]
            })

        # Add at-risk goals
        at_risk = self.get_at_risk_goals()
        if at_risk:
            results.append({
                "type": "at_risk_goals",
                "goals": at_risk[:3]
            })

        # Add blocked goals
        blocked = self.get_blocked_goals()
        if blocked:
            results.append({
                "type": "blocked_goals",
                "goals": blocked[:3]
            })

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get goal store statistics"""
        stats = {
            "total_goals": 0,
            "by_status": {s.value: 0 for s in GoalStatus},
            "total_milestones": 0,
            "milestones_completed": 0,
            "avg_health_score": 0.0,
            "criteria_met_rate": 0.0
        }

        total_health = 0
        total_criteria = 0
        met_criteria = 0

        for node in self.graph.nodes():
            if node.type == "goal":
                stats["total_goals"] += 1
                status = node.properties.get("status", GoalStatus.DRAFT.value)
                if status in stats["by_status"]:
                    stats["by_status"][status] += 1
                try:
                    health = int(node.properties.get("health_score", 100))
                except (ValueError, TypeError):
                    health = 100
                total_health += health

            elif node.type == "milestone":
                stats["total_milestones"] += 1
                if node.properties.get("status") == MilestoneStatus.COMPLETED.value:
                    stats["milestones_completed"] += 1

            elif node.type == "success_criterion":
                total_criteria += 1
                if node.properties.get("met") == "True":
                    met_criteria += 1

        if stats["total_goals"] > 0:
            stats["avg_health_score"] = round(total_health / stats["total_goals"], 1)

        if total_criteria > 0:
            stats["criteria_met_rate"] = round(met_criteria / total_criteria, 2)

        return stats
