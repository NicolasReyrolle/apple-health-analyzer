"""Export processor for Apple Health data."""

import sys
from types import TracebackType
from typing import Optional, Type
from zipfile import ZipFile

import pandas as pd
from defusedxml.ElementTree import iterparse


class ExportParser:
    """Reads and parses Apple Health export files."""

    def __init__(self, export_file: str):
        self.export_file = export_file
        self.running_workouts: pd.DataFrame = pd.DataFrame(
            columns=["startDate", "endDate", "duration"]
        )

    def __enter__(self) -> "ExportParser":
        return self

    def __exit__(
        self,
        exc_type: Optional[Type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[TracebackType],
    ) -> None:
        # Nothing to do for now
        pass

    def _load_running_workouts(self, zipfile: ZipFile) -> None:
        """Load running workouts from the export file."""
        print("Loading the running workouts...")

        with zipfile.open("apple_health_export/export.xml") as export_file:
            for event, elem in iterparse(export_file, events=("start", "end")):
                if event == "end" and elem.tag == "Workout":
                    workout_type = elem.get("workoutActivityType")
                    if workout_type == "HKWorkoutActivityTypeRunning":
                        self.running_workouts.loc[len(self.running_workouts)] = [
                            elem.get("startDate"),
                            elem.get("endDate"),
                            elem.get("duration"),
                        ]
                    elem.clear()  # Clear the element to save memory

            print(f"Loaded {len(self.running_workouts)} running workouts.")

    def parse(self) -> None:
        """Parse the export file."""
        try:
            with ZipFile(self.export_file, "r") as zipfile:
                self._load_running_workouts(zipfile)

        except FileNotFoundError:
            print(f"Apple Health Export file not found: {self.export_file}")
            sys.exit(1)
