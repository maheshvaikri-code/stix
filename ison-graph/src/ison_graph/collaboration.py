#!/usr/bin/env python3
"""
ISONGraph Collaboration Module

Provides multi-agent collaboration features:
- Graph transactions with rollback
- Conflict detection and resolution
- Version control (branching/merging)

Usage:
    from ison_graph import ISONGraph
    from ison_graph.collaboration import CollaborativeGraph, GraphTransaction

    # Create collaborative graph
    collab = CollaborativeGraph(graph)

    # Agent 1 transaction
    tx1 = collab.begin_transaction('agent-1')
    tx1.add_node('person', 'alice', name='Alice')
    tx1.add_edge('KNOWS', ('person', 'alice'), ('person', 'bob'))
    result = await collab.commit(tx1)

    # Branching
    branch = collab.branch('experiment')
    # ... work on branch ...
    collab.merge(branch)
"""

from __future__ import annotations

import copy
import time
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Optional, Set, Tuple,
    Callable, Union
)
from enum import Enum
from collections import defaultdict

from . import ISONGraph, Node, Edge, NodeRef, EdgeKey


# =============================================================================
# Operation Types
# =============================================================================

class OperationType(Enum):
    """Types of graph operations"""
    ADD_NODE = "add_node"
    UPDATE_NODE = "update_node"
    REMOVE_NODE = "remove_node"
    ADD_EDGE = "add_edge"
    UPDATE_EDGE = "update_edge"
    REMOVE_EDGE = "remove_edge"


@dataclass
class Operation:
    """A single graph operation"""
    type: OperationType
    timestamp: float
    agent_id: str

    # For node operations
    node_type: Optional[str] = None
    node_id: Optional[Union[int, str]] = None
    properties: Dict[str, Any] = field(default_factory=dict)

    # For edge operations
    rel_type: Optional[str] = None
    source: Optional[NodeRef] = None
    target: Optional[NodeRef] = None

    @property
    def node_ref(self) -> Optional[NodeRef]:
        if self.node_type and self.node_id is not None:
            return (self.node_type, self.node_id)
        return None

    @property
    def edge_key(self) -> Optional[EdgeKey]:
        if self.rel_type and self.source and self.target:
            return (self.rel_type, self.source, self.target)
        return None


# =============================================================================
# Graph Transaction
# =============================================================================

