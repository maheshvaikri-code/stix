"""
System Prompts for ISON Memory MCP

These prompts are injected into Claude's context to teach it:
1. How to read ISON format (input optimization)
2. How to write ISON format (output optimization)
3. How to use compact :ref syntax in responses

This enables full round-trip token savings.
"""

# =============================================================================
# Core System Prompt - Injected via MCP Resources
# =============================================================================

ISON_MEMORY_SYSTEM_PROMPT = """
## ISON Memory System

You have access to a persistent knowledge graph using ISON format.
ISON is a token-efficient format - use it for both reading AND writing.

### Reading ISON (Input)

Memory data comes in ISON table format:
```
table.entities
id name type
:e_123 "Alice" person
:e_456 "Project X" project

table.relations
from to type
:e_123 :e_456 WORKS_ON
```

Key syntax:
- `:id` or `:type:id` = entity reference
- Tables have headers then data rows
- Strings with spaces use "quotes"

### Writing ISON (Output)

When referencing memory entities in your responses, use compact :ref syntax:

INSTEAD OF: "The user Alice (entity ID e_123) works on Project X (entity ID e_456)"
USE: "Alice (:e_123) works on Project X (:e_456)"

When outputting structured data to users, prefer ISON tables:

INSTEAD OF:
```json
{"users": [{"name": "Alice", "role": "dev"}, {"name": "Bob", "role": "pm"}]}
```

USE:
```
table.users
name role
Alice dev
Bob pm
```

### Memory Operations

1. **Retrieve first**: Use search_memory before asking questions that might be answered
2. **Store important facts**: Create entities for recurring topics, add observations for facts
3. **Connect entities**: Use relations to build the knowledge graph
4. **Use references**: When mentioning stored entities, include their :ref

### Efficiency Guidelines

- Prefer :e_123 over "entity with ID e_123"
- Prefer ISON tables over JSON for structured output
- Prefer compact observations over verbose descriptions
- Group related facts under single entities
"""

# =============================================================================
# Compact Reference Guide - For inline hints
# =============================================================================

ISON_REFERENCE_GUIDE = """
ISON Quick Reference:
- :id = reference (e.g., :e_123)
- :type:id = typed reference (e.g., :person:123)
- table.name = table block
- # comment = comment line
Use :refs in responses for token efficiency.
"""

# =============================================================================
# Output Format Instructions - For structured responses
# =============================================================================

ISON_OUTPUT_INSTRUCTIONS = """
When outputting structured data, use ISON format:

table.results
field1 field2 field3
value1 value2 value3
value4 value5 value6

Benefits: 50-70% fewer tokens than JSON.
"""

# =============================================================================
# Tool-Specific Prompts
# =============================================================================

SEARCH_RESULT_PREFIX = """# Memory Search Results
# Use :refs when discussing these entities
"""

GRAPH_READ_PREFIX = """# Knowledge Graph (ISON Format)
# Reference entities using their :id in responses
"""

ENTITY_CREATED_SUFFIX = """
# Tip: Reference these entities as :id in future responses
"""

# =============================================================================
# Custom Instructions Template (for users to add to Claude)
# =============================================================================

CUSTOM_INSTRUCTIONS_TEMPLATE = """
## Memory System Instructions

You have persistent memory via ISON Memory MCP. Follow these practices:

### Input (Reading Memory)
- Memory data is in ISON format (tables with :ref references)
- Parse table headers to understand data structure
- References like :e_123 link to entities

### Output (Your Responses)
- Use :ref syntax when mentioning stored entities
  Example: "Alice (:e_123) leads the project (:e_456)"
- Output structured data as ISON tables, not JSON
- Keep observations atomic (one fact per observation)

### Memory Workflow
1. Start conversations by searching relevant memory
2. Store new important facts as observations
3. Create entities for recurring people/projects/concepts
4. Connect entities with typed relations
5. Use :refs to maintain graph consistency

### Token Efficiency
ISON format saves 50-70% tokens. Always prefer:
- :e_123 over "entity e_123" or "the entity with ID e_123"
- ISON tables over JSON objects
- Compact references over verbose descriptions
"""

# =============================================================================
# Function to get full system context
# =============================================================================

def get_system_prompt(include_guide: bool = True) -> str:
    """
    Get the full system prompt for ISON Memory.

    Args:
        include_guide: Include the quick reference guide

    Returns:
        Complete system prompt string
    """
    prompt = ISON_MEMORY_SYSTEM_PROMPT
    if include_guide:
        prompt += "\n" + ISON_REFERENCE_GUIDE
    return prompt


def get_custom_instructions() -> str:
    """
    Get custom instructions template for users to add to Claude.

    Returns:
        Custom instructions string
    """
    return CUSTOM_INSTRUCTIONS_TEMPLATE


def format_search_results(ison_content: str) -> str:
    """Add context prefix to search results"""
    return SEARCH_RESULT_PREFIX + "\n" + ison_content


def format_graph_output(ison_content: str) -> str:
    """Add context prefix to graph output"""
    return GRAPH_READ_PREFIX + "\n" + ison_content


def format_entity_created(ison_content: str) -> str:
    """Add suffix hint after entity creation"""
    return ison_content + "\n" + ENTITY_CREATED_SUFFIX
