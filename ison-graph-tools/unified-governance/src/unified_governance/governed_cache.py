"""
Governed Cache Store
====================

Applies governance controls TO the cache/memory layer itself.

Provides:
- Access control for cache operations
- Retention policies for governance data
- PII-aware caching (sensitivity-based TTL, redaction)
- Audit trail for all cache access
- Compliance-driven eviction policies
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable
import uuid
import hashlib

from ison_graph import ISONGraph


# =============================================================================
# Enums and Data Classes
# =============================================================================

class CacheAccessLevel(str, Enum):
    """Access levels for governance cache."""
    NONE = "none"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    ADMIN = "admin"


class CacheDataSensitivity(str, Enum):
    """Sensitivity levels for cached data."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"
    PII_CONTAINING = "pii_containing"


class RetentionPolicy(str, Enum):
    """Retention policies for governance cache."""
    SESSION_ONLY = "session_only"       # Delete at session end
    SHORT_TERM = "short_term"           # 24 hours
    MEDIUM_TERM = "medium_term"         # 7 days
    LONG_TERM = "long_term"             # 30 days
    COMPLIANCE_REQUIRED = "compliance"  # As required by regulation
    PERMANENT = "permanent"             # Never auto-delete


class CacheOperation(str, Enum):
    """Cache operations for audit."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    EVICT = "evict"
    SEARCH = "search"
    EXPORT = "export"


@dataclass
class CacheAccessGrant:
    """Access grant for a principal to cache resources."""
    grant_id: str
    principal_id: str
    principal_type: str  # agent, human, system
    access_level: CacheAccessLevel
    resource_patterns: List[str]  # e.g., ["decision:*", "pattern:*"]
    sensitivity_max: CacheDataSensitivity
    granted_at: str
    granted_by: str
    expires_at: Optional[str] = None
    conditions: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CacheAuditEntry:
    """Audit entry for cache access."""
    audit_id: str
    timestamp: str
    principal_id: str
    operation: CacheOperation
    resource_key: str
    resource_type: str
    sensitivity: CacheDataSensitivity
    outcome: str  # permitted, denied, redacted
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GovernedCacheEntry:
    """Cache entry with governance metadata."""
    key: str
    value: Any
    sensitivity: CacheDataSensitivity
    retention_policy: RetentionPolicy
    pii_types: List[str]
    created_at: str
    expires_at: Optional[str]
    created_by: str
    access_count: int = 0
    last_accessed: Optional[str] = None
    regulations_applicable: List[str] = field(default_factory=list)


# =============================================================================
# Sensitivity-based TTL Configuration
# =============================================================================

SENSITIVITY_TTL_SECONDS: Dict[CacheDataSensitivity, int] = {
    CacheDataSensitivity.PUBLIC: 86400 * 30,       # 30 days
    CacheDataSensitivity.INTERNAL: 86400 * 7,      # 7 days
    CacheDataSensitivity.CONFIDENTIAL: 86400,      # 24 hours
    CacheDataSensitivity.RESTRICTED: 3600,         # 1 hour
    CacheDataSensitivity.PII_CONTAINING: 1800,     # 30 minutes
}

RETENTION_TTL_SECONDS: Dict[RetentionPolicy, Optional[int]] = {
    RetentionPolicy.SESSION_ONLY: 3600,            # 1 hour max
    RetentionPolicy.SHORT_TERM: 86400,             # 24 hours
    RetentionPolicy.MEDIUM_TERM: 86400 * 7,        # 7 days
    RetentionPolicy.LONG_TERM: 86400 * 30,         # 30 days
    RetentionPolicy.COMPLIANCE_REQUIRED: 86400 * 365 * 7,  # 7 years
    RetentionPolicy.PERMANENT: None,               # Never expires
}


# =============================================================================
# Governed Cache Store
# =============================================================================

class GovernedCacheStore:
    """
    Cache store with governance controls applied.

    Enforces:
    - Principal-based access control
    - Sensitivity-aware caching
    - Retention policy enforcement
    - Full audit trail
    - PII redaction on access
    """

    def __init__(self, graph: ISONGraph):
        self.graph = graph
        self.domain = "governed_cache"
        self._cache: Dict[str, GovernedCacheEntry] = {}
        self._access_grants: Dict[str, CacheAccessGrant] = {}

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    def _generate_id(self, prefix: str) -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    def _add_node(self, node_type: str, node_id: str, properties: Dict[str, Any]) -> str:
        props = {**properties, "_domain": self.domain, "_created_at": self._now()}
        self.graph.add_node(node_type, node_id, props)
        return node_id

    # =========================================================================
    # Access Control
    # =========================================================================

    def grant_access(
        self,
        principal_id: str,
        principal_type: str,
        access_level: CacheAccessLevel,
        resource_patterns: List[str],
        sensitivity_max: CacheDataSensitivity,
        granted_by: str,
        expires_in_hours: Optional[int] = None,
        conditions: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Grant cache access to a principal."""
        grant_id = self._generate_id("cache_grant")

        expires_at = None
        if expires_in_hours:
            expires_at = (datetime.now(timezone.utc) +
                         timedelta(hours=expires_in_hours)).isoformat()

        grant = CacheAccessGrant(
            grant_id=grant_id,
            principal_id=principal_id,
            principal_type=principal_type,
            access_level=access_level,
            resource_patterns=resource_patterns,
            sensitivity_max=sensitivity_max,
            granted_at=self._now(),
            granted_by=granted_by,
            expires_at=expires_at,
            conditions=conditions or {},
        )

        self._access_grants[grant_id] = grant

        # Persist to graph
        self._add_node("cache_access_grant", grant_id, {
            "principal_id": principal_id,
            "principal_type": principal_type,
            "access_level": access_level.value,
            "resource_patterns": resource_patterns,
            "sensitivity_max": sensitivity_max.value,
            "granted_by": granted_by,
            "expires_at": expires_at,
            "conditions": conditions or {},
        })

        return grant_id

    def revoke_access(self, grant_id: str, revoked_by: str) -> bool:
        """Revoke a cache access grant."""
        if grant_id in self._access_grants:
            del self._access_grants[grant_id]

            # Update graph
            node = self.graph.get_node("cache_access_grant", grant_id)
            if node:
                props = {**node.properties, "revoked": True, "revoked_by": revoked_by,
                        "revoked_at": self._now()}
                self.graph.add_node("cache_access_grant", grant_id, props)

            return True
        return False

    def check_access(
        self,
        principal_id: str,
        operation: CacheOperation,
        resource_key: str,
        sensitivity: CacheDataSensitivity,
    ) -> Dict[str, Any]:
        """Check if principal has access to perform operation on resource."""
        # Find applicable grants
        applicable_grants = []

        for grant in self._access_grants.values():
            if grant.principal_id != principal_id:
                continue

            # Check expiration
            if grant.expires_at:
                if grant.expires_at < self._now():
                    continue

            # Check resource pattern match
            if not self._matches_pattern(resource_key, grant.resource_patterns):
                continue

            applicable_grants.append(grant)

        if not applicable_grants:
            return {
                "permitted": False,
                "reason": "No access grant found",
                "required_grant": {
                    "resource_patterns": [resource_key.split(":")[0] + ":*"],
                    "sensitivity_min": sensitivity.value,
                },
            }

        # Check access level
        for grant in applicable_grants:
            # Check operation permission
            if operation in [CacheOperation.READ, CacheOperation.SEARCH]:
                if grant.access_level in [CacheAccessLevel.READ_ONLY,
                                          CacheAccessLevel.READ_WRITE,
                                          CacheAccessLevel.ADMIN]:
                    pass
                else:
                    continue
            elif operation in [CacheOperation.WRITE, CacheOperation.DELETE]:
                if grant.access_level in [CacheAccessLevel.READ_WRITE,
                                          CacheAccessLevel.ADMIN]:
                    pass
                else:
                    continue
            elif operation in [CacheOperation.EVICT, CacheOperation.EXPORT]:
                if grant.access_level != CacheAccessLevel.ADMIN:
                    continue

            # Check sensitivity level
            sensitivity_order = list(CacheDataSensitivity)
            if sensitivity_order.index(sensitivity) > sensitivity_order.index(grant.sensitivity_max):
                continue

            return {
                "permitted": True,
                "grant_id": grant.grant_id,
                "access_level": grant.access_level.value,
            }

        return {
            "permitted": False,
            "reason": "Insufficient access level or sensitivity clearance",
        }

    def _matches_pattern(self, key: str, patterns: List[str]) -> bool:
        """Check if key matches any pattern."""
        for pattern in patterns:
            if pattern == "*":
                return True
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if key.startswith(prefix):
                    return True
            elif pattern == key:
                return True
        return False

    # =========================================================================
    # Governed Cache Operations
    # =========================================================================

    def set(
        self,
        key: str,
        value: Any,
        principal_id: str,
        sensitivity: CacheDataSensitivity = CacheDataSensitivity.INTERNAL,
        retention_policy: RetentionPolicy = RetentionPolicy.MEDIUM_TERM,
        pii_types: Optional[List[str]] = None,
        regulations: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Set a value in governed cache with access control."""
        # Check write access
        access = self.check_access(principal_id, CacheOperation.WRITE, key, sensitivity)

        if not access["permitted"]:
            self._audit(
                principal_id=principal_id,
                operation=CacheOperation.WRITE,
                resource_key=key,
                resource_type=key.split(":")[0] if ":" in key else "unknown",
                sensitivity=sensitivity,
                outcome="denied",
                reason=access.get("reason", "Access denied"),
            )
            return {"error": "Access denied", "reason": access.get("reason")}

        # Calculate expiration
        expires_at = self._calculate_expiration(sensitivity, retention_policy)

        # Create entry
        entry = GovernedCacheEntry(
            key=key,
            value=value,
            sensitivity=sensitivity,
            retention_policy=retention_policy,
            pii_types=pii_types or [],
            created_at=self._now(),
            expires_at=expires_at,
            created_by=principal_id,
            regulations_applicable=regulations or [],
        )

        self._cache[key] = entry

        # Audit
        self._audit(
            principal_id=principal_id,
            operation=CacheOperation.WRITE,
            resource_key=key,
            resource_type=key.split(":")[0] if ":" in key else "unknown",
            sensitivity=sensitivity,
            outcome="permitted",
            reason="Access granted",
            metadata={"pii_types": pii_types, "retention": retention_policy.value},
        )

        return {
            "key": key,
            "expires_at": expires_at,
            "sensitivity": sensitivity.value,
        }

    def get(
        self,
        key: str,
        principal_id: str,
        redact_pii: bool = True,
    ) -> Dict[str, Any]:
        """Get a value from governed cache with access control and optional PII redaction."""
        # Check if key exists
        if key not in self._cache:
            return {"error": "Key not found"}

        entry = self._cache[key]

        # Check expiration
        if entry.expires_at and entry.expires_at < self._now():
            del self._cache[key]
            return {"error": "Key expired"}

        # Check read access
        access = self.check_access(principal_id, CacheOperation.READ, key, entry.sensitivity)

        if not access["permitted"]:
            self._audit(
                principal_id=principal_id,
                operation=CacheOperation.READ,
                resource_key=key,
                resource_type=key.split(":")[0] if ":" in key else "unknown",
                sensitivity=entry.sensitivity,
                outcome="denied",
                reason=access.get("reason", "Access denied"),
            )
            return {"error": "Access denied", "reason": access.get("reason")}

        # Update access stats
        entry.access_count += 1
        entry.last_accessed = self._now()

        # Get value with optional redaction
        value = entry.value
        redacted = False

        if redact_pii and entry.pii_types:
            value, redacted = self._redact_pii(value, entry.pii_types, principal_id)

        # Audit
        self._audit(
            principal_id=principal_id,
            operation=CacheOperation.READ,
            resource_key=key,
            resource_type=key.split(":")[0] if ":" in key else "unknown",
            sensitivity=entry.sensitivity,
            outcome="redacted" if redacted else "permitted",
            reason="Access granted" + (" with PII redaction" if redacted else ""),
        )

        return {
            "key": key,
            "value": value,
            "sensitivity": entry.sensitivity.value,
            "redacted": redacted,
            "pii_types": entry.pii_types if not redacted else [],
        }

    def delete(
        self,
        key: str,
        principal_id: str,
        reason: str = "",
    ) -> Dict[str, Any]:
        """Delete a value from governed cache."""
        if key not in self._cache:
            return {"error": "Key not found"}

        entry = self._cache[key]

        # Check delete access
        access = self.check_access(principal_id, CacheOperation.DELETE, key, entry.sensitivity)

        if not access["permitted"]:
            self._audit(
                principal_id=principal_id,
                operation=CacheOperation.DELETE,
                resource_key=key,
                resource_type=key.split(":")[0] if ":" in key else "unknown",
                sensitivity=entry.sensitivity,
                outcome="denied",
                reason=access.get("reason", "Access denied"),
            )
            return {"error": "Access denied"}

        del self._cache[key]

        self._audit(
            principal_id=principal_id,
            operation=CacheOperation.DELETE,
            resource_key=key,
            resource_type=key.split(":")[0] if ":" in key else "unknown",
            sensitivity=entry.sensitivity,
            outcome="permitted",
            reason=reason or "Deleted by principal",
        )

        return {"deleted": True, "key": key}

    def _calculate_expiration(
        self,
        sensitivity: CacheDataSensitivity,
        retention: RetentionPolicy,
    ) -> Optional[str]:
        """Calculate expiration based on sensitivity and retention policy."""
        # Use the more restrictive of sensitivity TTL and retention TTL
        sensitivity_ttl = SENSITIVITY_TTL_SECONDS.get(sensitivity, 86400)
        retention_ttl = RETENTION_TTL_SECONDS.get(retention)

        if retention_ttl is None:
            # Permanent retention, use sensitivity TTL
            ttl = sensitivity_ttl
        else:
            ttl = min(sensitivity_ttl, retention_ttl)

        return (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()

    def _redact_pii(
        self,
        value: Any,
        pii_types: List[str],
        principal_id: str,
    ) -> tuple[Any, bool]:
        """Redact PII from value based on principal's clearance."""
        # Check if principal has PII access
        # For now, simple redaction - replace with [REDACTED]
        if isinstance(value, dict):
            redacted_value = {}
            was_redacted = False

            for k, v in value.items():
                # Check if key indicates PII
                if any(pii in k.lower() for pii in pii_types):
                    redacted_value[k] = f"[REDACTED:{pii_types[0]}]"
                    was_redacted = True
                elif isinstance(v, dict):
                    redacted_value[k], sub_redacted = self._redact_pii(v, pii_types, principal_id)
                    was_redacted = was_redacted or sub_redacted
                else:
                    redacted_value[k] = v

            return redacted_value, was_redacted

        return value, False

    # =========================================================================
    # Retention Enforcement
    # =========================================================================

    def enforce_retention(self) -> Dict[str, Any]:
        """Enforce retention policies - evict expired entries."""
        evicted = []
        now = self._now()

        for key in list(self._cache.keys()):
            entry = self._cache[key]

            if entry.expires_at and entry.expires_at < now:
                del self._cache[key]
                evicted.append({
                    "key": key,
                    "reason": "expired",
                    "retention_policy": entry.retention_policy.value,
                })

                self._audit(
                    principal_id="system",
                    operation=CacheOperation.EVICT,
                    resource_key=key,
                    resource_type=key.split(":")[0] if ":" in key else "unknown",
                    sensitivity=entry.sensitivity,
                    outcome="evicted",
                    reason="Retention policy enforcement",
                )

        return {
            "evicted_count": len(evicted),
            "evicted_keys": evicted,
        }

    def get_retention_report(self) -> Dict[str, Any]:
        """Get report on cache entries by retention policy."""
        by_policy = {}
        by_sensitivity = {}
        expiring_soon = []

        now = datetime.now(timezone.utc)
        soon = now + timedelta(hours=1)

        for key, entry in self._cache.items():
            # By policy
            policy = entry.retention_policy.value
            by_policy[policy] = by_policy.get(policy, 0) + 1

            # By sensitivity
            sens = entry.sensitivity.value
            by_sensitivity[sens] = by_sensitivity.get(sens, 0) + 1

            # Expiring soon
            if entry.expires_at:
                exp_time = datetime.fromisoformat(entry.expires_at.replace("Z", "+00:00"))
                if exp_time < soon:
                    expiring_soon.append({
                        "key": key,
                        "expires_at": entry.expires_at,
                        "sensitivity": entry.sensitivity.value,
                    })

        return {
            "total_entries": len(self._cache),
            "by_retention_policy": by_policy,
            "by_sensitivity": by_sensitivity,
            "expiring_within_hour": len(expiring_soon),
            "expiring_entries": expiring_soon[:10],  # Top 10
        }

    # =========================================================================
    # Audit Trail
    # =========================================================================

    def _audit(
        self,
        principal_id: str,
        operation: CacheOperation,
        resource_key: str,
        resource_type: str,
        sensitivity: CacheDataSensitivity,
        outcome: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Record audit entry for cache operation."""
        audit_id = self._generate_id("cache_audit")

        self._add_node("cache_audit", audit_id, {
            "principal_id": principal_id,
            "operation": operation.value,
            "resource_key": resource_key,
            "resource_type": resource_type,
            "sensitivity": sensitivity.value,
            "outcome": outcome,
            "reason": reason,
            "metadata": metadata or {},
        })

        return audit_id

    def get_audit_trail(
        self,
        principal_id: Optional[str] = None,
        resource_key: Optional[str] = None,
        operation: Optional[CacheOperation] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit trail with optional filters."""
        audits = []

        for node in self.graph.nodes():
            if node.type != "cache_audit":
                continue

            props = node.properties

            # Apply filters
            if principal_id and props.get("principal_id") != principal_id:
                continue
            if resource_key and props.get("resource_key") != resource_key:
                continue
            if operation and props.get("operation") != operation.value:
                continue

            audits.append({"id": node.id, **props})

        # Sort by timestamp descending
        audits.sort(key=lambda x: x.get("_created_at", ""), reverse=True)

        return audits[:limit]

    # =========================================================================
    # PII-Aware Operations
    # =========================================================================

    def get_pii_containing_entries(self) -> List[Dict[str, Any]]:
        """Get all cache entries containing PII."""
        pii_entries = []

        for key, entry in self._cache.items():
            if entry.pii_types:
                pii_entries.append({
                    "key": key,
                    "pii_types": entry.pii_types,
                    "sensitivity": entry.sensitivity.value,
                    "created_by": entry.created_by,
                    "expires_at": entry.expires_at,
                    "access_count": entry.access_count,
                })

        return pii_entries

    def purge_pii_for_subject(
        self,
        subject_id: str,
        principal_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Purge all cached data related to a subject (for erasure requests)."""
        purged = []

        for key in list(self._cache.keys()):
            entry = self._cache[key]

            # Check if entry relates to subject
            if isinstance(entry.value, dict):
                if entry.value.get("subject_id") == subject_id or \
                   entry.value.get("data_subject_id") == subject_id or \
                   subject_id in str(entry.value):

                    # Check delete access
                    access = self.check_access(
                        principal_id, CacheOperation.DELETE, key, entry.sensitivity
                    )
                    if access["permitted"]:
                        del self._cache[key]
                        purged.append(key)

                        self._audit(
                            principal_id=principal_id,
                            operation=CacheOperation.DELETE,
                            resource_key=key,
                            resource_type="pii_purge",
                            sensitivity=entry.sensitivity,
                            outcome="permitted",
                            reason=f"Subject erasure: {reason}",
                            metadata={"subject_id": subject_id},
                        )

        return {
            "subject_id": subject_id,
            "purged_count": len(purged),
            "purged_keys": purged,
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get governed cache statistics."""
        total_entries = len(self._cache)
        pii_entries = len([e for e in self._cache.values() if e.pii_types])
        total_grants = len(self._access_grants)

        # Count audits by outcome
        audit_outcomes = {}
        for node in self.graph.nodes():
            if node.type == "cache_audit":
                outcome = node.properties.get("outcome", "unknown")
                audit_outcomes[outcome] = audit_outcomes.get(outcome, 0) + 1

        return {
            "total_cache_entries": total_entries,
            "pii_containing_entries": pii_entries,
            "active_access_grants": total_grants,
            "audit_by_outcome": audit_outcomes,
        }
