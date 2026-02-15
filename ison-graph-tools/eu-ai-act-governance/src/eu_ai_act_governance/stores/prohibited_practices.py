"""
Prohibited Practices Store
==========================

Manages detection, prevention, and reporting of prohibited AI practices per Article 5.
Tracks prohibited practice screenings, violations, and enforcement actions.
"""

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from .base import BaseStore
from ..schema import ProhibitedPractice, AIRiskLevel

if TYPE_CHECKING:
    from ison_graph import ISONGraph


# Detailed prohibited practice definitions per Article 5
PROHIBITED_PRACTICE_DETAILS = {
    ProhibitedPractice.SUBLIMINAL_MANIPULATION: {
        "article": "5(1)(a)",
        "description": "AI deploying subliminal techniques beyond person's consciousness to distort behavior causing significant harm",
        "harm_type": "psychological",
        "detection_criteria": [
            "Uses techniques below conscious perception threshold",
            "Intended to materially distort behavior",
            "Causes or is likely to cause significant harm"
        ]
    },
    ProhibitedPractice.EXPLOITING_VULNERABILITIES: {
        "article": "5(1)(b)",
        "description": "AI exploiting vulnerabilities of specific groups (age, disability, social/economic situation)",
        "harm_type": "psychological/physical",
        "detection_criteria": [
            "Targets vulnerable groups",
            "Exploits age, physical or mental disability",
            "Exploits social or economic circumstances",
            "Materially distorts behavior causing harm"
        ]
    },
    ProhibitedPractice.SOCIAL_SCORING_PUBLIC: {
        "article": "5(1)(c)",
        "description": "Public authority social scoring leading to detrimental treatment",
        "harm_type": "civil rights",
        "detection_criteria": [
            "Evaluates or classifies natural persons over time",
            "Based on social behavior or personal characteristics",
            "Leads to detrimental treatment in unrelated contexts",
            "Disproportionate or unjustified treatment"
        ]
    },
    ProhibitedPractice.SOCIAL_SCORING_PRIVATE: {
        "article": "5(1)(c)",
        "description": "Private entity social scoring leading to detrimental treatment",
        "harm_type": "civil rights",
        "detection_criteria": [
            "Social scoring by private entities",
            "Generalizes behavior to unrelated contexts",
            "Causes unjustified adverse treatment"
        ]
    },
    ProhibitedPractice.REAL_TIME_BIOMETRIC_PUBLIC: {
        "article": "5(1)(d)",
        "description": "Real-time remote biometric identification in publicly accessible spaces for law enforcement",
        "harm_type": "privacy/civil rights",
        "detection_criteria": [
            "Real-time operation",
            "Remote biometric identification",
            "Publicly accessible spaces",
            "Law enforcement purpose",
            "No authorized exception applies"
        ],
        "exceptions": [
            "Targeted search for missing children/victims",
            "Prevention of imminent terrorist threat",
            "Detection of perpetrators of serious crimes"
        ]
    },
    ProhibitedPractice.BIOMETRIC_CATEGORIZATION_SENSITIVE: {
        "article": "5(1)(g)",
        "description": "Biometric categorization inferring sensitive attributes (race, politics, religion, sexual orientation)",
        "harm_type": "discrimination",
        "detection_criteria": [
            "Uses biometric data",
            "Infers or deduces sensitive attributes",
            "Covers race, political opinions, religion, sexuality"
        ]
    },
    ProhibitedPractice.FACIAL_RECOGNITION_SCRAPING: {
        "article": "5(1)(e)",
        "description": "Untargeted scraping of facial images from internet or CCTV for facial recognition databases",
        "harm_type": "privacy",
        "detection_criteria": [
            "Scrapes facial images",
            "Sources from internet or CCTV",
            "Creates or expands recognition databases",
            "Untargeted collection"
        ]
    },
    ProhibitedPractice.EMOTION_RECOGNITION_WORKPLACE: {
        "article": "5(1)(f)",
        "description": "Emotion recognition in workplace (except safety/medical)",
        "harm_type": "privacy/dignity",
        "detection_criteria": [
            "Infers emotions of workers",
            "Workplace context",
            "Not for safety or medical purposes"
        ],
        "exceptions": [
            "Safety-critical operations",
            "Medical/therapeutic purposes"
        ]
    },
    ProhibitedPractice.EMOTION_RECOGNITION_EDUCATION: {
        "article": "5(1)(f)",
        "description": "Emotion recognition in educational institutions",
        "harm_type": "privacy/dignity",
        "detection_criteria": [
            "Infers emotions of students",
            "Educational institution context"
        ],
        "exceptions": [
            "Medical/therapeutic purposes",
            "Safety reasons"
        ]
    },
    ProhibitedPractice.PREDICTIVE_POLICING_INDIVIDUAL: {
        "article": "5(1)(d)",
        "description": "Predicting individual criminal risk based solely on profiling/traits",
        "harm_type": "civil rights",
        "detection_criteria": [
            "Makes predictions about natural persons",
            "Assesses criminal offense risk",
            "Based solely on profiling",
            "Uses personality traits or characteristics"
        ]
    },
    ProhibitedPractice.MANIPULATION_DECEPTIVE: {
        "article": "5(1)(a)",
        "description": "Deceptive techniques that distort decision-making",
        "harm_type": "autonomy",
        "detection_criteria": [
            "Uses deceptive patterns",
            "Distorts decision-making",
            "Impairs informed choice"
        ]
    },
}


