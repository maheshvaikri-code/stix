# Agent Learning

A comprehensive agent learning and retraining system built on ISONGraph.

## Features

### Core Learning Stores

- **Experience Store**: Record and replay agent experiences for reinforcement learning
- **Mistake Store**: Track mistakes with pattern detection and correction tracking
- **Attention Store**: Monitor agent attention patterns and identify missed elements
- **Supervision Store**: Track human oversight, feedback, and corrections
- **Skill Store**: Manage agent skills with proficiency tracking and spaced repetition

### Retraining Engine

- Automatic identification of retraining needs based on:
  - Recurring mistake patterns
  - Experience failure rates
  - Supervision feedback
  - Attention quality issues
  - Skill gaps
- Curriculum generation with:
  - Remedial training for specific mistakes
  - Reinforcement for existing skills
  - Expansion for new capabilities
  - Compliance and safety modules

### Memory Integration

- **Learning Memory Store**: Following agent-memory patterns
  - Working memory (current session)
  - Episodic memory (experiences)
  - Semantic memory (consolidated knowledge)
  - Procedural memory (skills/procedures)
- **Cached Learning Context**: Token-budgeted context retrieval following ISONCache patterns
- **Learning Session Manager**: Session continuity with handoff support

### Learning Algorithms

- **Forgetting Curve**: Ebbinghaus-based memory decay
- **Spaced Repetition**: Optimal practice scheduling
- **Experience Replay**: Priority-based experience sampling
- **Pattern Detection**: Automatic mistake pattern identification

## Installation

```bash
pip install agent-learning
```

Or install from source:

```bash
pip install -e .
```

## Quick Start

```python
from ison_graph import ISONGraph
from agent_learning import (
    AgentLearningEngine,
    ExperienceOutcome,
    MistakeCategory,
    MistakeSeverity,
    SkillLevel,
)

# Initialize
graph = ISONGraph("my-learning-db")
engine = AgentLearningEngine(graph)

agent_id = "agent-1"

# Record an experience
exp_id = engine.record_experience(
    agent_id=agent_id,
    task="Complete user request",
    task_type="task_completion",
    environment={"platform": "production"},
    initial_state={"context_length": 1000},
    actions_taken=[{"action": "analyze", "result": "success"}],
    decisions_made=[{"decision": "use_tool", "confidence": 0.9}],
    outcome=ExperienceOutcome.SUCCESS,
    outcome_details="Task completed successfully",
    reward_signal=0.8,
    key_learnings=["Tool selection improved outcome"],
)

# Record a mistake
mistake_id = engine.record_mistake(
    agent_id=agent_id,
    category=MistakeCategory.JUDGMENT_ERROR,
    severity=MistakeSeverity.MEDIUM,
    task_context="User asked for file edit",
    agent_action="Edited wrong file",
    expected_action="Edit specified file",
    actual_outcome="Wrong file modified",
    expected_outcome="Correct file modified",
    root_cause="Misread file path",
)

# Apply correction
engine.apply_correction(
    mistake_id=mistake_id,
    correction="Added path verification step",
    corrected_by="supervisor-1",
    lesson_learned="Always verify file paths before editing",
    prevention_strategy="Confirm file path matches user intent",
)

# Register and practice a skill
skill_id = engine.register_skill(
    agent_id=agent_id,
    name="File Operations",
    category="core",
    description="Ability to correctly perform file operations",
    initial_level=SkillLevel.BEGINNER,
)

engine.record_practice(
    skill_id=skill_id,
    success=True,
    performance_score=0.85,
    notes="Successfully edited correct file",
)

# Identify retraining needs
needs = engine.identify_retraining_needs(agent_id, days=30)
print(f"Identified {needs['needs_identified']} retraining needs")

# Generate curriculum for a need
if needs["needs"]:
    curriculum = engine.generate_curriculum(agent_id, needs["needs"][0]["need_id"])
    print(f"Generated curriculum: {curriculum['title']}")

# Get learning profile
profile = engine.get_agent_learning_profile(agent_id)
print(f"Overall health score: {profile['overall_health_score']:.2f}")
```

## Memory Integration

