"""Test suite for ExportParser statistics methods"""
import pandas as pd
import pytest
from src import export_parser as ep

class TestPrintStatistics:
    """Test suite for ExportParser.print_statistics method."""

    def test_print_statistics_empty_dataframe(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_statistics with empty running_workouts DataFrame."""
        parser = ep.ExportParser("dummy_path.zip")
        parser.running_workouts = pd.DataFrame()

        parser.print_statistics()

        captured = capsys.readouterr()
        assert "No running workouts loaded." in captured.out

    def test_print_statistics_with_workouts_no_distance(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test print_statistics with workouts but no distance column."""
        parser = ep.ExportParser("dummy_path.zip")
        parser.running_workouts = pd.DataFrame(
            {
                "activityType": ["Running", "Running"],
                "duration": [3600, 1800],
            }
        )

        parser.print_statistics()

        captured = capsys.readouterr()
        assert "Total running workouts: 2" in captured.out
        assert "Total duration of 1h 30m 0s." in captured.out

    def test_print_statistics_with_distance(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_statistics with distance column."""
        parser = ep.ExportParser("dummy_path.zip")
        parser.running_workouts = pd.DataFrame(
            {
                "activityType": ["Running", "Running"],
                "duration": [3600, 3600],
                "sumDistanceWalkingRunning": [5.0, 10.0],
            }
        )

        parser.print_statistics()

        captured = capsys.readouterr()
        assert "Total running workouts: 2" in captured.out
        assert "Total distance of 15.00 km." in captured.out
        assert "Total duration of 2h 0m 0s." in captured.out

    def test_print_statistics_duration_calculation(
        self, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Test duration formatting (hours, minutes, seconds)."""
        parser = ep.ExportParser("dummy_path.zip")
        parser.running_workouts = pd.DataFrame(
            {
                "activityType": ["Running"],
                "duration": [3661],  # 1h 1m 1s
            }
        )

        parser.print_statistics()

        captured = capsys.readouterr()
        assert "Total duration of 1h 1m 1s." in captured.out

    def test_print_statistics_single_workout(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_statistics with a single workout."""
        parser = ep.ExportParser("dummy_path.zip")
        parser.running_workouts = pd.DataFrame(
            {
                "activityType": ["Running"],
                "duration": [1800],
                "sumDistanceWalkingRunning": [5.5],
            }
        )

        parser.print_statistics()

        captured = capsys.readouterr()
        assert "Total running workouts: 1" in captured.out
        assert "Total distance of 5.50 km." in captured.out
        assert "Total duration of 0h 30m 0s." in captured.out

    def test_print_statistics_zero_distance(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_statistics with zero total distance."""
        parser = ep.ExportParser("dummy_path.zip")
        parser.running_workouts = pd.DataFrame(
            {
                "activityType": ["Running"],
                "duration": [1800],
                "sumDistanceWalkingRunning": [0.0],
            }
        )

        parser.print_statistics()

        captured = capsys.readouterr()
        assert "Total distance of 0.00 km." in captured.out

    def test_print_statistics_large_duration(self, capsys: pytest.CaptureFixture[str]) -> None:
        """Test print_statistics with large duration (multiple hours)."""
        parser = ep.ExportParser("dummy_path.zip")
        parser.running_workouts = pd.DataFrame(
            {
                "activityType": ["Running"],
                "duration": [36000],  # 10 hours
            }
        )

        parser.print_statistics()

        captured = capsys.readouterr()
        assert "Total duration of 10h 0m 0s." in captured.out
