"""random-mcp-server — an MCP server that returns random JSON things.

The Node/Express `random-server` REST API is adapted here as a FastMCP server:
each REST route family (people, words, values, coords, empty) becomes a tool.
"""

from .generators import RandomFactory

__all__ = ["RandomFactory"]
