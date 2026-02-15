"""
Subject Unification Store
=========================

Unifies GDPR data subjects and CCPA consumers into a single identity.
"""

from typing import Any, Dict, List, Optional

from .base import BaseUnifiedStore
from ..schema import (
    GovernanceDomain,
    RegulationJurisdiction,
)


class SubjectUnificationStore(BaseUnifiedStore):
    """
    Store for unifying data subjects across GDPR and CCPA.

    Provides:
    - Unified subject identity management
    - Cross-regulation rights tracking
    - Consent/opt-out status aggregation
    - PII location mapping across systems
    """

    def __init__(self, graph):
        super().__init__(graph, "subject_unification")

    # =========================================================================
    # Unified Subject Management
    # =========================================================================

    def create_unified_subject(
        self,
        subject_id: str,
        gdpr_data_subject_id: Optional[str] = None,
        ccpa_consumer_id: Optional[str] = None,
        jurisdiction: RegulationJurisdiction = RegulationJurisdiction.GLOBAL,
        email: str = "",
        name: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Create a unified subject that spans GDPR and CCPA."""
        self._add_node("unified_subject", subject_id, {
            "gdpr_data_subject_id": gdpr_data_subject_id,
            "ccpa_consumer_id": ccpa_consumer_id,
            "jurisdiction": jurisdiction.value if isinstance(jurisdiction, RegulationJurisdiction) else jurisdiction,
            "email": email,
            "name": name,
            "metadata": metadata or {},
            "consent_status": {},
            "opt_out_status": {},
            "active_requests": [],
            "status": "active",
        })

        # Link to GDPR subject if exists
        if gdpr_data_subject_id:
            self._add_edge(
                "unified_subject", subject_id,
                "SAME_SUBJECT_AS",
                "data_subject", gdpr_data_subject_id,
                {"regulation": "gdpr"}
            )

        # Link to CCPA consumer if exists
        if ccpa_consumer_id:
            self._add_edge(
                "unified_subject", subject_id,
                "SAME_SUBJECT_AS",
                "consumer", ccpa_consumer_id,
                {"regulation": "ccpa"}
            )

        return subject_id

    def link_gdpr_subject(
        self,
        unified_subject_id: str,
        gdpr_data_subject_id: str,
    ) -> Dict[str, Any]:
        """Link a GDPR data subject to a unified subject."""
        subject = self._get_node("unified_subject", unified_subject_id)
        if not subject:
            return {"error": "Unified subject not found"}

        self._update_node("unified_subject", unified_subject_id, {
            "gdpr_data_subject_id": gdpr_data_subject_id,
        })

        self._add_edge(
            "unified_subject", unified_subject_id,
            "SAME_SUBJECT_AS",
            "data_subject", gdpr_data_subject_id,
            {"regulation": "gdpr"}
        )

        return {"linked": True, "gdpr_data_subject_id": gdpr_data_subject_id}

    def link_ccpa_consumer(
        self,
        unified_subject_id: str,
        ccpa_consumer_id: str,
    ) -> Dict[str, Any]:
        """Link a CCPA consumer to a unified subject."""
        subject = self._get_node("unified_subject", unified_subject_id)
        if not subject:
            return {"error": "Unified subject not found"}

        self._update_node("unified_subject", unified_subject_id, {
            "ccpa_consumer_id": ccpa_consumer_id,
        })

        self._add_edge(
            "unified_subject", unified_subject_id,
            "SAME_SUBJECT_AS",
            "consumer", ccpa_consumer_id,
            {"regulation": "ccpa"}
        )

        return {"linked": True, "ccpa_consumer_id": ccpa_consumer_id}

    def get_unified_subject(self, subject_id: str) -> Optional[Dict[str, Any]]:
        """Get a unified subject by ID."""
        return self._get_node("unified_subject", subject_id)

    def find_by_gdpr_id(self, gdpr_data_subject_id: str) -> Optional[Dict[str, Any]]:
        """Find unified subject by GDPR data subject ID."""
        subjects = self._find_nodes("unified_subject", gdpr_data_subject_id=gdpr_data_subject_id)
        return subjects[0] if subjects else None

    def find_by_ccpa_id(self, ccpa_consumer_id: str) -> Optional[Dict[str, Any]]:
        """Find unified subject by CCPA consumer ID."""
        subjects = self._find_nodes("unified_subject", ccpa_consumer_id=ccpa_consumer_id)
        return subjects[0] if subjects else None

    def find_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find unified subject by email."""
        subjects = self._find_nodes("unified_subject", email=email)
        return subjects[0] if subjects else None

    # =========================================================================
    # Consent and Opt-Out Aggregation
    # =========================================================================

    def update_consent_status(
        self,
        subject_id: str,
        consent_type: str,
        consented: bool,
        source_regulation: str,
        timestamp: str = "",
    ) -> Dict[str, Any]:
        """Update consent status for a unified subject."""
        subject = self._get_node("unified_subject", subject_id)
        if not subject:
            return {"error": "Subject not found"}

        consent_status = subject.get("consent_status", {})
        consent_status[consent_type] = {
            "consented": consented,
            "source_regulation": source_regulation,
            "updated_at": timestamp or self._now(),
        }

        self._update_node("unified_subject", subject_id, {
            "consent_status": consent_status,
        })

        return {"updated": True, "consent_type": consent_type, "consented": consented}

    def update_opt_out_status(
        self,
        subject_id: str,
        opt_out_type: str,
        opted_out: bool,
        source_regulation: str,
        method: str = "",
    ) -> Dict[str, Any]:
        """Update opt-out status for a unified subject."""
        subject = self._get_node("unified_subject", subject_id)
        if not subject:
            return {"error": "Subject not found"}

        opt_out_status = subject.get("opt_out_status", {})
        opt_out_status[opt_out_type] = {
            "opted_out": opted_out,
            "source_regulation": source_regulation,
            "method": method,
            "updated_at": self._now(),
        }

        self._update_node("unified_subject", subject_id, {
            "opt_out_status": opt_out_status,
        })

        return {"updated": True, "opt_out_type": opt_out_type, "opted_out": opted_out}

    def get_cross_regulation_status(self, subject_id: str) -> Dict[str, Any]:
        """Get aggregated consent/opt-out status across regulations."""
        subject = self._get_node("unified_subject", subject_id)
        if not subject:
            return {"error": "Subject not found"}

        consent_status = subject.get("consent_status", {})
        opt_out_status = subject.get("opt_out_status", {})

        # Analyze status
        gdpr_consents = {k: v for k, v in consent_status.items() if v.get("source_regulation") == "gdpr"}
        ccpa_consents = {k: v for k, v in consent_status.items() if v.get("source_regulation") == "ccpa"}

        gdpr_opt_outs = {k: v for k, v in opt_out_status.items() if v.get("source_regulation") == "gdpr"}
        ccpa_opt_outs = {k: v for k, v in opt_out_status.items() if v.get("source_regulation") == "ccpa"}

        return {
            "subject_id": subject_id,
            "gdpr": {
                "data_subject_id": subject.get("gdpr_data_subject_id"),
                "consents": gdpr_consents,
                "opt_outs": gdpr_opt_outs,
            },
            "ccpa": {
                "consumer_id": subject.get("ccpa_consumer_id"),
                "consents": ccpa_consents,
                "opt_outs": ccpa_opt_outs,
            },
            "all_consents": consent_status,
            "all_opt_outs": opt_out_status,
        }

    # =========================================================================
    # Rights Request Tracking
    # =========================================================================

    def record_rights_request(
        self,
        subject_id: str,
        request_type: str,
        source_regulation: str,
        request_id: str,
        deadline: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Record a rights request (GDPR or CCPA) for unified tracking."""
        subject = self._get_node("unified_subject", subject_id)
        if not subject:
            return {"error": "Subject not found"}

        active_requests = subject.get("active_requests", [])
        active_requests.append({
            "request_id": request_id,
            "request_type": request_type,
            "source_regulation": source_regulation,
            "deadline": deadline,
            "status": "pending",
            "created_at": self._now(),
            "details": details or {},
        })

        self._update_node("unified_subject", subject_id, {
            "active_requests": active_requests,
        })

        # Create request node for detailed tracking
        self._add_node("unified_rights_request", request_id, {
            "subject_id": subject_id,
            "request_type": request_type,
            "source_regulation": source_regulation,
            "deadline": deadline,
            "status": "pending",
            "details": details or {},
        })

        self._add_edge(
            "unified_subject", subject_id,
            "HAS_REQUEST",
            "unified_rights_request", request_id,
            {}
        )

        return {
            "recorded": True,
            "request_id": request_id,
            "deadline": deadline,
        }

    def complete_rights_request(
        self,
        subject_id: str,
        request_id: str,
        resolution: str,
        completed_by: str,
    ) -> Dict[str, Any]:
        """Mark a rights request as completed."""
        subject = self._get_node("unified_subject", subject_id)
        if not subject:
            return {"error": "Subject not found"}

        active_requests = subject.get("active_requests", [])
        updated_requests = []

        for req in active_requests:
            if req.get("request_id") == request_id:
                req["status"] = "completed"
                req["resolution"] = resolution
                req["completed_by"] = completed_by
                req["completed_at"] = self._now()
            updated_requests.append(req)

        self._update_node("unified_subject", subject_id, {
            "active_requests": updated_requests,
        })

        # Update request node
        self._update_node("unified_rights_request", request_id, {
            "status": "completed",
            "resolution": resolution,
            "completed_by": completed_by,
            "completed_at": self._now(),
        })

        return {"completed": True, "request_id": request_id}

    def get_pending_requests(self, subject_id: str) -> List[Dict[str, Any]]:
        """Get all pending rights requests for a subject."""
        subject = self._get_node("unified_subject", subject_id)
        if not subject:
            return []

        active_requests = subject.get("active_requests", [])
        return [r for r in active_requests if r.get("status") == "pending"]

    # =========================================================================
    # PII Location Tracking
    # =========================================================================

    def register_pii_location(
        self,
        subject_id: str,
        source_id: str,
        field_location: str,
        pii_type: str,
        record_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Register where a subject's PII is stored."""
        subject = self._get_node("unified_subject", subject_id)
        if not subject:
            return {"error": "Subject not found"}

        location_id = self._generate_id("pii_loc")

        self._add_node("subject_pii_location", location_id, {
            "subject_id": subject_id,
            "source_id": source_id,
            "field_location": field_location,
            "pii_type": pii_type,
            "record_id": record_id,
            "status": "active",
        })

        self._add_edge(
            "unified_subject", subject_id,
            "HAS_PII_AT",
            "subject_pii_location", location_id,
            {}
        )

        return {
            "location_id": location_id,
            "source_id": source_id,
            "field_location": field_location,
        }

    def get_pii_locations(self, subject_id: str) -> List[Dict[str, Any]]:
        """Get all PII locations for a subject."""
        locations = self._find_nodes("subject_pii_location", subject_id=subject_id)
        return [loc for loc in locations if loc.get("status") == "active"]

    def get_pii_map_for_subject(self, subject_id: str) -> Dict[str, Any]:
        """Get a map of all PII for a subject organized by source."""
        locations = self.get_pii_locations(subject_id)

        pii_map = {}
        for loc in locations:
            source_id = loc.get("source_id")
            if source_id not in pii_map:
                pii_map[source_id] = []
            pii_map[source_id].append({
                "field_location": loc.get("field_location"),
                "pii_type": loc.get("pii_type"),
                "location_id": loc.get("id"),
            })

        return {
            "subject_id": subject_id,
            "sources_count": len(pii_map),
            "pii_map": pii_map,
            "total_locations": len(locations),
        }

    def mark_pii_deleted(
        self,
        subject_id: str,
        location_id: str,
        deleted_by: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Mark a PII location as deleted (for erasure requests)."""
        location = self._get_node("subject_pii_location", location_id)
        if not location:
            return {"error": "Location not found"}

        if location.get("subject_id") != subject_id:
            return {"error": "Location does not belong to subject"}

        self._update_node("subject_pii_location", location_id, {
            "status": "deleted",
            "deleted_by": deleted_by,
            "deleted_at": self._now(),
            "deletion_reason": reason,
        })

        return {"deleted": True, "location_id": location_id}

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get subject unification statistics."""
        subjects = self._find_nodes("unified_subject")
        locations = self._find_nodes("subject_pii_location")
        requests = self._find_nodes("unified_rights_request")

        # Count by jurisdiction
        jurisdiction_counts = {}
        for subj in subjects:
            jur = subj.get("jurisdiction", "unknown")
            jurisdiction_counts[jur] = jurisdiction_counts.get(jur, 0) + 1

        # Count linked subjects
        gdpr_linked = sum(1 for s in subjects if s.get("gdpr_data_subject_id"))
        ccpa_linked = sum(1 for s in subjects if s.get("ccpa_consumer_id"))
        both_linked = sum(1 for s in subjects if s.get("gdpr_data_subject_id") and s.get("ccpa_consumer_id"))

        # Count pending requests
        pending_requests = sum(1 for r in requests if r.get("status") == "pending")

        return {
            "total_unified_subjects": len(subjects),
            "gdpr_linked": gdpr_linked,
            "ccpa_linked": ccpa_linked,
            "both_regulations_linked": both_linked,
            "total_pii_locations": len(locations),
            "total_rights_requests": len(requests),
            "pending_requests": pending_requests,
            "by_jurisdiction": jurisdiction_counts,
        }
