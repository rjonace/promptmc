# PromptMC Roadmap

## Vision

**AI-native infrastructure for nuclear simulation.**

PromptMC is repositioning from a Python/CLI wrapper around OpenMC into the canonical way for AI agents — and the engineers working alongside them — to design, validate, run, and reason about Monte Carlo nuclear simulations.

The thesis: OpenMC already has an excellent Python API for humans. The unmet need is a layer that lets reactor physics work happen agentically — through MCP servers, structured generation against validated schemas, and reproducible compute — so that one engineer plus an AI agent can do the work that used to take a team.

The goal customer for v2.x and beyond is the reactor physics team at an advanced reactor / SMR startup. The product is a productivity multiplier for scarce, expensive nuclear engineers.

## Where we are

**v1.2.1 (current, May 2026):**
- Production-grade CLI wrapper around OpenMC (subprocess + Python API)
- 12 commands, 190 tests, 83% coverage, full CI on Python 3.10/3.11/3.12
- Clean architecture: `OpenMCInstaller` / `OpenMCValidator` / `OpenMCRunner` separation
- Optional OpenTelemetry telemetry, optional LLM planning
- Pydantic schema validation for `settings.xml`, `materials.xml`, `geometry.xml`
- Working end-to-end UO₂ criticality example
- Curated public API exposed from `promptmc/__init__.py`

This is the foundation. The pivot reuses ~70% of the existing code; almost nothing is thrown away.

## Phase 5 — MCP Server (v2.0)

**Goal:** Make every PromptMC capability callable by an AI agent via the Model Context Protocol.

- [ ] `promptmc.mcp_server` module — MCP server exposing existing operations
- [ ] Tools: `openmc_check_installation`, `openmc_validate`, `openmc_run`, `openmc_template`, `openmc_analyze`, `openmc_list_isotopes`, `openmc_check_cross_sections`
- [ ] Tool enhancements: extend `openmc_validate` / `openmc_schema_check` with fail-fast geometry guards
- [ ] Tool: `openmc_schema_check` (returns structured Pydantic issues, not text reports)
- [ ] Tool: `openmc_run_async` for long-running simulations with status polling
- [ ] Resource: cross-section data discovery (`OPENMC_CROSS_SECTIONS`)
- [ ] Resource: simulation history per session
- [ ] CLI entry: `promptmc-mcp` (stdio MCP server)
- [ ] **Visual Verification:** Provide an `openmc_plot` tool that returns 2D `.png` cross-sections directly to the AI client to give engineers an immediate visual feedback loop.
- [ ] **Cognitive load reducer:** Ship a `openmc_analyze` response schema that surfaces k-effective, tallies, and paths without manual HDF5 spelunking.
- [ ] Demo: "AI assistant runs the UO₂ benchmark in one prompt"
- [ ] Documentation: how to configure AI assistants (e.g., Windsurf, Claude Desktop, Cursor, VS Code with Copilot) to use it
- [ ] Test coverage: 80%+ on the MCP layer

**Acceptance:** A user can install `pip install promptmc[mcp]`, drop a config block into their AI assistant, and have it run, validate, and analyze an OpenMC simulation end-to-end without writing Python.

## Phase 6 — Structured Geometry Generation (v2.5)

**Goal:** Solve the *actual* hard part of OpenMC — geometry, materials, and tallies — using Pydantic schemas as a constraint surface for LLM generation.

- [ ] `promptmc.geometry` package
  - [ ] Pydantic models for OpenMC CSG primitives (`Surface`, `HalfSpace`, `Region`, `Cell`, `Universe`, `Lattice`, `Material`, `Tally`)
  - [ ] Validators that enforce physical/geometric correctness (closed regions, non-overlapping cells, valid material refs)
  - [ ] XML serializer producing `geometry.xml` / `materials.xml` / `tallies.xml`
  - [ ] Round-trip property tests (model → XML → parsed → model)