```python
from agent_learning import (
    LearningMemoryStore,
    CachedLearningContext,
    LearningSessionManager,
)

# Create memory store
memory = LearningMemoryStore(graph)

# Store episodes
episode_id = memory.store_episode(
    agent_id=agent_id,
    episode_type="task_completion",
    content={"task": "Process request", "steps": [...]},
    outcome="success",
    emotional_valence=0.8,  # Positive experience
    importance=0.7,
    tags=["success", "efficient"],
)

# Store semantic knowledge
semantic_id = memory.store_semantic(
    agent_id=agent_id,
    concept="file_path_verification",
    category="best_practices",
    content="Always verify file paths before modification",
    confidence=0.9,
)

# Get cached context for task
cached = CachedLearningContext(
    memory_store=memory,
    mistake_store=engine.mistake,
    attention_store=engine.attention,
    supervision_store=engine.supervision,
    skill_store=engine.skill,
)

context = cached.get_context(
    agent_id=agent_id,
    task_type="file_operation",
    token_budget=2000,  # Fit within context window
)

# Use session manager
sessions = LearningSessionManager(memory)

session_id = sessions.start_session(
    agent_id=agent_id,
    task="Process file upload",
    task_type="file_processing",
)

# During session
sessions.add_learning(session_id, "Async processing is faster", 0.8)
sessions.add_mistake(session_id, "Forgot to validate file type", "low")

# End session
result = sessions.end_session(
    session_id=session_id,
    outcome="success",
    summary="File processed successfully",
    reward_signal=0.7,
)
```

## CLI Usage

```bash
# Show statistics
agent-learning stats --db ./learning.db

# Get agent learning profile
agent-learning profile --db ./learning.db --agent agent-1

# Identify retraining needs
agent-learning needs --db ./learning.db --agent agent-1 --days 30

# Get experiences for replay
agent-learning replay --db ./learning.db --agent agent-1 --limit 10

# Get mistake patterns
agent-learning patterns --db ./learning.db --agent agent-1

# Get skill summary
agent-learning skills --db ./learning.db --agent agent-1

# Apply skill decay
agent-learning decay --db ./learning.db --agent agent-1

# Run demo
agent-learning demo --db ./demo.db
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    AgentLearningEngine                       │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  Experience  │  │   Mistake    │  │  Attention   │       │
│  │    Store     │  │    Store     │  │    Store     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │ Supervision  │  │    Skill     │                          │
│  │    Store     │  │    Store     │                          │
│  └──────────────┘  └──────────────┘                          │
├─────────────────────────────────────────────────────────────┤
│                    RetrainingEngine                          │
│  ┌──────────────┐  ┌──────────────┐                          │
│  │    Need      │  │  Curriculum  │                          │
│  │    Store     │  │    Store     │                          │
│  └──────────────┘  └──────────────┘                          │
├─────────────────────────────────────────────────────────────┤
│                   Memory Integration                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Learning   │  │   Cached     │  │   Session    │       │
│  │MemoryStore   │  │LearningCtx   │  │  Manager     │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                       ISONGraph                              │
└─────────────────────────────────────────────────────────────┘
```

## Learning Data Model

### Node Types

- `experience` - Recorded experiences
- `mistake` - Recorded mistakes
- `mistake_pattern` - Detected mistake patterns
- `attention_record` - Attention events
- `missed_element_pattern` - Frequently missed elements
- `supervision_record` - Supervision events
- `skill` - Agent skills
- `practice_record` - Skill practice sessions
- `retraining_need` - Identified retraining needs
- `curriculum` - Generated curricula
- `episode` - Episodic memories
- `semantic_memory` - Consolidated knowledge
- `procedural_memory` - Procedures/skills

### Edge Types

- `LEARNED_FROM` - Learning derived from experience/mistake
- `SIMILAR_TO` - Similar mistakes
- `INFLUENCED` - Attention influenced decision
- `SUPERVISED_BY` - Action supervised by reviewer
- `REQUIRES` - Skill prerequisite
- `DEVELOPED_BY` - Skill developed by learning event
- `ADDRESSED_BY` - Need addressed by curriculum
- `DERIVED_FROM` - Semantic memory from episodes

## Testing

```bash
# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=agent_learning --cov-report=html
```

## License

MIT License
