"""
Agent Learning Schema
=====================

Data models for agent learning, retraining, and continuous improvement.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


# =============================================================================
# Learning Event Types
# =============================================================================

class LearningEventType(str, Enum):
    """Types of learning events."""
    # Positive learning
    SUCCESS = "success"
    SKILL_ACQUIRED = "skill_acquired"
    PATTERN_LEARNED = "pattern_learned"
    INSIGHT_GAINED = "insight_gained"
    EFFICIENCY_IMPROVED = "efficiency_improved"

    # Corrective learning
    MISTAKE_CORRECTED = "mistake_corrected"
    FEEDBACK_RECEIVED = "feedback_received"
    SUPERVISION_APPLIED = "supervision_applied"

    # Reinforcement
    POSITIVE_REINFORCEMENT = "positive_reinforcement"
    NEGATIVE_REINFORCEMENT = "negative_reinforcement"
    BEHAVIOR_ADJUSTED = "behavior_adjusted"

    # Knowledge
    KNOWLEDGE_ACQUIRED = "knowledge_acquired"
    KNOWLEDGE_UPDATED = "knowledge_updated"
    KNOWLEDGE_DEPRECATED = "knowledge_deprecated"


class MistakeCategory(str, Enum):
    """Categories of mistakes for analysis."""
    FACTUAL_ERROR = "factual_error"
    LOGICAL_ERROR = "logical_error"
    JUDGMENT_ERROR = "judgment_error"
    PROCEDURAL_ERROR = "procedural_error"
    COMMUNICATION_ERROR = "communication_error"
    SAFETY_VIOLATION = "safety_violation"
    COMPLIANCE_VIOLATION = "compliance_violation"
    PERFORMANCE_ISSUE = "performance_issue"
    CONTEXT_MISUNDERSTANDING = "context_misunderstanding"
    HALLUCINATION = "hallucination"
    OVERCONFIDENCE = "overconfidence"
    UNDERCONFIDENCE = "underconfidence"


class MistakeSeverity(str, Enum):
    """Severity levels for mistakes."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    MINOR = "minor"


class ExperienceOutcome(str, Enum):
    """Outcomes of experiences."""
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    CORRECTED = "corrected"


class AttentionType(str, Enum):
    """Types of attention focus."""
    TASK_FOCUS = "task_focus"
    CONTEXT_GATHERING = "context_gathering"
    RISK_ASSESSMENT = "risk_assessment"
    ERROR_CHECKING = "error_checking"
    USER_INTENT = "user_intent"
    COMPLIANCE_CHECK = "compliance_check"
    SAFETY_CHECK = "safety_check"
    QUALITY_ASSURANCE = "quality_assurance"


class SupervisionType(str, Enum):
    """Types of supervision."""
    HUMAN_REVIEW = "human_review"
    AUTOMATED_CHECK = "automated_check"
    PEER_REVIEW = "peer_review"
    EXPERT_VALIDATION = "expert_validation"
    COMPLIANCE_AUDIT = "compliance_audit"
    SAFETY_REVIEW = "safety_review"


class SupervisionOutcome(str, Enum):
    """Outcomes of supervision."""
    APPROVED = "approved"
    APPROVED_WITH_CHANGES = "approved_with_changes"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    ESCALATED = "escalated"


class SkillLevel(str, Enum):
    """Skill proficiency levels."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"
    MASTER = "master"


class RetrainingPriority(str, Enum):
    """Priority for retraining needs."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    OPTIONAL = "optional"


class CurriculumType(str, Enum):
    """Types of retraining curriculum."""
    REMEDIAL = "remedial"           # Fix specific mistakes
    REINFORCEMENT = "reinforcement"  # Strengthen existing skills
    EXPANSION = "expansion"          # Learn new capabilities
    ADAPTATION = "adaptation"        # Adapt to new contexts
    COMPLIANCE = "compliance"        # Regulatory updates
    SAFETY = "safety"               # Safety improvements


# =============================================================================
# Learning Data Classes
# =============================================================================

