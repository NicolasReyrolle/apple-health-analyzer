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
        assert list(result.columns) == [
            "startDate",
            "distance",
            "duration_s",
            "segment_start",
            "segment_end",
        ]

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
        assert list(result.columns) == [
            "startDate",
            "distance",
            "duration_s",
            "segment_start",
            "segment_end",
        ]

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
        assert list(result.columns) == [
            "startDate",
            "distance",
            "duration_s",
            "segment_start",
            "segment_end",
        ]

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

        result = manager.get_best_segments(topn=5, distances=[1000], end_date=datetime(2024, 3, 31))

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
        assert list(result.columns) == [
            "startDate",
            "distance",
            "duration_s",
            "segment_start",
            "segment_end",
        ]

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

        result = manager.get_best_segments(topn=5, distances=[1000], end_date=datetime(2024, 3, 31))

        assert not result.empty


class TestAnnotateSegmentsWithPower:
    """Test suite for WorkoutManager.annotate_segments_with_power."""

    @staticmethod
    def _make_route(start_time: datetime, duration_s: float) -> WorkoutRoute:
        # Use speed=0.0 so distance is computed via haversine (0.0→0.01 lon ≈ 1113 m)
        return WorkoutRoute(
            points=[
                RoutePoint(time=start_time, latitude=0.0, longitude=0.0, altitude=0.0, speed=0.0),
                RoutePoint(
                    time=start_time + timedelta(seconds=duration_s),
                    latitude=0.0,
                    longitude=0.01,
                    altitude=0.0,
                    speed=0.0,
                ),
            ]
        )

    @staticmethod
    def _record_df(timestamp: str, value: float) -> pd.DataFrame:
        return pd.DataFrame({"startDate": [timestamp], "value": [value]})

    def _make_manager(
        self, duration_s: float, workout_duration_s: float, avg_power: float | None = None
    ) -> WorkoutManager:
        start = datetime(2025, 1, 1, tzinfo=timezone.utc)
        cols: dict = {
            "activityType": ["Running"],
            "startDate": [pd.Timestamp("2025-01-01")],
            "distance": [5000.0],
            "duration": [workout_duration_s],
            "route": [self._make_route(start, duration_s)],
        }
        if avg_power is not None:
            cols["averageRunningPower"] = [avg_power]
        return WorkoutManager(pd.DataFrame(cols))

    def test_individual_records_used_when_within_window(self) -> None:
        """Power record inside the segment window should be used as avg_power."""
        manager = self._make_manager(duration_s=160.0, workout_duration_s=3600.0)
        # Record at +80 s (middle of 0–160 s window)
        rp_df = self._record_df("2025-01-01T00:01:20+00:00", 320.0)
        segments = manager.get_best_segments(topn=1, distances=[1000])

        result = manager.annotate_segments_with_power(segments, rp_df)

        assert "segment_avg_power" in result.columns
        assert result["segment_avg_power"].iloc[0] == pytest.approx(320.0)

    def test_record_outside_window_yields_none(self) -> None:
        """Power record entirely outside the segment window should not be used."""
        manager = self._make_manager(duration_s=160.0, workout_duration_s=3600.0)
        # Record 10 minutes after the window ends
        rp_df = self._record_df("2025-01-01T00:30:00+00:00", 320.0)
        segments = manager.get_best_segments(topn=1, distances=[1000])

        result = manager.annotate_segments_with_power(segments, rp_df)

        assert result["segment_avg_power"].iloc[0] is None

    def test_falls_back_to_workout_stats_when_durations_close(self) -> None:
        """Workout avg power should be used when workout duration ≈ segment duration."""
        # Segment ≈ 160 s, workout = 162 s (within 10 %)
        manager = self._make_manager(duration_s=160.0, workout_duration_s=162.0, avg_power=280.0)
        segments = manager.get_best_segments(topn=1, distances=[1000])

        result = manager.annotate_segments_with_power(segments, None)

        assert result["segment_avg_power"].iloc[0] == pytest.approx(280.0)

    def test_no_fallback_when_workout_duration_far_from_segment(self) -> None:
        """Workout avg power must NOT be used when workout is much longer than segment."""
        # Segment ≈ 160 s, workout = 3600 s (>10 % difference)
        manager = self._make_manager(duration_s=160.0, workout_duration_s=3600.0, avg_power=280.0)
        segments = manager.get_best_segments(topn=1, distances=[1000])

        result = manager.annotate_segments_with_power(segments, None)

        assert result["segment_avg_power"].iloc[0] is None

    def test_individual_records_take_priority_over_workout_stats(self) -> None:
        """Individual records should override workout-level avg power."""
        # Workout duration close to segment (would allow fallback), but individual record exists
        manager = self._make_manager(duration_s=160.0, workout_duration_s=162.0, avg_power=200.0)
        rp_df = self._record_df("2025-01-01T00:01:20+00:00", 350.0)
        segments = manager.get_best_segments(topn=1, distances=[1000])

        result = manager.annotate_segments_with_power(segments, rp_df)

        assert result["segment_avg_power"].iloc[0] == pytest.approx(350.0)

    def test_empty_segments_returns_empty_with_column(self) -> None:
        """Empty segments DataFrame should return empty with segment_avg_power column."""
        manager = WorkoutManager()
        segments = manager.get_best_segments(topn=1, distances=[1000])

        result = manager.annotate_segments_with_power(segments, None)

        assert result.empty
        assert "segment_avg_power" in result.columns


