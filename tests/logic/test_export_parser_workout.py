"""Tests for workout processing functionality."""

from pathlib import Path
from xml.etree.ElementTree import Element
from zipfile import ZipFile

import pytest

import logic.export_parser as ep
import logic.workout_manager as wm


class TestCreateWorkoutRecord:
    """Test the _create_workout_record method."""

    # pylint: disable=protected-access
    def test_create_workout_record_with_all_attributes(self):
        """Test creating a workout record with all attributes."""
        elem = Element(
            "Workout",
            attrib={
                "workoutActivityType": "HKWorkoutActivityTypeRunning",
                "duration": "30",
                "startDate": "2024-01-01 10:00:00",
                "endDate": "2024-01-01 10:30:00",
                "sourceName": "Apple Watch",
            },
        )
        parser = ep.ExportParser()
        record = parser._create_workout_record(elem, "Running")  # type: ignore[misc]

        assert record["activityType"] == "Running"
        assert isinstance(record.get("duration"), int)
        assert record.get("duration") == 1800
        assert record.get("startDate") == "2024-01-01 10:00:00"
        assert record.get("endDate") == "2024-01-01 10:30:00"
        assert record.get("source") == "Apple Watch"

    def test_create_workout_record_with_missing_attributes(self):
        """Test creating a workout record with missing attributes."""
        elem = Element(
            "Workout", attrib={"workoutActivityType": "HKWorkoutActivityTypeRunning"}
        )
        parser = ep.ExportParser()
        record = parser._create_workout_record(elem, "Running")  # type: ignore[misc]

        assert record["activityType"] == "Running"
        assert record.get("duration") is None
        assert record.get("startDate") is None
        assert record.get("endDate") is None
        assert record.get("source") is None


class TestProcessWorkoutStatistics:
    """Test the _process_workout_statistics method."""

    # pylint: disable=protected-access
    def test_process_workout_statistics_with_sum(self):
        """Test processing workout statistics with sum value."""
        elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierDistanceWalkingRunning",
                "sum": "5.2",
                "unit": "km",
            },
        )
        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_statistics(elem, record)  # type: ignore[misc]

        assert isinstance(record.get("sumDistanceWalkingRunning"), float)
        assert record.get("sumDistanceWalkingRunning") == pytest.approx(5.2)  # type: ignore[misc]
        assert record.get("sumDistanceWalkingRunningUnit") == "km"

    def test_process_workout_statistics_with_average(self):
        """Test processing workout statistics with average value."""
        elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierHeartRate",
                "average": "150",
                "unit": "count/min",
            },
        )
        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_statistics(elem, record)  # type: ignore[misc]

        assert isinstance(record.get("averageHeartRate"), float)
        assert record.get("averageHeartRate") == 150
        assert record.get("averageHeartRateUnit") == "count/min"

    def test_process_workout_statistics_with_multiple_values(self):
        """Test processing workout statistics with multiple values."""
        elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierSpeed",
                "minimum": "8.0",
                "unit": "km/h",
                "maximum": "12.0",
            },
        )
        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_statistics(elem, record)  # type: ignore[misc]

        assert isinstance(record.get("minimumSpeed"), float)
        assert record.get("minimumSpeed") == pytest.approx(8.0)  # type: ignore[misc]
        assert record.get("minimumSpeedUnit") == "km/h"
        assert isinstance(record.get("maximumSpeed"), float)
        assert record.get("maximumSpeed") == pytest.approx(12.0)  # type: ignore[misc]
        assert record.get("maximumSpeedUnit") == "km/h"

    def test_process_workout_statistics_with_no_values(self):
        """Test processing workout statistics with no values (all attributes missing)."""
        elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierEnergy",
            },
        )
        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_statistics(elem, record)  # type: ignore[misc]

        # Should not add any statistics since no values are present
        assert len(record) == 1  # Only activityType


class TestProcessMetadataEntry:
    """Test the _process_metadata_entry method."""

    # pylint: disable=protected-access
    def test_process_metadata_entry_with_simple_value(self):
        """Test processing a simple metadata entry."""
        elem = Element(
            "MetadataEntry",
            attrib={"key": "HKMetadataKeyTimeZone", "value": "Europe/Luxembourg"},
        )
        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem, record)  # type: ignore[misc]

        assert record.get("MetadataKeyTimeZone") == "Europe/Luxembourg"

    def test_process_metadata_entry_with_value_and_unit(self):
        """Test processing metadata entry with value and unit."""
        elem = Element(
            "MetadataEntry",
            attrib={"key": "HKMetadataKeyElevationAscended", "value": "100 m"},
        )
        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem, record)  # type: ignore[misc]
        assert isinstance(record.get("MetadataKeyElevationAscended"), float)
        assert record.get("MetadataKeyElevationAscended") == pytest.approx(  # type: ignore[misc]
            100.0
        )
        assert record.get("MetadataKeyElevationAscendedUnit") == "m"

    def test_process_metadata_entry_with_boolean_conversion(self):
        """Test metadata entry with boolean conversion."""
        elem = Element(
            "MetadataEntry",
            attrib={"key": "HKMetadataKeyIsIndoorWorkout", "value": "1"},
        )
        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem, record)  # type: ignore[misc]

        assert record.get("MetadataKeyIsIndoorWorkout") is True


