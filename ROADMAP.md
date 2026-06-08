# PromptMC Technical Roadmap

## Vision

**AI-native infrastructure for nuclear simulation.**

PromptMC is a deterministic, validated infrastructure layer for OpenMC workflows: describe a simulation, generate inputs, validate them, run OpenMC when available, and interpret results.

It provides a strictly typed, schema-driven Model Context Protocol (MCP) server so AI assistants can use OpenMC tooling without bypassing validation. The goal is not to replace engineering judgment; it is to make Monte Carlo simulation easier for students to start and faster for engineers to iterate.

## Who This Is For

- **Students and researchers:** learn OpenMC with less configuration friction.
- **Nuclear engineers at commercial startups:** run iterative design workflows faster.
- **AI assistants:** use a validated, schema-driven interface to OpenMC tooling.

Commercial nuclear companies are the near-term target; national labs are the long-term one.

## What Works Without OpenMC

- Natural-language planning (`promptmc plan`)
- XML template generation and schema validation
- MCP planning and validation tools
- Result parsing for existing OpenMC output files

OpenMC is required for simulation execution, geometry-debug checks, and plot rendering.

## Architectural Constraints

- **No Web UI:** We are not building a 3D visualization web app. Visual verification will be handled natively via the AI chat client using 2D slice plots.
- **No Unsupervised Design for Licensing/Safety:** The system is an engineering-assist tool with human-in-the-loop verification. A human reviews and approves every output. Never autonomous for licensing or safety-critical sign-off.
- **No Loose LLM Calls:** All LLM interactions must be routed through strict, schema-validated tool definitions.
- **MCP Parallels CLI:** The MCP layer should expose the same workflow surface as the CLI, not a separate hidden product.
- **Single Model Provider:** Where PromptMC itself invokes a model — the `plan` planner and v2.7 constrained generation — it uses Google Gemini only, behind a thin internal interface. The MCP server stays client-agnostic: users drive it with whatever AI client they choose, so provider freedom is preserved where it matters.

## Where We Are

**v2.0.1 (current):**

- MCP server (`promptmc-mcp`) exposing 10 OpenMC tools and 3 resources to AI assistants
- Chat-native 2D geometry plotting (`openmc_plot`) and geometry-debug validation
- Production-grade CLI wrapper around OpenMC (subprocess + Python API)
- 268 tests, 88% coverage, full CI on Python 3.10–3.13
- Clean architecture: `OpenMCInstaller` / `OpenMCValidator` / `OpenMCRunner`
- Pydantic schema validation for base XML configurations and MCP tool I/O
- Optional OpenTelemetry tracing

## Shipped — MCP Server (v2.0)

**Goal (met):** Expose PromptMC’s validation and execution logic directly to AI clients (Claude Desktop, Cursor, Windsurf, Antigravity) via MCP.

- **Shipped:** `promptmc-mcp` stdio server (bundled with `pip install promptmc`).
- **Shipped:** 10 tools incl. `openmc_validate`, `openmc_run`, `openmc_analyze`, and `openmc_schema_check` with strict Pydantic input/output schemas.
- **Shipped:** `openmc_plot` returning 2D slice plots (PNG + base64) natively to the chat client, using OpenMC’s native plotting mode.
- **Shipped:** `openmc_geometry_debug` for overlap detection via OpenMC geometry-debug mode.
- **Held to constraint:** No new CLI commands; the MCP layer parallels the CLI, it does not extend it.

## Shipped — CSG Schema + Serialization (v2.1)

- **Shipped:** Pydantic models for Surfaces, Regions, Cells, Materials, and Tallies.
- **Shipped:** Round-trip serialization to runnable OpenMC XML.
- **Shipped:** Dual-mode serialization: when OpenMC is available, serialize through OpenMC objects (`.export_to_xml()`); when absent, serialize Pydantic models to intermediate dicts and use a lightweight dict-to-xml utility to avoid double-maintenance.
- **Shipped:** First two validated reference geometries (PWR pin, Godiva) as schema integration tests.

