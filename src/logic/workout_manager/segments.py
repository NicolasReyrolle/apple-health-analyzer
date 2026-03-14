"""Best-segment mixin for WorkoutManager."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, List, Optional, TypedDict, Union

import pandas as pd

from logic.workout_route import WorkoutRoute

if TYPE_CHECKING:
    from pandas import Timestamp

_RUNNING_POWER_COL = "averageRunningPower"


class CriticalPowerResult(TypedDict):
    """Result of a critical power calculation for two segment distances."""

    short_distance: int
    long_distance: int
    avg_time_short_s: float
    avg_time_long_s: float
    avg_power_short_w: float
    avg_power_long_w: float
    critical_power_w: float
    w_prime_j: float
    count_short: int
    count_long: int


class WorkoutManagerSegmentsMixin:
    """Best-segment computation methods for running workouts."""

    workouts: pd.DataFrame
    DEFAULT_SEGMENT_DISTANCES: list[int]
    _filter_workouts: Callable[
        [str, Optional[Union[datetime, "Timestamp"]], Optional[Union[datetime, "Timestamp"]]],
        pd.DataFrame,
    ]

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
            for route_part in route_parts_obj:  # type: ignore[misc]
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

    def _fallback_filter_running_workouts(
        self,
        start_date: Optional[Union[datetime, pd.Timestamp]],
        end_date: Optional[Union[datetime, pd.Timestamp]],
    ) -> pd.DataFrame:
        """Fallback: filter running workouts with local logic and end-date handling."""
        runs = self.workouts[self.workouts["activityType"] == "Running"]
        if start_date is not None:
            runs = runs[runs["startDate"] >= pd.Timestamp(start_date)]
        if end_date is not None:
            end_ts = pd.Timestamp(end_date)
            is_date_only = end_ts.normalize() == end_ts
            if is_date_only:
                runs = runs[runs["startDate"] < end_ts + pd.Timedelta(days=1)]
            else:
                runs = runs[runs["startDate"] <= end_ts]
        return runs

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

        # Prefer shared filtering logic from WorkoutManagerAggregationsMixin to keep
        # date-handling semantics consistent across APIs.
        if hasattr(self, "_filter_workouts"):
            runs = self._filter_workouts("Running", start_date, end_date)
        else:
            runs = self._fallback_filter_running_workouts(start_date, end_date)

        if runs.empty:
            return self._empty_best_segments_frame()

        results: List[List[Any]] = []

        for run in runs.itertuples():
            results.extend(self._get_run_best_segment_rows(run, distances))

        if not results:
            return self._empty_best_segments_frame()

        return self._build_best_segments_frame(results, topn)

    def get_critical_power(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements
        self,
        topn: int = 5,
        short_distance: int = 800,
        long_distance: int = 5000,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Optional["CriticalPowerResult"]:
        """Compute Critical Power (CP) and W' using the 2-parameter power-duration model.

        The model fits a linear work-time relationship:
            W = CP * t + W'
        where W = P_avg * t is the total work done (Joules), CP is the maximum sustainable
        power (Watts), and W' is the anaerobic work capacity (Joules).

        For each target distance the average of the top-N best segment times and the
        average ``averageRunningPower`` of those workouts are used as the two data points.

        Args:
            topn: Number of best segments to average per distance (default 5).
            short_distance: Shorter target distance in metres (default 800).
            long_distance: Longer target distance in metres (default 5000).
            start_date: Optional start date filter applied to workouts.
            end_date: Optional end date filter applied to workouts (inclusive).

        Returns:
            A :class:`CriticalPowerResult` dict, or ``None`` when either distance
            has no matching segments with power data, or the model yields non-physical
            values (CP ≤ 0 or W' ≤ 0), or the two distances are equal.
        """
        if short_distance >= long_distance:
            return None

        if _RUNNING_POWER_COL not in self.workouts.columns:
            return None

        segments = self.get_best_segments(
            topn=topn,
            distances=[short_distance, long_distance],
            start_date=start_date,
            end_date=end_date,
        )

        if segments.empty:
            return None

        short_rows = segments[segments["distance"] == short_distance]
        long_rows = segments[segments["distance"] == long_distance]

        if short_rows.empty or long_rows.empty:
            return None

        # Join each segment group with workout-level average power
        power_lookup = self.workouts[["startDate", _RUNNING_POWER_COL]].dropna(
            subset=[_RUNNING_POWER_COL]
        )
        short_with_power = short_rows.merge(power_lookup, on="startDate", how="inner")
        long_with_power = long_rows.merge(power_lookup, on="startDate", how="inner")

        if short_with_power.empty or long_with_power.empty:
            return None

        avg_time_short = float(short_with_power["duration_s"].mean())
        avg_time_long = float(long_with_power["duration_s"].mean())
        avg_power_short = float(short_with_power[_RUNNING_POWER_COL].mean())
        avg_power_long = float(long_with_power[_RUNNING_POWER_COL].mean())

        time_diff = avg_time_long - avg_time_short
        if time_diff <= 0:
            return None

        work_short = avg_power_short * avg_time_short  # Joules
        work_long = avg_power_long * avg_time_long  # Joules

        critical_power_w = (work_long - work_short) / time_diff
        w_prime_j = work_short - critical_power_w * avg_time_short

        if critical_power_w <= 0 or w_prime_j <= 0:
            return None

        return CriticalPowerResult(
            short_distance=short_distance,
            long_distance=long_distance,
            avg_time_short_s=avg_time_short,
            avg_time_long_s=avg_time_long,
            avg_power_short_w=avg_power_short,
            avg_power_long_w=avg_power_long,
            critical_power_w=critical_power_w,
            w_prime_j=w_prime_j,
            count_short=len(short_with_power),
            count_long=len(long_with_power),
        )

    def get_critical_power_evolution(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        period: str = "M",
        short_distance: int = 800,
        long_distance: int = 5000,
        topn: int = 5,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        """Compute Critical Power (CP) and W' for each time period.

        For each period (e.g. month), the top-N best segments for both distances
        that fall within that period are averaged to derive one (CP, W') data point.
        Periods with insufficient segment data for either distance are omitted.

        Args:
            period: Pandas period alias (e.g. ``"M"`` monthly, ``"Q"`` quarterly,
                ``"Y"`` yearly).  Must match the ``trends_period`` codes used
                elsewhere in the app.
            short_distance: Shorter target distance in metres (default 800).
            long_distance: Longer target distance in metres (default 5000).
            topn: Number of best segments to include per distance per period.
            start_date: Optional start date filter.
            end_date: Optional end date filter (inclusive).

        Returns:
            DataFrame with columns ``period`` (str), ``critical_power_w`` (float),
            ``w_prime_kj`` (float).  Empty if insufficient data.
        """
        _empty = pd.DataFrame(columns=["period", "critical_power_w", "w_prime_kj"])

        if short_distance >= long_distance:
            return _empty

        if _RUNNING_POWER_COL not in self.workouts.columns:
            return _empty

        segments = self.get_best_segments(
            topn=topn,
            distances=[short_distance, long_distance],
            start_date=start_date,
            end_date=end_date,
        )

        if segments.empty:
            return _empty

        power_lookup = self.workouts[["startDate", _RUNNING_POWER_COL]].dropna(
            subset=[_RUNNING_POWER_COL]
        )
        segments_with_power = segments.merge(power_lookup, on="startDate", how="inner")

        if segments_with_power.empty:
            return _empty

        segments_with_power = segments_with_power.copy()
        # Strip timezone before period conversion to avoid pandas UserWarning about
        # dropping tz information; the date grouping only needs wall-clock dates.
        segments_with_power["period_key"] = (
            segments_with_power["startDate"].dt.tz_localize(None).dt.to_period(period)
        )

        results: list[dict[str, object]] = []
        for period_key, group in segments_with_power.groupby("period_key", sort=True):
            short_group = group[group["distance"] == short_distance]
            long_group = group[group["distance"] == long_distance]

            if short_group.empty or long_group.empty:
                continue

            avg_time_short = float(short_group["duration_s"].mean())
            avg_time_long = float(long_group["duration_s"].mean())
            avg_power_short = float(short_group[_RUNNING_POWER_COL].mean())
            avg_power_long = float(long_group[_RUNNING_POWER_COL].mean())

            time_diff = avg_time_long - avg_time_short
            if time_diff <= 0:
                continue

            work_short = avg_power_short * avg_time_short
            work_long = avg_power_long * avg_time_long
            cp = (work_long - work_short) / time_diff
            w_prime = work_short - cp * avg_time_short

            if cp <= 0 or w_prime <= 0:
                continue

            results.append(
                {
                    "period": str(period_key),
                    "critical_power_w": round(cp, 1),
                    "w_prime_kj": round(w_prime / 1000, 2),
                }
            )

        if not results:
            return _empty

        return pd.DataFrame(results)
