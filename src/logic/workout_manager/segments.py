"""Best-segment mixin for WorkoutManager."""

from datetime import datetime
from typing import Any, List, Optional, Union, cast

import pandas as pd

from logic.workout_route import WorkoutRoute


class WorkoutManagerSegmentsMixin:
    """Best-segment computation methods for running workouts."""

    workouts: pd.DataFrame
    DEFAULT_SEGMENT_DISTANCES: list[int]

    @staticmethod
    def _split_route_into_traces(route: WorkoutRoute) -> list[WorkoutRoute]:
        """Split a route into monotonic-time traces.

        Segment analysis must not cross timestamp reversals because they indicate
        disjoint windows or malformed ordering.
        """
        if len(route.points) < 2:
            return []

        traces: list[WorkoutRoute] = []
        current_points = [route.points[0]]
        for point in route.points[1:]:
            if point.time < current_points[-1].time:
                if len(current_points) >= 2:
                    traces.append(WorkoutRoute(points=current_points))
                current_points = [point]
                continue
            current_points.append(point)

        if len(current_points) >= 2:
            traces.append(WorkoutRoute(points=current_points))

        return traces

    @classmethod
    def _extract_route_traces(cls, run_record: Any) -> list[WorkoutRoute]:
        """Extract analysis traces from route parts first, then fallback to route."""
        route_parts_obj: Any = (
            run_record.route_parts if hasattr(run_record, "route_parts") else None
        )
        if isinstance(route_parts_obj, list):
            traces: list[WorkoutRoute] = []
            route_parts_list = cast(list[object], route_parts_obj)
            for route_part in route_parts_list:
                if isinstance(route_part, WorkoutRoute):
                    traces.extend(cls._split_route_into_traces(route_part))
            if traces:
                return traces

        route_obj: Any = run_record.route if hasattr(run_record, "route") else None
        if isinstance(route_obj, WorkoutRoute):
            return cls._split_route_into_traces(route_obj)

        return []

    @staticmethod
    def _empty_best_segments_frame() -> pd.DataFrame:
        """Return an empty DataFrame with the stable best-segment schema."""
        return pd.DataFrame(columns=["startDate", "distance", "duration_s"])

    @staticmethod
    def _get_run_distance_m(run_record: Any) -> Optional[float]:
        """Return the run distance in meters when present and finite."""
        raw_run_distance: Any = getattr(run_record, "distance", None)
        if raw_run_distance is None or pd.isna(raw_run_distance):
            return None
        return float(raw_run_distance)

    @staticmethod
    def _build_best_segments_frame(results: list[list[Any]], topn: int) -> pd.DataFrame:
        """Sort and keep the fastest Top-N segments per requested distance."""
        df = pd.DataFrame(results, columns=["startDate", "distance", "duration_s"])
        df = df.sort_values(["distance", "duration_s"], ascending=[True, True])
        return df.groupby("distance").head(topn).reset_index(drop=True)

    @staticmethod
    def _get_fastest_duration_for_distance(
        route_traces: list[WorkoutRoute],
        distance_m: float,
        distance_scale_factor: float,
    ) -> Optional[float]:
        """Return the fastest valid segment duration for one distance across all traces."""
        return min(
            (
                duration_s
                for route_trace in route_traces
                for duration_s in [
                    route_trace.find_fastest_segment(
                        distance_m,
                        distance_scale_factor=distance_scale_factor,
                    )
                ]
                if duration_s is not None
            ),
            default=None,
        )

    def _get_run_best_segment_rows(
        self,
        run_record: Any,
        distances: list[int],
    ) -> list[list[Any]]:
        """Collect best-segment result rows for one running workout."""
        route_traces = self._extract_route_traces(run_record)
        if not route_traces:
            return []

        run_distance_m = self._get_run_distance_m(run_record)
        total_trace_distance_m = sum(route_trace.distance_meters for route_trace in route_traces)
        distance_scale_factor = WorkoutRoute.calculate_distance_scale_factor(
            total_trace_distance_m,
            run_distance_m,
        )

        rows: list[list[Any]] = []
        for distance in distances:
            if run_distance_m is not None and float(distance) > run_distance_m:
                continue

            duration_s = self._get_fastest_duration_for_distance(
                route_traces,
                float(distance),
                distance_scale_factor,
            )
            if duration_s is None:
                continue

            rows.append([run_record.startDate, distance, duration_s])

        return rows

    def get_best_segments(
        self,
        topn: int = 5,
        distances: Optional[list[int]] = None,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        """Return a DataFrame of best segments across all running workouts for a defined list of
        distances for the Top-N values of each segment distance.
        The segments are defined as the fastest time for a given distance
        Args:
            topn: Number of top segments to return for each distance
            distances: List of distances (in meters) to consider for segment analysis
                (defaults to DEFAULT_SEGMENT_DISTANCES)
            start_date: Optional start date to filter workouts
            end_date: Optional end date to filter workouts (inclusive)

        Returns:
            DataFrame with columns: startDate, distance, duration_s
        """
        if distances is None:
            distances = self.DEFAULT_SEGMENT_DISTANCES

        if topn <= 0:
            return self._empty_best_segments_frame()

        required_columns = {"activityType", "startDate"}
        if not required_columns.issubset(self.workouts.columns):
            return self._empty_best_segments_frame()
        runs = self.workouts[self.workouts["activityType"] == "Running"]

        if start_date is not None:
            runs = runs[runs["startDate"] >= pd.Timestamp(start_date)]
        if end_date is not None:
            # Use exclusive next-day boundary so the full end_date day is included
            # (end_date from the date picker is a midnight datetime, i.e. date-only).
            next_day = pd.Timestamp(end_date) + pd.Timedelta(days=1)
            runs = runs[runs["startDate"] < next_day]

        if runs.empty:
            return self._empty_best_segments_frame()

        results: List[List[Any]] = []

        for run in runs.itertuples():
            results.extend(self._get_run_best_segment_rows(run, distances))

        if not results:
            return self._empty_best_segments_frame()

        return self._build_best_segments_frame(results, topn)
