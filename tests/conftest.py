"""Fixtures for testing Apple Health Analyzer."""

# pylint: disable=line-too-long

import asyncio
import contextlib
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import (
    Any,
    Callable,
    ContextManager,
    Generator,
    Iterator,
    List,
    Optional,
)
from unittest.mock import MagicMock, patch

import nicegui.storage
import pytest
from nicegui.testing import UserInteraction

from app_state import state as app_state
from tests.types_helper import StateAssertion

# XML Builder utilities for constructing complex test fixtures

# Mapping of activity types to their distance field identifiers
ACTIVITY_TYPE_TO_DISTANCE_FIELD = {
    "HKWorkoutActivityTypeRunning": "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKWorkoutActivityTypeWalking": "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKWorkoutActivityTypeHiking": "HKQuantityTypeIdentifierDistanceWalkingRunning",
    "HKWorkoutActivityTypeCycling": "HKQuantityTypeIdentifierDistanceCycling",
    "HKWorkoutActivityTypeSwimming": "HKQuantityTypeIdentifierDistanceSwimming",
}

# Distance units for different activity types
ACTIVITY_TYPE_TO_DISTANCE_UNIT = {
    "HKWorkoutActivityTypeRunning": "km",
    "HKWorkoutActivityTypeWalking": "km",
    "HKWorkoutActivityTypeHiking": "km",
    "HKWorkoutActivityTypeCycling": "km",
    "HKWorkoutActivityTypeSwimming": "m",  # Swimming distance is in meters
}

"""
XML BUILDER USAGE EXAMPLES
==========================

Example 1: Create a Running workout with distance and elevation
    def test_running_workout(build_complex_xml):
        activity = build_workout_activity(
            activity_type="HKWorkoutActivityTypeRunning",
            distance=10.5,  # in km
            elevation_cm="50000",  # 500 meters
            heart_rate_stats={"average": "150", "minimum": "120", "maximum": "180"}
        )
        xml = build_complex_xml(activities=[activity])

Example 2: Create a Swimming workout (distance in meters, no step count)
    def test_swimming_workout(build_complex_xml):
        activity = build_workout_activity(
            activity_type="HKWorkoutActivityTypeSwimming",
            distance=750,  # in meters
            step_count=None,  # Swimming doesn't use steps
            heart_rate_stats={"average": "130", "minimum": "100", "maximum": "160"}
        )
        xml = build_complex_xml(activities=[activity])

Example 3: Create a Cycling workout with elevation
    def test_cycling_workout(build_complex_xml):
        activity = build_workout_activity(
            activity_type="HKWorkoutActivityTypeCycling",
            distance=25.3,  # in km
            elevation_cm="15000",  # 150 meters of elevation
            heart_rate_stats={"average": "140", "minimum": "100", "maximum": "170"}
        )
        xml = build_complex_xml(activities=[activity])

Example 4: Create a workout without distance (e.g., Strength Training)
    def test_strength_training(build_complex_xml):
        activity = build_workout_activity(
            activity_type="HKWorkoutActivityTypeFunctionalStrengthTraining",
            distance=None,  # No distance for strength training
            heart_rate_stats={"average": "100", "minimum": "70", "maximum": "130"}
        )
        xml = build_complex_xml(activities=[activity])

Example 5: Multiple activities in one workout
    def test_multiple_activities(build_complex_xml):
        running_activity = build_workout_activity(
            activity_type="HKWorkoutActivityTypeRunning",
            distance=5.0
        )
        swimming_activity = build_workout_activity(
            activity_type="HKWorkoutActivityTypeSwimming",
            distance=500
        )
        xml = build_complex_xml(activities=[running_activity, swimming_activity])

KEY POINTS:
- Distance units vary: km for most activities, meters for swimming
- Not all activities have distance (e.g., strength training)
- Activity types are mapped to correct distance field names automatically
- distance parameter is optional (set to None to exclude)
- heart_rate_stats is optional dict with 'average', 'minimum', 'maximum' keys
"""


