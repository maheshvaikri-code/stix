"""
Base Store - Abstract base class for memory stores
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime

from ison_graph import ISONGraph


class BaseStore(ABC):
    """
    Abstract base class for memory stores.

    Each store manages a specific type of memory (conventions, bugs, etc.)
    and provides methods for querying, adding, and updating that memory.
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph
        self._cache: Dict[str, Any] = {}

    def _now(self) -> str:
        """Get current timestamp string"""
        return datetime.now().isoformat()

    def _relative_time(self, time_str: str) -> str:
        """Convert time string to relative format (T-Xd, T-Xh)"""
        if time_str.startswith("T-"):
            return time_str
        try:
            dt = datetime.fromisoformat(time_str)
            delta = datetime.now() - dt
            if delta.days > 0:
                return f"T-{delta.days}d"
            hours = delta.seconds // 3600
            if hours > 0:
                return f"T-{hours}h"
            minutes = delta.seconds // 60
            return f"T-{minutes}m"
        except:
            return time_str

    def _make_id(self, prefix: str, name: str) -> str:
        """Create a unique ID from prefix and name"""
        clean = name.replace(" ", "_").replace("/", "_").replace(".", "_").lower()
        return f"{prefix}_{clean}"

    def _sanitize(self, s: str) -> str:
        """Sanitize string for storage"""
        return s.replace("\n", " ").replace("\r", " ").replace('"', "'")

    @abstractmethod
    def get_relevant(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get relevant memories for a given context"""
        pass

    @abstractmethod
    def get_stats(self) -> Dict[str, int]:
        """Get statistics about this store"""
        pass


class QueryTemplates:
    """
    Common ISONQL query templates for memory operations.

    These can be used by stores to build queries.
    """

    # Find nodes with confidence above threshold
    CONFIDENT_KNOWLEDGE = """
        MATCH (agent)-[{rel_type}]->(target:{node_type})
        WHERE confidence > {threshold}
        RETURN target
    """

    # Find recent memories
    RECENT_MEMORIES = """
        MATCH (n:{node_type})
        WHERE last_used > {since}
        RETURN n
        ORDER BY last_used DESC
        LIMIT {limit}
    """

    # Find connected memories
    CONNECTED_TO = """
        TRAVERSE {node_type}:{node_id} -> {rel_type} -> {target_type}
        MAX {depth}
    """

    # Find what affects a module
    MODULE_CONTEXT = """
        TRAVERSE module:{module_id} <- * <- *
        MAX 2
    """

    # Find decisions constraining a module
    DECISION_CONSTRAINTS = """
        MATCH (d:decision)-[CONSTRAINS]->(m:module)
        WHERE m.id = {module_id}
        RETURN d
    """

    # Find bug patterns for a module
    BUG_RISKS = """
        MATCH (bp:bug_pattern)-[SIMILAR_CODE_EXISTS]->(m:module)
        WHERE m.id = {module_id}
        RETURN bp
    """

    # Find conventions for file type
    FILE_CONVENTIONS = """
        MATCH (c:convention)-[APPLIES_TO]->(pattern)
        WHERE pattern MATCHES {file_pattern}
        RETURN c
    """

    # Session continuity
    SESSION_CONTEXT = """
        TRAVERSE session:{session_id} <- CONTINUES <- session
        MAX 5
    """

    # Skills above threshold
    PROFICIENT_SKILLS = """
        MATCH (s:skill)
        WHERE s.proficiency > {threshold}
        RETURN s
        ORDER BY s.proficiency DESC
    """

    # Find expertise for topic
    FIND_EXPERT = """
        MATCH (tm:team_member)-[HAS_EXPERTISE]->(ea:expertise_area)
        WHERE ea.domain CONTAINS {topic}
        RETURN tm, ea
        ORDER BY ea.depth DESC
    """
