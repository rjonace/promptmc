# PromptMC

Validated OpenMC workflows for AI-assisted reactor physics.

> **PromptMC** is an AI-native infrastructure layer for OpenMC nuclear simulations.
> It helps engineers build, validate, run, and analyze Monte Carlo workflows with human-in-the-loop validation. The goal is not autonomous reactor design; the goal is safer, faster OpenMC iteration.

> **Safety & scope.** PromptMC is an engineering-assist tool that keeps a human in the loop. It is **not** a substitute for professional engineering judgment, independent verification & validation, or regulatory review, and it is **not** intended for safety, licensing, or other regulated decisions. Reproducing a published benchmark is not qualification for safety analysis. The software is provided "as is", without warranty of any kind (see [LICENSE](LICENSE)).

## Overview

OpenMC is powerful, but getting started can be challenging: you need to write XML configuration files, understand dozens of parameters, and manage simulation workflows manually.

**PromptMC reduces this friction through current and planned validation-first tools:**

- **Describing simulations in plain English** — Tell it what you want (`"make a shielding calculation with 1M particles"`) and get a validated plan
- **Generating production-ready XML** — Automatically creates `settings.xml` with sensible defaults based on your description
- **Fail-fast validation** — Schema checks today, with stronger geometry guards planned to catch impossible configurations before OpenMC ever runs
- **Managing workflows** — Batch runs, parallel execution, progress tracking, and resource limits
- **Observability built-in** — Distributed tracing and metrics via OpenTelemetry
- **Inline Visual Verification** — Ask for a cross-section and view 2D OpenMC slice plots directly inside your AI chat interface (v2.0, via `openmc_plot`)
- **Results at a glance** — Parse statepoint and tally outputs into structured summaries instead of spelunking HDF5 files

Whether you're new to Monte Carlo or an experienced researcher, PromptMC reduces friction and lets you focus on physics, not configuration.

**Current status:** The CLI and Python APIs are stable, and v2.0 ships the MCP server and agent-facing tools (`promptmc-mcp`, `openmc_plot`, `openmc_geometry_debug`). Structured geometry generation with stronger physics guards is planned for v2.5.

### What exists today vs. planned

| Capability | Status |
|---|---|
| CLI and Python API for OpenMC workflows | Available in v1.x |
| Natural-language planning via `promptmc ask` | Available in v1.x |
| Batch runs, progress reporting, and resource checks | Available in v1.x |
| XML schema validation and result parsing | Available in v1.x |
| MCP server (`promptmc-mcp`) | Available in v2.0 |
| Chat-native 2D plotting via `openmc_plot` | Available in v2.0; uses OpenMC's native plotting mode |
| OpenMC geometry-debug integration | Available in v2.0 |
| Structured geometry generation with stronger physics guards | Planned for v2.5 |

`openmc_plot` is intended as a fast visual sanity check, not a replacement for formal geometry debugging. For interactive model exploration, engineers should still use OpenMC's Plot Explorer from `openmc-dev/plotter`.

### Agent workflow

```
Human engineer
    ↓
AI assistant
    ↓
PromptMC tools: validate → plot → run → analyze
    ↓
OpenMC
    ↓
Structured results reviewed by the human engineer
```

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         CLI Layer                           │
│                    (Typer-based commands)                   │
├─────────────────────────────────────────────────────────────┤
│                      Business Logic                         │
│              (Simulation orchestration & config)            │
├─────────────────────────────────────────────────────────────┤
│                   OpenTelemetry Layer                       │
│         (Distributed tracing & structured metrics)          │
├─────────────────────────────────────────────────────────────┤
│                    OpenMC Integration                       │
│           (Python API & subprocess invocation)              │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **OpenMC Integration**: Python API wrapper and subprocess invocation support
- **Natural-Language Interface**: `promptmc ask` turns plain-English requests into OpenMC plans and settings files
- **Optional LLM Planning**: Use OpenAI-compatible models via `--llm` for richer natural-language interpretation
- **Parallel Execution**: Thread, process, and MPI-based parallel simulation execution
- **Batch Runner**: Run parameter sweeps from YAML/JSON specifications
- **Configuration Templates**: Built-in templates (criticality, fixed source, shielding, reactor pin)
- **Result Visualization**: Parse and visualize simulation outputs with text/JSON export
- **Performance Tools**: System profiling and optimization recommendations
- **Schema Validation**: Pydantic-based validation of OpenMC XML configuration files
- **Advanced Error Handling**: Structured exceptions, retry decorator, and error reporting
- **Progress Reporting**: Real-time simulation progress with Rich progress bars
- **Resource Management**: CPU/memory limits, disk-space checks, and workspace context manager
- **Input Validation**: XML structure validation for OpenMC input files
- **Modern CLI**: Extensible command-line interface built with Typer (12 commands)
- **Optional Observability**: OpenTelemetry integration for distributed tracing and metrics (`pip install promptmc[telemetry]`)
- **Type Safety**: Full type hints, `from __future__ import annotations`, Python 3.10+
- **Quality Assurance**: 260 tests, 87% coverage, and zero ruff warnings
- **Production-Ready**: Strict dependency management with Poetry

