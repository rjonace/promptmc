# PromptMC Technical Roadmap

## Vision

**AI-native infrastructure for nuclear simulation.**

PromptMC is a deterministic, validated infrastructure layer for OpenMC workflows: describe a simulation, generate inputs, validate them, run OpenMC when available, and interpret results.

It provides a strictly typed, schema-driven Model Context Protocol (MCP) server so AI assistants can use OpenMC tooling without bypassing validation. The goal is not to replace engineering judgment; it is to make Monte Carlo simulation easier for students to start and faster for engineers to iterate.

## Who This Is For

- **Students and researchers:** learn OpenMC with less configuration friction.
- **Nuclear engineers at commercial startups:** run iterative design workflows faster.
- **AI assistants:** use a validated, schema-driven interface to OpenMC tooling.

## Architectural Constraints

- **No Web UI:** We are not building a 3D visualization web app. Visual verification will be handled natively via the AI chat client using 2D slice plots.
- **No Unsupervised Design for Licensing/Safety:** The system is an engineering-assist tool with human-in-the-loop verification. A human reviews and approves every output. Never autonomous for licensing or safety-critical sign-off.
- **No Loose LLM Calls:** All LLM interactions must be routed through strict, schema-validated tool definitions.

## Shipped — CLI Initial Release (v0.1.0)

- **Shipped:** Production-grade CLI wrapper around OpenMC (subprocess + Python API): `plan`, `run`, `validate`, `analyze`, `batch`, `templates`, `info`, `configure`.
- **Shipped:** Pydantic schema validation for OpenMC XML configurations.
- **Shipped:** Batch simulation runner with parallel execution and resource management.
- **Shipped:** Optional OpenTelemetry tracing.

## Shipped — MCP Server (v0.2)

- **Shipped:** `promptmc-mcp` stdio server (bundled with `pip install promptmc`).
- **Shipped:** 10 tools incl. `openmc_validate`, `openmc_run`, `openmc_analyze`, and `openmc_schema_check` with strict Pydantic input/output schemas.
- **Shipped:** `openmc_plot` returning 2D slice plots (PNG + base64) natively to the chat client, using OpenMC’s native plotting mode.
- **Shipped:** `openmc_geometry_debug` for overlap detection via OpenMC geometry-debug mode.

## Shipped — CSG Schema + Serialization (v0.3)

- **Shipped:** Pydantic models for Surfaces, Regions, Cells, Materials, and Tallies.
- **Shipped:** Round-trip serialization to runnable OpenMC XML.
- **Shipped:** Dual-mode serialization: when OpenMC is available, serialize through OpenMC objects (`.export_to_xml()`); when absent, serialize Pydantic models to intermediate dicts and use a lightweight dict-to-xml utility to avoid double-maintenance.
- **Shipped:** First two validated reference geometries (PWR pin, Godiva) as schema integration tests.

## Next Sprints

### v0.4 — Reference Library

- **Deliverable:** Open-source library of validated reference geometries: PWR pin, BWR pin, Godiva, Jezebel, and selected ICSBEP benchmark cases.
- **Deliverable:** Each geometry is runnable, documented, and independently checked against known results.
- **Deliverable:** At least one shielding/streaming case and one fast/criticality case alongside the thermal-reactor geometries.

### v0.5 — Geometry Composition + Inspection

- **Deliverable:** Deterministic `openmc_build_geometry` MCP tool (semantic JSON → validated geometry object).
- **Deliverable:** Lean inspection surface: `openmc_query_geometry`, `openmc_list_cells`, and `openmc_list_materials`.

### v0.6 — Physics Safety Gate

- **Deliverable:** Pre-execution validation for cell overlaps, unbounded geometries, void cells, and tracking inconsistencies.
- **Deliverable:** Structured, human- and AI-readable failure explanations that feed exact fixes back into an agent’s context.
- **Deliverable:** `openmc_trace_point` to identify which cells claim a coordinate.
- **Deliverable:** Extended `promptmc validate` CLI.
- **Gate:** All v0.4 reference geometries must pass cleanly.

### v0.7 — Component Library

- **Deliverable:** Reusable, pre-approved components (FuelPin, GuideTube, ControlRod, ReflectorBlock, WaterBox).
- **Deliverable:** Hexagonal-lattice support for specialized reactor types.
- **Constraint:** Components are validated against the physics gate before they ship.

### v0.8 — Constrained Generation

- **Deliverable:** Gemini-based constrained-generation pipeline with a validate-and-repair loop, behind a thin internal model interface.
- **Deliverable:** `openmc_design` MCP tool: natural language → validated OpenMC input package.
- **Deliverable:** Repair loop bounded by the v0.6 physics gate; either it passes the gate or exits with a structured failure.
- **Deliverable:** `openmc_diff_geometry` to show exactly what the repair loop changed.
- **Deliverable:** Minimal audit record for generated output: model used and artifact produced.
- **Constraint:** Human reviews and approves every output. Never autonomous for licensing or safety-critical decisions.

### v0.9 — Observability, Provenance + Audit

- **Deliverable:** OpenTelemetry exporter for agent usage metrics: tool-call volume, payload size, and schema rejection rates.
- **Deliverable:** Distributed tracing across the tool surface.
- **Deliverable:** Wrap MCP tool calls in OpenTelemetry spans and write a local `audit.jsonl`.
- **Deliverable:** Capture MCP client identity via `clientInfo`; capture model/provider via `PROMPTMC_TRACKING_MODEL` and `PROMPTMC_COMPANY_ID`.
- **Deliverable:** Deterministic record of AI-authored actions for review and provenance.
