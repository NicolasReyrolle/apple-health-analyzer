"""Tests for package metadata."""

import src


def test_package_exposes_version() -> None:
    """Package root should expose a semantic version string."""
    assert src.__version__ == "0.1.0"
