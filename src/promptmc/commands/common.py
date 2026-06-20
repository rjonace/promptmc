"""Shared CLI command utilities."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from functools import wraps
from typing import Any

import typer
from rich.console import Console

from promptmc.errors import OpenMCNotFoundError, OpenMCValidationError

console = Console()


def emit_json(payload: Mapping[str, Any]) -> None:
    """Print a structured JSON payload to stdout for agents and CI.

    Written with ``typer.echo`` (not the Rich console) so the output is plain,
    un-styled JSON that downstream tools can parse directly, including when
    piped or redirected to a file.

    Args:
        payload: The JSON-serializable mapping to emit.
    """
    typer.echo(json.dumps(payload, indent=2, default=str))


def handle_errors(func: Callable[..., Any]) -> Callable[..., Any]:
    """Convert PromptMC exceptions into Typer exits."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except OpenMCValidationError as e:
            console.print(f"[red]Validation error: {e}[/red]")
            raise typer.Exit(1) from e
        except OpenMCNotFoundError as e:
            console.print(f"[red]OpenMC not found: {e}[/red]")
            raise typer.Exit(1) from e
        except typer.Exit:
            raise
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1) from e

    return wrapper
