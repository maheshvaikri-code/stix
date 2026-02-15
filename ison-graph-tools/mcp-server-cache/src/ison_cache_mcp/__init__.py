"""
ISONCache MCP Server
====================

A dedicated MCP server for token-efficient caching - the shared
data layer for all AI agents and ISONGraph tools.

Key Features:
- 72% token savings (ISON vs JSON)
- Token budget management per agent
- Graph caching with traversal
- Embedding storage for semantic search
- Cross-agent cache sharing
- Multiple backends (memory, SQLite, Redis)

Usage:
    # Run the server
    python -m ison_cache_mcp.server

    # Or use CLI
    ison-cache-mcp
"""

__version__ = "1.0.0"

from .server import main, server, state

__all__ = ["main", "server", "state", "__version__"]
