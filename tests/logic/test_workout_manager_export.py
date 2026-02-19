"""Tests for export functionality (JSON and CSV)."""

from datetime import datetime
import json
from io import StringIO
from pathlib import Path
from typing import Optional
from zipfile import ZipFile

import pandas as pd

import logic.export_parser as ep
import logic.workout_manager as wm


def create_test_zip(zip_path: Path, xml_content: bytes) -> None:
    """Helper to create a test ZIP file with XML content."""
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("apple_health_export/export.xml", xml_content)


def parse_and_export_json(zip_path: Path, exclude_columns: Optional[set[str]] = None) -> str:
    """Helper to parse ZIP and export to JSON."""
    parser = ep.ExportParser()
    with parser:
        workouts = wm.WorkoutManager(parser.parse(str(zip_path)))
        return workouts.export_to_json(exclude_columns=exclude_columns)


def parse_and_export_csv(zip_path: Path, exclude_columns: Optional[set[str]] = None) -> str:
    """Helper to parse ZIP and export to CSV."""
    parser = ep.ExportParser()
    with parser:
        workouts = wm.WorkoutManager(parser.parse(str(zip_path)))
        return workouts.export_to_csv(exclude_columns=exclude_columns)


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
        create_test_zip(zip_path, xml_content)
        json_content = StringIO(parse_and_export_json(zip_path))

        # Verify JSON structure
        data = json.load(json_content)
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
        create_test_zip(zip_path, xml_content)
        json_content = StringIO(parse_and_export_json(zip_path))

        data = json.load(json_content)
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
        create_test_zip(zip_path, xml_content)
        json_content = StringIO(parse_and_export_json(zip_path))

        data = json.load(json_content)
        start_dates = [record.get("startDate") for record in data["data"]]
        assert start_dates == sorted(start_dates)

    def test_export_to_json_empty_workouts(self, tmp_path: Path) -> None:
        """Test export_to_json with no workouts."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)
        json_content = StringIO(parse_and_export_json(zip_path))

        assert json_content is not None
        data = json.load(json_content)
        assert data["data"] == []


class TestExportToCsv:
    """Test the export_to_csv method."""

    def test_export_to_csv_has_correct_format(self, tmp_path: Path) -> None:
        """Test that export_to_csv creates a CSV file."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)
        csv_content = StringIO(parse_and_export_csv(zip_path))

        # Verify CSV content
        df = pd.read_csv(csv_content)  # type: ignore[misc]
        assert "startDate" in df.columns
        assert "endDate" in df.columns
        assert "duration" in df.columns
        assert "durationUnit" in df.columns

    def test_export_to_csv_with_multiple_workouts(self, tmp_path: Path) -> None:
        """Test export_to_csv with multiple workouts."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-02" endDate="2024-01-02" duration="25"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)
        csv_content = StringIO(parse_and_export_csv(zip_path))

        df = pd.read_csv(csv_content)  # type: ignore[misc]
        assert len(df) == 2

    def test_export_to_csv_empty_workouts(self, tmp_path: Path) -> None:
        """Test export_to_csv with no workouts."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)
        csv_content = StringIO(parse_and_export_csv(zip_path))

        try:
            df = pd.read_csv(csv_content)  # type: ignore[misc]
            assert len(df) == 0
        except pd.errors.EmptyDataError:
            # Empty DataFrame produces an empty CSV with no data
            pass


