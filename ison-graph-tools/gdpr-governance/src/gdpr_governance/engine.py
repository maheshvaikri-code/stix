"""
GDPR Governance Engine
======================

Main engine for comprehensive GDPR compliance management.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime

from ison_graph import ISONGraph

from .stores import (
    DataSubjectStore,
    ProcessingActivityStore,
    ConsentStore,
    DataSubjectRightsStore,
    DataBreachStore,
    DPIAStore,
    InternationalTransferStore,
)
from .schema import (
    LawfulBasis, PersonalDataCategory, ConsentType, ConsentStatus,
    DataSubjectRight, BreachSeverity, DPIAStatus, TransferMechanism,
    ActorRole, ComplianceStatus
)


class GDPRGovernance:
    """
    GDPR Compliance Governance Engine.

    Provides unified access to all GDPR governance stores and
    compliance reporting capabilities.

    Usage:
        from ison_graph import ISONGraph
        from gdpr_governance import GDPRGovernance

        graph = ISONGraph()
        gdpr = GDPRGovernance(graph)

        # Register processing activities
        activity_id = gdpr.processing.register_activity(...)

        # Manage consent
        consent_id = gdpr.consent.record_consent(...)

        # Handle data subject requests
        request_id = gdpr.rights.submit_request(...)

        # Generate compliance report
        report = gdpr.get_compliance_status()
    """

    def __init__(self, graph: ISONGraph):
        """
        Initialize GDPR Governance engine.

        Args:
            graph: ISONGraph instance to use as backend
        """
        self.graph = graph

        # Initialize all stores
        self.data_subjects = DataSubjectStore(graph)
        self.processing = ProcessingActivityStore(graph)
        self.consent = ConsentStore(graph)
        self.rights = DataSubjectRightsStore(graph)
        self.breach = DataBreachStore(graph)
        self.dpia = DPIAStore(graph)
        self.transfer = InternationalTransferStore(graph)

    # =========================================================================
    # Organization Setup
    # =========================================================================

    def register_organization(
        self,
        name: str,
        organization_type: str = "controller",
        country: str = "",
        dpo_name: str = "",
        dpo_email: str = "",
        registration_number: str = "",
    ) -> str:
        """
        Register the organization (controller/processor).

        Args:
            name: Organization name
            organization_type: "controller" or "processor"
            country: Country of establishment
            dpo_name: Data Protection Officer name
            dpo_email: DPO contact email
            registration_number: Company registration number

        Returns:
            Organization ID
        """
        org_id = f"org_{name.lower().replace(' ', '_')}"

        self.graph.add_node(
            "organization",
            org_id,
            name=name,
            organization_type=organization_type,
            country=country,
            dpo_name=dpo_name,
            dpo_email=dpo_email,
            registration_number=registration_number,
            created_at=datetime.now().isoformat(),
        )

        return org_id

    def register_controller(
        self,
        controller_id: str,
        name: str,
        contact: str = "",
        dpo_name: str = "",
    ) -> str:
        """Register a data controller"""
        self.graph.add_node(
            "controller",
            controller_id,
            name=name,
            contact=contact,
            dpo_name=dpo_name,
            created_at=datetime.now().isoformat(),
        )
        return controller_id

    def register_processor(
        self,
        processor_id: str,
        name: str,
        controller_id: str,
        contract_date: str = "",
        services: str = "",
    ) -> str:
        """Register a data processor"""
        self.graph.add_node(
            "processor",
            processor_id,
            name=name,
            controller_id=controller_id,
            contract_date=contract_date,
            services=services,
            created_at=datetime.now().isoformat(),
        )

        if self.graph.has_node("controller", controller_id):
            self.graph.add_edge(
                "PROCESSES_FOR",
                ("processor", processor_id),
                ("controller", controller_id),
            )

        return processor_id

    # =========================================================================
    # Compliance Reporting
    # =========================================================================

    def get_compliance_status(self, organization_id: str = "") -> Dict[str, Any]:
        """
        Generate comprehensive GDPR compliance status report.

        Returns:
            Compliance status with metrics and issues
        """
        # Gather stats from all stores
        processing_stats = self.processing.get_stats()
        consent_stats = self.consent.get_stats()
        rights_stats = self.rights.get_stats()
        breach_stats = self.breach.get_stats()
        dpia_stats = self.dpia.get_stats()
        transfer_stats = self.transfer.get_stats()
        subject_stats = self.data_subjects.get_stats()

        # Identify compliance issues
        issues = self._identify_compliance_issues(
            processing_stats,
            consent_stats,
            rights_stats,
            breach_stats,
            dpia_stats,
            transfer_stats,
        )

        # Calculate compliance score
        score = self._calculate_compliance_score(
            processing_stats,
            rights_stats,
            breach_stats,
            dpia_stats,
            transfer_stats,
        )

        return {
            "organization_id": organization_id,
            "generated_at": datetime.now().isoformat(),
            "compliance_score": score,
            "summary": {
                "processing_activities": processing_stats["total_activities"],
                "active_processing": processing_stats["active_activities"],
                "data_subjects": subject_stats["total_subjects"],
                "active_consents": consent_stats["active_consents"],
                "pending_requests": rights_stats["pending_requests"],
                "overdue_requests": rights_stats["overdue_requests"],
                "open_breaches": breach_stats["open_breaches"],
                "dpias_required": dpia_stats.get("by_status", {}).get("required", 0),
                "dpias_completed": dpia_stats.get("by_status", {}).get("completed", 0),
                "active_transfers": transfer_stats["active_transfers"],
            },
            "issues": issues,
            "detailed_stats": {
                "processing": processing_stats,
                "consent": consent_stats,
                "rights": rights_stats,
                "breach": breach_stats,
                "dpia": dpia_stats,
                "transfer": transfer_stats,
                "subjects": subject_stats,
            },
        }

    def _identify_compliance_issues(
        self,
        processing_stats: Dict,
        consent_stats: Dict,
        rights_stats: Dict,
        breach_stats: Dict,
        dpia_stats: Dict,
        transfer_stats: Dict,
    ) -> List[Dict[str, Any]]:
        """Identify compliance issues across all areas"""
        issues = []

        # Check for overdue DSR requests
        if rights_stats.get("overdue_requests", 0) > 0:
            issues.append({
                "severity": "critical",
                "area": "data_subject_rights",
                "issue": f"{rights_stats['overdue_requests']} data subject requests are overdue",
                "article": "Article 12(3)",
                "action": "Complete overdue requests immediately",
            })

        # Check for open breaches
        if breach_stats.get("open_breaches", 0) > 0:
            issues.append({
                "severity": "high",
                "area": "breach_management",
                "issue": f"{breach_stats['open_breaches']} data breaches are still open",
                "article": "Articles 33-34",
                "action": "Review and close open breaches",
            })

        # Check for required but incomplete DPIAs
        required_dpias = dpia_stats.get("by_status", {}).get("required", 0)
        in_progress = dpia_stats.get("by_status", {}).get("in_progress", 0)
        if required_dpias > 0:
            issues.append({
                "severity": "high",
                "area": "dpia",
                "issue": f"{required_dpias} DPIAs are required but not started",
                "article": "Article 35",
                "action": "Start required DPIAs",
            })

        # Check for DPIAs due for review
        if dpia_stats.get("due_for_review", 0) > 0:
            issues.append({
                "severity": "medium",
                "area": "dpia",
                "issue": f"{dpia_stats['due_for_review']} DPIAs are due for review",
                "article": "Article 35(11)",
                "action": "Review and update DPIAs",
            })

        # Check for transfers pending TIA
        if transfer_stats.get("pending_tia", 0) > 0:
            issues.append({
                "severity": "high",
                "area": "international_transfers",
                "issue": f"{transfer_stats['pending_tia']} transfers need Transfer Impact Assessment",
                "article": "Articles 44-49 (Schrems II)",
                "action": "Complete TIAs for transfers",
            })

        # Check for processing activities requiring DPIA
        if processing_stats.get("dpia_required", 0) > dpia_stats.get("total_dpias", 0):
            issues.append({
                "severity": "medium",
                "area": "processing_activities",
                "issue": "Some processing activities may lack required DPIAs",
                "article": "Article 35",
                "action": "Review processing activities for DPIA coverage",
            })

        # Check consent withdrawal rate
        total_consents = consent_stats.get("total_consents", 0)
        withdrawn = consent_stats.get("withdrawn_consents", 0)
        if total_consents > 0 and withdrawn / total_consents > 0.3:
            issues.append({
                "severity": "low",
                "area": "consent",
                "issue": f"High consent withdrawal rate ({withdrawn}/{total_consents})",
                "article": "Article 7",
                "action": "Review consent practices and user experience",
            })

        return issues

    def _calculate_compliance_score(
        self,
        processing_stats: Dict,
        rights_stats: Dict,
        breach_stats: Dict,
        dpia_stats: Dict,
        transfer_stats: Dict,
    ) -> float:
        """
        Calculate overall compliance score (0-100).

        Scoring:
        - DSR response timeliness: 30 points
        - Breach management: 20 points
        - DPIA coverage: 20 points
        - Transfer compliance: 15 points
        - Documentation: 15 points
        """
        score = 100.0

        # Penalize for overdue requests (up to -30 points)
        overdue = rights_stats.get("overdue_requests", 0)
        pending = rights_stats.get("pending_requests", 0)
        if pending > 0:
            overdue_ratio = overdue / max(pending, 1)
            score -= min(30, overdue_ratio * 30)

        # Penalize for open breaches (up to -20 points)
        open_breaches = breach_stats.get("open_breaches", 0)
        if open_breaches > 0:
            score -= min(20, open_breaches * 5)

        # Penalize for missing DPIAs (up to -20 points)
        required_dpias = dpia_stats.get("by_status", {}).get("required", 0)
        if required_dpias > 0:
            score -= min(20, required_dpias * 5)

        # Penalize for pending TIAs (up to -15 points)
        pending_tia = transfer_stats.get("pending_tia", 0)
        if pending_tia > 0:
            score -= min(15, pending_tia * 5)

        # Reward for documented activities (up to +15 bonus, max 100)
        activities = processing_stats.get("total_activities", 0)
        if activities > 0:
            score = min(100, score + min(15, activities))

        return max(0, round(score, 1))

    # =========================================================================
    # Quick Operations
    # =========================================================================

    def handle_erasure_request(
        self,
        data_subject_id: str,
        reason: str = "erasure_request",
    ) -> Dict[str, Any]:
        """
        Handle a right to erasure request (Article 17).

        Coordinates across stores to:
        1. Record the DSR request
        2. Delete personal data
        3. Update consent records
        """
        # Submit the request
        request_id = self.rights.submit_request(
            data_subject_id=data_subject_id,
            right_type=DataSubjectRight.ERASURE,
            details=reason,
        )

        # Delete personal data
        deletion_result = self.data_subjects.delete_subject_data(
            subject_id=data_subject_id,
            reason=reason,
        )

        # Withdraw all consents
        consents = self.consent.get_subject_consents(
            data_subject_id=data_subject_id,
            status=ConsentStatus.GIVEN,
        )
        for consent in consents:
            self.consent.withdraw_consent(
                consent_id=consent["id"],
                reason="erasure_request",
            )

        # Complete the request
        self.rights.complete_request(
            request_id=request_id,
            response="Personal data erased per Article 17 request",
            actions_taken=[
                f"Deleted {deletion_result['deleted_count']} data categories",
                f"Withdrew {len(consents)} consent records",
            ],
        )

        return {
            "request_id": request_id,
            "data_subject_id": data_subject_id,
            "deleted_categories": deletion_result["deleted_count"],
            "withdrawn_consents": len(consents),
            "status": "completed",
        }

    def handle_access_request(
        self,
        data_subject_id: str,
    ) -> Dict[str, Any]:
        """
        Handle a right of access request (Article 15).

        Collects all data about a subject.
        """
        # Submit the request
        request_id = self.rights.submit_request(
            data_subject_id=data_subject_id,
            right_type=DataSubjectRight.ACCESS,
        )

        # Gather all data
        subject = self.data_subjects.get_subject(data_subject_id)
        inventory = self.data_subjects.get_subject_data_inventory(data_subject_id)
        consents = self.consent.get_subject_consents(data_subject_id)
        requests = self.rights.get_subject_requests(data_subject_id)

        # Find related processing activities
        processing_activities = []
        for node in self.graph.nodes():
            if node.type == "processing_activity":
                subjects = node.properties.get("data_subjects", "")
                if data_subject_id in subjects:
                    processing_activities.append({
                        "id": node.id,
                        "name": node.properties.get("name"),
                        "purpose": node.properties.get("purpose"),
                    })

        response_data = {
            "subject_info": subject,
            "data_inventory": inventory,
            "consents": consents,
            "processing_activities": processing_activities,
            "previous_requests": requests,
        }

        # Complete the request
        self.rights.complete_request(
            request_id=request_id,
            response="Access request fulfilled",
            actions_taken=[
                f"Collected {len(inventory)} data categories",
                f"Included {len(consents)} consent records",
                f"Listed {len(processing_activities)} processing activities",
            ],
        )

        return {
            "request_id": request_id,
            "data_subject_id": data_subject_id,
            "data": response_data,
            "status": "completed",
        }

    def report_and_assess_breach(
        self,
        description: str,
        data_categories: List[PersonalDataCategory],
        subjects_affected: int,
        severity: BreachSeverity,
    ) -> Dict[str, Any]:
        """
        Quick method to report and assess a breach.

        Determines notification requirements based on severity.
        """
        from .schema import BreachType

        # Report the breach
        breach_id = self.breach.report_breach(
            description=description,
            breach_type=BreachType.CONFIDENTIALITY,
        )

        # Update investigation
        self.breach.update_investigation(
            breach_id=breach_id,
            data_categories=data_categories,
            subjects_affected_count=subjects_affected,
        )

        # Assess severity and notification requirements
        # Art 33: Always notify DPA unless unlikely to result in risk
        # Art 34: Notify subjects if high risk
        dpa_required = severity != BreachSeverity.LOW
        subject_required = severity in {BreachSeverity.HIGH, BreachSeverity.CRITICAL}

        self.breach.assess_severity(
            breach_id=breach_id,
            severity=severity,
            risk_assessment=f"Severity: {severity.value}, Subjects: {subjects_affected}",
            dpa_notification_required=dpa_required,
            subject_notification_required=subject_required,
        )

        return {
            "breach_id": breach_id,
            "severity": severity.value,
            "dpa_notification_required": dpa_required,
            "subject_notification_required": subject_required,
            "subjects_affected": subjects_affected,
            "72_hour_deadline": self.breach.get_breach(breach_id).get("dpa_deadline"),
        }

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def export_ropa(self) -> List[Dict[str, Any]]:
        """
        Export Records of Processing Activities (Article 30).

        Returns format suitable for regulatory submission.
        """
        activities = self.processing.list_activities()

        ropa = []
        for activity in activities:
            ropa.append({
                "name": activity.get("name"),
                "purpose": activity.get("purpose"),
                "lawful_basis": activity.get("lawful_basis"),
                "data_categories": activity.get("data_categories"),
                "data_subjects": activity.get("data_subjects"),
                "recipients": activity.get("recipients"),
                "retention_period": activity.get("retention_period"),
                "security_measures": activity.get("security_measures"),
                "international_transfers": activity.get("transfer_countries", []),
                "dpia_required": activity.get("dpia_required"),
            })

        return ropa

    def get_subject_dashboard(self, data_subject_id: str) -> Dict[str, Any]:
        """
        Get a dashboard view for a data subject.

        Useful for privacy portals.
        """
        return {
            "profile": self.data_subjects.get_subject(data_subject_id),
            "data_inventory": self.data_subjects.get_subject_data_inventory(data_subject_id),
            "active_consents": self.consent.get_subject_consents(
                data_subject_id, ConsentStatus.GIVEN
            ),
            "pending_requests": self.rights.get_subject_requests(
                data_subject_id
            ),
        }
