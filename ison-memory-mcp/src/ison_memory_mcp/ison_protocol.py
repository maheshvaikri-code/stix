"""
ISON Protocol Extensions for MCP

Provides ISON-aware parsing for tool arguments and optimized
response formatting. While MCP uses JSON-RPC, we can:

1. Accept ISON-formatted strings in arguments
2. Return ISON-formatted content (already implemented)
3. Provide helpers for ISON ↔ dict conversion

Future: If MCP adds ISON transport support, this module
would handle the full protocol.
"""

from __future__ import annotations

import re
from typing import Any, Optional, Union
from dataclasses import dataclass


# =============================================================================
# ISON Parser (Lightweight)
# =============================================================================

class ISONParser:
    """
    Lightweight ISON parser for MCP tool arguments.

    Supports:
    - Tables: table.name\\nfield1 field2\\nvalue1 value2
    - Objects: object.name\\nfield1 field2\\nvalue1 value2
    - References: :id or :type:id
    - Strings: "quoted" or unquoted_word
    - Numbers: 123, 45.67
    - Booleans: true, false
    - Null: null
    """

    # Reference pattern: :id or :type:id
    REF_PATTERN = re.compile(r'^:([a-zA-Z_][a-zA-Z0-9_]*)?:?([a-zA-Z0-9_]+)$')

    @classmethod
    def parse(cls, text: str) -> dict[str, Any]:
        """
        Parse ISON text into Python dict.

        Args:
            text: ISON formatted string

        Returns:
            Dictionary with parsed data
        """
        result: dict[str, Any] = {}
        current_block: Optional[dict[str, Any]] = None
        current_name: str = ""
        current_kind: str = ""
        headers: list[str] = []

        lines = text.strip().split('\n')

        for line in lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                continue

            # Block header: table.name or object.name
            if '.' in line and not line.startswith('"') and ' ' not in line.split('.')[0]:
                parts = line.split('.', 1)
                if len(parts) == 2 and parts[0] in ('table', 'object', 'meta', 'nodes', 'edges'):
                    current_kind = parts[0]
                    current_name = parts[1]
                    headers = []

                    if current_kind == 'table':
                        result[current_name] = []
                        current_block = result[current_name]
                    else:
                        result[current_name] = {}
                        current_block = result[current_name]
                    continue

            # If we have a block, parse content
            if current_block is not None:
                tokens = cls._tokenize(line)

                # First line after header is field names
                if not headers:
                    headers = tokens
                    continue

                # Parse values
                if isinstance(current_block, list):
                    # Table row
                    row = {}
                    for i, token in enumerate(tokens):
                        if i < len(headers):
                            row[headers[i].rstrip(':int:float:bool:ref')] = cls._parse_value(token)
                    current_block.append(row)
                else:
                    # Object single row
                    for i, token in enumerate(tokens):
                        if i < len(headers):
                            current_block[headers[i].rstrip(':int:float:bool:ref')] = cls._parse_value(token)

        return result

    @classmethod
    def _tokenize(cls, line: str) -> list[str]:
        """Split line into tokens, respecting quoted strings"""
        tokens = []
        current = ""
        in_quotes = False
        escape = False

        for char in line:
            if escape:
                current += char
                escape = False
            elif char == '\\':
                escape = True
            elif char == '"':
                if in_quotes:
                    tokens.append(current)
                    current = ""
                    in_quotes = False
                else:
                    in_quotes = True
            elif char == ' ' and not in_quotes:
                if current:
                    tokens.append(current)
                    current = ""
            else:
                current += char

        if current:
            tokens.append(current)

        return tokens

    @classmethod
    def _parse_value(cls, token: str) -> Any:
        """Parse a single token value"""
        # Null
        if token == 'null':
            return None

        # Boolean
        if token == 'true':
            return True
        if token == 'false':
            return False

        # Reference
        if token.startswith(':'):
            match = cls.REF_PATTERN.match(token)
            if match:
                type_part, id_part = match.groups()
                if type_part:
                    return {'_ref': True, 'type': type_part, 'id': id_part}
                return {'_ref': True, 'id': id_part}

        # Number
        try:
            if '.' in token:
                return float(token)
            return int(token)
        except ValueError:
            pass

        # String (already unquoted by tokenizer)
        return token

    @classmethod
    def parse_argument(cls, value: Any) -> Any:
        """
        Parse a tool argument that might be ISON-formatted.

        If the value is a string that looks like ISON, parse it.
        Otherwise return as-is.
        """
        if not isinstance(value, str):
            return value

        # Check if it looks like ISON
        if any(marker in value for marker in ['table.', 'object.', 'nodes.', 'edges.']):
            try:
                return cls.parse(value)
            except Exception:
                pass

        return value


# =============================================================================
# ISON Serializer
# =============================================================================

