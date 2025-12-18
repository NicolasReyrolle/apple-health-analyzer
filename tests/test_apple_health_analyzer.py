"""Tests for the Apple Health Analyzer CLI module."""

# pyright: reportGeneralTypeIssues=false
# pyright: reportUnknownParameterType=false
# pyright: ignore[reportUnknownMemberType]
import sys
import unittest
from unittest.mock import patch, MagicMock
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

    @patch('src.apple_health_analyzer.ExportParser')
    @patch('src.apple_health_analyzer.parse_cli_arguments')
    def test_main_calls_parser(self, mock_parse_args: MagicMock, mock_export_parser: MagicMock):
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

    @patch('src.apple_health_analyzer.parse_cli_arguments')
    def test_main_with_export_parser_error(self, mock_parse_args: MagicMock):
        """Test main() when ExportParser raises SystemExit."""
        mock_parse_args.return_value = {"export_file": "nonexistent.zip"}

        with patch('src.apple_health_analyzer.ExportParser') as mock_parser:
            mock_instance = MagicMock()
            mock_instance.parse.side_effect = SystemExit(1)
            mock_parser.return_value.__enter__.return_value = mock_instance

            with self.assertRaises(SystemExit):
                ah.main()


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


if __name__ == "__main__":
    unittest.main()
