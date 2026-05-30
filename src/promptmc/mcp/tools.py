"""MCP tool implementations for PromptMC.

Each tool is a pure function that accepts a Pydantic input model, calls
existing PromptMC code, and returns a Pydantic output model. These
functions intentionally have no dependency on the MCP SDK so they can be
unit-tested in isolation and reused outside an MCP context.

A small in-memory session history records every dispatched tool call for
the lifetime of the process; it backs the ``promptmc://history`` resource.
"""

from __future__ import annotations

import base64
import json
import os
import shlex
import shutil
import subprocess  # nosec B404
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from promptmc.errors import PromptMCError
from promptmc.mcp.schemas import (
    AnalyzeInput,
    CheckInstallationInput,
    CrossSectionCheckInput,
    CrossSectionCheckResult,
    GeometryDebugInput,
    GeometryDebugResult,
    ListTemplatesInput,
    ListTemplatesOutput,
    OpenMCInstallationStatus,
    PlotInput,
    PlotOutput,
    RunSimulationInput,
    SchemaCheckInput,
    SchemaIssueResult,
    SchemaValidationResult,
    SimulationResult,
    SimulationRunResult,
    TemplateInput,
    TemplateMetadataResult,
    TemplateOutput,
    ValidateInput,
    ValidationResult,
)
from promptmc.openmc_integration import (
    ExecutionMode,
    OpenMCInstaller,
    OpenMCRunner,
    OpenMCValidator,
)
from promptmc.schema import SchemaSeverity, SchemaValidator
from promptmc.templates import get_template
from promptmc.templates import list_templates as registry_list_templates
from promptmc.visualization import ResultParser

_MODE_MAP = {
    "auto": ExecutionMode.AUTO,
    "api": ExecutionMode.API,
    "subprocess": ExecutionMode.SUBPROCESS,
}


def check_installation(
    data: CheckInstallationInput,
) -> OpenMCInstallationStatus:
    """Report the local OpenMC installation status."""
    try:
        info = OpenMCInstaller().check_installation()
    except PromptMCError as exc:
        return OpenMCInstallationStatus(
            version="not found",
            executable_path="",
            python_available=False,
            subprocess_available=False,
            error=str(exc),
        )
    return OpenMCInstallationStatus(
        version=info.version,
        executable_path=info.executable_path,
        python_available=info.python_available,
        subprocess_available=info.subprocess_available,
    )


def validate_input(data: ValidateInput) -> ValidationResult:
    """Validate an OpenMC XML input file or directory."""
    try:
        OpenMCValidator().validate_input_file(data.input_path)
    except PromptMCError as exc:
        return ValidationResult(
            is_valid=False, message=str(exc), errors=[str(exc)]
        )
    except Exception as exc:
        return ValidationResult(
            is_valid=False,
            message=str(exc),
            errors=[str(exc)],
            error=str(exc),
        )
    return ValidationResult(is_valid=True, message="Input is valid")


def schema_check(data: SchemaCheckInput) -> SchemaValidationResult:
    """Run Pydantic schema validation over OpenMC input files."""
    try:
        validator = SchemaValidator()
        path = Path(data.input_path)
        if path.is_dir():
            result = validator.validate_directory(path)
        elif path.name == "materials.xml":
            result = validator.validate_materials(path)
        else:
            result = validator.validate_settings(path)
    except Exception as exc:
        return SchemaValidationResult(is_valid=False, error=str(exc))

    issues = [
        SchemaIssueResult(
            severity=issue.severity.value,
            field=issue.field,
            message=issue.message,
            file_path=issue.file_path,
        )
        for issue in result.issues
    ]
    error_count = sum(
        1 for i in result.issues if i.severity == SchemaSeverity.ERROR
    )
    warning_count = sum(
        1 for i in result.issues if i.severity == SchemaSeverity.WARNING
    )
    return SchemaValidationResult(
        is_valid=result.is_valid,
        issues=issues,
        error_count=error_count,
        warning_count=warning_count,
    )


def render_template(data: TemplateInput) -> TemplateOutput:
    """Render a settings.xml file from a named template."""
    try:
        template = get_template(data.template)
        output = template.render(
            data.output_path,
            particles=data.particles,
            batches=data.batches,
            inactive=data.inactive,
        )
        metadata = _template_metadata(template.metadata)
        return TemplateOutput(
            output_path=str(output), template_metadata=metadata
        )
    except Exception as exc:
        return TemplateOutput(
            output_path=data.output_path,
            template_metadata=TemplateMetadataResult(
                name="",
                template_type=data.template,
                description="",
                default_particles=0,
                default_batches=0,
                default_inactive=0,
            ),
            error=str(exc),
        )


