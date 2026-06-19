"""Pytest configuration and custom markers setup."""

from __future__ import annotations

import os
import shutil

import pytest

try:
    import openmc  # type: ignore

    OPENMC_AVAILABLE = hasattr(openmc, "Geometry")
except ImportError:
    OPENMC_AVAILABLE = False

OPENMC_DATA_AVAILABLE = OPENMC_AVAILABLE and bool(
    os.environ.get("OPENMC_CROSS_SECTIONS")
)

# The executable (subprocess) path is independent of the Python API: it only
# needs the ``openmc`` binary on PATH, plus cross-section data for a real run.
OPENMC_EXEC_AVAILABLE = shutil.which("openmc") is not None
OPENMC_EXEC_DATA_AVAILABLE = OPENMC_EXEC_AVAILABLE and bool(
    os.environ.get("OPENMC_CROSS_SECTIONS")
)


def pytest_runtest_setup(item: pytest.Item) -> None:
    """Skip tests marked requires_openmc or requires_openmc_data if dependencies are missing."""
    if any(item.iter_markers(name="requires_openmc")) and not OPENMC_AVAILABLE:
        pytest.skip("Test requires openmc to be installed.")
    if (
        any(item.iter_markers(name="requires_openmc_data"))
        and not OPENMC_DATA_AVAILABLE
    ):
        pytest.skip(
            "Test requires openmc and OPENMC_CROSS_SECTIONS to be configured."
        )
    if (
        any(item.iter_markers(name="requires_openmc_exec"))
        and not OPENMC_EXEC_DATA_AVAILABLE
    ):
        pytest.skip(
            "Test requires the openmc executable on PATH and "
            "OPENMC_CROSS_SECTIONS to be configured."
        )
