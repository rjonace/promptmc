"""Input validation CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from promptmc.commands.common import console, handle_errors
from promptmc.openmc_integration import OpenMCValidator
from promptmc.schema import SchemaValidator, format_validation_report


@handle_errors
def validate(
    input_file: Path = typer.Argument(
        ...,
        help="Path to OpenMC input file or directory",
        exists=True,
    ),
    schema: bool = typer.Option(
        False,
        "--schema",
        "-s",
        help="Also run schema validation",
    ),
) -> None:
    """Validate OpenMC input files (XML structure + optional schema checks)."""
    validator = OpenMCValidator()

    console.print(
        Panel(
            f"[bold]Validating OpenMC input[/bold]\n\n"
            f"Input: [cyan]{input_file}[/cyan]\n"
            f"Schema validation: [cyan]{schema}[/cyan]",
            title="Validation",
            border_style="yellow",
        )
    )

    is_valid = validator.validate_input_file(input_file)

    if is_valid:
        console.print("[green]✓[/green] XML structure validation passed")
    else:
        console.print("[red]✗[/red] XML structure validation failed")
        raise typer.Exit(1)

    if schema:
        schema_validator = SchemaValidator()
        if Path(input_file).is_dir():
            result = schema_validator.validate_directory(input_file)
        else:
            result = schema_validator.validate_settings(input_file)

        console.print(format_validation_report(result))

        if not result.is_valid:
            raise typer.Exit(1)
        else:
            console.print("[green]✓[/green] Schema validation passed")


@handle_errors
def schema_check(
    input_path: Path = typer.Argument(
        ...,
        help="Path to settings.xml file or input directory",
        exists=True,
    ),
) -> None:
    """Run schema validation against OpenMC XML input files."""
    validator = SchemaValidator()

    if Path(input_path).is_dir():
        result = validator.validate_directory(input_path)
    else:
        result = validator.validate_settings(input_path)

    console.print(format_validation_report(result))

    if not result.is_valid:
        raise typer.Exit(1)
