"""
Data Lineage Store
==================

PII data flow and lineage tracking.
"""

from typing import Any, Dict, List, Optional

from .base import BasePIIStore
from ..schema import DataLifecycleStage


class LineageStore(BasePIIStore):
    """
    PII Data Lineage Store.

    Tracks:
    - Data flow between systems
    - Transformations applied to PII
    - Data lifecycle stages
    - Impact analysis
    """

    def record_data_flow(
        self,
        source_system: str,
        target_system: str,
        pii_types: List[str],
        purpose: str,
        transformation: str = "",
        frequency: str = "",
    ) -> str:
        """
        Record a data flow between systems.

        Args:
            source_system: Source system/data source ID
            target_system: Target system/data source ID
            pii_types: Types of PII in the flow
            purpose: Business purpose for the flow
            transformation: Any transformation applied
            frequency: How often data flows (e.g., "real-time", "daily")

        Returns:
            Flow ID
        """
        flow_id = self._make_id("flow", f"{source_system}_{target_system}")

        self.graph.add_node(
            "data_flow",
            flow_id,
            source_system=source_system,
            target_system=target_system,
            pii_types=self._list_to_str(pii_types),
            purpose=self._sanitize(purpose),
            transformation=self._sanitize(transformation),
            frequency=frequency,
            status="active",
            created_at=self._now(),
            last_execution="",
        )

        # Create edges for lineage graph
        if self.graph.has_node("data_source", source_system):
            self.graph.add_edge(
                "FLOWS_FROM",
                ("data_flow", flow_id),
                ("data_source", source_system),
            )

        if self.graph.has_node("data_source", target_system):
            self.graph.add_edge(
                "FLOWS_TO",
                ("data_flow", flow_id),
                ("data_source", target_system),
            )

        return flow_id

    def record_transformation(
        self,
        flow_id: str,
        transformation_type: str,
        description: str,
        input_fields: List[str],
        output_fields: List[str],
    ) -> str:
        """
        Record a data transformation in a flow.

        Args:
            flow_id: Data flow ID
            transformation_type: Type (aggregation, masking, encryption, etc.)
            description: Description of transformation
            input_fields: Input field names
            output_fields: Output field names

        Returns:
            Transformation ID
        """
        transform_id = self._make_id("transform", flow_id)

        self.graph.add_node(
            "data_transformation",
            transform_id,
            flow_id=flow_id,
            transformation_type=transformation_type,
            description=self._sanitize(description),
            input_fields=self._list_to_str(input_fields),
            output_fields=self._list_to_str(output_fields),
            created_at=self._now(),
        )

        if self.graph.has_node("data_flow", flow_id):
            self.graph.add_edge(
                "HAS_TRANSFORMATION",
                ("data_flow", flow_id),
                ("data_transformation", transform_id),
            )

        return transform_id

    def record_lifecycle_event(
        self,
        pii_field_id: str,
        stage: DataLifecycleStage,
        system: str,
        actor: str,
        details: str = "",
    ) -> str:
        """
        Record a lifecycle event for a PII field.

        Args:
            pii_field_id: PII field ID
            stage: Lifecycle stage
            system: System where event occurred
            actor: Who/what performed the action
            details: Additional details

        Returns:
            Event ID
        """
        event_id = self._make_id("lifecycle", f"{pii_field_id}_{stage.value}")

        self.graph.add_node(
            "lifecycle_event",
            event_id,
            pii_field_id=pii_field_id,
            stage=stage.value,
            system=system,
            actor=actor,
            details=self._sanitize(details),
            occurred_at=self._now(),
        )

        if self.graph.has_node("pii_classification", pii_field_id):
            self.graph.add_edge(
                "HAS_LIFECYCLE_EVENT",
                ("pii_classification", pii_field_id),
                ("lifecycle_event", event_id),
            )

        return event_id

    def get_data_flow(self, flow_id: str) -> Optional[Dict[str, Any]]:
        """Get data flow details"""
        node = self.graph.get_node("data_flow", flow_id)
        if node:
            # Get transformations
            transformations = []
            for n in self.graph.nodes():
                if (n.type == "data_transformation" and
                    n.properties.get("flow_id") == flow_id):
                    transformations.append({"id": n.id, **n.properties})

            return {
                "id": flow_id,
                **node.properties,
                "pii_types": self._str_to_list(node.properties.get("pii_types", "")),
                "transformations": transformations,
            }
        return None

    def get_flows_from_source(self, source_system: str) -> List[Dict[str, Any]]:
        """Get all data flows from a source system"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "data_flow" and
                node.properties.get("source_system") == source_system):
                results.append(self.get_data_flow(node.id))
        return results

    def get_flows_to_target(self, target_system: str) -> List[Dict[str, Any]]:
        """Get all data flows to a target system"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "data_flow" and
                node.properties.get("target_system") == target_system):
                results.append(self.get_data_flow(node.id))
        return results

    def get_pii_lineage(self, pii_type: str) -> List[Dict[str, Any]]:
        """Get lineage for a specific PII type"""
        results = []
        for node in self.graph.nodes():
            if node.type == "data_flow":
                pii_types = self._str_to_list(node.properties.get("pii_types", ""))
                if pii_type in pii_types:
                    results.append(self.get_data_flow(node.id))
        return results

    def get_field_lifecycle(self, pii_field_id: str) -> List[Dict[str, Any]]:
        """Get lifecycle history for a PII field"""
        events = []
        for node in self.graph.nodes():
            if (node.type == "lifecycle_event" and
                node.properties.get("pii_field_id") == pii_field_id):
                events.append({"id": node.id, **node.properties})
        return sorted(events, key=lambda x: x.get("occurred_at", ""))

    def trace_upstream(self, system_id: str, depth: int = 5) -> Dict[str, Any]:
        """
        Trace data lineage upstream from a system.

        Returns systems that feed data into the specified system.
        """
        visited = set()
        upstream = []

        def trace(system: str, current_depth: int):
            if current_depth > depth or system in visited:
                return
            visited.add(system)

            for node in self.graph.nodes():
                if (node.type == "data_flow" and
                    node.properties.get("target_system") == system):
                    source = node.properties.get("source_system")
                    upstream.append({
                        "system": source,
                        "flow_id": node.id,
                        "depth": current_depth,
                        "pii_types": self._str_to_list(
                            node.properties.get("pii_types", "")
                        ),
                    })
                    trace(source, current_depth + 1)

        trace(system_id, 1)
        return {
            "target_system": system_id,
            "upstream_systems": upstream,
        }

    def trace_downstream(self, system_id: str, depth: int = 5) -> Dict[str, Any]:
        """
        Trace data lineage downstream from a system.

        Returns systems that receive data from the specified system.
        """
        visited = set()
        downstream = []

        def trace(system: str, current_depth: int):
            if current_depth > depth or system in visited:
                return
            visited.add(system)

            for node in self.graph.nodes():
                if (node.type == "data_flow" and
                    node.properties.get("source_system") == system):
                    target = node.properties.get("target_system")
                    downstream.append({
                        "system": target,
                        "flow_id": node.id,
                        "depth": current_depth,
                        "pii_types": self._str_to_list(
                            node.properties.get("pii_types", "")
                        ),
                    })
                    trace(target, current_depth + 1)

        trace(system_id, 1)
        return {
            "source_system": system_id,
            "downstream_systems": downstream,
        }

    def impact_analysis(self, system_id: str) -> Dict[str, Any]:
        """
        Perform impact analysis for a system.

        Identifies all systems and PII types that would be affected
        if the specified system has issues.
        """
        downstream = self.trace_downstream(system_id)

        affected_systems = set()
        affected_pii_types = set()

        for item in downstream["downstream_systems"]:
            affected_systems.add(item["system"])
            for pii_type in item["pii_types"]:
                affected_pii_types.add(pii_type)

        return {
            "source_system": system_id,
            "affected_systems_count": len(affected_systems),
            "affected_systems": list(affected_systems),
            "affected_pii_types": list(affected_pii_types),
            "impact_level": "high" if len(affected_systems) > 5 else
                          "medium" if len(affected_systems) > 2 else "low",
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get lineage statistics"""
        flows = 0
        transformations = 0
        lifecycle_events = 0
        systems_with_flows = set()
        pii_types_in_flows = set()

        for node in self.graph.nodes():
            if node.type == "data_flow":
                flows += 1
                systems_with_flows.add(node.properties.get("source_system"))
                systems_with_flows.add(node.properties.get("target_system"))
                for pii in self._str_to_list(node.properties.get("pii_types", "")):
                    pii_types_in_flows.add(pii)
            elif node.type == "data_transformation":
                transformations += 1
            elif node.type == "lifecycle_event":
                lifecycle_events += 1

        return {
            "total_data_flows": flows,
            "total_transformations": transformations,
            "total_lifecycle_events": lifecycle_events,
            "systems_with_flows": len(systems_with_flows),
            "pii_types_in_flows": len(pii_types_in_flows),
        }
