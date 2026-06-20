"""Result visualization for OpenMC simulations."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, cast

from promptmc._typing import PathLike

try:  # noqa: SIM105
    import openmc

    _openmc: Any = openmc
except ImportError:  # pragma: no cover - the openmc extra is optional
    _openmc = None


@dataclass
class SimulationResult:
    """Parsed OpenMC simulation result."""

    statepoint_path: Path | None = None
    summary_path: Path | None = None
    tallies_path: Path | None = None
    k_effective: float | None = None
    k_effective_std: float | None = None
    n_batches: int = 0
    n_particles: int = 0
    runtime_seconds: float = 0.0
    tallies: dict[str, Any] = field(default_factory=dict)
    raw_data: dict[str, Any] = field(default_factory=dict)


class ResultParser:
    """Parses OpenMC simulation results from output files."""

    def parse_results(self, output_path: PathLike) -> SimulationResult:
        """Parse simulation results from output directory.

        Args:
            output_path: Path to output directory

        Returns:
            Parsed simulation result
        """
        output_path = Path(output_path)
        result = SimulationResult()

        # Find statepoint files
        statepoints = sorted(output_path.glob("statepoint.*.h5"))
        if statepoints:
            result.statepoint_path = statepoints[-1]  # Use latest
            self._parse_statepoint(result.statepoint_path, result)

        # Find summary file
        summary_file = output_path / "summary.h5"
        if summary_file.exists():
            result.summary_path = summary_file
            self._parse_summary(summary_file, result)

        # Find tallies file
        tallies_file = output_path / "tallies.out"
        if tallies_file.exists():
            result.tallies_path = tallies_file
            self._parse_tallies(tallies_file, result)

        return result

    def _parse_statepoint(
        self, statepoint_path: Path, result: SimulationResult
    ) -> None:
        """Parse a statepoint file into ``result``.

        Prefers the OpenMC ``StatePoint`` API (``keff`` superseded the
        deprecated ``k_combined`` dataset in 0.13.1) and falls back to a
        direct h5py read when the optional ``openmc`` package is absent.

        Args:
            statepoint_path: Path to statepoint file
            result: Result object to populate
        """
        if self._parse_statepoint_via_openmc(statepoint_path, result):
            return
        self._parse_statepoint_via_h5py(statepoint_path, result)

    def _parse_statepoint_via_openmc(
        self, statepoint_path: Path, result: SimulationResult
    ) -> bool:
        """Parse a statepoint using the modern OpenMC ``StatePoint`` API.

        Args:
            statepoint_path: Path to statepoint file
            result: Result object to populate

        Returns:
            ``True`` when OpenMC is available and the file was parsed,
            otherwise ``False`` so the caller can fall back to h5py.
        """
        if _openmc is None:
            return False
        try:
            statepoint = _openmc.StatePoint(statepoint_path)
        except Exception as e:
            result.raw_data["statepoint_error"] = str(e)
            return False
        try:
            if statepoint.run_mode == "eigenvalue":
                keff = statepoint.keff
                result.k_effective = float(keff.nominal_value)
                result.k_effective_std = float(keff.std_dev)
            result.n_batches = int(statepoint.n_batches)
            result.n_particles = int(statepoint.n_particles)
            total = statepoint.runtime.get("total")
            if total is not None:
                result.runtime_seconds = float(total)
        finally:
            statepoint.close()
        return True

    def _parse_statepoint_via_h5py(
        self, statepoint_path: Path, result: SimulationResult
    ) -> None:
        """Parse a statepoint by reading the HDF5 file directly.

        Args:
            statepoint_path: Path to statepoint file
            result: Result object to populate
        """
        try:
            import h5py

            with h5py.File(statepoint_path, "r") as f:
                # Extract k-effective if available
                k_key = "keff" if "keff" in f else "k_combined"
                if k_key in f:
                    k_data = f[k_key][()]
                    if hasattr(k_data, "__len__") and len(k_data) >= 2:
                        result.k_effective = float(k_data[0])
                        result.k_effective_std = float(k_data[1])

                # Extract batch and particle counts
                if "n_batches" in f.attrs:
                    result.n_batches = int(f.attrs["n_batches"])
                if "n_particles" in f.attrs:
                    result.n_particles = int(f.attrs["n_particles"])

                # Extract runtime
                if "runtime" in f:
                    runtime_data = f["runtime"]
                    if "total" in runtime_data.attrs:
                        result.runtime_seconds = float(
                            runtime_data.attrs["total"]
                        )

                # Store raw attributes
                result.raw_data["statepoint_attrs"] = dict(f.attrs)

        except ImportError:
            # h5py not available
            pass
        except Exception as e:
            result.raw_data["statepoint_error"] = str(e)

    def _parse_summary(
        self, summary_path: Path, result: SimulationResult
    ) -> None:
        """Parse summary HDF5 file.

        Args:
            summary_path: Path to summary file
            result: Result object to populate
        """
        try:
            import h5py

            with h5py.File(summary_path, "r") as f:
                summary_data = {}
                for key in f.attrs:
                    summary_data[key] = f.attrs[key]
                result.raw_data["summary"] = summary_data

        except ImportError:
            pass
        except Exception as e:
            result.raw_data["summary_error"] = str(e)

    def _parse_tallies(
        self, tallies_path: Path, result: SimulationResult
    ) -> None:
        """Parse tallies output file.

        Args:
            tallies_path: Path to tallies file
            result: Result object to populate
        """
        try:
            content = tallies_path.read_text()
            result.tallies["raw_content"] = content
            result.tallies["line_count"] = len(content.splitlines())
        except Exception as e:
            result.tallies["error"] = str(e)


class ResultVisualizer:
    """Visualizes OpenMC simulation results."""

    def format_text_report(self, result: SimulationResult) -> str:
        """Format result as a text report.

        Args:
            result: Simulation result

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 60)
        lines.append("OpenMC Simulation Results")
        lines.append("=" * 60)
        lines.append("")

        # Files
        lines.append("Output Files:")
        if result.statepoint_path:
            lines.append(f"  Statepoint: {result.statepoint_path}")
        if result.summary_path:
            lines.append(f"  Summary:    {result.summary_path}")
        if result.tallies_path:
            lines.append(f"  Tallies:    {result.tallies_path}")
        lines.append("")

        # Key results
        lines.append("Key Results:")
        if result.k_effective is not None:
            std_str = (
                f" ± {result.k_effective_std:.5f}"
                if result.k_effective_std
                else ""
            )
            lines.append(f"  k-effective: {result.k_effective:.5f}{std_str}")
        if result.n_batches:
            lines.append(f"  Batches:     {result.n_batches}")
        if result.n_particles:
            lines.append(f"  Particles:   {result.n_particles:,}")
        if result.runtime_seconds:
            lines.append(f"  Runtime:     {result.runtime_seconds:.2f}s")
        lines.append("")

        # Tallies summary
        if result.tallies and "line_count" in result.tallies:
            lines.append("Tallies:")
            lines.append(f"  Lines: {result.tallies['line_count']}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def result_to_dict(self, result: SimulationResult) -> dict[str, Any]:
        """Render a result as a JSON-serializable dict.

        Args:
            result: Simulation result

        Returns:
            A plain dict suitable for ``json.dumps`` (numpy types coerced).
        """
        data = {
            "statepoint_path": str(result.statepoint_path)
            if result.statepoint_path
            else None,
            "summary_path": str(result.summary_path)
            if result.summary_path
            else None,
            "tallies_path": str(result.tallies_path)
            if result.tallies_path
            else None,
            "k_effective": result.k_effective,
            "k_effective_std": result.k_effective_std,
            "n_batches": result.n_batches,
            "n_particles": result.n_particles,
            "runtime_seconds": result.runtime_seconds,
            "tallies": {
                k: v
                for k, v in result.tallies.items()
                if k != "raw_content"  # Skip raw content for cleaner JSON
            },
        }

        # Convert any non-serializable values (numpy types, bytes, ...).
        # ``data`` is a dict, so the recursion returns a dict here.
        return cast("dict[str, Any]", self._make_json_serializable(data))

    def export_json(
        self, result: SimulationResult, output_path: PathLike
    ) -> Path:
        """Export result as JSON.

        Args:
            result: Simulation result
            output_path: Output file path

        Returns:
            Path to generated JSON file
        """
        output_path = Path(output_path)
        output_path.write_text(
            json.dumps(self.result_to_dict(result), indent=2)
        )
        return output_path

    def export_summary_table(self, results: list[SimulationResult]) -> str:
        """Export multiple results as a summary table.

        Args:
            results: List of simulation results

        Returns:
            Formatted table as string
        """
        if not results:
            return "No results to display"

        lines = []
        # Header
        header = f"{'#':<4} {'k-effective':<15} {'Batches':<10} {'Particles':<15} {'Runtime (s)':<12}"
        lines.append(header)
        lines.append("-" * len(header))

        # Rows
        for i, result in enumerate(results, 1):
            k_str = f"{result.k_effective:.5f}" if result.k_effective else "N/A"
            if result.k_effective_std:
                k_str = f"{result.k_effective:.5f}±{result.k_effective_std:.5f}"
            row = (
                f"{i:<4} {k_str:<15} {result.n_batches:<10} "
                f"{result.n_particles:<15,} {result.runtime_seconds:<12.2f}"
            )
            lines.append(row)

        return "\n".join(lines)

    def _make_json_serializable(self, obj: object) -> Any:
        """Recursively convert non-JSON-serializable objects.

        Args:
            obj: Object to convert

        Returns:
            JSON-serializable version
        """
        if isinstance(obj, dict):
            return {k: self._make_json_serializable(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        elif isinstance(obj, str | int | float | bool) or obj is None:
            return obj
        elif hasattr(obj, "tolist"):  # numpy arrays
            return obj.tolist()
        elif hasattr(obj, "item"):  # numpy scalars
            return obj.item()
        elif isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        else:
            return str(obj)
