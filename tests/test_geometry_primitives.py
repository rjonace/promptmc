"""Tests for geometry primitives, materials, tallies, and serialization."""

from __future__ import annotations

import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from promptmc.geometry.materials import Material, MaterialsModel, NuclideSpec
from promptmc.geometry.primitives import (
    Cell,
    GeometryModel,
    HalfSpace,
    Intersection,
    Sphere,
    Universe,
)
from promptmc.geometry.tallies import TalliesModel, Tally
from promptmc.geometry.xml_serializer import (
    serialize_geometry,
    serialize_materials,
)
from pydantic import ValidationError

# Optional imports for test config
try:
    import openmc  # type: ignore

    OPENMC_AVAILABLE = True
except ImportError:
    OPENMC_AVAILABLE = False


def test_surface_validation() -> None:
    """Test that surface parameters are validated correctly."""
    # Sphere requires radius > 0
    with pytest.raises(ValidationError):
        Sphere(r=0.0)

    with pytest.raises(ValidationError):
        Sphere(r=-1.5)

    # Valid sphere
    s = Sphere(id=1, name="sphere1", r=5.0)
    assert s.r == 5.0
    assert s.kind == "sphere"
    assert s.boundary_type == "transmission"


def test_region_validation() -> None:
    """Test region construction and structure."""
    hs = HalfSpace(surface_id=1, side="-")
    assert hs.kind == "halfspace"
    assert hs.surface_id == 1
    assert hs.side == "-"

    # Test intersection
    intersection = Intersection(nodes=[hs])
    assert intersection.kind == "intersection"
    assert len(intersection.nodes) == 1


def test_geometry_model_validation() -> None:
    """Test GeometryModel constraints (uniqueness, boundaries, references)."""
    # 1. Non-unique surface IDs
    with pytest.raises(ValidationError):
        GeometryModel(
            surfaces=[
                Sphere(id=1, r=1.0, boundary_type="vacuum"),
                Sphere(id=1, r=2.0),
            ],
            root_universe=Universe(id=1, cells=[]),
        )

    # 2. Dangling surface reference in HalfSpace
    with pytest.raises(ValidationError):
        GeometryModel(
            surfaces=[Sphere(id=1, r=1.0, boundary_type="vacuum")],
            root_universe=Universe(
                id=1,
                cells=[
                    Cell(
                        id=1,
                        region=HalfSpace(surface_id=99, side="-"),
                    )
                ],
            ),
        )

    # 3. Missing outer boundary (all surfaces transmission)
    with pytest.raises(ValidationError):
        GeometryModel(
            surfaces=[
                Sphere(id=1, r=1.0, boundary_type="transmission"),
            ],
            root_universe=Universe(
                id=1,
                cells=[
                    Cell(
                        id=1,
                        region=HalfSpace(surface_id=1, side="-"),
                    )
                ],
            ),
        )

    # 4. Valid model
    valid_model = GeometryModel(
        surfaces=[Sphere(id=1, r=10.0, boundary_type="vacuum")],
        root_universe=Universe(
            id=1,
            cells=[
                Cell(
                    id=1,
                    region=HalfSpace(surface_id=1, side="-"),
                )
            ],
        ),
    )
    assert len(valid_model.surfaces) == 1
    assert len(valid_model.root_universe.cells) == 1


def test_materials_validation() -> None:
    """Test Nuclide, Material and MaterialsModel validation."""
    # Negative density
    with pytest.raises(ValidationError):
        Material(id=1, name="fuel", density_g_per_cc=-10.0, nuclides=[])

    # Bad nuclide format
    with pytest.raises(ValidationError):
        Material(
            id=1,
            name="fuel",
            density_g_per_cc=10.0,
            nuclides=[NuclideSpec(name="123-U", fraction=1.0)],
        )

    # Non-unique material IDs
    with pytest.raises(ValidationError):
        MaterialsModel(
            materials=[
                Material(id=1, name="m1", density_g_per_cc=1.0, nuclides=[]),
                Material(id=1, name="m2", density_g_per_cc=2.0, nuclides=[]),
            ]
        )


