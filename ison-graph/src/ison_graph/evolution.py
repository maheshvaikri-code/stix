#!/usr/bin/env python3
"""
ISONGraph Schema Evolution Module

Provides schema inference, validation, and zero-migration evolution:
- Automatic schema inference from graph data
- Type coercion for flexible data handling
- Schema validation and migration

Usage:
    from ison_graph import ISONGraph
    from ison_graph.evolution import SchemaInference, SchemaManager, TypeCoercion

    graph = ISONGraph()
    graph.add_node('person', 1, name='Alice', age=30)

    # Infer schema from data
    inference = SchemaInference()
    schema = inference.infer_from_graph(graph)

    # Manage schema evolution
    manager = SchemaManager(schema)
    manager.add_property('person', 'email', type='string', required=False)

    # Validate graph against schema
    result = manager.validate(graph)

    # Type coercion
    value = TypeCoercion.coerce("42", 'number')  # Returns 42
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import (
    Any, Dict, List, Optional, Set, Tuple,
    Callable, Union, Type
)
from enum import Enum
from datetime import datetime

from . import ISONGraph, Node, Edge, NodeRef


# =============================================================================
# Property Types
# =============================================================================

class PropertyType(Enum):
    """Supported property types"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    ARRAY = "array"
    OBJECT = "object"
    ANY = "any"


# =============================================================================
# Property Definition
# =============================================================================

@dataclass
class PropertyDef:
    """Definition of a property"""
    name: str
    type: PropertyType = PropertyType.ANY
    required: bool = False
    default: Any = None
    nullable: bool = True
    unique: bool = False
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None
    enum_values: Optional[List[Any]] = None
    description: str = ""


@dataclass
class NodeTypeDef:
    """Definition of a node type"""
    name: str
    properties: Dict[str, PropertyDef] = field(default_factory=dict)
    description: str = ""


@dataclass
class EdgeTypeDef:
    """Definition of an edge type"""
    name: str
    properties: Dict[str, PropertyDef] = field(default_factory=dict)
    source_types: Optional[List[str]] = None  # Allowed source node types
    target_types: Optional[List[str]] = None  # Allowed target node types
    description: str = ""


# =============================================================================
# Graph Schema
# =============================================================================

@dataclass
class GraphSchema:
    """Complete schema for a graph"""
    node_types: Dict[str, NodeTypeDef] = field(default_factory=dict)
    edge_types: Dict[str, EdgeTypeDef] = field(default_factory=dict)
    version: str = "1.0.0"
    name: str = "schema"
    description: str = ""

    def get_node_type(self, name: str) -> Optional[NodeTypeDef]:
        return self.node_types.get(name)

    def get_edge_type(self, name: str) -> Optional[EdgeTypeDef]:
        return self.edge_types.get(name)


# =============================================================================
# Validation Result
# =============================================================================

@dataclass
class ValidationError:
    """A single validation error"""
    entity_type: str  # 'node' or 'edge'
    entity_id: Any
    property_name: Optional[str]
    error_code: str
    message: str
    severity: str = "error"  # 'error' or 'warning'


@dataclass
class ValidationResult:
    """Result of schema validation"""
    valid: bool
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    @property
    def error_count(self) -> int:
        return len(self.errors)

    @property
    def warning_count(self) -> int:
        return len(self.warnings)


# =============================================================================
# Type Coercion
# =============================================================================

