"""
Unified Governance Engine
=========================

Main engine integrating Agent, GDPR, CCPA, and PII governance.
"""

from typing import Any, Dict, List, Optional

from ison_graph import ISONGraph

from .stores import (
    RegulatoryBridgeStore,
    PIIComplianceStore,
    SubjectUnificationStore,
    AgentIntegrationStore,
)
from .schema import (
    GovernanceDomain,
    ComplianceStatus,
    CrossDomainRiskLevel,
    IntegrationEventType,
    RegulationJurisdiction,
)
from .memory_integration import (
    GovernanceMemoryStore,
    CachedGovernanceContext,
    GovernanceSessionManager,
)
from .governed_cache import (
    GovernedCacheStore,
    CacheAccessLevel,
    CacheDataSensitivity,
    RetentionPolicy,
    CacheOperation,
)


class UnifiedGovernanceEngine:
    """
    Unified governance engine integrating all governance domains.

    Combines:
    - Agent Governance (authority, policy, risk, audit)
    - GDPR Governance (consent, rights, processing, breach)
    - CCPA Governance (consumer rights, opt-out, sale/share)
    - PII Governance (detection, classification, inventory)

    Provides cross-domain:
    - Compliance checking
    - Risk assessment
    - Subject unification
    - Audit trails
    """

    def __init__(
        self,
        graph: Optional[ISONGraph] = None,
        name: str = "unified_governance",
    ):
        """
        Initialize unified governance engine.

        Args:
            graph: Shared ISONGraph instance (creates new if None)
            name: Name for this governance instance
        """
        self.name = name
        self.graph = graph or ISONGraph()

        # Integration stores
        self.regulatory = RegulatoryBridgeStore(self.graph)
        self.pii_compliance = PIIComplianceStore(self.graph)
        self.subjects = SubjectUnificationStore(self.graph)
        self.agent_integration = AgentIntegrationStore(self.graph)

        # Memory integration (agent-memory + ISONCache pattern)
        self.memory = GovernanceMemoryStore(self.graph)
        self.sessions = GovernanceSessionManager(self.graph)
        self._cached_context = None  # Lazy initialized

        # Governed cache (governance applied TO the cache)
        self.governed_cache = GovernedCacheStore(self.graph)

        # Domain engines (lazy loaded)
        self._agent_gov = None
        self._gdpr_gov = None
        self._ccpa_gov = None
        self._pii_gov = None

    # =========================================================================
    # Domain Engine Access
    # =========================================================================

    @property
    def agent(self):
        """Get Agent Governance engine."""
        if self._agent_gov is None:
            try:
                from agent_governance import GovernanceEngine
                self._agent_gov = GovernanceEngine(self.name)
                self._agent_gov.graph = self.graph
            except ImportError:
                return None
        return self._agent_gov

    @property
    def gdpr(self):
        """Get GDPR Governance engine."""
        if self._gdpr_gov is None:
            try:
                from gdpr_governance import GDPRGovernance
                self._gdpr_gov = GDPRGovernance(self.graph)
            except ImportError:
                return None
        return self._gdpr_gov

    @property
    def ccpa(self):
        """Get CCPA Governance engine."""
        if self._ccpa_gov is None:
            try:
                from ccpa_governance import CCPAGovernance
                self._ccpa_gov = CCPAGovernance(self.graph)
            except ImportError:
                return None
        return self._ccpa_gov

    @property
    def pii(self):
        """Get PII Governance engine."""
        if self._pii_gov is None:
            try:
                from pii_governance import PIIGovernance
                self._pii_gov = PIIGovernance(self.graph)
            except ImportError:
                return None
        return self._pii_gov

    @property
    def cached_context(self) -> CachedGovernanceContext:
        """Get cached governance context manager."""
        if self._cached_context is None:
            self._cached_context = CachedGovernanceContext(self, self.memory)
        return self._cached_context

    # =========================================================================
    # Memory and Learning Operations
    # =========================================================================

    def start_session(self, task: str) -> str:
        """Start a governance session for workflow continuity."""
        return self.sessions.start_session(task)

    def end_session(self, outcome: str, summary: str = "") -> Dict[str, Any]:
        """End current governance session."""
        return self.sessions.end_session(outcome, summary)

    def get_session_handoff(self) -> Dict[str, Any]:
        """Get handoff data from previous session."""
        return self.sessions.get_session_handoff()

    def get_context_for_action(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_subject_id: Optional[str] = None,
        token_budget: int = 2000,
    ) -> Dict[str, Any]:
        """Get cached governance context for an action (token-budgeted)."""
        return self.cached_context.get_context(
            agent_id=agent_id,
            action=action,
            pii_types=pii_types,
            data_subject_id=data_subject_id,
            token_budget=token_budget,
        )

    def check_warnings(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
    ) -> List[Dict[str, Any]]:
        """Check for proactive warnings based on learned patterns."""
        return self.memory.check_warnings(agent_id, action, pii_types)

    def add_governance_convention(
        self,
        category: str,
        rule: str,
        description: str,
        regulations: Optional[List[str]] = None,
    ) -> str:
        """Add a governance convention for the organization."""
        return self.memory.add_convention(category, rule, description, regulations)

    def add_warning_pattern(
        self,
        name: str,
        trigger: Dict[str, Any],
        warning_message: str,
        severity: str = "medium",
        auto_block: bool = False,
    ) -> str:
        """Add a proactive warning pattern."""
        return self.memory.add_warning_pattern(
            name, trigger, warning_message, severity, auto_block
        )

    def provide_feedback(
        self,
        decision_id: str,
        feedback: str,
        was_correct: bool,
    ) -> Dict[str, Any]:
        """Provide feedback on a compliance decision (reinforcement learning)."""
        return self.memory.add_feedback(decision_id, feedback, was_correct)

    # =========================================================================
    # Governed Cache Operations
    # =========================================================================

    def grant_cache_access(
        self,
        principal_id: str,
        principal_type: str,
        access_level: CacheAccessLevel,
        resource_patterns: List[str],
        sensitivity_max: CacheDataSensitivity,
        granted_by: str,
        expires_in_hours: Optional[int] = None,
    ) -> str:
        """Grant cache access to a principal with governance controls."""
        return self.governed_cache.grant_access(
            principal_id=principal_id,
            principal_type=principal_type,
            access_level=access_level,
            resource_patterns=resource_patterns,
            sensitivity_max=sensitivity_max,
            granted_by=granted_by,
            expires_in_hours=expires_in_hours,
        )

    def cache_with_governance(
        self,
        key: str,
        value: Any,
        principal_id: str,
        sensitivity: CacheDataSensitivity = CacheDataSensitivity.INTERNAL,
        retention: RetentionPolicy = RetentionPolicy.MEDIUM_TERM,
        pii_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Store value in governed cache with access control and retention."""
        return self.governed_cache.set(
            key=key,
            value=value,
            principal_id=principal_id,
            sensitivity=sensitivity,
            retention_policy=retention,
            pii_types=pii_types,
        )

    def get_from_governed_cache(
        self,
        key: str,
        principal_id: str,
        redact_pii: bool = True,
    ) -> Dict[str, Any]:
        """Get value from governed cache with access control."""
        return self.governed_cache.get(
            key=key,
            principal_id=principal_id,
            redact_pii=redact_pii,
        )

    def purge_subject_from_cache(
        self,
        subject_id: str,
        principal_id: str,
        reason: str,
    ) -> Dict[str, Any]:
        """Purge all cached data for a subject (erasure request support)."""
        return self.governed_cache.purge_pii_for_subject(
            subject_id=subject_id,
            principal_id=principal_id,
            reason=reason,
        )

    def get_cache_audit_trail(
        self,
        principal_id: Optional[str] = None,
        resource_key: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get audit trail for cache operations."""
        return self.governed_cache.get_audit_trail(
            principal_id=principal_id,
            resource_key=resource_key,
            limit=limit,
        )

    def enforce_cache_retention(self) -> Dict[str, Any]:
        """Enforce retention policies on governed cache."""
        return self.governed_cache.enforce_retention()

    # =========================================================================
    # Cross-Domain Compliance Check
    # =========================================================================

    def check_compliance(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_subject_id: Optional[str] = None,
        jurisdiction: RegulationJurisdiction = RegulationJurisdiction.GLOBAL,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Perform comprehensive compliance check across all domains.

        Args:
            agent_id: ID of the agent performing the action
            action: Action being performed
            pii_types: Types of PII involved
            data_subject_id: Optional unified subject ID
            jurisdiction: Regulatory jurisdiction
            context: Additional context for compliance checks

        Returns:
            Comprehensive compliance check result
        """
        check_id = self.regulatory._generate_id("unified_check")
        context = context or {}

        results = {
            "check_id": check_id,
            "agent_id": agent_id,
            "action": action,
            "pii_types": pii_types,
            "data_subject_id": data_subject_id,
            "jurisdiction": jurisdiction.value,
            "timestamp": self.regulatory._now(),
            "domain_results": {},
            "blocking_issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # 1. Agent integration check
        agent_check = self.agent_integration.check_action_compliance(
            agent_id=agent_id,
            action=action,
            pii_types_involved=pii_types,
            data_subject_id=data_subject_id,
            context=context,
        )
        results["domain_results"]["agent_integration"] = agent_check
        results["blocking_issues"].extend(agent_check.get("blocking_issues", []))
        results["warnings"].extend(agent_check.get("warnings", []))

        # 2. Check if action is blocked
        block_check = self.agent_integration.is_action_blocked(agent_id, action)
        if block_check.get("blocked"):
            results["blocking_issues"].append({
                "domain": "agent_block",
                "issue": "Action is blocked by regulatory requirement",
                "blocks": block_check.get("blocks", []),
            })

        # 3. PII compliance check for each PII type
        for pii_type in pii_types:
            pii_check = self.pii_compliance.check_all_regulations(
                pii_type=pii_type,
                context={
                    "gdpr": context.get("gdpr", {}),
                    "ccpa": context.get("ccpa", {}),
                },
            )
            results["domain_results"][f"pii_{pii_type}"] = pii_check

            if pii_check.get("overall_status") == ComplianceStatus.NON_COMPLIANT.value:
                results["blocking_issues"].append({
                    "domain": "pii_compliance",
                    "pii_type": pii_type,
                    "issue": f"PII type '{pii_type}' has compliance issues",
                    "details": pii_check.get("issues", []),
                })
            elif pii_check.get("overall_status") == ComplianceStatus.PARTIAL.value:
                results["warnings"].append({
                    "domain": "pii_compliance",
                    "pii_type": pii_type,
                    "issue": f"PII type '{pii_type}' has partial compliance",
                    "details": pii_check.get("issues", []),
                })

        # 4. Data subject status check (if applicable)
        if data_subject_id:
            subject_status = self.subjects.get_cross_regulation_status(data_subject_id)
            if subject_status.get("error"):
                results["warnings"].append({
                    "domain": "subject",
                    "issue": "Data subject not found in unified registry",
                })
            else:
                results["domain_results"]["subject_status"] = subject_status

                # Check for opt-outs
                ccpa_opt_outs = subject_status.get("ccpa", {}).get("opt_outs", {})
                for opt_type, opt_info in ccpa_opt_outs.items():
                    if opt_info.get("opted_out"):
                        if action in ["share_with_third_party", "transfer_data_external"]:
                            results["blocking_issues"].append({
                                "domain": "ccpa",
                                "issue": f"Consumer opted out of {opt_type}",
                                "action_required": "Honor opt-out preference",
                            })

        # 5. Regulatory requirements check
        reg_requirements = self.regulatory.get_cross_regulation_requirements(pii_types)
        results["applicable_regulations"] = reg_requirements.get("applicable_regulations", [])
        results["domain_results"]["regulatory_requirements"] = reg_requirements

        # Determine overall status
        if results["blocking_issues"]:
            results["overall_status"] = ComplianceStatus.NON_COMPLIANT.value
            results["permitted"] = False
        elif results["warnings"]:
            results["overall_status"] = ComplianceStatus.PARTIAL.value
            results["permitted"] = True
        else:
            results["overall_status"] = ComplianceStatus.COMPLIANT.value
            results["permitted"] = True

        # Calculate risk level
        results["risk_level"] = self._calculate_unified_risk(
            len(results["blocking_issues"]),
            len(results["warnings"]),
            pii_types,
            action,
        )

        # Add recommendations
        results["recommendations"] = self._generate_recommendations(results)

        # Record decision to memory for learning
        outcome = "blocked" if not results["permitted"] else (
            "warning" if results["warnings"] else "permitted"
        )
        reason = "; ".join([
            issue.get("issue", str(issue))
            for issue in results["blocking_issues"] + results["warnings"]
        ]) or "Compliant"

        decision_id = self.memory.record_decision(
            agent_id=agent_id,
            action=action,
            pii_types=pii_types,
            outcome=outcome,
            reason=reason[:500],  # Truncate long reasons
            regulations_involved=results.get("applicable_regulations", []),
            context=context,
        )
        results["decision_id"] = decision_id

        # Record to session if active
        if self.sessions.get_current_session():
            self.sessions.record_check(
                check_type="compliance",
                target=f"{agent_id}:{action}",
                result=results,
            )

        return results

    def _calculate_unified_risk(
        self,
        blocking_count: int,
        warning_count: int,
        pii_types: List[str],
        action: str,
    ) -> str:
        """Calculate unified risk level."""
        sensitive_pii = ["ssn", "health_record", "credit_card", "biometric", "genetic"]
        high_risk_actions = ["write_personal_data", "transfer_data_external", "automated_decision"]

        score = blocking_count * 5 + warning_count * 2

        for pii in pii_types:
            if pii in sensitive_pii:
                score += 3

        if action in high_risk_actions:
            score += 3

        if score >= 15:
            return CrossDomainRiskLevel.CRITICAL.value
        elif score >= 10:
            return CrossDomainRiskLevel.HIGH.value
        elif score >= 5:
            return CrossDomainRiskLevel.MEDIUM.value
        elif score >= 2:
            return CrossDomainRiskLevel.LOW.value
        else:
            return CrossDomainRiskLevel.MINIMAL.value

    def _generate_recommendations(self, results: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on compliance check results."""
        recommendations = []

        if results.get("blocking_issues"):
            recommendations.append("Resolve all blocking issues before proceeding")

        # Check for consent issues
        for issue in results.get("blocking_issues", []) + results.get("warnings", []):
            if "consent" in str(issue).lower():
                recommendations.append("Verify and document consent from data subject")
            if "opt-out" in str(issue).lower() or "opted out" in str(issue).lower():
                recommendations.append("Honor consumer opt-out preferences")
            if "encryption" in str(issue).lower():
                recommendations.append("Implement encryption for sensitive PII")

        # Check subject registration
        if results.get("data_subject_id"):
            subject_result = results.get("domain_results", {}).get("subject_status", {})
            if not subject_result.get("gdpr", {}).get("data_subject_id"):
                recommendations.append("Register data subject in GDPR system")
            if not subject_result.get("ccpa", {}).get("consumer_id"):
                recommendations.append("Register consumer in CCPA system")

        return list(set(recommendations))

    # =========================================================================
    # Subject Management
    # =========================================================================

    def register_subject(
        self,
        subject_id: str,
        email: str = "",
        name: str = "",
        jurisdiction: RegulationJurisdiction = RegulationJurisdiction.GLOBAL,
        gdpr_data_subject_id: Optional[str] = None,
        ccpa_consumer_id: Optional[str] = None,
    ) -> str:
        """Register a unified subject across regulations."""
        return self.subjects.create_unified_subject(
            subject_id=subject_id,
            gdpr_data_subject_id=gdpr_data_subject_id,
            ccpa_consumer_id=ccpa_consumer_id,
            jurisdiction=jurisdiction,
            email=email,
            name=name,
        )

    def sync_gdpr_subject(
        self,
        unified_subject_id: str,
        gdpr_data_subject_id: str,
    ) -> Dict[str, Any]:
        """Sync a unified subject with GDPR data subject."""
        result = self.subjects.link_gdpr_subject(unified_subject_id, gdpr_data_subject_id)

        # If GDPR governance is available, sync consent
        if self.gdpr:
            try:
                # Get GDPR consent status
                consents = self.gdpr.consent.get_consents_for_subject(gdpr_data_subject_id)
                for consent in consents:
                    self.subjects.update_consent_status(
                        subject_id=unified_subject_id,
                        consent_type=consent.get("purpose", "general"),
                        consented=consent.get("status") == "active",
                        source_regulation="gdpr",
                    )
            except Exception:
                pass

        return result

    def sync_ccpa_consumer(
        self,
        unified_subject_id: str,
        ccpa_consumer_id: str,
    ) -> Dict[str, Any]:
        """Sync a unified subject with CCPA consumer."""
        result = self.subjects.link_ccpa_consumer(unified_subject_id, ccpa_consumer_id)

        # If CCPA governance is available, sync opt-out status
        if self.ccpa:
            try:
                consumer = self.ccpa.consumers.get_consumer(ccpa_consumer_id)
                if consumer:
                    if consumer.get("opt_out_sale"):
                        self.subjects.update_opt_out_status(
                            subject_id=unified_subject_id,
                            opt_out_type="sale",
                            opted_out=True,
                            source_regulation="ccpa",
                        )
                    if consumer.get("opt_out_share"):
                        self.subjects.update_opt_out_status(
                            subject_id=unified_subject_id,
                            opt_out_type="share",
                            opted_out=True,
                            source_regulation="ccpa",
                        )
            except Exception:
                pass

        return result

    # =========================================================================
    # Agent PII Access
    # =========================================================================

    def grant_agent_pii_access(
        self,
        agent_id: str,
        pii_types: List[str],
        purpose: str,
        legal_basis: str = "",
        consent_verified: bool = False,
        expires_at: str = "",
    ) -> str:
        """Grant an agent access to specific PII types."""
        return self.agent_integration.register_agent_pii_access(
            agent_id=agent_id,
            pii_types=pii_types,
            purpose=purpose,
            legal_basis=legal_basis,
            consent_verified=consent_verified,
            expires_at=expires_at,
        )

    def check_agent_action(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_subject_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Quick check if an agent action is permitted."""
        result = self.check_compliance(
            agent_id=agent_id,
            action=action,
            pii_types=pii_types,
            data_subject_id=data_subject_id,
        )

        return {
            "permitted": result["permitted"],
            "status": result["overall_status"],
            "risk_level": result["risk_level"],
            "issues_count": len(result["blocking_issues"]) + len(result["warnings"]),
            "check_id": result["check_id"],
        }

    def record_agent_action(
        self,
        agent_id: str,
        action: str,
        pii_types: List[str],
        data_source: str,
        outcome: str,
        compliance_check_id: Optional[str] = None,
        data_subject_id: Optional[str] = None,
    ) -> str:
        """Record an agent action for audit purposes."""
        return self.agent_integration.record_agent_pii_action(
            agent_id=agent_id,
            action=action,
            pii_types=pii_types,
            data_source=data_source,
            outcome=outcome,
            compliance_check_id=compliance_check_id,
            data_subject_id=data_subject_id,
        )

    # =========================================================================
    # PII Discovery Integration
    # =========================================================================

    def discover_and_link_pii(
        self,
        source_id: str,
        fields: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Discover PII and automatically link to compliance requirements.

        Uses PII governance to detect and classify, then links to regulations.
        """
        if not self.pii:
            return {"error": "PII Governance not available"}

        # Discover and classify
        discovery = self.pii.discover_and_classify(
            source_id=source_id,
            fields=fields,
        )

        linked_items = []

        for classification in discovery.get("classifications", []):
            pii_type = classification.get("pii_type")

            # Link to compliance requirements
            link_result = self.pii_compliance.link_pii_to_compliance(
                pii_inventory_item_id=classification.get("inventory_id", ""),
                pii_type=pii_type,
                source_id=source_id,
                field_location=classification.get("field_id", ""),
                sensitivity_level=classification.get("sensitivity", "internal"),
                protection_status="unprotected",  # Default
            )

            linked_items.append({
                "pii_type": pii_type,
                "field": classification.get("field_name"),
                "applicable_regulations": link_result.get("applicable_regulations", []),
                "compliance_gaps": link_result.get("compliance_gaps", []),
                "risk_level": link_result.get("risk_level"),
            })

        return {
            "source_id": source_id,
            "fields_analyzed": discovery.get("fields_analyzed", 0),
            "pii_found": discovery.get("pii_found", 0),
            "linked_items": linked_items,
            "total_compliance_gaps": sum(
                len(item.get("compliance_gaps", [])) for item in linked_items
            ),
        }

    # =========================================================================
    # Reporting
    # =========================================================================

    def get_unified_report(self) -> Dict[str, Any]:
        """Get comprehensive governance report across all domains."""
        report = {
            "generated_at": self.regulatory._now(),
            "domains": {},
            "cross_domain": {},
        }

        # Integration store stats
        report["cross_domain"]["regulatory_bridge"] = self.regulatory.get_stats()
        report["cross_domain"]["pii_compliance"] = self.pii_compliance.get_stats()
        report["cross_domain"]["subject_unification"] = self.subjects.get_stats()
        report["cross_domain"]["agent_integration"] = self.agent_integration.get_stats()

        # Domain-specific stats
        if self.agent:
            try:
                report["domains"]["agent"] = self.agent.get_stats()
            except Exception:
                report["domains"]["agent"] = {"status": "unavailable"}

        if self.gdpr:
            try:
                report["domains"]["gdpr"] = self.gdpr.get_stats()
            except Exception:
                report["domains"]["gdpr"] = {"status": "unavailable"}

        if self.ccpa:
            try:
                report["domains"]["ccpa"] = self.ccpa.get_stats()
            except Exception:
                report["domains"]["ccpa"] = {"status": "unavailable"}

        if self.pii:
            try:
                pii_stats = {}
                pii_stats["classification"] = self.pii.classification.get_stats()
                pii_stats["inventory"] = self.pii.inventory.get_stats()
                pii_stats["risk"] = self.pii.risk.get_stats()
                pii_stats["lineage"] = self.pii.lineage.get_stats()
                report["domains"]["pii"] = pii_stats
            except Exception:
                report["domains"]["pii"] = {"status": "unavailable"}

        # Calculate overall health
        report["health"] = self._calculate_health(report)

        return report

    def _calculate_health(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate overall governance health."""
        scores = []

        # Check cross-domain stats
        pii_comp = report.get("cross_domain", {}).get("pii_compliance", {})
        risk_breakdown = pii_comp.get("risk_level_breakdown", {})

        # Penalty for high-risk items
        critical = risk_breakdown.get("critical", 0)
        high = risk_breakdown.get("high", 0)

        base_score = 100
        base_score -= critical * 10
        base_score -= high * 5

        # Penalty for compliance gaps
        gaps = pii_comp.get("total_compliance_gaps", 0)
        base_score -= gaps * 2

        # Cap at 0-100
        base_score = max(0, min(100, base_score))

        return {
            "overall_score": base_score,
            "status": "healthy" if base_score >= 80 else "warning" if base_score >= 50 else "critical",
            "critical_items": critical,
            "high_risk_items": high,
            "compliance_gaps": gaps,
        }

    def get_executive_summary(self) -> str:
        """Get executive summary of unified governance status."""
        report = self.get_unified_report()
        health = report.get("health", {})

        lines = [
            "=" * 60,
            "UNIFIED GOVERNANCE EXECUTIVE SUMMARY",
            "=" * 60,
            "",
            f"Overall Health Score: {health.get('overall_score', 0)}/100",
            f"Status: {health.get('status', 'unknown').upper()}",
            "",
            "Cross-Domain Metrics:",
            "-" * 40,
        ]

        # Subject unification
        subj = report.get("cross_domain", {}).get("subject_unification", {})
        lines.append(f"  Unified Subjects: {subj.get('total_unified_subjects', 0)}")
        lines.append(f"  GDPR Linked: {subj.get('gdpr_linked', 0)}")
        lines.append(f"  CCPA Linked: {subj.get('ccpa_linked', 0)}")

        # Agent integration
        agent = report.get("cross_domain", {}).get("agent_integration", {})
        lines.append(f"  Agent PII Access Grants: {agent.get('total_pii_access_grants', 0)}")
        lines.append(f"  Action Checks: {agent.get('total_action_checks', 0)}")
        lines.append(f"  Active Blocks: {agent.get('active_blocks', 0)}")

        # PII compliance
        pii = report.get("cross_domain", {}).get("pii_compliance", {})
        lines.append(f"  PII Compliance Links: {pii.get('total_pii_compliance_links', 0)}")
        lines.append(f"  Compliance Gaps: {pii.get('total_compliance_gaps', 0)}")

        lines.append("")
        lines.append("Domain Status:")
        lines.append("-" * 40)

        for domain, stats in report.get("domains", {}).items():
            status = "Available" if stats.get("status") != "unavailable" else "Unavailable"
            lines.append(f"  {domain.upper()}: {status}")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    # =========================================================================
    # Persistence
    # =========================================================================

    def save(self, path: str) -> None:
        """Save unified governance graph to file."""
        self.graph.save(path)

    @classmethod
    def load(cls, path: str) -> "UnifiedGovernanceEngine":
        """Load unified governance from file."""
        graph = ISONGraph()
        graph.load(path)
        engine = cls(graph=graph)
        return engine


def quick_unified_governance(
    name: str = "unified",
    setup_defaults: bool = True,
) -> UnifiedGovernanceEngine:
    """Quick setup for unified governance."""
    engine = UnifiedGovernanceEngine(name=name)

    if setup_defaults:
        # Register common regulations
        engine.regulatory.register_regulation(
            regulation_id="gdpr",
            name="General Data Protection Regulation",
            jurisdiction=RegulationJurisdiction.EU,
            description="EU data protection regulation",
            effective_date="2018-05-25",
        )

        engine.regulatory.register_regulation(
            regulation_id="ccpa",
            name="California Consumer Privacy Act",
            jurisdiction=RegulationJurisdiction.US_CALIFORNIA,
            description="California privacy law",
            effective_date="2020-01-01",
        )

        engine.regulatory.register_regulation(
            regulation_id="hipaa",
            name="Health Insurance Portability and Accountability Act",
            jurisdiction=RegulationJurisdiction.US_FEDERAL,
            description="US health data privacy",
            effective_date="1996-08-21",
        )

        engine.regulatory.register_regulation(
            regulation_id="pci_dss",
            name="Payment Card Industry Data Security Standard",
            jurisdiction=RegulationJurisdiction.GLOBAL,
            description="Payment card data security",
            effective_date="2004-12-15",
        )

    return engine
