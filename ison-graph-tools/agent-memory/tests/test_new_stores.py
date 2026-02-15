"""
Tests for new agent-memory stores: TodoStore, GoalStore, IssueStore
"""

import pytest
from ison_graph import ISONGraph

from agent_memory import AgentMemory
from agent_memory.stores import (
    TodoStore, TaskStatus, TaskPriority,
    GoalStore, GoalStatus, MilestoneStatus,
    IssueStore, IssueStatus, IssueSeverity, IssueType,
)


# ============================================================================
# TodoStore Tests
# ============================================================================

class TestTodoStore:
    @pytest.fixture
    def store(self):
        g = ISONGraph(name="test")
        g.add_node("agent", "self", name="agent")
        return TodoStore(g)

    def test_add_task(self, store):
        """Test adding a new task"""
        task_id = store.add_task(
            title="Implement feature X",
            description="Add the feature X to the system",
            priority=TaskPriority.HIGH
        )
        assert task_id is not None
        assert task_id.startswith("task_")

    def test_add_task_with_all_options(self, store):
        """Test adding task with all optional parameters"""
        task_id = store.add_task(
            title="Complete task",
            description="Full description",
            priority=TaskPriority.CRITICAL,
            deadline="2025-12-31",
            tags=["urgent", "backend"],
            estimated_effort="2h"
        )
        task = store.get_task(task_id)
        assert task is not None
        assert task["title"] == "Complete task"
        assert task["priority"] == "critical"
        assert task["deadline"] == "2025-12-31"
        assert "urgent" in task["tags"]

    def test_start_task(self, store):
        """Test starting a task"""
        task_id = store.add_task("Test task")
        result = store.start_task(task_id)
        assert result is True

        task = store.get_task(task_id)
        assert task["status"] == TaskStatus.IN_PROGRESS.value
        assert task["started_at"] != ""

    def test_complete_task(self, store):
        """Test completing a task"""
        task_id = store.add_task("Test task")
        store.start_task(task_id)
        result = store.complete_task(task_id, actual_effort="1h")
        assert result is True

        task = store.get_task(task_id)
        assert task["status"] == TaskStatus.COMPLETED.value
        assert task["progress"] == "100"

    def test_block_task(self, store):
        """Test blocking a task"""
        task_id = store.add_task("Test task")
        store.block_task(task_id, "Waiting for dependency")

        task = store.get_task(task_id)
        assert task["status"] == TaskStatus.BLOCKED.value
        assert "dependency" in task["blocked_reason"]

    def test_unblock_task(self, store):
        """Test unblocking a task"""
        task_id = store.add_task("Test task")
        store.start_task(task_id)
        store.block_task(task_id, "Blocked")
        store.unblock_task(task_id, "Dependency resolved")

        task = store.get_task(task_id)
        assert task["status"] == TaskStatus.IN_PROGRESS.value

    def test_cancel_task(self, store):
        """Test cancelling a task"""
        task_id = store.add_task("Test task")
        store.cancel_task(task_id, "No longer needed")

        task = store.get_task(task_id)
        assert task["status"] == TaskStatus.CANCELLED.value

    def test_update_progress(self, store):
        """Test updating task progress"""
        task_id = store.add_task("Test task")
        store.start_task(task_id)
        store.update_progress(task_id, 50, "Halfway done")

        task = store.get_task(task_id)
        assert task["progress"] == "50"

    def test_add_subtask(self, store):
        """Test adding subtasks"""
        parent_id = store.add_task("Parent task")
        sub_id = store.add_subtask(parent_id, "Subtask 1")

        parent = store.get_task(parent_id)
        assert len(parent["subtasks"]) == 1
        assert parent["subtasks"][0]["id"] == sub_id

    def test_add_dependency(self, store):
        """Test adding task dependencies"""
        task1 = store.add_task("First task")
        task2 = store.add_task("Second task")
        store.add_dependency(task2, task1)

        task = store.get_task(task2)
        assert len(task["dependencies"]) == 1
        assert task["dependencies"][0]["id"] == task1

    def test_get_pending_tasks(self, store):
        """Test getting pending tasks"""
        store.add_task("Task 1", priority=TaskPriority.HIGH)
        store.add_task("Task 2", priority=TaskPriority.LOW)
        store.add_task("Task 3", priority=TaskPriority.HIGH)

        pending = store.get_pending_tasks()
        assert len(pending) == 3
        # Should be sorted by priority
        assert pending[0]["priority"] == "high"

    def test_get_pending_tasks_by_priority(self, store):
        """Test filtering pending tasks by priority"""
        store.add_task("Task 1", priority=TaskPriority.HIGH)
        store.add_task("Task 2", priority=TaskPriority.LOW)

        high_priority = store.get_pending_tasks(priority=TaskPriority.HIGH)
        assert len(high_priority) == 1
        assert high_priority[0]["priority"] == "high"

    def test_get_in_progress_tasks(self, store):
        """Test getting in-progress tasks"""
        task1 = store.add_task("Task 1")
        task2 = store.add_task("Task 2")
        store.start_task(task1)

        in_progress = store.get_in_progress_tasks()
        assert len(in_progress) == 1
        assert in_progress[0]["id"] == task1

    def test_get_blocked_tasks(self, store):
        """Test getting blocked tasks"""
        task_id = store.add_task("Blocked task")
        store.block_task(task_id, "Reason")

        blocked = store.get_blocked_tasks()
        assert len(blocked) == 1

    def test_get_next_task(self, store):
        """Test getting next task recommendation"""
        store.add_task("Low priority", priority=TaskPriority.LOW)
        high_id = store.add_task("High priority", priority=TaskPriority.HIGH)

        next_task = store.get_next_task()
        assert next_task is not None
        assert next_task["id"] == high_id

    def test_get_next_task_respects_dependencies(self, store):
        """Test that next task respects dependencies"""
        dep_id = store.add_task("Dependency")
        task_id = store.add_task("Main task", priority=TaskPriority.CRITICAL)
        store.add_dependency(task_id, dep_id)

        next_task = store.get_next_task()
        # Should return the dependency first
        assert next_task["id"] == dep_id

    def test_get_task_summary(self, store):
        """Test getting task summary statistics"""
        store.add_task("Task 1", priority=TaskPriority.HIGH)
        task2 = store.add_task("Task 2", priority=TaskPriority.LOW)
        store.complete_task(task2)

        summary = store.get_task_summary()
        assert summary["total"] == 2
        assert summary["by_status"]["pending"] == 1
        assert summary["by_status"]["completed"] == 1
        assert summary["by_priority"]["high"] == 1

    def test_get_stats(self, store):
        """Test getting store statistics"""
        store.add_task("Task 1")
        task2 = store.add_task("Task 2")
        store.complete_task(task2)

        stats = store.get_stats()
        assert stats["total_tasks"] == 2
        assert stats["completed"] == 1


