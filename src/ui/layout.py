"""UI layout components for Apple Health Analyzer application."""

import asyncio
import logging
import re
import time
from collections.abc import Hashable, Mapping, Sequence
from typing import Any, Callable, Optional

import pandas as pd
from nicegui import app, ui

from app_state import state
from assets import APP_ICON_BASE64
from i18n import LANGUAGES, get_language, t
from i18n.activity_types import build_activity_select_options, translate_activity_value_map
from logic.export_parser import ExportParser
from logic.records_by_type import RecordsByType
from logic.workout_manager import (
    HALF_MARATHON_DISTANCE_M,
    MARATHON_DISTANCE_M,
    STANDARD_SEGMENT_DISTANCES,
    WorkoutManager,
)
from ui.helpers import (
    format_date_label,
    format_distance_label,
    format_duration_label,
    format_float,
    format_integer,
    period_code_to_label,
    qdate_locale_json,
)
from ui.local_file_picker import LocalFilePicker

# Get logger for this module
_logger = logging.getLogger(__name__)

# CSS class constants
ROW_CENTERED_CLASSES = "w-full justify-center gap-4"
BUTTON_FLAT_ROUND_PROPS = "flat round"
LABEL_UPPERCASE_CLASSES = "text-sm text-gray-500 uppercase"


def schedule_best_segments_load(force: bool = False) -> None:
    """Schedule best-segments loading and keep a reference to the task."""

    def _clear_completed_task(task: asyncio.Task[None]) -> None:
        if state.best_segments_task is task:
            state.best_segments_task = None

    task: Any = asyncio.create_task(load_best_segments_data(force=force))
    state.best_segments_task = task if hasattr(task, "add_done_callback") else None
    if state.best_segments_task is not None:
        state.best_segments_task.add_done_callback(_clear_completed_task)


def handle_json_export() -> None:
    """Handle exporting data to JSON format."""
    json_data = state.workouts.export_to_json(
        activity_type=state.selected_activity_type,
        start_date=state.start_date,
        end_date=state.end_date,
    )
    ui.download(json_data.encode("utf-8"), "apple_health_export.json")


def handle_csv_export() -> None:
    """Handle exporting data to CSV format."""
    csv_data = state.workouts.export_to_csv(
        activity_type=state.selected_activity_type,
        start_date=state.start_date,
        end_date=state.end_date,
    )
    ui.download(csv_data.encode("utf-8"), "apple_health_export.csv")


def refresh_data() -> None:
    """Refresh the displayed data."""
    _logger.info(
        "Refreshing data: activity_type=%s, start_date=%s, end_date=%s",
        state.selected_activity_type,
        state.start_date,
        state.end_date,
    )

    state.metrics["count"] = state.workouts.get_count(
        state.selected_activity_type, state.start_date, state.end_date
    )
    state.metrics["distance"] = state.workouts.get_total_distance(
        state.selected_activity_type, start_date=state.start_date, end_date=state.end_date
    )
    state.metrics["duration"] = state.workouts.get_total_duration(
        state.selected_activity_type, start_date=state.start_date, end_date=state.end_date
    )
    state.metrics["elevation"] = state.workouts.get_total_elevation(
        state.selected_activity_type, start_date=state.start_date, end_date=state.end_date
    )
    state.metrics["calories"] = state.workouts.get_total_calories(
        state.selected_activity_type, start_date=state.start_date, end_date=state.end_date
    )
    state.metrics["longest_run"] = state.workouts.get_longest_workout(
        ["Running"], start_date=state.start_date, end_date=state.end_date
    )
    state.metrics["longest_walk"] = state.workouts.get_longest_workout(
        ["Walking", "Hiking"], start_date=state.start_date, end_date=state.end_date
    )
    state.metrics["longest_cycling"] = state.workouts.get_longest_workout(
        ["Cycling"], start_date=state.start_date, end_date=state.end_date
    )

    state.metrics_display["count"] = format_integer(state.metrics["count"])
    state.metrics_display["distance"] = format_integer(state.metrics["distance"])
    state.metrics_display["duration"] = format_integer(state.metrics["duration"])
    state.metrics_display["elevation"] = format_integer(state.metrics["elevation"])
    state.metrics_display["calories"] = format_integer(state.metrics["calories"])
    state.metrics_display["longest_run"] = format_float(state.metrics["longest_run"])
    state.metrics_display["longest_walk"] = format_float(state.metrics["longest_walk"])
    state.metrics_display["longest_cycling"] = format_float(state.metrics["longest_cycling"])

    # Invalidate best-segments cache and cancel any in-flight load for stale data.
    best_segments_task: Any = getattr(state, "best_segments_task", None)
    if isinstance(best_segments_task, asyncio.Task) and not best_segments_task.done():
        best_segments_task.cancel()
    # Ensure task and loading flag are reset so a new load can start after refresh.
    state.best_segments_task = None
    if hasattr(state, "best_segments_loading"):
        state.best_segments_loading = False
    state.best_segments_rows = []
    state.best_segments_loaded = False

    render_activity_graphs.refresh()
    render_trends_graphs.refresh()
    render_health_data_tab.refresh()
    render_best_segments_tab.refresh()

    # If user is already on the tab, load asynchronously after invalidation.
    if state.selected_main_tab == "best_segments":
        schedule_best_segments_load()