def list_templates(data: ListTemplatesInput) -> ListTemplatesOutput:
    """List the available configuration templates."""
    try:
        metadata = registry_list_templates()
    except Exception as exc:
        return ListTemplatesOutput(error=str(exc))
    return ListTemplatesOutput(
        templates=[_template_metadata(m) for m in metadata]
    )


def run_simulation(data: RunSimulationInput) -> SimulationRunResult:
    """Run an OpenMC simulation and capture the result."""
    mode = _MODE_MAP.get(data.mode.lower(), ExecutionMode.AUTO)
    try:
        runner = OpenMCRunner(execution_mode=mode)
        completed = runner.run_simulation(
            data.input_path,
            threads=data.threads,
            output_path=data.output_path,
        )
    except Exception as exc:
        return SimulationRunResult(
            success=False,
            return_code=-1,
            stderr=str(exc),
            input_path=data.input_path,
            mode=data.mode,
            error=str(exc),
        )
    return SimulationRunResult(
        success=completed.returncode == 0,
        return_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        input_path=data.input_path,
        mode=data.mode,
    )


def analyze_results(data: AnalyzeInput) -> SimulationResult:
    """Parse simulation outputs into a structured summary."""
    try:
        parsed = ResultParser().parse_results(data.output_path)
    except Exception as exc:
        return SimulationResult(error=str(exc))
    return SimulationResult(
        statepoint_path=_path_str(parsed.statepoint_path),
        summary_path=_path_str(parsed.summary_path),
        tallies_path=_path_str(parsed.tallies_path),
        k_effective=parsed.k_effective,
        k_effective_std=parsed.k_effective_std,
        n_batches=parsed.n_batches,
        n_particles=parsed.n_particles,
        runtime_seconds=parsed.runtime_seconds,
        tallies_present=bool(parsed.tallies),
    )


def check_cross_sections(
    data: CrossSectionCheckInput,
) -> CrossSectionCheckResult:
    """Check whether OpenMC cross-section data is configured."""
    value = os.environ.get("OPENMC_CROSS_SECTIONS")
    if value and Path(value).exists():
        return CrossSectionCheckResult(found=True, path=value)
    return CrossSectionCheckResult(found=False, path=value or None)


def plot_geometry(data: PlotInput) -> PlotOutput:
    """Render a 2D geometry slice as a base64-encoded PNG."""
    try:
        import openmc
    except ImportError as exc:
        return PlotOutput(error=f"OpenMC Python API not available: {exc}")
    try:  # pragma: no cover - requires the optional openmc dependency
        return _render_plot(openmc, data)
    except Exception as exc:
        return PlotOutput(error=str(exc))


def geometry_debug(data: GeometryDebugInput) -> GeometryDebugResult:
    """Run OpenMC geometry overlap detection via subprocess."""
    executable = shutil.which("openmc")
    if executable is None:
        message = "OpenMC executable not found in PATH"
        return GeometryDebugResult(
            success=False, message=message, error=message
        )
    command = [executable, "--geometry-debug"]
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=data.input_path,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        return GeometryDebugResult(
            success=False, message=str(exc), error=str(exc)
        )
    combined = f"{completed.stdout}\n{completed.stderr}"
    overlaps = [
        line for line in combined.splitlines() if "overlap" in line.lower()
    ]
    return GeometryDebugResult(
        success=completed.returncode == 0,
        overlaps_found=bool(overlaps),
        message=shlex.join(command),
        overlap_details=overlaps,
    )


def _render_plot(
    openmc: Any, data: PlotInput
) -> PlotOutput:  # pragma: no cover
    """Generate a geometry plot PNG using the OpenMC Python API."""
    geometry_dir = Path(data.geometry_xml_path)
    plot = openmc.Plot()
    plot.basis = data.basis
    plot.origin = data.origin
    plot.width = data.width
    plot.pixels = data.pixels
    plot.color_by = data.color_by
    if data.show_overlaps:
        plot.show_overlaps = True
    plot.filename = "promptmc_plot"

    plots = openmc.Plots([plot])
    plots.export_to_xml(geometry_dir)
    openmc.plot_geometry(cwd=str(geometry_dir))

    image_path = geometry_dir / "promptmc_plot.png"
    encoded = base64.b64encode(image_path.read_bytes()).decode()
    return PlotOutput(image_path=str(image_path), base64_png=encoded)


