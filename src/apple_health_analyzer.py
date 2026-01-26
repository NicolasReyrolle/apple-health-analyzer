#!/usr/bin/env python3
"""
Apple Health Analyzer GUI

A graphical user interface for analyzing Apple Health data.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor  # pylint: disable=no-name-in-module
from typing import Any

from nicegui import ui, app

from assets import APP_ICON_BASE64
from export_parser import ExportParser

import apple_health_analyzer as _module
from local_file_picker import LocalFilePicker

parser: ExportParser = ExportParser()


@ui.page("/")
def welcome_page() -> None:
    """Welcome page for the Apple Health Analyzer."""

    async def pick_file() -> None:
        """Open a file picker dialog to select the Apple Health export file."""
        # Use a module-level lookup to allow for testing with mocks
        picker_class: Any = getattr(_module, "LocalFilePicker", None)
        if picker_class is None:
            picker_class = LocalFilePicker
        result: list[str] = await picker_class("~", multiple=False, file_filter=".zip")
        if not result:
            ui.notify("No file selected")
            return

        input_file.value = result[0]

    async def load_file() -> None:
        """Load and parse the selected Apple Health export file."""
        if input_file.value == "":
            ui.notify("Please select an Apple Health export file first.")
            return

        try:
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                await loop.run_in_executor(
                    executor, lambda: parser.parse(input_file.value, log=log)
                )
            log.push(parser.get_statistics())
            ui.notify("File parsed successfully.")
        except Exception as e:  # pylint: disable=broad-except
            ui.notify(f"Error parsing file: {e}")

    with ui.row().classes("w-full items-center"):
        ui.image(APP_ICON_BASE64).classes("w-16 h-16")
        ui.label("Apple Health Analyzer")

    with ui.row().classes("w-full items-center"):
        input_file = (
            ui.input(
                "Apple Health export file",
                placeholder="Select an Apple Health export file...",
            )
            .classes("flex-grow")
            .bind_value(app.storage.user, "input_file_path")
        )
        ui.button("Browse", on_click=pick_file, icon="folder_open")

    with ui.row().classes("w-full items-center mt-4"):
        ui.button("Load", on_click=load_file, icon="play_arrow").classes("flex-grow")

    log = ui.log(max_lines=10).classes("w-full h-20")


def main() -> None:
    """Main entry point for the application."""

    ui.run(  # type: ignore[misc]
        title="Apple Health Analyzer",
        favicon=APP_ICON_BASE64,
        storage_secret=os.getenv("STORAGE_SECRET", "default-dev-key"),
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
