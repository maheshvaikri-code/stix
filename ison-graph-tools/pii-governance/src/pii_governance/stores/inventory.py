"""
PII Inventory Store
===================

Data source and PII inventory management.
"""

from typing import Any, Dict, List, Optional

from .base import BasePIIStore
from ..schema import (
    DataSourceType, StorageLocation, SensitivityLevel,
    ProtectionStatus, RetentionStatus, RiskLevel
)


class InventoryStore(BasePIIStore):
    """
    PII Inventory Management Store.

    Tracks:
    - Data sources containing PII
    - PII inventory items
    - Data ownership
    - Retention status
    """

    def register_data_source(
        self,
        source_id: str,
        name: str,
        source_type: DataSourceType,
        storage_location: StorageLocation,
        owner: str,
        custodian: str = "",
        connection_info: str = "",
        description: str = "",
    ) -> str:
        """
        Register a data source that may contain PII.

        Args:
            source_id: Unique source identifier
            name: Human-readable name
            source_type: Type of data source
            storage_location: Where data is stored
            owner: Data owner
            custodian: Technical custodian
            connection_info: Connection details (should be encrypted)
            description: Description of the source

        Returns:
            Source ID
        """
        self.graph.add_node(
            "data_source",
            source_id,
            name=name,
            source_type=source_type.value,
            storage_location=storage_location.value,
            owner=owner,
            custodian=custodian or owner,
            connection_info=self._sanitize(connection_info),
            description=self._sanitize(description),
            sensitivity_level=SensitivityLevel.INTERNAL.value,
            pii_field_count="0",
            last_scan="",
            scan_status="pending",
            created_at=self._now(),
            updated_at=self._now(),
        )

        return source_id

    def update_data_source(
        self,
        source_id: str,
        **updates
    ) -> Dict[str, Any]:
        """Update data source information"""
        node = self.graph.get_node("data_source", source_id)
        if not node:
            return {"error": "Data source not found"}

        updates["updated_at"] = self._now()
        self.graph.update_node("data_source", source_id, **updates)

        return {"source_id": source_id, "updated": True}

    def record_scan(
        self,
        source_id: str,
        pii_fields_found: int,
        highest_sensitivity: SensitivityLevel,
        scan_details: str = "",
    ) -> Dict[str, Any]:
        """Record a PII scan of a data source"""
        node = self.graph.get_node("data_source", source_id)
        if not node:
            return {"error": "Data source not found"}

        self.graph.update_node(
            "data_source",
            source_id,
            last_scan=self._now(),
            scan_status="completed",
            pii_field_count=str(pii_fields_found),
            sensitivity_level=highest_sensitivity.value,
            last_scan_details=self._sanitize(scan_details),
            updated_at=self._now(),
        )

        # Record scan history
        scan_id = self._make_id("scan", source_id)
        self.graph.add_node(
            "pii_scan",
            scan_id,
            source_id=source_id,
            scanned_at=self._now(),
            pii_fields_found=str(pii_fields_found),
            highest_sensitivity=highest_sensitivity.value,
            details=self._sanitize(scan_details),
        )

        self.graph.add_edge(
            "HAS_SCAN",
            ("data_source", source_id),
            ("pii_scan", scan_id),
        )

        return {
            "source_id": source_id,
            "scan_id": scan_id,
            "pii_fields_found": pii_fields_found,
        }

    def add_inventory_item(
        self,
        source_id: str,
        pii_type: str,
        field_location: str,
        record_count: int,
        sensitivity: SensitivityLevel,
        protection_status: ProtectionStatus,
        business_purpose: str,
        data_owner: str,
        retention_period: str = "",
        regulations: List[str] = None,
    ) -> str:
        """
        Add an item to the PII inventory.

        Args:
            source_id: Data source ID
            pii_type: Type of PII
            field_location: Location (table.column, path, etc.)
            record_count: Number of records
            sensitivity: Sensitivity level
            protection_status: Current protection status
            business_purpose: Why this PII is collected
            data_owner: Owner of the data
            retention_period: How long data is retained
            regulations: Applicable regulations

        Returns:
            Inventory item ID
        """
        item_id = self._make_id("inv", f"{source_id}_{pii_type}")

        # Calculate risk level based on sensitivity and protection
        risk_level = self._calculate_risk(sensitivity, protection_status)

        self.graph.add_node(
            "pii_inventory_item",
            item_id,
            source_id=source_id,
            pii_type=pii_type,
            field_location=field_location,
            record_count=str(record_count),
            sensitivity=sensitivity.value,
            risk_level=risk_level.value,
            protection_status=protection_status.value,
            retention_status=RetentionStatus.ACTIVE.value,
            business_purpose=self._sanitize(business_purpose),
            data_owner=data_owner,
            retention_period=retention_period,
            regulations=self._list_to_str(regulations or []),
            created_at=self._now(),
            last_updated=self._now(),
        )

        # Link to data source
        if self.graph.has_node("data_source", source_id):
            self.graph.add_edge(
                "CONTAINS_PII",
                ("data_source", source_id),
                ("pii_inventory_item", item_id),
            )

        return item_id

    def _calculate_risk(
        self,
        sensitivity: SensitivityLevel,
        protection: ProtectionStatus
    ) -> RiskLevel:
        """Calculate risk level based on sensitivity and protection"""
        sensitivity_scores = {
            SensitivityLevel.PUBLIC: 1,
            SensitivityLevel.INTERNAL: 2,
            SensitivityLevel.CONFIDENTIAL: 3,
            SensitivityLevel.RESTRICTED: 4,
            SensitivityLevel.TOP_SECRET: 5,
        }

        protection_scores = {
            ProtectionStatus.ANONYMIZED: 1,
            ProtectionStatus.PSEUDONYMIZED: 2,
            ProtectionStatus.TOKENIZED: 2,
            ProtectionStatus.FULLY_ENCRYPTED: 2,
            ProtectionStatus.ENCRYPTED_AT_REST: 3,
            ProtectionStatus.ENCRYPTED_IN_TRANSIT: 3,
            ProtectionStatus.MASKED: 3,
            ProtectionStatus.REDACTED: 2,
            ProtectionStatus.UNPROTECTED: 5,
        }

        sens_score = sensitivity_scores.get(sensitivity, 3)
        prot_score = protection_scores.get(protection, 5)

        risk_score = sens_score * prot_score

        if risk_score >= 20:
            return RiskLevel.CRITICAL
        elif risk_score >= 12:
            return RiskLevel.HIGH
        elif risk_score >= 6:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW

    def update_protection_status(
        self,
        item_id: str,
        protection_status: ProtectionStatus,
        protection_details: str = "",
    ) -> Dict[str, Any]:
        """Update protection status of an inventory item"""
        node = self.graph.get_node("pii_inventory_item", item_id)
        if not node:
            return {"error": "Inventory item not found"}

        sensitivity = SensitivityLevel(node.properties.get("sensitivity"))
        risk_level = self._calculate_risk(sensitivity, protection_status)

        self.graph.update_node(
            "pii_inventory_item",
            item_id,
            protection_status=protection_status.value,
            protection_details=protection_details,
            risk_level=risk_level.value,
            last_updated=self._now(),
        )

        return {
            "item_id": item_id,
            "protection_status": protection_status.value,
            "risk_level": risk_level.value,
        }

    def update_retention_status(
        self,
        item_id: str,
        retention_status: RetentionStatus,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Update retention status of an inventory item"""
        node = self.graph.get_node("pii_inventory_item", item_id)
        if not node:
            return {"error": "Inventory item not found"}

        self.graph.update_node(
            "pii_inventory_item",
            item_id,
            retention_status=retention_status.value,
            retention_status_reason=reason,
            retention_status_updated=self._now(),
            last_updated=self._now(),
        )

        return {
            "item_id": item_id,
            "retention_status": retention_status.value,
        }

    def get_data_source(self, source_id: str) -> Optional[Dict[str, Any]]:
        """Get data source details"""
        node = self.graph.get_node("data_source", source_id)
        if node:
            return {"id": source_id, **node.properties}
        return None

    def get_inventory_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get inventory item details"""
        node = self.graph.get_node("pii_inventory_item", item_id)
        if node:
            return {
                "id": item_id,
                **node.properties,
                "regulations": self._str_to_list(node.properties.get("regulations", "")),
            }
        return None

    def list_data_sources(
        self,
        source_type: Optional[DataSourceType] = None,
        storage_location: Optional[StorageLocation] = None,
    ) -> List[Dict[str, Any]]:
        """List data sources with optional filters"""
        results = []
        for node in self.graph.nodes():
            if node.type == "data_source":
                if source_type and node.properties.get("source_type") != source_type.value:
                    continue
                if storage_location and node.properties.get("storage_location") != storage_location.value:
                    continue
                results.append({"id": node.id, **node.properties})
        return results

    def get_inventory_by_source(self, source_id: str) -> List[Dict[str, Any]]:
        """Get all inventory items for a data source"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pii_inventory_item" and
                node.properties.get("source_id") == source_id):
                results.append(self.get_inventory_item(node.id))
        return results

    def get_inventory_by_sensitivity(
        self,
        sensitivity: SensitivityLevel
    ) -> List[Dict[str, Any]]:
        """Get inventory items at a specific sensitivity level"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pii_inventory_item" and
                node.properties.get("sensitivity") == sensitivity.value):
                results.append(self.get_inventory_item(node.id))
        return results

    def get_high_risk_inventory(self) -> List[Dict[str, Any]]:
        """Get high risk and critical inventory items"""
        results = []
        high_risk = {RiskLevel.HIGH.value, RiskLevel.CRITICAL.value}
        for node in self.graph.nodes():
            if (node.type == "pii_inventory_item" and
                node.properties.get("risk_level") in high_risk):
                results.append(self.get_inventory_item(node.id))
        return results

    def get_unprotected_inventory(self) -> List[Dict[str, Any]]:
        """Get inventory items that are not adequately protected"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pii_inventory_item" and
                node.properties.get("protection_status") == ProtectionStatus.UNPROTECTED.value):
                results.append(self.get_inventory_item(node.id))
        return results

    def search_inventory(
        self,
        pii_type: Optional[str] = None,
        data_owner: Optional[str] = None,
        regulation: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Search inventory with filters"""
        results = []
        for node in self.graph.nodes():
            if node.type == "pii_inventory_item":
                if pii_type and node.properties.get("pii_type") != pii_type:
                    continue
                if data_owner and node.properties.get("data_owner") != data_owner:
                    continue
                if regulation:
                    regulations = self._str_to_list(node.properties.get("regulations", ""))
                    if regulation not in regulations:
                        continue
                results.append(self.get_inventory_item(node.id))
        return results

    def get_stats(self) -> Dict[str, Any]:
        """Get inventory statistics"""
        sources = 0
        items = 0
        by_sensitivity = {}
        by_risk = {}
        by_protection = {}
        total_records = 0
        unprotected = 0

        for node in self.graph.nodes():
            if node.type == "data_source":
                sources += 1
            elif node.type == "pii_inventory_item":
                items += 1

                sensitivity = node.properties.get("sensitivity", "unknown")
                by_sensitivity[sensitivity] = by_sensitivity.get(sensitivity, 0) + 1

                risk = node.properties.get("risk_level", "unknown")
                by_risk[risk] = by_risk.get(risk, 0) + 1

                protection = node.properties.get("protection_status", "unknown")
                by_protection[protection] = by_protection.get(protection, 0) + 1

                if protection == ProtectionStatus.UNPROTECTED.value:
                    unprotected += 1

                try:
                    total_records += int(node.properties.get("record_count", "0"))
                except ValueError:
                    pass

        return {
            "total_data_sources": sources,
            "total_inventory_items": items,
            "total_records_with_pii": total_records,
            "unprotected_items": unprotected,
            "by_sensitivity": by_sensitivity,
            "by_risk_level": by_risk,
            "by_protection_status": by_protection,
        }
