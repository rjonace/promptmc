# PromptMC Technical Roadmap

## Vision
**AI-native infrastructure for nuclear simulation.**

PromptMC is a deterministic, highly validated layer for AI agents—and the engineers working alongside them—to design, validate, run, and reason about Monte Carlo nuclear simulations. 

It provides a strictly typed, schema-driven Model Context Protocol (MCP) server that reduces AI hallucinations by validating inputs and exposing deterministic OpenMC workflows. The longer-term goal (v2.5) is to enforce physics and geometry constraints before the underlying OpenMC engine is ever invoked.

## Where we are
**v2.0.0 (current):**
- MCP server (`promptmc-mcp`) exposing 10 OpenMC tools and 3 resources to AI assistants
- Chat-native 2D geometry plotting (`openmc_plot`) and geometry-debug validation
- Production-grade CLI wrapper around OpenMC (subprocess + Python API)
- 260 tests, 87% coverage, full CI on Python 3.10–3.12
- Clean architecture: `OpenMCInstaller` / `OpenMCValidator` / `OpenMCRunner`
- Pydantic schema validation for base XML configurations and MCP tool I/O
- Optional OpenTelemetry tracing

## Shipped: — MCP Server (v2.0)
**Goal (met):** Expose PromptMC's validation and execution logic directly to AI clients (Claude Desktop, Cursor, Windsurf) via MCP.
- **Shipped:** `promptmc-mcp` stdio server (`pip install promptmc[mcp]`).
- **Shipped:** 10 tools incl. `openmc_validate`, `openmc_run`, `openmc_analyze`, and `openmc_schema_check` with strict Pydantic input/output schemas.
- **Shipped:** `openmc_plot` returning 2D slice plots (PNG + base64) natively to the chat client, using OpenMC's native plotting mode.
- **Shipped:** `openmc_geometry_debug` for overlap detection via OpenMC geometry-debug mode.
- **Held to constraint:** No new CLI commands; the MCP layer parallels the CLI, it does not extend it.

## Next Sprints: — Structured Geometry (v2.1 → v2.5)
Structured geometry ships as three sequential, independently-valuable releases with increasing risk — deterministic foundation first, LLM generation last.

### v2.1 — CSG schema + serialization
- **Deliverable:** Pydantic models for Surfaces, Regions, Cells, Materials, and Tallies.
- **Deliverable:** Round-trip serialization to runnable OpenMC XML.
- **Deliverable:** First two validated reference geometries (PWR pin, Godiva).

### v2.2 — Validation layer + reference library
- **Deliverable:** Pre-execution validation to catch unbounded geometries and cell overlaps.
- **Deliverable:** Open-source library of ~6 validated reference geometries (PWR/BWR pin, Godiva, Jezebel, ICSBEP cases).
- **Deliverable:** Deterministic `openmc_build_geometry` MCP tool.

### v2.5 — Constrained generation
- **Deliverable:** LLM-agnostic constrained-generation pipeline with a validate-and-repair loop.
- **Deliverable:** `openmc_design` MCP tool (natural language → validated OpenMC input).

## Architectural Constraints (What we are explicitly *not* doing)
- **No Web UI:** We are not building a 3D visualization web app. Visual verification will be handled natively via the AI chat client using 2D slice plots.
- **No Autonomous Reactor Design:** The system acts as an engineering assist tool with human-in-the-loop verification. It does not natively generate autonomous designs.
- **No Loose LLM Calls:** All LLM interactions must be routed through strict, schema-validated tool definitions.
