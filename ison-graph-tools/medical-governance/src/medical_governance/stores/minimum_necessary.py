"""
Minimum Necessary Store
=======================

Implements HIPAA Minimum Necessary Standard (45 CFR 164.502(b)).
Manages use case profiles, field filtering, and justification tracking.
"""

from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING

from .base import BaseStore
from ..schema import AccessPurpose, UseCase, MinimumNecessaryProfile, FieldJustification

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class MinimumNecessaryStore(BaseStore):
    """Store for minimum necessary standard enforcement"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "minimum_necessary")

    # =========================================================================
    # Use Case Management
    # =========================================================================

    def add_use_case(
        self,
        name: str,
        purpose: AccessPurpose,
        requester_type: str,
        frequency: str = "medium",
        description: str = "",
        use_case_id: Optional[str] = None
    ) -> str:
        """Add a use case definition"""
        ucid = use_case_id or name
        props = {
            "name": name,
            "purpose": purpose.value,
            "requester_type": requester_type,  # ai_clinical, ai_billing, human, etc.
            "frequency": frequency,
            "active": True,
            "description": description or f"Use case: {name}"
        }
        return self._add_node("use_case", ucid, props)

    def get_use_case(self, use_case_id: str) -> Optional[Dict[str, Any]]:
        """Get use case by ID"""
        return self._get_node("use_case", use_case_id)

    def list_use_cases(
        self,
        purpose: Optional[AccessPurpose] = None,
        requester_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List use cases with optional filters"""
        use_cases = self._find_nodes("use_case", active=True)

        if purpose:
            use_cases = [uc for uc in use_cases if uc.get("purpose") == purpose.value]
        if requester_type:
            use_cases = [uc for uc in use_cases if uc.get("requester_type") == requester_type]

        return use_cases

    # =========================================================================
    # Minimum Necessary Profile Management
    # =========================================================================

    def add_profile(
        self,
        use_case_id: str,
        phi_required: List[str],
        phi_excluded: List[str],
        justification: str,
        profile_id: Optional[str] = None
    ) -> str:
        """Add a minimum necessary profile for a use case"""
        pid = profile_id or self._generate_id("mn")
        props = {
            "use_case_id": use_case_id,
            "phi_required": phi_required,
            "phi_excluded": phi_excluded,
            "justification": justification,
            "active": True,
            "description": f"MN profile for {use_case_id}"
        }
        self._add_node("mn_profile", pid, props)

        # Link profile to use case
        self._add_edge(
            "use_case", use_case_id,
            "HAS_MN_PROFILE",
            "mn_profile", pid,
            {}
        )

        return pid

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Get profile by ID"""
        return self._get_node("mn_profile", profile_id)

    def get_profile_for_use_case(self, use_case_id: str) -> Optional[Dict[str, Any]]:
        """Get minimum necessary profile for a use case"""
        profiles = self._find_nodes("mn_profile", use_case_id=use_case_id, active=True)
        return profiles[0] if profiles else None

    def update_profile(
        self,
        profile_id: str,
        phi_required: Optional[List[str]] = None,
        phi_excluded: Optional[List[str]] = None,
        justification: Optional[str] = None
    ):
        """Update a profile"""
        updates = {}
        if phi_required is not None:
            updates["phi_required"] = phi_required
        if phi_excluded is not None:
            updates["phi_excluded"] = phi_excluded
        if justification is not None:
            updates["justification"] = justification

        if updates:
            self._update_node("mn_profile", profile_id, updates)

    # =========================================================================
    # Field Justification
    # =========================================================================

    def add_field_justification(
        self,
        profile_id: str,
        field_name: str,
        justification: str,
        alternative_if_denied: str
    ) -> str:
        """Add justification for a field in a profile"""
        fid = self._generate_id("fj")
        props = {
            "profile_id": profile_id,
            "field_name": field_name,
            "justification": justification,
            "alternative_if_denied": alternative_if_denied,
            "description": f"Justification for {field_name}"
        }
        self._add_node("field_justification", fid, props)

        # Link to profile
        self._add_edge(
            "mn_profile", profile_id,
            "FIELD_JUSTIFIED",
            "field_justification", fid,
            {}
        )

        return fid

    def get_field_justifications(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get all field justifications for a profile"""
        return self._find_nodes("field_justification", profile_id=profile_id)

    # =========================================================================
    # Request Filtering
    # =========================================================================

    def filter_request(
        self,
        use_case_id: str,
        requested_fields: List[str]
    ) -> Dict[str, Any]:
        """Filter a request based on minimum necessary profile"""
        profile = self.get_profile_for_use_case(use_case_id)

        if not profile:
            # No profile - conservative approach: allow nothing
            return {
                "allowed_fields": [],
                "filtered_fields": requested_fields,
                "profile_id": None,
                "compliant": False,
                "reason": "no_profile_defined"
            }

        phi_required = set(profile.get("phi_required", []))
        phi_excluded = set(profile.get("phi_excluded", []))
        requested_set = set(requested_fields)

        # Determine allowed fields
        allowed = requested_set & phi_required
        filtered = requested_set - phi_required
        excess = requested_set & phi_excluded

        # Record the validation
        self._record_validation(
            profile["id"],
            use_case_id,
            list(requested_set),
            list(allowed),
            list(filtered),
            list(excess)
        )

        return {
            "allowed_fields": list(allowed),
            "filtered_fields": list(filtered),
            "excess_fields": list(excess),
            "profile_id": profile["id"],
            "compliant": len(excess) == 0,
            "reason": "filtered_per_profile" if filtered else "all_allowed"
        }

    def _record_validation(
        self,
        profile_id: str,
        use_case_id: str,
        requested: List[str],
        allowed: List[str],
        filtered: List[str],
        excess: List[str]
    ):
        """Record a minimum necessary validation event"""
        vid = self._generate_id("mnv")
        props = {
            "profile_id": profile_id,
            "use_case_id": use_case_id,
            "requested_fields": requested,
            "allowed_fields": allowed,
            "filtered_fields": filtered,
            "excess_fields": excess,
            "timestamp": self._now(),
            "compliant": len(excess) == 0,
            "description": f"MN validation for {use_case_id}"
        }
        self._add_node("mn_validation", vid, props)

    # =========================================================================
    # Exception Management
    # =========================================================================

    def add_exception(
        self,
        profile_id: str,
        exception_type: str,  # patient_request, treatment_emergency, etc.
        authorization: str,
        duration: str,
        fields_allowed: List[str],
        reason: str
    ) -> str:
        """Add an exception to minimum necessary profile"""
        eid = self._generate_id("mne")
        props = {
            "profile_id": profile_id,
            "exception_type": exception_type,
            "authorization": authorization,
            "duration": duration,
            "fields_allowed": fields_allowed,
            "reason": reason,
            "active": True,
            "granted_at": self._now(),
            "description": f"MN exception: {exception_type}"
        }
        self._add_node("mn_exception", eid, props)

        return eid

    def get_active_exceptions(self, profile_id: str) -> List[Dict[str, Any]]:
        """Get active exceptions for a profile"""
        return self._find_nodes("mn_exception", profile_id=profile_id, active=True)

    def revoke_exception(self, exception_id: str, revoked_by: str, reason: str):
        """Revoke an exception"""
        self._update_node("mn_exception", exception_id, {
            "active": False,
            "revoked_at": self._now(),
            "revoked_by": revoked_by,
            "revocation_reason": reason
        })

    # =========================================================================
    # Enforcement Points
    # =========================================================================

    def add_enforcement_point(
        self,
        name: str,
        location: str,  # api_layer, query_layer, data_layer
        profiles_enforced: List[str],
        action_on_excess: str = "strip_and_log"
    ) -> str:
        """Add an enforcement point"""
        epid = self._generate_id("ep")
        props = {
            "name": name,
            "location": location,
            "profiles_enforced": profiles_enforced,
            "action_on_excess": action_on_excess,
            "active": True,
            "description": f"Enforcement point: {name}"
        }
        return self._add_node("enforcement_point", epid, props)

    def get_enforcement_points(self) -> List[Dict[str, Any]]:
        """Get all enforcement points"""
        return self._find_nodes("enforcement_point", active=True)

    # =========================================================================
    # Compliance Metrics
    # =========================================================================

    def get_compliance_metrics(
        self,
        use_case_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get minimum necessary compliance metrics"""
        from datetime import datetime, timedelta

        cutoff = (
            datetime.fromisoformat(self._now().replace("+00:00", "")) -
            timedelta(days=days)
        ).isoformat()

        validations = self._find_nodes("mn_validation")

        if use_case_id:
            validations = [v for v in validations if v.get("use_case_id") == use_case_id]

        # Filter by time
        validations = [v for v in validations if v.get("timestamp", "") >= cutoff]

        if not validations:
            return {
                "period_days": days,
                "total_requests": 0,
                "compliance_rate": 1.0,
                "fields_requested": 0,
                "fields_filtered": 0
            }

        compliant = len([v for v in validations if v.get("compliant")])
        total_requested = sum(len(v.get("requested_fields", [])) for v in validations)
        total_filtered = sum(len(v.get("filtered_fields", [])) for v in validations)

        return {
            "period_days": days,
            "total_requests": len(validations),
            "compliant_requests": compliant,
            "non_compliant_requests": len(validations) - compliant,
            "compliance_rate": compliant / len(validations) if validations else 1.0,
            "fields_requested": total_requested,
            "fields_filtered": total_filtered,
            "filter_rate": total_filtered / total_requested if total_requested > 0 else 0
        }

    def get_profile_audit(self, profile_id: str) -> Dict[str, Any]:
        """Get audit information for a profile"""
        profile = self.get_profile(profile_id)
        if not profile:
            return {"error": "Profile not found"}

        validations = self._find_nodes("mn_validation", profile_id=profile_id)
        justifications = self.get_field_justifications(profile_id)
        exceptions = self.get_active_exceptions(profile_id)

        # Calculate usage stats
        field_access = {}
        for v in validations:
            for field in v.get("allowed_fields", []):
                field_access[field] = field_access.get(field, 0) + 1

        return {
            "profile_id": profile_id,
            "use_case_id": profile.get("use_case_id"),
            "phi_required": profile.get("phi_required", []),
            "phi_excluded": profile.get("phi_excluded", []),
            "justification": profile.get("justification"),
            "field_justifications": len(justifications),
            "active_exceptions": len(exceptions),
            "validations_30d": len([
                v for v in validations
                if v.get("timestamp", "") >= self._now()[:10]
            ]),
            "field_access_counts": field_access
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get minimum necessary statistics"""
        base_stats = super().get_stats()
        use_cases = self._find_nodes("use_case", active=True)
        profiles = self._find_nodes("mn_profile", active=True)
        justifications = self._find_nodes("field_justification")
        validations = self._find_nodes("mn_validation")
        exceptions = self._find_nodes("mn_exception", active=True)

        compliant = len([v for v in validations if v.get("compliant")])

        return {
            **base_stats,
            "use_cases": len(use_cases),
            "profiles": len(profiles),
            "field_justifications": len(justifications),
            "validations": len(validations),
            "compliant_validations": compliant,
            "compliance_rate": compliant / len(validations) if validations else 1.0,
            "active_exceptions": len(exceptions)
        }
