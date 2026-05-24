"""Resource management for OpenMC simulations: limits, monitoring, and cleanup."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from promptmc.errors import ResourceError


@dataclass
class ResourceLimits:
    """Resource limits for simulation execution.

    Attributes:
        max_memory_mb: Maximum memory in MB (None = no limit).
        max_threads: Maximum threads to use (None = system default).
        max_disk_mb: Maximum disk space for outputs in MB.
        max_runtime_seconds: Maximum execution time.
    """

    max_memory_mb: float | None = None
    max_threads: int | None = None
    max_disk_mb: float | None = None
    max_runtime_seconds: float | None = None


@dataclass
class ResourceUsage:
    """Snapshot of current resource usage."""

    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    open_files: int = 0
    disk_used_mb: float = 0.0
    threads: int = 1


class ResourceMonitor:
    """Monitors and enforces resource limits during simulation."""

    def __init__(self, limits: ResourceLimits | None = None) -> None:
        """Initialize the monitor.

        Args:
            limits: Resource limits to enforce. None disables enforcement.
        """
        self.limits = limits or ResourceLimits()
        self._process = self._get_process()

    @staticmethod
    def _get_process() -> Any | None:
        """Get a psutil Process if psutil is available."""
        try:
            import psutil

            return psutil.Process(os.getpid())
        except ImportError:
            return None

    def current_usage(self) -> ResourceUsage:
        """Snapshot current resource usage."""
        if self._process is None:
            return ResourceUsage()

        try:
            memory_info = self._process.memory_info()
            cpu_percent = self._process.cpu_percent(interval=None)
            try:
                open_files = len(self._process.open_files())
            except Exception:
                open_files = 0
            try:
                num_threads = self._process.num_threads()
            except Exception:
                num_threads = 1

            return ResourceUsage(
                memory_mb=memory_info.rss / (1024 * 1024),
                cpu_percent=cpu_percent,
                open_files=open_files,
                threads=num_threads,
            )
        except Exception:
            return ResourceUsage()

    def check_limits(self) -> str | None:
        """Check whether any limits are exceeded.

        Returns:
            Description of the violated limit, or None if all limits are OK.
        """
        usage = self.current_usage()

        if self.limits.max_memory_mb is not None and usage.memory_mb > self.limits.max_memory_mb:
            return (
                f"Memory limit exceeded: {usage.memory_mb:.1f}MB > "
                f"{self.limits.max_memory_mb:.1f}MB"
            )

        if self.limits.max_threads is not None and usage.threads > self.limits.max_threads:
            return f"Thread limit exceeded: {usage.threads} > {self.limits.max_threads}"

        return None

    def enforce(self) -> None:
        """Raise ResourceError if limits are exceeded."""
        violation = self.check_limits()
        if violation:
            raise ResourceError(message=violation)


class TempDirectoryManager:
    """Context-managed temp directory with automatic cleanup."""

    def __init__(
        self,
        prefix: str = "openmc-",
        keep_on_error: bool = True,
        base_dir: Path | None = None,
    ) -> None:
        self.prefix = prefix
        self.keep_on_error = keep_on_error
        self.base_dir = base_dir
        self.path: Path | None = None
        self._error_occurred = False

    def __enter__(self) -> Path:
        self.path = Path(
            tempfile.mkdtemp(prefix=self.prefix, dir=str(self.base_dir) if self.base_dir else None)
        )
        return self.path

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type is not None:
            self._error_occurred = True

        if self.path is None or not self.path.exists():
            return

        if self._error_occurred and self.keep_on_error:
            return

        shutil.rmtree(self.path, ignore_errors=True)


@dataclass
class DiskSpace:
    """Disk space information."""

    total_mb: float
    used_mb: float
    free_mb: float

    @property
    def percent_used(self) -> float:
        if self.total_mb <= 0:
            return 0.0
        return (self.used_mb / self.total_mb) * 100


def get_disk_space(path: Path) -> DiskSpace:
    """Get disk space information for a given path."""
    usage = shutil.disk_usage(path)
    return DiskSpace(
        total_mb=usage.total / (1024 * 1024),
        used_mb=usage.used / (1024 * 1024),
        free_mb=usage.free / (1024 * 1024),
    )


def check_disk_space(path: Path, required_mb: float) -> None:
    """Check that the path has sufficient disk space.

    Raises:
        ResourceError: If insufficient disk space.
    """
    space = get_disk_space(path)
    if space.free_mb < required_mb:
        raise ResourceError(
            f"Insufficient disk space at {path}: "
            f"{space.free_mb:.1f}MB free, {required_mb:.1f}MB required"
        )


@dataclass
class SimulationWorkspace:
    """A managed workspace for a simulation run.

    Provides a clean directory tree, automatic cleanup, and disk-space
    pre-flight checks.
    """

    root: Path
    keep_on_error: bool = True
    cleanup_on_exit: bool = True
    _created_paths: list[Path] = field(default_factory=list)
    _error_occurred: bool = False

    def create_subdirectory(self, name: str) -> Path:
        """Create a subdirectory under the workspace root."""
        subdir = self.root / name
        subdir.mkdir(parents=True, exist_ok=True)
        self._created_paths.append(subdir)
        return subdir

    def cleanup(self) -> None:
        """Clean up the workspace."""
        if self._error_occurred and self.keep_on_error:
            return
        if self.root.exists():
            shutil.rmtree(self.root, ignore_errors=True)


@contextmanager
def simulation_workspace(
    root: Path | None = None,
    keep_on_error: bool = True,
    required_disk_mb: float | None = None,
) -> Iterator[SimulationWorkspace]:
    """Context manager for a simulation workspace.

    Args:
        root: Root directory. If None, a temp directory is used.
        keep_on_error: Keep the workspace if an exception occurs.
        required_disk_mb: Pre-flight check for required disk space.

    Yields:
        A SimulationWorkspace instance.
    """
    if root is None:
        temp = Path(tempfile.mkdtemp(prefix="openmc-workspace-"))
        owns_root = True
    else:
        root.mkdir(parents=True, exist_ok=True)
        temp = root
        owns_root = False

    if required_disk_mb is not None:
        check_disk_space(temp, required_disk_mb)

    workspace = SimulationWorkspace(
        root=temp,
        keep_on_error=keep_on_error,
        cleanup_on_exit=owns_root,
    )

    try:
        yield workspace
    except Exception:
        workspace._error_occurred = True
        raise
    finally:
        if workspace.cleanup_on_exit:
            workspace.cleanup()
