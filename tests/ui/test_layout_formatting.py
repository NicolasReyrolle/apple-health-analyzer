"""Tests for UI formatting in layout refresh."""

from datetime import datetime
from typing import Any, Optional, Union
from unittest.mock import patch

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
