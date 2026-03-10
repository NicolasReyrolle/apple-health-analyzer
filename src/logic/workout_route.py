"""Module defining the structure of workout route data extracted from Apple Health exports."""
from datetime import datetime
from typing import TypedDict

class WorkoutRoute(TypedDict):
    """Type definition for workout route structure."""

    time: datetime
    latitude: float
    longitude: float
    altitude: float
