# Agentic Implementation Instructions for PromptMC

> **Purpose:** This file is written for AI coding agents (Claude Code, Cursor, etc.) tasked with advancing PromptMC. It compresses the project's working norms and concrete next-sprint instructions into one document an agent can ground itself in at session start.
>
> If you are an AI agent reading this: **read all of this file before making changes.** Then check `ROADMAP.md` (the authoritative release plan) and `README.md` for orienting context.
>
> If you are a human: feel free to edit this file. The agent will follow what you write.

---

## 1. North Star

PromptMC is **AI-native infrastructure for nuclear simulation**: validated OpenMC workflows for AI-assisted reactor physics. The product surface is:

1. An **MCP server** that exposes OpenMC operations to AI agents.
2. **Pydantic geometry/material/tally schemas** for OpenMC CSG that are usable as constraint surfaces for LLM-driven structured generation.
3. A **library of validated reference geometries** (PWR pin, BWR pin, Godiva, Jezebel, ICSBEP cases) that ground the generation pipeline.
4. A **constrained-generation pipeline** that produces validated, runnable OpenMC inputs from natural language.

Every change should advance one of these four pillars or harden the existing foundation that supports them.

PromptMC is **not** an unsupervised reactor designer. It is a human-in-the-loop workflow accelerator: validate first, visualize cheaply, run intentionally, and summarize results for engineering review. v0.8 adds **bounded** generation — agents iterate on geometry within validated physics constraints, but a human reviews and approves every output; never autonomous for licensing or safety-critical sign-off.

Do not work on Next.js frontends, REST APIs, or 3D web visualization — there is no web UI. All visual verification must be handled natively via the AI chat client using the `openmc_plot` 2D image tool.

**Guardrails (important).** PromptMC is an open-source tool built for usefulness, not monetization — do not add growth, usage-telemetry, analytics, or upsell machinery. Keep the project **civilian, public, and US-domestic**: never frame benchmarks (including Godiva/HEU and Jezebel/Pu) around weapons, enrichment, or "critical mass" — they are *published* civilian-physics references; and **never bundle or redistribute cross-section data** — users bring their own. These are legal-surface guardrails, not style preferences.

---

## 2. Hard rules (non-negotiable)

These are the engineering norms the project has earned across 0.1 → 0.3. Do not regress them.

1. **All CI must pass:** `ruff check`, `ruff format --check`, `mypy src/`, `pytest`, `bandit -r src/`.
2. **Test coverage must not decrease.** The Codecov number (README badge) is the source of truth. New code requires tests.
3. **Python 3.10+ only.** Use `from __future__ import annotations` at the top of every new module.
4. **Type hints on every public function and class.** Mypy is in strict mode.
5. **Never break the public API** exported from `src/promptmc/__init__.py` without explicit approval.
6. **Never delete or weaken tests** without an explicit human request.
7. **No new direct dependencies** without justification. Optional dependencies belong in `[tool.poetry.extras]`.
8. **Use `defusedxml` for XML parsing.** Bandit will fail if you use stdlib `xml.etree` unsafely.
9. **Use `shlex.join` for any shell-command construction**, never `" ".join(...)`.
10. **Telemetry stays optional.** Never `import opentelemetry` outside `telemetry.py`. Guard it with `_OTEL_AVAILABLE`.
11. **Keep AGENTS.md current — especially the §4.1 repository map.** If you add, move, or rename a module, change the package layout, or change the public API, update the §4.1 map (and any affected acceptance criteria) in the *same commit*. A stale map misleads every future session, so treat it as part of the change, not a follow-up.

---

## 3. Coding standards

- Line length: **80 characters** (enforced by `ruff format`).
- Imports: stdlib → third-party → first-party (`promptmc.*`), enforced by ruff `I001`.
- No mid-file imports. All imports at top of file. (Exception: optional dependencies like `openmc` may be imported inline with a comment explaining why.)
- Path types: prefer `from promptmc._typing import PathLike`.
- Dataclasses for internal value objects. Pydantic only for external boundary schemas (XML parsing, MCP tool inputs/outputs, LLM-generated structured outputs). This split is intentional: dataclasses for internal plumbing, Pydantic where data crosses a trust boundary and needs validation or JSON-schema generation.
- Pydantic schemas for MCP tools: use `Literal` for constrained string fields (e.g., `Literal["error", "warning", "info"]` for severity) instead of plain `str` for stronger typing and better JSON Schema generation for LLM clients.
- Docstrings: Google style. Required on all public APIs.
- Errors: subclass `PromptMCError` for new error types. The unified hierarchy lives in `errors.py`.
- Logging: use `configure_logging()` from `errors.py`; do not add new logging frameworks.
- Comments: do not add or delete comments unless asked. Code should self-document via names and types.