## Next Sprints

### v2.2 — Reference Library (launch milestone)

- **Deliverable:** Open-source library of validated reference geometries: PWR pin, BWR pin, Godiva, Jezebel, and selected ICSBEP benchmark cases.
- **Deliverable:** Each geometry is runnable, documented, and independently checked against known results.
- **Deliverable:** Keep at least one shielding/streaming case and one fast/criticality case visible so the library doesn't read as PWR-only — the community frames OpenMC across fusion neutronics, spent fuel, and radiation protection, not just thermal reactors.
- **Release:** This is the public launch milestone. The validated benchmark k-eff tables (matching published values within σ) are the credibility artifact this audience rewards — treat them as launch-ready collateral. Align geometry naming and expected values with `mit-crpg/benchmarks`. Launch through OpenMC Discourse "Show & Tell" / GitHub Discussions and the nuclear subreddits (r/NuclearEngineering, r/nuclear, r/NuclearPower).

The reference library is the trust asset. It ships before additional geometry automation, and it — not the v2.7 generative story — leads the messaging.

### v2.3 — Geometry Composition + Inspection

- **Deliverable:** Deterministic `openmc_build_geometry` MCP tool (semantic JSON → validated geometry object).
- **Deliverable:** Lean inspection surface: `openmc_query_geometry`, `openmc_list_cells`, and `openmc_list_materials`.

### v2.4 — Physics Safety Gate

- **Deliverable:** Pre-execution validation for cell overlaps, unbounded geometries, void cells, and tracking inconsistencies.
- **Deliverable:** Structured, human- and AI-readable failure explanations that feed exact fixes back into an agent’s context.
- **Deliverable:** `openmc_trace_point` to identify which cells claim a coordinate.
- **Deliverable:** Extended `promptmc validate` CLI.
- **Gate:** All v2.2 reference geometries must pass cleanly.

### v2.5 — Component Library

- **Deliverable:** Reusable, pre-approved components (FuelPin, GuideTube, ControlRod, ReflectorBlock, WaterBox).
- **Deliverable:** Hexagonal-lattice support for specialized reactor types.
- **Constraint:** Components are validated against the physics gate before they ship.

### v2.6 — Observability

- **Deliverable:** OpenTelemetry exporter for agent usage metrics: tool-call volume, payload size, and schema rejection rates.
- **Deliverable:** Distributed tracing across the tool surface.

Instrument before shipping constrained generation, where behavior most needs inspection.

### v2.7 — Constrained Generation

- **Deliverable:** Gemini-based constrained-generation pipeline with a validate-and-repair loop.
- **Deliverable:** Google Gemini as the single supported model provider, invoked behind the same thin internal interface as the `plan` planner — so adding another provider later would be an addition rather than a rewrite. Provider freedom for users is preserved through the client-agnostic MCP server, not through this pipeline.
- **Deliverable:** `openmc_design` MCP tool: natural language → validated OpenMC input package.
- **Deliverable:** Repair loop bounded by the v2.4 physics gate; either it passes the gate or exits with a structured failure.
- **Deliverable:** `openmc_diff_geometry` to show exactly what the repair loop changed.
- **Deliverable:** Minimal audit record for generated output: model used and artifact produced.
- **Constraint:** Human reviews and approves every output. Never autonomous for licensing or safety-critical decisions.

### v2.8 — Provenance + Audit

- **Deliverable:** Wrap MCP tool calls in OpenTelemetry spans and write a local `audit.jsonl`.
- **Deliverable:** Capture MCP client identity via `clientInfo`; capture model/provider via `PROMPTMC_TRACKING_MODEL` and `PROMPTMC_COMPANY_ID`.
- **Deliverable:** Deterministic record of AI-authored actions for review and provenance.