class ISONSerializer:
    """
    Serialize Python data structures to ISON format.
    """

    @classmethod
    def dumps(cls, data: dict[str, Any], name: str = "data") -> str:
        """
        Serialize dict to ISON format.

        Args:
            data: Dictionary to serialize
            name: Block name

        Returns:
            ISON formatted string
        """
        lines = []

        for key, value in data.items():
            if isinstance(value, list) and value and isinstance(value[0], dict):
                # Table
                lines.append(f"table.{key}")

                # Get all keys from all rows
                all_keys = set()
                for row in value:
                    all_keys.update(row.keys())
                headers = sorted(all_keys)

                lines.append(" ".join(headers))

                for row in value:
                    row_values = []
                    for h in headers:
                        row_values.append(cls._format_value(row.get(h)))
                    lines.append(" ".join(row_values))

                lines.append("")

            elif isinstance(value, dict):
                # Object
                lines.append(f"object.{key}")
                headers = list(value.keys())
                lines.append(" ".join(headers))

                values = [cls._format_value(v) for v in value.values()]
                lines.append(" ".join(values))
                lines.append("")

            else:
                # Simple value - add as meta
                lines.append(f"# {key}: {cls._format_value(value)}")

        return "\n".join(lines)

    @classmethod
    def _format_value(cls, value: Any) -> str:
        """Format a single value for ISON output"""
        if value is None:
            return "null"
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, str):
            if ' ' in value or '"' in value or '\n' in value:
                escaped = value.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
                return f'"{escaped}"'
            return value if value else '""'
        if isinstance(value, dict) and value.get('_ref'):
            if 'type' in value:
                return f":{value['type']}:{value['id']}"
            return f":{value['id']}"
        if isinstance(value, (int, float)):
            return str(value)
        return str(value)


# =============================================================================
# ISON Reference Helpers
# =============================================================================

@dataclass
class ISONRef:
    """Represents an ISON reference"""
    id: str
    type: Optional[str] = None

    def __str__(self) -> str:
        if self.type:
            return f":{self.type}:{self.id}"
        return f":{self.id}"

    @classmethod
    def parse(cls, ref_str: str) -> Optional['ISONRef']:
        """Parse reference string to ISONRef"""
        if not ref_str.startswith(':'):
            return None

        parts = ref_str[1:].split(':')
        if len(parts) == 1:
            return cls(id=parts[0])
        elif len(parts) == 2:
            return cls(type=parts[0], id=parts[1])
        return None


def ref(id: str, type: Optional[str] = None) -> str:
    """Create an ISON reference string"""
    if type:
        return f":{type}:{id}"
    return f":{id}"


def parse_ref(ref_str: str) -> tuple[Optional[str], str]:
    """
    Parse ISON reference string.

    Returns:
        Tuple of (type, id) - type may be None
    """
    if not ref_str.startswith(':'):
        return (None, ref_str)

    parts = ref_str[1:].split(':')
    if len(parts) == 1:
        return (None, parts[0])
    elif len(parts) == 2:
        return (parts[0], parts[1])
    return (None, ref_str)


# =============================================================================
# ISON Response Builders
# =============================================================================

class ISONResponse:
    """
    Builder for ISON-formatted MCP responses.

    Usage:
        response = ISONResponse()
        response.add_comment("Search Results")
        response.add_table("entities", [
            {"id": ":e_123", "name": "Test", "type": "concept"}
        ])
        return response.build()
    """

    def __init__(self) -> None:
        self._lines: list[str] = []

    def add_comment(self, text: str) -> 'ISONResponse':
        """Add a comment line"""
        self._lines.append(f"# {text}")
        return self

    def add_blank(self) -> 'ISONResponse':
        """Add a blank line"""
        self._lines.append("")
        return self

    def add_table(
        self,
        name: str,
        rows: list[dict[str, Any]],
        headers: Optional[list[str]] = None
    ) -> 'ISONResponse':
        """Add a table block"""
        if not rows:
            return self

        self._lines.append(f"table.{name}")

        # Determine headers
        if headers is None:
            all_keys = set()
            for row in rows:
                all_keys.update(row.keys())
            headers = sorted(all_keys)

        self._lines.append(" ".join(headers))

        for row in rows:
            values = [ISONSerializer._format_value(row.get(h)) for h in headers]
            self._lines.append(" ".join(values))

        self._lines.append("")
        return self

    def add_object(self, name: str, data: dict[str, Any]) -> 'ISONResponse':
        """Add an object block"""
        self._lines.append(f"object.{name}")

        headers = list(data.keys())
        self._lines.append(" ".join(headers))

        values = [ISONSerializer._format_value(v) for v in data.values()]
        self._lines.append(" ".join(values))
        self._lines.append("")
        return self

    def add_error(self, code: str, message: str) -> 'ISONResponse':
        """Add an error block"""
        self._lines.append(f"error.{code}")
        self._lines.append("message")
        self._lines.append(f'"{message}"')
        return self

    def add_raw(self, text: str) -> 'ISONResponse':
        """Add raw ISON text"""
        self._lines.append(text)
        return self

    def build(self) -> str:
        """Build the final ISON string"""
        return "\n".join(self._lines)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    'ISONParser',
    'ISONSerializer',
    'ISONRef',
    'ISONResponse',
    'ref',
    'parse_ref',
]
