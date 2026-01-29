"""Export processor for Apple Health data."""

from datetime import datetime
import json
from types import TracebackType
from typing import Any, Dict, List, Optional, Tuple, Type, TypedDict
from xml.etree.ElementTree import Element, iterparse
from zipfile import ZipFile

from nicegui import ui
import pandas as pd


class WorkoutRecordRequired(TypedDict):
    """Required fields for workout record."""

    activityType: str


class WorkoutRecord(WorkoutRecordRequired, total=False):
    """Type definition for workout record structure."""

    duration: Optional[float]
    durationUnit: Optional[str]
    startDate: Optional[str]
    endDate: Optional[str]
    source: Optional[str]
    routeFile: Optional[str]
    route: Optional[pd.DataFrame]
    sumDistanceWalkingRunning: Optional[float]


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

    def __init__(self) -> None:
        self.log = None
        self.running_workouts: pd.DataFrame = pd.DataFrame(
            columns=[
                "startDate",
                "endDate",
                "duration",
                "durationUnit",
                "sumDistanceWalkingRunning",
            ]
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

    @staticmethod
    def _duration_to_seconds(value: float, unit: str = "min") -> int:
        if unit == "min" or unit == "":
            return int(value * 60)
        elif unit == "h":
            return int(value * 3600)
        elif unit == "s":
            return int(value)
        else:
            raise ValueError(f"Unknown duration unit: {unit}")

    def _log(self, message: str) -> None:
        """Log a message if logging is enabled."""
        if self.log:
            self.log.push(message)

    def _load_workouts(self, zipfile: ZipFile, workout_type: str) -> None:
        """Load workouts of a specific type from the export file."""
        if self.log:
            self._log(f"Loading the {workout_type} workouts...")

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
            if len(self.running_workouts) > 0:
                self.running_workouts["startDate"] = pd.to_datetime(
                    self.running_workouts["startDate"]
                ).dt.tz_localize(None)

    def get_statistics(self) -> str:
        """Print global statistics of the loaded data."""
        if not self.running_workouts.empty:
            result = f"Total running workouts: {len(self.running_workouts)}\n"
            if "sumDistanceWalkingRunning" in self.running_workouts.columns:
                result += (
                    f"Total distance of "
                    f"{self.running_workouts['sumDistanceWalkingRunning'].sum():.2f} km.\n"
                )
            if "duration" in self.running_workouts.columns:
                total_duration_sec = self.running_workouts["duration"].sum()
                hours, remainder = divmod(total_duration_sec, 3600)
                minutes, seconds = divmod(remainder, 60)
                result += f"Total duration of {int(hours)}h {int(minutes)}m {int(seconds)}s.\n"
        else:
            result = "No running workouts loaded."

        return result

    def _extract_activity_type(self, elem: Element) -> str:
        """Extract and clean activity type from workout element."""
        activity_type_raw = elem.get("workoutActivityType", "")
        return activity_type_raw.replace("HKWorkoutActivityType", "")

    def _create_workout_record(
        self, elem: Element, activity_type: str
    ) -> WorkoutRecord:
        """Create base workout record from element attributes."""
        duration_str = elem.get("duration")
        duration_unit_str: str = elem.get("durationUnit") or ""
        return {
            "activityType": activity_type,
            "duration": self._duration_to_seconds(
                float(duration_str), duration_unit_str
            )
            if duration_str
            else None,
            "durationUnit": "seconds",
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
            self._log(f"Route file not found in export: {route_path}")
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

        # If the key already exists and both current and new values are numeric (but not bool),
        # sum them
        # Note: bool is a subclass of int, so we must explicitly exclude it
        if (
            key in record
            and isinstance(record[key], (int, float))
            and not isinstance(record[key], bool)
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            record[key] = record[key] + value
        else:
            record[key] = value
            if unit:
                record[f"{key}Unit"] = unit

    def parse(self, export_file: str, log: Optional[ui.log] = None) -> None:
        """Parse the export file."""

        try:
            self.log = log
            self._log("Starting to parse the Apple Health export file...")
            with ZipFile(export_file, "r") as zipfile:
                self._load_workouts(zipfile, "Running")
            self._log("Finished parsing the Apple Health export file.")
        except Exception as e:
            self._log(f"Error during parsing: {e}")
            raise

    def export_to_json(self, exclude_columns: Optional[set[str]] = None) -> str:
        """Export to JSON: Schema first, specific column order, no nulls. Return JSON string.

        Args:
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

        # 5. Return the JSON string
        return json.dumps(final_obj, indent=2)

    def export_to_csv(self, exclude_columns: Optional[set[str]] = None) -> str:
        """Export running workouts to a CSV format, returns the CSV string.

        Args:
            exclude_columns: Set of column names to exclude. If None, uses DEFAULT_EXCLUDED_COLUMNS.
        """
        # Filter columns to exclude (default: routeFile and route)
        excluded: set[str] = (
            exclude_columns
            if exclude_columns is not None
            else self.DEFAULT_EXCLUDED_COLUMNS
        )

        result: str = ""

        # If DataFrame is empty, create one with expected columns
        if self.running_workouts.empty:
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
            cols_to_keep = [
                col for col in self.running_workouts.columns if col not in excluded
            ]
            result = self.running_workouts[cols_to_keep].to_csv(index=False)

        return result
