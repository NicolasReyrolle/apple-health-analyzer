"""Tests for complex workout parsing and route handling."""

from pathlib import Path
from xml.etree.ElementTree import Element
from zipfile import ZipFile
from typing import Callable

import pandas as pd
import pytest

from logic.export_parser import ExportParser, WorkoutRecord

from tests.conftest import build_health_export_xml, load_export_fragment


class TestComplexRealWorldWorkout:
    """Test parsing of a complex real-world Apple Health workout with multiple elements."""

    def test_parse_complex_workout_with_all_elements(
        self, create_health_zip: Callable[..., str]
    ) -> None:
        """Test parsing a complex running workout with multiple activities and route"""

        xml_content = build_health_export_xml([load_export_fragment("workout_running.xml")])
        zip_path = create_health_zip(xml_content=xml_content)

        parser = ExportParser()
        with parser:
            workouts = parser.parse(str(zip_path))

        # Verify the workout was parsed
        assert len(workouts) == 1

        # Get the parsed workout record
        workout = workouts.iloc[0]

        # Verify basic attributes
        assert workout["activityType"] == "Running"
        assert workout["startDate"] == pd.Timestamp("2025-09-16 16:14:50")
        assert workout["endDate"] == "2025-09-16 17:15:43 +0100"
        assert workout["duration"] == 3653
        assert workout["durationUnit"] == "seconds"
        assert workout["source"] == "Apple Watch"

        # Verify metadata entries were captured
        assert not workout["IndoorWorkout"]  # "0" converts to False
        assert workout["TimeZone"] == "Europe/Paris"
        assert workout["WeatherHumidity"] == pytest.approx(  # type: ignore[misc]
            64.0, abs=0.001
        )  # "6400 %" -> 64.0
        assert workout["WeatherTemperature"] == pytest.approx(  # type: ignore[misc]
            16.650, abs=0.001
        )  # 61.9694 degF -> ~16.650 degC

        # Verify statistics were captured
        assert workout["sumStepCount"] == pytest.approx(9787.18)  # type: ignore[misc]
        assert workout["averageRunningGroundContactTime"] == pytest.approx(  # type: ignore[misc]
            303.967
        )
        assert workout["minimumRunningGroundContactTime"] == 231
        assert workout["maximumRunningGroundContactTime"] == 353
        assert workout["averageRunningPower"] == pytest.approx(208.697)  # type: ignore[misc]
        assert workout["sumActiveEnergyBurned"] == pytest.approx(655.465)  # type: ignore[misc]
        assert workout["distance"] == 8955
        assert workout["averageHeartRate"] == pytest.approx(130.153)  # type: ignore[misc]

        # Verify metadata entries for elevation
        assert workout["ElevationAscended"] == pytest.approx(65.75, abs=0.01)  # type: ignore[misc]

        # Verify the routeFile is captured
        assert workout["routeFile"] == "/workout-routes/route_2025-09-16_6.15pm.gpx"

    def test_parse_multiple_separate_workouts_with_different_distance_units(
        self, tmp_path: Path
    ) -> None:
        """Test parsing an export file containing separate swimming and running workouts.

        This verifies that:
        - Swimming workout with distance in meters (750 m) is correctly parsed
        - Running workout with distance in kilometers (8.95512 km) is correctly parsed
        - Both workouts are parsed as separate records with their correct distance units
        """

        swimming_workout = load_export_fragment("workout_swimming.xml")
        running_workout = load_export_fragment("workout_running.xml")

        # Create HealthData XML with both separate workouts
        xml_content = build_health_export_xml([swimming_workout, running_workout])

        zip_path = tmp_path / "multiple_workouts.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content.encode("utf-8"))

        parser = ExportParser()
        with parser:
            workouts = parser.parse(str(zip_path))

        # Should parse as two separate workout records
        assert len(workouts) == 2

        # First workout: Swimming
        swimming = workouts.iloc[0]
        assert swimming["activityType"] == "Swimming"
        assert swimming["distance"] == 750
        assert swimming["averageHeartRate"] == pytest.approx(102.834)  # type: ignore[misc]

        # Second workout: Running
        running = workouts.iloc[1]
        assert running["activityType"] == "Running"
        assert running["distance"] == 8955
        assert running["averageHeartRate"] == pytest.approx(130.153)  # type: ignore[misc]
        assert running["ElevationAscended"] == pytest.approx(65.75, abs=0.01)  # type: ignore[misc]

    def test_metadata_not_duplicated_when_present_at_multiple_levels(
        self, create_health_zip: Callable[..., str]
    ) -> None:
        """Test that metadata entries appearing at both WorkoutActivity and Workout levels
        are not stored twice or have their values doubled.

        The workout_running.xml fixture has duplicate MetadataEntry elements:
        - Some appear inside <WorkoutActivity> elements
        - The same entries also appear at the top <Workout> level

        The parser should process each unique metadata key only once with its original value,
        not accumulate or double the values when encountering duplicates.

        This test currently fails because the parser processes metadata at both levels,
        causing values to be doubled (e.g., 6400% becomes 64.0 twice -> 128.0).
        """

        xml_content = build_health_export_xml([load_export_fragment("workout_running.xml")])
        zip_path = create_health_zip(xml_content=xml_content)

        parser = ExportParser()
        with parser:
            workouts = parser.parse(str(zip_path))

        assert len(workouts) == 1
        workout = workouts.iloc[0]

        # Test metadata that appears at both WorkoutActivity and top-level Workout
        # Original value: "6400 %" -> should be 64.0, NOT 128.0 (doubled)
        assert workout["WeatherHumidity"] == pytest.approx(64.0, abs=0.001)  # type: ignore[misc]

        # Original value: "6575 cm" -> should be 65.75 m, NOT 131.5 m (doubled)
        assert workout["ElevationAscended"] == pytest.approx(65.75, abs=0.01)  # type: ignore[misc]

        # Original value: "61.9694 degF" -> should be ~16.65°C, NOT ~33.3°C (doubled)
        assert workout["WeatherTemperature"] == pytest.approx(  # type: ignore[misc]
            16.650, abs=0.001
        )

        # Boolean metadata should remain False/True, not become True
        # (0 + 0 = 0, but semantically wrong)
        assert not workout["IndoorWorkout"]  # Should be False, not processed twice


