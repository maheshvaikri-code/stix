"""
Governed Agent Memory - Integrated solution combining agent-memory with agent-governance

This module provides a comprehensive system that combines:
- Agent Memory: Task/goal/issue tracking, learning, session management
- Agent Governance: Policy enforcement, audit trails, compliance, rollback

Together they enable agents to:
1. Track issues and problems encountered
2. Maintain structured todo lists
3. Define and track progress towards goals
4. Apply governance policies to all actions
5. Audit all decisions and actions
6. Rollback failed operations
7. Learn from past experiences
"""

from typing import Any, Dict, List, Optional
from enum import Enum

from ison_graph import ISONGraph

# Import from agent-memory
from .memory import AgentMemory
from .stores import (
    TodoStore, TaskStatus, TaskPriority,
    GoalStore, GoalStatus, MilestoneStatus,
    IssueStore, IssueStatus, IssueSeverity, IssueType
)

# Try to import agent-governance (optional dependency)
try:
    from agent_governance import (
        GovernanceEngine,
        AuthorityLevel,
        RiskLevel,
        EscalationLevel,
        IncidentSeverity,
        RollbackType,
        RollbackTrigger,
    )
    GOVERNANCE_AVAILABLE = True
except ImportError:
    GOVERNANCE_AVAILABLE = False
    GovernanceEngine = None


