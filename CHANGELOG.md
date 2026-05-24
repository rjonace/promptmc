# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
