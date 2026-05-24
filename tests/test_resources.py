"""Tests for resource management module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from promptmc.errors import ResourceError
from promptmc.resources import (
    DiskSpace,
    ResourceLimits,
    ResourceMonitor,
    ResourceUsage,
    TempDirectoryManager,
    check_disk_space,
    get_disk_space,
    simulation_workspace,
)


def test_resource_limits_creation():
    """Test ResourceLimits creation."""
    limits = ResourceLimits(
        max_memory_mb=1024,
        max_threads=4,
        max_disk_mb=10000,
    )
    assert limits.max_memory_mb == 1024
    assert limits.max_threads == 4


def test_resource_limits_defaults():
    """Test ResourceLimits defaults (all None)."""
    limits = ResourceLimits()
    assert limits.max_memory_mb is None
    assert limits.max_threads is None


def test_resource_monitor_current_usage():
    """Test ResourceMonitor returns current usage."""
    monitor = ResourceMonitor()
    usage = monitor.current_usage()
    assert isinstance(usage, ResourceUsage)
    assert usage.memory_mb >= 0


def test_resource_monitor_no_limits():
    """Test that monitor with no limits never violates."""
    monitor = ResourceMonitor()
    assert monitor.check_limits() is None


def test_resource_monitor_memory_limit_exceeded():
    """Test that low memory limit triggers violation."""
    monitor = ResourceMonitor(ResourceLimits(max_memory_mb=0.001))
    violation = monitor.check_limits()
    if monitor._process is not None:
        # psutil available; should detect violation
        assert violation is not None
        assert "Memory" in violation


def test_resource_monitor_enforce_no_violation():
    """Test enforce does nothing when within limits."""
    monitor = ResourceMonitor()
    monitor.enforce()  # Should not raise


def test_temp_directory_manager_cleanup():
    """Test that temp directory is cleaned up."""
    with TempDirectoryManager() as path:
        assert path.exists()
        assert path.is_dir()
        # Create a file inside
        (path / "test.txt").write_text("hello")

    # After exit, directory should be removed
    assert not path.exists()


def test_temp_directory_manager_keep_on_error():
    """Test that directory is kept on error."""
    captured_path: list[Path] = []

    with pytest.raises(RuntimeError), TempDirectoryManager(keep_on_error=True) as path:
        captured_path.append(path)
        raise RuntimeError("test error")

    # Directory should still exist
    assert captured_path[0].exists()
    # Cleanup manually
    import shutil

    shutil.rmtree(captured_path[0])


def test_temp_directory_manager_remove_on_error():
    """Test that directory is removed on error when keep_on_error=False."""
    captured_path: list[Path] = []

    with pytest.raises(RuntimeError), TempDirectoryManager(keep_on_error=False) as path:
        captured_path.append(path)
        raise RuntimeError("test error")

    assert not captured_path[0].exists()


def test_get_disk_space():
    """Test getting disk space info."""
    with tempfile.TemporaryDirectory() as temp_dir:
        space = get_disk_space(Path(temp_dir))
        assert space.total_mb > 0
        assert space.free_mb > 0
        assert space.percent_used >= 0


def test_disk_space_percent():
    """Test disk space percent calculation."""
    space = DiskSpace(total_mb=100, used_mb=25, free_mb=75)
    assert space.percent_used == 25.0


def test_disk_space_zero_total():
    """Test disk space with zero total."""
    space = DiskSpace(total_mb=0, used_mb=0, free_mb=0)
    assert space.percent_used == 0.0


def test_check_disk_space_sufficient():
    """Test check_disk_space when sufficient."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Should not raise for tiny requirement
        check_disk_space(Path(temp_dir), required_mb=0.1)


def test_check_disk_space_insufficient():
    """Test check_disk_space raises when insufficient."""
    with tempfile.TemporaryDirectory() as temp_dir, pytest.raises(ResourceError):
        # Require absurd amount
        check_disk_space(Path(temp_dir), required_mb=10**12)


def test_simulation_workspace_creates_subdirectory():
    """Test creating subdirectories in workspace."""
    with simulation_workspace() as ws:
        sub = ws.create_subdirectory("results")
        assert sub.exists()
        assert sub.parent == ws.root


def test_simulation_workspace_cleanup():
    """Test workspace is cleaned up on exit."""
    captured: list[Path] = []

    with simulation_workspace() as ws:
        captured.append(ws.root)

    assert not captured[0].exists()


def test_simulation_workspace_keep_on_error():
    """Test workspace kept on error."""
    captured: list[Path] = []

    with pytest.raises(RuntimeError), simulation_workspace(keep_on_error=True) as ws:
        captured.append(ws.root)
        raise RuntimeError("test")

    assert captured[0].exists()
    import shutil

    shutil.rmtree(captured[0])


def test_simulation_workspace_with_explicit_root():
    """Test workspace with caller-supplied root."""
    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir) / "ws"
        with simulation_workspace(root=root) as ws:
            assert ws.root == root
            assert root.exists()
        # Caller-supplied root is not deleted by the context manager
        assert root.exists()
