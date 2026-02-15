"""
ISON Memory MCP Server
======================

A robust, production-ready persistent memory system for Claude applications
using ISON format with SQLite backend.

Features:
- Token-efficient ISON/ISONGraph storage format
- SQLite persistence with automatic migrations
- Memory compaction and optimization
- Cross-platform support (Claude Desktop, CLI, VSCode)
- Configurable via environment variables and config files

Usage:
    # Start the server
    ison-memory-mcp serve

    # With custom config
    ison-memory-mcp serve --config ~/.ison-memory/config.toml

    # Run maintenance
    ison-memory-mcp compact
    ison-memory-mcp backup

Author: Mahesh Vaikri
License: MIT
"""

__version__ = "1.0.0"
__author__ = "Mahesh Vaikri"

from ison_memory_mcp.config import MemoryConfig, get_config
from ison_memory_mcp.server import run_server

__all__ = [
    "__version__",
    "MemoryConfig",
    "get_config",
    "run_server",
]