---

## 4. The shipped foundation: repository map, tool surface, invariants

v0.1–v0.3 have shipped. The MCP layer is live — **do not re-implement it.** This
section orients you to what already exists and the invariants to preserve.

### 4.1 Repository map (where things live)

```
src/promptmc/
├── __init__.py            # public API: OpenMCInstaller/OpenMCValidator/OpenMCRunner, ExecutionMode, BatchRunner, ParallelConfig/ParallelMode
├── _typing.py             # shared type aliases (PathLike)
├── cli.py                 # Typer CLI entry point (dispatches into commands/)
├── commands/              # one module per CLI subcommand: plan, run, validate, analyze, batch, templates, info, configure
├── openmc_integration.py  # core OpenMC wrapper — OpenMCInstaller / OpenMCValidator / OpenMCRunner (subprocess + Python API), ExecutionMode
├── schema.py              # Pydantic validation of OpenMC XML (Settings/Materials/Geometry…) + SchemaValidator; uses defusedxml
├── templates.py           # config templates (Criticality / FixedSource / Shielding / ReactorPin) + TemplateRegistry
├── assistant.py           # NL planner behind `promptmc plan` (NaturalLanguageAssistant) — the keyword router v0.8 replaces
├── batch.py               # batch + parallel execution (BatchRunner, ParallelExecutor)
├── resources.py           # resource limits / monitoring / cleanup, temp simulation workspaces
├── progress.py            # progress reporting + system profiling / performance monitoring
├── visualization.py       # result parsing (ResultParser → StatePoint.keff) + plotting
├── errors.py              # PromptMCError hierarchy + configure_logging() + retry logic
├── telemetry.py           # optional OpenTelemetry (TelemetryManager; no-ops when absent) — the v0.9 hook
├── geometry/              # Pydantic CSG models, materials, tallies schemas + XML serializer (v0.3)
├── benchmarks/            # validated reference geometries library: Godiva, PWR pin (v0.3/v0.4)
├── examples/              # bundled UO2 criticality example (package data backing the MCP examples resource)
└── mcp/                    # the v0.2 MCP server
    ├── server.py          #   stdio server; wires the SDK to the tools
    ├── tools.py           #   pure tool functions (no SDK dependency)
    ├── schemas.py         #   Pydantic input/output schema per tool
    └── resources.py       #   MCP resource handlers
```

**New code lands in new packages** (don't look for these yet — they arrive with
the roadmap): `components/` (v0.7), `generation/` (v0.8 pipeline). The
v0.9 telemetry + audit work extends `telemetry.py`.