def _template_metadata(metadata: Any) -> TemplateMetadataResult:
    """Convert internal template metadata to the output schema."""
    return TemplateMetadataResult(
        name=metadata.name,
        template_type=metadata.template_type.value,
        description=metadata.description,
        default_particles=metadata.default_particles,
        default_batches=metadata.default_batches,
        default_inactive=metadata.default_inactive,
    )


def _path_str(value: Any) -> str | None:
    """Return ``str(value)`` or None when value is falsy."""
    return str(value) if value else None


@dataclass
class ToolSpec:
    """Internal registration record for a single MCP tool."""

    name: str
    description: str
    input_model: type[BaseModel]
    output_model: type[BaseModel]
    handler: Callable[[Any], BaseModel]


TOOL_REGISTRY: dict[str, ToolSpec] = {
    "openmc_check_installation": ToolSpec(
        name="openmc_check_installation",
        description="Check OpenMC installation status",
        input_model=CheckInstallationInput,
        output_model=OpenMCInstallationStatus,
        handler=check_installation,
    ),
    "openmc_validate": ToolSpec(
        name="openmc_validate",
        description="Validate OpenMC XML input files",
        input_model=ValidateInput,
        output_model=ValidationResult,
        handler=validate_input,
    ),
    "openmc_schema_check": ToolSpec(
        name="openmc_schema_check",
        description="Run Pydantic schema validation",
        input_model=SchemaCheckInput,
        output_model=SchemaValidationResult,
        handler=schema_check,
    ),
    "openmc_template": ToolSpec(
        name="openmc_template",
        description="Generate settings.xml from a template",
        input_model=TemplateInput,
        output_model=TemplateOutput,
        handler=render_template,
    ),
    "openmc_list_templates": ToolSpec(
        name="openmc_list_templates",
        description="List available templates",
        input_model=ListTemplatesInput,
        output_model=ListTemplatesOutput,
        handler=list_templates,
    ),
    "openmc_run": ToolSpec(
        name="openmc_run",
        description="Run an OpenMC simulation",
        input_model=RunSimulationInput,
        output_model=SimulationRunResult,
        handler=run_simulation,
    ),
    "openmc_analyze": ToolSpec(
        name="openmc_analyze",
        description="Parse simulation results",
        input_model=AnalyzeInput,
        output_model=SimulationResult,
        handler=analyze_results,
    ),
    "openmc_check_cross_sections": ToolSpec(
        name="openmc_check_cross_sections",
        description="Check cross-section data availability",
        input_model=CrossSectionCheckInput,
        output_model=CrossSectionCheckResult,
        handler=check_cross_sections,
    ),
    "openmc_plot": ToolSpec(
        name="openmc_plot",
        description="Generate 2D geometry slice plot",
        input_model=PlotInput,
        output_model=PlotOutput,
        handler=plot_geometry,
    ),
    "openmc_geometry_debug": ToolSpec(
        name="openmc_geometry_debug",
        description="Run geometry overlap detection",
        input_model=GeometryDebugInput,
        output_model=GeometryDebugResult,
        handler=geometry_debug,
    ),
}


@dataclass
class HistoryEntry:
    """A single recorded tool invocation in the MCP session."""

    tool: str
    timestamp: str
    input_summary: str
    success: bool


_SESSION_HISTORY: list[HistoryEntry] = []


def record_history(tool: str, arguments: dict[str, Any], success: bool) -> None:
    """Append a tool invocation to the in-memory session history."""
    summary = json.dumps(arguments, default=str)[:200]
    _SESSION_HISTORY.append(
        HistoryEntry(
            tool=tool,
            timestamp=datetime.now(timezone.utc).isoformat(),
            input_summary=summary,
            success=success,
        )
    )


def get_session_history() -> list[HistoryEntry]:
    """Return a copy of the current session history."""
    return list(_SESSION_HISTORY)


def clear_session_history() -> None:
    """Clear the in-memory session history."""
    _SESSION_HISTORY.clear()


def dispatch(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Validate input, run the named tool, and record the call.

    Args:
        name: Registered MCP tool name.
        arguments: Raw argument mapping from the MCP client.

    Returns:
        The tool output model serialized to a JSON-compatible dict.

    Raises:
        KeyError: If the tool name is not registered.
    """
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        raise KeyError(f"Unknown tool: {name}")
    data = spec.input_model.model_validate(arguments)
    result = spec.handler(data)
    success = getattr(result, "error", None) is None
    record_history(name, arguments, success)
    return result.model_dump(mode="json")
