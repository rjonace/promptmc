"""Pydantic input/output schemas for PromptMC MCP tools.

These models are the external boundary contracts for every MCP tool. Each
tool consumes one input model and produces one output model. Every output
model inherits :class:`ToolOutput`, which carries an optional ``error``
field so failures are surfaced as structured data rather than propagating
exceptions to the MCP layer.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ExecutionModeName = Literal["auto", "api", "subprocess"]
PlotBasis = Literal["xy", "xz", "yz"]
PlotColorBy = Literal["material", "cell"]
TemplateName = Literal[
    "criticality", "fixed_source", "shielding", "reactor_pin", "depletion"
]


class ToolOutput(BaseModel):
    """Base class for every MCP tool output model.

    Attributes:
        error: Human-readable message set when the tool hit an unexpected
            internal failure; ``None`` on a normal (non-crashing) return.
    """

    error: str | None = None


class CheckInstallationInput(BaseModel):
    """Input for openmc_check_installation tool."""


class OpenMCInstallationStatus(ToolOutput):
    """Output for openmc_check_installation tool."""

    version: str = ""
    executable_path: str = ""
    python_available: bool = False
    subprocess_available: bool = False


class ValidateInput(BaseModel):
    """Input for openmc_validate tool."""

    input_path: str = Field(
        description="Path to OpenMC input file or directory"
    )


class ValidationResult(ToolOutput):
    """Output for openmc_validate tool."""

    is_valid: bool = False
    message: str = ""
    errors: list[str] = Field(default_factory=list)


class SchemaCheckInput(BaseModel):
    """Input for openmc_schema_check tool."""

    input_path: str = Field(
        description="Path to settings.xml, materials.xml, or a directory"
    )


class SchemaIssueResult(BaseModel):
    """A single schema validation issue."""

    severity: str
    field: str
    message: str
    file_path: str | None = None


class SchemaValidationResult(ToolOutput):
    """Output for openmc_schema_check tool."""

    is_valid: bool = False
    issues: list[SchemaIssueResult] = Field(default_factory=list)
    error_count: int = 0
    warning_count: int = 0


class TemplateInput(BaseModel):
    """Input for openmc_template tool."""

    template: TemplateName = Field(description="Template type to render")
    output_path: str = Field(default="settings.xml")
    particles: int | None = None
    batches: int | None = None
    inactive: int | None = None


class TemplateMetadataResult(BaseModel):
    """Template metadata in tool output."""

    name: str
    template_type: str
    description: str
    default_particles: int
    default_batches: int
    default_inactive: int


class TemplateOutput(ToolOutput):
    """Output for openmc_template tool."""

    output_path: str = ""
    template_metadata: TemplateMetadataResult | None = None


class ListTemplatesInput(BaseModel):
    """Input for openmc_list_templates tool."""


class ListTemplatesOutput(ToolOutput):
    """Output for openmc_list_templates tool."""

    templates: list[TemplateMetadataResult] = Field(default_factory=list)


class RunSimulationInput(BaseModel):
    """Input for openmc_run tool."""

    input_path: str = Field(
        description="Path to OpenMC input file or directory"
    )
    threads: int = Field(default=1, ge=1)
    output_path: str | None = None
    mode: ExecutionModeName = Field(
        default="auto",
        description="Execution mode: auto, api, or subprocess",
    )


class SimulationRunResult(ToolOutput):
    """Output for openmc_run tool."""

    success: bool = False
    return_code: int = -1
    stdout: str = ""
    stderr: str = ""
    input_path: str = ""
    mode: str = ""


class AnalyzeInput(BaseModel):
    """Input for openmc_analyze tool."""

    output_path: str = Field(description="Path to OpenMC output directory")


class AnalysisResult(ToolOutput):
    """Output for openmc_analyze tool."""

    statepoint_path: str | None = None
    summary_path: str | None = None
    tallies_path: str | None = None
    k_effective: float | None = None
    k_effective_std: float | None = None
    n_batches: int = 0
    n_particles: int = 0
    runtime_seconds: float = 0.0
    tallies_present: bool = False


class CrossSectionCheckInput(BaseModel):
    """Input for openmc_check_cross_sections tool."""


class CrossSectionCheckResult(ToolOutput):
    """Output for openmc_check_cross_sections tool."""

    found: bool = False
    path: str | None = None


class PlotInput(BaseModel):
    """Input for openmc_plot tool."""

    geometry_xml_path: str = Field(
        description="Path to directory containing geometry.xml"
    )
    basis: PlotBasis = Field(default="xy", description="Plot slice basis")
    origin: tuple[float, float, float] = Field(default=(0.0, 0.0, 0.0))
    width: tuple[float, float] = Field(default=(10.0, 10.0))
    pixels: tuple[int, int] = Field(default=(400, 400))
    color_by: PlotColorBy = Field(
        default="material", description="Color cells by material or cell"
    )
    show_overlaps: bool = False


class PlotOutput(ToolOutput):
    """Output for openmc_plot tool."""

    image_path: str = ""
    base64_png: str = ""


class GeometryDebugInput(BaseModel):
    """Input for openmc_geometry_debug tool."""

    input_path: str = Field(description="Path to OpenMC input directory")


class GeometryDebugResult(ToolOutput):
    """Output for openmc_geometry_debug tool."""

    success: bool = False
    overlaps_found: bool = False
    command: str = ""
    overlap_details: list[str] = Field(default_factory=list)
