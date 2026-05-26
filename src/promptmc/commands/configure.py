"""Configuration generation CLI command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from promptmc.commands.common import console, handle_errors
from promptmc.openmc_integration import OpenMCRunner


@handle_errors
def configure(
    output: Path = typer.Option(
        Path("openmc_config.xml"),
        "--output",
        "-o",
        help="Output configuration file path",
    ),
    particles: int = typer.Option(
        10000,
        "--particles",
        "-p",
        help="Number of particles per batch",
        min=1,
    ),
    batches: int = typer.Option(
        10,
        "--batches",
        "-b",
        help="Number of batches",
        min=1,
    ),
    inactive: int = typer.Option(
        5,
        "--inactive",
        "-i",
        help="Number of inactive batches",
        min=0,
    ),
) -> None:
    """Generate an OpenMC configuration file."""
    runner = OpenMCRunner()

    console.print(
        Panel(
            f"[bold]Generating OpenMC configuration[/bold]\n\n"
            f"Output: [cyan]{output}[/cyan]\n"
            f"Particles: [cyan]{particles}[/cyan]\n"
            f"Batches: [cyan]{batches}[/cyan]\n"
            f"Inactive: [cyan]{inactive}[/cyan]",
            title="Configuration",
            border_style="blue",
        )
    )

    result_path = runner.generate_configuration(
        output_path=output,
        particles=particles,
        batches=batches,
        inactive=inactive,
    )

    console.print(
        f"[green]✓[/green] Configuration generated: [cyan]{result_path}[/cyan]"
    )