> **Keep this map current** — update it in the same commit as any module
> add/move/rename or public-API change (hard rule #11). A stale map is worse than none.

### 4.2 The MCP tool surface (shipped in v0.2)

Ten agent-callable tools, each with a Pydantic input/output schema (`mcp/schemas.py`),
implemented as pure functions (`mcp/tools.py`) and wired to the SDK (`mcp/server.py`):

| Tool | Wraps |
|---|---|
| `openmc_check_installation` | `OpenMCInstaller.check_installation()` |
| `openmc_validate` | `OpenMCValidator.validate_input_file()` |
| `openmc_schema_check` | `SchemaValidator.validate_directory()` |
| `openmc_template` | `get_template().render()` |
| `openmc_run` | `OpenMCRunner.run_simulation()` |
| `openmc_analyze` | `ResultParser.parse_results()` (uses `StatePoint.keff`) |
| `openmc_list_templates` | `list_templates()` |
| `openmc_check_cross_sections` | cross-section discovery |
| `openmc_plot` | `openmc.Plot` — 2D PNG via OpenMC's native plotting |
| `openmc_geometry_debug` | OpenMC `--geometry-debug` (overlaps / lost particles) |

Plus three resources: `promptmc://cross-sections`, `promptmc://history`,
`promptmc://examples/uo2_criticality`. Use OpenMC's own parsers/plotting rather
than hand-rolled equivalents.

### 4.3 Invariants the MCP layer must keep

- Do not modify `cli.py` for new tools. The MCP layer parallels the CLI; it does
  not extend it.
- Do not add LLM calls to the MCP layer. PromptMC provides tools to *some other*
  agent; **it is not the agent.**
- Synchronous tool calls only — no streaming, no `openmc_run_async`. Async
  orchestration is out of scope.
- MCP stdio assumes trusted local invocation — no auth layer.
- Every MCP tool gets a unit test that exercises it **through the MCP layer** (not
  just the underlying function), plus an entry in the integration round-trip.

---

## 5. Current roadmap: Structured Geometry → Generation → Provenance (v0.4 → v0.9)

The remaining work ships as sequential, independently-valuable minor releases with increasing risk — deterministic foundation first, LLM generation later, provenance to close. Build them in order; each must ship standalone value against the acceptance criteria below. **This section mirrors `ROADMAP.md`, which is the authoritative source; if the two ever disagree, ROADMAP wins and this section should be reconciled to it.**

Each release has a design document under `docs/design/` with the architecture, key decisions, testing strategy, and open questions. **Read the matching design doc before starting a sprint**, and if the implementation diverges from it, update the design doc in the same PR.

### 5.1 Release plan

| Version | Scope | Risk |
|---|---|---|
| **v0.4** | Validated reference geometry library (~6 benchmarks) | Low–med |
| **v0.5** | Geometry composition + inspection: deterministic `openmc_build_geometry` + `openmc_query_geometry` / `openmc_list_cells` / `openmc_list_materials` | Low–med |
| **v0.6** | Physics safety gate: deterministic pre-run validation (overlaps, unbounded, void, tracking) + `openmc_trace_point` + extended `promptmc validate` | Med |
| **v0.7** | Component library: reusable components (FuelPin, GuideTube, etc.) + hex lattices, validated against the v0.6 gate | Low–med |
| **v0.8** | Constrained generation: `openmc_design` + validate-and-repair loop (Gemini) + `openmc_diff_geometry` | High |
| **v0.9** | Observability, provenance + audit: OpenTelemetry usage metrics + tracing; spans + local `audit.jsonl`; MCP client / model / provider capture | Low |

### 5.2 Key design decisions to enforce

- **Pydantic v2** with strict validation. Use `model_validator` for cross-field constraints.
- **OpenMC CSG correctness** must be checked at validation time, not at simulation time. A model that validates must produce a runnable OpenMC input.
- **Dual-mode serialization (avoid the double-maintenance trap):** When OpenMC is available, prefer serializing *through* OpenMC objects (map Pydantic models to `openmc.*` objects and call `.export_to_xml()`) to guarantee valid XML and match OpenMC's current schema. When OpenMC is absent, avoid hand-rolling a custom standard-library XML generator—this creates an annoying double-maintenance track. Instead, serialize Pydantic models to a clean, intermediate dictionary structure and use a lightweight, generic dict-to-xml utility to dump the file. Keep the translation layer as dumb as possible.
- **Reference geometries are tested against ICSBEP** where applicable. Each benchmark module must include the expected k-eff and acceptable bounds.
- **Generation behind a thin internal interface.** The pipeline takes a `Generator` protocol; **Google Gemini is the supported provider**, plus a local mock for testing.
- **No LLM calls in tests.** Use a deterministic mock generator that returns prerecorded structured outputs.

### 5.3 Per-release acceptance criteria

**v0.4 — Reference geometry library**
- ~6 reference geometries (Godiva, Jezebel, PWR pin, BWR pin, + selected ICSBEP) build as typed models and round-trip: Pydantic → XML → parsed by OpenMC → simulated → match expected k-eff within 3σ. Each benchmark module includes the expected k-eff and bounds.
- Each geometry is runnable, documented, and independently checked against published results.
- Schema public surface stabilized (experimental flag removed).

**v0.5 — Geometry composition + inspection**
- Deterministic `openmc_build_geometry` MCP tool (semantic JSON → validated geometry object); no LLM.
- Lean inspection surface exposed: `openmc_query_geometry`, `openmc_list_cells`, `openmc_list_materials`.
- (`openmc_trace_point` is deferred to v0.6; `openmc_diff_geometry` to v0.8.)

**v0.6 — Physics safety gate**
- Deterministic pre-run validation catches cell overlaps, unbounded geometries, void cells, and tracking inconsistencies before OpenMC runs (the §7.4 failure modes).
- Structured, human- and AI-readable failure explanations that feed exact fixes back into an agent's context.
- `openmc_trace_point` identifies which cells claim a coordinate.
- Extended `promptmc validate` CLI. **Gate:** all v0.4 reference geometries pass cleanly.

**v0.7 — Component library**
- Reusable, pre-approved components (FuelPin, GuideTube, ControlRod, ReflectorBlock, WaterBox).
- Hexagonal-lattice support for specialized reactor types.
- Every component validated against the v0.6 physics gate before it ships.

**v0.8 — Constrained generation**
- `Generator` protocol behind a thin internal interface; **Google Gemini** is the supported provider, plus a local mock.
- Validate-and-repair loop produces validated, runnable inputs from natural language; the loop is bounded by the v0.6 physics gate (it passes the gate or exits with a structured failure).
- New MCP tool `openmc_design(description: str)`; `promptmc plan` rebuilt on the pipeline; old keyword router deleted.
- `openmc_diff_geometry` shows exactly what the repair loop changed. Minimal audit record (model used + artifact produced).
- A human reviews and approves every output (never autonomous for licensing/safety). No LLM calls in tests (deterministic mock).

**v0.9 — Observability, provenance + audit**
- OpenTelemetry exporter for agent usage metrics (tool-call volume, payload size, schema rejection rates).
- Distributed tracing across the tool surface. Opt-in, local, off by default — never phones home (see §7.5 and hard rule #10).
- Every MCP tool call wrapped in an OpenTelemetry span and written to a local `audit.jsonl`.
- Capture MCP client identity via `clientInfo`; capture model/provider via `PROMPTMC_TRACKING_MODEL` / `PROMPTMC_COMPANY_ID`.
- A deterministic, local record of AI-authored actions for the operator's review and provenance.

---

## 6. Working norms for AI agents on this repo

### 6.1 Sequencing

- One step in progress at a time.
- Use the `todo_list` tool to track multi-step work.
- After every meaningful change set, run `ruff check`, `ruff format --check`, `mypy src/`, and `pytest`. Do not push code that fails any of these locally.
- Make small commits with present-tense imperative messages, prefixed conventionally: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `ci:`, `chore:`, `release:`.

### 6.2 Communication

- When ambiguous, ask a question rather than guessing — but bias toward proposing a default and proceeding if the question is not blocking.
- Surface tradeoffs explicitly. Never hide a decision in a commit.
- If a suggested simplification turns out to be wrong (e.g., the "templates if/elif chain" suggestion in this project's history), say so and recant. Do not double down.

### 6.3 Refactoring discipline

- Prefer minimal upstream fixes over downstream workarounds.
- When deleting a feature (e.g., the plugin system in v0.1.1), delete it everywhere in one commit: source, tests, CLI, docs, and exports. No "shim" half-states.
- When merging modules (e.g., `parallel.py` into `batch.py`), retain meaningful structure inside the file and do not leave "formerly X.py" comments.
- After significant restructuring, update `README.md`, `ROADMAP.md`, and the public API in `__init__.py` in the same commit.

### 6.4 What to do when stuck

- Read the closest test that exercises the area you're modifying.
- Read the git log for the last 5 commits touching the area.
- If still stuck, write a short plan in chat, mark a todo as `in_progress`, and propose the change before implementing it.

### 6.5 Releases

- Bump version in both `pyproject.toml` and `src/promptmc/__init__.py`.
- Tag with `v<major>.<minor>.<patch>` (e.g., `v0.2.0`, not `v0.2`).
- Use `gh release create` with structured release notes (sections: What's Changed, Verified, Full Changelog link).
- Do not release unless all CI is green.

---

## 7. Reference: domain knowledge an agent needs

The following compressed reference exists so an agent does not have to research nuclear physics from scratch every session. Treat it as "good enough" approximations; consult OpenMC docs (`docs.openmc.org`) for authoritative details.

### 7.1 OpenMC at a glance

- **Monte Carlo** particle transport code for neutron and photon transport.
- Inputs: `geometry.xml`, `materials.xml`, `settings.xml`, optionally `tallies.xml`, `plots.xml`.
- Geometry uses **constructive solid geometry (CSG)**: surfaces (planes, spheres, cylinders, cones), half-spaces, regions (intersection/union of half-spaces), cells (regions with a fill), universes (collections of cells), lattices (periodic arrays of universes).
- Outputs: `summary.h5`, `statepoint.<batch>.h5` (HDF5 binary).
- **Run modes:** `eigenvalue` (criticality, k-effective), `fixed source` (shielding/dose).
- **Cross-section data** must be present at `OPENMC_CROSS_SECTIONS` env var or specified in `materials.xml`. Common libraries: ENDF/B-VIII.0, JEFF-3.3, TENDL-2019.

### 7.2 Common simulation types

- **Criticality:** find k-effective for an assembly. Eigenvalue calc. Examples: Godiva (k≈1.0 for HEU sphere), Jezebel (k≈1.0 for Pu sphere).
- **Shielding:** track radiation through walls. Fixed-source calc. Survival biasing helps with deep-penetration efficiency.
- **Reactor pin cell:** small repeating unit of a reactor core. Used for cross-section condensation. Mosteller PWR pin is a canonical benchmark.
- **Depletion:** burnup analysis over time. OpenMC has built-in support; PromptMC does not yet wrap it.

### 7.3 Validation benchmarks worth knowing

- **ICSBEP** (International Criticality Safety Benchmark Evaluation Project): hundreds of validated criticality experiments.
- **Mosteller benchmark:** PWR pin cell with known k-eff at various enrichments and temperatures.
- **Kord Smith's benchmarks:** challenge problems for whole-core analysis.

### 7.4 Failure modes to guard against

- **Unbounded geometry:** a region that doesn't fully enclose particles → infinite tracking → simulation hangs or crashes. Always include a vacuum boundary.
- **Cell overlap:** two cells claiming the same space → particle tracking ambiguity → wrong results.
- **Missing material assignment:** a cell without a fill → undefined behavior.
- **Cross-section data missing isotope:** simulation aborts with "no data for nuclide X".
- **Negative density / mass fractions summing to >1.0:** material physically invalid.

The Pydantic schemas in the geometry module must catch all of these at validation time.

### 7.5 Observability and AI provenance (v0.9)

All of it is **opt-in, local, and off by default** (hard rule #10) — provenance for the operator's own review, not analytics phoned home.

- **Audit logging:** when enabled, wrap each MCP tool call in an OpenTelemetry span and record the inputs (JSON arguments) and the outcome (success/failure), so there is a deterministic local record of what the agent attempted.
- **MCP client capture (automatic):** the MCP `initialize` request carries a `clientInfo` payload naming the client (e.g. "Claude Desktop", "Cursor"). Read it at startup and attach it as the `llm_product` dimension.
- **Model/provider capture (env injection):** MCP doesn't pass the model (the client app owns API keys and routing), so read it from env vars the client sets in its config — `PROMPTMC_TRACKING_MODEL` (→ `llm_model`) and `PROMPTMC_COMPANY_ID` (→ `llm_company`). Example client config:
  ```json
  {
    "mcpServers": {
      "promptmc": {
        "command": "promptmc-mcp",
        "env": {
          "OPENMC_CROSS_SECTIONS": "/path/to/cross_sections.xml",
          "PROMPTMC_TRACKING_MODEL": "gemini-2.5-pro",
          "PROMPTMC_COMPANY_ID": "Google"
        }
      }
    }
  }
  ```
- **Dimensions:** attach `llm_product`, `llm_model`, `llm_company` to spans and counters. Together they let an operator answer, on their own machine, "which client/model drove which tool calls, and how many were rejected by validation" — useful for debugging the agent loop, not a product-analytics pipeline.

---

## 8. End-of-session checklist for agents

Before declaring a task complete:

- [ ] All tests pass locally (`pytest`)
- [ ] `ruff check .` passes
- [ ] `ruff format --check .` passes
- [ ] `mypy src/` passes
- [ ] Coverage did not decrease
- [ ] Public API (`src/promptmc/__init__.py`) updated if new symbols added
- [ ] README updated if user-visible behavior changed
- [ ] ROADMAP item checked off if a roadmap deliverable was completed
- [ ] Design doc (`docs/design/`) updated if the implementation diverged from it
- [ ] Commit messages use conventional prefixes
- [ ] If a release: version bumped in both files, tag created, GitHub release published

When in doubt, ask. The human reviewing this work will trust an agent that surfaces decisions more than one that hides them.
