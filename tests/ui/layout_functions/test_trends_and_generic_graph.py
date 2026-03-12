"""Tests for ui.layout trend rendering and generic chart helper."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

from app_state import state
from ui import layout

from ._helpers import DummyRow


class TestRenderTrendsGraphs:
    """Tests for render_trends_graphs function."""

    def test_render_trends_graphs_renders_all_charts(self) -> None:
        """Test that render_trends_graphs calls render_generic_graph for all metrics."""
        original_workouts: Any = state.workouts
        original_activity = state.selected_activity_type

        workouts_mock = MagicMock()
        workouts_mock.get_count_by_period.return_value = {"2024-01": 5}
        workouts_mock.get_distance_by_period.return_value = {"2024-01": 10}
        workouts_mock.get_calories_by_period.return_value = {"2024-01": 500}
        workouts_mock.get_duration_by_period.return_value = {"2024-01": 120}
        workouts_mock.get_elevation_by_period.return_value = {"2024-01": 50}

        try:
            state.workouts = workouts_mock
            state.selected_activity_type = "Running"

            with patch("ui.layout.ui.row", return_value=DummyRow()):
                with patch("ui.layout.render_generic_graph") as render_graph_mock:
                    layout.render_trends_graphs.func()

            assert render_graph_mock.call_count == 5
            render_graph_mock.assert_any_call("Count by month", {"2024-01": 5})
            render_graph_mock.assert_any_call("Distance by month", {"2024-01": 10}, "km")
            render_graph_mock.assert_any_call("Calories by month", {"2024-01": 500}, "kcal")
            render_graph_mock.assert_any_call("Duration by month", {"2024-01": 120}, "h")
            render_graph_mock.assert_any_call("Elevation by month", {"2024-01": 50}, "m")

            workouts_mock.get_count_by_period.assert_called_once_with(
                "M", activity_type="Running", start_date=None, end_date=None
            )
            workouts_mock.get_distance_by_period.assert_called_once_with(
                "M", activity_type="Running", start_date=None, end_date=None
            )
            workouts_mock.get_calories_by_period.assert_called_once_with(
                "M", activity_type="Running", start_date=None, end_date=None
            )
            workouts_mock.get_duration_by_period.assert_called_once_with(
                "M", activity_type="Running", start_date=None, end_date=None
            )
            workouts_mock.get_elevation_by_period.assert_called_once_with(
                "M", activity_type="Running", unit="m", start_date=None, end_date=None
            )
        finally:
            state.workouts = original_workouts
            state.selected_activity_type = original_activity

    def test_render_trends_graphs_with_week_period(self) -> None:
        """Test that render_trends_graphs uses correct period when set to week."""
        original_workouts: Any = state.workouts
        original_activity = state.selected_activity_type
        original_period = state.trends_period

        workouts_mock = MagicMock()
        workouts_mock.get_count_by_period.return_value = {"2024-W01": 2}
        workouts_mock.get_distance_by_period.return_value = {"2024-W01": 10}
        workouts_mock.get_calories_by_period.return_value = {"2024-W01": 500}
        workouts_mock.get_duration_by_period.return_value = {"2024-W01": 120}
        workouts_mock.get_elevation_by_period.return_value = {"2024-W01": 50}

        try:
            state.workouts = workouts_mock
            state.selected_activity_type = "Running"
            state.trends_period = "W"

            with patch("ui.layout.ui.row", return_value=DummyRow()):
                with patch("ui.layout.render_generic_graph") as render_graph_mock:
                    layout.render_trends_graphs.func()

            workouts_mock.get_count_by_period.assert_called_once_with(
                "W", activity_type="Running", start_date=None, end_date=None
            )
            workouts_mock.get_distance_by_period.assert_called_once_with(
                "W", activity_type="Running", start_date=None, end_date=None
            )

            called_labels = [call[0][0] for call in render_graph_mock.call_args_list]
            assert any("week" in label.lower() for label in called_labels)
        finally:
            state.workouts = original_workouts
            state.selected_activity_type = original_activity
            state.trends_period = original_period

    def test_render_trends_graphs_with_quarter_period(self) -> None:
        """Test that render_trends_graphs uses correct period when set to quarter."""
        original_workouts: Any = state.workouts
        original_activity = state.selected_activity_type
        original_period = state.trends_period

        workouts_mock = MagicMock()
        workouts_mock.get_count_by_period.return_value = {"2024-Q1": 15}
        workouts_mock.get_distance_by_period.return_value = {"2024-Q1": 50}
        workouts_mock.get_calories_by_period.return_value = {"2024-Q1": 2000}
        workouts_mock.get_duration_by_period.return_value = {"2024-Q1": 600}
        workouts_mock.get_elevation_by_period.return_value = {"2024-Q1": 250}

        try:
            state.workouts = workouts_mock
            state.selected_activity_type = "Running"
            state.trends_period = "Q"

            with patch("ui.layout.ui.row", return_value=DummyRow()):
                with patch("ui.layout.render_generic_graph") as render_graph_mock:
                    layout.render_trends_graphs.func()

            workouts_mock.get_count_by_period.assert_called_once_with(
                "Q", activity_type="Running", start_date=None, end_date=None
            )

            called_labels = [call[0][0] for call in render_graph_mock.call_args_list]
            assert any("quarter" in label.lower() for label in called_labels)
        finally:
            state.workouts = original_workouts
            state.selected_activity_type = original_activity
            state.trends_period = original_period

    def test_render_trends_graphs_with_year_period(self) -> None:
        """Test that render_trends_graphs uses correct period when set to year."""
        original_workouts: Any = state.workouts
        original_activity = state.selected_activity_type
        original_period = state.trends_period

        workouts_mock = MagicMock()
        workouts_mock.get_count_by_period.return_value = {"2024": 60}
        workouts_mock.get_distance_by_period.return_value = {"2024": 200}
        workouts_mock.get_calories_by_period.return_value = {"2024": 8000}
        workouts_mock.get_duration_by_period.return_value = {"2024": 2400}
        workouts_mock.get_elevation_by_period.return_value = {"2024": 1000}

        try:
            state.workouts = workouts_mock
            state.selected_activity_type = "Running"
            state.trends_period = "Y"

            with patch("ui.layout.ui.row", return_value=DummyRow()):
                with patch("ui.layout.render_generic_graph") as render_graph_mock:
                    layout.render_trends_graphs.func()

            workouts_mock.get_count_by_period.assert_called_once_with(
                "Y", activity_type="Running", start_date=None, end_date=None
            )

            called_labels = [call[0][0] for call in render_graph_mock.call_args_list]
            assert any("year" in label.lower() for label in called_labels)
        finally:
            state.workouts = original_workouts
            state.selected_activity_type = original_activity
            state.trends_period = original_period


class TestRenderGenericGraph:
    """Tests for render_generic_graph function."""

    def test_render_generic_graph_includes_trend_by_default(self) -> None:
        """Trend series is included when show_trend is not specified."""
        values = {"2024-01": 10, "2024-02": 20}

        with (
            patch("ui.layout.ui.card", return_value=DummyRow()),
            patch("ui.layout.ui.label"),
            patch("ui.layout.ui.echart") as echart_mock,
        ):
            layout.render_generic_graph("Distance by month", values, "km")

        chart_options = echart_mock.call_args.args[0]
        series = chart_options["series"]
        assert len(series) == 2
        assert series[0]["type"] == "bar"
        assert series[1]["name"] == "Trend"

    def test_render_generic_graph_excludes_trend_when_disabled(self) -> None:
        """Trend series is omitted when show_trend is False."""
        values = {"2024-01": 10, "2024-02": 20}

        with (
            patch("ui.layout.ui.card", return_value=DummyRow()),
            patch("ui.layout.ui.label"),
            patch("ui.layout.ui.echart") as echart_mock,
        ):
            layout.render_generic_graph("Distance by month", values, "km", show_trend=False)

        chart_options = echart_mock.call_args.args[0]
        series = chart_options["series"]
        assert len(series) == 1
        assert series[0]["type"] == "bar"
