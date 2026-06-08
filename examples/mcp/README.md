# MCP Demo: UO2 [Criticality](https://en.wikipedia.org/wiki/Nuclear_chain_reaction) Benchmark

This demonstrates running the bundled UO2 example through PromptMC's [MCP](https://modelcontextprotocol.io) server.

## Connect

Configure an MCP-capable assistant (Claude Desktop, Claude Code, Cursor,
Devin/Windsurf, Google Antigravity, VS Code with Copilot) using the per-client
setup in the [MCP server configuration guide](../../docs/mcp.md). The client
launches the `promptmc-mcp` server for you over stdio — you don't run it by
hand. Set `OPENMC_CROSS_SECTIONS` in that config so this example can execute
and plot.

To smoke-test the command outside a client:

```bash
export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml
promptmc-mcp   # serves MCP over stdio; Ctrl-C to exit
```

## Driving the demo

You don't type the tool calls below — you prompt the assistant in plain English
and it picks the tools. For example:

> Validate and run the bundled UO2 criticality example with 4 threads, then
> show me k-effective and an xy slice of the geometry.

The assistant would carry that out with roughly these calls:

1. **Check installation**: `openmc_check_installation` → confirms OpenMC is available
2. **Check cross sections**: `openmc_check_cross_sections` → confirms `OPENMC_CROSS_SECTIONS` is set
3. **Validate inputs**: `openmc_validate { "input_path": "examples/uo2_criticality" }`
4. **Schema check**: `openmc_schema_check { "input_path": "examples/uo2_criticality" }`
5. **Run simulation**: `openmc_run { "input_path": "examples/uo2_criticality", "threads": 4 }`
6. **Analyze results**: `openmc_analyze { "output_path": "examples/uo2_criticality" }`
7. **Plot geometry**: `openmc_plot { "geometry_xml_path": "examples/uo2_criticality", "basis": "xy" }`

The `promptmc://history` resource records each tool call made during the
session, and `promptmc://examples/uo2_criticality` lists the files in the
bundled example.
