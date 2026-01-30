"""Application state management for Apple Health Analyzer."""

from nicegui import ui

from logic.export_parser import ExportParser


class AppState:
    """Application state."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        """Reset the application state."""
        self.parser: ExportParser = ExportParser()
        self.file_loaded: bool = False
        self.input_file: ui.input
        self.log: ui.log

        self.metrics = {
            "distance": 0,
            "duration": 0,
            "elevation": 0,
        }


state = AppState()
