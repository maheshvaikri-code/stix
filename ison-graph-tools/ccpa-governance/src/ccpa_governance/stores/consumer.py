"""
Consumer Store
==============

Manages consumer records and personal information inventory.
"""

from typing import Any, Dict, List, Optional

from .base import BaseCCPAStore
from ..schema import (
    PersonalInfoCategory, SensitivePersonalInfo,
    OptOutStatus, MinorCategory
)


class ConsumerStore(BaseCCPAStore):
    """
    Consumer Management Store.

    Tracks:
    - Consumer registration and identification
    - Personal information inventory
    - California residency status
    - Minor status and protections
    - Opt-out preferences
    """

    def register_consumer(
        self,
        consumer_id: str,
        external_id: Optional[str] = None,
        email: Optional[str] = None,
        is_california_resident: bool = True,
        is_minor: bool = False,
        minor_category: Optional[MinorCategory] = None,
    ) -> str:
        """
        Register a consumer.

        Args:
            consumer_id: Internal consumer ID
            external_id: External/customer ID
            email: Consumer email
            is_california_resident: Whether consumer is CA resident
            is_minor: Whether consumer is a minor
            minor_category: Age category for minors

        Returns:
            Consumer node ID
        """
        node_id = f"consumer_{consumer_id}"

        self.graph.add_node(
            "consumer",
            node_id,
            consumer_id=consumer_id,
            external_id=external_id or "",
            email=email or "",
            is_california_resident=str(is_california_resident),
            is_minor=str(is_minor),
            minor_category=minor_category.value if minor_category else "",
            opt_out_status=OptOutStatus.NOT_OPTED_OUT.value,
            opt_out_sale=str(False),
            opt_out_share=str(False),
            limit_spi=str(False),
            gpc_signal_detected=str(False),
            pi_categories="",
            spi_categories="",
            created_at=self._now(),
            last_activity=self._now(),
        )

        return node_id

    def add_personal_info(
        self,
        consumer_id: str,
        category: PersonalInfoCategory,
        source: str,
        purpose: str,
        is_sensitive: bool = False,
    ) -> str:
        """
        Record personal information held for a consumer.

        Args:
            consumer_id: Consumer ID
            category: Category of personal information
            source: Where PI was collected from
            purpose: Business purpose for collection
            is_sensitive: Whether this is Sensitive PI (CPRA)

        Returns:
            PI record ID
        """
        node_id = f"consumer_{consumer_id}"
        pi_id = self._make_id("pi", f"{consumer_id}_{category.value}")

        self.graph.add_node(
            "personal_information",
            pi_id,
            consumer_id=consumer_id,
            category=category.value,
            source=source,
            purpose=purpose,
            is_sensitive=str(is_sensitive),
            collected_at=self._now(),
            retention_period="",
            disclosed_to="",
            sold_to="",
            shared_to="",
        )

        # Link to consumer
        if self.graph.has_node("consumer", node_id):
            self.graph.add_edge(
                "HAS_PI",
                ("consumer", node_id),
                ("personal_information", pi_id),
            )

            # Update consumer's PI categories
            consumer = self.graph.get_node("consumer", node_id)
            if consumer:
                categories = self._str_to_list(
                    consumer.properties.get("pi_categories", "")
                )
                if category.value not in categories:
                    categories.append(category.value)
                    self.graph.update_node(
                        "consumer", node_id,
                        pi_categories=self._list_to_str(categories)
                    )

                # Track sensitive PI
                if is_sensitive:
                    spi_cats = self._str_to_list(
                        consumer.properties.get("spi_categories", "")
                    )
                    if category.value not in spi_cats:
                        spi_cats.append(category.value)
                        self.graph.update_node(
                            "consumer", node_id,
                            spi_categories=self._list_to_str(spi_cats)
                        )

        return pi_id

    def update_opt_out_status(
        self,
        consumer_id: str,
        opt_out_sale: bool = False,
        opt_out_share: bool = False,
        limit_spi: bool = False,
        gpc_detected: bool = False,
        method: str = "",
    ) -> Dict[str, Any]:
        """
        Update consumer's opt-out preferences.

        Args:
            consumer_id: Consumer ID
            opt_out_sale: Opt out of PI sale
            opt_out_share: Opt out of PI sharing (cross-context ads)
            limit_spi: Limit use of Sensitive PI (CPRA)
            gpc_detected: Global Privacy Control signal detected
            method: How opt-out was submitted

        Returns:
            Updated status
        """
        node_id = f"consumer_{consumer_id}"
        node = self.graph.get_node("consumer", node_id)
        if not node:
            return {"error": "Consumer not found"}

        # Determine overall status
        if opt_out_sale and opt_out_share:
            status = OptOutStatus.OPTED_OUT_BOTH
        elif opt_out_sale:
            status = OptOutStatus.OPTED_OUT_SALE
        elif opt_out_share:
            status = OptOutStatus.OPTED_OUT_SHARE
        elif limit_spi:
            status = OptOutStatus.OPTED_OUT_SPI
        elif gpc_detected:
            status = OptOutStatus.GPC_DETECTED
        else:
            status = OptOutStatus.NOT_OPTED_OUT

        self.graph.update_node(
            "consumer",
            node_id,
            opt_out_status=status.value,
            opt_out_sale=str(opt_out_sale),
            opt_out_share=str(opt_out_share),
            limit_spi=str(limit_spi),
            gpc_signal_detected=str(gpc_detected),
            opt_out_method=method,
            opt_out_at=self._now() if any([opt_out_sale, opt_out_share, limit_spi]) else "",
            last_activity=self._now(),
        )

        # Record opt-out event
        self._record_opt_out_event(consumer_id, status.value, method)

        return {
            "consumer_id": consumer_id,
            "opt_out_status": status.value,
            "opt_out_sale": opt_out_sale,
            "opt_out_share": opt_out_share,
            "limit_spi": limit_spi,
        }

    def check_opt_out_status(self, consumer_id: str) -> Dict[str, Any]:
        """Check consumer's current opt-out status"""
        node_id = f"consumer_{consumer_id}"
        node = self.graph.get_node("consumer", node_id)
        if not node:
            return {"error": "Consumer not found", "can_sell": True, "can_share": True}

        return {
            "consumer_id": consumer_id,
            "opt_out_status": node.properties.get("opt_out_status"),
            "can_sell": node.properties.get("opt_out_sale") != "True",
            "can_share": node.properties.get("opt_out_share") != "True",
            "can_use_spi": node.properties.get("limit_spi") != "True",
            "gpc_detected": node.properties.get("gpc_signal_detected") == "True",
        }

    def get_consumer(self, consumer_id: str) -> Optional[Dict[str, Any]]:
        """Get consumer record"""
        node_id = f"consumer_{consumer_id}"
        node = self.graph.get_node("consumer", node_id)
        if node:
            return {
                "id": node_id,
                **node.properties,
                "pi_categories": self._str_to_list(
                    node.properties.get("pi_categories", "")
                ),
                "spi_categories": self._str_to_list(
                    node.properties.get("spi_categories", "")
                ),
            }
        return None

    def get_consumer_pi_inventory(
        self,
        consumer_id: str,
        sensitive_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """Get all personal information held for a consumer"""
        inventory = []
        for node in self.graph.nodes():
            if (node.type == "personal_information" and
                node.properties.get("consumer_id") == consumer_id):
                if sensitive_only and node.properties.get("is_sensitive") != "True":
                    continue
                inventory.append({"id": node.id, **node.properties})
        return inventory

    def delete_consumer_pi(
        self,
        consumer_id: str,
        categories: Optional[List[PersonalInfoCategory]] = None,
        reason: str = "consumer_request",
    ) -> Dict[str, Any]:
        """
        Delete personal information for a consumer (Right to Delete).

        Args:
            consumer_id: Consumer ID
            categories: Specific categories to delete (None = all)
            reason: Reason for deletion

        Returns:
            Summary of deleted data
        """
        deleted = []

        for node in list(self.graph.nodes()):
            if (node.type == "personal_information" and
                node.properties.get("consumer_id") == consumer_id):
                if categories is None or PersonalInfoCategory(
                    node.properties.get("category")
                ) in categories:
                    deleted.append({
                        "category": node.properties.get("category"),
                        "deleted_at": self._now(),
                    })
                    self.graph.remove_node("personal_information", node.id)

        # Record deletion
        deletion_id = self._make_id("deletion", consumer_id)
        self.graph.add_node(
            "pi_deletion",
            deletion_id,
            consumer_id=consumer_id,
            reason=reason,
            categories_deleted=self._list_to_str([d["category"] for d in deleted]),
            deleted_at=self._now(),
        )

        return {
            "consumer_id": consumer_id,
            "deleted_count": len(deleted),
            "deleted_categories": deleted,
            "deletion_id": deletion_id,
        }

    def search_consumers(
        self,
        email: Optional[str] = None,
        external_id: Optional[str] = None,
        is_minor: Optional[bool] = None,
        opted_out: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Search for consumers"""
        results = []
        for node in self.graph.nodes():
            if node.type == "consumer":
                if email and node.properties.get("email") != email:
                    continue
                if external_id and node.properties.get("external_id") != external_id:
                    continue
                if is_minor is not None:
                    if str(is_minor) != node.properties.get("is_minor"):
                        continue
                if opted_out is not None:
                    has_opted_out = node.properties.get("opt_out_status") != \
                                   OptOutStatus.NOT_OPTED_OUT.value
                    if opted_out != has_opted_out:
                        continue
                results.append({"id": node.id, **node.properties})
        return results

    def _record_opt_out_event(
        self,
        consumer_id: str,
        status: str,
        method: str,
    ) -> None:
        """Record opt-out audit event"""
        event_id = self._make_id("opt_out_event", consumer_id)
        self.graph.add_node(
            "opt_out_event",
            event_id,
            consumer_id=consumer_id,
            status=status,
            method=method,
            timestamp=self._now(),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get consumer statistics"""
        total = 0
        california = 0
        minors = 0
        opted_out_sale = 0
        opted_out_share = 0
        with_spi = 0

        for node in self.graph.nodes():
            if node.type == "consumer":
                total += 1
                if node.properties.get("is_california_resident") == "True":
                    california += 1
                if node.properties.get("is_minor") == "True":
                    minors += 1
                if node.properties.get("opt_out_sale") == "True":
                    opted_out_sale += 1
                if node.properties.get("opt_out_share") == "True":
                    opted_out_share += 1
                if node.properties.get("spi_categories"):
                    with_spi += 1

        return {
            "total_consumers": total,
            "california_residents": california,
            "minors": minors,
            "opted_out_sale": opted_out_sale,
            "opted_out_share": opted_out_share,
            "with_sensitive_pi": with_spi,
        }