class TypeCoercion:
    """
    Handles type coercion for flexible schema handling.
    """

    @staticmethod
    def coerce(value: Any, target_type: Union[PropertyType, str]) -> Any:
        """
        Coerce a value to a target type.

        Args:
            value: Value to coerce
            target_type: Target type (PropertyType or string)

        Returns:
            Coerced value

        Raises:
            ValueError: If coercion fails
        """
        if isinstance(target_type, str):
            target_type = PropertyType(target_type.lower())

        if value is None:
            return None

        try:
            if target_type == PropertyType.STRING:
                return str(value)

            elif target_type in (PropertyType.NUMBER, PropertyType.FLOAT):
                if isinstance(value, (int, float)):
                    return float(value)
                return float(str(value).strip())

            elif target_type == PropertyType.INTEGER:
                if isinstance(value, int):
                    return value
                if isinstance(value, float):
                    return int(value)
                return int(float(str(value).strip()))

            elif target_type == PropertyType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                if isinstance(value, str):
                    lower = value.lower().strip()
                    if lower in ('true', 'yes', '1', 'on'):
                        return True
                    if lower in ('false', 'no', '0', 'off'):
                        return False
                return bool(value)

            elif target_type == PropertyType.DATE:
                if isinstance(value, datetime):
                    return value.date()
                if isinstance(value, str):
                    # Try common date formats
                    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y'):
                        try:
                            return datetime.strptime(value, fmt).date()
                        except ValueError:
                            continue
                raise ValueError(f"Cannot parse date: {value}")

            elif target_type == PropertyType.DATETIME:
                if isinstance(value, datetime):
                    return value
                if isinstance(value, str):
                    # Try ISO format
                    try:
                        return datetime.fromisoformat(value.replace('Z', '+00:00'))
                    except ValueError:
                        pass
                raise ValueError(f"Cannot parse datetime: {value}")

            elif target_type == PropertyType.ARRAY:
                if isinstance(value, list):
                    return value
                if isinstance(value, str):
                    # Try to split by common delimiters
                    if ',' in value:
                        return [v.strip() for v in value.split(',')]
                return [value]

            elif target_type == PropertyType.OBJECT:
                if isinstance(value, dict):
                    return value
                raise ValueError(f"Cannot coerce to object: {value}")

            else:
                return value

        except (ValueError, TypeError) as e:
            raise ValueError(f"Cannot coerce {type(value).__name__} to {target_type.value}: {e}")

    @staticmethod
    def detect_type(value: Any) -> PropertyType:
        """
        Detect the type of a value.

        Args:
            value: Value to analyze

        Returns:
            Detected PropertyType
        """
        if value is None:
            return PropertyType.ANY

        if isinstance(value, bool):
            return PropertyType.BOOLEAN

        if isinstance(value, int):
            return PropertyType.INTEGER

        if isinstance(value, float):
            return PropertyType.FLOAT

        if isinstance(value, str):
            # Check for boolean strings
            if value.lower() in ('true', 'false', 'yes', 'no'):
                return PropertyType.BOOLEAN

            # Check for numeric strings
            try:
                float(value)
                if '.' in value:
                    return PropertyType.FLOAT
                return PropertyType.INTEGER
            except ValueError:
                pass

            # Check for date/datetime
            if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                return PropertyType.DATE
            if re.match(r'^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}', value):
                return PropertyType.DATETIME

            return PropertyType.STRING

        if isinstance(value, list):
            return PropertyType.ARRAY

        if isinstance(value, dict):
            return PropertyType.OBJECT

        if isinstance(value, datetime):
            return PropertyType.DATETIME

        return PropertyType.ANY

    @staticmethod
    def are_compatible(type1: PropertyType, type2: PropertyType) -> bool:
        """Check if two types are compatible"""
        if type1 == type2:
            return True
        if PropertyType.ANY in (type1, type2):
            return True

        # Number types are compatible
        numeric = {PropertyType.NUMBER, PropertyType.INTEGER, PropertyType.FLOAT}
        if type1 in numeric and type2 in numeric:
            return True

        # Date types are compatible
        if {type1, type2} == {PropertyType.DATE, PropertyType.DATETIME}:
            return True

        return False


# =============================================================================
# Schema Inference
# =============================================================================

