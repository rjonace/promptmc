"""Tests for advanced error handling module."""

from __future__ import annotations

import logging

from promptmc.errors import (
    ConfigurationError,
    ErrorCategory,
    ErrorContext,
    ErrorReporter,
    ErrorSeverity,
    ExecutionError,
    PromptMCError,
    ValidationError,
    configure_logging,
    default_retry,
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


def test_promptmc_error():
    """Test PromptMCError creation."""
    err = PromptMCError("Test error")
    assert err.message == "Test error"
    assert err.context.operation == "unknown"


def test_promptmc_error_with_cause():
    """Test error with underlying cause."""
    cause = ValueError("Original error")
    err = PromptMCError("Wrapper error", cause=cause)
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
    assert isinstance(err, PromptMCError)


def test_execution_error():
    """Test ExecutionError."""
    err = ExecutionError("Run failed")
    assert isinstance(err, PromptMCError)


def test_default_retry_returns_decorator():
    decorator = default_retry()
    assert callable(decorator)


def test_error_reporter_record_and_errors():
    reporter = ErrorReporter()
    err = PromptMCError(
        "test error",
        context=ErrorContext(
            operation="test_op",
            category=ErrorCategory.VALIDATION,
        ),
    )
    reporter.record(err)
    assert reporter.has_errors()
    assert len(reporter.errors) == 1
    assert reporter.errors[0].message == "test error"


def test_error_reporter_has_critical():
    reporter = ErrorReporter()
    non_critical = PromptMCError(
        "minor",
        context=ErrorContext(
            operation="op",
            severity=ErrorSeverity.WARNING,
        ),
    )
    reporter.record(non_critical)
    assert not reporter.has_critical()

    critical = PromptMCError(
        "severe",
        context=ErrorContext(
            operation="op",
            severity=ErrorSeverity.CRITICAL,
        ),
    )
    reporter.record(critical)
    assert reporter.has_critical()


def test_error_reporter_clear():
    reporter = ErrorReporter()
    reporter.record(
        PromptMCError(
            "err",
            context=ErrorContext(operation="op"),
        )
    )
    assert reporter.has_errors()
    reporter.clear()
    assert not reporter.has_errors()
    assert len(reporter.errors) == 0


def test_error_reporter_to_dict():
    reporter = ErrorReporter()
    reporter.record(
        PromptMCError(
            "err",
            context=ErrorContext(operation="op"),
        )
    )
    d = reporter.to_dict()
    assert d["total"] == 1
    assert len(d["errors"]) == 1
    assert d["errors"][0]["message"] == "err"


def test_error_reporter_format_report_empty():
    reporter = ErrorReporter()
    assert reporter.format_report() == "No errors recorded."


def test_error_reporter_format_report_with_errors():
    reporter = ErrorReporter()
    reporter.record(
        PromptMCError(
            "first error",
            context=ErrorContext(
                operation="op1",
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                correlation_id="abc-123",
                metadata={"key": "value"},
            ),
            cause=ValueError("underlying"),
        )
    )
    report = reporter.format_report()
    assert "first error" in report
    assert "op1" in report
    assert "abc-123" in report
    assert "underlying" in report
    assert "key" in report


def test_configure_logging_no_duplicate_handlers():
    logger = logging.getLogger("promptmc")
    # Clear to test fresh
    logger.handlers.clear()

    configure_logging()
    first_count = len(logger.handlers)
    configure_logging()
    second_count = len(logger.handlers)
    assert first_count == second_count

    # Cleanup
    logger.handlers.clear()
