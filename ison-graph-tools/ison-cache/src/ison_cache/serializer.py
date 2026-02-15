"""
ISON Serializer
===============

Converts between Python objects and ISON format for efficient LLM context.
"""

from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
import re


class ISONSerializer:
    """
    Serializes Python objects to ISON format.

    ISON is optimized for LLM token efficiency with:
    - Columnar format for tables
    - No redundant keys per row
    - Space-separated values
    - Native reference syntax (:type:id)
    """

    def __init__(self, indent: bool = False):
        self.indent = indent

    def serialize(
        self,
        value: Any,
        block_name: str = "data",
        block_kind: str = "auto"
    ) -> str:
        """
        Serialize a Python object to ISON format.

        Args:
            value: Python object (dict, list, or primitive)
            block_name: Name for the ISON block
            block_kind: "object", "table", or "auto" (detect)

        Returns:
            ISON-formatted string
        """
        if isinstance(value, dict):
            return self._serialize_object(value, block_name)
        elif isinstance(value, list):
            return self._serialize_table(value, block_name)
        elif isinstance(value, str) and value.startswith(("object.", "table.")):
            # Already ISON formatted
            return value
        else:
            # Primitive value
            return self._value_to_ison(value)

    def _serialize_object(self, obj: Dict[str, Any], name: str = "object") -> str:
        """Serialize a single object/dict"""
        if not obj:
            return f"object.{name}\n"

        lines = [f"object.{name}"]

        # Field names
        fields = list(obj.keys())
        lines.append(" ".join(fields))

        # Values
        values = [self._value_to_ison(obj[f]) for f in fields]
        lines.append(" ".join(values))

        return "\n".join(lines)

    def _serialize_table(self, items: List[Any], name: str = "table") -> str:
        """Serialize a list of objects as an ISON table"""
        if not items:
            return f"table.{name}\n"

        # Handle list of dicts
        if isinstance(items[0], dict):
            return self._serialize_dict_table(items, name)

        # Handle list of primitives
        lines = [f"table.{name}", "value"]
        for item in items:
            lines.append(self._value_to_ison(item))

        return "\n".join(lines)

    def _serialize_dict_table(
        self,
        items: List[Dict[str, Any]],
        name: str
    ) -> str:
        """Serialize list of dicts as columnar table"""
        # Collect all unique fields across all items
        all_fields = set()
        for item in items:
            all_fields.update(item.keys())

        # Sort fields for consistent output (id first if present)
        fields = sorted(all_fields)
        if "id" in fields:
            fields.remove("id")
            fields.insert(0, "id")

        lines = [f"table.{name}"]
        lines.append(" ".join(fields))

        for item in items:
            values = []
            for field in fields:
                val = item.get(field)
                values.append(self._value_to_ison(val))
            lines.append(" ".join(values))

        return "\n".join(lines)

    def _value_to_ison(self, value: Any) -> str:
        """Convert a single value to ISON format"""
        if value is None:
            return "null"
        elif isinstance(value, bool):
            return "true" if value else "false"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, str):
            # Check if it's a reference
            if re.match(r'^:[a-zA-Z_]\w*:[a-zA-Z0-9_]+$', value):
                return value  # Already a reference

            # Escape strings with spaces or special chars
            if " " in value or '"' in value or "\n" in value:
                escaped = value.replace("\\", "\\\\").replace('"', '\\"')
                escaped = escaped.replace("\n", "\\n")
                return f'"{escaped}"'
            elif value == "":
                return '""'
            return value
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, date):
            return value.isoformat()
        elif isinstance(value, (list, tuple)):
            # Inline list as JSON-like array
            items = [self._value_to_ison(v) for v in value]
            return "[" + ",".join(items) + "]"
        elif isinstance(value, dict):
            # Inline object - use reference or serialize
            if "id" in value and "type" in value:
                return f":{value['type']}:{value['id']}"
            # Fallback to inline
            pairs = [f"{k}:{self._value_to_ison(v)}" for k, v in value.items()]
            return "{" + ",".join(pairs) + "}"
        else:
            return str(value)

    def serialize_multiple(
        self,
        items: Dict[str, Any],
        merge_tables: bool = True
    ) -> str:
        """
        Serialize multiple items to ISON.

        Args:
            items: Dict of name -> value pairs
            merge_tables: If True, merge similar tables into one block

        Returns:
            ISON-formatted string with multiple blocks
        """
        blocks = []

        if merge_tables:
            # Group by schema for merging
            schema_groups: Dict[str, List[tuple]] = {}

            for name, value in items.items():
                if isinstance(value, dict):
                    schema_key = tuple(sorted(value.keys()))
                    if schema_key not in schema_groups:
                        schema_groups[schema_key] = []
                    schema_groups[schema_key].append((name, value))
                else:
                    # Non-dict items serialized individually
                    blocks.append(self.serialize(value, name))

            # Merge same-schema dicts into tables
            for schema_key, group in schema_groups.items():
                if len(group) == 1:
                    name, value = group[0]
                    blocks.append(self._serialize_object(value, name))
                else:
                    # Merge into table
                    merged = [item[1] for item in group]
                    # Use common prefix or generic name
                    names = [item[0] for item in group]
                    common_prefix = self._find_common_prefix(names)
                    table_name = common_prefix if common_prefix else "items"
                    blocks.append(self._serialize_dict_table(merged, table_name))
        else:
            for name, value in items.items():
                blocks.append(self.serialize(value, name))

        return "\n\n".join(blocks)

    def _find_common_prefix(self, names: List[str]) -> str:
        """Find common prefix in list of names"""
        if not names:
            return ""
        if len(names) == 1:
            return names[0]

        prefix = names[0]
        for name in names[1:]:
            while not name.startswith(prefix) and prefix:
                prefix = prefix[:-1]
        return prefix.rstrip(":_-")

    def serialize_graph(
        self,
        entities: List[Dict[str, Any]],
        relations: List[Dict[str, Any]],
        graph_name: str = "graph"
    ) -> str:
        """
        Serialize a graph (entities + relations) to ISON.

        Args:
            entities: List of entity dicts with at least 'id' and 'type'
            relations: List of relation dicts with 'from', 'to', 'type'
            graph_name: Name prefix for blocks

        Returns:
            ISON-formatted graph
        """
        blocks = []

        # Entities
        if entities:
            blocks.append(self._serialize_dict_table(entities, f"{graph_name}.entities"))

        # Relations
        if relations:
            blocks.append(self._serialize_dict_table(relations, f"{graph_name}.relations"))

        return "\n\n".join(blocks)


