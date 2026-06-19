"""End-to-end execution against the real ``openmc`` executable (subprocess mode).

This is the deployment the README emphasises: PromptMC driving OpenMC through the
binary, with no Python bindings installed. It is gated by the
``requires_openmc_exec`` marker (see conftest.py), so it only runs when the
``openmc`` executable is on PATH and ``OPENMC_CROSS_SECTIONS`` is configured;
otherwise it skips.
"""

from __future__ import annotations

from importlib.resources import files
from pathlib import Path

import pytest
from promptmc.openmc_integration import ExecutionMode, OpenMCRunner
from promptmc.visualization import ResultParser

# The bundled UO2 sphere is a deterministic 500-particle / 20-batch eigenvalue
# smoke fixture. OpenMC's fixed default RNG seed makes k reproducible, so the
# tolerance below brackets the reference (~0.437) with margin for OpenMC
# version / cross-section data differences.
EXPECTED_K = 0.43707
K_TOLERANCE = 0.05

REQUIRED_INPUTS = ("geometry.xml", "materials.xml", "settings.xml")


@pytest.mark.requires_openmc_exec
def test_subprocess_run_bundled_example(tmp_path: Path) -> None:
    """Run the bundled example via the executable, then parse k-eff from output."""
    example = files("promptmc") / "examples" / "uo2_criticality"
    for name in REQUIRED_INPUTS:
        (tmp_path / name).write_text((example / name).read_text())

    runner = OpenMCRunner(execution_mode=ExecutionMode.SUBPROCESS)
    result = runner.run_simulation(
        input_path=tmp_path, threads=2, output_path=tmp_path
    )
    assert result.returncode == 0, result.stderr

    statepoints = list(tmp_path.glob("statepoint.*.h5"))
    assert statepoints, "run produced no statepoint file"

    parsed = ResultParser().parse_results(tmp_path)
    assert parsed.k_effective is not None
    assert abs(parsed.k_effective - EXPECTED_K) < K_TOLERANCE
