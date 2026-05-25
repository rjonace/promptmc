import re

with open("src/promptmc/telemetry.py", "r") as f:
    content = f.read()

# 1. Add _NoopTelemetryManager
noop_class = """
class _NoopTelemetryManager:
    \"\"\"A telemetry manager that does nothing when OpenTelemetry is unavailable.\"\"\"

    def record_simulation_start(self, simulation_id: str) -> None:
        pass

    def record_simulation_complete(
        self,
        simulation_id: str,
        duration_seconds: float,
        particle_count: int = 0,
    ) -> None:
        pass

    def record_simulation_error(
        self, simulation_id: str, error_type: str
    ) -> None:
        pass

    @contextmanager
    def trace_operation(
        self, operation_name: str, **attributes: Any
    ) -> Iterator[Any]:
        yield None

    def trace_function(self, func: Callable[..., T]) -> Callable[..., T]:
        return func

    def shutdown(self) -> None:
        pass

    def _safe_shutdown(self) -> None:
        pass
"""
# Insert before TelemetryManager
content = content.replace("class TelemetryManager:", noop_class + "\n\nclass TelemetryManager:")

# 2. Modify get_telemetry_manager
new_get_manager = """def get_telemetry_manager() -> TelemetryManager | _NoopTelemetryManager:
    \"\"\"Get or create the global telemetry manager instance.

    Reads configuration from environment variables:
    - ``OTEL_EXPORTER_OTLP_ENDPOINT``: OTLP collector endpoint
    - ``OTEL_CONSOLE_EXPORT``: ``true``/``false`` (default ``true``)

    Returns:
        The global TelemetryManager instance.
    \"\"\"
    global _telemetry_manager

    if _telemetry_manager is not None:
        return _telemetry_manager

    if not _OTEL_AVAILABLE:
        _telemetry_manager = _NoopTelemetryManager()
        return _telemetry_manager

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    enable_console = os.getenv("OTEL_CONSOLE_EXPORT", "true").lower() == "true\""

    _telemetry_manager = TelemetryManager(
        service_name="promptmc",
        enable_console=enable_console,
        otlp_endpoint=otlp_endpoint,
    )
    return _telemetry_manager"""

# We'll replace the old get_telemetry_manager using regex
content = re.sub(r'def get_telemetry_manager\(\) -> TelemetryManager:.*?(?=def reset_telemetry_manager)', new_get_manager + '\n\n\n', content, flags=re.DOTALL)

# Also fix the type of _telemetry_manager at module level
content = content.replace("_telemetry_manager: TelemetryManager | None = None", "_telemetry_manager: TelemetryManager | _NoopTelemetryManager | None = None")

# 3. Remove guards from TelemetryManager
# We'll use regex to remove `if not _OTEL_AVAILABLE: return` 
content = re.sub(r'\s+if not _OTEL_AVAILABLE:\n\s+return\n', '\n', content)
content = re.sub(r'\s+if not _OTEL_AVAILABLE:\n\s+yield None  # type: ignore\[misc\]\n\s+return\n', '\n', content)
content = re.sub(r'\s+if not _OTEL_AVAILABLE:\n\s+return func\n', '\n', content)
# For TelemetryManager.__init__
content = re.sub(r'\s+if not _OTEL_AVAILABLE:\n\s+return\n', '\n', content, count=1) # replace first occurrence

with open("src/promptmc/telemetry.py", "w") as f:
    f.write(content)

