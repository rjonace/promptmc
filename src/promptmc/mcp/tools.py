"""MCP tool implementations for PromptMC.

Each tool is a function that accepts a Pydantic input model, calls existing
PromptMC code, and returns a Pydantic output model. These functions
intentionally have no dependency on the MCP SDK so they can be unit-tested
in isolation and reused outside an MCP context.

A bounded, in-memory session history records every dispatched tool call for
the lifetime of the process; it backs the ``promptmc://history`` resource.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import shlex
import shutil
import subprocess  # nosec B404
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Generic, TypeVar

from defusedxml.ElementTree import ParseError
from defusedxml.ElementTree import parse as defused_parse
from pydantic import BaseModel
from pydantic import ValidationError as PydanticValidationError

from promptmc.errors import MCPError, PromptMCError
from promptmc.mcp.schemas import (
    AnalysisResult,
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
    SimulationRunResult,
    TemplateInput,
    TemplateMetadataResult,
    TemplateOutput,
    ToolOutput,
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
from promptmc.schema import SchemaValidationResult as InternalSchemaResult
from promptmc.templates import TemplateMetadata, get_template
from promptmc.templates import list_templates as registry_list_templates
from promptmc.visualization import ResultParser

try:  # noqa: SIM105
    import openmc

    _openmc: Any = openmc
except ImportError:  # pragma: no cover - the openmc extra is optional
    _openmc = None

logger = logging.getLogger(__name__)

_MODE_MAP: dict[str, ExecutionMode] = {
    "auto": ExecutionMode.AUTO,
    "api": ExecutionMode.API,
    "subprocess": ExecutionMode.SUBPROCESS,
}

_GEOMETRY_DEBUG_TIMEOUT_SECONDS = 300
_MAX_PLOT_PNG_BYTES = 8 * 1024 * 1024
_HISTORY_MAX_ENTRIES = 1000


def check_installation(
    _data: CheckInstallationInput,
) -> OpenMCInstallationStatus:
    """Report the local OpenMC installation status.

    Args:
        _data: Empty input model; this tool takes no parameters.

    Returns:
        The detected installation details, or an ``error`` when OpenMC
        cannot be located.
    """
    try:
        info = OpenMCInstaller().check_installation()
    except PromptMCError as exc:
        return OpenMCInstallationStatus(error=str(exc))
    return OpenMCInstallationStatus(
        version=info.version,
        executable_path=info.executable_path,
        python_available=info.python_available,
        subprocess_available=info.subprocess_available,
    )


def validate_input(data: ValidateInput) -> ValidationResult:
    """Validate an OpenMC XML input file or directory.

    Args:
        data: The path to validate.

    Returns:
        A result describing whether the input is valid. Validation failures
        populate ``errors``; unexpected internal failures also set ``error``.
    """
    try:
        OpenMCValidator().validate_input_file(data.input_path)
    except PromptMCError as exc:
        return ValidationResult(
            is_valid=False, message=str(exc), errors=[str(exc)]
        )
    except Exception as exc:
        logger.exception("openmc_validate failed unexpectedly")
        return ValidationResult(
            is_valid=False,
            message=str(exc),
            errors=[str(exc)],
            error=str(exc),
        )
    return ValidationResult(is_valid=True, message="Input is valid")


def schema_check(data: SchemaCheckInput) -> SchemaValidationResult:
    """Run Pydantic schema validation over OpenMC input files.

    Args:
        data: The path to a directory, ``settings.xml``, or ``materials.xml``.

    Returns:
        The schema validation outcome, or an ``error`` when the path is
        unrecognized or validation fails unexpectedly.
    """
    path = Path(data.input_path)
    try:
        result = _run_schema_validation(path)
    except PromptMCError as exc:
        return SchemaValidationResult(error=str(exc))
    except Exception as exc:
        logger.exception("openmc_schema_check failed unexpectedly")
        return SchemaValidationResult(error=str(exc))
    if result is None:
        return SchemaValidationResult(
            error=(
                "Unrecognized input: expected a directory, settings.xml, "
                "or materials.xml"
            )
        )
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


def _run_schema_validation(path: Path) -> InternalSchemaResult | None:
    """Route a path to the matching schema validator.

    Args:
        path: The directory or XML file to validate.

    Returns:
        The internal validation result, or ``None`` when the path is neither
        a directory nor a recognized OpenMC input filename.
    """
    validator = SchemaValidator()
    if path.is_dir():
        return validator.validate_directory(path)
    if path.name == "materials.xml":
        return validator.validate_materials(path)
    if path.name == "settings.xml":
        return validator.validate_settings(path)
    return None


def render_template(data: TemplateInput) -> TemplateOutput:
    """Render a settings.xml file from a named template.

    Args:
        data: The template name and optional particle/batch overrides.

    Returns:
        The rendered output path and template metadata, or an ``error`` with
        ``template_metadata`` left as ``None`` on failure.
    """
    try:
        template = get_template(data.template)
        output = template.render(
            data.output_path,
            particles=data.particles,
            batches=data.batches,
            inactive=data.inactive,
        )
    except PromptMCError as exc:
        return TemplateOutput(output_path=data.output_path, error=str(exc))
    except Exception as exc:
        logger.exception("openmc_template failed unexpectedly")
        return TemplateOutput(output_path=data.output_path, error=str(exc))
    return TemplateOutput(
        output_path=str(output),
        template_metadata=_template_metadata(template.metadata),
    )


def list_templates(_data: ListTemplatesInput) -> ListTemplatesOutput:
    """List the available configuration templates.

    Args:
        _data: Empty input model; this tool takes no parameters.

    Returns:
        The available template metadata, or an ``error`` on failure.
    """
    try:
        metadata = registry_list_templates()
    except PromptMCError as exc:
        return ListTemplatesOutput(error=str(exc))
    except Exception as exc:
        logger.exception("openmc_list_templates failed unexpectedly")
        return ListTemplatesOutput(error=str(exc))
    return ListTemplatesOutput(
        templates=[_template_metadata(m) for m in metadata]
    )


def run_simulation(data: RunSimulationInput) -> SimulationRunResult:
    """Run an OpenMC simulation and capture the result.

    Args:
        data: The input path, thread count, output path, and execution mode.

    Returns:
        The process outcome, or a failed result carrying ``error`` when the
        run cannot complete.
    """
    mode = _MODE_MAP[data.mode]
    try:
        runner = OpenMCRunner(execution_mode=mode)
        completed = runner.run_simulation(
            data.input_path,
            threads=data.threads,
            output_path=data.output_path,
        )
    except PromptMCError as exc:
        return _run_failure(data, exc)
    except Exception as exc:
        logger.exception("openmc_run failed unexpectedly")
        return _run_failure(data, exc)
    return SimulationRunResult(
        success=completed.returncode == 0,
        return_code=completed.returncode,
        stdout=completed.stdout or "",
        stderr=completed.stderr or "",
        input_path=data.input_path,
        mode=data.mode,
    )


def _run_failure(
    data: RunSimulationInput, exc: Exception
) -> SimulationRunResult:
    """Build a failed simulation result from an exception.

    Args:
        data: The originating run input, echoed back in the result.
        exc: The exception that aborted the run.

    Returns:
        A result with ``success`` false and ``error`` set.
    """
    return SimulationRunResult(
        success=False,
        return_code=-1,
        stderr=str(exc),
        input_path=data.input_path,
        mode=data.mode,
        error=str(exc),
    )


def analyze_results(data: AnalyzeInput) -> AnalysisResult:
    """Parse simulation outputs into a structured summary.

    Args:
        data: The path to the OpenMC output directory.

    Returns:
        The parsed analysis summary, or an ``error`` on failure.
    """
    try:
        parsed = ResultParser().parse_results(data.output_path)
    except PromptMCError as exc:
        return AnalysisResult(error=str(exc))
    except Exception as exc:
        logger.exception("openmc_analyze failed unexpectedly")
        return AnalysisResult(error=str(exc))
    return AnalysisResult(
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
    _data: CrossSectionCheckInput,
) -> CrossSectionCheckResult:
    """Check whether OpenMC cross-section data is configured.

    Args:
        _data: Empty input model; this tool takes no parameters.

    Returns:
        Whether ``OPENMC_CROSS_SECTIONS`` points at an existing file.
    """
    value = os.environ.get("OPENMC_CROSS_SECTIONS")
    if value and Path(value).exists():
        return CrossSectionCheckResult(
            found=True,
            path=value,
            isotopes=_cross_section_isotopes(Path(value)),
        )
    return CrossSectionCheckResult(found=False, path=value or None)


def _cross_section_isotopes(path: Path) -> list[str]:
    """Parse a cross_sections.xml file for available neutron nuclides.

    Args:
        path: Path to the OpenMC ``cross_sections.xml`` index.

    Returns:
        The sorted nuclide names listed for neutron libraries, or an empty
        list when the file cannot be read or parsed.
    """
    try:
        root = defused_parse(str(path)).getroot()
    except (OSError, ParseError):
        logger.exception("failed to parse cross_sections.xml at %s", path)
        return []
    if root is None:
        return []
    return sorted(
        {
            library.get("materials", "")
            for library in root.findall("library")
            if library.get("type") == "neutron" and library.get("materials")
        }
    )


def plot_geometry(data: PlotInput) -> PlotOutput:
    """Render a 2D geometry slice as a base64-encoded PNG.

    Args:
        data: The geometry directory and plot parameters.

    Returns:
        The encoded image, or an ``error`` when OpenMC's Python API is
        unavailable or rendering fails.
    """
    if _openmc is None:
        return PlotOutput(error="OpenMC Python API not available")
    try:  # pragma: no cover - requires the optional openmc dependency
        return _render_plot(_openmc, data)
    except Exception as exc:  # pragma: no cover - requires openmc
        logger.exception("openmc_plot failed unexpectedly")
        return PlotOutput(error=str(exc))


def geometry_debug(data: GeometryDebugInput) -> GeometryDebugResult:
    """Run OpenMC geometry overlap detection via subprocess.

    Args:
        data: The OpenMC input directory to debug and the number of
            particles per generation to drive the overlap check.

    Returns:
        Whether overlaps were detected, the command run, and any matching
        log lines, or an ``error`` when OpenMC is missing or the run fails.
    """
    executable = shutil.which("openmc")
    if executable is None:
        return GeometryDebugResult(error="OpenMC executable not found in PATH")
    command = [
        executable,
        "--geometry-debug",
        "--particles",
        str(data.particles),
    ]
    try:
        completed = subprocess.run(  # nosec B603
            command,
            cwd=data.input_path,
            capture_output=True,
            text=True,
            check=False,
            timeout=_GEOMETRY_DEBUG_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return GeometryDebugResult(error=str(exc))
    combined = f"{completed.stdout}\n{completed.stderr}"
    overlaps = [
        line for line in combined.splitlines() if "overlap" in line.lower()
    ]
    return GeometryDebugResult(
        success=completed.returncode == 0,
        overlaps_found=bool(overlaps),
        command=shlex.join(command),
        overlap_details=overlaps,
    )


def _render_plot(
    openmc: ModuleType, data: PlotInput
) -> PlotOutput:  # pragma: no cover - requires the optional openmc dependency
    """Generate a geometry plot PNG using the OpenMC Python API.

    Args:
        openmc: The imported ``openmc`` module.
        data: Validated plot parameters.

    Returns:
        A PlotOutput with the encoded PNG or an error from :func:`_encode_png`.
    """
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

    return _encode_png(geometry_dir / "promptmc_plot.png")


def _encode_png(image_path: Path) -> PlotOutput:
    """Read a rendered PNG and return it base64-encoded.

    Args:
        image_path: Path to the PNG produced by the OpenMC plotter.

    Returns:
        A PlotOutput with the base64 payload, or an ``error`` when the file
        is missing or exceeds :data:`_MAX_PLOT_PNG_BYTES`.
    """
    if not image_path.is_file():
        return PlotOutput(error=f"Plot image not generated: {image_path}")
    raw = image_path.read_bytes()
    if len(raw) > _MAX_PLOT_PNG_BYTES:
        return PlotOutput(
            image_path=str(image_path),
            error=f"Plot image exceeds {_MAX_PLOT_PNG_BYTES} bytes",
        )
    encoded = base64.b64encode(raw).decode()
    return PlotOutput(image_path=str(image_path), base64_png=encoded)


def _template_metadata(metadata: TemplateMetadata) -> TemplateMetadataResult:
    """Convert internal template metadata to the output schema.

    Args:
        metadata: The internal template metadata record.

    Returns:
        The equivalent output-schema metadata model.
    """
    return TemplateMetadataResult(
        name=metadata.name,
        template_type=metadata.template_type.value,
        description=metadata.description,
        default_particles=metadata.default_particles,
        default_batches=metadata.default_batches,
        default_inactive=metadata.default_inactive,
    )


def _path_str(value: Path | None) -> str | None:
    """Return ``str(value)`` or ``None`` when value is falsy.

    Args:
        value: A path or ``None``.

    Returns:
        The string form of the path, or ``None``.
    """
    return str(value) if value else None


InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=ToolOutput)


@dataclass(frozen=True)
class ToolSpec(Generic[InputT, OutputT]):
    """Registration record binding a tool to its input and output models.

    The generic parameters statically tie ``handler`` to ``input_model`` and
    ``output_model`` at construction, so a handler cannot be registered
    against a mismatched schema.
    """

    name: str
    description: str
    input_model: type[InputT]
    output_model: type[OutputT]
    handler: Callable[[InputT], OutputT]


TOOL_REGISTRY: dict[str, ToolSpec[Any, Any]] = {
    "openmc_check_installation": ToolSpec(
        name="openmc_check_installation",
        description=(
            "Check whether OpenMC is installed and report"
            " its version, executable path, and available"
            " execution modes. Call this first to verify"
            " the environment before running simulations."
        ),
        input_model=CheckInstallationInput,
        output_model=OpenMCInstallationStatus,
        handler=check_installation,
    ),
    "openmc_validate": ToolSpec(
        name="openmc_validate",
        description=(
            "Validate that OpenMC XML input files are"
            " well-formed and parseable. Returns errors"
            " for malformed XML or missing required"
            " files. Does NOT check physics correctness"
            " or geometry overlaps \u2014 use"
            " openmc_schema_check and"
            " openmc_geometry_debug for deeper"
            " validation."
        ),
        input_model=ValidateInput,
        output_model=ValidationResult,
        handler=validate_input,
    ),
    "openmc_schema_check": ToolSpec(
        name="openmc_schema_check",
        description=(
            "Run Pydantic schema validation against"
            " OpenMC input files to catch structural"
            " issues like invalid parameter values,"
            " duplicate IDs, or constraint violations."
            " Accepts a directory or individual"
            " settings.xml / materials.xml. Use after"
            " openmc_validate for deeper checks."
        ),
        input_model=SchemaCheckInput,
        output_model=SchemaValidationResult,
        handler=schema_check,
    ),
    "openmc_template": ToolSpec(
        name="openmc_template",
        description=(
            "Generate a settings.xml file from a named"
            " template (criticality, fixed_source,"
            " shielding, reactor_pin, or depletion)."
            " Optionally override particle count,"
            " batches, and inactive batches. Returns the"
            " output path and template metadata."
        ),
        input_model=TemplateInput,
        output_model=TemplateOutput,
        handler=render_template,
    ),
    "openmc_list_templates": ToolSpec(
        name="openmc_list_templates",
        description=(
            "List all available configuration templates"
            " with their names, types, descriptions, and"
            " default parameter values. Use this to"
            " discover what templates exist before"
            " calling openmc_template."
        ),
        input_model=ListTemplatesInput,
        output_model=ListTemplatesOutput,
        handler=list_templates,
    ),
    "openmc_run": ToolSpec(
        name="openmc_run",
        description=(
            "Run an OpenMC simulation. Requires valid"
            " geometry.xml, materials.xml, and"
            " settings.xml in the input directory, plus"
            " configured cross-section data. Returns"
            " stdout, stderr, and the exit code. Use"
            " openmc_validate and openmc_schema_check"
            " first."
        ),
        input_model=RunSimulationInput,
        output_model=SimulationRunResult,
        handler=run_simulation,
    ),
    "openmc_analyze": ToolSpec(
        name="openmc_analyze",
        description=(
            "Parse OpenMC simulation outputs (statepoint"
            " and summary HDF5 files) and return"
            " structured results including k-effective,"
            " batch count, particle count, and runtime."
            " Call this after a successful openmc_run."
        ),
        input_model=AnalyzeInput,
        output_model=AnalysisResult,
        handler=analyze_results,
    ),
    "openmc_check_cross_sections": ToolSpec(
        name="openmc_check_cross_sections",
        description=(
            "Check whether the OPENMC_CROSS_SECTIONS"
            " environment variable is set and points to"
            " an existing cross_sections.xml file. Lists"
            " available isotopes if found. Call this"
            " before openmc_run to diagnose missing"
            " data."
        ),
        input_model=CrossSectionCheckInput,
        output_model=CrossSectionCheckResult,
        handler=check_cross_sections,
    ),
    "openmc_plot": ToolSpec(
        name="openmc_plot",
        description=(
            "Generate a 2D geometry slice plot as a"
            " base64-encoded PNG image. Requires the"
            " OpenMC Python API to be installed. Specify"
            " the slice basis (xy, xz, yz), origin,"
            " width, resolution, and coloring. Use for"
            " visual geometry sanity checks."
        ),
        input_model=PlotInput,
        output_model=PlotOutput,
        handler=plot_geometry,
    ),
    "openmc_geometry_debug": ToolSpec(
        name="openmc_geometry_debug",
        description=(
            "Run OpenMC geometry overlap detection via"
            " the --geometry-debug flag. Reports whether"
            " overlapping cells were found and includes"
            " the relevant log lines. Use this to catch"
            " geometry errors that schema validation"
            " cannot detect."
        ),
        input_model=GeometryDebugInput,
        output_model=GeometryDebugResult,
        handler=geometry_debug,
    ),
}


@dataclass
class HistoryEntry:
    """A single recorded tool invocation in the MCP session.

    Attributes:
        success: ``True`` when the tool returned without an unexpected
            internal error (``output.error is None``). A domain failure such
            as an invalid input still counts as a successful invocation.
    """

    tool: str
    timestamp: str
    input_summary: str
    success: bool


_SESSION_HISTORY: deque[HistoryEntry] = deque(maxlen=_HISTORY_MAX_ENTRIES)


def record_history(tool: str, arguments: dict[str, Any], success: bool) -> None:
    """Append a tool invocation to the bounded session history.

    Args:
        tool: The dispatched tool name.
        arguments: The raw argument mapping, truncated when serialized.
        success: Whether the tool returned without an internal error; see
            :class:`HistoryEntry`.
    """
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
    """Return a snapshot copy of the current session history.

    Returns:
        The recorded entries, oldest first.
    """
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
        MCPError: If the tool name is not registered.
    """
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        raise MCPError(f"Unknown tool: {name}")
    try:
        data = spec.input_model.model_validate(arguments)
    except PydanticValidationError as exc:
        error_msg = f"Invalid arguments for {name}: {exc}"
        record_history(name, arguments, success=False)
        return {"error": error_msg}
    output: ToolOutput = spec.handler(data)
    record_history(name, arguments, success=output.error is None)
    return output.model_dump(mode="json")
