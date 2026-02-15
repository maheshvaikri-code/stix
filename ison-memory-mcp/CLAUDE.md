# ISON Memory MCP - Instructions for Claude

This document provides guidelines for Claude to effectively use the ISON Memory MCP system.

## Overview

ISON Memory MCP is your persistent knowledge graph. Use it to:
- Remember users, their projects, preferences, and context
- Track relationships between entities
- Recall information across conversations
- Build a comprehensive understanding of the user's world

## Memory Guidelines

### When to Store Memory

**DO store:**
- User's name, role, and preferences
- Projects they're working on
- Tools and technologies they use
- Important decisions and their context
- Recurring topics and interests
- Key facts about their work

**DON'T store:**
- Sensitive credentials or secrets
- Temporary debugging information
- Generic coding questions
- One-time requests

### Creating Entities

Use `create_entities` for notable people, projects, organizations, tools, and concepts:

```
Good entity examples:
- Person: "John Smith" (person) - the user
- Project: "E-commerce Platform" (project)
- Tool: "React" (tool)
- Concept: "Clean Architecture" (concept)
- Preference: "Dark Mode" (preference)
```

### Adding Observations

Use `create_observations` for atomic facts. Each observation should be:
- **Specific**: One clear fact per observation
- **Useful**: Information worth remembering
- **Accurate**: Based on what the user actually said

```
Good observations:
- "Prefers TypeScript over JavaScript"
- "Working on migrating from REST to GraphQL"
- "Uses VSCode as primary editor"
- "Timezone is PST (UTC-8)"

Bad observations:
- "Asked about code" (too vague)
- "Had a conversation" (not useful)
- "Might like Python" (uncertain)
```

### Creating Relations

Use `create_relations` to connect entities:

```
Common patterns:
- Person WORKS_ON Project
- Person USES Tool
- Project DEPENDS_ON Library
- Person KNOWS Person
- Person PREFERS Concept
- Project INTEGRATES Tool
```

## Conversation Flow

### At Conversation Start

1. If the user mentions their name or a specific project, search for it:
   ```
   search_memory: "John" or "E-commerce"
   ```

2. For returning users, use `read_graph` to get full context

3. Use `multi_hop_search` to explore relationships from a known entity

### During Conversation

1. When the user mentions new facts, create observations:
   - "I'm working on a new authentication system" → Add observation to their project

2. When new entities emerge, create them:
   - "We're using Supabase for the backend" → Create Supabase entity, relate to project

3. Update preferences when stated:
   - "I prefer functional components" → Add to user's preferences

### At Conversation End

1. Save any important new information that emerged
2. Create relations between newly mentioned entities
3. Update observations if facts have changed

## ISON Output Format

All responses are in ISON format for token efficiency. Learn to read:

```ison
# Comments start with #
table.entities
id name type
:e_abc123 "John Smith" person
:e_def456 "My Project" project

table.observations
id entity_id content timestamp
:o_123 :e_abc123 "Prefers dark mode" 2025-01-15T10:00:00Z

table.relations
from_entity to_entity relation_type
:e_abc123 :e_def456 WORKS_ON
```

## Tool Usage Examples

### Remember a new user
```
create_entities: [
  {name: "Sarah Chen", entityType: "person",
   observations: ["Software engineer", "Works at TechCorp"]}
]
```

### Add context to existing entity
```
create_observations: [
  {entityName: "Sarah Chen", content: "Prefers test-driven development"},
  {entityName: "Sarah Chen", content: "Expert in Kubernetes"}
]
```

### Connect entities
```
create_relations: [
  {fromEntity: "Sarah Chen", toEntity: "Cloud Migration", relationType: "LEADS"},
  {fromEntity: "Cloud Migration", toEntity: "Kubernetes", relationType: "USES"}
]
```

### Search for context
```
search_memory: "cloud migration"
```

### Get everything about a topic
```
multi_hop_search: {entityName: "Sarah Chen", maxHops: 2}
```

## Maintenance

Periodically (monthly or when prompted):
1. Use `compact_memory` with strategy "smart" to clean old data
2. Use `backup_memory` before major operations
3. Use `memory_stats` to monitor growth

## Best Practices

1. **Be consistent**: Use the same entity names across conversations
2. **Be specific**: "Uses React 18" is better than "Uses React"
3. **Be relevant**: Only store information that helps future conversations
4. **Be proactive**: Search memory before asking questions already answered
5. **Be connected**: Create relations to build a rich knowledge graph

## Privacy Considerations

- Never store: passwords, API keys, tokens, or secrets
- Ask before storing: sensitive personal information
- Respect: user requests to forget information (use `delete_entities`)
