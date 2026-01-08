"""Tests for the ExportParser module."""

import json
import os
from pathlib import Path
from typing import Generator
from xml.etree.ElementTree import Element
from zipfile import ZipFile

import pandas as pd
import pytest
from _pytest.capture import CaptureFixture

from src import export_parser as ep


class TestExportParser:
    """Test cases for the ExportParser class."""

    @pytest.fixture
    def sample_file(self) -> str:
        """Provide path to sample export file for testing."""
        sample_path = os.path.join(
            os.path.dirname(__file__), "fixtures", "export_sample.zip"
        )
        if os.path.exists(sample_path):
            return sample_path
        # Skip if sample doesn't exist
        pytest.skip("export_sample.zip not found in tests/fixtures/")
        return ""  # This line won't be reached but satisfies pylint

    @pytest.fixture
    def setup_data(self, sample_file: str) -> Generator[ep.ExportParser, None, None]:
        """Create ExportParser instance for testing."""
        parser = ep.ExportParser(sample_file)
        yield parser

    def test_init(self, sample_file: str):
        """Test that the ExportParser instance is correctly initialized."""
        parser = ep.ExportParser(sample_file)
        assert parser.export_file == sample_file
        assert len(parser.running_workouts) == 0
        assert list(parser.running_workouts.columns) == [
            "startDate",
            "endDate",
            "duration",
            "durationUnit",
        ]

    def test_context_manager_protocol(self, setup_data: ep.ExportParser) -> None:
        """Test that ExportParser correctly implements context manager protocol."""
        with setup_data as result:
            assert result is setup_data

    def test_parse_with_sample_file(self, setup_data: ep.ExportParser) -> None:
        """Test that parse() method can be called without error."""
        with setup_data:
            # This should not raise an error (file may not have data, but should parse)
            try:
                setup_data.parse()
            except FileNotFoundError:
                # If file doesn't exist or is invalid, that's okay for this test
                pass

    def test_missing_file_exits_gracefully(self, capsys: CaptureFixture[str]) -> None:
        """Test that parse() handles missing files gracefully."""
        parser = ep.ExportParser("nonexistent_file.zip")
        with pytest.raises(SystemExit) as exc_info:
            parser.parse()
        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "Apple Health Export file not found" in captured.out

    def test_running_workouts_dataframe_initialized(self, sample_file: str):
        """Test that running_workouts DataFrame is initialized with correct columns."""
        parser = ep.ExportParser(sample_file)
        assert isinstance(parser.running_workouts, pd.DataFrame)
        assert len(parser.running_workouts) == 0
        assert list(parser.running_workouts.columns) == [
            "startDate",
            "endDate",
            "duration",
            "durationUnit",
        ]


class TestLoadRunningWorkouts:
    """Test the _load_running_workouts method."""

    def test_load_running_workouts_with_valid_zip(self, tmp_path: Path) -> None:
        """Test loading running workouts from a valid Apple Health ZIP file."""
        # Create a temporary ZIP with mock export.xml
        zip_path = tmp_path / "mock_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeCycling" startDate="2024-01-02" endDate="2024-01-02" duration="45"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-03" endDate="2024-01-03" duration="25"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()

        # Should have loaded only running workouts (2, not the cycling one)
        assert len(parser.running_workouts) == 2
        assert list(parser.running_workouts["startDate"]) == [
            "2024-01-01",
            "2024-01-03",
        ]

    def test_load_running_workouts_empty(
        self, tmp_path: Path, capsys: CaptureFixture[str]
    ) -> None:
        """Test loading workouts from ZIP with no running workouts."""
        zip_path = tmp_path / "empty_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()

        assert len(parser.running_workouts) == 0
        captured = capsys.readouterr()
        assert "Loaded 0 running workouts" in captured.out

    def test_load_multiple_workouts_accumulate(self, tmp_path: Path) -> None:
        """Test that multiple workouts are loaded into DataFrame."""
        zip_path = tmp_path / "multi_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30" durationUnit="min"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-02" endDate="2024-01-02" duration="25" durationUnit="min"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()

        # First parse should have 2 workouts
        assert len(parser.running_workouts) == 2
        # Check duration values are captured (as strings from XML attributes)
        assert list(parser.running_workouts["duration"]) == ["30", "25"]