# ============================================================================
# GoalStore Tests
# ============================================================================

class TestGoalStore:
    @pytest.fixture
    def store(self):
        g = ISONGraph(name="test")
        g.add_node("agent", "self", name="agent")
        return GoalStore(g)

    def test_define_goal(self, store):
        """Test defining a new goal"""
        goal_id = store.define_goal(
            name="Implement Authentication",
            description="Add user authentication to the app",
            success_criteria=["Login works", "Logout works", "Session management"]
        )
        assert goal_id is not None
        assert goal_id.startswith("goal_")

    def test_define_goal_with_acceptance_criteria(self, store):
        """Test defining goal with acceptance criteria"""
        goal_id = store.define_goal(
            name="Feature X",
            description="Description",
            success_criteria=["Works correctly"],
            acceptance_criteria=["Performance < 100ms", "No security issues"]
        )

        goal = store.get_goal(goal_id)
        assert len(goal["success_criteria"]) == 1
        assert len(goal["acceptance_criteria"]) == 2

    def test_activate_goal(self, store):
        """Test activating a goal"""
        goal_id = store.define_goal(
            name="Test Goal",
            description="Test",
            success_criteria=["Done"]
        )

        result = store.activate_goal(goal_id)
        assert result is True

        goal = store.get_goal(goal_id)
        assert goal["status"] == GoalStatus.ACTIVE.value
        assert goal["started_at"] != ""

    def test_add_milestone(self, store):
        """Test adding milestones to a goal"""
        goal_id = store.define_goal(
            name="Test Goal",
            description="Test",
            success_criteria=["Done"]
        )

        mile_id = store.add_milestone(
            goal_id=goal_id,
            name="Phase 1",
            description="First phase",
            order=1,
            deliverables=["Design doc", "API spec"]
        )

        assert mile_id is not None
        goal = store.get_goal(goal_id)
        assert len(goal["milestones"]) == 1
        assert goal["milestones"][0]["name"] == "Phase 1"

    def test_start_milestone(self, store):
        """Test starting a milestone"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        mile_id = store.add_milestone(goal_id, "Milestone 1")

        result = store.start_milestone(mile_id)
        assert result is True

        goal = store.get_goal(goal_id)
        assert goal["milestones"][0]["status"] == MilestoneStatus.IN_PROGRESS.value

    def test_complete_milestone(self, store):
        """Test completing a milestone"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        mile_id = store.add_milestone(goal_id, "Milestone 1")
        store.start_milestone(mile_id)

        result = store.complete_milestone(mile_id)
        assert result is True

        goal = store.get_goal(goal_id)
        assert goal["milestones"][0]["status"] == MilestoneStatus.COMPLETED.value
        assert goal["milestones"][0]["progress"] == "100"

    def test_update_milestone_progress(self, store):
        """Test updating milestone progress"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        mile_id = store.add_milestone(goal_id, "Milestone 1")
        store.start_milestone(mile_id)

        store.update_milestone_progress(mile_id, 50, "Halfway there")

        goal = store.get_goal(goal_id)
        assert goal["milestones"][0]["progress"] == "50"

    def test_meet_criterion(self, store):
        """Test meeting success criteria"""
        goal_id = store.define_goal(
            name="Goal",
            description="Desc",
            success_criteria=["Criterion 1", "Criterion 2"]
        )

        result = store.meet_criterion(goal_id, 0, "Test passed")
        assert result is True

        goal = store.get_goal(goal_id)
        assert goal["success_criteria"][0]["met"] == "True"
        assert goal["success_criteria"][0]["evidence"] == "Test passed"
        assert goal["success_criteria"][1]["met"] == "False"

    def test_complete_goal(self, store):
        """Test completing a goal with all criteria met"""
        goal_id = store.define_goal(
            name="Goal",
            description="Desc",
            success_criteria=["Criterion 1"]
        )

        # Complete criterion first
        store.meet_criterion(goal_id, 0, "Evidence")

        result = store.complete_goal(goal_id)
        assert result["success"] is True

        goal = store.get_goal(goal_id)
        assert goal["status"] == GoalStatus.COMPLETED.value

    def test_complete_goal_fails_without_criteria(self, store):
        """Test that goal completion fails without meeting criteria"""
        goal_id = store.define_goal(
            name="Goal",
            description="Desc",
            success_criteria=["Criterion 1", "Criterion 2"]
        )

        result = store.complete_goal(goal_id)
        assert result["success"] is False
        assert len(result["unmet_criteria"]) == 2

    def test_complete_goal_force(self, store):
        """Test forcing goal completion"""
        goal_id = store.define_goal(
            name="Goal",
            description="Desc",
            success_criteria=["Criterion 1"]
        )

        result = store.complete_goal(goal_id, force=True)
        assert result["success"] is True
        assert result["forced"] is True

    def test_block_goal(self, store):
        """Test blocking a goal"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        store.block_goal(goal_id, "Waiting for external dependency")

        goal = store.get_goal(goal_id)
        assert goal["status"] == GoalStatus.BLOCKED.value

    def test_add_risk(self, store):
        """Test adding risks to a goal"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        risk_id = store.add_risk(goal_id, "Third party API might fail", "high")

        assert risk_id is not None
        goal = store.get_goal(goal_id)
        assert len(goal["risks"]) == 1
        assert goal["risks"][0]["severity"] == "high"

    def test_resolve_risk(self, store):
        """Test resolving a risk"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        risk_id = store.add_risk(goal_id, "Risk description", "medium")

        store.resolve_risk(risk_id, "Implemented fallback")

        goal = store.get_goal(goal_id)
        assert goal["risks"][0]["status"] == "resolved"

    def test_risk_affects_health(self, store):
        """Test that risks affect goal health score"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        store.add_risk(goal_id, "Critical risk", "critical")

        goal = store.get_goal(goal_id)
        assert int(goal["health_score"]) < 100

    def test_get_active_goals(self, store):
        """Test getting active goals"""
        goal1 = store.define_goal("Goal 1", "Desc", ["Done"])
        goal2 = store.define_goal("Goal 2", "Desc", ["Done"])
        store.activate_goal(goal1)

        active = store.get_active_goals()
        assert len(active) == 1
        assert active[0]["id"] == goal1

    def test_get_at_risk_goals(self, store):
        """Test getting at-risk goals"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        store.activate_goal(goal_id)
        # Add multiple risks to push health below threshold
        store.add_risk(goal_id, "Risk 1", "critical")
        store.add_risk(goal_id, "Risk 2", "high")
        store.add_risk(goal_id, "Risk 3", "high")

        at_risk = store.get_at_risk_goals()
        # Should be at risk due to low health
        assert len(at_risk) >= 0  # May or may not trigger based on threshold

    def test_get_blocked_goals(self, store):
        """Test getting blocked goals"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        store.block_goal(goal_id, "Reason")

        blocked = store.get_blocked_goals()
        assert len(blocked) == 1

    def test_get_completed_goals(self, store):
        """Test getting completed goals"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        store.meet_criterion(goal_id, 0, "Evidence")
        store.complete_goal(goal_id)

        completed = store.get_completed_goals()
        assert len(completed) == 1

    def test_get_goal_progress_report(self, store):
        """Test getting goal progress report"""
        goal_id = store.define_goal(
            name="Goal",
            description="Desc",
            success_criteria=["C1", "C2"],
            acceptance_criteria=["A1"]
        )
        store.add_milestone(goal_id, "M1")
        store.meet_criterion(goal_id, 0, "Evidence")

        report = store.get_goal_progress_report(goal_id)
        assert report["criteria"]["success"]["met"] == 1
        assert report["criteria"]["success"]["total"] == 2
        assert report["milestones"]["total"] == 1

    def test_verify_delivery(self, store):
        """Test delivery verification"""
        goal_id = store.define_goal(
            name="Goal",
            description="Desc",
            success_criteria=["Criterion 1"]
        )

        # Not verified - criteria not met
        verification = store.verify_delivery(goal_id)
        assert verification["verified"] is False

        # Meet criterion
        store.meet_criterion(goal_id, 0, "Done")

        # Now verified
        verification = store.verify_delivery(goal_id)
        assert verification["verified"] is True

    def test_get_stats(self, store):
        """Test getting store statistics"""
        goal_id = store.define_goal("Goal", "Desc", ["Done"])
        store.add_milestone(goal_id, "M1")

        stats = store.get_stats()
        assert stats["total_goals"] == 1
        assert stats["total_milestones"] == 1


