"""Fixtures for testing Apple Health Analyzer."""

import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Callable, Generator, Any, Optional, Protocol

import nicegui.storage
from nicegui.testing import UserInteraction
import pytest

import local_file_picker
import apple_health_analyzer as aha_module

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


def create_mock_file_picker(return_path: str | None = None) -> Callable[..., Any]:
    """Create a mock LocalFilePicker that returns the given path.

    Args:
        return_path: The file path to return, or None for empty result.
    """

    def mock_picker(*args: Any, **kwargs: Any) -> Any:  # pylint: disable=unused-argument
        class MockFilePicker:
            """Mock class for LocalFilePicker."""

            def __init__(self, *init_args: Any, **init_kw: Any) -> None:  # pylint: disable=unused-argument
                pass

            async def __aenter__(self) -> "MockFilePicker":
                return self

            async def __aexit__(self, *exit_args: Any) -> None:  # pylint: disable=unused-argument
                pass

            def __await__(self) -> Generator[Any, None, list[str]]:
                async def _return_file() -> list[str]:
                    if return_path:
                        return [return_path]
                    return []

                return _return_file().__await__()  # type: ignore # pylint: disable=no-member

        return MockFilePicker()

    return mock_picker


@pytest.fixture
def mock_file_picker_context() -> Callable[[str | None], Any]:
    """Context manager for temporarily mocking LocalFilePicker.

    Usage:
        with mock_file_picker_context("/path/to/file.zip") as original:
            # Test code here
    """

    original = local_file_picker.LocalFilePicker

    def _context_manager(return_path: str | None = None) -> Any:
        class _Ctx:
            def __enter__(self) -> Any:
                mock_picker = create_mock_file_picker(return_path)
                local_file_picker.LocalFilePicker = mock_picker  # type: ignore[assignment]
                aha_module.LocalFilePicker = mock_picker  # type: ignore[attr-defined]
                return original

            def __exit__(self, *args: Any) -> None:  # pylint: disable=unused-argument
                local_file_picker.LocalFilePicker = original
                aha_module.LocalFilePicker = original  # type: ignore[attr-defined]

        return _Ctx()

    return _context_manager


@pytest.fixture(autouse=True, scope="session")
def cleanup_windows_storage():
    """Fixture to clean up NiceGUI storage on Windows after tests."""
    yield
    temp_storage = Path(".nicegui")
    if temp_storage.exists():
        shutil.rmtree(temp_storage, ignore_errors=True)


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


def patched_clear(self: Any) -> None:
    """
    Safely clear NiceGUI storage by ignoring Windows file locks.
    This prevents PermissionError (WinError 32) during pytest teardown.
    """
    if not self.path.exists():
        return

    for filepath in self.path.glob("storage-*.json"):
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except (PermissionError, OSError):
            # Silently ignore locked files on Windows.
            # These are temp files and will be cleared by the OS/Session cleanup.
            pass


# Apply the monkeypatch to the class
PersistentDict.clear = patched_clear
