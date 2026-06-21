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
- **MCP Parallels CLI:** The MCP layer should expose the same workflow surface as the CLI, not a separate hidden product.

## Shipped — CLI Initial Release (v0.1.0)

- **Shipped:** Production-grade CLI wrapper around OpenMC (subprocess + Python API): `plan`, `run`, `validate`, `analyze`, `batch`, `templates`, `info`.
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

Each release has a design document — architecture, key decisions, testing strategy, and open questions — under [docs/design/](docs/design/README.md).

## Next Sprints

### v0.4 — Reference Library + Onboarding

- **Deliverable:** Open-source library of validated reference geometries: PWR pin, BWR pin, Godiva, Jezebel, and selected ICSBEP benchmark cases.
- **Deliverable:** Each geometry is runnable, documented, and independently checked against known results.
- **Deliverable:** At least one shielding/streaming case and one fast/criticality case alongside the thermal-reactor geometries.
- **Deliverable:** `promptmc examples` to list bundled examples and copy one into the working directory as a runnable starting point (e.g. `promptmc examples copy godiva ./run`). This is the delivery mechanism for the reference library: it turns "the library exists in the repo" into "I have a working Godiva in my folder in seconds."
- **Deliverable:** `promptmc compare` to check a run's computed k-eff against a benchmark's published value and tolerance, reporting the deviation (absolute and in σ) with a pass/fail and `--json` for CI. It makes "independently checked against known results" a one-command reproducibility check, reading an existing statepoint rather than re-running OpenMC.
- **Deliverable:** Expose every reference benchmark as a read-only MCP resource (e.g. `promptmc://benchmarks/godiva`), the MCP parallel to `promptmc examples` (per the "MCP Parallels CLI" constraint), so an assistant can read a known-good geometry as grounding and a few-shot seed. Extends the single bundled example resource to the whole `ALL_BENCHMARKS` registry.
- **Deliverable:** `promptmc doctor`, one command that runs every environment check (OpenMC present, Python API importable, `cross_sections.xml` set and valid, data downloaded, telemetry extra installed) and prints a single status report with a fix hint for each missing piece. Setup is the top onboarding friction, and the individual checks already exist.
- **Deliverable:** Consistent `--json` structured output across `validate`, `plan`, and `info` (already present on `analyze`), so agents and CI can parse results instead of Rich tables.
- **Deliverable:** Provenance header on generated files: a leading comment recording PromptMC version, timestamp, and the exact command used, written into every emitted `settings.xml`.

### v0.5 — Geometry Composition + Inspection

- **Deliverable:** Deterministic `openmc_build_geometry` MCP tool (semantic JSON → validated geometry object).
- **Deliverable:** Lean inspection surface: `openmc_query_geometry`, `openmc_list_cells`, and `openmc_list_materials`.

### v0.6 — Physics Safety Gate

- **Deliverable:** Pre-execution validation for cell overlaps, unbounded geometries, void cells, and tracking inconsistencies.
- **Deliverable:** Structured, human- and AI-readable failure explanations that feed exact fixes back into an agent’s context.
- **Deliverable:** The failure/fix-hint output is a stable, **model-agnostic, documented contract** — parseable by *any* external agent's error-recovery loop, not just PromptMC's own repair. This is the validation layer other agents plug into.
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