class ProhibitedPracticesStore(BaseStore):
    """Store for managing prohibited AI practice detection and prevention"""

    def __init__(self, graph: "ISONGraph"):
        super().__init__(graph, "prohibited_practices")

    # =========================================================================
    # Screening Process
    # =========================================================================

    def create_screening(
        self,
        system_id: str,
        screener: str,
        screening_type: str = "pre_market",  # pre_market, periodic, complaint_triggered
        screening_id: Optional[str] = None
    ) -> str:
        """Create a prohibited practices screening for an AI system"""
        sid = screening_id or self._generate_id("pps")
        props = {
            "system_id": system_id,
            "screener": screener,
            "screening_type": screening_type,
            "status": "in_progress",
            "started_at": self._now(),
            "practices_checked": [],
            "violations_found": [],
            "description": f"Prohibited practices screening for {system_id}"
        }
        return self._add_node("prohibited_screening", sid, props)

    def get_screening(self, screening_id: str) -> Optional[Dict[str, Any]]:
        """Get screening by ID"""
        return self._get_node("prohibited_screening", screening_id)

    def get_system_screenings(self, system_id: str) -> List[Dict[str, Any]]:
        """Get all screenings for a system"""
        return self._find_nodes("prohibited_screening", system_id=system_id)

    # =========================================================================
    # Practice Checks
    # =========================================================================

    def check_practice(
        self,
        screening_id: str,
        practice: ProhibitedPractice,
        indicators_present: List[str],
        evidence: str,
        conclusion: str,  # clear, potential_violation, violation
        checked_by: str,
        notes: str = ""
    ) -> str:
        """Check for a specific prohibited practice"""
        details = PROHIBITED_PRACTICE_DETAILS.get(practice, {})
        cid = self._generate_id("pc")
        props = {
            "screening_id": screening_id,
            "practice": practice.value,
            "practice_name": practice.name,
            "article_reference": details.get("article", "Art. 5"),
            "description": details.get("description", ""),
            "harm_type": details.get("harm_type", ""),
            "detection_criteria": details.get("detection_criteria", []),
            "indicators_present": indicators_present,
            "evidence": evidence,
            "conclusion": conclusion,
            "checked_by": checked_by,
            "checked_at": self._now(),
            "notes": notes
        }
        self._add_node("practice_check", cid, props)

        # Link to screening
        self._add_edge(
            "prohibited_screening", screening_id,
            "HAS_CHECK",
            "practice_check", cid,
            {"practice": practice.value}
        )

        # Update screening status
        screening = self.get_screening(screening_id)
        if screening:
            checked = screening.get("practices_checked", [])
            checked.append(practice.value)
            updates = {"practices_checked": checked}

            if conclusion in ["potential_violation", "violation"]:
                violations = screening.get("violations_found", [])
                violations.append(practice.value)
                updates["violations_found"] = violations

            self._update_node("prohibited_screening", screening_id, updates)

        return cid

    def get_practice_checks(
        self,
        screening_id: str,
        conclusion: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get practice checks for a screening"""
        checks = self._find_nodes("practice_check", screening_id=screening_id)
        if conclusion:
            checks = [c for c in checks if c.get("conclusion") == conclusion]
        return checks

    # =========================================================================
    # Exception Evaluation
    # =========================================================================

    def evaluate_exception(
        self,
        check_id: str,
        exception_type: str,
        exception_justification: str,
        applies: bool,
        evaluated_by: str
    ) -> str:
        """Evaluate if an exception applies to a potential violation"""
        eid = self._generate_id("pe")
        props = {
            "check_id": check_id,
            "exception_type": exception_type,
            "justification": exception_justification,
            "applies": applies,
            "evaluated_by": evaluated_by,
            "evaluated_at": self._now(),
            "description": f"Exception evaluation: {exception_type}"
        }
        self._add_node("practice_exception", eid, props)

        # If exception applies, update the check
        if applies:
            self._update_node("practice_check", check_id, {
                "exception_applied": exception_type,
                "conclusion": "exception_applies"
            })

        return eid

    # =========================================================================
    # Complete Screening
    # =========================================================================

    def complete_screening(
        self,
        screening_id: str,
        overall_conclusion: str,  # compliant, non_compliant, requires_modification
        recommendations: List[str],
        completed_by: str
    ) -> Dict[str, Any]:
        """Complete the screening and generate results"""
        screening = self.get_screening(screening_id)
        if not screening:
            return {"error": "Screening not found"}

        violations = screening.get("violations_found", [])

        # Determine market status
        if violations:
            market_status = "prohibited"
            risk_level = AIRiskLevel.UNACCEPTABLE.value
        elif overall_conclusion == "requires_modification":
            market_status = "conditional"
            risk_level = None
        else:
            market_status = "allowed"
            risk_level = None

        self._update_node("prohibited_screening", screening_id, {
            "status": "completed",
            "overall_conclusion": overall_conclusion,
            "recommendations": recommendations,
            "completed_by": completed_by,
            "completed_at": self._now(),
            "market_status": market_status
        })

        return {
            "screening_id": screening_id,
            "system_id": screening.get("system_id"),
            "conclusion": overall_conclusion,
            "violations_found": violations,
            "market_status": market_status,
            "risk_level": risk_level,
            "recommendations": recommendations
        }

    # =========================================================================
    # Violation Reporting
    # =========================================================================

    def report_violation(
        self,
        system_id: str,
        practice: ProhibitedPractice,
        reporter: str,
        reporter_type: str,  # user, employee, competitor, authority, ngo
        description: str,
        evidence: str,
        report_id: Optional[str] = None
    ) -> str:
        """Report a suspected prohibited practice violation"""
        rid = report_id or self._generate_id("vr")
        props = {
            "system_id": system_id,
            "practice": practice.value,
            "reporter": reporter,
            "reporter_type": reporter_type,
            "description": description,
            "evidence": evidence,
            "status": "received",
            "reported_at": self._now(),
            "node_description": f"Violation report: {practice.value}"
        }
        return self._add_node("violation_report", rid, props)

    def get_violation_report(self, report_id: str) -> Optional[Dict[str, Any]]:
        """Get violation report by ID"""
        return self._get_node("violation_report", report_id)

    def triage_report(
        self,
        report_id: str,
        priority: str,  # low, medium, high, critical
        assigned_to: str,
        initial_assessment: str
    ):
        """Triage a violation report"""
        self._update_node("violation_report", report_id, {
            "status": "triaged",
            "priority": priority,
            "assigned_to": assigned_to,
            "initial_assessment": initial_assessment,
            "triaged_at": self._now()
        })

    def investigate_report(
        self,
        report_id: str,
        investigator: str,
        findings: str,
        conclusion: str,  # substantiated, unsubstantiated, inconclusive
        recommended_action: str
    ):
        """Complete investigation of a violation report"""
        self._update_node("violation_report", report_id, {
            "status": "investigated",
            "investigator": investigator,
            "findings": findings,
            "investigation_conclusion": conclusion,
            "recommended_action": recommended_action,
            "investigated_at": self._now()
        })

    def get_pending_reports(self) -> List[Dict[str, Any]]:
        """Get reports pending investigation"""
        reports = self._find_nodes("violation_report")
        return [r for r in reports if r.get("status") in ["received", "triaged"]]

    # =========================================================================
    # Enforcement Actions
    # =========================================================================

    def create_enforcement_action(
        self,
        system_id: str,
        violation_type: ProhibitedPractice,
        action_type: str,  # warning, fine, market_withdrawal, ban
        authority: str,
        description: str,
        action_id: Optional[str] = None
    ) -> str:
        """Create an enforcement action for a violation"""
        aid = action_id or self._generate_id("ea")
        props = {
            "system_id": system_id,
            "violation_type": violation_type.value,
            "action_type": action_type,
            "authority": authority,
            "description": description,
            "status": "pending",
            "created_at": self._now(),
            "node_description": f"Enforcement action: {action_type}"
        }
        return self._add_node("enforcement_action", aid, props)

    def execute_enforcement(
        self,
        action_id: str,
        executed_by: str,
        execution_details: str,
        fine_amount: Optional[float] = None
    ):
        """Execute an enforcement action"""
        updates = {
            "status": "executed",
            "executed_by": executed_by,
            "execution_details": execution_details,
            "executed_at": self._now()
        }
        if fine_amount is not None:
            updates["fine_amount"] = fine_amount
            updates["fine_currency"] = "EUR"

        self._update_node("enforcement_action", action_id, updates)

    def appeal_enforcement(
        self,
        action_id: str,
        appellant: str,
        grounds: str
    ):
        """Record an appeal against enforcement action"""
        self._update_node("enforcement_action", action_id, {
            "status": "appealed",
            "appellant": appellant,
            "appeal_grounds": grounds,
            "appealed_at": self._now()
        })

    def get_enforcement_actions(
        self,
        system_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get enforcement actions"""
        actions = self._find_nodes("enforcement_action")
        if system_id:
            actions = [a for a in actions if a.get("system_id") == system_id]
        if status:
            actions = [a for a in actions if a.get("status") == status]
        return actions

    # =========================================================================
    # Market Withdrawal
    # =========================================================================

    def order_withdrawal(
        self,
        system_id: str,
        reason: str,
        authority: str,
        deadline: str,
        scope: str = "eu_wide"  # eu_wide, member_state
    ) -> str:
        """Order market withdrawal of a prohibited system"""
        wid = self._generate_id("mw")
        props = {
            "system_id": system_id,
            "reason": reason,
            "authority": authority,
            "deadline": deadline,
            "scope": scope,
            "status": "ordered",
            "ordered_at": self._now(),
            "description": f"Market withdrawal order for {system_id}"
        }
        return self._add_node("market_withdrawal", wid, props)

    def confirm_withdrawal(
        self,
        withdrawal_id: str,
        confirmed_by: str,
        verification: str
    ):
        """Confirm that market withdrawal has been completed"""
        self._update_node("market_withdrawal", withdrawal_id, {
            "status": "completed",
            "confirmed_by": confirmed_by,
            "verification": verification,
            "completed_at": self._now()
        })

    # =========================================================================
    # Analysis & Statistics
    # =========================================================================

    def analyze_practice_trends(self) -> Dict[str, Any]:
        """Analyze trends in prohibited practice violations"""
        reports = self._find_nodes("violation_report")
        screenings = self._find_nodes("prohibited_screening")

        # Count by practice type
        by_practice = {}
        for practice in ProhibitedPractice:
            count = len([r for r in reports if r.get("practice") == practice.value])
            by_practice[practice.value] = count

        # Most reported practices
        sorted_practices = sorted(
            by_practice.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]

        # Substantiation rate
        investigated = [r for r in reports if r.get("status") == "investigated"]
        substantiated = len([
            r for r in investigated
            if r.get("investigation_conclusion") == "substantiated"
        ])
        substantiation_rate = (
            (substantiated / len(investigated)) * 100
            if investigated else 0
        )

        return {
            "total_reports": len(reports),
            "total_screenings": len(screenings),
            "violations_by_practice": by_practice,
            "most_reported": sorted_practices,
            "substantiation_rate": round(substantiation_rate, 1),
            "pending_reports": len([r for r in reports if r.get("status") in ["received", "triaged"]])
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get prohibited practices statistics"""
        base_stats = super().get_stats()
        screenings = self._find_nodes("prohibited_screening")
        reports = self._find_nodes("violation_report")
        actions = self._find_nodes("enforcement_action")
        withdrawals = self._find_nodes("market_withdrawal")

        return {
            **base_stats,
            "total_screenings": len(screenings),
            "completed_screenings": len([s for s in screenings if s.get("status") == "completed"]),
            "screenings_with_violations": len([s for s in screenings if s.get("violations_found")]),
            "total_reports": len(reports),
            "pending_reports": len([r for r in reports if r.get("status") in ["received", "triaged"]]),
            "enforcement_actions": len(actions),
            "executed_actions": len([a for a in actions if a.get("status") == "executed"]),
            "market_withdrawals": len(withdrawals),
            "completed_withdrawals": len([w for w in withdrawals if w.get("status") == "completed"])
        }
