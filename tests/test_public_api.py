"""Tests for the top-level ``promptmc`` public API surface."""

from __future__ import annotations

import promptmc


def test_validation_and_geometry_exports_are_public():
    expected = {
        "Cell",
        "GeometryModel",
        "Material",
        "MaterialsModel",
        "NuclideSpec",
        "Region",
        "SchemaValidationResult",
        "SchemaValidator",
        "SettingsSchema",
        "Surface",
    }
    assert expected.issubset(set(promptmc.__all__))
    for name in expected:
        assert getattr(promptmc, name) is not None


def test_runner_infrastructure_still_exported():
    for name in (
        "BatchRunner",
        "ExecutionMode",
        "OpenMCInstaller",
        "OpenMCRunner",
        "OpenMCValidator",
        "ParallelConfig",
        "ParallelMode",
    ):
        assert name in promptmc.__all__
        assert getattr(promptmc, name) is not None
