"""
Notice Store
============

CCPA Notice and Disclosure management.
"""

from typing import Any, Dict, List, Optional

from .base import BaseCCPAStore
from ..schema import (
    NoticeType, DisclosureCategory, PersonalInfoCategory
)


class NoticeStore(BaseCCPAStore):
    """
    CCPA Notice and Disclosure Management.

    Tracks:
    - Privacy policy versions
    - Notice at Collection
    - "Do Not Sell" link compliance
    - "Limit Sensitive PI" link (CPRA)
    - Financial incentive notices
    - Required disclosures
    """

    def create_notice(
        self,
        notice_type: NoticeType,
        version: str,
        effective_date: str,
        content_summary: str,
        url: Optional[str] = None,
        categories_disclosed: Optional[List[DisclosureCategory]] = None,
    ) -> str:
        """
        Create a new notice record.

        Args:
            notice_type: Type of notice
            version: Version number
            effective_date: When notice becomes effective
            content_summary: Summary of notice contents
            url: URL where notice is published
            categories_disclosed: What disclosure categories are covered

        Returns:
            Notice ID
        """
        notice_id = self._make_id("notice", f"{notice_type.value}_{version}")

        disclosed = [c.value for c in (categories_disclosed or [])]

        self.graph.add_node(
            "ccpa_notice",
            notice_id,
            notice_type=notice_type.value,
            version=version,
            effective_date=effective_date,
            content_summary=self._sanitize(content_summary),
            url=url or "",
            categories_disclosed=self._list_to_str(disclosed),
            created_at=self._now(),
            last_updated=self._now(),
            is_current=str(True),
        )

        # Mark previous versions as not current
        for node in self.graph.nodes():
            if (node.type == "ccpa_notice" and
                node.properties.get("notice_type") == notice_type.value and
                node.id != notice_id):
                self.graph.update_node(
                    "ccpa_notice",
                    node.id,
                    is_current=str(False),
                )

        return notice_id

    def update_notice(
        self,
        notice_id: str,
        content_summary: Optional[str] = None,
        url: Optional[str] = None,
        categories_disclosed: Optional[List[DisclosureCategory]] = None,
    ) -> Dict[str, Any]:
        """Update an existing notice"""
        node = self.graph.get_node("ccpa_notice", notice_id)
        if not node:
            return {"error": "Notice not found"}

        updates = {"last_updated": self._now()}
        if content_summary:
            updates["content_summary"] = self._sanitize(content_summary)
        if url:
            updates["url"] = url
        if categories_disclosed:
            updates["categories_disclosed"] = self._list_to_str(
                [c.value for c in categories_disclosed]
            )

        self.graph.update_node("ccpa_notice", notice_id, **updates)

        return {"notice_id": notice_id, "updated": True}

    def get_current_notice(
        self,
        notice_type: NoticeType
    ) -> Optional[Dict[str, Any]]:
        """Get the current version of a notice type"""
        for node in self.graph.nodes():
            if (node.type == "ccpa_notice" and
                node.properties.get("notice_type") == notice_type.value and
                node.properties.get("is_current") == "True"):
                return {
                    "id": node.id,
                    **node.properties,
                    "categories_disclosed": self._str_to_list(
                        node.properties.get("categories_disclosed", "")
                    ),
                }
        return None

    def get_notice_history(
        self,
        notice_type: NoticeType
    ) -> List[Dict[str, Any]]:
        """Get all versions of a notice type"""
        results = []
        for node in self.graph.nodes():
            if (node.type == "ccpa_notice" and
                node.properties.get("notice_type") == notice_type.value):
                results.append({"id": node.id, **node.properties})
        return sorted(results, key=lambda x: x.get("effective_date", ""), reverse=True)

    def record_disclosure(
        self,
        disclosure_type: str,
        pi_categories: List[PersonalInfoCategory],
        sources: List[str],
        purposes: List[str],
        third_parties: List[str],
        retention_periods: Dict[str, str] = None,
    ) -> str:
        """
        Record the specific disclosures made in privacy policy.

        This tracks what was actually disclosed to comply with
        CCPA Section 1798.130 requirements.
        """
        disclosure_id = self._make_id("disclosure", disclosure_type)

        self.graph.add_node(
            "ccpa_disclosure",
            disclosure_id,
            disclosure_type=disclosure_type,
            pi_categories=self._list_to_str([c.value for c in pi_categories]),
            sources=self._list_to_str(sources),
            purposes=self._list_to_str(purposes),
            third_parties=self._list_to_str(third_parties),
            retention_periods=str(retention_periods or {}),
            recorded_at=self._now(),
        )

        return disclosure_id

    def check_notice_compliance(self) -> Dict[str, Any]:
        """
        Check if all required notices are in place.

        Returns compliance status for each notice type.
        """
        required_notices = [
            NoticeType.PRIVACY_POLICY,
            NoticeType.NOTICE_AT_COLLECTION,
            NoticeType.DO_NOT_SELL_LINK,
        ]

        # Add CPRA requirement
        required_notices.append(NoticeType.LIMIT_SPI_LINK)

        compliance = {}
        for notice_type in required_notices:
            notice = self.get_current_notice(notice_type)
            compliance[notice_type.value] = {
                "exists": notice is not None,
                "version": notice.get("version") if notice else None,
                "last_updated": notice.get("last_updated") if notice else None,
                "url": notice.get("url") if notice else None,
            }

        all_compliant = all(c["exists"] for c in compliance.values())

        return {
            "all_notices_present": all_compliant,
            "notices": compliance,
        }

    def record_consent_collection(
        self,
        consumer_id: str,
        notice_id: str,
        notice_version: str,
        collection_point: str,
    ) -> str:
        """Record that notice was provided at point of collection"""
        record_id = self._make_id("notice_collection", consumer_id)

        self.graph.add_node(
            "notice_collection",
            record_id,
            consumer_id=consumer_id,
            notice_id=notice_id,
            notice_version=notice_version,
            collection_point=collection_point,
            provided_at=self._now(),
        )

        return record_id

    def get_stats(self) -> Dict[str, Any]:
        """Get notice statistics"""
        notices_by_type = {}
        current_notices = 0
        total_notices = 0

        for node in self.graph.nodes():
            if node.type == "ccpa_notice":
                total_notices += 1
                notice_type = node.properties.get("notice_type", "unknown")
                notices_by_type[notice_type] = notices_by_type.get(notice_type, 0) + 1
                if node.properties.get("is_current") == "True":
                    current_notices += 1

        compliance = self.check_notice_compliance()

        return {
            "total_notices": total_notices,
            "current_notices": current_notices,
            "by_type": notices_by_type,
            "compliance_status": compliance["all_notices_present"],
        }
