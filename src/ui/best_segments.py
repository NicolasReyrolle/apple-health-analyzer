"""Best-segments loading and rendering for Apple Health Analyzer."""

import asyncio
import logging
from typing import Any

from nicegui import ui

from app_state import state
from i18n import get_language, t
from logic.workout_manager import (
    HALF_MARATHON_DISTANCE_M,
    MARATHON_DISTANCE_M,
    STANDARD_SEGMENT_DISTANCES,
)
from ui.charts import LABEL_UPPERCASE_CLASSES, ROW_CENTERED_CLASSES
from ui.helpers import format_date_label, format_distance_label, format_duration_label

_logger = logging.getLogger(__name__)


def _build_best_segments_rows() -> list[dict[str, Any]]:
    """Compute and format best segments rows for tab rendering.

    Returns one row per distance (the #1 record). Runner-up records are stored
    in a ``children`` list so the table can expand them on demand.
    """
    _logger.debug("Calculating best segments for distances: %s", STANDARD_SEGMENT_DISTANCES)
    best_segments = state.workouts.get_best_segments(
        distances=STANDARD_SEGMENT_DISTANCES,
        start_date=state.start_date,
        end_date=state.end_date,
    )
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
