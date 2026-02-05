"""Module to manage workout data and metrics."""

import json
from typing import Any, Dict, List, Optional

import pandas as pd


class WorkoutManager:
    """Class to manage workout data and metrics."""

    # Columns to exclude from exports by default
    DEFAULT_EXCLUDED_COLUMNS = {"routeFile", "route"}

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
                    "distanceUnit",
                ]
            )
        else:
            self.workouts = pd_workouts

    def get_activity_types(self) -> List[str]:
        """Return the list of unique activity types."""
        if self.workouts.empty or "activityType" not in self.workouts.columns:
            return []
        return self.workouts["activityType"].dropna().unique().tolist()

    def count(self, activity_type: str = "All") -> int:
        """Return the number of workouts."""
        if activity_type != "All":
            return len(self.workouts[self.workouts["activityType"] == activity_type])
        return len(self.workouts)

    def get_total_distance(self, activity_type: str = "All", unit: str = "km") -> int:
        """Return the total distance optionally per activity_type, and in the given unit

        Args:
            activity_type (str, optional): type of activity. Defaults to "All".
            unit (str, optional): unit in which to return the distance. Defaults to "km". Allowed: "km", "m", "mi".

        Returns:
            int: Total distance in the specified unit.
        """
        if activity_type != "All":
            workouts = self.workouts[self.workouts["activityType"] == activity_type]
        else:
            workouts = self.workouts

        if "distance" in workouts.columns:
            total_distance_meters = workouts["distance"].sum()
            if unit == "km":
                result = int(round(total_distance_meters / 1000))
            elif unit == "m":
                return total_distance_meters
            elif unit == "mi":
                return int(round(total_distance_meters / 1609.34))
            else:
                raise ValueError(f"Unsupported unit: {unit}")
        else:
            result = 0

        return result

    def get_total_duration(self, activity_type: str = "All") -> int:
        """Return the total duration of workouts in hours rounded to the nearest integer"""
        if activity_type != "All":
            workouts = self.workouts[self.workouts["activityType"] == activity_type]
        else:
            workouts = self.workouts

        if "duration" in workouts.columns:
            return int(round(workouts["duration"].sum() / 3600))

        return 0

    def get_total_elevation(self, activity_type: str = "All") -> int:
        """Return the total elevation gain of workouts in kilometers
        rounded to the nearest integer."""
        if activity_type != "All":
            workouts = self.workouts[self.workouts["activityType"] == activity_type]
        else:
            workouts = self.workouts

        if "ElevationAscended" in workouts.columns:
            return int(round(workouts["ElevationAscended"].sum() / 1000))

        return 0

    def get_workouts(self) -> pd.DataFrame:
        """Return the DataFrame of workouts."""
        return self.workouts

    def get_statistics(self) -> str:
        """Return global statistics of the loaded data as a formatted string."""
        if not self.workouts.empty:
            result = f"Total workouts: {len(self.workouts)}\n"
            if "distance" in self.workouts.columns:
                result += f"Total distance of " f"{self.get_total_distance()} km.\n"
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
        # Filter columns to exclude (default: routeFile and route)
        excluded: set[str] = (
            exclude_columns if exclude_columns is not None else self.DEFAULT_EXCLUDED_COLUMNS
        )
        cols_to_keep = [col for col in self.workouts.columns if col not in excluded]
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
        # Filter columns to exclude (default: routeFile and route)
        excluded: set[str] = (
            exclude_columns if exclude_columns is not None else self.DEFAULT_EXCLUDED_COLUMNS
        )

        # Filter workouts by activity type
        if activity_type != "All":
            filtered_workouts = self.workouts[self.workouts["activityType"] == activity_type]
        else:
            filtered_workouts = self.workouts

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
            cols_to_keep = [col for col in expected_columns if col not in excluded]
            empty_df = pd.DataFrame(columns=cols_to_keep)
            result = empty_df.to_csv(index=False)
        else:
            cols_to_keep = [col for col in filtered_workouts.columns if col not in excluded]
            result = filtered_workouts[cols_to_keep].to_csv(index=False)

        return result
