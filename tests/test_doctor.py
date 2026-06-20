"""Tests for the `promptmc doctor` environment diagnostics command."""

from __future__ import annotations

import json

from promptmc.cli import app
from promptmc.commands import doctor as doctor_mod
from typer.testing import CliRunner

runner = CliRunner()


def _make_cross_sections(tmp_path, libraries):
    """Write a minimal cross_sections.xml referencing ``libraries`` paths."""
    entries = "\n".join(
        f'  <library materials="{mat}" path="{path}" type="neutron"/>'
        for mat, path in libraries
    )
    xs = tmp_path / "cross_sections.xml"
    xs.write_text(f"<cross_sections>\n{entries}\n</cross_sections>\n")
    return xs


def _patch_environment(
    monkeypatch,
    *,
    executable="/usr/local/bin/openmc",
    python_api=True,
    cross_sections=None,
    telemetry=True,
):
    """Drive every doctor check to a known state."""
    monkeypatch.setattr(doctor_mod.shutil, "which", lambda _name: executable)
    monkeypatch.setattr(doctor_mod, "telemetry_available", lambda: telemetry)
    if python_api:
        monkeypatch.setattr(
            doctor_mod,
            "_check_python_api",
            lambda: doctor_mod.Check(
                "openmc_python_api",
                "OpenMC Python API",
                True,
                "ok",
                optional=True,
            ),
        )
    else:
        monkeypatch.setattr(
            doctor_mod,
            "_check_python_api",
            lambda: doctor_mod.Check(
                "openmc_python_api",
                "OpenMC Python API",
                False,
                "absent",
                fix="install it",
                optional=True,
            ),
        )
    if cross_sections is None:
        monkeypatch.delenv("OPENMC_CROSS_SECTIONS", raising=False)
    else:
        monkeypatch.setenv("OPENMC_CROSS_SECTIONS", str(cross_sections))


def test_doctor_all_green(monkeypatch, tmp_path):
    """Executable + valid index + present data + telemetry => ready, exit 0."""
    (tmp_path / "U235.h5").touch()
    xs = _make_cross_sections(tmp_path, [("U235", "U235.h5")])
    _patch_environment(monkeypatch, cross_sections=xs)

    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ready"] is True
    by_name = {c["name"]: c for c in payload["checks"]}
    assert by_name["openmc_executable"]["ok"] is True
    assert by_name["cross_sections"]["ok"] is True
    assert by_name["data_downloaded"]["ok"] is True


def test_doctor_missing_executable_not_ready(monkeypatch, tmp_path):
    (tmp_path / "U235.h5").touch()
    xs = _make_cross_sections(tmp_path, [("U235", "U235.h5")])
    _patch_environment(monkeypatch, executable=None, cross_sections=xs)

    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["ready"] is False
    by_name = {c["name"]: c for c in payload["checks"]}
    assert by_name["openmc_executable"]["ok"] is False
    assert by_name["openmc_executable"]["fix"]


def test_doctor_unset_cross_sections(monkeypatch):
    _patch_environment(monkeypatch, cross_sections=None)

    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    by_name = {c["name"]: c for c in payload["checks"]}
    assert by_name["cross_sections"]["ok"] is False
    # Data files cannot be verified without an index.
    assert by_name["data_downloaded"]["ok"] is False


def test_doctor_missing_data_files(monkeypatch, tmp_path):
    """A valid index whose data files are absent fails the data check."""
    xs = _make_cross_sections(
        tmp_path, [("U235", "U235.h5"), ("U238", "U238.h5")]
    )
    (tmp_path / "U235.h5").touch()  # only one of two present
    _patch_environment(monkeypatch, cross_sections=xs)

    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    by_name = {c["name"]: c for c in payload["checks"]}
    assert by_name["cross_sections"]["ok"] is True
    assert by_name["data_downloaded"]["ok"] is False
    assert "1 of 2" in by_name["data_downloaded"]["detail"]


def test_doctor_optional_failures_still_ready(monkeypatch, tmp_path):
    """Missing Python API and telemetry are optional; env stays ready."""
    (tmp_path / "U235.h5").touch()
    xs = _make_cross_sections(tmp_path, [("U235", "U235.h5")])
    _patch_environment(
        monkeypatch, python_api=False, telemetry=False, cross_sections=xs
    )

    result = runner.invoke(app, ["doctor", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["ready"] is True
    by_name = {c["name"]: c for c in payload["checks"]}
    assert by_name["openmc_python_api"]["optional"] is True
    assert by_name["telemetry_extra"]["optional"] is True


def test_doctor_text_report_lists_fix_hints(monkeypatch, tmp_path):
    """Text mode shows a fix hint and keeps bracketed extras intact."""
    (tmp_path / "U235.h5").touch()
    xs = _make_cross_sections(tmp_path, [("U235", "U235.h5")])
    _patch_environment(monkeypatch, telemetry=False, cross_sections=xs)

    result = runner.invoke(app, ["doctor"])
    # Ready overall (telemetry is optional) so exit 0.
    assert result.exit_code == 0
    assert "How to fix" in result.stdout
    # Rich must not swallow the `[telemetry]` extra as markup.
    assert "promptmc[telemetry]" in result.stdout
