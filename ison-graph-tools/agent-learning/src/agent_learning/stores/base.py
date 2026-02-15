"""
Base Store for Agent Learning
=============================

Abstract base class for all agent learning stores.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

from ison_graph import ISONGraph


class BaseLearningStore(ABC):
    """Base class for agent learning stores."""

    def __init__(self, graph: ISONGraph, domain: str = "learning"):
        self.graph = graph
        self.domain = domain

    def _now(self) -> str:
        """Get current ISO timestamp."""
        return datetime.now(timezone.utc).isoformat()

    def _generate_id(self, prefix: str) -> str:
        """Generate unique ID with prefix."""
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _add_node(
        self,
        node_type: str,
        node_id: str,
        properties: Dict[str, Any],
    ) -> str:
        """Add a node to the graph."""
        props = {
            **properties,
            "_domain": self.domain,
            "_created_at": self._now(),
        }
        self.graph.add_node(node_type, node_id, props)
        return node_id

    def _add_edge(
        self,
        source_type: str,
        source_id: str,
        rel_type: str,
        target_type: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Add an edge to the graph."""
        props = properties or {}
        props["_domain"] = self.domain
        props["_created_at"] = self._now()
        self.graph.add_edge(
            source_type, source_id,
            rel_type,
            target_type, target_id,
            props
        )

    def _get_node(self, node_type: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by type and ID."""
        node = self.graph.get_node(node_type, node_id)
        if node:
            return {"id": node.id, "type": node.type, **node.properties}
        return None

    def _update_node(
        self,
        node_type: str,
        node_id: str,
        properties: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update node properties."""
        node = self.graph.get_node(node_type, node_id)
        if node:
            props = {**node.properties, **properties, "_updated_at": self._now()}
            self.graph.add_node(node_type, node_id, props)
            return {"id": node_id, "type": node_type, **props}
        return None

    def _find_nodes(
        self,
        node_type: str,
        **filters: Any,
    ) -> List[Dict[str, Any]]:
        """Find nodes matching filters."""
        results = []
        for node in self.graph.nodes():
            if node.type != node_type:
                continue
            match = True
            for key, value in filters.items():
                if node.properties.get(key) != value:
                    match = False
                    break
            if match:
                results.append({"id": node.id, "type": node.type, **node.properties})
        return results

    def _find_edges(
        self,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        rel_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Find edges matching criteria."""
        results = []
        for edge in self.graph.edges():
            if source_type and edge.source_type != source_type:
                continue
            if source_id and edge.source_id != source_id:
                continue
            if rel_type and edge.rel_type != rel_type:
                continue
            if target_type and edge.target_type != target_type:
                continue
            if target_id and edge.target_id != target_id:
                continue
            results.append({
                "source_type": edge.source_type,
                "source_id": edge.source_id,
                "rel_type": edge.rel_type,
                "target_type": edge.target_type,
                "target_id": edge.target_id,
                **edge.properties,
            })
        return results

    def _delete_node(self, node_type: str, node_id: str) -> bool:
        """Delete a node."""
        try:
            self.graph.remove_node(node_type, node_id)
            return True
        except Exception:
            return False

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for this store."""
        pass
