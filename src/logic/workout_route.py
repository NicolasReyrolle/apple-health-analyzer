"""WorkoutRoute represents a sequence of GPS points recorded during a workout,
allowing for calculations of distance, elevation gain/loss, and duration."""

# src/logic/workout_route.py
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from math import atan2, cos, radians, sin, sqrt
import pandas as pd


@dataclass(frozen=True)
class RoutePoint:
    """Represents a single GPS point in a workout route."""

    time: datetime
    latitude: float
    longitude: float
    altitude: float = 0.0


@dataclass
class WorkoutRoute:
    """Represents a workout route as a sequence of GPS points."""

    points: list[RoutePoint]

    @property
    def is_empty(self) -> bool:
        """Check if the workout route has no points."""
        return len(self.points) == 0

    @property
    def duration_seconds(self) -> float:
        """Calculate the total duration of the workout route in seconds."""
        if len(self.points) < 2:
            return 0.0
        return (self.points[-1].time - self.points[0].time).total_seconds()

    @property
    def distance_meters(self) -> float:
        """Calculate the total distance of the workout route in meters."""
        return sum(
            self._haversine_m(a.latitude, a.longitude, b.latitude, b.longitude)
            for a, b in zip(self.points, self.points[1:])
        )

    @property
    def elevation_gain_m(self) -> float:
        """Calculate the total elevation gain of the workout route in meters."""
        return sum(max(0.0, b.altitude - a.altitude) for a, b in zip(self.points, self.points[1:]))

    @property
    def elevation_loss_m(self) -> float:
        """Calculate the total elevation loss of the workout route in meters."""
        return sum(max(0.0, a.altitude - b.altitude) for a, b in zip(self.points, self.points[1:]))

    def to_dataframe(self) -> pd.DataFrame:
        """Convert the workout route to a pandas DataFrame."""
        return pd.DataFrame(
            {
                "time": [p.time for p in self.points],
                "latitude": [p.latitude for p in self.points],
                "longitude": [p.longitude for p in self.points],
                "altitude": [p.altitude for p in self.points],
            }
        )

    def add_point(self, point: RoutePoint) -> None:
        """Add a new point to the workout route."""
        self.points.append(point)

    @staticmethod
    def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the Haversine distance between two GPS points in meters."""
        r = 6_371_000.0
        p1, p2 = radians(lat1), radians(lat2)
        dp = radians(lat2 - lat1)
        dl = radians(lon2 - lon1)
        a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
        return 2 * r * atan2(sqrt(a), sqrt(1 - a))

    def find_fastest_segment(self, segment_length_m: float) -> float | None:
        """Find the fastest segment of the given length in meters.

        Returns:
            The duration in seconds of the fastest qualifying segment,
            or None if no valid segment exists.
        """
        if self.is_empty or segment_length_m <= 0:
            return None

        best_duration_s = 0.0
        best_speed = 0.0

        for start_idx, start_point in enumerate(self.points):
            for end_point in self.points[start_idx + 1 :]:
                distance = self._haversine_m(
                    start_point.latitude,
                    start_point.longitude,
                    end_point.latitude,
                    end_point.longitude,
                )
                if distance >= segment_length_m:
                    duration_s = (end_point.time - start_point.time).total_seconds()
                    if duration_s > 0:
                        speed = distance / duration_s
                        if speed > best_speed:
                            best_speed = speed
                            best_duration_s = duration_s
                    break

        if best_speed > 0:
            return best_duration_s
        return None
