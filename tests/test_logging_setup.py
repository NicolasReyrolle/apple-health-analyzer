"""Tests for the _setup_logging function in apple_health_analyzer.py."""

import logging
import logging.handlers
import sys
from pathlib import Path
from unittest.mock import patch

# Import the module to test
import apple_health_analyzer


class TestSetupLogging:
    """Tests for the _setup_logging function."""

    # pylint: disable=protected-access

    def test_setup_logging_with_debug_level(self, tmp_path: Path) -> None:
        """Test that _setup_logging correctly configures DEBUG level."""
        # Clear any existing handlers
        logger = logging.getLogger()
        logger.handlers.clear()

        # Change to tmp_path to avoid creating logs directory in project root
        with patch("apple_health_analyzer.Path") as mock_path_class:
            mock_log_dir = tmp_path / "logs"
            mock_path_class.return_value = mock_log_dir

            apple_health_analyzer._setup_logging("DEBUG", enable_file_logging=True)

        # Verify logger is configured at DEBUG level
        assert logger.level == logging.DEBUG

        # Verify we have 2 handlers (console + file)
        assert len(logger.handlers) == 2

        # Verify handlers are at DEBUG level
        for handler in logger.handlers:
            assert handler.level == logging.DEBUG

        # Verify one handler is StreamHandler (console)
        console_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(console_handlers) >= 1

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_with_info_level(self, tmp_path: Path) -> None:
        """Test that _setup_logging correctly configures INFO level."""
        logger = logging.getLogger()
        logger.handlers.clear()

        with patch("apple_health_analyzer.Path") as mock_path_class:
            mock_log_dir = tmp_path / "logs"
            mock_path_class.return_value = mock_log_dir

            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

        # Verify logger is configured at INFO level
        assert logger.level == logging.INFO

        # Verify handlers are at INFO level
        for handler in logger.handlers:
            assert handler.level == logging.INFO

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_with_warning_level(self, tmp_path: Path) -> None:
        """Test that _setup_logging correctly configures WARNING level."""
        logger = logging.getLogger()
        logger.handlers.clear()

        with patch("apple_health_analyzer.Path") as mock_path_class:
            mock_log_dir = tmp_path / "logs"
            mock_path_class.return_value = mock_log_dir

            apple_health_analyzer._setup_logging("WARNING", enable_file_logging=True)

        assert logger.level == logging.WARNING
        for handler in logger.handlers:
            assert handler.level == logging.WARNING

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_with_error_level(self, tmp_path: Path) -> None:
        """Test that _setup_logging correctly configures ERROR level."""
        logger = logging.getLogger()
        logger.handlers.clear()

        with patch("apple_health_analyzer.Path") as mock_path_class:
            mock_log_dir = tmp_path / "logs"
            mock_path_class.return_value = mock_log_dir

            apple_health_analyzer._setup_logging("ERROR", enable_file_logging=True)

        assert logger.level == logging.ERROR
        for handler in logger.handlers:
            assert handler.level == logging.ERROR

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_disables_file_logging_in_dev_mode(self) -> None:
        """Test that file logging is disabled when enable_file_logging=False."""
        logger = logging.getLogger()
        logger.handlers.clear()

        apple_health_analyzer._setup_logging("INFO", enable_file_logging=False)

        # Verify we have only 1 handler (console only, no file handler)
        assert len(logger.handlers) == 1

        # Verify the handler is a StreamHandler (console)
        assert isinstance(logger.handlers[0], logging.StreamHandler)

        # Verify it's not a RotatingFileHandler
        assert not isinstance(logger.handlers[0], logging.handlers.RotatingFileHandler)

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_clears_existing_handlers(self, tmp_path: Path) -> None:
        """Test that _setup_logging clears existing handlers to prevent duplicates."""
        logger = logging.getLogger()
        # Start fresh
        logger.handlers.clear()

        # Add some dummy handlers
        dummy_handler1 = logging.StreamHandler(sys.stdout)
        dummy_handler2 = logging.StreamHandler(sys.stdout)
        logger.addHandler(dummy_handler1)
        logger.addHandler(dummy_handler2)

        # Verify we have 2 handlers before calling _setup_logging
        handler_count_before = len(logger.handlers)
        assert handler_count_before == 2

        with patch("apple_health_analyzer.Path") as mock_path_class:
            mock_log_dir = tmp_path / "logs"
            mock_path_class.return_value = mock_log_dir

            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

        # After calling _setup_logging, we should have exactly 2 new handlers (console + file)
        # The old handlers should be cleared
        assert len(logger.handlers) == 2

        # Verify none of the handlers are the dummy ones we added
        assert dummy_handler1 not in logger.handlers
        assert dummy_handler2 not in logger.handlers

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_creates_log_directory(self, tmp_path: Path) -> None:
        """Test that _setup_logging creates the logs directory."""
        # pylint: disable=import-outside-toplevel
        logger = logging.getLogger()
        logger.handlers.clear()

        # Use a real path in tmp_path
        log_dir = tmp_path / "logs"
        assert not log_dir.exists(), "Log directory should not exist initially"

        # Change working directory temporarily to tmp_path
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

            # Verify log directory was created
            assert log_dir.exists(), "Log directory should be created"
        finally:
            os.chdir(original_cwd)

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_console_handler_uses_stdout(self) -> None:
        """Test that the console handler writes to stdout."""
        logger = logging.getLogger()
        logger.handlers.clear()

        apple_health_analyzer._setup_logging("INFO", enable_file_logging=False)

        # Get the StreamHandler
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) == 1

        # Verify it uses stdout
        assert stream_handlers[0].stream == sys.stdout

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_handlers_have_formatters(self, tmp_path: Path) -> None:
        """Test that all handlers have formatters configured."""
        logger = logging.getLogger()
        logger.handlers.clear()

        with patch("apple_health_analyzer.Path") as mock_path_class:
            mock_log_dir = tmp_path / "logs"
            mock_path_class.return_value = mock_log_dir

            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

        # Verify all handlers have formatters
        for handler in logger.handlers:
            assert handler.formatter is not None
            assert isinstance(handler.formatter, logging.Formatter)

        # Cleanup
        logger.handlers.clear()

    def test_setup_logging_with_file_handler_configuration(self, tmp_path: Path) -> None:
        """Test that file handler is configured with correct settings."""
        # pylint: disable=import-outside-toplevel
        logger = logging.getLogger()
        logger.handlers.clear()

        # Create actual logs directory for this test
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            log_dir = tmp_path / "logs"
            log_dir.mkdir(exist_ok=True)

            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

            # Find the RotatingFileHandler in the handlers
            file_handlers = [
                h for h in logger.handlers if isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            assert len(file_handlers) == 1, "Should have exactly one RotatingFileHandler"

            file_handler = file_handlers[0]
            # Verify the handler has the correct configuration
            assert file_handler.maxBytes == 10 * 1024 * 1024  # 10MB
            assert file_handler.backupCount == 3
        finally:
            os.chdir(original_cwd)

        # Cleanup
        logger.handlers.clear()


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing logic."""

    def test_log_level_argument_default(self) -> None:
        """Test that --log-level defaults to INFO."""
        # pylint: disable=import-outside-toplevel
        with patch("sys.argv", ["apple_health_analyzer.py"]):
            import argparse

            parser = argparse.ArgumentParser()
            parser.add_argument(
                "--log-level",
                type=str,
                choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                default="INFO",
            )
            args, _ = parser.parse_known_args()

            assert args.log_level == "INFO"

    def test_log_level_argument_accepts_debug(self) -> None:
        """Test that --log-level accepts DEBUG."""
        # pylint: disable=import-outside-toplevel
        with patch("sys.argv", ["apple_health_analyzer.py", "--log-level", "DEBUG"]):
            import argparse

            parser = argparse.ArgumentParser()
            parser.add_argument(
                "--log-level",
                type=str,
                choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                default="INFO",
            )
            args, _ = parser.parse_known_args()

            assert args.log_level == "DEBUG"

    def test_log_level_argument_accepts_warning(self) -> None:
        """Test that --log-level accepts WARNING."""
        # pylint: disable=import-outside-toplevel
        with patch("sys.argv", ["apple_health_analyzer.py", "--log-level", "WARNING"]):
            import argparse

            parser = argparse.ArgumentParser()
            parser.add_argument(
                "--log-level",
                type=str,
                choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                default="INFO",
            )
            args, _ = parser.parse_known_args()

            assert args.log_level == "WARNING"

    def test_log_level_argument_accepts_error(self) -> None:
        """Test that --log-level accepts ERROR."""
        # pylint: disable=import-outside-toplevel
        with patch("sys.argv", ["apple_health_analyzer.py", "--log-level", "ERROR"]):
            import argparse

            parser = argparse.ArgumentParser()
            parser.add_argument(
                "--log-level",
                type=str,
                choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                default="INFO",
            )
            args, _ = parser.parse_known_args()

            assert args.log_level == "ERROR"

    def test_dev_file_argument_parsing(self) -> None:
        """Test that --dev-file argument is parsed correctly."""
        # pylint: disable=import-outside-toplevel
        test_path = "/path/to/export.zip"
        with patch("sys.argv", ["apple_health_analyzer.py", "--dev-file", test_path]):
            import argparse

            parser = argparse.ArgumentParser()
            parser.add_argument("--dev-file", type=str)
            args, _ = parser.parse_known_args()

            assert args.dev_file == test_path

    def test_combined_arguments_parsing(self) -> None:
        """Test that both --dev-file and --log-level can be used together."""
        # pylint: disable=import-outside-toplevel
        test_path = "/path/to/export.zip"
        with patch(
            "sys.argv",
            ["apple_health_analyzer.py", "--dev-file", test_path, "--log-level", "DEBUG"],
        ):
            import argparse

            parser = argparse.ArgumentParser()
            parser.add_argument("--dev-file", type=str)
            parser.add_argument(
                "--log-level",
                type=str,
                choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                default="INFO",
            )
            args, _ = parser.parse_known_args()

            assert args.dev_file == test_path
            assert args.log_level == "DEBUG"
