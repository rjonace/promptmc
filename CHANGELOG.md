# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Renamed the `ask` CLI command to `plan` (`promptmc plan "..."`). The behavior, flags (`--write`, `--llm`, `--model`, `--output`), and underlying planner are unchanged.

## [2.1.0] - 2026-06-07

### Added
- Pydantic v2 models for constructive solid geometry (CSG) primitive types (Surfaces, Regions, Cell, Universe, GeometryModel) in new `promptmc.geometry` package.
- Discriminated union of surfaces including `XPlane`, `YPlane`, `ZPlane`, `Plane`, `Sphere`, `XCylinder`, `YCylinder`, and `ZCylinder`.
- Tree-based region representation (`HalfSpace`, `Intersection`, `Union_`, `Complement`).
- Validation rules for geometry constraints: uniqueness of surface/cell IDs, dangling region references, and anti-hang bounded geometry checks.
- Unified Pydantic material schema validation (`NuclideSpec`, `Material`, `MaterialsModel`) and tallies schema (`TallyFilter`, `Tally`, `TalliesModel`).
- Dual-mode serialization in `xml_serializer.py` that outputs XML using standard `openmc` objects when importable, and gracefully falls back to a clean dictionary-to-xml serializer when `openmc` is absent.
- Validated reference geometry seeds under the new `promptmc.benchmarks` package:
  - `godiva` bare HEU sphere (ICSBEP HEU-MET-FAST-001) with vacuum boundaries.
  - `pwr_pin` pincell (Mosteller PWR pin cell benchmark) with reflective boundaries.
- Conditional pytest execution markers (`requires_openmc` and `requires_openmc_data`) to prevent test suite crashes when OpenMC or cross-section datasets are absent.

## [2.0.2] - 2026-06-07

### Added
- Integrated `google-genai` SDK as a core dependency to support future Gemini-based constrained generation.

### Changed
- Promoted `mcp` from an optional extra to a core dependency. The MCP server (`promptmc-mcp`) is now available out-of-the-box upon installing `promptmc`.
- Reduced packaging extras to `[telemetry]` only; removed the `[mcp]` extra.
- Transitioned the `ask --llm` planner to use Google Gemini exclusively via the new `GeminiClient` seam.
- Configured Gemini structured outputs using the new `GeminiPlanResponse` Pydantic model to guarantee valid JSON responses.
- Replaced the OpenAI-compatible configuration environment variables (`PROMPTMC_LLM_ENDPOINT` and `OPENAI_API_KEY`) with standard `GEMINI_API_KEY` and `GEMINI_MODEL` (defaulting to `gemini-3.5-flash`).
- Refactored `src/promptmc/mcp/server.py` to import the `mcp` SDK lazily, ensuring standard CLI commands do not incur import overhead.

## [2.0.1] - 2026-06-06

### Changed
- Updated README and ROADMAP to match the current validation surface: planning and XML/schema validation work without OpenMC; simulation execution, geometry-debug checks, and plot rendering require OpenMC.
- Fixed stale documentation links and refreshed quality metrics to 268 tests, 88% coverage, and CI on Python 3.10–3.13.
- Added Python 3.13 to the supported/tested version set in documentation and CI.

## [2.0.0] - 2026-05-30

### Added
- **MCP server** (`src/promptmc/mcp/`) — a Model Context Protocol server that exposes PromptMC capabilities as agent-callable tools, allowing AI assistants (Claude Desktop, Cursor, VS Code with Copilot) to drive end-to-end OpenMC workflows without writing Python.
  - `openmc_check_installation` — verify OpenMC installation status.
  - `openmc_validate` — validate an OpenMC input file.
  - `openmc_schema_check` — Pydantic schema validation for an input directory.
  - `openmc_template` — render a named configuration template to XML.
  - `openmc_run` — run an OpenMC simulation.
  - `openmc_analyze` — parse statepoint HDF5 and return k-eff / tally results.
  - `openmc_list_templates` — list all available configuration templates.
  - `openmc_check_cross_sections` — verify cross-section data availability.
  - `openmc_plot` — render a 2D geometry slice as a base64 PNG via OpenMC's native plot API.
  - `openmc_geometry_debug` — run OpenMC geometry-debug mode for overlap detection.
