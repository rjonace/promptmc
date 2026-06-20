"""Natural-language assistant CLI command."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.panel import Panel
from rich.table import Table

from promptmc.assistant import DEFAULT_GEMINI_MODEL, NaturalLanguageAssistant
from promptmc.commands.common import console, emit_json, handle_errors


@handle_errors
def plan(
    prompt: str = typer.Argument(
        ...,
        help="Plain-English OpenMC request, e.g. 'make a shielding run with 1M particles'",
    ),
    output: Path = typer.Option(
        Path("openmc_inputs"),
        "--output",
        "-o",
        help="Output directory for the input deck when --write is used",
    ),
    write: bool = typer.Option(
        False,
        "--write",
        "-w",
        help="Write the recommended OpenMC input deck",
    ),
    llm: bool = typer.Option(
        False,
        "--llm",
        help="Use Google Gemini LLM (requires GEMINI_API_KEY)",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        help=f"Gemini model name when --llm is used (default: {DEFAULT_GEMINI_MODEL})",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON to stdout instead of a table",
    ),
) -> None:
    """Turn a plain-English OpenMC request into a runnable configuration plan."""
    assistant = NaturalLanguageAssistant()
    result = assistant.plan(prompt, use_llm=llm, model=model)

    if json_output:
        payload: dict[str, object] = {
            "source": result.source,
            "template_type": result.template_type.value,
            "particles": result.particles,
            "batches": result.batches,
            "inactive": result.inactive,
            "confidence": result.confidence,
            "summary": result.summary,
            "command": result.command(output),
            "rationale": result.rationale,
            "warnings": result.warnings,
            "next_steps": result.next_steps,
        }
        if write:
            payload["written"] = str(result.render(output))
        emit_json(payload)
        return

    table = Table(title="Natural-Language OpenMC Plan", border_style="green")
    table.add_column("Field", style="cyan", no_wrap=True)
    table.add_column("Value")
    table.add_row("Source", result.source)
    table.add_row("Template", result.template_type.value)
    table.add_row("Particles", f"{result.particles:,}")
    table.add_row("Batches", str(result.batches))
    table.add_row("Inactive", str(result.inactive))
    table.add_row("Match score", f"{result.confidence:.0%}")
    table.add_row("Command", result.command(output))
    console.print(table)
    console.print(Panel(result.summary, title="Summary", border_style="blue"))

    if result.rationale:
        console.print("[bold]Why this plan[/bold]")
        for reason in result.rationale:
            console.print(f"- {reason}")

    if result.warnings:
        console.print("[bold yellow]Warnings[/bold yellow]")
        for warning in result.warnings:
            console.print(f"- {warning}")

    if result.next_steps:
        console.print("[bold]Next steps[/bold]")
        for step in result.next_steps:
            console.print(f"- {step}")

    if write:
        result_path = result.render(output)
        console.print(
            f"[green]✓[/green] Wrote input deck: [cyan]{result_path}/[/cyan]"
        )
        console.print(
            f"[dim]Next: validate with `promptmc validate {result_path} --schema`[/dim]"
        )