def _build_best_segments_rows() -> list[dict[str, Any]]:
    """Compute and format best segments rows for tab rendering.

    Returns one row per distance (the #1 record). Runner-up records are stored
    in a ``children`` list so the table can expand them on demand.
    """
    _logger.debug("Calculating best segments for distances: %s", STANDARD_SEGMENT_DISTANCES)
    best_segments = state.workouts.get_best_segments(distances=STANDARD_SEGMENT_DISTANCES)
    _logger.debug("Best segments data:\n%s", best_segments)
    language_code = get_language()

    def _format_entry(distance_m: float, duration_s: float, start_date: Any) -> dict[str, str]:
        average_speed = (distance_m / 1000) / (duration_s / 3600) if duration_s > 0 else 0.0
        return {
            "distance": format_distance_label(
                distance_m,
                language_code,
                HALF_MARATHON_DISTANCE_M,
                MARATHON_DISTANCE_M,
            ),
            "duration": format_duration_label(duration_s),
            "average_speed": f"{average_speed:.2f} km/h",
            "start_date": format_date_label(start_date, language_code),
        }

    rows: list[dict[str, Any]] = []
    for _, group_df in best_segments.groupby("distance", sort=True):
        records = list(group_df.sort_values("duration_s").itertuples(index=False))
        if not records:
            continue

        distance_m = float(getattr(records[0], "distance", 0.0))
        start_date = getattr(records[0], "startDate", None)
        if start_date is None:
            continue

        parent: dict[str, Any] = {
            **_format_entry(distance_m, float(getattr(records[0], "duration_s", 0.0)), start_date),
            "id": str(int(distance_m)),
            "children": [
                _format_entry(
                    distance_m,
                    float(getattr(record, "duration_s", 0.0)),
                    getattr(record, "startDate"),
                )
                for record in records[1:]
                if getattr(record, "startDate", None) is not None
            ],
        }
        rows.append(parent)

    return rows


async def load_best_segments_data(force: bool = False) -> None:
    """Load best segments asynchronously for the tab, with concurrency guard."""
    if state.best_segments_loading:
        return
    if state.best_segments_loaded and not force:
        return
    if not state.file_loaded:
        return

    state.best_segments_loading = True
    render_best_segments_tab.refresh()

    try:
        rows = await asyncio.to_thread(_build_best_segments_rows)
        state.best_segments_rows = rows
        state.best_segments_loaded = True
    except Exception:  # pylint: disable=broad-except
        _logger.exception("Failed to load best segments data")
    finally:
        state.best_segments_loading = False
        render_best_segments_tab.refresh()


