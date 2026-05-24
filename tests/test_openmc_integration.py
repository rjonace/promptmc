"""Tests for OpenMC integration module."""

import tempfile
from pathlib import Path

import pytest
from promptmc.openmc_integration import (
    ExecutionMode,
    OpenMCIntegration,
    OpenMCIntegrationError,
    OpenMCNotFoundError,
    OpenMCValidationError,
)


def test_openmc_integration_initialization():
    """Test OpenMCIntegration initialization."""
    integration = OpenMCIntegration(ExecutionMode.AUTO)
    assert integration.execution_mode == ExecutionMode.AUTO


def test_check_installation():
    """Test OpenMC installation check."""
    integration = OpenMCIntegration()

    # This will likely fail if OpenMC is not installed, which is expected
    try:
        info = integration.check_installation()
        assert info is not None
        assert hasattr(info, "version")
        assert hasattr(info, "python_available")
        assert hasattr(info, "subprocess_available")
    except OpenMCNotFoundError:
        # Expected if OpenMC is not installed
        pass


def test_check_installation_caches_result():
    """Test that installation check caches the result."""
    integration = OpenMCIntegration()

    try:
        info1 = integration.check_installation()
        info2 = integration.check_installation()
        assert info1 is info2
    except OpenMCNotFoundError:
        # Expected if OpenMC is not installed
        pass


def test_validate_input_file_valid_xml():
    """Test validation of valid XML file."""
    integration = OpenMCIntegration()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write("<settings><run_mode>eigenvalue</run_mode></settings>")
        temp_path = Path(f.name)

    try:
        result = integration.validate_input_file(temp_path)
        assert result is True
    finally:
        temp_path.unlink()


def test_validate_input_file_invalid_xml():
    """Test validation of invalid XML file."""
    integration = OpenMCIntegration()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write("<settings><run_mode>eigenvalue</run_mode")  # Missing closing tag
        temp_path = Path(f.name)

    try:
        with pytest.raises(OpenMCValidationError):
            integration.validate_input_file(temp_path)
    finally:
        temp_path.unlink()


def test_validate_input_file_wrong_extension():
    """Test validation of file with wrong extension."""
    integration = OpenMCIntegration()

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("test")
        temp_path = Path(f.name)

    try:
        with pytest.raises(OpenMCValidationError):
            integration.validate_input_file(temp_path)
    finally:
        temp_path.unlink()


def test_validate_input_file_not_exists():
    """Test validation of non-existent file."""
    integration = OpenMCIntegration()

    with pytest.raises(OpenMCValidationError):
        integration.validate_input_file("/nonexistent/path.xml")


def test_validate_directory_with_required_files():
    """Test validation of directory with required files."""
    integration = OpenMCIntegration()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create required files
        (temp_path / "geometry.xml").write_text("<geometry></geometry>")
        (temp_path / "materials.xml").write_text("<materials></materials>")
        (temp_path / "settings.xml").write_text("<settings></settings>")

        result = integration.validate_input_file(temp_path)
        assert result is True


def test_validate_directory_missing_files():
    """Test validation of directory missing required files."""
    integration = OpenMCIntegration()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Only create one file, missing others
        (temp_path / "geometry.xml").write_text("<geometry></geometry>")

        with pytest.raises(OpenMCValidationError):
            integration.validate_input_file(temp_path)


def test_generate_configuration():
    """Test configuration file generation."""
    integration = OpenMCIntegration()

    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
        temp_path = Path(f.name)

    try:
        result = integration.generate_configuration(
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


def test_parse_output_directory():
    """Test parsing output directory."""
    integration = OpenMCIntegration()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create some dummy output files
        (temp_path / "tallies.out").write_text("test output")

        result = integration.parse_output(temp_path)

        assert result["path"] == str(temp_path)
        assert "tallies.out" in [Path(f).name for f in result["files"]]


def test_parse_output_nonexistent():
    """Test parsing non-existent output directory."""
    integration = OpenMCIntegration()

    result = integration.parse_output("/nonexistent/path")
    assert result["path"] == "/nonexistent/path"
    assert result["files"] == []


def test_determine_execution_mode_auto():
    """Test automatic execution mode determination."""
    integration = OpenMCIntegration(ExecutionMode.AUTO)

    # This will use the actual installation check
    try:
        mode = integration._determine_execution_mode()
        assert mode in [ExecutionMode.API, ExecutionMode.SUBPROCESS]
    except OpenMCNotFoundError:
        # Expected if OpenMC is not installed
        pass


def test_determine_execution_mode_api():
    """Test API execution mode."""
    integration = OpenMCIntegration(ExecutionMode.API)
    try:
        mode = integration._determine_execution_mode()
        assert mode == ExecutionMode.API
    except OpenMCNotFoundError:
        # API mode now triggers installation check; OK if OpenMC not installed
        pass


def test_determine_execution_mode_subprocess():
    """Test subprocess execution mode."""
    integration = OpenMCIntegration(ExecutionMode.SUBPROCESS)
    mode = integration._determine_execution_mode()
    assert mode == ExecutionMode.SUBPROCESS


def test_run_simulation_without_openmc():
    """Test that running simulation without OpenMC raises error."""
    integration = OpenMCIntegration()

    with tempfile.NamedTemporaryFile(mode="wb", suffix=".xml", delete=False) as f:
        f.write(b"<settings><run_mode>eigenvalue</run_mode></settings>")
        temp_path = Path(f.name)

    try:
        with pytest.raises((OpenMCNotFoundError, OpenMCIntegrationError)):
            integration.run_simulation(temp_path)
    finally:
        temp_path.unlink()