## MCP Server (v2.0)

PromptMC exposes an MCP server so AI assistants can run OpenMC workflows directly.

### Installation

```bash
pip install promptmc[mcp]
```

### Usage

```bash
promptmc-mcp
```

### AI Assistant Configuration

#### Claude Desktop (`claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "promptmc": {
      "command": "promptmc-mcp",
      "env": {
        "OPENMC_CROSS_SECTIONS": "/path/to/cross_sections.xml"
      }
    }
  }
}
```

#### Windsurf / Cursor

Add to your MCP server configuration:

```json
{
  "promptmc": {
    "command": "promptmc-mcp"
  }
}
```

### Available Tools

| Tool | Description |
|---|---|
| `openmc_check_installation` | Check OpenMC installation status |
| `openmc_validate` | Validate OpenMC XML input files |
| `openmc_schema_check` | Run Pydantic schema validation |
| `openmc_template` | Generate settings.xml from a template |
| `openmc_list_templates` | List available templates |
| `openmc_run` | Run an OpenMC simulation |
| `openmc_analyze` | Parse simulation results |
| `openmc_check_cross_sections` | Check cross-section data availability |
| `openmc_plot` | Generate 2D geometry slice plot |
| `openmc_geometry_debug` | Run geometry overlap detection |

### Resources

| Resource URI | Returns |
|---|---|
| `promptmc://cross-sections` | Configured `cross_sections.xml` location |
| `promptmc://history` | Tool calls made during this MCP session |
| `promptmc://examples/uo2_criticality` | File listing of the bundled UO2 example |

See [`examples/mcp/`](examples/mcp/README.md) for a scripted walkthrough.

## Installation

### Prerequisites

- Python 3.10 or higher (required for OpenMC Python API compatibility)
- OpenMC (built from source or executable in PATH)
- Nuclear cross-section data (for running simulations)

### Install OpenMC

OpenMC is not available via pip. Build from source:

```bash
# Install build dependencies (macOS with Homebrew)
brew install cmake hdf5

# Clone and build OpenMC
git clone https://github.com/openmc-dev/openmc.git
cd openmc
mkdir build && cd build
cmake ..
make -j4
sudo make install
```

For detailed installation instructions, see https://docs.openmc.org/en/stable/quickstart.html

### Install Nuclear Data

OpenMC requires nuclear cross-section data to run simulations. The easiest way to get this is using the `openmc_data_downloader` package:

```bash
# Install the downloader
pip install openmc-data-downloader

# Download data for specific isotopes (e.g., U-235, U-238, O-16, H-1)
openmc_data_downloader -l TENDL-2019 -i U235 U238 O16 H1 -d cross_sections

# Export the path so OpenMC can find it
export OPENMC_CROSS_SECTIONS=$(pwd)/cross_sections/cross_sections.xml
```

### Install PromptMC

```bash
# Clone the repository
git clone https://github.com/rjonace/promptmc.git
cd promptmc

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode
pip install -e .

# Install with optional telemetry support
pip install -e ".[telemetry]"

# Install development dependencies (optional)
pip install pytest pytest-cov mypy ruff pre-commit bandit types-PyYAML types-psutil types-defusedxml
```

## Quick Start

### Natural-Language Workflow

The easiest way to start is to describe what you want in plain English:

```bash
# Ask for a plan without writing files
promptmc ask "make a concrete shielding calculation with 1 million particles"

# Generate settings.xml directly from natural language
promptmc ask "set up a reactor pin cell criticality run with 50k particles" --write

# Use an OpenAI-compatible LLM for richer interpretation
export OPENAI_API_KEY="..."
promptmc ask "I need a high-statistics shielding model for a 14 MeV source" --llm --write
```

`ask` is offline-first. Without an API key, it uses a deterministic local planner that maps
plain-English domain language to built-in templates and safe defaults. With `--llm`, it can call an
OpenAI-compatible chat completions endpoint configured by:

