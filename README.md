# PromptMC

**PromptMC** is an AI-native infrastructure layer for OpenMC nuclear simulations. It helps engineers build, validate, run, and analyze Monte Carlo workflows with human-in-the-loop validation. The goal is not autonomous reactor design; the goal is safer, faster OpenMC iteration.

> **Safety & scope.** PromptMC is an engineering-assist tool that keeps a human in the loop. It is **not** a substitute for professional engineering judgment, independent verification & validation, or regulatory review, and it is **not** intended for safety, licensing, or other regulated decisions. Reproducing a published benchmark is not qualification for safety analysis. The software is provided "as is", without warranty of any kind (see [LICENSE](LICENSE)).

**What PromptMC validation does:** checks that XML files are well-formed and conform to the OpenMC schema (correct element names, required attributes, value types), and that the local planner's keyword matching produced a recognizable template choice.

**What it does not do:** verify physical correctness of your geometry, confirm that materials are meaningful for your application, check for geometry overlaps beyond calling OpenMC's own geometry-debug mode, or provide any assurance suitable for licensing, safety analysis, or regulatory submission. Every simulation output must be independently reviewed by a qualified nuclear engineer before any engineering decision is made.

## Overview

OpenMC is powerful, but getting started can be challenging. PromptMC reduces this friction through natural-language planning, automated XML generation, and fail-fast schema validation.

Whether you're new to Monte Carlo or an experienced researcher, PromptMC lets you focus on physics, not configuration.

### Current Status vs. Planned

| Capability | Status |
|---|---|
| CLI and Python API for OpenMC workflows | Available in v1.x |
| Natural-language planning via `promptmc ask` | Available in v1.x |
| Batch runs, progress reporting, and resource checks | Available in v1.x |
| XML schema validation and result parsing | Available in v1.x |
| MCP server (`promptmc-mcp`) | Available in v2.0 |
| Chat-native 2D plotting via `openmc_plot` | Available in v2.0 |
| OpenMC geometry-debug integration | Available in v2.0 |
| Structured geometry generation with stronger physics guards | Planned for v2.5 |

*Note: For interactive 3D model exploration, engineers should still use OpenMC's Plot Explorer from `openmc-dev/plotter`. `openmc_plot` provides fast visual sanity checks natively inside your AI chat interface.*

## MCP Server (v2.0)

PromptMC exposes a Model Context Protocol (MCP) server so AI assistants can securely run OpenMC workflows, validate schemas, and plot geometries directly.

### Installation

```bash
pip install promptmc[mcp]
```

### AI Assistant Configuration

**Claude Desktop (`claude_desktop_config.json`):**
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

**Windsurf / Cursor:**
```json
{
  "promptmc": {
    "command": "promptmc-mcp"
  }
}
```

*For a full list of available MCP tools and resources, see [docs/cli-reference.md](docs/cli-reference.md).*

## Installation

### Prerequisites
- Python 3.10 or higher
- OpenMC installed and in your PATH. *(See the [Official OpenMC Installation Guide](https://docs.openmc.org/en/stable/quickstart.html))*
- Nuclear cross-section data

### Install Nuclear Data
The easiest way to get cross-section data is using the `openmc_data_downloader` package:

```bash
pip install openmc-data-downloader
openmc_data_downloader -l TENDL-2019 -i U235 U238 O16 H1 -d cross_sections
export OPENMC_CROSS_SECTIONS=$(pwd)/cross_sections/cross_sections.xml
```

### Install PromptMC

```bash
git clone https://github.com/rjonace/promptmc.git
cd promptmc
python3 -m venv .venv
source .venv/bin/activate

# Install in editable mode (add [telemetry] for OpenTelemetry support)
pip install -e .
```

## Quick Start

### Natural-Language Workflow

Describe what you want in plain English. `ask` is offline-first and uses a deterministic rule-based planner to map domain language to built-in templates and safe defaults.

```bash
# Generate a plan and output settings.xml directly
promptmc ask "make a concrete shielding calculation with 1 million particles" --write
```
*Output: PromptMC identifies the `shielding` template, maps 1,000,000 particles and 10 batches, and generates the validated `settings.xml` file.*

Use an OpenAI-compatible LLM for richer interpretation:
```bash
export OPENAI_API_KEY="..."
promptmc ask "I need a high-statistics shielding model for a 14 MeV source" --llm --write
```

### CLI Usage

```bash
# Validate XML structure + schema (Pydantic)
promptmc validate input.xml --schema

# Run a schema-only check on a directory
promptmc schema-check ./input_dir/

# Run a simulation (auto-detects API or subprocess)
promptmc run input.xml --threads 4

# Analyze simulation results
promptmc analyze ./output --json results.json
```

*For Advanced CLI usage, Python API examples, and the full Project Architecture, visit the **[Documentation](docs/)** folder. See [examples/](examples/) for working code examples.*

## Related Work & Ecosystem

PromptMC focuses on a specific, currently underserved layer: **natural-language authoring and fail-fast input validation, exposed to AI assistants via MCP.** It is designed to complement, not replace, the excellent existing tools in the [OpenMC ecosystem](https://github.com/openmc-dev/openmc-ecosystem):

- **Model creation & templating:** [WATTS](https://github.com/watts-dev/watts) and ELSA.
- **Parametric CAD geometry:** [Paramak](https://github.com/fusion-energy/paramak) (primarily for fusion).
- **Design optimization:** [OpenNeoMC](https://github.com/XuboGU/OpenNeoMC).
- **Verification & validation:** [JADE](https://github.com/JADE-V-V/JADE).

A natural workflow: PromptMC authors and validates the model → hand it downstream to optimization (OpenNeoMC), coupling (Cardinal), or visualization tools.

## About & Architecture

I studied nuclear engineering at MIT over 20 years ago, running MCNP 4 for my senior thesis. Though I left during my senior year, I spent the next decade working as an infrastructure and site reliability engineer at a major FAANG cloud provider.

PromptMC bridges those two worlds. It is an exploration of agentic programming—using AI agents (Cascade, Claude, Gemini) to build software—held to strict infrastructure-grade SRE standards.

Because AI hallucination is a valid concern in reactor physics, the system is designed with deterministic blast walls. We do not blindly trust the AI:
- **Fail-Fast Schemas:** All AI interactions are routed through strict Pydantic schemas. The AI cannot touch OpenMC directly.
- **Manual Review & Integration Tests:** Tests are verified against real OpenMC runs (`examples/uo2_criticality/`), not just unit test mocks.
- **Static Analysis:** Bandit, strict MyPy, and Ruff provide independent validation untouched by the agent.

The result is a fully functional, highly tested tool designed to make Monte Carlo iteration safer and faster.

## Contributions & Support
We welcome contributions! Please ensure all checks pass (`pytest`, `ruff check`, `mypy src/`) before opening a PR.
- **License:** MIT
- **Documentation:** [GitHub Repository](https://github.com/rjonace/promptmc)
- **Issues & Discussions:** [GitHub Issues](https://github.com/rjonace/promptmc/issues)
