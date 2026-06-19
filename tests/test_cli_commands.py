"""Tests for CLI command registration."""

from promptmc.cli import app


def test_cli_command_count():
    """Verify exactly 11 commands are registered to prevent silent drift."""
    registered = [cmd.name for cmd in app.registered_commands]
    assert (
        len(registered) == 11
    ), f"Expected 11 commands, found {len(registered)}: {registered}"
