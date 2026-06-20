# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `promptmc doctor`: a single command that runs every onboarding environment check (OpenMC executable on PATH, importable Python API, `OPENMC_CROSS_SECTIONS` set and parseable, referenced cross-section data files present, and the optional `telemetry` extra) and prints one status report with a concrete fix hint for each missing piece. The Python API and telemetry are reported as optional and do not affect the ready/exit status; missing required pieces exit non-zero.
- Provenance header on every emitted `settings.xml`: a leading XML comment recording the PromptMC version, a UTC timestamp, and the exact command used. Written by both the template renderer (`promptmc template`, `promptmc plan --write`) and `OpenMCRunner.generate_configuration()`. Double-hyphens in the recorded command are escaped so the comment stays well-formed XML; OpenMC ignores the comment.
- `--json` structured stdout output on `validate`, `plan`, and `info` (joining `analyze`), so agents and CI can parse results instead of Rich tables. Output is plain, un-styled JSON suitable for piping or redirection. `validate --json` reports malformed XML as `valid: false` data (exiting 1) rather than a raised error.
- `ResultVisualizer.result_to_dict()` and `promptmc.telemetry.telemetry_available()` helpers backing the above.

### Changed
- `mcp` is once again a core dependency (reverting the optional `[mcp]` extra): the `promptmc-mcp` server now installs with `pip install promptmc` out of the box. The `[mcp]` extra is removed and `mcp` no longer appears in the `all` extra; the now-unreachable "install promptmc[mcp]" import guard in `mcp/server.py` was dropped.
- `h5py` is now a core dependency (removing the `[hdf5]` extra): `promptmc analyze` parses statepoint HDF5 out of the box, so the bundled example's `analyze` works from a bare `pip install promptmc` even without OpenMC. `h5py` no longer appears in the `all` extra.
- `promptmc analyze --json` is now a boolean flag that emits the result JSON to stdout (redirect with `>` to save a file) instead of taking a file path, for consistency with the other commands. The `ResultVisualizer.export_json(result, path)` Python API is unchanged.

## [0.3.4] - 2026-06-20

### Added
- **Complete input deck emission**: Templates now produce a complete runnable OpenMC input deck (settings.xml + geometry.xml + materials.xml) instead of just settings.xml, so `promptmc template` output passes `SchemaValidator.validate_directory` and can be handed straight to OpenMC.
- **In-memory model execution**: `OpenMCRunner.run_from_models()` executes simulations straight from validated Pydantic models. When OpenMC's Python API is importable, it maps models to `openmc` objects and runs them without writing an input deck to disk; otherwise it serializes to a working directory and runs the `openmc` executable as a subprocess.
- **Template run methods**: `ConfigurationTemplate.run()` builds geometry/materials/settings and dispatches through `OpenMCRunner.run_from_models` for one-step template execution.
- **Benchmark run methods**: `godiva.run()` and `pwr_pin.run()` convenience methods execute benchmarks with sensible eigenvalue defaults.
- **OpenMC bridges**: `to_openmc_geometry()`, `to_openmc_materials()`, and `to_openmc_settings()` functions in the geometry module for mapping Pydantic models to OpenMC objects.
- **SimulationResult.output_dir**: New field reporting the directory used for the run (useful when `cwd=None` defaults to a temp directory).

### Changed
- **Breaking**: `ConfigurationTemplate.render()` now treats `output_path` as a directory (created if absent) and returns it, instead of writing/returning a single file. The default `-o` for CLI commands is now `openmc_inputs/`.
- Updated all template call sites: CLI `template` and `plan` commands, `NaturalLanguagePlan.render`, MCP `render_template` tool, and `TemplateInput`/`TemplateOutput` schemas.
- Updated documentation: README.md, docs/cli-reference.md, docs/python-api.md, and AGENTS.md §4.1 repository map.

### Fixed
- Removed duplicate imports in `xml_serializer.py` that caused ruff F811 errors.

## [0.3.3] - 2026-06-19

