# Python API Reference

The PromptMC Python API provides programmatic access to OpenMC workflows for power users who want to bypass the CLI and write custom automation scripts.

## Installation

```bash
pip install promptmc
```

## Core Classes

### OpenMCInstaller

Check and manage OpenMC installation.

```python
from promptmc import OpenMCInstaller

# Check OpenMC installation
installer = OpenMCInstaller()
info = installer.check_installation()
print(f"OpenMC version: {info.version}")
print(f"Python API available: {info.python_available}")
print(f"OpenMC executable: {info.executable_path}")
```

### OpenMCValidator

Validate OpenMC input files and schemas.

```python
from promptmc import OpenMCValidator
from promptmc.schema import SchemaValidator

# Validate input files
validator = OpenMCValidator()

# Validate XML structure
validator.validate_input_file("input.xml")

# Validate a directory for required OpenMC XML files
validator.validate_input_file("./input_dir/")

# Run schema checks separately
schema_validator = SchemaValidator()
schema_validator.validate_directory("./input_dir/")
```

### OpenMCRunner

Run OpenMC simulations with flexible execution modes.

```python
from promptmc import OpenMCRunner, ExecutionMode

# Create runner with auto-detection
runner = OpenMCRunner(execution_mode=ExecutionMode.AUTO)

# Generate configuration
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

print(f"Simulation completed: {result.returncode == 0}")
print(result.stdout or result.stderr)
```

### ResultParser

Parse and analyze simulation outputs.

```python
from promptmc.visualization import ResultParser, ResultVisualizer

# Parse output
parser = ResultParser()
results = parser.parse_results("results")

print(f"k-effective: {results.k_effective}")
print(f"Statepoint: {results.statepoint_path}")
print(f"Summary: {results.summary_path}")

# Export to JSON
visualizer = ResultVisualizer()
visualizer.export_json(results, "results.json")
```

## Telemetry

### Basic Usage

```python
from promptmc.telemetry import get_telemetry_manager

# Get telemetry manager (no-op unless promptmc[telemetry] is installed)
telemetry = get_telemetry_manager()

# Record simulation events
telemetry.record_simulation_start("sim-001")

# Run simulation
# ... your simulation code ...

telemetry.record_simulation_complete(
    simulation_id="sim-001",
    duration_seconds=120.5,
)
```

### Context Manager

```python
from promptmc.telemetry import get_telemetry_manager

telemetry = get_telemetry_manager()

with telemetry.trace_operation("simulation_run", simulation_id="sim-001"):
    # Your simulation code here
    pass
```

## Batch Execution

### BatchRunner

Run parameter sweeps from YAML/JSON specifications.

```python
from promptmc import BatchRunner, ParallelConfig, ParallelMode
from promptmc.batch import load_batch_spec

# Create batch runner
runner = BatchRunner(
    parallel_config=ParallelConfig(mode=ParallelMode.THREADS, max_workers=4)
)

# Load batch specification
spec = load_batch_spec("batch_spec.yaml")

# Run batch
summary = runner.run_batch(spec)

# Process results
for result in summary.job_results:
    print(f"Simulation {result.job_id}: {result.success}")
```

### ParallelExecutor

Fine-grained control over parallel execution.

```python
from pathlib import Path

from promptmc.batch import (
    ParallelConfig,
    ParallelExecutor,
    ParallelMode,
    SimulationJob,
)

# Create executor
executor = ParallelExecutor(
    config=ParallelConfig(mode=ParallelMode.THREADS, max_workers=4)
)

# Run multiple simulations
tasks = [
    SimulationJob(
        job_id="sim1",
        input_path=Path("sim1"),
        output_path=Path("results1"),
    ),
    SimulationJob(
        job_id="sim2",
        input_path=Path("sim2"),
        output_path=Path("results2"),
    ),
]

results = executor.execute_jobs(tasks)
```

## Configuration Templates

### Built-in templates

Generate configurations from built-in templates.

```python
from promptmc.templates import TemplateType, get_template

# Create template
template = get_template(TemplateType.CRITICALITY)

# Generate and save configuration
config_path = template.render(
    output_path="settings.xml",
    particles=10000,
    batches=100,
    inactive=10,
)
```

## Error Handling

### PromptMCError

Base exception for all PromptMC errors.

```python
from promptmc.errors import PromptMCError

try:
    runner.run_simulation("input.xml")
except PromptMCError as e:
    print(f"PromptMC error: {e}")
```

### Specific Error Types

```python
from promptmc.errors import (
    OpenMCNotFoundError,
    ValidationError,
    OpenMCExecutionError,
    ConfigurationError,
)

try:
    runner.run_simulation("input.xml")
except OpenMCNotFoundError:
    print("OpenMC not found in PATH")
except ValidationError as e:
    print(f"Validation failed: {e}")
except OpenMCExecutionError as e:
    print(f"Simulation failed: {e}")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Type Hints

All public APIs include type hints for IDE support and mypy validation.

```python
from promptmc import OpenMCRunner, ExecutionMode

def run_simulation(
    input_path: str,
    threads: int = 4,
    output_path: str | None = None,
) -> bool:
    runner = OpenMCRunner(execution_mode=ExecutionMode.AUTO)
    result = runner.run_simulation(
        input_path=input_path,
        threads=threads,
        output_path=output_path,
    )
    return result.returncode == 0
```

## Complete Example

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

# Run simulation with telemetry
telemetry = get_telemetry_manager()
telemetry.record_simulation_start("sim-001")

with telemetry.trace_operation("simulation_run", simulation_id="sim-001"):
    result = runner.run_simulation(
        input_path="input.xml",
        threads=4,
        output_path="results",
    )

telemetry.record_simulation_complete(
    simulation_id="sim-001",
    duration_seconds=120.5,
)

# Parse output
parser = ResultParser()
results = parser.parse_results("results")
print(f"k-effective: {results.k_effective}")
print(f"Statepoint: {results.statepoint_path}")
```
