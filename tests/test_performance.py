"""Tests for performance optimization tools."""

import time

from promptmc.progress import (
    OptimizationAdvisor,
    OptimizationRecommendation,
    PerformanceMonitor,
    SystemInfo,
    SystemProfiler,
)


def test_system_profiler_get_info():
    """Test getting system info."""
    profiler = SystemProfiler()
    info = profiler.get_system_info()

    assert isinstance(info, SystemInfo)
    assert info.cpu_count >= 1
    assert info.cpu_count_physical >= 1
    assert info.platform != ""
    assert info.python_version != ""


def test_recommend_thread_count_single_job():
    """Test thread recommendation for single job."""
    profiler = SystemProfiler()
    threads = profiler.recommend_thread_count(target_jobs=1)
    assert threads >= 1


def test_recommend_thread_count_multiple_jobs():
    """Test thread recommendation for multiple jobs."""
    profiler = SystemProfiler()
    threads = profiler.recommend_thread_count(target_jobs=4)
    assert threads >= 1


def test_recommend_thread_count_zero_jobs():
    """Test thread recommendation handles zero jobs."""
    profiler = SystemProfiler()
    threads = profiler.recommend_thread_count(target_jobs=0)
    assert threads >= 1


def test_recommend_particle_count():
    """Test particle count recommendation."""
    profiler = SystemProfiler()
    particles = profiler.recommend_particle_count()
    assert particles >= 1000
    assert particles <= 10_000_000


def test_recommend_particle_count_low_memory():
    """Test particle count recommendation with low memory."""
    profiler = SystemProfiler()
    particles = profiler.recommend_particle_count(available_memory_gb=0.1)
    assert particles >= 1000


def test_performance_monitor_basic():
    """Test basic performance monitoring."""
    monitor = PerformanceMonitor(sample_interval_seconds=0.1)

    with monitor.monitor():
        time.sleep(0.3)

    metrics = monitor.get_metrics()
    assert metrics.duration_seconds >= 0.2
    assert metrics.start_time > 0
    assert metrics.end_time > metrics.start_time


def test_performance_monitor_no_samples():
    """Test monitor handles case with no samples."""
    monitor = PerformanceMonitor(sample_interval_seconds=10.0)

    with monitor.monitor():
        pass  # Exit immediately

    metrics = monitor.get_metrics()
    assert metrics is not None


def test_optimization_advisor_initialization():
    """Test OptimizationAdvisor initialization."""
    advisor = OptimizationAdvisor()
    assert advisor.profiler is not None


def test_analyze_returns_recommendations():
    """Test analyze returns recommendations list."""
    advisor = OptimizationAdvisor()
    recommendations = advisor.analyze(
        threads=1,
        particles=10000,
        batches=100,
        target_jobs=1,
    )
    assert isinstance(recommendations, list)
    assert len(recommendations) >= 1


def test_analyze_low_batches_warning():
    """Test that low batches produces warning."""
    advisor = OptimizationAdvisor()
    recommendations = advisor.analyze(
        threads=1,
        particles=10000,
        batches=5,  # Too low
        target_jobs=1,
    )

    batch_warnings = [r for r in recommendations if r.category == "batches"]
    assert len(batch_warnings) >= 1
    assert batch_warnings[0].severity == "warning"


def test_analyze_excessive_threads():
    """Test that excessive threads produces warning."""
    advisor = OptimizationAdvisor()
    recommendations = advisor.analyze(
        threads=10000,  # Way too many
        particles=10000,
        batches=100,
        target_jobs=1,
    )

    thread_warnings = [
        r
        for r in recommendations
        if r.category == "threads" and r.severity == "warning"
    ]
    assert len(thread_warnings) >= 1


def test_format_report():
    """Test formatting recommendations as report."""
    advisor = OptimizationAdvisor()
    recommendations = [
        OptimizationRecommendation(
            category="test",
            severity="info",
            message="Test message",
            suggested_action="Test action",
        ),
    ]

    report = advisor.format_report(recommendations)
    assert "Optimization Recommendations" in report
    assert "Test message" in report
    assert "Test action" in report


def test_format_report_severity_ordering():
    """Test that report orders by severity."""
    advisor = OptimizationAdvisor()
    recommendations = [
        OptimizationRecommendation("test", "info", "Info msg", "Action"),
        OptimizationRecommendation(
            "test", "critical", "Critical msg", "Action"
        ),
        OptimizationRecommendation("test", "warning", "Warning msg", "Action"),
    ]

    report = advisor.format_report(recommendations)

    # Critical should come before warning, warning before info
    critical_pos = report.find("Critical msg")
    warning_pos = report.find("Warning msg")
    info_pos = report.find("Info msg")

    assert critical_pos < warning_pos
    assert warning_pos < info_pos
