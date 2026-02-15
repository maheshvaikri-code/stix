# ISONGraph Unified MCP Server

A single MCP (Model Context Protocol) server that exposes **ALL** ISONGraph tools to AI agents, including Claude, GPT, and any MCP-compatible system.

## Overview

This MCP server provides **80+ tools** across 7 categories:

| Category | Tools | Description |
|----------|-------|-------------|
| **Converters** | 6 | GraphML, RDF, CSV, Cypher, DOT format conversion |
| **Schema** | 3 | Auto-generate schemas from data |
| **Cache** | 5 | Token-efficient caching (72% savings) |
| **Agent Memory** | 12 | Persistent memory across sessions |
| **Agent Governance** | 13 | Policy, escalation, multi-agent coordination |
| **Agent Learning** | 6 | Experience recording, mistake tracking |
| **Compliance** | 15+ | GDPR, CCPA, PII, EU AI Act, HIPAA |
| **Code Analysis** | 5 | Code flow graphs, call analysis |

## Quick Start

### Installation

```bash
# Install with all features
pip install isongraph-mcp[all]

# Or install specific features
pip install isongraph-mcp[memory,governance]  # Agent tools only
pip install isongraph-mcp[gdpr,ccpa,hipaa]    # Compliance only
```

### Running the Server

```bash
# Run directly
python -m isongraph_mcp.server

# Or use the CLI
isongraph-mcp
```

