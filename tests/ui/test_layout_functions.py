"""Tests for utility functions in ui.layout module."""

from __future__ import annotations

from pathlib import Path
from types import TracebackType
from typing import Any
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import pandas as pd

from app_state import state
from ui import layout


class TestExportHandlers:
    """Tests for export handler functions."""

    def test_handle_json_export_calls_export_and_download(self) -> None:
        """Test that handle_json_export calls the correct methods."""
        original_workouts: Any = state.workouts

        workouts_mock = MagicMock()
        workouts_mock.export_to_json.return_value = '{"test": "data"}'

        try:
            state.workouts = workouts_mock

            with patch("ui.layout.ui.download") as download_mock:
                layout.handle_json_export()

            workouts_mock.export_to_json.assert_called_once()
            download_mock.assert_called_once_with(b'{"test": "data"}', "apple_health_export.json")
        finally:
            state.workouts = original_workouts

    def test_handle_csv_export_calls_export_and_download(self) -> None:
        """Test that handle_csv_export calls the correct methods."""
        original_workouts: Any = state.workouts

        workouts_mock = MagicMock()
        workouts_mock.export_to_csv.return_value = "header1,header2\nvalue1,value2"

        try:
            state.workouts = workouts_mock

            with patch("ui.layout.ui.download") as download_mock:
                layout.handle_csv_export()

            workouts_mock.export_to_csv.assert_called_once()
            download_mock.assert_called_once_with(
                b"header1,header2\nvalue1,value2", "apple_health_export.csv"
            )
        finally:
            state.workouts = original_workouts


class TestActivityFilter:
    """Tests for activity filter update functionality."""

    def test_update_activity_filter_updates_state_and_refreshes(self) -> None:
        """Test that update_activity_filter updates state and calls refresh_data."""
        original_activity = state.selected_activity_type

        try:
            state.selected_activity_type = "All"

            with patch("ui.layout.refresh_data") as refresh_mock:
                layout.update_activity_filter("Running")

            assert state.selected_activity_type == "Running"
            refresh_mock.assert_called_once()
        finally:
            state.selected_activity_type = original_activity


class TestCalculateMovingAverage:
    """Tests for calculate_moving_average function."""

    def test_calculate_moving_average_with_small_list(self) -> None:
        """Test moving average with list smaller than window size."""
        y_values = [1, 2, 3, 4, 5]
        result = layout.calculate_moving_average(y_values, window_size=12)

        # Should return the original values as floats
        assert result == [1.0, 2.0, 3.0, 4.0, 5.0]

    def test_calculate_moving_average_with_exact_window_size(self) -> None:
        """Test moving average with list exactly matching window size."""
        y_values = [10, 20, 30, 40, 50]
        result = layout.calculate_moving_average(y_values, window_size=5)

        # With pandas rolling and min_periods=1, uses expanding window until full
        assert result[0] == 10.0  # Average of [10]
        assert result[1] == 15.0  # Average of [10, 20]
        assert result[2] == 20.0  # Average of [10, 20, 30]
        assert result[3] == 25.0  # Average of [10, 20, 30, 40]
        assert result[4] == 30.0  # Average of [10, 20, 30, 40, 50]

    def test_calculate_moving_average_with_larger_list(self) -> None:
        """Test moving average with list larger than window size."""
        y_values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120, 130, 140]
        result = layout.calculate_moving_average(y_values, window_size=3)

        # With pandas rolling and min_periods=1, the first values use an expanding window
        # until window_size is reached, then it becomes a sliding window
        assert result[0] == 10.0  # Average of [10] (expanding)
        assert result[1] == 15.0  # Average of [10, 20] (expanding)
        assert result[2] == 20.0  # Average of [10, 20, 30] (window full)
        assert result[3] == 30.0  # Average of [20, 30, 40] (sliding window)
        assert result[4] == 40.0  # Average of [30, 40, 50] (sliding window)
        # Check length matches
        assert len(result) == len(y_values)

    def test_calculate_moving_average_with_default_window(self) -> None:
        """Test moving average with default window size of 12."""
        y_values = list(range(1, 25))  # 24 values
        result = layout.calculate_moving_average(y_values)

        # With pandas rolling and min_periods=1, uses expanding window until full
        assert result[0] == 1.0  # Average of [1]
        assert result[1] == 1.5  # Average of [1, 2]
        assert result[10] == 6.0  # Average of [1..11]
        # Index 11 is the first value with a full window of 12
        expected_avg = sum(range(1, 13)) / 12
        assert result[11] == round(expected_avg, 2)

    def test_calculate_moving_average_with_constant_values(self) -> None:
        """Test moving average with all constant values."""
        y_values = [50] * 20
        result = layout.calculate_moving_average(y_values, window_size=5)

        # All values should be 50.0
        assert all(v == 50.0 for v in result)

    def test_calculate_moving_average_with_empty_list(self) -> None:
        """Test moving average with empty list."""
        y_values: list[int] = []
        result = layout.calculate_moving_average(y_values, window_size=12)

        assert result == []

    def test_calculate_moving_average_with_single_value(self) -> None:
        """Test moving average with single value."""
        y_values = [42]
        result = layout.calculate_moving_average(y_values, window_size=12)

        assert result == [42.0]


