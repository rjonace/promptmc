"""Template CLI commands."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from promptmc.commands.common import console, handle_errors
from promptmc.templates import TemplateType, get_template, list_templates


@handle_errors
def template(
    template_type: str = typer.Argument(
        ...,
        help="Template type: criticality, fixed_source, shielding, reactor_pin",
    ),
    output: Path = typer.Option(
        Path("settings.xml"),
        "--output",
        "-o",
        help="Output file path",
    ),
    particles: int | None = typer.Option(
        None, "--particles", "-p", help="Override particles"
    ),
    batches: int | None = typer.Option(
        None, "--batches", "-b", help="Override batches"
    ),
    inactive: int | None = typer.Option(
        None, "--inactive", "-i", help="Override inactive"
    ),
) -> None:
    """Generate a settings.xml from a named template."""
    tmpl_type = TemplateType(template_type.lower())

    tmpl = get_template(tmpl_type)
    result_path = tmpl.render(
        output_path=output,
        particles=particles,
        batches=batches,
        inactive=inactive,
    )

    console.print(
        Panel(
            f"[bold]Template Generated[/bold]\n\n"
            f"Type: [cyan]{tmpl.metadata.name}[/cyan]\n"
            f"Description: {tmpl.metadata.description}\n"
            f"Output: [cyan]{result_path}[/cyan]",
            title="Configuration Template",
            border_style="green",
        )
    )


@handle_errors
def list_templates_cmd() -> None:
    """List all available configuration templates."""
    templates = list_templates()

    table = Table(title="Available Templates", border_style="blue")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Description")
    table.add_column("Particles", justify="right")
    table.add_column("Batches", justify="right")
    table.add_column("Inactive", justify="right")

    for tmpl in templates:
        table.add_row(
            tmpl.template_type.value,
            tmpl.description,
            f"{tmpl.default_particles:,}",
            str(tmpl.default_batches),
            str(tmpl.default_inactive),
        )

    console.print(table)