@ui.refreshable
def render_activity_select() -> None:
    """Render the activity type selection dropdown."""

    ui.select(
        options=build_activity_select_options(state.activity_options),
        on_change=refresh_data,
        value=state.selected_activity_type,
        label=t("Activity Type"),
    ).classes("w-40").bind_enabled_from(state, "file_loaded").bind_value(
        state, "selected_activity_type"
    )


def render_left_drawer() -> None:
    """Generate the left drawer with filters."""

    with ui.left_drawer().props("width=330"):
        ui.label(t("Activities"))
        render_activity_select()

        ui.separator()

        render_date_range_selector()

        ui.separator()
        with ui.dropdown_button(t("Export data"), icon="download").bind_enabled_from(
            state, "file_loaded"
        ):
            ui.button(t("to JSON"), on_click=handle_json_export).props("flat").classes("w-full")
            ui.button(t("to CSV"), on_click=handle_csv_export).props("flat").classes("w-full")


@ui.refreshable
def render_date_range_selector() -> None:
    """Render the date range selector with linked input and date picker."""
    with ui.row().classes("items-center gap-2"):
        min_date, max_date = state.workouts.get_date_bounds()
        date_locale = qdate_locale_json(get_language())

        date_input = (
            ui.input(t("Date range"))
            .classes("w-50")
            .bind_enabled_from(state, "file_loaded")
            .bind_value(state, "date_range_text")
            .props("clearable")
        )
        ui.date(
            on_change=refresh_data,
        ).props(
            f'range default-year-month="{max_date[:7]}" '
            f":locale='{date_locale}' "
            f''':options="date => date >= '{min_date}' && date <= '{max_date}'"'''
        ).bind_value(
            date_input,
            forward=lambda x: (
                f'{x["from"]} - {x["to"]}'
                if isinstance(x, dict) and "from" in x
                else str(x or "")  # type: ignore[arg-type]
            ),
            backward=lambda x: (
                {
                    "from": x.split(" - ")[0],
                    "to": x.split(" - ")[1],
                }
                if " - " in (x or "")
                else None
            ),
        ).bind_enabled_from(
            state, "file_loaded"
        )


def _change_language(language_code: str) -> None:
    """Store the selected language and refresh translated UI in place."""
    app.storage.user["language"] = language_code
    _logger.info("Language changed to '%s', reloading page.", language_code)
    # NiceGUI top-level layout elements (header/drawer/body containers) cannot be
    # nested in refreshable containers. Reloading ensures all translated UI text updates.
    ui.navigate.reload()


def render_header() -> None:
    """Generate the application header with a dark mode toggle and language selector."""
    dark = ui.dark_mode()
    with ui.header().classes("items-center justify-between border-b"):
        ui.image(APP_ICON_BASE64).classes("w-16 h-16")
        ui.label(t("Apple Health Analyzer")).classes("font-bold text-xl")

        # Toggle button with dynamic icon
        ui.button(icon="dark_mode", on_click=dark.enable).bind_visibility_from(
            dark, "value", backward=lambda v: not v
        ).props(BUTTON_FLAT_ROUND_PROPS)
        ui.button(icon="light_mode", on_click=dark.disable).bind_visibility_from(
            dark, "value"
        ).props(BUTTON_FLAT_ROUND_PROPS).classes("text-main")

        # Language selector (globe icon)
        with ui.button(icon="language").props(BUTTON_FLAT_ROUND_PROPS):
            with ui.menu():
                for code, name in LANGUAGES.items():
                    ui.menu_item(name, on_click=lambda _event, c=code: _change_language(c))


