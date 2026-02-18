"""Application state management for Apple Health Analyzer."""

from datetime import datetime

from nicegui import ui

from logic.workout_manager import WorkoutManager


class AppState:
    """Application state."""

    def __init__(self) -> None:
        self.reset()
        self.input_file: ui.input  # Assigned in layout.py
        self.log: ui.log  # Assigned in layout.py

    def reset(self) -> None:
        """Reset the application state."""
        self.workouts: WorkoutManager = WorkoutManager()
        self.file_loaded: bool = False
        self.loading: bool = False
        self.metrics = {
            "count": 0,
            "distance": 0,
            "duration": 0,
            "elevation": 0,
            "calories": 0,
        }
        self.metrics_display = {
            "count": "0",
            "distance": "0",
            "duration": "0",
            "elevation": "0",
            "calories": "0",
        }

        self.selected_activity_type: str = "All"
        self.activity_options: list[str] = ["All"]
        self.date_range_text: str = ""

    @property
    def start_date(self) -> datetime | None:
        """Get the start date from the date range text."""
        if " - " in self.date_range_text:
            date_str = self.date_range_text.split(" - ", maxsplit=1)[0]
            return datetime.strptime(date_str, "%Y-%m-%d")
        return None

    @property
    def end_date(self) -> datetime | None:
        """Get the end date from the date range text."""
        if " - " in self.date_range_text:
            date_str = self.date_range_text.split(" - ")[1]
            return datetime.strptime(date_str, "%Y-%m-%d")
        return None


state = AppState()
