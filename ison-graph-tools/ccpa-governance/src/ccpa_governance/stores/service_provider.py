"""
Service Provider Store
======================

Service Provider and Contractor contract management under CCPA/CPRA.
"""

from typing import Any, Dict, List, Optional

from .base import BaseCCPAStore
from ..schema import BusinessRole, PersonalInfoCategory


class ServiceProviderStore(BaseCCPAStore):
    """
    Service Provider and Contractor Management.

    Tracks:
    - Service provider contracts
    - Contractor contracts (CPRA)
    - Required contract provisions
    - PI categories shared
    - Audit rights and compliance
    """

    def register_service_provider(
        self,
        provider_id: str,
        name: str,
        services: str,
        pi_categories: List[PersonalInfoCategory],
        contract_date: str,
        contact: str = "",
        audit_rights: bool = False,
        expires_at: Optional[str] = None,
    ) -> str:
        """
        Register a service provider with required CCPA contract.

        Service provider must:
        - Not retain, use, or disclose PI except as specified
        - Not sell the PI
        - Comply with applicable CCPA requirements
        - Certify understanding of restrictions

        Args:
            provider_id: Provider identifier
            name: Provider name
            services: Services provided
            pi_categories: Categories of PI shared
            contract_date: Contract effective date
            contact: Provider contact
            audit_rights: Whether business has audit rights
            expires_at: Contract expiration date

        Returns:
            Provider node ID
        """
        categories = [c.value for c in pi_categories]

        self.graph.add_node(
            "service_provider",
            provider_id,
            name=name,
            role=BusinessRole.SERVICE_PROVIDER.value,
            services=self._sanitize(services),
            pi_categories=self._list_to_str(categories),
            contract_date=contract_date,
            contact=contact,
            audit_rights=str(audit_rights),
            expires_at=expires_at or "",
            status="active",
            # Required CCPA contract provisions
            no_sell_provision=str(True),
            no_retain_provision=str(True),
            limited_use_provision=str(True),
            compliance_certification=str(True),
            created_at=self._now(),
            last_reviewed=self._now(),
        )

        return provider_id

    def register_contractor(
        self,
        contractor_id: str,
        name: str,
        services: str,
        pi_categories: List[PersonalInfoCategory],
        contract_date: str,
        business_purpose: str,
        contact: str = "",
        audit_rights: bool = False,
        expires_at: Optional[str] = None,
    ) -> str:
        """
        Register a contractor (CPRA addition).

        Contractors have similar but distinct requirements from
        service providers. Must have written contract with
        specific business purpose.
        """
        categories = [c.value for c in pi_categories]

        self.graph.add_node(
            "contractor",
            contractor_id,
            name=name,
            role=BusinessRole.CONTRACTOR.value,
            services=self._sanitize(services),
            business_purpose=self._sanitize(business_purpose),
            pi_categories=self._list_to_str(categories),
            contract_date=contract_date,
            contact=contact,
            audit_rights=str(audit_rights),
            expires_at=expires_at or "",
            status="active",
            # Required CPRA contractor provisions
            specific_purpose_provision=str(True),
            no_sell_share_provision=str(True),
            no_combine_provision=str(True),
            compliance_certification=str(True),
            created_at=self._now(),
            last_reviewed=self._now(),
        )

        return contractor_id

    def update_contract(
        self,
        provider_id: str,
        is_contractor: bool = False,
        **updates
    ) -> Dict[str, Any]:
        """Update a service provider or contractor contract"""
        node_type = "contractor" if is_contractor else "service_provider"
        node = self.graph.get_node(node_type, provider_id)
        if not node:
            return {"error": f"{node_type} not found"}

        updates["last_reviewed"] = self._now()
        self.graph.update_node(node_type, provider_id, **updates)

        return {"provider_id": provider_id, "updated": True}

    def record_audit(
        self,
        provider_id: str,
        is_contractor: bool = False,
        audit_date: str = "",
        auditor: str = "",
        findings: str = "",
        compliant: bool = True,
    ) -> str:
        """Record an audit of a service provider/contractor"""
        audit_id = self._make_id("sp_audit", provider_id)

        self.graph.add_node(
            "provider_audit",
            audit_id,
            provider_id=provider_id,
            provider_type="contractor" if is_contractor else "service_provider",
            audit_date=audit_date or self._now(),
            auditor=auditor,
            findings=self._sanitize(findings),
            compliant=str(compliant),
            created_at=self._now(),
        )

        node_type = "contractor" if is_contractor else "service_provider"
        if self.graph.has_node(node_type, provider_id):
            self.graph.add_edge(
                "HAS_AUDIT",
                (node_type, provider_id),
                ("provider_audit", audit_id),
            )
            self.graph.update_node(
                node_type, provider_id,
                last_audit=self._now(),
                last_audit_compliant=str(compliant),
            )

        return audit_id

    def terminate_contract(
        self,
        provider_id: str,
        is_contractor: bool = False,
        reason: str = "",
        data_return_confirmed: bool = False,
        data_deletion_confirmed: bool = False,
    ) -> Dict[str, Any]:
        """Terminate a service provider/contractor contract"""
        node_type = "contractor" if is_contractor else "service_provider"
        node = self.graph.get_node(node_type, provider_id)
        if not node:
            return {"error": f"{node_type} not found"}

        self.graph.update_node(
            node_type,
            provider_id,
            status="terminated",
            terminated_at=self._now(),
            termination_reason=reason,
            data_return_confirmed=str(data_return_confirmed),
            data_deletion_confirmed=str(data_deletion_confirmed),
        )

        return {
            "provider_id": provider_id,
            "status": "terminated",
            "data_handled": data_return_confirmed or data_deletion_confirmed,
        }

    def get_service_provider(self, provider_id: str) -> Optional[Dict[str, Any]]:
        """Get service provider details"""
        node = self.graph.get_node("service_provider", provider_id)
        if node:
            return {
                "id": provider_id,
                **node.properties,
                "pi_categories": self._str_to_list(
                    node.properties.get("pi_categories", "")
                ),
            }
        return None

    def get_contractor(self, contractor_id: str) -> Optional[Dict[str, Any]]:
        """Get contractor details"""
        node = self.graph.get_node("contractor", contractor_id)
        if node:
            return {
                "id": contractor_id,
                **node.properties,
                "pi_categories": self._str_to_list(
                    node.properties.get("pi_categories", "")
                ),
            }
        return None

    def list_service_providers(
        self,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """List all service providers"""
        results = []
        for node in self.graph.nodes():
            if node.type == "service_provider":
                if status and node.properties.get("status") != status:
                    continue
                results.append(self.get_service_provider(node.id))
        return results

    def list_contractors(
        self,
        status: str = "active"
    ) -> List[Dict[str, Any]]:
        """List all contractors"""
        results = []
        for node in self.graph.nodes():
            if node.type == "contractor":
                if status and node.properties.get("status") != status:
                    continue
                results.append(self.get_contractor(node.id))
        return results

    def get_providers_with_category(
        self,
        category: PersonalInfoCategory
    ) -> List[Dict[str, Any]]:
        """Get all providers/contractors with access to a PI category"""
        results = []
        for node in self.graph.nodes():
            if node.type in ["service_provider", "contractor"]:
                categories = self._str_to_list(
                    node.properties.get("pi_categories", "")
                )
                if category.value in categories:
                    results.append({"id": node.id, **node.properties})
        return results

    def get_expiring_contracts(
        self,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """Get contracts expiring within specified days"""
        threshold = self._deadline(days)
        results = []
        for node in self.graph.nodes():
            if node.type in ["service_provider", "contractor"]:
                expires = node.properties.get("expires_at", "")
                if expires and expires <= threshold and \
                   node.properties.get("status") == "active":
                    results.append({"id": node.id, **node.properties})
        return results

    def check_contract_compliance(
        self,
        provider_id: str,
        is_contractor: bool = False,
    ) -> Dict[str, Any]:
        """Check if a contract has all required CCPA provisions"""
        node_type = "contractor" if is_contractor else "service_provider"
        node = self.graph.get_node(node_type, provider_id)
        if not node:
            return {"error": f"{node_type} not found"}

        if is_contractor:
            required = [
                "specific_purpose_provision",
                "no_sell_share_provision",
                "no_combine_provision",
                "compliance_certification",
            ]
        else:
            required = [
                "no_sell_provision",
                "no_retain_provision",
                "limited_use_provision",
                "compliance_certification",
            ]

        missing = []
        for provision in required:
            if node.properties.get(provision) != "True":
                missing.append(provision)

        return {
            "provider_id": provider_id,
            "compliant": len(missing) == 0,
            "missing_provisions": missing,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get service provider statistics"""
        service_providers = 0
        contractors = 0
        active = 0
        terminated = 0
        with_audit_rights = 0
        pi_categories_shared = set()

        for node in self.graph.nodes():
            if node.type == "service_provider":
                service_providers += 1
                if node.properties.get("status") == "active":
                    active += 1
                else:
                    terminated += 1
                if node.properties.get("audit_rights") == "True":
                    with_audit_rights += 1
                for cat in self._str_to_list(node.properties.get("pi_categories", "")):
                    pi_categories_shared.add(cat)
            elif node.type == "contractor":
                contractors += 1
                if node.properties.get("status") == "active":
                    active += 1
                else:
                    terminated += 1

        return {
            "total_service_providers": service_providers,
            "total_contractors": contractors,
            "active_contracts": active,
            "terminated_contracts": terminated,
            "with_audit_rights": with_audit_rights,
            "pi_categories_shared": list(pi_categories_shared),
        }
