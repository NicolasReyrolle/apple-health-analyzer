"""Tests for export functionality (JSON and CSV)."""

import json
from pathlib import Path
from zipfile import ZipFile

import pandas as pd

from src import export_parser as ep


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
        try:
            df = pd.read_csv(output_file)  # type: ignore[misc]
            assert len(df) == 0
        except pd.errors.EmptyDataError:
            # Empty DataFrame produces an empty CSV with no data
            pass


class TestColumnExclusion:
    """Test column exclusion behavior in export methods."""

    def test_default_excluded_columns_constant(self) -> None:
        """Test that DEFAULT_EXCLUDED_COLUMNS is defined correctly."""
        assert hasattr(ep.ExportParser, "DEFAULT_EXCLUDED_COLUMNS")
        assert ep.ExportParser.DEFAULT_EXCLUDED_COLUMNS == {"routeFile", "route"}

    def test_export_to_json_excludes_default_columns(self, tmp_path: Path) -> None:
        """Test that export_to_json excludes routeFile and route by default."""
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.csv"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_csv(str(output_file))

        df = pd.read_csv(output_file)  # type: ignore[misc]
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            # Export with empty exclude set to include all columns
            parser.export_to_json(str(output_file), exclude_columns=set())

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.csv"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            # Export with empty exclude set to include all columns
            parser.export_to_csv(str(output_file), exclude_columns=set())

        df = pd.read_csv(output_file)  # type: ignore[misc]
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            # Exclude custom columns: duration and durationUnit
            parser.export_to_json(
                str(output_file), exclude_columns={"duration", "durationUnit"}
            )

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.csv"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            # Exclude custom columns: startDate
            parser.export_to_csv(str(output_file), exclude_columns={"startDate"})

        df = pd.read_csv(output_file)  # type: ignore[misc]
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            # Exclude a column that doesn't exist
            parser.export_to_json(
                str(output_file), exclude_columns={"nonexistent_column"}
            )

        assert output_file.exists()
        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            assert "data" in data

    def test_export_to_csv_exclude_nonexistent_column(self, tmp_path: Path) -> None:
        """Test that excluding a non-existent column doesn't raise an error in CSV."""
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
            # Exclude a column that doesn't exist
            parser.export_to_csv(
                str(output_file), exclude_columns={"nonexistent_column"}
            )

        assert output_file.exists()
        df = pd.read_csv(output_file)  # type: ignore[misc]
        assert len(df) > 0


class TestDataTypeConversion:
    """Test data type conversions during parsing and export."""

    def test_indoor_workout_field_exported_as_boolean_json(
        self, tmp_path: Path
    ) -> None:
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            # Verify that IndoorWorkout values are boolean (true/false), not floats
            for record in data["data"]:
                if "IndoorWorkout" in record:
                    value = record["IndoorWorkout"]
                    assert isinstance(value, bool), (
                        f"IndoorWorkout should be boolean, got {type(value).__name__}"
                    )
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.csv"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_csv(str(output_file))

        df = pd.read_csv(output_file)  # type: ignore[misc]
        # Check that IndoorWorkout column exists and contains boolean values (True/False)
        assert "IndoorWorkout" in df.columns, "IndoorWorkout column not found in CSV"
        values = df["IndoorWorkout"].dropna()
        # CSV exports booleans as True/False (not as floats like 0.0 or 1.0)
        for val in values:
            # In CSV, pandas represents booleans as 1 (True) or 0 (False) when read
            assert val in [True, False, 1, 0], (
                f"IndoorWorkout should be boolean (1 or 0), got {val} of type {type(val).__name__}"
            )
            # Ensure no float values like 1.0 or 0.0
            assert not (isinstance(val, float) and val in [0.0, 1.0]), (
                f"IndoorWorkout should not be float (0.0 or 1.0), got {val}"
            )

    def test_zero_value_without_unit_becomes_boolean_false(
        self, tmp_path: Path
    ) -> None:
        """Test that value '0' without unit is converted to boolean False."""
        zip_path = tmp_path / "test_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30">
        <MetadataEntry key="HKIndoorWorkout" value="0"/>
    </Workout>
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            assert len(data["data"]) == 1
            record = data["data"][0]
            assert "TestValue" in record
            # Should be float, not boolean
            assert isinstance(record["TestValue"], (int, float))
            assert record["TestValue"] == 42

    def test_indoor_workout_never_exported_as_float(self, tmp_path: Path) -> None:
        """Test that IndoorWorkout is NEVER exported as 0.0 or 1.0 (float) even with multiple entries."""
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
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        output_file = tmp_path / "output.json"
        parser = ep.ExportParser(str(zip_path))
        with parser:
            parser.parse()
            parser.export_to_json(str(output_file))

        with open(output_file, encoding="utf-8") as f:
            data = json.load(f)
            for record in data["data"]:
                if "IndoorWorkout" in record:
                    value = record["IndoorWorkout"]
                    # Must be boolean True or False, not float 0.0 or 1.0
                    assert isinstance(value, bool), (
                        f"IndoorWorkout must be boolean, got {type(value).__name__}: {value}"
                    )
                    assert value in [True, False]
                    # Explicitly reject floats
                    assert not isinstance(value, float), (
                        f"IndoorWorkout must not be float, got {value}"
                    )
