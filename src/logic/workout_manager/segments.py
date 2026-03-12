"""Best-segment mixin for WorkoutManager."""

from typing import Any, List, Optional, cast

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

    def get_best_segments(
        self, topn: int = 5, distances: Optional[list[int]] = None
    ) -> pd.DataFrame:
        """Return a DataFrame of best segments across all running workouts for a defined list of
        distances for the Top-N values of each segment distance.
        The segments are defined as the fastest time for a given distance
        Args:
            topn: Number of top segments to return for each distance
            distances: List of distances (in meters) to consider for segment analysis
                (defaults to DEFAULT_SEGMENT_DISTANCES)

        Returns:
            DataFrame with columns: startDate, distance, duration_s
        """
        if distances is None:
            distances = self.DEFAULT_SEGMENT_DISTANCES

        if topn <= 0:
            return pd.DataFrame(columns=["startDate", "distance", "duration_s"])

        runs = self.workouts[self.workouts["activityType"] == "Running"]
        if runs.empty:
            return pd.DataFrame(columns=["startDate", "distance", "duration_s"])

        results: List[List[Any]] = []

        for run in runs.itertuples():
            route_traces = self._extract_route_traces(run)
            if not route_traces:
                continue

            raw_run_distance: Any = getattr(run, "distance", None)
            run_distance_m: Optional[float] = (
                float(raw_run_distance)
                if raw_run_distance is not None and not pd.isna(raw_run_distance)
                else None
            )
            total_trace_distance_m = sum(
                route_trace.distance_meters for route_trace in route_traces
            )
            distance_scale_factor = WorkoutRoute.calculate_distance_scale_factor(
                total_trace_distance_m,
                run_distance_m,
            )

            for distance in distances:
                if run_distance_m is not None and float(distance) > run_distance_m:
                    continue
                distance_f = float(distance)
                fastest_for_run = min(
                    (
                        duration_s
                        for route_trace in route_traces
                        for duration_s in [
                            route_trace.find_fastest_segment(
                                distance_f,
                                distance_scale_factor=distance_scale_factor,
                            )
                        ]
                        if duration_s is not None
                    ),
                    default=None,
                )
                duration_s = fastest_for_run
                if duration_s is None:
                    continue

                results.append([run.startDate, distance, duration_s])

        if not results:
            return pd.DataFrame(columns=["startDate", "distance", "duration_s"])

        df = pd.DataFrame(results, columns=["startDate", "distance", "duration_s"])
        df = df.sort_values(["distance", "duration_s"], ascending=[True, True])
        df = df.groupby("distance").head(topn).reset_index(drop=True)

        return df
