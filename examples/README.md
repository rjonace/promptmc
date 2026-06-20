# Examples

- **[UO2 criticality](../src/promptmc/examples/uo2_criticality/README.md)** — a basic UO2 + light-water eigenvalue (k-effective) run driven from the CLI. The geometry is a small subcritical water-reflected sphere (expected k ≈ 0.44), used to exercise the toolchain; validated critical benchmarks ship in the reference geometry library. The files live inside the package (`src/promptmc/examples/`) because they ship in the wheel as the data behind the MCP `promptmc://examples/uo2_criticality` resource.
- **[MCP demo](mcp/README.md)** — driving the same bundled example through the MCP server from an AI chat client.

This directory also holds small standalone inputs used in the docs: `settings.xml` (validation example) and `batch_spec.yaml` (batch-run example).
