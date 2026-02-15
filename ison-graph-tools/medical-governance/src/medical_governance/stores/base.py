"""
Base Store for Medical Governance
=================================

Common functionality for all HIPAA governance stores.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class BaseStore(ABC):
    """Base class for all HIPAA governance stores"""

    def __init__(self, graph: "ISONGraph", domain: str):
        self.graph = graph
        self.domain = domain

    def _now(self) -> str:
        """Get current timestamp in ISO format"""
        return datetime.now(timezone.utc).isoformat()

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID with prefix"""
        import uuid
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def _add_node(self, node_type: str, node_id: str, properties: Dict[str, Any]) -> str:
        """Add a node to the graph"""
        properties["_created_at"] = self._now()
        properties["_domain"] = self.domain
        self.graph.add_node(node_type, node_id, **properties)
        return node_id

    def _add_edge(
        self,
        source_type: str,
        source_id: str,
        rel_type: str,
        target_type: str,
        target_id: str,
        properties: Optional[Dict[str, Any]] = None
    ):
        """Add an edge to the graph"""
        props = properties or {}
        props["_created_at"] = self._now()
        self.graph.add_edge(
            rel_type,
            (source_type, source_id),
            (target_type, target_id),
            **props
        )

    def _get_node(self, node_type: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by type and ID"""
        try:
            node = self.graph.get_node(node_type, node_id)
            return {"id": node.id, **dict(node.properties)}
        except Exception:
            return None

    def _update_node(self, node_type: str, node_id: str, properties: Dict[str, Any]):
        """Update node properties"""
        properties["_updated_at"] = self._now()
        self.graph.update_node(node_type, node_id, **properties)

    def _find_nodes(self, node_type: str, **filters) -> List[Dict[str, Any]]:
        """Find nodes by type and optional filters"""
        results = []
        for node in self.graph.nodes():
            if node.type == node_type:
                match = True
                for key, value in filters.items():
                    if node.properties.get(key) != value:
                        match = False
                        break
                if match:
                    results.append({"id": node.id, **dict(node.properties)})
        return results

    def _find_edges(
        self,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        rel_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find edges by various criteria"""
        results = []
        for edge in self.graph.edges():
            if source_type and edge.source[0] != source_type:
                continue
            if source_id and edge.source[1] != source_id:
                continue
            if rel_type and edge.rel_type != rel_type:
                continue
            if target_type and edge.target[0] != target_type:
                continue
            if target_id and edge.target[1] != target_id:
                continue
            results.append({
                "source": edge.source,
                "rel_type": edge.rel_type,
                "target": edge.target,
                "properties": dict(edge.properties)
            })
        return results

    def _delete_node(self, node_type: str, node_id: str):
        """Delete a node"""
        self.graph.delete_node(node_type, node_id)

    def get_stats(self) -> Dict[str, int]:
        """Get statistics for this store's domain"""
        nodes = 0
        edges = 0

        for node in self.graph.nodes():
            if node.properties.get("_domain") == self.domain:
                nodes += 1

        for edge in self.graph.edges():
            if edge.properties.get("_domain") == self.domain:
                edges += 1

        return {"nodes": nodes, "edges": edges}
