"""Advanced error handling, retry logic, and structured exceptions."""

from __future__ import annotations

import functools
import logging
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class ErrorCategory(str, Enum):
    """Categories for structured errors."""

    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    EXECUTION = "execution"
    RESOURCE = "resource"
    INTEGRATION = "integration"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Severity levels for structured errors."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class ErrorContext:
    """Structured context for an error.

    Captures the failing operation, related identifiers, and any extra
    metadata so logs and reports stay actionable.
    """

    operation: str
    category: ErrorCategory = ErrorCategory.UNKNOWN
    severity: ErrorSeverity = ErrorSeverity.ERROR
    correlation_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    traceback_str: Optional[str] = None

    def to_dict(self) -> dict:
        """Serialize the context for logging or telemetry."""
        return {
            "operation": self.operation,
            "category": self.category.value,
            "severity": self.severity.value,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "traceback": self.traceback_str,
        }


class PromptMCError(Exception):
    """Base exception for all PromptMC errors with structured context."""

    def __init__(
        self,
        message: str,
        context: Optional[ErrorContext] = None,
        cause: Optional[Exception] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.context = context or ErrorContext(operation="unknown")
        self.cause = cause
        if cause is not None and self.context.traceback_str is None:
            self.context.traceback_str = "".join(
                traceback.format_exception(type(cause), cause, cause.__traceback__)
            )

    def to_dict(self) -> dict:
        """Serialize the error for logging or JSON export."""
        return {
            "type": type(self).__name__,
            "message": self.message,
            "context": self.context.to_dict(),
            "cause": str(self.cause) if self.cause else None,
        }


class ConfigurationError(PromptMCError):
    """Raised when configuration is invalid or missing."""


class ValidationError(PromptMCError):
    """Raised when validation fails."""


class ExecutionError(PromptMCError):
    """Raised when execution fails."""


class ResourceError(PromptMCError):
    """Raised when resource limits are exceeded or resources unavailable."""


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""

    max_attempts: int = 3
    initial_delay_seconds: float = 1.0
    max_delay_seconds: float = 60.0
    backoff_multiplier: float = 2.0
    retryable_exceptions: tuple = (OSError, TimeoutError, ExecutionError)

    def compute_delay(self, attempt: int) -> float:
        """Compute the delay for a given attempt (1-indexed)."""
        delay = self.initial_delay_seconds * (self.backoff_multiplier ** (attempt - 1))
        return min(delay, self.max_delay_seconds)


def retry(
    policy: Optional[RetryPolicy] = None,
    on_retry: Optional[Callable[[int, Exception, float], None]] = None,
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """Decorator that retries a function on configured exceptions.

    Args:
        policy: Retry policy. Uses defaults when not provided.
        on_retry: Callback invoked as ``on_retry(attempt, exception, delay)``
            after each failed attempt before the next one.

    Returns:
        The decorated function.
    """
    actual_policy = policy or RetryPolicy()

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exc: Optional[Exception] = None
            for attempt in range(1, actual_policy.max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except actual_policy.retryable_exceptions as e:
                    last_exc = e
                    if attempt >= actual_policy.max_attempts:
                        break
                    delay = actual_policy.compute_delay(attempt)
                    logger.warning(
                        "Attempt %d/%d failed for %s: %s. Retrying in %.1fs",
                        attempt,
                        actual_policy.max_attempts,
                        func.__name__,
                        e,
                        delay,
                    )
                    if on_retry is not None:
                        on_retry(attempt, e, delay)
                    time.sleep(delay)

            assert last_exc is not None
            raise last_exc

        return wrapper

    return decorator


class ErrorReporter:
    """Aggregates and reports errors that occur during a session."""

    def __init__(self) -> None:
        self._errors: list[PromptMCError] = []

    def record(self, error: PromptMCError) -> None:
        """Record an error for later reporting."""
        self._errors.append(error)
        logger.error(
            "[%s] %s: %s",
            error.context.category.value,
            error.context.operation,
            error.message,
        )

    @property
    def errors(self) -> list[PromptMCError]:
        return list(self._errors)

    def has_errors(self) -> bool:
        return bool(self._errors)

    def has_critical(self) -> bool:
        return any(e.context.severity == ErrorSeverity.CRITICAL for e in self._errors)

    def clear(self) -> None:
        """Clear recorded errors."""
        self._errors.clear()

    def to_dict(self) -> dict:
        """Serialize all errors as a dict."""
        return {
            "total": len(self._errors),
            "errors": [e.to_dict() for e in self._errors],
        }

    def format_report(self) -> str:
        """Format errors as a human-readable report."""
        if not self._errors:
            return "No errors recorded."

        lines = []
        lines.append("=" * 60)
        lines.append(f"Error Report ({len(self._errors)} error(s))")
        lines.append("=" * 60)
        lines.append("")

        for i, err in enumerate(self._errors, 1):
            lines.append(f"[{i}] {type(err).__name__}: {err.message}")
            lines.append(f"    Operation: {err.context.operation}")
            lines.append(f"    Category:  {err.context.category.value}")
            lines.append(f"    Severity:  {err.context.severity.value}")
            if err.context.correlation_id:
                lines.append(f"    Correlation ID: {err.context.correlation_id}")
            if err.context.metadata:
                lines.append(f"    Metadata:  {err.context.metadata}")
            if err.cause:
                lines.append(f"    Caused by: {err.cause}")
            lines.append("")

        return "\n".join(lines)


def configure_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
) -> None:
    """Configure structured logging for PromptMC.

    Args:
        level: Logging level (e.g. ``logging.INFO``).
        format_string: Optional log format string.
    """
    if format_string is None:
        format_string = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(format_string))

    root_logger = logging.getLogger("promptmc")
    root_logger.setLevel(level)
    root_logger.addHandler(handler)
    root_logger.propagate = False
