"""Best-segment mixin for WorkoutManager."""

from datetime import datetime
from typing import TYPE_CHECKING, Any, Callable, List, Optional, TypedDict, Union

import pandas as pd

from logic.workout_route import WorkoutRoute

if TYPE_CHECKING:
    from pandas import Timestamp

# Fallback tolerance: workout-level average power is only used as a fallback for
# the per-segment power when the workout duration is within this fraction of the
# segment duration (i.e. the whole workout ≈ the segment being analysed).
_WORKOUT_SEGMENT_DURATION_TOLERANCE = 0.10


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
        return pd.DataFrame(
            columns=["startDate", "distance", "duration_s", "segment_start", "segment_end"]
        )

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
        df = pd.DataFrame(
            results, columns=["startDate", "distance", "duration_s", "segment_start", "segment_end"]
        )
        df = df.sort_values(["distance", "duration_s"], ascending=[True, True])
        return df.groupby("distance").head(topn).reset_index(drop=True)

    @staticmethod
    def _get_fastest_segment_window(
        route_traces: list[WorkoutRoute],
        distance_m: float,
        distance_scale_factor: float,
    ) -> Optional[tuple[float, datetime, datetime]]:
        """Return (duration_s, start_time, end_time) for the fastest segment across traces."""
        best: Optional[tuple[float, datetime, datetime]] = None
        for route_trace in route_traces:
            result = route_trace.find_fastest_segment_window(
                distance_m,
                distance_scale_factor=distance_scale_factor,
            )
            if result is not None and (best is None or result[0] < best[0]):
                best = result
        return best

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

            window = self._get_fastest_segment_window(
                route_traces,
                float(distance),
                distance_scale_factor,
            )
            if window is None:
                continue

            duration_s, seg_start, seg_end = window
            rows.append([run_record.startDate, distance, duration_s, seg_start, seg_end])

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
            DataFrame with columns: startDate, distance, duration_s, segment_start, segment_end
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

    def annotate_segments_with_power(  # pylint: disable=too-many-locals
        self,
        segments: pd.DataFrame,
        running_power_df: Optional[pd.DataFrame],
    ) -> pd.DataFrame:
        """Add ``segment_avg_power`` column to a best-segments DataFrame.

        Power for each segment is determined with the following priority:

        1. **Individual records**: mean value of ``HKQuantityTypeIdentifierRunningPower``
           records whose ``startDate`` falls within ``[segment_start, segment_end]``.
        2. **Workout-level fallback**: ``averageRunningPower`` from the workout statistics
           is used *only* when the workout duration is within
           :data:`_WORKOUT_SEGMENT_DURATION_TOLERANCE` (10 %) of the segment duration,
           meaning the whole workout is essentially the segment being measured.
        3. ``None`` when neither source provides usable data.

        Args:
            segments: DataFrame returned by :meth:`get_best_segments` (must have
                ``startDate``, ``duration_s``, ``segment_start``, ``segment_end``).
            running_power_df: Optional DataFrame of individual ``RunningPower`` records
                with columns ``startDate`` (raw ISO-8601 string) and ``value`` (float W).

        Returns:
            Copy of *segments* with an additional ``segment_avg_power`` column
            (float Watts, or ``None``).
        """
        result = segments.copy()
        if segments.empty or "segment_start" not in segments.columns:
            result["segment_avg_power"] = None
            return result

        # Parse individual RunningPower record timestamps once for efficiency.
        # Apple Health timestamps include timezone offsets, so parse as tz-aware and
        # keep UTC normalisation from ISO8601 parser for consistent comparison with
        # GPS segment times (which are always stored as UTC).
        rp_times: Optional[pd.Series] = None
        rp_values: Optional[pd.Series] = None
        if (
            running_power_df is not None
            and not running_power_df.empty
            and "startDate" in running_power_df.columns
            and "value" in running_power_df.columns
        ):
            rp_times = pd.to_datetime(
                running_power_df["startDate"], format="ISO8601", errors="coerce"
            )
            rp_values = pd.to_numeric(running_power_df["value"], errors="coerce")

        # Build workout-level fallback lookup: startDate → (duration_s, avg_power_w).
        workout_fallback: dict[Any, tuple[float, Optional[float]]] = {}
        avg_power_col = "averageRunningPower"
        for w in self.workouts.itertuples():
            w_start = getattr(w, "startDate", None)
            w_dur = float(getattr(w, "duration", 0.0) or 0.0)
            raw_pwr = (
                getattr(w, avg_power_col, None) if avg_power_col in self.workouts.columns else None
            )
            w_pwr = float(raw_pwr) if raw_pwr is not None and not pd.isna(raw_pwr) else None
            workout_fallback[w_start] = (w_dur, w_pwr)

        avg_powers: list[Optional[float]] = []
        for row in segments.itertuples():
            seg_start = getattr(row, "segment_start", None)
            seg_end = getattr(row, "segment_end", None)
            seg_duration = float(getattr(row, "duration_s", 0.0))
            workout_start = getattr(row, "startDate", None)

            power: Optional[float] = None

            # 1. Individual RunningPower records within the GPS segment time window.
            if (
                rp_times is not None
                and rp_values is not None
                and seg_start is not None
                and seg_end is not None
            ):
                seg_start_ts = pd.Timestamp(seg_start)
                seg_end_ts = pd.Timestamp(seg_end)
                mask = (rp_times >= seg_start_ts) & (rp_times <= seg_end_ts) & rp_values.notna()
                vals = rp_values[mask]
                if not vals.empty:
                    power = float(vals.mean())

            # 2. Workout-level fallback when the workout ≈ the segment.
            if power is None and workout_start in workout_fallback:
                workout_dur, workout_avg_pwr = workout_fallback[workout_start]
                if (
                    workout_avg_pwr is not None
                    and workout_dur > 0
                    and abs(seg_duration - workout_dur) / workout_dur
                    <= _WORKOUT_SEGMENT_DURATION_TOLERANCE
                ):
                    power = workout_avg_pwr

            avg_powers.append(power)

        result["segment_avg_power"] = avg_powers
        return result

    def get_critical_power(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals,too-many-return-statements
        self,
        running_power_df: Optional[pd.DataFrame] = None,
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

        Per-segment average power is derived from individual ``RunningPower`` health
        records within the segment GPS time window (see :meth:`annotate_segments_with_power`).

        Args:
            running_power_df: DataFrame of individual ``HKQuantityTypeIdentifierRunningPower``
                records (columns ``startDate``, ``value``). Pass
                ``records_by_type.get("RunningPower")`` from the app state.
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

        segments = self.get_best_segments(
            topn=topn,
            distances=[short_distance, long_distance],
            start_date=start_date,
            end_date=end_date,
        )

        if segments.empty:
            return None

        segments = self.annotate_segments_with_power(segments, running_power_df)

        short_rows = segments[
            (segments["distance"] == short_distance) & segments["segment_avg_power"].notna()
        ]
        long_rows = segments[
            (segments["distance"] == long_distance) & segments["segment_avg_power"].notna()
        ]

        if short_rows.empty or long_rows.empty:
            return None

        avg_time_short = float(short_rows["duration_s"].mean())
        avg_time_long = float(long_rows["duration_s"].mean())
        avg_power_short = float(short_rows["segment_avg_power"].mean())
        avg_power_long = float(long_rows["segment_avg_power"].mean())

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
            count_short=len(short_rows),
            count_long=len(long_rows),
        )

    def get_critical_power_evolution(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
        self,
        running_power_df: Optional[pd.DataFrame] = None,
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
            running_power_df: DataFrame of individual ``HKQuantityTypeIdentifierRunningPower``
                records (columns ``startDate``, ``value``). Pass
                ``records_by_type.get("RunningPower")`` from the app state.
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

        segments = self.get_best_segments(
            topn=topn,
            distances=[short_distance, long_distance],
            start_date=start_date,
            end_date=end_date,
        )

        if segments.empty:
            return _empty

        segments = self.annotate_segments_with_power(segments, running_power_df)
        segments = segments[segments["segment_avg_power"].notna()].copy()

        if segments.empty:
            return _empty

        # Strip timezone before period conversion to avoid pandas UserWarning about
        # dropping tz information; the date grouping only needs wall-clock dates.
        segments["period_key"] = (
            segments["startDate"].dt.tz_localize(None).dt.to_period(period)
            if isinstance(segments["startDate"].dtype, pd.DatetimeTZDtype)
            else segments["startDate"].dt.to_period(period)
        )

        results: list[dict[str, object]] = []
        for period_key, group in segments.groupby("period_key", sort=True):
            short_group = group[group["distance"] == short_distance]
            long_group = group[group["distance"] == long_distance]

            if short_group.empty or long_group.empty:
                continue

            avg_time_short = float(short_group["duration_s"].mean())
            avg_time_long = float(long_group["duration_s"].mean())
            avg_power_short = float(short_group["segment_avg_power"].mean())
            avg_power_long = float(long_group["segment_avg_power"].mean())

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
