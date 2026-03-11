"""Export processor for Apple Health data."""

import logging
from collections import defaultdict
from datetime import datetime
from types import TracebackType
from typing import Any, Callable, List, Optional, Tuple, Type
from xml.etree.ElementTree import Element
from zipfile import ZipFile

import pandas as pd
from defusedxml.ElementTree import iterparse

from logic.models import WorkoutRecord
from logic.parsed_health_data import ParsedHealthData
from logic.workout_route import WorkoutRoute, RoutePoint

_logger = logging.getLogger(__name__)

# Configuration constants
WORKOUT_PROGRESS_INTERVAL = 100  # Report progress every N workouts

# Only parse record types that the application currently supports to limit memory usage.
SUPPORTED_RECORD_TYPES = frozenset({"HeartRate", "BodyMass", "VO2Max"})


class ExportParser:
    """Reads and parses Apple Health export files."""

    def __init__(self, progress_callback: Optional[Callable[[str], None]] = None) -> None:
        self.progress_callback = progress_callback

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
    def to_number(raw: str | None) -> float | int | None:
        """Convert a string to a number (int or float), or return None if conversion fails."""
        if raw is None:
            return None
        try:
            value = float(raw)
            return int(value) if value.is_integer() else value
        except ValueError:
            return None

    @staticmethod
    def parse_metadata_value(raw_value: Optional[str]) -> Tuple[Any, Optional[str]]:
        """
        Parse a metadata entry value without boolean coercion.

        Unlike _parse_value, numeric values "0" and "1" are returned as integers,
        not booleans. This is needed for enumerated metadata fields such as
        HeartRateMotionContext (0/1/2).

        Returns: (value, unit) where unit is None when no unit is present.
        """
        if not raw_value:
            return None, None

        raw_value = raw_value.strip()

        parts = raw_value.split(maxsplit=1)
        if len(parts) == 1:
            num = ExportParser.to_number(parts[0])
            if num is not None:
                return num, None
            return parts[0], None

        num = ExportParser.to_number(parts[0])
        if num is not None:
            unit = parts[1].strip() or None
            return float(num), unit
        return raw_value, None

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
    def duration_to_seconds(value: float, unit: str = "min") -> int:
        """Convert duration to seconds based on the unit."""
        if unit == "min" or unit == "":
            return int(value * 60)
        elif unit == "h":
            return int(value * 3600)
        elif unit == "s":
            return int(value)
        else:
            raise ValueError(f"Unknown duration unit: {unit}")

    def _log(self, message: str) -> None:
        """Emit progress message if callback is enabled."""
        if self.progress_callback:
            try:
                self.progress_callback(message)
            except Exception:  # pylint: disable=broad-except
                _logger.debug(message)

    def _process_workout_event(
        self,
        elem: Element,
        zipfile: ZipFile,
        workout_rows: list[WorkoutRecord],
    ) -> None:
        """Process a workout element and append the normalized workout record."""
        activity_type = self._extract_activity_type(elem)
        record = self._create_workout_record(elem, activity_type)
        self._process_workout_children(elem, record, zipfile)
        workout_rows.append(record)

        if len(workout_rows) % WORKOUT_PROGRESS_INTERVAL == 0:
            self._log(f"Processed {len(workout_rows)} workouts...")

    def _process_record_event(
        self,
        elem: Element,
        record_rows_by_type: dict[str, list[dict[str, Any]]],
    ) -> None:
        """Process a health record element and store supported record types."""
        result = self._extract_health_data_record(elem)
        if result is None:
            return

        record_type, record_data = result
        if record_type in SUPPORTED_RECORD_TYPES:
            record_rows_by_type[record_type].append(record_data)

    def _build_parsed_health_data(
        self,
        workout_rows: list[WorkoutRecord],
        record_rows_by_type: dict[str, list[dict[str, Any]]],
    ) -> ParsedHealthData:
        """Build ParsedHealthData from parsed row collections."""
        workouts_df = pd.DataFrame(workout_rows)
        records_by_type_df = {
            record_type: pd.DataFrame(rows) for record_type, rows in record_rows_by_type.items()
        }

        if len(workouts_df) > 0:
            workouts_df["startDate"] = pd.to_datetime(workouts_df["startDate"]).dt.tz_localize(None)

        self._log(f"Loaded {len(workouts_df)} workouts total.")
        return ParsedHealthData(workouts=workouts_df, records_by_type=records_by_type_df)

    def _load_data(self, zipfile: ZipFile) -> ParsedHealthData:
        """Load workouts and HealthKit records from the export file into ParsedHealthData."""
        self._log("Loading the workouts...")

        with zipfile.open("apple_health_export/export.xml") as export_file:
            workout_rows: List[WorkoutRecord] = []
            record_rows_by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)

            for event, elem in iterparse(export_file, events=("end",)):
                if event == "end" and elem.tag == "Workout":
                    self._process_workout_event(elem, zipfile, workout_rows)

                    elem.clear()
                    continue

                if event == "end" and elem.tag == "Record":
                    self._process_record_event(elem, record_rows_by_type)

                    elem.clear()

            return self._build_parsed_health_data(workout_rows, record_rows_by_type)

    def _extract_health_data_record(self, elem: Element) -> Optional[Tuple[str, dict[str, Any]]]:
        """Extract and clean health data record from element attributes and metadata."""
        raw_type = elem.get("type")
        if not raw_type:
            return None
        record_type = raw_type.replace("HKQuantityTypeIdentifier", "")
        record_data = {
            "type": record_type,
            "startDate": elem.get("startDate"),
            "value": self.to_number(elem.get("value")),
        }
        # Include metadata entries as additional fields
        for child in elem:
            if child.tag == "MetadataEntry":
                raw_key = child.get("key", "")
                if raw_key.startswith("HKMetadataKey"):
                    key = raw_key[len("HKMetadataKey") :]
                elif raw_key.startswith("HK"):
                    key = raw_key[2:]
                else:
                    key = raw_key
                value, unit = self.parse_metadata_value(child.get("value", ""))
                record_data[key] = value
                if unit:
                    record_data[f"{key}Unit"] = unit
        return record_type, record_data

    def _extract_activity_type(self, elem: Element) -> str:
        """Extract and clean activity type from workout element."""
        activity_type_raw = elem.get("workoutActivityType", "")
        return activity_type_raw.replace("HKWorkoutActivityType", "")

    def _create_workout_record(self, elem: Element, activity_type: str) -> WorkoutRecord:
        """Create base workout record from element attributes."""
        duration_str = elem.get("duration")
        duration_unit_str: str = elem.get("durationUnit") or ""
        return {
            "activityType": activity_type,
            "duration": (
                self.duration_to_seconds(float(duration_str), duration_unit_str)
                if duration_str
                else None
            ),
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
            elif child.tag == "WorkoutRoute":
                self._process_workout_route(child, record, zipfile)

    @staticmethod
    def str_distance_to_meters(value: str, unit: Optional[str]) -> int:
        """Convert distance to meters."""
        if unit is None:
            raise ValueError("Distance unit is missing (None). Cannot convert to meters.")
        if unit == "km":
            return int(float(value) * 1000)
        if unit == "m":
            return int(float(value))
        if unit == "mi":
            return int(float(value) * 1609.34)
        raise ValueError(f"Unknown distance unit: {unit}")

    def _process_workout_statistics(self, child: Element, record: WorkoutRecord) -> None:
        """Process workout statistics child element."""
        stat_type = child.get("type", "").replace("HKQuantityTypeIdentifier", "")

        for stat_attr in ["sum", "average", "minimum", "maximum"]:
            if child.get(stat_attr):
                stat_attr_str = child.get(stat_attr) or "0"
                # Consolidate all distance types into a single Distance field
                if stat_attr == "sum" and "Distance" in stat_type:
                    record["distance"] = self.str_distance_to_meters(
                        stat_attr_str, child.get("unit")
                    )
                else:
                    record[f"{stat_attr}{stat_type}"] = float(stat_attr_str)
                    record[f"{stat_attr}{stat_type}Unit"] = child.get("unit")

    def _load_route(self, zipfile: ZipFile, route_path: str) -> Optional[WorkoutRoute]:
        """Load GPX route file from the export zip."""
        try:
            with zipfile.open(f"apple_health_export{route_path}") as route_file:
                route: WorkoutRoute = WorkoutRoute(points=[])
                for event, elem in iterparse(route_file, events=("start", "end")):
                    if event == "end" and elem.tag == "{http://www.topografix.com/GPX/1/1}trkpt":
                        latitude: str = elem.get("lat") or "0.0"
                        longitude: str = elem.get("lon") or "0.0"

                        # Extract child elements (ele and time are not attributes)
                        ele_elem = elem.find("{http://www.topografix.com/GPX/1/1}ele")
                        time_elem = elem.find("{http://www.topografix.com/GPX/1/1}time")

                        altitude: str = ele_elem.text or "0.0" if ele_elem is not None else "0.0"
                        time_str: str = time_elem.text or "" if time_elem is not None else ""

                        route.add_point(
                            RoutePoint(
                                time=datetime.fromisoformat(time_str.replace("Z", "+00:00")),
                                latitude=float(latitude),
                                longitude=float(longitude),
                                altitude=float(altitude),
                            )
                        )
                        elem.clear()
                return route
        except KeyError:
            self._log(f"Route file not found in export: {route_path}")
            return None

    def _process_workout_route(
        self, elem: Element, record: WorkoutRecord, zipfile: ZipFile
    ) -> None:
        """Process workout route child element."""
        for child in elem:
            if child.tag == "FileReference":
                route_path = child.get("path")
                if not route_path:
                    continue

                route_part = self._load_route(zipfile, route_path)

                route_files = record.get("routeFiles")
                if not isinstance(route_files, list):
                    route_files = []
                    record["routeFiles"] = route_files
                route_files.append(route_path)

                # Backward compatibility: keep first route in legacy singular fields.
                if "routeFile" not in record:
                    record["routeFile"] = route_path

                if route_part is None:
                    continue

                existing_route = record.get("route")
                if isinstance(existing_route, WorkoutRoute):
                    if (
                        existing_route.points
                        and route_part.points
                        and existing_route.points[-1] == route_part.points[0]
                    ):
                        existing_route.points.extend(route_part.points[1:])
                    else:
                        existing_route.points.extend(route_part.points)
                else:
                    record["route"] = route_part

    def _process_metadata_entry(self, child: Element, record: WorkoutRecord) -> None:
        """Process metadata entry child element."""
        key = child.get("key", "").replace("HK", "")

        # Skip keys that have no meaning for analysis
        if key == "WOIntervalStepKeyPath":
            return

        value, unit = self._parse_value(child.get("value", ""))

        # If the key already exists, do not consider it as there can be duplicate in the real file
        if key in record:
            logging.debug("Duplicate key '%s' found, bypassing the second one", key)
        else:
            record[key] = value
            if unit:
                record[f"{key}Unit"] = unit

    def parse(self, export_file: str) -> ParsedHealthData:
        """Parse the export file."""

        try:
            self._log("Starting to parse the Apple Health export file...")
            with ZipFile(export_file, "r") as zipfile:
                result = self._load_data(zipfile)
            self._log("Finished parsing the Apple Health export file.")
            return result
        except Exception as e:
            self._log(f"Error during parsing: {e}")
            raise