### Added
- `depletion` configuration template — eigenvalue transport settings for a depletion/burnup calculation, available via `promptmc template depletion`, the local planner (depletion/burnup keywords), and the MCP `openmc_template` tool. The burnup schedule itself (timesteps, power, depletion chain) is configured through OpenMC's Python depletion API.
- Quickstart section in the README: a no-OpenMC walkthrough that drives the validation gate (`plan` → `validate --schema`) and shows the gate rejecting a malformed input.
- Executable-based integration test tier (`requires_openmc_exec` marker) that runs the bundled UO2 example end-to-end through the `openmc` executable in subprocess mode and checks the parsed k-effective.

### Changed
- Replaced the non-existent `input.xml` placeholder throughout the README, docs, and examples with `settings.xml` (single file) or `./model` (a directory of `geometry.xml` + `materials.xml` + `settings.xml`), matching how OpenMC actually reads inputs. Renamed `examples/input.xml` → `examples/settings.xml`.

### Removed
- The `configure` CLI command, a redundant subset of `template criticality` that emitted an eigenvalue `settings.xml` (without a source) under the misleading name `openmc_config.xml`. The underlying `OpenMCRunner.generate_configuration()` Python API is retained.

## [0.3.2] - 2026-06-11

### Added
- Troubleshooting section in the installation guide covering the failure modes new users actually hit: `No matching distribution found` (Python older than 3.10, e.g. macOS's bundled 3.9), `externally-managed-environment` (PEP 668), entry points missing from `PATH`, and OpenMC/cross-section detection via `promptmc info`.

### Changed
- Rewrote the installation guide around four install methods — uv (recommended) and pipx for isolated CLI installs, pip for sharing an environment with OpenMC's Python API (required for plot rendering and geometry-debug), and Poetry for development — with a decision table mapping desired features to the right method.
- README installation section now leads with `uv tool install promptmc` and notes the macOS bundled-Python pitfall.
- Social-preview card simplified to mark, wordmark, and tagline; dropped the `pip install` command line.
- README copy fixes: planner-deletion language, restored the MCP-parallels-CLI constraint, consolidated examples.

## [0.3.1] - 2026-06-10

### Added
- PyPI publishing workflow (`.github/workflows/publish.yml`) using trusted publishing (OIDC), triggered when a GitHub release is published.
- PyPI project metadata: repository/changelog/issues URLs, keywords, and license/development-status classifiers.
- `py.typed` marker (PEP 561) so downstream type checkers consume PromptMC's type annotations.
- Python 3.14 in the CI test matrix and trove classifiers.
- Per-release design documents under `docs/design/` — retrospective for v0.1–v0.3, forward-looking (with open questions) for v0.4–v0.9.
- Social/branding kit under `docs/assets/`: 1280×640 social-preview card (SVG + PNG) and a transparent-background PNG logo.

### Fixed
- Codecov uploads now authenticate via OIDC; they had been silently rejected ("Token required - not valid tokenless upload") since Codecov dropped anonymous uploads.
- README images and links now use absolute URLs so the PyPI project page renders them correctly (relative paths 404 on PyPI).
- Added Python 3.14 to the installation guide prerequisites.

### Changed
- Renamed the `ask` CLI command to `plan` (`promptmc plan "..."`). The behavior, flags (`--write`, `--llm`, `--model`, `--output`), and underlying planner are unchanged.
- Moved the bundled UO2 criticality example into the package (`promptmc/examples/uo2_criticality`) so wheels no longer install a top-level `examples` directory into site-packages. The repo-root `examples/` folder (batch spec, MCP walkthrough) now ships in the sdist only.
- New project description, aligned across GitHub and PyPI: "Infrastructure for safely using OpenMC with LLMs: plan, build, validate, run, analyze".
- PyPI keywords aligned with the GitHub repo topics; added `Framework :: Pydantic` classifiers.

## [0.3.0] - 2026-06-07

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

## [0.2.2] - 2026-06-07

### Added
- Integrated `google-genai` SDK as a core dependency to support future Gemini-based constrained generation.

### Changed
- Promoted `mcp` from an optional extra to a core dependency. The MCP server (`promptmc-mcp`) is now available out-of-the-box upon installing `promptmc`.
- Reduced packaging extras to `[telemetry]` only; removed the `[mcp]` extra.
- Transitioned the `ask --llm` planner to use Google Gemini exclusively via the new `GeminiClient` seam.
- Configured Gemini structured outputs using the new `GeminiPlanResponse` Pydantic model to guarantee valid JSON responses.
- Replaced the OpenAI-compatible configuration environment variables (`PROMPTMC_LLM_ENDPOINT` and `OPENAI_API_KEY`) with standard `GEMINI_API_KEY` and `GEMINI_MODEL` (defaulting to `gemini-3.5-flash`).
- Refactored `src/promptmc/mcp/server.py` to import the `mcp` SDK lazily, ensuring standard CLI commands do not incur import overhead.

## [0.2.1] - 2026-06-06

### Changed
- Updated README and ROADMAP to match the current validation surface: planning and XML/schema validation work without OpenMC; simulation execution, geometry-debug checks, and plot rendering require OpenMC.
- Fixed stale documentation links and refreshed quality metrics to 268 tests, 88% coverage, and CI on Python 3.10–3.13.
- Added Python 3.13 to the supported/tested version set in documentation and CI.

## [0.2.0] - 2026-05-30

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
- Bumped version to `0.2.0`.
- Coverage increased to **87%** (MCP package ≥80%).
- **README safety and scope disclaimer** — added a prominent human-in-the-loop / not-for-licensing notice near the top of `README.md`.
- **ROADMAP.md** — structured-geometry sprint split into three sequential releases: v0.3 (CSG schema + serialization), v0.4 (validation layer + reference library + deterministic MCP tool), v0.7 (constrained generation pipeline).
- **ROADMAP.md** — added AI audit logging deliverable to v0.4 (deterministic audit trails via OpenTelemetry).
- **Documentation restructure** — trimmed README from 586 to 161 lines; created `docs/` folder with installation, CLI reference, Python API, and telemetry guides; added `CONTRIBUTING.md` with PR gate and scope guard.
- **Style** — replaced all ampersands with 'and' in documentation text for consistency.

## [0.1.2] - 2026-05-25

### Refactored
- **Boilerplate Reduction in CLI**: Refactored `cli.py` to use a single custom error-handling decorator (`_handle_errors`) across all typer CLI commands, significantly reducing redundant try-except blocks.
- **Simplified Schema Validation**: Consolidated validation helper methods in `schema.py` to use a single helper method rather than duplicate blocks for settings, materials, and geometry.
- **Consolidated OpenMC Integration**: Refactored the heavyweight `OpenMCIntegration` class into three focused, single-responsibility classes: `OpenMCRunner`, `OpenMCValidator`, and `OpenMCInstaller`.
- **Streamlined Exception Tree**: Simplified `errors.py` by removing custom context wrappers (`ErrorContext` and `ErrorReporter`), leaving a lightweight exception tree.
- **Psutil and Type Improvements**: Removed optional `psutil` dependency guards (since `psutil` is now required) and unified path typing with a new `PathLike` alias across all files.

### Fixed
- **OpenTelemetry Availability**: Added `pytest.mark.skipif` guards to `test_telemetry.py` to gracefully bypass telemetry tests when the library is installed without the `telemetry` extras.

## [0.1.1] - 2026-05-25

### Changed
- **Consolidated Modules**: Merged parallel and performance tools directly into batch runner, resource monitor, and progress reporter.
- **Removed Plugins**: Removed the plugin registry system (`plugins.py`) to keep core API simple and focused.
- **Lazy Telemetry**: Telemetry dependency components are now lazily loaded and initialized to prevent unnecessary overhead when unused.

## [0.1.0] - 2026-05-23

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
- Bumped version to `0.1.0`
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

## [0.0.3] - 2026-05-23

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
- Bumped version to 0.0.3

## [0.0.2] - 2026-05-17 (Phase 2)

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

## [0.0.1] - 2026-05-17

### Added
- Project initialization
- Basic CLI structure with stub commands
- Telemetry manager with console and OTLP export
- GitHub Actions CI/CD workflow
