"""Application state management for Apple Health Analyzer."""

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
        self.metrics = {
            "count": 0,
            "distance": 0,
            "duration": 0,
            "elevation": 0,
            "calories": 0,
        }

        self.selected_activity_type: str = "All"
        self.activity_options: list[str] = ["All"]


state = AppState()
