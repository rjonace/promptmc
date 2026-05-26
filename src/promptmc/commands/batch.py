"""Batch execution CLI command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from promptmc.batch import (
    BatchRunner,
    ParallelConfig,
    ParallelMode,
    load_batch_spec,
)
from promptmc.commands.common import console, handle_errors


@handle_errors
def batch(
    spec_file: Path = typer.Argument(
        ...,
        help="Path to batch specification YAML/JSON file",
        exists=True,
    ),
    parallel_mode: str = typer.Option(
        "threads",
        "--parallel",
        "-P",
        help="Parallel mode: threads, processes, or mpi",
    ),
    max_workers: int | None = typer.Option(
        None,
        "--workers",
        "-w",
        help="Maximum concurrent workers",
    ),
) -> None:
    """Run a batch of simulations from a specification file."""
    mode = ParallelMode(parallel_mode.lower())

    spec = load_batch_spec(spec_file)
    config = ParallelConfig(mode=mode, max_workers=max_workers)
    runner = BatchRunner(parallel_config=config)

    console.print(
        Panel(
            f"[bold]Running Batch: {spec.name}[/bold]\n\n"
            f"Description: {spec.description}\n"
            f"Base input:  [cyan]{spec.base_input}[/cyan]\n"
            f"Output root: [cyan]{spec.output_root}[/cyan]\n"
            f"Mode:        [cyan]{parallel_mode}[/cyan]\n"
            f"Workers:     [cyan]{config.max_workers or 'auto'}[/cyan]",
            title="Batch Configuration",
            border_style="green",
        )
    )

    summary = runner.run_batch(spec)

    border = "green" if summary.failed_jobs == 0 else "yellow"
    console.print(
        Panel(
            f"[bold]Batch Complete[/bold]\n\n"
            f"Batch ID:         [cyan]{summary.batch_id}[/cyan]\n"
            f"Total:            [cyan]{summary.total_jobs}[/cyan]\n"
            f"Successful:       [green]{summary.successful_jobs}[/green]\n"
            f"Failed:           [red]{summary.failed_jobs}[/red]\n"
            f"Total duration:   [cyan]{summary.total_duration_seconds:.2f}s[/cyan]\n"
            f"Average duration: [cyan]{summary.average_duration_seconds:.2f}s[/cyan]",
            title="Batch Summary",
            border_style=border,
        )
    )

    if summary.failed_jobs > 0:
        raise typer.Exit(1)