### Claude Desktop Configuration

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "isongraph": {
      "command": "python",
      "args": ["-m", "isongraph_mcp.server"]
    }
  }
}
```

### Cursor/VSCode Configuration

Add to MCP settings:

```json
{
  "mcp.servers": {
    "isongraph": {
      "command": "python",
      "args": ["-m", "isongraph_mcp.server"]
    }
  }
}
```

## Available Tools

### Converter Tools

| Tool | Description |
|------|-------------|
| `convert_to_graphml` | Convert ISONGraph to GraphML (Gephi/yEd) |
| `convert_to_rdf` | Convert to RDF/Turtle (semantic web) |
| `convert_to_csv` | Convert to CSV (nodes.csv, edges.csv) |
| `convert_to_cypher` | Convert to Neo4j Cypher statements |
| `convert_to_dot` | Convert to DOT/Graphviz for visualization |
| `import_from_graphml` | Import from GraphML format |

### Schema Generator Tools

| Tool | Description |
|------|-------------|
| `generate_schema` | Auto-generate schema from JSON data |
| `format_schema` | Format schema as Python/TypeScript/JSON |
| `analyze_data_structure` | Analyze graph data structure |

### ISON Cache Tools

| Tool | Description |
|------|-------------|
| `cache_set` | Store value in token-efficient cache |
| `cache_get` | Retrieve value in ISON format |
| `cache_get_within_budget` | Get values within token budget |
| `cache_graph_traverse` | Cache graph with traversal support |
| `count_tokens` | Count tokens for content |

### Agent Memory Tools

| Tool | Description |
|------|-------------|
| `memory_init` | Initialize memory for a project |
| `memory_get_context` | Get coding context (conventions, decisions, etc.) |
| `memory_add_convention` | Record a code convention |
| `memory_add_decision` | Record an architectural decision |
| `memory_add_bug_pattern` | Record a bug pattern for prevention |
| `memory_check_before_coding` | Check approach against known issues |
| `memory_session_start` | Start a coding session |
| `memory_session_end` | End session with summary |
| `memory_get_handoff` | Get session handoff for continuity |
| `memory_who_knows` | Find expertise for a topic |
| `memory_save` | Save memory to file |
| `memory_load` | Load memory from file |

### Agent Governance Tools

| Tool | Description |
|------|-------------|
| `governance_init` | Initialize governance engine |
| `governance_register_agent` | Register agent with authority level |
| `governance_check_action` | Check if action is permitted |
| `governance_add_policy` | Add governance policy with rules |
| `governance_evaluate_policy` | Evaluate policies against context |
| `governance_add_escalation_trigger` | Add escalation trigger |
| `governance_trigger_escalation` | Trigger escalation |
| `governance_resolve_escalation` | Resolve escalation (human) |
| `governance_assess_risk` | Get risk posture assessment |
| `governance_report_incident` | Report security incident |
| `governance_create_agent_group` | Create multi-agent group |
| `governance_assign_group_role` | Assign role in group |
| `governance_get_audit_trail` | Get decision audit trail |

### Agent Learning Tools

| Tool | Description |
|------|-------------|
| `learning_init` | Initialize learning engine |
| `learning_record_experience` | Record experience for learning |
| `learning_record_mistake` | Record mistake for prevention |
| `learning_identify_retraining_needs` | Identify retraining needs |
| `learning_generate_curriculum` | Generate retraining curriculum |
| `learning_get_skill_progression` | Get skill progression |

### GDPR Compliance Tools

| Tool | Description |
|------|-------------|
| `gdpr_register_processing` | Register processing activity (Art. 30) |
| `gdpr_record_consent` | Record consent (Art. 7) |
| `gdpr_submit_rights_request` | Submit data subject request (Art. 15-22) |
| `gdpr_report_breach` | Report data breach (Art. 33-34) |
| `gdpr_get_compliance_status` | Get compliance status |

### CCPA Compliance Tools

| Tool | Description |
|------|-------------|
| `ccpa_register_consumer` | Register California consumer |
| `ccpa_process_opt_out` | Process Do Not Sell/Share opt-out |
| `ccpa_submit_request` | Submit consumer rights request |
| `ccpa_get_compliance_status` | Get compliance status |

### PII Governance Tools

| Tool | Description |
|------|-------------|
| `pii_scan_text` | Scan text for PII |
| `pii_classify_field` | Classify data field for PII type |
| `pii_register_data_source` | Register data source |
| `pii_get_governance_report` | Get governance report |

### EU AI Act Tools

| Tool | Description |
|------|-------------|
| `eu_ai_act_onboard_system` | Onboard AI system |
| `eu_ai_act_classify_risk` | Classify risk level (Art. 5-7) |
| `eu_ai_act_check_prohibited` | Check prohibited practices (Art. 5) |
| `eu_ai_act_get_compliance_status` | Get compliance status |

### HIPAA Tools

| Tool | Description |
|------|-------------|
| `hipaa_authorize_phi_access` | Authorize PHI access |
| `hipaa_apply_minimum_necessary` | Apply minimum necessary standard |
| `hipaa_get_compliance_dashboard` | Get compliance dashboard |

### Unified Compliance Tools

| Tool | Description |
|------|-------------|
| `unified_check_compliance` | Cross-regulation compliance check |
| `unified_grant_agent_pii_access` | Grant agent PII access |
| `unified_record_agent_action` | Record action for audit |

### Code Flow Tools

| Tool | Description |
|------|-------------|
| `codeflow_analyze_local` | Analyze local directory |
| `codeflow_analyze_github` | Analyze GitHub repository |
| `codeflow_query` | Query code flow graph |
| `codeflow_get_function_callers` | Find function callers |
| `codeflow_get_import_chain` | Get import chain |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Client (Claude, etc.)                │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ MCP Protocol (stdio/SSE)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  ISONGraph Unified MCP Server               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                    Tool Router                       │   │
│  │  (80+ tools across all categories)                   │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                              │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │Converters│ Schema   │  Cache   │  Memory  │Governance│  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
│  ┌──────────┬──────────┬──────────┬──────────┬──────────┐  │
│  │ Learning │   GDPR   │   CCPA   │   PII    │  EU AI   │  │
│  └──────────┴──────────┴──────────┴──────────┴──────────┘  │
│  ┌──────────┬──────────┬──────────────────────────────────┐│
│  │  HIPAA   │ Unified  │        Code Flow                 ││
│  └──────────┴──────────┴──────────────────────────────────┘│
│                              │                              │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                  Shared State                        │   │
│  │  - graphs: dict[str, ISONGraph]                      │   │
│  │  - memories: dict[str, AgentMemory]                  │   │
│  │  - governance_engines: dict[str, GovernanceEngine]   │   │
│  │  - learning_engines: dict[str, LearningEngine]       │   │
│  │  - caches: dict[str, ISONCache]                      │   │
│  │  - compliance_engines: dict[str, *Engine]            │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Example Workflows

### 1. Agent with Persistent Memory

```python
# Initialize memory
await client.call_tool("memory_init", {
    "project_id": "my-project",
    "project_path": "/path/to/project"
})

