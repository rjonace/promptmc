# MCP Demo: UO2 Criticality Benchmark

This demonstrates running the bundled UO2 example through PromptMC's MCP server.

Start the server (after `pip install promptmc[mcp]`):

```bash
export OPENMC_CROSS_SECTIONS=/path/to/cross_sections.xml
promptmc-mcp
```

Then connect an MCP-capable AI assistant (Claude Desktop, Windsurf, Cursor,
VS Code with Copilot) using the configuration in the main
[README](../../README.md#ai-assistant-configuration).

## Steps (as performed by an AI assistant)

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
