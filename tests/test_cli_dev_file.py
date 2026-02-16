"""Tests for command-line dev file parameter.

These tests invoke the actual application script (src/apple_health_analyzer.py) as a subprocess
to validate the CLI argument parsing and application startup behavior. This approach tests the
real application code path that users would experience when running the application, rather than
testing argument parsing in isolation with mock implementations.

The tests verify:
1. Help output includes all expected CLI options
2. Invalid file paths cause immediate failure with non-zero exit codes
3. Valid file paths allow the application to start successfully
"""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest


def test_dev_file_help() -> None:
    """Test that --help shows the --dev-file option on the real CLI.

    This test invokes the actual application module (src/apple_health_analyzer.py)
    as a subprocess, ensuring we test the real CLI argument parser, not a mock.
    This guarantees that --dev-file will be detected here if and only if it exists
    in the actual argparse setup in cli_main().
    """
    result = subprocess.run(
        [
            sys.executable,
            "src/apple_health_analyzer.py",
            "--help",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # Help should succeed and mention the --dev-file option
    assert result.returncode == 0, "Help command should succeed on real CLI"
    combined_output = (result.stdout or "") + (result.stderr or "")
    assert "--dev-file" in combined_output, "Help output should mention --dev-file option"


def test_dev_file_invalid_path() -> None:
    """Test that an invalid --dev-file path causes a non-zero exit on startup."""
    invalid_path = "/nonexistent/file.zip"

    result = subprocess.run(
        [
            sys.executable,
            "src/apple_health_analyzer.py",
            "--dev-file",
            invalid_path,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # The application should fail fast when given a clearly invalid dev file path
    assert result.returncode != 0, "Invalid --dev-file path should cause non-zero exit"


def test_dev_file_valid_path() -> None:
    """Test that a valid --dev-file path does not cause immediate startup failure."""
    fixture_path = Path("tests/fixtures/export_sample.zip")

    if not fixture_path.exists():
        pytest.skip(f"Test fixture not found: {fixture_path}")

    # Clean the environment to prevent NiceGUI from detecting a test context
    env = os.environ.copy()
    env.pop("PYTEST_CURRENT_TEST", None)
    env.pop("NICEGUI_SCREEN_TEST_PORT", None)

    # Start the real application with a valid dev file. We don't wait indefinitely;
    # instead, allow a short startup window, then terminate if still running.
    process = subprocess.Popen(  # pylint: disable=consider-using-with
        [
            sys.executable,
            "src/apple_health_analyzer.py",
            "--dev-file",
            str(fixture_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env,
    )

    try:
        # Give the server a small amount of time to start up
        time.sleep(3)
        exit_code = process.poll()
        if exit_code is not None:
            # Process has already exited, which indicates a startup failure
            _, stderr = process.communicate()
            assert exit_code == 0, f"Startup failed with error: {stderr}"

        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    finally:
        # Ensure the process is not left running
        if process.poll() is None:
            process.kill()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                # Best-effort cleanup: if the process still has not exited,
                # ignore the timeout to avoid masking test results.
                pass
