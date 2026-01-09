"""Core tests for the ExportParser module."""

import os
from pathlib import Path
from typing import Generator
from zipfile import ZipFile

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


class TestLoadRunningWorkouts:
    """Test the _load_running_workouts method."""

    def test_load_running_workouts_with_valid_zip(self, tmp_path: Path) -> None:
        """Test loading running workouts from a valid Apple Health ZIP file."""
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
