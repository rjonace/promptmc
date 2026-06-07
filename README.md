# PromptMC

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![CI](https://img.shields.io/github/actions/workflow/status/rjonace/promptmc/ci.yml)

OpenMC is powerful and painful: you hand-write XML, manage batch runs, and read results out of HDF5. PromptMC is the infrastructure layer that reduces that friction — a validated CLI and MCP server.

It works like a grammar checker between an AI LLM assistant and OpenMC: your AI proposes a configuration, PromptMC validates XML structure and supported schema constraints before the simulator runs, and catches malformed inputs early.

Most planning and schema-validation workflows work without OpenMC installed; execution, geometry-debug checks, and 2D plot rendering require OpenMC.

---

## What you can do

**Without OpenMC:**
- Describe a simulation in plain English → a validated plan and `settings.xml` (the default planner uses no generative AI)
- Validate XML structure and PromptMC's supported OpenMC schemas
- Drive planning and schema validation from an AI client via the MCP server

**With OpenMC:**
- Run simulations (subprocess or Python API)
- Run geometry-debug overlap checks and generate 2D slice plots inside your AI chat client
- Parse statepoint and tally outputs without touching HDF5

---

## Quick start

```bash
pip install promptmc
```

No OpenMC needed:

```bash
promptmc ask "concrete shielding calculation with 1 million particles"
promptmc ask "pin cell criticality with 50k particles" --write
```

By default, `ask` uses a deterministic local planner — no API key, no network, no generative AI. The optional `--llm` flag calls Google Gemini (set GEMINI_API_KEY), which can interpret more open-ended natural-language requests. Customize the model name with GEMINI_MODEL (defaults to gemini-3.5-flash).

See the [CLI reference](docs/cli-reference.md) for provider setup.

---

## MCP server

PromptMC exposes a Model Context Protocol server so AI assistants can run OpenMC workflows natively — validation, plotting, execution, and result parsing from inside your LLM chat client.

```bash
pip install promptmc
promptmc-mcp
```

**Claude Desktop:**

```json
{
  "mcpServers": {
    "promptmc": {
      "command": "promptmc-mcp",
      "env": { "OPENMC_CROSS_SECTIONS": "/path/to/cross_sections.xml" }
    }
  }
}
```

Also works with Cursor, Windsurf, and Google Antigravity.

**Tools:** `openmc_validate`, `openmc_schema_check`, `openmc_template`, `openmc_list_templates`, `openmc_run`, `openmc_analyze`, `openmc_plot` (2D slice, returned to the chat client), `openmc_geometry_debug`, `openmc_check_installation`, `openmc_check_cross_sections`.

Resources expose the configured cross-sections path, the session's tool-call history, and the bundled examples.

Every output is reviewed by a human. PromptMC is an assistant, never an autonomous designer.

---

## Documentation

- [Installation](docs/installation.md) — setup paths for PromptMC, OpenMC, and nuclear data
- [CLI reference](docs/cli-reference.md) — commands, flags, environment variables
- [Python API](docs/python-api.md) — scripting PromptMC
- [Templates](docs/cli-reference.md#templates) · [Telemetry](docs/telemetry-and-audit.md)
- [Examples](examples/uo2_criticality/README.md) · [MCP example](examples/mcp/README.md)
- [Roadmap](ROADMAP.md) · [Changelog](CHANGELOG.md) · [Contributing](CONTRIBUTING.md)

---

## Installation

```bash
pip install promptmc              # core (includes CLI, MCP server, and Gemini planner)
pip install promptmc[telemetry]   # + OpenTelemetry tracing
```

**OpenMC** (required for simulation execution, geometry-debug checks, and plot rendering) is not on PyPI — build from source per [docs.openmc.org](https://docs.openmc.org/en/stable/quickstart.html). Planning and XML/schema validation work without it.

**Cross-section data** (for running simulations):

```bash
pip install openmc-data-downloader
openmc_data_downloader -l TENDL-2019 -i U235 U238 O16 H1 -d cross_sections
export OPENMC_CROSS_SECTIONS=$(pwd)/cross_sections/cross_sections.xml
```

---

## CLI at a glance

```bash
promptmc ask "criticality run with 100k particles" --write   # plan (no OpenMC)
promptmc template criticality --particles 10000              # generate settings.xml
promptmc validate input.xml --schema                         # validate
promptmc run input.xml --threads 4                           # run (needs OpenMC)
promptmc batch batch_spec.yaml --parallel threads --workers 4
promptmc analyze ./output --json results.json
promptmc info                                                # environment status
```

Full options in the [CLI reference](docs/cli-reference.md).

---

## Quality

279 tests · 87% coverage · CI on Python 3.10–3.13 · strict MyPy · zero Ruff warnings · Bandit scanning.

---

## Safety

PromptMC is an engineering-assist tool that keeps a human in the loop. It is not a substitute for professional engineering judgment, independent verification and validation, or regulatory review, and is not for safety, licensing, or other regulated decisions. Reproducing a published benchmark is not qualification for safety analysis. Provided as-is (see [LICENSE](LICENSE)).

## About

I studied nuclear engineering at MIT over 20 years ago, running MCNP 4 for my senior thesis. Though I left during my senior year, I eventually went back to university to get a degree in Computer Science, and I have spent the last 11 years working as a software engineer and site reliability engineer at a major FAANG cloud provider.

PromptMC bridges those two worlds. It is also, for me, an exploration of using agentic programming to build software for fun but still holding professional production principles and standards.

## Contributions and Support

I welcome contributions! Please ensure all checks pass (`pytest`, `ruff check`, `mypy src/`) before opening a PR.
- **License:** MIT
- **Documentation:** [GitHub Repository](https://github.com/rjonace/promptmc)
- **Issues and Discussions:** [GitHub Issues](https://github.com/rjonace/promptmc/issues)
- **Roadmap:** [ROADMAP.md](ROADMAP.md) for planned features and scope.