class ISONDeserializer:
    """
    Deserializes ISON format back to Python objects.
    """

    def deserialize(self, ison_text: str) -> Dict[str, Any]:
        """
        Deserialize ISON text to Python objects.

        Returns:
            Dict mapping block names to parsed values
        """
        result = {}
        blocks = ison_text.strip().split("\n\n")

        for block in blocks:
            if not block.strip():
                continue

            lines = block.strip().split("\n")
            if not lines:
                continue

            # Parse header
            header = lines[0]
            if "." in header:
                kind, name = header.split(".", 1)
            else:
                kind = "data"
                name = header

            if kind == "object":
                if len(lines) >= 3:
                    fields = lines[1].split()
                    values = self._parse_values(lines[2])
                    result[name] = dict(zip(fields, values))
                else:
                    result[name] = {}

            elif kind == "table":
                if len(lines) >= 2:
                    fields = lines[1].split()
                    rows = []
                    for line in lines[2:]:
                        if line.strip():
                            values = self._parse_values(line)
                            rows.append(dict(zip(fields, values)))
                    result[name] = rows
                else:
                    result[name] = []

            else:
                # Unknown kind, store as raw
                result[name] = block

        return result

    def _parse_values(self, line: str) -> List[Any]:
        """Parse space-separated values handling quoted strings"""
        values = []
        i = 0
        current = ""
        in_quotes = False

        while i < len(line):
            char = line[i]

            if char == '"' and not in_quotes:
                in_quotes = True
                i += 1
                continue
            elif char == '"' and in_quotes:
                if i > 0 and line[i-1] == '\\':
                    current += '"'
                else:
                    in_quotes = False
                i += 1
                continue

            if char == ' ' and not in_quotes:
                if current:
                    values.append(self._parse_value(current))
                    current = ""
            else:
                current += char

            i += 1

        if current:
            values.append(self._parse_value(current))

        return values

    def _parse_value(self, s: str) -> Any:
        """Parse a single value string"""
        if s == "null":
            return None
        elif s == "true":
            return True
        elif s == "false":
            return False
        elif s.startswith(":"):
            # Reference - return as string
            return s
        elif s.startswith("[") and s.endswith("]"):
            # Array
            inner = s[1:-1]
            if not inner:
                return []
            parts = inner.split(",")
            return [self._parse_value(p.strip()) for p in parts]
        elif s.startswith("{") and s.endswith("}"):
            # Inline object
            inner = s[1:-1]
            if not inner:
                return {}
            pairs = inner.split(",")
            result = {}
            for pair in pairs:
                if ":" in pair:
                    k, v = pair.split(":", 1)
                    result[k.strip()] = self._parse_value(v.strip())
            return result
        else:
            # Try numeric
            try:
                if "." in s:
                    return float(s)
                return int(s)
            except ValueError:
                return s


# Convenience functions
_serializer = ISONSerializer()
_deserializer = ISONDeserializer()


def to_ison(value: Any, name: str = "data") -> str:
    """Convert value to ISON format"""
    return _serializer.serialize(value, name)


def from_ison(text: str) -> Dict[str, Any]:
    """Parse ISON text to Python objects"""
    return _deserializer.deserialize(text)


def to_ison_graph(
    entities: List[Dict[str, Any]],
    relations: List[Dict[str, Any]],
    name: str = "graph"
) -> str:
    """Convert graph to ISON format"""
    return _serializer.serialize_graph(entities, relations, name)
