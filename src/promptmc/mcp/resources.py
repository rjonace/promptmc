"""MCP resource handlers for PromptMC.

Resources expose read-only context to MCP clients: the configured
cross-section data location, the in-memory session history, and a listing
of the bundled UO2 criticality example. Each handler returns a JSON string
payload. These handlers have no dependency on the MCP SDK.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict
from pathlib import Path
from typing import Any

from promptmc.mcp.tools import get_session_history

CROSS_SECTIONS_URI = "promptmc://cross-sections"
HISTORY_URI = "promptmc://history"
UO2_EXAMPLE_URI = "promptmc://examples/uo2_criticality"

RESOURCE_MIME_TYPE = "application/json"


def read_cross_sections() -> str:
    """Report the configured OpenMC cross-section data location."""
    value = os.environ.get("OPENMC_CROSS_SECTIONS")
    payload: dict[str, Any] = {"configured": bool(value), "path": value}
    if value:
        payload["exists"] = Path(value).exists()
    return json.dumps(payload, indent=2)


def read_history() -> str:
    """Return the recorded tool-call history for this MCP session."""
    entries = [asdict(entry) for entry in get_session_history()]
    return json.dumps(entries, indent=2)


def read_uo2_example() -> str:
    """List the files bundled with the UO2 criticality example."""
    example_dir = _uo2_example_dir()
    if not example_dir.is_dir():
        return json.dumps(
            {"path": str(example_dir), "files": [], "available": False},
            indent=2,
        )
    files = sorted(
        path.name for path in example_dir.iterdir() if path.is_file()
    )
    return json.dumps(
        {"path": str(example_dir), "files": files, "available": True},
        indent=2,
    )


def _uo2_example_dir() -> Path:
    """Locate the bundled UO2 criticality example directory.

    Resolution order: the ``PROMPTMC_EXAMPLES_DIR`` environment variable,
    then the first ``examples/uo2_criticality`` directory found while
    walking up from this file. The walk handles both editable installs and
    wheels that ship ``examples`` as bundled data, so the resource resolves
    regardless of how PromptMC was installed.

    Returns:
        The resolved example directory path, which may not exist.
    """
    override = os.environ.get("PROMPTMC_EXAMPLES_DIR")
    if override:
        return Path(override) / "uo2_criticality"
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "examples" / "uo2_criticality"
        if candidate.is_dir():
            return candidate
    return here.parents[3] / "examples" / "uo2_criticality"


RESOURCE_READERS: dict[str, Callable[[], str]] = {
    CROSS_SECTIONS_URI: read_cross_sections,
    HISTORY_URI: read_history,
    UO2_EXAMPLE_URI: read_uo2_example,
}
