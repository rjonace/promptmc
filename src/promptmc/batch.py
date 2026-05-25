"""Batch simulation runner for OpenMC."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

import yaml

from promptmc.parallel import (
    JobResult,
    ParallelConfig,
    ParallelExecutor,
    SimulationJob,
)


@dataclass
class BatchSpec:
    """Specification for a batch of simulations."""

    name: str
    base_input: Path
    output_root: Path
    parameter_sweeps: list[dict] = field(default_factory=list)
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


def load_batch_spec(spec_path: str | Path) -> BatchSpec:
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


def save_batch_spec(spec: BatchSpec, output_path: str | Path) -> Path:
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