class TestGetCriticalPower:
    """Test suite for WorkoutManager.get_critical_power."""

    @staticmethod
    def _make_route(
        start_time: datetime, distance_m: float, duration_s: float, end_lon: float
    ) -> WorkoutRoute:
        speed = distance_m / duration_s
        return WorkoutRoute(
            points=[
                RoutePoint(time=start_time, latitude=0.0, longitude=0.0, altitude=0.0, speed=speed),
                RoutePoint(
                    time=start_time + timedelta(seconds=duration_s),
                    latitude=0.0,
                    longitude=end_lon,
                    altitude=0.0,
                    speed=speed,
                ),
            ]
        )

    @staticmethod
    def _rp_df(start_time: datetime, duration_s: float, power_w: float) -> pd.DataFrame:
        """RunningPower record placed in the middle of the segment window."""
        mid = start_time + timedelta(seconds=duration_s / 2)
        return pd.DataFrame(
            {"startDate": [mid.strftime("%Y-%m-%dT%H:%M:%S+00:00")], "value": [power_w]}
        )

    def test_returns_none_for_empty_manager(self) -> None:
        """No workouts should return None."""
        assert WorkoutManager().get_critical_power() is None

    def test_returns_none_when_no_power_data(self) -> None:
        """Return None when neither individual records nor workout stats are available."""
        t800 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        t5000 = datetime(2025, 2, 1, tzinfo=timezone.utc)
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-01")],
                    "distance": [800.0, 5000.0],
                    "route": [
                        self._make_route(t800, 800.0, 160.0, 0.007),
                        self._make_route(t5000, 5000.0, 1250.0, 0.045),
                    ],
                }
            )
        )

        assert manager.get_critical_power() is None

    def test_returns_none_when_short_distance_missing(self) -> None:
        """Return None when no best segment exists for the short distance."""
        t = datetime(2025, 1, 1, tzinfo=timezone.utc)
        route = self._make_route(t, 5000.0, 1500.0, 0.045)
        rp_df = self._rp_df(t, 1500.0, 250.0)
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [5000.0],
                    "route": [route],
                }
            )
        )

        assert (
            manager.get_critical_power(
                running_power_df=rp_df, short_distance=10000, long_distance=50000
            )
            is None
        )

    def test_returns_none_when_short_ge_long(self) -> None:
        """Return None for degenerate distance inputs."""
        manager = WorkoutManager()
        assert manager.get_critical_power(short_distance=800, long_distance=800) is None
        assert manager.get_critical_power(short_distance=5000, long_distance=800) is None

    def test_critical_power_formula_with_individual_records(self) -> None:
        """CP and W' computed from individual RunningPower records within segment windows."""
        time_800 = 160
        power_800 = 350.0
        time_5000 = 1250
        power_5000 = 250.0
        t800 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        t5000 = datetime(2025, 2, 1, tzinfo=timezone.utc)

        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-01")],
                    "distance": [800.0, 5000.0],
                    "route": [
                        self._make_route(t800, 800.0, float(time_800), 0.007),
                        self._make_route(t5000, 5000.0, float(time_5000), 0.045),
                    ],
                }
            )
        )

        # Build a combined RunningPower records DataFrame with one record per segment
        rp_df = pd.concat(
            [
                self._rp_df(t800, float(time_800), power_800),
                self._rp_df(t5000, float(time_5000), power_5000),
            ],
            ignore_index=True,
        )

        result = manager.get_critical_power(
            running_power_df=rp_df, topn=1, short_distance=800, long_distance=5000
        )

        assert result is not None
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

    def test_fallback_to_workout_stats_when_workout_is_the_segment(self) -> None:
        """Workout-level avg power is used when workout duration ≈ segment duration."""
        time_800 = 160
        time_5000 = 1250
        t800 = datetime(2025, 1, 1, tzinfo=timezone.utc)
        t5000 = datetime(2025, 2, 1, tzinfo=timezone.utc)

        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": [pd.Timestamp("2025-01-01"), pd.Timestamp("2025-02-01")],
                    "distance": [800.0, 5000.0],
                    # duration ≈ segment duration (within 10%)
                    "duration": [float(time_800), float(time_5000)],
                    "averageRunningPower": [350.0, 250.0],
                    "route": [
                        self._make_route(t800, 800.0, float(time_800), 0.007),
                        self._make_route(t5000, 5000.0, float(time_5000), 0.045),
                    ],
                }
            )
        )

        # No individual records, but workout duration ≈ segment → fallback applies
        result = manager.get_critical_power(
            running_power_df=None, topn=1, short_distance=800, long_distance=5000
        )

        assert result is not None
        assert result["avg_power_short_w"] == pytest.approx(350.0, rel=0.01)
        assert result["avg_power_long_w"] == pytest.approx(250.0, rel=0.01)