class SchemaInference:
    """
    Infers schema from graph data.
    """

    def __init__(self):
        self._type_counts: Dict[str, Dict[str, Dict[PropertyType, int]]] = {}

    def infer_from_graph(self, graph: ISONGraph) -> GraphSchema:
        """
        Infer schema from an existing graph.

        Args:
            graph: Graph to analyze

        Returns:
            Inferred GraphSchema
        """
        schema = GraphSchema(name=f"{graph.name}_schema")

        # Infer node types
        for node in graph.nodes():
            if node.type not in schema.node_types:
                schema.node_types[node.type] = NodeTypeDef(name=node.type)

            node_def = schema.node_types[node.type]
            self._infer_properties(node_def.properties, node.properties)

        # Infer edge types
        for edge in graph.edges():
            if edge.rel_type not in schema.edge_types:
                schema.edge_types[edge.rel_type] = EdgeTypeDef(name=edge.rel_type)

            edge_def = schema.edge_types[edge.rel_type]
            self._infer_properties(edge_def.properties, edge.properties)

            # Track source/target types
            if edge_def.source_types is None:
                edge_def.source_types = []
            if edge.source[0] not in edge_def.source_types:
                edge_def.source_types.append(edge.source[0])

            if edge_def.target_types is None:
                edge_def.target_types = []
            if edge.target[0] not in edge_def.target_types:
                edge_def.target_types.append(edge.target[0])

        return schema

    def _infer_properties(
        self,
        prop_defs: Dict[str, PropertyDef],
        properties: Dict[str, Any]
    ) -> None:
        """Infer property definitions from data"""
        for key, value in properties.items():
            if key not in prop_defs:
                prop_defs[key] = PropertyDef(
                    name=key,
                    type=TypeCoercion.detect_type(value),
                    required=True
                )
            else:
                existing = prop_defs[key]
                detected = TypeCoercion.detect_type(value)

                # Widen type if needed
                if not TypeCoercion.are_compatible(existing.type, detected):
                    existing.type = PropertyType.ANY

    def merge_schemas(self, schemas: List[GraphSchema]) -> GraphSchema:
        """
        Merge multiple schemas into one.

        Args:
            schemas: Schemas to merge

        Returns:
            Merged schema
        """
        merged = GraphSchema(name="merged_schema")

        for schema in schemas:
            for name, node_def in schema.node_types.items():
                if name not in merged.node_types:
                    merged.node_types[name] = NodeTypeDef(name=name)
                self._merge_properties(
                    merged.node_types[name].properties,
                    node_def.properties
                )

            for name, edge_def in schema.edge_types.items():
                if name not in merged.edge_types:
                    merged.edge_types[name] = EdgeTypeDef(name=name)
                self._merge_properties(
                    merged.edge_types[name].properties,
                    edge_def.properties
                )

        return merged

    def _merge_properties(
        self,
        target: Dict[str, PropertyDef],
        source: Dict[str, PropertyDef]
    ) -> None:
        """Merge property definitions"""
        for name, prop in source.items():
            if name not in target:
                target[name] = PropertyDef(
                    name=name,
                    type=prop.type,
                    required=prop.required
                )
            else:
                existing = target[name]
                # Property exists in both - might not be required
                existing.required = existing.required and prop.required
                # Widen type if needed
                if not TypeCoercion.are_compatible(existing.type, prop.type):
                    existing.type = PropertyType.ANY


# =============================================================================
# Schema Manager
# =============================================================================

