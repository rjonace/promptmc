"""Re-export shim — parallel primitives have moved to batch.py."""

from promptmc.batch import (  # noqa: F401
    JobResult,
    ParallelConfig,
    ParallelExecutor,
    ParallelMode,
    SimulationJob,
    _run_job_in_process,
)

__all__ = [
    "JobResult",
    "ParallelConfig",
    "ParallelExecutor",
    "ParallelMode",
    "SimulationJob",
    "_run_job_in_process",
]
