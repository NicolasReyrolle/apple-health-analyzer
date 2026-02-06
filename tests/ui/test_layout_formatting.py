"""Tests for UI formatting in layout refresh."""

from typing import Any

from logic.workout_manager import WorkoutManager

from app_state import state
from ui.helpers import format_integer
from ui.layout import refresh_data


class _DummyWorkouts(WorkoutManager):
    def count(self, activity_type: str = "All") -> int:
        return 12345

    def get_total_distance(
        self, activity_type: str = "All", unit: str = "km"  # pylint: disable=unused-argument
    ) -> int:
        return 67890

    def get_total_duration(
        self, activity_type: str = "All", unit: str = "h"  # pylint: disable=unused-argument
    ) -> int:
        return 24680

    def get_total_elevation(
        self, activity_type: str = "All", unit: str = "km"  # pylint: disable=unused-argument
    ) -> int:
        return 13579

    def get_total_calories(
        self, activity_type: str = "All", unit: str = "kcal"  # pylint: disable=unused-argument
    ) -> int:
        return 98765


def test_refresh_data_formats_metrics_display() -> None:
    """refresh_data should populate formatted display values."""
    original_workouts: Any = state.workouts

    try:
        state.workouts = _DummyWorkouts()
        state.selected_activity_type = "All"
        refresh_data()

        assert state.metrics_display["count"] == format_integer(12345)
        assert state.metrics_display["distance"] == format_integer(67890)
        assert state.metrics_display["duration"] == format_integer(24680)
        assert state.metrics_display["elevation"] == format_integer(13579)
        assert state.metrics_display["calories"] == format_integer(98765)
    finally:
        state.workouts = original_workouts
