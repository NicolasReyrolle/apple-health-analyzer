"""Tests for ui.layout core behaviors not covered by integration tests."""

from __future__ import annotations
from typing import Any

from unittest.mock import MagicMock, patch

from app_state import state
from ui import layout

def test_render_activity_graphs_renders_all_charts() -> None:
    """Test that render_activity_graphs calls render_pie_rose_graph for all metrics."""
    original_workouts: Any = state.workouts

    workouts_mock = MagicMock()
    workouts_mock.get_count_by_activity.return_value = {"Running": 1}
    workouts_mock.get_distance_by_activity.return_value = {"Running": 5}
    workouts_mock.get_calories_by_activity.return_value = {"Running": 200}
    workouts_mock.get_duration_by_activity.return_value = {"Running": 1}
    workouts_mock.get_elevation_by_activity.return_value = {"Running": 1}

    try:
        state.workouts = workouts_mock
        with patch("ui.layout.render_pie_rose_graph") as render_graph_mock:
            layout.render_activity_graphs()

        assert render_graph_mock.call_count == 5
        render_graph_mock.assert_any_call("Count by activity", {"Running": 1})
        render_graph_mock.assert_any_call("Distance by activity", {"Running": 5}, "km")
        render_graph_mock.assert_any_call("Calories by activity", {"Running": 200}, "kcal")
        render_graph_mock.assert_any_call("Duration by activity", {"Running": 1}, "h")
        render_graph_mock.assert_any_call("Elevation by activity", {"Running": 1}, "km")
    finally:
        state.workouts = original_workouts
