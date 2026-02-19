"""Tests for UI formatting in layout refresh."""

from datetime import datetime
from typing import Any, Optional, Union
from unittest.mock import MagicMock, patch

import pandas as pd

from app_state import state
from logic.workout_manager import WorkoutManager
from ui.helpers import format_integer
from ui.layout import refresh_data


class _DummyWorkouts(WorkoutManager):
    def get_count(
        self,
        activity_type: str = "All",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        return 12345

    def get_total_distance(
        self,
        activity_type: str = "All",
        unit: str = "km",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        return 67890

    def get_total_duration(
        self,
        activity_type: str = "All",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        return 24680

    def get_total_elevation(
        self,
        activity_type: str = "All",
        unit: str = "m",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        return 13579

    def get_total_calories(
        self,
        activity_type: str = "All",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        return 98765


def test_refresh_data_formats_metrics_display() -> None:
    """refresh_data should populate formatted display values."""
    original_workouts: Any = state.workouts

    try:
        state.workouts = _DummyWorkouts()
        state.selected_activity_type = "All"

        # Mock the refresh calls to avoid event loop issues in testing
        with patch("ui.layout.render_activity_graphs.refresh"):
            with patch("ui.layout.render_trends_graphs.refresh"):
                refresh_data()

        assert state.metrics_display["count"] == format_integer(12345)
        assert state.metrics_display["distance"] == format_integer(67890)
        assert state.metrics_display["duration"] == format_integer(24680)
        assert state.metrics_display["elevation"] == format_integer(13579)
        assert state.metrics_display["calories"] == format_integer(98765)
    finally:
        state.workouts = original_workouts


def test_refresh_data_passes_date_range_to_workouts() -> None:
    """refresh_data should forward date range filters to workout methods."""
    original_workouts: Any = state.workouts
    original_date_range = state.date_range_text
    original_activity = state.selected_activity_type

    workouts_mock = MagicMock()
    workouts_mock.get_count.return_value = 1
    workouts_mock.get_total_distance.return_value = 2
    workouts_mock.get_total_duration.return_value = 3
    workouts_mock.get_total_elevation.return_value = 4
    workouts_mock.get_total_calories.return_value = 5

    try:
        state.workouts = workouts_mock
        state.selected_activity_type = "Running"
        state.date_range_text = "2024/02/01 - 2024/02/01"

        expected_start = datetime(2024, 2, 1)
        expected_end = datetime(2024, 2, 1)

        with patch("ui.layout.render_activity_graphs.refresh"):
            with patch("ui.layout.render_trends_graphs.refresh"):
                refresh_data()

        workouts_mock.get_count.assert_called_once_with("Running", expected_start, expected_end)
        workouts_mock.get_total_distance.assert_called_once_with(
            "Running", start_date=expected_start, end_date=expected_end
        )
        workouts_mock.get_total_duration.assert_called_once_with(
            "Running", start_date=expected_start, end_date=expected_end
        )
        workouts_mock.get_total_elevation.assert_called_once_with(
            "Running", start_date=expected_start, end_date=expected_end
        )
        workouts_mock.get_total_calories.assert_called_once_with(
            "Running", start_date=expected_start, end_date=expected_end
        )
    finally:
        state.workouts = original_workouts
        state.date_range_text = original_date_range
        state.selected_activity_type = original_activity
