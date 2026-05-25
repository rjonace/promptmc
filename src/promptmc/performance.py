"""Performance optimization and monitoring tools for OpenMC simulations."""

from __future__ import annotations

import multiprocessing
import os
import time
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass


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
            SystemInfo with hardware and software details
        """
        import platform
        import sys

        try:
            import psutil

            memory = psutil.virtual_memory()
            return SystemInfo(
                cpu_count=psutil.cpu_count(logical=True) or 1,
                cpu_count_physical=psutil.cpu_count(logical=False) or 1,
                total_memory_gb=memory.total / (1024**3),
                available_memory_gb=memory.available / (1024**3),
                platform=platform.platform(),
                python_version=sys.version,
            )
        except ImportError:
            return SystemInfo(
                cpu_count=multiprocessing.cpu_count(),
                cpu_count_physical=multiprocessing.cpu_count(),
                total_memory_gb=0.0,
                available_memory_gb=0.0,
                platform=platform.platform(),
                python_version=sys.version,
            )

    def recommend_thread_count(self, target_jobs: int = 1) -> int:
        """Recommend optimal OpenMP thread count.

        Args:
            target_jobs: Number of concurrent simulation jobs

        Returns:
            Recommended number of threads
        """
        info = self.get_system_info()

        if target_jobs <= 0:
            target_jobs = 1

        # Use physical cores divided by concurrent jobs
        threads = max(1, info.cpu_count_physical // target_jobs)

        # Cap at logical core count
        return min(threads, info.cpu_count)

    def recommend_particle_count(
        self, available_memory_gb: float | None = None
    ) -> int:
        """Recommend particle count based on available memory.

        Args:
            available_memory_gb: Available memory in GB (auto-detect if None)

        Returns:
            Recommended particles per batch
        """
        if available_memory_gb is None:
            info = self.get_system_info()
            available_memory_gb = info.available_memory_gb

        # Rough heuristic: ~1KB per particle in memory
        # Use 25% of available memory for particles
        if available_memory_gb <= 0:
            return 10000  # Conservative default

        usable_memory_kb = available_memory_gb * 1024 * 1024 * 0.25
        recommended = int(usable_memory_kb)

        # Clamp to reasonable range
        return max(1000, min(recommended, 10_000_000))


class PerformanceMonitor:
    """Monitors performance metrics during simulation execution."""

    def __init__(self, sample_interval_seconds: float = 1.0) -> None:
        """Initialize the monitor.

        Args:
            sample_interval_seconds: How often to sample metrics
        """
        self.sample_interval = sample_interval_seconds
        self._samples: list[dict] = []
        self._monitoring = False

    @contextmanager
    def monitor(self) -> Iterator[PerformanceMonitor]:
        """Context manager for monitoring a code block.

        Yields:
            The monitor instance

        Example:
            >>> monitor = PerformanceMonitor()
            >>> with monitor.monitor():
            ...     run_simulation()
            >>> metrics = monitor.get_metrics()
        """
        import threading

        self._samples = []
        self._monitoring = True
        start_time = time.time()

        # Start sampling thread
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
        try:
            import psutil

            process = psutil.Process(os.getpid())

            while self._monitoring:
                try:
                    cpu_percent = process.cpu_percent(interval=None)
                    memory_info = process.memory_info()
                    memory_mb = memory_info.rss / (1024**2)

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
        except ImportError:
            # psutil not available
            pass

    def get_metrics(self) -> PerformanceMetrics:
        """Get aggregated metrics from monitoring.

        Returns:
            PerformanceMetrics with aggregated data
        """
        if not self._samples:
            return PerformanceMetrics(
                duration_seconds=getattr(self, "_end_time", 0)
                - getattr(self, "_start_time", 0),
                cpu_percent_avg=0.0,
                cpu_percent_max=0.0,
                memory_mb_avg=0.0,
                memory_mb_max=0.0,
                samples=0,
                start_time=getattr(self, "_start_time", 0),
                end_time=getattr(self, "_end_time", 0),
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
            threads: Configured thread count
            particles: Configured particles per batch
            batches: Configured batches
            target_jobs: Number of concurrent jobs planned

        Returns:
            List of optimization recommendations
        """
        recommendations = []
        info = self.profiler.get_system_info()

        # Thread analysis
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

        # Particle analysis
        recommended_particles = self.profiler.recommend_particle_count()
        if particles > recommended_particles * 2:
            recommendations.append(
                OptimizationRecommendation(
                    category="particles",
                    severity="warning",
                    message=(
                        f"Configured {particles:,} particles may exceed available memory "
                        f"({info.available_memory_gb:.1f}GB)"
                    ),
                    suggested_action=f"Reduce particles to {recommended_particles:,}",
                )
            )

        # Batch analysis
        if batches < 10:
            recommendations.append(
                OptimizationRecommendation(
                    category="batches",
                    severity="warning",
                    message=f"Low batch count ({batches}) may produce unreliable statistics",
                    suggested_action="Increase to at least 50-100 batches",
                )
            )

        # Memory analysis
        if info.available_memory_gb < 2.0 and info.available_memory_gb > 0:
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
            recommendations: List of recommendations

        Returns:
            Formatted report text
        """
        lines = []
        lines.append("=" * 60)
        lines.append("Optimization Recommendations")
        lines.append("=" * 60)
        lines.append("")

        severity_order = {"critical": 0, "warning": 1, "info": 2}
        sorted_recs = sorted(
            recommendations, key=lambda r: severity_order.get(r.severity, 3)
        )

        for rec in sorted_recs:
            severity_marker = {
                "critical": "[CRITICAL]",
                "warning": "[WARNING]",
                "info": "[INFO]",
            }.get(rec.severity, "[INFO]")

            lines.append(f"{severity_marker} {rec.category.upper()}")
            lines.append(f"  Issue:  {rec.message}")
            lines.append(f"  Action: {rec.suggested_action}")
            lines.append("")

        return "\n".join(lines)
