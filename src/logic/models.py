"""Models representing the structured data extracted from the Apple Health export."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, TypedDict

import pandas as pd


class WorkoutRecordRequired(TypedDict):
    """Required fields for workout record."""

    activityType: str


class WorkoutRecord(WorkoutRecordRequired, total=False):
    """Type definition for workout record structure."""

    duration: Optional[float]
    durationUnit: Optional[str]
    startDate: Optional[str]
    endDate: Optional[str]
    source: Optional[str]
    routeFile: Optional[str]
    route: Optional[pd.DataFrame]
    distance: Optional[int]  # Total distance in meters


class WorkoutRoute(TypedDict):
    """Type definition for workout route structure."""

    time: datetime
    latitude: float
    longitude: float
    altitude: float


@dataclass(frozen=True)
class ParsedHealthData:
    """Structured data extracted from the Apple Health export."""

    workouts: pd.DataFrame
    records_by_type: dict[str, pd.DataFrame]

    @property
    def all_records(self) -> pd.DataFrame:
        """Combine all records into a single DataFrame."""
        frames: list[pd.DataFrame] = list(self.records_by_type.values())
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
