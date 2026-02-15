"""
Token Manager
=============

Token counting and budget management for LLM-optimized caching.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import json


@dataclass
class TokenBudget:
    """Tracks token budget usage"""
    total: int
    used: int = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.used)

    @property
    def utilization(self) -> float:
        if self.total == 0:
            return 0.0
        return (self.used / self.total) * 100

    def can_fit(self, tokens: int) -> bool:
        """Check if tokens fit in remaining budget"""
        return tokens <= self.remaining

    def consume(self, tokens: int) -> bool:
        """Consume tokens from budget, returns True if successful"""
        if self.can_fit(tokens):
            self.used += tokens
            return True
        return False


class TokenManager:
    """
    Manages token counting for ISON-formatted content.

    Uses tiktoken for accurate token counting compatible with
    GPT-4 and Claude models.
    """

    # Average tokens per character for estimation
    CHARS_PER_TOKEN = 4

    # ISON-specific overhead estimates
    BLOCK_HEADER_TOKENS = 2   # "table.name\n"
    FIELD_HEADER_TOKENS = 1   # Per field in header row
    ROW_SEPARATOR_TOKENS = 1  # Newline between rows
    VALUE_OVERHEAD = 0.5      # Average overhead per value

    def __init__(self, model: str = "cl100k_base"):
        """
        Initialize token manager.

        Args:
            model: Tokenizer model (cl100k_base for GPT-4/Claude)
        """
        self.model = model
        self._encoder = None

    @property
    def encoder(self):
        """Lazy load tiktoken encoder"""
        if self._encoder is None:
            try:
                import tiktoken
                self._encoder = tiktoken.get_encoding(self.model)
            except ImportError:
                self._encoder = None
        return self._encoder

    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text using tiktoken.

        Falls back to character-based estimation if tiktoken unavailable.
        """
        if self.encoder:
            return len(self.encoder.encode(text))
        # Fallback estimation
        return len(text) // self.CHARS_PER_TOKEN + 1

    def count_value_tokens(self, value: Any) -> int:
        """
        Count tokens for a value when serialized to ISON.

        Args:
            value: Python value (dict, list, string, number, etc.)

        Returns:
            Estimated token count
        """
        if isinstance(value, dict):
            return self._count_dict_tokens(value)
        elif isinstance(value, list):
            return self._count_list_tokens(value)
        elif isinstance(value, str):
            return self.count_tokens(value)
        elif value is None:
            return 1  # "null"
        elif isinstance(value, bool):
            return 1  # "true" or "false"
        else:
            return self.count_tokens(str(value))

    def _count_dict_tokens(self, d: Dict[str, Any]) -> int:
        """Count tokens for a dict (single object in ISON)"""
        if not d:
            return 1

        # ISON format: "object.name\nfield1 field2...\nval1 val2..."
        tokens = self.BLOCK_HEADER_TOKENS

        # Field header row
        tokens += len(d) * self.FIELD_HEADER_TOKENS

        # Values
        for key, val in d.items():
            tokens += self.count_value_tokens(val)

        tokens += self.ROW_SEPARATOR_TOKENS * 2

        return int(tokens)

    def _count_list_tokens(self, lst: List[Any]) -> int:
        """Count tokens for a list (table in ISON)"""
        if not lst:
            return 1

        # ISON format: "table.name\nfield1 field2...\nrow1\nrow2..."
        tokens = self.BLOCK_HEADER_TOKENS

        # Get all unique keys for header
        if lst and isinstance(lst[0], dict):
            all_keys = set()
            for item in lst:
                if isinstance(item, dict):
                    all_keys.update(item.keys())

            # Field header
            tokens += len(all_keys) * self.FIELD_HEADER_TOKENS

            # Each row
            for item in lst:
                for key in all_keys:
                    val = item.get(key) if isinstance(item, dict) else item
                    tokens += self.count_value_tokens(val)
                tokens += self.ROW_SEPARATOR_TOKENS
        else:
            # Simple list
            for item in lst:
                tokens += self.count_value_tokens(item)
                tokens += self.ROW_SEPARATOR_TOKENS

        return int(tokens)

    def count_ison_tokens(self, ison_text: str) -> int:
        """Count tokens in ISON-formatted text"""
        return self.count_tokens(ison_text)

    def estimate_json_tokens(self, value: Any) -> int:
        """Estimate tokens if value were JSON-serialized"""
        try:
            json_str = json.dumps(value, separators=(',', ':'))
            return self.count_tokens(json_str)
        except (TypeError, ValueError):
            return self.count_value_tokens(value) * 3  # Rough estimate

    def compare_formats(self, value: Any) -> Dict[str, Any]:
        """
        Compare token counts between ISON and JSON formats.

        Returns:
            Dictionary with comparison metrics
        """
        ison_tokens = self.count_value_tokens(value)
        json_tokens = self.estimate_json_tokens(value)

        savings = json_tokens - ison_tokens
        savings_percent = (savings / json_tokens * 100) if json_tokens > 0 else 0

        return {
            "ison_tokens": ison_tokens,
            "json_tokens": json_tokens,
            "savings": savings,
            "savings_percent": round(savings_percent, 1),
        }

    def fit_within_budget(
        self,
        items: List[Tuple[str, Any, int]],
        budget: int,
        priority: str = "tokens"
    ) -> Tuple[List[Tuple[str, Any]], List[str]]:
        """
        Select items that fit within token budget.

        Args:
            items: List of (key, value, tokens) tuples
            budget: Maximum tokens
            priority: Sort order - "tokens" (smallest first),
                     "hits" (most accessed first), or "recent"

        Returns:
            Tuple of (included_items, excluded_keys)
        """
        # Sort by priority
        if priority == "tokens":
            sorted_items = sorted(items, key=lambda x: x[2])
        elif priority == "hits":
            # Assume items already sorted by hits (caller's responsibility)
            sorted_items = items
        elif priority == "recent":
            sorted_items = items
        else:
            sorted_items = items

        included = []
        excluded = []
        remaining = budget

        for key, value, tokens in sorted_items:
            if tokens <= remaining:
                included.append((key, value))
                remaining -= tokens
            else:
                excluded.append(key)

        return included, excluded

    def truncate_to_budget(
        self,
        text: str,
        budget: int,
        suffix: str = "..."
    ) -> Tuple[str, int]:
        """
        Truncate text to fit within token budget.

        Args:
            text: Text to truncate
            budget: Maximum tokens
            suffix: Suffix to add if truncated

        Returns:
            Tuple of (truncated_text, actual_tokens)
        """
        tokens = self.count_tokens(text)
        if tokens <= budget:
            return text, tokens

        # Binary search for optimal truncation point
        suffix_tokens = self.count_tokens(suffix)
        target = budget - suffix_tokens

        if target <= 0:
            return suffix, self.count_tokens(suffix)

        # Estimate character position
        char_ratio = len(text) / tokens
        estimated_chars = int(target * char_ratio)

        # Refine by checking actual tokens
        while estimated_chars > 0:
            truncated = text[:estimated_chars] + suffix
            actual_tokens = self.count_tokens(truncated)
            if actual_tokens <= budget:
                return truncated, actual_tokens
            estimated_chars = int(estimated_chars * 0.9)

        return suffix, self.count_tokens(suffix)


# Singleton instance for convenience
_default_manager: Optional[TokenManager] = None


def get_token_manager(model: str = "cl100k_base") -> TokenManager:
    """Get or create default token manager"""
    global _default_manager
    if _default_manager is None or _default_manager.model != model:
        _default_manager = TokenManager(model)
    return _default_manager
