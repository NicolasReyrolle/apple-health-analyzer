"""WorkoutRoute represents a sequence of GPS points recorded during a workout,
allowing for calculations of distance, elevation gain/loss, and duration."""

# src/logic/workout_route.py
from __future__ import annotations
from dataclasses import dataclass, field
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
    _cumulative_distance_cache: list[float] | None = field(default=None, init=False, repr=False)

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
        self._cumulative_distance_cache = None

    @staticmethod
    def _haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate the Haversine distance between two GPS points in meters."""
        r = 6_371_000.0
        p1, p2 = radians(lat1), radians(lat2)
        dp = radians(lat2 - lat1)
        dl = radians(lon2 - lon1)
        a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
        return 2 * r * atan2(sqrt(a), sqrt(1 - a))

    def _cumulative_distances(self) -> list[float]:
        """Return cumulative route distances for each point.

        The value at index ``i`` is the total traveled distance from the
        first point up to point ``i``.
        """
        if self._cumulative_distance_cache is not None:
            return self._cumulative_distance_cache

        if len(self.points) < 2:
            self._cumulative_distance_cache = [0.0] * len(self.points)
            return self._cumulative_distance_cache

        distances = [0.0]
        for previous, current in zip(self.points, self.points[1:]):
            segment_distance = self._haversine_m(
                previous.latitude,
                previous.longitude,
                current.latitude,
                current.longitude,
            )
            distances.append(distances[-1] + segment_distance)

        self._cumulative_distance_cache = distances
        return self._cumulative_distance_cache

    def find_fastest_segment(self, segment_length_m: float) -> float | None:
        """Find the fastest segment of the given length in meters.

        Uses traveled route distance rather than straight-line displacement.
        This matches how running segments are typically defined and allows a
        sliding-window search with linear complexity.

        Returns:
            The duration in seconds of the fastest qualifying segment,
            or None if no valid segment exists.
        """
        if self.is_empty or segment_length_m <= 0:
            return None

        if len(self.points) < 2:
            return None

        cumulative_distances = self._cumulative_distances()
        best_duration_s: float | None = None
        end_idx = 1

        for start_idx in range(len(self.points) - 1):
            if end_idx <= start_idx:
                end_idx = start_idx + 1

            while end_idx < len(self.points):
                route_distance = cumulative_distances[end_idx] - cumulative_distances[start_idx]
                if route_distance >= segment_length_m:
                    break
                end_idx += 1

            if end_idx == len(self.points):
                break

            duration_s = (self.points[end_idx].time - self.points[start_idx].time).total_seconds()
            if duration_s > 0 and (best_duration_s is None or duration_s < best_duration_s):
                best_duration_s = duration_s

        return best_duration_s
