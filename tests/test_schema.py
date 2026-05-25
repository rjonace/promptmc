"""Tests for schema validation module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from promptmc.schema import (
    GeometrySchema,
    MaterialsSchema,
    RunMode,
    SchemaSeverity,
    SchemaValidator,
    SettingsSchema,
    format_validation_report,
)
from pydantic import ValidationError


def test_settings_schema_defaults():
    """Test SettingsSchema with default values."""
    settings = SettingsSchema()
    assert settings.run_mode == RunMode.EIGENVALUE
    assert settings.batches == 10
    assert settings.inactive == 5
    assert settings.particles == 10000


def test_settings_schema_validation_inactive_lt_batches():
    """Test that inactive must be less than batches."""
    with pytest.raises(ValidationError):
        SettingsSchema(batches=5, inactive=10)


def test_settings_schema_negative_particles():
    """Test that particles must be positive."""
    with pytest.raises(ValidationError):
        SettingsSchema(particles=-1)


def test_settings_schema_excessive_particles():
    """Test particles upper bound."""
    with pytest.raises(ValidationError):
        SettingsSchema(particles=10_000_000_000)


def test_materials_schema_unique_ids():
    """Test that material IDs must be unique."""
    from promptmc.schema import MaterialSchema

    with pytest.raises(ValidationError):
        MaterialsSchema(
            materials=[
                MaterialSchema(id=1),
                MaterialSchema(id=1),
            ]
        )


def test_geometry_schema_unique_ids():
    """Test that cell IDs must be unique."""
    from promptmc.schema import CellSchema

    with pytest.raises(ValidationError):
        GeometrySchema(
            cells=[
                CellSchema(id=1),
                CellSchema(id=1),
            ]
        )


def test_validator_settings_valid():
    """Test validating a valid settings.xml."""
    validator = SchemaValidator()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as f:
        f.write(
            "<settings>"
            "<run_mode>eigenvalue</run_mode>"
            "<batches>100</batches>"
            "<inactive>10</inactive>"
            "<particles>10000</particles>"
            "</settings>"
        )
        temp_path = Path(f.name)

    try:
        result = validator.validate_settings(temp_path)
        assert result.is_valid
        assert len(result.errors) == 0
    finally:
        temp_path.unlink()


def test_validator_settings_invalid_inactive():
    """Test validating settings with inactive >= batches."""
    validator = SchemaValidator()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as f:
        f.write(
            "<settings>"
            "<batches>10</batches>"
            "<inactive>15</inactive>"
            "<particles>10000</particles>"
            "</settings>"
        )
        temp_path = Path(f.name)

    try:
        result = validator.validate_settings(temp_path)
        assert not result.is_valid
        assert len(result.errors) > 0
    finally:
        temp_path.unlink()


def test_validator_invalid_xml():
    """Test validating malformed XML."""
    validator = SchemaValidator()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as f:
        f.write("<settings><run_mode>")  # malformed
        temp_path = Path(f.name)

    try:
        result = validator.validate_settings(temp_path)
        assert not result.is_valid
        assert any("Invalid XML" in e.message for e in result.errors)
    finally:
        temp_path.unlink()


def test_validator_materials_valid():
    """Test validating valid materials.xml."""
    validator = SchemaValidator()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as f:
        f.write(
            "<materials>"
            '<material id="1" name="water">'
            '<density value="1.0" units="g/cm3"/>'
            '<nuclide name="H-1"/>'
            '<nuclide name="O-16"/>'
            "</material>"
            "</materials>"
        )
        temp_path = Path(f.name)

    try:
        result = validator.validate_materials(temp_path)
        assert result.is_valid
    finally:
        temp_path.unlink()


def test_validator_geometry_valid():
    """Test validating valid geometry.xml."""
    validator = SchemaValidator()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False, encoding="utf-8"
    ) as f:
        f.write(
            "<geometry>"
            '<cell id="1" name="core" material="1"/>'
            '<cell id="2" name="reflector" material="2"/>'
            "</geometry>"
        )
        temp_path = Path(f.name)

    try:
        result = validator.validate_geometry(temp_path)
        assert result.is_valid
    finally:
        temp_path.unlink()


def test_validator_directory_missing_files():
    """Test directory validation with missing required files."""
    validator = SchemaValidator()

    with tempfile.TemporaryDirectory() as temp_dir:
        result = validator.validate_directory(temp_dir)
        assert not result.is_valid
        assert any("missing" in e.message.lower() for e in result.errors)


def test_format_validation_report():
    """Test formatting a validation report."""
    from promptmc.schema import SchemaIssue, SchemaValidationResult

    result = SchemaValidationResult(
        is_valid=False,
        issues=[
            SchemaIssue(
                severity=SchemaSeverity.ERROR,
                field="batches",
                message="Must be positive",
            ),
        ],
    )
    report = format_validation_report(result)
    assert "Schema Validation Report" in report
    assert "FAILED" in report
    assert "batches" in report
