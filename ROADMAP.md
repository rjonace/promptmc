# PromptMC Technical Roadmap

## Vision
**AI-native infrastructure for nuclear simulation.**

PromptMC is a deterministic, highly validated layer for AI agents—and the engineers working alongside them—to design, validate, run, and reason about Monte Carlo nuclear simulations. 

It provides a strictly typed, schema-driven Model Context Protocol (MCP) server that reduces AI hallucinations by validating inputs and exposing deterministic OpenMC workflows. The longer-term goal (v2.5) is to enforce physics and geometry constraints before the underlying OpenMC engine is ever invoked.

### Architectural Constraints (What we are explicitly *not* doing)
- **No Web UI:** We are not building a 3D visualization web app. Visual verification will be handled natively via the AI chat client using 2D slice plots.
- **No Autonomous Reactor Design:** The system acts as an engineering assist tool with human-in-the-loop verification. It does not natively generate autonomous designs.
- **No Loose LLM Calls:** All LLM interactions must be routed through strict, schema-validated tool definitions.

## Where we are
**v2.0.0 (current):**
- MCP server (`promptmc-mcp`) exposing 10 OpenMC tools and 3 resources to AI assistants
- Chat-native 2D geometry plotting (`openmc_plot`) and geometry-debug validation
- Production-grade CLI wrapper around OpenMC (subprocess + Python API)
- 260 tests, 87% coverage, full CI on Python 3.10–3.12
- Clean architecture: `OpenMCInstaller` / `OpenMCValidator` / `OpenMCRunner`
- Pydantic schema validation for base XML configurations and MCP tool I/O
- Optional OpenTelemetry tracing

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
- **Deliverable:** Deterministic AI audit logging. All MCP tool calls are wrapped in OpenTelemetry spans and written to a local `audit.jsonl` file to guarantee complete provenance of AI actions.

### v2.5 — Constrained generation
- **Deliverable:** LLM-agnostic constrained-generation pipeline with a validate-and-repair loop.
- **Deliverable:** `openmc_design` MCP tool (natural language → validated OpenMC input).
