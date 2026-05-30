"""Tests for PromptMC MCP tool functions, dispatch, and history."""

from __future__ import annotations

import base64
import subprocess
from subprocess import CompletedProcess
from unittest.mock import MagicMock, patch

import pytest
from promptmc.errors import (
    ConfigurationError,
    MCPError,
    OpenMCExecutionError,
    OpenMCNotFoundError,
    OpenMCValidationError,
)
from promptmc.mcp import tools
from promptmc.mcp.schemas import (
    AnalyzeInput,
    CheckInstallationInput,
    CrossSectionCheckInput,
    GeometryDebugInput,
    ListTemplatesInput,
    OpenMCInstallationStatus,
    PlotInput,
    RunSimulationInput,
    SchemaCheckInput,
    TemplateInput,
    ValidateInput,
    ValidationResult,
)
from promptmc.openmc_integration import ExecutionMode, OpenMCInfo
from promptmc.schema import (
    SchemaIssue,
    SchemaSeverity,
)
from promptmc.schema import (
    SchemaValidationResult as DataclassSchemaResult,
)
from promptmc.templates import TemplateMetadata, TemplateType
from promptmc.visualization import SimulationResult as DataclassSimResult


@pytest.fixture(autouse=True)
def _clear_history():
    tools.clear_session_history()
    yield
    tools.clear_session_history()


@patch("promptmc.mcp.tools.OpenMCInstaller")
def test_check_installation_success(mock_cls):
    mock_cls.return_value.check_installation.return_value = OpenMCInfo(
        version="0.15.1",
        executable_path="/usr/bin/openmc",
        python_available=True,
        subprocess_available=True,
    )
    result = tools.check_installation(CheckInstallationInput())
    assert isinstance(result, OpenMCInstallationStatus)
    assert result.version == "0.15.1"
    assert result.python_available is True
    assert result.error is None


@patch("promptmc.mcp.tools.OpenMCInstaller")
def test_check_installation_not_found(mock_cls):
    mock_cls.return_value.check_installation.side_effect = OpenMCNotFoundError(
        "missing"
    )
    result = tools.check_installation(CheckInstallationInput())
    assert result.version == ""
    assert result.python_available is False
    assert result.error is not None


@patch("promptmc.mcp.tools.OpenMCValidator")
def test_validate_input_success(mock_cls):
    mock_cls.return_value.validate_input_file.return_value = True
    result = tools.validate_input(ValidateInput(input_path="/tmp/s.xml"))
    assert isinstance(result, ValidationResult)
    assert result.is_valid is True
    assert result.error is None


@patch("promptmc.mcp.tools.OpenMCValidator")
def test_validate_input_invalid(mock_cls):
    mock_cls.return_value.validate_input_file.side_effect = (
        OpenMCValidationError("bad xml")
    )
    result = tools.validate_input(ValidateInput(input_path="/tmp/s.xml"))
    assert result.is_valid is False
    assert result.errors == ["bad xml"]
    assert result.error is None


@patch("promptmc.mcp.tools.OpenMCValidator")
def test_validate_input_unexpected_error(mock_cls):
    mock_cls.return_value.validate_input_file.side_effect = RuntimeError("boom")
    result = tools.validate_input(ValidateInput(input_path="/tmp/s.xml"))
    assert result.is_valid is False
    assert result.error == "boom"


@patch("promptmc.mcp.tools.SchemaValidator")
def test_schema_check_directory(mock_cls, tmp_path):
    mock_cls.return_value.validate_directory.return_value = (
        DataclassSchemaResult(
            is_valid=False,
            issues=[
                SchemaIssue(
                    severity=SchemaSeverity.ERROR,
                    field="batches",
                    message="too small",
                ),
                SchemaIssue(
                    severity=SchemaSeverity.WARNING,
                    field="seed",
                    message="missing",
                ),
            ],
        )
    )
    result = tools.schema_check(SchemaCheckInput(input_path=str(tmp_path)))
    assert result.is_valid is False
    assert result.error_count == 1
    assert result.warning_count == 1
    assert len(result.issues) == 2
    mock_cls.return_value.validate_directory.assert_called_once()


