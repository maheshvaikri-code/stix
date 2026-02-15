"""
ISONGraph Unified MCP Server
============================

A single MCP server that exposes ALL ISONGraph tools to AI agents:

**Core Tools:**
- Format Converters (GraphML, RDF, CSV, Cypher, DOT)
- Schema Generator (auto-generate from data)
- ISON Cache (token-efficient caching)

**Agent AI Tools:**
- Agent Memory (12+ persistent memory stores)
- Agent Governance (15 governance domains)
- Agent Learning (experience & mistake tracking)

**Compliance Tools:**
- GDPR Governance (Articles 6-49)
- CCPA Governance (Consumer rights)
- PII Governance (Detection & classification)
- EU AI Act Governance (Risk classification)
- HIPAA Governance (PHI protection)
- Unified Governance (Cross-regulation)

**Code Analysis:**
- Code Flow Graph (structure analysis)

Usage with Claude Desktop:
    Add to claude_desktop_config.json:
    {
        "mcpServers": {
            "isongraph": {
                "command": "python",
                "args": ["-m", "isongraph_mcp.server"]
            }
        }
    }

Or run directly:
    python -m isongraph_mcp.server

Tools available: 80+
"""

__version__ = "1.0.0"

from .server import main, server, state

__all__ = ["main", "server", "state", "__version__"]