class TestGetCriticalPowerEvolution:
    """Test suite for WorkoutManager.get_critical_power_evolution."""

    @staticmethod
    def _make_route(
        start_time: datetime, distance_m: float, duration_s: float, end_lon: float
    ) -> WorkoutRoute:
        speed = distance_m / duration_s
        return WorkoutRoute(
            points=[
                RoutePoint(time=start_time, latitude=0.0, longitude=0.0, altitude=0.0, speed=speed),
                RoutePoint(
                    time=start_time + timedelta(seconds=duration_s),
                    latitude=0.0,
                    longitude=end_lon,
                    altitude=0.0,
                    speed=speed,
                ),
            ]
        )

    @staticmethod
    def _rp_record(start_time: datetime, duration_s: float, power_w: float) -> dict:
        mid = start_time + timedelta(seconds=duration_s / 2)
        return {"startDate": mid.strftime("%Y-%m-%dT%H:%M:%S+00:00"), "value": power_w}

    def test_returns_empty_for_empty_manager(self) -> None:
        """No workouts returns an empty DataFrame with expected columns."""
        result = WorkoutManager().get_critical_power_evolution()
        assert result.empty
        assert list(result.columns) == ["period", "critical_power_w", "w_prime_kj"]

    def test_returns_empty_when_no_power_data(self) -> None:
        """Return empty when no individual records and no workout stats available."""
        t = datetime(2025, 1, 1, tzinfo=timezone.utc)
        route = self._make_route(t, 800.0, 160.0, 0.007)
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

        assert manager.get_critical_power_evolution().empty

    def test_evolution_groups_by_period(self) -> None:
        """Each calendar period with both distances produces one CP/W' row."""
        data = [
            (datetime(2025, 1, 5, tzinfo=timezone.utc), 800.0, 160.0, 0.007, 350.0),
            (datetime(2025, 1, 20, tzinfo=timezone.utc), 5000.0, 1250.0, 0.045, 250.0),
            (datetime(2025, 2, 5, tzinfo=timezone.utc), 800.0, 155.0, 0.007, 360.0),
            (datetime(2025, 2, 20, tzinfo=timezone.utc), 5000.0, 1200.0, 0.045, 260.0),
        ]
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"] * 4,
                    "startDate": [pd.Timestamp(dt) for dt, *_ in data],
                    "distance": [d for _, d, *_ in data],
                    "route": [
                        self._make_route(dt, dist, dur, lon) for dt, dist, dur, lon, _ in data
                    ],
                }
            )
        )
        rp_df = pd.DataFrame([self._rp_record(dt, dur, pwr) for dt, _, dur, _, pwr in data])

        result = manager.get_critical_power_evolution(running_power_df=rp_df, period="M")

        assert len(result) == 2
        assert list(result.columns) == ["period", "critical_power_w", "w_prime_kj"]
        assert all(result["critical_power_w"] > 0)
        assert all(result["w_prime_kj"] > 0)

    def test_period_with_only_one_distance_is_skipped(self) -> None:
        """A period with only the short distance but no long distance is omitted."""
        t = datetime(2025, 1, 1, tzinfo=timezone.utc)
        manager = WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": [pd.Timestamp("2025-01-01")],
                    "distance": [800.0],
                    "route": [self._make_route(t, 800.0, 160.0, 0.007)],
                }
            )
        )
        rp_df = pd.DataFrame([self._rp_record(t, 160.0, 350.0)])

        assert manager.get_critical_power_evolution(running_power_df=rp_df, period="M").empty
