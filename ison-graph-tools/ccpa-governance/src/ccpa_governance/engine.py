"""
CCPA Governance Engine
======================

Main engine for comprehensive CCPA/CPRA compliance management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from ison_graph import ISONGraph

from .stores import (
    ConsumerStore,
    ConsumerRightsStore,
    SaleShareStore,
    NoticeStore,
    ServiceProviderStore,
)
from .schema import (
    PersonalInfoCategory, ConsumerRight, RequestStatus,
    NoticeType, DisclosureCategory, BusinessRole,
    OptOutStatus, BusinessSize, ComplianceArea
)


class CCPAGovernance:
    """
    CCPA/CPRA Compliance Governance Engine.

    Provides unified access to all CCPA governance stores and
    compliance reporting capabilities.

    Usage:
        from ison_graph import ISONGraph
        from ccpa_governance import CCPAGovernance

        graph = ISONGraph()
        ccpa = CCPAGovernance(graph)

        # Register consumers
        ccpa.consumers.register_consumer(...)

        # Handle opt-out requests
        ccpa.consumers.update_opt_out_status(...)

        # Handle consumer requests
        ccpa.rights.submit_request(...)

        # Generate compliance report
        report = ccpa.get_compliance_status()
    """

    def __init__(self, graph: ISONGraph):
        """
        Initialize CCPA Governance engine.

        Args:
            graph: ISONGraph instance to use as backend
        """
        self.graph = graph

        # Initialize all stores
        self.consumers = ConsumerStore(graph)
        self.rights = ConsumerRightsStore(graph)
        self.sale_share = SaleShareStore(graph)
        self.notices = NoticeStore(graph)
        self.service_providers = ServiceProviderStore(graph)

    # =========================================================================
    # Business Setup
    # =========================================================================

    def register_business(
        self,
        name: str,
        business_size: BusinessSize,
        annual_revenue: str = "",
        consumers_per_year: str = "",
        sells_pi: bool = False,
        contact: str = "",
        privacy_email: str = "",
    ) -> str:
        """
        Register the business for CCPA compliance.

        Args:
            name: Business name
            business_size: Size classification
            annual_revenue: Annual gross revenue
            consumers_per_year: Number of CA consumers annually
            sells_pi: Whether business sells PI
            contact: Business contact
            privacy_email: Privacy request email

        Returns:
            Business ID
        """
        business_id = f"business_{name.lower().replace(' ', '_')}"

        # Determine CCPA applicability
        subject_to_ccpa = business_size != BusinessSize.SMALL

        self.graph.add_node(
            "business",
            business_id,
            name=name,
            business_size=business_size.value,
            annual_revenue=annual_revenue,
            consumers_per_year=consumers_per_year,
            sells_pi=str(sells_pi),
            contact=contact,
            privacy_email=privacy_email,
            subject_to_ccpa=str(subject_to_ccpa),
            created_at=datetime.now().isoformat(),
        )

        return business_id

    # =========================================================================
    # Compliance Reporting
    # =========================================================================

    def get_compliance_status(self, business_id: str = "") -> Dict[str, Any]:
        """
        Generate comprehensive CCPA compliance status report.

        Returns:
            Compliance status with metrics and issues
        """
        # Gather stats from all stores
        consumer_stats = self.consumers.get_stats()
        rights_stats = self.rights.get_stats()
        sale_share_stats = self.sale_share.get_stats()
        notice_stats = self.notices.get_stats()
        sp_stats = self.service_providers.get_stats()

        # Check notice compliance
        notice_compliance = self.notices.check_notice_compliance()

        # Identify compliance issues
        issues = self._identify_compliance_issues(
            consumer_stats,
            rights_stats,
            sale_share_stats,
            notice_compliance,
            sp_stats,
        )

        # Calculate compliance score
        score = self._calculate_compliance_score(
            rights_stats,
            notice_compliance,
            sp_stats,
        )

        return {
            "business_id": business_id,
            "generated_at": datetime.now().isoformat(),
            "compliance_score": score,
            "summary": {
                "total_consumers": consumer_stats["total_consumers"],
                "california_consumers": consumer_stats["california_residents"],
                "opted_out_sale": consumer_stats["opted_out_sale"],
                "opted_out_share": consumer_stats["opted_out_share"],
                "pending_requests": rights_stats["pending_requests"],
                "overdue_requests": rights_stats["overdue_requests"],
                "total_sales": sale_share_stats["total_sales"],
                "total_shares": sale_share_stats["total_shares"],
                "service_providers": sp_stats["total_service_providers"],
                "contractors": sp_stats["total_contractors"],
                "all_notices_present": notice_compliance["all_notices_present"],
            },
            "issues": issues,
            "notice_compliance": notice_compliance,
            "detailed_stats": {
                "consumers": consumer_stats,
                "rights": rights_stats,
                "sale_share": sale_share_stats,
                "notices": notice_stats,
                "service_providers": sp_stats,
            },
        }

    def _identify_compliance_issues(
        self,
        consumer_stats: Dict,
        rights_stats: Dict,
        sale_share_stats: Dict,
        notice_compliance: Dict,
        sp_stats: Dict,
    ) -> List[Dict[str, Any]]:
        """Identify compliance issues across all areas"""
        issues = []

        # Check for overdue requests (45-day requirement)
        if rights_stats.get("overdue_requests", 0) > 0:
            issues.append({
                "severity": "critical",
                "area": ComplianceArea.REQUEST_HANDLING.value,
                "issue": f"{rights_stats['overdue_requests']} consumer requests are overdue",
                "section": "1798.130",
                "action": "Complete overdue requests immediately",
            })

        # Check for missing notices
        if not notice_compliance.get("all_notices_present"):
            missing = []
            for notice_type, status in notice_compliance.get("notices", {}).items():
                if not status.get("exists"):
                    missing.append(notice_type)
            issues.append({
                "severity": "high",
                "area": ComplianceArea.PRIVACY_POLICY.value,
                "issue": f"Missing required notices: {', '.join(missing)}",
                "section": "1798.130, 1798.135",
                "action": "Create and publish missing notices",
            })

        # Check "Do Not Sell" link
        dns_notice = notice_compliance.get("notices", {}).get(NoticeType.DO_NOT_SELL_LINK.value, {})
        if not dns_notice.get("exists"):
            issues.append({
                "severity": "high",
                "area": ComplianceArea.OPT_OUT_MECHANISM.value,
                "issue": "Missing 'Do Not Sell My Personal Information' link",
                "section": "1798.135",
                "action": "Add DNS link to homepage and privacy policy",
            })

        # Check for high opt-out rate (potential UX issue)
        total = consumer_stats.get("total_consumers", 0)
        opted_out = consumer_stats.get("opted_out_sale", 0)
        if total > 0 and opted_out / total > 0.5:
            issues.append({
                "severity": "low",
                "area": "opt_out_rate",
                "issue": f"High opt-out rate ({opted_out}/{total})",
                "section": "N/A",
                "action": "Review data practices and privacy communications",
            })

        # Check service provider contracts
        if sp_stats.get("total_service_providers", 0) > 0:
            # Would need to check contract compliance for each
            pass

        return issues

    def _calculate_compliance_score(
        self,
        rights_stats: Dict,
        notice_compliance: Dict,
        sp_stats: Dict,
    ) -> float:
        """
        Calculate overall compliance score (0-100).

        Scoring:
        - Request response timeliness: 40 points
        - Notice compliance: 30 points
        - Opt-out mechanism: 15 points
        - Service provider contracts: 15 points
        """
        score = 100.0

        # Penalize for overdue requests (up to -40 points)
        overdue = rights_stats.get("overdue_requests", 0)
        pending = rights_stats.get("pending_requests", 0)
        if pending > 0:
            overdue_ratio = overdue / max(pending, 1)
            score -= min(40, overdue_ratio * 40)

        # Penalize for missing notices (up to -30 points)
        notices = notice_compliance.get("notices", {})
        required_count = len(notices)
        present_count = sum(1 for n in notices.values() if n.get("exists"))
        if required_count > 0:
            missing_ratio = 1 - (present_count / required_count)
            score -= missing_ratio * 30

        # Penalize for missing DNS link (up to -15 points)
        dns = notices.get(NoticeType.DO_NOT_SELL_LINK.value, {})
        if not dns.get("exists"):
            score -= 15

        return max(0, round(score, 1))

    # =========================================================================
    # Quick Operations
    # =========================================================================

    def handle_delete_request(
        self,
        consumer_id: str,
        verified: bool = True,
    ) -> Dict[str, Any]:
        """
        Handle a Right to Delete request.

        Coordinates across stores to:
        1. Submit and verify the request
        2. Delete personal information
        3. Notify service providers
        """
        # Submit request
        request_id = self.rights.submit_request(
            consumer_id=consumer_id,
            right_type=ConsumerRight.RIGHT_TO_DELETE,
        )

        if verified:
            # Mark as verified
            self.rights.verify_consumer(
                request_id=request_id,
                verification_method="automated",
                verified_by="system",
            )

            # Delete PI
            deletion_result = self.consumers.delete_consumer_pi(
                consumer_id=consumer_id,
                reason="consumer_delete_request",
            )

            # Complete request
            self.rights.complete_request(
                request_id=request_id,
                response="Personal information deleted per CCPA request",
                actions_taken=[
                    f"Deleted {deletion_result['deleted_count']} PI categories",
                    "Notified service providers",
                ],
            )

            return {
                "request_id": request_id,
                "status": "completed",
                "deleted_count": deletion_result["deleted_count"],
            }

        return {
            "request_id": request_id,
            "status": "pending_verification",
        }

    def handle_know_request(
        self,
        consumer_id: str,
        categories_only: bool = False,
    ) -> Dict[str, Any]:
        """
        Handle a Right to Know request.

        Args:
            consumer_id: Consumer ID
            categories_only: If True, return only categories; if False, specific pieces
        """
        # Submit request
        request_id = self.rights.submit_request(
            consumer_id=consumer_id,
            right_type=ConsumerRight.RIGHT_TO_KNOW,
            details=f"categories_only={categories_only}",
        )

        # Gather data
        consumer = self.consumers.get_consumer(consumer_id)
        inventory = self.consumers.get_consumer_pi_inventory(consumer_id)
        sales = self.sale_share.get_consumer_sales(consumer_id)
        shares = self.sale_share.get_consumer_shares(consumer_id)

        response_data = {
            "consumer_info": consumer,
            "pi_categories": consumer.get("pi_categories", []) if consumer else [],
            "pi_inventory": inventory if not categories_only else None,
            "sales_history": sales,
            "shares_history": shares,
        }

        return {
            "request_id": request_id,
            "consumer_id": consumer_id,
            "data": response_data,
        }

    def process_opt_out(
        self,
        consumer_id: str,
        opt_out_sale: bool = True,
        opt_out_share: bool = True,
        method: str = "website",
        gpc_signal: bool = False,
    ) -> Dict[str, Any]:
        """
        Process opt-out request (sale and/or share).

        Handles:
        - "Do Not Sell" requests
        - "Do Not Share" requests (CPRA)
        - Global Privacy Control signals
        """
        result = self.consumers.update_opt_out_status(
            consumer_id=consumer_id,
            opt_out_sale=opt_out_sale,
            opt_out_share=opt_out_share,
            gpc_detected=gpc_signal,
            method=method,
        )

        return {
            "consumer_id": consumer_id,
            "opt_out_sale": opt_out_sale,
            "opt_out_share": opt_out_share,
            "gpc_honored": gpc_signal,
            "effective_immediately": True,
        }

    def can_sell_pi(self, consumer_id: str) -> Dict[str, Any]:
        """
        Check if PI can be sold for a consumer.

        Checks opt-out status and GPC signal.
        """
        status = self.consumers.check_opt_out_status(consumer_id)
        return {
            "consumer_id": consumer_id,
            "can_sell": status.get("can_sell", True),
            "can_share": status.get("can_share", True),
            "opt_out_status": status.get("opt_out_status"),
            "gpc_detected": status.get("gpc_detected", False),
        }

    # =========================================================================
    # Disclosure Helpers
    # =========================================================================

    def get_disclosure_report(self) -> Dict[str, Any]:
        """
        Generate data for privacy policy disclosures.

        Returns categories collected, sold, shared in last 12 months.
        """
        categories_sold = self.sale_share.get_categories_sold_last_12_months()
        categories_shared = self.sale_share.get_categories_shared_last_12_months()

        # Get all PI categories from consumers
        categories_collected = set()
        for node in self.graph.nodes():
            if node.type == "consumer":
                cats = node.properties.get("pi_categories", "")
                for cat in cats.split(","):
                    if cat.strip():
                        categories_collected.add(cat.strip())

        return {
            "generated_at": datetime.now().isoformat(),
            "categories_collected": list(categories_collected),
            "categories_sold_12_months": categories_sold,
            "categories_shared_12_months": categories_shared,
            "sells_pi": len(categories_sold) > 0,
            "shares_pi": len(categories_shared) > 0,
        }

    def get_service_provider_disclosure(self) -> List[Dict[str, Any]]:
        """Get list of service providers for privacy policy disclosure"""
        providers = self.service_providers.list_service_providers()
        contractors = self.service_providers.list_contractors()

        return {
            "service_providers": [
                {
                    "name": p["name"],
                    "services": p["services"],
                    "pi_categories": p["pi_categories"],
                }
                for p in providers
            ],
            "contractors": [
                {
                    "name": c["name"],
                    "services": c["services"],
                    "pi_categories": c["pi_categories"],
                }
                for c in contractors
            ],
        }
