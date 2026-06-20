"""Batch and parallel simulation execution for OpenMC."""

from __future__ import annotations

import json
import multiprocessing
import os
import subprocess  # nosec B404
import time
import uuid
from collections.abc import Callable
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from promptmc._typing import PathLike
from promptmc.openmc_integration import OpenMCRunner


class ParallelMode(Enum):
    """Parallel execution mode."""

    THREADS = "threads"
    PROCESSES = "processes"
    MPI = "mpi"


@dataclass
class ParallelConfig:
    """Configuration for parallel execution."""

    mode: ParallelMode = ParallelMode.THREADS
    max_workers: int | None = None
    omp_threads: int = 1
    mpi_processes: int = 1
    mpi_executable: str = "mpirun"

    def __post_init__(self) -> None:
        """Set default max_workers based on CPU count."""
        if self.max_workers is None:
            self.max_workers = multiprocessing.cpu_count()


@dataclass
class SimulationJob:
    """Represents a single simulation job."""

    job_id: str
    input_path: Path
    output_path: Path | None = None
    threads: int = 1
    extra_args: dict[str, Any] = field(default_factory=dict)


@dataclass
class JobResult:
    """Result of a simulation job."""

    job_id: str
    success: bool
    duration_seconds: float
    return_code: int
    stdout: str = ""
    stderr: str = ""
    error: str | None = None


def _run_job_in_process(job: SimulationJob) -> JobResult:
    """Top-level helper for ProcessPoolExecutor (must be picklable)."""
    start_time = time.time()
    try:
        runner = OpenMCRunner()
        result = runner.run_simulation(
            input_path=job.input_path,
            threads=job.threads,
            output_path=job.output_path,
        )
        duration = time.time() - start_time
        return JobResult(
            job_id=job.job_id,
            success=result.returncode == 0,
            duration_seconds=duration,
            return_code=result.returncode,
            stdout=result.stdout or "",
            stderr=result.stderr or "",
        )
    except Exception as e:
        return JobResult(
            job_id=job.job_id,
            success=False,
            duration_seconds=time.time() - start_time,
            return_code=-1,
            error=str(e),
        )


