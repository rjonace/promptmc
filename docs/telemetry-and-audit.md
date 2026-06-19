# Telemetry and Audit Roadmap

PromptMC currently provides optional OpenTelemetry integration for simulation observability. Deterministic AI audit logging is planned on the roadmap, but is not implemented yet.

## Installation

Telemetry is optional. Install with the telemetry extra:

```bash
pip install 'promptmc[telemetry]'
```

Without the telemetry extra, all telemetry calls are no-ops and have no performance impact.

## Console Export (Default)

When telemetry is installed, it exports to console by default with no configuration required:

```bash
promptmc run ./model
# Telemetry output appears in console
```

## OTLP Export

Set the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable to export to an OTLP-compatible backend (e.g., Jaeger, Tempo, Grafana):

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
promptmc run ./model
```

## Disable Console Export

To disable console export while using OTLP:

```bash
export OTEL_CONSOLE_EXPORT="false"
promptmc run ./model
```

## Python API Usage

### Basic Telemetry

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

## Current MCP History Resource

The MCP server keeps a bounded in-memory history for the lifetime of the server process. It backs the `promptmc://history` resource and is useful for inspecting tool calls made during the current session.

This is not durable audit logging: it is not written to disk, does not capture model/provider identity, and is reset when the MCP server exits.

## Planned Audit Logging

Durable AI audit logging is planned for the roadmap's provenance work. The intended shape is:

- local `audit.jsonl` records for MCP tool calls
- OpenTelemetry spans around tool execution
- MCP client identity from `clientInfo`
- model/provider metadata supplied by environment or client configuration
- deterministic provenance for AI-authored actions

Until that ships, treat PromptMC telemetry as operational observability rather than compliance-grade audit logging.

## Environment Variables

- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint for telemetry export
- `OTEL_CONSOLE_EXPORT`: Set to "false" to disable console export

## Performance Impact

Telemetry has minimal performance impact when disabled (no-op implementation). When enabled, console export adds ~1-2ms per operation, and OTLP export adds network latency depending on backend configuration.

## Security Considerations

- Telemetry spans and metrics may contain simulation identifiers or operational metadata
- OTLP endpoints should use TLS for secure transmission
- Do not treat the current in-memory MCP history resource as a durable compliance record