@patch("promptmc.mcp.tools.SchemaValidator")
def test_schema_check_settings_file(mock_cls, tmp_path):
    settings = tmp_path / "settings.xml"
    settings.write_text("<settings/>")
    mock_cls.return_value.validate_settings.return_value = (
        DataclassSchemaResult(is_valid=True, issues=[])
    )
    result = tools.schema_check(SchemaCheckInput(input_path=str(settings)))
    assert result.is_valid is True
    mock_cls.return_value.validate_settings.assert_called_once()


@patch("promptmc.mcp.tools.SchemaValidator")
def test_schema_check_materials_file(mock_cls, tmp_path):
    materials = tmp_path / "materials.xml"
    materials.write_text("<materials/>")
    mock_cls.return_value.validate_materials.return_value = (
        DataclassSchemaResult(is_valid=True, issues=[])
    )
    result = tools.schema_check(SchemaCheckInput(input_path=str(materials)))
    assert result.is_valid is True
    mock_cls.return_value.validate_materials.assert_called_once()


@patch("promptmc.mcp.tools.SchemaValidator")
def test_schema_check_error(mock_cls, tmp_path):
    mock_cls.return_value.validate_directory.side_effect = OSError("nope")
    result = tools.schema_check(SchemaCheckInput(input_path=str(tmp_path)))
    assert result.is_valid is False
    assert result.error == "nope"


@patch("promptmc.mcp.tools.SchemaValidator")
def test_schema_check_promptmc_error(mock_cls, tmp_path):
    mock_cls.return_value.validate_directory.side_effect = ConfigurationError(
        "bad schema"
    )
    result = tools.schema_check(SchemaCheckInput(input_path=str(tmp_path)))
    assert result.is_valid is False
    assert result.error == "bad schema"


def test_schema_check_unrecognized_file(tmp_path):
    geometry = tmp_path / "geometry.xml"
    geometry.write_text("<geometry/>")
    result = tools.schema_check(SchemaCheckInput(input_path=str(geometry)))
    assert result.is_valid is False
    assert result.error is not None
    assert "Unrecognized" in result.error


def _fake_metadata():
    return TemplateMetadata(
        name="Criticality",
        template_type=TemplateType.CRITICALITY,
        description="desc",
        default_particles=10000,
        default_batches=100,
        default_inactive=10,
    )


@patch("promptmc.mcp.tools.get_template")
def test_render_template_success(mock_get, tmp_path):
    out_file = tmp_path / "settings.xml"
    template = MagicMock()
    template.render.return_value = out_file
    template.metadata = _fake_metadata()
    mock_get.return_value = template
    result = tools.render_template(
        TemplateInput(template="criticality", output_path=str(out_file))
    )
    assert result.output_path == str(out_file)
    assert result.template_metadata.template_type == "criticality"
    assert result.error is None


@patch("promptmc.mcp.tools.get_template")
def test_render_template_error(mock_get):
    mock_get.side_effect = ConfigurationError("render failed")
    result = tools.render_template(TemplateInput(template="criticality"))
    assert result.error == "render failed"
    assert result.template_metadata is None


@patch("promptmc.mcp.tools.get_template")
def test_render_template_unexpected_error(mock_get):
    template = MagicMock()
    template.render.side_effect = RuntimeError("disk full")
    mock_get.return_value = template
    result = tools.render_template(TemplateInput(template="criticality"))
    assert result.error == "disk full"
    assert result.template_metadata is None


@patch("promptmc.mcp.tools.registry_list_templates")
def test_list_templates_success(mock_list):
    mock_list.return_value = [_fake_metadata()]
    result = tools.list_templates(ListTemplatesInput())
    assert len(result.templates) == 1
    assert result.templates[0].name == "Criticality"


@patch("promptmc.mcp.tools.registry_list_templates")
def test_list_templates_error(mock_list):
    mock_list.side_effect = RuntimeError("boom")
    result = tools.list_templates(ListTemplatesInput())
    assert result.error == "boom"


@patch("promptmc.mcp.tools.registry_list_templates")
def test_list_templates_promptmc_error(mock_list):
    mock_list.side_effect = ConfigurationError("bad registry")
    result = tools.list_templates(ListTemplatesInput())
    assert result.error == "bad registry"


@patch("promptmc.mcp.tools.OpenMCRunner")
def test_run_simulation_success(mock_cls):
    mock_cls.return_value.run_simulation.return_value = CompletedProcess(
        args=["openmc"], returncode=0, stdout="done", stderr=""
    )
    result = tools.run_simulation(
        RunSimulationInput(input_path="/tmp/case", mode="api", threads=4)
    )
    assert result.success is True
    assert result.return_code == 0
    assert result.stdout == "done"
    mock_cls.assert_called_once_with(execution_mode=ExecutionMode.API)


