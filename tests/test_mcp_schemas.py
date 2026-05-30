"""Tests for PromptMC MCP Pydantic schemas."""

from __future__ import annotations

import pytest
from promptmc.mcp.schemas import (
    AnalysisResult,
    GeometryDebugInput,
    PlotInput,
    RunSimulationInput,
    SchemaValidationResult,
    TemplateInput,
    ValidateInput,
)
from pydantic import ValidationError


def test_validate_input_requires_path():
    with pytest.raises(ValidationError):
        ValidateInput()


def test_validate_input_accepts_path():
    inp = ValidateInput(input_path="/tmp/settings.xml")
    assert inp.input_path == "/tmp/settings.xml"


def test_run_simulation_defaults():
    inp = RunSimulationInput(input_path="/tmp/case")
    assert inp.threads == 1
    assert inp.mode == "auto"
    assert inp.output_path is None


def test_run_simulation_rejects_zero_threads():
    with pytest.raises(ValidationError):
        RunSimulationInput(input_path="/tmp/case", threads=0)


def test_geometry_debug_requires_path():
    with pytest.raises(ValidationError):
        GeometryDebugInput()


def test_geometry_debug_particles_default():
    inp = GeometryDebugInput(input_path="/tmp/case")
    assert inp.particles == 100


def test_geometry_debug_rejects_zero_particles():
    with pytest.raises(ValidationError):
        GeometryDebugInput(input_path="/tmp/case", particles=0)


def test_run_simulation_rejects_invalid_mode():
    with pytest.raises(ValidationError):
        RunSimulationInput(input_path="/tmp/case", mode="gpu")


def test_plot_rejects_invalid_basis():
    with pytest.raises(ValidationError):
        PlotInput(geometry_xml_path="/tmp/case", basis="diagonal")


def test_template_rejects_unknown_template():
    with pytest.raises(ValidationError):
        TemplateInput(template="bogus")


def test_template_input_defaults():
    inp = TemplateInput(template="criticality")
    assert inp.output_path == "settings.xml"
    assert inp.particles is None


def test_plot_input_defaults():
    inp = PlotInput(geometry_xml_path="/tmp/case")
    assert inp.basis == "xy"
    assert inp.origin == (0.0, 0.0, 0.0)
    assert inp.width == (10.0, 10.0)
    assert inp.pixels == (400, 400)
    assert inp.color_by == "material"
    assert inp.show_overlaps is False


def test_schema_validation_result_defaults():
    result = SchemaValidationResult(is_valid=True)
    assert result.issues == []
    assert result.error_count == 0
    assert result.warning_count == 0
    assert result.error is None


def test_analysis_result_defaults():
    result = AnalysisResult()
    assert result.k_effective is None
    assert result.n_batches == 0
    assert result.tallies_present is False
    assert result.error is None
