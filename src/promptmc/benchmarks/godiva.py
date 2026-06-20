"""Godiva (HEU-MET-FAST-001) bare HEU sphere benchmark."""

from __future__ import annotations

from promptmc._typing import PathLike
from promptmc.geometry.materials import Material, MaterialsModel, NuclideSpec
from promptmc.geometry.primitives import (
    Cell,
    GeometryModel,
    HalfSpace,
    Sphere,
    Universe,
)
from promptmc.openmc_integration import OpenMCRunner, SimulationResult
from promptmc.schema import RunMode, SettingsSchema

NAME = "Godiva"
SOURCE = "ICSBEP HEU-MET-FAST-001"
EXPECTED_KEFF = 1.0000
KEFF_TOLERANCE = 0.0050


def build() -> tuple[GeometryModel, MaterialsModel]:
    """Build the Godiva bare HEU sphere geometry and material models."""
    # 1. Geometry Model
    sphere = Sphere(
        id=1, name="godiva_sphere", r=8.7407, boundary_type="vacuum"
    )

    cell = Cell(
        id=10,
        name="heu_sphere",
        region=HalfSpace(surface_id=1, side="-"),
        fill_material_id=1,
    )

    geom = GeometryModel(
        surfaces=[sphere],
        root_universe=Universe(id=1, cells=[cell]),
    )

    # 2. Materials Model
    heu = Material(
        id=1,
        name="HEU",
        density_g_per_cc=18.74,
        nuclides=[
            NuclideSpec(name="U235", fraction=0.9377),
            NuclideSpec(name="U238", fraction=0.0623),
        ],
    )

    mats = MaterialsModel(materials=[heu])

    return geom, mats


def run(
    particles: int | None = None,
    batches: int | None = None,
    inactive: int | None = None,
    threads: int = 1,
    cwd: PathLike | None = None,
) -> SimulationResult:
    """Build and run the Godiva benchmark through OpenMC.

    Args:
        particles: Particles per batch (default 10000).
        batches: Total batches (default 100).
        inactive: Inactive batches (default 20).
        threads: Number of OpenMP threads to use.
        cwd: Working directory for the run.

    Returns:
        The :class:`SimulationResult` describing the run outcome.
    """
    geom, mats = build()
    settings = SettingsSchema(
        run_mode=RunMode.EIGENVALUE,
        particles=particles or 10000,
        batches=batches or 100,
        inactive=inactive if inactive is not None else 20,
    )
    return OpenMCRunner().run_from_models(
        geometry=geom,
        materials=mats,
        settings=settings,
        threads=threads,
        cwd=cwd,
    )