class GraphTransaction:
    """
    A transaction for batching graph operations.

    Supports:
    - Atomic commit/rollback
    - Operation batching
    - Fluent API
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.operations: List[Operation] = []
        self.started_at = time.time()
        self._committed = False
        self._rolled_back = False

    def add_node(
        self,
        node_type: str,
        node_id: Union[int, str],
        **properties: Any
    ) -> 'GraphTransaction':
        """Add a node to the transaction"""
        self._check_active()
        self.operations.append(Operation(
            type=OperationType.ADD_NODE,
            timestamp=time.time(),
            agent_id=self.agent_id,
            node_type=node_type,
            node_id=node_id,
            properties=properties
        ))
        return self

    def update_node(
        self,
        node_type: str,
        node_id: Union[int, str],
        **properties: Any
    ) -> 'GraphTransaction':
        """Update a node in the transaction"""
        self._check_active()
        self.operations.append(Operation(
            type=OperationType.UPDATE_NODE,
            timestamp=time.time(),
            agent_id=self.agent_id,
            node_type=node_type,
            node_id=node_id,
            properties=properties
        ))
        return self

    def remove_node(
        self,
        node_type: str,
        node_id: Union[int, str]
    ) -> 'GraphTransaction':
        """Remove a node in the transaction"""
        self._check_active()
        self.operations.append(Operation(
            type=OperationType.REMOVE_NODE,
            timestamp=time.time(),
            agent_id=self.agent_id,
            node_type=node_type,
            node_id=node_id
        ))
        return self

    def add_edge(
        self,
        rel_type: str,
        source: NodeRef,
        target: NodeRef,
        **properties: Any
    ) -> 'GraphTransaction':
        """Add an edge to the transaction"""
        self._check_active()
        self.operations.append(Operation(
            type=OperationType.ADD_EDGE,
            timestamp=time.time(),
            agent_id=self.agent_id,
            rel_type=rel_type,
            source=source,
            target=target,
            properties=properties
        ))
        return self

    def remove_edge(
        self,
        rel_type: str,
        source: NodeRef,
        target: NodeRef
    ) -> 'GraphTransaction':
        """Remove an edge in the transaction"""
        self._check_active()
        self.operations.append(Operation(
            type=OperationType.REMOVE_EDGE,
            timestamp=time.time(),
            agent_id=self.agent_id,
            rel_type=rel_type,
            source=source,
            target=target
        ))
        return self

    def get_operations(self) -> List[Operation]:
        """Get all operations in the transaction"""
        return list(self.operations)

    def is_active(self) -> bool:
        """Check if transaction is still active"""
        return not self._committed and not self._rolled_back

    def _check_active(self) -> None:
        """Ensure transaction is active"""
        if self._committed:
            raise RuntimeError("Transaction already committed")
        if self._rolled_back:
            raise RuntimeError("Transaction already rolled back")

    def _mark_committed(self) -> None:
        self._committed = True

    def _mark_rolled_back(self) -> None:
        self._rolled_back = True


# =============================================================================
# Conflict Types
# =============================================================================

class ConflictType(Enum):
    """Types of conflicts"""
    CONCURRENT_UPDATE = "concurrent_update"
    DELETE_UPDATE = "delete_update"
    DUPLICATE_CREATE = "duplicate_create"


class ResolutionStrategy(Enum):
    """Strategies for resolving conflicts"""
    LAST_WRITE_WINS = "last_write_wins"
    FIRST_WRITE_WINS = "first_write_wins"
    MERGE = "merge"
    MANUAL = "manual"


@dataclass
class Conflict:
    """Represents a conflict between operations"""
    type: ConflictType
    operations: List[Operation]
    entity_type: str  # 'node' or 'edge'
    entity_id: Any  # NodeRef or EdgeKey
    description: str = ""


@dataclass
class Resolution:
    """Resolution for a conflict"""
    conflict: Conflict
    strategy: ResolutionStrategy
    winning_operation: Optional[Operation] = None
    merged_properties: Optional[Dict[str, Any]] = None


# =============================================================================
# Conflict Resolver
# =============================================================================

class ConflictResolver:
    """
    Detects and resolves conflicts between operations.
    """

    def __init__(self, default_strategy: ResolutionStrategy = ResolutionStrategy.LAST_WRITE_WINS):
        self.default_strategy = default_strategy

    def detect_conflicts(
        self,
        ops1: List[Operation],
        ops2: List[Operation]
    ) -> List[Conflict]:
        """
        Detect conflicts between two sets of operations.

        Args:
            ops1: First set of operations
            ops2: Second set of operations

        Returns:
            List of detected conflicts
        """
        conflicts = []

        # Group operations by entity
        node_ops1 = self._group_node_ops(ops1)
        node_ops2 = self._group_node_ops(ops2)
        edge_ops1 = self._group_edge_ops(ops1)
        edge_ops2 = self._group_edge_ops(ops2)

        # Check node conflicts
        for node_ref in set(node_ops1.keys()) & set(node_ops2.keys()):
            conflict = self._check_node_conflict(
                node_ref,
                node_ops1[node_ref],
                node_ops2[node_ref]
            )
            if conflict:
                conflicts.append(conflict)

        # Check edge conflicts
        for edge_key in set(edge_ops1.keys()) & set(edge_ops2.keys()):
            conflict = self._check_edge_conflict(
                edge_key,
                edge_ops1[edge_key],
                edge_ops2[edge_key]
            )
            if conflict:
                conflicts.append(conflict)

        return conflicts

    def resolve(
        self,
        conflict: Conflict,
        strategy: Optional[ResolutionStrategy] = None
    ) -> Resolution:
        """
        Resolve a conflict using the specified strategy.

        Args:
            conflict: The conflict to resolve
            strategy: Resolution strategy (uses default if not specified)

        Returns:
            Resolution object
        """
        strategy = strategy or self.default_strategy

        if strategy == ResolutionStrategy.LAST_WRITE_WINS:
            winning = max(conflict.operations, key=lambda o: o.timestamp)
            return Resolution(
                conflict=conflict,
                strategy=strategy,
                winning_operation=winning
            )

        elif strategy == ResolutionStrategy.FIRST_WRITE_WINS:
            winning = min(conflict.operations, key=lambda o: o.timestamp)
            return Resolution(
                conflict=conflict,
                strategy=strategy,
                winning_operation=winning
            )

        elif strategy == ResolutionStrategy.MERGE:
            merged = {}
            for op in sorted(conflict.operations, key=lambda o: o.timestamp):
                merged.update(op.properties)
            return Resolution(
                conflict=conflict,
                strategy=strategy,
                merged_properties=merged
            )

        else:  # MANUAL
            return Resolution(
                conflict=conflict,
                strategy=strategy
            )

    def _group_node_ops(self, ops: List[Operation]) -> Dict[NodeRef, List[Operation]]:
        """Group operations by node reference"""
        grouped: Dict[NodeRef, List[Operation]] = defaultdict(list)
        for op in ops:
            if op.node_ref:
                grouped[op.node_ref].append(op)
        return grouped

    def _group_edge_ops(self, ops: List[Operation]) -> Dict[EdgeKey, List[Operation]]:
        """Group operations by edge key"""
        grouped: Dict[EdgeKey, List[Operation]] = defaultdict(list)
        for op in ops:
            if op.edge_key:
                grouped[op.edge_key].append(op)
        return grouped

    def _check_node_conflict(
        self,
        node_ref: NodeRef,
        ops1: List[Operation],
        ops2: List[Operation]
    ) -> Optional[Conflict]:
        """Check for conflicts on a specific node"""
        types1 = {op.type for op in ops1}
        types2 = {op.type for op in ops2}

        # Check for concurrent updates
        if (OperationType.UPDATE_NODE in types1 and
            OperationType.UPDATE_NODE in types2):
            return Conflict(
                type=ConflictType.CONCURRENT_UPDATE,
                operations=ops1 + ops2,
                entity_type='node',
                entity_id=node_ref,
                description=f"Concurrent update on node {node_ref}"
            )

        # Check for delete/update conflict
        if ((OperationType.REMOVE_NODE in types1 and
             OperationType.UPDATE_NODE in types2) or
            (OperationType.UPDATE_NODE in types1 and
             OperationType.REMOVE_NODE in types2)):
            return Conflict(
                type=ConflictType.DELETE_UPDATE,
                operations=ops1 + ops2,
                entity_type='node',
                entity_id=node_ref,
                description=f"Delete/update conflict on node {node_ref}"
            )

        # Check for duplicate create
        if (OperationType.ADD_NODE in types1 and
            OperationType.ADD_NODE in types2):
            return Conflict(
                type=ConflictType.DUPLICATE_CREATE,
                operations=ops1 + ops2,
                entity_type='node',
                entity_id=node_ref,
                description=f"Duplicate create on node {node_ref}"
            )

        return None

    def _check_edge_conflict(
        self,
        edge_key: EdgeKey,
        ops1: List[Operation],
        ops2: List[Operation]
    ) -> Optional[Conflict]:
        """Check for conflicts on a specific edge"""
        types1 = {op.type for op in ops1}
        types2 = {op.type for op in ops2}

        # Check for duplicate create
        if (OperationType.ADD_EDGE in types1 and
            OperationType.ADD_EDGE in types2):
            return Conflict(
                type=ConflictType.DUPLICATE_CREATE,
                operations=ops1 + ops2,
                entity_type='edge',
                entity_id=edge_key,
                description=f"Duplicate create on edge {edge_key}"
            )

        return None


# =============================================================================
# Version Entry
# =============================================================================

@dataclass
class VersionEntry:
    """A version in the graph history"""
    version: int
    agent_id: str
    timestamp: float
    operations: List[Operation]
    message: str = ""


# =============================================================================
# Commit Result
# =============================================================================

@dataclass
class CommitResult:
    """Result of a commit operation"""
    success: bool
    version: int = 0
    conflicts: List[Conflict] = field(default_factory=list)
    resolutions: List[Resolution] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class MergeResult:
    """Result of a merge operation"""
    success: bool
    conflicts: List[Conflict] = field(default_factory=list)
    resolutions: List[Resolution] = field(default_factory=list)
    error: Optional[str] = None


# =============================================================================
# Collaborative Graph
# =============================================================================

class CollaborativeGraph:
    """
    A graph with multi-agent collaboration support.

    Features:
    - Transaction-based editing
    - Conflict detection and resolution
    - Version control with branching
    """

    def __init__(
        self,
        graph: ISONGraph,
        conflict_resolver: Optional[ConflictResolver] = None
    ):
        self.graph = graph
        self.conflict_resolver = conflict_resolver or ConflictResolver()
        self._version = 0
        self._history: List[VersionEntry] = []
        self._pending_transactions: Dict[str, GraphTransaction] = {}
        self._branch_name = "main"
        self._parent: Optional['CollaborativeGraph'] = None

    def begin_transaction(self, agent_id: str) -> GraphTransaction:
        """
        Begin a new transaction.

        Args:
            agent_id: Identifier for the agent

        Returns:
            New GraphTransaction
        """
        tx = GraphTransaction(agent_id)
        self._pending_transactions[agent_id] = tx
        return tx

    async def commit(
        self,
        transaction: GraphTransaction,
        message: str = ""
    ) -> CommitResult:
        """
        Commit a transaction.

        Args:
            transaction: The transaction to commit
            message: Optional commit message

        Returns:
            CommitResult with success status and any conflicts
        """
        if not transaction.is_active():
            return CommitResult(
                success=False,
                error="Transaction is not active"
            )

        # Check for conflicts with other pending transactions
        conflicts = []
        resolutions = []

        for other_id, other_tx in self._pending_transactions.items():
            if other_id != transaction.agent_id and other_tx.is_active():
                detected = self.conflict_resolver.detect_conflicts(
                    transaction.get_operations(),
                    other_tx.get_operations()
                )
                conflicts.extend(detected)

        # Resolve conflicts
        for conflict in conflicts:
            resolution = self.conflict_resolver.resolve(conflict)
            resolutions.append(resolution)

        # Apply operations
        try:
            self._apply_operations(transaction.get_operations(), resolutions)
            transaction._mark_committed()

            # Update version and history
            self._version += 1
            self._history.append(VersionEntry(
                version=self._version,
                agent_id=transaction.agent_id,
                timestamp=time.time(),
                operations=transaction.get_operations(),
                message=message
            ))

            # Remove from pending
            if transaction.agent_id in self._pending_transactions:
                del self._pending_transactions[transaction.agent_id]

            return CommitResult(
                success=True,
                version=self._version,
                conflicts=conflicts,
                resolutions=resolutions
            )

        except Exception as e:
            transaction._mark_rolled_back()
            return CommitResult(
                success=False,
                error=str(e),
                conflicts=conflicts
            )

    def rollback(self, transaction: GraphTransaction) -> None:
        """Roll back a transaction"""
        transaction._mark_rolled_back()
        if transaction.agent_id in self._pending_transactions:
            del self._pending_transactions[transaction.agent_id]

    def branch(self, name: str, agent_id: str = "system") -> 'CollaborativeGraph':
        """
        Create a branch of the graph.

        Args:
            name: Branch name
            agent_id: Agent creating the branch

        Returns:
            New CollaborativeGraph representing the branch
        """
        # Create deep copy of graph
        branch_graph = ISONGraph(
            name=f"{self.graph.name}:{name}",
            directed=self.graph.directed
        )

        # Copy nodes
        for node in self.graph.nodes():
            branch_graph.add_node(
                node.type,
                node.id,
                **copy.deepcopy(node.properties)
            )

        # Copy edges
        for edge in self.graph.edges():
            branch_graph.add_edge(
                edge.rel_type,
                edge.source,
                edge.target,
                **copy.deepcopy(edge.properties)
            )

        # Create branch collaborative graph
        branch = CollaborativeGraph(branch_graph, self.conflict_resolver)
        branch._version = self._version
        branch._history = list(self._history)
        branch._branch_name = name
        branch._parent = self

        return branch

    def merge(
        self,
        source: 'CollaborativeGraph',
        strategy: ResolutionStrategy = ResolutionStrategy.MERGE,
        on_conflict: Optional[Callable[[Conflict], Resolution]] = None
    ) -> MergeResult:
        """
        Merge another branch into this one.

        Args:
            source: Source branch to merge from
            strategy: Default conflict resolution strategy
            on_conflict: Optional callback for custom conflict resolution

        Returns:
            MergeResult with success status and conflicts
        """
        # Find operations since branch point
        branch_ops = []
        for entry in source._history:
            if entry.version > self._version:
                branch_ops.extend(entry.operations)

        # Detect conflicts with current state
        current_ops = []
        for entry in self._history:
            if entry.version > source._history[0].version if source._history else 0:
                current_ops.extend(entry.operations)

        conflicts = self.conflict_resolver.detect_conflicts(current_ops, branch_ops)

        # Resolve conflicts
        resolutions = []
        for conflict in conflicts:
            if on_conflict:
                resolution = on_conflict(conflict)
            else:
                resolution = self.conflict_resolver.resolve(conflict, strategy)
            resolutions.append(resolution)

        # Apply operations
        try:
            self._apply_operations(branch_ops, resolutions)

            self._version += 1
            self._history.append(VersionEntry(
                version=self._version,
                agent_id="merge",
                timestamp=time.time(),
                operations=branch_ops,
                message=f"Merged branch '{source._branch_name}'"
            ))

            return MergeResult(
                success=True,
                conflicts=conflicts,
                resolutions=resolutions
            )

        except Exception as e:
            return MergeResult(
                success=False,
                error=str(e),
                conflicts=conflicts
            )

    def get_history(self) -> List[VersionEntry]:
        """Get version history"""
        return list(self._history)

    def get_version(self) -> int:
        """Get current version number"""
        return self._version

    def _apply_operations(
        self,
        operations: List[Operation],
        resolutions: List[Resolution]
    ) -> None:
        """Apply operations to the graph"""
        # Build resolution map
        resolved_ops = set()
        resolution_data = {}

        for resolution in resolutions:
            for op in resolution.conflict.operations:
                resolved_ops.add(id(op))
                if resolution.winning_operation:
                    resolution_data[id(op)] = resolution.winning_operation
                elif resolution.merged_properties:
                    resolution_data[id(op)] = resolution.merged_properties

        for op in operations:
            # Skip if this operation was part of a conflict and wasn't the winner
            if id(op) in resolved_ops:
                winning = resolution_data.get(id(op))
                if winning and winning != op:
                    continue

            try:
                self._apply_single_operation(op)
            except Exception:
                # Continue on error for resilience
                pass

    def _apply_single_operation(self, op: Operation) -> None:
        """Apply a single operation to the graph"""
        if op.type == OperationType.ADD_NODE:
            if not self.graph.has_node(op.node_type, op.node_id):
                self.graph.add_node(op.node_type, op.node_id, **op.properties)

        elif op.type == OperationType.UPDATE_NODE:
            if self.graph.has_node(op.node_type, op.node_id):
                self.graph.update_node(op.node_type, op.node_id, **op.properties)

        elif op.type == OperationType.REMOVE_NODE:
            if self.graph.has_node(op.node_type, op.node_id):
                self.graph.remove_node(op.node_type, op.node_id)

        elif op.type == OperationType.ADD_EDGE:
            if not self.graph.has_edge(op.rel_type, op.source, op.target):
                self.graph.add_edge(op.rel_type, op.source, op.target, **op.properties)

        elif op.type == OperationType.REMOVE_EDGE:
            if self.graph.has_edge(op.rel_type, op.source, op.target):
                self.graph.remove_edge(op.rel_type, op.source, op.target)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Operations
    'OperationType',
    'Operation',

    # Transaction
    'GraphTransaction',

    # Conflicts
    'ConflictType',
    'ResolutionStrategy',
    'Conflict',
    'Resolution',
    'ConflictResolver',

    # Version Control
    'VersionEntry',
    'CommitResult',
    'MergeResult',

    # Main Class
    'CollaborativeGraph',
]
