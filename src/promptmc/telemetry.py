"""OpenTelemetry telemetry and observability module."""

from __future__ import annotations

import atexit
import functools
import os
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager, suppress
from typing import Any, TypeVar

try:
    from opentelemetry import metrics, trace
    from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
        OTLPMetricExporter,
    )
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
        OTLPSpanExporter,
    )
    from opentelemetry.sdk.metrics import MeterProvider
    from opentelemetry.sdk.metrics.export import (
        ConsoleMetricExporter,
        MetricExporter,
        MetricExportResult,
        MetricsData,
        PeriodicExportingMetricReader,
    )
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import (
        BatchSpanProcessor,
        ConsoleSpanExporter,
        SimpleSpanProcessor,
    )
    from opentelemetry.trace import Span

    _OTEL_AVAILABLE = True
except ImportError:
    _OTEL_AVAILABLE = False
    metrics = None  # type: ignore[assignment]
    trace = None  # type: ignore[assignment]
    MeterProvider = None  # type: ignore[assignment,misc]
    TracerProvider = None  # type: ignore[assignment,misc]
    Resource = None  # type: ignore[assignment,misc]
    SERVICE_NAME = "service.name"
    Span = None  # type: ignore[assignment,misc]
    ConsoleMetricExporter = object  # type: ignore[assignment,misc]
    MetricExporter = object  # type: ignore[assignment,misc]
    MetricExportResult = None  # type: ignore[assignment,misc]
    MetricsData = None  # type: ignore[assignment,misc]

T = TypeVar("T")

# Module-level singleton (None until first access)
_telemetry_manager: TelemetryManager | _NoopTelemetryManager | None = None


class _SafeConsoleMetricExporter(ConsoleMetricExporter):
    """Console metric exporter that swallows I/O errors during shutdown.

    The default exporter raises ``ValueError: I/O operation on closed file``
    when its background flush thread runs after stdout has been closed
    (common during interpreter shutdown / pytest teardown).
    """

    def export(
        self,
        metrics_data: MetricsData,
        timeout_millis: float = 10_000,
        **kwargs: Any,
    ) -> MetricExportResult:
        try:
            return super().export(metrics_data, timeout_millis, **kwargs)
        except (ValueError, OSError):
            return MetricExportResult.SUCCESS


class _NoopTelemetryManager:
    """A telemetry manager that does nothing when OpenTelemetry is unavailable."""

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
        self, _operation_name: str, **_attributes: Any
    ) -> Iterator[Any]:
        yield None

    def trace_function(self, func: Callable[..., T]) -> Callable[..., T]:
        return func

    def shutdown(self) -> None:
        pass

    def _safe_shutdown(self) -> None:
        pass


