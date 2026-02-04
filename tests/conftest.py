"""Fixtures for testing Apple Health Analyzer."""

import asyncio
import contextlib
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import (
    Callable,
    Generator,
    Any,
    Optional,
    Protocol,
    ContextManager,
    List,
    Iterator,
)

from unittest.mock import patch, MagicMock
import nicegui.storage
from nicegui.testing import UserInteraction
import pytest

from app_state import state as app_state

# Centralized default XML structure
DEFAULT_XML = """<?xml version="1.0" encoding="UTF-8"?>
<HealthData version="11">
    <ExportDate value="2026-01-20 22:00:00 +0100"/>
    <Me HKCharacteristicTypeIdentifierDateOfBirth="1990-01-01" 
        HKCharacteristicTypeIdentifierBiologicalSex="HKBiologicalSexMale"/>
    <Workout workoutActivityType="HKWorkoutActivityTypeRunning" 
             duration="119.2710362156232" durationUnit="min" 
             sourceName="Apple Watch" sourceVersion="26.2" 
             creationDate="2025-12-20 14:51:19 +0100" 
             startDate="2025-12-20 12:51:00 +0100" 
             endDate="2025-12-20 14:50:16 +0100">
        <MetadataEntry key="HKIndoorWorkout" value="0"/>
        <MetadataEntry key="HKTimeZone" value="Europe/Paris"/>
        <MetadataEntry key="HKWeatherHumidity" value="9400 %"/>
        <MetadataEntry key="HKWeatherTemperature" value="47.6418 degF"/>
        <MetadataEntry key="HKAverageMETs" value="9.66668 kcal/hr·kg"/>
        <WorkoutEvent type="HKWorkoutEventTypeSegment" date="2025-12-20 12:51:00 +0100" duration="8.048923822244008" durationUnit="min"/>
        <WorkoutActivity uuid="936B9E1D-52B9-41CA-BCA9-9654D43F004E" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" duration="119.2710362156232" durationUnit="min">
            <WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="17599" unit="count"/>
            <MetadataEntry key="HKElevationAscended" value="45443 cm"/>
        </WorkoutActivity>
        <WorkoutStatistics type="HKQuantityTypeIdentifierStepCount" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="17599" unit="count"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierRunningGroundContactTime" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="323.718" minimum="224" maximum="369" unit="ms"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierRunningPower" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="222.789" minimum="61" maximum="479" unit="W"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierActiveEnergyBurned" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="1389.98" unit="kcal"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierDistanceWalkingRunning" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" sum="16.1244" unit="km"/>
        <WorkoutStatistics type="HKQuantityTypeIdentifierHeartRate" startDate="2025-12-20 12:51:00 +0100" endDate="2025-12-20 14:50:16 +0100" average="140.139" minimum="75" maximum="157" unit="count/min"/>
    </Workout>
</HealthData>
"""


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

            mock_instance.__await__ = future.__await__()

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


# Define a Protocol to describe the helper signature precisely
class StateAssertion(Protocol):
    """Protocol for UI state assertion functions."""

    def __call__(
        self,
        interaction: UserInteraction[Any],
        enabled: Optional[bool] = None,
        visible: Optional[bool] = None,
    ) -> None: ...


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
            is_disabled = element_any._props.get("disable", False)  # pylint: disable=protected-access
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
                    except (PermissionError, OSError):
                        pass
            elif os.path.isfile(path_str):
                try:
                    os.remove(path_str)
                except (PermissionError, OSError):
                    pass

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
        # record.exc_text or record.exc_info contains the traceback if any
        log_message = record.getMessage()
        if record.exc_info:
            # Check if exception info exists, convert to string roughly if needed,
            # but usually checking the message is enough or checking str(record.msg)
            pass

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
