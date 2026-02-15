"""
Data Governance Store
=====================

Manages data governance requirements per Article 10.
Tracks training data, validation datasets, bias monitoring, and data quality.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import DataGovernanceRequirement, BiasType

if TYPE_CHECKING:
    from ison_graph import ISONGraph


class DataGovernanceStore(BaseStore):
    """Store for data governance management"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "data_governance")

    # =========================================================================
    # Dataset Registration
    # =========================================================================

    def register_dataset(
        self,
        system_id: str,
        dataset_type: str,  # training, validation, testing
        name: str,
        source: str,
        size: int,  # number of samples
        format_type: str,
        provenance: str,
        dataset_id: Optional[str] = None
    ) -> str:
        """Register a dataset used by an AI system"""
        did = dataset_id or self._generate_id("ds")
        props = {
            "system_id": system_id,
            "dataset_type": dataset_type,
            "name": name,
            "source": source,
            "size": size,
            "format": format_type,
            "provenance": provenance,
            "status": "registered",
            "created_at": self._now(),
            "quality_score": None,
            "bias_assessed": False,
            "description": f"Dataset: {name} ({dataset_type})"
        }
        return self._add_node("dataset", did, props)

    def get_dataset(self, dataset_id: str) -> Optional[Dict[str, Any]]:
        """Get dataset by ID"""
        return self._get_node("dataset", dataset_id)

    def get_system_datasets(
        self,
        system_id: str,
        dataset_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all datasets for a system"""
        datasets = self._find_nodes("dataset", system_id=system_id)
        if dataset_type:
            datasets = [d for d in datasets if d.get("dataset_type") == dataset_type]
        return datasets

    # =========================================================================
    # Data Quality Assessment
    # =========================================================================

    def assess_data_quality(
        self,
        dataset_id: str,
        assessor: str,
        assessment_id: Optional[str] = None
    ) -> str:
        """Create a data quality assessment"""
        aid = assessment_id or self._generate_id("dqa")
        props = {
            "dataset_id": dataset_id,
            "assessor": assessor,
            "status": "in_progress",
            "started_at": self._now(),
            "criteria_checked": [],
            "issues_found": [],
            "description": f"Data quality assessment for {dataset_id}"
        }
        return self._add_node("data_quality_assessment", aid, props)

    def check_quality_criterion(
        self,
        assessment_id: str,
        criterion: str,  # completeness, accuracy, consistency, timeliness, representativeness
        score: int,  # 0-100
        findings: str,
        methodology: str
    ) -> str:
        """Check a specific quality criterion"""
        cid = self._generate_id("qc")
        props = {
            "assessment_id": assessment_id,
            "criterion": criterion,
            "score": score,
            "findings": findings,
            "methodology": methodology,
            "passed": score >= 70,
            "checked_at": self._now(),
            "description": f"Quality check: {criterion}"
        }
        self._add_node("quality_check", cid, props)

        # Update assessment
        assessment = self._get_node("data_quality_assessment", assessment_id)
        if assessment:
            checked = assessment.get("criteria_checked", [])
            checked.append(criterion)
            updates = {"criteria_checked": checked}

            if score < 70:
                issues = assessment.get("issues_found", [])
                issues.append({"criterion": criterion, "score": score, "findings": findings})
                updates["issues_found"] = issues

            self._update_node("data_quality_assessment", assessment_id, updates)

        return cid

    def complete_quality_assessment(
        self,
        assessment_id: str,
        overall_score: int,
        recommendations: List[str],
        compliant: bool
    ) -> Dict[str, Any]:
        """Complete quality assessment"""
        self._update_node("data_quality_assessment", assessment_id, {
            "status": "completed",
            "overall_score": overall_score,
            "recommendations": recommendations,
            "compliant": compliant,
            "completed_at": self._now()
        })

        # Update dataset quality score
        assessment = self._get_node("data_quality_assessment", assessment_id)
        if assessment:
            dataset_id = assessment.get("dataset_id")
            self._update_node("dataset", dataset_id, {
                "quality_score": overall_score,
                "quality_assessment_id": assessment_id
            })

        return {
            "assessment_id": assessment_id,
            "overall_score": overall_score,
            "compliant": compliant,
            "recommendations": recommendations
        }

    # =========================================================================
    # Bias Monitoring (per Art. 10(2)(f))
    # =========================================================================

    def create_bias_monitoring(
        self,
        dataset_id: str,
        protected_attributes: List[str],
        monitor_id: Optional[str] = None
    ) -> str:
        """Create bias monitoring for a dataset"""
        mid = monitor_id or self._generate_id("bm")
        props = {
            "dataset_id": dataset_id,
            "protected_attributes": protected_attributes,
            "status": "active",
            "checks_performed": 0,
            "issues_detected": [],
            "created_at": self._now(),
            "description": f"Bias monitoring for {dataset_id}"
        }
        return self._add_node("bias_monitoring", mid, props)

    def perform_bias_check(
        self,
        monitor_id: str,
        bias_type: BiasType,
        attribute: str,
        metric: str,
        baseline_value: float,
        current_value: float,
        threshold: float,
        check_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Perform a bias check"""
        cid = check_id or self._generate_id("bc")
        deviation = abs(current_value - baseline_value)
        passed = deviation <= threshold

        props = {
            "monitor_id": monitor_id,
            "bias_type": bias_type.value,
            "attribute": attribute,
            "metric": metric,
            "baseline_value": baseline_value,
            "current_value": current_value,
            "deviation": deviation,
            "threshold": threshold,
            "passed": passed,
            "checked_at": self._now(),
            "description": f"Bias check: {bias_type.value} on {attribute}"
        }
        self._add_node("bias_check", cid, props)

        # Update monitor
        monitor = self._get_node("bias_monitoring", monitor_id)
        if monitor:
            checks = monitor.get("checks_performed", 0)
            updates = {"checks_performed": checks + 1}

            if not passed:
                issues = monitor.get("issues_detected", [])
                issues.append({
                    "check_id": cid,
                    "bias_type": bias_type.value,
                    "attribute": attribute,
                    "deviation": deviation
                })
                updates["issues_detected"] = issues

            self._update_node("bias_monitoring", monitor_id, updates)

        return {
            "check_id": cid,
            "passed": passed,
            "deviation": deviation,
            "threshold": threshold,
            "requires_remediation": not passed
        }

    def get_bias_issues(
        self,
        dataset_id: Optional[str] = None,
        bias_type: Optional[BiasType] = None
    ) -> List[Dict[str, Any]]:
        """Get bias issues"""
        checks = self._find_nodes("bias_check", passed=False)

        if bias_type:
            checks = [c for c in checks if c.get("bias_type") == bias_type.value]

        if dataset_id:
            # Get monitors for dataset
            monitors = self._find_nodes("bias_monitoring", dataset_id=dataset_id)
            monitor_ids = [m["id"] for m in monitors]
            checks = [c for c in checks if c.get("monitor_id") in monitor_ids]

        return checks

    # =========================================================================
    # Data Processing Records
    # =========================================================================

    def record_processing(
        self,
        dataset_id: str,
        processing_type: str,  # cleaning, labeling, augmentation, transformation
        description: str,
        parameters: Dict[str, Any],
        performed_by: str,
        processing_id: Optional[str] = None
    ) -> str:
        """Record data processing operation"""
        pid = processing_id or self._generate_id("dp")
        props = {
            "dataset_id": dataset_id,
            "processing_type": processing_type,
            "description": description,
            "parameters": parameters,
            "performed_by": performed_by,
            "performed_at": self._now(),
            "node_description": f"Data processing: {processing_type}"
        }
        return self._add_node("data_processing", pid, props)

    def get_processing_history(self, dataset_id: str) -> List[Dict[str, Any]]:
        """Get processing history for a dataset"""
        records = self._find_nodes("data_processing", dataset_id=dataset_id)
        records.sort(key=lambda x: x.get("performed_at", ""))
        return records

    # =========================================================================
    # Data Governance Requirements Tracking
    # =========================================================================

    def initialize_governance_requirements(
        self,
        system_id: str,
        responsible_party: str
    ) -> List[str]:
        """Initialize data governance requirements for a system"""
        requirement_ids = []

        for req in DataGovernanceRequirement:
            rid = self._generate_id("dgr")
            props = {
                "system_id": system_id,
                "requirement": req.value,
                "responsible_party": responsible_party,
                "status": "not_started",
                "evidence": [],
                "created_at": self._now(),
                "description": f"Data governance requirement: {req.value}"
            }
            self._add_node("dg_requirement", rid, props)
            requirement_ids.append(rid)

        return requirement_ids

    def update_requirement_status(
        self,
        requirement_id: str,
        status: str,  # not_started, in_progress, implemented, verified
        evidence: List[str],
        notes: str = ""
    ):
        """Update requirement status"""
        self._update_node("dg_requirement", requirement_id, {
            "status": status,
            "evidence": evidence,
            "notes": notes,
            "updated_at": self._now()
        })

    def get_governance_status(self, system_id: str) -> Dict[str, Any]:
        """Get overall data governance status"""
        requirements = self._find_nodes("dg_requirement", system_id=system_id)

        if not requirements:
            return {"system_id": system_id, "status": "not_initialized"}

        total = len(requirements)
        implemented = len([r for r in requirements if r.get("status") == "implemented"])
        verified = len([r for r in requirements if r.get("status") == "verified"])

        compliance = round(((implemented + verified) / total) * 100) if total > 0 else 0

        return {
            "system_id": system_id,
            "total_requirements": total,
            "implemented": implemented,
            "verified": verified,
            "compliance_percentage": compliance,
            "status": "compliant" if compliance >= 100 else "in_progress"
        }

    # =========================================================================
    # Labeling Quality
    # =========================================================================

    def record_labeling_process(
        self,
        dataset_id: str,
        labeling_type: str,  # manual, automated, hybrid
        labelers: List[str],
        guidelines_ref: str,
        quality_control: str,
        labeling_id: Optional[str] = None
    ) -> str:
        """Record labeling process details"""
        lid = labeling_id or self._generate_id("lp")
        props = {
            "dataset_id": dataset_id,
            "labeling_type": labeling_type,
            "labelers": labelers,
            "guidelines_ref": guidelines_ref,
            "quality_control": quality_control,
            "inter_annotator_agreement": None,
            "created_at": self._now(),
            "description": f"Labeling process for {dataset_id}"
        }
        return self._add_node("labeling_process", lid, props)

    def record_annotation_agreement(
        self,
        labeling_id: str,
        metric: str,  # kappa, fleiss_kappa, percentage
        score: float,
        threshold: float,
        passed: bool
    ):
        """Record inter-annotator agreement score"""
        self._update_node("labeling_process", labeling_id, {
            "inter_annotator_agreement": {
                "metric": metric,
                "score": score,
                "threshold": threshold,
                "passed": passed,
                "measured_at": self._now()
            }
        })

    # =========================================================================
    # Data Lineage
    # =========================================================================

    def add_data_source(
        self,
        dataset_id: str,
        source_type: str,  # public, commercial, proprietary, synthetic
        source_name: str,
        source_uri: str,
        license_type: str,
        acquisition_date: str,
        source_id: Optional[str] = None
    ) -> str:
        """Add data source information"""
        sid = source_id or self._generate_id("src")
        props = {
            "dataset_id": dataset_id,
            "source_type": source_type,
            "source_name": source_name,
            "source_uri": source_uri,
            "license_type": license_type,
            "acquisition_date": acquisition_date,
            "verified": False,
            "description": f"Data source: {source_name}"
        }
        return self._add_node("data_source", sid, props)

    def verify_data_source(
        self,
        source_id: str,
        verified_by: str,
        verification_method: str,
        compliant: bool,
        notes: str = ""
    ):
        """Verify a data source"""
        self._update_node("data_source", source_id, {
            "verified": True,
            "verified_by": verified_by,
            "verification_method": verification_method,
            "compliant": compliant,
            "verification_notes": notes,
            "verified_at": self._now()
        })

    def get_data_lineage(self, dataset_id: str) -> Dict[str, Any]:
        """Get complete data lineage for a dataset"""
        dataset = self.get_dataset(dataset_id)
        if not dataset:
            return {"error": "Dataset not found"}

        sources = self._find_nodes("data_source", dataset_id=dataset_id)
        processing = self.get_processing_history(dataset_id)
        labeling = self._find_nodes("labeling_process", dataset_id=dataset_id)

        return {
            "dataset_id": dataset_id,
            "dataset_info": dataset,
            "sources": sources,
            "processing_history": processing,
            "labeling_processes": labeling
        }

    # =========================================================================
    # Statistical Properties (Art. 10(3))
    # =========================================================================

    def record_statistical_properties(
        self,
        dataset_id: str,
        properties: Dict[str, Any],
        recorded_by: str
    ) -> str:
        """Record statistical properties of a dataset"""
        pid = self._generate_id("sp")
        props = {
            "dataset_id": dataset_id,
            "properties": properties,  # e.g., distribution, mean, variance, class balance
            "recorded_by": recorded_by,
            "recorded_at": self._now(),
            "description": f"Statistical properties for {dataset_id}"
        }
        return self._add_node("statistical_properties", pid, props)

    def check_representativeness(
        self,
        dataset_id: str,
        target_population: Dict[str, Any],
        checker: str
    ) -> Dict[str, Any]:
        """Check dataset representativeness"""
        cid = self._generate_id("rc")

        dataset = self.get_dataset(dataset_id)
        stats = self._find_nodes("statistical_properties", dataset_id=dataset_id)

        # Basic check - in practice this would involve statistical analysis
        issues = []
        if not stats:
            issues.append("No statistical properties recorded")

        props = {
            "dataset_id": dataset_id,
            "target_population": target_population,
            "issues": issues,
            "representative": len(issues) == 0,
            "checked_by": checker,
            "checked_at": self._now(),
            "description": f"Representativeness check for {dataset_id}"
        }
        self._add_node("representativeness_check", cid, props)

        return {
            "check_id": cid,
            "representative": len(issues) == 0,
            "issues": issues
        }

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get data governance statistics"""
        base_stats = super().get_stats()
        datasets = self._find_nodes("dataset")
        quality_assessments = self._find_nodes("data_quality_assessment")
        bias_monitors = self._find_nodes("bias_monitoring")
        bias_checks = self._find_nodes("bias_check")
        requirements = self._find_nodes("dg_requirement")

        return {
            **base_stats,
            "total_datasets": len(datasets),
            "training_datasets": len([d for d in datasets if d.get("dataset_type") == "training"]),
            "quality_assessments": len(quality_assessments),
            "compliant_datasets": len([
                qa for qa in quality_assessments
                if qa.get("compliant")
            ]),
            "bias_monitors": len(bias_monitors),
            "bias_checks_performed": len(bias_checks),
            "bias_issues_found": len([bc for bc in bias_checks if not bc.get("passed")]),
            "governance_requirements": len(requirements),
            "requirements_met": len([r for r in requirements if r.get("status") in ["implemented", "verified"]])
        }