@dataclass
class LearningEvent:
    """A single learning event."""
    event_id: str
    agent_id: str
    event_type: LearningEventType
    timestamp: str
    context: Dict[str, Any]
    learning_content: str
    source: str  # Where learning came from
    confidence: float  # 0-1 confidence in learning
    reinforcement_count: int = 0
    decay_factor: float = 1.0  # For forgetting curve
    tags: List[str] = field(default_factory=list)


@dataclass
class Mistake:
    """Record of a mistake for learning."""
    mistake_id: str
    agent_id: str
    category: MistakeCategory
    severity: MistakeSeverity
    timestamp: str

    # What happened
    task_context: str
    agent_action: str
    expected_action: str
    actual_outcome: str
    expected_outcome: str

    # Analysis
    root_cause: str
    contributing_factors: List[str]

    # Correction
    correction_applied: str
    corrected_by: str
    correction_verified: bool = False

    # Learning
    lesson_learned: str
    prevention_strategy: str
    similar_mistakes: List[str] = field(default_factory=list)

    # Tracking
    recurrence_count: int = 0
    last_recurrence: Optional[str] = None


@dataclass
class Experience:
    """A recorded experience for replay learning."""
    experience_id: str
    agent_id: str
    timestamp: str

    # Context
    task: str
    task_type: str
    environment: Dict[str, Any]
    initial_state: Dict[str, Any]

    # Actions
    actions_taken: List[Dict[str, Any]]
    decisions_made: List[Dict[str, Any]]

    # Outcome
    outcome: ExperienceOutcome
    outcome_details: str
    reward_signal: float  # -1 to 1

    # Learnings
    key_learnings: List[str]
    attention_points: List[str]
    challenges_faced: List[str]

    # Metadata
    duration_seconds: int = 0
    tokens_used: int = 0
    replay_count: int = 0
    last_replayed: Optional[str] = None


@dataclass
class AttentionRecord:
    """Record of what agent focused on."""
    attention_id: str
    agent_id: str
    timestamp: str
    attention_type: AttentionType

    # What was attended to
    focus_target: str
    focus_context: Dict[str, Any]
    attention_duration_ms: int

    # Quality
    attention_quality: float  # 0-1
    missed_elements: List[str]
    over_focused_elements: List[str]

    # Outcome influence
    influenced_decision: bool
    decision_id: Optional[str] = None


@dataclass
class SupervisionRecord:
    """Record of supervision applied to agent."""
    supervision_id: str
    agent_id: str
    supervisor_id: str
    supervisor_type: str  # human, system, peer
    supervision_type: SupervisionType
    timestamp: str

    # What was supervised
    supervised_action: str
    supervised_output: str
    context: Dict[str, Any]

    # Outcome
    outcome: SupervisionOutcome
    feedback: str
    required_changes: List[str]

    # Learning
    learning_points: List[str]
    agent_acknowledged: bool = False


@dataclass
class Skill:
    """A skill the agent has or is learning."""
    skill_id: str
    agent_id: str
    name: str
    category: str
    description: str

    # Proficiency
    level: SkillLevel
    proficiency_score: float  # 0-100
    confidence_score: float  # 0-1

    # Progress
    acquired_at: str
    last_practiced: str
    practice_count: int
    success_rate: float

    # Learning
    learning_events: List[str] = field(default_factory=list)
    related_mistakes: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)


@dataclass
class RetrainingNeed:
    """Identified need for retraining."""
    need_id: str
    agent_id: str
    identified_at: str
    priority: RetrainingPriority

    # What needs retraining
    skill_area: str
    specific_issue: str
    evidence: List[str]  # Mistake IDs, experience IDs, etc.

    # Curriculum
    curriculum_type: CurriculumType
    recommended_exercises: List[Dict[str, Any]]
    estimated_duration_hours: float

    # Status
    status: str = "pending"
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    effectiveness_score: Optional[float] = None


