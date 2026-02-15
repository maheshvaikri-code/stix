"""
CCPA Governance Stores
======================

Specialized stores for CCPA compliance management.
"""

from .base import BaseCCPAStore
from .consumer import ConsumerStore
from .rights import ConsumerRightsStore
from .sale_share import SaleShareStore
from .notice import NoticeStore
from .service_provider import ServiceProviderStore

__all__ = [
    "BaseCCPAStore",
    "ConsumerStore",
    "ConsumerRightsStore",
    "SaleShareStore",
    "NoticeStore",
    "ServiceProviderStore",
]
