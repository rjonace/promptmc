"""Tests for batch simulation runner."""

import tempfile
from pathlib import Path

import pytest
from promptmc.batch import (
    BatchRunner,
    BatchSpec,
    ParallelConfig,
    ParallelMode,
    load_batch_spec,
    save_batch_spec,
)


def test_batch_spec_creation():
    """Test BatchSpec creation."""
    spec = BatchSpec(
        name="test-batch",
        base_input=Path("/tmp/input.xml"),
        output_root=Path("/tmp/output"),
        threads_per_job=4,
    )
    assert spec.name == "test-batch"
    assert spec.base_input == Path("/tmp/input.xml")
    assert spec.threads_per_job == 4
    assert spec.parameter_sweeps == []


def test_batch_runner_initialization():
    """Test BatchRunner initialization."""
    runner = BatchRunner()
    assert runner.parallel_config is not None
    assert runner.executor is not None


def test_batch_runner_custom_config():
    """Test BatchRunner with custom parallel config."""
    config = ParallelConfig(mode=ParallelMode.PROCESSES, max_workers=2)
    runner = BatchRunner(parallel_config=config)
    assert runner.parallel_config.max_workers == 2


def test_save_and_load_yaml_spec():
    """Test saving and loading batch spec as YAML."""
    spec = BatchSpec(
        name="yaml-test",
        base_input=Path("/tmp/input.xml"),
        output_root=Path("/tmp/output"),
        threads_per_job=2,
        parameter_sweeps=[{"param1": "value1"}],
        description="Test description",
    )

    with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        save_batch_spec(spec, temp_path)
        assert temp_path.exists()

        loaded = load_batch_spec(temp_path)
        assert loaded.name == spec.name
        assert loaded.threads_per_job == spec.threads_per_job
        assert loaded.parameter_sweeps == spec.parameter_sweeps
    finally:
        temp_path.unlink()


def test_save_and_load_json_spec():
    """Test saving and loading batch spec as JSON."""
    spec = BatchSpec(
        name="json-test",
        base_input=Path("/tmp/input.xml"),
        output_root=Path("/tmp/output"),
        threads_per_job=4,
    )

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        temp_path = Path(f.name)

    try:
        save_batch_spec(spec, temp_path)
        assert temp_path.exists()

        loaded = load_batch_spec(temp_path)
        assert loaded.name == spec.name
        assert loaded.threads_per_job == spec.threads_per_job
    finally:
        temp_path.unlink()


def test_load_spec_invalid_format():
    """Test loading spec with invalid format raises error."""
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        temp_path = Path(f.name)

    try:
        with pytest.raises(ValueError):
            load_batch_spec(temp_path)
    finally:
        temp_path.unlink()


def test_load_spec_nonexistent():
    """Test loading nonexistent spec raises error."""
    with pytest.raises(ValueError):
        load_batch_spec("/nonexistent/file.yaml")


def test_save_spec_invalid_format():
    """Test saving spec with invalid format raises error."""
    spec = BatchSpec(
        name="test",
        base_input=Path("/tmp/input.xml"),
        output_root=Path("/tmp/output"),
    )

    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as f:
        temp_path = Path(f.name)

    try:
        with pytest.raises(ValueError):
            save_batch_spec(spec, temp_path)
    finally:
        temp_path.unlink()


def test_run_batch_no_openmc():
    """Test running batch handles missing OpenMC gracefully."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        input_file = temp_path / "input.xml"
        input_file.write_text("<settings></settings>")
        output_root = temp_path / "output"

        spec = BatchSpec(
            name="no-openmc-test",
            base_input=input_file,
            output_root=output_root,
            parameter_sweeps=[{"i": 1}, {"i": 2}],
        )

        config = ParallelConfig(mode=ParallelMode.THREADS, max_workers=1)
        runner = BatchRunner(parallel_config=config)
        summary = runner.run_batch(spec)

        assert summary.total_jobs == 2
        # Jobs may fail due to missing OpenMC, but the runner should complete
        assert summary.batch_id != ""

        # Summary file should be created
        summary_file = output_root / "batch_summary.json"
        assert summary_file.exists()
