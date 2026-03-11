"""Tests for WorkoutManager.get_best_segments."""

from datetime import datetime, timezone
from pathlib import Path
from zipfile import ZipFile

import pandas as pd
import pytest

from logic.export_parser import ExportParser
from logic.workout_manager import WorkoutManager
from logic.workout_route import RoutePoint, WorkoutRoute
from tests.conftest import build_health_export_xml, load_export_fragment


def _two_point_route(duration_s: int, distance_deg_lon: float = 0.01) -> WorkoutRoute:
    """Build a minimal route with one segment over ~1km for deterministic best-segment tests."""
    start_time = datetime(2025, 1, 1, tzinfo=timezone.utc)
    end_time = start_time + pd.Timedelta(seconds=duration_s)
    return WorkoutRoute(
        points=[
            RoutePoint(time=start_time, latitude=0.0, longitude=0.0, altitude=0.0),
            RoutePoint(
                time=end_time,
                latitude=0.0,
                longitude=distance_deg_lon,
                altitude=0.0,
            ),
        ]
    )


class TestGetBestSegments:
    """Test suite for WorkoutManager.get_best_segments."""

    def test_returns_empty_dataframe_for_empty_manager(self) -> None:
        """No workouts should return an empty DataFrame with stable output columns."""
        manager = WorkoutManager()

        result = manager.get_best_segments(topn=3, distances=[1000])

        assert result.empty
        assert list(result.columns) == ["startDate", "distance", "duration_s"]

    def test_returns_empty_when_topn_is_non_positive(self) -> None:
        """Non-positive topn should return an empty DataFrame."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "route": [_two_point_route(300)],
                }
            )
        )

        result = manager.get_best_segments(topn=0, distances=[1000])

        assert result.empty
        assert list(result.columns) == ["startDate", "distance", "duration_s"]

    def test_selects_fastest_segments_and_applies_topn(self) -> None:
        """topn should keep the fastest (smallest duration) segments per distance."""
        fast_route = _two_point_route(250)
        slow_route = _two_point_route(400)

        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": [
                        pd.Timestamp("2025-01-02"),
                        pd.Timestamp("2025-01-01"),
                        pd.Timestamp("2025-01-03"),
                    ],
                    "route": [slow_route, fast_route, _two_point_route(200)],
                }
            )
        )

        top1 = manager.get_best_segments(topn=1, distances=[1000])
        assert len(top1) == 1
        assert int(top1.iloc[0]["distance"]) == 1000
        assert float(top1.iloc[0]["duration_s"]) == pytest.approx(250.0)  # type: ignore[misc]
        assert top1.iloc[0]["startDate"] == pd.Timestamp("2025-01-01")

        top2 = manager.get_best_segments(topn=2, distances=[1000])
        assert len(top2) == 2
        expected_durations = [pytest.approx(250.0), pytest.approx(400.0)]  # type: ignore[misc]
        assert list(top2["duration_s"]) == expected_durations

    def test_with_real_fixture_running_route(self, tmp_path: Path) -> None:
        """Existing real fixture should produce a known best traveled 1000m segment."""
        workout_xml = load_export_fragment("workout_running.xml")
        route_file = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "exports"
            / "workout-routes"
            / "route_2025-09-16_6.15pm.gpx"
        )

        zip_path = tmp_path / "running_with_route.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", build_health_export_xml([workout_xml]))
            zf.writestr(
                "apple_health_export/workout-routes/route_2025-09-16_6.15pm.gpx",
                route_file.read_bytes(),
            )

        parser = ExportParser()
        with parser:
            parsed = parser.parse(str(zip_path))

        manager = WorkoutManager(parsed.workouts)
        result = manager.get_best_segments(topn=1, distances=[1000])

        assert len(result) == 1
        assert int(result.iloc[0]["distance"]) == 1000
        expected_duration = pytest.approx(375.0, rel=1e-3)  # type: ignore[misc]
        assert float(result.iloc[0]["duration_s"]) == expected_duration
