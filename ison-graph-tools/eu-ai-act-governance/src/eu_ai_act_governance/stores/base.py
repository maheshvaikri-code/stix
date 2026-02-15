"""
Base Store for EU AI Act Governance
===================================

Provides common functionality for all governance stores.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
import uuid

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class BaseStore:
    """Base class for EU AI Act governance stores"""

    def __init__(self, graph: "ISONGraph", store_name: str):
        self.graph = graph
        self.store_name = store_name

    def _now(self) -> str:
        """Get current UTC timestamp"""
        return datetime.now(timezone.utc).isoformat()

    def _generate_id(self, prefix: str = "") -> str:
        """Generate a unique ID"""
        uid = uuid.uuid4().hex[:12]
        return f"{prefix}_{uid}" if prefix else uid

    def _add_node(
        self,
        node_type: str,
        node_id: str,
        properties: Dict[str, Any]
    ) -> str:
        """Add a node to the graph"""
        props = {
            **properties,
            "_created_at": self._now(),
            "_updated_at": self._now(),
            "_store": self.store_name
        }
        self.graph.add_node(node_type, node_id, **props)
        return node_id

    def _get_node(self, node_type: str, node_id: str) -> Optional[Dict[str, Any]]:
        """Get a node by type and ID"""
        try:
            node = self.graph.get_node(node_type, node_id)
            if node:
                return {"id": node.id, "type": node_type, **dict(node.properties)}
            return None
        except Exception:
            return None

    def _update_node(
        self,
        node_type: str,
        node_id: str,
        properties: Dict[str, Any]
    ):
        """Update node properties"""
        props = {
            **properties,
            "_updated_at": self._now(),
        }
        self.graph.update_node(node_type, node_id, **props)

    def _delete_node(self, node_type: str, node_id: str):
        """Delete a node"""
        self.graph.delete_node(node_type, node_id)

    def _find_nodes(
        self,
        node_type: str,
        **filters
    ) -> List[Dict[str, Any]]:
        """Find nodes matching criteria"""
        results = []

        for node in self.graph.nodes():
            if node.type == node_type:
                match = True
                for key, value in filters.items():
                    if node.properties.get(key) != value:
                        match = False
                        break
                if match:
                    results.append({"id": node.id, "type": node_type, **dict(node.properties)})

        return results

    def _add_edge(
        self,
        source_type: str,
        source_id: str,
        rel_type: str,
        target_type: str,
        target_id: str,
        properties: Dict[str, Any] = None
    ) -> str:
        """Add an edge between nodes"""
        props = properties or {}
        props["_created_at"] = self._now()
        self.graph.add_edge(
            rel_type,
            (source_type, source_id),
            (target_type, target_id),
            **props
        )
        return f"{source_type}:{source_id}->{rel_type}->{target_type}:{target_id}"

    def _find_edges(
        self,
        source_type: Optional[str] = None,
        source_id: Optional[str] = None,
        rel_type: Optional[str] = None,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find edges matching criteria"""
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

    def _delete_edge(
        self,
        source_type: str,
        source_id: str,
        rel_type: str,
        target_type: str,
        target_id: str
    ):
        """Delete an edge"""
        self.graph.delete_edge(
            rel_type,
            (source_type, source_id),
            (target_type, target_id)
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get store statistics - override in subclasses"""
        nodes = 0
        edges = 0

        for node in self.graph.nodes():
            if node.properties.get("_store") == self.store_name:
                nodes += 1

        for edge in self.graph.edges():
            # Count edges created by this store
            pass

        return {
            "store_name": self.store_name,
            "nodes": nodes,
            "timestamp": self._now()
        }
