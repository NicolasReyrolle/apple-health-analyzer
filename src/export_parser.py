"""Export processor for Apple Health data."""

from datetime import datetime
import json
import sys
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple, Type, TypedDict
from xml.etree.ElementTree import Element, iterparse
from zipfile import ZipFile

import pandas as pd


class WorkoutRecordRequired(TypedDict):
    """Required fields for workout record."""

    activityType: str


class WorkoutRecord(WorkoutRecordRequired, total=False):
    """Type definition for workout record structure."""

    duration: Optional[float]
    startDate: Optional[str]
    endDate: Optional[str]
    source: Optional[str]
    routeFile: Optional[str]
    route: Optional[pd.DataFrame]


class WorkoutRoute(TypedDict):
    """Type definition for workout route structure."""

    time: datetime
    latitude: float
    longitude: float
    altitude: float


class ExportParser:
    """Reads and parses Apple Health export files."""

    # Columns to exclude from exports by default
    DEFAULT_EXCLUDED_COLUMNS = {"routeFile", "route"}

    def __init__(self, export_file: str):
        self.export_file = export_file
        self.running_workouts: pd.DataFrame = pd.DataFrame(
            columns=["startDate", "endDate", "duration", "durationUnit"]
        )

    def __enter__(self) -> "ExportParser":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        # Nothing to do for now
        pass

    @staticmethod
    def _parse_value(raw_value: Optional[str]) -> Tuple[Any, Optional[str]]:
        """
        Internal helper: Separates value and unit, converts to standard metric system.

        Specific rules:
        - Number without unit (0 or 1) -> Boolean (False/True)
        - Number without unit (other) -> Float
        - String (not a number) -> String
        - "Value Unit" -> Converted Float + Unit

        Returns: (value, unit) or (None, None)
        """
        # Check if value is empty or None
        if not raw_value:
            return None, None

        # CASE A: No unit detected (No space)
        if " " not in raw_value:
            try:
                val = float(raw_value)

                # Logic for Booleans (0 or 1 without unit)
                # We compare with 0 and 1. Note that 0.0 == 0 is True in Python.
                if val == 0:
                    return False, None
                if val == 1:
                    return True, None

                # Other numbers (e.g. "10", "42.5")
                return val, None

            except ValueError:
                # It is not a number, so it is a string (e.g. "Europe/Luxembourg")
                return raw_value, None

        # CASE B: Value with Unit (contains space)
        parts = raw_value.split(" ")

        # Handle cases like "String with spaces" that are not numbers
        # We try to parse the first part as a number. If it fails, treat whole string as text.
        try:
            val = float(parts[0])
        except ValueError:
            return raw_value, None

        unit = parts[1]

        # --- Unit Conversion Logic ---
        if unit == "cm":
            val = val / 100.0
            unit = "m"

        elif unit == "%":
            val = val / 100.0
            unit = "%"

        elif unit == "degF":
            val = (val - 32) * 5.0 / 9.0
            unit = "degC"

        return val, unit

    def _load_workouts(self, zipfile: ZipFile, workout_type: str) -> None:
        """Load workouts of a specific type from the export file."""
        print(f"Loading the {workout_type} workouts...")

        with zipfile.open("apple_health_export/export.xml") as export_file:
            rows: List[WorkoutRecord] = []

            for event, elem in iterparse(export_file, events=("start", "end")):
                if event == "end" and elem.tag == "Workout":
                    activity_type = self._extract_activity_type(elem)

                    if activity_type == workout_type:
                        record = self._create_workout_record(elem, activity_type)
                        self._process_workout_children(elem, record, zipfile)
                        rows.append(record)

                    elem.clear()

            self.running_workouts = pd.DataFrame(rows)
            print(f"Loaded {len(self.running_workouts)} running workouts.")

    def _extract_activity_type(self, elem: Element) -> str:
        """Extract and clean activity type from workout element."""
        activity_type_raw = elem.get("workoutActivityType", "")
        return activity_type_raw.replace("HKWorkoutActivityType", "")

    def _create_workout_record(
        self, elem: Element, activity_type: str
    ) -> WorkoutRecord:
        """Create base workout record from element attributes."""
        duration_str = elem.get("duration")
        return {
            "activityType": activity_type,
            "duration": float(duration_str) if duration_str else None,
            "startDate": elem.get("startDate"),
            "endDate": elem.get("endDate"),
            "source": elem.get("sourceName"),
        }

    def _process_workout_children(
        self, elem: Element, record: WorkoutRecord, zipfile: ZipFile
    ) -> None:
        """Process child elements of workout (statistics and metadata)."""
        for child in elem:
            if child.tag == "WorkoutStatistics":
                self._process_workout_statistics(child, record)
            elif child.tag == "MetadataEntry":
                self._process_metadata_entry(child, record)
            elif child.tag == "WorkoutActivity":
                self._process_workout_children(child, record, zipfile)
            elif child.tag == "WorkoutRoute":
                self._process_workout_route(child, record, zipfile)

    def _process_workout_statistics(
        self, child: Element, record: WorkoutRecord
    ) -> None:
        """Process workout statistics child element."""
        stat_type = child.get("type", "").replace("HKQuantityTypeIdentifier", "")

        for stat_attr in ["sum", "average", "minimum", "maximum"]:
            if child.get(stat_attr):
                stat_attr_str = child.get(stat_attr) or "0"
                record[f"{stat_attr}{stat_type}"] = float(stat_attr_str)
                record[f"{stat_attr}{stat_type}Unit"] = child.get("unit")

    def _load_route(self, zipfile: ZipFile, route_path: str) -> Optional[pd.DataFrame]:
        """Load GPX route file from the export zip."""
        try:
            with zipfile.open(f"apple_health_export{route_path}") as route_file:
                rows: List[WorkoutRoute] = []
                for event, elem in iterparse(route_file, events=("start", "end")):
                    if (
                        event == "end"
                        and elem.tag == "{http://www.topografix.com/GPX/1/1}trkpt"
                    ):
                        latitude: str = elem.get("lat") or "0.0"
                        longitude: str = elem.get("lon") or "0.0"

                        # Extract child elements (ele and time are not attributes)
                        ele_elem = elem.find("{http://www.topografix.com/GPX/1/1}ele")
                        time_elem = elem.find("{http://www.topografix.com/GPX/1/1}time")

                        altitude: str = (
                            ele_elem.text or "0.0" if ele_elem is not None else "0.0"
                        )
                        time_str: str = (
                            time_elem.text or "" if time_elem is not None else ""
                        )

                        rows.append(
                            {
                                "time": datetime.fromisoformat(
                                    time_str.replace("Z", "+00:00")
                                ),
                                "latitude": float(latitude),
                                "longitude": float(longitude),
                                "altitude": float(altitude),
                            }
                        )
                        elem.clear()
                return pd.DataFrame(rows)
        except KeyError:
            print(f"Route file not found in export: {route_path}")
            return None

    def _process_workout_route(
        self, elem: Element, record: WorkoutRecord, zipfile: ZipFile
    ) -> None:
        """Process workout route child element."""
        for child in elem:
            if child.tag == "FileReference":
                record["routeFile"] = child.get("path")
                record["route"] = self._load_route(zipfile, child.get("path") or "")

    def _process_metadata_entry(self, child: Element, record: WorkoutRecord) -> None:
        """Process metadata entry child element."""
        key = child.get("key", "").replace("HK", "")

        # Skip keys that have no meaning for analysis
        if key == "WOIntervalStepKeyPath":
            return

        value, unit = self._parse_value(child.get("value", ""))

        # If the key already exists and both current and new values are numeric, sum them
        if (
            key in record
            and isinstance(record[key], (int, float))
            and isinstance(value, (int, float))
        ):
            record[key] = record[key] + value
        else:
            record[key] = value
            if unit:
                record[f"{key}Unit"] = unit

    def parse(self) -> None:
        """Parse the export file."""
        try:
            with ZipFile(self.export_file, "r") as zipfile:
                self._load_workouts(zipfile, "Running")

        except FileNotFoundError:
            print(f"Apple Health Export file not found: {self.export_file}")
            sys.exit(1)

    def export_to_json(
        self, output_file: str, exclude_columns: Optional[set[str]] = None
    ) -> None:
        """Export to JSON: Schema first, specific column order, no nulls.

        Args:
            output_file: Output file path.
            exclude_columns: Set of column names to exclude. If None, uses DEFAULT_EXCLUDED_COLUMNS.
        """
        # Filter columns to exclude (default: routeFile and route)
        excluded: set[str] = (
            exclude_columns
            if exclude_columns is not None
            else self.DEFAULT_EXCLUDED_COLUMNS
        )
        cols_to_keep = [
            col for col in self.running_workouts.columns if col not in excluded
        ]
        df_filtered = self.running_workouts[cols_to_keep]

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

        # 5. Write to file
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(final_obj, f, indent=2)

        print(f"Exported running workouts to {output_file}")

    def export_to_csv(
        self, output_file: str, exclude_columns: Optional[set[str]] = None
    ) -> None:
        """Export running workouts to a CSV file.

        Args:
            output_file: Output file path.
            exclude_columns: Set of column names to exclude. If None, uses DEFAULT_EXCLUDED_COLUMNS.
        """
        # Filter columns to exclude (default: routeFile and route)
        excluded: set[str] = (
            exclude_columns
            if exclude_columns is not None
            else self.DEFAULT_EXCLUDED_COLUMNS
        )
        cols_to_keep = [
            col for col in self.running_workouts.columns if col not in excluded
        ]
        self.running_workouts[cols_to_keep].to_csv(output_file, index=False)
