"""OpenMC integration module for API wrapper and subprocess invocation."""

from __future__ import annotations

import os
import shutil
import subprocess  # nosec B404
import xml.etree.ElementTree as ET  # nosec B405
from defusedxml.ElementTree import parse as defused_parse
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

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


class OpenMCIntegrationError(Exception):
    """Base exception for OpenMC integration errors."""


class OpenMCNotFoundError(OpenMCIntegrationError):
    """Raised when OpenMC is not found."""


class OpenMCValidationError(OpenMCIntegrationError):
    """Raised when OpenMC input validation fails."""


class OpenMCExecutionError(OpenMCIntegrationError):
    """Raised when OpenMC simulation execution fails."""


class OpenMCIntegration:
    """Manages OpenMC integration supporting both Python API and subprocess invocation."""

    def __init__(self, execution_mode: ExecutionMode = ExecutionMode.AUTO) -> None:
        """Initialize OpenMC integration.

        Args:
            execution_mode: Mode of execution (API, subprocess, or auto-detect).
        """
        self.execution_mode = execution_mode
        self._openmc_info: OpenMCInfo | None = None
        self._openmc_module: Any = None

    def check_installation(self) -> OpenMCInfo:
        """Check OpenMC installation and return information.

        Returns:
            OpenMCInfo describing the installation.

        Raises:
            OpenMCNotFoundError: If neither the Python API nor the executable is available.
        """
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
                version = self._query_executable_version(executable_path) or "unknown"

        if not subprocess_available and not python_available:
            raise OpenMCNotFoundError(
                "OpenMC not found. Please install OpenMC via:\n"
                "- pip install openmc (for Python API)\n"
                "- or install OpenMC executable and add to PATH"
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

    def validate_input_file(self, input_path: str | Path) -> bool:
        """Validate an OpenMC input file or directory.

        Args:
            input_path: Path to input file or directory.

        Returns:
            True if valid.

        Raises:
            OpenMCValidationError: If validation fails.
        """
        input_path = Path(input_path)

        if input_path.is_file():
            if input_path.suffix != ".xml":
                raise OpenMCValidationError(
                    f"Input file must be XML format, got: {input_path.suffix}"
                )
            self._validate_xml_structure(input_path)
        elif input_path.is_dir():
            missing = [name for name in REQUIRED_INPUT_FILES if not (input_path / name).exists()]
            if missing:
                raise OpenMCValidationError(f"Missing required files in directory: {missing}")
            for file_name in REQUIRED_INPUT_FILES:
                self._validate_xml_structure(input_path / file_name)
        else:
            raise OpenMCValidationError(f"Path does not exist: {input_path}")

        return True

    @staticmethod
    def _validate_xml_structure(xml_path: Path) -> None:
        """Validate that a file contains parseable XML.

        Raises:
            OpenMCValidationError: If the XML is malformed.
        """
        try:
            defused_parse(xml_path)
        except ET.ParseError as e:
            raise OpenMCValidationError(f"Invalid XML in {xml_path}: {e}") from e

    def run_simulation(
        self,
        input_path: str | Path,
        threads: int = 1,
        output_path: str | Path | None = None,
        cwd: str | Path | None = None,
    ) -> subprocess.CompletedProcess:
        """Run an OpenMC simulation.

        Args:
            input_path: Path to input file or directory.
            threads: Number of OpenMP threads.
            output_path: Output directory for results (default: input directory).
            cwd: Working directory for execution (default: input directory).

        Returns:
            ``subprocess.CompletedProcess`` with execution results.

        Raises:
            OpenMCNotFoundError: If OpenMC is not available.
            OpenMCExecutionError: If subprocess invocation fails unexpectedly.
        """
        input_path = Path(input_path)
        resolved_input_dir = input_path if input_path.is_dir() else input_path.parent
        output_path = Path(output_path) if output_path else resolved_input_dir
        cwd = Path(cwd) if cwd else resolved_input_dir

        mode = self._determine_execution_mode()

        if mode == ExecutionMode.API and self._openmc_module is not None:
            return self._run_via_api(input_path, threads, output_path, cwd)
        return self._run_via_subprocess(input_path, threads, output_path, cwd)

    def _determine_execution_mode(self) -> ExecutionMode:
        """Determine the execution mode based on configuration and availability."""
        if self.execution_mode == ExecutionMode.API:
            # Trigger a check so self._openmc_module is populated
            self.check_installation()
            return ExecutionMode.API
        if self.execution_mode == ExecutionMode.SUBPROCESS:
            return ExecutionMode.SUBPROCESS

        info = self.check_installation()
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
    ) -> subprocess.CompletedProcess:
        """Run simulation using the OpenMC Python API."""
        os.environ["OMP_NUM_THREADS"] = str(threads)

        original_cwd = os.getcwd()
        os.chdir(cwd)
        try:
            try:
                # Re-import to satisfy type checkers; cached import is fine
                import openmc
                from typing import Any, cast

                cast(Any, openmc).run(output_path=str(output_path))
                return subprocess.CompletedProcess[str](
                    args=["openmc", str(input_path)],
                    returncode=0,
                    stdout="Simulation completed successfully via API",
                    stderr="",
                )
            except Exception as e:  # noqa: BLE001 - convert to CompletedProcess result
                return subprocess.CompletedProcess[str](
                    args=["openmc", str(input_path)],
                    returncode=1,
                    stdout="",
                    stderr=str(e),
                )
        finally:
            os.chdir(original_cwd)

    def _run_via_subprocess(
        self,
        input_path: Path,  # noqa: ARG002 – kept for API symmetry with _run_via_api
        threads: int,
        output_path: Path,
        cwd: Path,
    ) -> subprocess.CompletedProcess:
        """Run simulation using the OpenMC executable via subprocess.

        OpenMC reads its inputs from ``cwd``. The output directory is
        controlled via the ``-s``/``--output`` flag if it differs from cwd.
        """
        cmd = ["openmc"]
        if output_path.resolve() != cwd.resolve():
            cmd.extend(["-s", str(output_path)])

        env = os.environ.copy()
        env["OMP_NUM_THREADS"] = str(threads)

        # Ensure output path exists if specified
        output_path.mkdir(parents=True, exist_ok=True)

        try:
            return subprocess.run(  # nosec B603
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                env=env,
                check=False,
            )
        except FileNotFoundError as e:
            raise OpenMCNotFoundError("OpenMC executable not found in PATH") from e
        except OSError as e:
            raise OpenMCExecutionError(f"Failed to run OpenMC subprocess: {e}") from e

    def generate_configuration(
        self,
        output_path: str | Path,
        particles: int = 10000,
        batches: int = 10,
        inactive: int = 5,
    ) -> Path:
        """Generate a basic OpenMC settings.xml configuration file.

        Args:
            output_path: Path where the configuration file will be saved.
            particles: Number of particles per batch.
            batches: Number of batches.
            inactive: Number of inactive batches.

        Returns:
            Path to the generated configuration file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        root = ET.Element("settings")
        ET.SubElement(root, "run_mode").text = "eigenvalue"
        ET.SubElement(root, "batches").text = str(batches)
        ET.SubElement(root, "inactive").text = str(inactive)
        ET.SubElement(root, "particles").text = str(particles)

        output_elem = ET.SubElement(root, "output")
        ET.SubElement(output_elem, "path").text = str(output_path.parent)

        tree = ET.ElementTree(root)
        ET.indent(tree, space="  ")
        tree.write(output_path, encoding="utf-8", xml_declaration=True)

        return output_path

    def parse_output(self, output_path: str | Path) -> dict:
        """Parse OpenMC simulation output files.

        Args:
            output_path: Path to output directory.

        Returns:
            Dictionary with discovered files and any extracted summary metrics.
        """
        output_path = Path(output_path)
        results: dict = {"path": str(output_path), "files": []}

        if not output_path.is_dir():
            return results

        candidates = ["summary.h5", "tallies.out"]
        for name in candidates:
            file_path = output_path / name
            if file_path.exists():
                results["files"].append(str(file_path))

        # Wildcard patterns
        for pattern in ("statepoint.*.h5",):
            for match in sorted(output_path.glob(pattern)):
                results["files"].append(str(match))

        summary_file = output_path / "summary.h5"
        if summary_file.exists():
            self._extract_summary_metrics(summary_file, results)

        return results

    @staticmethod
    def _extract_summary_metrics(summary_file: Path, results: dict) -> None:
        """Extract summary metrics from summary.h5 if h5py is available."""
        try:
            import h5py
        except ImportError:
            return

        try:
            with h5py.File(summary_file, "r") as f:
                if "k-effective" in f:
                    results["k_effective"] = list(f["k-effective"][()])
                results["n_batches"] = int(f.attrs.get("n_batches", 0) or 0)
                results["n_particles"] = int(f.attrs.get("n_particles", 0) or 0)
        except Exception:
            # File present but unreadable; surface only what we have
            return