class TestParseValue:
    """Test cases for the _parse_value static method."""

    # pylint: disable=protected-access
    @pytest.mark.parametrize(
        "input_str, expected_val, expected_unit",
        [
            # --- 1. Boolean Rules (0 or 1 without unit) ---
            ("0", False, None),  # "0" -> False
            ("1", True, None),  # "1" -> True
            ("0.0", False, None),  # "0.0" -> False (mathematically 0)
            ("1.0", True, None),  # "1.0" -> True
            # --- 2. String Rules (Text without unit) ---
            ("Europe/Luxembourg", "Europe/Luxembourg", None),  # Standard string
            ("Running", "Running", None),  # Activity name
            (
                "String with spaces",
                "String with spaces",
                None,
            ),  # String containing spaces but no number at start
            # --- 3. Number without unit (others) ---
            ("2", 2.0, None),  # Integer other than 0/1
            ("123.45", 123.45, None),  # Float
            ("-5", -5.0, None),  # Negative number
            # --- 4. Standard Unit Conversions (unchanged) ---
            ("860 cm", 8.6, "m"),  # cm to meters
            ("10586 cm", 105.86, "m"),  # cm to meters
            ("8500 %", 85.0, "%"),  # Percentage scaling
            ("10 km", 10.0, "km"),  # Unknown unit passthrough
        ],
    )
    def test_parse_value_logic_rules(
        self, input_str: str, expected_val: str, expected_unit: str
    ):
        """
        Tests the routing logic: Booleans, Strings, Numbers, and Unit conversion.
        """
        val, unit = ep.ExportParser._parse_value(input_str)  # type: ignore[misc]
        assert val == expected_val
        assert unit == expected_unit

    def test_parse_value_fahrenheit(self):
        """
        Tests Fahrenheit conversion with float precision.
        """
        val, unit = ep.ExportParser._parse_value("52.0326 degF")  # type: ignore[misc]
        assert unit == "degC"
        assert val == pytest.approx(11.12922, abs=0.0001)  # type: ignore[misc]

    def test_parse_value_zero_with_unit(self):
        """
        Edge case: "0 cm".
        Should NOT be boolean False, but 0.0 meters.
        """
        val, unit = ep.ExportParser._parse_value("0 cm")  # type: ignore[misc]
        assert val == pytest.approx(0.0)  # type: ignore[misc]
        assert val is not False  # Explicit type check (optional but strict)
        assert unit == "m"

    @pytest.mark.parametrize("input_val", [None, ""])
    def test_parse_value_empty(self, input_val: str):
        """Tests handling of empty or None values."""
        val, unit = ep.ExportParser._parse_value(input_val)  # type: ignore[misc]
        assert val is None
        assert unit is None


