"""Tests for the _setup_logging function in apple_health_analyzer.py."""

import logging
import logging.handlers
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Import the module to test
import apple_health_analyzer


class TestSetupLogging:
    """Tests for the _setup_logging function."""

    # pylint: disable=protected-access

    def test_setup_logging_with_debug_level(
        self, clean_logger: logging.Logger, tmp_path: Path
    ) -> None:
        """Test that _setup_logging correctly configures DEBUG level."""
        logger = clean_logger

        # Change working directory temporarily to tmp_path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            apple_health_analyzer._setup_logging("DEBUG", enable_file_logging=True)

            # Verify logger is configured at DEBUG level
            assert logger.level == logging.DEBUG

            # Verify we have 2 handlers (console + file)
            assert len(logger.handlers) == 2

            # Verify handlers are at DEBUG level
            for handler in logger.handlers:
                assert handler.level == logging.DEBUG

            # Verify one handler is StreamHandler (console) but not RotatingFileHandler
            console_handlers = [
                h
                for h in logger.handlers
                if isinstance(h, logging.StreamHandler)
                and not isinstance(h, logging.handlers.RotatingFileHandler)
            ]
            assert len(console_handlers) == 1
        finally:
            os.chdir(original_cwd)

    def test_setup_logging_with_info_level(
        self, clean_logger: logging.Logger, tmp_path: Path
    ) -> None:
        """Test that _setup_logging correctly configures INFO level."""
        logger = clean_logger

        # Change working directory temporarily to tmp_path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

            # Verify logger is configured at INFO level
            assert logger.level == logging.INFO

            # Verify handlers are at INFO level
            for handler in logger.handlers:
                assert handler.level == logging.INFO
        finally:
            os.chdir(original_cwd)

    def test_setup_logging_with_warning_level(
        self, clean_logger: logging.Logger, tmp_path: Path
    ) -> None:
        """Test that _setup_logging correctly configures WARNING level."""
        logger = clean_logger

        # Change working directory temporarily to tmp_path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            apple_health_analyzer._setup_logging("WARNING", enable_file_logging=True)

            assert logger.level == logging.WARNING
            for handler in logger.handlers:
                assert handler.level == logging.WARNING
        finally:
            os.chdir(original_cwd)

    def test_setup_logging_with_error_level(
        self, clean_logger: logging.Logger, tmp_path: Path
    ) -> None:
        """Test that _setup_logging correctly configures ERROR level."""
        logger = clean_logger

        # Change working directory temporarily to tmp_path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            apple_health_analyzer._setup_logging("ERROR", enable_file_logging=True)

            assert logger.level == logging.ERROR
            for handler in logger.handlers:
                assert handler.level == logging.ERROR
        finally:
            os.chdir(original_cwd)

    def test_setup_logging_disables_file_logging_in_dev_mode(
        self, clean_logger: logging.Logger
    ) -> None:
        """Test that file logging is disabled when enable_file_logging=False."""
        logger = clean_logger

        apple_health_analyzer._setup_logging("INFO", enable_file_logging=False)

        # Verify we have only 1 handler (console only, no file handler)
        assert len(logger.handlers) == 1

        # Verify the handler is a StreamHandler (console)
        assert isinstance(logger.handlers[0], logging.StreamHandler)

        # Verify it's not a RotatingFileHandler
        assert not isinstance(logger.handlers[0], logging.handlers.RotatingFileHandler)

    def test_setup_logging_clears_existing_handlers(
        self, clean_logger: logging.Logger, tmp_path: Path
    ) -> None:
        """Test that _setup_logging clears existing handlers to prevent duplicates."""
        logger = clean_logger

        # Add some dummy handlers
        dummy_handler1 = logging.StreamHandler(sys.stdout)
        dummy_handler2 = logging.StreamHandler(sys.stdout)
        logger.addHandler(dummy_handler1)
        logger.addHandler(dummy_handler2)

        # Record the dummy handlers to verify they are removed
        handlers_before = set(logger.handlers)
        dummy_handlers = {dummy_handler1, dummy_handler2}

        # Change working directory temporarily to tmp_path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

            # After calling _setup_logging, verify none of the dummy handlers remain
            handlers_after = set(logger.handlers)
            assert not dummy_handlers.intersection(
                handlers_after
            ), "Dummy handlers should have been removed by _setup_logging"

            # Verify we have exactly 2 new handlers (console + file)
            assert len(logger.handlers) == 2, f"Expected 2 handlers, got {len(logger.handlers)}"
        finally:
            os.chdir(original_cwd)

    def test_setup_logging_creates_log_directory(
        self, clean_logger: logging.Logger, tmp_path: Path
    ) -> None:
        """Test that _setup_logging creates the logs directory."""
        logger = clean_logger

        # Use a real path in tmp_path
        log_dir = tmp_path / "logs"
        assert not log_dir.exists(), "Log directory should not exist initially"

        # Change working directory temporarily to tmp_path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

            # Verify log directory was created
            assert log_dir.exists(), "Log directory should be created"
        finally:
            os.chdir(original_cwd)

    def test_setup_logging_console_handler_uses_stdout(self, clean_logger: logging.Logger) -> None:
        """Test that the console handler writes to stdout."""
        logger = clean_logger

        apple_health_analyzer._setup_logging("INFO", enable_file_logging=False)

        # Get the StreamHandler
        stream_handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
        assert len(stream_handlers) == 1

        # Verify it uses stdout
        assert stream_handlers[0].stream == sys.stdout

    def test_setup_logging_handlers_have_formatters(
        self, clean_logger: logging.Logger, tmp_path: Path
    ) -> None:
        """Test that all handlers have formatters configured."""
        logger = clean_logger

        # Change working directory temporarily to tmp_path
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            apple_health_analyzer._setup_logging("INFO", enable_file_logging=True)

            # Verify all handlers have formatters
            for handler in logger.handlers:
                assert handler.formatter is not None
                assert isinstance(handler.formatter, logging.Formatter)
        finally:
            os.chdir(original_cwd)

    def test_setup_logging_with_file_handler_configuration(
        self, clean_logger: logging.Logger, tmp_path: Path
    ) -> None:
        """Test that file handler is configured with correct settings."""
        logger = clean_logger

        # Create actual logs directory for this test
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


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing logic."""

    @staticmethod
    def _extract_log_level_from_mock(mock_setup_logging) -> str:
        """Helper to extract log_level from _setup_logging mock calls.

        Args:
            mock_setup_logging: The mock for _setup_logging

        Returns:
            The log level string passed to _setup_logging
        """
        # Ensure at least one call was made
        assert len(mock_setup_logging.call_args_list) > 0, "Expected _setup_logging to be called"
        # Get the most recent call
        call_args = mock_setup_logging.call_args
        # Extract log_level from either positional or keyword arguments
        log_level: str = call_args[0][0] if call_args[0] else call_args[1].get("log_level")
        return log_level

    def test_log_level_argument_default(self) -> None:
        """Test that --log-level defaults to INFO in the real CLI."""
        with (
            patch("sys.argv", ["apple_health_analyzer.py"]),
            patch("apple_health_analyzer._setup_logging") as mock_setup_logging,
            patch("apple_health_analyzer.ui.run") as mock_ui_run,
        ):
            apple_health_analyzer.cli_main()

        mock_setup_logging.assert_called()
        log_level = self._extract_log_level_from_mock(mock_setup_logging)
        assert log_level == "INFO"
        assert mock_ui_run.called

    def test_log_level_argument_accepts_debug(self) -> None:
        """Test that --log-level DEBUG is accepted by the real CLI."""
        with (
            patch(
                "sys.argv",
                ["apple_health_analyzer.py", "--log-level", "DEBUG"],
            ),
            patch("apple_health_analyzer._setup_logging") as mock_setup_logging,
            patch("apple_health_analyzer.ui.run") as mock_ui_run,
        ):
            apple_health_analyzer.cli_main()

        mock_setup_logging.assert_called()
        log_level = self._extract_log_level_from_mock(mock_setup_logging)
        assert log_level == "DEBUG"
        assert mock_ui_run.called

    def test_log_level_argument_accepts_warning(self) -> None:
        """Test that --log-level WARNING is accepted by the real CLI."""
        with (
            patch(
                "sys.argv",
                ["apple_health_analyzer.py", "--log-level", "WARNING"],
            ),
            patch("apple_health_analyzer._setup_logging") as mock_setup_logging,
            patch("apple_health_analyzer.ui.run") as mock_ui_run,
        ):
            apple_health_analyzer.cli_main()

        mock_setup_logging.assert_called()
        log_level = self._extract_log_level_from_mock(mock_setup_logging)
        assert log_level == "WARNING"
        assert mock_ui_run.called

    def test_log_level_argument_accepts_error(self) -> None:
        """Test that --log-level ERROR is accepted by the real CLI."""
        with (
            patch(
                "sys.argv",
                ["apple_health_analyzer.py", "--log-level", "ERROR"],
            ),
            patch("apple_health_analyzer._setup_logging") as mock_setup_logging,
            patch("apple_health_analyzer.ui.run") as mock_ui_run,
        ):
            apple_health_analyzer.cli_main()

        mock_setup_logging.assert_called()
        log_level = self._extract_log_level_from_mock(mock_setup_logging)
        assert log_level == "ERROR"
        assert mock_ui_run.called

    def test_no_browser_argument_default(self) -> None:
        """Test that browser opens by default (show=True)."""
        with (
            patch("sys.argv", ["apple_health_analyzer.py"]),
            patch("apple_health_analyzer._setup_logging"),
            patch("apple_health_analyzer.ui.run") as mock_ui_run,
        ):
            apple_health_analyzer.cli_main()

        # Verify ui.run was called with show=True (default)
        mock_ui_run.assert_called_once()
        call_kwargs = mock_ui_run.call_args[1]
        assert call_kwargs.get("show") is True

    def test_no_browser_argument_prevents_browser_open(self) -> None:
        """Test that --no-browser prevents browser from opening (show=False)."""
        with (
            patch("sys.argv", ["apple_health_analyzer.py", "--no-browser"]),
            patch("apple_health_analyzer._setup_logging"),
            patch("apple_health_analyzer.ui.run") as mock_ui_run,
        ):
            apple_health_analyzer.cli_main()

        # Verify ui.run was called with show=False
        mock_ui_run.assert_called_once()
        call_kwargs = mock_ui_run.call_args[1]
        assert call_kwargs.get("show") is False