- **`OPENAI_API_KEY` or `PROMPTMC_LLM_API_KEY`**: API key
- **`PROMPTMC_LLM_MODEL`**: model name, defaults to `gpt-4o-mini`
- **`PROMPTMC_LLM_ENDPOINT`**: OpenAI-compatible endpoint

This makes OpenMC approachable for new users while still producing explicit, reviewable commands and
validated XML files for production workflows.

#### Example Output

```bash
$ promptmc ask "make a concrete shielding calculation with 1 million particles"

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃               Natural-Language OpenMC Plan                     ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Field          │ Value                                         │
├────────────────┼───────────────────────────────────────────────┤
│ Source         │ local                                         │
│ Template       │ shielding                                     │
│ Particles      │ 1,000,000                                     │
│ Batches        │ 10                                            │
│ Inactive       │ 0                                             │
│ Confidence     │ 85%                                           │
│ Command        │ promptmc template shielding --output          │
│                │ settings.xml --particles 1000000 --batches 10 │
└────────────────┴───────────────────────────────────────────────┘

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Summary                                                        ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Use the shielding template with 1,000,000 particles and 10     │
│ batches.                                                       │
└────────────────────────────────────────────────────────────────┘

Why this plan
- Shielding/dose keywords suggest a shielding calculation.

Next steps
- Generate settings.xml from the recommended template.
- Add or verify materials.xml and geometry.xml for the physical model.
- Run schema validation before launching OpenMC.
```

### CLI Usage

```bash
# Natural-language planning
promptmc ask "criticality run for a small reactor with 100k particles"

# Natural-language generation
promptmc ask "make a shielding calculation with 1M particles" --write --output settings.xml

# Check OpenMC installation
promptmc info

# Get system info and tuning recommendations
promptmc system-info

# List available configuration templates
promptmc list-templates

# Generate settings.xml from a template
promptmc template criticality --output settings.xml --particles 10000
promptmc template fixed_source --output settings.xml --particles 50000

# Generate a configuration file (basic)
promptmc configure --output config.xml --particles 10000 --batches 10

# Validate XML structure
promptmc validate input.xml

# Validate XML structure + schema (Pydantic)
promptmc validate input.xml --schema

# Run schema-only check
promptmc schema-check settings.xml
promptmc schema-check ./input_dir/

# Run a simulation (auto-detects API or subprocess)
promptmc run input.xml --threads 4
promptmc run input.xml --mode api
promptmc run input.xml --mode subprocess

# Run a batch of simulations from a YAML spec
promptmc batch examples/batch_spec.yaml --parallel threads --workers 4

# Analyze simulation results
promptmc analyze ./output --json results.json

# Get optimization recommendations
promptmc optimize --threads 4 --particles 10000 --batches 100

# Enable verbose output
promptmc --verbose run input.xml
```

### Python API Usage

```python
from promptmc import (
    ExecutionMode,
    OpenMCInstaller,
    OpenMCRunner,
    OpenMCValidator,
)
from promptmc.telemetry import get_telemetry_manager
from promptmc.visualization import ResultParser

# Check OpenMC installation
installer = OpenMCInstaller()
info = installer.check_installation()
print(f"OpenMC version: {info.version}")
print(f"Python API available: {info.python_available}")

# Validate input files
validator = OpenMCValidator()
validator.validate_input_file("input.xml")

# Generate configuration
runner = OpenMCRunner(execution_mode=ExecutionMode.AUTO)
runner.generate_configuration(
    output_path="settings.xml",
    particles=10000,
    batches=10,
    inactive=5,
)

# Run simulation
result = runner.run_simulation(
    input_path="input.xml",
    threads=4,
    output_path="results",
)

# Parse output
parser = ResultParser()
results = parser.parse_results("results")
print(f"k-effective: {results.k_effective}")
print(f"Statepoint: {results.statepoint_path}")

# Use telemetry (no-op unless `promptmc[telemetry]` is installed)
telemetry = get_telemetry_manager()
telemetry.record_simulation_start("sim-001")

with telemetry.trace_operation("simulation_run", simulation_id="sim-001"):
    # Your simulation code here
    pass

telemetry.record_simulation_complete(
    simulation_id="sim-001",
    duration_seconds=120.5,
)
```

## Development

### Local Development Setup

```bash
# Install development dependencies
poetry install --with dev

# Set up pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
ruff check .
ruff format .

# Run type checking
mypy src/
```

### Project Structure

