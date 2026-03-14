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
        expected_duration = pytest.approx(377.0, rel=1e-3)  # type: ignore[misc]
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
        assert abs(float(result.iloc[0]["duration_s"]) - 260.0) < 1e-6

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

    def test_real_fixture_long_distance_includes_half_marathon_segments(
        self, tmp_path: Path
    ) -> None:
        """Long-distance fixture should produce best segments beyond 5 km."""
        workout_xml = load_export_fragment("workout_running_long_distance.xml")
        route_file = (
            Path(__file__).resolve().parents[1]
            / "fixtures"
            / "exports"
            / "workout-routes"
            / "route_2025-11-30_6.06pm.gpx"
        )

        zip_path = tmp_path / "running_long_distance.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", build_health_export_xml([workout_xml]))
            zf.writestr(
                "apple_health_export/workout-routes/route_2025-11-30_6.06pm.gpx",
                route_file.read_bytes(),
            )

        parser = ExportParser()
        with parser:
            parsed = parser.parse(str(zip_path))

        manager = WorkoutManager(parsed.workouts)
        distances = [100, 200, 400, 800, 1000, 5000, 10000, 15000, 21097]
        result = manager.get_best_segments(topn=1, distances=distances)

        available_distances = set(result["distance"].astype(int).tolist())
        assert 5000 in available_distances
        assert 10000 in available_distances
        assert 15000 in available_distances
        assert 21097 in available_distances

    def test_get_best_segments_ignores_single_point_route(self) -> None:
        """A route with fewer than two points should yield no best segment."""
        route = WorkoutRoute(
            points=[
                RoutePoint(
                    time=datetime(2025, 1, 1, tzinfo=timezone.utc),
                    latitude=0.0,
                    longitude=0.0,
                    altitude=0.0,
                )
            ]
        )

        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "route": [route],
                }
            )
        )

        result = manager.get_best_segments(topn=1, distances=[100])

        assert result.empty

    def test_get_best_segments_handles_time_reversal_by_splitting_trace(self) -> None:
        """Timestamp reversals should split traces and still allow valid segment computation."""
        t0 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        route = WorkoutRoute(
            points=[
                RoutePoint(time=t0, latitude=0.0, longitude=0.0, altitude=0.0),
                RoutePoint(
                    time=t0 + timedelta(seconds=5),
                    latitude=0.0,
                    longitude=0.001,
                    altitude=0.0,
                ),
                RoutePoint(
                    time=t0 - timedelta(seconds=1),
                    latitude=0.0,
                    longitude=0.002,
                    altitude=0.0,
                ),
                RoutePoint(
                    time=t0 + timedelta(seconds=1),
                    latitude=0.0,
                    longitude=0.003,
                    altitude=0.0,
                ),
            ]
        )

        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [1000.0],
                    "route": [route],
                }
            )
        )

        result = manager.get_best_segments(topn=1, distances=[100])

        assert len(result) == 1
        assert int(result.iloc[0]["distance"]) == 100

    def test_get_best_segments_uses_default_distances_when_not_provided(self) -> None:
        """When distances is None, manager default segment distances should be used."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [5000.0],
                    "route": [_two_point_route(300)],
                }
            )
        )

        result = manager.get_best_segments(topn=1, distances=None)

        assert not result.empty
        assert int(result.iloc[0]["distance"]) == 100

    def test_get_best_segments_skips_distance_above_run_distance(self) -> None:
        """Requested segment distance above run distance should be skipped."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [500.0],
                    "route": [_two_point_route(300)],
                }
            )
        )

        result = manager.get_best_segments(topn=1, distances=[1000])

        assert result.empty
        assert list(result.columns) == ["startDate", "distance", "duration_s"]

    def test_get_best_segments_handles_nan_distance_by_using_route_trace(self) -> None:
        """NaN run distance should not block segment computation when route data exists."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [float("nan")],
                    "route": [_two_point_route(300)],
                }
            )
        )

        result = manager.get_best_segments(topn=1, distances=[1000])

        assert len(result) == 1
        assert int(result.iloc[0]["distance"]) == 1000


class TestGetBestSegmentsDateFiltering:
    """Test date-range filtering in get_best_segments."""

    def test_get_best_segments_filters_by_start_date(self) -> None:
        """Workouts before start_date should be excluded."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-06-01")],
                    "distance": [5000.0, 5000.0],
                    "route": [_two_point_route(300), _two_point_route(200)],
                }
            )
        )

        result = manager.get_best_segments(
            topn=5, distances=[1000], start_date=datetime(2024, 3, 1)
        )

        # Only the June workout should be included; January workout excluded
        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["startDate"] == pd.Timestamp("2024-06-01")

    def test_get_best_segments_filters_by_end_date(self) -> None:
        """Workouts after end_date should be excluded."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": [pd.Timestamp("2024-01-01"), pd.Timestamp("2024-06-01")],
                    "distance": [5000.0, 5000.0],
                    "route": [_two_point_route(300), _two_point_route(200)],
                }
            )
        )

        result = manager.get_best_segments(
            topn=5, distances=[1000], end_date=datetime(2024, 3, 31)
        )

        # Only the January workout should be included; June workout excluded
        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["startDate"] == pd.Timestamp("2024-01-01")

    def test_get_best_segments_filters_by_both_dates(self) -> None:
        """Only workouts within [start_date, end_date] should contribute."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Running"],
                    "startDate": [
                        pd.Timestamp("2024-01-01"),
                        pd.Timestamp("2024-03-15"),
                        pd.Timestamp("2024-06-01"),
                    ],
                    "distance": [5000.0, 5000.0, 5000.0],
                    "route": [_two_point_route(300), _two_point_route(200), _two_point_route(400)],
                }
            )
        )

        result = manager.get_best_segments(
            topn=5,
            distances=[1000],
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 4, 30),
        )

        # Only the March workout should be included
        assert not result.empty
        assert all(result["startDate"] >= pd.Timestamp("2024-02-01"))
        assert all(result["startDate"] <= pd.Timestamp("2024-04-30"))

    def test_get_best_segments_returns_empty_when_no_workouts_in_range(self) -> None:
        """Return empty DataFrame when date filter excludes all workouts."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2024-01-01")],
                    "distance": [5000.0],
                    "route": [_two_point_route(300)],
                }
            )
        )

        result = manager.get_best_segments(
            topn=5, distances=[1000], start_date=datetime(2024, 6, 1)
        )

        assert result.empty
        assert list(result.columns) == ["startDate", "distance", "duration_s"]

    def test_get_best_segments_end_date_is_inclusive(self) -> None:
        """A workout exactly on end_date should be included."""
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2024-03-31")],
                    "distance": [5000.0],
                    "route": [_two_point_route(300)],
                }
            )
        )

        result = manager.get_best_segments(
            topn=5, distances=[1000], end_date=datetime(2024, 3, 31)
        )

        assert not result.empty


class TestGetCriticalPower:
    """Test suite for WorkoutManager.get_critical_power."""

    @staticmethod
    def _make_speed_route(
        start_time: datetime,
        distance_m: float,
        duration_s: float,
        end_longitude: float,
    ) -> WorkoutRoute:
        """Create a 2-point route driven by speed attribute for the given distance/time."""
        speed = distance_m / duration_s
        return WorkoutRoute(
            points=[
                RoutePoint(
                    time=start_time,
                    latitude=0.0,
                    longitude=0.0,
                    altitude=0.0,
                    speed=speed,
                ),
                RoutePoint(
                    time=start_time + pd.Timedelta(seconds=duration_s),
                    latitude=0.0,
                    longitude=end_longitude,
                    altitude=0.0,
                    speed=speed,
                ),
            ]
        )

    def _make_manager_with_two_segments(
        self,
        time_800m: int,
        power_800m: float,
        time_5000m: int,
        power_5000m: float,
    ) -> WorkoutManager:
        """Return a manager with 800 m and 5000 m routes and workout-level average power."""
        route_800 = self._make_speed_route(
            datetime(2025, 1, 1, tzinfo=timezone.utc), 800.0, float(time_800m), 0.007
        )
        route_5000 = self._make_speed_route(
            datetime(2025, 2, 1, tzinfo=timezone.utc), 5000.0, float(time_5000m), 0.045
        )
        return WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": [
                        pd.Timestamp("2025-01-01"),
                        pd.Timestamp("2025-02-01"),
                    ],
                    "distance": [800.0, 5000.0],
                    "averageRunningPower": [power_800m, power_5000m],
                    "route": [route_800, route_5000],
                }
            )
        )

    def test_returns_none_for_empty_manager(self) -> None:
        """No workouts should return None."""
        manager = WorkoutManager()

        result = manager.get_critical_power()

        assert result is None

    def test_returns_none_when_power_column_missing(self) -> None:
        """Return None when workouts have no running power data at all."""
        route_800 = self._make_speed_route(
            datetime(2025, 1, 1, tzinfo=timezone.utc), 800.0, 160.0, 0.007
        )
        route_5000 = self._make_speed_route(
            datetime(2025, 2, 1, tzinfo=timezone.utc), 5000.0, 1250.0, 0.045
        )
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-01")],
                    "distance": [800.0, 5000.0],
                    "route": [route_800, route_5000],
                }
            )
        )

        result = manager.get_critical_power()

        assert result is None

    def test_returns_none_when_short_distance_missing(self) -> None:
        """Return None when no best segment exists for the short distance."""
        route_5000 = self._make_speed_route(
            datetime(2025, 1, 1, tzinfo=timezone.utc), 5000.0, 1500.0, 0.045
        )
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [5000.0],
                    "averageRunningPower": [250.0],
                    "route": [route_5000],
                }
            )
        )

        result = manager.get_critical_power(
            short_distance=10000,  # longer than this workout's distance
            long_distance=50000,
        )

        assert result is None

    def test_returns_none_when_short_ge_long(self) -> None:
        """Return None when short_distance >= long_distance (degenerate inputs)."""
        manager = WorkoutManager()

        assert manager.get_critical_power(short_distance=800, long_distance=800) is None
        assert manager.get_critical_power(short_distance=5000, long_distance=800) is None

    def test_critical_power_formula(self) -> None:
        """CP and W' should satisfy the 2-parameter model for known inputs."""
        time_800 = 160  # s
        power_800 = 350.0  # W
        time_5000 = 1250  # s
        power_5000 = 250.0  # W
        manager = self._make_manager_with_two_segments(time_800, power_800, time_5000, power_5000)

        result = manager.get_critical_power(
            topn=1,
            short_distance=800,
            long_distance=5000,
        )

        assert result is not None
        # W1 = 350 * 160 = 56000 J; W2 = 250 * 1250 = 312500 J
        # CP = (312500 - 56000) / (1250 - 160) = 256500 / 1090 ≈ 235.3 W
        # W' = 56000 - 235.3 * 160 ≈ 18352 J
        assert result["short_distance"] == 800
        assert result["long_distance"] == 5000
        assert result["avg_time_short_s"] == pytest.approx(time_800, rel=0.05)
        assert result["avg_time_long_s"] == pytest.approx(time_5000, rel=0.05)
        assert result["avg_power_short_w"] == pytest.approx(power_800, rel=0.01)
        assert result["avg_power_long_w"] == pytest.approx(power_5000, rel=0.01)
        work_short = power_800 * time_800
        work_long = power_5000 * time_5000
        expected_cp = (work_long - work_short) / (time_5000 - time_800)
        expected_w_prime = work_short - expected_cp * time_800
        assert result["critical_power_w"] == pytest.approx(expected_cp, rel=0.01)
        assert result["w_prime_j"] == pytest.approx(expected_w_prime, rel=0.01)
        assert result["count_short"] == 1
        assert result["count_long"] == 1

    def test_averages_multiple_segments(self) -> None:
        """With topn>1, CP is based on the mean time and power across top-N segments."""
        # Two 800 m workouts (160 s / 350 W and 180 s / 330 W → avg 170 s / 340 W)
        # One 5000 m workout (1250 s / 250 W)
        route_800_fast = self._make_speed_route(
            datetime(2025, 1, 1, tzinfo=timezone.utc), 800.0, 160.0, 0.007
        )
        route_800_slow = self._make_speed_route(
            datetime(2025, 1, 2, tzinfo=timezone.utc), 800.0, 180.0, 0.007
        )
        route_long = self._make_speed_route(
            datetime(2025, 2, 1, tzinfo=timezone.utc), 5000.0, 1250.0, 0.045
        )
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Running"],
                    "startDate": [
                        pd.Timestamp("2025-01-01"),
                        pd.Timestamp("2025-01-02"),
                        pd.Timestamp("2025-02-01"),
                    ],
                    "distance": [800.0, 800.0, 5000.0],
                    "averageRunningPower": [350.0, 330.0, 250.0],
                    "route": [route_800_fast, route_800_slow, route_long],
                }
            )
        )

        result = manager.get_critical_power(topn=2, short_distance=800, long_distance=5000)

        assert result is not None
        assert result["count_short"] == 2
        assert result["count_long"] == 1
        assert result["avg_time_short_s"] == pytest.approx(170.0, rel=0.05)
        assert result["avg_power_short_w"] == pytest.approx(340.0, rel=0.01)


