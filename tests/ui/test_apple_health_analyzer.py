"""Tests for the Apple Health Analyzer main GUI module."""

import asyncio
import json
from typing import Callable, Any, cast

from nicegui.testing import User
from nicegui import ui

from tests.types_helper import StateAssertion


def is_valid_json(data_string: str) -> bool:
    """Check if a string is valid JSON."""
    try:
        json.loads(data_string)
        return True
    except (json.JSONDecodeError, TypeError):
        return False


def is_valid_csv(data_string: str, expected_column: str = "") -> bool:
    """Check if a string is valid CSV."""
    first_line = data_string.splitlines()[0] if data_string else ""

    for delimiter in [",", ";"]:
        if delimiter in first_line:
            if expected_column and expected_column in first_line.split(delimiter):
                return True
            if not expected_column:
                return True
    return False


class TestMainWindow:
    """Integration tests for the main CLI."""

    async def test_click_browse(self, user: User) -> None:
        """Test that the browse button works."""
        await user.open("/")
        await user.should_see("Apple Health Analyzer")
        user.find("Browse").click()
        await user.should_see("Ok")

    async def test_load_without_file(self, user: User) -> None:
        """Test that loading without selecting a file shows a notification."""
        await user.open("/")
        await user.should_see("Apple Health Analyzer")
        user.find("Load").click()
        await user.should_see("Please select an Apple Health export file first.")

    async def test_load_with_non_existent_file(self, user: User) -> None:
        """Test that loading a non-existent file shows an error notification."""

        await user.open("/")
        await user.should_see("Apple Health Analyzer")
        user.find("Apple Health export file").type("invalid_export.zip")
        user.find("Load").click()
        await user.should_see("No such file or directory")

    async def test_load_with_valid_file(
        self, user: User, create_health_zip: Callable[..., str]
    ) -> None:
        """Test that loading a valid export file shows statistics."""
        await user.open("/")
        # 1. Prepare the input
        zip_path = create_health_zip()
        user.find("Apple Health export file").type(zip_path)

        # 2. Trigger the processing
        user.find("Load").click()

        # 3. Robust check: Wait for the log to confirm start
        # This confirms the click was registered and the function is running
        await user.should_see("Starting to parse", retries=20)

        # 4. Critical step: Wait for the processing to finish
        # We use a higher retry count (100 * 0.1s = 10s) to handle slow CI runners.
        await user.should_see("Finished parsing", retries=100)

        # 5.Check if the UI correctly displays data from our XML
        await user.should_see("Total distance of 16", retries=50)
        await user.should_see("Total duration of 1h")

    async def test_browse_button_opens_picker(self, user: User) -> None:
        """Test that the browse button opens the file picker dialog."""
        await user.open("/")
        await user.should_see("Apple Health Analyzer")
        user.find("Browse").click()
        await user.should_see("Ok")
        # Small delay to ensure Windows releases file handles before teardown
        await asyncio.sleep(0.2)

    async def test_input_file_persists_in_storage(self, user: User) -> None:
        """Test that the input file path is persisted in app storage."""
        await user.open("/")
        user.find("Apple Health export file").type("tests/fixtures/export_sample.zip")
        await user.open("/")
        await user.should_see("tests/fixtures/export_sample.zip")

    async def test_parse_error_shows_notification(self, user: User) -> None:
        """Test that parse errors display error notification."""
        await user.open("/")
        user.find("Apple Health export file").type("tests/fixtures/corrupt_export.zip")
        user.find("Load").click()
        await user.should_see("Error parsing file")

    async def test_browse_no_file_selected(
        self, user: User, mock_file_picker_context: Any
    ) -> None:
        """Test that not selecting a file (mock returns empty) shows a notification."""

        with mock_file_picker_context(None):  # None = empty result
            await user.open("/")
            user.find("Browse").click()

            # Wait for the async operation
            await asyncio.sleep(0.5)

            # Should see "No file selected" notification
            await user.should_see("No file selected")

    async def test_browse_file_selected(
        self, user: User, mock_file_picker_context: Any
    ) -> None:
        """Test that selecting a file via the dialog updates the input_file value."""
        fake_path = "/path/to/fake_health_export.zip"

        with mock_file_picker_context(fake_path):
            await user.open("/")

            # Verify input is initially empty
            input_elements = list(user.find("Apple Health export file").elements)
            input_field = input_elements[0] if input_elements else None
            assert input_field is not None
            actual_value = input_field.value  # type: ignore[union-attr]
            assert actual_value == "", "Input should start empty"

            # Click Browse
            user.find("Browse").click()
            await asyncio.sleep(1.0)

            # Check if value was set
            assert fake_path in input_field.value, (  # type: ignore[union-attr]
                f"Expected {fake_path} in {input_field.value}"  # type: ignore[union-attr]
            )

    async def test_export_dropdown_has_json_option(self, user: User) -> None:
        """Test that the export dropdown contains the 'to JSON' option."""
        await user.open("/")

        # 1. Open the export dropdown
        export_button = user.find("Export data")
        assert export_button is not None, "Export data button not found"
        export_button.click()
        await asyncio.sleep(0.2)

        # 2. Verify the "to JSON" menu item is present
        json_option = user.find("to JSON")
        assert json_option is not None, "to JSON export option not found"

    async def test_export_dropdown_has_csv_option(self, user: User) -> None:
        """Test that the export dropdown contains the 'to CSV' option."""
        await user.open("/")

        # 1. Open the export dropdown
        export_button = user.find("Export data")
        assert export_button is not None, "Export data button not found"
        export_button.click()
        await asyncio.sleep(0.2)

        # 2. Verify the "to CSV" menu item is present
        csv_option = user.find("to CSV")
        assert csv_option is not None, "to CSV export option not found"

    async def test_export_to_json_click_executes(
        self,
        user: User,
        create_health_zip: Callable[..., str],
        assert_ui_state: StateAssertion,
    ) -> None:
        """Test that clicking 'Export data > to JSON' can be executed without errors.

        This integration test verifies:
        1. The export dropdown button is accessible after file loads
        2. The "to JSON" menu item can be clicked without throwing an exception
        3. The parser's export_to_json method works correctly
        """
        await user.open("/")

        # Load a valid health data file
        zip_path = create_health_zip()
        user.find("Apple Health export file").type(zip_path)
        user.find("Load").click()

        # Wait for parsing to complete
        await user.should_see("Finished parsing", retries=100)

        # Verify the export dropdown is present
        export_interaction = user.find("Export data")
        assert_ui_state(export_interaction, enabled=True)
        export_interaction.click()
        await asyncio.sleep(0.5)

        # Verify the "to JSON" menu item exists
        await user.should_see("to JSON")

        # Click the export button (this should trigger the download without error)
        user.find("to JSON").click()

        found = False
        for _ in range(30):  # Wait up to 3 seconds (30 * 0.1s)
            if user.download.http_responses:
                found = True
                break
            await asyncio.sleep(0.1)

        assert found, "No download was triggered"

        res = user.download.http_responses[-1]
        assert res.status_code == 200
        assert is_valid_json(res.text)

    async def test_export_to_csv_click_executes(
        self,
        user: User,
        create_health_zip: Callable[..., str],
        assert_ui_state: StateAssertion,
    ) -> None:
        """Test that clicking 'Export data > to CSV' can be executed without errors.

        This integration test verifies:
        1. The export dropdown button is accessible after file loads
        2. The "to CSV" menu item can be clicked without throwing an exception
        3. The parser's export_to_csv method works correctly
        """
        await user.open("/")

        # Load a valid health data file
        zip_path = create_health_zip()
        user.find("Apple Health export file").type(zip_path)
        user.find("Load").click()

        # Wait for parsing to complete
        await user.should_see("Finished parsing", retries=100)

        # Verify the export dropdown is present
        export_interaction = user.find("Export data")
        assert_ui_state(export_interaction, enabled=True)
        export_interaction.click()
        await asyncio.sleep(0.2)

        # Verify the "to CSV" menu item exists
        await user.should_see("to CSV")

        # Click the export button (this should trigger the download without error)
        user.find("to CSV").click()

        found = False
        for _ in range(30):  # Wait up to 3 seconds (30 * 0.1s)
            if user.download.http_responses:
                found = True
                break
            await asyncio.sleep(0.1)

        assert found, "No download was triggered"

        res = user.download.http_responses[-1]
        assert res.status_code == 200
        assert is_valid_csv(res.text)

    async def test_export_without_loading_file_is_disabled(
        self, user: User, assert_ui_state: StateAssertion
    ) -> None:
        """Test that the export dropdown is disabled when no file is loaded."""
        await user.open("/")

        export_interaction = user.find("Export data")
        assert_ui_state(export_interaction, enabled=False)

    async def test_activity_filter_checkbox_rendering(
        self, user: User, create_health_zip: Callable[..., str]
    ) -> None:
        """Test that activity filter checkboxes are rendered correctly after loading data."""

        await user.open("/")

        # 1. Load a valid health data file
        zip_path = create_health_zip()
        user.find("Apple Health export file").type(zip_path)
        user.find("Load").click()

        # 2. Wait for parsing to complete
        await user.should_see("Finished parsing", retries=100)

        # 3. Verify the activities section is present
        select = cast(ui.select, user.find("Activity Type").elements.pop())
        assert select.options == ["All", "Running"]  # type: ignore