class TestColumnExclusion:
    """Test column exclusion behavior in export methods."""

    def test_default_excluded_columns_constant(self) -> None:
        """Test that DEFAULT_EXCLUDED_COLUMNS is defined correctly."""
        assert hasattr(wm.WorkoutManager, "DEFAULT_EXCLUDED_COLUMNS")
        assert wm.WorkoutManager.DEFAULT_EXCLUDED_COLUMNS == {"routeFile", "route"}

    def test_export_to_json_excludes_default_columns(self, tmp_path: Path) -> None:
        """Test that export_to_json excludes routeFile and route by default."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)
        json_content = StringIO(parse_and_export_json(zip_path))

        data = json.load(json_content)
        # Check that routeFile and route are not in the schema columns
        schema_fields = [field["name"] for field in data["schema"]["fields"]]
        assert "routeFile" not in schema_fields
        assert "route" not in schema_fields

    def test_export_to_csv_excludes_default_columns(self, tmp_path: Path) -> None:
        """Test that export_to_csv excludes routeFile and route by default."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        parser = ep.ExportParser()
        with parser:
            parser.parse(str(zip_path))
            csv_content = StringIO(parse_and_export_csv(zip_path))

        df = pd.read_csv(csv_content)  # type: ignore[misc]
        assert "routeFile" not in df.columns
        assert "route" not in df.columns

    def test_export_to_json_empty_exclude_set(self, tmp_path: Path) -> None:
        """Test that export_to_json with empty exclude_columns set includes all columns."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(parse_and_export_json(zip_path, exclude_columns=set()))

        data = json.load(json_content)
        # All columns from running_workouts should be in the output
        schema_fields = [field["name"] for field in data["schema"]["fields"]]
        # activityType is required, duration/startDate/endDate/durationUnit exist
        assert "activityType" in schema_fields

    def test_export_to_csv_empty_exclude_set(self, tmp_path: Path) -> None:
        """Test that export_to_csv with empty exclude_columns set includes all columns."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        csv_content = StringIO(parse_and_export_csv(zip_path, exclude_columns=set()))

        df = pd.read_csv(csv_content)  # type: ignore[misc]
        # Should have at least the standard columns
        assert "startDate" in df.columns
        assert "endDate" in df.columns
        assert "duration" in df.columns

    def test_export_to_json_custom_exclude_columns(self, tmp_path: Path) -> None:
        """Test export_to_json with custom exclude_columns set."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(
            parse_and_export_json(zip_path, exclude_columns={"duration", "durationUnit"})
        )

        data = json.load(json_content)
        schema_fields = [field["name"] for field in data["schema"]["fields"]]
        # These should be excluded
        assert "duration" not in schema_fields
        assert "durationUnit" not in schema_fields
        # These should still be present
        assert "startDate" in schema_fields
        assert "endDate" in schema_fields

    def test_export_to_csv_custom_exclude_columns(self, tmp_path: Path) -> None:
        """Test export_to_csv with custom exclude_columns set."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        csv_content = StringIO(parse_and_export_csv(zip_path, exclude_columns={"startDate"}))

        df = pd.read_csv(csv_content)  # type: ignore[misc]
        assert "startDate" not in df.columns
        # These should still be present
        assert "endDate" in df.columns
        assert "duration" in df.columns

    def test_export_to_json_exclude_nonexistent_column(self, tmp_path: Path) -> None:
        """Test that excluding a non-existent column doesn't raise an error."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(
            parse_and_export_json(zip_path, exclude_columns={"nonexistent_column"})
        )
        data = json.load(json_content)
        assert "data" in data

    def test_export_to_csv_exclude_nonexistent_column(self, tmp_path: Path) -> None:
        """Test that excluding a non-existent column doesn't raise an error in CSV."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        csv_content = StringIO(
            parse_and_export_csv(zip_path, exclude_columns={"nonexistent_column"})
        )

        df = pd.read_csv(csv_content)  # type: ignore[misc]
        assert len(df) > 0


