"""
Sale and Share Store
====================

Tracks sale and sharing of personal information under CCPA/CPRA.
"""

from typing import Any, Dict, List, Optional

from .base import BaseCCPAStore
from ..schema import (
    PersonalInfoCategory, SaleShareType, BusinessRole, OptOutStatus
)


class SaleShareStore(BaseCCPAStore):
    """
    Personal Information Sale and Sharing Management.

    Tracks:
    - Sale of PI (monetary or valuable consideration)
    - Sharing for cross-context behavioral advertising (CPRA)
    - Opt-out compliance
    - Third party disclosures
    """

    def register_recipient(
        self,
        recipient_id: str,
        name: str,
        role: BusinessRole,
        contact: str = "",
        contract_date: str = "",
    ) -> str:
        """
        Register a recipient of personal information.

        Args:
            recipient_id: Recipient identifier
            name: Recipient name
            role: Business role (third_party, service_provider, contractor)
            contact: Contact information
            contract_date: Date of contract if applicable

        Returns:
            Recipient node ID
        """
        self.graph.add_node(
            "pi_recipient",
            recipient_id,
            name=name,
            role=role.value,
            contact=contact,
            contract_date=contract_date,
            created_at=self._now(),
        )

        return recipient_id

    def record_sale(
        self,
        consumer_id: str,
        recipient_id: str,
        pi_categories: List[PersonalInfoCategory],
        purpose: str,
        consideration: str = "",
    ) -> Dict[str, Any]:
        """
        Record a sale of personal information.

        Sale = disclosure for monetary or other valuable consideration.
        Must check opt-out status before selling.

        Args:
            consumer_id: Consumer ID
            recipient_id: Recipient ID
            pi_categories: Categories of PI sold
            purpose: Purpose of sale
            consideration: What was received in exchange

        Returns:
            Sale record or error if opted out
        """
        # Check opt-out status
        consumer_node_id = f"consumer_{consumer_id}"
        consumer = self.graph.get_node("consumer", consumer_node_id)

        if consumer:
            opt_out_sale = consumer.properties.get("opt_out_sale") == "True"
            gpc = consumer.properties.get("gpc_signal_detected") == "True"

            if opt_out_sale or gpc:
                return {
                    "error": "Consumer has opted out of sale",
                    "opt_out_status": consumer.properties.get("opt_out_status"),
                    "sale_blocked": True,
                }

        sale_id = self._make_id("sale", f"{consumer_id}_{recipient_id}")

        self.graph.add_node(
            "pi_sale",
            sale_id,
            consumer_id=consumer_id,
            recipient_id=recipient_id,
            transfer_type=SaleShareType.SALE.value,
            pi_categories=self._list_to_str([c.value for c in pi_categories]),
            purpose=self._sanitize(purpose),
            consideration=consideration,
            transferred_at=self._now(),
            opt_out_checked=str(True),
            opt_out_status=consumer.properties.get("opt_out_status") if consumer else "",
        )

        # Link to consumer and recipient
        if self.graph.has_node("consumer", consumer_node_id):
            self.graph.add_edge(
                "PI_SOLD",
                ("consumer", consumer_node_id),
                ("pi_sale", sale_id),
            )

        if self.graph.has_node("pi_recipient", recipient_id):
            self.graph.add_edge(
                "SOLD_TO",
                ("pi_sale", sale_id),
                ("pi_recipient", recipient_id),
            )

        return {
            "sale_id": sale_id,
            "consumer_id": consumer_id,
            "recipient_id": recipient_id,
            "categories": [c.value for c in pi_categories],
            "transferred_at": self._now(),
        }

    def record_share(
        self,
        consumer_id: str,
        recipient_id: str,
        pi_categories: List[PersonalInfoCategory],
        advertising_purpose: str,
    ) -> Dict[str, Any]:
        """
        Record sharing for cross-context behavioral advertising (CPRA).

        Sharing = disclosure for cross-context behavioral advertising,
        regardless of monetary exchange.

        Args:
            consumer_id: Consumer ID
            recipient_id: Advertising partner ID
            pi_categories: Categories of PI shared
            advertising_purpose: Purpose of sharing

        Returns:
            Share record or error if opted out
        """
        # Check opt-out status
        consumer_node_id = f"consumer_{consumer_id}"
        consumer = self.graph.get_node("consumer", consumer_node_id)

        if consumer:
            opt_out_share = consumer.properties.get("opt_out_share") == "True"
            gpc = consumer.properties.get("gpc_signal_detected") == "True"

            if opt_out_share or gpc:
                return {
                    "error": "Consumer has opted out of sharing",
                    "opt_out_status": consumer.properties.get("opt_out_status"),
                    "share_blocked": True,
                }

        share_id = self._make_id("share", f"{consumer_id}_{recipient_id}")

        self.graph.add_node(
            "pi_share",
            share_id,
            consumer_id=consumer_id,
            recipient_id=recipient_id,
            transfer_type=SaleShareType.SHARE.value,
            pi_categories=self._list_to_str([c.value for c in pi_categories]),
            purpose=self._sanitize(advertising_purpose),
            transferred_at=self._now(),
            opt_out_checked=str(True),
            opt_out_status=consumer.properties.get("opt_out_status") if consumer else "",
        )

        # Link to consumer and recipient
        if self.graph.has_node("consumer", consumer_node_id):
            self.graph.add_edge(
                "PI_SHARED",
                ("consumer", consumer_node_id),
                ("pi_share", share_id),
            )

        if self.graph.has_node("pi_recipient", recipient_id):
            self.graph.add_edge(
                "SHARED_TO",
                ("pi_share", share_id),
                ("pi_recipient", recipient_id),
            )

        return {
            "share_id": share_id,
            "consumer_id": consumer_id,
            "recipient_id": recipient_id,
            "categories": [c.value for c in pi_categories],
            "transferred_at": self._now(),
        }

    def record_service_provider_disclosure(
        self,
        consumer_id: str,
        provider_id: str,
        pi_categories: List[PersonalInfoCategory],
        business_purpose: str,
        contract_reference: str = "",
    ) -> str:
        """
        Record disclosure to service provider (not a sale).

        Service provider disclosures are permitted without opt-out
        when proper contract is in place.
        """
        disclosure_id = self._make_id("sp_disclosure", f"{consumer_id}_{provider_id}")

        self.graph.add_node(
            "service_provider_disclosure",
            disclosure_id,
            consumer_id=consumer_id,
            provider_id=provider_id,
            transfer_type=SaleShareType.SERVICE_PROVIDER.value,
            pi_categories=self._list_to_str([c.value for c in pi_categories]),
            business_purpose=self._sanitize(business_purpose),
            contract_reference=contract_reference,
            disclosed_at=self._now(),
        )

        return disclosure_id

    def get_consumer_sales(self, consumer_id: str) -> List[Dict[str, Any]]:
        """Get all sales for a consumer"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pi_sale" and
                node.properties.get("consumer_id") == consumer_id):
                results.append({
                    "id": node.id,
                    **node.properties,
                    "pi_categories": self._str_to_list(
                        node.properties.get("pi_categories", "")
                    ),
                })
        return results

    def get_consumer_shares(self, consumer_id: str) -> List[Dict[str, Any]]:
        """Get all shares for a consumer"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pi_share" and
                node.properties.get("consumer_id") == consumer_id):
                results.append({
                    "id": node.id,
                    **node.properties,
                    "pi_categories": self._str_to_list(
                        node.properties.get("pi_categories", "")
                    ),
                })
        return results

    def get_recipient_sales(self, recipient_id: str) -> List[Dict[str, Any]]:
        """Get all sales to a specific recipient"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "pi_sale" and
                node.properties.get("recipient_id") == recipient_id):
                results.append({"id": node.id, **node.properties})
        return results

    def get_categories_sold_last_12_months(self) -> Dict[str, int]:
        """Get categories of PI sold in last 12 months (for disclosure)"""
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=365)).isoformat()

        categories = {}
        for node in self.graph.nodes():
            if node.type == "pi_sale":
                transferred = node.properties.get("transferred_at", "")
                if transferred >= cutoff:
                    cats = self._str_to_list(node.properties.get("pi_categories", ""))
                    for cat in cats:
                        categories[cat] = categories.get(cat, 0) + 1
        return categories

    def get_categories_shared_last_12_months(self) -> Dict[str, int]:
        """Get categories of PI shared in last 12 months (for disclosure)"""
        from datetime import datetime, timedelta
        cutoff = (datetime.now() - timedelta(days=365)).isoformat()

        categories = {}
        for node in self.graph.nodes():
            if node.type == "pi_share":
                transferred = node.properties.get("transferred_at", "")
                if transferred >= cutoff:
                    cats = self._str_to_list(node.properties.get("pi_categories", ""))
                    for cat in cats:
                        categories[cat] = categories.get(cat, 0) + 1
        return categories

    def get_stats(self) -> Dict[str, Any]:
        """Get sale/share statistics"""
        total_sales = 0
        total_shares = 0
        total_sp_disclosures = 0
        sales_blocked = 0
        shares_blocked = 0
        by_recipient = {}
        categories_sold = set()
        categories_shared = set()

        for node in self.graph.nodes():
            if node.type == "pi_sale":
                total_sales += 1
                recipient = node.properties.get("recipient_id", "unknown")
                by_recipient[recipient] = by_recipient.get(recipient, 0) + 1
                for cat in self._str_to_list(node.properties.get("pi_categories", "")):
                    categories_sold.add(cat)
            elif node.type == "pi_share":
                total_shares += 1
                for cat in self._str_to_list(node.properties.get("pi_categories", "")):
                    categories_shared.add(cat)
            elif node.type == "service_provider_disclosure":
                total_sp_disclosures += 1

        return {
            "total_sales": total_sales,
            "total_shares": total_shares,
            "total_service_provider_disclosures": total_sp_disclosures,
            "categories_sold": list(categories_sold),
            "categories_shared": list(categories_shared),
            "sales_by_recipient": by_recipient,
        }
