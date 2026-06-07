"""Protocol definitions for simulation benchmarks."""

from __future__ import annotations

from typing import Protocol

from promptmc.geometry.materials import MaterialsModel
from promptmc.geometry.primitives import GeometryModel


class Benchmark(Protocol):
    """Protocol that all reference benchmarks must implement."""

    NAME: str
    SOURCE: str
    EXPECTED_KEFF: float
    KEFF_TOLERANCE: float

    def build(self) -> tuple[GeometryModel, MaterialsModel]:
        """Construct the geometry and material models for this benchmark."""
        ...
