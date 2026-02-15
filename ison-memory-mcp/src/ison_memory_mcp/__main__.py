"""
Allow running the package directly:
    python -m ison_memory_mcp serve
    python -m ison_memory_mcp stats
"""

from ison_memory_mcp.cli import main

if __name__ == "__main__":
    main()