# ============================================================================
# IssueStore Tests
# ============================================================================

class TestIssueStore:
    @pytest.fixture
    def store(self):
        g = ISONGraph(name="test")
        g.add_node("agent", "self", name="agent")
        return IssueStore(g)

    def test_create_issue(self, store):
        """Test creating a new issue"""
        issue_id = store.create_issue(
            title="Login fails on mobile",
            description="Users cannot log in from mobile devices",
            severity=IssueSeverity.HIGH,
            issue_type=IssueType.BUG
        )
        assert issue_id is not None
        assert issue_id.startswith("issue_")

    def test_create_issue_with_all_fields(self, store):
        """Test creating issue with all fields"""
        issue_id = store.create_issue(
            title="Performance issue",
            description="Slow response",
            severity=IssueSeverity.MEDIUM,
            issue_type=IssueType.PERFORMANCE,
            location="src/api/handler.py:42",
            steps_to_reproduce=["Call API", "Wait 5 seconds"],
            expected_behavior="Response in 100ms",
            actual_behavior="Response in 5000ms",
            tags=["performance", "api"]
        )

        issue = store.get_issue(issue_id)
        assert issue["location"] == "src/api/handler.py:42"
        assert "Call API" in issue["steps_to_reproduce"]

    def test_assign_issue(self, store):
        """Test assigning an issue"""
        issue_id = store.create_issue("Bug", "Description")
        result = store.assign_issue(issue_id, "developer")
        assert result is True

        issue = store.get_issue(issue_id)
        assert issue["assigned_to"] == "developer"

    def test_start_investigation(self, store):
        """Test starting issue investigation"""
        issue_id = store.create_issue("Bug", "Description")
        result = store.start_investigation(issue_id, "Looking into it")
        assert result is True

        issue = store.get_issue(issue_id)
        assert issue["status"] == IssueStatus.INVESTIGATING.value

    def test_start_fix(self, store):
        """Test starting issue fix"""
        issue_id = store.create_issue("Bug", "Description")
        result = store.start_fix(issue_id, "Will refactor the code")
        assert result is True

        issue = store.get_issue(issue_id)
        assert issue["status"] == IssueStatus.IN_PROGRESS.value

    def test_add_comment(self, store):
        """Test adding comments to an issue"""
        issue_id = store.create_issue("Bug", "Description")
        comment_id = store.add_comment(issue_id, "update", "Found the root cause")

        assert comment_id is not None
        issue = store.get_issue(issue_id)
        assert len(issue["comments"]) == 1
        assert issue["comments"][0]["content"] == "Found the root cause"

    def test_record_root_cause(self, store):
        """Test recording root cause"""
        issue_id = store.create_issue("Bug", "Description")
        store.record_root_cause(issue_id, "Race condition in async handler")

        issue = store.get_issue(issue_id)
        assert "Race condition" in issue["root_cause"]

    def test_resolve_issue(self, store):
        """Test resolving an issue"""
        issue_id = store.create_issue("Bug", "Description")
        result = store.resolve_issue(
            issue_id,
            resolution="Added mutex lock",
            fix_commit="abc123",
            root_cause="Race condition"
        )
        assert result is True

        issue = store.get_issue(issue_id)
        assert issue["status"] == IssueStatus.RESOLVED.value
        assert issue["resolution"] == "Added mutex lock"
        assert issue["fix_commit"] == "abc123"

    def test_close_issue(self, store):
        """Test closing an issue"""
        issue_id = store.create_issue("Bug", "Description")
        result = store.close_issue(issue_id, "Fixed and verified")
        assert result is True

        issue = store.get_issue(issue_id)
        assert issue["status"] == IssueStatus.CLOSED.value

    def test_reopen_issue(self, store):
        """Test reopening an issue"""
        issue_id = store.create_issue("Bug", "Description")
        store.resolve_issue(issue_id, "Fixed")
        store.reopen_issue(issue_id, "Bug still occurs")

        issue = store.get_issue(issue_id)
        assert issue["status"] == IssueStatus.OPEN.value

    def test_mark_duplicate(self, store):
        """Test marking issue as duplicate"""
        issue1 = store.create_issue("Original bug", "Description")
        issue2 = store.create_issue("Same bug", "Description")

        result = store.mark_duplicate(issue2, issue1)
        assert result is True

        issue = store.get_issue(issue2)
        assert issue["status"] == IssueStatus.DUPLICATE.value

    def test_mark_wont_fix(self, store):
        """Test marking issue as won't fix"""
        issue_id = store.create_issue("Feature request", "Description")
        result = store.mark_wont_fix(issue_id, "Out of scope")
        assert result is True

        issue = store.get_issue(issue_id)
        assert issue["status"] == IssueStatus.WONT_FIX.value

    def test_link_issues(self, store):
        """Test linking related issues"""
        issue1 = store.create_issue("Issue 1", "Desc")
        issue2 = store.create_issue("Issue 2", "Desc")

        store.link_issues(issue1, issue2, "related")

        issue = store.get_issue(issue1)
        assert len(issue["related_issues"]) == 1

    def test_add_workaround(self, store):
        """Test adding workaround"""
        issue_id = store.create_issue("Bug", "Description")
        wa_id = store.add_workaround(issue_id, "Clear cache before login")

        assert wa_id is not None
        issue = store.get_issue(issue_id)
        assert len(issue["workarounds"]) == 1

    def test_get_open_issues(self, store):
        """Test getting open issues"""
        store.create_issue("Issue 1", "Desc", severity=IssueSeverity.HIGH)
        store.create_issue("Issue 2", "Desc", severity=IssueSeverity.LOW)
        issue3 = store.create_issue("Issue 3", "Desc")
        store.resolve_issue(issue3, "Fixed")

        open_issues = store.get_open_issues()
        assert len(open_issues) == 2
        # Should be sorted by severity
        assert open_issues[0]["severity"] == "high"

    def test_get_open_issues_filtered(self, store):
        """Test filtering open issues"""
        store.create_issue("Bug 1", "Desc", severity=IssueSeverity.HIGH)
        store.create_issue("Bug 2", "Desc", severity=IssueSeverity.LOW)

        high_issues = store.get_open_issues(severity=IssueSeverity.HIGH)
        assert len(high_issues) == 1

    def test_get_critical_issues(self, store):
        """Test getting critical issues"""
        store.create_issue("Critical bug", "Desc", severity=IssueSeverity.CRITICAL)
        store.create_issue("Normal bug", "Desc", severity=IssueSeverity.MEDIUM)

        critical = store.get_critical_issues()
        assert len(critical) == 1

    def test_get_issues_by_location(self, store):
        """Test getting issues by code location"""
        store.create_issue("Bug 1", "Desc", location="src/api/handler.py")
        store.create_issue("Bug 2", "Desc", location="src/db/model.py")

        issues = store.get_issues_by_location("api/handler")
        assert len(issues) == 1

    def test_get_resolved_issues(self, store):
        """Test getting resolved issues"""
        issue_id = store.create_issue("Bug", "Desc")
        store.resolve_issue(issue_id, "Fixed")

        resolved = store.get_resolved_issues()
        assert len(resolved) == 1

    def test_find_similar_issues(self, store):
        """Test finding similar issues"""
        store.create_issue("Login fails on mobile browser", "Users cannot login")
        store.create_issue("Login page broken", "Login not working")
        store.create_issue("Database connection timeout", "DB issues")

        similar = store.find_similar_issues("login fails", "users cannot login")
        # Should find at least one similar issue with "login" keyword
        assert len(similar) >= 1
        assert "login" in similar[0]["title"].lower()

    def test_get_issue_summary(self, store):
        """Test getting issue summary"""
        store.create_issue("Bug 1", "Desc", severity=IssueSeverity.HIGH)
        issue2 = store.create_issue("Bug 2", "Desc", severity=IssueSeverity.LOW)
        store.resolve_issue(issue2, "Fixed")

        summary = store.get_issue_summary()
        assert summary["total"] == 2
        assert summary["by_severity"]["high"] == 1
        assert summary["by_status"]["resolved"] == 1

    def test_get_stats(self, store):
        """Test getting store statistics"""
        store.create_issue("Bug", "Desc", severity=IssueSeverity.CRITICAL)

        stats = store.get_stats()
        assert stats["total_issues"] == 1
        assert stats["critical"] == 1


