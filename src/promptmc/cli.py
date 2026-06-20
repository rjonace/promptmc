"""Command-line interface for PromptMC."""

from __future__ import annotations

import sys
from pathlib import Path

import typer

from promptmc import __version__
from promptmc.commands.analyze import analyze
from promptmc.commands.batch import batch
from promptmc.commands.common import console
from promptmc.commands.doctor import doctor
from promptmc.commands.info import info, optimize, system_info_cmd
from promptmc.commands.plan import plan
from promptmc.commands.run import run
from promptmc.commands.templates import list_templates_cmd, template
from promptmc.commands.validate import schema_check, validate
from promptmc.errors import configure_logging

app = typer.Typer(
    name="promptmc",
    help="Production-grade Python wrapper for OpenMC Monte Carlo simulations",
    add_completion=False,
)


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(
            f"[bold green]promptmc[/bold green] version [cyan]{__version__}[/cyan]"
        )
        raise typer.Exit()


@app.callback()
def main(
    version: bool | None = typer.Option(
        None,
        "--version",
        "-v",
        callback=version_callback,
        is_eager=True,
        help="Show version and exit",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose output",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to configuration file",
        exists=True,
    ),
) -> None:
    """PromptMC – production-grade Python wrapper for OpenMC Monte Carlo simulations."""
    if verbose:
        configure_logging()
        console.print("[dim]Verbose mode enabled[/dim]")

    if config:
        console.print(f"[dim]Using config file: {config}[/dim]")


app.command()(run)
app.command()(validate)
app.command()(doctor)
app.command()(info)
app.command()(template)
app.command(name="list-templates")(list_templates_cmd)
app.command()(plan)
app.command()(batch)
app.command()(analyze)
app.command()(optimize)
app.command(name="system-info")(system_info_cmd)
app.command(name="schema-check")(schema_check)


def main_cli() -> None:
    """Entry point for the CLI."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main_cli()
