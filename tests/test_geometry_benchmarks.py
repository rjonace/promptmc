"""Tests for validated benchmark reference geometries."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from promptmc.benchmarks import ALL_BENCHMARKS
from promptmc.benchmarks.godiva import build as build_godiva
from promptmc.benchmarks.pwr_pin import build as build_pwr_pin
from promptmc.geometry.xml_serializer import (
    serialize_geometry,
    serialize_materials,
)
from promptmc.openmc_integration import OpenMCRunner
from promptmc.visualization import ResultParser


def test_godiva_benchmark_structure() -> None:
    """Test Godiva benchmark returns correct structure."""
    geom, mats = build_godiva()

    # Godiva is a single sphere of HEU
    assert len(geom.surfaces) == 1
    assert geom.surfaces[0].kind == "sphere"
    assert geom.surfaces[0].boundary_type == "vacuum"

    assert len(geom.root_universe.cells) == 1
    cell = geom.root_universe.cells[0]
    assert cell.fill_material_id is not None
    assert cell.region.kind == "halfspace"
    assert cell.region.side == "-"

    # Material checks
    assert len(mats.materials) == 1
    mat = mats.materials[0]
    assert mat.density_g_per_cc > 0.0
    assert any(n.name == "U235" for n in mat.nuclides)
    assert any(n.name == "U238" for n in mat.nuclides)


def test_pwr_pin_benchmark_structure() -> None:
    """Test PWR Pin Cell benchmark returns correct structure."""
    geom, mats = build_pwr_pin()

    # PWR pin has:
    # 2 cylinders (pellet outer, clad outer) or maybe 3 (with clad inner)
    # Plus bounding planes for the square lattice cell
    cyls = [s for s in geom.surfaces if s.kind == "z-cylinder"]
    planes = [
        s
        for s in geom.surfaces
        if s.kind in ("x-plane", "y-plane", "z-plane", "plane")
    ]

    assert len(cyls) >= 1
    assert len(planes) >= 2
    assert all(p.boundary_type == "reflective" for p in planes)

    # 3 cells: fuel, clad, moderator (or 4 cells if gap included)
    assert len(geom.root_universe.cells) >= 3

    # Materials check
    assert len(mats.materials) >= 2  # fuel, clad, moderator
    mat_ids = {m.id for m in mats.materials}
    assert all(
        c.fill_material_id in mat_ids
        for c in geom.root_universe.cells
        if c.fill_material_id is not None
    )


@pytest.mark.requires_openmc
def test_benchmarks_export_to_xml() -> None:
    """Test that both benchmarks can be exported to valid XML."""
    for _, bench in ALL_BENCHMARKS.items():
        geom, mats = bench.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            geom_path = Path(tmpdir) / "geometry.xml"
            mats_path = Path(tmpdir) / "materials.xml"

            serialize_geometry(geom, geom_path)
            serialize_materials(mats, mats_path)

            assert geom_path.exists()
            assert mats_path.exists()


@pytest.mark.requires_openmc_data
def test_benchmarks_simulation() -> None:
    """Run real OpenMC simulation for benchmarks and assert k-effective."""
    for _, bench in ALL_BENCHMARKS.items():
        geom, mats = bench.build()

        with tempfile.TemporaryDirectory() as tmpdir:
            run_dir = Path(tmpdir)
            geom_path = run_dir / "geometry.xml"
            mats_path = run_dir / "materials.xml"
            settings_path = run_dir / "settings.xml"

            serialize_geometry(geom, geom_path)
            serialize_materials(mats, mats_path)

            # Generate basic eigenvalue settings
            runner = OpenMCRunner()
            runner.generate_configuration(
                settings_path,
                particles=5000,
                batches=25,
                inactive=5,
            )

            # Run OpenMC
            result = runner.run_simulation(run_dir, threads=1)
            assert result.success

            # Parse statepoint
            statepoints = list(run_dir.glob("statepoint.*.h5"))
            assert len(statepoints) == 1

            parser = ResultParser()
            metrics = parser.parse_results(statepoints[0])
            keff = metrics.keff

            # Check within tolerance
            assert abs(keff.value - bench.EXPECTED_KEFF) < bench.KEFF_TOLERANCE
