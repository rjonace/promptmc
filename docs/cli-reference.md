# CLI Reference

Complete reference for all PromptMC CLI commands.

## Natural-Language Planning

### `promptmc plan`

Turn plain-English requests into OpenMC plans and complete input decks.

`promptmc plan` supports two execution modes:
1. **Local Deterministic Planner (Default):** Runs completely offline with no network calls and no API key. It parses request keywords deterministically to choose templates and estimate particle/batch counts.
2. **Gemini LLM Planner (with `--llm`):** Calls Google Gemini to interpret more complex or open-ended requests. This requires setting the `GEMINI_API_KEY` environment variable.

*Note: The Gemini client and the MCP server are built-in, core features of PromptMC and require no separate installation steps.*

```bash
# Plan without writing files
promptmc plan "make a concrete shielding calculation with 1 million particles"

# Generate a complete input deck directly from natural language (writes openmc_inputs/)
promptmc plan "set up a reactor pin cell criticality run with 50k particles" --write

# Use Google Gemini LLM for richer interpretation
export GEMINI_API_KEY="..."
promptmc plan "I need a high-statistics shielding model for a 14 MeV source" --llm --write

# Specify the output deck directory
promptmc plan "criticality run" --write --output my_inputs

# Use a specific Gemini model
promptmc plan "shielding calculation" --llm --model gemini-2.5-pro --write

# Machine-readable JSON (includes the rebuild command; add --write for "written" path)
promptmc plan "criticality run with 50k particles" --json
```

#### Example Output

```bash
$ promptmc plan "make a concrete shielding calculation with 1 million particles"

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
│ Match score    │ 85%  (3 keywords matched)                     │
│ Command        │ promptmc template shielding --output           │
│                │ openmc_inputs --particles 1000000 --batches 10 │
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
- Render the recommended template into a complete input deck (settings.xml + geometry.xml + materials.xml).
- Review the geometry and materials for the physical model.
- Run schema validation before launching OpenMC.
```

**Note:** The **Match score** is a deterministic count of domain keywords matched, converted to a fixed scale (`min(0.95, 0.55 + 0.1 × matches)`). It is **not** a probabilistic confidence interval — it reflects keyword coverage, not certainty about intent.

## Environment Diagnostics

### `promptmc doctor`

Run every onboarding environment check at once and print a single status
report with a fix hint for each missing piece. Checks: the `openmc`
executable on PATH, the importable Python API, `OPENMC_CROSS_SECTIONS` set and
parseable, the cross-section data files it references present on disk, and the
optional `telemetry` extra. The Python API and telemetry are reported as
optional; missing required pieces exit non-zero.

```bash
# Human-readable status report with fix hints
promptmc doctor

# Machine-readable JSON for CI / agents
promptmc doctor --json
```

## System Information

### `promptmc info`

Show OpenMC installation details (version, Python API, subprocess executable).

```bash
promptmc info

# Machine-readable JSON
promptmc info --json
```

### `promptmc system-info`

Get system information and tuning recommendations.

```bash
promptmc system-info
```

## Templates

### `promptmc list-templates`

List available configuration templates.

```bash
promptmc list-templates
```

### `promptmc template`

Generate a complete OpenMC input deck from a template. `--output` is a
**directory** (default `openmc_inputs/`); each run writes `settings.xml`,
`geometry.xml`, and `materials.xml` into it.

```bash
# Criticality template
promptmc template criticality --output openmc_inputs --particles 10000

# Fixed source template
promptmc template fixed_source --output openmc_inputs --particles 50000

# Shielding template
promptmc template shielding --output openmc_inputs --particles 1000000

# Reactor pin template
promptmc template reactor_pin --output openmc_inputs --particles 50000

# Specify batches and inactive
promptmc template criticality --output openmc_inputs --particles 10000 --batches 100 --inactive 10
```

## Validation

### `promptmc validate`

Validate XML structure and optionally run schema validation.

```bash
# Validate XML structure only
promptmc validate settings.xml

# Validate XML structure + schema (Pydantic)
promptmc validate settings.xml --schema

# Validate multiple files
promptmc validate geometry.xml materials.xml settings.xml --schema

# Machine-readable JSON (exits 1 when invalid; malformed XML is reported as data)
promptmc validate settings.xml --schema --json
```

### `promptmc schema-check`

Run schema-only check on files or directories.

```bash
# Check a single file
promptmc schema-check settings.xml

# Check all supported XML files in a directory
promptmc schema-check ./input_dir/
```

## Simulation Execution

### `promptmc run`

Run an OpenMC simulation.

```bash
# Auto-detect API or subprocess mode
promptmc run ./model --threads 4

# Force API mode
promptmc run ./model --mode api

# Force subprocess mode
promptmc run ./model --mode subprocess

# Specify output directory
promptmc run ./model --output results

# Run with verbose output
promptmc --verbose run ./model

```

### `promptmc batch`

Run a batch of simulations from a YAML specification.

```bash
# Run with thread-based parallelism
promptmc batch examples/batch_spec.yaml --parallel threads --workers 4

# Run with process-based parallelism
promptmc batch examples/batch_spec.yaml --parallel processes --workers 4

# Run with MPI (requires MPI installation)
promptmc batch examples/batch_spec.yaml --parallel mpi --workers 4
```

## Analysis

### `promptmc analyze`

Parse and analyze simulation results.

```bash
# Analyze results in default format
promptmc analyze ./output

# Emit machine-readable JSON to stdout (redirect to save a file)
promptmc analyze ./output --json
promptmc analyze ./output --json > results.json
```

## Optimization

### `promptmc optimize`

Get optimization recommendations for simulation parameters.

```bash
promptmc optimize --threads 4 --particles 10000 --batches 100
```

## Global Options

```bash
# Enable verbose output
promptmc --verbose <command>

# Use a configuration file
promptmc --config path/to/config <command>

# Show version
promptmc --version

# Show help
promptmc --help
promptmc <command> --help
```

## Environment Variables

- `OPENMC_CROSS_SECTIONS`: Path to cross_sections.xml file
- `GEMINI_API_KEY`: API key for Gemini LLM planning (when `--llm` is used)
- `GEMINI_MODEL`: Gemini model name (default: gemini-3.5-flash)
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint for telemetry (if telemetry is installed)
- `OTEL_CONSOLE_EXPORT`: Set to "false" to disable console telemetry export