@dataclass
class RetrainingCurriculum:
    """A curriculum for agent retraining."""
    curriculum_id: str
    agent_id: str
    curriculum_type: CurriculumType
    created_at: str

    # Content
    title: str
    description: str
    objectives: List[str]
    modules: List[Dict[str, Any]]

    # Source data
    based_on_mistakes: List[str]
    based_on_experiences: List[str]
    based_on_supervision: List[str]

    # Progress
    total_modules: int
    completed_modules: int = 0
    current_module: int = 0
    status: str = "pending"

    # Results
    pre_assessment_score: Optional[float] = None
    post_assessment_score: Optional[float] = None


# =============================================================================
# Analysis Data Classes
# =============================================================================

@dataclass
class MistakePattern:
    """A detected pattern in mistakes."""
    pattern_id: str
    agent_id: str
    name: str
    description: str

    # Pattern details
    categories_involved: List[MistakeCategory]
    trigger_conditions: Dict[str, Any]
    frequency: int
    recency_weighted_score: float

    # Examples
    example_mistakes: List[str]
    contexts_occurred: List[str]

    # Prevention
    prevention_strategies: List[str]
    mitigation_applied: bool = False


@dataclass
class LearningProgress:
    """Agent's overall learning progress."""
    agent_id: str
    assessed_at: str

    # Overall metrics
    total_learning_events: int
    total_mistakes: int
    mistake_reduction_rate: float  # % reduction over time
    skill_acquisition_rate: float  # Skills per time period

    # By category
    skills_by_level: Dict[SkillLevel, int]
    mistakes_by_category: Dict[MistakeCategory, int]

    # Trends
    learning_velocity: float  # Learning rate
    retention_rate: float  # How well learnings are retained
    application_rate: float  # How often learnings are applied

    # Recommendations
    focus_areas: List[str]
    recommended_retraining: List[str]


# =============================================================================
# Edge Types
# =============================================================================

LEARNING_EDGE_TYPES = {
    # Learning relationships
    "LEARNED_FROM": "Agent learned from experience/mistake",
    "PREVENTS": "Learning prevents mistake pattern",
    "REINFORCES": "Experience reinforces skill",
    "CORRECTS": "Supervision corrects behavior",

    # Skill relationships
    "REQUIRES_SKILL": "Task requires skill",
    "DEVELOPS_SKILL": "Experience develops skill",
    "DEMONSTRATES_SKILL": "Action demonstrates skill",

    # Mistake relationships
    "CAUSED_BY": "Mistake caused by factor",
    "SIMILAR_TO": "Mistake similar to another",
    "RECURRENCE_OF": "Mistake is recurrence of pattern",

    # Attention relationships
    "FOCUSED_ON": "Attention focused on element",
    "MISSED": "Agent missed element",
    "INFLUENCED": "Attention influenced decision",

    # Supervision relationships
    "SUPERVISED_BY": "Action supervised by reviewer",
    "CORRECTED_BY": "Mistake corrected by supervisor",
    "APPROVED_BY": "Output approved by reviewer",

    # Retraining relationships
    "ADDRESSES": "Curriculum addresses need",
    "BASED_ON": "Curriculum based on data",
    "IMPROVES": "Retraining improves skill",
}


# =============================================================================
# Constants for Learning Algorithms
# =============================================================================

# Forgetting curve parameters (Ebbinghaus)
FORGETTING_CURVE = {
    "initial_retention": 1.0,
    "decay_rate": 0.5,  # Half-life in days
    "min_retention": 0.1,
}

# Spaced repetition intervals (days)
SPACED_REPETITION_INTERVALS = [1, 3, 7, 14, 30, 60, 120]

# Skill level thresholds
SKILL_LEVEL_THRESHOLDS = {
    SkillLevel.NOVICE: 0,
    SkillLevel.BEGINNER: 20,
    SkillLevel.INTERMEDIATE: 40,
    SkillLevel.ADVANCED: 60,
    SkillLevel.EXPERT: 80,
    SkillLevel.MASTER: 95,
}

# Mistake severity weights for retraining priority
MISTAKE_SEVERITY_WEIGHTS = {
    MistakeSeverity.CRITICAL: 10,
    MistakeSeverity.HIGH: 5,
    MistakeSeverity.MEDIUM: 3,
    MistakeSeverity.LOW: 1,
    MistakeSeverity.MINOR: 0.5,
}
