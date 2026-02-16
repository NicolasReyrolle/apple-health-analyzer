"""Tests for command-line dev file parameter."""

import subprocess
import sys
import time
from pathlib import Path


def test_dev_file_help() -> None:
    """Test that --help shows the --dev-file option on the real CLI."""
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
        # Generate the fixture if needed
        subprocess.run(
            [sys.executable, "tests/fixtures/update_export_sample.py"],
            capture_output=True,
            check=False,
        )

    # Start the real application with a valid dev file. We don't wait indefinitely;
    # instead, allow a short startup window, then terminate if still running.
    process = subprocess.Popen(
        [
            sys.executable,
            "src/apple_health_analyzer.py",
            "--dev-file",
            str(fixture_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        # Give the server a small amount of time to start up
        time.sleep(3)
        return_code = process.poll()
        if return_code is None:
            # Still running: terminate gracefully and ensure it did not fail immediately
            process.terminate()
            return_code = process.wait(timeout=10)
        # A valid dev file should not cause an immediate error exit
        assert return_code == 0, "Valid --dev-file path should not cause startup failure"
    finally:
        # Ensure the process is not left running
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)
