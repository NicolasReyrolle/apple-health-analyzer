"""Models representing the structured data extracted from the Apple Health export."""

from typing import Optional, TypedDict

from logic.workout_route import WorkoutRoute


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
    route: Optional[WorkoutRoute]
    routeFiles: Optional[list[str]]
    distance: Optional[int]  # Total distance in meters
