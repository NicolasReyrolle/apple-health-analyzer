"""Tests for ui.layout core behaviors not covered by integration tests."""

from __future__ import annotations

from types import SimpleNamespace
from types import TracebackType
from typing import Any
from unittest.mock import MagicMock, patch

from app_state import state
from ui import layout


class _DummyRow:
    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        return False

    def classes(self, *_args: Any, **_kwargs: Any) -> "_DummyRow":
        """Mock method to allow chaining."""
        return self


class _DummyRadio:
    def __init__(self, _options: dict[str, str], on_change: Any = None):
        self.on_change = on_change
        self.target: Any | None = None
        self.key: str | None = None

    def bind_value(self, _target: Any, _key: str) -> "_DummyRadio":
        """Mock bind_value to capture binding information."""
        self.target = _target
        self.key = _key
        return self

    def props(self, *_args: Any, **_kwargs: Any) -> "_DummyRadio":
        """Mock props to enable chaining."""
        return self


def test_render_activity_graphs_renders_all_charts() -> None:
    """Test that render_activity_graphs calls render_pie_rose_graph for all metrics."""
    original_workouts: Any = state.workouts

    workouts_mock = MagicMock()
    workouts_mock.get_count_by_activity.return_value = {"Running": 1}
    workouts_mock.get_distance_by_activity.return_value = {"Running": 5}
    workouts_mock.get_calories_by_activity.return_value = {"Running": 200}
    workouts_mock.get_duration_by_activity.return_value = {"Running": 1}
    workouts_mock.get_elevation_by_activity.return_value = {"Running": 1}

    try:
        state.workouts = workouts_mock
        with patch("ui.layout.ui.row", return_value=_DummyRow()):
            with patch("ui.layout.render_pie_rose_graph") as render_graph_mock:
                layout.render_activity_graphs.func()

        assert render_graph_mock.call_count == 5
        render_graph_mock.assert_any_call("Count by activity", {"Running": 1})
        render_graph_mock.assert_any_call("Distance by activity", {"Running": 5}, "km")
        render_graph_mock.assert_any_call("Calories by activity", {"Running": 200}, "kcal")
        render_graph_mock.assert_any_call("Duration by activity", {"Running": 1}, "h")
        render_graph_mock.assert_any_call("Elevation by activity", {"Running": 1}, "m")
    finally:
        state.workouts = original_workouts


def test_render_trends_tab_renders_period_selector() -> None:
    """Test that render_trends_tab renders the period selector radio button."""

    with patch("ui.layout.ui.row", return_value=_DummyRow()):
        with patch("ui.layout.ui.label") as label_mock:
            with patch("ui.layout.ui.radio", side_effect=_DummyRadio) as radio_mock:
                with patch("ui.layout.render_trends_graphs") as render_graphs_mock:
                    layout.render_trends_tab()

    # Verify the label was created
    label_mock.assert_called_once_with("Aggregate by:")

    # Verify the radio button was created with correct options
    radio_mock.assert_called_once()
    radio_options, call_kwargs = radio_mock.call_args[0][0], radio_mock.call_args[1]
    assert radio_options == {"W": "Week", "M": "Month", "Q": "Quarter", "Y": "Year"}
    assert "on_change" in call_kwargs

    # Verify render_trends_graphs was called
    render_graphs_mock.assert_called_once()


def test_render_trends_tab_radio_bound_to_state() -> None:
    """Test that render_trends_tab radio button is bound to state.trends_period."""

    radio_instances: list[_DummyRadio] = []

    def _radio_factory(_options: dict[str, str], on_change: Any = None) -> _DummyRadio:
        """Create and track radio instances for assertions."""
        instance = _DummyRadio(_options, on_change)
        radio_instances.append(instance)
        return instance

    with patch("ui.layout.ui.row", return_value=_DummyRow()):
        with patch("ui.layout.ui.label"):
            with patch("ui.layout.ui.radio", side_effect=_radio_factory) as radio_mock:
                with patch("ui.layout.render_trends_graphs"):
                    layout.render_trends_tab()

    # Get the radio instance that was created
    assert radio_mock.call_count == 1
    radio_instance = radio_instances[0]

    # Verify bind_value was called with correct arguments
    assert radio_instance.target == state
    assert radio_instance.key == "trends_period"


def test_render_trends_tab_radio_calls_refresh_on_change() -> None:
    """Test that render_trends_tab radio button triggers graphs refresh on change."""

    radio_instances: list[_DummyRadio] = []

    def _radio_factory(_options: dict[str, str], on_change: Any = None) -> _DummyRadio:
        """Create and track radio instances for assertions."""
        instance = _DummyRadio(_options, on_change)
        radio_instances.append(instance)
        return instance

    with patch("ui.layout.ui.row", return_value=_DummyRow()):
        with patch("ui.layout.ui.label"):
            with patch("ui.layout.ui.radio", side_effect=_radio_factory) as radio_mock:
                with patch("ui.layout.render_trends_graphs") as render_graphs_mock:
                    layout.render_trends_tab()

    # Verify on_change callback is set to render_trends_graphs.refresh
    assert radio_mock.call_count == 1
    radio_instance = radio_instances[0]
    assert radio_instance.on_change == render_graphs_mock.refresh


def test_change_language_refreshes_ui_without_reload_or_file_load() -> None:
    """Language switch should refresh safe subcomponents only, without reload side effects."""

    fake_app = SimpleNamespace(storage=SimpleNamespace(user={}))

    with patch("ui.layout.app", fake_app):
        with patch("ui.layout.render_activity_select.refresh") as activity_refresh:
            with patch("ui.layout.render_date_range_selector.refresh") as date_refresh:
                with patch("ui.layout.render_activity_graphs.refresh") as activity_graphs_refresh:
                    with patch("ui.layout.render_trends_graphs.refresh") as trends_refresh:
                        with patch("ui.layout.render_health_data_tab.refresh") as health_refresh:
                            with patch("ui.layout.ui.navigate.reload") as reload_mock:
                                with patch("ui.layout.load_file") as load_file_mock:
                                    change_language = getattr(layout, "_change_language")
                                    change_language("fr")

    assert fake_app.storage.user["language"] == "fr"
    activity_refresh.assert_called_once()
    date_refresh.assert_called_once()
    activity_graphs_refresh.assert_called_once()
    trends_refresh.assert_called_once()
    health_refresh.assert_called_once()
    reload_mock.assert_not_called()
    load_file_mock.assert_not_called()


def test_top_level_layout_functions_are_not_refreshable() -> None:
    """Top-level NiceGUI layout functions must stay non-refreshable to avoid startup crashes."""

    assert not hasattr(layout.render_header, "refresh")
    assert not hasattr(layout.render_left_drawer, "refresh")
