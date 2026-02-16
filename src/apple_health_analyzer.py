#!/usr/bin/env python3
"""
Apple Health Analyzer GUI

A graphical user interface for analyzing Apple Health data.
"""

import argparse
import logging
import logging.handlers
import os
import sys
import uuid
from pathlib import Path

from nicegui import app, ui

from app_state import state
from assets import APP_ICON_BASE64
from ui.layout import load_file, render_body, render_header, render_left_drawer

# Configure basic logging at module level to ensure logger has handlers
# This will be reconfigured by _setup_logging() when the application starts
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
_logger = logging.getLogger(__name__)


def _setup_logging(log_level: str, enable_file_logging: bool = True) -> None:
    """Configure logging with both console and file handlers.

    Args:
        log_level: Logging level as string (DEBUG, INFO, WARNING, ERROR)
        enable_file_logging: Whether to write logs to a file
            (disabled in dev mode to avoid reload loops)
    """
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, log_level))

    # Remove any existing handlers to prevent duplicates
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level))
    console_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)

    # File handler for persistence (in case console is captured)
    if enable_file_logging:
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / "apple_health_analyzer.log",
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=3,
        )
        file_handler.setLevel(getattr(logging, log_level))
        file_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)


def main() -> None:
    """Main NiceGUI page setup function.

    This function is called by NiceGUI for each page render.
    It should not contain CLI argument parsing or app initialization logic.
    """

    render_header()
    render_left_drawer()
    render_body()

    with ui.footer():
        state.log = ui.log(max_lines=10).classes("w-full h-20")

    app.add_static_files("/resources", "resources")
    ui.add_head_html('<link rel="stylesheet" href="/resources/style.css">', shared=True)

    # Check if dev file was passed through app storage
    # Note: This auto-load mechanism intentionally triggers on every page render
    # (e.g., browser refresh or new tab). This is useful for development as it
    # allows quickly testing changes by simply refreshing the browser.
    dev_file: str | None = app.storage.general.get(  # type: ignore[no-untyped-call]
        "_dev_file_path"
    )
    if dev_file is not None:
        _logger.info("Dev file will be auto-loaded: %s", dev_file)
        state.input_file.value = dev_file

        async def _auto_load() -> None:
            """Auto-load the dev file after UI is ready."""
            _logger.info("Auto-loading file: %s", dev_file)
            await load_file()

        # Use ui.timer with the async callback
        _logger.debug("Scheduling file load via ui.timer after 1 second")
        ui.timer(1.0, _auto_load, once=True)


def cli_main() -> None:
    """CLI entry point that handles argument parsing and starts the application.

    This function should be called from the command line or the entry point.
    It parses CLI arguments, sets up logging, and starts the NiceGUI server.
    """
    # Parse command-line arguments for developer mode
    parser = argparse.ArgumentParser(
        description="Apple Health Analyzer - Analyze your Apple Health data",
        prog="apple-health-analyzer",
    )
    parser.add_argument(
        "--dev-file",
        type=str,
        help="(Developer mode) Path to an Apple Health export ZIP file"
        " to load automatically on startup",
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Set the logging level",
    )
    parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Prevent browser from automatically opening on startup",
    )
    args, _ = parser.parse_known_args()

    # Validate dev file if provided
    if args.dev_file is not None:
        # Disable file logging in dev mode to avoid reload loops from log file changes
        _setup_logging(args.log_level, enable_file_logging=False)
        try:
            resolved_path = Path(args.dev_file).expanduser().resolve()
        except OSError as exc:
            _logger.error("Invalid dev file path '%s': %s", args.dev_file, exc)
            sys.exit(1)
        if not resolved_path.is_file():
            _logger.error("File not found: %s", resolved_path)
            sys.exit(1)
        _logger.info("Dev mode: file logging disabled to prevent reload loops")
        _logger.info("Dev file specified: %s", resolved_path)
    else:
        # Enable file logging in normal mode
        _setup_logging(args.log_level, enable_file_logging=True)

    _logger.info("Starting Apple Health Analyzer with log level: %s", args.log_level)

    secret = uuid.uuid4().hex if "pytest" in sys.modules else os.getenv("STORAGE_SECRET", "secret")

    # Pass dev file path through app storage so it's accessible in main()
    if args.dev_file is not None:
        app.storage.general["_dev_file_path"] = str(resolved_path)
        _logger.debug("Stored dev file path in app storage: %s", resolved_path)

    _logger.debug("Initializing NiceGUI app")
    ui.run(  # type: ignore[misc]
        main,
        title="Apple Health Analyzer",
        favicon=APP_ICON_BASE64,
        storage_secret=secret,
        uvicorn_reload_dirs="src,resources",  # Only include needed dirs for the reload
        show=not args.no_browser,
    )


if __name__ in {"__main__", "__mp_main__"}:
    cli_main()