class TestLoadRoute:
    """Test the _load_route method."""

    # pylint: disable=protected-access
    def test_load_route_with_valid_gpx(self, tmp_path: Path) -> None:
        """Test loading a valid GPX route file."""
        zip_path = tmp_path / "route_export.zip"
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
            <trkpt lat="48.8566" lon="2.3522">
                <ele>100.5</ele>
                <time>2024-01-01T10:00:00Z</time>
            </trkpt>
            <trkpt lat="48.8567" lon="2.3523">
                <ele>101.2</ele>
                <time>2024-01-01T10:01:00Z</time>
            </trkpt>
        </trkseg>
    </trk>
</gpx>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/workout-routes/test_route.gpx", gpx_content)

        parser = ExportParser()
        with ZipFile(zip_path, "r") as zf:
            result = parser._load_route(zf, "/workout-routes/test_route.gpx")  # type: ignore[misc]

        assert result is not None
        assert len(result) == 2
        assert list(result.columns) == ["time", "latitude", "longitude", "altitude"]
        assert result.iloc[0]["latitude"] == pytest.approx(48.8566)  # type: ignore[misc]
        assert result.iloc[0]["longitude"] == pytest.approx(2.3522)  # type: ignore[misc]
        assert result.iloc[0]["altitude"] == pytest.approx(100.5)  # type: ignore[misc]

    def test_load_route_empty_gpx(self, tmp_path: Path) -> None:
        """Test loading an empty GPX file."""
        zip_path = tmp_path / "route_export.zip"
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
        </trkseg>
    </trk>
</gpx>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/workout-routes/empty_route.gpx", gpx_content)

        parser = ExportParser()
        with ZipFile(zip_path, "r") as zf:
            result = parser._load_route(zf, "/workout-routes/empty_route.gpx")  # type: ignore[misc]

        assert result is not None
        assert len(result) == 0

    def test_load_route_missing_ele_and_time(self, tmp_path: Path) -> None:
        """Test loading GPX with missing altitude and time elements."""
        zip_path = tmp_path / "route_export.zip"
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
            <trkpt lat="48.8566" lon="2.3522">
            </trkpt>
        </trkseg>
    </trk>
</gpx>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/workout-routes/incomplete_route.gpx", gpx_content)

        parser = ExportParser()
        with ZipFile(zip_path, "r") as zf:
            # This should raise a ValueError when trying to parse empty time string
            with pytest.raises(ValueError):
                parser._load_route(zf, "/workout-routes/incomplete_route.gpx")  # type: ignore[misc]


class TestProcessWorkoutRoute:
    """Test the _process_workout_route method."""

    # pylint: disable=protected-access
    def test_process_workout_route_with_file_reference(self, tmp_path: Path) -> None:
        """Test processing a workout route with FileReference."""
        zip_path = tmp_path / "route_export.zip"
        gpx_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<gpx version="1.1" xmlns="http://www.topografix.com/GPX/1/1">
    <trk>
        <trkseg>
            <trkpt lat="48.8566" lon="2.3522">
                <ele>100.0</ele>
                <time>2024-01-01T10:00:00Z</time>
            </trkpt>
        </trkseg>
    </trk>
</gpx>
"""
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <WorkoutRoute sourceName="Apple Watch">
            <FileReference path="/workout-routes/test_route.gpx"/>
        </WorkoutRoute>
    </Workout>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)
            zf.writestr("apple_health_export/workout-routes/test_route.gpx", gpx_content)

        # Create a route element with FileReference child
        route_elem = Element("WorkoutRoute")
        file_ref = Element("FileReference", attrib={"path": "/workout-routes/test_route.gpx"})
        route_elem.append(file_ref)

        parser = ExportParser()
        record: WorkoutRecord = {"activityType": "Running"}

        with ZipFile(zip_path, "r") as zf:
            parser._process_workout_route(route_elem, record, zf)  # type: ignore[misc]

        # Verify routeFile is set
        assert record.get("routeFile") == "/workout-routes/test_route.gpx"
        # Verify route DataFrame is loaded
        assert record.get("route") is not None
        assert isinstance(record.get("route"), pd.DataFrame)

    def test_process_workout_route_empty_route_element(self, tmp_path: Path) -> None:
        """Test processing an empty workout route element."""
        zip_path = tmp_path / "route_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        route_elem = Element("WorkoutRoute")

        parser = ExportParser()
        record: WorkoutRecord = {"activityType": "Running"}

        with ZipFile(zip_path, "r") as zf:
            parser._process_workout_route(route_elem, record, zf)  # type: ignore[misc]

        # Record should remain unchanged if no FileReference
        assert record == {"activityType": "Running"}
