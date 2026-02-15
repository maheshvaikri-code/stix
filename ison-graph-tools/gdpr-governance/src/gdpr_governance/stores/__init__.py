"""
GDPR Governance Stores
======================

Specialized stores for GDPR compliance management.
"""

from .base import BaseGDPRStore
from .data_subject import DataSubjectStore
from .processing import ProcessingActivityStore
from .consent import ConsentStore
from .rights import DataSubjectRightsStore
from .breach import DataBreachStore
from .dpia import DPIAStore
from .transfer import InternationalTransferStore

__all__ = [
    "BaseGDPRStore",
    "DataSubjectStore",
    "ProcessingActivityStore",
    "ConsentStore",
    "DataSubjectRightsStore",
    "DataBreachStore",
    "DPIAStore",
    "InternationalTransferStore",
]
