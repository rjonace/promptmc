# PromptMC Technical Roadmap

## Vision
**AI-native infrastructure for nuclear simulation.**

PromptMC is a deterministic, highly validated layer for AI agents—and the engineers working alongside them—to design, validate, run, and reason about Monte Carlo nuclear simulations. 

It provides a strictly typed, schema-driven Model Context Protocol (MCP) server that reduces AI hallucinations by validating inputs and exposing deterministic OpenMC workflows. The longer-term goal (v2.6) is to enforce physics and geometry constraints before the underlying OpenMC engine is ever invoked, culminating in constrained, human-reviewed autonomous generation.

## Architectural Constraints (What we are explicitly *not* doing)
- **No Web UI:** We are not building a 3D visualization web app. Visual verification will be handled natively via the AI chat client using 2D slice plots.
- **No Unsupervised Design for Licensing/Safety:** The system is an engineering-assist tool with human-in-the-loop verification. v2.6 autonomy is bounded exploration and optimization within validated physics constraints — a human reviews and approves every output. Never autonomous for licensing or safety-critical sign-off.
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

## Shipped: — MCP Server (v2.0)
**Goal (met):** Expose PromptMC's validation and execution logic directly to AI clients (Claude Desktop, Cursor, Windsurf, Antigravity) via MCP.
- **Shipped:** `promptmc-mcp` stdio server (`pip install promptmc[mcp]`).
- **Shipped:** 10 tools incl. `openmc_validate`, `openmc_run`, `openmc_analyze`, and `openmc_schema_check` with strict Pydantic input/output schemas.
- **Shipped:** `openmc_plot` returning 2D slice plots (PNG + base64) natively to the chat client, using OpenMC's native plotting mode.
- **Shipped:** `openmc_geometry_debug` for overlap detection via OpenMC geometry-debug mode.
- **Held to constraint:** No new CLI commands; the MCP layer parallels the CLI, it does not extend it.

## Next Sprints

### v2.1 — CSG schema + serialization
- **Deliverable:** Pydantic models for Surfaces, Regions, Cells, Materials, and Tallies.
- **Deliverable:** Round-trip serialization to runnable OpenMC XML.
- **Deliverable:** Dual-mode serialization: when OpenMC is available, serialize through OpenMC objects (`.export_to_xml()`); when absent, serialize Pydantic models to intermediate dicts and use a lightweight dict-to-xml utility to avoid double-maintenance.
- **Deliverable:** First two validated reference geometries (PWR pin, Godiva).

### v2.2 — Validation + reference library
- **Deliverable:** Pre-execution validation to catch unbounded geometries and void cells.
- **Deliverable:** Open-source library of ~6 validated reference geometries (PWR/BWR pin, Godiva, Jezebel, ICSBEP cases) — the structural moat.

### v2.3 — Geometry composition + inspection
- **Deliverable:** Deterministic `openmc_build_geometry` MCP tool (semantic JSON → validated geometry object).
- **Deliverable:** Inspection and query tools: `openmc_query_geometry`, `openmc_list_cells`, `openmc_list_materials`, `openmc_trace_point`, `openmc_diff_geometry`, `openmc_describe_geometry`.

### v2.4 — Component library
- **Deliverable:** Reusable, pre-approved components (FuelPin, GuideTube, ControlRod, ReflectorBlock, WaterBox).
- **Deliverable:** Hexagonal-lattice support for specialized reactor types.

### v2.5 — Physics safety gate
- **Deliverable:** Deterministic `promptmc validate` CLI and engine catching cell overlaps, invalid boundaries, and tracking inconsistencies before OpenMC runs.
- **Deliverable:** Structured, human- and AI-readable failure explanations (explainability) that feed exact fixes back into an agent's context.

### v2.6 — Constrained + autonomous generation
- **Deliverable:** LLM-agnostic constrained-generation pipeline with a validate-and-repair loop.
- **Deliverable:** `openmc_design` MCP tool (natural language → validated OpenMC input).
- **Deliverable:** Closed-loop, multi-turn optimization that iterates on geometry within validated physics constraints. A human reviews and approves every output; never autonomous for licensing or safety-critical decisions.

### v2.7 — Observability + provenance
- **Deliverable:** OpenTelemetry exporter library for agent usage metrics (tool-call volume, payload size, schema rejection rates).
- **Deliverable:** AI provenance — capture the connecting MCP client from `clientInfo`, plus the model and provider via `PROMPTMC_TRACKING_MODEL` / `PROMPTMC_COMPANY_ID`.
- **Deliverable:** Deterministic AI audit logging. All MCP tool calls are wrapped in OpenTelemetry spans and written to a local `audit.jsonl` file to guarantee complete provenance of AI actions.
