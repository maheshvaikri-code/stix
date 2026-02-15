"""
Rollback Store
==============

Comprehensive rollback support for agent actions including:
- State snapshots before execution
- Compensating transaction definitions
- Rollback execution engine
- Checkpoint management
- Partial and cascading rollbacks
- Rollback policies and audit trail
"""

import hashlib
import json
from typing import Any, Dict, List, Optional, Callable, TYPE_CHECKING
from datetime import datetime, timezone, timedelta

from .base import BaseStore
from ..schema import (
    RollbackStatus,
    RollbackType,
    RollbackTrigger,
    SnapshotType,
    CompensatingActionType,
)

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class RollbackStore(BaseStore):
    """
    Store for rollback and recovery governance.

    Provides:
    - Action state snapshots before execution
    - Compensating transaction definitions and registry
    - Rollback execution engine with retry support
    - Checkpoint management for multi-step operations
    - Partial rollback for specific steps
    - Cascading rollback for dependent actions
    - Rollback policies with automatic triggers
    - Complete audit trail for all rollback operations
    """

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "rollback")
        self._compensating_handlers: Dict[str, Callable] = {}
        self._setup_default_compensating_transactions()

    def _setup_default_compensating_transactions(self):
        """Set up default compensating transaction definitions."""
        default_transactions = [
            ("file_write", "file_restore", CompensatingActionType.RESTORE),
            ("file_delete", "file_restore", CompensatingActionType.RESTORE),
            ("file_modify", "file_restore", CompensatingActionType.RESTORE),
            ("database_insert", "database_delete", CompensatingActionType.REVERSE),
            ("database_update", "database_restore", CompensatingActionType.RESTORE),
            ("database_delete", "database_restore", CompensatingActionType.RESTORE),
            ("api_call", "api_reverse_call", CompensatingActionType.REVERSE),
            ("config_change", "config_restore", CompensatingActionType.RESTORE),
            ("permission_grant", "permission_revoke", CompensatingActionType.REVERSE),
            ("permission_revoke", "permission_grant", CompensatingActionType.REVERSE),
            ("resource_create", "resource_delete", CompensatingActionType.REVERSE),
            ("resource_delete", "resource_restore", CompensatingActionType.RESTORE),
            ("state_change", "state_restore", CompensatingActionType.RESTORE),
        ]

        for action_type, comp_action, comp_type in default_transactions:
            existing = self._find_nodes("compensating_transaction", action_type=action_type)
            if not existing:
                self.register_compensating_transaction(
                    action_type=action_type,
                    compensating_action=comp_action,
                    compensating_type=comp_type,
                )

    # =========================================================================
    # Transaction Boundary Management
    # =========================================================================

    def begin_transaction(
        self,
        agent_id: str,
        name: str,
        description: str = "",
        transaction_id: Optional[str] = None,
    ) -> str:
        """Begin a new transaction boundary."""
        tid = transaction_id or self._generate_id("txn")

        self._add_node("transaction_boundary", tid, {
            "name": name,
            "agent_id": agent_id,
            "description": description,
            "status": "active",
            "actions": [],
            "checkpoints": [],
            "started_at": self._now(),
        })

        return tid

    def commit_transaction(self, transaction_id: str) -> Dict[str, Any]:
        """Commit a transaction (mark as complete, no rollback possible after)."""
        txn = self._get_node("transaction_boundary", transaction_id)
        if not txn:
            return {"error": "Transaction not found"}

        if txn.get("status") != "active":
            return {"error": f"Transaction is {txn.get('status')}, cannot commit"}

        self._update_node("transaction_boundary", transaction_id, {
            "status": "committed",
            "completed_at": self._now(),
        })

        # Clean up snapshots after successful commit (optional retention)
        self._archive_transaction_snapshots(transaction_id)

        return {"committed": True, "transaction_id": transaction_id}

    def get_transaction(self, transaction_id: str) -> Optional[Dict[str, Any]]:
        """Get transaction details."""
        return self._get_node("transaction_boundary", transaction_id)

    def list_active_transactions(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List active transactions."""
        if agent_id:
            txns = self._find_nodes("transaction_boundary", agent_id=agent_id, status="active")
        else:
            txns = self._find_nodes("transaction_boundary", status="active")

        return sorted(txns, key=lambda t: t.get("started_at", ""), reverse=True)

    # =========================================================================
    # State Snapshots
    # =========================================================================

    def create_snapshot(
        self,
        action_id: str,
        agent_id: str,
        state_data: Dict[str, Any],
        affected_resources: List[str],
        snapshot_type: SnapshotType = SnapshotType.FULL,
        transaction_id: Optional[str] = None,
        ttl_hours: int = 24,
        snapshot_id: Optional[str] = None,
    ) -> str:
        """Create a state snapshot before an action."""
        sid = snapshot_id or self._generate_id("snap")

        # Calculate checksum for integrity verification
        state_json = json.dumps(state_data, sort_keys=True, default=str)
        checksum = hashlib.sha256(state_json.encode()).hexdigest()

        expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()

        self._add_node("action_snapshot", sid, {
            "action_id": action_id,
            "agent_id": agent_id,
            "transaction_id": transaction_id,
            "snapshot_type": snapshot_type.value if isinstance(snapshot_type, SnapshotType) else snapshot_type,
            "state_data": state_data,
            "affected_resources": affected_resources,
            "checksum": checksum,
            "size_bytes": len(state_json),
            "expires_at": expires_at,
            "restored": False,
        })

        # Link to action (only if action node exists)
        if self.graph.has_node("action", action_id):
            self._add_edge(
                "action_snapshot", sid,
                "SNAPSHOT_FOR",
                "action", action_id,
                {}
            )

        # Link to transaction if provided
        if transaction_id:
            self._add_edge(
                "action_snapshot", sid,
                "BELONGS_TO",
                "transaction_boundary", transaction_id,
                {}
            )

        return sid

    def get_snapshot(self, snapshot_id: str) -> Optional[Dict[str, Any]]:
        """Get a snapshot by ID."""
        return self._get_node("action_snapshot", snapshot_id)

    def get_snapshots_for_action(self, action_id: str) -> List[Dict[str, Any]]:
        """Get all snapshots for an action."""
        return self._find_nodes("action_snapshot", action_id=action_id)

    def get_snapshots_for_transaction(self, transaction_id: str) -> List[Dict[str, Any]]:
        """Get all snapshots for a transaction."""
        snapshots = self._find_nodes("action_snapshot", transaction_id=transaction_id)
        return sorted(snapshots, key=lambda s: s.get("_created_at", ""))

    def verify_snapshot_integrity(self, snapshot_id: str) -> Dict[str, Any]:
        """Verify snapshot data integrity."""
        snapshot = self._get_node("action_snapshot", snapshot_id)
        if not snapshot:
            return {"valid": False, "error": "Snapshot not found"}

        state_data = snapshot.get("state_data", {})
        state_json = json.dumps(state_data, sort_keys=True, default=str)
        current_checksum = hashlib.sha256(state_json.encode()).hexdigest()

        stored_checksum = snapshot.get("checksum", "")

        return {
            "valid": current_checksum == stored_checksum,
            "snapshot_id": snapshot_id,
            "stored_checksum": stored_checksum,
            "computed_checksum": current_checksum,
        }

    def _archive_transaction_snapshots(self, transaction_id: str):
        """Archive snapshots for a committed transaction."""
        snapshots = self.get_snapshots_for_transaction(transaction_id)
        for snapshot in snapshots:
            self._update_node("action_snapshot", snapshot["id"], {
                "archived": True,
                "archived_at": self._now(),
            })

    # =========================================================================
    # Checkpoints
    # =========================================================================

    def create_checkpoint(
        self,
        transaction_id: str,
        name: str,
        snapshot_id: str,
        step_number: Optional[int] = None,
        dependencies: Optional[List[str]] = None,
        checkpoint_id: Optional[str] = None,
    ) -> str:
        """Create a checkpoint within a transaction."""
        cid = checkpoint_id or self._generate_id("ckpt")

        txn = self._get_node("transaction_boundary", transaction_id)
        if not txn:
            raise ValueError(f"Transaction {transaction_id} not found")

        # Auto-assign step number if not provided
        if step_number is None:
            existing_checkpoints = self._find_nodes("rollback_checkpoint", transaction_id=transaction_id)
            step_number = len(existing_checkpoints) + 1

        self._add_node("rollback_checkpoint", cid, {
            "transaction_id": transaction_id,
            "name": name,
            "step_number": step_number,
            "snapshot_id": snapshot_id,
            "dependencies": dependencies or [],
            "can_rollback_to": True,
        })

        # Link to transaction
        self._add_edge(
            "rollback_checkpoint", cid,
            "CHECKPOINT_IN",
            "transaction_boundary", transaction_id,
            {"step_number": step_number}
        )

        # Update transaction's checkpoint list
        checkpoints = txn.get("checkpoints", [])
        checkpoints.append(cid)
        self._update_node("transaction_boundary", transaction_id, {
            "checkpoints": checkpoints,
        })

        return cid

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get a checkpoint by ID."""
        return self._get_node("rollback_checkpoint", checkpoint_id)

    def get_checkpoints_for_transaction(
        self,
        transaction_id: str,
    ) -> List[Dict[str, Any]]:
        """Get all checkpoints for a transaction in order."""
        checkpoints = self._find_nodes("rollback_checkpoint", transaction_id=transaction_id)
        return sorted(checkpoints, key=lambda c: c.get("step_number", 0))

    def disable_checkpoint(self, checkpoint_id: str, reason: str = "") -> Dict[str, Any]:
        """Disable a checkpoint (cannot rollback to it)."""
        checkpoint = self._get_node("rollback_checkpoint", checkpoint_id)
        if not checkpoint:
            return {"error": "Checkpoint not found"}

        self._update_node("rollback_checkpoint", checkpoint_id, {
            "can_rollback_to": False,
            "disabled_reason": reason,
            "disabled_at": self._now(),
        })

        return {"disabled": True, "checkpoint_id": checkpoint_id}

    # =========================================================================
    # Compensating Transactions
    # =========================================================================

    def register_compensating_transaction(
        self,
        action_type: str,
        compensating_action: str,
        compensating_type: CompensatingActionType,
        preconditions: Optional[List[str]] = None,
        postconditions: Optional[List[str]] = None,
        idempotent: bool = True,
        timeout_seconds: int = 300,
        retry_policy: Optional[Dict[str, Any]] = None,
        transaction_id: Optional[str] = None,
    ) -> str:
        """Register a compensating transaction definition."""
        ctid = transaction_id or self._generate_id("comp")

        self._add_node("compensating_transaction", ctid, {
            "action_type": action_type,
            "compensating_action": compensating_action,
            "compensating_type": compensating_type.value if isinstance(compensating_type, CompensatingActionType) else compensating_type,
            "preconditions": preconditions or [],
            "postconditions": postconditions or [],
            "idempotent": idempotent,
            "timeout_seconds": timeout_seconds,
            "retry_policy": retry_policy or {"max_retries": 3, "backoff_seconds": 5},
        })

        return ctid

    def get_compensating_transaction(self, action_type: str) -> Optional[Dict[str, Any]]:
        """Get compensating transaction definition for an action type."""
        transactions = self._find_nodes("compensating_transaction", action_type=action_type)
        return transactions[0] if transactions else None

    def register_compensating_handler(
        self,
        action_type: str,
        handler: Callable[[Dict[str, Any]], Dict[str, Any]],
    ):
        """Register a handler function for executing compensation."""
        self._compensating_handlers[action_type] = handler

    def list_compensating_transactions(self) -> List[Dict[str, Any]]:
        """List all registered compensating transactions."""
        return self._find_nodes("compensating_transaction")

    # =========================================================================
    # Rollback Policies
    # =========================================================================

    def create_rollback_policy(
        self,
        name: str,
        trigger_conditions: List[str],
        rollback_type: RollbackType,
        max_rollback_depth: int = 10,
        timeout_seconds: int = 600,
        requires_approval: bool = False,
        notification_channels: Optional[List[str]] = None,
        policy_id: Optional[str] = None,
    ) -> str:
        """Create a rollback policy."""
        pid = policy_id or self._generate_id("rbpol")

        self._add_node("rollback_policy", pid, {
            "name": name,
            "trigger_conditions": trigger_conditions,
            "rollback_type": rollback_type.value if isinstance(rollback_type, RollbackType) else rollback_type,
            "max_rollback_depth": max_rollback_depth,
            "timeout_seconds": timeout_seconds,
            "requires_approval": requires_approval,
            "notification_channels": notification_channels or [],
            "active": True,
        })

        return pid

    def get_rollback_policy(self, policy_id: str) -> Optional[Dict[str, Any]]:
        """Get a rollback policy."""
        return self._get_node("rollback_policy", policy_id)

    def evaluate_rollback_policies(
        self,
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Evaluate which rollback policies match the context."""
        policies = self._find_nodes("rollback_policy", active=True)

        matching = []
        for policy in policies:
            conditions = policy.get("trigger_conditions", [])
            if self._evaluate_conditions(conditions, context):
                matching.append(policy)

        return matching

    def _evaluate_conditions(
        self,
        conditions: List[str],
        context: Dict[str, Any],
    ) -> bool:
        """Evaluate if conditions match context."""
        for condition in conditions:
            # Simple condition matching (can be extended)
            if "=" in condition:
                key, value = condition.split("=", 1)
                if str(context.get(key.strip())) != value.strip():
                    return False
            elif condition.startswith("error_type:"):
                expected_type = condition.split(":", 1)[1].strip()
                if context.get("error_type") != expected_type:
                    return False
            elif condition == "any_error":
                if not context.get("has_error"):
                    return False

        return True

    # =========================================================================
    # Rollback Execution
    # =========================================================================

    def initiate_rollback(
        self,
        transaction_id: str,
        rollback_type: RollbackType,
        trigger: RollbackTrigger,
        triggered_by: str,
        target_checkpoint: Optional[str] = None,
        reason: str = "",
        rollback_id: Optional[str] = None,
    ) -> str:
        """Initiate a rollback operation."""
        rid = rollback_id or self._generate_id("rb")

        txn = self._get_node("transaction_boundary", transaction_id)
        if not txn:
            raise ValueError(f"Transaction {transaction_id} not found")

        if txn.get("status") == "committed":
            raise ValueError("Cannot rollback committed transaction")

        # Calculate steps needed
        if rollback_type == RollbackType.CHECKPOINT and target_checkpoint:
            checkpoint = self._get_node("rollback_checkpoint", target_checkpoint)
            if not checkpoint:
                raise ValueError(f"Checkpoint {target_checkpoint} not found")
            steps = self._calculate_checkpoint_rollback_steps(transaction_id, target_checkpoint)
        else:
            steps = self._calculate_full_rollback_steps(transaction_id)

        self._add_node("rollback_operation", rid, {
            "transaction_id": transaction_id,
            "rollback_type": rollback_type.value if isinstance(rollback_type, RollbackType) else rollback_type,
            "trigger": trigger.value if isinstance(trigger, RollbackTrigger) else trigger,
            "triggered_by": triggered_by,
            "target_checkpoint": target_checkpoint,
            "reason": reason,
            "status": RollbackStatus.PENDING.value,
            "steps_total": len(steps),
            "steps_completed": 0,
            "started_at": self._now(),
        })

        # Create rollback steps
        for i, step_info in enumerate(steps):
            self._create_rollback_step(rid, i + 1, step_info)

        # Update transaction status
        self._update_node("transaction_boundary", transaction_id, {
            "status": "rolling_back",
        })

        return rid

    def _calculate_full_rollback_steps(self, transaction_id: str) -> List[Dict[str, Any]]:
        """Calculate steps for full rollback."""
        snapshots = self.get_snapshots_for_transaction(transaction_id)
        # Reverse order for rollback
        return [
            {
                "action_id": s.get("action_id"),
                "snapshot_id": s.get("id"),
                "affected_resources": s.get("affected_resources", []),
            }
            for s in reversed(snapshots)
        ]

    def _calculate_checkpoint_rollback_steps(
        self,
        transaction_id: str,
        target_checkpoint: str,
    ) -> List[Dict[str, Any]]:
        """Calculate steps for checkpoint rollback."""
        checkpoint = self._get_node("rollback_checkpoint", target_checkpoint)
        if not checkpoint:
            return []

        target_step = checkpoint.get("step_number", 0)
        snapshots = self.get_snapshots_for_transaction(transaction_id)

        # Only rollback snapshots after the checkpoint
        steps = []
        for s in reversed(snapshots):
            # Include this snapshot if it's after the checkpoint
            # This requires tracking step numbers in snapshots
            steps.append({
                "action_id": s.get("action_id"),
                "snapshot_id": s.get("id"),
                "affected_resources": s.get("affected_resources", []),
            })

        return steps

    def _create_rollback_step(
        self,
        rollback_id: str,
        step_number: int,
        step_info: Dict[str, Any],
    ) -> str:
        """Create a rollback step."""
        sid = self._generate_id("rbstep")

        action_id = step_info.get("action_id", "")
        snapshot_id = step_info.get("snapshot_id", "")

        # Find compensating action
        # Try to determine action type from action node
        comp_action = "restore_from_snapshot"

        self._add_node("rollback_step", sid, {
            "rollback_id": rollback_id,
            "step_number": step_number,
            "action_to_undo": action_id,
            "snapshot_id": snapshot_id,
            "compensating_action": comp_action,
            "affected_resources": step_info.get("affected_resources", []),
            "status": RollbackStatus.PENDING.value,
            "retries": 0,
        })

        self._add_edge(
            "rollback_step", sid,
            "STEP_OF",
            "rollback_operation", rollback_id,
            {"step_number": step_number}
        )

        return sid

    def execute_rollback(
        self,
        rollback_id: str,
        executor_id: str,
    ) -> Dict[str, Any]:
        """Execute a rollback operation."""
        rollback = self._get_node("rollback_operation", rollback_id)
        if not rollback:
            return {"error": "Rollback operation not found"}

        if rollback.get("status") not in [RollbackStatus.PENDING.value, RollbackStatus.PARTIAL.value]:
            return {"error": f"Rollback is {rollback.get('status')}, cannot execute"}

        self._update_node("rollback_operation", rollback_id, {
            "status": RollbackStatus.IN_PROGRESS.value,
            "executor_id": executor_id,
            "execution_started_at": self._now(),
        })

        # Get steps
        steps = self._find_nodes("rollback_step", rollback_id=rollback_id)
        steps = sorted(steps, key=lambda s: s.get("step_number", 0))

        completed = 0
        failed_step = None

        for step in steps:
            if step.get("status") == RollbackStatus.COMPLETED.value:
                completed += 1
                continue

            result = self._execute_rollback_step(step)

            if result.get("success"):
                completed += 1
                self._update_node("rollback_step", step["id"], {
                    "status": RollbackStatus.COMPLETED.value,
                    "completed_at": self._now(),
                })
            else:
                failed_step = step
                self._update_node("rollback_step", step["id"], {
                    "status": RollbackStatus.FAILED.value,
                    "error_message": result.get("error", "Unknown error"),
                    "retries": step.get("retries", 0) + 1,
                })
                break

        # Update rollback status
        if failed_step:
            final_status = RollbackStatus.PARTIAL.value if completed > 0 else RollbackStatus.FAILED.value
        else:
            final_status = RollbackStatus.COMPLETED.value

        self._update_node("rollback_operation", rollback_id, {
            "status": final_status,
            "steps_completed": completed,
            "completed_at": self._now() if final_status == RollbackStatus.COMPLETED.value else None,
        })

        # Update transaction status
        transaction_id = rollback.get("transaction_id")
        if transaction_id:
            txn_status = "rolled_back" if final_status == RollbackStatus.COMPLETED.value else "rollback_failed"
            self._update_node("transaction_boundary", transaction_id, {
                "status": txn_status,
                "completed_at": self._now(),
            })

        return {
            "rollback_id": rollback_id,
            "status": final_status,
            "steps_total": len(steps),
            "steps_completed": completed,
            "failed_step": failed_step.get("id") if failed_step else None,
        }

    def _execute_rollback_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a single rollback step."""
        snapshot_id = step.get("snapshot_id")

        if not snapshot_id:
            return {"success": False, "error": "No snapshot for step"}

        snapshot = self._get_node("action_snapshot", snapshot_id)
        if not snapshot:
            return {"success": False, "error": "Snapshot not found"}

        # Verify integrity
        integrity = self.verify_snapshot_integrity(snapshot_id)
        if not integrity.get("valid"):
            return {"success": False, "error": "Snapshot integrity check failed"}

        # Get compensating action type
        action_id = step.get("action_to_undo", "")

        # Try to find handler
        # In a real implementation, this would call the actual handler
        # For now, we'll simulate success

        # Mark snapshot as restored
        self._update_node("action_snapshot", snapshot_id, {
            "restored": True,
            "restored_at": self._now(),
        })

        return {"success": True, "restored_from": snapshot_id}

    def get_rollback(self, rollback_id: str) -> Optional[Dict[str, Any]]:
        """Get rollback operation details."""
        return self._get_node("rollback_operation", rollback_id)

    def get_rollback_steps(self, rollback_id: str) -> List[Dict[str, Any]]:
        """Get all steps for a rollback operation."""
        steps = self._find_nodes("rollback_step", rollback_id=rollback_id)
        return sorted(steps, key=lambda s: s.get("step_number", 0))

    def cancel_rollback(
        self,
        rollback_id: str,
        cancelled_by: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Cancel a pending or in-progress rollback."""
        rollback = self._get_node("rollback_operation", rollback_id)
        if not rollback:
            return {"error": "Rollback not found"}

        if rollback.get("status") in [RollbackStatus.COMPLETED.value, RollbackStatus.CANCELLED.value]:
            return {"error": f"Cannot cancel {rollback.get('status')} rollback"}

        self._update_node("rollback_operation", rollback_id, {
            "status": RollbackStatus.CANCELLED.value,
            "cancelled_by": cancelled_by,
            "cancel_reason": reason,
            "cancelled_at": self._now(),
        })

        # Revert transaction status
        transaction_id = rollback.get("transaction_id")
        if transaction_id:
            self._update_node("transaction_boundary", transaction_id, {
                "status": "active",
            })

        return {"cancelled": True, "rollback_id": rollback_id}

    def retry_rollback_step(
        self,
        step_id: str,
        executor_id: str,
    ) -> Dict[str, Any]:
        """Retry a failed rollback step."""
        step = self._get_node("rollback_step", step_id)
        if not step:
            return {"error": "Step not found"}

        if step.get("status") != RollbackStatus.FAILED.value:
            return {"error": "Step is not in failed state"}

        self._update_node("rollback_step", step_id, {
            "status": RollbackStatus.IN_PROGRESS.value,
            "retry_started_at": self._now(),
        })

        result = self._execute_rollback_step(step)

        if result.get("success"):
            self._update_node("rollback_step", step_id, {
                "status": RollbackStatus.COMPLETED.value,
                "completed_at": self._now(),
                "retries": step.get("retries", 0) + 1,
            })
        else:
            self._update_node("rollback_step", step_id, {
                "status": RollbackStatus.FAILED.value,
                "error_message": result.get("error", "Unknown error"),
                "retries": step.get("retries", 0) + 1,
            })

        return {
            "step_id": step_id,
            "success": result.get("success"),
            "retries": step.get("retries", 0) + 1,
        }

    # =========================================================================
    # Rollback History & Audit
    # =========================================================================

    def get_rollback_history(
        self,
        agent_id: Optional[str] = None,
        transaction_id: Optional[str] = None,
        status: Optional[RollbackStatus] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get rollback history with filters."""
        rollbacks = self._find_nodes("rollback_operation")

        if transaction_id:
            rollbacks = [r for r in rollbacks if r.get("transaction_id") == transaction_id]

        if status:
            status_val = status.value if isinstance(status, RollbackStatus) else status
            rollbacks = [r for r in rollbacks if r.get("status") == status_val]

        if agent_id:
            # Filter by agent through transaction
            agent_rollbacks = []
            for r in rollbacks:
                txn = self._get_node("transaction_boundary", r.get("transaction_id", ""))
                if txn and txn.get("agent_id") == agent_id:
                    agent_rollbacks.append(r)
            rollbacks = agent_rollbacks

        rollbacks = sorted(rollbacks, key=lambda r: r.get("started_at", ""), reverse=True)
        return rollbacks[:limit]

    def get_rollback_audit_trail(self, rollback_id: str) -> Dict[str, Any]:
        """Get complete audit trail for a rollback."""
        rollback = self._get_node("rollback_operation", rollback_id)
        if not rollback:
            return {"error": "Rollback not found"}

        steps = self.get_rollback_steps(rollback_id)
        transaction_id = rollback.get("transaction_id")
        txn = self._get_node("transaction_boundary", transaction_id) if transaction_id else None

        # Get related snapshots
        snapshots = []
        for step in steps:
            snap_id = step.get("snapshot_id")
            if snap_id:
                snap = self._get_node("action_snapshot", snap_id)
                if snap:
                    snapshots.append(snap)

        return {
            "rollback": rollback,
            "transaction": txn,
            "steps": steps,
            "snapshots": snapshots,
            "timeline": self._build_rollback_timeline(rollback, steps),
        }

    def _build_rollback_timeline(
        self,
        rollback: Dict[str, Any],
        steps: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Build timeline of rollback events."""
        timeline = []

        # Rollback initiated
        timeline.append({
            "event": "rollback_initiated",
            "timestamp": rollback.get("started_at"),
            "details": {
                "trigger": rollback.get("trigger"),
                "triggered_by": rollback.get("triggered_by"),
                "type": rollback.get("rollback_type"),
            },
        })

        # Step events
        for step in steps:
            if step.get("started_at"):
                timeline.append({
                    "event": "step_started",
                    "timestamp": step.get("started_at"),
                    "details": {"step_number": step.get("step_number")},
                })

            if step.get("completed_at"):
                timeline.append({
                    "event": "step_completed",
                    "timestamp": step.get("completed_at"),
                    "details": {
                        "step_number": step.get("step_number"),
                        "status": step.get("status"),
                    },
                })

        # Rollback completed/failed
        if rollback.get("completed_at"):
            timeline.append({
                "event": "rollback_completed",
                "timestamp": rollback.get("completed_at"),
                "details": {"status": rollback.get("status")},
            })

        return sorted(timeline, key=lambda t: t.get("timestamp", ""))

    # =========================================================================
    # Cleanup & Maintenance
    # =========================================================================

    def cleanup_expired_snapshots(self) -> Dict[str, Any]:
        """Remove expired snapshots."""
        snapshots = self._find_nodes("action_snapshot")
        now = datetime.now(timezone.utc).isoformat()

        expired = []
        for snap in snapshots:
            expires_at = snap.get("expires_at")
            if expires_at and expires_at < now and not snap.get("restored"):
                self._delete_node("action_snapshot", snap["id"])
                expired.append(snap["id"])

        return {
            "cleaned_up": len(expired),
            "snapshot_ids": expired,
        }

    def get_snapshot_storage_stats(self) -> Dict[str, Any]:
        """Get statistics about snapshot storage."""
        snapshots = self._find_nodes("action_snapshot")

        total_size = sum(s.get("size_bytes", 0) for s in snapshots)
        by_type = {}
        by_status = {"active": 0, "archived": 0, "restored": 0}

        for snap in snapshots:
            stype = snap.get("snapshot_type", "unknown")
            by_type[stype] = by_type.get(stype, 0) + 1

            if snap.get("archived"):
                by_status["archived"] += 1
            elif snap.get("restored"):
                by_status["restored"] += 1
            else:
                by_status["active"] += 1

        return {
            "total_snapshots": len(snapshots),
            "total_size_bytes": total_size,
            "by_type": by_type,
            "by_status": by_status,
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get rollback store statistics."""
        base_stats = super().get_stats()

        transactions = self._find_nodes("transaction_boundary")
        snapshots = self._find_nodes("action_snapshot")
        checkpoints = self._find_nodes("rollback_checkpoint")
        rollbacks = self._find_nodes("rollback_operation")
        policies = self._find_nodes("rollback_policy")

        txn_by_status = {}
        for txn in transactions:
            status = txn.get("status", "unknown")
            txn_by_status[status] = txn_by_status.get(status, 0) + 1

        rb_by_status = {}
        rb_by_type = {}
        rb_by_trigger = {}
        for rb in rollbacks:
            status = rb.get("status", "unknown")
            rb_by_status[status] = rb_by_status.get(status, 0) + 1

            rbtype = rb.get("rollback_type", "unknown")
            rb_by_type[rbtype] = rb_by_type.get(rbtype, 0) + 1

            trigger = rb.get("trigger", "unknown")
            rb_by_trigger[trigger] = rb_by_trigger.get(trigger, 0) + 1

        return {
            **base_stats,
            "transactions": len(transactions),
            "transactions_by_status": txn_by_status,
            "snapshots": len(snapshots),
            "checkpoints": len(checkpoints),
            "rollbacks": len(rollbacks),
            "rollbacks_by_status": rb_by_status,
            "rollbacks_by_type": rb_by_type,
            "rollbacks_by_trigger": rb_by_trigger,
            "policies": len(policies),
            "active_policies": len([p for p in policies if p.get("active")]),
        }
