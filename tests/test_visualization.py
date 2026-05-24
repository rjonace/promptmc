"""Tests for visualization module."""

import json
import tempfile
from pathlib import Path

from promptmc.visualization import (
    ResultParser,
    ResultVisualizer,
    SimulationResult,
)


def test_simulation_result_creation():
    """Test SimulationResult creation."""
    result = SimulationResult(
        k_effective=1.0,
        k_effective_std=0.001,
        n_batches=100,
        n_particles=10000,
    )
    assert result.k_effective == 1.0
    assert result.n_batches == 100


def test_parse_results_empty_directory():
    """Test parsing empty directory."""
    parser = ResultParser()

    with tempfile.TemporaryDirectory() as temp_dir:
        result = parser.parse_results(temp_dir)
        assert result.statepoint_path is None
        assert result.summary_path is None
        assert result.tallies_path is None


def test_parse_results_with_tallies():
    """Test parsing directory with tallies file."""
    parser = ResultParser()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        tallies_file = temp_path / "tallies.out"
        tallies_file.write_text("Tally 1: 1.234e-5\nTally 2: 5.678e-3\n")

        result = parser.parse_results(temp_path)
        assert result.tallies_path == tallies_file
        assert "raw_content" in result.tallies
        assert result.tallies["line_count"] == 2


def test_format_text_report_empty():
    """Test formatting empty result as text."""
    visualizer = ResultVisualizer()
    result = SimulationResult()
    report = visualizer.format_text_report(result)

    assert "OpenMC Simulation Results" in report
    assert "Output Files" in report


def test_format_text_report_with_data():
    """Test formatting result with data."""
    visualizer = ResultVisualizer()
    result = SimulationResult(
        k_effective=1.00500,
        k_effective_std=0.00012,
        n_batches=100,
        n_particles=1000000,
        runtime_seconds=120.5,
    )
    report = visualizer.format_text_report(result)

    assert "1.00500" in report
    assert "100" in report
    assert "1,000,000" in report
    assert "120.50" in report


def test_export_json():
    """Test exporting result to JSON."""
    visualizer = ResultVisualizer()
    result = SimulationResult(
        k_effective=1.005,
        n_batches=100,
        n_particles=10000,
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = Path(f.name)

    try:
        result_path = visualizer.export_json(result, temp_path)
        assert result_path == temp_path
        assert temp_path.exists()

        data = json.loads(temp_path.read_text())
        assert data["k_effective"] == 1.005
        assert data["n_batches"] == 100
        assert data["n_particles"] == 10000
    finally:
        temp_path.unlink()


def test_export_summary_table_empty():
    """Test exporting empty summary table."""
    visualizer = ResultVisualizer()
    table = visualizer.export_summary_table([])
    assert "No results" in table


def test_export_summary_table_with_results():
    """Test exporting summary table with multiple results."""
    visualizer = ResultVisualizer()
    results = [
        SimulationResult(k_effective=1.0, n_batches=100, n_particles=10000, runtime_seconds=10.0),
        SimulationResult(k_effective=0.99, n_batches=100, n_particles=10000, runtime_seconds=11.0),
    ]
    table = visualizer.export_summary_table(results)

    assert "k-effective" in table
    assert "1.00000" in table
    assert "0.99000" in table


def test_make_json_serializable_basic():
    """Test JSON serialization of basic types."""
    visualizer = ResultVisualizer()

    assert visualizer._make_json_serializable("str") == "str"
    assert visualizer._make_json_serializable(42) == 42
    assert visualizer._make_json_serializable(3.14) == 3.14
    assert visualizer._make_json_serializable(True) is True
    assert visualizer._make_json_serializable(None) is None


def test_make_json_serializable_collections():
    """Test JSON serialization of collections."""
    visualizer = ResultVisualizer()

    result = visualizer._make_json_serializable({"a": 1, "b": [1, 2, 3]})
    assert result == {"a": 1, "b": [1, 2, 3]}


def test_make_json_serializable_bytes():
    """Test JSON serialization of bytes."""
    visualizer = ResultVisualizer()

    result = visualizer._make_json_serializable(b"hello")
    assert result == "hello"