class TestMetadataEntryAccumulation:
    """Test numeric accumulation in _process_metadata_entry."""

    # pylint: disable=protected-access
    def test_process_metadata_entry_accumulates_numeric_values(self) -> None:
        """Test that numeric values with same key are accumulated (summed)."""
        elem1 = Element(
            "MetadataEntry", attrib={"key": "HKElevationAscended", "value": "100 m"}
        )
        elem2 = Element(
            "MetadataEntry", attrib={"key": "HKElevationAscended", "value": "50 m"}
        )

        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem1, record)  # type: ignore[misc]
        # After first entry: should have ElevationAscended = 100.0
        assert isinstance(record.get("ElevationAscended"), float)
        assert record.get("ElevationAscended") == pytest.approx(100.0)  # type: ignore[misc]

        parser._process_metadata_entry(elem2, record)  # type: ignore[misc]
        # After second entry: should accumulate to 150.0
        assert isinstance(record.get("ElevationAscended"), float)
        assert record.get("ElevationAscended") == pytest.approx(150.0)  # type: ignore[misc]

    def test_process_metadata_entry_skips_interval_step_key(self) -> None:
        """Test that WOIntervalStepKeyPath is skipped."""
        elem = Element(
            "MetadataEntry",
            attrib={"key": "HKWOIntervalStepKeyPath", "value": "0.0.0"},
        )

        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem, record)  # type: ignore[misc]

        # Should be skipped, so record remains unchanged
        assert record == {"activityType": "Running"}

    def test_process_metadata_entry_overwrites_non_numeric_with_numeric(self) -> None:
        """Test that non-numeric values are overwritten when numeric values come later."""
        elem1 = Element(
            "MetadataEntry", attrib={"key": "HKTestKey", "value": "some string"}
        )
        elem2 = Element("MetadataEntry", attrib={"key": "HKTestKey", "value": "100 m"})

        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem1, record)  # type: ignore[misc]
        assert record.get("TestKey") == "some string"

        parser._process_metadata_entry(elem2, record)  # type: ignore[misc]
        # Should overwrite with numeric value (not accumulate)
        assert isinstance(record.get("TestKey"), float)
        assert record.get("TestKey") == pytest.approx(100.0)  # type: ignore[misc]


class TestProcessWorkoutChildren:
    """Test the _process_workout_children method."""

    # pylint: disable=protected-access
    def test_process_workout_children_with_statistics(self, tmp_path: Path) -> None:
        """Test processing workout with child statistics."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parent = Element("Workout")
        stats_elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierDistance",
                "sum": "10.0",
                "unit": "km",
            },
        )
        parent.append(stats_elem)

        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        with ZipFile(zip_path, "r") as zf:
            parser._process_workout_children(parent, record, zf)  # type: ignore[misc]

        assert isinstance(record.get("sumDistance"), float)
        assert record.get("sumDistance") == pytest.approx(10.0)  # type: ignore[misc]
        assert record.get("sumDistanceUnit") == "km"

    def test_process_workout_children_with_metadata(self, tmp_path: Path) -> None:
        """Test processing workout with child metadata entries."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parent = Element("Workout")
        metadata_elem = Element(
            "MetadataEntry",
            attrib={"key": "HKMetadataKeyTimeZone", "value": "Europe/Paris"},
        )
        parent.append(metadata_elem)

        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        with ZipFile(zip_path, "r") as zf:
            parser._process_workout_children(parent, record, zf)  # type: ignore[misc]

        assert record.get("MetadataKeyTimeZone") == "Europe/Paris"

    def test_process_workout_children_mixed(self, tmp_path: Path) -> None:
        """Test processing workout with mixed children."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parent = Element("Workout")
        stats_elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierDistance",
                "sum": "5.0",
                "sumUnit": "km",
            },
        )
        metadata_elem = Element(
            "MetadataEntry", attrib={"key": "HKMetadataKeyTimeZone", "value": "UTC"}
        )
        parent.append(stats_elem)
        parent.append(metadata_elem)

        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        with ZipFile(zip_path, "r") as zf:
            parser._process_workout_children(parent, record, zf)  # type: ignore[misc]

        assert isinstance(record.get("sumDistance"), float)
        assert record.get("sumDistance") == pytest.approx(5.0)  # type: ignore[misc]
        assert record.get("MetadataKeyTimeZone") == "UTC"

    def test_process_workout_children_with_unknown_element(
        self, tmp_path: Path
    ) -> None:
        """Test processing workout with unknown child element (should be ignored)."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parent = Element("Workout")
        unknown_elem = Element("UnknownElement", attrib={"some": "attribute"})
        parent.append(unknown_elem)

        parser = ep.ExportParser()
        record: ep.WorkoutRecord = {"activityType": "Running"}

        with ZipFile(zip_path, "r") as zf:
            parser._process_workout_children(parent, record, zf)  # type: ignore[misc]

        # Should only have activityType, unknown element should be ignored
        assert record == {"activityType": "Running"}


class TestLoadWorkouts:
    """Test the _load_workouts method."""

    def test_load_workouts_with_nested_workout_activity(self, tmp_path: Path) -> None:
        """Test loading workouts with nested WorkoutActivity elements."""
        zip_path = tmp_path / "workouts_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <WorkoutActivity uuid="test-uuid" startDate="2024-01-01" endDate="2024-01-01" duration="30">
            <WorkoutStatistics type="HKQuantityTypeIdentifierDistance" sum="5.0" sumUnit="km"/>
        </WorkoutActivity>
    </Workout>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parser = ep.ExportParser()
        with ZipFile(zip_path, "r") as zf:
            workouts = wm.WorkoutManager(parser.parse(str(zip_path)))

        assert workouts.count() == 1
        # Verify statistics from nested element were captured
        assert isinstance(workouts.get_workouts().iloc[0].get("sumDistance"), float)
        assert workouts.get_workouts().iloc[0].get(
            "sumDistance") == pytest.approx( # type: ignore[misc]
            5.0
        )