# pylint: disable=protected-access
class TestExtractActivityType:
    """Test the _extract_activity_type method."""

    def test_extract_activity_type_running(self):
        """Test extracting running activity type."""

        elem = Element(
            "Workout", attrib={"workoutActivityType": "HKWorkoutActivityTypeRunning"}
        )
        parser = ep.ExportParser("dummy.zip")
        result = parser._extract_activity_type(elem)  # type: ignore[misc]
        assert result == "Running"

    def test_extract_activity_type_cycling(self):
        """Test extracting cycling activity type."""

        elem = Element(
            "Workout", attrib={"workoutActivityType": "HKWorkoutActivityTypeCycling"}
        )
        parser = ep.ExportParser("dummy.zip")
        result = parser._extract_activity_type(elem)  # type: ignore[misc]
        assert result == "Cycling"

    def test_extract_activity_type_missing_attribute(self):
        """Test extracting activity type when attribute is missing."""

        elem = Element("Workout")
        parser = ep.ExportParser("dummy.zip")
        result = parser._extract_activity_type(elem)  # type: ignore[misc]
        assert result == ""


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
        parser = ep.ExportParser("dummy.zip")
        record = parser._create_workout_record(elem, "Running")  # type: ignore[misc]

        assert record["activityType"] == "Running"
        assert record.get("duration") == "30"
        assert record.get("startDate") == "2024-01-01 10:00:00"
        assert record.get("endDate") == "2024-01-01 10:30:00"
        assert record.get("source") == "Apple Watch"

    def test_create_workout_record_with_missing_attributes(self):
        """Test creating a workout record with missing attributes."""

        elem = Element(
            "Workout", attrib={"workoutActivityType": "HKWorkoutActivityTypeRunning"}
        )
        parser = ep.ExportParser("dummy.zip")
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
                "sumUnit": "km",
            },
        )
        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_statistics(elem, record)  # type: ignore[misc]

        assert record.get("sumDistanceWalkingRunning") == "5.2"
        assert record.get("sumDistanceWalkingRunningUnit") == "km"

    def test_process_workout_statistics_with_average(self):
        """Test processing workout statistics with average value."""

        elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierHeartRate",
                "average": "150",
                "averageUnit": "count/min",
            },
        )
        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_statistics(elem, record)  # type: ignore[misc]

        assert record.get("averageHeartRate") == "150"
        assert record.get("averageHeartRateUnit") == "count/min"

    def test_process_workout_statistics_with_multiple_values(self):
        """Test processing workout statistics with multiple values."""

        elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierSpeed",
                "minimum": "8.0",
                "minimumUnit": "km/h",
                "maximum": "12.0",
                "maximumUnit": "km/h",
            },
        )
        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_statistics(elem, record)  # type: ignore[misc]

        assert record.get("minimumSpeed") == "8.0"
        assert record.get("minimumSpeedUnit") == "km/h"
        assert record.get("maximumSpeed") == "12.0"
        assert record.get("maximumSpeedUnit") == "km/h"

    def test_process_workout_statistics_with_no_values(self):
        """Test processing workout statistics with no values (all attributes missing)."""

        elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierEnergy",
            },
        )
        parser = ep.ExportParser("dummy.zip")
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
        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem, record)  # type: ignore[misc]

        assert record.get("MetadataKeyTimeZone") == "Europe/Luxembourg"

    def test_process_metadata_entry_with_value_and_unit(self):
        """Test processing metadata entry with value and unit."""

        elem = Element(
            "MetadataEntry",
            attrib={"key": "HKMetadataKeyElevationAscended", "value": "100 m"},
        )
        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem, record)  # type: ignore[misc]

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
        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_metadata_entry(elem, record)  # type: ignore[misc]

        assert record.get("MetadataKeyIsIndoorWorkout") is True


class TestProcessWorkoutChildren:
    """Test the _process_workout_children method."""

    # pylint: disable=protected-access
    def test_process_workout_children_with_statistics(self):
        """Test processing workout with child statistics."""

        parent = Element("Workout")
        stats_elem = Element(
            "WorkoutStatistics",
            attrib={
                "type": "HKQuantityTypeIdentifierDistance",
                "sum": "10.0",
                "sumUnit": "km",
            },
        )
        parent.append(stats_elem)

        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_children(parent, record)  # type: ignore[misc]

        assert record.get("sumDistance") == "10.0"
        assert record.get("sumDistanceUnit") == "km"

    def test_process_workout_children_with_metadata(self):
        """Test processing workout with child metadata entries."""

        parent = Element("Workout")
        metadata_elem = Element(
            "MetadataEntry",
            attrib={"key": "HKMetadataKeyTimeZone", "value": "Europe/Paris"},
        )
        parent.append(metadata_elem)

        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_children(parent, record)  # type: ignore[misc]

        assert record.get("MetadataKeyTimeZone") == "Europe/Paris"

    def test_process_workout_children_mixed(self):
        """Test processing workout with mixed children."""

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

        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_children(parent, record)  # type: ignore[misc]

        assert record.get("sumDistance") == "5.0"
        assert record.get("MetadataKeyTimeZone") == "UTC"

    def test_process_workout_children_with_unknown_element(self):
        """Test processing workout with unknown child element (should be ignored)."""

        parent = Element("Workout")
        unknown_elem = Element("UnknownElement", attrib={"some": "attribute"})
        parent.append(unknown_elem)

        parser = ep.ExportParser("dummy.zip")
        record: ep.WorkoutRecord = {"activityType": "Running"}

        parser._process_workout_children(parent, record)  # type: ignore[misc]

        # Should only have activityType, unknown element should be ignored
        assert record == {"activityType": "Running"}