- [ ] `promptmc.benchmarks` — library of validated reference geometries
  - [ ] PWR pin cell (Mosteller benchmark)
  - [ ] BWR pin cell
  - [ ] Godiva (HEU sphere)
  - [ ] Jezebel (Pu sphere)
  - [ ] 3×3 PWR fuel mini-assembly
  - [ ] ICSBEP HEU-MET-FAST-001 case
- [ ] `promptmc.generation` — constrained LLM pipeline
  - [ ] OpenAI / Anthropic / local-LLM agnostic interface
  - [ ] JSON-schema-mode generation against the Pydantic models
  - [ ] Self-validation loop: emit → validate → repair → re-emit
  - [ ] Confidence scoring grounded in validation, not heuristics
- [ ] CLI: rebuild `promptmc ask` on top of structured generation; remove keyword router
- [ ] MCP tool: `openmc_design(description: str) -> GeometryModel`

**Acceptance:** A user can say "design a PWR pin cell with 4.95% UO₂ at 0.41 cm radius" and get a runnable, validated, physics-checked OpenMC input set.

## Phase 7 — Hosted Compute (v3.0)

**Goal:** Customers don't have to manage HPC. Submit a model, get results.

- [ ] `promptmc-cloud` service (Python FastAPI backend)
- [ ] Authentication, billing, usage metering
- [ ] Compute backend: Coreweave / AWS Batch / RunPod / Lambda Cloud (pluggable)
- [ ] Cross-section data hosting and version-pinning (TENDL, ENDF/B-VIII.0, JEFF)
- [ ] Reproducibility: every simulation gets a content-addressed hash including code, data, and inputs
- [ ] CLI: `promptmc cloud submit ./input/` and `promptmc cloud results <id>`
- [ ] MCP tool: `openmc_run_cloud` for agents
- [ ] Web UI (minimal): job list, status, log streaming, statepoint download

**Acceptance:** An SMR startup can sign up, drop a credit card, and run their first cloud OpenMC simulation in under 10 minutes with no IT setup.

## Phase 8 — Team & Enterprise (v4.0)

**Goal:** Move from per-seat to team plans. Lock in customers with workflow features they can't easily replace.

- [ ] Team workspaces with shared geometry libraries
- [ ] Design version control (every model is a git-like commit)
- [ ] Simulation history with diffing and comparison
- [ ] Audit trail: every cross-section data version, every input change, every result, immutable
- [ ] Verification suite: automated runs against ICSBEP / Mosteller / Kord benchmarks for any new design
- [ ] Compliance scaffolding for NRC Part 50/52/53 documentation
- [ ] On-prem / VPC deployment option for security-conscious customers
- [ ] SAML / SSO

**Acceptance:** A 20-engineer SMR startup can use PromptMC as the system of record for their reactor physics work. Switching cost is high enough that they don't want to leave.

## Long-term horizons (beyond v4)

- **Adjacent markets:** medical isotope production (shielding, dosimetry), space nuclear (NTP, fission surface power), fusion neutronics
- **Multi-physics coupling:** integrate with thermal-hydraulics (e.g., Cardinal/MOOSE), depletion (OpenMC + ORIGEN)
- **Regulatory tooling:** NRC Part 53 application generation
- **Open core wedge:** keep the library and MCP server open, monetize hosting + team features (Sentry / GitLab model)

## What we are explicitly *not* doing

- Not building a Next.js / React 3D web app as the primary interface (that was the v1 vision; rejected — the market wants programmatic and agentic, not UI)
- Not chasing utilities, regulators, or national labs as the first paying customer (wrong velocity, wrong decade)
- Not competing with Westinghouse / Framatome / SCALE / MCNP head-on; we serve the segment they don't
- Not generating reactor designs autonomously without human-in-the-loop verification (liability)
- Not adding features to the v1 CLI beyond what supports v2+ (CLI is now a thin adapter, not the product)

## Success metrics by phase

| Phase | Lead metric | Lag metric |
|---|---|---|
| v2.0 | MCP installs / week | Demo videos shipped |
| v2.5 | Reference geometries validated against ICSBEP | Design-partner pilots signed |
| v3.0 | Time-to-first-simulation for new signup | Paying customers > 0 |
| v4.0 | Sims/customer/month | ARR |