@patch("promptmc.mcp.tools.OpenMCRunner")
def test_run_simulation_failure(mock_cls):
    mock_cls.return_value.run_simulation.side_effect = OpenMCExecutionError(
        "crash"
    )
    result = tools.run_simulation(RunSimulationInput(input_path="/tmp/case"))
    assert result.success is False
    assert result.return_code == -1
    assert result.error == "crash"


@patch("promptmc.mcp.tools.OpenMCRunner")
def test_run_simulation_unexpected_error(mock_cls):
    mock_cls.return_value.run_simulation.side_effect = RuntimeError("kaboom")
    result = tools.run_simulation(RunSimulationInput(input_path="/tmp/case"))
    assert result.success is False
    assert result.error == "kaboom"


@patch("promptmc.mcp.tools.ResultParser")
def test_analyze_results_success(mock_cls):
    mock_cls.return_value.parse_results.return_value = DataclassSimResult(
        k_effective=1.0,
        k_effective_std=0.001,
        n_batches=100,
        n_particles=10000,
        tallies={"flux": 1},
    )
    result = tools.analyze_results(AnalyzeInput(output_path="/tmp/out"))
    assert result.k_effective == 1.0
    assert result.n_batches == 100
    assert result.tallies_present is True
    assert result.statepoint_path is None


@patch("promptmc.mcp.tools.ResultParser")
def test_analyze_results_error(mock_cls):
    mock_cls.return_value.parse_results.side_effect = OSError("no dir")
    result = tools.analyze_results(AnalyzeInput(output_path="/tmp/out"))
    assert result.error == "no dir"


@patch("promptmc.mcp.tools.ResultParser")
def test_analyze_results_promptmc_error(mock_cls):
    mock_cls.return_value.parse_results.side_effect = ConfigurationError("nope")
    result = tools.analyze_results(AnalyzeInput(output_path="/tmp/out"))
    assert result.error == "nope"


def test_check_cross_sections_found(tmp_path, monkeypatch):
    xs = tmp_path / "cross_sections.xml"
    xs.write_text("<cross_sections/>")
    monkeypatch.setenv("OPENMC_CROSS_SECTIONS", str(xs))
    result = tools.check_cross_sections(CrossSectionCheckInput())
    assert result.found is True
    assert result.path == str(xs)


