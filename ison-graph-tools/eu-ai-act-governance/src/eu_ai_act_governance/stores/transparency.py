"""
Transparency Store
==================

Manages transparency requirements per Articles 13 and 50.
Tracks user notifications, AI interaction disclosures, and information provision.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import TransparencyObligation, DisclosureStatus, AIRiskLevel

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class TransparencyStore(BaseStore):
    """Store for transparency requirement management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "transparency")

    # =========================================================================
    # Transparency Configuration
    # =========================================================================

    def configure_transparency(
        self,
        system_id: str,
        risk_level: AIRiskLevel,
        applicable_obligations: List[TransparencyObligation],
        config_id: Optional[str] = None
    ) -> str:
        """Configure transparency requirements for a system"""
        cid = config_id or self._generate_id("tc")

        props = {
            "system_id": system_id,
            "risk_level": risk_level.value,
            "obligations": [o.value for o in applicable_obligations],
            "status": "configured",
            "created_at": self._now(),
            "description": f"Transparency config for {system_id}"
        }
        return self._add_node("transparency_config", cid, props)

    def get_transparency_config(self, config_id: str) -> Optional[Dict[str, Any]]:
        """Get transparency configuration by ID"""
        return self._get_node("transparency_config", config_id)

    def get_system_transparency(self, system_id: str) -> Optional[Dict[str, Any]]:
        """Get transparency configuration for a system"""
        configs = self._find_nodes("transparency_config", system_id=system_id)
        return configs[0] if configs else None

    # =========================================================================
    # AI Interaction Disclosure (Art. 50)
    # =========================================================================

    def create_disclosure_template(
        self,
        system_id: str,
        disclosure_type: str,  # ai_interaction, emotion_recognition, biometric_categorization, deepfake
        content: str,
        format_type: str,  # text, audio, visual, multimodal
        language: str,
        placement: str,
        template_id: Optional[str] = None
    ) -> str:
        """Create a disclosure template"""
        tid = template_id or self._generate_id("dt")
        props = {
            "system_id": system_id,
            "disclosure_type": disclosure_type,
            "content": content,
            "format": format_type,
            "language": language,
            "placement": placement,
            "status": DisclosureStatus.DRAFT.value,
            "created_at": self._now(),
            "description": f"Disclosure template: {disclosure_type}"
        }
        return self._add_node("disclosure_template", tid, props)

    def approve_disclosure_template(
        self,
        template_id: str,
        approved_by: str,
        review_notes: str = ""
    ):
        """Approve a disclosure template"""
        self._update_node("disclosure_template", template_id, {
            "status": DisclosureStatus.APPROVED.value,
            "approved_by": approved_by,
            "approved_at": self._now(),
            "review_notes": review_notes
        })

    def deploy_disclosure(
        self,
        template_id: str,
        deployed_by: str,
        deployment_location: str
    ):
        """Deploy a disclosure"""
        self._update_node("disclosure_template", template_id, {
            "status": DisclosureStatus.DEPLOYED.value,
            "deployed_by": deployed_by,
            "deployment_location": deployment_location,
            "deployed_at": self._now()
        })

    def get_disclosures(
        self,
        system_id: str,
        status: Optional[DisclosureStatus] = None
    ) -> List[Dict[str, Any]]:
        """Get disclosures for a system"""
        disclosures = self._find_nodes("disclosure_template", system_id=system_id)
        if status:
            disclosures = [d for d in disclosures if d.get("status") == status.value]
        return disclosures

    # =========================================================================
    # Instructions for Use (Art. 13)
    # =========================================================================

    def create_instructions(
        self,
        system_id: str,
        version: str,
        author: str,
        instructions_id: Optional[str] = None
    ) -> str:
        """Create instructions for use document"""
        iid = instructions_id or self._generate_id("ifu")

        # Required sections per Art. 13(3)
        sections = [
            {"name": "provider_identity", "status": "pending", "content": None},
            {"name": "system_characteristics", "status": "pending", "content": None},
            {"name": "intended_purpose", "status": "pending", "content": None},
            {"name": "performance_levels", "status": "pending", "content": None},
            {"name": "known_limitations", "status": "pending", "content": None},
            {"name": "human_oversight_measures", "status": "pending", "content": None},
            {"name": "expected_lifetime", "status": "pending", "content": None},
            {"name": "maintenance_requirements", "status": "pending", "content": None},
            {"name": "logging_capabilities", "status": "pending", "content": None},
        ]

        props = {
            "system_id": system_id,
            "version": version,
            "author": author,
            "sections": sections,
            "status": "draft",
            "completeness": 0,
            "created_at": self._now(),
            "description": f"Instructions for use: {system_id} v{version}"
        }
        return self._add_node("instructions_for_use", iid, props)

    def update_instruction_section(
        self,
        instructions_id: str,
        section_name: str,
        content: str,
        updated_by: str
    ):
        """Update a section of the instructions"""
        instructions = self._get_node("instructions_for_use", instructions_id)
        if not instructions:
            return

        sections = instructions.get("sections", [])
        for section in sections:
            if section["name"] == section_name:
                section["status"] = "completed"
                section["content"] = content
                section["updated_by"] = updated_by
                section["updated_at"] = self._now()
                break

        # Calculate completeness
        completed = len([s for s in sections if s["status"] == "completed"])
        completeness = round((completed / len(sections)) * 100) if sections else 0

        self._update_node("instructions_for_use", instructions_id, {
            "sections": sections,
            "completeness": completeness,
            "last_updated": self._now()
        })

    def finalize_instructions(
        self,
        instructions_id: str,
        finalized_by: str
    ) -> Dict[str, Any]:
        """Finalize instructions for use"""
        instructions = self._get_node("instructions_for_use", instructions_id)
        if not instructions:
            return {"error": "Instructions not found"}

        sections = instructions.get("sections", [])
        incomplete = [s["name"] for s in sections if s["status"] != "completed"]

        if incomplete:
            return {
                "success": False,
                "reason": "incomplete_sections",
                "incomplete": incomplete
            }

        self._update_node("instructions_for_use", instructions_id, {
            "status": "finalized",
            "finalized_by": finalized_by,
            "finalized_at": self._now()
        })

        return {"success": True, "instructions_id": instructions_id}

    def get_instructions(self, system_id: str) -> List[Dict[str, Any]]:
        """Get instructions for a system"""
        return self._find_nodes("instructions_for_use", system_id=system_id)

    # =========================================================================
    # User Notifications
    # =========================================================================

    def create_notification(
        self,
        system_id: str,
        notification_type: str,  # ai_generated_content, synthetic_media, emotion_inference
        target_audience: str,  # users, public, deployers
        content: str,
        delivery_method: str,  # in_app, email, label, watermark
        notification_id: Optional[str] = None
    ) -> str:
        """Create a user notification"""
        nid = notification_id or self._generate_id("un")
        props = {
            "system_id": system_id,
            "notification_type": notification_type,
            "target_audience": target_audience,
            "content": content,
            "delivery_method": delivery_method,
            "status": "created",
            "created_at": self._now(),
            "description": f"User notification: {notification_type}"
        }
        return self._add_node("user_notification", nid, props)

    def deploy_notification(
        self,
        notification_id: str,
        deployed_by: str
    ):
        """Deploy a notification"""
        self._update_node("user_notification", notification_id, {
            "status": "deployed",
            "deployed_by": deployed_by,
            "deployed_at": self._now()
        })

    def record_notification_delivery(
        self,
        notification_id: str,
        user_id: str,
        acknowledged: bool,
        delivery_id: Optional[str] = None
    ) -> str:
        """Record delivery of a notification to a user"""
        did = delivery_id or self._generate_id("nd")
        props = {
            "notification_id": notification_id,
            "user_id": user_id,
            "acknowledged": acknowledged,
            "delivered_at": self._now(),
            "description": f"Notification delivery to {user_id}"
        }
        return self._add_node("notification_delivery", did, props)

    def get_notification_stats(
        self,
        notification_id: str
    ) -> Dict[str, Any]:
        """Get notification delivery statistics"""
        deliveries = self._find_nodes("notification_delivery", notification_id=notification_id)
        total = len(deliveries)
        acknowledged = len([d for d in deliveries if d.get("acknowledged")])

        return {
            "notification_id": notification_id,
            "total_deliveries": total,
            "acknowledged": acknowledged,
            "acknowledgment_rate": round((acknowledged / total) * 100) if total > 0 else 0
        }

    # =========================================================================
    # Synthetic Media Labeling (Art. 50(4))
    # =========================================================================

    def register_synthetic_content(
        self,
        system_id: str,
        content_type: str,  # image, audio, video, text
        content_hash: str,
        creation_method: str,
        labeling_method: str,  # watermark, metadata, visible_label
        content_id: Optional[str] = None
    ) -> str:
        """Register synthetic/deepfake content"""
        cid = content_id or self._generate_id("sc")
        props = {
            "system_id": system_id,
            "content_type": content_type,
            "content_hash": content_hash,
            "creation_method": creation_method,
            "labeling_method": labeling_method,
            "labeled": False,
            "created_at": self._now(),
            "description": f"Synthetic content: {content_type}"
        }
        return self._add_node("synthetic_content", cid, props)

    def apply_label(
        self,
        content_id: str,
        label_type: str,
        label_data: str,
        applied_by: str
    ):
        """Apply label to synthetic content"""
        self._update_node("synthetic_content", content_id, {
            "labeled": True,
            "label_type": label_type,
            "label_data": label_data,
            "labeled_by": applied_by,
            "labeled_at": self._now()
        })

    def verify_label(
        self,
        content_id: str,
        verified_by: str,
        verification_method: str,
        valid: bool
    ):
        """Verify content labeling"""
        self._update_node("synthetic_content", content_id, {
            "label_verified": True,
            "verification_method": verification_method,
            "label_valid": valid,
            "verified_by": verified_by,
            "verified_at": self._now()
        })

    # =========================================================================
    # Transparency Obligation Tracking
    # =========================================================================

    def track_obligation(
        self,
        system_id: str,
        obligation: TransparencyObligation,
        responsible_party: str,
        deadline: Optional[str] = None,
        obligation_id: Optional[str] = None
    ) -> str:
        """Track a transparency obligation"""
        oid = obligation_id or self._generate_id("to")
        props = {
            "system_id": system_id,
            "obligation": obligation.value,
            "responsible_party": responsible_party,
            "deadline": deadline,
            "status": "pending",
            "created_at": self._now(),
            "description": f"Transparency obligation: {obligation.value}"
        }
        return self._add_node("transparency_obligation", oid, props)

    def fulfill_obligation(
        self,
        obligation_id: str,
        evidence: str,
        fulfilled_by: str
    ):
        """Mark obligation as fulfilled"""
        self._update_node("transparency_obligation", obligation_id, {
            "status": "fulfilled",
            "evidence": evidence,
            "fulfilled_by": fulfilled_by,
            "fulfilled_at": self._now()
        })

    def get_obligations_status(
        self,
        system_id: str
    ) -> Dict[str, Any]:
        """Get transparency obligations status"""
        obligations = self._find_nodes("transparency_obligation", system_id=system_id)

        total = len(obligations)
        fulfilled = len([o for o in obligations if o.get("status") == "fulfilled"])
        pending = len([o for o in obligations if o.get("status") == "pending"])

        return {
            "system_id": system_id,
            "total_obligations": total,
            "fulfilled": fulfilled,
            "pending": pending,
            "compliance_rate": round((fulfilled / total) * 100) if total > 0 else 0
        }

    # =========================================================================
    # Information Requests
    # =========================================================================

    def record_information_request(
        self,
        system_id: str,
        requester: str,
        requester_type: str,  # user, authority, auditor
        information_requested: str,
        request_id: Optional[str] = None
    ) -> str:
        """Record an information request"""
        rid = request_id or self._generate_id("ir")
        props = {
            "system_id": system_id,
            "requester": requester,
            "requester_type": requester_type,
            "information_requested": information_requested,
            "status": "received",
            "received_at": self._now(),
            "description": f"Information request from {requester}"
        }
        return self._add_node("information_request", rid, props)

    def respond_to_request(
        self,
        request_id: str,
        response: str,
        responded_by: str,
        attachments: Optional[List[str]] = None
    ):
        """Respond to an information request"""
        self._update_node("information_request", request_id, {
            "status": "responded",
            "response": response,
            "responded_by": responded_by,
            "attachments": attachments or [],
            "responded_at": self._now()
        })

    def get_pending_requests(self, system_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get pending information requests"""
        requests = self._find_nodes("information_request", status="received")
        if system_id:
            requests = [r for r in requests if r.get("system_id") == system_id]
        return requests

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get transparency statistics"""
        base_stats = super().get_stats()
        configs = self._find_nodes("transparency_config")
        disclosures = self._find_nodes("disclosure_template")
        instructions = self._find_nodes("instructions_for_use")
        notifications = self._find_nodes("user_notification")
        synthetic = self._find_nodes("synthetic_content")
        obligations = self._find_nodes("transparency_obligation")
        requests = self._find_nodes("information_request")

        return {
            **base_stats,
            "transparency_configs": len(configs),
            "disclosure_templates": len(disclosures),
            "deployed_disclosures": len([d for d in disclosures if d.get("status") == DisclosureStatus.DEPLOYED.value]),
            "instructions_documents": len(instructions),
            "finalized_instructions": len([i for i in instructions if i.get("status") == "finalized"]),
            "user_notifications": len(notifications),
            "deployed_notifications": len([n for n in notifications if n.get("status") == "deployed"]),
            "synthetic_content_registered": len(synthetic),
            "labeled_content": len([s for s in synthetic if s.get("labeled")]),
            "total_obligations": len(obligations),
            "fulfilled_obligations": len([o for o in obligations if o.get("status") == "fulfilled"]),
            "information_requests": len(requests),
            "pending_requests": len([r for r in requests if r.get("status") == "received"])
        }
