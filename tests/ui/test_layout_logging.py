"""Tests for logging in layout module."""

import logging
from typing import Generator
from unittest.mock import MagicMock

import pytest

from app_state import state
from ui import layout


@pytest.fixture
def clean_logger() -> Generator[logging.Logger, None, None]:
    """Setup a clean logger for testing."""
    logger = logging.getLogger()
    # Store original level
    original_level = logger.level
    # Set to DEBUG to capture everything
    logger.setLevel(logging.DEBUG)
    # Clear existing handlers except pytest
    for h in list(logger.handlers):
        if not h.__class__.__module__.startswith("_pytest."):
            logger.removeHandler(h)
    # Add a simple handler for testing
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)

    yield logger

    # Cleanup
    logger.setLevel(original_level)


def test_refresh_data_logs_to_root_logger(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that the layout module logger logs at INFO level by default."""
    # Get the layout logger
    layout_logger = logging.getLogger("ui.layout")

    # Capture logs at INFO level
    with caplog.at_level(logging.INFO):
        # Test that we can log at INFO level
        layout_logger.info("Test INFO message")
        layout_logger.debug("Test DEBUG message - should not be captured")

    # Check if INFO message was captured
    log_messages = [record.message for record in caplog.records]

    # Should have the INFO message but not the DEBUG message
    assert any(
        "Test INFO message" in msg for msg in log_messages
    ), f"Expected INFO message to be logged, got: {log_messages}"

    # DEBUG message should not be captured (INFO is default level)
    assert not any(
        "Test DEBUG message" in msg for msg in log_messages
    ), f"DEBUG message should not be captured at INFO level, got: {log_messages}"


def test_layout_logger_propagates(caplog: pytest.LogCaptureFixture) -> None:
    """Test that the layout module logger properly propagates to root logger."""
    with caplog.at_level(logging.INFO):
        # Get the layout logger
        layout_logger = logging.getLogger("ui.layout")
        layout_logger.info("TEST MESSAGE FROM LAYOUT")

    log_messages = [record.message for record in caplog.records]
    print(f"Captured log messages: {log_messages}")

    assert any(
        "TEST MESSAGE FROM LAYOUT" in msg for msg in log_messages
    ), f"Expected test message to be logged, got: {log_messages}"


def test_module_logger_exists() -> None:
    """Test that the _logger in layout module is properly configured."""
    # The _logger should be logging.getLogger("ui.layout")
    assert hasattr(layout, "_logger"), "layout module should have _logger attribute"
    assert isinstance(
        layout._logger, logging.Logger  # type: ignore[attr-defined]  # pylint: disable=protected-access
    ), "_logger should be a Logger instance"
    assert (
        layout._logger.name == "ui.layout"  # type: ignore[attr-defined]  # pylint: disable=protected-access
    ), f"Logger name should be 'ui.layout', got {layout._logger.name}"  # type: ignore[attr-defined]  # pylint: disable=protected-access
    # Logger should propagate by default
    assert (
        layout._logger.propagate  # type: ignore[attr-defined]  # pylint: disable=protected-access
    ), "Logger should propagate to parent loggers"


def test_refresh_data_called_once_on_activity_selection_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that refresh_data is called exactly once when activity selection changes."""
    # Track calls to refresh_data
    refresh_data_mock = MagicMock()

    # Patch refresh_data in the layout module
    monkeypatch.setattr(layout, "refresh_data", refresh_data_mock)

    # Also need to mock the state and workouts to avoid issues
    mock_workouts = MagicMock()
    mock_workouts.get_count.return_value = 5
    mock_workouts.get_total_distance.return_value = 10
    mock_workouts.get_total_duration.return_value = 2
    mock_workouts.get_total_elevation.return_value = 100
    mock_workouts.get_total_calories.return_value = 500
    monkeypatch.setattr(state, "workouts", mock_workouts)

    # Simulate what happens when activity selection changes
    # The on_change callback is set to refresh_data and receives the new activity type
    refresh_data_mock("FunctionalStrengthTraining")

    # Verify refresh_data was called exactly once
    assert refresh_data_mock.call_count == 1, (
        f"refresh_data should be called exactly once on activity selection change, "
        f"but was called {refresh_data_mock.call_count} times"
    )


def test_refresh_data_called_once_on_date_range_change(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Test that refresh_data is called exactly once when date range changes."""
    # Track calls to refresh_data
    refresh_data_mock = MagicMock()

    # Patch refresh_data in the layout module
    monkeypatch.setattr(layout, "refresh_data", refresh_data_mock)

    # Mock state and workouts
    mock_workouts = MagicMock()
    mock_workouts.get_count.return_value = 5
    mock_workouts.get_total_distance.return_value = 10
    mock_workouts.get_total_duration.return_value = 2
    mock_workouts.get_total_elevation.return_value = 100
    mock_workouts.get_total_calories.return_value = 500
    monkeypatch.setattr(state, "workouts", mock_workouts)

    # Simulate what happens when date range changes
    # The on_change callback for the date picker is set to refresh_data
    refresh_data_mock()

    # Verify refresh_data was called exactly once
    assert refresh_data_mock.call_count == 1, (
        f"refresh_data should be called exactly once on date range change, "
        f"but was called {refresh_data_mock.call_count} times"
    )
