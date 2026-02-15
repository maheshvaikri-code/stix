#!/usr/bin/env python3
"""
CCPA Governance Demo
====================

Demonstrates comprehensive CCPA/CPRA compliance management using ISONGraph.
"""

import sys
sys.path.insert(0, "../src")

from ison_graph import ISONGraph
from ccpa_governance import (
    CCPAGovernance,
    PersonalInfoCategory,
    ConsumerRight,
    NoticeType,
    DisclosureCategory,
    BusinessRole,
    BusinessSize,
    OptOutMethod,
)


def main():
    print("=" * 60)
    print("CCPA/CPRA Governance Demo")
    print("=" * 60)

    # Initialize
    graph = ISONGraph()
    ccpa = CCPAGovernance(graph)

    # =========================================================================
    # 1. Business Setup
    # =========================================================================
    print("\n1. BUSINESS SETUP")
    print("-" * 40)

    business_id = ccpa.register_business(
        name="Acme Commerce Inc",
        business_size=BusinessSize.LARGE,
        annual_revenue="$50M",
        consumers_per_year="500,000",
        sells_pi=True,
        privacy_email="privacy@acme.com",
    )
    print(f"Registered business: {business_id}")

    # =========================================================================
    # 2. Privacy Notices (Section 1798.130, 1798.135)
    # =========================================================================
    print("\n2. PRIVACY NOTICES")
    print("-" * 40)

    # Create privacy policy
    policy_id = ccpa.notices.create_notice(
        notice_type=NoticeType.PRIVACY_POLICY,
        version="2.0",
        effective_date="2024-01-01",
        content_summary="Comprehensive CCPA-compliant privacy policy",
        url="https://acme.com/privacy",
        categories_disclosed=[
            DisclosureCategory.CATEGORIES_COLLECTED,
            DisclosureCategory.SOURCES,
            DisclosureCategory.BUSINESS_PURPOSE,
            DisclosureCategory.THIRD_PARTIES,
            DisclosureCategory.CATEGORIES_SOLD,
            DisclosureCategory.CATEGORIES_SHARED,
            DisclosureCategory.RETENTION_PERIODS,
        ],
    )
    print(f"Created privacy policy: {policy_id}")

    # Notice at Collection
    nac_id = ccpa.notices.create_notice(
        notice_type=NoticeType.NOTICE_AT_COLLECTION,
        version="1.0",
        effective_date="2024-01-01",
        content_summary="Notice provided at point of PI collection",
        url="https://acme.com/collection-notice",
    )
    print(f"Created notice at collection: {nac_id}")

    # "Do Not Sell" link
    dns_id = ccpa.notices.create_notice(
        notice_type=NoticeType.DO_NOT_SELL_LINK,
        version="1.0",
        effective_date="2024-01-01",
        content_summary="Do Not Sell My Personal Information",
        url="https://acme.com/do-not-sell",
    )
    print(f"Created DNS link: {dns_id}")

    # "Limit Sensitive PI" link (CPRA)
    limit_id = ccpa.notices.create_notice(
        notice_type=NoticeType.LIMIT_SPI_LINK,
        version="1.0",
        effective_date="2024-01-01",
        content_summary="Limit Use of My Sensitive Personal Information",
        url="https://acme.com/limit-sensitive-pi",
    )
    print(f"Created Limit SPI link: {limit_id}")

    # Check notice compliance
    compliance = ccpa.notices.check_notice_compliance()
    print(f"All notices present: {compliance['all_notices_present']}")

    # =========================================================================
    # 3. Consumer Registration
    # =========================================================================
    print("\n3. CONSUMER REGISTRATION")
    print("-" * 40)

    # Register California consumers
    consumer1 = ccpa.consumers.register_consumer(
        consumer_id="user001",
        email="alice@example.com",
        is_california_resident=True,
    )
    print(f"Registered consumer: {consumer1}")

    consumer2 = ccpa.consumers.register_consumer(
        consumer_id="user002",
        email="bob@example.com",
        is_california_resident=True,
        is_minor=True,
        minor_category=ccpa.schema.MinorCategory.AGE_13_TO_15 if hasattr(ccpa, 'schema') else None,
    )
    print(f"Registered minor consumer: {consumer2}")

    # Add personal information
    ccpa.consumers.add_personal_info(
        consumer_id="user001",
        category=PersonalInfoCategory.IDENTIFIERS,
        source="account_registration",
        purpose="service_delivery",
    )
    ccpa.consumers.add_personal_info(
        consumer_id="user001",
        category=PersonalInfoCategory.COMMERCIAL_INFO,
        source="purchase_history",
        purpose="order_fulfillment",
    )
    ccpa.consumers.add_personal_info(
        consumer_id="user001",
        category=PersonalInfoCategory.INTERNET_ACTIVITY,
        source="website_cookies",
        purpose="analytics",
    )
    print(f"  Added PI categories for user001")

    # Add sensitive PI
    ccpa.consumers.add_personal_info(
        consumer_id="user001",
        category=PersonalInfoCategory.PRECISE_GEOLOCATION,
        source="mobile_app",
        purpose="location_services",
        is_sensitive=True,
    )
    print(f"  Added sensitive PI (precise geolocation)")

    # =========================================================================
    # 4. Service Providers (Section 1798.140)
    # =========================================================================
    print("\n4. SERVICE PROVIDERS")
    print("-" * 40)

    sp1 = ccpa.service_providers.register_service_provider(
        provider_id="analytics_co",
        name="Analytics Corp",
        services="Website analytics and reporting",
        pi_categories=[
            PersonalInfoCategory.INTERNET_ACTIVITY,
            PersonalInfoCategory.IDENTIFIERS,
        ],
        contract_date="2024-01-01",
        audit_rights=True,
    )
    print(f"Registered service provider: {sp1}")

    sp2 = ccpa.service_providers.register_contractor(
        contractor_id="email_vendor",
        name="Email Marketing Inc",
        services="Email delivery and tracking",
        pi_categories=[
            PersonalInfoCategory.IDENTIFIERS,
            PersonalInfoCategory.CUSTOMER_RECORDS,
        ],
        contract_date="2024-01-01",
        business_purpose="marketing_communications",
        audit_rights=True,
    )
    print(f"Registered contractor: {sp2}")

    # =========================================================================
    # 5. Sale and Sharing (Section 1798.120)
    # =========================================================================
    print("\n5. SALE AND SHARING")
    print("-" * 40)

    # Register third party recipient
    ccpa.sale_share.register_recipient(
        recipient_id="ad_network",
        name="AdTech Network",
        role=BusinessRole.THIRD_PARTY,
    )

    # Attempt to sell PI (will check opt-out)
    sale_result = ccpa.sale_share.record_sale(
        consumer_id="user001",
        recipient_id="ad_network",
        pi_categories=[
            PersonalInfoCategory.IDENTIFIERS,
            PersonalInfoCategory.INTERNET_ACTIVITY,
        ],
        purpose="targeted_advertising",
        consideration="advertising_revenue",
    )
    if "error" not in sale_result:
        print(f"Recorded PI sale: {sale_result['sale_id']}")
    else:
        print(f"Sale blocked: {sale_result['error']}")

    # Record sharing for cross-context behavioral advertising
    share_result = ccpa.sale_share.record_share(
        consumer_id="user001",
        recipient_id="ad_network",
        pi_categories=[PersonalInfoCategory.INTERNET_ACTIVITY],
        advertising_purpose="cross_context_behavioral_ads",
    )
    if "error" not in share_result:
        print(f"Recorded PI share: {share_result['share_id']}")

    # =========================================================================
    # 6. Opt-Out Handling (Section 1798.120)
    # =========================================================================
    print("\n6. OPT-OUT HANDLING")
    print("-" * 40)

    # Process opt-out request
    opt_out_result = ccpa.process_opt_out(
        consumer_id="user001",
        opt_out_sale=True,
        opt_out_share=True,
        method="website",
    )
    print(f"Processed opt-out: sale={opt_out_result['opt_out_sale']}, share={opt_out_result['opt_out_share']}")

    # Check if we can sell now
    can_sell = ccpa.can_sell_pi("user001")
    print(f"Can sell PI: {can_sell['can_sell']}")
    print(f"Can share PI: {can_sell['can_share']}")

    # Attempt sale after opt-out (should be blocked)
    blocked_sale = ccpa.sale_share.record_sale(
        consumer_id="user001",
        recipient_id="ad_network",
        pi_categories=[PersonalInfoCategory.IDENTIFIERS],
        purpose="targeting",
    )
    print(f"Sale after opt-out: {'BLOCKED' if 'error' in blocked_sale else 'allowed'}")

    # =========================================================================
    # 7. Consumer Requests (Section 1798.100-1798.105)
    # =========================================================================
    print("\n7. CONSUMER REQUESTS")
    print("-" * 40)

    # Right to Know request
    know_result = ccpa.handle_know_request(
        consumer_id="user001",
        categories_only=False,
    )
    print(f"Right to Know request: {know_result['request_id']}")
    print(f"  PI categories: {know_result['data']['pi_categories']}")

    # Right to Delete request
    delete_result = ccpa.handle_delete_request(
        consumer_id="user001",
        verified=True,
    )
    print(f"Right to Delete request: {delete_result['request_id']}")
    print(f"  Deleted: {delete_result['deleted_count']} categories")

    # Submit correction request (CPRA)
    correction_id = ccpa.rights.submit_request(
        consumer_id="user002",
        right_type=ConsumerRight.RIGHT_TO_CORRECT,
        details="Update email address to newemail@example.com",
    )
    print(f"Right to Correct request: {correction_id}")

    # Verify and complete
    ccpa.rights.verify_consumer(
        request_id=correction_id,
        verification_method="email_confirmation",
        verified_by="privacy_team",
    )
    ccpa.rights.complete_request(
        request_id=correction_id,
        response="Email address updated as requested",
        actions_taken=["Updated email in customer database"],
    )
    print(f"  Correction request completed")

    # =========================================================================
    # 8. Disclosure Report
    # =========================================================================
    print("\n8. DISCLOSURE REPORT")
    print("-" * 40)

    disclosure = ccpa.get_disclosure_report()
    print(f"Categories collected: {disclosure['categories_collected']}")
    print(f"Categories sold (12mo): {list(disclosure['categories_sold_12_months'].keys())}")
    print(f"Categories shared (12mo): {list(disclosure['categories_shared_12_months'].keys())}")
    print(f"Sells PI: {disclosure['sells_pi']}")
    print(f"Shares PI: {disclosure['shares_pi']}")

    # =========================================================================
    # 9. Compliance Status
    # =========================================================================
    print("\n9. COMPLIANCE STATUS")
    print("-" * 40)

    status = ccpa.get_compliance_status(business_id)

    print(f"Compliance Score: {status['compliance_score']}/100")
    print(f"\nSummary:")
    print(f"  Total Consumers: {status['summary']['total_consumers']}")
    print(f"  Opted Out Sale: {status['summary']['opted_out_sale']}")
    print(f"  Opted Out Share: {status['summary']['opted_out_share']}")
    print(f"  Pending Requests: {status['summary']['pending_requests']}")
    print(f"  Overdue Requests: {status['summary']['overdue_requests']}")
    print(f"  Service Providers: {status['summary']['service_providers']}")
    print(f"  All Notices Present: {status['summary']['all_notices_present']}")

    if status['issues']:
        print(f"\nCompliance Issues ({len(status['issues'])}):")
        for issue in status['issues']:
            print(f"  [{issue['severity'].upper()}] {issue['issue']}")
            print(f"    Section: {issue['section']}")
            print(f"    Action: {issue['action']}")
    else:
        print("\nNo compliance issues found!")

    # =========================================================================
    # Save graph
    # =========================================================================
    print("\n" + "=" * 60)
    graph.save("ccpa_compliance_demo.json")
    print("Graph saved to ccpa_compliance_demo.json")
    print("=" * 60)


if __name__ == "__main__":
    main()
