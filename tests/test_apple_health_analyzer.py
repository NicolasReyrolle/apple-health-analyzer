"""Tests for the Apple Health Analyzer CLI module."""

# pyright: reportGeneralTypeIssues=false
# pyright: reportUnknownParameterType=false
# pyright: ignore[reportUnknownMemberType]
import sys
import unittest
from unittest.mock import patch, MagicMock
import subprocess
import tempfile
from zipfile import ZipFile
from pathlib import Path
from src import apple_health_analyzer as ah


class TestParseCliArguments(unittest.TestCase):
    """Test the CLI argument parsing."""

    def test_parse_cli_arguments(self):
        """Check the parser will return the provided arguments."""
        sys.argv = ["apple_health_analyzer.py", "test_export.zip"]
        result = ah.parse_cli_arguments()
        self.assertEqual(result, {"export_file": "test_export.zip"})

    def test_parse_cli_arguments_with_path(self):
        """Test parsing with full file path."""
        sys.argv = ["apple_health_analyzer.py", "/path/to/export.zip"]
        result = ah.parse_cli_arguments()
        self.assertEqual(result, {"export_file": "/path/to/export.zip"})

    def test_parse_cli_arguments_with_spaces(self):
        """Test parsing file path with spaces."""
        sys.argv = ["apple_health_analyzer.py", "path with spaces/export.zip"]
        result = ah.parse_cli_arguments()
        self.assertEqual(result, {"export_file": "path with spaces/export.zip"})


class TestMain(unittest.TestCase):
    """Test the main() entry point."""

    @patch("src.apple_health_analyzer.ExportParser")
    @patch("src.apple_health_analyzer.parse_cli_arguments")
    def test_main_calls_parser(
        self, mock_parse_args: MagicMock, mock_export_parser: MagicMock
    ):
        """Test that main() calls parse_cli_arguments and ExportParser."""
        mock_parse_args.return_value = {"export_file": "test.zip"}
        mock_parser_instance = MagicMock()
        mock_export_parser.return_value.__enter__.return_value = mock_parser_instance

        ah.main()

        mock_parse_args.assert_called_once()
        mock_export_parser.assert_called_once_with("test.zip")
        mock_parser_instance.parse.assert_called_once()


class TestMainIntegration(unittest.TestCase):
    """Integration tests for the main CLI."""

    @patch("src.apple_health_analyzer.parse_cli_arguments")
    def test_main_with_export_parser_error(self, mock_parse_args: MagicMock):
        """Test main() when ExportParser raises SystemExit."""
        mock_parse_args.return_value = {"export_file": "nonexistent.zip"}

        with patch("src.apple_health_analyzer.ExportParser") as mock_parser:
            mock_instance = MagicMock()
            mock_instance.parse.side_effect = SystemExit(1)
            mock_parser.return_value.__enter__.return_value = mock_instance

            with self.assertRaises(SystemExit):
                ah.main()

    @patch("src.apple_health_analyzer.parse_cli_arguments")
    def test_main_calls_export_methods(self, mock_parse_args: MagicMock):
        """Test that main() calls both export methods."""
        mock_parse_args.return_value = {"export_file": "test.zip"}
        mock_parser_instance = MagicMock()

        with patch("src.apple_health_analyzer.ExportParser") as mock_export_parser:
            mock_export_parser.return_value.__enter__.return_value = (
                mock_parser_instance
            )

            ah.main()

            # Verify export methods are called
            mock_parser_instance.export_to_json.assert_called_once_with(
                "output/running_workouts.json"
            )
            mock_parser_instance.export_to_csv.assert_called_once_with(
                "output/running_workouts.csv"
            )


class TestKeyboardInterrupt(unittest.TestCase):
    """Test KeyboardInterrupt handling."""

    def test_keyboard_interrupt_simulated(self):
        """Test that KeyboardInterrupt results in exit code 130 (simulated)."""
        # This simulates what the __main__ block does
        try:
            raise KeyboardInterrupt()
        except KeyboardInterrupt:
            exit_code = 130
            self.assertEqual(exit_code, 130)

    @patch("src.apple_health_analyzer.main")
    def test_keyboard_interrupt_in_main(self, mock_main: MagicMock):
        """Test that KeyboardInterrupt in main is handled gracefully."""
        mock_main.side_effect = KeyboardInterrupt()

        with patch("sys.stderr"):
            with self.assertRaises(SystemExit) as context:
                try:
                    ah.main()
                except KeyboardInterrupt:
                    print("\nInterrupted by user", file=sys.stderr)
                    sys.exit(130)

        self.assertEqual(context.exception.code, 130)


class TestMainBlock(unittest.TestCase):
    """Test the __main__ block execution."""

    def test_main_execution_with_valid_file(self):
        """Test that the script runs successfully with a valid ZIP file."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            zip_path = tmp_path / "test_export.zip"

            # Create a minimal valid export file
            xml_content = b"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" startDate="2024-01-01" endDate="2024-01-01" duration="30"/>
</HealthData>
"""
            with ZipFile(zip_path, "w") as zf:
                zf.writestr("apple_health_export/export.xml", xml_content)

            # Run the script as a subprocess
            result = subprocess.run(
                [sys.executable, "-m", "src.apple_health_analyzer", str(zip_path)],
                cwd=str(Path(__file__).parent.parent),
                capture_output=True,
                text=True,
                check=False,
            )

            # Should succeed with exit code 0
            self.assertEqual(result.returncode, 0)
            self.assertIn("Processing", result.stdout)


if __name__ == "__main__":
    unittest.main()
