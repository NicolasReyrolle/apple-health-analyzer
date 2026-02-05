"""Export processor for Apple Health data."""

from datetime import datetime
from types import TracebackType
from typing import Any, List, Optional, Tuple, Type, TypedDict
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
    distance: Optional[float]
    distanceUnit: Optional[str]


class WorkoutRoute(TypedDict):
    """Type definition for workout route structure."""

    time: datetime
    latitude: float
    longitude: float
    altitude: float


class ExportParser:
    """Reads and parses Apple Health export files."""

    def __init__(self) -> None:
        self.log = None

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

    def _load_workouts(self, zipfile: ZipFile) -> pd.DataFrame:
        """Load workouts of a specific type from the export file."""
        if self.log:
            self._log("Loading the workouts...")

        with zipfile.open("apple_health_export/export.xml") as export_file:
            rows: List[WorkoutRecord] = []

            for event, elem in iterparse(export_file, events=("start", "end")):
                if event == "end" and elem.tag == "Workout":
                    activity_type = self._extract_activity_type(elem)

                    record = self._create_workout_record(elem, activity_type)
                    self._process_workout_children(elem, record, zipfile)
                    rows.append(record)

                    elem.clear()

            result = pd.DataFrame(rows)
            if len(result) > 0:
                result["startDate"] = pd.to_datetime(
                    result["startDate"]
                ).dt.tz_localize(None)

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
                # Consolidate all distance types into a single Distance field
                if stat_attr == "sum" and "Distance" in stat_type:
                    record["distance"] = float(stat_attr_str)
                    record["distanceUnit"] = child.get("unit")
                else:
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

    def parse(self, export_file: str, log: Optional[ui.log] = None) -> pd.DataFrame:
        """Parse the export file."""

        try:
            self.log = log
            self._log("Starting to parse the Apple Health export file...")
            with ZipFile(export_file, "r") as zipfile:
                result = self._load_workouts(zipfile)
            self._log("Finished parsing the Apple Health export file.")
            return result
        except Exception as e:
            self._log(f"Error during parsing: {e}")
            raise
