# ISONGraph Tools - Comprehensive Documentation

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Core Tools](#core-tools)
   - [Format Converters](#format-converters)
   - [Schema Generator](#schema-generator)
   - [ISON Cache](#ison-cache)
4. [Agent AI Development Tools](#agent-ai-development-tools)
   - [Agent Memory](#agent-memory)
   - [Agent Governance](#agent-governance)
   - [Agent Learning](#agent-learning)
5. [Regulatory Compliance Tools](#regulatory-compliance-tools)
   - [GDPR Governance](#gdpr-governance)
   - [CCPA Governance](#ccpa-governance)
   - [PII Governance](#pii-governance)
   - [EU AI Act Governance](#eu-ai-act-governance)
   - [Medical/HIPAA Governance](#medicalhipaa-governance)
   - [Unified Governance](#unified-governance)
6. [Code Analysis Tools](#code-analysis-tools)
   - [Code Flow Graph](#code-flow-graph)
7. [IDE Extensions](#ide-extensions)
   - [VSCode ISON Language](#vscode-ison-language)
   - [VSCode ISONGraph](#vscode-isongraph)
8. [Agentic AI Development Specifications](#agentic-ai-development-specifications)
9. [Integration Patterns](#integration-patterns)
10. [API Reference](#api-reference)

---

## Overview

The ISONGraph Tools folder is a comprehensive toolkit designed for building **Agentic AI systems** with:

- **Token-efficient data formats** (72% reduction vs JSON)
- **Persistent agent memory** across sessions
- **Governance and compliance** frameworks
- **Regulatory compliance** (GDPR, CCPA, HIPAA, EU AI Act)
- **Code analysis** and flow graphs
- **IDE support** for ISON format

### Key Benefits for Agentic AI

| Capability | Tool | Benefit |
|------------|------|---------|
| Memory Persistence | Agent Memory | Agents remember context across sessions |
| Governance Control | Agent Governance | Safe, auditable agent actions |
| Learning from Mistakes | Agent Learning | Continuous improvement |
| Regulatory Compliance | *-governance tools | Legal compliance (GDPR, HIPAA, etc.) |
| Token Efficiency | ISON Cache | 72% token savings for LLM context |
| Code Understanding | Code Flow Graph | Agents understand codebase structure |

---

## Architecture

```
tools/
├── converters/              # Format conversion (GraphML, RDF, CSV, Cypher, DOT)
├── schema-generator/        # Auto-generate schemas from data
├── ison-cache/              # Token-efficient caching for LLMs
│
├── agent-memory/            # Persistent memory for coding agents
├── agent-governance/        # Governance framework (15 domains)
├── agent-learning/          # Experience recording & retraining
│
├── gdpr-governance/         # EU GDPR compliance
├── ccpa-governance/         # California CCPA/CPRA compliance
├── pii-governance/          # PII detection & classification
├── eu-ai-act-governance/    # EU AI Act compliance
├── medical-governance/      # HIPAA compliance
├── unified-governance/      # Cross-regulation integration
│
├── code-flow-graph/         # Code structure analysis
├── vscode-ison/             # VSCode ISON language support
├── vscode-isongraph/        # VSCode graph visualization
└── playground/              # Interactive playground
```

---

## Core Tools

### Format Converters

**Location:** `tools/converters/`

Convert between ISONGraph and popular graph formats.

#### Supported Formats

| Format | Import | Export | Use Case |
|--------|--------|--------|----------|
| GraphML | Yes | Yes | Gephi, yEd visualization |
| RDF/Turtle | Yes | Yes | Semantic web, ontologies |
| N-Triples | No | Yes | Streaming RDF |
| CSV | Yes | Yes | Spreadsheets, bulk import |
| Neo4j Cypher | No | Yes | Graph database import |
| DOT/Graphviz | No | Yes | SVG/PNG visualization |

#### Programmatic Usage

```python
from tools.converters import (
    GraphMLConverter,
    RDFConverter,
    CSVConverter,
    CypherConverter,
    DOTConverter
)
from ison_graph import ISONGraph

# Create a graph
graph = ISONGraph("social")
graph.add_node("person", "alice", {"name": "Alice", "age": 30})
graph.add_node("person", "bob", {"name": "Bob", "age": 25})
graph.add_edge("KNOWS", ("person", "alice"), ("person", "bob"), {"since": 2020})

# Export to various formats
graphml = GraphMLConverter().to_graphml(graph)
turtle = RDFConverter(base_uri="http://example.org/").to_turtle(graph)
nodes_csv, edges_csv = CSVConverter().to_csv(graph)
cypher = CypherConverter().to_cypher(graph, mode="merge")
dot = DOTConverter().to_dot(graph)

# Save visualizations
DOTConverter().save_svg(graph, "graph.svg")
DOTConverter().save_png(graph, "graph.png")
```

#### CLI Usage

```bash
# Convert formats
ison-convert input.json output.ison
ison-convert graph.ison graph.graphml
ison-convert graph.ison import.cypher --cypher-mode merge
ison-convert graph.ison graph.ttl --base-uri https://myproject.org/
```

---

### Schema Generator

**Location:** `tools/schema-generator/`

Automatically generate ISONGraph schemas from JSON data by analyzing structure and inferring types.

#### Features

- **Type inference**: string, int, float, bool
- **Constraint detection**: min/max values, string lengths
- **Enum detection**: Low-cardinality fields
- **Pattern recognition**: email, URL, date, UUID, phone

#### Programmatic Usage

```python
from tools.schema_generator import SchemaGenerator, SchemaFormatter

# Sample data
data = {
    "nodes": [
        {"type": "person", "id": "1", "name": "Alice", "age": 30, "email": "alice@example.com"},
        {"type": "company", "id": "acme", "name": "Acme Corp", "size": "large"}
    ],
    "edges": [
        {"rel_type": "WORKS_AT", "source": {"type": "person", "id": "1"},
         "target": {"type": "company", "id": "acme"}, "properties": {"role": "Engineer"}}
    ]
}

# Generate schema
generator = SchemaGenerator(
    infer_constraints=True,
    infer_enums=True,
    infer_patterns=True
)
schema = generator.generate(data, name="organization")

# Output formats
python_code = generator.to_python(schema)       # Python code
json_schema = SchemaFormatter.to_json(schema)   # JSON Schema
ts_code = SchemaFormatter.to_typescript(schema) # TypeScript
ison_schema = SchemaFormatter.to_ison_schema(schema)  # ISON
```

---

### ISON Cache

**Location:** `tools/ison-cache/`

Token-efficient caching system optimized for LLM context injection.

#### Features

- **72% token reduction** compared to JSON
- **Token budget management** for LLM context windows
- **Graph traversal caching** with multi-hop support
- **Multiple backends**: Memory, SQLite, Redis
- **Embedding support** for vector similarity search

#### Programmatic Usage

```python
from ison_cache import ISONCache, ISONGraphCache, TokenBudget

# Basic key-value cache
cache = ISONCache()
cache.set("user:101", {"id": 101, "name": "Alice", "email": "alice@example.com"})
value = cache.get("user:101")  # Returns ISON-formatted string

# Graph cache with traversal
graph_cache = ISONGraphCache()
graph_cache.set_graph("session:abc", entities, relations)
subgraph = graph_cache.traverse("user:101", max_hops=2)

# Token-budgeted retrieval (perfect for LLM context)
result = cache.get_within_budget(["user:*"], token_budget=2000)

# Token budget management
budget = TokenBudget(max_tokens=4000)
budget.allocate("system_prompt", 500)
budget.allocate("context", 2000)
budget.allocate("history", 1000)
remaining = budget.remaining()  # 500 tokens for response
```

#### Agentic AI Integration

```python
from agent_memory import AgentMemory
from ison_cache import ISONCache

# Create memory with token-efficient caching
memory = AgentMemory("project")
cache = ISONCache()

# Before each LLM call, get context within budget
context = memory.get_coding_context(task="fix auth bug", files=["auth.py"])
cached_context = cache.format_for_llm(context, token_budget=2000)

# Use in LLM prompt
prompt = f"Context:\n{cached_context}\n\nTask: fix auth bug"
```

---

## Agent AI Development Tools

### Agent Memory

**Location:** `tools/agent-memory/`

Persistent graph-based memory system for AI coding agents.

#### Memory Types (12 Stores)

| Store | Purpose | Key Methods |
|-------|---------|-------------|
| `CodebaseStore` | Architecture & module understanding | `add_module()`, `get_module()` |
| `DecisionStore` | Architectural Decision Records | `add_decision()`, `query_decisions()` |
| `ConventionStore` | Code style and patterns | `add()`, `get_for_file()` |
| `BugPatternStore` | Historical bugs and fixes | `add_pattern()`, `add_fix_pattern()` |
| `DependencyStore` | Library quirks and workarounds | `add_dependency()`, `add_quirk()` |
| `TestPatternStore` | Testing conventions | `add_pattern()` |
| `PerformanceStore` | Hot paths and constraints | `add_hotpath()` |
| `TechDebtStore` | Refactoring history | `add_debt()` |
| `TeamStore` | Who knows what | `add_expertise()`, `who_knows()` |
| `SessionStore` | Continuity between sessions | `start()`, `end()`, `handoff()` |
| `TemplateStore` | Code generation patterns | `add_template()` |
| `SkillStore` | Agent learning progression | `record_skill()`, `get_progression()` |

#### Additional Stores (Task Management)

| Store | Purpose |
|-------|---------|
| `TodoStore` | Task tracking with status |
| `GoalStore` | High-level goal tracking |
| `IssueStore` | Bug/issue tracking |

#### Programmatic Usage

```python
from agent_memory import AgentMemory, prepare_for_project

# Initialize memory for a project
memory = AgentMemory("my-project")

# Record conventions
memory.conventions.add(
    category="naming",
    rule="snake_case_functions",
    enforced_by="ruff"
)

# Record a decision
memory.decisions.add_decision(
    title="Use async/await",
    context="Need high concurrency for API handlers",
    consequences_positive=["Better throughput", "Non-blocking"],
    consequences_negative=["Complexity"]
)

# Record a bug pattern
memory.bugs.add_pattern(
    name="race_condition",
    signature="shared_state_without_lock",
    modules_affected=["cache", "session"]
)

# Query before coding
context = memory.get_coding_context(
    task="modify traversal module",
    files=["graph/traverse.py"]
)

# Save/load memory
memory.save("project-memory.ison")
memory = AgentMemory.load("project-memory.ison")
```

#### Session Workflow

```python
from agent_memory import AgentIntegration, prepare_for_project

# Start session
agent = prepare_for_project("/path/to/project")
session_id, context = agent.start_session("Add Redis caching layer")

# Get context for LLM prompt
prompt_context = context.to_prompt()

# Check approach before coding
warnings = agent.check_before_coding("Use global dict for cache")
if warnings:
    print(f"Warnings: {warnings}")

# Record decisions during coding
agent.record_decision("Use Redis over in-memory dict", "Need persistence")

# Record partial work
agent.record_partial_work("code", "src/cache/redis.py", "skeleton_only")

# End session
summary = agent.end_session(completion=0.6, outcome="partial")

# Next session: Get handoff
handoff = agent.get_session_handoff()
print(handoff)  # Shows open questions, partial work, etc.
```

---

### Agent Governance

**Location:** `tools/agent-governance/`

Comprehensive governance framework with **15 domains** for safe, auditable AI agents.

#### Governance Domains

| Domain | Description |
|--------|-------------|
| 1. Authority & Delegation | Who can authorize what actions |
| 2. Policy Engine | Rules, conditions, and evaluation |
| 3. Compliance Framework | GDPR, HIPAA, SOX, EU AI Act mapping |
| 4. Audit Trail | Decision provenance and accountability |
| 5. Risk Assessment | Threats, controls, and mitigation |
| 6. Human Oversight | Escalation and review workflows |
| 7. Resource Governance | Budgets and allocation |
| 8. Multi-Agent Coordination | Group governance protocols |
| 9. Ethics & Values | Value alignment and dilemmas |
| 10. Capability Governance | Feature flags and grants |
| 11. Incident Response | Detection and recovery |
| 12. Meta-Governance | Governing the governance |
| 13. Cross-Organizational | Trust and agreements |
| 14. Temporal Governance | Time-bound authority |
| 15. Observability | Metrics and dashboards |

#### Programmatic Usage

```python
from agent_governance import GovernanceEngine, quick_governance, AuthorityLevel

# Quick setup with defaults
engine = quick_governance("my-agent-system", setup_defaults=True)

# Register agents
engine.register_agent("agent_1", "Research Agent", AuthorityLevel.LIMITED)
engine.register_agent("agent_2", "Writer Agent", AuthorityLevel.DELEGATED)

# Register human overseer
engine.register_human("human_1", "Admin Sarah", AuthorityLevel.ELEVATED)

# Grant authority
engine.authority.grant_authority("agent_1", "read_public", "public_read_only")

# Check if action is permitted
result = engine.check_action(
    agent_id="agent_1",
    action="write_external",
    context={"data_classification": "internal"}
)

if result["permitted"]:
    # Proceed with action
    pass
elif result["escalation_required"]:
    # Wait for human approval
    escalation_id = result["escalation_id"]
else:
    # Action denied
    print(result["reason"])
```

#### Policy Enforcement

```python
# Create policies
engine.add_policy("data_classification", [
    {
        "condition": "data_classification == 'secret'",
        "action": "deny_external",
        "description": "Secret data cannot leave"
    },
    {
        "condition": "data_classification == 'internal'",
        "action": "allow_internal",
        "description": "Internal data for internal use"
    }
], priority=100)

# Evaluate policies
result = engine.policy.evaluate({"data_classification": "secret"})
print(result["result"])  # "deny_external"
```

#### Escalation Workflow

```python
from agent_governance import EscalationLevel

# Add reviewers
engine.escalation.add_reviewer("Security Team", ["security", "data"], "24/7")

# Add triggers
engine.escalation.add_trigger(
    "confidence < 0.7",
    EscalationLevel.L3_OPERATOR,
    timeout="1hr",
    category="uncertain_decision"
)

# Trigger escalation
escalation_ids = engine.escalation.trigger_escalation({
    "confidence": 0.6,
    "agent_id": "agent_1",
    "action": "write_external"
})

# Resolve escalation (by human)
engine.escalation.resolve_escalation(
    escalation_ids[0],
    decision="approved",
    reason="Action verified safe by human reviewer"
)
```

#### Multi-Agent Coordination

```python
# Create agent group
group_id = engine.coordination.create_group(
    "research_swarm",
    "Parallel research task execution",
    "dynamic"
)

# Assign roles
engine.coordination.assign_role(group_id, "agent_1", "coordinator", "task_assignment")
engine.coordination.assign_role(group_id, "agent_2", "worker", "execute_assigned")

# Add protocols
engine.coordination.add_protocol(
    group_id,
    "task_distribution",
    "coordinator_assigns_round_robin",
    "state_validator"
)

# Check coordination authority
auth = engine.coordination.check_coordination_authority("agent_1", group_id, "task_assignment")
```

---

### Agent Learning

**Location:** `tools/agent-learning/`

Comprehensive learning and retraining system for AI agents.

#### Features

- **Experience recording** and replay learning
- **Mistake tracking** with pattern detection
- **Attention monitoring** and improvement
- **Supervision integration**
- **Skill development** with spaced repetition
- **Automated retraining** curriculum generation

#### Programmatic Usage

```python
from agent_learning import (
    AgentLearningEngine,
    MistakeCategory,
    MistakeSeverity,
    ExperienceOutcome
)
from ison_graph import ISONGraph

# Initialize
graph = ISONGraph("learning-db")
engine = AgentLearningEngine(graph)

# Record an experience
exp_id = engine.record_experience(
    agent_id="agent-1",
    task="Complete user request",
    task_type="task_completion",
    environment={"platform": "production"},
    initial_state={"context_length": 1000},
    actions_taken=[{"action": "analyze", "result": "success"}],
    decisions_made=[{"decision": "use_tool", "confidence": 0.9}],
    outcome=ExperienceOutcome.SUCCESS,
    reward_signal=0.8,
    key_learnings=["Tool selection improved outcome"],
)

# Record a mistake
mistake_id = engine.record_mistake(
    agent_id="agent-1",
    category=MistakeCategory.JUDGMENT_ERROR,
    severity=MistakeSeverity.MEDIUM,
    task_context="User asked for file edit",
    agent_action="Edited wrong file",
    expected_action="Edit specified file",
    root_cause="Misread file path",
)

# Identify retraining needs
needs = engine.identify_retraining_needs("agent-1")

# Generate curriculum
curriculum = engine.generate_curriculum("agent-1", needs["needs"][0]["need_id"])
```

---

## Regulatory Compliance Tools

### GDPR Governance

**Location:** `tools/gdpr-governance/`

EU General Data Protection Regulation compliance.

#### Coverage

| Article | Feature |
|---------|---------|
| Art. 6 | Lawful basis management |
| Art. 7 | Consent management |
| Art. 15-22 | Data subject rights |
| Art. 30 | Records of Processing Activities |
| Art. 33-34 | Data breach notification |
| Art. 35 | Data Protection Impact Assessments |
| Art. 44-49 | International transfers |

```python
from gdpr_governance import GDPRGovernance, LawfulBasis, DataSubjectRight

graph = ISONGraph()
gdpr = GDPRGovernance(graph)

# Register processing activity (Article 30)
activity_id = gdpr.processing.register_activity(
    name="Customer Newsletter",
    purpose="Marketing communications",
    lawful_basis=LawfulBasis.CONSENT,
    data_categories=["basic_identity", "contact"],
    retention_period="Until consent withdrawn",
)

# Record consent (Article 7)
consent_id = gdpr.consent.record_consent(
    data_subject_id="user123",
    purpose="marketing_newsletter",
    evidence="web_form_checkbox",
)

# Handle data subject request (Articles 15-22)
request_id = gdpr.rights.submit_request(
    data_subject_id="user123",
    right_type=DataSubjectRight.ACCESS,
)

# Get compliance status
status = gdpr.get_compliance_status()
```

---

### CCPA Governance

**Location:** `tools/ccpa-governance/`

California Consumer Privacy Act / CPRA compliance.

#### Coverage

- Consumer registration and PI inventory
- Consumer Rights (Know, Delete, Correct, Opt-Out, Limit SPI)
- Sale and Sharing of Personal Information
- "Do Not Sell" / "Do Not Share" opt-outs
- Global Privacy Control (GPC) signal handling
- Service Provider contracts

```python
from ccpa_governance import CCPAGovernance, ConsumerRight

graph = ISONGraph()
ccpa = CCPAGovernance(graph)

# Register consumer
consumer_id = ccpa.consumers.register_consumer(
    consumer_id="user123",
    email="user@example.com",
    is_california_resident=True,
)

# Process opt-out
ccpa.process_opt_out(
    consumer_id="user123",
    opt_out_sale=True,
    opt_out_share=True,
)

# Handle consumer request
request_id = ccpa.rights.submit_request(
    consumer_id="user123",
    right_type=ConsumerRight.RIGHT_TO_KNOW,
)
```

---

### PII Governance

**Location:** `tools/pii-governance/`

PII detection, classification, and governance.

#### Features

- **PII detection**: Regex, column name inference
- **Sensitivity mapping**: Public to highly sensitive
- **Data source inventory**
- **Risk assessment and scoring**
- **Cross-regulation mapping** (GDPR, CCPA, HIPAA, PCI-DSS)

```python
from pii_governance import PIIGovernance, DataSourceType

graph = ISONGraph()
pii = PIIGovernance(graph)

# Register data source
pii.inventory.register_data_source(
    source_id="customer_db",
    name="Customer Database",
    source_type=DataSourceType.DATABASE,
    owner="data_team",
)

# Classify PII fields
pii.classification.classify_field(
    field_name="email",
    field_id="customers.email",
    source_id="customer_db",
    sample_values=["user@example.com"],
)

# Scan text for PII
detections = pii.scan_text_for_pii("Contact: john@email.com, SSN: 123-45-6789")

# Get governance report
report = pii.get_governance_report()
```

---

### EU AI Act Governance

**Location:** `tools/eu-ai-act-governance/`

EU AI Act (Regulation 2024/1689) compliance.

#### Coverage

| Article | Feature |
|---------|---------|
| Art. 5 | Prohibited practices detection |
| Art. 5-7 | Risk classification |
| Art. 8-15 | High-risk system requirements |
| Art. 43-49 | Conformity assessment |
| Art. 11, Annex IV | Technical documentation |
| Art. 10 | Data governance |
| Art. 14 | Human oversight |
| Art. 13, 50 | Transparency |
| Art. 72 | Post-market monitoring |
| Art. 73 | Incident reporting |
| Art. 51-56 | GPAI model governance |

```python
from eu_ai_act_governance import EUAIActGovernanceEngine, AIRiskLevel

graph = ISONGraph()
engine = EUAIActGovernanceEngine(graph)

# Onboard an AI system
result = engine.onboard_ai_system(
    name="Customer Service Bot",
    version="1.0",
    provider="My Company",
    intended_purpose="Customer service automation",
    technical_description="NLP-based chatbot"
)

# Classify risk
classification = engine.classify_system_risk(
    system_id=result["system_id"],
    assessor="compliance_officer"
)

# Check for prohibited practices
prohibited = engine.check_prohibited_practices(result["system_id"])

# Get compliance status
status = engine.get_system_compliance_status(result["system_id"])
```

---

### Medical/HIPAA Governance

**Location:** `tools/medical-governance/`

HIPAA-compliant governance for medical AI systems.

#### Coverage (45 CFR)

| Regulation | Feature |
|------------|---------|
| 164.502(b) | Minimum Necessary Standard |
| 164.508/522 | Consent Management |
| 164.312(a) | Access Control & Authorization |
| 164.312(b), 164.528 | Audit Trail |
| 164.308(b) | Business Associate Governance |
| 164.400-414 | Breach Notification |
| 164.520-528 | Patient Rights |
| 164.308(a)(3), 164.530(e) | Workforce Training |

```python
from medical_governance import HIPAAGovernanceEngine, AccessPurpose

graph = ISONGraph("medical_governance")
engine = HIPAAGovernanceEngine(graph)

# Authorize PHI access
result = engine.authorize_phi_access(
    actor_id="dr_smith",
    actor_type="workforce",
    patient_id="patient_123",
    phi_elements=["diagnosis", "medications"],
    purpose=AccessPurpose.TREATMENT
)

# Apply minimum necessary
filtered = engine.apply_minimum_necessary(
    requestor="dr_smith",
    patient_id="patient_123",
    requested_phi=["diagnosis", "medications", "social_history"],
    purpose=AccessPurpose.TREATMENT
)

# Get compliance dashboard
dashboard = engine.get_compliance_dashboard()
```

---

### Unified Governance

**Location:** `tools/unified-governance/`

Integrates Agent, GDPR, CCPA, and PII governance into a unified framework.

#### Features

- Cross-domain compliance checking
- PII to regulation mapping
- Subject unification (GDPR data subjects + CCPA consumers)
- Agent-PII access control
- Unified audit trails
- Cross-regulation risk assessment

```python
from unified_governance import UnifiedGovernanceEngine, quick_unified_governance

# Quick setup
engine = quick_unified_governance(setup_defaults=True)

# Register unified subject
engine.register_subject(
    subject_id="user_123",
    email="user@example.com",
    gdpr_data_subject_id="gdpr_ds_123",
    ccpa_consumer_id="ccpa_c_123",
)

# Grant agent PII access
engine.grant_agent_pii_access(
    agent_id="agent_1",
    pii_types=["email", "phone"],
    purpose="customer_support",
    legal_basis="legitimate_interest",
)

# Check compliance before action
result = engine.check_compliance(
    agent_id="agent_1",
    action="read_personal_data",
    pii_types=["email"],
    data_subject_id="user_123",
)

if result["permitted"]:
    # Record the action
    engine.record_agent_action(
        agent_id="agent_1",
        action="read_personal_data",
        pii_types=["email"],
        outcome="success",
    )
```

---

## Code Analysis Tools

### Code Flow Graph

**Location:** `tools/code-flow-graph/`

Generate code flow graphs from repositories.

#### Features

- Analyze GitHub repositories or local directories
- Create property graphs of code structure
- Node types: Files, classes, functions, modules
- Edge types: Imports, calls, definitions, inheritance
- Query with ISONGraph query engine

```python
from code_flow_graph import CodeFlowAnalyzer, analyze_github, analyze_local

# Analyze GitHub repository
analyzer = CodeFlowAnalyzer()
graph = analyzer.analyze_repo("https://github.com/user/repo")

# Or analyze local directory
graph = analyze_local("/path/to/project")

# Query the graph
from ison_graph.query import QueryEngine
engine = QueryEngine(graph)

# Find what calls a function
result = engine.execute("TRAVERSE function:main <- CALLS <- function")

# Find import chain
result = engine.execute("TRAVERSE file:main.py -> IMPORTS -> file MAX 5")

# Find class hierarchy
result = engine.execute("TRAVERSE class:BaseHandler -> INHERITS -> class")
```

#### Integration with Agent Memory

```python
from agent_memory import AgentMemory
from code_flow_graph import enrich_memory_with_code_flow

memory = AgentMemory("my-project")
enrich_memory_with_code_flow(memory, "/path/to/project")

# Now memory includes code structure understanding
context = memory.get_coding_context(task="refactor auth module")
```

---

## IDE Extensions

### VSCode ISON Language

**Location:** `tools/vscode-ison/`

Syntax highlighting and language support for ISON format.

#### Features

- Syntax highlighting for `.ison` and `.isonl` files
- JSON to ISON conversion
- ISON to JSON conversion
- Document formatting
- Document validation
- Code snippets

#### Installation

```bash
cd tools/vscode-ison
npm install
npm run compile
# Then install the .vsix file in VS Code
```

#### Commands

- `ISON: Convert JSON to ISON`
- `ISON: Convert ISON to JSON`
- `ISON: Format Document`
- `ISON: Validate Document`

### VSCode ISONGraph

**Location:** `tools/vscode-isongraph/`

Graph visualization and outline for ISONGraph files.

#### Features

- Graph outline view
- Node types provider
- Edge types provider
- ISON file parsing

---

## Agentic AI Development Specifications

### Complete Agent Workflow

```python
"""
Complete Agent Workflow with Memory, Governance, and Learning
"""
from ison_graph import ISONGraph
from agent_memory import AgentMemory, prepare_for_project
from agent_governance import GovernanceEngine, quick_governance
from agent_learning import AgentLearningEngine

# === SETUP ===

# 1. Initialize memory for project
memory = AgentMemory("my-project")
agent = prepare_for_project("/path/to/project")

# 2. Initialize governance
governance = quick_governance("my-agent", setup_defaults=True)
governance.register_agent("agent_1", "Coding Agent", "delegated")

# 3. Initialize learning
learning_graph = ISONGraph("learning-db")
learning = AgentLearningEngine(learning_graph)

# === SESSION START ===

# Start session with context
session_id, context = agent.start_session("Implement user authentication")

# Get token-efficient context for LLM
prompt_context = context.to_prompt()

# === BEFORE EACH ACTION ===

def execute_action(agent_id, action, context):
    # Check governance
    result = governance.check_action(agent_id, action, context)

    if not result["permitted"]:
        if result["escalation_required"]:
            # Wait for human approval
            return {"status": "pending_approval", "escalation_id": result["escalation_id"]}
        else:
            return {"status": "denied", "reason": result["reason"]}

    # Check against known bugs/issues
    warnings = agent.check_before_coding(action)
    if warnings:
        # Log warnings, possibly escalate
        pass

    return {"status": "approved"}

# === DURING CODING ===

# Record decisions
agent.record_decision(
    "Use JWT for authentication",
    "Stateless, works with microservices"
)

# Prevent known bugs
agent.prevent_bug("race_condition", "src/auth/session.py:45")

# === AFTER ACTION ===

def record_outcome(agent_id, task, outcome, details):
    # Record in memory
    if outcome == "success":
        agent.learn_convention("auth", "Use bcrypt for password hashing")

    # Record experience for learning
    learning.record_experience(
        agent_id=agent_id,
        task=task,
        outcome=outcome,
        key_learnings=details.get("learnings", [])
    )

    # If mistake, record for future prevention
    if outcome == "failure":
        learning.record_mistake(
            agent_id=agent_id,
            category="implementation_error",
            severity="medium",
            task_context=task,
            agent_action=details.get("action"),
            expected_action=details.get("expected"),
            root_cause=details.get("root_cause")
        )

# === SESSION END ===

summary = agent.end_session(
    completion=1.0,
    outcome="success",
    lessons=["JWT refresh tokens need secure storage"]
)

# Save memory
agent.memory.save("project-memory.ison")
```

### Governed Agent with Compliance

```python
"""
Agent with Regulatory Compliance (GDPR + CCPA)
"""
from unified_governance import UnifiedGovernanceEngine, quick_unified_governance

# Initialize unified governance
unified = quick_unified_governance(setup_defaults=True)

# Agent needs to read user data
async def agent_read_user_data(agent_id: str, user_id: str, data_fields: list):
    # Check compliance before action
    result = unified.check_compliance(
        agent_id=agent_id,
        action="read_personal_data",
        pii_types=data_fields,
        data_subject_id=user_id,
    )

    if not result["permitted"]:
        raise PermissionError(f"Access denied: {result['reason']}")

    # Get data with minimum necessary principle
    allowed_fields = result.get("allowed_fields", data_fields)

    # Perform action
    user_data = await fetch_user_data(user_id, allowed_fields)

    # Record action for audit
    unified.record_agent_action(
        agent_id=agent_id,
        action="read_personal_data",
        pii_types=allowed_fields,
        data_source="user_db",
        outcome="success",
    )

    return user_data
```

### Multi-Agent Coordination

```python
"""
Multi-Agent System with Governance
"""
from agent_governance import GovernanceEngine, quick_governance

engine = quick_governance("multi-agent-system", setup_defaults=True)

# Create agent group
group_id = engine.coordination.create_group(
    "research_team",
    "Parallel research and synthesis",
    "dynamic"
)

# Register agents with roles
engine.register_agent("researcher_1", "Research Agent 1", "limited")
engine.register_agent("researcher_2", "Research Agent 2", "limited")
engine.register_agent("synthesizer", "Synthesis Agent", "delegated")

# Assign roles in group
engine.coordination.assign_role(group_id, "synthesizer", "coordinator", "task_assignment")
engine.coordination.assign_role(group_id, "researcher_1", "worker", "research_only")
engine.coordination.assign_role(group_id, "researcher_2", "worker", "research_only")

# Add protocols
engine.coordination.add_protocol(
    group_id,
    "task_distribution",
    "coordinator_assigns",
    "coordinator"
)
engine.coordination.add_protocol(
    group_id,
    "conflict_resolution",
    "coordinator_arbitrates",
    "coordinator"
)

# Check coordination authority before inter-agent communication
def agent_assign_task(coordinator_id, worker_id, task):
    auth = engine.coordination.check_coordination_authority(
        coordinator_id, group_id, "task_assignment"
    )

    if not auth["authorized"]:
        raise PermissionError(f"Cannot assign: {auth['reason']}")

    # Proceed with assignment
    pass
```

---

## Integration Patterns

### Pattern 1: Token-Efficient Agent Context

```python
from agent_memory import AgentMemory
from ison_cache import ISONCache, TokenBudget

def get_agent_context(memory: AgentMemory, task: str, token_limit: int = 4000):
    """Get token-efficient context for LLM."""

    # Create budget
    budget = TokenBudget(max_tokens=token_limit)
    budget.allocate("system", 500)
    budget.allocate("context", 2500)
    budget.allocate("task", 500)
    budget.allocate("response", 500)

    # Get context within budget
    context = memory.get_coding_context(task=task)

    # Convert to ISON format (72% token savings)
    cache = ISONCache()
    ison_context = cache.format_for_llm(context, budget.allocation("context"))

    return {
        "context": ison_context,
        "tokens_used": cache.count_tokens(ison_context),
        "tokens_remaining": budget.remaining()
    }
```

### Pattern 2: Governed Code Modification

```python
from agent_governance import GovernanceEngine
from agent_memory import AgentMemory

def safe_code_modification(
    governance: GovernanceEngine,
    memory: AgentMemory,
    agent_id: str,
    file_path: str,
    modification: str
):
    """Safely modify code with governance checks."""

    # Check governance
    result = governance.check_action(
        agent_id=agent_id,
        action="modify_code",
        context={
            "file_path": file_path,
            "modification_type": "edit"
        }
    )

    if not result["permitted"]:
        return {"success": False, "reason": result["reason"]}

    # Check against known issues
    warnings = memory.check_before_coding(modification)
    if warnings:
        # Escalate if needed
        governance.escalation.trigger_escalation({
            "agent_id": agent_id,
            "action": "modify_code",
            "warnings": warnings
        })

    # Perform modification
    # ...

    # Record decision
    memory.decisions.add_decision(
        title=f"Modified {file_path}",
        context=modification,
        consequences_positive=["Task completed"],
        consequences_negative=[]
    )

    return {"success": True}
```

### Pattern 3: Continuous Learning Agent

```python
from agent_learning import AgentLearningEngine, ExperienceOutcome

def learning_agent_loop(
    learning: AgentLearningEngine,
    agent_id: str
):
    """Agent that learns from every interaction."""

    while True:
        task = get_next_task()

        # Get historical context
        similar_experiences = learning.get_similar_experiences(agent_id, task)
        past_mistakes = learning.get_relevant_mistakes(agent_id, task)

        # Execute with awareness
        try:
            result = execute_task(task, similar_experiences, past_mistakes)

            # Record success
            learning.record_experience(
                agent_id=agent_id,
                task=task.description,
                outcome=ExperienceOutcome.SUCCESS,
                reward_signal=result.quality_score,
                key_learnings=result.learnings
            )

        except Exception as e:
            # Record failure for learning
            learning.record_mistake(
                agent_id=agent_id,
                category="execution_error",
                severity="medium",
                task_context=task.description,
                agent_action=str(e),
                root_cause=analyze_error(e)
            )

        # Periodic retraining check
        if should_check_retraining():
            needs = learning.identify_retraining_needs(agent_id)
            if needs["needs"]:
                curriculum = learning.generate_curriculum(
                    agent_id, needs["needs"][0]["need_id"]
                )
                # Apply curriculum...
```

---

## API Reference

### Quick Start Functions

```python
# Agent Memory
from agent_memory import prepare_for_project, quick_context
agent = prepare_for_project("/path/to/project")
context = quick_context("/path/to/project", task="fix bug")

# Agent Governance
from agent_governance import quick_governance
engine = quick_governance("my-system", setup_defaults=True)

# Unified Governance
from unified_governance import quick_unified_governance
unified = quick_unified_governance(setup_defaults=True)

# Code Flow
from code_flow_graph import analyze_local, analyze_github
graph = analyze_local("/path/to/project")
graph = analyze_github("https://github.com/user/repo")

# Schema Generation
from tools.schema_generator import generate_schema
schema = generate_schema(data, name="my_schema", output_format="python")
```

### Core Classes

| Class | Module | Purpose |
|-------|--------|---------|
| `AgentMemory` | agent_memory | Persistent memory store |
| `AgentIntegration` | agent_memory | Session-aware agent interface |
| `GovernanceEngine` | agent_governance | Action governance |
| `AgentLearningEngine` | agent_learning | Experience & learning |
| `GDPRGovernance` | gdpr_governance | GDPR compliance |
| `CCPAGovernance` | ccpa_governance | CCPA compliance |
| `PIIGovernance` | pii_governance | PII management |
| `EUAIActGovernanceEngine` | eu_ai_act_governance | EU AI Act compliance |
| `HIPAAGovernanceEngine` | medical_governance | HIPAA compliance |
| `UnifiedGovernanceEngine` | unified_governance | Cross-regulation |
| `CodeFlowAnalyzer` | code_flow_graph | Code analysis |
| `ISONCache` | ison_cache | Token-efficient cache |
| `ISONGraphCache` | ison_cache | Graph caching |
| `SchemaGenerator` | schema_generator | Schema generation |

### CLI Commands

```bash
# Format conversion
ison-convert input.json output.ison
ison-convert graph.ison graph.graphml

# Schema generation
python -m schema_generator graph.json -o schema.py
python -m schema_generator graph.json --format typescript -o schema.ts

# Agent memory CLI
python -m agent_memory.cli init /path/to/project
python -m agent_memory.cli stats
python -m agent_memory.cli export project-memory.json

# Governance CLI
python -m agent_governance.cli status
python -m agent_governance.cli audit --days 7
```

---

## Token Efficiency

ISON format provides significant token savings:

| Format | Tokens (relative) | Savings |
|--------|-------------------|---------|
| JSON | 100% | - |
| **ISON** | **28%** | **72%** |
| CSV | 40% | 60% |
| GraphML | 150% | -50% |
| Turtle | 80% | 20% |
| Cypher | 200% | -100% |

**For Agentic AI**: Use ISON format to fit more context in LLM windows.

---

## License

MIT License - see [LICENSE](../LICENSE) for details.

---

*Documentation generated for ISONGraph Tools v1.0.0*
