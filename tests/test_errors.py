"""Tests for advanced error handling module."""

from __future__ import annotations

import pytest
from openmc_wrapper.errors import (
    ConfigurationError,
    ErrorCategory,
    ErrorContext,
    ErrorReporter,
    ErrorSeverity,
    ExecutionError,
    OpenMCWrapperError,
    RetryPolicy,
    ValidationError,
    retry,
)


def test_error_context_creation():
    """Test ErrorContext creation."""
    ctx = ErrorContext(
        operation="test-op",
        category=ErrorCategory.EXECUTION,
        severity=ErrorSeverity.WARNING,
        correlation_id="abc-123",
        metadata={"key": "value"},
    )
    assert ctx.operation == "test-op"
    assert ctx.category == ErrorCategory.EXECUTION
    assert ctx.correlation_id == "abc-123"


def test_error_context_to_dict():
    """Test ErrorContext serialization."""
    ctx = ErrorContext(operation="op")
    data = ctx.to_dict()
    assert data["operation"] == "op"
    assert data["category"] == "unknown"
    assert data["severity"] == "error"


def test_openmc_wrapper_error():
    """Test OpenMCWrapperError creation."""
    err = OpenMCWrapperError("Test error")
    assert err.message == "Test error"
    assert err.context.operation == "unknown"


def test_openmc_wrapper_error_with_cause():
    """Test error with underlying cause."""
    cause = ValueError("Original error")
    err = OpenMCWrapperError("Wrapper error", cause=cause)
    assert err.cause is cause


def test_error_to_dict():
    """Test error serialization."""
    err = ConfigurationError(
        "Config issue",
        context=ErrorContext(operation="config-load"),
    )
    data = err.to_dict()
    assert data["type"] == "ConfigurationError"
    assert data["message"] == "Config issue"
    assert data["context"]["operation"] == "config-load"


def test_validation_error():
    """Test ValidationError."""
    err = ValidationError("Bad input")
    assert isinstance(err, OpenMCWrapperError)


def test_execution_error():
    """Test ExecutionError."""
    err = ExecutionError("Run failed")
    assert isinstance(err, OpenMCWrapperError)


def test_retry_policy_compute_delay():
    """Test retry delay computation."""
    policy = RetryPolicy(
        initial_delay_seconds=1.0,
        max_delay_seconds=10.0,
        backoff_multiplier=2.0,
    )
    assert policy.compute_delay(1) == 1.0
    assert policy.compute_delay(2) == 2.0
    assert policy.compute_delay(3) == 4.0
    # Capped at max
    assert policy.compute_delay(10) == 10.0


def test_retry_decorator_success():
    """Test retry decorator with success."""
    call_count = [0]

    @retry(RetryPolicy(max_attempts=3, initial_delay_seconds=0.01))
    def func():
        call_count[0] += 1
        return "success"

    result = func()
    assert result == "success"
    assert call_count[0] == 1


def test_retry_decorator_eventual_success():
    """Test retry decorator with eventual success."""
    call_count = [0]

    @retry(RetryPolicy(max_attempts=3, initial_delay_seconds=0.01))
    def func():
        call_count[0] += 1
        if call_count[0] < 2:
            raise OSError("transient")
        return "success"

    result = func()
    assert result == "success"
    assert call_count[0] == 2


def test_retry_decorator_max_attempts_reached():
    """Test retry decorator gives up after max attempts."""
    call_count = [0]

    @retry(RetryPolicy(max_attempts=3, initial_delay_seconds=0.01))
    def func():
        call_count[0] += 1
        raise OSError("persistent")

    with pytest.raises(OSError):
        func()

    assert call_count[0] == 3


def test_retry_decorator_non_retryable():
    """Test retry decorator does not retry non-listed exceptions."""
    call_count = [0]

    @retry(RetryPolicy(max_attempts=3, initial_delay_seconds=0.01))
    def func():
        call_count[0] += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError):
        func()

    assert call_count[0] == 1  # Only called once


def test_retry_callback():
    """Test retry callback is invoked."""
    callbacks: list = []

    def on_retry(attempt: int, exc: Exception, delay: float) -> None:
        callbacks.append((attempt, str(exc), delay))

    @retry(
        RetryPolicy(max_attempts=3, initial_delay_seconds=0.01),
        on_retry=on_retry,
    )
    def func():
        raise OSError("test")

    with pytest.raises(OSError):
        func()

    assert len(callbacks) == 2  # Called for attempt 1 and 2 (not 3)


def test_error_reporter_record():
    """Test ErrorReporter records errors."""
    reporter = ErrorReporter()
    err = ConfigurationError("Test")
    reporter.record(err)

    assert reporter.has_errors()
    assert len(reporter.errors) == 1


def test_error_reporter_critical():
    """Test ErrorReporter detects critical errors."""
    reporter = ErrorReporter()

    normal = ConfigurationError(
        "normal",
        context=ErrorContext(operation="x", severity=ErrorSeverity.WARNING),
    )
    critical = ExecutionError(
        "critical",
        context=ErrorContext(operation="y", severity=ErrorSeverity.CRITICAL),
    )

    reporter.record(normal)
    reporter.record(critical)

    assert reporter.has_critical()


def test_error_reporter_clear():
    """Test ErrorReporter can be cleared."""
    reporter = ErrorReporter()
    reporter.record(ConfigurationError("test"))
    assert reporter.has_errors()

    reporter.clear()
    assert not reporter.has_errors()


def test_error_reporter_format_report():
    """Test formatting error report."""
    reporter = ErrorReporter()
    reporter.record(ConfigurationError("Test error"))

    report = reporter.format_report()
    assert "Error Report" in report
    assert "Test error" in report


def test_error_reporter_empty_report():
    """Test report when no errors."""
    reporter = ErrorReporter()
    report = reporter.format_report()
    assert "No errors" in report


def test_error_reporter_to_dict():
    """Test serializing error reporter to dict."""
    reporter = ErrorReporter()
    reporter.record(ConfigurationError("test"))
    data = reporter.to_dict()
    assert data["total"] == 1
    assert len(data["errors"]) == 1
