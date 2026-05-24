"""Tests for telemetry module."""

from openmc_wrapper.telemetry import TelemetryManager


def test_telemetry_manager_initialization():
    """Test TelemetryManager initialization."""
    manager = TelemetryManager(enable_console=False, otlp_endpoint=None)
    assert manager.service_name == "openmc-wrapper"
    assert manager.enable_console is False
    assert manager.otlp_endpoint is None


def test_record_simulation_start():
    """Test recording simulation start."""
    manager = TelemetryManager(enable_console=False, otlp_endpoint=None)
    manager.record_simulation_start("test-sim-001")
    # No assertion needed - should not raise exception


def test_record_simulation_complete():
    """Test recording simulation completion."""
    manager = TelemetryManager(enable_console=False, otlp_endpoint=None)
    manager.record_simulation_complete(
        simulation_id="test-sim-001",
        duration_seconds=120.5,
        particle_count=1000000,
    )
    # No assertion needed - should not raise exception


def test_record_simulation_error():
    """Test recording simulation error."""
    manager = TelemetryManager(enable_console=False, otlp_endpoint=None)
    manager.record_simulation_error(
        simulation_id="test-sim-001",
        error_type="ValidationError",
    )
    # No assertion needed - should not raise exception


def test_trace_operation():
    """Test tracing an operation."""
    manager = TelemetryManager(enable_console=False, otlp_endpoint=None)
    with manager.trace_operation("test_operation", key="value"):
        pass
    # No assertion needed - should not raise exception


def test_trace_function():
    """Test tracing a function."""
    manager = TelemetryManager(enable_console=False, otlp_endpoint=None)

    @manager.trace_function
    def test_func():
        return 42

    result = test_func()
    assert result == 42


def test_get_telemetry_manager_singleton():
    """Test that get_telemetry_manager returns singleton instance."""
    from openmc_wrapper.telemetry import get_telemetry_manager

    manager1 = get_telemetry_manager()
    manager2 = get_telemetry_manager()
    assert manager1 is manager2
