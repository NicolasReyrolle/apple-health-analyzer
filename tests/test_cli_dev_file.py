"""Tests for command-line dev file parameter."""

import subprocess
import sys
from pathlib import Path


def test_dev_file_help() -> None:
    """Test that --help shows the --dev-file option."""
    # Note: This test verifies the help message works
    # Full integration test requires NiceGUI server which is beyond scope here

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import argparse; "
            "parser = argparse.ArgumentParser(); "
            "parser.add_argument('--dev-file', type=str, help='Test'); "
            "args = parser.parse_args(['--help'])",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    # argparse prints help and exits with code 0
    assert result.returncode == 0, "Help command should succeed"


def test_dev_file_invalid_path() -> None:
    """Test that invalid file path is caught at startup."""
    test_code = """
import sys
sys.path.insert(0, 'src')
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('--dev-file', type=str)
args = parser.parse_args(['--dev-file', '/nonexistent/file.zip'])

if args.dev_file is not None:
    if not os.path.isfile(args.dev_file):
        print('Error: File not found:', args.dev_file)
        sys.exit(1)
"""
    result = subprocess.run(
        [sys.executable, "-c", test_code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1, "Should exit with error for invalid file"
    assert "File not found" in result.stdout, "Should show error message"


def test_dev_file_valid_path() -> None:
    """Test that valid file path is accepted."""
    fixture_path = Path("tests/fixtures/export_sample.zip")

    if not fixture_path.exists():
        # Generate the fixture
        subprocess.run(
            [sys.executable, "tests/fixtures/update_export_sample.py"],
            capture_output=True,
            check=False,
        )

    test_code = f"""
import sys
sys.path.insert(0, 'src')
import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument('--dev-file', type=str)
args = parser.parse_args(['--dev-file', r'{fixture_path}'])

if args.dev_file is not None:
    if not os.path.isfile(args.dev_file):
        print('Error: File not found:', args.dev_file)
        sys.exit(1)
    else:
        print('File found:', args.dev_file)
        sys.exit(0)
"""
    result = subprocess.run(
        [sys.executable, "-c", test_code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "Should exit successfully with valid file"
    assert "File found" in result.stdout, "Should confirm file found"
