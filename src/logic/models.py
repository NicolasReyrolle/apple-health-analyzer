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
    route: Optional[WorkoutRoute]
    route_parts: list[WorkoutRoute]
    distance: Optional[int]  # Total distance in meters
