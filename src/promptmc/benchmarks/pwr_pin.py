"""Mosteller PWR pin cell benchmark geometry and materials."""

from __future__ import annotations

from promptmc.geometry.materials import Material, MaterialsModel, NuclideSpec
from promptmc.geometry.primitives import (
    Cell,
    GeometryModel,
    HalfSpace,
    Intersection,
    Universe,
    XPlane,
    YPlane,
    ZCylinder,
)

NAME = "PWR Pin"
SOURCE = "Mosteller PWR pin cell benchmark"
EXPECTED_KEFF = 1.1705
KEFF_TOLERANCE = 0.0100


def build() -> tuple[GeometryModel, MaterialsModel]:
    """Build the PWR pin cell geometry and material models."""
    # 1. Surfaces
    pellet_out = ZCylinder(id=1, name="pellet_out", r=0.39116)
    clad_out = ZCylinder(id=2, name="clad_out", r=0.45720)

    # Square cell boundaries (pitch = 1.25984 cm, half-pitch = 0.62992 cm)
    half_pitch = 0.62992
    min_x = XPlane(
        id=11, name="min_x", x0=-half_pitch, boundary_type="reflective"
    )
    max_x = XPlane(
        id=12, name="max_x", x0=half_pitch, boundary_type="reflective"
    )
    min_y = YPlane(
        id=13, name="min_y", y0=-half_pitch, boundary_type="reflective"
    )
    max_y = YPlane(
        id=14, name="max_y", y0=half_pitch, boundary_type="reflective"
    )

    # 2. Cells
    fuel_cell = Cell(
        id=1,
        name="fuel",
        region=HalfSpace(surface_id=1, side="-"),
        fill_material_id=1,
    )

    clad_cell = Cell(
        id=2,
        name="clad",
        region=Intersection(
            nodes=[
                HalfSpace(surface_id=1, side="+"),
                HalfSpace(surface_id=2, side="-"),
            ]
        ),
        fill_material_id=2,
    )

    mod_cell = Cell(
        id=3,
        name="moderator",
        region=Intersection(
            nodes=[
                HalfSpace(surface_id=2, side="+"),
                HalfSpace(surface_id=11, side="+"),
                HalfSpace(surface_id=12, side="-"),
                HalfSpace(surface_id=13, side="+"),
                HalfSpace(surface_id=14, side="-"),
            ]
        ),
        fill_material_id=3,
    )

    geom = GeometryModel(
        surfaces=[pellet_out, clad_out, min_x, max_x, min_y, max_y],
        root_universe=Universe(id=1, cells=[fuel_cell, clad_cell, mod_cell]),
    )

    # 3. Materials
    fuel_mat = Material(
        id=1,
        name="UO2",
        density_g_per_cc=10.3,
        nuclides=[
            NuclideSpec(name="U235", fraction=0.0379),
            NuclideSpec(name="U238", fraction=0.8436),
            NuclideSpec(name="O16", fraction=0.1185),
        ],
    )

    clad_mat = Material(
        id=2,
        name="Zircaloy",
        density_g_per_cc=6.55,
        nuclides=[
            NuclideSpec(name="Zr90", fraction=1.0),
        ],
    )

    mod_mat = Material(
        id=3,
        name="Water",
        density_g_per_cc=0.743,
        nuclides=[
            NuclideSpec(name="H1", fraction=0.1119),
            NuclideSpec(name="O16", fraction=0.8881),
        ],
    )

    mats = MaterialsModel(materials=[fuel_mat, clad_mat, mod_mat])

    return geom, mats
