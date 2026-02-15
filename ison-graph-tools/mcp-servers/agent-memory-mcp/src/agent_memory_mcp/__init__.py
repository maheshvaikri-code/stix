"""
Agent Memory MCP Server
=======================

Persistent memory system for AI coding agents.
12+ memory stores for project-specific knowledge.

Memory Types:
- CodebaseModel: Architecture and module understanding
- Decisions: Architectural Decision Records (ADRs)
- Conventions: Code style and patterns
- BugPatterns: Historical bugs and fixes
- Dependencies: Library quirks and workarounds
- TestPatterns: Testing conventions
- Performance: Hot paths and constraints
- TechDebt: Refactoring history
- TeamKnowledge: Who knows what
- Sessions: Continuity between sessions
- Templates: Code generation patterns
- Skills: Agent learning progression

Usage:
    # Run the server
    python -m agent_memory_mcp.server

    # Or use CLI
    agent-memory-mcp
"""

__version__ = "1.0.0"

from .server import main, server, state

__all__ = ["main", "server", "state", "__version__"]