def stat_card(label: str, value_ref: dict[str, str], key: str, unit: str = ""):
    """
    Create a reactive KPI card.
    'value_ref' is a dictionary containing the totals,
    allowing automatic updates via NiceGUI binding.
    """
    with ui.card().classes("w-40 h-24 items-center justify-center shadow-sm"):
        ui.label(label).classes("text-xs text-gray-500 uppercase")
        with ui.row().classes("items-baseline gap-1"):
            # Bind the text to the dictionary key for reactive updates
            ui.label().classes("text-xl font-bold").bind_text_from(value_ref, key)
            if unit:
                ui.label(unit).classes("text-xs text-gray-400")


def render_pie_rose_graph(label: str, values: Mapping[str, float | int], unit: str = "") -> None:
    """Render a pie/rose graph for the given values."""

    chart_data = [{"value": v, "name": k} for k, v in values.items()]

    with ui.card().classes("w-100 h-80 items-center justify-center shadow-sm"):
        ui.label(label).classes(LABEL_UPPERCASE_CLASSES)
        ui.echart(
            {
                "tooltip": {"trigger": "item", "formatter": f"{{b}}: {{c}} {unit} ({{d}}%)"},
                "series": [
                    {
                        "type": "pie",
                        "name": label,
                        "data": chart_data,
                        "roseType": "rose",
                        "radius": ["10", "60"],
                        "center": ["50%", "50%"],
                    },
                ],
            }
        )


def calculate_moving_average(
    y_values: Sequence[float | int | None], window_size: int = 12
) -> list[float | None]:
    """
    Calculate a moving average to smooth out peaks and valleys in sports data.

    Uses a rolling window with ``min_periods=1``, which behaves like an expanding
    average for the initial points when there are fewer samples than ``window_size``.
    Missing values (None/NaN) are preserved as None in the output.
    """
    # Use pandas rolling window to calculate the moving average consistently
    # Convert y_values to a list to ensure compatibility with pandas Series
    # constructor's type hints.
    series = pd.Series(list(y_values), dtype=float)
    result = series.rolling(window=window_size, min_periods=1).mean().round(2)
    return [None if pd.isna(v) else float(v) for v in result]


def render_generic_graph(
    label: str,
    values: Mapping[str, float | int | None],
    unit: str = "",
    graph_type: str = "bar",
    show_trend: bool = True,
) -> None:
    """Render generic graphs for the given values."""

    # Transform dictionary data into ECharts format: [{'value': x, 'name': y}, ...]
    chart_data = [{"value": v, "name": k} for k, v in values.items()]

    # Extract raw lists for the axes and series
    categories = [d["name"] for d in chart_data]
    data_points = list(values.values())

    series: list[dict[str, object]] = [{"data": data_points, "type": graph_type}]
    if show_trend:
        series.append(
            {
                "name": "Trend",
                "type": "line",
                "data": calculate_moving_average(data_points),
                "symbol": "none",  # Removes the dots on the line
                "lineStyle": {
                    "width": 2,
                    "type": "dashed",  # Dashed line for statistical trends
                },
                "itemStyle": {"color": "#e74c3c"},  # Red color to stand out
            }
        )

    with ui.card().classes("w-100 h-80 items-center justify-center shadow-sm"):
        ui.label(label).classes(LABEL_UPPERCASE_CLASSES)
        ui.echart(
            {
                "tooltip": {"trigger": "axis", "formatter": f"{{b}}: {{c}} {unit}"},
                "xAxis": {
                    "type": "category",
                    "data": categories,
                    "axisTick": {"alignWithLabel": True},
                },
                "yAxis": {"type": "value", "scale": True},
                "series": series,
            }
        )


async def pick_file() -> None:
    """Open a file picker dialog to select the Apple Health export file."""
    result: list[str] = await LocalFilePicker("~", multiple=False, file_filter=".zip")

    if not result:
        ui.notify(t("No file selected"))
        return

    state.input_file.value = result[0]