- **MCP resources**: `promptmc://cross-sections`, `promptmc://history`, `promptmc://examples/uo2_criticality`.
- **`promptmc-mcp` CLI entry point** — starts the stdio MCP server.
- **`mcp` optional extra** — `pip install promptmc[mcp]` installs the MCP SDK.
- **Pydantic input/output schemas** for every MCP tool (`src/promptmc/mcp/schemas.py`).
- **MCP test suite** — unit tests for each tool through the MCP layer; integration test spawning the server in a subprocess and exercising `tools/list` and `tools/call` round-trips.
- **`mcp-tests` CI job** running on Python 3.12 in addition to the 3.10/3.11/3.12 matrix.
- **Documentation** — README section on configuring AI assistants with PromptMC's MCP server; sample `claude_desktop_config.json` snippet.

### Changed
- Bumped version to `2.0.0`.
- Coverage increased to **87%** (MCP package ≥80%).
- **README safety and scope disclaimer** — added a prominent human-in-the-loop / not-for-licensing notice near the top of `README.md`.
- **ROADMAP.md** — structured-geometry sprint split into three sequential releases: v2.1 (CSG schema + serialization), v2.2 (validation layer + reference library + deterministic MCP tool), v2.5 (constrained generation pipeline).
- **ROADMAP.md** — added AI audit logging deliverable to v2.2 (deterministic audit trails via OpenTelemetry).
- **Documentation restructure** — trimmed README from 586 to 161 lines; created `docs/` folder with installation, CLI reference, Python API, and telemetry guides; added `CONTRIBUTING.md` with PR gate and scope guard.
- **Style** — replaced all ampersands with 'and' in documentation text for consistency.

## [1.2.0] - 2026-05-25

### Refactored
- **Boilerplate Reduction in CLI**: Refactored `cli.py` to use a single custom error-handling decorator (`_handle_errors`) across all typer CLI commands, significantly reducing redundant try-except blocks.
- **Simplified Schema Validation**: Consolidated validation helper methods in `schema.py` to use a single helper method rather than duplicate blocks for settings, materials, and geometry.
- **Consolidated OpenMC Integration**: Refactored the heavyweight `OpenMCIntegration` class into three focused, single-responsibility classes: `OpenMCRunner`, `OpenMCValidator`, and `OpenMCInstaller`.
- **Streamlined Exception Tree**: Simplified `errors.py` by removing custom context wrappers (`ErrorContext` and `ErrorReporter`), leaving a lightweight exception tree.
- **Psutil and Type Improvements**: Removed optional `psutil` dependency guards (since `psutil` is now required) and unified path typing with a new `PathLike` alias across all files.

### Fixed
- **OpenTelemetry Availability**: Added `pytest.mark.skipif` guards to `test_telemetry.py` to gracefully bypass telemetry tests when the library is installed without the `telemetry` extras.

## [1.1.0] - 2026-05-25

### Changed
- **Consolidated Modules**: Merged parallel and performance tools directly into batch runner, resource monitor, and progress reporter.
- **Removed Plugins**: Removed the plugin registry system (`plugins.py`) to keep core API simple and focused.
- **Lazy Telemetry**: Telemetry dependency components are now lazily loaded and initialized to prevent unnecessary overhead when unused.

## [1.0.0] - 2026-05-23

### Added
- Natural-language OpenMC assistant:
  - New `assistant.py` module with deterministic offline planning from plain-English requests
  - Optional OpenAI-compatible LLM planning via `--llm`
  - New `ask` CLI command to produce a reviewed plan or write `settings.xml`
  - Environment configuration: `OPENAI_API_KEY`, `PROMPTMC_LLM_API_KEY`, `PROMPTMC_LLM_MODEL`, `PROMPTMC_LLM_ENDPOINT`
