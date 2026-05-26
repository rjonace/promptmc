# PromptMC Technical Roadmap

## Vision
**AI-native infrastructure for nuclear simulation.**

PromptMC is a deterministic, highly validated layer for AI agents—and the engineers working alongside them—to design, validate, run, and reason about Monte Carlo nuclear simulations. 

The goal is to provide a strictly typed, schema-driven Model Context Protocol (MCP) server that prevents AI hallucinations by enforcing physics and geometry constraints before the underlying OpenMC engine is ever invoked.

## Where we are
**v1.2.1 (current):**
- Production-grade CLI wrapper around OpenMC (subprocess + Python API)
- 190 tests, 83% coverage, full CI on Python 3.10+
- Clean architecture: `OpenMCInstaller` / `OpenMCValidator` / `OpenMCRunner`
- Optional OpenTelemetry tracing
- Pydantic schema validation for base XML configurations

## Next Sprint: — MCP Server (v2.0)
**Goal:** Expose PromptMC's validation and execution logic directly to AI clients (Claude Desktop, Cursor) via MCP.
- **Deliverable:** `promptmc-mcp` stdio server.
- **Deliverable:** `openmc_validate` and `openmc_run` tools with strict Pydantic input/output schemas.
- **Deliverable:** `openmc_plot` tool to return 2D slice plots natively to the chat client for immediate visual verification.
- **Constraint:** No new CLI commands. The MCP layer parallels the CLI; it does not extend it.

## Future Horizon: — Structured Geometry (v2.5)
**Goal:** Build comprehensive Pydantic models for OpenMC Constructive Solid Geometry (CSG) to act as constraint surfaces for LLM-driven structured generation.
- **Deliverable:** Full schema coverage for Surfaces, Regions, Cells, and Materials.
- **Deliverable:** Validation layer to catch unbounded geometries and cell overlaps pre-execution.
- **Deliverable:** Open-source library of validated reference geometries (PWR pin, Godiva, ICSBEP cases).

## Architectural Constraints (What we are explicitly *not* doing)
- **No Web UI:** We are not building a 3D visualization web app. Visual verification will be handled natively via the AI chat client using 2D slice plots.
- **No Autonomous Reactor Design:** The system acts as an engineering assist tool with human-in-the-loop verification. It does not natively generate autonomous designs.
- **No Loose LLM Calls:** All LLM interactions must be routed through strict, schema-validated tool definitions.
