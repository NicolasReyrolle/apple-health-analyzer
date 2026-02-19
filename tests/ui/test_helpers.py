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


class TestPeriodCodeToLabel:
    """Tests for period_code_to_label conversion."""

    def test_converts_day_code(self) -> None:
        """Day code 'D' should convert to 'day'."""
        assert helpers.period_code_to_label("D") == "day"

    def test_converts_week_code(self) -> None:
        """Week code 'W' should convert to 'week'."""
        assert helpers.period_code_to_label("W") == "week"

    def test_converts_month_code(self) -> None:
        """Month code 'M' should convert to 'month'."""
        assert helpers.period_code_to_label("M") == "month"

    def test_converts_quarter_code(self) -> None:
        """Quarter code 'Q' should convert to 'quarter'."""
        assert helpers.period_code_to_label("Q") == "quarter"

    def test_converts_year_code(self) -> None:
        """Year code 'Y' should convert to 'year'."""
        assert helpers.period_code_to_label("Y") == "year"

    def test_returns_code_for_unknown_value(self) -> None:
        """Unknown code should return the code itself."""
        assert helpers.period_code_to_label("X") == "X"
        assert helpers.period_code_to_label("ABC") == "ABC"

    def test_case_sensitive(self) -> None:
        """Conversion should be case-sensitive."""
        assert helpers.period_code_to_label("w") == "w"
        assert helpers.period_code_to_label("m") == "m"
