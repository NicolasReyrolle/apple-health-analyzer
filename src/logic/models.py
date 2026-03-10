"""Models representing the structured data extracted from the Apple Health export."""

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
