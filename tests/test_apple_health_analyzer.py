"""Tests for the Apple Health Analyzer main GUI module."""

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

    async def test_load_with_valid_file(self, user: User) -> None:
        """Test that loading a valid export file shows statistics."""
        await user.open("/")
        await user.should_see("Apple Health Analyzer")
        user.find("Apple Health export file").type("tests/fixtures/export_sample.zip")
        user.find("Load").click()
        await user.should_see("No running workouts loaded", retries=50)

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