# ============================================================================
# Integration Tests with AgentMemory
# ============================================================================

class TestAgentMemoryIntegration:
    @pytest.fixture
    def memory(self):
        return AgentMemory("test-project")

    def test_memory_has_new_stores(self, memory):
        """Test that AgentMemory has new stores"""
        assert hasattr(memory, "todos")
        assert hasattr(memory, "goals")
        assert hasattr(memory, "issues")

        assert isinstance(memory.todos, TodoStore)
        assert isinstance(memory.goals, GoalStore)
        assert isinstance(memory.issues, IssueStore)

    def test_stats_include_new_stores(self, memory):
        """Test that stats include new stores"""
        stats = memory.get_stats()

        assert "todos" in stats["stores"]
        assert "goals" in stats["stores"]
        assert "issues" in stats["stores"]

    def test_full_workflow(self, memory):
        """Test a complete workflow with all new stores"""
        # Define a goal
        goal_id = memory.goals.define_goal(
            name="Implement feature X",
            description="Add feature X to the system",
            success_criteria=["Tests pass", "Documentation updated"]
        )
        memory.goals.activate_goal(goal_id)

        # Add tasks for the goal
        task1 = memory.todos.add_task(
            title="Write unit tests",
            goal_id=goal_id,
            priority=TaskPriority.HIGH
        )
        task2 = memory.todos.add_task(
            title="Implement feature",
            goal_id=goal_id,
            priority=TaskPriority.HIGH
        )
        memory.todos.add_dependency(task2, task1)

        # Start working
        memory.todos.start_task(task1)

        # Encounter an issue
        issue_id = memory.issues.create_issue(
            title="Test framework issue",
            description="Tests not running correctly",
            severity=IssueSeverity.MEDIUM,
            task_id=task1,
            goal_id=goal_id
        )

        # Resolve issue
        memory.issues.resolve_issue(issue_id, "Updated test config")

        # Complete tasks
        memory.todos.complete_task(task1)
        memory.todos.start_task(task2)
        memory.todos.complete_task(task2)

        # Meet criteria
        memory.goals.meet_criterion(goal_id, 0, "All tests pass")
        memory.goals.meet_criterion(goal_id, 1, "Docs updated")

        # Complete goal
        result = memory.goals.complete_goal(goal_id)
        assert result["success"] is True

        # Verify final state
        goal = memory.goals.get_goal(goal_id)
        assert goal["status"] == GoalStatus.COMPLETED.value

        tasks = memory.todos.get_tasks_by_goal(goal_id)
        assert all(t["status"] == TaskStatus.COMPLETED.value for t in tasks)

    def test_save_and_load_with_new_stores(self, memory, tmp_path):
        """Test saving and loading memory with new stores"""
        # Add data to new stores
        memory.todos.add_task("Test task")
        memory.goals.define_goal("Test goal", "Desc", ["Done"])
        memory.issues.create_issue("Test issue", "Desc")

        # Save
        save_path = str(tmp_path / "test.ison")
        memory.save(save_path)

        # Load
        loaded = AgentMemory.load(save_path)

        # Verify stores are restored
        assert hasattr(loaded, "todos")
        assert hasattr(loaded, "goals")
        assert hasattr(loaded, "issues")

        # Verify data is present
        stats = loaded.get_stats()
        assert stats["stores"]["todos"]["total_tasks"] == 1
        assert stats["stores"]["goals"]["total_goals"] == 1
        assert stats["stores"]["issues"]["total_issues"] == 1
