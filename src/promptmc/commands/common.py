"""Shared CLI command utilities."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

import typer
from rich.console import Console

from promptmc.errors import OpenMCNotFoundError, OpenMCValidationError

console = Console()


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
