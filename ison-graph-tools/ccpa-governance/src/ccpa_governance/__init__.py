"""
CCPA Governance for ISONGraph
=============================

Comprehensive CCPA/CPRA compliance management using ISONGraph.

This package provides tools for managing:
- Consumer registration and PI inventory
- Consumer Rights (Know, Delete, Correct, Opt-Out, Limit SPI)
- Sale and Sharing of Personal Information
- "Do Not Sell" and "Do Not Share" opt-outs
- Global Privacy Control (GPC) signal handling
- Service Provider and Contractor contracts
- Privacy Policy and Notice compliance
- Compliance reporting and metrics

Usage:
    from ison_graph import ISONGraph
    from ccpa_governance import CCPAGovernance

    graph = ISONGraph()
    ccpa = CCPAGovernance(graph)

    # Register a consumer
    consumer_id = ccpa.consumers.register_consumer(
        consumer_id="user123",
        email="user@example.com",
        is_california_resident=True,
    )

    # Process opt-out
    ccpa.process_opt_out(
        consumer_id="user123",
        opt_out_sale=True,
        opt_out_share=True,
    )

    # Handle consumer request
    request_id = ccpa.rights.submit_request(
        consumer_id="user123",
        right_type=ConsumerRight.RIGHT_TO_KNOW,
    )

    # Get compliance status
    status = ccpa.get_compliance_status()
"""

from .schema import (
    # Business roles
    BusinessRole,
    BusinessSize,
    # Personal Information categories
    PersonalInfoCategory,
    SensitivePersonalInfo,
    # Consumer Rights
    ConsumerRight,
    RequestStatus,
    DenialReason,
    # Sale and Sharing
    SaleShareType,
    OptOutStatus,
    OptOutMethod,
    # Business Purposes
    BusinessPurpose,
    LegalException,
    # Notices
    NoticeType,
    DisclosureCategory,
    # Minors
    MinorCategory,
    # Financial Incentives
    IncentiveType,
    IncentiveStatus,
    # Violations
    ViolationType,
    ComplianceArea,
    # Data classes
    Consumer,
    ConsumerRequest,
    SaleShareRecord,
    ServiceProviderContract,
    FinancialIncentive,
    NoticeRecord,
    ComplianceStatus,
)

from .stores import (
    BaseCCPAStore,
    ConsumerStore,
    ConsumerRightsStore,
    SaleShareStore,
    NoticeStore,
    ServiceProviderStore,
)

from .engine import CCPAGovernance

__version__ = "0.1.0"

__all__ = [
    # Main engine
    "CCPAGovernance",
    # Stores
    "BaseCCPAStore",
    "ConsumerStore",
    "ConsumerRightsStore",
    "SaleShareStore",
    "NoticeStore",
    "ServiceProviderStore",
    # Enums - Business
    "BusinessRole",
    "BusinessSize",
    # Enums - Personal Information
    "PersonalInfoCategory",
    "SensitivePersonalInfo",
    # Enums - Rights
    "ConsumerRight",
    "RequestStatus",
    "DenialReason",
    # Enums - Sale/Share
    "SaleShareType",
    "OptOutStatus",
    "OptOutMethod",
    # Enums - Business Purpose
    "BusinessPurpose",
    "LegalException",
    # Enums - Notices
    "NoticeType",
    "DisclosureCategory",
    # Enums - Other
    "MinorCategory",
    "IncentiveType",
    "IncentiveStatus",
    "ViolationType",
    "ComplianceArea",
    # Data classes
    "Consumer",
    "ConsumerRequest",
    "SaleShareRecord",
    "ServiceProviderContract",
    "FinancialIncentive",
    "NoticeRecord",
    "ComplianceStatus",
]