- Phase 4: Production Features
  - **Schema validation** (`schema.py`) – Pydantic models for `settings.xml`, `materials.xml`, and `geometry.xml`; `SchemaValidator` with per-file and directory validation; severity levels and formatted reports
  - **Advanced error handling** (`errors.py`) – Structured exception hierarchy (`PromptMCError`, `ConfigurationError`, `ValidationError`, `ExecutionError`, `ResourceError`); `ErrorContext` dataclass; `retry` decorator with exponential back-off; `ErrorReporter` with JSON export
  - **Progress reporting** (`progress.py`) – `ProgressReporter` with subscriber callbacks; `RichProgressDisplay` for CLI progress bars; `ProgressStage` enum; `SimulationProgress` for real-time OpenMC log parsing
  - **Resource management** (`resources.py`) – `ResourceLimits` and `ResourceMonitor` with CPU/memory enforcement; `TempDirectoryManager`; `DiskSpace` utilities; `simulation_workspace` context manager
  - **Plugin system** (`plugins.py`) – `Plugin` ABC with lifecycle hooks; `PostProcessorPlugin` and `HookPlugin`; `PluginRegistry` singleton with entry-point discovery; `hook` decorator
- New CLI commands:
  - `ask` – translate plain-English OpenMC requests into template plans and optional `settings.xml` output
  - `schema-check` – standalone Pydantic schema validation for XML files or directories
  - `list-plugins` – list registered plugins discovered from entry points
  - `--schema` flag on `validate` command for combined XML + Pydantic validation
  - Plugin lifecycle hooks wired into `run` command (`before_run`, `after_run`)
  - `--verbose` flag now activates structured logging via `configure_logging()`

### Changed
- Bumped version to `1.0.0`
- CLI refactored: all `except` blocks use `raise ... from e` (B904 resolved)
- `list-templates` now renders a Rich `Table` instead of a plain panel
- README now leads with the plain-English workflow and optional LLM usage
- `pyproject.toml` per-file ignore rules extended for `templates.py` and `openmc_integration.py`

### Fixed
- B904 linting: all re-raised exceptions in `cli.py` now chain with `from e` or `from None`
- SIM105: replaced `try/except/pass` with `contextlib.suppress` in `progress.py` and `schema.py`
- B017: `pytest.raises(Exception)` in `test_schema.py` replaced with `pytest.raises(ValidationError)`
- Unused import `json` removed from `test_cli.py`
- Import sort order fixed in `test_cli.py` and `test_schema.py`

### Tests
- CLI test suite expanded from 5 to 58 tests; CLI coverage remains 80%
- Assistant test suite added with 8 focused tests
- Total test count: **218 tests** (up from 158)
- Total coverage: **82%** (up from 73%)
- Zero `ruff` warnings across `src/` and `tests/`

## [0.2.0] - 2026-05-23

### Added
- Phase 3: Advanced Features
  - **Parallel execution** (`parallel.py`) - thread, process, and MPI-based concurrent simulation execution
  - **Batch runner** (`batch.py`) - parameter sweep simulations from YAML/JSON specifications
  - **Configuration templates** (`templates.py`) - built-in templates for criticality, fixed source, shielding, and reactor pin calculations
  - **Result visualization** (`visualization.py`) - parse statepoint/summary HDF5 files with text and JSON export
  - **Performance tools** (`performance.py`) - system profiling, performance monitoring, and optimization recommendations
- New CLI commands:
  - `template` - generate configuration from template
  - `list-templates` - list all available templates
  - `batch` - run batch simulations from spec file
  - `analyze` - analyze simulation results
  - `optimize` - get optimization recommendations
  - `system-info` - display system info for tuning
- New dependencies: `pyyaml`, `psutil`
- Example batch specification YAML file

### Changed
- Bumped version to 0.2.0

## [0.1.0] - 2026-05-17 (initial release with Phase 2)

### Added
- Phase 2: OpenMC integration module (`openmc_integration.py`)
  - OpenMC Python API wrapper with auto-detection
  - Subprocess invocation support for OpenMC executable
  - Input file validation (XML structure and required files)
  - Configuration file generation with customizable parameters
  - Output parsing for simulation results (statepoint, summary, tallies)
  - Execution mode selection (auto, api, subprocess)
- Updated CLI commands with full OpenMC integration
  - `run` command with `--mode` option for execution mode selection
  - `configure` command with `--particles`, `--batches`, `--inactive` options
  - `validate` command with proper XML validation
  - `info` command with detailed installation detection
- h5py dependency for parsing OpenMC HDF5 output files
- Comprehensive test suite for OpenMC integration

## [0.1.0] - 2026-05-17

### Added
- Project initialization
- Basic CLI structure with stub commands
- Telemetry manager with console and OTLP export
- GitHub Actions CI/CD workflow