class TelemetryManager:
    """Manages OpenTelemetry tracing and metrics for OpenMC simulations.

    The manager configures both tracing and metrics with sensible defaults:
    - Console export by default (zero configuration)
    - OTLP export if `OTEL_EXPORTER_OTLP_ENDPOINT` is provided
    - Disable console with `OTEL_CONSOLE_EXPORT=false`

    Lifecycle:
    - The manager registers an atexit handler that flushes telemetry on shutdown.
    - Call `shutdown()` explicitly for deterministic cleanup.
    """

    def __init__(
        self,
        service_name: str = "promptmc",
        enable_console: bool = True,
        otlp_endpoint: str | None = None,
    ) -> None:
        """Initialize the telemetry manager.

        Args:
            service_name: Name of the service for telemetry identification.
            enable_console: Enable console export for traces and metrics.
            otlp_endpoint: OTLP endpoint for telemetry (e.g. ``http://localhost:4317``).
        """
        self.service_name = service_name
        self.enable_console = enable_console
        self.otlp_endpoint = otlp_endpoint
        self._shutdown_called = False

        self.resource = Resource.create({SERVICE_NAME: service_name})

        self._tracer_provider = self._build_tracer_provider()
        self._meter_provider = self._build_meter_provider()

        # Set as global providers (idempotent for same instance)
        trace.set_tracer_provider(self._tracer_provider)
        metrics.set_meter_provider(self._meter_provider)

        self.tracer = trace.get_tracer(__name__)
        self.meter = metrics.get_meter(__name__)
        self._create_metrics()

        # Register shutdown handler for clean exit (avoids closed-stream errors)
        atexit.register(self._safe_shutdown)

    def _build_tracer_provider(self) -> TracerProvider:
        """Build the configured tracer provider."""
        provider = TracerProvider(resource=self.resource)

        if self.enable_console:
            provider.add_span_processor(
                SimpleSpanProcessor(ConsoleSpanExporter())
            )

        if self.otlp_endpoint:
            provider.add_span_processor(
                BatchSpanProcessor(
                    OTLPSpanExporter(endpoint=self.otlp_endpoint, insecure=True)
                )
            )

        return provider

    def _build_meter_provider(self) -> MeterProvider:
        """Build the configured meter provider."""
        exporter: MetricExporter
        if self.otlp_endpoint:
            exporter = OTLPMetricExporter(
                endpoint=self.otlp_endpoint, insecure=True
            )
        else:
            exporter = _SafeConsoleMetricExporter()

        # Long export interval; explicit shutdown() flushes pending data
        reader = PeriodicExportingMetricReader(
            exporter, export_interval_millis=60_000
        )
        return MeterProvider(resource=self.resource, metric_readers=[reader])

    def _create_metrics(self) -> None:
        """Create metric instruments for tracking simulations."""
        self.simulation_counter = self.meter.create_counter(
            "openmc_simulations_total",
            description="Total number of OpenMC simulations executed",
        )
        self.particle_counter = self.meter.create_counter(
            "openmc_particles_total",
            description="Total number of particles simulated",
        )
        self.simulation_duration = self.meter.create_histogram(
            "openmc_simulation_duration_seconds",
            description="Duration of OpenMC simulations in seconds",
        )
        self.memory_usage = self.meter.create_histogram(
            "openmc_memory_usage_bytes",
            description="Memory usage during OpenMC simulations",
        )

    def record_simulation_start(self, simulation_id: str) -> None:
        """Record the start of a simulation."""
        self.simulation_counter.add(
            1, {"simulation_id": simulation_id, "status": "started"}
        )

    def record_simulation_complete(
        self,
        simulation_id: str,
        duration_seconds: float,
        particle_count: int = 0,
    ) -> None:
        """Record the completion of a simulation."""
        self.simulation_counter.add(
            1, {"simulation_id": simulation_id, "status": "completed"}
        )
        self.simulation_duration.record(
            duration_seconds, {"simulation_id": simulation_id}
        )
        if particle_count > 0:
            self.particle_counter.add(
                particle_count, {"simulation_id": simulation_id}
            )

    def record_simulation_error(
        self, simulation_id: str, error_type: str
    ) -> None:
        """Record a simulation error."""
        self.simulation_counter.add(
            1,
            {
                "simulation_id": simulation_id,
                "status": "error",
                "error_type": error_type,
            },
        )

    @contextmanager
    def trace_operation(
        self, operation_name: str, **attributes: Any
    ) -> Iterator[Span]:
        """Context manager for tracing an operation.

        Args:
            operation_name: Name of the operation to trace.
            **attributes: Additional attributes to add to the span.

        Yields:
            The active span for the operation.
        """
        with self.tracer.start_as_current_span(operation_name) as span:
            for key, value in attributes.items():
                span.set_attribute(key, value)
            yield span

    def trace_function(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to automatically trace a function."""

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            with self.tracer.start_as_current_span(func.__name__) as span:
                span.set_attribute("function.name", func.__name__)
                span.set_attribute("function.module", func.__module__)
                return func(*args, **kwargs)

        return wrapper

    def shutdown(self) -> None:
        """Shutdown telemetry providers and flush pending data."""
        if self._shutdown_called or not _OTEL_AVAILABLE:
            return
        self._shutdown_called = True
        with suppress(Exception):
            self._tracer_provider.shutdown()
        with suppress(Exception):
            self._meter_provider.shutdown()

    def _safe_shutdown(self) -> None:
        """Atexit-safe shutdown that swallows interpreter-shutdown errors."""
        # During interpreter shutdown stdout/stderr may be closed; suppress
        # the resulting "I/O operation on closed file" exporter errors.
        with suppress(Exception):
            self.shutdown()
        # Also redirect stdout to devnull during shutdown to suppress any
        # pending exporter writes from background threads.
        with suppress(Exception):
            sys.stdout.flush()


def telemetry_available() -> bool:
    """Whether the optional OpenTelemetry ``telemetry`` extra is installed.

    Returns:
        ``True`` when the OpenTelemetry packages import successfully, i.e.
        PromptMC was installed with the ``telemetry`` extra.
    """
    return _OTEL_AVAILABLE


def get_telemetry_manager() -> TelemetryManager | _NoopTelemetryManager:
    """Get or create the global telemetry manager instance.

    Reads configuration from environment variables:
    - ``OTEL_EXPORTER_OTLP_ENDPOINT``: OTLP collector endpoint
    - ``OTEL_CONSOLE_EXPORT``: ``true``/``false`` (default ``true``)

    Returns:
        The global TelemetryManager instance.
    """
    global _telemetry_manager

    if _telemetry_manager is not None:
        return _telemetry_manager

    if not _OTEL_AVAILABLE:
        _telemetry_manager = _NoopTelemetryManager()
        return _telemetry_manager

    otlp_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")
    enable_console = os.getenv("OTEL_CONSOLE_EXPORT", "true").lower() == "true"
    _telemetry_manager = TelemetryManager(
        service_name="promptmc",
        enable_console=enable_console,
        otlp_endpoint=otlp_endpoint,
    )
    return _telemetry_manager


def reset_telemetry_manager() -> None:
    """Reset the global telemetry manager (primarily for testing)."""
    global _telemetry_manager
    if _telemetry_manager is not None:
        _telemetry_manager.shutdown()
    _telemetry_manager = None
