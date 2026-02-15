"""
Todo Store - Task management and tracking for agents
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from .base import BaseStore


class TaskStatus(Enum):
    """Task status values"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TaskPriority(Enum):
    """Task priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class TodoStore(BaseStore):
    """
    Manages task/todo tracking for agents.

    Tracks:
    - Tasks with status, priority, and deadlines
    - Task dependencies and blockers
    - Task progress and completion
    - Task history and context

    This enables agents to:
    - Maintain a structured todo list
    - Track progress towards completing work
    - Handle blocked tasks and dependencies
    - Resume interrupted work
    """

    _task_counter = 0

    def add_task(
        self,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        deadline: Optional[str] = None,
        parent_task: Optional[str] = None,
        tags: Optional[List[str]] = None,
        estimated_effort: Optional[str] = None,
        session_id: Optional[str] = None,
        goal_id: Optional[str] = None
    ) -> str:
        """
        Add a new task to the todo list.

        Args:
            title: Task title/summary
            description: Detailed description
            priority: Task priority level
            deadline: Optional deadline (ISO format)
            parent_task: Parent task ID for subtasks
            tags: Optional tags for categorization
            estimated_effort: Estimated effort (e.g., "2h", "1d")
            session_id: Session that created this task
            goal_id: Goal this task contributes to

        Returns:
            Task ID
        """
        TodoStore._task_counter += 1
        task_id = self._make_id("task", f"{title[:20]}_{TodoStore._task_counter}")

        priority_val = priority.value if isinstance(priority, TaskPriority) else priority

        self.graph.add_node(
            "task",
            task_id,
            title=self._sanitize(title),
            description=self._sanitize(description),
            status=TaskStatus.PENDING.value,
            priority=priority_val,
            deadline=deadline or "",
            created_at=self._now(),
            started_at="",
            completed_at="",
            parent_task=parent_task or "",
            tags=",".join(tags or []),
            estimated_effort=estimated_effort or "",
            actual_effort="",
            session_id=session_id or "",
            goal_id=goal_id or "",
            progress="0",
            notes="",
            blocked_reason="",
        )

        # Link to parent task if exists
        if parent_task and self.graph.has_node("task", parent_task):
            self.graph.add_edge(
                "SUBTASK_OF",
                ("task", task_id),
                ("task", parent_task)
            )

        # Link to goal if exists
        if goal_id and self.graph.has_node("goal", goal_id):
            self.graph.add_edge(
                "CONTRIBUTES_TO",
                ("task", task_id),
                ("goal", goal_id)
            )

        # Link to session if exists
        if session_id and self.graph.has_node("session", session_id):
            self.graph.add_edge(
                "CREATED_IN",
                ("task", task_id),
                ("session", session_id)
            )

        return task_id

    def start_task(self, task_id: str, notes: str = "") -> bool:
        """
        Mark a task as in progress.

        Returns:
            True if task was started, False if blocked or not found
        """
        if not self.graph.has_node("task", task_id):
            return False

        task = self.graph.get_node("task", task_id)
        if not task:
            return False

        # Check if blocked
        if task.properties.get("status") == TaskStatus.BLOCKED.value:
            return False

        self.graph.update_node(
            "task",
            task_id,
            status=TaskStatus.IN_PROGRESS.value,
            started_at=self._now(),
            notes=self._sanitize(notes)
        )
        return True

    def update_progress(
        self,
        task_id: str,
        progress: int,
        notes: str = ""
    ) -> None:
        """Update task progress (0-100)"""
        if self.graph.has_node("task", task_id):
            update_data = {"progress": str(min(100, max(0, progress)))}
            if notes:
                task = self.graph.get_node("task", task_id)
                existing_notes = task.properties.get("notes", "") if task else ""
                new_notes = f"{existing_notes}\n[{self._now()}] {notes}" if existing_notes else notes
                update_data["notes"] = self._sanitize(new_notes)

            self.graph.update_node("task", task_id, **update_data)

    def complete_task(
        self,
        task_id: str,
        actual_effort: str = "",
        completion_notes: str = ""
    ) -> bool:
        """
        Mark a task as completed.

        Returns:
            True if completed, False if not found
        """
        if not self.graph.has_node("task", task_id):
            return False

        self.graph.update_node(
            "task",
            task_id,
            status=TaskStatus.COMPLETED.value,
            completed_at=self._now(),
            progress="100",
            actual_effort=actual_effort,
            notes=self._sanitize(completion_notes) if completion_notes else ""
        )

        # Check if this completes a parent task
        self._check_parent_completion(task_id)

        return True

    def block_task(
        self,
        task_id: str,
        reason: str,
        blocked_by_task: Optional[str] = None
    ) -> None:
        """Mark a task as blocked"""
        if not self.graph.has_node("task", task_id):
            return

        self.graph.update_node(
            "task",
            task_id,
            status=TaskStatus.BLOCKED.value,
            blocked_reason=self._sanitize(reason)
        )

        # Link to blocking task if provided
        if blocked_by_task and self.graph.has_node("task", blocked_by_task):
            self.graph.add_edge(
                "BLOCKED_BY",
                ("task", task_id),
                ("task", blocked_by_task),
                reason=self._sanitize(reason),
                blocked_at=self._now()
            )

    def unblock_task(self, task_id: str, resolution: str = "") -> None:
        """Unblock a task and set it back to pending or in_progress"""
        if not self.graph.has_node("task", task_id):
            return

        task = self.graph.get_node("task", task_id)
        if not task:
            return

        # Determine new status
        new_status = TaskStatus.PENDING.value
        if task.properties.get("started_at"):
            new_status = TaskStatus.IN_PROGRESS.value

        existing_notes = task.properties.get("notes", "")
        unblock_note = f"[{self._now()}] Unblocked: {resolution}" if resolution else f"[{self._now()}] Unblocked"
        new_notes = f"{existing_notes}\n{unblock_note}" if existing_notes else unblock_note

        self.graph.update_node(
            "task",
            task_id,
            status=new_status,
            blocked_reason="",
            notes=self._sanitize(new_notes)
        )

    def cancel_task(self, task_id: str, reason: str = "") -> None:
        """Cancel a task"""
        if self.graph.has_node("task", task_id):
            self.graph.update_node(
                "task",
                task_id,
                status=TaskStatus.CANCELLED.value,
                notes=f"Cancelled: {self._sanitize(reason)}" if reason else "Cancelled"
            )

    def add_dependency(
        self,
        task_id: str,
        depends_on_task_id: str,
        dependency_type: str = "must_complete"
    ) -> None:
        """Add a dependency between tasks"""
        if (self.graph.has_node("task", task_id) and
            self.graph.has_node("task", depends_on_task_id)):
            self.graph.add_edge(
                "DEPENDS_ON",
                ("task", task_id),
                ("task", depends_on_task_id),
                dependency_type=dependency_type
            )

    def add_subtask(
        self,
        parent_task_id: str,
        title: str,
        description: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM
    ) -> str:
        """Add a subtask to an existing task"""
        return self.add_task(
            title=title,
            description=description,
            priority=priority,
            parent_task=parent_task_id
        )

    def _check_parent_completion(self, task_id: str) -> None:
        """Check if completing a subtask completes the parent"""
        # Find parent task
        for edge in self.graph.edges():
            if edge.rel_type == "SUBTASK_OF" and edge.source == ("task", task_id):
                parent_id = edge.target[1]

                # Check if all subtasks are complete
                all_complete = True
                subtask_count = 0
                completed_count = 0

                for e in self.graph.edges():
                    if e.rel_type == "SUBTASK_OF" and e.target == ("task", parent_id):
                        subtask_count += 1
                        subtask = self.graph.get_node(*e.source)
                        if subtask:
                            if subtask.properties.get("status") == TaskStatus.COMPLETED.value:
                                completed_count += 1
                            else:
                                all_complete = False

                # Update parent progress
                if subtask_count > 0:
                    progress = int((completed_count / subtask_count) * 100)
                    self.graph.update_node("task", parent_id, progress=str(progress))

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task with its subtasks and dependencies"""
        if not self.graph.has_node("task", task_id):
            return None

        task = self.graph.get_node("task", task_id)
        if not task:
            return None

        result = {
            "id": task_id,
            **task.properties,
            "subtasks": [],
            "dependencies": [],
            "blocked_by": []
        }

        # Get subtasks
        for edge in self.graph.edges():
            if edge.rel_type == "SUBTASK_OF" and edge.target == ("task", task_id):
                subtask = self.graph.get_node(*edge.source)
                if subtask:
                    result["subtasks"].append({
                        "id": subtask.id,
                        **subtask.properties
                    })

        # Get dependencies
        for edge in self.graph.edges():
            if edge.rel_type == "DEPENDS_ON" and edge.source == ("task", task_id):
                dep = self.graph.get_node(*edge.target)
                if dep:
                    result["dependencies"].append({
                        "id": dep.id,
                        **dep.properties
                    })

        # Get blockers
        for edge in self.graph.edges():
            if edge.rel_type == "BLOCKED_BY" and edge.source == ("task", task_id):
                blocker = self.graph.get_node(*edge.target)
                if blocker:
                    result["blocked_by"].append({
                        "id": blocker.id,
                        "reason": edge.properties.get("reason", ""),
                        **blocker.properties
                    })

        return result

    def get_pending_tasks(self, priority: Optional[TaskPriority] = None) -> List[Dict[str, Any]]:
        """Get all pending tasks, optionally filtered by priority"""
        tasks = []
        priority_val = priority.value if isinstance(priority, TaskPriority) else priority

        for node in self.graph.nodes():
            if node.type == "task" and node.properties.get("status") == TaskStatus.PENDING.value:
                if priority_val is None or node.properties.get("priority") == priority_val:
                    tasks.append({"id": node.id, **node.properties})

        # Sort by priority then creation date
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        tasks.sort(key=lambda x: (
            priority_order.get(x.get("priority", "medium"), 2),
            x.get("created_at", "")
        ))

        return tasks

    def get_in_progress_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks currently in progress"""
        return [
            {"id": node.id, **node.properties}
            for node in self.graph.nodes()
            if node.type == "task" and node.properties.get("status") == TaskStatus.IN_PROGRESS.value
        ]

    def get_blocked_tasks(self) -> List[Dict[str, Any]]:
        """Get all blocked tasks with their blockers"""
        blocked = []

        for node in self.graph.nodes():
            if node.type == "task" and node.properties.get("status") == TaskStatus.BLOCKED.value:
                task_data = {"id": node.id, **node.properties, "blockers": []}

                # Find what's blocking this task
                for edge in self.graph.edges():
                    if edge.rel_type == "BLOCKED_BY" and edge.source == ("task", node.id):
                        blocker = self.graph.get_node(*edge.target)
                        if blocker:
                            task_data["blockers"].append({
                                "id": blocker.id,
                                "title": blocker.properties.get("title", ""),
                                "status": blocker.properties.get("status", "")
                            })

                blocked.append(task_data)

        return blocked

    def get_completed_tasks(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get completed tasks, optionally since a date"""
        completed = []

        for node in self.graph.nodes():
            if node.type == "task" and node.properties.get("status") == TaskStatus.COMPLETED.value:
                completed_at = node.properties.get("completed_at", "")
                if since is None or completed_at >= since:
                    completed.append({"id": node.id, **node.properties})

        completed.sort(key=lambda x: x.get("completed_at", ""), reverse=True)
        return completed

    def get_tasks_by_goal(self, goal_id: str) -> List[Dict[str, Any]]:
        """Get all tasks contributing to a goal"""
        tasks = []

        for edge in self.graph.edges():
            if edge.rel_type == "CONTRIBUTES_TO" and edge.target == ("goal", goal_id):
                task = self.graph.get_node(*edge.source)
                if task:
                    tasks.append({"id": task.id, **task.properties})

        return tasks

    def get_tasks_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all tasks from a session"""
        tasks = []

        for node in self.graph.nodes():
            if node.type == "task" and node.properties.get("session_id") == session_id:
                tasks.append({"id": node.id, **node.properties})

        return tasks

    def get_overdue_tasks(self) -> List[Dict[str, Any]]:
        """Get tasks that are past their deadline"""
        now = self._now()
        overdue = []

        for node in self.graph.nodes():
            if node.type == "task":
                deadline = node.properties.get("deadline", "")
                status = node.properties.get("status", "")

                if deadline and deadline < now and status not in [
                    TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value
                ]:
                    overdue.append({"id": node.id, **node.properties})

        return overdue

    def get_next_task(self) -> Optional[Dict[str, Any]]:
        """
        Get the next task to work on based on priority and dependencies.

        Returns the highest priority task that:
        - Is pending or in_progress
        - Has no unresolved dependencies
        - Is not blocked
        """
        candidates = []

        for node in self.graph.nodes():
            if node.type == "task" and node.properties.get("status") in [
                TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value
            ]:
                # Check dependencies
                has_unmet_deps = False
                for edge in self.graph.edges():
                    if edge.rel_type == "DEPENDS_ON" and edge.source == ("task", node.id):
                        dep = self.graph.get_node(*edge.target)
                        if dep and dep.properties.get("status") != TaskStatus.COMPLETED.value:
                            has_unmet_deps = True
                            break

                if not has_unmet_deps:
                    candidates.append({"id": node.id, **node.properties})

        if not candidates:
            return None

        # Sort by: in_progress first, then priority, then creation date
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        candidates.sort(key=lambda x: (
            0 if x.get("status") == TaskStatus.IN_PROGRESS.value else 1,
            priority_order.get(x.get("priority", "medium"), 2),
            x.get("created_at", "")
        ))

        return candidates[0]

    def get_task_summary(self) -> Dict[str, Any]:
        """Get a summary of all tasks"""
        summary = {
            "total": 0,
            "by_status": {s.value: 0 for s in TaskStatus},
            "by_priority": {p.value: 0 for p in TaskPriority},
            "overdue": 0,
            "completion_rate": 0.0
        }

        now = self._now()
        completed = 0
        closed = 0  # completed + cancelled

        for node in self.graph.nodes():
            if node.type == "task":
                summary["total"] += 1
                status = node.properties.get("status", TaskStatus.PENDING.value)
                priority = node.properties.get("priority", TaskPriority.MEDIUM.value)

                if status in summary["by_status"]:
                    summary["by_status"][status] += 1
                if priority in summary["by_priority"]:
                    summary["by_priority"][priority] += 1

                if status == TaskStatus.COMPLETED.value:
                    completed += 1
                    closed += 1
                elif status == TaskStatus.CANCELLED.value:
                    closed += 1

                deadline = node.properties.get("deadline", "")
                if deadline and deadline < now and status not in [
                    TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value
                ]:
                    summary["overdue"] += 1

        if summary["total"] > 0:
            summary["completion_rate"] = completed / summary["total"]

        return summary

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant task info for context"""
        results = []

        # Add current in-progress tasks
        in_progress = self.get_in_progress_tasks()
        if in_progress:
            results.append({
                "type": "current_tasks",
                "tasks": in_progress[:5]
            })

        # Add blocked tasks
        blocked = self.get_blocked_tasks()
        if blocked:
            results.append({
                "type": "blocked_tasks",
                "tasks": blocked[:3]
            })

        # Add overdue tasks
        overdue = self.get_overdue_tasks()
        if overdue:
            results.append({
                "type": "overdue_tasks",
                "tasks": overdue[:3]
            })

        # Suggest next task
        next_task = self.get_next_task()
        if next_task:
            results.append({
                "type": "suggested_next",
                "task": next_task
            })

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get todo store statistics"""
        summary = self.get_task_summary()
        return {
            "total_tasks": summary["total"],
            "pending": summary["by_status"].get("pending", 0),
            "in_progress": summary["by_status"].get("in_progress", 0),
            "blocked": summary["by_status"].get("blocked", 0),
            "completed": summary["by_status"].get("completed", 0),
            "cancelled": summary["by_status"].get("cancelled", 0),
            "overdue": summary["overdue"],
            "completion_rate": round(summary["completion_rate"], 2)
        }