def _translate_parser_progress_message(message: str) -> str:
    """Translate parser progress messages emitted by ExportParser."""
    if message == "Starting to parse the Apple Health export file...":
        return t("Starting to parse the Apple Health export file...")
    if message == "Loading the workouts...":
        return t("Loading the workouts...")
    if message == "Finished parsing the Apple Health export file.":
        return t("Finished parsing the Apple Health export file.")

    processed_match = re.match(r"^Processed (\d+) workouts\.\.\.$", message)
    if processed_match:
        return t("Processed {count} workouts...", count=processed_match.group(1))

    loaded_match = re.match(r"^Loaded (\d+) workouts total\.$", message)
    if loaded_match:
        return t("Loaded {count} workouts total.", count=loaded_match.group(1))

    error_match = re.match(r"^Error during parsing: (.+)$", message)
    if error_match:
        return t("Error during parsing: {error}", error=error_match.group(1))

    return message


def load_workouts_from_file(
    file_path: str,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> tuple[WorkoutManager, list[str], RecordsByType]:
    """Load and parse the Apple Health export file.

    Returns a tuple of (WorkoutManager, activity_options, records_by_type) so that all UI
    state mutations and refresh calls can be performed on the event-loop
    thread by the caller (load_file), avoiding thread-safety issues.
    """

    def report(progress: int, message: str) -> None:
        localized_message = _translate_parser_progress_message(message)
        _logger.info(localized_message)
        if progress_callback:
            progress_callback(progress, localized_message)

    parser_progress = 20

    def parser_message_handler(message: str) -> None:
        nonlocal parser_progress

        if message.startswith("Starting to parse"):
            parser_progress = max(parser_progress, 20)
        elif message.startswith("Loading the workouts"):
            parser_progress = max(parser_progress, 35)
        elif message.startswith("Processed "):
            parser_progress = min(parser_progress + 2, 80)
        elif message.startswith("Loaded "):
            parser_progress = max(parser_progress, 85)
        elif message.startswith("Finished parsing"):
            parser_progress = max(parser_progress, 90)

        report(parser_progress, message)

    report(5, t("Preparing file load..."))
    start_time = time.perf_counter()
    _logger.info("Starting to load file: %s", file_path)

    with ExportParser(progress_callback=parser_message_handler) as ep:
        phd = ep.parse(file_path)
        workouts_df = phd.workouts
        records_by_type = RecordsByType(data=phd.records_by_type)

    report(93, t("Building workout index..."))
    workouts = WorkoutManager(workouts_df)
    elapsed = time.perf_counter() - start_time
    _logger.info(workouts.get_statistics())
    _logger.info("Finished parsing in %s seconds.", elapsed)

    activity_types = workouts.get_activity_types()
    activity_types.sort()
    activity_options = ["All"] + activity_types

    report(97, t("Preparing dashboard update..."))
    return workouts, activity_options, records_by_type


async def load_file() -> None:
    """Load and parse the selected Apple Health export file."""
    if state.input_file.value == "":
        ui.notify(t("Please select an Apple Health export file first."))
        return

    # Guard against concurrent invocations (e.g., from auto-load timer + manual click)
    if state.loading:
        _logger.debug("File loading already in progress, skipping concurrent invocation")
        return

    state.loading = True
    state.loading_status = f"0% - {t('Initializing...')}"

    loop = asyncio.get_running_loop()

    def progress_callback(progress: int, message: str) -> None:
        """Schedule a UI-safe update of the loading status from a worker thread."""

        def _update() -> None:
            if state.loading:
                state.loading_status = f"{progress}% - {message}"

        loop.call_soon_threadsafe(_update)

    try:
        workouts, activity_options, records_by_type = await asyncio.to_thread(
            load_workouts_from_file,
            state.input_file.value,
            progress_callback,
        )
        state.workouts = workouts
        state.records_by_type = records_by_type
        state.file_loaded = True
        state.activity_options = activity_options
        render_activity_select.refresh()
        render_date_range_selector.refresh()
        refresh_data()
        ui.notify(t("File parsed successfully."))
    except Exception as e:  # pylint: disable=broad-except
        ui.notify(t("Error parsing file: {error}", error=str(e)))
    finally:
        state.loading_status = ""
        state.loading = False


def render_body() -> None:
    """Generate the main body of the application."""
    with ui.row().classes("w-full items-center"):
        state.input_file = (
            ui.input(
                t("Apple Health export file"),
                placeholder=t("Select an Apple Health export file..."),
            )
            .classes("flex-grow")
            .bind_value(app.storage.user, "input_file_path")
        )
        ui.button(t("Browse"), on_click=pick_file, icon="folder_open")

    with ui.row().classes("w-full items-center"):
        ui.button(t("Load"), on_click=load_file, icon="play_arrow").classes(
            "flex-grow"
        ).bind_enabled_from(state, "loading", backward=lambda loading: not loading)
        ui.spinner(size="lg").bind_visibility_from(state, "loading")

    ui.label().classes("text-sm text-gray-500").bind_text_from(
        state, "loading_status"
    ).bind_visibility_from(state, "loading")

    def _on_tab_change(event: Any) -> None:
        value = getattr(event, "value", None)
        tab_name = str(getattr(value, "name", value)) if value is not None else ""
        state.selected_main_tab = tab_name
        if tab_name == "best_segments":
            schedule_best_segments_load()

    with ui.tabs(on_change=_on_tab_change).classes("w-full") as tabs:
        ui.tab("summary", t("Overview"))
        ui.tab("activities", t("Activities")).bind_enabled_from(state, "file_loaded")
        ui.tab("trends", t("Trends")).bind_enabled_from(state, "file_loaded")
        ui.tab("health_data", t("Health Data")).bind_enabled_from(state, "file_loaded")
        ui.tab("best_segments", t("Best Segments")).bind_enabled_from(state, "file_loaded")

    # Restore the previously selected tab (defaults to "summary" on first render).
    tabs.value = state.selected_main_tab or "summary"

    with ui.tab_panels(tabs, value=state.selected_main_tab or "summary").classes("w-full"):
        with ui.tab_panel("summary"):
            with ui.row().classes(ROW_CENTERED_CLASSES):
                stat_card(t("Count"), state.metrics_display, "count")
                stat_card(t("Distance"), state.metrics_display, "distance", "km")
                stat_card(t("Duration"), state.metrics_display, "duration", "h")
                stat_card(t("Elevation"), state.metrics_display, "elevation", "km")
            with ui.row().classes(ROW_CENTERED_CLASSES):
                stat_card(t("Calories"), state.metrics_display, "calories", "kcal")
            with ui.row().classes(ROW_CENTERED_CLASSES):
                stat_card(t("Longest Run"), state.metrics_display, "longest_run", "km")
                stat_card(t("Longest Walk/Hike"), state.metrics_display, "longest_walk", "km")
                stat_card(t("Longest Cycling"), state.metrics_display, "longest_cycling", "km")

        with ui.tab_panel("activities"):
            render_activity_graphs()

        with ui.tab_panel("trends"):
            render_trends_tab()

        with ui.tab_panel("health_data"):
            render_health_data_tab()

        with ui.tab_panel("best_segments"):
            render_best_segments_tab()


@ui.refreshable
def render_activity_graphs() -> None:
    """Render graphs by activity type."""
    with ui.row().classes(ROW_CENTERED_CLASSES):
        render_pie_rose_graph(
            t("Count by activity"),
            translate_activity_value_map(
                state.workouts.get_count_by_activity(
                    start_date=state.start_date, end_date=state.end_date
                )
            ),
        )
        render_pie_rose_graph(
            t("Distance by activity"),
            translate_activity_value_map(
                state.workouts.get_distance_by_activity(
                    start_date=state.start_date, end_date=state.end_date
                )
            ),
            "km",
        )
    with ui.row().classes(ROW_CENTERED_CLASSES):
        render_pie_rose_graph(
            t("Calories by activity"),
            translate_activity_value_map(
                state.workouts.get_calories_by_activity(
                    start_date=state.start_date, end_date=state.end_date
                )
            ),
            "kcal",
        )
        render_pie_rose_graph(
            t("Duration by activity"),
            translate_activity_value_map(
                state.workouts.get_duration_by_activity(
                    start_date=state.start_date, end_date=state.end_date
                )
            ),
            "h",
        )
    with ui.row().classes(ROW_CENTERED_CLASSES):
        # Display elevation in meters (not km like the stat card) because per-activity
        # values can be small and would show as 0.0X km, making the chart less readable
        render_pie_rose_graph(
            t("Elevation by activity"),
            translate_activity_value_map(
                state.workouts.get_elevation_by_activity(
                    start_date=state.start_date, end_date=state.end_date
                )
            ),
            "m",
        )


def render_trends_tab() -> None:
    """Render the trends tab with period selection and graphs."""
    with ui.row().classes(ROW_CENTERED_CLASSES):
        ui.label(t("Aggregate by:")).classes("text-sm text-gray-500 uppercase self-center")
        ui.radio(
            {
                "W": t("Week"),
                "M": t("Month"),
                "Q": t("Quarter"),
                "Y": t("Year"),
            },
            on_change=render_trends_graphs.refresh,
        ).bind_value(state, "trends_period").props("inline")

    render_trends_graphs()


@ui.refreshable
def render_trends_graphs() -> None:
    """Render trend graphs."""
    period_label = t(period_code_to_label(state.trends_period))
    with ui.row().classes(ROW_CENTERED_CLASSES):
        render_generic_graph(
            t("Count by {period}", period=period_label),
            state.workouts.get_count_by_period(
                state.trends_period,
                activity_type=state.selected_activity_type,
                start_date=state.start_date,
                end_date=state.end_date,
            ),
        )
        render_generic_graph(
            t("Distance by {period}", period=period_label),
            state.workouts.get_distance_by_period(
                state.trends_period,
                activity_type=state.selected_activity_type,
                start_date=state.start_date,
                end_date=state.end_date,
            ),
            "km",
        )
    with ui.row().classes(ROW_CENTERED_CLASSES):
        render_generic_graph(
            t("Calories by {period}", period=period_label),
            state.workouts.get_calories_by_period(
                state.trends_period,
                activity_type=state.selected_activity_type,
                start_date=state.start_date,
                end_date=state.end_date,
            ),
            "kcal",
        )
        render_generic_graph(
            t("Duration by {period}", period=period_label),
            state.workouts.get_duration_by_period(
                state.trends_period,
                activity_type=state.selected_activity_type,
                start_date=state.start_date,
                end_date=state.end_date,
            ),
            "h",
        )
    with ui.row().classes(ROW_CENTERED_CLASSES):
        # Display elevation in meters (not km like the stat card) because values for the
        # selected period can be small and would show as 0.0X km, making the chart less readable
        render_generic_graph(
            t("Elevation by {period}", period=period_label),
            state.workouts.get_elevation_by_period(
                state.trends_period,
                activity_type=state.selected_activity_type,
                unit="m",
                start_date=state.start_date,
                end_date=state.end_date,
            ),
            "m",
        )


@ui.refreshable
def render_health_data_tab() -> None:
    """Render the health data tab with filters and graphs."""

    def to_json_safe(d: dict[Hashable, Any]) -> dict[str, float | int | None]:
        """Replace pd.NA/NaN with None for JSON-safe chart data."""
        result: dict[str, float | int | None] = {}
        for key, value in d.items():
            normalized_key = str(key)
            if value is None:
                result[normalized_key] = None
            elif isinstance(value, float) and pd.isna(value):
                result[normalized_key] = None
            elif isinstance(value, (int, float)):
                result[normalized_key] = value
            else:
                result[normalized_key] = None
        return result

    with ui.row().classes(ROW_CENTERED_CLASSES):
        heart_rate_stats = state.records_by_type.heart_rate_stats(
            period=state.trends_period, context=RecordsByType.HeartRateMeasureContext.SEDENTARY
        )
        render_generic_graph(
            t("Resting HR frequency over time"),
            to_json_safe(
                heart_rate_stats.assign(period=heart_rate_stats["period"].astype(str))
                .set_index("period")["avg"]
                .to_dict()
            ),
            "bpm",
            graph_type="line",
        )

        body_mass_stats = state.records_by_type.weight_stats(period=state.trends_period)
        render_generic_graph(
            t("Body Mass over time"),
            to_json_safe(
                body_mass_stats.assign(period=body_mass_stats["period"].astype(str))
                .set_index("period")["avg"]
                .to_dict()
            ),
            "kg",
            graph_type="line",
        )

    with ui.row().classes(ROW_CENTERED_CLASSES):
        vo2_max_stats = state.records_by_type.vo2_max_stats(period=state.trends_period)
        render_generic_graph(
            t("VO2 Max over time"),
            to_json_safe(
                vo2_max_stats.assign(period=vo2_max_stats["period"].astype(str))
                .set_index("period")["avg"]
                .to_dict()
            ),
            "ml/kg/min",
            graph_type="line",
        )


@ui.refreshable
def render_best_segments_tab() -> None:
    """Render the best segments for standard running distances in a table format."""
    with ui.card().classes(ROW_CENTERED_CLASSES):
        ui.label(t("Best segments for standard running distances")).classes(LABEL_UPPERCASE_CLASSES)
        columns = [
            {"name": "distance", "label": t("Distance"), "field": "distance"},
            {"name": "duration", "label": t("Duration"), "field": "duration"},
            {
                "name": "average_speed",
                "label": t("Average Speed"),
                "field": "average_speed",
            },
            {"name": "start_date", "label": t("Date"), "field": "start_date"},
        ]

        if state.best_segments_loading:
            with ui.row().classes("w-full items-center justify-center q-gutter-sm"):
                ui.spinner(size="lg")
                ui.label(t("Loading best segments..."))
            return

        if not state.best_segments_loaded:
            ui.label(t("Open this tab to load best segments.")).classes("text-gray-500")
            return

        _logger.debug("Table rendered with %d rows", len(state.best_segments_rows))
        table = ui.table(
            columns=columns,
            rows=state.best_segments_rows,
            row_key="id",
        ).classes("w-full")
        table.add_slot(
            "header",
            r"""
            <q-tr :props="props">
                <q-th auto-width />
                <q-th v-for="col in props.cols" :key="col.name" :props="props">
                    {{ col.label }}
                </q-th>
            </q-tr>
            """,
        )
        table.add_slot(
            "body",
            r"""
            <q-tr :props="props">
                <q-td auto-width>
                    <q-btn
                        v-if="props.row.children && props.row.children.length"
                        size="sm" flat round dense
                        @click="props.expand = !props.expand"
                        :icon="props.expand ? 'expand_less' : 'expand_more'" />
                    <span v-else style="display:inline-block;width:28px" />
                </q-td>
                <q-td v-for="col in props.cols" :key="col.name" :props="props">
                    {{ col.value }}
                </q-td>
            </q-tr>
            <q-tr v-show="props.expand" :props="props">
                <q-td colspan="100%" class="bg-grey-1">
                    <q-list dense>
                        <q-item v-for="(child, i) in props.row.children" :key="i">
                            <q-item-section>
                                <span class="text-caption text-grey-9">
                                    #{{ i + 2 }}&nbsp;&nbsp;
                                    {{ child.duration }}&nbsp;&nbsp;
                                    {{ child.average_speed }}&nbsp;&nbsp;
                                    {{ child.start_date }}
                                </span>
                            </q-item-section>
                        </q-item>
                    </q-list>
                </q-td>
            </q-tr>
            """,
        )
