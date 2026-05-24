# OpenMC Wrapper

Production-grade Python wrapper for OpenMC Monte Carlo particle transport simulations.

## Overview

OpenMC is powerful, but getting started can be challenging: you need to write XML configuration files, understand dozens of parameters, and manage simulation workflows manually.

**OpenMC Wrapper solves this by:**

- **Describing simulations in plain English** — Tell it what you want (`"make a shielding calculation with 1M particles"`) and get a validated plan
- **Generating production-ready XML** — Automatically creates `settings.xml` with sensible defaults based on your description
- **Validating before you run** — Schema validation catches errors before OpenMC even starts
- **Managing workflows** — Batch runs, parallel execution, progress tracking, and resource limits
- **Observability built-in** — Distributed tracing and metrics via OpenTelemetry

Whether you're new to Monte Carlo or an experienced researcher, OpenMC Wrapper reduces friction and lets you focus on physics, not configuration.

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
│                    OpenMC Integration                        │
│           (Python API & subprocess invocation)              │
└─────────────────────────────────────────────────────────────┘
```

### Key Features

- **OpenMC Integration**: Python API wrapper and subprocess invocation support
- **Natural-Language Interface**: `openmc-wrapper ask` turns plain-English requests into OpenMC plans and settings files
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
- **Plugin System**: Extensible hook and post-processor plugin architecture
- **Input Validation**: XML structure validation for OpenMC input files
- **Modern CLI**: Extensible command-line interface built with Typer (13 commands)
- **Built-in Observability**: OpenTelemetry integration for distributed tracing and metrics
- **Type Safety**: Full type hints, `from __future__ import annotations`, Python 3.9+
- **Quality Assurance**: 218 tests, 82% coverage, and zero ruff warnings
- **Zero-Config Telemetry**: Console export by default with OTLP support
- **Production-Ready**: Strict dependency management with Poetry

## Installation

### Prerequisites

- Python 3.9 or higher
- Poetry (for development)
- OpenMC (Python API via `pip install openmc` or executable in PATH)

### Install from Source

```bash
# Clone the repository
git clone https://github.com/your-org/openmc-wrapper.git
cd openmc-wrapper

# Install with Poetry
poetry install

# Activate the virtual environment
poetry shell
```

### Install as a Package (when published)

```bash
pip install openmc-wrapper
```

## Quick Start

### Natural-Language Workflow

The easiest way to start is to describe what you want in plain English:

```bash
# Ask for a plan without writing files
openmc-wrapper ask "make a concrete shielding calculation with 1 million particles"

# Generate settings.xml directly from natural language
openmc-wrapper ask "set up a reactor pin cell criticality run with 50k particles" --write

# Use an OpenAI-compatible LLM for richer interpretation
export OPENAI_API_KEY="..."
openmc-wrapper ask "I need a high-statistics shielding model for a 14 MeV source" --llm --write
```

`ask` is offline-first. Without an API key, it uses a deterministic local planner that maps
plain-English domain language to built-in templates and safe defaults. With `--llm`, it can call an
OpenAI-compatible chat completions endpoint configured by:

- **`OPENAI_API_KEY` or `OPENMC_WRAPPER_LLM_API_KEY`**: API key
- **`OPENMC_WRAPPER_LLM_MODEL`**: model name, defaults to `gpt-4o-mini`
- **`OPENMC_WRAPPER_LLM_ENDPOINT`**: OpenAI-compatible endpoint

This makes OpenMC approachable for new users while still producing explicit, reviewable commands and
validated XML files for production workflows.

#### Example Output

```bash
$ openmc-wrapper ask "make a concrete shielding calculation with 1 million particles"

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃               Natural-Language OpenMC Plan                      ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Field          │ Value                                          │
├────────────────┼────────────────────────────────────────────────┤
│ Source         │ local                                          │
│ Template       │ shielding                                      │
│ Particles      │ 1,000,000                                      │
│ Batches        │ 10                                             │
│ Inactive       │ 0                                              │
│ Confidence     │ 85%                                            │
│ Command        │ openmc-wrapper template shielding --output     │
│                │ settings.xml --particles 1000000 --batches 10  │
└────────────────┴────────────────────────────────────────────────┘

┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Summary                                                       ┃
┡━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Use the shielding template with 1,000,000 particles and 10   │
│ batches.                                                      │
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
openmc-wrapper ask "criticality run for a small reactor with 100k particles"

# Natural-language generation
openmc-wrapper ask "make a shielding calculation with 1M particles" --write --output settings.xml

# Check OpenMC installation
openmc-wrapper info

# Get system info and tuning recommendations
openmc-wrapper system-info

# List available configuration templates
openmc-wrapper list-templates

# Generate settings.xml from a template
openmc-wrapper template criticality --output settings.xml --particles 10000
openmc-wrapper template fixed_source --output settings.xml --particles 50000

# Generate a configuration file (basic)
openmc-wrapper configure --output config.xml --particles 10000 --batches 10

# Validate XML structure
openmc-wrapper validate input.xml

# Validate XML structure + schema (Pydantic)
openmc-wrapper validate input.xml --schema

# Run schema-only check
openmc-wrapper schema-check settings.xml
openmc-wrapper schema-check ./input_dir/

# Run a simulation (auto-detects API or subprocess)
openmc-wrapper run input.xml --threads 4
openmc-wrapper run input.xml --mode api
openmc-wrapper run input.xml --mode subprocess

# Run a batch of simulations from a YAML spec
openmc-wrapper batch examples/batch_spec.yaml --parallel threads --workers 4

# Analyze simulation results
openmc-wrapper analyze ./output --json results.json