# Start session
await client.call_tool("memory_session_start", {
    "project_id": "my-project",
    "task_description": "Implement user authentication"
})

# Get context for LLM
context = await client.call_tool("memory_get_context", {
    "project_id": "my-project",
    "task": "implement auth",
    "files": ["auth.py", "users.py"]
})

# Record decisions
await client.call_tool("memory_add_decision", {
    "project_id": "my-project",
    "title": "Use JWT for authentication",
    "context": "Need stateless auth for microservices"
})

# End session
await client.call_tool("memory_session_end", {
    "project_id": "my-project",
    "completion": 1.0,
    "outcome": "success",
    "lessons": ["JWT refresh tokens need secure storage"]
})
```

### 2. Governed Agent Actions

```python
# Initialize governance
await client.call_tool("governance_init", {
    "governance_id": "my-agent-system",
    "setup_defaults": True
})

# Register agent
await client.call_tool("governance_register_agent", {
    "governance_id": "my-agent-system",
    "agent_id": "agent_1",
    "name": "Coding Agent",
    "authority_level": "delegated"
})

# Check action before executing
result = await client.call_tool("governance_check_action", {
    "governance_id": "my-agent-system",
    "agent_id": "agent_1",
    "action": "write_file",
    "context": {"file_path": "/etc/passwd"}
})

if result["permitted"]:
    # Execute action
    pass
elif result["escalation_required"]:
    # Wait for human approval
    pass
else:
    # Action denied
    print(result["reason"])
```

### 3. Compliance-Aware Data Processing

```python
# Check unified compliance
result = await client.call_tool("unified_check_compliance", {
    "agent_id": "agent_1",
    "action": "read_personal_data",
    "pii_types": ["email", "phone"],
    "data_subject_id": "user_123"
})

if result["permitted"]:
    # Process data

    # Record action for audit
    await client.call_tool("unified_record_agent_action", {
        "agent_id": "agent_1",
        "action": "read_personal_data",
        "pii_types": ["email", "phone"],
        "data_source": "user_db",
        "outcome": "success"
    })
```

### 4. Code Analysis Integration

```python
# Analyze codebase
await client.call_tool("codeflow_analyze_local", {
    "graph_id": "myproject",
    "path": "/path/to/project"
})

# Find what calls a function
callers = await client.call_tool("codeflow_get_function_callers", {
    "graph_id": "myproject",
    "function_name": "authenticate_user"
})

# Query import chain
imports = await client.call_tool("codeflow_get_import_chain", {
    "graph_id": "myproject",
    "file_path": "src/auth/handlers.py",
    "max_depth": 3
})
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ISONGRAPH_LOG_LEVEL` | Logging level | `INFO` |
| `ISONGRAPH_STATE_DIR` | State persistence directory | `~/.isongraph` |
| `ISONGRAPH_MAX_MEMORY` | Max memory per project (MB) | `100` |

### Feature Flags

Install only the features you need:

```bash
# Minimal (core only)
pip install isongraph-mcp

# Agent development
pip install isongraph-mcp[memory,governance,learning]

# Compliance only
pip install isongraph-mcp[gdpr,ccpa,pii,hipaa]

# Everything
pip install isongraph-mcp[all]
```

## Development

```bash
# Clone the repo
git clone https://github.com/isongraph/isongraph
cd isongraph/tools/mcp-server

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Format code
black src/
ruff check src/ --fix

# Type check
mypy src/
```

## License

MIT License - see [LICENSE](../../LICENSE) for details.
