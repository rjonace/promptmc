"""PromptMC MCP server package.

Exposes PromptMC OpenMC workflows as Model Context Protocol tools and
resources. Import :func:`main` to start the stdio server.
"""

from __future__ import annotations

from promptmc.mcp.server import main

__all__ = ["main"]
