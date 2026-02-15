"""
Schema definitions for Agent Memory Graph

Defines all node types, edge types, and their properties.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
from enum import Enum


# =============================================================================
# Enums
# =============================================================================

class Severity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Confidence(Enum):
    LOW = 0.3
    MEDIUM = 0.6
    HIGH = 0.85
    VERY_HIGH = 0.95


class DecisionStatus(Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class DebtSeverity(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# =============================================================================
# Codebase Mental Model
# =============================================================================

@dataclass
class Module:
    """Represents a code module/package"""
    id: str
    path: str
    purpose: str
    complexity: str = "medium"  # low, medium, high, very_high
    stability: str = "stable"   # evolving, stable, frozen
    properties: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Abstraction:
    """High-level abstraction spanning modules"""
    id: str
    name: str
    level: str  # high, medium, low
    modules: List[str] = field(default_factory=list)
    documentation: Optional[str] = None


@dataclass
class DesignPattern:
    """Design pattern used in codebase"""
    id: str
    name: str
    where_used: List[str] = field(default_factory=list)
    why_chosen: Optional[str] = None


# =============================================================================
# Architectural Decisions
# =============================================================================

@dataclass
class Decision:
    """Architectural Decision Record"""
    id: str
    title: str
    status: DecisionStatus = DecisionStatus.ACCEPTED
    date: Optional[str] = None
    deciders: List[str] = field(default_factory=list)
    context: Optional[str] = None
    consequences_positive: List[str] = field(default_factory=list)
    consequences_negative: List[str] = field(default_factory=list)


@dataclass
class Alternative:
    """Alternative considered for a decision"""
    id: str
    decision_id: str
    option: str
    rejected_because: str


# =============================================================================
# Code Conventions
# =============================================================================

@dataclass
class Convention:
    """Code style convention"""
    id: str
    category: str  # naming, imports, docstrings, typing, error
    rule: str
    enforced_by: str = "manual"  # ruff, mypy, manual, etc.
    exceptions: List[str] = field(default_factory=list)


@dataclass
class Idiom:
    """Project-specific idiom/pattern"""
    id: str
    pattern: str
    preferred_form: str
    avoid: str


@dataclass
class ProjectPattern:
    """Project-specific code pattern"""
    id: str
    name: str
    template: str
    usage_context: str


# =============================================================================
# Bug Patterns
# =============================================================================

@dataclass
class Bug:
    """Historical bug record"""
    id: str
    title: str
    severity: Severity = Severity.MEDIUM
    module: Optional[str] = None
    introduced: Optional[str] = None
    fixed: Optional[str] = None
    fix_commit: Optional[str] = None


@dataclass
class BugPattern:
    """Recurring bug pattern"""
    id: str
    name: str
    signature: str  # How to recognize it
    modules_affected: List[str] = field(default_factory=list)


@dataclass
class FixPattern:
    """Fix pattern for a bug type"""
    id: str
    bug_pattern_id: str
    fix_template: str
    caveats: Optional[str] = None


# =============================================================================
# Dependencies
# =============================================================================

@dataclass
class Dependency:
    """External dependency"""
    id: str
    name: str
    version: str
    category: str  # storage, validation, http, compute
    stability: str = "stable"


@dataclass
class Quirk:
    """Dependency quirk/gotcha"""
    id: str
    dependency_id: str
    description: str
    severity: Severity = Severity.MEDIUM
    documented: bool = False


@dataclass
class Workaround:
    """Workaround for a quirk"""
    id: str
    quirk_id: str
    solution: str
    performance_impact: str = "none"


# =============================================================================
# Test Patterns
# =============================================================================

@dataclass
class TestConvention:
    """Testing convention"""
    id: str
    category: str  # unit, fixture, mock, assertion, parametrize
    pattern: str
    required_for: str = "all"


@dataclass
class RequiredTestCase:
    """Required test cases for patterns"""
    id: str
    for_pattern: str
    cases_required: List[str] = field(default_factory=list)
    rationale: Optional[str] = None


# =============================================================================
# Performance
# =============================================================================

@dataclass
class PerformanceBaseline:
    """Performance baseline measurement"""
    id: str
    operation: str
    p50_ms: float
    p99_ms: float
    throughput: str
    measured_at: Optional[str] = None


@dataclass
class HotPath:
    """Performance-critical code path"""
    id: str
    name: str
    frequency: str  # low, medium, high, very_high
    optimization_level: str = "low"
    untouchable: bool = False


@dataclass
class Bottleneck:
    """Known performance bottleneck"""
    id: str
    location: str
    cause: str
    mitigation: Optional[str] = None


# =============================================================================
# Technical Debt
# =============================================================================

@dataclass
class TechDebt:
    """Technical debt item"""
    id: str
    location: str
    description: str
    severity: DebtSeverity = DebtSeverity.MEDIUM
    age_days: int = 0
    caused_by: Optional[str] = None


@dataclass
class RefactoringAttempt:
    """Past refactoring attempt"""
    id: str
    debt_id: str
    when: str
    approach: str
    outcome: str  # success, partial, failed
    reason_failed: Optional[str] = None


# =============================================================================
# Team Knowledge
# =============================================================================

@dataclass
class TeamMember:
    """Team member"""
    id: str
    name: str
    role: str
    active: bool = True
    timezone: Optional[str] = None


@dataclass
class ExpertiseArea:
    """Area of expertise"""
    id: str
    domain: str
    depth: str  # shallow, medium, deep, expert
    modules: List[str] = field(default_factory=list)


# =============================================================================
# Session Continuity
# =============================================================================

@dataclass
class Session:
    """Agent session"""
    id: str
    started: str
    ended: Optional[str] = None
    task: str = ""
    completion: float = 0.0


@dataclass
class PartialWork:
    """Incomplete work from a session"""
    id: str
    session_id: str
    work_type: str  # code, test, doc
    location: str
    state: str


@dataclass
class SessionDecision:
    """Decision made during session"""
    id: str
    session_id: str
    decision: str
    rationale: str
    sticky: bool = True  # Carries forward to next session


@dataclass
class OpenQuestion:
    """Unanswered question from session"""
    id: str
    session_id: str
    question: str
    answered_in: Optional[str] = None
    answer: Optional[str] = None


# =============================================================================
# Templates
# =============================================================================

@dataclass
class Template:
    """Code generation template"""
    id: str
    name: str
    category: str  # model, handler, algorithm, migration
    usage_count: int = 0
    last_used: Optional[str] = None


@dataclass
class Snippet:
    """Reusable code snippet"""
    id: str
    name: str
    code: str
    usage_context: str


# =============================================================================
# Skills & Learning
# =============================================================================

@dataclass
class Skill:
    """Agent skill"""
    id: str
    name: str
    category: str  # language, framework, domain, tooling
    proficiency: float = 0.0  # 0.0 to 1.0
    examples_seen: int = 0


@dataclass
class LearningEvent:
    """Learning event"""
    id: str
    skill_id: str
    event_type: str  # success, failure, correction
    context: str
    lesson: Optional[str] = None


# =============================================================================
# Edge Types
# =============================================================================

EDGE_TYPES = {
    # Codebase
    "DEPENDS_ON": "Module dependencies",
    "ABSTRACTS": "Abstraction covers module",
    "IMPLEMENTS": "Module implements pattern",
    "MENTAL_MODEL_CONFIDENCE": "Agent's understanding confidence",

    # Decisions
    "SUPERSEDES": "Decision supersedes another",
    "CONSTRAINS": "Decision constrains module",
    "AGENT_VIOLATED": "Agent violated decision",

    # Conventions
    "APPLIES_TO": "Convention applies to files",
    "LEARNED_FROM": "Agent learned convention from examples",
    "VIOLATION_HISTORY": "Past violations by agent",

    # Bugs
    "INSTANCE_OF": "Bug is instance of pattern",
    "SIMILAR_CODE_EXISTS": "Similar risky code exists",
    "PREVENTED_BY_AGENT": "Agent prevented this bug",
    "MISSED_BY_AGENT": "Agent missed this bug",

    # Dependencies
    "HAS_QUIRK": "Dependency has quirk",
    "WORKAROUND_FOR": "Workaround for quirk",
    "AGENT_KNOWS": "Agent knows workaround",

    # Tests
    "MUST_TEST": "Required test cases",
    "TEST_FOR_BUG": "Test exists for past bug",

    # Performance
    "PERFORMANCE_SENSITIVE": "Hot path affects baseline",
    "REGRESSION_HISTORY": "Past performance regression",

    # Tech Debt
    "CAUSED_BY": "Debt caused by",
    "BLOCKED_BY": "Refactoring blocked by",

    # Team
    "HAS_EXPERTISE": "Team member has expertise",
    "AUTHORED_DECISION": "Member authored decision",
    "CONTACT_FOR": "Contact for expertise area",

    # Sessions
    "CONTINUES": "Session continues previous",
    "DECISION_CARRIES_FORWARD": "Decision applies to session",
    "WORK_RESUMED": "Work resumed from partial",

    # Templates
    "USES_SNIPPET": "Template uses snippet",
    "TEMPLATE_EVOLVED": "Template evolved from",

    # Skills
    "SKILL_APPLIED": "Skill applied in session",
    "LEARNED_IN": "Skill learned in session",
}
