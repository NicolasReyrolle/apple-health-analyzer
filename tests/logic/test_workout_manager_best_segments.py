"""Tests for WorkoutManager.get_best_segments."""

from datetime import datetime, timedelta, timezone
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
        expected_duration = pytest.approx(374.0, rel=1e-3)  # type: ignore[misc]
        assert float(result.iloc[0]["duration_s"]) == expected_duration

    def test_considers_each_route_part_separately(self) -> None:
        """Best-segment search should not bridge disjoint route parts."""
        start_time = datetime(2025, 9, 26, tzinfo=timezone.utc)
        first_part = WorkoutRoute(
            points=[
                RoutePoint(time=start_time, latitude=0.0, longitude=0.0, altitude=0.0),
                RoutePoint(
                    time=start_time + pd.Timedelta(seconds=410),
                    latitude=0.0,
                    longitude=0.01,
                    altitude=0.0,
                ),
            ]
        )
        second_part = WorkoutRoute(
            points=[
                RoutePoint(
                    time=start_time + pd.Timedelta(seconds=670),
                    latitude=0.0,
                    longitude=0.01,
                    altitude=0.0,
                ),
                RoutePoint(
                    time=start_time + pd.Timedelta(seconds=930),
                    latitude=0.0,
                    longitude=0.02,
                    altitude=0.0,
                ),
            ]
        )

        merged_route = WorkoutRoute(points=first_part.points + second_part.points)

        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-09-26")],
                    "route": [merged_route],
                    "route_parts": [[first_part, second_part]],
                }
            )
        )

        result = manager.get_best_segments(topn=2, distances=[1000])

        assert len(result) == 1
        assert list(result["distance"]) == [1000]
        assert list(result["duration_s"]) == [pytest.approx(260.0)]

    def test_last_unpaired_motion_paused_trims_vehicle_section(self, tmp_path: Path) -> None:
        """Active-end trimming removes vehicle GPS recorded after forgetting to stop the watch.

        Uses the Usain Bolt fixture XML (last MotionPaused at 16:46:13 +0100, no following
        MotionResumed) combined with a synthetic GPX that has:
          - 200 running points at ≈1 m/s (best 100 m ≈ 101 s)
          - 3 car points at ≈100 m/s starting 1 second after the last MotionPaused

        Without trimming the car section the best 100 m would be 1 s (impossible).
        With trimming it must be ≥ 100 s (realistic running pace).
        """
        # WorkoutRoute window: 14:30:02Z – 15:50:31Z (+0100 = UTC-1h)
        # Last MotionPaused in fixture: 2021-12-26 16:46:13 +0100 = 15:46:13Z
        t_run_start = datetime(2021, 12, 26, 14, 30, 2, tzinfo=timezone.utc)
        t_car_start = datetime(2021, 12, 26, 15, 46, 14, tzinfo=timezone.utc)  # 1s after pause

        step_deg = 0.000009  # ≈ 1 m at the equator (one degree latitude ≈ 111 139 m)
        running_points = "\n".join(
            f'      <trkpt lat="{i * step_deg:.9f}" lon="0.000000">'
            f"<ele>100</ele>"
            f"<time>{(t_run_start + timedelta(seconds=i)).strftime('%Y-%m-%dT%H:%M:%SZ')}</time>"
            "</trkpt>"
            for i in range(200)
        )
        car_points = "\n".join(
            f'      <trkpt lat="{(200 + i * 100) * step_deg:.9f}" lon="0.000000">'
            f"<ele>100</ele>"
            f"<time>{(t_car_start + timedelta(seconds=i)).strftime('%Y-%m-%dT%H:%M:%SZ')}</time>"
            "</trkpt>"
            for i in range(3)
        )
        gpx = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<gpx version="1.1" creator="Test" xmlns="http://www.topografix.com/GPX/1/1">'
            "<trk><trkseg>"
            f"{running_points}\n{car_points}"
            "</trkseg></trk></gpx>"
        )

        workout_xml = load_export_fragment("workout_running_usaint_bolt.xml")

        zip_path = tmp_path / "running_usaint_bolt_synthetic.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", build_health_export_xml([workout_xml]))
            zf.writestr(
                "apple_health_export/workout-routes/route_2021-12-26_4.50pm.gpx",
                gpx.encode(),
            )

        parser = ExportParser()
        with parser:
            parsed = parser.parse(str(zip_path))

        manager = WorkoutManager(parsed.workouts)
        result = manager.get_best_segments(topn=1, distances=[100])

        assert len(result) == 1
        duration_s = float(result.iloc[0]["duration_s"])
        # Car section excluded; running at ≈1 m/s → need 101 steps for 100 m → 101 s
        assert (
            duration_s >= 100.0
        ), f"Expected ≥ 100 s (car trimmed, running at 1 m/s), got {duration_s} s"

    def test_real_fixture_too_fast_does_not_generate_one_second_100m(self, tmp_path: Path) -> None:
        """Window clipping and per-part analysis prevent impossible 100m=1s artifacts."""
        workout_xml = load_export_fragment("workout_running_too_fast.xml")
        route_dir = Path(__file__).resolve().parents[1] / "fixtures" / "exports" / "workout-routes"
        route_files = sorted(route_dir.glob("route_2024-12-26_*.gpx"))

        zip_path = tmp_path / "running_too_fast.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", build_health_export_xml([workout_xml]))
            for route_file in route_files:
                zf.writestr(
                    f"apple_health_export/workout-routes/{route_file.name}",
                    route_file.read_bytes(),
                )

        parser = ExportParser()
        with parser:
            parsed = parser.parse(str(zip_path))

        manager = WorkoutManager(parsed.workouts)
        result = manager.get_best_segments(topn=1, distances=[100])

        assert len(result) == 1
        duration_s = float(result.iloc[0]["duration_s"])
        assert duration_s > 1.0
