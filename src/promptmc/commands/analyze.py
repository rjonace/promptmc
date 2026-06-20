"""Result analysis CLI command."""

from __future__ import annotations

from pathlib import Path

import typer

from promptmc.commands.common import console, emit_json, handle_errors
from promptmc.visualization import ResultParser, ResultVisualizer


@handle_errors
def analyze(
    output_path: Path = typer.Argument(
        ...,
        help="Path to OpenMC output directory",
        exists=True,
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        "-j",
        help="Emit machine-readable JSON to stdout instead of a report "
        "(redirect with > to save to a file)",
    ),
) -> None:
    """Analyze OpenMC simulation results."""
    parser = ResultParser()
    visualizer = ResultVisualizer()

    result = parser.parse_results(output_path)

    if json_output:
        emit_json(visualizer.result_to_dict(result))
        return

    report = visualizer.format_text_report(result)
    console.print(report)