def test_tallies_validation() -> None:
    """Test tallies schema validation."""
    # Valid tally
    t = Tally(id=1, name="flux_tally", scores=["flux"])
    assert t.scores == ["flux"]

    # Unique tally IDs
    with pytest.raises(ValidationError):
        TalliesModel(
            tallies=[
                Tally(id=1, name="t1", scores=["flux"]),
                Tally(id=1, name="t2", scores=["fission"]),
            ]
        )


def test_fallback_serialization() -> None:
    """Test serialization using fallback method (XML string parsing, no OpenMC required)."""
    model = GeometryModel(
        surfaces=[
            Sphere(id=1, r=8.5, boundary_type="vacuum"),
        ],
        root_universe=Universe(
            id=1,
            cells=[
                Cell(
                    id=10,
                    name="main_cell",
                    region=HalfSpace(surface_id=1, side="-"),
                    fill_material_id=2,
                )
            ],
        ),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        xml_path = Path(tmpdir) / "geometry.xml"
        # Since serialize_geometry checks _OPENMC_AVAILABLE internally, let's call it.
        # It should dump valid XML format regardless.
        serialize_geometry(model, xml_path)

        assert xml_path.exists()
        tree = ET.parse(xml_path)
        root = tree.getroot()
        assert root.tag == "geometry"

        # Check surface
        surf_elems = root.findall(".//surface")
        assert len(surf_elems) == 1
        assert surf_elems[0].get("id") == "1"
        assert surf_elems[0].get("type") == "sphere"
        assert surf_elems[0].get("coeffs") == "0.0 0.0 0.0 8.5"
        assert surf_elems[0].get("boundary") == "vacuum"

        # Check cell
        cell_elems = root.findall(".//cell")
        assert len(cell_elems) == 1
        assert cell_elems[0].get("id") == "10"
        assert cell_elems[0].get("name") == "main_cell"
        assert cell_elems[0].get("material") == "2"
        assert cell_elems[0].get("region") == "-1"


def test_materials_serialization() -> None:
    """Test serialization of materials."""
    mats = MaterialsModel(
        materials=[
            Material(
                id=1,
                name="fuel",
                density_g_per_cc=19.1,
                nuclides=[
                    NuclideSpec(name="U235", fraction=0.9),
                    NuclideSpec(name="U238", fraction=0.1),
                ],
            )
        ]
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        xml_path = Path(tmpdir) / "materials.xml"
        serialize_materials(mats, xml_path)

        assert xml_path.exists()
        tree = ET.parse(xml_path)
        root = tree.getroot()
        assert root.tag == "materials"

        mat_elems = root.findall(".//material")
        assert len(mat_elems) == 1
        assert mat_elems[0].get("id") == "1"
        assert mat_elems[0].get("name") == "fuel"

        density_elem = mat_elems[0].find("density")
        assert density_elem is not None
        assert density_elem.get("value") == "19.1"
        assert density_elem.get("units") == "g/cm3"

        nuc_elems = mat_elems[0].findall("nuclide")
        assert len(nuc_elems) == 2
        assert nuc_elems[0].get("name") == "U235"
        assert nuc_elems[0].get("wo") == "0.9"


@pytest.mark.requires_openmc
def test_openmc_roundtrip() -> None:
    """Test round-trip serialization using OpenMC parsing (requires openmc package)."""
    model = GeometryModel(
        surfaces=[
            Sphere(id=1, r=12.0, boundary_type="vacuum"),
        ],
        root_universe=Universe(
            id=1,
            cells=[
                Cell(
                    id=10,
                    name="sphere_cell",
                    region=HalfSpace(surface_id=1, side="-"),
                )
            ],
        ),
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        xml_path = Path(tmpdir) / "geometry.xml"
        # Export XML through the main serializer
        serialize_geometry(model, xml_path)

        # Parse XML back using OpenMC geometry module
        geom = openmc.Geometry.from_xml(str(xml_path))  # type: ignore

        # Validate that the structure matches the source model
        surfaces = geom.get_all_surfaces()
        assert len(surfaces) == 1
        s_id = list(surfaces.keys())[0]
        s_obj = surfaces[s_id]

        assert isinstance(s_obj, openmc.Sphere)  # type: ignore
        assert s_obj.r == 12.0
        assert s_obj.boundary_type == "vacuum"

        cells = geom.get_all_cells()
        assert len(cells) == 1
        c_id = list(cells.keys())[0]
        c_obj = cells[c_id]
        assert c_obj.name == "sphere_cell"