def get_distance_field_for_activity(activity_type: str) -> Optional[str]:
    """Get the correct distance field name for a given activity type."""
    return ACTIVITY_TYPE_TO_DISTANCE_FIELD.get(activity_type)


def get_distance_unit_for_activity(activity_type: str) -> str:
    """Get the distance unit for a given activity type."""
    return ACTIVITY_TYPE_TO_DISTANCE_UNIT.get(activity_type, "km")


def build_workout_activity(
    uuid: str = "936B9E1D-52B9-41CA-BCA9-9654D43F004E",
    start_date: str = "2025-12-20 12:51:00 +0100",
    end_date: str = "2025-12-20 14:50:16 +0100",
    duration: str = "119.2710362156232",
    step_count: Optional[str] = None,
    elevation_cm: Optional[str] = None,
    activity_type: str = "HKWorkoutActivityTypeRunning",
    distance: Optional[float] = None,
    heart_rate_stats: Optional[dict[str, str]] = None,
) -> str:
    """
    Build a WorkoutActivity XML element with configurable parameters.

    Args:
        uuid: Activity UUID
        start_date: Start date string
        end_date: End date string
        duration: Duration in minutes
        step_count: Optional step count (not all activities have this)
        elevation_cm: Optional elevation in centimeters
        activity_type: HKWorkoutActivityType (e.g., HKWorkoutActivityTypeRunning)
        distance: Optional distance value (will use correct field based on activity type)
        heart_rate_stats: Optional dict with keys 'average', 'minimum', 'maximum'

    Returns:
        WorkoutActivity XML element as string
    """
    # Build statistics
    statistics: list[str] = []

    # Add step count if provided
    if step_count:
        statistics.append(
            f'            <WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" '
            f'startDate="{start_date}" endDate="{end_date}" sum="{step_count}" unit="count"/>'
        )

    # Add distance if provided
    if distance is not None:
        distance_field = get_distance_field_for_activity(activity_type)
        distance_unit = get_distance_unit_for_activity(activity_type)
        if distance_field:
            statistics.append(
                f'            <WorkoutStatistics type="{distance_field}" '
                f'startDate="{start_date}" endDate="{end_date}" '
                f'sum="{distance}" unit="{distance_unit}"/>'
            )

    # Add heart rate if provided
    if heart_rate_stats:
        avg: str = heart_rate_stats.get("average", "100")
        min_val: str = heart_rate_stats.get("minimum", "60")
        max_val: str = heart_rate_stats.get("maximum", "150")
        statistics.append(
            f'            <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" '
            f'startDate="{start_date}" endDate="{end_date}" average="{avg}" '
            f'minimum="{min_val}" maximum="{max_val}" unit="count/min"/>'
        )

    # Build metadata entries
    metadata: list[str] = []
    if elevation_cm:
        metadata.append(
            f'            <MetadataEntry key="HKElevationAscended" value="{elevation_cm} cm"/>'
        )

    # Combine all elements
    stats_xml = "\n".join(statistics)
    metadata_xml = "\n".join(metadata)

    combined_content = (
        f"{stats_xml}\n{metadata_xml}"
        if stats_xml and metadata_xml
        else (stats_xml or metadata_xml)
    )

    return f"""        <WorkoutActivity uuid="{uuid}" startDate="{start_date}" endDate="{end_date}" duration="{duration}" durationUnit="min">
{combined_content}
        </WorkoutActivity>"""


def build_workout_route(
    source_name: str = "Apple Watch de Nicolas",
    creation_date: str = "2025-12-20 14:51:25 +0100",
    start_date: str = "2025-12-20 12:51:00 +0100",
    end_date: str = "2025-12-20 14:50:16 +0100",
    route_path: str = "/workout-routes/route_2025-12-20_2.50pm.gpx",
) -> str:
    """Build a WorkoutRoute XML element with configurable parameters."""
    return f"""        <WorkoutRoute sourceName="{source_name}" sourceVersion="26.2" creationDate="{creation_date}" startDate="{start_date}" endDate="{end_date}">
            <MetadataEntry key="HKMetadataKeySyncVersion" value="2"/>
            <FileReference path="{route_path}"/>
        </WorkoutRoute>"""