class GovernedAgentMemory:
    """
    Integrated system combining Agent Memory with Agent Governance.

    This provides a unified interface for:
    - Task management with governance checks
    - Goal tracking with compliance verification
    - Issue tracking with incident management
    - Session continuity with audit trails
    - Skill progression with capability checks

    Usage:
        from agent_memory import GovernedAgentMemory

        # Initialize with both memory and governance
        agent = GovernedAgentMemory("my-project")

        # Define a goal with governance
        goal_id = agent.create_governed_goal(
            name="Implement user authentication",
            success_criteria=["Login works", "Logout works", "Session management"],
            compliance_frameworks=["SOC2", "GDPR"]
        )

        # Add tasks that contribute to the goal
        task_id = agent.add_governed_task(
            title="Implement login endpoint",
            goal_id=goal_id,
            requires_approval=False
        )

        # Track issues with automatic incident creation
        issue_id = agent.report_issue(
            title="Login fails on mobile",
            severity=IssueSeverity.HIGH,
            auto_escalate=True
        )

        # Complete work with governance verification
        result = agent.complete_task_with_verification(task_id)
    """

    def __init__(
        self,
        name: str,
        enable_governance: bool = True,
        governance_config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize Governed Agent Memory.

        Args:
            name: Project/agent name
            enable_governance: Whether to enable governance features
            governance_config: Optional governance configuration
        """
        self.name = name
        self.governance_enabled = enable_governance and GOVERNANCE_AVAILABLE

        # Initialize memory system
        self.memory = AgentMemory(name)

        # Initialize governance if available and enabled
        self.governance = None
        if self.governance_enabled:
            self.governance = GovernanceEngine(name)
            self._setup_governance(governance_config or {})

        # Current session tracking
        self._current_session_id = None
        self._current_goal_id = None

    def _setup_governance(self, config: Dict[str, Any]) -> None:
        """Setup default governance policies"""
        if not self.governance:
            return

        # Register the agent
        self.governance.register_agent(
            agent_id="self",
            name=self.name,
            authority_level=AuthorityLevel.LIMITED,
            capabilities=["read", "write", "execute"]
        )

        # Add default policies
        self.governance.add_policy(
            name="task_policy",
            rules=[
                {
                    "condition": "action == 'complete_task' and task_status != 'in_progress'",
                    "action": "deny",
                    "description": "Cannot complete task that is not in progress"
                },
                {
                    "condition": "action == 'complete_goal' and criteria_met < criteria_total",
                    "action": "escalate",
                    "description": "Goal completion with unmet criteria requires approval"
                }
            ]
        )

        self.governance.add_policy(
            name="issue_policy",
            rules=[
                {
                    "condition": "severity == 'critical' and auto_escalate == True",
                    "action": "escalate",
                    "description": "Critical issues auto-escalate"
                }
            ]
        )

    # =========================================================================
    # Session Management
    # =========================================================================

    def start_session(self, task_description: str) -> str:
        """Start a new working session"""
        session_id = self.memory.start_session(task_description)
        self._current_session_id = session_id

        if self.governance:
            # Record in audit
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="session_start",
                outcome="started",
                confidence=1.0,
                metadata={"session_id": session_id, "task": task_description}
            )

        return session_id

    def end_session(self, completion: float = 1.0, notes: str = "") -> Dict[str, Any]:
        """End the current session with summary"""
        if not self._current_session_id:
            return {"error": "No active session"}

        session_id = self._current_session_id

        # Get session summary before ending
        summary = self.get_session_summary()

        # End the session
        self.memory.end_session(session_id, completion)

        if self.governance:
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="session_end",
                outcome="completed" if completion >= 1.0 else "partial",
                confidence=completion,
                metadata={"session_id": session_id, "summary": summary, "notes": notes}
            )

        self._current_session_id = None
        return summary

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session"""
        if not self._current_session_id:
            return {}

        # Get task progress
        tasks = self.memory.todos.get_tasks_by_session(self._current_session_id)
        completed = [t for t in tasks if t.get("status") == TaskStatus.COMPLETED.value]
        in_progress = [t for t in tasks if t.get("status") == TaskStatus.IN_PROGRESS.value]
        blocked = [t for t in tasks if t.get("status") == TaskStatus.BLOCKED.value]

        # Get issues
        issues_created = [
            n for n in self.memory.graph.nodes()
            if n.type == "issue" and n.properties.get("session_id") == self._current_session_id
        ]
        issues_resolved = [i for i in issues_created if i.properties.get("status") == IssueStatus.RESOLVED.value]

        return {
            "session_id": self._current_session_id,
            "tasks": {
                "total": len(tasks),
                "completed": len(completed),
                "in_progress": len(in_progress),
                "blocked": len(blocked)
            },
            "issues": {
                "created": len(issues_created),
                "resolved": len(issues_resolved)
            },
            "completion_rate": len(completed) / len(tasks) if tasks else 0
        }

    # =========================================================================
    # Goal Management with Governance
    # =========================================================================

    def create_governed_goal(
        self,
        name: str,
        description: str,
        success_criteria: List[str],
        acceptance_criteria: Optional[List[str]] = None,
        deadline: Optional[str] = None,
        compliance_frameworks: Optional[List[str]] = None,
        requires_approval: bool = False
    ) -> str:
        """
        Create a goal with governance tracking.

        Args:
            name: Goal name
            description: Goal description
            success_criteria: Criteria that define success
            acceptance_criteria: Additional acceptance criteria
            deadline: Target deadline
            compliance_frameworks: Compliance frameworks to track
            requires_approval: Whether goal completion requires approval

        Returns:
            Goal ID
        """
        # Create goal in memory
        goal_id = self.memory.goals.define_goal(
            name=name,
            description=description,
            success_criteria=success_criteria,
            acceptance_criteria=acceptance_criteria,
            deadline=deadline,
            tags=compliance_frameworks
        )

        self._current_goal_id = goal_id

        if self.governance:
            # Record in audit
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="goal_created",
                outcome="created",
                confidence=1.0,
                metadata={
                    "goal_id": goal_id,
                    "name": name,
                    "criteria_count": len(success_criteria),
                    "compliance": compliance_frameworks or []
                }
            )

            # Add compliance tracking if frameworks specified
            if compliance_frameworks:
                for framework in compliance_frameworks:
                    self.governance.compliance.map_behavior_to_framework(
                        goal_id, framework
                    )

        return goal_id

    def activate_goal(self, goal_id: str) -> bool:
        """Activate a goal and start tracking"""
        success = self.memory.goals.activate_goal(goal_id)

        if success and self.governance:
            # Start transaction for rollback support
            self.governance.begin_transaction(
                name=f"Goal: {goal_id}",
                agent_id="self",
                action_type="goal_execution"
            )

        return success

    def add_milestone_to_goal(
        self,
        goal_id: str,
        name: str,
        description: str = "",
        target_date: Optional[str] = None,
        deliverables: Optional[List[str]] = None
    ) -> str:
        """Add a milestone to a goal"""
        milestone_id = self.memory.goals.add_milestone(
            goal_id=goal_id,
            name=name,
            description=description,
            target_date=target_date,
            deliverables=deliverables
        )

        if self.governance:
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="milestone_added",
                outcome="created",
                confidence=1.0,
                metadata={"goal_id": goal_id, "milestone_id": milestone_id, "name": name}
            )

        return milestone_id

    def complete_goal_with_verification(self, goal_id: str) -> Dict[str, Any]:
        """
        Attempt to complete a goal with full verification.

        Verifies all criteria are met and applies governance checks.
        """
        # First verify delivery
        verification = self.memory.goals.verify_delivery(goal_id)

        if not verification.get("verified"):
            if self.governance:
                # Check if we can escalate for approval
                check = self.governance.check_action(
                    agent_id="self",
                    action="complete_goal",
                    context={
                        "goal_id": goal_id,
                        "criteria_met": len([c for c in verification.get("success_criteria", []) if c.get("met")]),
                        "criteria_total": len(verification.get("success_criteria", [])),
                        "issues": verification.get("issues", [])
                    }
                )

                if check.get("escalation_required"):
                    return {
                        "status": "pending_approval",
                        "verification": verification,
                        "escalation": check.get("escalation_level")
                    }

            return {
                "status": "not_verified",
                "verification": verification
            }

        # Complete the goal
        result = self.memory.goals.complete_goal(goal_id)

        if self.governance and result.get("success"):
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="goal_completed",
                outcome="success",
                confidence=1.0,
                metadata={"goal_id": goal_id, "verification": verification}
            )

        return {
            "status": "completed" if result.get("success") else "failed",
            "verification": verification,
            "result": result
        }

    # =========================================================================
    # Task Management with Governance
    # =========================================================================

    def add_governed_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        goal_id: Optional[str] = None,
        requires_approval: bool = False,
        dependencies: Optional[List[str]] = None
    ) -> str:
        """
        Add a task with governance tracking.

        Args:
            title: Task title
            description: Task description
            priority: Task priority
            goal_id: Goal this task contributes to
            requires_approval: Whether task completion requires approval
            dependencies: Task IDs this task depends on

        Returns:
            Task ID
        """
        task_id = self.memory.todos.add_task(
            title=title,
            description=description,
            priority=priority,
            session_id=self._current_session_id,
            goal_id=goal_id or self._current_goal_id
        )

        # Add dependencies
        if dependencies:
            for dep_id in dependencies:
                self.memory.todos.add_dependency(task_id, dep_id)

        if self.governance:
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="task_created",
                outcome="created",
                confidence=1.0,
                metadata={
                    "task_id": task_id,
                    "title": title,
                    "priority": priority.value if isinstance(priority, TaskPriority) else priority,
                    "goal_id": goal_id,
                    "requires_approval": requires_approval
                }
            )

        return task_id

    def start_task(self, task_id: str) -> Dict[str, Any]:
        """Start working on a task with governance check"""
        task = self.memory.todos.get_task(task_id)
        if not task:
            return {"success": False, "reason": "Task not found"}

        # Check dependencies
        unmet_deps = []
        for dep in task.get("dependencies", []):
            if dep.get("status") != TaskStatus.COMPLETED.value:
                unmet_deps.append(dep)

        if unmet_deps:
            return {
                "success": False,
                "reason": "Unmet dependencies",
                "dependencies": unmet_deps
            }

        # Governance check
        if self.governance:
            check = self.governance.check_action(
                agent_id="self",
                action="start_task",
                context={"task_id": task_id, "task": task}
            )

            if not check.get("permitted"):
                return {
                    "success": False,
                    "reason": check.get("reason"),
                    "governance_check": check
                }

            # Create snapshot for rollback
            self.governance.create_snapshot(
                action_id=task_id,
                action_type="task_start",
                agent_id="self",
                state_before=task
            )

        success = self.memory.todos.start_task(task_id)
        return {"success": success, "task_id": task_id}

    def complete_task_with_verification(
        self,
        task_id: str,
        actual_effort: str = "",
        notes: str = ""
    ) -> Dict[str, Any]:
        """Complete a task with governance verification"""
        task = self.memory.todos.get_task(task_id)
        if not task:
            return {"success": False, "reason": "Task not found"}

        # Check task status
        if task.get("status") != TaskStatus.IN_PROGRESS.value:
            return {
                "success": False,
                "reason": f"Task is {task.get('status')}, not in_progress"
            }

        # Governance check
        if self.governance:
            check = self.governance.check_action(
                agent_id="self",
                action="complete_task",
                context={
                    "task_id": task_id,
                    "task_status": task.get("status"),
                    "progress": int(task.get("progress", 0))
                }
            )

            if not check.get("permitted"):
                if check.get("escalation_required"):
                    return {
                        "success": False,
                        "status": "pending_approval",
                        "escalation": check.get("escalation_level")
                    }
                return {
                    "success": False,
                    "reason": check.get("reason")
                }

            # Record in audit
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="task_completed",
                outcome="success",
                confidence=1.0,
                metadata={"task_id": task_id, "effort": actual_effort, "notes": notes}
            )

        success = self.memory.todos.complete_task(task_id, actual_effort, notes)

        # Update goal progress if linked
        if task.get("goal_id"):
            self._update_goal_from_tasks(task.get("goal_id"))

        return {"success": success, "task_id": task_id}

    def block_task_with_issue(
        self,
        task_id: str,
        reason: str,
        create_issue: bool = True,
        severity: IssueSeverity = IssueSeverity.MEDIUM
    ) -> Dict[str, Any]:
        """Block a task and optionally create an associated issue"""
        self.memory.todos.block_task(task_id, reason)

        issue_id = None
        if create_issue:
            task = self.memory.todos.get_task(task_id)
            issue_id = self.report_issue(
                title=f"Blocker: {reason[:50]}",
                description=f"Task '{task.get('title', task_id)}' blocked: {reason}",
                severity=severity,
                task_id=task_id,
                auto_escalate=severity == IssueSeverity.CRITICAL
            )

        return {
            "task_id": task_id,
            "blocked": True,
            "issue_id": issue_id
        }

    def _update_goal_from_tasks(self, goal_id: str) -> None:
        """Update goal progress based on associated tasks"""
        tasks = self.memory.todos.get_tasks_by_goal(goal_id)
        if not tasks:
            return

        completed = sum(1 for t in tasks if t.get("status") == TaskStatus.COMPLETED.value)
        total = len(tasks)
        progress = int((completed / total) * 100) if total > 0 else 0

        # Update goal progress through milestone if exists
        goal = self.memory.goals.get_goal(goal_id)
        if goal and goal.get("milestones"):
            # Find current milestone
            for milestone in goal["milestones"]:
                if milestone.get("status") == MilestoneStatus.IN_PROGRESS.value:
                    self.memory.goals.update_milestone_progress(
                        milestone.get("id"), progress
                    )
                    break

    # =========================================================================
    # Issue Management with Incident Tracking
    # =========================================================================

    def report_issue(
        self,
        title: str,
        description: str = "",
        severity: IssueSeverity = IssueSeverity.MEDIUM,
        issue_type: IssueType = IssueType.BUG,
        location: str = "",
        task_id: Optional[str] = None,
        goal_id: Optional[str] = None,
        auto_escalate: bool = False
    ) -> str:
        """
        Report an issue with optional governance incident creation.

        Args:
            title: Issue title
            description: Issue description
            severity: Issue severity
            issue_type: Type of issue
            location: Code location
            task_id: Related task
            goal_id: Related goal
            auto_escalate: Auto-escalate critical issues

        Returns:
            Issue ID
        """
        issue_id = self.memory.issues.create_issue(
            title=title,
            description=description,
            severity=severity,
            issue_type=issue_type,
            location=location,
            session_id=self._current_session_id,
            task_id=task_id,
            goal_id=goal_id or self._current_goal_id
        )

        if self.governance:
            # Record in audit
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="issue_reported",
                outcome="created",
                confidence=1.0,
                metadata={
                    "issue_id": issue_id,
                    "title": title,
                    "severity": severity.value if isinstance(severity, IssueSeverity) else severity
                }
            )

            # Create incident for high/critical severity
            if severity in [IssueSeverity.HIGH, IssueSeverity.CRITICAL]:
                incident_severity = (
                    IncidentSeverity.CRITICAL if severity == IssueSeverity.CRITICAL
                    else IncidentSeverity.HIGH
                )

                self.governance.report_incident(
                    severity=incident_severity,
                    category=issue_type.value if isinstance(issue_type, IssueType) else issue_type,
                    description=f"Issue: {title}\n{description}"
                )

            # Escalate if requested
            if auto_escalate and severity == IssueSeverity.CRITICAL:
                self.governance.escalation.trigger_escalation({
                    "issue_id": issue_id,
                    "title": title,
                    "severity": severity.value if isinstance(severity, IssueSeverity) else severity,
                    "type": "critical_issue"
                })

        # Add risk to goal if linked
        if goal_id or self._current_goal_id:
            gid = goal_id or self._current_goal_id
            risk_severity = "critical" if severity == IssueSeverity.CRITICAL else \
                           "high" if severity == IssueSeverity.HIGH else "medium"
            self.memory.goals.add_risk(
                gid, f"Issue: {title}", risk_severity
            )

        return issue_id

    def resolve_issue_with_learning(
        self,
        issue_id: str,
        resolution: str,
        root_cause: str = "",
        fix_commit: str = "",
        create_bug_pattern: bool = True
    ) -> Dict[str, Any]:
        """
        Resolve an issue and learn from it.

        Args:
            issue_id: Issue to resolve
            resolution: Resolution description
            root_cause: Root cause analysis
            fix_commit: Git commit with fix
            create_bug_pattern: Create bug pattern for future prevention

        Returns:
            Resolution result
        """
        issue = self.memory.issues.get_issue(issue_id)
        if not issue:
            return {"success": False, "reason": "Issue not found"}

        # Resolve the issue
        self.memory.issues.resolve_issue(
            issue_id=issue_id,
            resolution=resolution,
            fix_commit=fix_commit,
            root_cause=root_cause
        )

        # Learn from the issue
        if create_bug_pattern and root_cause:
            pattern_id = self.memory.bugs.add_pattern(
                name=f"Pattern from {issue.get('title', issue_id)[:30]}",
                signature=root_cause,
                modules_affected=[issue.get("location", "unknown")]
            )

            self.memory.bugs.add_fix_pattern(
                bug_pattern_name=f"Pattern from {issue.get('title', issue_id)[:30]}",
                fix_template=resolution,
                caveats=""
            )

            # Record skill learning
            self.memory.skills.record_learning_event(
                skill_name="debugging",
                event_type="issue_resolved",
                context=f"Resolved: {issue.get('title')}",
                lesson=f"Root cause: {root_cause}. Fix: {resolution}"
            )

        if self.governance:
            self.governance.audit.record_decision(
                agent_id="self",
                decision_type="issue_resolved",
                outcome="success",
                confidence=1.0,
                metadata={
                    "issue_id": issue_id,
                    "root_cause": root_cause,
                    "resolution": resolution
                }
            )

            # Resolve related goal risk if exists
            goal_id = issue.get("goal_id")
            if goal_id:
                # Find and resolve the risk
                goal = self.memory.goals.get_goal(goal_id)
                if goal:
                    for risk in goal.get("risks", []):
                        if issue.get("title") in risk.get("description", ""):
                            self.memory.goals.resolve_risk(
                                risk.get("id", ""),
                                f"Issue resolved: {resolution}"
                            )
                            break

        return {
            "success": True,
            "issue_id": issue_id,
            "learned": create_bug_pattern
        }

    # =========================================================================
    # Comprehensive Status and Reporting
    # =========================================================================

    def get_work_status(self) -> Dict[str, Any]:
        """Get comprehensive status of all work"""
        status = {
            "session": None,
            "current_goal": None,
            "tasks": self.memory.todos.get_task_summary(),
            "goals": self.memory.goals.get_stats(),
            "issues": self.memory.issues.get_issue_summary(),
            "blockers": [],
            "at_risk": [],
            "next_actions": []
        }

        # Current session
        if self._current_session_id:
            status["session"] = self.get_session_summary()

        # Current goal
        if self._current_goal_id:
            status["current_goal"] = self.memory.goals.get_goal_progress_report(
                self._current_goal_id
            )

        # Blockers
        blocked_tasks = self.memory.todos.get_blocked_tasks()
        status["blockers"].extend([
            {"type": "task", **t} for t in blocked_tasks
        ])

        blocked_goals = self.memory.goals.get_blocked_goals()
        status["blockers"].extend([
            {"type": "goal", **g} for g in blocked_goals
        ])

        # At risk
        at_risk_goals = self.memory.goals.get_at_risk_goals()
        status["at_risk"] = at_risk_goals

        # Critical issues
        critical_issues = self.memory.issues.get_critical_issues()
        if critical_issues:
            status["critical_issues"] = critical_issues

        # Suggested next actions
        next_task = self.memory.todos.get_next_task()
        if next_task:
            status["next_actions"].append({
                "type": "task",
                "action": f"Work on: {next_task.get('title')}",
                "id": next_task.get("id")
            })

        overdue = self.memory.todos.get_overdue_tasks()
        for task in overdue[:3]:
            status["next_actions"].append({
                "type": "overdue",
                "action": f"Complete overdue: {task.get('title')}",
                "id": task.get("id")
            })

        return status

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from both systems"""
        stats = {
            "memory": self.memory.get_stats(),
        }

        if self.governance:
            stats["governance"] = self.governance.get_stats()
            stats["governance_health"] = self.governance.get_health()
            stats["risk_posture"] = self.governance.assess_risk_posture()

        return stats

    # =========================================================================
    # Persistence
    # =========================================================================

    def save(self, path: str) -> None:
        """Save memory to file"""
        self.memory.save(path)

        if self.governance:
            gov_path = path.replace(".ison", "_governance.ison")
            self.governance.save(gov_path)

    @classmethod
    def load(cls, path: str, enable_governance: bool = True) -> "GovernedAgentMemory":
        """Load memory from file"""
        memory = AgentMemory.load(path)

        instance = cls.__new__(cls)
        instance.name = memory.name
        instance.memory = memory
        instance.governance_enabled = enable_governance and GOVERNANCE_AVAILABLE
        instance._current_session_id = None
        instance._current_goal_id = None

        if instance.governance_enabled:
            gov_path = path.replace(".ison", "_governance.ison")
            try:
                instance.governance = GovernanceEngine.load(gov_path)
            except:
                instance.governance = GovernanceEngine(memory.name)
                instance._setup_governance({})
        else:
            instance.governance = None

        return instance


# Convenience functions
def create_governed_agent(name: str, enable_governance: bool = True) -> GovernedAgentMemory:
    """Create a new governed agent memory system"""
    return GovernedAgentMemory(name, enable_governance)


def quick_work_session(name: str, task: str) -> GovernedAgentMemory:
    """Quick setup for a work session"""
    agent = GovernedAgentMemory(name)
    agent.start_session(task)
    return agent
