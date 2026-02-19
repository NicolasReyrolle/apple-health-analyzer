"""UI formatting helpers."""

from typing import Optional

from babel.core import default_locale
from babel.numbers import format_decimal


def _resolve_locale(locale_name: Optional[str] = None) -> str:
    """Resolve the locale to use for formatting."""
    if locale_name:
        return locale_name
    detected = default_locale()
    return detected or "en_US"


def format_integer(value: int, locale_name: Optional[str] = None) -> str:
    """Format an integer with grouping for the current locale."""
    return format_decimal(value, format="#,##0", locale=_resolve_locale(locale_name))


def period_code_to_label(code: str) -> str:
    """Convert a period code to a human-readable label."""
    mapping = {
        "D": "day",
        "W": "week",
        "M": "month",
        "Q": "quarter",
        "Y": "year",
    }
    return mapping.get(code, code)
