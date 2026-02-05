"""Tests for complex workout parsing and route handling."""

from pathlib import Path
from xml.etree.ElementTree import Element
from zipfile import ZipFile
from typing import Callable

import pandas as pd
import pytest

from logic.export_parser import ExportParser, WorkoutRecord

from tests.conftest import (
    build_health_xml,
    build_running_workout_example,
    build_swimming_workout_example,
    build_workout_activity,
)


class TestComplexRealWorldWorkout:
    """Test parsing of a complex real-world Apple Health workout with multiple elements."""

    def test_parse_complex_workout_with_all_elements(
        self, tmp_path: Path, build_complex_xml: Callable[..., str]
    ) -> None:
        """Test parsing a complex running workout with multiple activities and route"""

        # Create custom activity XML with elevation and distance
        activity_xml = build_workout_activity(
            activity_type="HKWorkoutActivityTypeRunning",
            distance=16.1244,
            elevation_cm="154430",
            heart_rate_stats={"average": "140.139", "minimum": "75", "maximum": "157"},
        )

        # Use the builder to create a complete workout
        xml_content = build_complex_xml(activities=[activity_xml], include_route=True)

        zip_path = tmp_path / "complex_export.zip"
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content.encode("utf-8"))

        parser = ExportParser()
        with parser:
            workouts = parser.parse(str(zip_path))

        # Verify the workout was parsed
        assert len(workouts) == 1

        # Get the parsed workout record
        workout = workouts.iloc[0]

        # Verify basic attributes
        assert workout["activityType"] == "Running"
        assert workout["startDate"] == pd.Timestamp("2025-12-20 12:51:00")
        assert workout["endDate"] == "2025-12-20 14:50:16 +0100"
        assert workout["duration"] == 7156
        assert workout["durationUnit"] == "seconds"
        assert workout["source"] == "Apple Watch"

        # Verify metadata entries were captured
        assert not workout["IndoorWorkout"]  # "0" converts to False
        assert workout["TimeZone"] == "Europe/Paris"
        assert workout["WeatherHumidity"] == pytest.approx(  # type: ignore[misc]
            94.0, abs=0.001
        )  # "9400 %" -> 94.0
        assert workout["WeatherTemperature"] == pytest.approx(  # type: ignore[misc]
            8.690, abs=0.001
        )  # 47.6418 degF -> ~8.690 degC

        # Verify statistics were captured
        assert workout["sumStepCount"] == 17599
        assert workout["averageRunningGroundContactTime"] == pytest.approx(  # type: ignore[misc]
            323.718
        )
        assert workout["minimumRunningGroundContactTime"] == 224
        assert workout["maximumRunningGroundContactTime"] == 369
        assert workout["averageRunningPower"] == pytest.approx(222.789)  # type: ignore[misc]
        assert workout["sumActiveEnergyBurned"] == pytest.approx(1389.98)  # type: ignore[misc]
        assert workout["distance"] == 16124
        assert workout["averageHeartRate"] == pytest.approx(140.139)  # type: ignore[misc]

        # Verify metadata entries for elevation (from WorkoutActivity)
        assert workout["ElevationAscended"] == pytest.approx(1544.3, abs=0.01)  # type: ignore[misc]

        # Verify the routeFile is captured
        assert workout["routeFile"] == "/workout-routes/route_2025-12-20_2.50pm.gpx"

    def test_parse_multiple_separate_workouts_with_different_distance_units(
        self, tmp_path: Path
    ) -> None:
        """Test parsing an export file containing separate swimming and running workouts.

        This verifies that:
        - Swimming workout with distance in meters (750 m) is correctly parsed
        - Running workout with distance in kilometers (3.06833 km) is correctly parsed
        - Both workouts are parsed as separate records with their correct distance units
        """

        swimming_workout = build_swimming_workout_example()
        running_workout = build_running_workout_example()

        # Create HealthData XML with both separate workouts
        xml_content = build_health_xml(workouts=[swimming_workout, running_workout])

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
        assert running["distance"] == 3068
        assert running["averageHeartRate"] == pytest.approx(129.194)  # type: ignore[misc]
        assert running["ElevationAscended"] == pytest.approx(73.3, abs=0.01)  # type: ignore[misc]


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
