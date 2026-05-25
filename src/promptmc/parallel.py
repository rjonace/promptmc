"""Parallel execution support for OpenMC simulations."""

from __future__ import annotations

import multiprocessing
import os
from collections.abc import Callable
from concurrent.futures import (
    ProcessPoolExecutor,
    ThreadPoolExecutor,
    as_completed,
)
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from promptmc.openmc_integration import OpenMCIntegration


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
    extra_args: dict = field(default_factory=dict)


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


class ParallelExecutor:
    """Manages parallel execution of OpenMC simulations."""

    def __init__(self, config: ParallelConfig | None = None) -> None:
        """Initialize the parallel executor.

        Args:
            config: Parallel execution configuration
        """
        self.config = config or ParallelConfig()

    def execute_jobs(
        self,
        jobs: list[SimulationJob],
        progress_callback: Callable[[str, JobResult], None] | None = None,
    ) -> list[JobResult]:
        """Execute multiple simulation jobs in parallel.

        Args:
            jobs: List of simulation jobs to execute
            progress_callback: Optional callback for progress updates

        Returns:
            List of job results in the same order as input jobs
        """
        if self.config.mode == ParallelMode.THREADS:
            return self._execute_with_threads(jobs, progress_callback)
        elif self.config.mode == ParallelMode.PROCESSES:
            return self._execute_with_processes(jobs, progress_callback)
        elif self.config.mode == ParallelMode.MPI:
            return self._execute_with_mpi(jobs, progress_callback)
        else:
            raise ValueError(f"Unknown parallel mode: {self.config.mode}")

    def _execute_with_threads(
        self,
        jobs: list[SimulationJob],
        progress_callback: Callable[[str, JobResult], None] | None = None,
    ) -> list[JobResult]:
        """Execute jobs using thread pool.

        Args:
            jobs: List of jobs to execute
            progress_callback: Progress callback

        Returns:
            List of job results
        """
        results: dict[str, JobResult] = {}

        with ThreadPoolExecutor(
            max_workers=self.config.max_workers
        ) as executor:
            future_to_job = {
                executor.submit(self._run_single_job, job): job for job in jobs
            }

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

        # Return results in original job order
        return [results[job.job_id] for job in jobs]

    def _execute_with_processes(
        self,
        jobs: list[SimulationJob],
        progress_callback: Callable[[str, JobResult], None] | None = None,
    ) -> list[JobResult]:
        """Execute jobs using process pool.

        Args:
            jobs: List of jobs to execute
            progress_callback: Progress callback

        Returns:
            List of job results
        """
        results: dict[str, JobResult] = {}

        with ProcessPoolExecutor(
            max_workers=self.config.max_workers
        ) as executor:
            future_to_job = {
                executor.submit(_run_job_in_process, job): job for job in jobs
            }

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

    def _execute_with_mpi(
        self,
        jobs: list[SimulationJob],
        progress_callback: Callable[[str, JobResult], None] | None = None,
    ) -> list[JobResult]:
        """Execute jobs using MPI.

        Args:
            jobs: List of jobs to execute
            progress_callback: Progress callback

        Returns:
            List of job results
        """
        # MPI execution runs jobs sequentially but each job uses MPI internally
        results = []
        for job in jobs:
            result = self._run_mpi_job(job)
            results.append(result)
            if progress_callback:
                progress_callback(job.job_id, result)
        return results

    def _run_single_job(self, job: SimulationJob) -> JobResult:
        """Run a single simulation job.

        Args:
            job: Job to run

        Returns:
            Job result
        """
        import time

        start_time = time.time()

        try:
            integration = OpenMCIntegration()
            result = integration.run_simulation(
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
                stdout=result.stdout if result.stdout else "",
                stderr=result.stderr if result.stderr else "",
            )
        except Exception as e:
            duration = time.time() - start_time
            return JobResult(
                job_id=job.job_id,
                success=False,
                duration_seconds=duration,
                return_code=-1,
                error=str(e),
            )

    def _run_mpi_job(self, job: SimulationJob) -> JobResult:
        """Run a job using MPI.

        Args:
            job: Job to run

        Returns:
            Job result
        """
        import subprocess  # nosec B404
        import time

        start_time = time.time()

        cmd = [
            self.config.mpi_executable,
            "-n",
            str(self.config.mpi_processes),
            "openmc",
        ]

        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = str(self.config.omp_threads)

        try:
            cwd = (
                job.input_path.parent
                if job.input_path.is_file()
                else job.input_path
            )

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
            duration = time.time() - start_time
            return JobResult(
                job_id=job.job_id,
                success=False,
                duration_seconds=duration,
                return_code=-1,
                error=str(e),
            )


def _run_job_in_process(job: SimulationJob) -> JobResult:
    """Helper function for ProcessPoolExecutor (must be picklable).

    Args:
        job: Job to run

    Returns:
        Job result
    """
    import time

    start_time = time.time()

    try:
        integration = OpenMCIntegration()
        result = integration.run_simulation(
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
            stdout=result.stdout if result.stdout else "",
            stderr=result.stderr if result.stderr else "",
        )
    except Exception as e:
        duration = time.time() - start_time
        return JobResult(
            job_id=job.job_id,
            success=False,
            duration_seconds=duration,
            return_code=-1,
            error=str(e),
        )