class TestDataTypeConversion:
    """Test data type conversions during parsing and export."""

    def test_indoor_workout_field_exported_as_boolean_json(self, tmp_path: Path) -> None:
        """Test that IndoorWorkout field (0 or 1) is exported as boolean in JSON."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <MetadataEntry key="HKIndoorWorkout" value="1"/>
    </Workout>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-02" endDate="2024-01-02" duration="25">
        <MetadataEntry key="HKIndoorWorkout" value="0"/>
    </Workout>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(parse_and_export_json(zip_path))

        data = json.load(json_content)
        # Verify that IndoorWorkout values are boolean (true/false), not floats
        for record in data["data"]:
            if "IndoorWorkout" in record:
                value = record["IndoorWorkout"]
                assert isinstance(
                    value, bool
                ), f"IndoorWorkout should be boolean, got {type(value).__name__}"
                assert value in [True, False]

    def test_indoor_workout_field_exported_as_boolean_csv(self, tmp_path: Path) -> None:
        """Test that IndoorWorkout field (0 or 1) is exported as boolean in CSV."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <MetadataEntry key="HKIndoorWorkout" value="1"/>
    </Workout>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-02" endDate="2024-01-02" duration="25">
        <MetadataEntry key="HKIndoorWorkout" value="0"/>
    </Workout>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        csv_content = StringIO(parse_and_export_csv(zip_path))

        df = pd.read_csv(csv_content)  # type: ignore[misc]
        # Check that IndoorWorkout column exists and contains boolean values (True/False)
        assert "IndoorWorkout" in df.columns, "IndoorWorkout column not found in CSV"
        values = df["IndoorWorkout"].dropna()
        # CSV exports booleans as True/False (not as floats like 0.0 or 1.0)
        for val in values:
            # In CSV, pandas represents booleans as 1 (True) or 0 (False) when read
            assert val in [
                True,
                False,
                1,
                0,
            ], f"IndoorWorkout should be boolean (1 or 0), got {val} of type {type(val).__name__}"
            # Ensure no float values like 1.0 or 0.0
            assert not (
                isinstance(val, float) and val in [0.0, 1.0]
            ), f"IndoorWorkout should not be float (0.0 or 1.0), got {val}"

    def test_zero_value_without_unit_becomes_boolean_false(self, tmp_path: Path) -> None:
        """Test that value '0' without unit is converted to boolean False."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <MetadataEntry key="HKIndoorWorkout" value="0"/>
    </Workout>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(parse_and_export_json(zip_path))

        data = json.load(json_content)
        assert len(data["data"]) == 1
        record = data["data"][0]
        assert "IndoorWorkout" in record
        assert record["IndoorWorkout"] is False

    def test_one_value_without_unit_becomes_boolean_true(self, tmp_path: Path) -> None:
        """Test that value '1' without unit is converted to boolean True."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <MetadataEntry key="HKIndoorWorkout" value="1"/>
    </Workout>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(parse_and_export_json(zip_path))

        data = json.load(json_content)
        assert len(data["data"]) == 1
        record = data["data"][0]
        assert "IndoorWorkout" in record
        assert record["IndoorWorkout"] is True

    def test_numeric_values_without_unit_stay_float(self, tmp_path: Path) -> None:
        """Test that numeric values other than 0/1 stay as float, not boolean."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <MetadataEntry key="HKTestValue" value="42"/>
    </Workout>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(parse_and_export_json(zip_path))

        data = json.load(json_content)
        assert len(data["data"]) == 1
        record = data["data"][0]
        assert "TestValue" in record
        # Should be float, not boolean
        assert isinstance(record["TestValue"], (int, float))
        assert record["TestValue"] == 42

    def test_indoor_workout_never_exported_as_float(self, tmp_path: Path) -> None:
        """Test that IndoorWorkout is NEVER exported as 0.0 or 1.0 (float)
        even with multiple entries."""
        zip_path = tmp_path / "test_export.zip"
        # Also includes multiple MetadataEntry elements with same key to trigger aggregation logic
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <MetadataEntry key="HKIndoorWorkout" value="0"/>
    </Workout>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-02" endDate="2024-01-02" duration="25">
        <MetadataEntry key="HKIndoorWorkout" value="1"/>
        <MetadataEntry key="HKIndoorWorkout" value="1"/>
    </Workout>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(parse_and_export_json(zip_path))

        data = json.load(json_content)
        for record in data["data"]:
            if "IndoorWorkout" in record:
                value = record["IndoorWorkout"]
                # Must be boolean True or False, not float 0.0 or 1.0
                assert isinstance(
                    value, bool
                ), f"IndoorWorkout must be boolean, got {type(value).__name__}: {value}"
                assert value in [True, False]
                # Explicitly reject floats
                assert not isinstance(value, float), f"IndoorWorkout must not be float, got {value}"


class TestStartDateTimezoneHandling:
    """Test that startDate timezone handling doesn't break JSON export.

    Regression test for: AttributeError: 'datetime.timezone' object has no attribute 'zone'
    This occurs when startDate is parsed as timezone-aware and pandas tries to build JSON schema.
    """

    def test_export_to_json_with_timezone_aware_startdate(self, tmp_path: Path) -> None:
        """Test that export_to_json works with startDate timestamps that may have timezone info.

        This test ensures that when startDate is converted to a timestamp or datetime with
        timezone information, the pandas JSON export still works without AttributeError.
        """
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01 10:30:45 +0100" endDate="2024-01-01 11:00:00 +0100" duration="30"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-02 14:15:30 +0100" endDate="2024-01-02 14:45:30 +0100" duration="30"/>
</HealthData>
"""
        create_test_zip(zip_path, xml_content)

        json_content = StringIO(parse_and_export_json(zip_path))

        # Verify JSON is valid and contains the workouts
        data = json.load(json_content)
        assert "schema" in data
        assert "data" in data
        assert len(data["data"]) == 2


