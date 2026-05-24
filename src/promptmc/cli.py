"""Command-line interface for PromptMC."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from promptmc import __version__
from promptmc.assistant import NaturalLanguageAssistant
from promptmc.batch import BatchRunner, load_batch_spec
from promptmc.errors import configure_logging
from promptmc.openmc_integration import (
    ExecutionMode,
    OpenMCIntegration,
    OpenMCNotFoundError,
    OpenMCValidationError,
)
from promptmc.parallel import ParallelConfig, ParallelMode
from promptmc.performance import OptimizationAdvisor, SystemProfiler
from promptmc.plugins import get_plugin_registry
from promptmc.schema import SchemaValidator, format_validation_report
from promptmc.telemetry import get_telemetry_manager
from promptmc.templates import TemplateType, get_template, list_templates
from promptmc.visualization import ResultParser, ResultVisualizer

app = typer.Typer(
    name="promptmc",
    help="Production-grade Python wrapper for OpenMC Monte Carlo simulations",
    add_completion=False,
)

console = Console()


def version_callback(value: bool) -> None:
    """Show version and exit."""
    if value:
        console.print(f"[bold green]promptmc[/bold green] version [cyan]{__version__}[/cyan]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        callback=version_callback,
        help="Show version and exit",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose",
        help="Enable verbose output",
    ),
    config: Optional[Path] = typer.Option(
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


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


@app.command()
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
    output: Optional[Path] = typer.Option(
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
    try:
        execution_mode = ExecutionMode(mode.lower())
    except ValueError:
        console.print(f"[red]Invalid mode: {mode}. Use 'auto', 'api', or 'subprocess'[/red]")
        raise typer.Exit(1) from None

    try:
        integration = OpenMCIntegration(execution_mode=execution_mode)

        console.print(f"[dim]Validating input: {input_file}[/dim]")
        integration.validate_input_file(input_file)
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

        registry = get_plugin_registry()
        registry.fire_hook("before_run", {"input_file": str(input_file), "threads": threads})

        telemetry.record_simulation_start(simulation_id)

        with telemetry.trace_operation(
            "openmc_simulation",
            simulation_id=simulation_id,
            threads=threads,
            mode=mode,
        ):
            result = integration.run_simulation(
                input_path=input_file,
                threads=threads,
                output_path=output,
            )

        registry.fire_hook("after_run", {"returncode": result.returncode})

        if result.returncode == 0:
            console.print("[green]✓[/green] Simulation completed successfully")
            if result.stdout:
                console.print(f"[dim]{result.stdout}[/dim]")
            telemetry.record_simulation_complete(
                simulation_id=simulation_id,
                duration_seconds=0.0,
            )
        else:
            console.print(f"[red]✗[/red] Simulation failed with return code {result.returncode}")
            if result.stderr:
                console.print(f"[red]{result.stderr}[/red]")
            telemetry.record_simulation_error(
                simulation_id=simulation_id,
                error_type="ExecutionError",
            )
            raise typer.Exit(1)

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


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------


@app.command()
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
    try:
        integration = OpenMCIntegration()

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

        result_path = integration.generate_configuration(
            output_path=output,
            particles=particles,
            batches=batches,
            inactive=inactive,
        )

        console.print(f"[green]✓[/green] Configuration generated: [cyan]{result_path}[/cyan]")

    except Exception as e:
        console.print(f"[red]Error generating configuration: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


@app.command()
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
    try:
        integration = OpenMCIntegration()

        console.print(
            Panel(
                f"[bold]Validating OpenMC input[/bold]\n\n"
                f"Input: [cyan]{input_file}[/cyan]\n"
                f"Schema validation: [cyan]{schema}[/cyan]",
                title="Validation",
                border_style="yellow",
            )
        )

        is_valid = integration.validate_input_file(input_file)

        if is_valid:
            console.print("[green]✓[/green] XML structure validation passed")
        else:
            console.print("[red]✗[/red] XML structure validation failed")
            raise typer.Exit(1)

        if schema:
            validator = SchemaValidator()
            if Path(input_file).is_dir():
                result = validator.validate_directory(input_file)
            else:
                result = validator.validate_settings(input_file)

            console.print(format_validation_report(result))

            if not result.is_valid:
                raise typer.Exit(1)
            else:
                console.print("[green]✓[/green] Schema validation passed")

    except OpenMCValidationError as e:
        console.print(f"[red]Validation error: {e}[/red]")
        raise typer.Exit(1) from e
    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


@app.command()
def info() -> None:
    """Show OpenMC installation information."""
    try:
        integration = OpenMCIntegration()
        installation = integration.check_installation()

        api_status = "Available" if installation.python_available else "Not available"
        sub_status = "Available" if installation.subprocess_available else "Not available"
        info_text = (
            f"[bold]OpenMC Installation Information[/bold]\n\n"
            f"Version:    [cyan]{installation.version}[/cyan]\n"
            f"Python API: [cyan]{api_status}[/cyan]\n"
            f"Subprocess: [cyan]{sub_status}[/cyan]\n"
        )

        if installation.executable_path:
            info_text += f"Executable: [cyan]{installation.executable_path}[/cyan]\n"

        console.print(Panel(info_text, title="System Information", border_style="cyan"))

    except OpenMCNotFoundError as e:
        console.print(f"[red]OpenMC not found: {e}[/red]")
        raise typer.Exit(1) from e
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------


@app.command()
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
    particles: Optional[int] = typer.Option(None, "--particles", "-p", help="Override particles"),
    batches: Optional[int] = typer.Option(None, "--batches", "-b", help="Override batches"),
    inactive: Optional[int] = typer.Option(None, "--inactive", "-i", help="Override inactive"),
) -> None:
    """Generate a settings.xml from a named template."""
    try:
        tmpl_type = TemplateType(template_type.lower())
    except ValueError:
        available = [t.value for t in TemplateType]
        console.print(f"[red]Unknown template: {template_type}. Available: {available}[/red]")
        raise typer.Exit(1) from None

    try:
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

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# list-templates
# ---------------------------------------------------------------------------


@app.command(name="list-templates")
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


# ---------------------------------------------------------------------------
# ask
# ---------------------------------------------------------------------------


@app.command()
def ask(
    prompt: str = typer.Argument(
        ...,
        help="Plain-English OpenMC request, e.g. 'make a shielding run with 1M particles'",
    ),
    output: Path = typer.Option(
        Path("settings.xml"),
        "--output",
        "-o",
        help="Output settings.xml path when --write is used",
    ),
    write: bool = typer.Option(
        False,
        "--write",
        "-w",
        help="Write the recommended settings.xml file",
    ),
    llm: bool = typer.Option(
        False,
        "--llm",
        help="Use an OpenAI-compatible LLM if OPENAI_API_KEY or PROMPTMC_LLM_API_KEY is set",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="LLM model name when --llm is used",
    ),
    endpoint: Optional[str] = typer.Option(
        None,
        "--endpoint",
        help="OpenAI-compatible chat completions endpoint when --llm is used",
    ),
) -> None:
    """Turn a plain-English OpenMC request into a runnable configuration plan."""
    try:
        assistant = NaturalLanguageAssistant()
        plan = assistant.plan(prompt, use_llm=llm, model=model, endpoint=endpoint)

        table = Table(title="Natural-Language OpenMC Plan", border_style="green")
        table.add_column("Field", style="cyan", no_wrap=True)
        table.add_column("Value")
        table.add_row("Source", plan.source)
        table.add_row("Template", plan.template_type.value)
        table.add_row("Particles", f"{plan.particles:,}")
        table.add_row("Batches", str(plan.batches))
        table.add_row("Inactive", str(plan.inactive))
        table.add_row("Confidence", f"{plan.confidence:.0%}")
        table.add_row("Command", plan.command(output))
        console.print(table)
        console.print(Panel(plan.summary, title="Summary", border_style="blue"))

        if plan.rationale:
            console.print("[bold]Why this plan[/bold]")
            for reason in plan.rationale:
                console.print(f"- {reason}")

        if plan.warnings:
            console.print("[bold yellow]Warnings[/bold yellow]")
            for warning in plan.warnings:
                console.print(f"- {warning}")

        if plan.next_steps:
            console.print("[bold]Next steps[/bold]")
            for step in plan.next_steps:
                console.print(f"- {step}")

        if write:
            result_path = plan.render(output)
            console.print(f"[green]✓[/green] Wrote settings file: [cyan]{result_path}[/cyan]")
            console.print(
                "[dim]Next: validate with `promptmc validate "
                f"{result_path} --schema`[/dim]"
            )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------


@app.command()
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
    max_workers: Optional[int] = typer.Option(
        None,
        "--workers",
        "-w",
        help="Maximum concurrent workers",
    ),
) -> None:
    """Run a batch of simulations from a specification file."""
    try:
        mode = ParallelMode(parallel_mode.lower())
    except ValueError:
        console.print(f"[red]Invalid parallel mode: {parallel_mode}[/red]")
        raise typer.Exit(1) from None

    try:
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

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


@app.command()
def analyze(
    output_path: Path = typer.Argument(
        ...,
        help="Path to OpenMC output directory",
        exists=True,
    ),
    export_json: Optional[Path] = typer.Option(
        None,
        "--json",
        "-j",
        help="Export results to JSON file",
    ),
) -> None:
    """Analyze OpenMC simulation results."""
    try:
        parser = ResultParser()
        visualizer = ResultVisualizer()

        result = parser.parse_results(output_path)
        report = visualizer.format_text_report(result)
        console.print(report)

        if export_json:
            json_path = visualizer.export_json(result, export_json)
            console.print(f"[green]✓[/green] Results exported to: [cyan]{json_path}[/cyan]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# optimize
# ---------------------------------------------------------------------------


@app.command()
def optimize(
    threads: int = typer.Option(1, "--threads", "-t", help="Configured thread count"),
    particles: int = typer.Option(10000, "--particles", "-p", help="Configured particles"),
    batches: int = typer.Option(100, "--batches", "-b", help="Configured batches"),
    target_jobs: int = typer.Option(1, "--jobs", "-j", help="Number of concurrent jobs"),
) -> None:
    """Get optimization recommendations for your configuration."""
    try:
        advisor = OptimizationAdvisor()
        recommendations = advisor.analyze(
            threads=threads,
            particles=particles,
            batches=batches,
            target_jobs=target_jobs,
        )
        report = advisor.format_report(recommendations)
        console.print(report)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# system-info
# ---------------------------------------------------------------------------


@app.command(name="system-info")
def system_info_cmd() -> None:
    """Display system information for OpenMC tuning."""
    try:
        profiler = SystemProfiler()
        sys_info = profiler.get_system_info()

        console.print(
            Panel(
                f"[bold]System Information[/bold]\n\n"
                f"CPU (logical):       [cyan]{sys_info.cpu_count}[/cyan]\n"
                f"CPU (physical):      [cyan]{sys_info.cpu_count_physical}[/cyan]\n"
                f"Total memory:        [cyan]{sys_info.total_memory_gb:.2f} GB[/cyan]\n"
                f"Available memory:    [cyan]{sys_info.available_memory_gb:.2f} GB[/cyan]\n"
                f"Platform:            [cyan]{sys_info.platform}[/cyan]\n"
                f"Recommended threads: [cyan]{profiler.recommend_thread_count()}[/cyan]\n"
                f"Recommended particles: [cyan]{profiler.recommend_particle_count():,}[/cyan]",
                title="System Info",
                border_style="cyan",
            )
        )

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# schema-check
# ---------------------------------------------------------------------------


@app.command(name="schema-check")
def schema_check(
    input_path: Path = typer.Argument(
        ...,
        help="Path to settings.xml file or input directory",
        exists=True,
    ),
) -> None:
    """Run schema validation against OpenMC XML input files."""
    try:
        validator = SchemaValidator()

        if Path(input_path).is_dir():
            result = validator.validate_directory(input_path)
        else:
            result = validator.validate_settings(input_path)

        console.print(format_validation_report(result))

        if not result.is_valid:
            raise typer.Exit(1)

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


# ---------------------------------------------------------------------------
# plugins
# ---------------------------------------------------------------------------


@app.command(name="list-plugins")
def list_plugins_cmd() -> None:
    """List all registered plugins."""
    registry = get_plugin_registry()
    loaded = registry.discover_entry_points()
    plugins = registry.list_plugins()

    if loaded:
        console.print(f"[dim]Discovered {loaded} plugin(s) from entry points[/dim]")

    if not plugins:
        console.print("[yellow]No plugins registered.[/yellow]")
        return

    table = Table(title="Registered Plugins", border_style="blue")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Type")
    table.add_column("Version")
    table.add_column("Description")

    for meta in plugins:
        table.add_row(
            meta.name,
            meta.plugin_type.value,
            meta.version,
            meta.description or "",
        )

    console.print(table)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


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
