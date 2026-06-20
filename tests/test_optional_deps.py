"""Tests for graceful degradation when optional extras are absent.

The packages themselves stay installed in the test environment; these tests
flip the module-level ``_*_AVAILABLE`` guards to exercise the fallback paths
that run when ``promptmc`` is installed without the corresponding extra.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
from promptmc import assistant, batch, progress, resources


def test_system_profiler_without_psutil(monkeypatch):
    monkeypatch.setattr(progress, "_PSUTIL_AVAILABLE", False)
    info = progress.SystemProfiler().get_system_info()
    assert info.cpu_count >= 1
    assert info.cpu_count_physical >= 1
    assert info.total_memory_gb == 0.0
    assert info.available_memory_gb == 0.0


def test_performance_monitor_without_psutil(monkeypatch):
    monkeypatch.setattr(progress, "_PSUTIL_AVAILABLE", False)
    monitor = progress.PerformanceMonitor(sample_interval_seconds=0.01)
    with monitor.monitor():
        pass
    metrics = monitor.get_metrics()
    assert metrics.samples == 0
    assert metrics.cpu_percent_avg == 0.0


def test_resource_monitor_without_psutil(monkeypatch):
    monkeypatch.setattr(resources, "_PSUTIL_AVAILABLE", False)
    monitor = resources.ResourceMonitor()
    assert monitor._process is None
    usage = monitor.current_usage()
    assert usage == resources.ResourceUsage()
    assert monitor.check_limits() is None


def test_load_yaml_spec_without_pyyaml(monkeypatch):
    monkeypatch.setattr(batch, "_YAML_AVAILABLE", False)
    with tempfile.TemporaryDirectory() as tmp:
        spec_path = Path(tmp) / "spec.yaml"
        spec_path.write_text("name: x\n")
        with pytest.raises(ImportError, match="promptmc\\[yaml\\]"):
            batch.load_batch_spec(spec_path)


def test_save_yaml_spec_without_pyyaml(monkeypatch):
    monkeypatch.setattr(batch, "_YAML_AVAILABLE", False)
    spec = batch.BatchSpec(
        name="x",
        base_input=Path("in.xml"),
        output_root=Path("out"),
    )
    with (
        tempfile.TemporaryDirectory() as tmp,
        pytest.raises(ImportError, match="promptmc\\[yaml\\]"),
    ):
        batch.save_batch_spec(spec, Path(tmp) / "spec.yaml")


def test_json_spec_still_works_without_pyyaml(monkeypatch):
    monkeypatch.setattr(batch, "_YAML_AVAILABLE", False)
    spec = batch.BatchSpec(
        name="x",
        base_input=Path("in.xml"),
        output_root=Path("out"),
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = batch.save_batch_spec(spec, Path(tmp) / "spec.json")
        loaded = batch.load_batch_spec(path)
        assert loaded.name == "x"


def test_gemini_client_without_genai(monkeypatch):
    monkeypatch.setattr(assistant, "_GENAI_AVAILABLE", False)
    client = assistant.GeminiClient(api_key="dummy-key")
    with pytest.raises(ImportError, match="promptmc\\[llm\\]"):
        client.generate_structured(
            "system", "user", assistant.GeminiPlanResponse
        )


def test_assistant_imports_when_google_absent():
    """Importing assistant must not crash when ``google`` is uninstalled.

    ``find_spec`` on the dotted ``google.genai`` imports the parent package,
    so a missing ``google`` raises ``ModuleNotFoundError`` instead of
    returning ``None`` -- the core-only install path.
    """
    import importlib
    import importlib.util

    real_find_spec = importlib.util.find_spec

    def fake_find_spec(name, *args, **kwargs):
        if name == "google.genai":
            raise ModuleNotFoundError("No module named 'google'")
        return real_find_spec(name, *args, **kwargs)

    importlib.util.find_spec = fake_find_spec
    try:
        reloaded = importlib.reload(assistant)
        assert reloaded._GENAI_AVAILABLE is False
    finally:
        importlib.util.find_spec = real_find_spec
        importlib.reload(assistant)
