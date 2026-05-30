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

# Validate input files
validator = OpenMCValidator()

# Validate XML structure
validator.validate_input_file("input.xml")

# Validate with schema checking
validator.validate_input_file("input.xml", check_schema=True)

# Validate a directory
validator.validate_directory("./input_dir/")
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

print(f"Simulation completed: {result.success}")
print(f"Output path: {result.output_path}")
```

### ResultParser

Parse and analyze simulation outputs.

```python
from promptmc.visualization import ResultParser

# Parse output
parser = ResultParser()
results = parser.parse_results("results")

print(f"k-effective: {results.k_effective}")
print(f"Statepoint: {results.statepoint_path}")
print(f"Summary: {results.summary_path}")

# Export to JSON
results.export_json("results.json")

# Export to text
results.export_text("results.txt")
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
from promptmc import BatchRunner

# Create batch runner
runner = BatchRunner()

# Load batch specification
spec = runner.load_spec("batch_spec.yaml")

# Run batch with thread-based parallelism
results = runner.run_batch(
    spec=spec,
    parallel_mode="threads",
    workers=4,
)

# Process results
for result in results:
    print(f"Simulation {result.simulation_id}: {result.status}")
```

### ParallelExecutor

Fine-grained control over parallel execution.

```python
from promptmc import ParallelExecutor, ParallelMode

# Create executor
executor = ParallelExecutor(parallel_mode=ParallelMode.THREADS)

# Run multiple simulations
tasks = [
    {"input_path": "sim1.xml", "output_path": "results1"},
    {"input_path": "sim2.xml", "output_path": "results2"},
]

results = executor.execute_tasks(tasks, workers=4)
```

## Configuration Templates

### ConfigurationTemplate

Generate configurations from built-in templates.

```python
from promptmc import ConfigurationTemplate, TemplateType

# Create template
template = ConfigurationTemplate(template_type=TemplateType.CRITICALITY)

# Generate configuration
config = template.render(
    particles=10000,
    batches=100,
    inactive=10,
)

# Save to file
config.save("settings.xml")
```

## Error Handling

### PromptMCError

Base exception for all PromptMC errors.

```python
from promptmc import PromptMCError

try:
    runner.run_simulation("input.xml")
except PromptMCError as e:
    print(f"PromptMC error: {e}")
```

### Specific Error Types

```python
from promptmc import (
    OpenMCNotFoundError,
    ValidationError,
    SimulationError,
    ConfigurationError,
)

try:
    runner.run_simulation("input.xml")
except OpenMCNotFoundError:
    print("OpenMC not found in PATH")
except ValidationError as e:
    print(f"Validation failed: {e}")
except SimulationError as e:
    print(f"Simulation failed: {e}")
except ConfigurationError as e:
    print(f"Configuration error: {e}")
```

## Type Hints

All public APIs include type hints for IDE support and mypy validation.

```python
from promptmc import OpenMCRunner, ExecutionMode
from typing import Optional

def run_simulation(
    input_path: str,
    threads: int = 4,
    output_path: Optional[str] = None,
) -> bool:
    runner = OpenMCRunner(execution_mode=ExecutionMode.AUTO)
    result = runner.run_simulation(
        input_path=input_path,
        threads=threads,
        output_path=output_path,
    )
    return result.success
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
