"""
ISONGraph MCP Server
====================

Core graph operations MCP server for ISONGraph.
The foundation layer that all other MCP servers depend on.

Features:
- Graph CRUD operations
- Node and edge management
- Multi-hop traversal
- Path finding (shortest, all paths)
- ISONQL query execution
- Graph analysis (connectivity, cycles, degree)
- ISON format serialization

Usage:
    # Run the server
    python -m isongraph_mcp.server

    # Or use CLI
    isongraph-mcp
"""

__version__ = "1.0.0"

from .server import main, server, state

__all__ = ["main", "server", "state", "__version__"]
