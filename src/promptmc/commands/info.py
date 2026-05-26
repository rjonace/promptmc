"""OpenMC/system information CLI commands."""

from __future__ import annotations

import typer
from rich.panel import Panel

from promptmc.commands.common import console, handle_errors
from promptmc.openmc_integration import OpenMCInstaller
from promptmc.progress import OptimizationAdvisor, SystemProfiler


@handle_errors
def info() -> None:
    """Show OpenMC installation information."""
    installer = OpenMCInstaller()
    installation = installer.check_installation()

    api_status = (
        "Available" if installation.python_available else "Not available"
    )
    sub_status = (
        "Available" if installation.subprocess_available else "Not available"
    )
    info_text = (
        f"[bold]OpenMC Installation Information[/bold]\n\n"
        f"Version:    [cyan]{installation.version}[/cyan]\n"
        f"Python API: [cyan]{api_status}[/cyan]\n"
        f"Subprocess: [cyan]{sub_status}[/cyan]\n"
    )

    if installation.executable_path:
        info_text += (
            f"Executable: [cyan]{installation.executable_path}[/cyan]\n"
        )

    console.print(
        Panel(info_text, title="System Information", border_style="cyan")
    )


@handle_errors
def optimize(
    threads: int = typer.Option(
        1, "--threads", "-t", help="Configured thread count"
    ),
    particles: int = typer.Option(
        10000, "--particles", "-p", help="Configured particles"
    ),
    batches: int = typer.Option(
        100, "--batches", "-b", help="Configured batches"
    ),
    target_jobs: int = typer.Option(
        1, "--jobs", "-j", help="Number of concurrent jobs"
    ),
) -> None:
    """Get optimization recommendations for your configuration."""
    advisor = OptimizationAdvisor()
    recommendations = advisor.analyze(
        threads=threads,
        particles=particles,
        batches=batches,
        target_jobs=target_jobs,
    )
    report = advisor.format_report(recommendations)
    console.print(report)


@handle_errors
def system_info_cmd() -> None:
    """Display system information for OpenMC tuning."""
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
