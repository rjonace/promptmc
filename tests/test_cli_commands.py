"""Tests for CLI command registration."""

from promptmc.cli import app


def test_cli_command_count():
    """Verify exactly 12 commands are registered to prevent silent drift."""
    registered = [cmd.name for cmd in app.registered_commands]
    assert (
        len(registered) == 12
    ), f"Expected 12 commands, found {len(registered)}: {registered}"


def test_doctor_command_registered():
    """The doctor diagnostics command is wired into the app."""
    callbacks = {
        cmd.callback.__name__
        for cmd in app.registered_commands
        if cmd.callback is not None
    }
    assert "doctor" in callbacks
