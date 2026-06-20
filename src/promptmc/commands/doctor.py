"""Environment diagnostics CLI command.

``promptmc doctor`` runs every onboarding environment check in one shot and
prints a single status report with a concrete fix hint for each missing
piece. Setup is the top onboarding friction; the individual checks already
exist across the codebase and this command composes them.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from xml.etree.ElementTree import ParseError  # nosec B405

import typer
from defusedxml.ElementTree import parse as defused_parse
from rich.markup import escape
from rich.table import Table

from promptmc.commands.common import console, emit_json, handle_errors
from promptmc.telemetry import telemetry_available

_INSTALL_HINT = (
    "Install OpenMC, e.g. `conda create -n openmc-env -c conda-forge openmc` "
    "(see https://docs.openmc.org/en/stable/quickinstall.html)."
)
_DATA_HINT = (
    "Download OpenMC nuclear data and point OPENMC_CROSS_SECTIONS at the "
    "resulting cross_sections.xml (see "
    "https://docs.openmc.org/en/stable/usersguide/cross_sections.html)."
)


@dataclass
class Check:
    """The outcome of a single environment check.

    Attributes:
        name: Stable machine-readable identifier (used as the JSON key).
        label: Human-readable name for the status report.
        ok: Whether the check passed.
        detail: One-line explanation of the current state.
        fix: A concrete remediation hint, present only when ``ok`` is False.
        optional: When True the check is informational and does not affect the
            overall ready/exit status (enhancements like the Python API and
            telemetry rather than hard requirements for running OpenMC).
    """

    name: str
    label: str
    ok: bool
    detail: str
    fix: str | None = None
    optional: bool = False


def _check_openmc_executable() -> Check:
    """Check that the ``openmc`` executable is on PATH."""
    path = shutil.which("openmc")
    if path:
        return Check(
            "openmc_executable",
            "OpenMC executable",
            True,
            f"found at {path}",
        )
    return Check(
        "openmc_executable",
        "OpenMC executable",
        False,
        "not found on PATH",
        fix=_INSTALL_HINT,
    )


def _check_python_api() -> Check:
    """Check that the OpenMC Python API can be imported."""
    try:
        import openmc
    except ImportError:
        return Check(
            "openmc_python_api",
            "OpenMC Python API",
            False,
            "`import openmc` is not available in this environment",
            fix=(
                "Install OpenMC's Python package into this environment "
                "(needed for plot rendering and geometry-debug)."
            ),
            optional=True,
        )
    version = getattr(openmc, "__version__", "unknown")
    return Check(
        "openmc_python_api",
        "OpenMC Python API",
        True,
        f"import openmc OK (version {version})",
        optional=True,
    )


def _cross_section_checks() -> list[Check]:
    """Check that cross-section data is configured and present on disk.

    Produces two checks: whether ``OPENMC_CROSS_SECTIONS`` resolves to a
    parseable ``cross_sections.xml`` index, and whether the data files that
    index references actually exist (i.e. the data has been downloaded).
    """

    def _failed(detail: str, reason: str) -> list[Check]:
        return [
            Check(
                "cross_sections",
                "Cross-section index",
                False,
                detail,
                fix=_DATA_HINT,
            ),
            _data_unknown(reason),
        ]

    value = os.environ.get("OPENMC_CROSS_SECTIONS")
    if not value:
        return _failed(
            "OPENMC_CROSS_SECTIONS is not set",
            "OPENMC_CROSS_SECTIONS is not set",
        )

    path = Path(value)
    if not path.exists():
        return _failed(
            f"OPENMC_CROSS_SECTIONS points at a missing file: {value}",
            "the index file is missing",
        )

    try:
        root = defused_parse(str(path)).getroot()
    except (OSError, ParseError) as e:
        return _failed(
            f"cross_sections.xml could not be parsed: {e}",
            "the index could not be parsed",
        )

    configured = Check(
        "cross_sections",
        "Cross-section index",
        True,
        f"valid index at {path}",
    )
    return [configured, _check_data_files(path, root)]


def _data_unknown(reason: str) -> Check:
    """A failing data check when the index itself is unavailable."""
    return Check(
        "data_downloaded",
        "Cross-section data files",
        False,
        f"cannot verify data files because {reason}",
        fix=_DATA_HINT,
    )


def _check_data_files(index_path: Path, root: object) -> Check:
    """Check that the data files referenced by the index exist on disk."""
    base = index_path.parent
    libraries = [
        lib.get("path")
        for lib in root.findall("library")  # type: ignore[attr-defined]
        if lib.get("path")
    ]
    if not libraries:
        return Check(
            "data_downloaded",
            "Cross-section data files",
            False,
            "the index lists no data libraries",
            fix=_DATA_HINT,
        )

    missing = 0
    for lib in libraries:
        candidate = Path(lib)
        if not candidate.is_absolute():
            candidate = base / lib
        if not candidate.exists():
            missing += 1

    total = len(libraries)
    present = total - missing
    if missing:
        return Check(
            "data_downloaded",
            "Cross-section data files",
            False,
            f"{present} of {total} referenced data files present "
            f"({missing} missing)",
            fix=_DATA_HINT,
        )
    return Check(
        "data_downloaded",
        "Cross-section data files",
        True,
        f"all {total} referenced data files present",
    )


def _check_telemetry() -> Check:
    """Check whether the optional telemetry extra is installed."""
    if telemetry_available():
        return Check(
            "telemetry_extra",
            "Telemetry extra",
            True,
            "OpenTelemetry packages are importable",
            optional=True,
        )
    return Check(
        "telemetry_extra",
        "Telemetry extra",
        False,
        "the optional `telemetry` extra is not installed",
        fix="Install with `pip install 'promptmc[telemetry]'` (optional).",
        optional=True,
    )


def gather_checks() -> list[Check]:
    """Run every environment check and return the results in report order."""
    checks = [_check_openmc_executable(), _check_python_api()]
    checks.extend(_cross_section_checks())
    checks.append(_check_telemetry())
    return checks


@handle_errors
def doctor(
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit machine-readable JSON to stdout instead of a table",
    ),
) -> None:
    """Run all environment checks and report setup status with fix hints."""
    checks = gather_checks()
    ready = all(c.ok for c in checks if not c.optional)

    if json_output:
        emit_json(
            {
                "ready": ready,
                "checks": [
                    {
                        "name": c.name,
                        "ok": c.ok,
                        "optional": c.optional,
                        "detail": c.detail,
                        "fix": c.fix,
                    }
                    for c in checks
                ],
            }
        )
        if not ready:
            raise typer.Exit(1)
        return

    table = Table(title="PromptMC Environment", border_style="cyan")
    table.add_column("", no_wrap=True)
    table.add_column("Check", style="cyan", no_wrap=True)
    table.add_column("Status")

    for check in checks:
        if check.ok:
            mark = "[green]✓[/green]"
        elif check.optional:
            mark = "[yellow]○[/yellow]"
        else:
            mark = "[red]✗[/red]"
        table.add_row(mark, check.label, escape(check.detail))

    console.print(table)

    failures = [c for c in checks if not c.ok]
    if failures:
        console.print("\n[bold]How to fix[/bold]")
        for check in failures:
            console.print(
                f"[cyan]{check.label}[/cyan]: {escape(check.fix or '')}"
            )

    console.print()
    if ready:
        console.print("[green]✓ Environment ready to run OpenMC.[/green]")
    else:
        required_failures = sum(
            1 for c in checks if not c.ok and not c.optional
        )
        console.print(
            f"[red]✗ {required_failures} required check(s) need attention "
            f"before OpenMC can run.[/red]"
        )
        raise typer.Exit(1)
