"""UI formatting and locale helpers."""

import json

from typing import Optional

from babel.core import default_locale
from babel.numbers import format_decimal

from i18n import translate


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


def qdate_locale_json(language_code: str) -> str:
    """Return Quasar QDate locale data serialized as JSON."""

    def tr(message: str) -> str:
        return translate(message, language=language_code)

    locale_by_language = {
        "fr": {
            "days": [
                tr("Sunday"),
                tr("Monday"),
                tr("Tuesday"),
                tr("Wednesday"),
                tr("Thursday"),
                tr("Friday"),
                tr("Saturday"),
            ],
            "daysShort": [
                tr("Sun"),
                tr("Mon"),
                tr("Tue"),
                tr("Wed"),
                tr("Thu"),
                tr("Fri"),
                tr("Sat"),
            ],
            "months": [
                tr("January"),
                tr("February"),
                tr("March"),
                tr("April"),
                tr("May"),
                tr("June"),
                tr("July"),
                tr("August"),
                tr("September"),
                tr("October"),
                tr("November"),
                tr("December"),
            ],
            "monthsShort": [
                tr("Jan"),
                tr("Feb"),
                tr("Mar"),
                tr("Apr"),
                tr("May"),
                tr("Jun"),
                tr("Jul"),
                tr("Aug"),
                tr("Sep"),
                tr("Oct"),
                tr("Nov"),
                tr("Dec"),
            ],
            "firstDayOfWeek": 1,
        },
        "en": {
            "days": [
                "Sunday",
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
            ],
            "daysShort": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            "months": [
                "January",
                "February",
                "March",
                "April",
                "May",
                "June",
                "July",
                "August",
                "September",
                "October",
                "November",
                "December",
            ],
            "monthsShort": [
                "Jan",
                "Feb",
                "Mar",
                "Apr",
                "May",
                "Jun",
                "Jul",
                "Aug",
                "Sep",
                "Oct",
                "Nov",
                "Dec",
            ],
            "firstDayOfWeek": 0,
        },
    }
    locale = locale_by_language.get(language_code, locale_by_language["en"])
    return json.dumps(locale)
