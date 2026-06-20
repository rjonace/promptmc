"""Protocol definitions for simulation benchmarks."""

from __future__ import annotations

from typing import Protocol

from promptmc._typing import PathLike
from promptmc.geometry.materials import MaterialsModel
from promptmc.geometry.primitives import GeometryModel
from promptmc.openmc_integration import SimulationResult


class Benchmark(Protocol):
    """Protocol that all reference benchmarks must implement."""

    NAME: str
    SOURCE: str
    EXPECTED_KEFF: float
    KEFF_TOLERANCE: float

    def build(self) -> tuple[GeometryModel, MaterialsModel]:
        """Construct the geometry and material models for this benchmark."""
        ...

    def run(
        self,
        particles: int | None = None,
        batches: int | None = None,
        inactive: int | None = None,
        threads: int = 1,
        cwd: PathLike | None = None,
    ) -> SimulationResult:
        """Build and run this benchmark through OpenMC."""
        ...
