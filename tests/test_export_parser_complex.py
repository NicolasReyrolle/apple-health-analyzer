"""Tests for complex workout parsing and route handling."""

from pathlib import Path
from unittest.mock import MagicMock, patch
from xml.etree.ElementTree import Element
from zipfile import ZipFile

import pandas as pd
import pytest
from _pytest.capture import CaptureFixture

from apple_health_analyzer import main as ah_main
from export_parser import ExportParser, WorkoutRecord


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

        parser = ExportParser(str(zip_path))
        with parser:
            parser.parse()

        # Verify the workout was parsed
        assert len(parser.running_workouts) == 1

        # Get the parsed workout record
        workout = parser.running_workouts.iloc[0]

        # Verify basic attributes
        assert workout["activityType"] == "Running"
        assert workout["startDate"] == pd.Timestamp('2025-12-20 12:51:00')
        assert workout["endDate"] == "2025-12-20 14:50:16 +0100"
        assert workout["duration"] == 7156
        assert workout["durationUnit"] == "seconds"
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
        assert workout["sumStepCount"] == 17599
        assert workout["averageRunningGroundContactTime"] == pytest.approx(  # type: ignore[misc]
            323.718
        )
        assert workout["minimumRunningGroundContactTime"] == 224
        assert workout["maximumRunningGroundContactTime"] == 369
        assert workout["averageRunningPower"] == pytest.approx(222.789)  # type: ignore[misc]
        assert workout["sumActiveEnergyBurned"] == pytest.approx(1389.98)  # type: ignore[misc]
        assert workout["sumDistanceWalkingRunning"] == pytest.approx(16.1244)  # type: ignore[misc]
        assert workout["averageHeartRate"] == pytest.approx(140.139)  # type: ignore[misc]

        # Verify statistics under WorkoutActivity are captured
        assert workout["ElevationAscended"] == pytest.approx(554.43, abs=0.01)  # type: ignore[misc]

        # Verify the routeFile is captured
        assert workout["routeFile"] == "/workout-routes/route_2025-12-20_2.50pm.gpx"


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
            zf.writestr(
                "apple_health_export/workout-routes/test_route.gpx", gpx_content
            )

        parser = ExportParser(str(zip_path))
        with ZipFile(zip_path, "r") as zf:
            result = parser._load_route(zf, "/workout-routes/test_route.gpx")  # type: ignore[misc]

        assert result is not None
        assert len(result) == 2
        assert list(result.columns) == ["time", "latitude", "longitude", "altitude"]
        assert result.iloc[0]["latitude"] == pytest.approx(48.8566)  # type: ignore[misc]
        assert result.iloc[0]["longitude"] == pytest.approx(2.3522)  # type: ignore[misc]
        assert result.iloc[0]["altitude"] == pytest.approx(100.5)  # type: ignore[misc]

    def test_load_route_missing_file(
        self, tmp_path: Path, capsys: CaptureFixture[str]
    ) -> None:
        """Test loading a route file that doesn't exist in the zip."""
        zip_path = tmp_path / "route_export.zip"
        xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
</HealthData>
"""
        with ZipFile(zip_path, "w") as zf:
            zf.writestr("apple_health_export/export.xml", xml_content)

        parser = ExportParser(str(zip_path))
        with ZipFile(zip_path, "r") as zf:
            result = parser._load_route(zf, "/workout-routes/nonexistent.gpx")  # type: ignore[misc]

        assert result is None
        captured = capsys.readouterr()
        assert "Route file not found in export" in captured.out

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
            zf.writestr(
                "apple_health_export/workout-routes/empty_route.gpx", gpx_content
            )

        parser = ExportParser(str(zip_path))
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
            zf.writestr(
                "apple_health_export/workout-routes/incomplete_route.gpx", gpx_content
            )

        parser = ExportParser(str(zip_path))
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
            zf.writestr(
                "apple_health_export/workout-routes/test_route.gpx", gpx_content
            )

        # Create a route element with FileReference child
        route_elem = Element("WorkoutRoute")
        file_ref = Element(
            "FileReference", attrib={"path": "/workout-routes/test_route.gpx"}
        )
        route_elem.append(file_ref)

        parser = ExportParser(str(zip_path))
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

        parser = ExportParser(str(zip_path))
        record: WorkoutRecord = {"activityType": "Running"}

        with ZipFile(zip_path, "r") as zf:
            parser._process_workout_route(route_elem, record, zf)  # type: ignore[misc]

        # Record should remain unchanged if no FileReference
        assert record == {"activityType": "Running"}


class TestMainErrorHandling:
    """Test error handling in the main() entry point."""

    @patch("apple_health_analyzer.ExportParser")
    @patch("apple_health_analyzer.parse_cli_arguments")
    def test_main_with_system_exit_from_parser(
        self, mock_parse_args: MagicMock, mock_export_parser: MagicMock
    ) -> None:
        """Test that main() propagates SystemExit from ExportParser."""
        mock_parse_args.return_value = {"export_file": "nonexistent.zip"}
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.side_effect = SystemExit(1)
        mock_export_parser.return_value.__enter__.return_value = mock_parser_instance

        with pytest.raises(SystemExit) as exc_info:
            ah_main()
        assert exc_info.value.code == 1

    @patch("apple_health_analyzer.ExportParser")
    @patch("apple_health_analyzer.parse_cli_arguments")
    def test_main_with_file_not_found_error(
        self, mock_parse_args: MagicMock, mock_export_parser: MagicMock
    ) -> None:
        """Test that main() handles FileNotFoundError from parse()."""
        mock_parse_args.return_value = {"export_file": "nonexistent.zip"}
        mock_parser_instance = MagicMock()
        mock_parser_instance.parse.side_effect = FileNotFoundError("File not found")
        mock_export_parser.return_value.__enter__.return_value = mock_parser_instance

        with pytest.raises(FileNotFoundError):
            ah_main()

    @patch("apple_health_analyzer.ExportParser")
    @patch("apple_health_analyzer.parse_cli_arguments")
    def test_main_export_methods_called_on_success(
        self, mock_parse_args: MagicMock, mock_export_parser: MagicMock
    ) -> None:
        """Test that both export methods are called on successful parse."""
        mock_parse_args.return_value = {"export_file": "test.zip"}
        mock_parser_instance = MagicMock()
        mock_export_parser.return_value.__enter__.return_value = mock_parser_instance

        ah_main()

        # Verify both export methods are called
        mock_parser_instance.parse.assert_called_once()
        mock_parser_instance.export_to_json.assert_called_once_with(
            "output/running_workouts.json"
        )
        mock_parser_instance.export_to_csv.assert_called_once_with(
            "output/running_workouts.csv"
        )

    @patch("apple_health_analyzer.ExportParser")
    @patch("apple_health_analyzer.parse_cli_arguments")
    def test_main_uses_context_manager(
        self, mock_parse_args: MagicMock, mock_export_parser: MagicMock
    ) -> None:
        """Test that main() properly uses ExportParser as context manager."""
        mock_parse_args.return_value = {"export_file": "test.zip"}
        mock_parser_instance = MagicMock()
        mock_export_parser.return_value.__enter__.return_value = mock_parser_instance
        mock_export_parser.return_value.__exit__.return_value = None

        ah_main()

        # Verify context manager is used
        mock_export_parser.return_value.__enter__.assert_called_once()
        mock_export_parser.return_value.__exit__.assert_called_once()
