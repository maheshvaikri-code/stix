"""
CCPA Governance Base Store
==========================

Abstract base class for all CCPA governance stores.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List
from datetime import datetime, timedelta

from ison_graph import ISONGraph


class BaseCCPAStore(ABC):
    """
    Abstract base class for CCPA governance stores.

    Provides common utilities for all governance stores.
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph

    def _now(self) -> str:
        """Get current ISO timestamp"""
        return datetime.now().isoformat()

    def _deadline(self, days: int = 45) -> str:
        """Calculate deadline (default 45 days for CCPA requests)"""
        return (datetime.now() + timedelta(days=days)).isoformat()

    def _make_id(self, prefix: str, name: str) -> str:
        """Generate unique ID"""
        clean = name.replace(" ", "_").replace("/", "_").replace(".", "_").lower()
        return f"{prefix}_{clean}_{datetime.now().strftime('%Y%m%d%H%M%S')}"

    def _sanitize(self, s: str) -> str:
        """Sanitize string for storage"""
        if not s:
            return ""
        return s.replace("\n", " ").replace("\r", " ").replace('"', "'")

    def _list_to_str(self, items: List[str]) -> str:
        """Convert list to comma-separated string"""
        return ",".join(items) if items else ""

    def _str_to_list(self, s: str) -> List[str]:
        """Convert comma-separated string to list"""
        if not s:
            return []
        return [item.strip() for item in s.split(",") if item.strip()]

    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics for this store"""
        pass
