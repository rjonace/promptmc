# PromptMC

**Validated OpenMC workflows for AI-assisted reactor physics.**

OpenMC is powerful and painful: you hand-write XML, manage batch runs, and read results out of HDF5. PromptMC is the infrastructure layer that removes that friction — a validated CLI and MCP server.

It works like a grammar checker between an AI assistant and OpenMC: the AI proposes a configuration, PromptMC validates it against physical and geometric constraints before the simulator runs, and catches the impossible geometries that would otherwise crash it. Most of it works without OpenMC installed.

---

## What you can do

**Without OpenMC:**
- Describe a simulation in plain English → a validated plan and `settings.xml` (the default planner uses no generative AI)
- Validate and schema-check OpenMC
- Drive any of the above from an AI client via the MCP server

**With OpenMC:**
- Run simulations (subprocess or Python API)
- 2D geometry slice plots inside your AI chat client
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

By default, `ask` uses a deterministic local planner — no API key, no network, no generative AI. The optional `--llm` flag calls an external OpenAI-compatible model, configured through environment variables (`PROMPTMC_LLM_API_KEY`, `PROMPTMC_LLM_ENDPOINT`,
`PROMPTMC_LLM_MODEL`); the key is read only from the environment. See the [CLI reference](docs/cli-reference.md) for provider setup.

---

## MCP server

PromptMC exposes a Model Context Protocol server so AI assistants can run OpenMC workflows natively — validation, plotting, execution, and result parsing from inside your LLM chat client.

```bash
pip install promptmc[mcp]
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

**Tools:** `openmc_validate`, `openmc_schema_check`, `openmc_template`, `openmc_list_templates`, `openmc_run`, `openmc_analyze`, `openmc_plot` (2D slice, returned to the chat client), `openmc_geometry_debug`, `openmc_check_installation`, `openmc_check_cross_sections`. Resources expose the configured cross-sections path, the session's tool-call history, and the bundled examples.

Every output is reviewed by a human. PromptMC is an assistant, never an autonomous designer.

---

## Documentation

- [CLI reference](docs/cli-reference.md) — commands, flags, environment variables
- [Python API](docs/python-api.md) — scripting PromptMC
- [Templates](docs/templates.md) · [Telemetry](docs/telemetry.md)
- [Roadmap](ROADMAP.md) · [Contributing](CONTRIBUTING.md)

---

## Installation

```bash
pip install promptmc              # core
pip install promptmc[mcp]         # + MCP server
pip install promptmc[telemetry]   # + OpenTelemetry tracing
```

**OpenMC** (required only for simulation execution) is not on PyPI — build from source per [docs.openmc.org](https://docs.openmc.org/en/stable/quickstart.html). Planning, validation, and geometry work without it.

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

260 tests · 87% coverage · CI on Python 3.10–3.12 · strict MyPy · zero Ruff warnings · Bandit scanning.

---

## Safety

PromptMC is an engineering-assist tool that keeps a human in the loop. It is not a substitute for professional engineering judgment, independent verification and validation, or regulatory review, and is not for safety, licensing, or other regulated decisions. Reproducing a published benchmark is not qualification for safety analysis. Provided as-is (see [LICENSE](LICENSE)).

## Related Work and Ecosystem

PromptMC focuses on a specific, currently underserved layer: **natural-language authoring and fail-fast input validation, exposed to AI assistants via MCP.** It is designed to complement, not replace, the excellent existing tools in the [OpenMC ecosystem](https://github.com/openmc-dev/openmc-ecosystem):

- **Model creation and templating:** [WATTS](https://github.com/watts-dev/watts) and [ELSA](https://github.com/IdahoLabResearch/ELSA).
- **Parametric CAD geometry:** [Paramak](https://github.com/fusion-energy/paramak) (primarily for fusion).
- **Design optimization:** [OpenNeoMC](https://github.com/XuboGU/OpenNeoMC).
- **Verification and validation:** [JADE](https://github.com/JADE-V-V/JADE).

**A natural workflow:**

PromptMC authors and validates the model → hand it downstream to optimization (OpenNeoMC), coupling (Cardinal), or visualization tools.

## About the Author

I studied nuclear engineering at MIT over 20 years ago, running MCNP 4 for my senior thesis. Though I left during my senior year, I eventually went back to univeristy to get a degree in Computer Science and I have spent the last 11 years working as a software engineer and site reliability at a major FAANG cloud provider.

PromptMC bridges those two worlds. It also for me an exploration of using agentic programming to build software—held to strict infrastructure-grade SRE standards.

## Contributions and Support

We welcome contributions! Please ensure all checks pass (`pytest`, `ruff check`, `mypy src/`) before opening a PR.
- **License:** MIT
- **Documentation:** [GitHub Repository](https://github.com/rjonace/promptmc)
- **Issues and Discussions:** [GitHub Issues](https://github.com/rjonace/promptmc/issues)
- **Roadmap:** [ROADMAP.md](ROADMAP.md) for planned features and release timeline.