class TestRenderTrendsGraphs:
    """Tests for render_trends_graphs function."""

    def test_render_trends_graphs_renders_all_charts(self) -> None:
        """Test that render_trends_graphs calls render_bar_graph for all metrics."""
        original_workouts: Any = state.workouts
        original_activity = state.selected_activity_type

        workouts_mock = MagicMock()
        workouts_mock.get_count_by_period.return_value = {"2024-01": 5}
        workouts_mock.get_distance_by_period.return_value = {"2024-01": 10}
        workouts_mock.get_calories_by_period.return_value = {"2024-01": 500}
        workouts_mock.get_duration_by_period.return_value = {"2024-01": 120}
        workouts_mock.get_elevation_by_period.return_value = {"2024-01": 50}

        class _DummyRow:
            def __enter__(self):
                return self

            def __exit__(
                self,
                exc_type: type[BaseException] | None,
                exc: BaseException | None,
                tb: TracebackType | None,
            ) -> bool:
                return False

            def classes(self, *_args: Any, **_kwargs: Any) -> "_DummyRow":
                """Mock method to allow chaining."""
                return self

        try:
            state.workouts = workouts_mock
            state.selected_activity_type = "Running"

            with patch("ui.layout.ui.row", return_value=_DummyRow()):
                with patch("ui.layout.render_bar_graph") as render_graph_mock:
                    layout.render_trends_graphs.func()

            assert render_graph_mock.call_count == 5

            # Verify all the expected calls were made
            render_graph_mock.assert_any_call("Count by month", {"2024-01": 5})
            render_graph_mock.assert_any_call("Distance by month", {"2024-01": 10}, "km")
            render_graph_mock.assert_any_call("Calories by month", {"2024-01": 500}, "kcal")
            render_graph_mock.assert_any_call("Duration by month", {"2024-01": 120}, "h")
            render_graph_mock.assert_any_call("Elevation by month", {"2024-01": 50}, "m")

            # Verify that get_*_by_period was called with correct parameters
            workouts_mock.get_count_by_period.assert_called_once_with("M", activity_type="Running")
            workouts_mock.get_distance_by_period.assert_called_once_with(
                "M", activity_type="Running"
            )
            workouts_mock.get_calories_by_period.assert_called_once_with(
                "M", activity_type="Running"
            )
            workouts_mock.get_duration_by_period.assert_called_once_with(
                "M", activity_type="Running"
            )
            workouts_mock.get_elevation_by_period.assert_called_once_with(
                "M", activity_type="Running"
            )
        finally:
            state.workouts = original_workouts
            state.selected_activity_type = original_activity


class TestLoadWorkoutsFromFile:
    """Tests for load_workouts_from_file function."""

    def test_load_workouts_from_file_with_valid_zip(self, tmp_path: Path) -> None:
        """Test loading workouts from a valid ZIP file."""
        original_workouts: Any = state.workouts
        original_log: Any = getattr(state, "log", None)

        # Create a test ZIP file
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" 
             startDate="2024-01-01 10:00:00 +0000" 
             endDate="2024-01-01 11:00:00 +0000" 
             duration="60" 
             totalDistance="5.0" 
             totalEnergyBurned="300"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        try:
            # Mock state.log to avoid NiceGUI dependency
            state.log = None  # type: ignore[assignment]
            layout.load_workouts_from_file(str(zip_path))

            # Verify state.workouts was updated
            assert state.workouts is not None
            assert state.workouts.count() > 0
        finally:
            state.workouts = original_workouts
            if original_log is None and hasattr(state, "log"):
                delattr(state, "log")
            elif original_log is not None:
                state.log = original_log

    def test_load_workouts_from_file_uses_context_manager(self, tmp_path: Path) -> None:
        """Test that load_workouts_from_file uses ExportParser as context manager."""
        original_workouts: Any = state.workouts
        original_log: Any = getattr(state, "log", None)

        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" 
             startDate="2024-01-01 10:00:00 +0000" 
             endDate="2024-01-01 11:00:00 +0000" 
             duration="60"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        try:
            # Mock state.log to avoid NiceGUI dependency
            state.log = MagicMock()  # type: ignore[assignment]

            with patch("ui.layout.ExportParser") as parser_class_mock:
                parser_instance_mock = MagicMock()
                parser_instance_mock.parse.return_value = pd.DataFrame()
                parser_class_mock.return_value.__enter__.return_value = parser_instance_mock
                parser_class_mock.return_value.__exit__.return_value = None

                layout.load_workouts_from_file(str(zip_path))

                # Verify ExportParser was used as context manager
                parser_class_mock.return_value.__enter__.assert_called_once()
                parser_class_mock.return_value.__exit__.assert_called_once()
                parser_instance_mock.parse.assert_called_once_with(str(zip_path), log=state.log)
        finally:
            state.workouts = original_workouts
            if original_log is None and hasattr(state, "log"):
                delattr(state, "log")
            elif original_log is not None:
                state.log = original_log

    def test_load_workouts_from_file_creates_workout_manager(self, tmp_path: Path) -> None:
        """Test that load_workouts_from_file creates a WorkoutManager instance."""
        original_workouts: Any = state.workouts
        original_log: Any = getattr(state, "log", None)

        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" 
             startDate="2024-01-01 10:00:00 +0000" 
             endDate="2024-01-01 11:00:00 +0000" 
             duration="60"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        try:
            # Mock state.log to avoid NiceGUI dependency
            state.log = MagicMock()  # type: ignore[assignment]

            with patch("ui.layout.WorkoutManager") as wm_class_mock:
                wm_instance_mock = MagicMock()
                wm_class_mock.return_value = wm_instance_mock

                layout.load_workouts_from_file(str(zip_path))

                # Verify WorkoutManager was instantiated
                wm_class_mock.assert_called_once()
                # Verify state.workouts was set to the WorkoutManager instance
                assert state.workouts == wm_instance_mock
        finally:
            state.workouts = original_workouts
            if original_log is None and hasattr(state, "log"):
                delattr(state, "log")
            elif original_log is not None:
                state.log = original_log