def build_metadata_entry(key: str, value: str) -> str:
    """Build a MetadataEntry XML element."""
    return f'<MetadataEntry key="{key}" value="{value}"/>'


def build_workout_statistics(
    stat_type: str,
    start_date: str,
    end_date: str,
    unit: str,
    sum_value: Optional[str] = None,
    average: Optional[str] = None,
    minimum: Optional[str] = None,
    maximum: Optional[str] = None,
) -> str:
    """Build a WorkoutStatistics XML element."""
    attributes = [
        f'type="{stat_type}"',
        f'startDate="{start_date}"',
        f'endDate="{end_date}"',
    ]
    if sum_value is not None:
        attributes.append(f'sum="{sum_value}"')
    if average is not None:
        attributes.append(f'average="{average}"')
    if minimum is not None:
        attributes.append(f'minimum="{minimum}"')
    if maximum is not None:
        attributes.append(f'maximum="{maximum}"')
    attributes.append(f'unit="{unit}"')
    return f"<WorkoutStatistics {' '.join(attributes)}/>"


def build_workout_event(
    event_type: str,
    date: str,
    duration: str,
    duration_unit: str,
    metadata_entries: Optional[List[str]] = None,
) -> str:
    """Build a WorkoutEvent XML element, optionally with MetadataEntry children."""
    if not metadata_entries:
        return (
            f'<WorkoutEvent type="{event_type}" date="{date}" '
            f'duration="{duration}" durationUnit="{duration_unit}"/>'
        )

    metadata_xml = "\n".join([f"    {entry}" for entry in metadata_entries])
    return (
        f'<WorkoutEvent type="{event_type}" date="{date}" '
        f'duration="{duration}" durationUnit="{duration_unit}">\n'
        f"{metadata_xml}\n"
        f"</WorkoutEvent>"
    )


def build_swimming_workout_example() -> str:
    """Build a sample swimming workout XML element."""
    start_date = "2025-09-13 15:39:17 +0100"
    end_date = "2025-09-13 16:18:24 +0100"

    metadata = [
        build_metadata_entry("HKLapLength", "50 m"),
        build_metadata_entry("HKIndoorWorkout", "0"),
        build_metadata_entry("HKTimeZone", "Europe/Luxembourg"),
        build_metadata_entry("HKSwimmingLocationType", "1"),
        build_metadata_entry("HKAverageMETs", "6.52565 kcal/hr·kg"),
    ]

    events = [
        build_workout_event(
            event_type="HKWorkoutEventTypeSegment",
            date=start_date,
            duration="2.565596975882848",
            duration_unit="min",
            metadata_entries=[
                build_metadata_entry("HKSWOLFScore", "105.7867826223373"),
            ],
        )
    ]

    statistics = [
        build_workout_statistics(
            stat_type="HKQuantityTypeIdentifierDistanceSwimming",
            start_date=start_date,
            end_date=end_date,
            sum_value="750",
            unit="m",
        ),
        build_workout_statistics(
            stat_type="HKQuantityTypeIdentifierSwimmingStrokeCount",
            start_date=start_date,
            end_date=end_date,
            sum_value="509",
            unit="count",
        ),
        build_workout_statistics(
            stat_type="HKQuantityTypeIdentifierActiveEnergyBurned",
            start_date=start_date,
            end_date=end_date,
            sum_value="277.588",
            unit="kcal",
        ),
        build_workout_statistics(
            stat_type="HKQuantityTypeIdentifierHeartRate",
            start_date=start_date,
            end_date=end_date,
            average="102.834",
            minimum="80",
            maximum="133",
            unit="count/min",
        ),
    ]

    return build_workout(
        activity_type="HKWorkoutActivityTypeSwimming",
        workout_start=start_date,
        workout_end=end_date,
        workout_duration="39.128",
        source_name="Apple Watch de Nicolas",
        source_version="11.6.1",
        creation_date="2025-09-13 16:18:26 +0100",
        metadata=metadata,
        events=events,
        statistics=statistics,
    )


