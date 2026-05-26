"""Natural-language assistant CLI command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from promptmc.assistant import NaturalLanguageAssistant
from promptmc.commands.common import console, handle_errors


@handle_errors
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
    model: str | None = typer.Option(
        None,
        "--model",
        help="LLM model name when --llm is used",
    ),
    endpoint: str | None = typer.Option(
        None,
        "--endpoint",
        help="OpenAI-compatible chat completions endpoint when --llm is used",
    ),
) -> None:
    """Turn a plain-English OpenMC request into a runnable configuration plan."""
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
        console.print(
            f"[green]✓[/green] Wrote settings file: [cyan]{result_path}[/cyan]"
        )
        console.print(
            f"[dim]Next: validate with `promptmc validate {result_path} --schema`[/dim]"
        )
