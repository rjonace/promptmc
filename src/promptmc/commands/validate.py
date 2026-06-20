"""Input validation CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel

from promptmc.commands.common import console, emit_json, handle_errors
from promptmc.errors import OpenMCValidationError
from promptmc.openmc_integration import OpenMCValidator
from promptmc.schema import (
    SchemaValidationResult,
    SchemaValidator,
    format_validation_report,
)


def _issues_payload(result: SchemaValidationResult) -> list[dict[str, object]]:
    """Render schema issues as plain JSON-serializable dicts."""
    return [
        {
            "severity": issue.severity.value,
            "field": issue.field,
            "message": issue.message,
            "file_path": issue.file_path,
        }
        for issue in result.issues
    ]


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
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON to stdout instead of a report",
    ),
) -> None:
    """Validate OpenMC input files (XML structure + optional schema checks)."""
    validator = OpenMCValidator()

    if not json_output:
        console.print(
            Panel(
                f"[bold]Validating OpenMC input[/bold]\n\n"
                f"Input: [cyan]{input_file}[/cyan]\n"
                f"Schema validation: [cyan]{schema}[/cyan]",
                title="Validation",
                border_style="yellow",
            )
        )

    # ``validate_input_file`` returns True or raises on malformed XML; in JSON
    # mode the failure is reported as data rather than a raised error so the
    # output stays parseable.
    xml_error: str | None = None
    try:
        xml_valid = bool(validator.validate_input_file(input_file))
    except OpenMCValidationError as e:
        if not json_output:
            raise
        xml_valid = False
        xml_error = str(e)

    schema_result: SchemaValidationResult | None = None
    if schema and xml_valid:
        schema_validator = SchemaValidator()
        if Path(input_file).is_dir():
            schema_result = schema_validator.validate_directory(input_file)
        else:
            schema_result = schema_validator.validate_settings(input_file)

    schema_valid = schema_result.is_valid if schema_result else None
    overall_valid = xml_valid and schema_valid is not False

    if json_output:
        emit_json(
            {
                "input": str(input_file),
                "schema_checked": schema,
                "xml_valid": xml_valid,
                "xml_error": xml_error,
                "schema_valid": schema_valid,
                "issues": _issues_payload(schema_result)
                if schema_result
                else [],
                "valid": overall_valid,
            }
        )
        if not overall_valid:
            raise typer.Exit(1)
        return

    if xml_valid:
        console.print("[green]✓[/green] XML structure validation passed")
    else:
        console.print("[red]✗[/red] XML structure validation failed")
        raise typer.Exit(1)

    if schema_result is not None:
        console.print(format_validation_report(schema_result))

        if not schema_result.is_valid:
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