class SchemaManager:
    """
    Manages schema evolution with zero-migration changes.
    """

    def __init__(self, schema: Optional[GraphSchema] = None):
        self.schema = schema or GraphSchema()
        self._migrations: List[Dict[str, Any]] = []

    def add_node_type(
        self,
        name: str,
        properties: Optional[Dict[str, PropertyDef]] = None,
        description: str = ""
    ) -> None:
        """Add a new node type to the schema"""
        if name in self.schema.node_types:
            raise ValueError(f"Node type '{name}' already exists")

        self.schema.node_types[name] = NodeTypeDef(
            name=name,
            properties=properties or {},
            description=description
        )
        self._migrations.append({
            'type': 'add_node_type',
            'name': name
        })

    def add_edge_type(
        self,
        name: str,
        properties: Optional[Dict[str, PropertyDef]] = None,
        source_types: Optional[List[str]] = None,
        target_types: Optional[List[str]] = None,
        description: str = ""
    ) -> None:
        """Add a new edge type to the schema"""
        if name in self.schema.edge_types:
            raise ValueError(f"Edge type '{name}' already exists")

        self.schema.edge_types[name] = EdgeTypeDef(
            name=name,
            properties=properties or {},
            source_types=source_types,
            target_types=target_types,
            description=description
        )
        self._migrations.append({
            'type': 'add_edge_type',
            'name': name
        })

    def add_property(
        self,
        type_name: str,
        property_name: str,
        type: Union[PropertyType, str] = PropertyType.ANY,
        required: bool = False,
        default: Any = None,
        **kwargs
    ) -> None:
        """
        Add a property to a node or edge type.

        Args:
            type_name: Node or edge type name
            property_name: Property name
            type: Property type
            required: Whether property is required
            default: Default value
            **kwargs: Additional property options
        """
        if isinstance(type, str):
            type = PropertyType(type.lower())

        prop_def = PropertyDef(
            name=property_name,
            type=type,
            required=required,
            default=default,
            **kwargs
        )

        # Check node types first
        if type_name in self.schema.node_types:
            self.schema.node_types[type_name].properties[property_name] = prop_def
        elif type_name in self.schema.edge_types:
            self.schema.edge_types[type_name].properties[property_name] = prop_def
        else:
            raise ValueError(f"Type '{type_name}' not found in schema")

        self._migrations.append({
            'type': 'add_property',
            'type_name': type_name,
            'property_name': property_name,
            'property_def': prop_def
        })

    def remove_property(self, type_name: str, property_name: str) -> None:
        """Remove a property from a node or edge type"""
        if type_name in self.schema.node_types:
            props = self.schema.node_types[type_name].properties
        elif type_name in self.schema.edge_types:
            props = self.schema.edge_types[type_name].properties
        else:
            raise ValueError(f"Type '{type_name}' not found in schema")

        if property_name in props:
            del props[property_name]
            self._migrations.append({
                'type': 'remove_property',
                'type_name': type_name,
                'property_name': property_name
            })

    def rename_property(
        self,
        type_name: str,
        old_name: str,
        new_name: str
    ) -> None:
        """Rename a property"""
        if type_name in self.schema.node_types:
            props = self.schema.node_types[type_name].properties
        elif type_name in self.schema.edge_types:
            props = self.schema.edge_types[type_name].properties
        else:
            raise ValueError(f"Type '{type_name}' not found in schema")

        if old_name in props:
            prop = props[old_name]
            prop.name = new_name
            props[new_name] = prop
            del props[old_name]
            self._migrations.append({
                'type': 'rename_property',
                'type_name': type_name,
                'old_name': old_name,
                'new_name': new_name
            })

    def validate(self, graph: ISONGraph) -> ValidationResult:
        """
        Validate a graph against the schema.

        Args:
            graph: Graph to validate

        Returns:
            ValidationResult with errors and warnings
        """
        errors = []
        warnings = []

        # Validate nodes
        for node in graph.nodes():
            node_errors, node_warnings = self._validate_node(node)
            errors.extend(node_errors)
            warnings.extend(node_warnings)

        # Validate edges
        for edge in graph.edges():
            edge_errors, edge_warnings = self._validate_edge(edge)
            errors.extend(edge_errors)
            warnings.extend(edge_warnings)

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )

    def _validate_node(self, node: Node) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate a single node"""
        errors = []
        warnings = []

        type_def = self.schema.node_types.get(node.type)
        if not type_def:
            warnings.append(ValidationError(
                entity_type='node',
                entity_id=node.ref,
                property_name=None,
                error_code='UNKNOWN_TYPE',
                message=f"Unknown node type: {node.type}",
                severity='warning'
            ))
            return errors, warnings

        # Check required properties
        for prop_name, prop_def in type_def.properties.items():
            if prop_def.required and prop_name not in node.properties:
                errors.append(ValidationError(
                    entity_type='node',
                    entity_id=node.ref,
                    property_name=prop_name,
                    error_code='MISSING_REQUIRED',
                    message=f"Missing required property: {prop_name}"
                ))

        # Validate property values
        for prop_name, value in node.properties.items():
            prop_def = type_def.properties.get(prop_name)
            if prop_def:
                prop_errors = self._validate_property_value(
                    node.ref, prop_name, value, prop_def
                )
                errors.extend(prop_errors)

        return errors, warnings

    def _validate_edge(self, edge: Edge) -> Tuple[List[ValidationError], List[ValidationError]]:
        """Validate a single edge"""
        errors = []
        warnings = []

        type_def = self.schema.edge_types.get(edge.rel_type)
        if not type_def:
            warnings.append(ValidationError(
                entity_type='edge',
                entity_id=edge.key,
                property_name=None,
                error_code='UNKNOWN_TYPE',
                message=f"Unknown edge type: {edge.rel_type}",
                severity='warning'
            ))
            return errors, warnings

        # Check source/target type constraints
        if type_def.source_types and edge.source[0] not in type_def.source_types:
            errors.append(ValidationError(
                entity_type='edge',
                entity_id=edge.key,
                property_name=None,
                error_code='INVALID_SOURCE_TYPE',
                message=f"Invalid source type: {edge.source[0]}, expected: {type_def.source_types}"
            ))

        if type_def.target_types and edge.target[0] not in type_def.target_types:
            errors.append(ValidationError(
                entity_type='edge',
                entity_id=edge.key,
                property_name=None,
                error_code='INVALID_TARGET_TYPE',
                message=f"Invalid target type: {edge.target[0]}, expected: {type_def.target_types}"
            ))

        # Check required properties
        for prop_name, prop_def in type_def.properties.items():
            if prop_def.required and prop_name not in edge.properties:
                errors.append(ValidationError(
                    entity_type='edge',
                    entity_id=edge.key,
                    property_name=prop_name,
                    error_code='MISSING_REQUIRED',
                    message=f"Missing required property: {prop_name}"
                ))

        return errors, warnings

    def _validate_property_value(
        self,
        entity_id: Any,
        prop_name: str,
        value: Any,
        prop_def: PropertyDef
    ) -> List[ValidationError]:
        """Validate a property value against its definition"""
        errors = []

        # Check null
        if value is None:
            if not prop_def.nullable:
                errors.append(ValidationError(
                    entity_type='node',
                    entity_id=entity_id,
                    property_name=prop_name,
                    error_code='NULL_NOT_ALLOWED',
                    message=f"Null not allowed for property: {prop_name}"
                ))
            return errors

        # Check type
        detected = TypeCoercion.detect_type(value)
        if not TypeCoercion.are_compatible(detected, prop_def.type):
            errors.append(ValidationError(
                entity_type='node',
                entity_id=entity_id,
                property_name=prop_name,
                error_code='TYPE_MISMATCH',
                message=f"Type mismatch: expected {prop_def.type.value}, got {detected.value}"
            ))

        # Check enum values
        if prop_def.enum_values and value not in prop_def.enum_values:
            errors.append(ValidationError(
                entity_type='node',
                entity_id=entity_id,
                property_name=prop_name,
                error_code='INVALID_ENUM_VALUE',
                message=f"Value must be one of: {prop_def.enum_values}"
            ))

        # Check numeric constraints
        if isinstance(value, (int, float)):
            if prop_def.min_value is not None and value < prop_def.min_value:
                errors.append(ValidationError(
                    entity_type='node',
                    entity_id=entity_id,
                    property_name=prop_name,
                    error_code='VALUE_TOO_SMALL',
                    message=f"Value must be >= {prop_def.min_value}"
                ))
            if prop_def.max_value is not None and value > prop_def.max_value:
                errors.append(ValidationError(
                    entity_type='node',
                    entity_id=entity_id,
                    property_name=prop_name,
                    error_code='VALUE_TOO_LARGE',
                    message=f"Value must be <= {prop_def.max_value}"
                ))

        # Check string constraints
        if isinstance(value, str):
            if prop_def.min_length is not None and len(value) < prop_def.min_length:
                errors.append(ValidationError(
                    entity_type='node',
                    entity_id=entity_id,
                    property_name=prop_name,
                    error_code='STRING_TOO_SHORT',
                    message=f"String must be >= {prop_def.min_length} characters"
                ))
            if prop_def.max_length is not None and len(value) > prop_def.max_length:
                errors.append(ValidationError(
                    entity_type='node',
                    entity_id=entity_id,
                    property_name=prop_name,
                    error_code='STRING_TOO_LONG',
                    message=f"String must be <= {prop_def.max_length} characters"
                ))
            if prop_def.pattern and not re.match(prop_def.pattern, value):
                errors.append(ValidationError(
                    entity_type='node',
                    entity_id=entity_id,
                    property_name=prop_name,
                    error_code='PATTERN_MISMATCH',
                    message=f"String must match pattern: {prop_def.pattern}"
                ))

        return errors

    def migrate(
        self,
        graph: ISONGraph,
        add_defaults: bool = True,
        coerce_types: bool = False,
        remove_unknown: bool = False
    ) -> ISONGraph:
        """
        Migrate a graph to conform to the schema.

        Args:
            graph: Graph to migrate
            add_defaults: Add default values for missing properties
            coerce_types: Coerce values to expected types
            remove_unknown: Remove properties not in schema

        Returns:
            Migrated graph (modified in place)
        """
        for node in graph.nodes():
            type_def = self.schema.node_types.get(node.type)
            if not type_def:
                continue

            # Add defaults
            if add_defaults:
                for prop_name, prop_def in type_def.properties.items():
                    if prop_name not in node.properties and prop_def.default is not None:
                        node.properties[prop_name] = prop_def.default

            # Coerce types
            if coerce_types:
                for prop_name, value in list(node.properties.items()):
                    prop_def = type_def.properties.get(prop_name)
                    if prop_def and prop_def.type != PropertyType.ANY:
                        try:
                            node.properties[prop_name] = TypeCoercion.coerce(
                                value, prop_def.type
                            )
                        except ValueError:
                            pass

            # Remove unknown
            if remove_unknown:
                for prop_name in list(node.properties.keys()):
                    if prop_name not in type_def.properties:
                        del node.properties[prop_name]

        return graph

    def get_migrations(self) -> List[Dict[str, Any]]:
        """Get list of migrations applied"""
        return list(self._migrations)


# =============================================================================
# Exports
# =============================================================================

__all__ = [
    # Types
    'PropertyType',
    'PropertyDef',
    'NodeTypeDef',
    'EdgeTypeDef',
    'GraphSchema',

    # Validation
    'ValidationError',
    'ValidationResult',

    # Type Coercion
    'TypeCoercion',

    # Schema Operations
    'SchemaInference',
    'SchemaManager',
]
