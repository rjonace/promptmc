"""Tests for parallel execution module."""

import multiprocessing
import tempfile
from pathlib import Path

from openmc_wrapper.parallel import (
    JobResult,
    ParallelConfig,
    ParallelExecutor,
    ParallelMode,
    SimulationJob,
)


def test_parallel_config_defaults():
    """Test ParallelConfig default values."""
    config = ParallelConfig()
    assert config.mode == ParallelMode.THREADS
    assert config.max_workers == multiprocessing.cpu_count()
    assert config.omp_threads == 1
    assert config.mpi_processes == 1


def test_parallel_config_custom():
    """Test ParallelConfig with custom values."""
    config = ParallelConfig(
        mode=ParallelMode.PROCESSES,
        max_workers=4,
        omp_threads=2,
    )
    assert config.mode == ParallelMode.PROCESSES
    assert config.max_workers == 4
    assert config.omp_threads == 2


def test_simulation_job_creation():
    """Test SimulationJob creation."""
    job = SimulationJob(
        job_id="test-001",
        input_path=Path("/tmp/input.xml"),
        output_path=Path("/tmp/output"),
        threads=4,
    )
    assert job.job_id == "test-001"
    assert job.input_path == Path("/tmp/input.xml")
    assert job.threads == 4


def test_job_result_creation():
    """Test JobResult creation."""
    result = JobResult(
        job_id="test-001",
        success=True,
        duration_seconds=10.5,
        return_code=0,
    )
    assert result.job_id == "test-001"
    assert result.success is True
    assert result.duration_seconds == 10.5
    assert result.return_code == 0


def test_parallel_executor_initialization():
    """Test ParallelExecutor initialization."""
    config = ParallelConfig(max_workers=2)
    executor = ParallelExecutor(config)
    assert executor.config.max_workers == 2


def test_parallel_executor_default_config():
    """Test ParallelExecutor with default config."""
    executor = ParallelExecutor()
    assert executor.config is not None
    assert executor.config.mode == ParallelMode.THREADS


def test_execute_jobs_with_threads_no_openmc():
    """Test thread-based execution gracefully handles missing OpenMC."""
    config = ParallelConfig(mode=ParallelMode.THREADS, max_workers=2)
    executor = ParallelExecutor(config)

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".xml", delete=False) as f:
        f.write(b"<settings></settings>")
        temp_path = Path(f.name)

    try:
        jobs = [
            SimulationJob(
                job_id=f"test-{i:03d}",
                input_path=temp_path,
            )
            for i in range(2)
        ]

        results = executor.execute_jobs(jobs)
        assert len(results) == 2
        # All jobs should fail since OpenMC is not installed
        for result in results:
            assert isinstance(result, JobResult)
            assert result.job_id.startswith("test-")
    finally:
        temp_path.unlink()