```
promptmc/
├── src/promptmc/
│   ├── __init__.py              # Package initialization
│   ├── cli.py                   # CLI (12 commands)
│   ├── assistant.py             # Natural-language and optional LLM planning
│   ├── telemetry.py             # OpenTelemetry integration (optional)
│   ├── openmc_integration.py    # OpenMCInstaller, OpenMCValidator, OpenMCRunner
│   ├── _typing.py               # Shared type aliases (PathLike)
│   ├── batch.py                 # Batch and parallel simulation execution
│   ├── templates.py             # Configuration templates
│   ├── visualization.py         # Result parsing and visualization
│   ├── schema.py                # Pydantic schema validation
│   ├── errors.py                # Structured exceptions and retry logic
│   ├── progress.py              # Progress reporting and performance monitoring
│   ├── resources.py             # Resource limits and workspace management
│   └── mcp/                     # MCP server: tools, resources, schemas, stdio server
├── tests/
│   ├── test_cli.py               # CLI tests
│   ├── test_assistant.py         # Natural-language assistant tests
│   ├── test_telemetry.py         # Telemetry tests
│   ├── test_openmc_integration.py # OpenMC integration tests
│   ├── test_parallel.py          # Parallel execution tests
│   ├── test_batch.py             # Batch runner tests
│   ├── test_templates.py         # Template tests
│   ├── test_visualization.py     # Visualization tests
│   ├── test_performance.py       # Performance tools tests
│   ├── test_schema.py            # Schema validation tests
│   ├── test_errors.py            # Error handling tests
│   ├── test_progress.py          # Progress reporting tests
│   ├── test_resources.py         # Resource management tests
│   ├── test_mcp_tools.py         # MCP tool unit tests
│   ├── test_mcp_schemas.py       # MCP Pydantic schema tests
│   ├── test_mcp_resources.py     # MCP resource handler tests
│   └── test_mcp_integration.py   # MCP stdio round-trip integration test
├── examples/                    # Usage examples
│   ├── batch_spec.yaml          # Example batch specification
│   └── uo2_criticality/         # Full UO2 and Light Water criticality example
├── .github/workflows/           # CI/CD pipelines
├── pyproject.toml               # Poetry configuration
└── README.md                    # This file
```

### Code Quality Standards

- **Linting**: Ruff with strict rules
- **Type Checking**: MyPy in strict mode
- **Testing**: pytest with coverage reporting
- **Security**: Bandit security scanning
- **Formatting**: Ruff formatter with 80 character line length

## Telemetry Configuration

Telemetry is **optional**. Install with `pip install promptmc[telemetry]` to enable OpenTelemetry support. Without it, all telemetry calls are no-ops.

### Console Export (Default)

When telemetry is installed, it exports to console by default with no configuration required:

```bash
promptmc run input.xml
# Telemetry output appears in console
```

### OTLP Export

Set the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable to export to an OTLP-compatible backend:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
promptmc run input.xml
```

### Disable Console Export

```bash
export OTEL_CONSOLE_EXPORT="false"
promptmc run input.xml
```

## Roadmap

See the [ROADMAP.md](ROADMAP.md) file for the project's development phases and current status.

## About the Author / Motivation

I studied nuclear engineering at MIT over 20 years ago and used MCNP 4 for my senior thesis project. I left during my senior year and didn't graduated but since then I've had 10 years as a software engineer at a major FAANG cloud provider.

This project is a personal exploration of agentic programming — using AI agents to build software. PromptMC seemed like the perfect test case: it combines my background in nuclear physics with modern software engineering practices. The goal was to see how much of a production-grade tool could be built through agentic coding, from architecture design to implementation, testing, and documentation.

The result is a fully functional, well-tested tool that I hope will be useful to the OpenMC community — whether you're a student learning Monte Carlo methods or a researcher running production simulations.

## Agentic Coding Disclaimer

This project was developed using agentic programming techniques with AI coding assistants, specifically Cascade, Antigravity, and Gemini. While the code was generated through AI-human collaboration, it has been reviewed, tested, and validated for production use. The project demonstrates the potential of agentic workflows while maintaining software engineering best practices: comprehensive testing, linting, type checking, and documentation.

## Contributions

We welcome contributions! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes with tests
4. Ensure all checks pass (`pytest`, `ruff check`, `mypy src/`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Workflow

- All code must pass CI checks before merging
- New features require test coverage
- Follow the existing code style and patterns
- Update documentation for API changes

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [OpenMC](https://openmc.org/) - The Monte Carlo particle transport code
- [Typer](https://typer.tiangolo.com/) - Modern CLI framework
- [OpenTelemetry](https://opentelemetry.io/) - Observability framework

## Support

- Documentation: [GitHub Repository](https://github.com/rjonace/promptmc)
- Issues: [GitHub Issues](https://github.com/rjonace/promptmc/issues)
- Discussions: [GitHub Discussions](https://github.com/rjonace/promptmc/discussions)
