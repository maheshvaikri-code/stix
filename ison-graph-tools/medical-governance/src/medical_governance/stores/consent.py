"""
Consent Management Store
========================

Manages patient consents, authorizations, and restrictions per HIPAA 45 CFR 164.508/164.522.
Tracks consent lifecycle, scopes, and verification.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import ConsentType, ConsentStatus, AccessPurpose

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class ConsentStore(BaseStore):
    """Store for patient consent management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "consent")

    # =========================================================================
    # Consent Type Management
    # =========================================================================

    def add_consent_type(
        self,
        name: str,
        consent_type: ConsentType,
        hipaa_basis: str,
        required_for: str,
        default: str,  # required, implied, opt_in, opt_out
        description: str = ""
    ) -> str:
        """Add a consent type definition"""
        ctid = name
        props = {
            "name": name,
            "consent_type": consent_type.value,
            "hipaa_basis": hipaa_basis,
            "required_for": required_for,
            "default": default,
            "description": description or f"Consent type: {name}"
        }
        return self._add_node("consent_type_def", ctid, props)

    def get_consent_type(self, type_id: str) -> Optional[Dict[str, Any]]:
        """Get consent type by ID"""
        return self._get_node("consent_type_def", type_id)

    def list_consent_types(self) -> List[Dict[str, Any]]:
        """List all consent types"""
        return self._find_nodes("consent_type_def")

    # =========================================================================
    # Consent Record Management
    # =========================================================================

    def add_consent(
        self,
        patient_id: str,
        consent_type: ConsentType,
        status: ConsentStatus,
        scope: str,
        granted_date: Optional[str] = None,
        expires: Optional[str] = None,
        witness: Optional[str] = None,
        consent_id: Optional[str] = None
    ) -> str:
        """Add a patient consent record"""
        cid = consent_id or self._generate_id("cs")
        props = {
            "patient_id": patient_id,
            "consent_type": consent_type.value,
            "status": status.value,
            "scope": scope,
            "granted_date": granted_date or self._now(),
            "expires": expires,
            "witness": witness,
            "description": f"Consent for {patient_id}: {consent_type.value}"
        }
        self._add_node("consent_record", cid, props)

        # Try to link to patient if patient node exists
        try:
            patient_node = self._get_node("patient", patient_id)
            if patient_node:
                self._add_edge(
                    "patient", patient_id,
                    "HAS_CONSENT",
                    "consent_record", cid,
                    {"consent_type": consent_type.value}
                )
        except Exception:
            # Patient node doesn't exist, that's ok
            pass

        return cid

    def get_consent(self, consent_id: str) -> Optional[Dict[str, Any]]:
        """Get consent by ID"""
        return self._get_node("consent_record", consent_id)

    def get_patient_consents(
        self,
        patient_id: str,
        consent_type: Optional[ConsentType] = None,
        status: Optional[ConsentStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get all consents for a patient"""
        consents = self._find_nodes("consent_record", patient_id=patient_id)

        if consent_type:
            consents = [c for c in consents if c.get("consent_type") == consent_type.value]
        if status:
            consents = [c for c in consents if c.get("status") == status.value]

        return consents

    def check_consent(
        self,
        patient_id: str,
        consent_type: ConsentType,
        purpose: Optional[AccessPurpose] = None
    ) -> Dict[str, Any]:
        """Check if patient has valid consent for a type"""
        consents = self.get_patient_consents(
            patient_id,
            consent_type=consent_type,
            status=ConsentStatus.ACTIVE
        )

        if not consents:
            # Check for explicit denial
            denied = self.get_patient_consents(
                patient_id,
                consent_type=consent_type,
                status=ConsentStatus.DENIED
            )
            if denied:
                return {
                    "has_consent": False,
                    "reason": "explicitly_denied",
                    "consent_id": denied[0]["id"]
                }

            return {
                "has_consent": False,
                "reason": "no_consent_on_file",
                "consent_id": None
            }

        # Check expiration
        consent = consents[0]
        expires = consent.get("expires")
        if expires and expires < self._now():
            return {
                "has_consent": False,
                "reason": "consent_expired",
                "consent_id": consent["id"],
                "expired_at": expires
            }

        return {
            "has_consent": True,
            "consent_id": consent["id"],
            "scope": consent.get("scope"),
            "granted_date": consent.get("granted_date"),
            "expires": expires
        }

    # =========================================================================
    # Consent Scope Management
    # =========================================================================

    def add_consent_scope(
        self,
        consent_id: str,
        scope_type: str,  # data_elements, time_period, recipients, organizations
        included: List[str],
        excluded: Optional[List[str]] = None
    ) -> str:
        """Add scope details to a consent"""
        sid = self._generate_id("csc")
        props = {
            "consent_id": consent_id,
            "scope_type": scope_type,
            "included": included,
            "excluded": excluded or [],
            "description": f"Consent scope: {scope_type}"
        }
        self._add_node("consent_scope", sid, props)

        # Link to consent
        self._add_edge(
            "consent_record", consent_id,
            "HAS_SCOPE",
            "consent_scope", sid,
            {}
        )

        return sid

    def get_consent_scopes(self, consent_id: str) -> List[Dict[str, Any]]:
        """Get all scopes for a consent"""
        return self._find_nodes("consent_scope", consent_id=consent_id)

    def check_scope_includes(
        self,
        consent_id: str,
        scope_type: str,
        item: str
    ) -> bool:
        """Check if a consent scope includes an item"""
        scopes = self._find_nodes(
            "consent_scope",
            consent_id=consent_id,
            scope_type=scope_type
        )

        if not scopes:
            return True  # No scope restriction = allowed

        scope = scopes[0]
        included = scope.get("included", [])
        excluded = scope.get("excluded", [])

        if item in excluded:
            return False
        if not included:  # Empty included means all allowed
            return True
        return item in included

    # =========================================================================
    # Consent Revocation
    # =========================================================================

    def revoke_consent(
        self,
        consent_id: str,
        revoked_by: str,
        reason: str,
        effective: str = "prospective"  # prospective, retroactive
    ) -> str:
        """Revoke a consent"""
        self._update_node("consent_record", consent_id, {
            "status": ConsentStatus.REVOKED.value,
            "revoked_at": self._now(),
            "revoked_by": revoked_by
        })

        # Record revocation event
        rid = self._generate_id("rv")
        props = {
            "consent_id": consent_id,
            "revoked_by": revoked_by,
            "reason": reason,
            "effective": effective,
            "revoked_at": self._now(),
            "description": f"Consent revocation: {consent_id}"
        }
        self._add_node("consent_revocation", rid, props)

        return rid

    def get_revocation(self, consent_id: str) -> Optional[Dict[str, Any]]:
        """Get revocation record for a consent"""
        revocations = self._find_nodes("consent_revocation", consent_id=consent_id)
        return revocations[0] if revocations else None

    # =========================================================================
    # Consent Witness
    # =========================================================================

    def add_witness(
        self,
        consent_id: str,
        witness_type: str,  # staff_witness, patient_signature, notarized
        witness_name: str,
        date: Optional[str] = None
    ) -> str:
        """Add a witness to a consent"""
        wid = self._generate_id("cw")
        props = {
            "consent_id": consent_id,
            "witness_type": witness_type,
            "witness_name": witness_name,
            "date": date or self._now(),
            "description": f"Consent witness: {witness_name}"
        }
        self._add_node("consent_witness", wid, props)

        # Link to consent
        self._add_edge(
            "consent_record", consent_id,
            "WITNESSED_BY",
            "consent_witness", wid,
            {}
        )

        return wid

    # =========================================================================
    # Restriction Requests
    # =========================================================================

    def add_restriction(
        self,
        patient_id: str,
        restriction_type: str,  # disclosure_restriction, self_pay, family_restriction
        scope: str,
        status: str = "requested"
    ) -> str:
        """Add a patient restriction request"""
        rid = self._generate_id("rr")
        props = {
            "patient_id": patient_id,
            "restriction_type": restriction_type,
            "scope": scope,
            "status": status,  # requested, agreed, denied
            "requested_at": self._now(),
            "description": f"Restriction request: {restriction_type}"
        }
        self._add_node("restriction_request", rid, props)

        return rid

    def approve_restriction(
        self,
        restriction_id: str,
        approved_by: str,
        implementation_notes: str = ""
    ):
        """Approve a restriction request"""
        self._update_node("restriction_request", restriction_id, {
            "status": "agreed",
            "approved_at": self._now(),
            "approved_by": approved_by,
            "implementation_notes": implementation_notes or "Restriction implemented"
        })

    def get_patient_restrictions(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all restrictions for a patient"""
        restrictions = self._find_nodes("restriction_request", patient_id=patient_id)
        return [r for r in restrictions if r.get("status") == "agreed"]

    def check_restriction(
        self,
        patient_id: str,
        restriction_type: str
    ) -> Dict[str, Any]:
        """Check if a restriction is active"""
        restrictions = self._find_nodes(
            "restriction_request",
            patient_id=patient_id,
            restriction_type=restriction_type,
            status="agreed"
        )

        if restrictions:
            return {
                "restricted": True,
                "restriction_id": restrictions[0]["id"],
                "scope": restrictions[0].get("scope")
            }

        return {"restricted": False}

    # =========================================================================
    # Confidential Communications
    # =========================================================================

    def add_confidential_comm(
        self,
        patient_id: str,
        comm_type: str,  # alternate_address, alternate_phone, portal_only
        alternative: str,
        status: str = "active"
    ) -> str:
        """Add a confidential communication preference"""
        ccid = self._generate_id("cc")
        props = {
            "patient_id": patient_id,
            "comm_type": comm_type,
            "alternative": alternative,
            "status": status,
            "requested_at": self._now(),
            "description": f"Confidential comm: {comm_type}"
        }
        return self._add_node("confidential_comm", ccid, props)

    def get_confidential_comms(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get confidential communication preferences for a patient"""
        return self._find_nodes("confidential_comm", patient_id=patient_id, status="active")

    # =========================================================================
    # Consent Verification
    # =========================================================================

    def verify_consent(
        self,
        consent_id: str,
        verified_by: str,
        verification_method: str
    ) -> str:
        """Record consent verification"""
        vid = self._generate_id("cv")
        props = {
            "consent_id": consent_id,
            "verified_by": verified_by,
            "verification_method": verification_method,
            "verified_at": self._now(),
            "description": f"Consent verification: {consent_id}"
        }
        return self._add_node("consent_verification", vid, props)

    # =========================================================================
    # Consent Audit Trail
    # =========================================================================

    def get_consent_history(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get full consent history for a patient"""
        consents = self.get_patient_consents(patient_id)

        history = []
        for consent in consents:
            entry = {
                "consent_id": consent["id"],
                "type": consent.get("consent_type"),
                "status": consent.get("status"),
                "granted_date": consent.get("granted_date"),
                "events": []
            }

            # Add creation event
            entry["events"].append({
                "event": "created",
                "date": consent.get("granted_date"),
                "status": "active" if consent.get("status") == "active" else consent.get("status")
            })

            # Check for revocation
            revocation = self.get_revocation(consent["id"])
            if revocation:
                entry["events"].append({
                    "event": "revoked",
                    "date": revocation.get("revoked_at"),
                    "by": revocation.get("revoked_by"),
                    "reason": revocation.get("reason")
                })

            history.append(entry)

        return history

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get consent management statistics"""
        base_stats = super().get_stats()
        consent_types = self._find_nodes("consent_type_def")
        consents = self._find_nodes("consent_record")
        restrictions = self._find_nodes("restriction_request")
        revocations = self._find_nodes("consent_revocation")

        active = len([c for c in consents if c.get("status") == ConsentStatus.ACTIVE.value])
        revoked = len([c for c in consents if c.get("status") == ConsentStatus.REVOKED.value])
        denied = len([c for c in consents if c.get("status") == ConsentStatus.DENIED.value])

        return {
            **base_stats,
            "consent_types": len(consent_types),
            "total_consents": len(consents),
            "active_consents": active,
            "revoked_consents": revoked,
            "denied_consents": denied,
            "restrictions": len(restrictions),
            "active_restrictions": len([r for r in restrictions if r.get("status") == "agreed"]),
            "revocations": len(revocations)
        }