class TestGetCriticalPowerEvolution:
    """Test suite for WorkoutManager.get_critical_power_evolution."""

    @staticmethod
    def _make_speed_route(
        start_time: datetime,
        distance_m: float,
        duration_s: float,
        end_longitude: float,
    ) -> WorkoutRoute:
        speed = distance_m / duration_s
        return WorkoutRoute(
            points=[
                RoutePoint(time=start_time, latitude=0.0, longitude=0.0, altitude=0.0, speed=speed),
                RoutePoint(
                    time=start_time + pd.Timedelta(seconds=duration_s),
                    latitude=0.0,
                    longitude=end_longitude,
                    altitude=0.0,
                    speed=speed,
                ),
            ]
        )

    def test_returns_empty_for_empty_manager(self) -> None:
        """No workouts returns an empty DataFrame with expected columns."""
        manager = WorkoutManager()

        result = manager.get_critical_power_evolution()

        assert result.empty
        assert list(result.columns) == ["period", "critical_power_w", "w_prime_kj"]

    def test_returns_empty_when_power_column_missing(self) -> None:
        """Return empty when no running power data is available."""
        route = self._make_speed_route(
            datetime(2025, 1, 1, tzinfo=timezone.utc), 800.0, 160.0, 0.007
        )
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [800.0],
                    "route": [route],
                }
            )
        )

        result = manager.get_critical_power_evolution()

        assert result.empty

    def test_evolution_groups_by_period(self) -> None:
        """Each calendar period with both distances produces one CP/W' row."""
        # Month 1: 800 m (160 s / 350 W) + 5000 m (1250 s / 250 W)
        # Month 2: 800 m (155 s / 360 W) + 5000 m (1200 s / 260 W)
        routes_and_data = [
            (datetime(2025, 1, 5, tzinfo=timezone.utc), 800.0, 160.0, 0.007, 350.0),
            (datetime(2025, 1, 20, tzinfo=timezone.utc), 5000.0, 1250.0, 0.045, 250.0),
            (datetime(2025, 2, 5, tzinfo=timezone.utc), 800.0, 155.0, 0.007, 360.0),
            (datetime(2025, 2, 20, tzinfo=timezone.utc), 5000.0, 1200.0, 0.045, 260.0),
        ]
        routes = [
            self._make_speed_route(dt, dist, dur, lon)
            for dt, dist, dur, lon, _ in routes_and_data
        ]
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"] * 4,
                    "startDate": [pd.Timestamp(dt) for dt, *_ in routes_and_data],
                    "distance": [d for _, d, *_ in routes_and_data],
                    "averageRunningPower": [p for *_, p in routes_and_data],
                    "route": routes,
                }
            )
        )

        result = manager.get_critical_power_evolution(period="M")

        assert len(result) == 2
        assert list(result.columns) == ["period", "critical_power_w", "w_prime_kj"]
        # Both periods should have positive CP and W'
        assert all(result["critical_power_w"] > 0)
        assert all(result["w_prime_kj"] > 0)

    def test_period_with_only_one_distance_is_skipped(self) -> None:
        """A period with only the short distance but no long distance is omitted."""
        route_800 = self._make_speed_route(
            datetime(2025, 1, 1, tzinfo=timezone.utc), 800.0, 160.0, 0.007
        )
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [800.0],
                    "averageRunningPower": [350.0],
                    "route": [route_800],
                }
            )
        )

        result = manager.get_critical_power_evolution(period="M")

        assert result.empty
