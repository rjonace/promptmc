"""PromptMC MCP server (stdio transport).

Wires the MCP SDK to the pure tool functions in :mod:`promptmc.mcp.tools`
and the resource handlers in :mod:`promptmc.mcp.resources`. The ``mcp``
import is guarded so importing this module without the ``[mcp]`` extra does
not raise; :func:`build_server` reports a clear error in that case.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Iterable
from typing import Any

from pydantic import AnyUrl

from promptmc.errors import MCPError
from promptmc.mcp.resources import (
    CROSS_SECTIONS_URI,
    HISTORY_URI,
    RESOURCE_MIME_TYPE,
    RESOURCE_READERS,
    UO2_EXAMPLE_URI,
)
from promptmc.mcp.tools import TOOL_REGISTRY, dispatch

try:
    import mcp.types as types
    from mcp.server import Server
    from mcp.server.lowlevel.helper_types import ReadResourceContents
    from mcp.server.stdio import stdio_server

    _MCP_AVAILABLE = True
except ImportError:  # pragma: no cover
    _MCP_AVAILABLE = False

_INSTALL_HINT = (
    "The 'mcp' extra is required to run the PromptMC MCP server. "
    "Install it with: pip install promptmc[mcp]"
)


def build_server() -> Server:  # pragma: no cover
    """Build and configure the PromptMC MCP server instance."""
    if not _MCP_AVAILABLE:
        raise RuntimeError(_INSTALL_HINT)

    server: Server = Server("promptmc")

    @server.list_tools()
    async def _list_tools() -> list[types.Tool]:
        return [
            types.Tool(
                name=spec.name,
                description=spec.description,
                inputSchema=spec.input_model.model_json_schema(),
                outputSchema=spec.output_model.model_json_schema(),
            )
            for spec in TOOL_REGISTRY.values()
        ]

    @server.call_tool()
    async def _call_tool(
        name: str, arguments: dict[str, Any]
    ) -> list[types.TextContent]:
        result = await asyncio.to_thread(dispatch, name, arguments)
        return [types.TextContent(type="text", text=json.dumps(result))]

    @server.list_resources()
    async def _list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=AnyUrl(CROSS_SECTIONS_URI),
                name="OpenMC Cross Sections",
                description="Configured cross-section data location",
                mimeType=RESOURCE_MIME_TYPE,
            ),
            types.Resource(
                uri=AnyUrl(HISTORY_URI),
                name="MCP Session History",
                description="Tool calls made during this MCP session",
                mimeType=RESOURCE_MIME_TYPE,
            ),
            types.Resource(
                uri=AnyUrl(UO2_EXAMPLE_URI),
                name="UO2 Criticality Example",
                description="File listing of the bundled UO2 example",
                mimeType=RESOURCE_MIME_TYPE,
            ),
        ]

    @server.read_resource()
    async def _read_resource(uri: AnyUrl) -> Iterable[ReadResourceContents]:
        reader = RESOURCE_READERS.get(str(uri))
        if reader is None:
            raise MCPError(f"Unknown resource: {uri}")
        return [
            ReadResourceContents(content=reader(), mime_type=RESOURCE_MIME_TYPE)
        ]

    return server


def main() -> None:  # pragma: no cover
    """Entry point: start the stdio MCP server."""
    server = build_server()

    async def _run() -> None:
        async with stdio_server() as (read_stream, write_stream):
            await server.run(
                read_stream,
                write_stream,
                server.create_initialization_options(),
            )

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    main()
