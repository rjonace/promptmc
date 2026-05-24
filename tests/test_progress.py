"""Tests for progress reporting module."""

from __future__ import annotations

from openmc_wrapper.progress import (
    ProgressEvent,
    ProgressReporter,
    ProgressStage,
    RichProgressDisplay,
    SimulationProgress,
    parse_openmc_output_progress,
)


def test_progress_event_creation():
    """Test ProgressEvent creation."""
    event = ProgressEvent(
        stage=ProgressStage.SIMULATING,
        message="Running batches",
        progress=0.5,
    )
    assert event.stage == ProgressStage.SIMULATING
    assert event.progress == 0.5


def test_progress_event_clamps_progress():
    """Test that progress is clamped to [0, 1]."""
    reporter = ProgressReporter()
    event = reporter.report(ProgressStage.SIMULATING, "test", progress=2.0)
    assert event.progress == 1.0

    event = reporter.report(ProgressStage.SIMULATING, "test", progress=-0.5)
    assert event.progress == 0.0


def test_progress_reporter_subscribe():
    """Test subscribing to progress events."""
    reporter = ProgressReporter()
    received: list = []

    reporter.subscribe(lambda event: received.append(event))
    reporter.report(ProgressStage.VALIDATING, "Validating")

    assert len(received) == 1
    assert received[0].stage == ProgressStage.VALIDATING


def test_progress_reporter_unsubscribe():
    """Test unsubscribing from progress events."""
    reporter = ProgressReporter()
    received: list = []

    def callback(event):
        return received.append(event)

    reporter.subscribe(callback)
    reporter.unsubscribe(callback)
    reporter.report(ProgressStage.SIMULATING, "test")

    assert len(received) == 0


def test_progress_reporter_failing_callback_does_not_break():
    """Test that a failing callback doesn't break the reporter."""
    reporter = ProgressReporter()

    def bad_callback(event):
        raise RuntimeError("bad")

    received: list = []
    reporter.subscribe(bad_callback)
    reporter.subscribe(lambda e: received.append(e))

    reporter.report(ProgressStage.SIMULATING, "test")
    # The good callback should still receive the event
    assert len(received) == 1


def test_progress_reporter_records_events():
    """Test that events are recorded."""
    reporter = ProgressReporter()
    reporter.report(ProgressStage.INITIALIZING, "init")
    reporter.report(ProgressStage.VALIDATING, "validating")
    reporter.report(ProgressStage.SIMULATING, "simulating")

    assert len(reporter.events) == 3
    assert reporter.current_stage == ProgressStage.SIMULATING


def test_simulation_progress_fractions():
    """Test SimulationProgress fraction properties."""
    progress = SimulationProgress(
        total_batches=100,
        completed_batches=25,
        total_particles=1000,
        completed_particles=500,
    )
    assert progress.batch_fraction == 0.25
    assert progress.particle_fraction == 0.5


def test_simulation_progress_zero_total():
    """Test SimulationProgress with zero total."""
    progress = SimulationProgress()
    assert progress.batch_fraction == 0.0
    assert progress.particle_fraction == 0.0


def test_parse_batch_line():
    """Test parsing batch lines from OpenMC output."""
    result = parse_openmc_output_progress("Batch 5")
    assert result is not None
    assert result.completed_batches == 5


def test_parse_invalid_batch_line():
    """Test parsing non-batch lines."""
    assert parse_openmc_output_progress("Some other output") is None
    assert parse_openmc_output_progress("") is None
    assert parse_openmc_output_progress("Batch invalid") is None


def test_rich_progress_display_callback():
    """Test that RichProgressDisplay generates a callback."""
    display = RichProgressDisplay()
    callback = display.make_callback()
    # Without an active progress context, calling should not raise
    callback(ProgressEvent(stage=ProgressStage.SIMULATING, message="test"))


def test_rich_progress_display_context():
    """Test using RichProgressDisplay as context manager."""
    display = RichProgressDisplay()
    with display.display(title="Test", total_steps=100):
        display.update_main(description="Running", advance=10)
    # Should exit cleanly


def test_rich_progress_with_subtask():
    """Test adding subtasks to progress display."""
    display = RichProgressDisplay()
    with display.display(title="Test", total_steps=100):
        sub_id = display.add_subtask("Subtask", total=50)
        display.update_subtask(sub_id, advance=25)
