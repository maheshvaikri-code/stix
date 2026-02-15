# Agent Memory MCP Server

**Persistent Memory for Coding Agents** - 12+ memory stores for AI coding agents with project-specific knowledge retention.

## Why Agent Memory?

AI coding agents need to remember:
- Project conventions and patterns
- Architectural decisions (ADRs)
- Historical bugs and fixes
- Dependency quirks
- Session context for continuity
- Team knowledge and ownership

## Quick Start

### Installation

```bash
pip install agent-memory-mcp
```

### Run the Server

```bash
agent-memory-mcp
# or
python -m agent_memory_mcp.server
```

### Claude Desktop Configuration

```json
{
  "mcpServers": {
    "memory": {
      "command": "python",
      "args": ["-m", "agent_memory_mcp.server"]
    }
  }
}
```

## Memory Stores (12+)

| Store | Purpose |
|-------|---------|
| **Codebase** | Architecture, modules, structure |
| **Decisions** | Architectural Decision Records (ADRs) |
| **Conventions** | Code style, naming, patterns |
| **BugPatterns** | Historical bugs and fixes |
| **Dependencies** | Libraries, versions, quirks |
| **TestPatterns** | Testing conventions |
| **Performance** | Hot paths, constraints |
| **TechDebt** | Refactoring history |
| **Team** | Who knows what, ownership |
| **Sessions** | Continuity between sessions |
| **Templates** | Code generation patterns |
| **Skills** | Agent learning progression |
| **Todos** | Task tracking |
| **Goals** | Goal management |

## Tools (40+)

### Memory Management

| Tool | Description |
|------|-------------|
| `memory_init` | Initialize for a project |
| `memory_load` | Load saved memory |
| `memory_save` | Persist memory |
| `memory_list` | List all projects |
| `memory_bootstrap` | Auto-scan project |

### Context Retrieval

| Tool | Description |
|------|-------------|
| `context_get` | Get coding context |
| `context_for_task` | Task-specific context |
| `context_for_files` | File-specific context |

### Conventions

| Tool | Description |
|------|-------------|
| `convention_add` | Add convention |
| `convention_query` | Query conventions |
| `convention_for_file` | Get for file |

### Decisions (ADRs)

| Tool | Description |
|------|-------------|
| `decision_add` | Record decision |
| `decision_query` | Query decisions |
| `decision_related` | Find related |

### Bug Patterns

| Tool | Description |
|------|-------------|
| `bug_pattern_add` | Record pattern |
| `bug_fix_add` | Add fix template |
| `bug_check` | Check for bugs |
| `bug_prevent` | Prevention tips |

### Dependencies

| Tool | Description |
|------|-------------|
| `dependency_add` | Track dependency |
| `dependency_quirk` | Record quirk |
| `dependency_query` | Query deps |

### Sessions

| Tool | Description |
|------|-------------|
| `session_start` | Start session |
| `session_end` | End with summary |
| `session_handoff` | Handoff context |
| `session_history` | View history |

### Team Knowledge

| Tool | Description |
|------|-------------|
| `team_add_expertise` | Record expertise |
| `team_who_knows` | Find expert |
| `team_ownership` | Code ownership |

### Tasks

| Tool | Description |
|------|-------------|
| `todo_add` | Add task |
| `todo_update` | Update status |
| `todo_query` | Query tasks |
| `goal_add` | Add goal |
| `goal_track` | Track progress |

### Skills

| Tool | Description |
|------|-------------|
| `skill_record` | Record usage |
| `skill_progression` | Get progression |

## Example Usage

### Initialize Memory

```python
# Initialize for a project
await mcp.call_tool("memory_init", {
    "project_id": "my-project",
    "project_path": "/path/to/project"
})
```

### Record Convention

```python
await mcp.call_tool("convention_add", {
    "category": "naming",
    "rule": "snake_case_functions",
    "description": "All functions use snake_case",
    "enforced_by": "ruff",
    "applies_to": ["*.py"]
})
```

### Record Architectural Decision

```python
await mcp.call_tool("decision_add", {
    "title": "Use SQLite for local caching",
    "context": "Need persistent cache that works offline",
    "decision": "Use SQLite with WAL mode",
    "consequences": [
        "Single-machine only",
        "Simple deployment",
        "No external dependencies"
    ],
    "alternatives": ["Redis", "PostgreSQL"],
    "status": "accepted"
})
```

### Get Coding Context

```python
context = await mcp.call_tool("context_get", {
    "task": "Add user authentication",
    "files": ["src/auth.py", "src/models/user.py"],
    "token_budget": 2000
})
# Returns relevant conventions, decisions, bug patterns
```

### Session Continuity

```python
# Start session
await mcp.call_tool("session_start", {
    "goal": "Implement OAuth2 login",
    "files": ["src/auth.py"]
})

# ... work on task ...

# End session
await mcp.call_tool("session_end", {
    "summary": "Implemented Google OAuth, needs testing",
    "completed_tasks": ["OAuth2 provider integration"],
    "pending_tasks": ["Add unit tests", "Add error handling"],
    "learnings": ["Google OAuth requires PKCE flow"]
})

# Later - get handoff
handoff = await mcp.call_tool("session_handoff", {})
# Returns context for continuing work
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Agent Memory MCP Server                       │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │                    Memory Manager                           │ │
│  │  Per-project memory instances with ISON persistence        │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │ Codebase │ │Decisions │ │Conventions│ │BugPatterns│         │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │  Deps    │ │ Sessions │ │   Team   │ │  Skills  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐          │
│  │  Todos   │ │  Goals   │ │Templates │ │TechDebt  │          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘          │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ISONGraph + ISONCache                         │
│              Graph-based storage with token efficiency           │
└─────────────────────────────────────────────────────────────────┘
```

## Integration with Other MCPs

Agent Memory MCP works best with:

- **ISONGraph MCP** - Graph storage backend
- **ISONCache MCP** - Token-budgeted context retrieval
- **Agent Governance MCP** - Governed memory access

## Dependencies

- `mcp>=1.0.0` - Model Context Protocol SDK
- `agent-memory>=1.0.0` - Agent Memory core library

## License

MIT License
