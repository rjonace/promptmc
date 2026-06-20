"""Core OpenMC integration: installation checks, input validation, and execution."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import xml.etree.ElementTree as ET  # nosec B405
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, cast

from defusedxml.ElementTree import parse as defused_parse

from promptmc._typing import PathLike
from promptmc.errors import (
    OpenMCExecutionError,
    OpenMCNotFoundError,
    OpenMCValidationError,
)
from promptmc.provenance import write_xml_with_provenance

# OpenMC required input files for a directory-based simulation
REQUIRED_INPUT_FILES = ("geometry.xml", "materials.xml", "settings.xml")


class ExecutionMode(Enum):
    """Mode of OpenMC execution."""

    API = "api"
    SUBPROCESS = "subprocess"
    AUTO = "auto"


@dataclass
class OpenMCInfo:
    """Information about OpenMC installation."""

    version: str
    executable_path: str
    python_available: bool
    subprocess_available: bool


@dataclass
class SimulationResult:
    """Outcome of an OpenMC simulation run.

    This is the execution result (did the run succeed, what did it print).
    For parsed physics outputs (k-eff, tallies) see
    ``promptmc.visualization.SimulationResult``.
    """

    success: bool
    return_code: int
    stdout: str = ""
    stderr: str = ""
    error: str | None = None


class OpenMCInstaller:
    """Manages OpenMC installation detection."""

    def __init__(self) -> None:
        self._openmc_info: OpenMCInfo | None = None
        self._openmc_module: Any = None

    def check_installation(self) -> OpenMCInfo:
        """Check OpenMC installation and return information."""
        if self._openmc_info is not None:
            return self._openmc_info

        executable_path = shutil.which("openmc")
        subprocess_available = executable_path is not None

        python_available = False
        version = "not found"
        try:
            import openmc as openmc_module

            self._openmc_module = openmc_module
            python_available = True
            version = getattr(openmc_module, "__version__", "unknown")
        except ImportError:
            if subprocess_available and executable_path is not None:
                version = (
                    self._query_executable_version(executable_path) or "unknown"
                )

        if not subprocess_available and not python_available:
            raise OpenMCNotFoundError(
                "OpenMC not found. Please install OpenMC via one of the following:\n"
                "- Conda (recommended): conda create -n openmc-env -c conda-forge openmc\n"
                "  (On Apple Silicon, use: conda create -n openmc-env --platform osx-64 -c conda-forge openmc)\n"
                "- Spack: spack install py-openmc\n"
                "- Docker: docker run openmc/openmc:latest\n"
                "- Source: Build executable, then run 'python -m pip install .' from the repo root\n"
                "For details, see: https://docs.openmc.org/en/stable/quickinstall.html"
            )

        self._openmc_info = OpenMCInfo(
            version=version,
            executable_path=executable_path or "",
            python_available=python_available,
            subprocess_available=subprocess_available,
        )
        return self._openmc_info

    @staticmethod
    def _query_executable_version(executable_path: str) -> str | None:
        """Query OpenMC executable for its version string."""
        try:
            result = subprocess.run(  # nosec B603
                [executable_path, "--version"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            output = (result.stdout or result.stderr or "").strip()
            return output.splitlines()[0] if output else None
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return None


class OpenMCValidator:
    """Validates OpenMC XML inputs."""

    def validate_input_file(self, input_path: PathLike) -> bool:
        """Validate an OpenMC input file or directory."""
        input_path = Path(input_path)

        if input_path.is_file():
            if input_path.suffix != ".xml":
                raise OpenMCValidationError(
                    f"Input file must be XML format, got: {input_path.suffix}"
                )
            self._validate_xml_structure(input_path)
        elif input_path.is_dir():
            missing = [
                name
                for name in REQUIRED_INPUT_FILES
                if not (input_path / name).exists()
            ]
            if missing:
                raise OpenMCValidationError(
                    f"Missing required files in directory: {missing}"
                )
            for file_name in REQUIRED_INPUT_FILES:
                self._validate_xml_structure(input_path / file_name)
        else:
            raise OpenMCValidationError(f"Path does not exist: {input_path}")

        return True

    @staticmethod
    def _validate_xml_structure(xml_path: Path) -> None:
        """Validate that a file contains parseable XML."""
        try:
            defused_parse(xml_path)
        except ET.ParseError as e:
            raise OpenMCValidationError(
                f"Invalid XML in {xml_path}: {e}"
            ) from e


class OpenMCRunner:
    """Runs OpenMC simulations."""

    def __init__(
        self, execution_mode: ExecutionMode = ExecutionMode.AUTO
    ) -> None:
        self.execution_mode = execution_mode
        self.installer = OpenMCInstaller()

    def run_simulation(
        self,
        input_path: PathLike,
        threads: int = 1,
        output_path: PathLike | None = None,
        cwd: PathLike | None = None,
    ) -> SimulationResult:
        """Run an OpenMC simulation."""
        input_path = Path(input_path)
        resolved_input_dir = (
            input_path if input_path.is_dir() else input_path.parent
        )
        output_path = Path(output_path) if output_path else resolved_input_dir
        cwd = Path(cwd) if cwd else resolved_input_dir

        mode = self._determine_execution_mode()

        if (
            mode == ExecutionMode.API
            and self.installer._openmc_module is not None
        ):
            return self._run_via_api(input_path, threads, output_path, cwd)
        return self._run_via_subprocess(input_path, threads, output_path, cwd)

    def _determine_execution_mode(self) -> ExecutionMode:
        if self.execution_mode == ExecutionMode.API:
            self.installer.check_installation()
            return ExecutionMode.API
        if self.execution_mode == ExecutionMode.SUBPROCESS:
            return ExecutionMode.SUBPROCESS

        info = self.installer.check_installation()
        if info.python_available:
            return ExecutionMode.API
        if info.subprocess_available:
            return ExecutionMode.SUBPROCESS
        raise OpenMCNotFoundError("OpenMC not available for execution")

    def _run_via_api(
        self,
        input_path: Path,
        threads: int,
        output_path: Path,
        cwd: Path,
    ) -> SimulationResult:
        original_threads = os.environ.get("OMP_NUM_THREADS")
        os.environ["OMP_NUM_THREADS"] = str(threads)
        try:
            # openmc is an optional dependency; import inline to allow
            # the core library to function without it installed
            import openmc

            cast(Any, openmc).run(cwd=str(cwd), threads=threads)
            return SimulationResult(
                success=True,
                return_code=0,
                stdout="Simulation completed successfully via API",
            )
        except Exception as e:
            return SimulationResult(
                success=False,
                return_code=1,
                stderr=str(e),
                error=str(e),
            )
        finally:
            if original_threads is None:
                os.environ.pop("OMP_NUM_THREADS", None)
            else:
                os.environ["OMP_NUM_THREADS"] = original_threads

    def _run_via_subprocess(
        self,
        input_path: Path,
        threads: int,
        output_path: Path,
        cwd: Path,
    ) -> SimulationResult:
        cmd = ["openmc"]
        if output_path.resolve() != cwd.resolve():
            cmd.extend(["-s", str(output_path)])

        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = str(threads)

        output_path.mkdir(parents=True, exist_ok=True)

        try:
            completed = subprocess.run(  # nosec B603
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
            return SimulationResult(
                success=completed.returncode == 0,
                return_code=completed.returncode,
                stdout=completed.stdout or "",
                stderr=completed.stderr or "",
            )
        except FileNotFoundError as e:
            raise OpenMCNotFoundError(
                "OpenMC executable not found in PATH"
            ) from e
        except OSError as e:
            raise OpenMCExecutionError(
                f"Failed to run OpenMC subprocess: {e}"
            ) from e

    def generate_configuration(
        self,
        output_path: PathLike,
        particles: int = 10000,
        batches: int = 10,
        inactive: int = 5,
    ) -> Path:
        """Generate a basic OpenMC settings.xml configuration file."""
        output_path = Path(output_path)

        root = ET.Element("settings")
        ET.SubElement(root, "run_mode").text = "eigenvalue"
        ET.SubElement(root, "batches").text = str(batches)
        ET.SubElement(root, "inactive").text = str(inactive)
        ET.SubElement(root, "particles").text = str(particles)

        output_elem = ET.SubElement(root, "output")
        ET.SubElement(output_elem, "path").text = str(output_path.parent)

        return write_xml_with_provenance(root, output_path)
