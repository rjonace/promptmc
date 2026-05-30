# CLI Reference

Complete reference for all PromptMC CLI commands.

## Natural-Language Planning

### `promptmc ask`

Turn plain-English requests into OpenMC plans and settings files.

```bash
# Ask for a plan without writing files
promptmc ask "make a concrete shielding calculation with 1 million particles"

# Generate settings.xml directly from natural language
promptmc ask "set up a reactor pin cell criticality run with 50k particles" --write

# Use an OpenAI-compatible LLM for richer interpretation
export OPENAI_API_KEY="..."
promptmc ask "I need a high-statistics shielding model for a 14 MeV source" --llm --write

# Specify output file
promptmc ask "criticality run" --write --output my_settings.xml

# Use a specific LLM model
promptmc ask "shielding calculation" --llm --model gpt-4 --write

# Use a custom LLM endpoint
promptmc ask "shielding calculation" --llm --endpoint https://api.example.com/v1/chat/completions --write
```

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
│ Match score    │ 85%  (3 keywords matched)                     │
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

**Note:** The **Match score** is a deterministic count of domain keywords matched, converted to a fixed scale (`min(0.95, 0.55 + 0.1 × matches)`). It is **not** a probabilistic confidence interval — it reflects keyword coverage, not certainty about intent.

## System Information

### `promptmc info`

Check OpenMC installation status.

```bash
promptmc info
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

Generate settings.xml from a template.

```bash
# Criticality template
promptmc template criticality --output settings.xml --particles 10000

# Fixed source template
promptmc template fixed_source --output settings.xml --particles 50000

# Shielding template
promptmc template shielding --output settings.xml --particles 1000000

# Reactor pin template
promptmc template reactor_pin --output settings.xml --particles 50000

# Specify batches and inactive
promptmc template criticality --output settings.xml --particles 10000 --batches 100 --inactive 10
```

### `promptmc configure`

Generate a basic configuration file.

```bash
promptmc configure --output config.xml --particles 10000 --batches 10
```

## Validation

### `promptmc validate`

Validate XML structure and optionally run schema validation.

```bash
# Validate XML structure only
promptmc validate input.xml

# Validate XML structure + schema (Pydantic)
promptmc validate input.xml --schema

# Validate multiple files
promptmc validate geometry.xml materials.xml settings.xml --schema
```

### `promptmc schema-check`

Run schema-only check on files or directories.

```bash
# Check a single file
promptmc schema-check settings.xml

# Check all XML files in a directory
promptmc schema-check ./input_dir/

# Check recursively
promptmc schema-check ./input_dir/ --recursive
```

## Simulation Execution

### `promptmc run`

Run an OpenMC simulation.

```bash
# Auto-detect API or subprocess mode
promptmc run input.xml --threads 4

# Force API mode
promptmc run input.xml --mode api

# Force subprocess mode
promptmc run input.xml --mode subprocess

# Specify output directory
promptmc run input.xml --output results

# Run with verbose output
promptmc --verbose run input.xml

# Run with custom particle count (overrides settings.xml)
promptmc run input.xml --particles 100000
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

# Export results to JSON
promptmc analyze ./output --json results.json

# Export results to text
promptmc analyze ./output --text results.txt
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

# Enable debug output
promptmc --debug <command>

# Show help
promptmc --help
promptmc <command> --help
```

## Environment Variables

- `OPENMC_CROSS_SECTIONS`: Path to cross_sections.xml file
- `OPENAI_API_KEY` or `PROMPTMC_LLM_API_KEY`: API key for LLM planning
- `PROMPTMC_LLM_MODEL`: LLM model name (default: gpt-4o-mini)
- `PROMPTMC_LLM_ENDPOINT`: OpenAI-compatible endpoint URL
- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint for telemetry (if telemetry is installed)
- `OTEL_CONSOLE_EXPORT`: Set to "false" to disable console telemetry export