def build_running_workout_example() -> str:
    """Build a sample running workout XML element."""
    workout_start = "2025-09-14 17:11:57 +0100"
    workout_end = "2025-09-14 17:53:06 +0100"
    activity_end = "2025-09-14 17:31:57 +0100"

    metadata = [
        build_metadata_entry("HKIndoorWorkout", "0"),
        build_metadata_entry("HKElevationAscended", "7330 cm"),
        build_metadata_entry("HKWeatherHumidity", "7900 %"),
        build_metadata_entry("HKTimeZone", "Europe/Luxembourg"),
        build_metadata_entry("HKWeatherTemperature", "61.4907 degF"),
        build_metadata_entry("HKAverageMETs", "10.2221 kcal/hr·kg"),
    ]

    events = [
        build_workout_event(
            event_type="HKWorkoutEventTypeSegment",
            date=workout_start,
            duration="6.449974838892619",
            duration_unit="min",
        )
    ]

    activity = build_workout_activity(
        uuid="138D5D6C-D7B0-49D8-9854-804F369D5C9B",
        start_date=workout_start,
        end_date=activity_end,
        duration="20.00001126726469",
        step_count="3305.88",
        activity_type="HKWorkoutActivityTypeRunning",
        distance=3.06833,
        heart_rate_stats={"average": "129.194", "minimum": "113", "maximum": "151"},
    )

    statistics = [
        build_workout_statistics(
            stat_type="HKQuantityTypeIdentifierDistanceWalkingRunning",
            start_date=workout_start,
            end_date=workout_end,
            sum_value="3.06833",
            unit="km",
        ),
        build_workout_statistics(
            stat_type="HKQuantityTypeIdentifierActiveEnergyBurned",
            start_date=workout_start,
            end_date=workout_end,
            sum_value="239.743",
            unit="kcal",
        ),
        build_workout_statistics(
            stat_type="HKQuantityTypeIdentifierHeartRate",
            start_date=workout_start,
            end_date=workout_end,
            average="129.194",
            minimum="113",
            maximum="151",
            unit="count/min",
        ),
    ]

    return build_workout(
        activity_type="HKWorkoutActivityTypeRunning",
        workout_start=workout_start,
        workout_end=workout_end,
        workout_duration="41.154",
        source_name="Apple Watch de Nicolas",
        source_version="11.6.1",
        creation_date="2025-09-14 17:53:17 +0100",
        activities=[activity],
        metadata=metadata,
        events=events,
        statistics=statistics,
    )