class ParallelExecutor:
    """Manages parallel execution of OpenMC simulations."""

    def __init__(self, config: ParallelConfig | None = None) -> None:
        """Initialize the parallel executor.

        Args:
            config: Parallel execution configuration.
        """
        self.config = config or ParallelConfig()

    def execute_jobs(
        self,
        jobs: list[SimulationJob],
        progress_callback: Callable[[str, JobResult], None] | None = None,
    ) -> list[JobResult]:
        """Execute multiple simulation jobs in parallel.

        Args:
            jobs: List of simulation jobs to execute.
            progress_callback: Optional callback for progress updates.

        Returns:
            List of job results in the same order as input jobs.
        """
        if self.config.mode == ParallelMode.THREADS:
            return self._execute_with_pool(
                jobs,
                ThreadPoolExecutor,
                _run_job_in_process,
                progress_callback,
            )
        if self.config.mode == ParallelMode.PROCESSES:
            return self._execute_with_pool(
                jobs,
                ProcessPoolExecutor,
                _run_job_in_process,
                progress_callback,
            )
        if self.config.mode == ParallelMode.MPI:
            return self._execute_mpi(jobs, progress_callback)
        raise ValueError(f"Unknown parallel mode: {self.config.mode}")

    def _execute_with_pool(
        self,
        jobs: list[SimulationJob],
        executor_cls: type,
        run_fn: Callable[[SimulationJob], JobResult],
        progress_callback: Callable[[str, JobResult], None] | None,
    ) -> list[JobResult]:
        """Generic pool executor shared by threads and processes modes."""
        results: dict[str, JobResult] = {}
        with executor_cls(max_workers=self.config.max_workers) as executor:
            future_to_job = {executor.submit(run_fn, job): job for job in jobs}
            for future in as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result()
                except Exception as e:
                    result = JobResult(
                        job_id=job.job_id,
                        success=False,
                        duration_seconds=0.0,
                        return_code=-1,
                        error=str(e),
                    )
                results[job.job_id] = result
                if progress_callback:
                    progress_callback(job.job_id, result)
        return [results[job.job_id] for job in jobs]

    def _execute_mpi(
        self,
        jobs: list[SimulationJob],
        progress_callback: Callable[[str, JobResult], None] | None,
    ) -> list[JobResult]:
        """Execute jobs sequentially, each using MPI internally."""
        results = []
        for job in jobs:
            result = self._run_mpi_job(job)
            results.append(result)
            if progress_callback:
                progress_callback(job.job_id, result)
        return results

    def _run_mpi_job(self, job: SimulationJob) -> JobResult:
        """Run a single job using MPI."""
        start_time = time.time()
        cmd = [
            self.config.mpi_executable,
            "-n",
            str(self.config.mpi_processes),
            "openmc",
        ]
        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = str(self.config.omp_threads)
        cwd = (
            job.input_path.parent
            if job.input_path.is_file()
            else job.input_path
        )
        try:
            result = subprocess.run(  # nosec B603
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            duration = time.time() - start_time
            return JobResult(
                job_id=job.job_id,
                success=result.returncode == 0,
                duration_seconds=duration,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
            )
        except Exception as e:
            return JobResult(
                job_id=job.job_id,
                success=False,
                duration_seconds=time.time() - start_time,
                return_code=-1,
                error=str(e),
            )


@dataclass
class BatchSpec:
    """Specification for a batch of simulations."""

    name: str
    base_input: Path
    output_root: Path
    parameter_sweeps: list[dict[str, Any]] = field(default_factory=list)
    threads_per_job: int = 1
    description: str = ""


@dataclass
class BatchSummary:
    """Summary of a batch execution."""

    batch_id: str
    name: str
    total_jobs: int
    successful_jobs: int
    failed_jobs: int
    total_duration_seconds: float
    average_duration_seconds: float
    job_results: list[JobResult] = field(default_factory=list)


class BatchRunner:
    """Runs batches of OpenMC simulations with parameter sweeps."""

    def __init__(
        self,
        parallel_config: ParallelConfig | None = None,
    ) -> None:
        """Initialize the batch runner.

        Args:
            parallel_config: Configuration for parallel execution
        """
        self.parallel_config = parallel_config or ParallelConfig()
        self.executor = ParallelExecutor(self.parallel_config)

    def run_batch(self, spec: BatchSpec) -> BatchSummary:
        """Run a batch of simulations.

        Args:
            spec: Batch specification

        Returns:
            Batch summary with results
        """
        batch_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        # Create output directory
        spec.output_root.mkdir(parents=True, exist_ok=True)

        # Generate jobs from parameter sweeps
        jobs = self._generate_jobs(spec, batch_id)

        # Execute jobs in parallel
        results = self.executor.execute_jobs(jobs)

        # Calculate summary statistics
        total_duration = time.time() - start_time
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        avg_duration = (
            sum(r.duration_seconds for r in results) / len(results)
            if results
            else 0.0
        )

        summary = BatchSummary(
            batch_id=batch_id,
            name=spec.name,
            total_jobs=len(jobs),
            successful_jobs=successful,
            failed_jobs=failed,
            total_duration_seconds=total_duration,
            average_duration_seconds=avg_duration,
            job_results=results,
        )

        # Save batch summary
        self._save_summary(summary, spec.output_root)

        return summary

    def _generate_jobs(
        self, spec: BatchSpec, batch_id: str
    ) -> list[SimulationJob]:
        """Generate jobs from batch spec.

        Args:
            spec: Batch specification
            batch_id: Unique batch identifier

        Returns:
            List of simulation jobs
        """
        jobs = []

        if not spec.parameter_sweeps:
            # Single job with no parameter sweep
            job = SimulationJob(
                job_id=f"{batch_id}-001",
                input_path=spec.base_input,
                output_path=spec.output_root / "run-001",
                threads=spec.threads_per_job,
            )
            jobs.append(job)
        else:
            for i, params in enumerate(spec.parameter_sweeps, 1):
                job_id = f"{batch_id}-{i:03d}"
                output_path = spec.output_root / f"run-{i:03d}"

                job = SimulationJob(
                    job_id=job_id,
                    input_path=spec.base_input,
                    output_path=output_path,
                    threads=spec.threads_per_job,
                    extra_args=params,
                )
                jobs.append(job)

        return jobs

    def _save_summary(self, summary: BatchSummary, output_root: Path) -> None:
        """Save batch summary to JSON file.

        Args:
            summary: Batch summary
            output_root: Output directory
        """
        summary_path = output_root / "batch_summary.json"
        data = asdict(summary)

        # Convert non-serializable values
        for result in data.get("job_results", []):
            for key, value in result.items():
                if isinstance(value, Path):
                    result[key] = str(value)

        summary_path.write_text(json.dumps(data, indent=2, default=str))


def load_batch_spec(spec_path: PathLike) -> BatchSpec:
    """Load a batch specification from YAML or JSON file.

    Args:
        spec_path: Path to specification file

    Returns:
        Loaded batch specification

    Raises:
        ValueError: If file format is unsupported or invalid
    """
    spec_path = Path(spec_path)

    if not spec_path.exists():
        raise ValueError(f"Spec file not found: {spec_path}")

    content = spec_path.read_text()

    if spec_path.suffix in [".yaml", ".yml"]:
        data = yaml.safe_load(content)
    elif spec_path.suffix == ".json":
        data = json.loads(content)
    else:
        raise ValueError(
            f"Unsupported file format: {spec_path.suffix}. Use .yaml, .yml, or .json"
        )

    if not isinstance(data, dict):
        raise ValueError("Spec file must contain a dictionary at the root")

    # Convert paths
    if "base_input" in data:
        data["base_input"] = Path(data["base_input"])
    if "output_root" in data:
        data["output_root"] = Path(data["output_root"])

    return BatchSpec(**data)


def save_batch_spec(spec: BatchSpec, output_path: PathLike) -> Path:
    """Save a batch specification to YAML or JSON file.

    Args:
        spec: Batch specification
        output_path: Output file path

    Returns:
        Path to saved file
    """
    output_path = Path(output_path)

    data = {
        "name": spec.name,
        "description": spec.description,
        "base_input": str(spec.base_input),
        "output_root": str(spec.output_root),
        "threads_per_job": spec.threads_per_job,
        "parameter_sweeps": spec.parameter_sweeps,
    }

    if output_path.suffix in [".yaml", ".yml"]:
        output_path.write_text(yaml.safe_dump(data, sort_keys=False))
    elif output_path.suffix == ".json":
        output_path.write_text(json.dumps(data, indent=2))
    else:
        raise ValueError(
            f"Unsupported file format: {output_path.suffix}. Use .yaml, .yml, or .json"
        )

    return output_path
