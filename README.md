<p align="center">
  <img src="https://raw.githubusercontent.com/rjonace/promptmc/main/docs/assets/logo.svg" alt="PromptMC logo" width="140">
</p>

<h1 align="center">PromptMC</h1>

<p align="center">
  <a href="https://pypi.org/project/promptmc/"><img src="https://img.shields.io/pypi/v/promptmc" alt="PyPI"></a>
  <img src="https://img.shields.io/pypi/pyversions/promptmc" alt="Python">
  <a href="https://app.codecov.io/gh/rjonace/promptmc"><img src="https://img.shields.io/codecov/c/github/rjonace/promptmc" alt="Coverage"></a>
  <img src="https://img.shields.io/github/actions/workflow/status/rjonace/promptmc/ci.yml" alt="CI">
  <a href="https://github.com/astral-sh/ruff"><img src="https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json" alt="Ruff"></a>
  <a href="https://mypy-lang.org/"><img src="https://www.mypy-lang.org/static/mypy_badge.svg" alt="Checked with mypy"></a>
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
</p>

[OpenMC](https://docs.openmc.org/en/stable/) is powerful but can be painful to use: you hand-write XML, manage batch runs, and read results out of [HDF5](https://www.hdfgroup.org/solutions/hdf5/). It would be great if we could safely use AI to reduce that friction.

PromptMC does that by providing infrastructure and tooling that allows both AI LLM assistants and humans to interact with OpenMC through typed, schema-driven workflows.

It works like a grammar checker between an AI LLM assistant and OpenMC: your AI proposes a configuration, PromptMC validates XML structure and supported schema constraints before the simulator runs, and catches malformed inputs early.

Because AI [hallucination](https://link.springer.com/article/10.1007/s10676-024-09775-5) is a valid concern in reactor physics, the system is designed with deterministic blast walls. Every configuration (from a human, the deterministic local planner, or AI) is validated against the same typed [Pydantic](https://docs.pydantic.dev/) schemas before it reaches the simulator.

## What you can do

Most planning and schema-validation workflows work without OpenMC installed; execution, geometry-debug checks, and 2D plot rendering require OpenMC.

**Without OpenMC installed:**
- Validate XML structure and PromptMC's supported OpenMC schemas
- Describe a simulation → a validated plan and `settings.xml` (the default planner is keyword-based and uses no generative AI)
- Drive planning and schema validation from an AI client via the MCP server

**With OpenMC installed:**
- Run simulations (subprocess or Python API)
- Run geometry-debug overlap checks and generate 2D slice plots inside your AI chat client
- Parse [statepoint and tally](https://docs.openmc.org/en/stable/usersguide/tallies.html) outputs without touching HDF5

## Installation

**Prerequisites:**
- Python 3.10 or higher (note: macOS's bundled Python is 3.9 — `uv` below sidesteps this by fetching its own)

**PromptMC** — quickest as an isolated CLI install via [uv](https://docs.astral.sh/uv/) or [pipx](https://pipx.pypa.io/):

```bash
uv tool install promptmc          # or: pipx install promptmc
```

Or with pip into an existing environment:

```bash
pip install promptmc              # core: CLI, schema validation, the local planner
pip install 'promptmc[mcp]'       # + MCP server (promptmc-mcp)
pip install 'promptmc[llm]'       # + Gemini-backed `plan --llm`
pip install 'promptmc[hdf5]'      # + HDF5 statepoint parsing without OpenMC's Python API
pip install 'promptmc[yaml]'      # + YAML batch specs (JSON works without it)
pip install 'promptmc[monitoring]'# + psutil-based resource/perf monitoring
pip install 'promptmc[telemetry]' # + OpenTelemetry tracing
pip install 'promptmc[all]'       # everything above except telemetry
```

The core install depends only on `typer`, `rich`, `pydantic`, `defusedxml`, and `tenacity`; heavier integrations live behind the extras above and degrade gracefully (or raise a clear "install promptmc[…]" error) when absent.

Plot rendering and geometry-debug import OpenMC's Python API, so for those install PromptMC with pip into the same environment as OpenMC (e.g. your conda env). Everything else — planning, validation, MCP server (`[mcp]`), and simulation runs via the `openmc` executable — works from an isolated install.

**OpenMC** (required for simulation execution, geometry-debug checks, and plot rendering) can be installed via Conda, Spack, Docker, or build from source per [docs.openmc.org](https://docs.openmc.org/en/stable/quickinstall.html). Planning and XML/schema validation work without it.

**[Cross-section data](https://www.nndc.bnl.gov/endf/)** (for running simulations):

```bash
pip install openmc-data-downloader
openmc_data_downloader -l TENDL-2019 -i U235 U238 O16 H1 -d cross_sections
export OPENMC_CROSS_SECTIONS=$(pwd)/cross_sections/cross_sections.xml
```

See [installation](https://github.com/rjonace/promptmc/blob/main/docs/installation.md) for more details.

## Quickstart

The validation gate is the core of PromptMC, and you can exercise it with no OpenMC install, no cross-section data, and no API key.

```bash
# 1. Turn a plain-English request into a complete input deck (deterministic local planner, no API key)
promptmc plan "pin cell criticality with 50k particles" --write   # writes openmc_inputs/

# 2. Validate the deck against PromptMC's typed schemas
promptmc validate openmc_inputs --schema      # passes
```

`--write` emits a directory (default `openmc_inputs/`) containing a complete,
runnable deck — `settings.xml`, `geometry.xml`, and `materials.xml`.

The gate's job is catching malformed inputs before a run consumes them. Hand it a value an AI assistant might plausibly invent, such as `<run_mode>criticalize</run_mode>`, and it rejects the input and reports what was allowed:

```text
[ERROR] (settings.xml:run_mode)
        Input should be 'eigenvalue', 'fixed source', 'plot', 'particle restart' or 'volume'
```

The error is structured, so an assistant can read it and self-correct.

### From a deck to a full run

`plan --write` and `promptmc template` emit a complete deck directory
(`settings.xml`, `geometry.xml`, `materials.xml`, plus an optional
`tallies.xml`). With OpenMC and cross-section data installed, run it directly:

```bash
promptmc run ./openmc_inputs        # runs the simulation
promptmc analyze ./openmc_inputs    # k-effective and tallies, parsed from the statepoint
```

The built-in templates back their decks with validated reference geometries
(PWR pin, Godiva); swap in your own `geometry.xml`/`materials.xml` for a custom
model.

## MCP server

PromptMC exposes a [Model Context Protocol](https://modelcontextprotocol.io) server so AI assistants can run OpenMC workflows natively — validation, plotting, execution, and result parsing from inside your LLM chat client, such as Claude Desktop, Cursor, and Google Antigravity.

The point of routing these through MCP is that an assistant can validate its own generated geometry and inputs (schema checks, overlap detection) before you spend a run on them, catching the malformed inputs that are easy for an LLM to produce and hard to spot by eye.

**[Tools](https://modelcontextprotocol.io/docs/concepts/tools):** `openmc_validate`, `openmc_schema_check`, `openmc_template`, `openmc_list_templates`, `openmc_run`, `openmc_analyze`, `openmc_plot` (2D slice, returned to the chat client), `openmc_geometry_debug`, `openmc_check_installation`, `openmc_check_cross_sections`.

[Resources](https://modelcontextprotocol.io/docs/concepts/resources) expose the configured cross-sections path, the session's tool-call history, and the bundled examples.

**Setup:** see the [MCP server configuration guide](https://github.com/rjonace/promptmc/blob/main/docs/mcp.md) for per-client steps (Claude Desktop/Code, Cursor, Google Antigravity, VS Code).

## CLI

By default, `plan` uses a deterministic local planner, needing no API key, no network, no generative AI. The optional `--llm` flag calls Google Gemini (set GEMINI_API_KEY), which can interpret more open-ended natural-language requests. Customize the model name with GEMINI_MODEL (defaults to gemini-3.5-flash).

```bash
<<<<<<< HEAD
promptmc plan "pin cell criticality with 50k particles" --write
promptmc validate settings.xml --schema                         # structure + schema, no OpenMC needed
promptmc template criticality --particles 10000                 # generate settings.xml
=======
promptmc doctor                                                 # one-shot environment check with fix hints
promptmc validate openmc_inputs --schema                        # structure + schema, no OpenMC needed
promptmc template criticality --particles 10000                 # generate a complete input deck dir
>>>>>>> devin/1781955416-task8-run-from-models
promptmc run ./model --threads 4                                # needs OpenMC (geometry + materials + settings)
promptmc batch batch_spec.yaml --parallel threads --workers 4
promptmc analyze ./model --json > results.json                  # parse statepoint + tallies
promptmc plan --llm "concrete shielding calculation with 1 million particles"
promptmc info                                                   # OpenMC installation details
promptmc doctor                                                 # one-shot environment check with fix hints
```

Full options in the [CLI reference](https://github.com/rjonace/promptmc/blob/main/docs/cli-reference.md).

## Safety

PromptMC is an engineering-assist tool that keeps a human in the loop. It is not a substitute for professional engineering judgment, independent verification and validation, or regulatory review, and is not for safety, licensing, or other regulated decisions. Reproducing a published benchmark is not qualification for safety analysis. Provided as-is (see [LICENSE](https://github.com/rjonace/promptmc/blob/main/LICENSE)).

The goal is not autonomous reactor design; the goal is safer, faster OpenMC iteration.

## Documentation

- [Installation](https://github.com/rjonace/promptmc/blob/main/docs/installation.md)
- [MCP server](https://github.com/rjonace/promptmc/blob/main/docs/mcp.md)
- [CLI reference](https://github.com/rjonace/promptmc/blob/main/docs/cli-reference.md)
- [Python API](https://github.com/rjonace/promptmc/blob/main/docs/python-api.md)
- [Templates](https://github.com/rjonace/promptmc/blob/main/docs/cli-reference.md#templates) · [Telemetry](https://github.com/rjonace/promptmc/blob/main/docs/telemetry-and-audit.md)
- [Examples](https://github.com/rjonace/promptmc/blob/main/examples/README.md)
- [Design docs](https://github.com/rjonace/promptmc/blob/main/docs/design/README.md)
- [Roadmap](https://github.com/rjonace/promptmc/blob/main/ROADMAP.md) · [Changelog](https://github.com/rjonace/promptmc/blob/main/CHANGELOG.md) · [Contributing](https://github.com/rjonace/promptmc/blob/main/CONTRIBUTING.md)

## About

I studied nuclear engineering at MIT over 20 years ago, running MCNP 4 for my senior thesis. Though I left during my senior year, I eventually went back to university to get a degree in Computer Science, and I have spent the last 11 years working as a software engineer and site reliability engineer at a major FAANG cloud provider.

PromptMC bridges those two worlds. It is also, for me, an exploration of using agentic programming to build software for fun but still holding professional production principles and standards.

## Contributions and Support

I welcome contributions! Please ensure all checks pass (`pytest`, `ruff check`, `mypy src/`) before opening a PR.
- **License:** MIT
- **Documentation:** [GitHub Repository](https://github.com/rjonace/promptmc)
- **Issues and Discussions:** [GitHub Issues](https://github.com/rjonace/promptmc/issues)
- **Roadmap:** [ROADMAP.md](https://github.com/rjonace/promptmc/blob/main/ROADMAP.md) for planned features and scope.