def build_workout(
    activity_type: str = "HKWorkoutActivityTypeRunning",
    workout_start: str = "2025-12-20 12:51:00 +0100",
    workout_end: str = "2025-12-20 14:50:16 +0100",
    workout_duration: str = "119.2710362156232",
    source_name: str = "Apple Watch",
    source_version: str = "26.2",
    creation_date: str = "2025-12-20 14:51:19 +0100",
    activities: Optional[List[str]] = None,
    include_route: bool = False,
    statistics: Optional[List[str]] = None,
    metadata: Optional[List[str]] = None,
    events: Optional[List[str]] = None,
) -> str:
    """
    Build a complete Workout XML element with all sub-elements.

    Args:
        activity_type: HKWorkoutActivityType (e.g., HKWorkoutActivityTypeRunning).
        workout_start: Workout start date.
        workout_end: Workout end date.
        workout_duration: Workout duration in minutes.
        source_name: Source name for the workout.
        source_version: Source version string.
        creation_date: Workout creation date.
        activities: List of WorkoutActivity XML strings.
        include_route: Whether to include a WorkoutRoute element.
        statistics: List of WorkoutStatistics XML strings.
        metadata: List of MetadataEntry XML strings.
        events: List of WorkoutEvent XML strings.

    Returns:
        Complete Workout XML element as string.
    """
    # Build metadata entries
    metadata_xml = ""
    if metadata:
        metadata_xml = "\n".join([f"        {entry}" for entry in metadata])

    # Build events
    events_xml = ""
    if events:
        events_xml = "\n".join([f"        {event}" for event in events])

    # Build activities
    activities_xml = ""
    if activities:
        activities_xml = "\n".join(activities)

    # Build statistics
    statistics_xml = ""
    if statistics:
        statistics_xml = "\n".join([f"        {stat}" for stat in statistics])

    # Build route
    route_xml = ""
    if include_route:
        route_xml = "\n" + build_workout_route()

    # Combine all parts
    content_parts = [
        metadata_xml,
        events_xml,
        activities_xml,
        statistics_xml,
        route_xml,
    ]
    content = "\n".join(part for part in content_parts if part)

    return f"""    <Workout workoutActivityType="{activity_type}" duration="{workout_duration}" durationUnit="min" sourceName="{source_name}" sourceVersion="{source_version}" creationDate="{creation_date}" startDate="{workout_start}" endDate="{workout_end}">
{content}
    </Workout>"""


def build_health_xml(
    workouts: Optional[List[str]] = None,
    activities: Optional[List[str]] = None,
    include_route: bool = False,
    activity_type: str = "HKWorkoutActivityTypeRunning",
    workout_start: str = "2025-12-20 12:51:00 +0100",
    workout_end: str = "2025-12-20 14:50:16 +0100",
    workout_duration: str = "119.2710362156232",
    source_name: str = "Apple Watch",
    elevation_cm: str = "154430",
    include_default_statistics: bool = True,
) -> str:
    """
    Build complete HealthData XML with configurable workouts.

    Args:
        workouts: List of complete Workout XML strings. If provided, other workout params are ignored.
        activities: List of WorkoutActivity XML strings. If None, creates one default activity.
        include_route: Whether to include a WorkoutRoute element.
        activity_type: HKWorkoutActivityType (e.g., HKWorkoutActivityTypeRunning).
        workout_start: Workout start date.
        workout_end: Workout end date.
        workout_duration: Workout duration in minutes.
        source_name: Source name for the workout.
        elevation_cm: Evelation in centimeters for the default activity.
        include_default_statistics: Whether to include default workout statistics (distance, etc).

    Returns:
        Complete HealthData XML string.
    """
    # If workouts are provided directly, use them
    if workouts is not None:
        workouts_xml = "\n".join(workouts)
        return f"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData version="11">
    <ExportDate value="2026-01-20 22:00:00 +0100"/>
    <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01" HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexMale"/>
{workouts_xml}
</HealthData>
"""

    # Otherwise, build a single workout from activities (backward compatibility)
    if activities is None:
        activities = [
            build_workout_activity(
                activity_type=activity_type,
                distance=16.1244 if get_distance_field_for_activity(activity_type) else None,
                elevation_cm=elevation_cm,
                heart_rate_stats={"average": "140.139", "minimum": "75", "maximum": "157"},
            )
        ]

    # Build optional default statistics
    statistics = None
    if include_default_statistics:
        statistics = [
            f'<WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" startDate="{workout_start}" endDate="{workout_end}" sum="17599" unit="count"/>',
            f'<WorkoutStatistics type="HKQuantityTypeIdentifierRunningGroundContactTime" startDate="{workout_start}" endDate="{workout_end}" average="323.718" minimum="224" maximum="369" unit="ms"/>',
            f'<WorkoutStatistics type="HKQuantityTypeIdentifierRunningPower" startDate="{workout_start}" endDate="{workout_end}" average="222.789" minimum="61" maximum="479" unit="W"/>',
            f'<WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="{workout_start}" endDate="{workout_end}" sum="1389.98" unit="kcal"/>',
            f'<WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" startDate="{workout_start}" endDate="{workout_end}" sum="16.1244" unit="km"/>',
            f'<WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" startDate="{workout_start}" endDate="{workout_end}" average="140.139" minimum="75" maximum="157" unit="count/min"/>',
        ]

    # Build metadata entries
    metadata = [
        '<MetadataEntry key="HKIndoorWorkout" value="0"/>',
        '<MetadataEntry key="HKTimeZone" value="Europe/Paris"/>',
        '<MetadataEntry key="HKWeatherHumidity" value="9400 %"/>',
        '<MetadataEntry key="HKWeatherTemperature" value="47.6418 degF"/>',
        '<MetadataEntry key="HKAverageMETs" value="9.66668 kcal/hr·kg"/>',
    ]

    # Build events
    events = [
        f'<WorkoutEvent type="HKWorkoutEventTypeSegment" date="{workout_start}" duration="8.048923822244008" durationUnit="min"/>'
    ]

    workout_xml = build_workout(
        activity_type=activity_type,
        workout_start=workout_start,
        workout_end=workout_end,
        workout_duration=workout_duration,
        source_name=source_name,
        activities=activities,
        include_route=include_route,
        statistics=statistics,
        metadata=metadata,
        events=events,
    )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<HealthData version="11">
    <ExportDate value="2026-01-20 22:00:00 +0100"/>
    <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01" HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexMale"/>
{workout_xml}
</HealthData>
"""


