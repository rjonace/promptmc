"""Tests for OpenMC XML -> promptmc model deserialization."""

from __future__ import annotations

from pathlib import Path

import pytest
from promptmc.benchmarks import godiva, pwr_pin
from promptmc.geometry.primitives import (
    Complement,
    HalfSpace,
    Intersection,
    Union_,
)
from promptmc.geometry.xml_serializer import (
    parse_geometry_xml,
    parse_materials_xml,
    parse_region_string,
    serialize_geometry,
    serialize_materials,
)
from pydantic import ValidationError


def test_parse_region_halfspace():
    """A bare/signed surface id parses to a HalfSpace."""
    assert parse_region_string("-1") == HalfSpace(surface_id=1, side="-")
    assert parse_region_string("+2") == HalfSpace(surface_id=2, side="+")
    assert parse_region_string("3") == HalfSpace(surface_id=3, side="+")


def test_parse_region_intersection():
    """Space-separated halfspaces parse to an Intersection."""
    region = parse_region_string("+1 -2 +3")
    assert isinstance(region, Intersection)
    assert region.nodes == [
        HalfSpace(surface_id=1, side="+"),
        HalfSpace(surface_id=2, side="-"),
        HalfSpace(surface_id=3, side="+"),
    ]


def test_parse_region_union():
    """A '|' separated expression parses to a Union."""
    region = parse_region_string("-1 | 2")
    assert isinstance(region, Union_)
    assert region.nodes == [
        HalfSpace(surface_id=1, side="-"),
        HalfSpace(surface_id=2, side="+"),
    ]


def test_parse_region_complement_and_parentheses():
    """Complement and parentheses nest correctly."""
    region = parse_region_string("~(-1 | 2)")
    assert isinstance(region, Complement)
    assert isinstance(region.node, Union_)


def test_parse_region_mixed_precedence():
    """Union binds looser than intersection."""
    region = parse_region_string("-1 -2 | 3")
    assert isinstance(region, Union_)
    assert isinstance(region.nodes[0], Intersection)
    assert region.nodes[1] == HalfSpace(surface_id=3, side="+")


def test_parse_region_unsupported_syntax():
    """Unsupported characters raise a clear error."""
    with pytest.raises(ValueError, match="Unsupported region syntax"):
        parse_region_string("-1 & 2")


def test_parse_region_unbalanced_parentheses():
    """Unbalanced parentheses raise an error."""
    with pytest.raises(ValueError, match="parentheses"):
        parse_region_string("(-1 | 2")


@pytest.mark.parametrize("module", [godiva, pwr_pin])
def test_geometry_round_trip(module, tmp_path: Path):
    """serialize_geometry -> parse_geometry_xml reproduces the model."""
    geom, _ = module.build()
    path = tmp_path / "geometry.xml"
    serialize_geometry(geom, path)

    parsed = parse_geometry_xml(path)

    assert len(parsed.surfaces) == len(geom.surfaces)
    assert {s.id for s in parsed.surfaces} == {s.id for s in geom.surfaces}
    assert len(parsed.root_universe.cells) == len(geom.root_universe.cells)
    for original, restored in zip(
        geom.root_universe.cells, parsed.root_universe.cells, strict=False
    ):
        assert restored.region == original.region
        assert restored.fill_material_id == original.fill_material_id


@pytest.mark.parametrize("module", [godiva, pwr_pin])
def test_materials_round_trip(module, tmp_path: Path):
    """serialize_materials -> parse_materials_xml reproduces the model."""
    _, mats = module.build()
    path = tmp_path / "materials.xml"
    serialize_materials(mats, path)

    parsed = parse_materials_xml(path)

    assert len(parsed.materials) == len(mats.materials)
    for original, restored in zip(
        mats.materials, parsed.materials, strict=False
    ):
        assert restored.id == original.id
        assert restored.density_g_per_cc == pytest.approx(
            original.density_g_per_cc
        )
        assert [n.name for n in restored.nuclides] == [
            n.name for n in original.nuclides
        ]


def test_parse_geometry_dangling_surface(tmp_path: Path):
    """A region referencing an unknown surface fails validation."""
    path = tmp_path / "geometry.xml"
    path.write_text(
        "<geometry>"
        '<surface id="1" type="sphere" coeffs="0 0 0 5" boundary="vacuum"/>'
        '<cell id="1" material="1" region="-9"/>'
        "</geometry>",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        parse_geometry_xml(path)


def test_parse_geometry_unbounded(tmp_path: Path):
    """A geometry with only transmission boundaries is rejected."""
    path = tmp_path / "geometry.xml"
    path.write_text(
        "<geometry>"
        '<surface id="1" type="sphere" coeffs="0 0 0 5"/>'
        '<cell id="1" material="1" region="-1"/>'
        "</geometry>",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        parse_geometry_xml(path)


def test_parse_geometry_missing_region(tmp_path: Path):
    """A cell without a region raises a clear error."""
    path = tmp_path / "geometry.xml"
    path.write_text(
        "<geometry>"
        '<surface id="1" type="sphere" coeffs="0 0 0 5" boundary="vacuum"/>'
        '<cell id="1" material="1"/>'
        "</geometry>",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="missing a region"):
        parse_geometry_xml(path)


def test_parse_materials_negative_density(tmp_path: Path):
    """A non-positive density fails Material validation."""
    path = tmp_path / "materials.xml"
    path.write_text(
        "<materials>"
        '<material id="1" name="bad">'
        '<density value="-1.0" units="g/cm3"/>'
        '<nuclide name="U235" wo="1.0"/>'
        "</material>"
        "</materials>",
        encoding="utf-8",
    )
    with pytest.raises(ValidationError):
        parse_materials_xml(path)
