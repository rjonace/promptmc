"""Integration test: spawn the MCP server and round-trip over stdio."""

from __future__ import annotations

import asyncio
import json
import sys

import pytest

pytest.importorskip("mcp")

from mcp import ClientSession  # noqa: E402
from mcp.client.stdio import (  # noqa: E402
    StdioServerParameters,
    stdio_client,
)
from pydantic import AnyUrl  # noqa: E402

EXPECTED_TOOLS = {
    "openmc_check_installation",
    "openmc_validate",
    "openmc_schema_check",
    "openmc_template",
    "openmc_list_templates",
    "openmc_run",
    "openmc_analyze",
    "openmc_check_cross_sections",
    "openmc_plot",
    "openmc_geometry_debug",
}


async def _exercise_server() -> None:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "promptmc.mcp.server"],
    )
    async with (
        stdio_client(params) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        await session.initialize()

        tools_result = await session.list_tools()
        names = {tool.name for tool in tools_result.tools}
        assert names == EXPECTED_TOOLS

        call_result = await session.call_tool("openmc_check_cross_sections", {})
        assert call_result.isError is False
        content = call_result.content[0].text
        result = json.loads(content)
        assert "found" in result

        resources_result = await session.list_resources()
        resource_uris = {str(r.uri) for r in resources_result.resources}
        assert {
            "promptmc://cross-sections",
            "promptmc://history",
            "promptmc://examples/uo2_criticality",
        } <= resource_uris

        read_result = await session.read_resource(
            AnyUrl("promptmc://cross-sections")
        )
        assert read_result.contents
        assert "configured" in read_result.contents[0].text


@pytest.mark.integration
def test_mcp_server_stdio_round_trip():
    asyncio.run(asyncio.wait_for(_exercise_server(), timeout=30))