def test_check_cross_sections_missing_file(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENMC_CROSS_SECTIONS", str(tmp_path / "missing.xml"))
    result = tools.check_cross_sections(CrossSectionCheckInput())
    assert result.found is False
    assert result.path is not None


def test_check_cross_sections_unset(monkeypatch):
    monkeypatch.delenv("OPENMC_CROSS_SECTIONS", raising=False)
    result = tools.check_cross_sections(CrossSectionCheckInput())
    assert result.found is False
    assert result.path is None


def test_plot_geometry_openmc_missing():
    result = tools.plot_geometry(PlotInput(geometry_xml_path="/tmp/case"))
    assert result.base64_png == ""
    assert result.error is not None
    assert "OpenMC" in result.error


@patch("promptmc.mcp.tools.shutil.which", return_value=None)
def test_geometry_debug_no_executable(mock_which):
    result = tools.geometry_debug(GeometryDebugInput(input_path="/tmp/case"))
    assert result.success is False
    assert result.error is not None


@patch("promptmc.mcp.tools.subprocess.run")
@patch("promptmc.mcp.tools.shutil.which", return_value="/usr/bin/openmc")
def test_geometry_debug_overlaps(mock_which, mock_run):
    mock_run.return_value = CompletedProcess(
        args=["openmc"],
        returncode=0,
        stdout="WARNING: Overlap found at cell 3",
        stderr="",
    )
    result = tools.geometry_debug(GeometryDebugInput(input_path="/tmp/case"))
    assert result.success is True
    assert result.overlaps_found is True
    assert result.overlap_details


@patch("promptmc.mcp.tools.subprocess.run")
@patch("promptmc.mcp.tools.shutil.which", return_value="/usr/bin/openmc")
def test_geometry_debug_clean(mock_which, mock_run):
    mock_run.return_value = CompletedProcess(
        args=["openmc"], returncode=0, stdout="no issues", stderr=""
    )
    result = tools.geometry_debug(GeometryDebugInput(input_path="/tmp/case"))
    assert result.success is True
    assert result.overlaps_found is False


@patch("promptmc.mcp.tools.subprocess.run", side_effect=OSError("boom"))
@patch("promptmc.mcp.tools.shutil.which", return_value="/usr/bin/openmc")
def test_geometry_debug_os_error(mock_which, mock_run):
    result = tools.geometry_debug(GeometryDebugInput(input_path="/tmp/case"))
    assert result.success is False
    assert result.error == "boom"


@patch(
    "promptmc.mcp.tools.subprocess.run",
    side_effect=subprocess.TimeoutExpired(cmd="openmc", timeout=300),
)
@patch("promptmc.mcp.tools.shutil.which", return_value="/usr/bin/openmc")
def test_geometry_debug_timeout(mock_which, mock_run):
    result = tools.geometry_debug(GeometryDebugInput(input_path="/tmp/case"))
    assert result.success is False
    assert result.error is not None


@patch("promptmc.mcp.tools.subprocess.run")
@patch("promptmc.mcp.tools.shutil.which", return_value="/usr/bin/openmc")
def test_geometry_debug_records_command(mock_which, mock_run):
    mock_run.return_value = CompletedProcess(
        args=["openmc"], returncode=0, stdout="ok", stderr=""
    )
    result = tools.geometry_debug(GeometryDebugInput(input_path="/tmp/case"))
    assert result.command == "/usr/bin/openmc --geometry-debug"
    assert result.error is None


def test_encode_png_success(tmp_path):
    image = tmp_path / "plot.png"
    image.write_bytes(b"fake-png-bytes")
    result = tools._encode_png(image)
    assert result.error is None
    assert base64.b64decode(result.base64_png) == b"fake-png-bytes"
    assert result.image_path == str(image)


def test_encode_png_missing(tmp_path):
    result = tools._encode_png(tmp_path / "absent.png")
    assert result.base64_png == ""
    assert result.error is not None


def test_encode_png_too_large(tmp_path, monkeypatch):
    monkeypatch.setattr(tools, "_MAX_PLOT_PNG_BYTES", 4)
    image = tmp_path / "plot.png"
    image.write_bytes(b"too-many-bytes")
    result = tools._encode_png(image)
    assert result.base64_png == ""
    assert result.error is not None
    assert "exceeds" in result.error


def test_plot_geometry_missing_api(monkeypatch):
    monkeypatch.setattr(tools, "_openmc", None)
    result = tools.plot_geometry(PlotInput(geometry_xml_path="/tmp/case"))
    assert result.base64_png == ""
    assert result.error is not None


def test_registry_has_ten_tools():
    assert len(tools.TOOL_REGISTRY) == 10
    expected = {
        "openmc_check_installation",
        "openmc_validate",
        "openmc_schema_check",
        "openmc_template",
        "openmc_list_templates",
        "openmc_run",
        "openmc_analyze",
        "openmc_check_cross_sections",
        "openmc_plot",
        "openmc_geometry_debug",
    }
    assert set(tools.TOOL_REGISTRY) == expected


def test_dispatch_records_history(monkeypatch):
    monkeypatch.delenv("OPENMC_CROSS_SECTIONS", raising=False)
    result = tools.dispatch("openmc_check_cross_sections", {})
    assert result["found"] is False
    history = tools.get_session_history()
    assert len(history) == 1
    assert history[0].tool == "openmc_check_cross_sections"
    assert history[0].success is True


@patch("promptmc.mcp.tools.shutil.which", return_value=None)
def test_dispatch_records_failure(mock_which):
    tools.dispatch("openmc_geometry_debug", {"input_path": "/tmp/case"})
    history = tools.get_session_history()
    assert history[-1].success is False


def test_dispatch_unknown_tool():
    with pytest.raises(MCPError):
        tools.dispatch("openmc_nonexistent", {})


def test_history_is_bounded():
    tools.clear_session_history()
    for _ in range(tools._HISTORY_MAX_ENTRIES + 50):
        tools.record_history("openmc_validate", {}, True)
    assert len(tools.get_session_history()) == tools._HISTORY_MAX_ENTRIES
