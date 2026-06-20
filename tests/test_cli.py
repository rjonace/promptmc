"""Tests for CLI module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from promptmc.cli import app
from typer.testing import CliRunner

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_SETTINGS_XML = """\
<?xml version="1.0"?>
<settings>
  <run_mode>eigenvalue</run_mode>
  <batches>10</batches>
  <inactive>5</inactive>
  <particles>1000</particles>
</settings>
"""


def _write_settings(path: Path) -> Path:
    p = path / "settings.xml"
    p.write_text(MINIMAL_SETTINGS_XML)
    return p


# ---------------------------------------------------------------------------
# --version / --help
# ---------------------------------------------------------------------------


def test_version():
    """Test --version flag."""
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "promptmc" in result.stdout


def test_verbose_flag():
    """Test --verbose flag doesn't crash."""
    result = runner.invoke(app, ["--verbose", "--help"])
    assert result.exit_code == 0


def test_help():
    """Top-level --help."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def test_run_help():
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0


def test_run_invalid_mode():
    """Invalid --mode causes exit 1."""
    with tempfile.TemporaryDirectory() as tmp:
        p = _write_settings(Path(tmp))
        result = runner.invoke(app, ["run", str(p), "--mode", "badmode"])
    assert result.exit_code == 1


@patch("promptmc.commands.run.OpenMCValidator")
@patch("promptmc.commands.run.OpenMCRunner")
def test_run_success(mock_runner_cls, mock_validator_cls):
    mock_validator = MagicMock()
    mock_validator.validate_input_file.return_value = True
    mock_validator_cls.return_value = mock_validator

    mock_runner = MagicMock()
    proc = MagicMock()
    proc.returncode = 0
    proc.stdout = "Simulation complete"
    proc.stderr = ""
    mock_runner.run_simulation.return_value = proc
    mock_runner_cls.return_value = mock_runner

    with tempfile.TemporaryDirectory() as tmp:
        p = _write_settings(Path(tmp))
        result = runner.invoke(app, ["run", str(p)])

    assert result.exit_code == 0


@patch("promptmc.commands.run.OpenMCValidator")
@patch("promptmc.commands.run.OpenMCRunner")
def test_run_simulation_failure(mock_runner_cls, mock_validator_cls):
    mock_validator = MagicMock()
    mock_validator.validate_input_file.return_value = True
    mock_validator_cls.return_value = mock_validator

    mock_runner = MagicMock()
    proc = MagicMock()
    proc.returncode = 1
    proc.stdout = ""
    proc.stderr = "Segfault"
    mock_runner.run_simulation.return_value = proc
    mock_runner_cls.return_value = mock_runner

    with tempfile.TemporaryDirectory() as tmp:
        p = _write_settings(Path(tmp))
        result = runner.invoke(app, ["run", str(p)])

    assert result.exit_code == 1


@patch("promptmc.commands.run.OpenMCValidator")
def test_run_validation_error(mock_validator_cls):
    from promptmc.openmc_integration import OpenMCValidationError

    mock_validator = MagicMock()
    mock_validator.validate_input_file.side_effect = OpenMCValidationError(
        "bad xml"
    )
    mock_validator_cls.return_value = mock_validator

    with tempfile.TemporaryDirectory() as tmp:
        p = _write_settings(Path(tmp))
        result = runner.invoke(app, ["run", str(p)])

    assert result.exit_code == 1
    assert "Validation error" in result.stdout


@patch("promptmc.commands.run.OpenMCValidator")
@patch("promptmc.commands.run.OpenMCRunner")
def test_run_not_found_error(mock_runner_cls, mock_validator_cls):
    from promptmc.openmc_integration import OpenMCNotFoundError

    mock_validator = MagicMock()
    mock_validator.validate_input_file.return_value = True
    mock_validator_cls.return_value = mock_validator

    mock_runner = MagicMock()
    mock_runner.run_simulation.side_effect = OpenMCNotFoundError("not found")
    mock_runner_cls.return_value = mock_runner

    with tempfile.TemporaryDirectory() as tmp:
        p = _write_settings(Path(tmp))
        result = runner.invoke(app, ["run", str(p)])

    assert result.exit_code == 1
    assert "OpenMC not found" in result.stdout


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------


def test_validate_help():
    result = runner.invoke(app, ["validate", "--help"])
    assert result.exit_code == 0


@patch("promptmc.commands.validate.OpenMCValidator")
def test_validate_success(mock_validator_cls):
    mock_validator = MagicMock()
    mock_validator.validate_input_file.return_value = True
    mock_validator_cls.return_value = mock_validator

    with tempfile.TemporaryDirectory() as tmp:
        p = _write_settings(Path(tmp))
        result = runner.invoke(app, ["validate", str(p)])

    assert result.exit_code == 0
    assert "passed" in result.stdout


@patch("promptmc.commands.validate.OpenMCValidator")
def test_validate_fail(mock_validator_cls):
    mock_validator = MagicMock()
    mock_validator.validate_input_file.return_value = False
    mock_validator_cls.return_value = mock_validator

    with tempfile.TemporaryDirectory() as tmp:
        p = _write_settings(Path(tmp))
        result = runner.invoke(app, ["validate", str(p)])

    assert result.exit_code == 1


@patch("promptmc.commands.validate.OpenMCValidator")
def test_validate_with_schema(mock_validator_cls):
    mock_validator = MagicMock()
    mock_validator.validate_input_file.return_value = True
    mock_validator_cls.return_value = mock_validator

    with tempfile.TemporaryDirectory() as tmp:
        p = _write_settings(Path(tmp))
        result = runner.invoke(app, ["validate", str(p), "--schema"])

    assert result.exit_code in [0, 1]


# ---------------------------------------------------------------------------
# info
# ---------------------------------------------------------------------------


def test_info_help():
    result = runner.invoke(app, ["info", "--help"])
    assert result.exit_code == 0


def test_info_command():
    """Info exits 0 (OpenMC present) or 1 (not present)."""
    result = runner.invoke(app, ["info"])
    assert result.exit_code in [0, 1]


@patch("promptmc.commands.info.OpenMCInstaller")
def test_info_success(mock_installer_cls):
    mock_info = MagicMock()
    mock_info.version = "0.14.0"
    mock_info.python_available = True
    mock_info.subprocess_available = True
    mock_info.executable_path = "/usr/local/bin/openmc"
    mock_installer = MagicMock()
    mock_installer.check_installation.return_value = mock_info
    mock_installer_cls.return_value = mock_installer

    result = runner.invoke(app, ["info"])
    assert result.exit_code == 0
    assert "0.14.0" in result.stdout


@patch("promptmc.commands.info.OpenMCInstaller")
def test_info_not_found(mock_installer_cls):
    from promptmc.openmc_integration import OpenMCNotFoundError

    mock_installer = MagicMock()
    mock_installer.check_installation.side_effect = OpenMCNotFoundError(
        "not found"
    )
    mock_installer_cls.return_value = mock_installer

    result = runner.invoke(app, ["info"])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# list-templates
# ---------------------------------------------------------------------------


def test_list_templates():
    result = runner.invoke(app, ["list-templates"])
    assert result.exit_code == 0
    assert "criticality" in result.stdout.lower()


# ---------------------------------------------------------------------------
# template
# ---------------------------------------------------------------------------


def test_template_help():
    result = runner.invoke(app, ["template", "--help"])
    assert result.exit_code == 0


def test_template_invalid_type():
    result = runner.invoke(app, ["template", "badtype"])
    assert result.exit_code == 1
    assert "is not a valid TemplateType" in result.stdout


def test_template_criticality(tmp_path):
    out = tmp_path / "settings.xml"
    result = runner.invoke(
        app, ["template", "criticality", "--output", str(out)]
    )
    assert result.exit_code == 0
    assert out.exists()


def test_template_fixed_source(tmp_path):
    out = tmp_path / "settings.xml"
    result = runner.invoke(
        app,
        [
            "template",
            "fixed_source",
            "--output",
            str(out),
            "--particles",
            "5000",
        ],
    )
    assert result.exit_code == 0
    assert out.exists()


# ---------------------------------------------------------------------------
# plan
# ---------------------------------------------------------------------------


def test_plan_help():
    result = runner.invoke(app, ["plan", "--help"])
    assert result.exit_code == 0
    assert "plain-English" in result.stdout or "Plain-English" in result.stdout
    assert "GEMINI_API_KEY" in result.stdout


def test_plan_shielding_plan():
    result = runner.invoke(
        app, ["plan", "make a shielding run with 1 million particles"]
    )
    assert result.exit_code == 0
    assert "shielding" in result.stdout
    assert "1,000,000" in result.stdout


def test_plan_write_settings(tmp_path):
    output = tmp_path / "settings.xml"
    result = runner.invoke(
        app,
        [
            "plan",
            "make a reactor pin calculation with 20000 particles",
            "--write",
            "-o",
            str(output),
        ],
    )
    assert result.exit_code == 0
    assert output.exists()


def test_plan_llm_fails_fast():
    # Run with --llm but without setting GEMINI_API_KEY in the environment
    import os
    from unittest.mock import patch

    with patch.dict(os.environ, {}, clear=True):
        result = runner.invoke(app, ["plan", "criticality run", "--llm"])
        assert result.exit_code == 1
        assert "GEMINI_API_KEY" in result.stdout


# ---------------------------------------------------------------------------
# batch
# ---------------------------------------------------------------------------


def test_batch_help():
    result = runner.invoke(app, ["batch", "--help"])
    assert result.exit_code == 0


def test_batch_invalid_parallel_mode(tmp_path):
    spec = tmp_path / "batch.yaml"
    spec.write_text("name: test\nbase_input: sim\noutput_root: out\n")
    result = runner.invoke(app, ["batch", str(spec), "--parallel", "badmode"])
    assert result.exit_code == 1


@patch("promptmc.commands.batch.BatchRunner")
@patch("promptmc.commands.batch.load_batch_spec")
def test_batch_success(mock_load, mock_runner_cls, tmp_path):
    spec = tmp_path / "batch.yaml"
    spec.write_text("name: test\nbase_input: sim\noutput_root: out\n")

    mock_spec = MagicMock()
    mock_spec.name = "test"
    mock_spec.description = "desc"
    mock_spec.base_input = "sim"
    mock_spec.output_root = "out"
    mock_load.return_value = mock_spec

    mock_summary = MagicMock()
    mock_summary.batch_id = "abc123"
    mock_summary.total_jobs = 1
    mock_summary.successful_jobs = 1
    mock_summary.failed_jobs = 0
    mock_summary.total_duration_seconds = 1.5
    mock_summary.average_duration_seconds = 1.5
    mock_runner = MagicMock()
    mock_runner.run_batch.return_value = mock_summary
    mock_runner_cls.return_value = mock_runner

    result = runner.invoke(app, ["batch", str(spec)])
    assert result.exit_code == 0
    assert "Batch Complete" in result.stdout


@patch("promptmc.commands.batch.BatchRunner")
@patch("promptmc.commands.batch.load_batch_spec")
def test_batch_with_failures(mock_load, mock_runner_cls, tmp_path):
    spec = tmp_path / "batch.yaml"
    spec.write_text("name: test\nbase_input: sim\noutput_root: out\n")

    mock_spec = MagicMock()
    mock_spec.name = "test"
    mock_spec.description = "desc"
    mock_spec.base_input = "sim"
    mock_spec.output_root = "out"
    mock_load.return_value = mock_spec

    mock_summary = MagicMock()
    mock_summary.batch_id = "abc123"
    mock_summary.total_jobs = 2
    mock_summary.successful_jobs = 1
    mock_summary.failed_jobs = 1
    mock_summary.total_duration_seconds = 2.0
    mock_summary.average_duration_seconds = 1.0
    mock_runner = MagicMock()
    mock_runner.run_batch.return_value = mock_summary
    mock_runner_cls.return_value = mock_runner

    result = runner.invoke(app, ["batch", str(spec)])
    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------


def test_analyze_help():
    result = runner.invoke(app, ["analyze", "--help"])
    assert result.exit_code == 0


@patch("promptmc.commands.analyze.ResultParser")
@patch("promptmc.commands.analyze.ResultVisualizer")
def test_analyze_success(mock_viz_cls, mock_parser_cls, tmp_path):
    mock_result = MagicMock()
    mock_parser = MagicMock()
    mock_parser.parse_results.return_value = mock_result
    mock_parser_cls.return_value = mock_parser

    mock_viz = MagicMock()
    mock_viz.format_text_report.return_value = "[bold]Report[/bold]"
    mock_viz_cls.return_value = mock_viz

    result = runner.invoke(app, ["analyze", str(tmp_path)])
    assert result.exit_code == 0


@patch("promptmc.commands.analyze.ResultParser")
@patch("promptmc.commands.analyze.ResultVisualizer")
def test_analyze_json_to_stdout(mock_viz_cls, mock_parser_cls, tmp_path):
    """`analyze --json` emits the result dict to stdout, no text report."""
    mock_result = MagicMock()
    mock_parser = MagicMock()
    mock_parser.parse_results.return_value = mock_result
    mock_parser_cls.return_value = mock_parser

    mock_viz = MagicMock()
    mock_viz.result_to_dict.return_value = {
        "k_effective": 1.0,
        "n_batches": 100,
    }
    mock_viz_cls.return_value = mock_viz

    result = runner.invoke(app, ["analyze", str(tmp_path), "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["k_effective"] == 1.0
    mock_viz.result_to_dict.assert_called_once_with(mock_result)
    mock_viz.format_text_report.assert_not_called()


# ---------------------------------------------------------------------------
# optimize
# ---------------------------------------------------------------------------


def test_optimize_help():
    result = runner.invoke(app, ["optimize", "--help"])
    assert result.exit_code == 0


def test_optimize_default():
    result = runner.invoke(app, ["optimize"])
    assert result.exit_code == 0


def test_optimize_custom():
    result = runner.invoke(
        app,
        [
            "optimize",
            "--threads",
            "4",
            "--particles",
            "50000",
            "--batches",
            "200",
            "--jobs",
            "2",
        ],
    )
    assert result.exit_code == 0


# ---------------------------------------------------------------------------
# system-info
# ---------------------------------------------------------------------------


def test_system_info_help():
    result = runner.invoke(app, ["system-info", "--help"])
    assert result.exit_code == 0


def test_system_info():
    result = runner.invoke(app, ["system-info"])
    assert result.exit_code == 0
    assert "CPU" in result.stdout


# ---------------------------------------------------------------------------
# schema-check
# ---------------------------------------------------------------------------


def test_schema_check_help():
    result = runner.invoke(app, ["schema-check", "--help"])
    assert result.exit_code == 0


def test_schema_check_valid_file(tmp_path):
    p = _write_settings(tmp_path)
    result = runner.invoke(app, ["schema-check", str(p)])
    assert result.exit_code in [0, 1]


def test_schema_check_directory(tmp_path):
    _write_settings(tmp_path)
    result = runner.invoke(app, ["schema-check", str(tmp_path)])
    assert result.exit_code in [0, 1]


# ---------------------------------------------------------------------------
# error paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cmd",
    [
        ["run", "--help"],
        ["validate", "--help"],
        ["doctor", "--help"],
        ["info", "--help"],
        ["template", "--help"],
        ["list-templates"],
        ["plan", "--help"],
        ["batch", "--help"],
        ["analyze", "--help"],
        ["optimize", "--help"],
        ["system-info", "--help"],
        ["schema-check", "--help"],
    ],
)
def test_all_commands_have_help(cmd):
    """Every command must respond to --help with exit code 0."""
    result = runner.invoke(app, cmd)
    assert result.exit_code == 0, f"Command {cmd} failed: {result.stdout}"


# ---------------------------------------------------------------------------
# --json structured output (validate, plan, info; analyze covered above)
# ---------------------------------------------------------------------------


def test_validate_json_valid(tmp_path):
    """`validate --json --schema` emits a parseable, valid=True payload."""
    p = _write_settings(tmp_path)
    result = runner.invoke(app, ["validate", str(p), "--schema", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["xml_valid"] is True
    assert payload["schema_checked"] is True
    assert payload["valid"] is True
    assert payload["issues"] == []


def test_validate_json_malformed_xml(tmp_path):
    """Malformed XML reports valid=False as data and exits 1, not a crash."""
    bad = tmp_path / "bad.xml"
    bad.write_text("<settings><batches>")
    result = runner.invoke(app, ["validate", str(bad), "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["xml_valid"] is False
    assert payload["valid"] is False
    assert payload["xml_error"]


def test_plan_json(tmp_path):
    """`plan --json` emits the structured plan with the rebuild command."""
    result = runner.invoke(
        app, ["plan", "shielding run with 2M particles", "--json"]
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["template_type"] == "shielding"
    assert payload["particles"] == 2_000_000
    assert payload["source"] == "local"
    assert payload["command"].startswith("promptmc template shielding")
    assert "written" not in payload


def test_plan_json_write(tmp_path):
    """`plan --json --write` reports the written path and creates the file."""
    out = tmp_path / "settings.xml"
    result = runner.invoke(
        app,
        ["plan", "criticality run", "--json", "--write", "--output", str(out)],
    )
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["written"] == str(out)
    assert out.exists()


@patch("promptmc.commands.info.OpenMCInstaller")
def test_info_json(mock_installer_cls):
    """`info --json` emits installation fields as JSON."""
    mock_info = MagicMock()
    mock_info.version = "0.14.0"
    mock_info.python_available = True
    mock_info.subprocess_available = True
    mock_info.executable_path = "/usr/local/bin/openmc"
    mock_installer = MagicMock()
    mock_installer.check_installation.return_value = mock_info
    mock_installer_cls.return_value = mock_installer

    result = runner.invoke(app, ["info", "--json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["version"] == "0.14.0"
    assert payload["python_api"] is True
    assert payload["executable_path"] == "/usr/local/bin/openmc"


@patch("promptmc.commands.info.OpenMCInstaller")
def test_info_json_not_found(mock_installer_cls):
    """`info --json` still emits JSON (and exits 1) when OpenMC is absent."""
    from promptmc.openmc_integration import OpenMCNotFoundError

    mock_installer = MagicMock()
    mock_installer.check_installation.side_effect = OpenMCNotFoundError("nope")
    mock_installer_cls.return_value = mock_installer

    result = runner.invoke(app, ["info", "--json"])
    assert result.exit_code == 1
    payload = json.loads(result.stdout)
    assert payload["version"] == "not found"
    assert payload["python_api"] is False