# Get optimization recommendations
openmc-wrapper optimize --threads 4 --particles 10000 --batches 100

# List loaded plugins
openmc-wrapper list-plugins

# Enable verbose output
openmc-wrapper --verbose run input.xml
```

### Python API Usage

```python
from openmc_wrapper import TelemetryManager
from openmc_wrapper.openmc_integration import OpenMCIntegration, ExecutionMode

# Initialize OpenMC integration
integration = OpenMCIntegration(execution_mode=ExecutionMode.AUTO)

# Check OpenMC installation
info = integration.check_installation()
print(f"OpenMC version: {info.version}")
print(f"Python API available: {info.python_available}")

# Validate input files
integration.validate_input_file("input.xml")

# Generate configuration
integration.generate_configuration(
    output_path="settings.xml",
    particles=10000,
    batches=10,
    inactive=5,
)

# Run simulation
result = integration.run_simulation(
    input_path="input.xml",
    threads=4,
    output_path="results",
)

# Parse output
results = integration.parse_output("results")
print(f"Output files: {results['files']}")

# Use telemetry
telemetry = TelemetryManager()
telemetry.record_simulation_start("sim-001")

with telemetry.trace_operation("simulation_run", simulation_id="sim-001"):
    # Your simulation code here
    pass

telemetry.record_simulation_complete(
    simulation_id="sim-001",
    duration_seconds=120.5,
    particle_count=1000000,
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
openmc-wrapper/
├── src/openmc_wrapper/
│   ├── __init__.py              # Package initialization
│   ├── cli.py                   # CLI (13 commands)
│   ├── assistant.py             # Natural-language and optional LLM planning
│   ├── telemetry.py             # OpenTelemetry integration
│   ├── openmc_integration.py    # OpenMC API wrapper and subprocess support
│   ├── parallel.py              # Parallel execution (threads/processes/MPI)
│   ├── batch.py                 # Batch simulation runner
│   ├── templates.py             # Configuration templates
│   ├── visualization.py         # Result parsing and visualization
│   ├── performance.py           # Performance profiling and optimization
│   ├── schema.py                # Pydantic schema validation
│   ├── errors.py                # Structured exceptions and retry logic
│   ├── progress.py              # Rich progress reporting
│   ├── resources.py             # Resource limits and workspace management
│   └── plugins.py               # Extensible plugin system
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
│   └── test_plugins.py           # Plugin system tests
├── examples/                    # Usage examples
│   └── batch_spec.yaml          # Example batch specification
├── .github/workflows/           # CI/CD pipelines
├── pyproject.toml               # Poetry configuration
└── README.md                    # This file
```

### Code Quality Standards

- **Linting**: Ruff with strict rules
- **Type Checking**: MyPy in strict mode
- **Testing**: pytest with coverage reporting
- **Security**: Bandit security scanning
- **Formatting**: Ruff formatter with 100 character line length

## Telemetry Configuration

### Console Export (Default)

Telemetry is exported to console by default with no configuration required:

```bash
openmc-wrapper run input.xml
# Telemetry output appears in console
```

### OTLP Export

Set the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable to export to an OTLP-compatible backend:

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
openmc-wrapper run input.xml
```

### Disable Console Export

```bash
export OTEL_CONSOLE_EXPORT="false"
openmc-wrapper run input.xml
```

## Roadmap to v1.0

### Phase 1: Core Functionality (Current)
- [x] Project scaffolding with Poetry
- [x] CLI architecture with Typer
- [x] OpenTelemetry integration
- [x] CI/CD pipeline
- [x] Documentation foundation

### Phase 2: OpenMC Integration
- [x] OpenMC Python API wrapper
- [x] Subprocess invocation support
- [x] Input file validation
- [x] Configuration file generation
- [x] Output parsing and analysis

### Phase 3: Advanced Features
- [x] Parallel execution support
- [x] Result visualization
- [x] Configuration templates
- [x] Batch simulation runner
- [x] Performance optimization tools

### Phase 4: Production Features (v1.0)
- [x] Configuration file schema validation
- [x] Advanced error handling
- [x] Progress reporting
- [x] Resource management
- [x] Plugin system
- [x] CLI Phase 4 integration (`schema-check`, `list-plugins`, `--schema` flag)
- [x] Natural-language assistant command (`ask`) with optional OpenAI-compatible LLM mode
- [x] 218 tests, 82% coverage, and zero lint warnings

## About the Author / Motivation

I studied nuclear engineering at MIT over 20 years ago and used MCNP 4 for my senior thesis project. I left during my senior year without graduating. Since then, I've been a software engineer at Google for the past 10 years.

This project is a personal exploration of agentic programming — using AI agents to build software. OpenMC Wrapper seemed like the perfect test case: it combines my background in nuclear physics with modern software engineering practices. The goal was to see how much of a production-grade tool could be built through agentic coding, from architecture design to implementation, testing, and documentation.

The result is a fully functional, well-tested tool that I hope will be useful to the OpenMC community — whether you're a student learning Monte Carlo methods or a researcher running production simulations.

## Agentic Coding Disclaimer

This project was developed using agentic programming techniques with Cascade (an AI coding assistant). While the code was generated through AI-human collaboration, it has been reviewed, tested, and validated for production use. The project demonstrates the potential of agentic workflows while maintaining software engineering best practices: comprehensive testing, linting, type checking, and documentation.

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

- Documentation: [GitHub Repository](https://github.com/rjonace/openmc-wrapper)
- Issues: [GitHub Issues](https://github.com/rjonace/openmc-wrapper/issues)
- Discussions: [GitHub Discussions](https://github.com/rjonace/openmc-wrapper/discussions)
