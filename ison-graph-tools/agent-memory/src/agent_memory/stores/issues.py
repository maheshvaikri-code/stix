"""
Issue Store - Issue tracking and resolution management
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from .base import BaseStore


class IssueStatus(Enum):
    """Issue status values"""
    OPEN = "open"
    INVESTIGATING = "investigating"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    RESOLVED = "resolved"
    CLOSED = "closed"
    WONT_FIX = "wont_fix"
    DUPLICATE = "duplicate"


class IssueSeverity(Enum):
    """Issue severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IssueType(Enum):
    """Issue types"""
    BUG = "bug"
    ERROR = "error"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    ENHANCEMENT = "enhancement"
    QUESTION = "question"
    BLOCKER = "blocker"


class IssueStore(BaseStore):
    """
    Manages issue tracking for agents.

    Tracks:
    - Issues with severity, type, and status
    - Issue investigation and resolution
    - Issue relationships and duplicates
    - Issue history and audit trail

    This enables agents to:
    - Track problems encountered during work
    - Document investigation and resolution
    - Learn from past issues
    - Prevent recurring issues
    """

    _issue_counter = 0
    _comment_counter = 0

    def create_issue(
        self,
        title: str,
        description: str,
        severity: IssueSeverity = IssueSeverity.MEDIUM,
        issue_type: IssueType = IssueType.BUG,
        source: str = "",
        location: str = "",
        steps_to_reproduce: Optional[List[str]] = None,
        expected_behavior: str = "",
        actual_behavior: str = "",
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None,
        task_id: Optional[str] = None,
        goal_id: Optional[str] = None
    ) -> str:
        """
        Create a new issue.

        Args:
            title: Issue title
            description: Detailed description
            severity: Issue severity
            issue_type: Type of issue
            source: Where the issue was discovered
            location: Code location (file, line, function)
            steps_to_reproduce: Steps to reproduce the issue
            expected_behavior: What should happen
            actual_behavior: What actually happens
            tags: Categorization tags
            session_id: Session where issue was found
            task_id: Related task ID
            goal_id: Related goal ID

        Returns:
            Issue ID
        """
        IssueStore._issue_counter += 1
        issue_id = self._make_id("issue", f"{title[:20]}_{IssueStore._issue_counter}")

        severity_val = severity.value if isinstance(severity, IssueSeverity) else severity
        type_val = issue_type.value if isinstance(issue_type, IssueType) else issue_type

        self.graph.add_node(
            "issue",
            issue_id,
            title=self._sanitize(title),
            description=self._sanitize(description),
            status=IssueStatus.OPEN.value,
            severity=severity_val,
            issue_type=type_val,
            source=source,
            location=location,
            steps_to_reproduce="|".join(steps_to_reproduce or []),
            expected_behavior=self._sanitize(expected_behavior),
            actual_behavior=self._sanitize(actual_behavior),
            tags=",".join(tags or []),
            created_at=self._now(),
            updated_at=self._now(),
            resolved_at="",
            closed_at="",
            session_id=session_id or "",
            task_id=task_id or "",
            goal_id=goal_id or "",
            assigned_to="",
            resolution="",
            root_cause="",
            fix_commit="",
            time_to_resolve=""
        )

        # Link to related entities
        if session_id and self.graph.has_node("session", session_id):
            self.graph.add_edge(
                "DISCOVERED_IN",
                ("issue", issue_id),
                ("session", session_id)
            )

        if task_id and self.graph.has_node("task", task_id):
            self.graph.add_edge(
                "BLOCKS",
                ("issue", issue_id),
                ("task", task_id)
            )

        if goal_id and self.graph.has_node("goal", goal_id):
            self.graph.add_edge(
                "AFFECTS",
                ("issue", issue_id),
                ("goal", goal_id)
            )

        return issue_id

    def assign_issue(self, issue_id: str, assigned_to: str) -> bool:
        """Assign an issue to someone"""
        if not self.graph.has_node("issue", issue_id):
            return False

        self.graph.update_node(
            "issue",
            issue_id,
            assigned_to=assigned_to,
            updated_at=self._now()
        )
        return True

    def start_investigation(self, issue_id: str, notes: str = "") -> bool:
        """Start investigating an issue"""
        if not self.graph.has_node("issue", issue_id):
            return False

        self.graph.update_node(
            "issue",
            issue_id,
            status=IssueStatus.INVESTIGATING.value,
            updated_at=self._now()
        )

        if notes:
            self.add_comment(issue_id, "investigation_started", notes)

        return True

    def start_fix(self, issue_id: str, approach: str = "") -> bool:
        """Start working on fixing an issue"""
        if not self.graph.has_node("issue", issue_id):
            return False

        self.graph.update_node(
            "issue",
            issue_id,
            status=IssueStatus.IN_PROGRESS.value,
            updated_at=self._now()
        )

        if approach:
            self.add_comment(issue_id, "fix_started", f"Approach: {approach}")

        return True

    def add_comment(
        self,
        issue_id: str,
        comment_type: str,
        content: str,
        author: str = "agent"
    ) -> str:
        """Add a comment to an issue"""
        IssueStore._comment_counter += 1
        comment_id = self._make_id("comment", f"{issue_id[:10]}_{IssueStore._comment_counter}")

        self.graph.add_node(
            "issue_comment",
            comment_id,
            issue_id=issue_id,
            comment_type=comment_type,
            content=self._sanitize(content),
            author=author,
            created_at=self._now()
        )

        if self.graph.has_node("issue", issue_id):
            self.graph.add_edge(
                "HAS_COMMENT",
                ("issue", issue_id),
                ("issue_comment", comment_id)
            )
            self.graph.update_node("issue", issue_id, updated_at=self._now())

        return comment_id

    def record_root_cause(self, issue_id: str, root_cause: str) -> None:
        """Record the root cause of an issue"""
        if self.graph.has_node("issue", issue_id):
            self.graph.update_node(
                "issue",
                issue_id,
                root_cause=self._sanitize(root_cause),
                updated_at=self._now()
            )
            self.add_comment(issue_id, "root_cause", root_cause)

    def resolve_issue(
        self,
        issue_id: str,
        resolution: str,
        fix_commit: str = "",
        root_cause: str = ""
    ) -> bool:
        """Resolve an issue"""
        if not self.graph.has_node("issue", issue_id):
            return False

        issue = self.graph.get_node("issue", issue_id)
        created_at = issue.properties.get("created_at", "") if issue else ""
        resolved_at = self._now()

        # Calculate time to resolve
        time_to_resolve = ""
        if created_at:
            # Simple calculation - could be enhanced
            time_to_resolve = f"Created: {created_at}, Resolved: {resolved_at}"

        update_data = {
            "status": IssueStatus.RESOLVED.value,
            "resolution": self._sanitize(resolution),
            "resolved_at": resolved_at,
            "updated_at": resolved_at,
            "time_to_resolve": time_to_resolve
        }

        if fix_commit:
            update_data["fix_commit"] = fix_commit
        if root_cause:
            update_data["root_cause"] = self._sanitize(root_cause)

        self.graph.update_node("issue", issue_id, **update_data)
        self.add_comment(issue_id, "resolved", resolution)

        return True

    def close_issue(self, issue_id: str, reason: str = "") -> bool:
        """Close an issue"""
        if not self.graph.has_node("issue", issue_id):
            return False

        self.graph.update_node(
            "issue",
            issue_id,
            status=IssueStatus.CLOSED.value,
            closed_at=self._now(),
            updated_at=self._now()
        )

        if reason:
            self.add_comment(issue_id, "closed", reason)

        return True

    def reopen_issue(self, issue_id: str, reason: str) -> bool:
        """Reopen a closed/resolved issue"""
        if not self.graph.has_node("issue", issue_id):
            return False

        self.graph.update_node(
            "issue",
            issue_id,
            status=IssueStatus.OPEN.value,
            resolved_at="",
            closed_at="",
            updated_at=self._now()
        )

        self.add_comment(issue_id, "reopened", reason)
        return True

    def mark_duplicate(self, issue_id: str, duplicate_of: str) -> bool:
        """Mark an issue as duplicate of another"""
        if not self.graph.has_node("issue", issue_id):
            return False
        if not self.graph.has_node("issue", duplicate_of):
            return False

        self.graph.update_node(
            "issue",
            issue_id,
            status=IssueStatus.DUPLICATE.value,
            updated_at=self._now()
        )

        self.graph.add_edge(
            "DUPLICATE_OF",
            ("issue", issue_id),
            ("issue", duplicate_of)
        )

        self.add_comment(issue_id, "duplicate", f"Duplicate of {duplicate_of}")
        return True

    def mark_wont_fix(self, issue_id: str, reason: str) -> bool:
        """Mark an issue as won't fix"""
        if not self.graph.has_node("issue", issue_id):
            return False

        self.graph.update_node(
            "issue",
            issue_id,
            status=IssueStatus.WONT_FIX.value,
            resolution=f"Won't fix: {self._sanitize(reason)}",
            updated_at=self._now()
        )

        self.add_comment(issue_id, "wont_fix", reason)
        return True

    def link_issues(
        self,
        issue_id: str,
        related_issue_id: str,
        relationship: str = "related"
    ) -> None:
        """Link two related issues"""
        if (self.graph.has_node("issue", issue_id) and
            self.graph.has_node("issue", related_issue_id)):
            self.graph.add_edge(
                "RELATED_TO",
                ("issue", issue_id),
                ("issue", related_issue_id),
                relationship=relationship
            )

    def add_workaround(self, issue_id: str, workaround: str) -> str:
        """Add a workaround for an issue"""
        workaround_id = self._make_id("wa", f"{issue_id[:10]}")

        self.graph.add_node(
            "workaround",
            workaround_id,
            issue_id=issue_id,
            description=self._sanitize(workaround),
            created_at=self._now(),
            verified="False"
        )

        if self.graph.has_node("issue", issue_id):
            self.graph.add_edge(
                "HAS_WORKAROUND",
                ("issue", issue_id),
                ("workaround", workaround_id)
            )

        return workaround_id

    # =========================================================================
    # Query Methods
    # =========================================================================

    def get_issue(self, issue_id: str) -> Optional[Dict[str, Any]]:
        """Get an issue with all its details"""
        if not self.graph.has_node("issue", issue_id):
            return None

        issue = self.graph.get_node("issue", issue_id)
        if not issue:
            return None

        result = {
            "id": issue_id,
            **issue.properties,
            "comments": [],
            "workarounds": [],
            "related_issues": []
        }

        # Get comments
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_COMMENT" and edge.source == ("issue", issue_id):
                comment = self.graph.get_node(*edge.target)
                if comment:
                    result["comments"].append(comment.properties)

        # Sort comments by date
        result["comments"].sort(key=lambda x: x.get("created_at", ""))

        # Get workarounds
        for edge in self.graph.edges():
            if edge.rel_type == "HAS_WORKAROUND" and edge.source == ("issue", issue_id):
                wa = self.graph.get_node(*edge.target)
                if wa:
                    result["workarounds"].append(wa.properties)

        # Get related issues
        for edge in self.graph.edges():
            if edge.rel_type == "RELATED_TO" and edge.source == ("issue", issue_id):
                related = self.graph.get_node(*edge.target)
                if related:
                    result["related_issues"].append({
                        "id": related.id,
                        "title": related.properties.get("title"),
                        "status": related.properties.get("status"),
                        "relationship": edge.properties.get("relationship", "related")
                    })

        return result

    def get_open_issues(
        self,
        severity: Optional[IssueSeverity] = None,
        issue_type: Optional[IssueType] = None
    ) -> List[Dict[str, Any]]:
        """Get all open issues with optional filtering"""
        open_statuses = [
            IssueStatus.OPEN.value,
            IssueStatus.INVESTIGATING.value,
            IssueStatus.IN_PROGRESS.value,
            IssueStatus.PENDING_REVIEW.value
        ]

        issues = []
        severity_val = severity.value if isinstance(severity, IssueSeverity) else severity
        type_val = issue_type.value if isinstance(issue_type, IssueType) else issue_type

        for node in self.graph.nodes():
            if node.type == "issue" and node.properties.get("status") in open_statuses:
                if severity_val and node.properties.get("severity") != severity_val:
                    continue
                if type_val and node.properties.get("issue_type") != type_val:
                    continue
                issues.append({"id": node.id, **node.properties})

        # Sort by severity then created date
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        issues.sort(key=lambda x: (
            severity_order.get(x.get("severity", "medium"), 2),
            x.get("created_at", "")
        ))

        return issues

    def get_critical_issues(self) -> List[Dict[str, Any]]:
        """Get all critical open issues"""
        return self.get_open_issues(severity=IssueSeverity.CRITICAL)

    def get_issues_by_location(self, location: str) -> List[Dict[str, Any]]:
        """Get issues affecting a specific code location"""
        issues = []
        for node in self.graph.nodes():
            if node.type == "issue":
                issue_location = node.properties.get("location", "")
                if location in issue_location or issue_location in location:
                    issues.append({"id": node.id, **node.properties})
        return issues

    def get_issues_by_task(self, task_id: str) -> List[Dict[str, Any]]:
        """Get issues blocking a task"""
        issues = []
        for edge in self.graph.edges():
            if edge.rel_type == "BLOCKS" and edge.target == ("task", task_id):
                issue = self.graph.get_node(*edge.source)
                if issue:
                    issues.append({"id": issue.id, **issue.properties})
        return issues

    def get_issues_by_goal(self, goal_id: str) -> List[Dict[str, Any]]:
        """Get issues affecting a goal"""
        issues = []
        for edge in self.graph.edges():
            if edge.rel_type == "AFFECTS" and edge.target == ("goal", goal_id):
                issue = self.graph.get_node(*edge.source)
                if issue:
                    issues.append({"id": issue.id, **issue.properties})
        return issues

    def get_resolved_issues(self, since: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get resolved issues, optionally since a date"""
        resolved = []
        for node in self.graph.nodes():
            if node.type == "issue" and node.properties.get("status") == IssueStatus.RESOLVED.value:
                resolved_at = node.properties.get("resolved_at", "")
                if since is None or resolved_at >= since:
                    resolved.append({"id": node.id, **node.properties})

        resolved.sort(key=lambda x: x.get("resolved_at", ""), reverse=True)
        return resolved

    def find_similar_issues(self, title: str, description: str = "") -> List[Dict[str, Any]]:
        """Find potentially similar or duplicate issues"""
        similar = []
        search_terms = set(title.lower().split() + description.lower().split())

        for node in self.graph.nodes():
            if node.type == "issue":
                issue_terms = set(
                    node.properties.get("title", "").lower().split() +
                    node.properties.get("description", "").lower().split()
                )
                overlap = len(search_terms & issue_terms)
                if overlap >= 2:  # At least 2 common terms
                    similar.append({
                        "id": node.id,
                        "similarity": overlap,
                        **node.properties
                    })

        similar.sort(key=lambda x: x.get("similarity", 0), reverse=True)
        return similar[:5]  # Return top 5

    def get_issue_summary(self) -> Dict[str, Any]:
        """Get a summary of all issues"""
        summary = {
            "total": 0,
            "by_status": {s.value: 0 for s in IssueStatus},
            "by_severity": {s.value: 0 for s in IssueSeverity},
            "by_type": {t.value: 0 for t in IssueType},
            "resolution_rate": 0.0,
            "avg_resolution_time": "N/A"
        }

        resolved_count = 0

        for node in self.graph.nodes():
            if node.type == "issue":
                summary["total"] += 1
                status = node.properties.get("status", IssueStatus.OPEN.value)
                severity = node.properties.get("severity", IssueSeverity.MEDIUM.value)
                issue_type = node.properties.get("issue_type", IssueType.BUG.value)

                if status in summary["by_status"]:
                    summary["by_status"][status] += 1
                if severity in summary["by_severity"]:
                    summary["by_severity"][severity] += 1
                if issue_type in summary["by_type"]:
                    summary["by_type"][issue_type] += 1

                if status in [IssueStatus.RESOLVED.value, IssueStatus.CLOSED.value]:
                    resolved_count += 1

        if summary["total"] > 0:
            summary["resolution_rate"] = resolved_count / summary["total"]

        return summary

    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant issue info for context"""
        results = []

        # Add critical issues
        critical = self.get_critical_issues()
        if critical:
            results.append({
                "type": "critical_issues",
                "issues": critical[:3]
            })

        # Add issues for current files
        files = context.get("files", [])
        for file_path in files:
            file_issues = self.get_issues_by_location(file_path)
            if file_issues:
                results.append({
                    "type": "file_issues",
                    "file": file_path,
                    "issues": file_issues[:3]
                })

        # Add recent resolved issues (for learning)
        resolved = self.get_resolved_issues()[:3]
        if resolved:
            results.append({
                "type": "recently_resolved",
                "issues": resolved
            })

        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get issue store statistics"""
        summary = self.get_issue_summary()
        return {
            "total_issues": summary["total"],
            "open": summary["by_status"].get("open", 0) +
                   summary["by_status"].get("investigating", 0) +
                   summary["by_status"].get("in_progress", 0),
            "critical": summary["by_severity"].get("critical", 0),
            "resolved": summary["by_status"].get("resolved", 0),
            "closed": summary["by_status"].get("closed", 0),
            "resolution_rate": round(summary["resolution_rate"], 2)
        }
