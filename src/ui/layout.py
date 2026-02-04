"""UI layout components for Apple Health Analyzer application."""

import asyncio
from concurrent.futures import ThreadPoolExecutor  # pylint: disable=no-name-in-module

from nicegui import app, ui

from app_state import state
from assets import APP_ICON_BASE64
from logic.export_parser import ExportParser
from logic.workout_manager import WorkoutManager
from ui.local_file_picker import LocalFilePicker


def handle_json_export() -> None:
    """Handle exporting data to JSON format."""
    print("Export to JSON")
    json_data = state.workouts.export_to_json()
    ui.download(json_data.encode("utf-8"), "apple_health_export.json")


def handle_csv_export() -> None:
    """Handle exporting data to CSV format."""
    print("Export to CSV")
    csv_data = state.workouts.export_to_csv()
    ui.download(csv_data.encode("utf-8"), "apple_health_export.csv")


def refresh_data() -> None:
    """Refresh the displayed data."""
    state.metrics["count"] = state.workouts.count(state.selected_activity_type)
    state.metrics["distance"] = state.workouts.get_total_distance(state.selected_activity_type)
    state.metrics["duration"] = state.workouts.get_total_duration(state.selected_activity_type)
    state.metrics["elevation"] = state.workouts.get_total_elevation(state.selected_activity_type)


def _update_activity_filter(new_value: str) -> None:
    state.selected_activity_type = new_value
    refresh_data()


@ui.refreshable
def render_activity_select() -> None:
    """Render the activity type selection dropdown."""

    ui.select(
        options=state.activity_options,
        on_change=lambda e: _update_activity_filter(e.value),
        value=state.selected_activity_type,
        label="Activity Type",
    ).classes("w-40").bind_enabled_from(state, "file_loaded")


def render_left_drawer() -> None:
    """Generate the left drawer with filters."""

    with ui.left_drawer():
        ui.label("Activities")
        render_activity_select()

        ui.separator()

        ui.label("Date Range")

        months = [
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
        ]
        years = [2024, 2025, 2026]
        with ui.row().classes("items-center gap-2"):
            ui.label("From").classes("text-sm text-muted")
            ui.select(months, value="Jan").classes("w-20").props("dense flat").props("disable")
            ui.select(years, value=2025).classes("w-24").props("dense flat").props("disable")

            ui.label("to").classes("text-sm text-muted")
            ui.select(months, value="Dec").classes("w-20").props("dense flat").props("disable")
            ui.select(years, value=2025).classes("w-24").props("dense flat").props("disable")

        ui.separator()
        with ui.dropdown_button("Export data", icon="download").bind_enabled_from(
            state, "file_loaded"
        ):
            ui.button("to JSON", on_click=handle_json_export).props("flat").classes("w-full")
            ui.button("to CSV", on_click=handle_csv_export).props("flat").classes("w-full")


def render_header() -> None:
    """Generate the application header with a dark mode toggle."""
    dark = ui.dark_mode()
    with ui.header().classes("items-center justify-between border-b"):
        ui.image(APP_ICON_BASE64).classes("w-16 h-16")
        ui.label("Apple Health Analyzer").classes("font-bold text-xl")

        # Toggle button with dynamic icon
        ui.button(icon="dark_mode", on_click=dark.enable).bind_visibility_from(
            dark, "value", backward=lambda v: not v
        ).props("flat round")
        ui.button(icon="light_mode", on_click=dark.disable).bind_visibility_from(
            dark, "value"
        ).props("flat round").classes("text-main")


def stat_card(label: str, value_ref: dict[str, int], key: str, unit: str = ""):
    """
    Create a reactive KPI card.
    'value_ref' is a dictionary containing the totals,
    allowing automatic updates via NiceGUI binding.
    """
    with ui.card().classes("w-32 h-24 items-center justify-center shadow-sm"):
        ui.label(label).classes("text-xs text-gray-500 uppercase")
        with ui.row().classes("items-baseline gap-1"):
            # Bind the text to the dictionary key for reactive updates
            ui.label().classes("text-xl font-bold").bind_text_from(value_ref, key)
            if unit:
                ui.label(unit).classes("text-xs text-gray-400")


async def pick_file() -> None:
    """Open a file picker dialog to select the Apple Health export file."""
    result: list[str] = await LocalFilePicker("~", multiple=False, file_filter=".zip")

    if not result:
        ui.notify("No file selected")
        return

    state.input_file.value = result[0]


def load_workouts_from_file(file_path: str) -> None:
    """Load and parse the Apple Health export file."""
    with ExportParser() as ep:
        state.workouts = WorkoutManager(ep.parse(file_path, log=state.log))


async def load_file() -> None:
    """Load and parse the selected Apple Health export file."""
    if state.input_file.value == "":
        ui.notify("Please select an Apple Health export file first.")
        return

    try:
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            await loop.run_in_executor(
                executor,
                lambda: load_workouts_from_file(state.input_file.value),
            )
        state.log.push(state.workouts.get_statistics())
        ui.notify("File parsed successfully.")
        state.file_loaded = True
        activity_types = state.workouts.get_activity_types()
        activity_types.sort()
        state.activity_options = ["All"] + activity_types
        render_activity_select.refresh()
        refresh_data()
    except Exception as e:  # pylint: disable=broad-except
        ui.notify(f"Error parsing file: {e}")


def render_body() -> None:
    """Generate the main body of the application."""
    with ui.row().classes("w-full items-center"):
        state.input_file = (
            ui.input(
                "Apple Health export file",
                placeholder="Select an Apple Health export file...",
            )
            .classes("flex-grow")
            .bind_value(app.storage.user, "input_file_path")
        )
        ui.button("Browse", on_click=pick_file, icon="folder_open")

    with ui.row().classes("w-full items-center"):
        ui.button("Load", on_click=load_file, icon="play_arrow").classes("flex-grow")

    with ui.tabs().classes("w-full") as tabs:
        tab_summary = ui.tab("Overview")
        ui.tab("Activities").props("disable")
        ui.tab("Health Data").props("disable")
        ui.tab("Trends").props("disable")

    with ui.tab_panels(tabs, value=tab_summary).classes("w-full"):
        with ui.tab_panel(tab_summary):
            with ui.row().classes("w-full justify-center gap-4"):
                stat_card("Count", state.metrics, "count")
                stat_card("Distance", state.metrics, "distance", "km")
                stat_card("Duration", state.metrics, "duration", "h")
                stat_card("Elevation", state.metrics, "elevation", "m")
