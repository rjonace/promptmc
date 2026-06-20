import tempfile
from pathlib import Path
from subprocess import CompletedProcess
from unittest.mock import patch

import pytest
from promptmc.errors import (
    OpenMCError as OpenMCIntegrationError,
)
from promptmc.errors import (
    OpenMCNotFoundError,
    OpenMCValidationError,
)
from promptmc.openmc_integration import (
    ExecutionMode,
    OpenMCInstaller,
    OpenMCRunner,
    OpenMCValidator,
    SimulationResult,
)


def test_simulation_result_defaults():
    """SimulationResult fills sensible defaults for the optional fields."""
    result = SimulationResult(success=True, return_code=0)
    assert result.stdout == ""
    assert result.stderr == ""
    assert result.error is None


def test_run_via_subprocess_converts_completed_process(tmp_path):
    """The subprocess path returns a SimulationResult, not CompletedProcess."""
    runner = OpenMCRunner(ExecutionMode.SUBPROCESS)
    completed = CompletedProcess(
        args=["openmc"], returncode=0, stdout="ok", stderr=""
    )
    with patch(
        "promptmc.openmc_integration.subprocess.run", return_value=completed
    ):
        result = runner._run_via_subprocess(tmp_path, 1, tmp_path, tmp_path)
    assert isinstance(result, SimulationResult)
    assert result.success is True
    assert result.return_code == 0
    assert result.stdout == "ok"


def test_run_simulation_without_openmc():
    """Test that running simulation without OpenMC raises error."""
    with (
        patch("shutil.which", return_value=None),
        patch.dict("sys.modules", {"openmc": None}),
    ):
        runner = OpenMCRunner()

        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".xml", delete=False
        ) as f:
            f.write(b"<settings><run_mode>eigenvalue</run_mode></settings>")
            temp_path = Path(f.name)

        try:
            with pytest.raises((OpenMCNotFoundError, OpenMCIntegrationError)):
                runner.run_simulation(temp_path)
        finally:
            temp_path.unlink()


def test_openmc_runner_initialization():
    """Test OpenMCRunner initialization."""
    runner = OpenMCRunner(ExecutionMode.AUTO)
    assert runner.execution_mode == ExecutionMode.AUTO


def test_check_installation():
    """Test OpenMC installation check."""
    installer = OpenMCInstaller()

    # This will likely fail if OpenMC is not installed, which is expected
    try:
        info = installer.check_installation()
        assert info is not None
        assert hasattr(info, "version")
        assert hasattr(info, "python_available")
        assert hasattr(info, "subprocess_available")
    except OpenMCNotFoundError:
        # Expected if OpenMC is not installed
        pass


def test_check_installation_caches_result():
    """Test that installation check caches the result."""
    installer = OpenMCInstaller()

    try:
        info1 = installer.check_installation()
        info2 = installer.check_installation()
        assert info1 is info2
    except OpenMCNotFoundError:
        # Expected if OpenMC is not installed
        pass


def test_validate_input_file_valid_xml():
    """Test validation of valid XML file."""
    validator = OpenMCValidator()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False
    ) as f:
        f.write("<settings><run_mode>eigenvalue</run_mode></settings>")
        temp_path = Path(f.name)

    try:
        result = validator.validate_input_file(temp_path)
        assert result is True
    finally:
        temp_path.unlink()


def test_validate_input_file_invalid_xml():
    """Test validation of invalid XML file."""
    validator = OpenMCValidator()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".xml", delete=False
    ) as f:
        f.write(
            "<settings><run_mode>eigenvalue</run_mode"
        )  # Missing closing tag
        temp_path = Path(f.name)

    try:
        with pytest.raises(OpenMCValidationError):
            validator.validate_input_file(temp_path)
    finally:
        temp_path.unlink()


def test_validate_input_file_wrong_extension():
    """Test validation of file with wrong extension."""
    validator = OpenMCValidator()

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False
    ) as f:
        f.write("test")
        temp_path = Path(f.name)

    try:
        with pytest.raises(OpenMCValidationError):
            validator.validate_input_file(temp_path)
    finally:
        temp_path.unlink()


def test_validate_input_file_not_exists():
    """Test validation of non-existent file."""
    validator = OpenMCValidator()

    with pytest.raises(OpenMCValidationError):
        validator.validate_input_file("/nonexistent/path.xml")


def test_validate_directory_with_required_files():
    """Test validation of directory with required files."""
    validator = OpenMCValidator()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create required files
        (temp_path / "geometry.xml").write_text("<geometry></geometry>")
        (temp_path / "materials.xml").write_text("<materials></materials>")
        (temp_path / "settings.xml").write_text("<settings></settings>")

        result = validator.validate_input_file(temp_path)
        assert result is True


def test_validate_directory_missing_files():
    """Test validation of directory missing required files."""
    validator = OpenMCValidator()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Only create one file, missing others
        (temp_path / "geometry.xml").write_text("<geometry></geometry>")

        with pytest.raises(OpenMCValidationError):
            validator.validate_input_file(temp_path)


def test_generate_configuration():
    """Test configuration file generation."""
    runner = OpenMCRunner()

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        result = runner.generate_configuration(
            output_path=temp_path,
            particles=10000,
            batches=10,
            inactive=5,
        )

        assert result == temp_path
        assert temp_path.exists()

        # Check file content
        content = temp_path.read_text()
        assert "eigenvalue" in content
        assert "10000" in content
        assert "10" in content
        assert "5" in content
    finally:
        temp_path.unlink()


def test_determine_execution_mode_auto():
    """Test automatic execution mode determination."""
    runner = OpenMCRunner(ExecutionMode.AUTO)

    # This will use the actual installation check
    try:
        mode = runner._determine_execution_mode()
        assert mode in [ExecutionMode.API, ExecutionMode.SUBPROCESS]
    except OpenMCNotFoundError:
        # Expected if OpenMC is not installed
        pass


def test_determine_execution_mode_api():
    """Test API execution mode."""
    runner = OpenMCRunner(ExecutionMode.API)
    try:
        mode = runner._determine_execution_mode()
        assert mode == ExecutionMode.API
    except OpenMCNotFoundError:
        # API mode now triggers installation check; OK if OpenMC not installed
        pass


def test_determine_execution_mode_subprocess():
    """Test subprocess execution mode."""
    runner = OpenMCRunner(ExecutionMode.SUBPROCESS)
    mode = runner._determine_execution_mode()
    assert mode == ExecutionMode.SUBPROCESS
