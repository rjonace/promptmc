# Telemetry and Audit Logging

PromptMC provides optional OpenTelemetry integration for observability and deterministic audit logging of AI actions.

## Installation

Telemetry is optional. Install with the telemetry extra:

```bash
pip install promptmc[telemetry]
```

Without the telemetry extra, all telemetry calls are no-ops and have no performance impact.

## Console Export (Default)

When telemetry is installed, it exports to console by default with no configuration required:

```bash
promptmc run input.xml
# Telemetry output appears in console
```

## OTLP Export

Set the `OTEL_EXPORTER_OTLP_ENDPOINT` environment variable to export to an OTLP-compatible backend (e.g., Jaeger, Tempo, Grafana):

```bash
export OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4317"
promptmc run input.xml
```

## Disable Console Export

To disable console export while using OTLP:

```bash
export OTEL_CONSOLE_EXPORT="false"
promptmc run input.xml
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

## AI Audit Logging (v2.2+)

PromptMC maintains a deterministic audit trail of all AI actions through the MCP server. Every tool call is wrapped in an OpenTelemetry span and logged to a local `audit.jsonl` file.

### MCP Client Tracking

The MCP protocol automatically reveals the LLM client (e.g., Claude Desktop, Cursor, Windsurf) via the `initialize` request's `clientInfo` payload. This is captured and attached to all telemetry as the `llm_product` dimension.

### Model and Provider Tracking

The MCP protocol does not natively pass the specific AI model (e.g., `gpt-4o`, `claude-3.5-sonnet`) because the client app handles API keys and model routing. To track this for enterprise auditability, configure the following environment variables in your MCP client configuration:

- `PROMPTMC_TRACKING_MODEL`: The specific model (e.g., "claude-3-5-sonnet")
- `PROMPTMC_COMPANY_ID`: The AI provider (e.g., "Anthropic", "OpenAI")

Example `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "promptmc": {
      "command": "promptmc-mcp",
      "env": {
        "OPENMC_CROSS_SECTIONS": "/path/to/cross_sections.xml",
        "PROMPTMC_TRACKING_MODEL": "claude-3-5-sonnet",
        "PROMPTMC_COMPANY_ID": "Anthropic"
      }
    }
  }
}
```

### Metric Dimensions

Every OpenTelemetry span includes three dimensions for complete AI provenance:

- `llm_product`: The MCP client (from `clientInfo.name`)
- `llm_model`: The specific model (from `PROMPTMC_TRACKING_MODEL`)
- `llm_company`: The AI provider (from `PROMPTMC_COMPANY_ID`)

This enables enterprise-grade audit trails: "Claude Desktop (using claude-3-5-sonnet) attempted to build 40 geometries this week, hallucinated 3 overlapping schemas, and successfully ran 37 simulations."

### Audit Log Location

The audit log is written to `audit.jsonl` in the current working directory when the MCP server is running.

### Audit Log Format

Each line in `audit.jsonl` is a JSON record containing:

```json
{
  "timestamp": "2026-05-30T12:34:56.789Z",
  "tool_name": "openmc_validate",
  "input_arguments": {
    "input_path": "/path/to/input.xml",
    "check_schema": true
  },
  "execution_result": {
    "success": true,
    "duration_ms": 123
  },
  "llm_product": "Claude Desktop",
  "llm_model": "claude-3-5-sonnet",
  "llm_company": "Anthropic",
  "span_id": "abc123",
  "trace_id": "def456"
}
```

### Monitoring Audit Logs

Watch the audit log in real-time:

```bash
tail -f audit.jsonl
```

### Audit Log for MCP Tools

When using the MCP server with an AI assistant, every tool call is automatically logged:

- `openmc_validate` — validation attempts and results
- `openmc_run` — simulation execution parameters
- `openmc_analyze` — result parsing operations
- `openmc_plot` — geometry plotting requests
- `openmc_template` — template generation requests

This provides complete provenance of what the AI agent attempted to do, enabling:

- **Post-mortem analysis** of anomalous simulation results
- **Compliance verification** for regulated workflows
- **Debugging** of AI behavior without relying on chat history

### Enterprise Use

For enterprise deployments, the audit log can be:

- Integrated with centralized logging systems (ELK, Splunk)
- Exported to OTLP backends for distributed tracing
- Used for compliance reporting and audit trails

## Environment Variables

- `OTEL_EXPORTER_OTLP_ENDPOINT`: OTLP endpoint for telemetry export
- `OTEL_CONSOLE_EXPORT`: Set to "false" to disable console export
- `OTEL_SERVICE_NAME`: Service name for telemetry (default: "promptmc")
- `OTEL_RESOURCE_ATTRIBUTES`: Additional resource attributes
- `PROMPTMC_TRACKING_MODEL`: Specific AI model for audit logging (e.g., "claude-3-5-sonnet")
- `PROMPTMC_COMPANY_ID`: AI provider for audit logging (e.g., "Anthropic", "OpenAI")

## Performance Impact

Telemetry has minimal performance impact when disabled (no-op implementation). When enabled, console export adds ~1-2ms per operation, and OTLP export adds network latency depending on backend configuration.

## Security Considerations

- Audit logs may contain sensitive simulation parameters
- Ensure proper access controls on `audit.jsonl` in production environments
- Consider encryption for audit logs in regulated environments
- OTLP endpoints should use TLS for secure transmission
