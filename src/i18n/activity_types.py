"""Helpers to localize Apple Health workout activity types for display.

Raw values are preserved for filtering and exports. These helpers only translate
labels shown in the UI.
"""

from __future__ import annotations

import logging
import re
from collections.abc import Mapping

from i18n import t

_logger = logging.getLogger(__name__)


# Complete public HKWorkoutActivityType set (including deprecated legacy values)
# collected from Apple HealthKit API documentation.
HK_WORKOUT_ACTIVITY_TYPES = frozenset(
    {
        "AmericanFootball",
        "Archery",
        "AustralianFootball",
        "Badminton",
        "Baseball",
        "Basketball",
        "Barre",
        "Bowling",
        "Boxing",
        "CardioDance",
        "Climbing",
        "Cooldown",
        "CoreTraining",
        "Cricket",
        "CrossCountrySkiing",
        "CrossTraining",
        "Curling",
        "Cycling",
        "Dance",
        "DanceInspiredTraining",
        "DiscSports",
        "DownhillSkiing",
        "Elliptical",
        "EquestrianSports",
        "Fencing",
        "Fishing",
        "FitnessGaming",
        "Flexibility",
        "FunctionalStrengthTraining",
        "Golf",
        "Gymnastics",
        "HandCycling",
        "Handball",
        "HighIntensityIntervalTraining",
        "Hiking",
        "Hockey",
        "Hunting",
        "JumpRope",
        "Kickboxing",
        "Lacrosse",
        "MartialArts",
        "MindAndBody",
        "MixedCardio",
        "MixedMetabolicCardioTraining",
        "Other",
        "PaddleSports",
        "Pickleball",
        "Pilates",
        "Play",
        "PreparationAndRecovery",
        "Racquetball",
        "Rowing",
        "Rugby",
        "Running",
        "Sailing",
        "SkatingSports",
        "Snowboarding",
        "SnowSports",
        "Soccer",
        "SocialDance",
        "Softball",
        "Squash",
        "StairClimbing",
        "Stairs",
        "StepTraining",
        "SurfingSports",
        "SwimBikeRun",
        "Swimming",
        "TableTennis",
        "TaiChi",
        "Tennis",
        "TrackAndField",
        "TraditionalStrengthTraining",
        "Transition",
        "UnderwaterDiving",
        "Volleyball",
        "Walking",
        "WaterFitness",
        "WaterPolo",
        "WaterSports",
        "WheelchairRunPace",
        "WheelchairWalkPace",
        "Wrestling",
        "Yoga",
    }
)

_DISPLAY_LABEL_OVERRIDES = {
    "All": "All",
    "Others": "Others",
}

_logged_unknown_activity_types: set[str] = set()


def _humanize_camel_case(value: str) -> str:
    """Convert camel-cased enum names to human-readable labels."""
    return re.sub(r"(?<!^)(?=[A-Z])", " ", value).strip()


def normalize_activity_type(activity_type: str) -> str:
    """Normalize Apple Health activity type values to canonical enum names."""
    normalized = activity_type.replace("HKWorkoutActivityType", "", 1)
    return normalized or activity_type


def activity_display_label(activity_type: str) -> str:
    """Return translated label for an activity type value."""
    normalized = normalize_activity_type(activity_type)
    if normalized in _DISPLAY_LABEL_OVERRIDES:
        return t(_DISPLAY_LABEL_OVERRIDES[normalized])

    if normalized in HK_WORKOUT_ACTIVITY_TYPES:
        return t(_humanize_camel_case(normalized))

    if normalized not in _logged_unknown_activity_types:
        _logged_unknown_activity_types.add(normalized)
        _logger.warning(
            "Unknown workout activity type '%s'. Falling back to humanized label.", normalized
        )
    return t(_humanize_camel_case(normalized))


def build_activity_select_options(activity_options: list[str]) -> dict[str, str]:
    """Build translated dropdown options while preserving raw activity values.

    NiceGUI `ui.select` expects dictionary options in the form
    `{value: label}`. The selected value remains the raw activity type.
    """
    translated_options: dict[str, str] = {}
    used_labels: set[str] = set()
    for raw_value in activity_options:
        display_label = activity_display_label(raw_value)
        if display_label in used_labels:
            display_label = f"{display_label} ({raw_value})"
        translated_options[raw_value] = display_label
        used_labels.add(display_label)
    return translated_options


def translate_activity_value_map(values: Mapping[str, float | int]) -> dict[str, float | int]:
    """Translate activity names in metric maps and merge label collisions if needed."""
    translated: dict[str, float | int] = {}
    for raw_label, metric_value in values.items():
        translated_label = activity_display_label(raw_label)
        if translated_label in translated:
            translated[translated_label] += metric_value
        else:
            translated[translated_label] = metric_value
    return translated