class TestExportToCsvActivityFilter:
    """Test the export_to_csv method with activity type filtering."""

    def test_export_to_csv_all_activities(self) -> None:
        """Test export_to_csv with activity_type='All' exports all workouts."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Walking", "Cycling", "Running"],
                    "duration": [30, 20, 45, 25],
                    "startDate": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                }
            )
        )

        csv_output = workouts.export_to_csv(activity_type="All")

        lines = csv_output.strip().split("\n")
        # Header + 4 data rows
        assert len(lines) == 5
        # Verify all activity types are present
        assert "Running" in csv_output
        assert "Walking" in csv_output
        assert "Cycling" in csv_output

    def test_export_to_csv_filter_running(self) -> None:
        """Test export_to_csv filters to only Running activities."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Walking", "Cycling", "Running"],
                    "duration": [30, 20, 45, 25],
                    "startDate": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                }
            )
        )

        csv_output = workouts.export_to_csv(activity_type="Running")

        lines = csv_output.strip().split("\n")
        # Header + 2 Running rows
        assert len(lines) == 3
        # Verify only Running activities are present
        assert "Running" in csv_output
        assert "Walking" not in csv_output
        assert "Cycling" not in csv_output

    def test_export_to_csv_filter_walking(self) -> None:
        """Test export_to_csv filters to only Walking activities."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Walking", "Cycling", "Running"],
                    "duration": [30, 20, 45, 25],
                    "startDate": ["2024-01-01", "2024-01-02", "2024-01-03", "2024-01-04"],
                }
            )
        )

        csv_output = workouts.export_to_csv(activity_type="Walking")

        lines = csv_output.strip().split("\n")
        # Header + 1 Walking row
        assert len(lines) == 2
        # Verify only Walking is present
        assert "Walking" in csv_output
        assert "Running" not in csv_output
        assert "Cycling" not in csv_output

    def test_export_to_csv_filter_no_match(self) -> None:
        """Test export_to_csv when activity type doesn't exist."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Walking"],
                    "duration": [30, 20],
                    "startDate": ["2024-01-01", "2024-01-02"],
                }
            )
        )

        csv_output = workouts.export_to_csv(activity_type="Swimming")

        lines = csv_output.strip().split("\n")
        # Only header row (empty result)
        assert len(lines) == 1

    def test_export_to_csv_filter_with_excluded_columns(self) -> None:
        """Test export_to_csv filters both by activity type and excluded columns."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Walking", "Running"],
                    "duration": [30, 20, 25],
                    "routeFile": ["route1", "route2", "route3"],
                    "startDate": ["2024-01-01", "2024-01-02", "2024-01-03"],
                }
            )
        )

        csv_output = workouts.export_to_csv(activity_type="Running", exclude_columns={"routeFile"})

        lines = csv_output.strip().split("\n")
        # Header + 2 Running rows
        assert len(lines) == 3
        # Verify routeFile is not in output
        assert "routeFile" not in csv_output
        # Verify Running activities are present
        assert csv_output.count("Running") == 2


class TestExportWithActivityAndDateFilters:
    """Test export methods with combined activity and date range filters."""

    def test_export_to_json_with_activity_and_date_filters(self) -> None:
        """JSON export should include only workouts matching both activity and date filters."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling", "Running"],
                    "duration": [30, 45, 60, 25],
                    "startDate": pd.to_datetime(
                        [
                            "2024-01-10 08:00:00",
                            "2024-02-10 09:00:00",
                            "2024-02-12 10:00:00",
                            "2024-03-05 07:30:00",
                        ]
                    ),
                }
            )
        )

        json_output = workouts.export_to_json(
            activity_type="Running",
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 2, 29),
        )

        payload = json.loads(json_output)
        assert "data" in payload
        assert len(payload["data"]) == 1
        assert payload["data"][0]["activityType"] == "Running"

    def test_export_to_csv_with_activity_and_date_filters(self) -> None:
        """CSV export should include only workouts matching both activity and date filters."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling", "Running"],
                    "duration": [30, 45, 60, 25],
                    "startDate": pd.to_datetime(
                        [
                            "2024-01-10 08:00:00",
                            "2024-02-10 09:00:00",
                            "2024-02-12 10:00:00",
                            "2024-03-05 07:30:00",
                        ]
                    ),
                }
            )
        )

        csv_output = workouts.export_to_csv(
            activity_type="Running",
            start_date=datetime(2024, 2, 1),
            end_date=datetime(2024, 2, 29),
        )

        csv_df = pd.read_csv(StringIO(csv_output))  # type: ignore[misc]
        assert len(csv_df) == 1
        assert set(csv_df["activityType"].tolist()) == {"Running"}
