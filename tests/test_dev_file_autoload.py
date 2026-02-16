"""Tests for dev file auto-load functionality.

These tests verify the auto-load mechanism that loads a dev file automatically
when specified via the --dev-file CLI argument and stored in app.storage.general.

The tests verify:
1. Dev file is auto-loaded on first page load when present in app.storage
2. Dev file is NOT reloaded on page refresh after successful load
3. Dev file path is cleared from app.storage after successful load
4. Auto-load does not trigger if file is already loaded
"""

import asyncio
from typing import Callable

from nicegui import app
from nicegui.testing import User

from app_state import state


class TestDevFileAutoLoad:
    """Tests for automatic dev file loading functionality."""

    async def test_dev_file_auto_loads_on_first_visit(
        self, user: User, create_health_zip: Callable[..., str]
    ) -> None:
        """Test that dev file is automatically loaded on first page visit."""
        # Create a valid test file
        zip_path = create_health_zip()

        # Simulate dev file being set in app storage (as done by cli_main)
        app.storage.general["_dev_file_path"] = zip_path  # type: ignore[index]

        try:
            # Open the page - this should trigger auto-load
            await user.open("/")

            # Wait for the file to be auto-loaded (timer is 1 second + parsing time)
            await user.should_see("Finished parsing", retries=100)

            # Verify the file was actually loaded
            assert state.file_loaded is True
            assert state.metrics["count"] == 1

            # Verify the dev file path was cleared from storage after successful load
            dev_file_in_storage = app.storage.general.get(  # type: ignore[no-untyped-call]
                "_dev_file_path"
            )
            assert (
                dev_file_in_storage is None
            ), "Dev file should be cleared from storage after load"

        finally:
            # Clean up storage
            if "_dev_file_path" in app.storage.general:  # type: ignore[operator]
                del app.storage.general["_dev_file_path"]  # type: ignore[attr-defined]

        await asyncio.sleep(0.2)

    async def test_dev_file_does_not_reload_on_page_refresh(
        self, user: User, create_health_zip: Callable[..., str]
    ) -> None:
        """Test that dev file is NOT reloaded when user refreshes the page."""
        # Create a valid test file
        zip_path = create_health_zip()

        # Simulate dev file being set in app storage
        app.storage.general["_dev_file_path"] = zip_path  # type: ignore[index]

        try:
            # First visit - should auto-load
            await user.open("/")
            await user.should_see("Finished parsing", retries=100)
            assert state.file_loaded is True

            # Dev file should be cleared from storage
            dev_file_in_storage = app.storage.general.get(  # type: ignore[no-untyped-call]
                "_dev_file_path"
            )
            assert dev_file_in_storage is None

            # Reset state to simulate what happens on page refresh
            # (state persists but we open the page again)
            original_file_loaded = state.file_loaded

            # Simulate page refresh - open the same page again
            await user.open("/")
            await asyncio.sleep(2)  # Wait longer than the auto-load timer

            # File should NOT be reloaded because:
            # 1. state.file_loaded is still True
            # 2. _dev_file_path was cleared from storage
            assert state.file_loaded == original_file_loaded

        finally:
            # Clean up storage
            if "_dev_file_path" in app.storage.general:  # type: ignore[operator]
                del app.storage.general["_dev_file_path"]  # type: ignore[attr-defined]

        await asyncio.sleep(0.2)

    async def test_auto_load_skipped_if_file_already_loaded(
        self, user: User, create_health_zip: Callable[..., str]
    ) -> None:
        """Test that auto-load is skipped if state.file_loaded is already True."""
        # Create a valid test file
        zip_path = create_health_zip()

        # Set up a scenario where file is already loaded
        # (e.g., user manually loaded a file, then dev file is set in storage)
        await user.open("/")

        # Manually load a file first
        manual_zip = create_health_zip()
        user.find("Apple Health export file").type(manual_zip)
        user.find("Load").click()
        await user.should_see("Finished parsing", retries=100)

        # Now set dev file in storage (simulating a scenario where it might persist)
        app.storage.general["_dev_file_path"] = zip_path  # type: ignore[index]

        try:
            # Record the current metrics
            original_count = state.metrics["count"]

            # Open page again - auto-load should NOT trigger because file_loaded is True
            await user.open("/")
            await asyncio.sleep(2)  # Wait longer than the auto-load timer

            # Metrics should be unchanged (file not reloaded)
            assert state.metrics["count"] == original_count

        finally:
            # Clean up storage
            if "_dev_file_path" in app.storage.general:  # type: ignore[operator]
                del app.storage.general["_dev_file_path"]  # type: ignore[attr-defined]

        await asyncio.sleep(0.2)

    async def test_auto_load_clears_storage_only_on_success(self, user: User) -> None:
        """Test that dev file path is only cleared from storage after successful load."""
        # Use a non-existent file to force a load failure
        invalid_zip = "/tmp/nonexistent_file.zip"

        # Set dev file in storage
        app.storage.general["_dev_file_path"] = invalid_zip  # type: ignore[index]

        try:
            # Open the page - auto-load will be attempted but will fail
            await user.open("/")

            # Wait for the auto-load attempt
            await asyncio.sleep(2)

            # File should NOT be loaded
            assert state.file_loaded is False

            # Dev file path should still be in storage (not cleared on failure)
            dev_file_in_storage = app.storage.general.get(  # type: ignore[no-untyped-call]
                "_dev_file_path"
            )
            assert dev_file_in_storage == invalid_zip, (
                "Dev file should remain in storage after failed load"
            )

        finally:
            # Clean up storage
            if "_dev_file_path" in app.storage.general:  # type: ignore[operator]
                del app.storage.general["_dev_file_path"]  # type: ignore[attr-defined]

        await asyncio.sleep(0.2)

    async def test_no_auto_load_without_dev_file_in_storage(self, user: User) -> None:
        """Test that auto-load does not trigger when dev file is not in storage."""
        # Ensure no dev file in storage
        if "_dev_file_path" in app.storage.general:  # type: ignore[operator]
            del app.storage.general["_dev_file_path"]  # type: ignore[attr-defined]

        # Open the page
        await user.open("/")
        await asyncio.sleep(2)

        # No file should be loaded
        assert state.file_loaded is False
        assert state.metrics["count"] == 0

        await asyncio.sleep(0.2)
