"""Tests for PromptMC MCP resource handlers."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from promptmc.mcp import resources, tools


@pytest.fixture(autouse=True)
def _clear_history():
    tools.clear_session_history()
    yield
    tools.clear_session_history()


def test_read_cross_sections_configured(tmp_path, monkeypatch):
    xs = tmp_path / "cross_sections.xml"
    xs.write_text("<cross_sections/>")
    monkeypatch.setenv("OPENMC_CROSS_SECTIONS", str(xs))
    payload = json.loads(resources.read_cross_sections())
    assert payload["configured"] is True
    assert payload["path"] == str(xs)
    assert payload["exists"] is True


def test_read_cross_sections_unset(monkeypatch):
    monkeypatch.delenv("OPENMC_CROSS_SECTIONS", raising=False)
    payload = json.loads(resources.read_cross_sections())
    assert payload["configured"] is False
    assert payload["path"] is None


def test_read_history_reflects_dispatched_calls(monkeypatch):
    monkeypatch.delenv("OPENMC_CROSS_SECTIONS", raising=False)
    tools.dispatch("openmc_check_cross_sections", {})
    payload = json.loads(resources.read_history())
    assert len(payload) == 1
    assert payload[0]["tool"] == "openmc_check_cross_sections"
    assert payload[0]["success"] is True


def test_read_uo2_example_lists_files():
    payload = json.loads(resources.read_uo2_example())
    assert payload["available"] is True
    assert "geometry.xml" in payload["files"]


def test_read_uo2_example_missing(monkeypatch):
    monkeypatch.setattr(
        resources,
        "_uo2_example_dir",
        lambda: Path("/nonexistent/uo2"),
    )
    payload = json.loads(resources.read_uo2_example())
    assert payload["available"] is False
    assert payload["files"] == []


def test_resource_readers_cover_all_uris():
    assert set(resources.RESOURCE_READERS) == {
        resources.CROSS_SECTIONS_URI,
        resources.HISTORY_URI,
        resources.UO2_EXAMPLE_URI,
    }
