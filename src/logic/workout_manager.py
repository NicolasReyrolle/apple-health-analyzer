"""Module to manage workout data and metrics."""

import json
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping, Optional, Union

import pandas as pd


class WorkoutManager:
    """Class to manage workout data and metrics."""

    # Columns to exclude from exports by default
    DEFAULT_EXCLUDED_COLUMNS = {"routeFile", "route"}
    # Date format for string representations
    DATE_FORMAT = "%Y/%m/%d"

    def __init__(self, pd_workouts: Optional[pd.DataFrame] = None) -> None:
        if pd_workouts is None:
            self.workouts: pd.DataFrame = pd.DataFrame(
                columns=[
                    "activityType",
                    "startDate",
                    "endDate",
                    "duration",
                    "durationUnit",
                    "distance",
                ]
            )
        else:
            self.workouts = pd_workouts

    def get_activity_types(self) -> List[str]:
        """Return the list of unique activity types."""
        if self.workouts.empty or "activityType" not in self.workouts.columns:
            return []
        return self.workouts["activityType"].dropna().unique().tolist()

    def _filter_workouts(
        self,
        activity_type: str = "All",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> pd.DataFrame:
        """Filter workouts by activity type and/or date range.

        Args:
            activity_type: Filter by activity type. "All" returns all activities.
            start_date: Include workouts from this date onwards (inclusive).
            end_date: Include workouts up to this date (inclusive).

        Returns:
            Filtered DataFrame of workouts.
        """
        workouts = self.workouts

        # Filter by activity type
        if activity_type != "All":
            workouts = workouts[workouts["activityType"] == activity_type]

        # Filter by date range
        if "startDate" in workouts.columns:
            if start_date is not None:
                workouts = workouts[workouts["startDate"] >= pd.Timestamp(start_date)]
            if end_date is not None:
                end_timestamp = pd.Timestamp(end_date)
                if self._is_date_only(end_date):
                    next_day = end_timestamp + pd.Timedelta(days=1)
                    workouts = workouts[workouts["startDate"] < next_day]
                else:
                    workouts = workouts[workouts["startDate"] <= end_timestamp]

        return workouts

    @staticmethod
    def _is_date_only(value: Union[datetime, pd.Timestamp]) -> bool:
        """Return True when the value represents a date without time-of-day information."""
        timestamp = pd.Timestamp(value)
        return timestamp == timestamp.normalize()

    def _get_filtered_columns(self, exclude_columns: Optional[set[str]] = None) -> List[str]:
        """Return list of columns after applying exclusion filters."""
        excluded = exclude_columns if exclude_columns is not None else self.DEFAULT_EXCLUDED_COLUMNS
        return [col for col in self.workouts.columns if col not in excluded]

    def _get_distance_divisor(self, unit: str) -> float:
        """Get the divisor for distance conversion based on unit."""
        if unit == "km":
            return 1000
        elif unit == "m":
            return 1
        elif unit == "mi":
            return 1609.34
        else:
            raise ValueError(f"Unsupported unit: {unit}")

    def _get_aggregate_total(
        self,
        activity_type: str,
        column: str,
        divisor: float = 1.0,
        default: int = 0,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        """Generic method to calculate total for any column with optional unit conversion.

        Args:
            activity_type: Filter by activity type ("All" for all)
            column: Column name to aggregate
            divisor: Divide the sum by this value (for unit conversion)
            default: Value to return if column doesn't exist
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Rounded total in the specified unit
        """
        workouts = self._filter_workouts(activity_type, start_date, end_date)
        if column not in workouts.columns:
            return default
        total = workouts[column].sum() / divisor
        return int(round(total))

    def _aggregate_by_activity(
        self,
        column: str,
        aggregation: Callable[[Any], pd.Series],
        transformation: Callable[[pd.Series], pd.Series],
        column_check: Optional[str] = None,
        filter_zeros: bool = True,
        combination_threshold: float = 10.0,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Generic method to aggregate metrics by activity type.

        Args:
            column: Column name to aggregate
            aggregation: Function to apply for aggregating (e.g., lambda x: x.sum())
            transformation: Function to apply to the aggregated series (e.g., .div(3600))
            column_check: Additional column to check exists (defaults to column)
            filter_zeros: Whether to filter out zero values
            combination_threshold: Threshold for grouping small values
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping activity types to aggregated values
        """
        column_check = column_check or column
        if "activityType" not in self.workouts.columns or column_check not in self.workouts.columns:
            return {}

        # Apply date filtering
        workouts = self._filter_workouts("All", start_date, end_date)

        grouped = aggregation(
            workouts.groupby("activityType")[column]  # type: ignore[reportUnknownMemberType]
        )
        if grouped.empty:
            return {}

        # Apply transformation
        transformed = transformation(grouped)
        result_float: Dict[str, float] = transformed.astype(
            float
        ).to_dict()  # type: ignore[reportUnknownMemberType]

        # Apply grouping if threshold > 0
        if combination_threshold > 0:
            result_float = self.group_small_values(
                result_float, threshold_percent=combination_threshold
            )

        # Round to integers
        result: Dict[str, int] = {k: int(round(v)) for k, v in result_float.items()}

        # Filter zero values if needed
        if filter_zeros:
            result = {k: v for k, v in result.items() if v > 0}

        return result

    def _aggregate_by_period(
        self,
        column: str,
        period: str,
        aggregation: Callable[[Any], Any],
        transformation: Callable[[pd.Series], pd.Series],
        column_check: Optional[str] = None,
        filter_zeros: bool = True,
        activity_type: str = "All",
        fill_missing_periods: bool = True,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Generic method to aggregate metrics by period.

        Args:
            column: Column name to aggregate.
            period: Period to group by (e.g., 'Y' for year, 'M' for month, 'W' for week).
            aggregation: Function to apply for aggregating.
            transformation: Function to apply to the aggregated series.
            column_check: Additional column to check exists (defaults to column).
            filter_zeros: Whether to filter out zero values.
            activity_type: Type of activity to filter by.
            fill_missing_periods: Whether to fill missing periods with zero values.
            start_date: Include workouts from this date onwards (inclusive).
            end_date: Include workouts up to this date (inclusive).

        Returns:
            Dictionary mapping periods to aggregated values.
        """
        column_check = column_check or column
        if (
            "activityType" not in self.workouts.columns
            or column_check not in self.workouts.columns
            or "startDate" not in self.workouts.columns
        ):
            return {}

        # Validate that startDate is datetime-like
        if not pd.api.types.is_datetime64_any_dtype(self.workouts["startDate"]):
            return {}

        workouts = self._filter_workouts(activity_type, start_date, end_date)

        # If there is no data after filtering, return empty dict as
        # dt.to_period would fail
        if workouts.empty:
            return {}

        grouped = aggregation(
            workouts.groupby(  # type: ignore[reportUnknownMemberType]
                workouts["startDate"].dt.to_period(period)  # type: ignore[reportUnknownMemberType]
            )[column]
        )

        # If aggregation returned an empty Series, there is nothing to aggregate
        # into periods; avoid calling grouped.index.min()/max() on an empty index.
        if grouped.empty:
            return {}
        # Add missing periods with zero values if needed
        if fill_missing_periods:
            full_range = pd.period_range(
                start=grouped.index.min(),
                end=grouped.index.max(),
                freq=period,
            )
            grouped = grouped.reindex(
                full_range, fill_value=0
            )  # type: ignore[reportUnknownMemberType]

        # Apply transformation
        transformed = transformation(grouped)
        result_float: Dict[str, float] = transformed.astype(
            float
        ).to_dict()  # type: ignore[reportUnknownMemberType]

        # Convert period to str and round to integers
        result: Dict[str, int] = {str(k): int(round(v)) for k, v in result_float.items()}

        # Filter zero values if needed, only if we didn't already filled missing periods with zeros
        if filter_zeros and not fill_missing_periods:
            result = {k: v for k, v in result.items() if v > 0}

        return result

    def get_count(
        self,
        activity_type: str = "All",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        """Return the number of workouts.

        Args:
            activity_type: Filter by activity type ("All" for all activities)
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Number of workouts matching the filters
        """
        return len(self._filter_workouts(activity_type, start_date, end_date))

    def get_total_distance(
        self,
        activity_type: str = "All",
        unit: str = "km",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        """Return the total distance optionally per activity_type, and in the given unit.

        Args:
            activity_type: Filter by activity type ("All" for all activities)
            unit: Unit for distance ("km", "m", or "mi"). Defaults to "km".
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Total distance in the specified unit
        """
        divisor = self._get_distance_divisor(unit)
        return self._get_aggregate_total(
            activity_type, "distance", divisor=divisor, start_date=start_date, end_date=end_date
        )

    def convert_distance(self, unit: str, total_distance_meters: float) -> float:
        """Convert distance in meters to the specified unit."""
        divisor = self._get_distance_divisor(unit)
        return total_distance_meters / divisor

    def get_total_duration(
        self,
        activity_type: str = "All",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        """Return the total duration of workouts in hours rounded to the nearest integer.

        Args:
            activity_type: Filter by activity type ("All" for all activities)
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Total duration in hours
        """
        return self._get_aggregate_total(
            activity_type, "duration", divisor=3600, start_date=start_date, end_date=end_date
        )

    def get_total_elevation(
        self,
        activity_type: str = "All",
        unit: str = "km",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        """Return the total elevation gain of workouts in the specified unit.

        Args:
            activity_type: Filter by activity type ("All" for all activities)
            unit: Unit for elevation ("km", "m", or "mi"). Defaults to "km".
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Total elevation in the specified unit
        """
        divisor = self._get_distance_divisor(unit)
        return self._get_aggregate_total(
            activity_type,
            "ElevationAscended",
            divisor=divisor,
            start_date=start_date,
            end_date=end_date,
        )

    def get_total_calories(
        self,
        activity_type: str = "All",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> int:
        """Return the total calories burned of workouts.

        Args:
            activity_type: Filter by activity type ("All" for all activities)
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Total calories burned
        """
        return self._get_aggregate_total(
            activity_type, "sumActiveEnergyBurned", start_date=start_date, end_date=end_date
        )

    def get_calories_by_activity(
        self,
        combination_threshold: float = 10.0,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping activity types to total calories burned.

        Activities that represent less than the combination_threshold percentage of total calories
        are grouped into an "Others" category.

        Args:
            combination_threshold: Percentage threshold for grouping small values
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping activity types to total calories
        """
        return self._aggregate_by_activity(
            "sumActiveEnergyBurned",
            lambda x: x.sum(),
            lambda x: x,
            combination_threshold=combination_threshold,
            start_date=start_date,
            end_date=end_date,
        )

    def get_calories_by_period(
        self,
        period: str,
        activity_type: str = "All",
        fill_missing_periods: bool = True,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping periods to total calories burned.

        Args:
            period: The period over which to aggregate calories. Typical values include
                "D" for day, "W" for week, "M" for month, and "Y" for year. The value is
                passed to the internal aggregation logic and should follow the expected
                period codes used there.
            activity_type: Filter by activity type ("All" for all activities). Defaults
                to "All".
            fill_missing_periods: If True, include periods with zero calories in the
                result. If False, only periods with recorded workouts are returned.
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            A dictionary mapping period labels (as strings) to total calories burned
            in each period.
        """
        return self._aggregate_by_period(
            "sumActiveEnergyBurned",
            period,
            lambda x: x.sum(),
            lambda x: x,
            activity_type=activity_type,
            fill_missing_periods=fill_missing_periods,
            start_date=start_date,
            end_date=end_date,
        )

    def get_distance_by_activity(
        self,
        unit: str = "km",
        combination_threshold: float = 10.0,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping activity types to total distance.

        Activities that represent less than the combination_threshold percentage of total distance
        are grouped into an "Others" category.

        Args:
            unit: Unit for distance ("km", "m", or "mi"). Defaults to "km".
            combination_threshold: Percentage threshold for grouping small values
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping activity types to total distance
        """
        return self._aggregate_by_activity(
            "distance",
            lambda x: x.sum(),
            lambda x: x.div(self._get_distance_divisor(unit)),
            combination_threshold=combination_threshold,
            start_date=start_date,
            end_date=end_date,
        )

    def get_distance_by_period(
        self,
        period: str,
        activity_type: str = "All",
        unit: str = "km",
        fill_missing_periods: bool = True,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping periods to total distance.

        Args:
            period: Period to group by (e.g., 'Y' for year, 'M' for month, 'W' for week)
            activity_type: Filter by activity type ("All" for all activities)
            unit: Unit for distance ("km", "m", or "mi"). Defaults to "km".
            fill_missing_periods: Whether to fill missing periods with zero values
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping periods to total distance
        """
        return self._aggregate_by_period(
            "distance",
            period,
            lambda x: x.sum(),
            lambda x: x.div(self._get_distance_divisor(unit)),
            filter_zeros=False,
            activity_type=activity_type,
            fill_missing_periods=fill_missing_periods,
            start_date=start_date,
            end_date=end_date,
        )

    def get_count_by_activity(
        self,
        combination_threshold: float = 10.0,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping activity types to workout counts.

        Activities that represent less than the combination_threshold percentage of total count
        are grouped into an "Others" category.

        Args:
            combination_threshold: Percentage threshold for grouping small values
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping activity types to workout counts
        """
        return self._aggregate_by_activity(
            "activityType",
            lambda x: x.count(),
            lambda x: x,
            column_check="activityType",
            combination_threshold=combination_threshold,
            start_date=start_date,
            end_date=end_date,
        )

    def get_count_by_period(
        self,
        period: str,
        activity_type: str = "All",
        fill_missing_periods: bool = True,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping periods to workout counts.

        Args:
            period: Period to group by (e.g., 'Y' for year, 'M' for month, 'W' for week)
            activity_type: Filter by activity type ("All" for all activities)
            fill_missing_periods: Whether to fill missing periods with zero values
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping periods to workout counts
        """
        return self._aggregate_by_period(
            "activityType",
            period,
            lambda x: x.count(),
            lambda x: x,
            column_check="activityType",
            activity_type=activity_type,
            fill_missing_periods=fill_missing_periods,
            start_date=start_date,
            end_date=end_date,
        )

    def get_duration_by_activity(
        self,
        combination_threshold: float = 10.0,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping activity types to total duration.

        Activities that represent less than the combination_threshold percentage of total duration
        are grouped into an "Others" category.

        Args:
            combination_threshold: Percentage threshold for grouping small values
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping activity types to total duration in hours
        """
        return self._aggregate_by_activity(
            "duration",
            lambda x: x.sum(),
            lambda x: x.div(3600),
            combination_threshold=combination_threshold,
            start_date=start_date,
            end_date=end_date,
        )

    def get_duration_by_period(
        self,
        period: str,
        activity_type: str = "All",
        fill_missing_periods: bool = True,
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping periods to total duration in hours.

        Args:
            period: Period to group by (e.g., 'Y' for year, 'M' for month, 'W' for week)
            activity_type: Filter by activity type ("All" for all activities)
            fill_missing_periods: Whether to fill missing periods with zero values
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping periods to total duration in hours
        """
        return self._aggregate_by_period(
            "duration",
            period,
            lambda x: x.sum(),
            lambda x: x.div(3600),
            activity_type=activity_type,
            fill_missing_periods=fill_missing_periods,
            start_date=start_date,
            end_date=end_date,
        )

    def get_elevation_by_activity(
        self,
        combination_threshold: float = 10.0,
        unit: str = "m",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping activity types to total elevation gain.

        Activities that represent less than the combination_threshold percentage of total elevation
        are grouped into an "Others" category.

        Args:
            combination_threshold: Percentage threshold for grouping small values
            unit: Unit for elevation ("km", "m", or "mi"). Defaults to "m".
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping activity types to total elevation
        """
        return self._aggregate_by_activity(
            "ElevationAscended",
            lambda x: x.sum(),
            lambda x: x.div(self._get_distance_divisor(unit)),
            filter_zeros=False,
            combination_threshold=combination_threshold,
            start_date=start_date,
            end_date=end_date,
        )

    def get_elevation_by_period(
        self,
        period: str,
        activity_type: str = "All",
        fill_missing_periods: bool = True,
        unit: str = "m",
        start_date: Optional[Union[datetime, pd.Timestamp]] = None,
        end_date: Optional[Union[datetime, pd.Timestamp]] = None,
    ) -> Dict[str, int]:
        """Return a dictionary mapping periods to total elevation gain in the specified unit.

        Args:
            period: Period to group by (e.g., 'Y' for year, 'M' for month, 'W' for week)
            activity_type: Filter by activity type ("All" for all activities)
            fill_missing_periods: Whether to fill missing periods with zero values
            unit: Unit for elevation ("km", "m", or "mi"). Defaults to "m".
            start_date: Include workouts from this date onwards (inclusive)
            end_date: Include workouts up to this date (inclusive)

        Returns:
            Dictionary mapping periods to total elevation in the specified unit
        """
        return self._aggregate_by_period(
            "ElevationAscended",
            period,
            lambda x: x.sum(),
            lambda x: x.div(self._get_distance_divisor(unit)),
            filter_zeros=False,
            activity_type=activity_type,
            fill_missing_periods=fill_missing_periods,
            start_date=start_date,
            end_date=end_date,
        )

    def group_small_values(
        self,
        data: Mapping[str, float],
        threshold_percent: float = 10.0,
        others_label: str = "Others",
    ) -> Dict[str, float]:
        """Group smallest values whose cumulative sum is below threshold into a single category.

        Accumulates the smallest values until their cumulative sum would exceed the threshold
        percentage of the total, and combines them into a single category (default: "Others").

        Args:
            data: Dictionary mapping keys to numeric values
            threshold_percent: Percentage threshold (0-100) below which smallest values
                are accumulated and grouped. Defaults to 10.0.
            others_label: Label for the grouped small values. Defaults to "Others".

        Returns:
            Dictionary with small values grouped under the others_label.

        Example:
            >>> data = {"A": 100, "B": 50, "C": 5, "D": 3}
            >>> manager.group_small_values(data, threshold_percent=10.0)
            {"A": 100, "B": 50, "Others": 8}  # C(5) + D(3) cumulative sum = 8 < 10% of 158
        """
        if not data:
            return {}

        # Calculate total
        total = sum(data.values())

        if total == 0:
            return dict(data)

        # Calculate threshold value
        threshold_value = total * (threshold_percent / 100.0)

        # Sort items by value (smallest first)
        sorted_items = sorted(data.items(), key=lambda x: x[1])

        # Accumulate smallest values while cumulative sum <= threshold
        result: Dict[str, float] = {}
        others_sum = 0.0
        cumulative_sum = 0.0

        for key, value in sorted_items:
            if cumulative_sum + value <= threshold_value:
                # This value can be added to "Others"
                others_sum += value
                cumulative_sum += value
            else:
                # This and all remaining values are large enough to stay separate
                result[key] = value

        # Add "Others" category if there are small values
        if others_sum > 0:
            result[others_label] = others_sum

        return result

    def get_workouts(self) -> pd.DataFrame:
        """Return the DataFrame of workouts."""
        return self.workouts

    def get_statistics(self) -> str:
        """Return global statistics of the loaded data as a formatted string."""
        if not self.workouts.empty:
            result = f"Total workouts: {len(self.workouts)}\n"
            if "distance" in self.workouts.columns:
                result += f"Total distance of {self.get_total_distance()} km.\n"
            if "duration" in self.workouts.columns:
                total_duration_sec = self.workouts["duration"].sum()
                hours, remainder = divmod(total_duration_sec, 3600)
                minutes, seconds = divmod(remainder, 60)
                result += f"Total duration of {int(hours)}h {int(minutes)}m {int(seconds)}s.\n"
        else:
            result = "No workout loaded."

        return result

    def export_to_json(self, exclude_columns: Optional[set[str]] = None) -> str:
        """Export to JSON: Schema first, specific column order, no nulls. Return JSON string.

        Args:
            exclude_columns: Set of column names to exclude. If None, uses DEFAULT_EXCLUDED_COLUMNS.
        """
        cols_to_keep = self._get_filtered_columns(exclude_columns)
        df_filtered = self.workouts[cols_to_keep]

        # 1. Get the raw JSON string
        json_str = df_filtered.to_json(orient="table")  # type: ignore[misc]
        raw_obj = json.loads(json_str)

        # Define the fixed order for specific columns
        # index=0, startDate=1, endDate=2, everything else=3
        column_priority = {"index": 0, "startDate": 1, "endDate": 2}

        # 2. Process 'data'
        cleaned_data: List[Dict[str, Any]] = []
        for row in raw_obj.get("data", []):
            # A. Filter nulls
            valid_items = {k: v for k, v in row.items() if v is not None}

            # B. Sort keys using the priority map
            # If 'k' is not in the map, it gets priority 3.
            # Secondary sort key is k.lower() (alphabetical)
            sorted_keys = sorted(
                valid_items.keys(), key=lambda k: (column_priority.get(k, 3), k.lower())
            )

            # C. Rebuild dict with sorted keys
            cleaned_data.append({k: valid_items[k] for k in sorted_keys})

        # 3. Sort the records (rows) by 'startDate'
        cleaned_data.sort(key=lambda x: x.get("startDate", ""))

        # 4. Construct final dict ensuring 'schema' is added first
        final_obj: Dict[str, Any] = {
            "schema": raw_obj.get("schema"),
            "data": cleaned_data,
        }

        # 5. Return the JSON string
        return json.dumps(final_obj, indent=2)

    def export_to_csv(
        self, activity_type: str = "All", exclude_columns: Optional[set[str]] = None
    ) -> str:
        """Export workouts to a CSV format, returns the CSV string.

        Args:
            activity_type: Filter by activity type. "All" returns all activities.
            exclude_columns: Set of column names to exclude. If None, uses DEFAULT_EXCLUDED_COLUMNS.
        """
        cols_to_keep = self._get_filtered_columns(exclude_columns)
        filtered_workouts = self._filter_workouts(activity_type)

        result: str = ""

        # If DataFrame is empty, create one with expected columns
        if filtered_workouts.empty:
            expected_columns = [
                "activityType",
                "duration",
                "durationUnit",
                "startDate",
                "endDate",
                "source",
            ]
            excluded = (
                exclude_columns if exclude_columns is not None else self.DEFAULT_EXCLUDED_COLUMNS
            )
            cols_to_keep = [col for col in expected_columns if col not in excluded]
            empty_df = pd.DataFrame(columns=cols_to_keep)
            result = empty_df.to_csv(index=False)
        else:
            result = filtered_workouts[cols_to_keep].to_csv(index=False)

        return result

    def get_date_bounds(self) -> tuple[str, str]:
        """Return the minimum and maximum start dates of the workouts as
        strings in "YYYY/MM/DD" format."""
        if self.workouts.empty or "startDate" not in self.workouts.columns:
            # Default bounds if no file is loaded
            return "2000/01/01", datetime.now().strftime(self.DATE_FORMAT)

        # Extract all start dates
        start_dates = [w.startDate for w in self.workouts.itertuples()]

        return (
            min(start_dates).strftime(self.DATE_FORMAT),  # type: ignore[arg-type,union-attr]
            max(start_dates).strftime(self.DATE_FORMAT),  # type: ignore[arg-type,union-attr]
        )
