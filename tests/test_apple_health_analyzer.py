"""Tests for the Apple Health Analyzer main GUI module."""

import asyncio
import os
import tempfile
from typing import Callable, Any

from nicegui.testing import User


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
        with tempfile.TemporaryDirectory() as tmpdirname:
            # Create a dummy zip file
            zip_name = "test_data.zip"
            zip_path = os.path.join(tmpdirname, zip_name)
            with open(zip_path, "w", encoding="utf-8") as f:
                f.write("dummy content")

            with mock_file_picker_context(zip_path):
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
                assert zip_path in input_field.value, (  # type: ignore[union-attr]
                    f"Expected {zip_path} in {input_field.value}"  # type: ignore[union-attr]
                )