@pytest.fixture
def build_complex_xml() -> Callable[..., str]:
    """Fixture that provides the build_health_xml function for constructing complex test XMLs."""
    return build_health_xml


# Centralized default XML structure
DEFAULT_XML = build_health_xml()


@pytest.fixture
def create_health_zip() -> Generator[Callable[[str], str], None, None]:
    """
    Factory fixture to generate a health export ZIP file.
    Usage: zip_path = create_health_zip([optional_xml_string])
    """
    temp_dirs: list[str] = []

    def _generate(xml_content: str = DEFAULT_XML) -> str:
        # Create a unique temp directory for this specific file
        temp_dir = tempfile.mkdtemp()
        temp_dirs.append(temp_dir)

        zip_path = Path(temp_dir) / "export.zip"
        internal_path = "apple_health_export/export.xml"

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            zipf.writestr(internal_path, xml_content)

        return str(zip_path)

    yield _generate

    # Cleanup after the test is finished
    for d in temp_dirs:
        shutil.rmtree(d, ignore_errors=True)


@pytest.fixture
def mock_file_picker_context() -> Callable[[Optional[str]], ContextManager[None]]:
    """
    Fixture providing a Context Manager to mock-up LocalFilePicker.
    """

    @contextlib.contextmanager
    def _mocker(return_path: Optional[str] = None) -> Iterator[None]:
        target = "ui.layout.LocalFilePicker"
        result_value: List[str] = [return_path] if return_path else []

        async def _simulated_picker(*args: Any, **kwargs: Any):  # pylint: disable=unused-argument
            return result_value

        with patch(target) as mock_class:
            mock_instance = MagicMock()

            future: asyncio.Future[List[str]] = asyncio.Future()
            future.set_result(result_value)

            mock_instance.__await__ = future.__await__

            mock_class.return_value = mock_instance
            mock_class.side_effect = _simulated_picker

            yield

    return _mocker


@pytest.fixture(autouse=True, scope="session")
def setup_test_environment():
    """Fixture to set up a temporary NiceGUI storage path for tests."""
    test_dir = tempfile.mkdtemp()
    os.environ["NICEGUI_STORAGE_PATH"] = test_dir

    yield

    shutil.rmtree(test_dir, ignore_errors=True)


