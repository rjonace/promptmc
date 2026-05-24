"""Progress reporting for OpenMC simulations using rich progress bars."""

from __future__ import annotations

import contextlib
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
    metadata: dict = field(default_factory=dict)


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
        kwargs: dict = {}
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
            raise RuntimeError("Progress display not active. Use within display() context.")
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
        kwargs: dict = {}
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
        if self.total_batches <= 0:
            return 0.0
        return min(1.0, self.completed_batches / self.total_batches)

    @property
    def particle_fraction(self) -> float:
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
