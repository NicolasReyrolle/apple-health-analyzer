"""Tests for UI helper formatting utilities."""

from typing import Optional

import pytest

from ui import helpers


def test_format_integer_uses_explicit_locale() -> None:
    """Explicit locale should be used for formatting."""
    assert helpers.format_integer(12345, locale_name="en_US") == "12,345"


def test_format_integer_defaults_to_fallback_locale(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fallback locale should be used when no default is detected."""

    def _no_locale() -> Optional[str]:
        return None

    monkeypatch.setattr(helpers, "default_locale", _no_locale)

    assert helpers.format_integer(1234) == "1,234"
