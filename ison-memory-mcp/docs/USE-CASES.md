# ISON Memory MCP - Use Cases & Examples

Practical use cases and implementation examples for ISON Memory MCP.

## Table of Contents

- [Overview](#overview)
- [Personal Assistant Memory](#personal-assistant-memory)
- [Project Context Tracking](#project-context-tracking)
- [Team Knowledge Base](#team-knowledge-base)
- [Code Context Memory](#code-context-memory)
- [Learning Progress Tracking](#learning-progress-tracking)
- [Research & Documentation](#research--documentation)
- [Client & Meeting Memory](#client--meeting-memory)
- [Workflow Patterns](#workflow-patterns)
- [Integration Examples](#integration-examples)

---

## Overview

ISON Memory MCP enables Claude to maintain persistent context across conversations. This document provides practical use cases with example tool calls and expected outputs.

### Memory Workflow Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CONVERSATION START                               │
│  1. Search relevant memory: search_memory("topic")                  │
│  2. Load context if found: multi_hop_search or read_graph           │
│  3. User sees Claude "remembers" previous context                   │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DURING CONVERSATION                              │
│  1. Capture new facts: create_observations                          │
│  2. Create new entities: create_entities                            │
│  3. Build connections: create_relations                             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     CONVERSATION END                                 │
│  1. Important facts stored automatically                            │
│  2. Available for next conversation                                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Personal Assistant Memory

### Scenario

Claude acts as a personal assistant, remembering user preferences, routines, and important information.

### Initial Setup

**User says:** "Hi, I'm Sarah Chen. I'm a senior frontend engineer at TechCorp. I work from home in Seattle, PST timezone."

**Claude stores:**

```json
// Tool: create_entities
{
  "entities": [
    {
      "name": "Sarah Chen",
      "entityType": "person",
      "observations": [
        "Senior frontend engineer",
        "Works at TechCorp",
        "Works from home",
        "Location: Seattle",
        "Timezone: PST (UTC-8)"
      ]
    },
    {
      "name": "TechCorp",
      "entityType": "organization"
    }
  ]
}

// Tool: create_relations
{
  "relations": [
    {
      "fromEntity": "Sarah Chen",
      "toEntity": "TechCorp",
      "relationType": "MEMBER_OF"
    }
  ]
}
```

### Storing Preferences

**User says:** "I prefer using TypeScript, love dark mode, and my editor is VSCode with Vim keybindings."

```json
// Tool: create_entities
{
  "entities": [
    {"name": "TypeScript", "entityType": "tool"},
    {"name": "VSCode", "entityType": "tool"},
    {"name": "Dark Mode", "entityType": "preference"},
    {"name": "Vim Keybindings", "entityType": "preference"}
  ]
}

// Tool: create_relations
{
  "relations": [
    {"fromEntity": "Sarah Chen", "toEntity": "TypeScript", "relationType": "PREFERS"},
    {"fromEntity": "Sarah Chen", "toEntity": "VSCode", "relationType": "USES"},
    {"fromEntity": "Sarah Chen", "toEntity": "Dark Mode", "relationType": "PREFERS"},
    {"fromEntity": "Sarah Chen", "toEntity": "Vim Keybindings", "relationType": "PREFERS"}
  ]
}
```

### Later Conversation

**User says:** "Set up a new React project for me"

**Claude searches:**

```json
// Tool: search_memory
{"query": "Sarah preferences tools"}
```

**Claude responds:**

"I'll set up a React project with your preferences in mind, Sarah (:e_sarah01):

- Using **TypeScript** (:e_ts01) as you prefer
- Configuring **dark mode** (:e_dark01) for your IDE
- Setting up **VSCode** (:e_vscode01) with **Vim keybindings** (:e_vim01)

Since you're in **PST**, I'll configure any time-related settings accordingly."

---

## Project Context Tracking

### Scenario

Claude tracks project details, tech stack, milestones, and team members across sessions.

### Creating Project Context

**User says:** "I'm starting a new e-commerce platform. We'll use Next.js, PostgreSQL, and Stripe for payments. Target launch is Q2 2025."

```json
// Tool: create_entities
{
  "entities": [
    {
      "name": "E-commerce Platform",
      "entityType": "project",
      "observations": [
        "Target launch: Q2 2025",
        "E-commerce website",
        "New project starting January 2025"
      ]
    },
    {"name": "Next.js", "entityType": "tool"},
    {"name": "PostgreSQL", "entityType": "tool"},
    {"name": "Stripe", "entityType": "tool"}
  ]
}

// Tool: create_relations
{
  "relations": [
    {"fromEntity": "E-commerce Platform", "toEntity": "Next.js", "relationType": "USES"},
    {"fromEntity": "E-commerce Platform", "toEntity": "PostgreSQL", "relationType": "USES"},
    {"fromEntity": "E-commerce Platform", "toEntity": "Stripe", "relationType": "INTEGRATES"},
    {"fromEntity": "Sarah Chen", "toEntity": "E-commerce Platform", "relationType": "WORKS_ON"}
  ]
}
```

### Adding Milestones

**User says:** "We finished the authentication system yesterday. Next up is the product catalog."

```json
// Tool: create_observations
{
  "observations": [
    {
      "entityName": "E-commerce Platform",
      "content": "Authentication system completed 2025-01-14"
    },
    {
      "entityName": "E-commerce Platform",
      "content": "Currently working on: Product catalog"
    }
  ]
}

// Tool: create_entities
{
  "entities": [
    {
      "name": "Authentication System",
      "entityType": "code",
      "observations": ["Completed 2025-01-14", "Part of E-commerce Platform"]
    },
    {
      "name": "Product Catalog",
      "entityType": "task",
      "observations": ["Next milestone", "In progress"]
    }
  ]
}

// Tool: create_relations
{
  "relations": [
    {"fromEntity": "E-commerce Platform", "toEntity": "Authentication System", "relationType": "HAS_PART"},
    {"fromEntity": "E-commerce Platform", "toEntity": "Product Catalog", "relationType": "HAS_PART"}
  ]
}
```

### Querying Project Status

**Later, user asks:** "What's the status of the e-commerce project?"

```json
// Tool: multi_hop_search
{
  "entityName": "E-commerce Platform",
  "maxHops": 2
}
```

**Response:**

```ison
# Multi-Hop Search from 'E-commerce Platform'

table.entities
id name type hop
:e_ecom E-commerce Platform project 0
:e_nextjs Next.js tool 1
:e_postgres PostgreSQL tool 1
:e_stripe Stripe tool 1
:e_auth Authentication System code 1
:e_catalog Product Catalog task 1
:e_sarah Sarah Chen person 2

table.observations
entity_id content
:e_ecom "Target launch: Q2 2025"
:e_ecom "Authentication system completed 2025-01-14"
:e_ecom "Currently working on: Product catalog"
:e_auth "Completed 2025-01-14"
:e_catalog "In progress"
```

**Claude responds:**

"Here's the status of **E-commerce Platform** (:e_ecom):

**Progress:**
- Authentication System (:e_auth) - Completed Jan 14
- Product Catalog (:e_catalog) - In Progress

**Tech Stack:**
- Next.js (:e_nextjs) for frontend
- PostgreSQL (:e_postgres) for database
- Stripe (:e_stripe) for payments

**Timeline:** Target launch Q2 2025

You (:e_sarah) are the main contributor."

---

## Team Knowledge Base

### Scenario

Claude maintains information about team members, their expertise, and project assignments.

### Building Team Profile

```json
// Tool: create_entities
{
  "entities": [
    {
      "name": "Alex Kumar",
      "entityType": "person",
      "observations": [
        "Backend engineer",
        "Expert in Python and Go",
        "Database optimization specialist",
        "5 years experience"
      ]
    },
    {
      "name": "Maria Garcia",
      "entityType": "person",
      "observations": [
        "DevOps engineer",
        "Kubernetes certified",
        "AWS Solutions Architect",
        "Manages CI/CD pipelines"
      ]
    },
    {
      "name": "Engineering Team",
      "entityType": "organization"
    }
  ]
}

// Tool: create_relations
{
  "relations": [
    {"fromEntity": "Alex Kumar", "toEntity": "Engineering Team", "relationType": "MEMBER_OF"},
    {"fromEntity": "Maria Garcia", "toEntity": "Engineering Team", "relationType": "MEMBER_OF"},
    {"fromEntity": "Sarah Chen", "toEntity": "Engineering Team", "relationType": "MEMBER_OF"},
    {"fromEntity": "Alex Kumar", "toEntity": "E-commerce Platform", "relationType": "WORKS_ON"},
    {"fromEntity": "Maria Garcia", "toEntity": "E-commerce Platform", "relationType": "WORKS_ON"}
  ]
}
```

### Finding Expertise

**User asks:** "Who can help with database performance issues?"

```json
// Tool: search_memory
{"query": "database optimization performance"}
```

**Claude responds:**

"For database performance issues, I'd recommend **Alex Kumar** (:e_alex):

- Database optimization specialist
- Expert in Python and Go (good for writing efficient queries)
- 5 years experience
- Currently on the E-commerce Platform (:e_ecom) team

He's worked with **PostgreSQL** (:e_postgres) which you're using for the project."

---

## Code Context Memory

### Scenario

Claude remembers codebase structure, architectural decisions, and implementation details.

### Storing Architecture Decisions

**User says:** "We decided to use JWT instead of sessions for auth because we need stateless scaling."

```json
// Tool: create_entities
{
  "entities": [
    {
      "name": "JWT Auth Decision",
      "entityType": "document",
      "observations": [
        "Decision: Use JWT over sessions",
        "Reason: Stateless scaling requirement",
        "Date: January 2025",
        "Affects: Authentication System"
      ]
    }
  ]
}

// Tool: create_relations
{
  "relations": [
    {"fromEntity": "JWT Auth Decision", "toEntity": "Authentication System", "relationType": "MENTIONED_IN"},
    {"fromEntity": "Authentication System", "toEntity": "JWT Auth Decision", "relationType": "DEPENDS_ON"}
  ]
}
```

### Storing Code Patterns

**User explains:** "Our API endpoints follow the pattern /api/v1/resource. All handlers are in src/api/handlers/."

```json
// Tool: create_observations
{
  "observations": [
    {
      "entityName": "E-commerce Platform",
      "content": "API pattern: /api/v1/resource"
    },
    {
      "entityName": "E-commerce Platform",
      "content": "API handlers location: src/api/handlers/"
    }
  ]
}
```

### Later Code Question

**User asks:** "Why are we using JWT? And where are the auth handlers?"

**Claude searches and responds:**

"According to the **JWT Auth Decision** (:e_jwt_decision):

**Why JWT:**
- Chose JWT over sessions for stateless scaling
- Decided in January 2025
- Applied to Authentication System (:e_auth)

**Handler Location:**
Based on your API pattern, auth handlers should be at:
`src/api/handlers/auth/`

Following your `/api/v1/resource` pattern, endpoints would be:
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `POST /api/v1/auth/refresh`"

---

## Learning Progress Tracking

### Scenario

Claude tracks what a user is learning and their progress.

### Recording Learning Journey

```json
// Tool: create_entities
{
  "entities": [
    {
      "name": "TypeScript Learning",
      "entityType": "task",
      "observations": [
        "Started: January 2025",
        "Progress: 60%",
        "Current topic: Generics"
      ]
    },
    {
      "name": "React Learning",
      "entityType": "task",
      "observations": [
        "Completed: December 2024",
        "Focus was: Hooks and Context"
      ]
    },
    {
      "name": "System Design Learning",
      "entityType": "task",
      "observations": [
        "Status: Not started",
        "Planned for: After TypeScript"
      ]
    }
  ]
}

// Tool: create_relations
{
  "relations": [
    {"fromEntity": "Sarah Chen", "toEntity": "TypeScript Learning", "relationType": "WORKS_ON"},
    {"fromEntity": "Sarah Chen", "toEntity": "React Learning", "relationType": "CREATOR_OF"},
    {"fromEntity": "System Design Learning", "toEntity": "TypeScript Learning", "relationType": "DEPENDS_ON"}
  ]
}
```

### Updating Progress

**User says:** "I finished the TypeScript generics section!"

```json
// Tool: create_observations
{
  "observations": [
    {
      "entityName": "TypeScript Learning",
      "content": "Completed: Generics (January 15, 2025)"
    },
    {
      "entityName": "TypeScript Learning",
      "content": "Progress updated: 75%"
    }
  ]
}
```

### Recommending Next Steps

**User asks:** "What should I learn next?"

**Claude analyzes and responds:**

"Based on your learning journey, Sarah (:e_sarah):

**Completed:**
- React Learning (:e_react_learn) - Done Dec 2024

**In Progress:**
- TypeScript Learning (:e_ts_learn) - 75% (great progress on Generics!)

**Recommended Next:**
- System Design Learning (:e_sysdesign) - Planned after TypeScript

Since you're at 75% with TypeScript, you might cover:
1. Advanced types (Conditional types, Mapped types)
2. TypeScript with React patterns
3. Then move to System Design

Your React + TypeScript combo will be great for system design patterns!"

---

## Research & Documentation

### Scenario

Claude helps track research topics, sources, and findings.

### Storing Research

```json
// Tool: create_entities
{
  "entities": [
    {
      "name": "Microservices vs Monolith Research",
      "entityType": "document",
      "observations": [
        "Topic: Architecture comparison",
        "Started: January 2025",
        "For: E-commerce Platform architecture decision"
      ]
    }
  ]
}

// Tool: create_observations
{
  "observations": [
    {
      "entityName": "Microservices vs Monolith Research",
      "content": "Pro microservices: Independent scaling, team autonomy",
      "source": "chat"
    },
    {
      "entityName": "Microservices vs Monolith Research",
      "content": "Pro monolith: Simpler deployment, easier debugging",
      "source": "chat"
    },
    {
      "entityName": "Microservices vs Monolith Research",
      "content": "Recommendation: Start monolith, extract services later",
      "source": "inference",
      "confidence": 0.8
    }
  ]
}
```

---

## Client & Meeting Memory

### Scenario

Claude remembers client interactions and meeting outcomes.

### Recording Client Info

```json
// Tool: create_entities
{
  "entities": [
    {
      "name": "Acme Corp",
      "entityType": "organization",
      "observations": [
        "Client since: 2024",
        "Industry: Retail",
        "Main contact: John Davis",
        "Prefers: Weekly status calls"
      ]
    },
    {
      "name": "John Davis",
      "entityType": "person",
      "observations": [
        "Role: VP of Engineering at Acme Corp",
        "Communication preference: Email for details, calls for decisions",
        "Timezone: EST"
      ]
    }
  ]
}

// Tool: create_relations
{
  "relations": [
    {"fromEntity": "John Davis", "toEntity": "Acme Corp", "relationType": "MEMBER_OF"},
    {"fromEntity": "Acme Corp", "toEntity": "E-commerce Platform", "relationType": "RELATED_TO"}
  ]
}
```

### Recording Meeting

```json
// Tool: create_entities
{
  "entities": [
    {
      "name": "Acme Weekly 2025-01-15",
      "entityType": "event",
      "observations": [
        "Date: January 15, 2025",
        "Attendees: Sarah Chen, John Davis",
        "Topic: Q2 launch timeline",
        "Decision: Soft launch April 1, full launch May 1",
        "Action: Sarah to send updated roadmap by Friday"
      ]
    }
  ]
}

// Tool: create_relations
{
  "relations": [
    {"fromEntity": "Acme Weekly 2025-01-15", "toEntity": "Acme Corp", "relationType": "RELATED_TO"},
    {"fromEntity": "Acme Weekly 2025-01-15", "toEntity": "E-commerce Platform", "relationType": "MENTIONED_IN"}
  ]
}
```

---

## Workflow Patterns

### Pattern 1: Start of Day Context Load

```json
// Search for recent and relevant context
{"tool": "search_memory", "arguments": {"query": "recent in progress"}}

// Get full graph if needed
{"tool": "read_graph", "arguments": {"format": "ison", "includeStats": true}}
```

### Pattern 2: Continuous Fact Capture

```json
// As user mentions new facts, store them immediately
{
  "tool": "create_observations",
  "arguments": {
    "observations": [
      {"entityName": "Current Project", "content": "New fact from conversation"}
    ]
  }
}
```

### Pattern 3: End of Session Summary

```json
// Store session summary as observation
{
  "tool": "create_observations",
  "arguments": {
    "observations": [
      {
        "entityName": "Sarah Chen",
        "content": "Session 2025-01-15: Discussed auth implementation, decided on JWT"
      }
    ]
  }
}
```

### Pattern 4: Regular Maintenance

```bash
# Weekly: Run smart compaction
ison-memory compact --strategy smart

# Daily: Create backup
ison-memory backup

# Monthly: Check stats
ison-memory stats
```

---

## Integration Examples

### Claude Desktop Custom Instructions

Add to Claude Desktop project settings:

```markdown
## Memory Instructions

You have persistent memory via ISON Memory MCP.

**At conversation start:**
1. Search for relevant context: search_memory("[user name or topic]")
2. Load related entities: multi_hop_search if needed

**During conversation:**
1. Store new important facts immediately
2. Create entities for new people, projects, tools
3. Build relations between entities

**Best practices:**
- Use :ref syntax when mentioning stored entities
- Keep observations atomic (one fact each)
- Create relations to build the knowledge graph
```

### Claude Code CLI Project Config

Create `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "project-memory": {
      "command": "ison-memory",
      "args": ["serve"],
      "env": {
        "ISON_MEMORY_STORAGE_PATH": "./.ison-memory/project.db"
      }
    }
  }
}
```

### Programmatic Integration

```python
import asyncio
from mcp import Client

async def use_memory():
    async with Client("ison-memory") as client:
        # Search for context
        results = await client.call_tool("search_memory", {
            "query": "project status"
        })

        # Store new information
        await client.call_tool("create_observations", {
            "observations": [{
                "entityName": "Current Project",
                "content": "Updated requirement from meeting"
            }]
        })

        # Get full context
        graph = await client.call_tool("read_graph", {
            "format": "ison"
        })

asyncio.run(use_memory())
```

---

This document provides practical patterns for using ISON Memory MCP. For technical details, see [Architecture](ARCHITECTURE.md). For API details, see [API Reference](API-REFERENCE.md). For troubleshooting, see [Troubleshooting](TROUBLESHOOTING.md).
