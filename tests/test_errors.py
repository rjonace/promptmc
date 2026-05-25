"""Tests for advanced error handling module."""

from __future__ import annotations

from promptmc.errors import (
    ConfigurationError,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    ExecutionError,
    PromptMCError,
    ValidationError,
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
