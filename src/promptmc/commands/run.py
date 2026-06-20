"""Run simulation CLI command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from promptmc.commands.common import console, handle_errors
from promptmc.openmc_integration import (
    ExecutionMode,
    OpenMCRunner,
    OpenMCValidator,
)
from promptmc.telemetry import get_telemetry_manager


@handle_errors
def run(
    input_file: Path = typer.Argument(
        ...,
        help="Path to OpenMC input file or directory",
        exists=True,
    ),
    threads: int = typer.Option(
        1,
        "--threads",
        "-t",
        help="Number of threads to use",
        min=1,
    ),
    output: Path | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory for results",
    ),
    mode: str = typer.Option(
        "auto",
        "--mode",
        "-m",
        help="Execution mode: auto, api, or subprocess",
    ),
) -> None:
    """Run an OpenMC simulation."""
    execution_mode = ExecutionMode(mode.lower())

    runner = OpenMCRunner(execution_mode=execution_mode)
    validator = OpenMCValidator()

    console.print(f"[dim]Validating input: {input_file}[/dim]")
    validator.validate_input_file(input_file)
    console.print("[green]✓[/green] Input validation passed")

    telemetry = get_telemetry_manager()
    simulation_id = input_file.stem

    console.print(
        Panel(
            f"[bold]Running OpenMC simulation[/bold]\n\n"
            f"Input: [cyan]{input_file}[/cyan]\n"
            f"Threads: [cyan]{threads}[/cyan]\n"
            f"Output: [cyan]{output or 'default'}[/cyan]\n"
            f"Mode: [cyan]{mode}[/cyan]",
            title="Simulation Configuration",
            border_style="green",
        )
    )

    telemetry.record_simulation_start(simulation_id)

    with telemetry.trace_operation(
        "openmc_simulation",
        simulation_id=simulation_id,
        threads=threads,
        mode=mode,
    ):
        result = runner.run_simulation(
            input_path=input_file,
            threads=threads,
            output_path=output,
        )

    if result.success:
        console.print("[green]✓[/green] Simulation completed successfully")
        if result.stdout:
            console.print(f"[dim]{result.stdout}[/dim]")
        telemetry.record_simulation_complete(
            simulation_id=simulation_id,
            duration_seconds=0.0,
        )
    else:
        console.print(
            f"[red]✗[/red] Simulation failed with return code {result.return_code}"
        )
        if result.stderr:
            console.print(f"[red]{result.stderr}[/red]")
        telemetry.record_simulation_error(
            simulation_id=simulation_id,
            error_type="ExecutionError",
        )
        raise typer.Exit(1)
