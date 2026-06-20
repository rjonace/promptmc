"""Progress reporting and performance monitoring for OpenMC simulations."""

from __future__ import annotations

import contextlib
import os
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

try:
    import psutil

    _PSUTIL_AVAILABLE = True
except ImportError:  # pragma: no cover - psutil is an optional extra
    psutil = None  # type: ignore[assignment]
    _PSUTIL_AVAILABLE = False


class ProgressStage(str, Enum):
    """Stages of OpenMC simulation execution."""

    INITIALIZING = "initializing"
    VALIDATING = "validating"
    PREPARING = "preparing"
    SIMULATING = "simulating"
    PROCESSING_RESULTS = "processing_results"
    FINALIZING = "finalizing"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class ProgressEvent:
    """A single progress event."""

    stage: ProgressStage
    message: str
    progress: float = 0.0  # 0.0 to 1.0
    timestamp: float = field(default_factory=time.time)
    metadata: dict[str, Any] = field(default_factory=dict)


ProgressCallback = Callable[[ProgressEvent], None]


class ProgressReporter:
    """Reports progress for long-running simulations.

    Supports multiple subscribers via callbacks, allowing both CLI display
    and telemetry instrumentation to react to the same events.
    """

    def __init__(self) -> None:
        self._callbacks: list[ProgressCallback] = []
        self._current_stage: ProgressStage = ProgressStage.INITIALIZING
        self._events: list[ProgressEvent] = []

    def subscribe(self, callback: ProgressCallback) -> None:
        """Subscribe a callback to progress events."""
        self._callbacks.append(callback)

    def unsubscribe(self, callback: ProgressCallback) -> None:
        """Unsubscribe a callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def report(
        self,
        stage: ProgressStage,
        message: str,
        progress: float = 0.0,
        **metadata: Any,
    ) -> ProgressEvent:
        """Report a progress event."""
        event = ProgressEvent(
            stage=stage,
            message=message,
            progress=max(0.0, min(1.0, progress)),
            metadata=metadata,
        )
        self._current_stage = stage
        self._events.append(event)
        for callback in self._callbacks:
            with contextlib.suppress(Exception):
                callback(event)
        return event

    @property
    def current_stage(self) -> ProgressStage:
        """The most recently reported stage."""
        return self._current_stage

    @property
    def events(self) -> list[ProgressEvent]:
        """All recorded events."""
        return list(self._events)


class RichProgressDisplay:
    """Rich-based progress display for CLI usage.

    Wraps a ``rich.progress.Progress`` instance with simulation-aware tasks
    for batches, particles, and the overall stage indicator.
    """

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self._progress: Progress | None = None
        self._main_task: TaskID | None = None
        self._subtask: TaskID | None = None

    @contextmanager
    def display(
        self,
        title: str = "OpenMC Simulation",
        total_steps: int | None = None,
    ) -> Iterator[RichProgressDisplay]:
        """Context manager that shows a live progress display."""
        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=self.console,
            transient=False,
        )

        with self._progress:
            self._main_task = self._progress.add_task(
                f"[cyan]{title}",
                total=total_steps,
            )
            try:
                yield self
            finally:
                self._main_task = None
                self._subtask = None
                self._progress = None

    def update_main(
        self,
        description: str | None = None,
        advance: float = 0.0,
        completed: float | None = None,
    ) -> None:
        """Update the main progress task."""
        if self._progress is None or self._main_task is None:
            return
        kwargs: dict[str, Any] = {}
        if description is not None:
            kwargs["description"] = description
        if completed is not None:
            kwargs["completed"] = completed
        if advance:
            kwargs["advance"] = advance
        self._progress.update(self._main_task, **kwargs)

    def add_subtask(self, description: str, total: int | None = None) -> TaskID:
        """Add a subtask under the main task."""
        if self._progress is None:
            raise RuntimeError(
                "Progress display not active. Use within display() context."
            )
        task_id = self._progress.add_task(description, total=total)
        self._subtask = task_id
        return task_id

    def update_subtask(
        self,
        task_id: TaskID,
        description: str | None = None,
        advance: float = 0.0,
        completed: float | None = None,
    ) -> None:
        """Update a subtask."""
        if self._progress is None:
            return
        kwargs: dict[str, Any] = {}
        if description is not None:
            kwargs["description"] = description
        if completed is not None:
            kwargs["completed"] = completed
        if advance:
            kwargs["advance"] = advance
        self._progress.update(task_id, **kwargs)

    def finish_subtask(self, task_id: TaskID) -> None:
        """Mark a subtask as complete."""
        if self._progress is None:
            return
        self._progress.update(task_id, completed=self._progress.tasks[0].total)

    def make_callback(self) -> ProgressCallback:
        """Build a ``ProgressCallback`` that drives this display."""
        stage_descriptions = {
            ProgressStage.INITIALIZING: "[blue]Initializing...",
            ProgressStage.VALIDATING: "[yellow]Validating inputs...",
            ProgressStage.PREPARING: "[yellow]Preparing simulation...",
            ProgressStage.SIMULATING: "[cyan]Running simulation...",
            ProgressStage.PROCESSING_RESULTS: "[magenta]Processing results...",
            ProgressStage.FINALIZING: "[blue]Finalizing...",
            ProgressStage.COMPLETE: "[green]Complete",
            ProgressStage.FAILED: "[red]Failed",
        }

        def callback(event: ProgressEvent) -> None:
            description = stage_descriptions.get(event.stage, event.message)
            if event.message and event.stage not in (
                ProgressStage.COMPLETE,
                ProgressStage.FAILED,
            ):
                description = f"{description} {event.message}"
            self.update_main(
                description=description,
                completed=event.progress * 100 if event.progress > 0 else None,
            )

        return callback


@dataclass
class SimulationProgress:
    """Progress state for a running simulation."""

    total_batches: int = 0
    completed_batches: int = 0
    total_particles: int = 0
    completed_particles: int = 0
    elapsed_seconds: float = 0.0

    @property
    def batch_fraction(self) -> float:
        """Fraction of batches completed (0.0 to 1.0)."""
        if self.total_batches <= 0:
            return 0.0
        return min(1.0, self.completed_batches / self.total_batches)

    @property
    def particle_fraction(self) -> float:
        """Fraction of particles completed (0.0 to 1.0)."""
        if self.total_particles <= 0:
            return 0.0
        return min(1.0, self.completed_particles / self.total_particles)


def parse_openmc_output_progress(line: str) -> SimulationProgress | None:
    """Parse an OpenMC stdout line for progress information.

    OpenMC prints lines like ``Batch  10`` and ``=== K_eff ===`` that we can
    use to drive a progress bar. Returns ``None`` if the line carries no
    actionable progress information.
    """
    line = line.strip()
    if not line:
        return None

    # Match "Batch X" pattern
    if line.lower().startswith("batch "):
        parts = line.split()
        if len(parts) >= 2:
            try:
                completed = int(parts[1])
                return SimulationProgress(completed_batches=completed)
            except ValueError:
                return None

    return None


@dataclass
class SystemInfo:
    """System hardware and software information."""

    cpu_count: int
    cpu_count_physical: int
    total_memory_gb: float
    available_memory_gb: float
    platform: str
    python_version: str


@dataclass
class PerformanceMetrics:
    """Performance metrics captured during execution."""

    duration_seconds: float
    cpu_percent_avg: float
    cpu_percent_max: float
    memory_mb_avg: float
    memory_mb_max: float
    samples: int
    start_time: float
    end_time: float


@dataclass
class OptimizationRecommendation:
    """Recommendation for performance optimization."""

    category: str
    severity: str  # info, warning, critical
    message: str
    suggested_action: str


class SystemProfiler:
    """Profiles system resources for OpenMC optimization."""

    def get_system_info(self) -> SystemInfo:
        """Get current system information.

        Returns:
            SystemInfo with hardware and software details.
        """
        import platform
        import sys

        if not _PSUTIL_AVAILABLE:
            cpu_count = os.cpu_count() or 1
            return SystemInfo(
                cpu_count=cpu_count,
                cpu_count_physical=cpu_count,
                total_memory_gb=0.0,
                available_memory_gb=0.0,
                platform=platform.platform(),
                python_version=sys.version,
            )

        memory = psutil.virtual_memory()
        return SystemInfo(
            cpu_count=psutil.cpu_count(logical=True) or 1,
            cpu_count_physical=psutil.cpu_count(logical=False) or 1,
            total_memory_gb=memory.total / (1024**3),
            available_memory_gb=memory.available / (1024**3),
            platform=platform.platform(),
            python_version=sys.version,
        )

    def recommend_thread_count(self, target_jobs: int = 1) -> int:
        """Recommend optimal OpenMP thread count.

        Args:
            target_jobs: Number of concurrent simulation jobs.

        Returns:
            Recommended number of threads.
        """
        info = self.get_system_info()
        target_jobs = max(1, target_jobs)
        threads = max(1, info.cpu_count_physical // target_jobs)
        return min(threads, info.cpu_count)

    def recommend_particle_count(
        self, available_memory_gb: float | None = None
    ) -> int:
        """Recommend particle count based on available memory.

        Args:
            available_memory_gb: Available memory in GB (auto-detect if None).

        Returns:
            Recommended particles per batch.
        """
        if available_memory_gb is None:
            available_memory_gb = self.get_system_info().available_memory_gb
        if available_memory_gb <= 0:
            return 10000
        usable_memory_kb = available_memory_gb * 1024 * 1024 * 0.25
        return max(1000, min(int(usable_memory_kb), 10_000_000))


class PerformanceMonitor:
    """Monitors performance metrics during simulation execution."""

    def __init__(self, sample_interval_seconds: float = 1.0) -> None:
        """Initialize the monitor.

        Args:
            sample_interval_seconds: How often to sample metrics.
        """
        self.sample_interval = sample_interval_seconds
        self._samples: list[dict[str, Any]] = []
        self._monitoring = False
        self._start_time = 0.0
        self._end_time = 0.0

    @contextmanager
    def monitor(self) -> Iterator[PerformanceMonitor]:
        """Context manager for monitoring a code block.

        Yields:
            The monitor instance.
        """
        self._samples = []
        self._monitoring = True
        start_time = time.time()

        sample_thread = threading.Thread(target=self._sample_loop, daemon=True)
        sample_thread.start()

        try:
            yield self
        finally:
            self._monitoring = False
            sample_thread.join(timeout=self.sample_interval * 2)
            self._end_time = time.time()
            self._start_time = start_time

    def _sample_loop(self) -> None:
        """Sample metrics periodically."""
        if not _PSUTIL_AVAILABLE:
            return
        process = psutil.Process(os.getpid())
        while self._monitoring:
            try:
                cpu_percent = process.cpu_percent(interval=None)
                memory_mb = process.memory_info().rss / (1024**2)
                self._samples.append(
                    {
                        "timestamp": time.time(),
                        "cpu_percent": cpu_percent,
                        "memory_mb": memory_mb,
                    }
                )
            except Exception:
                continue  # nosec B112
            time.sleep(self.sample_interval)

    def get_metrics(self) -> PerformanceMetrics:
        """Get aggregated metrics from monitoring.

        Returns:
            PerformanceMetrics with aggregated data.
        """
        start = self._start_time
        end = self._end_time
        if not self._samples:
            return PerformanceMetrics(
                duration_seconds=end - start,
                cpu_percent_avg=0.0,
                cpu_percent_max=0.0,
                memory_mb_avg=0.0,
                memory_mb_max=0.0,
                samples=0,
                start_time=start,
                end_time=end,
            )
        cpu_values = [s["cpu_percent"] for s in self._samples]
        memory_values = [s["memory_mb"] for s in self._samples]
        return PerformanceMetrics(
            duration_seconds=self._end_time - self._start_time,
            cpu_percent_avg=sum(cpu_values) / len(cpu_values),
            cpu_percent_max=max(cpu_values),
            memory_mb_avg=sum(memory_values) / len(memory_values),
            memory_mb_max=max(memory_values),
            samples=len(self._samples),
            start_time=self._start_time,
            end_time=self._end_time,
        )


class OptimizationAdvisor:
    """Provides optimization recommendations for OpenMC simulations."""

    def __init__(self) -> None:
        """Initialize the advisor."""
        self.profiler = SystemProfiler()

    def analyze(
        self,
        threads: int,
        particles: int,
        batches: int,
        target_jobs: int = 1,
    ) -> list[OptimizationRecommendation]:
        """Analyze configuration and provide recommendations.

        Args:
            threads: Configured thread count.
            particles: Configured particles per batch.
            batches: Configured batches.
            target_jobs: Number of concurrent jobs planned.

        Returns:
            List of optimization recommendations.
        """
        recommendations = []
        info = self.profiler.get_system_info()
        recommended_threads = self.profiler.recommend_thread_count(target_jobs)

        if threads > info.cpu_count:
            recommendations.append(
                OptimizationRecommendation(
                    category="threads",
                    severity="warning",
                    message=(
                        f"Configured {threads} threads exceeds CPU count "
                        f"({info.cpu_count} logical cores)"
                    ),
                    suggested_action=f"Reduce threads to {recommended_threads}",
                )
            )
        elif threads < recommended_threads:
            recommendations.append(
                OptimizationRecommendation(
                    category="threads",
                    severity="info",
                    message=(
                        f"Could use more threads. Currently using {threads}, "
                        f"recommended: {recommended_threads}"
                    ),
                    suggested_action=f"Increase threads to {recommended_threads}",
                )
            )

        recommended_particles = self.profiler.recommend_particle_count()
        if particles > recommended_particles * 2:
            recommendations.append(
                OptimizationRecommendation(
                    category="particles",
                    severity="warning",
                    message=(
                        f"Configured {particles:,} particles may exceed available "
                        f"memory ({info.available_memory_gb:.1f}GB)"
                    ),
                    suggested_action=f"Reduce particles to {recommended_particles:,}",
                )
            )

        if batches < 10:
            recommendations.append(
                OptimizationRecommendation(
                    category="batches",
                    severity="warning",
                    message=f"Low batch count ({batches}) may produce unreliable statistics",
                    suggested_action="Increase to at least 50-100 batches",
                )
            )

        if 0 < info.available_memory_gb < 2.0:
            recommendations.append(
                OptimizationRecommendation(
                    category="memory",
                    severity="warning",
                    message=f"Low available memory ({info.available_memory_gb:.1f}GB)",
                    suggested_action="Close other applications or reduce particles",
                )
            )

        if not recommendations:
            recommendations.append(
                OptimizationRecommendation(
                    category="general",
                    severity="info",
                    message="Configuration looks optimal for this system",
                    suggested_action="No changes needed",
                )
            )

        return recommendations

    def format_report(
        self, recommendations: list[OptimizationRecommendation]
    ) -> str:
        """Format recommendations as a text report.

        Args:
            recommendations: List of recommendations.

        Returns:
            Formatted report text.
        """
        severity_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_recs = sorted(
            recommendations, key=lambda r: severity_order.get(r.severity, 3)
        )
        lines = ["=" * 60, "Optimization Recommendations", "=" * 60, ""]
        for rec in sorted_recs:
            marker = {
                "critical": "[CRITICAL]",
                "warning": "[WARNING]",
                "info": "[INFO]",
            }.get(rec.severity, "[INFO]")
            lines.append(f"{marker} {rec.category.upper()}")
            lines.append(f"  Issue:  {rec.message}")
            lines.append(f"  Action: {rec.suggested_action}")
            lines.append("")
        return "\n".join(lines)