class TestExportToJson:
    """Test the export_to_json method."""

    def test_export_to_json_creates_file(self, tmp_path: Path) -> None:
        """Test that export_to_json creates a JSON file."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        assert output_file.exists()

        # Verify JSON structure
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            assert "schema" in data
            assert "data" in data
            assert isinstance(data["data"], list)

    def test_export_to_json_filters_null_values(self, tmp_path: Path) -> None:
        """Test that export_to_json filters null values."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            # Verify that all items don't have null values
            for record in data["data"]:
                for value in record.values():
                    assert value is not None

    def test_export_to_json_sorts_by_startdate(self, tmp_path: Path) -> None:
        """Test that export_to_json sorts records by startDate."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-03" endDate="2024-01-03" duration="30"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="25"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-02" endDate="2024-01-02" duration="28"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            start_dates = [record.get("startDate") for record in data["data"]]
            assert start_dates == sorted(start_dates)

    def test_export_to_json_empty_workouts(self, tmp_path: Path) -> None:
        """Test export_to_json with no workouts."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            assert data["data"] == []


class TestExportToCsv:
    """Test the export_to_csv method."""

    def test_export_to_csv_creates_file(self, tmp_path: Path) -> None:
        """Test that export_to_csv creates a CSV file."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.csv"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_csv(str(output_file))

        assert output_file.exists()

        # Verify CSV content
        df = pd.read_csv(output_file)  # type: ignore[misc]
        assert "startDate" in df.columns
        assert "endDate" in df.columns
        assert "duration" in df.columns

    def test_export_to_csv_with_multiple_workouts(self, tmp_path: Path) -> None:
        """Test export_to_csv with multiple workouts."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-02" endDate="2024-01-02" duration="25"/>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.csv"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_csv(str(output_file))

        df = pd.read_csv(output_file)  # type: ignore[misc]
        assert len(df) == 2

    def test_export_to_csv_empty_workouts(self, tmp_path: Path) -> None:
        """Test export_to_csv with no workouts."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.csv"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_csv(str(output_file))

        assert output_file.exists()
        df = pd.read_csv(output_file)  # type: ignore[misc]
        assert len(df) == 0


class TestComplexRealWorldWorkout:
    """Test parsing of a complex real-world Apple Health workout with multiple elements."""

    def test_parse_complex_workout_with_all_elements(self, tmp_path: Path) -> None:
        """Test parsing a complex running workout"""
        zip_path = tmp_path / "complex_export.zip"
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" duration="119.2710362156232" durationUnit="min" sourceName="Apple Watch de Nicolas" sourceVersion="26.2" device="&lt;&lt;HKDevice: 0xc936a3f60&gt;, name:Apple Watch, manufacturer:Apple Inc., model:Watch, hardware:Watch7,2, software:26.2, creation date:2025-12-13 12:48:57 +0000&gt;" creationDate="2025-12-20 14:51:19 +0100" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100">
        <MetadataEntry key="HKIndoorWorkout" value="0"/>
        <MetadataEntry key="HKTimeZone" value="Europe/Paris"/>
        <MetadataEntry key="HKWeatherHumidity" value="9400 %"/>
        <MetadataEntry key="HKWeatherTemperature" value="47.6418 degF"/>
        <MetadataEntry key="HKAverageMETs" value="9.66668 kcal/hr·kg"/>
        <WorkoutEvent type="HKWorkoutEventTypeSegment" date="2025-12-20 12:51:00 +0100" duration="8.048923822244008" durationUnit="min"/>
        <WorkoutEvent type="HKWorkoutEventTypeSegment" date="2025-12-20 12:51:00 +0100" duration="11.98028505643209" durationUnit="min"/>
        <WorkoutActivity uuid="936B9E1D-52B9-41CA-BCA9-9654D43F004E" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" duration="119.2710362156232" durationUnit="min">
            <WorkoutEvent type="HKWorkoutEventTypeSegment" date="2025-12-20 12:51:00 +0100" duration="8.048923822244008" durationUnit="min"/>
            <WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="17599" unit="count"/>
            <MetadataEntry key="WOIntervalStepKeyPath" value="0.0.0"/>
            <MetadataEntry key="HKElevationAscended" value="45443 cm"/>
        </WorkoutActivity>
        <WorkoutActivity uuid="936B9E1D-52B9-41CA-BCA9-9654D43F004E" startDate="2025-12-20 13:51:00 +0100" endDate="2025-12-20 15:50:16 +0100" duration="119.2710362156232" durationUnit="min">
            <WorkoutEvent type="HKWorkoutEventTypeSegment" date="2025-12-20 12:51:00 +0100" duration="8.048923822244008" durationUnit="min"/>
            <WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="17599" unit="count"/>
            <MetadataEntry key="WOIntervalStepKeyPath" value="0.0.0"/>
            <MetadataEntry key="HKElevationAscended" value="10000 cm"/>
        </WorkoutActivity>
        <WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="17599" unit="count"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierRunningGroundContactTime" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="323.718" minimum="224" maximum="369" unit="ms"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierRunningPower" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="222.789" minimum="61" maximum="479" unit="W"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="1389.98" unit="kcal"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="16.1244" unit="km"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="140.139" minimum="75" maximum="157" unit="count/min"/>
        <WorkoutRoute sourceName="Apple Watch de Nicolas" sourceVersion="26.2" creationDate="2025-12-20 14:51:25 +0100" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100">
            <MetadataEntry key="HKMetadataKeySyncVersion" value="2"/>
            <FileReference path="/workout-routes/route_2025-12-20_2.50pm.gpx"/>
        </WorkoutRoute>
    </Workout>
</HealthData>
""".encode("utf-8")
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()

        # Verify the workout was parsed
        assert len(parser.running_workouts) == 1

        # Get the parsed workout record
        workout = parser.running_workouts.iloc[0]

        # Verify basic attributes
        assert workout["activityType"] == "Running"
        assert workout["startDate"] == "2025-12-20 12:51:00 +0100"
        assert workout["endDate"] == "2025-12-20 14:50:16 +0100"
        assert workout["duration"] == "119.2710362156232"
        assert workout["source"] == "Apple Watch de Nicolas"

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
        assert workout["sumStepCount"] == "17599"
        assert workout["averageRunningGroundContactTime"] == "323.718"
        assert workout["minimumRunningGroundContactTime"] == "224"
        assert workout["maximumRunningGroundContactTime"] == "369"
        assert workout["averageRunningPower"] == "222.789"
        assert workout["sumActiveEnergyBurned"] == "1389.98"
        assert workout["sumDistanceWalkingRunning"] == "16.1244"
        assert workout["averageHeartRate"] == "140.139"

        # Verify statistics under WorkoutActivity are captured
        assert workout["ElevationAscended"] == pytest.approx(554.43, abs=0.01)  # type: ignore[misc]

    def test_parse_complex_workout_json_export(self, tmp_path: Path) -> None:
        """Test that complex workout can be exported to JSON correctly."""
        zip_path = tmp_path / "complex_export.zip"
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" duration="119.27" durationUnit="min" sourceName="Apple Watch" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100">
        <MetadataEntry key="HKTimeZone" value="Europe/Paris"/>
        <MetadataEntry key="HKWeatherTemperature" value="15.0 degC"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" sum="16.1244" unit="km"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" average="140.139" unit="count/min"/>
    </Workout>
</HealthData>
""".encode("utf-8")
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        # Verify JSON file was created and is valid
        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            assert "schema" in data
            assert "data" in data
            assert len(data["data"]) == 1

            record = data["data"][0]
            # Verify that metadata and statistics are present
            assert "TimeZone" in record or any("TimeZone" in k for k in record.keys())
            assert record.get("sumDistanceWalkingRunning") == "16.1244"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
