"""Tests for ui.layout health-data rendering and workout-file loading helpers."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import pandas as pd

from app_state import state
from ui import layout

from ._helpers import DummyRow, translated_message


class TestRenderHealthDataTab:
    """Tests for render_health_data_tab behavior."""

    def test_render_health_data_tab_converts_period_keys_to_strings(self) -> None:
        """Convert pandas Period keys to strings for JSON-safe chart options."""
        original_records_by_type: Any = state.records_by_type
        original_period = state.trends_period

        records_by_type_mock = MagicMock()
        records_by_type_mock.heart_rate_stats.return_value = pd.DataFrame(
            {
                "period": [pd.Period("2025-01", freq="M")],
                "avg": [67.0],
                "min": [67.0],
                "max": [67.0],
                "count": [1],
            }
        )

        try:
            state.records_by_type = records_by_type_mock
            state.trends_period = "M"

            with (
                patch("ui.layout.ui.row", return_value=DummyRow()),
                patch("ui.layout.render_generic_graph") as render_generic_graph_mock,
            ):
                layout.render_health_data_tab.func()

            heart_rate_call = next(
                call
                for call in render_generic_graph_mock.call_args_list
                if call.args and call.args[0] == "Resting HR frequency over time"
            )
            chart_data = heart_rate_call.args[1]
            assert isinstance(chart_data, dict)
            assert list(chart_data.keys()) == ["2025-01"]  # type: ignore[arg-type]
        finally:
            state.records_by_type = original_records_by_type
            state.trends_period = original_period

    def test_render_health_data_tab_serializes_missing_and_invalid_values(self) -> None:
        """Serialize None/NaN/non-numeric avg values to explicit None for chart data."""
        original_records_by_type: Any = state.records_by_type
        original_period = state.trends_period

        records_by_type_mock = MagicMock()
        records_by_type_mock.heart_rate_stats.return_value = pd.DataFrame(
            {
                "period": [pd.Period("2025-01", freq="M")],
                "avg": [None],
                "min": [0.0],
                "max": [0.0],
                "count": [0],
            }
        )
        records_by_type_mock.weight_stats.return_value = pd.DataFrame(
            {
                "period": [pd.Period("2025-01", freq="M")],
                "avg": [float("nan")],
                "min": [0.0],
                "max": [0.0],
                "count": [0],
            }
        )
        records_by_type_mock.vo2_max_stats.return_value = pd.DataFrame(
            {
                "period": [pd.Period("2025-01", freq="M")],
                "avg": ["invalid"],
                "min": [0.0],
                "max": [0.0],
                "count": [0],
            }
        )

        try:
            state.records_by_type = records_by_type_mock
            state.trends_period = "M"

            with (
                patch("ui.layout.ui.row", return_value=DummyRow()),
                patch("ui.layout.render_generic_graph") as render_generic_graph_mock,
            ):
                layout.render_health_data_tab.func()

            heart_rate_call = next(
                call
                for call in render_generic_graph_mock.call_args_list
                if call.args and call.args[0] == "Resting HR frequency over time"
            )
            body_mass_call = next(
                call
                for call in render_generic_graph_mock.call_args_list
                if call.args and call.args[0] == "Body Mass over time"
            )
            vo2_max_call = next(
                call
                for call in render_generic_graph_mock.call_args_list
                if call.args and call.args[0] == "VO2 Max over time"
            )

            assert heart_rate_call.args[1]["2025-01"] is None
            assert body_mass_call.args[1]["2025-01"] is None
            assert vo2_max_call.args[1]["2025-01"] is None
        finally:
            state.records_by_type = original_records_by_type
            state.trends_period = original_period


class TestLoadWorkoutsFromFile:
    """Tests for load_workouts_from_file function."""

    def test_load_workouts_from_file_with_valid_zip(self, tmp_path: Path) -> None:
        """Test loading workouts from a valid ZIP file."""
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

        workouts, activity_options, _ = layout.load_workouts_from_file(str(zip_path))

        assert workouts is not None
        assert workouts.get_count() > 0
        assert isinstance(activity_options, list)
        assert "All" in activity_options

    def test_load_workouts_from_file_uses_context_manager(self, tmp_path: Path) -> None:
        """Test that load_workouts_from_file uses ExportParser as context manager."""
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

        with patch("ui.layout.ExportParser") as parser_class_mock:
            parser_instance_mock = MagicMock()
            parser_instance_mock.parse.return_value.workouts = pd.DataFrame()
            parser_instance_mock.parse.return_value.records_by_type = {}
            parser_class_mock.return_value.__enter__.return_value = parser_instance_mock
            parser_class_mock.return_value.__exit__.return_value = None

            layout.load_workouts_from_file(str(zip_path))

            parser_class_mock.return_value.__enter__.assert_called_once()
            parser_class_mock.return_value.__exit__.assert_called_once()
            parser_instance_mock.parse.assert_called_once_with(str(zip_path))

    def test_load_workouts_from_file_creates_workout_manager(self, tmp_path: Path) -> None:
        """Test that load_workouts_from_file creates a WorkoutManager instance."""
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

        with patch("ui.layout.WorkoutManager") as wm_class_mock:
            wm_instance_mock = MagicMock()
            wm_instance_mock.get_activity_types.return_value = []
            wm_class_mock.return_value = wm_instance_mock

            workouts, activity_options, _ = layout.load_workouts_from_file(str(zip_path))

            wm_class_mock.assert_called_once()
            assert workouts == wm_instance_mock
            assert activity_options == ["All"]

    def test_load_workouts_from_file_reports_processed_progress_messages(self) -> None:
        """Progress callback should receive updates when parser reports processed workouts."""

        events: list[tuple[int, str]] = []

        with patch("ui.layout.ExportParser") as parser_class_mock:
            parser_instance_mock = MagicMock()

            def _parse_side_effect(_file_path: str) -> Any:
                parser_cb = parser_class_mock.call_args.kwargs["progress_callback"]
                parser_cb("Processed 100 workouts...")
                return SimpleNamespace(workouts=pd.DataFrame(), records_by_type={})

            parser_instance_mock.parse.side_effect = _parse_side_effect
            parser_class_mock.return_value.__enter__.return_value = parser_instance_mock
            parser_class_mock.return_value.__exit__.return_value = None

            with patch("ui.layout.WorkoutManager") as wm_class_mock:
                wm_instance_mock = MagicMock()
                wm_instance_mock.get_activity_types.return_value = []
                wm_class_mock.return_value = wm_instance_mock

                layout.load_workouts_from_file(
                    "dummy.zip",
                    progress_callback=lambda progress, message: events.append((progress, message)),
                )

        assert any(msg.startswith("Processed 100 workouts") for _progress, msg in events)
        assert any(progress == 22 for progress, msg in events if msg.startswith("Processed "))

    def test_load_workouts_from_file_translates_parser_progress_messages(self) -> None:
        """Parser progress text should be translated before reaching UI callback."""

        events: list[tuple[int, str]] = []

        with patch("ui.layout.t", side_effect=translated_message):
            with patch("ui.helpers.translate", side_effect=translated_message):
                with patch("ui.layout.ExportParser") as parser_class_mock:
                    parser_instance_mock = MagicMock()

                    def _parse_side_effect(_file_path: str) -> Any:
                        parser_cb = parser_class_mock.call_args.kwargs["progress_callback"]
                        parser_cb("Processed 3 workouts...")
                        return SimpleNamespace(workouts=pd.DataFrame(), records_by_type={})

                    parser_instance_mock.parse.side_effect = _parse_side_effect
                    parser_class_mock.return_value.__enter__.return_value = parser_instance_mock
                    parser_class_mock.return_value.__exit__.return_value = None

                    with patch("ui.layout.WorkoutManager") as wm_class_mock:
                        wm_instance_mock = MagicMock()
                        wm_instance_mock.get_activity_types.return_value = []
                        wm_class_mock.return_value = wm_instance_mock

                        layout.load_workouts_from_file(
                            "dummy.zip",
                            progress_callback=lambda progress, message: events.append(
                                (progress, message)
                            ),
                        )

        assert any(msg == "tr:Processed 3 workouts..." for _progress, msg in events)
