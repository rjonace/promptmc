"""Result analysis CLI command."""

from __future__ import annotations

from pathlib import Path

import typer

from promptmc.commands.common import console, handle_errors
from promptmc.visualization import ResultParser, ResultVisualizer


@handle_errors
def analyze(
    output_path: Path = typer.Argument(
        ...,
        help="Path to OpenMC output directory",
        exists=True,
    ),
    export_json: Path | None = typer.Option(
        None,
        "--json",
        "-j",
        help="Export results to JSON file",
    ),
) -> None:
    """Analyze OpenMC simulation results."""
    parser = ResultParser()
    visualizer = ResultVisualizer()

    result = parser.parse_results(output_path)
    report = visualizer.format_text_report(result)
    console.print(report)

    if export_json:
        json_path = visualizer.export_json(result, export_json)
        console.print(
            f"[green]✓[/green] Results exported to: [cyan]{json_path}[/cyan]"
        )