@pytest.fixture
def assert_ui_state() -> StateAssertion:
    """
    Helper fixture to verify the state of a NiceGUI element.
    Using a Protocol instead of Callable to support optional arguments
    without triggering 'Expected more positional arguments' errors.
    """

    def _assert(
        interaction: UserInteraction[Any],
        enabled: Optional[bool] = None,
        visible: Optional[bool] = None,
    ) -> None:
        # Check if any elements were found
        assert interaction.elements, f"No elements found for: {interaction}"

        # Get the underlying element
        element = next(iter(interaction.elements))

        # 1. Check Visibility
        if visible is not None:
            actual_visible = element.visible
            state_str = "visible" if visible else "hidden"
            assert actual_visible == visible, f"Element should be {state_str}."

        # 2. Check Enabled state
        if enabled is not None:
            # Cast to Any to access protected member _props
            element_any: Any = element
            is_disabled = element_any._props.get(  # pylint: disable=protected-access
                "disable", False
            )
            actual_enabled = not is_disabled
            state_str = "enabled" if enabled else "disabled"
            assert actual_enabled == enabled, f"Element should be {state_str}."

    return _assert


# --- Global Patch to prevent WinError 32 during teardown ---
PersistentDict = getattr(nicegui.storage, "PersistentDict")
original_clear = PersistentDict.clear


def patched_clear(self: Any) -> None:
    """
    Safely clear NiceGUI storage by ignoring Windows file locks.
    Calls the original dictionary clear directly to avoid recursion.
    """
    # Attempt to resolve the path attribute safely
    path = getattr(self, "path", getattr(self, "_path", None))

    if path is not None:
        path_str = str(path)
        if os.path.exists(path_str):
            if os.path.isdir(path_str):
                # Using list() to avoid issues with glob iterator
                for filepath in list(path.glob("storage-*.json")):
                    try:
                        os.remove(str(filepath))
                    except (PermissionError, OSError) as exc:
                        # Ignore file removal errors, which can happen due to Windows file locks.
                        logging.debug(
                            "Ignoring storage file removal error for %s: %s", filepath, exc
                        )
            elif os.path.isfile(path_str):
                try:
                    os.remove(path_str)
                except (PermissionError, OSError) as exc:
                    # Ignore file removal errors, which can happen due to Windows file locks.
                    logging.debug("Ignoring storage file removal error for %s: %s", path_str, exc)

    # 2. Instead of calling self.clear(), we call the original dict method
    # This satisfies the linter AND prevents the RecursionError
    dict.clear(self)  # type: ignore


# 3. Apply the patch
PersistentDict.clear = patched_clear


@pytest.fixture(autouse=True)
def reset_app_state():
    """Fixture to reset the application state before each test."""
    app_state.reset()


Storage = nicegui.storage.Storage


class NiceGUIErrorFilter(logging.Filter):
    """
    Filter to intercept and block specific known error messages from NiceGUI
    that are harmless during test teardown but cause pytest failures.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        # Convert message and exception info to string for searching
        # record.getMessage() gets the main message
        log_message = record.getMessage()

        # 1. Block the "Client deleted" error (Race condition on refresh)
        if "The client this element belongs to has been deleted" in log_message:
            return False  # Return False to DROP this log record

        # 2. Block the "binding_refresh_interval" error (Config corruption on exit)
        if "binding_refresh_interval" in log_message:
            return False

        # Allow all other logs
        return True


@pytest.fixture(autouse=True)
def filter_nicegui_errors() -> Generator[None, None, None]:
    """
    Automatically attach the custom error filter to the NiceGUI logger
    for every test.
    """
    # Get the main NiceGUI logger
    logger = logging.getLogger("nicegui")

    # Create and add our firewall
    error_filter = NiceGUIErrorFilter()
    logger.addFilter(error_filter)

    yield

    # Clean up: remove the filter to avoid side effects if we run other things later
    logger.removeFilter(error_filter)
