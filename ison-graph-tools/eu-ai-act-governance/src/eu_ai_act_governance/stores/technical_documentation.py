"""
Technical Documentation Store
=============================

Manages technical documentation requirements per Article 11 and Annex IV.
Tracks documentation completeness, updates, and authority access.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import DocumentationType

if TYPE_CHECKING:
    from ison_graph import ISONGraph


# Annex IV documentation requirements
ANNEX_IV_REQUIREMENTS = {
    DocumentationType.GENERAL_DESCRIPTION: {
        "section": "1",
        "title": "General description of the AI system",
        "requirements": [
            "Intended purpose",
            "Provider identity and contact",
            "Version and release date",
            "Interaction with hardware/software",
            "Versions of relevant software/firmware",
            "Forms in which the system is placed on market"
        ]
    },
    DocumentationType.SYSTEM_ARCHITECTURE: {
        "section": "2",
        "title": "Detailed description of system elements and development process",
        "requirements": [
            "Methods and steps for system development",
            "Design specifications",
            "System architecture",
            "Computational resources used",
            "Main classification choices",
            "Trade-offs made"
        ]
    },
    DocumentationType.ALGORITHM_DESCRIPTION: {
        "section": "2(b)",
        "title": "Algorithm and model description",
        "requirements": [
            "Logic and algorithms",
            "Key design choices",
            "Main assumptions",
            "Key parameters",
            "Model architecture description"
        ]
    },
    DocumentationType.DATA_REQUIREMENTS: {
        "section": "2(d)",
        "title": "Data requirements",
        "requirements": [
            "Training methodologies and techniques",
            "Training data sets description",
            "Data provenance",
            "Data labeling procedures",
            "Data cleaning operations",
            "Data selection criteria"
        ]
    },
    DocumentationType.TRAINING_PROCESS: {
        "section": "2(e)",
        "title": "Training process documentation",
        "requirements": [
            "Training process and techniques",
            "Validation and testing data",
            "Metrics used for training",
            "Key decisions during training"
        ]
    },
    DocumentationType.TESTING_VALIDATION: {
        "section": "3",
        "title": "Testing and validation",
        "requirements": [
            "Validation and testing procedures",
            "Metrics used",
            "Test results",
            "Robustness testing",
            "Testing against specific persons/groups"
        ]
    },
    DocumentationType.PERFORMANCE_METRICS: {
        "section": "3(b)",
        "title": "Performance metrics",
        "requirements": [
            "Accuracy levels",
            "Robustness metrics",
            "Cybersecurity metrics",
            "Performance on specific groups"
        ]
    },
    DocumentationType.RISK_MANAGEMENT: {
        "section": "4",
        "title": "Risk management documentation",
        "requirements": [
            "Risk management system description",
            "Identified risks",
            "Risk management measures",
            "Residual risks"
        ]
    },
    DocumentationType.CHANGE_LOG: {
        "section": "5",
        "title": "Change log",
        "requirements": [
            "Description of all changes",
            "Impact assessment of changes",
            "Version control information"
        ]
    },
    DocumentationType.MONITORING_PLAN: {
        "section": "6",
        "title": "Post-market monitoring plan",
        "requirements": [
            "Post-market monitoring description",
            "Procedures for ongoing compliance",
            "Incident reporting procedures"
        ]
    }
}


class TechnicalDocumentationStore(BaseStore):
    """Store for technical documentation management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "technical_documentation")

    # =========================================================================
    # Documentation Package
    # =========================================================================

    def create_documentation_package(
        self,
        system_id: str,
        version: str,
        author: str,
        package_id: Optional[str] = None
    ) -> str:
        """Create a technical documentation package for a system"""
        pid = package_id or self._generate_id("tdp")

        # Initialize sections from Annex IV
        sections = []
        for doc_type, details in ANNEX_IV_REQUIREMENTS.items():
            sections.append({
                "type": doc_type.value,
                "section": details["section"],
                "title": details["title"],
                "requirements": details["requirements"],
                "status": "pending",
                "completeness": 0,
                "documents": []
            })

        props = {
            "system_id": system_id,
            "version": version,
            "author": author,
            "sections": sections,
            "status": "draft",
            "overall_completeness": 0,
            "created_at": self._now(),
            "last_updated": self._now(),
            "description": f"Technical documentation for {system_id} v{version}"
        }
        return self._add_node("documentation_package", pid, props)

    def get_documentation_package(self, package_id: str) -> Optional[Dict[str, Any]]:
        """Get documentation package by ID"""
        return self._get_node("documentation_package", package_id)

    def get_system_documentation(self, system_id: str) -> List[Dict[str, Any]]:
        """Get all documentation packages for a system"""
        return self._find_nodes("documentation_package", system_id=system_id)

    # =========================================================================
    # Document Management
    # =========================================================================

    def add_document(
        self,
        package_id: str,
        section_type: DocumentationType,
        document_title: str,
        document_ref: str,  # file path or external reference
        author: str,
        format_type: str = "pdf",  # pdf, markdown, html, docx
        document_id: Optional[str] = None
    ) -> str:
        """Add a document to a section"""
        did = document_id or self._generate_id("doc")
        props = {
            "package_id": package_id,
            "section_type": section_type.value,
            "title": document_title,
            "document_ref": document_ref,
            "author": author,
            "format": format_type,
            "version": "1.0",
            "status": "draft",
            "created_at": self._now(),
            "last_updated": self._now(),
            "description": f"Document: {document_title}"
        }
        self._add_node("technical_document", did, props)

        # Update package section
        package = self.get_documentation_package(package_id)
        if package:
            sections = package.get("sections", [])
            for section in sections:
                if section["type"] == section_type.value:
                    section["documents"].append(did)
                    section["status"] = "in_progress"
                    break
            self._update_node("documentation_package", package_id, {
                "sections": sections,
                "last_updated": self._now()
            })

        return did

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID"""
        return self._get_node("technical_document", document_id)

    def update_document(
        self,
        document_id: str,
        new_version: str,
        changes: str,
        updated_by: str,
        new_ref: Optional[str] = None
    ):
        """Update a document version"""
        doc = self.get_document(document_id)
        if not doc:
            return

        # Record version history
        history = doc.get("version_history", [])
        history.append({
            "version": doc.get("version"),
            "ref": doc.get("document_ref"),
            "updated_at": doc.get("last_updated"),
            "updated_by": doc.get("author")
        })

        updates = {
            "version": new_version,
            "changes": changes,
            "updated_by": updated_by,
            "last_updated": self._now(),
            "version_history": history
        }
        if new_ref:
            updates["document_ref"] = new_ref

        self._update_node("technical_document", document_id, updates)

    def approve_document(
        self,
        document_id: str,
        approved_by: str,
        approval_notes: str = ""
    ):
        """Approve a document"""
        self._update_node("technical_document", document_id, {
            "status": "approved",
            "approved_by": approved_by,
            "approved_at": self._now(),
            "approval_notes": approval_notes
        })

    # =========================================================================
    # Section Completion
    # =========================================================================

    def update_section_completeness(
        self,
        package_id: str,
        section_type: DocumentationType,
        completeness: int,  # 0-100
        reviewer: str,
        notes: str = ""
    ):
        """Update section completeness"""
        package = self.get_documentation_package(package_id)
        if not package:
            return

        sections = package.get("sections", [])
        for section in sections:
            if section["type"] == section_type.value:
                section["completeness"] = completeness
                section["status"] = "complete" if completeness >= 100 else "in_progress"
                section["reviewed_by"] = reviewer
                section["review_notes"] = notes
                section["reviewed_at"] = self._now()
                break

        # Calculate overall completeness
        total = sum(s.get("completeness", 0) for s in sections)
        overall = round(total / len(sections)) if sections else 0

        self._update_node("documentation_package", package_id, {
            "sections": sections,
            "overall_completeness": overall,
            "last_updated": self._now()
        })

    def get_section_status(
        self,
        package_id: str,
        section_type: DocumentationType
    ) -> Optional[Dict[str, Any]]:
        """Get status of a specific section"""
        package = self.get_documentation_package(package_id)
        if not package:
            return None

        for section in package.get("sections", []):
            if section["type"] == section_type.value:
                return section
        return None

    # =========================================================================
    # Requirements Tracking
    # =========================================================================

    def mark_requirement_met(
        self,
        package_id: str,
        section_type: DocumentationType,
        requirement: str,
        evidence_document_id: str,
        verified_by: str
    ) -> str:
        """Mark a specific requirement as met"""
        rid = self._generate_id("rm")
        props = {
            "package_id": package_id,
            "section_type": section_type.value,
            "requirement": requirement,
            "evidence_document_id": evidence_document_id,
            "verified_by": verified_by,
            "verified_at": self._now(),
            "status": "met",
            "description": f"Requirement met: {requirement[:50]}..."
        }
        return self._add_node("requirement_status", rid, props)

    def get_requirements_status(
        self,
        package_id: str,
        section_type: Optional[DocumentationType] = None
    ) -> List[Dict[str, Any]]:
        """Get requirements status"""
        reqs = self._find_nodes("requirement_status", package_id=package_id)
        if section_type:
            reqs = [r for r in reqs if r.get("section_type") == section_type.value]
        return reqs

    # =========================================================================
    # Authority Access
    # =========================================================================

    def grant_authority_access(
        self,
        package_id: str,
        authority_name: str,
        authority_type: str,  # market_surveillance, notified_body, member_state
        access_level: str,  # view, download, full
        granted_by: str,
        expires: Optional[str] = None
    ) -> str:
        """Grant authority access to documentation"""
        aid = self._generate_id("aa")
        props = {
            "package_id": package_id,
            "authority_name": authority_name,
            "authority_type": authority_type,
            "access_level": access_level,
            "granted_by": granted_by,
            "granted_at": self._now(),
            "expires": expires,
            "status": "active",
            "description": f"Authority access: {authority_name}"
        }
        return self._add_node("authority_access", aid, props)

    def revoke_authority_access(
        self,
        access_id: str,
        revoked_by: str,
        reason: str
    ):
        """Revoke authority access"""
        self._update_node("authority_access", access_id, {
            "status": "revoked",
            "revoked_by": revoked_by,
            "revocation_reason": reason,
            "revoked_at": self._now()
        })

    def log_authority_access(
        self,
        access_id: str,
        accessed_sections: List[str],
        accessor: str
    ) -> str:
        """Log authority access event"""
        lid = self._generate_id("al")
        props = {
            "access_id": access_id,
            "accessed_sections": accessed_sections,
            "accessor": accessor,
            "accessed_at": self._now(),
            "description": f"Authority access log"
        }
        return self._add_node("access_log", lid, props)

    # =========================================================================
    # Validation
    # =========================================================================

    def validate_package(
        self,
        package_id: str,
        validator: str
    ) -> Dict[str, Any]:
        """Validate documentation package completeness"""
        package = self.get_documentation_package(package_id)
        if not package:
            return {"error": "Package not found"}

        issues = []
        sections = package.get("sections", [])

        for section in sections:
            if section.get("completeness", 0) < 100:
                issues.append({
                    "section": section["type"],
                    "issue": "incomplete",
                    "completeness": section.get("completeness", 0)
                })
            if not section.get("documents"):
                issues.append({
                    "section": section["type"],
                    "issue": "no_documents"
                })

        # Check for approved documents
        for section in sections:
            for doc_id in section.get("documents", []):
                doc = self.get_document(doc_id)
                if doc and doc.get("status") != "approved":
                    issues.append({
                        "section": section["type"],
                        "document_id": doc_id,
                        "issue": "not_approved"
                    })

        valid = len(issues) == 0

        # Update package status
        self._update_node("documentation_package", package_id, {
            "validation_status": "valid" if valid else "invalid",
            "validation_issues": issues,
            "validated_by": validator,
            "validated_at": self._now()
        })

        return {
            "package_id": package_id,
            "valid": valid,
            "issues_count": len(issues),
            "issues": issues,
            "overall_completeness": package.get("overall_completeness", 0)
        }

    def finalize_package(
        self,
        package_id: str,
        finalized_by: str
    ) -> Dict[str, Any]:
        """Finalize documentation package"""
        validation = self.validate_package(package_id, finalized_by)

        if not validation.get("valid"):
            return {
                "success": False,
                "reason": "validation_failed",
                "issues": validation.get("issues", [])
            }

        self._update_node("documentation_package", package_id, {
            "status": "finalized",
            "finalized_by": finalized_by,
            "finalized_at": self._now()
        })

        return {
            "success": True,
            "package_id": package_id,
            "status": "finalized"
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get technical documentation statistics"""
        base_stats = super().get_stats()
        packages = self._find_nodes("documentation_package")
        documents = self._find_nodes("technical_document")
        access_grants = self._find_nodes("authority_access")

        return {
            **base_stats,
            "total_packages": len(packages),
            "draft_packages": len([p for p in packages if p.get("status") == "draft"]),
            "finalized_packages": len([p for p in packages if p.get("status") == "finalized"]),
            "average_completeness": round(
                sum(p.get("overall_completeness", 0) for p in packages) / len(packages)
            ) if packages else 0,
            "total_documents": len(documents),
            "approved_documents": len([d for d in documents if d.get("status") == "approved"]),
            "authority_access_grants": len(access_grants),
            "active_access_grants": len([a for a in access_grants if a.get("status") == "active"])
        }
