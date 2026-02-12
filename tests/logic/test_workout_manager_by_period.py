"""Test suite for WorkoutManager by_period methods."""

import pandas as pd

import logic.workout_manager as wm


class TestGetCaloriesByPeriod:
    """Test suite for WorkoutManager.get_calories_by_period method."""

    def test_get_calories_by_period_empty(self) -> None:
        """Return empty dict for empty DataFrame."""
        workouts = wm.WorkoutManager()

        result = workouts.get_calories_by_period("M")

        assert result == {}

    def test_get_calories_by_period_missing_columns(self) -> None:
        """Return empty dict when required columns are missing."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": pd.to_datetime(["2024-01-01"]),
                }
            )
        )

        result = workouts.get_calories_by_period("M")

        assert result == {}

    def test_get_calories_by_period_groups_by_month(self) -> None:
        """Aggregate calories by month without grouping threshold."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-01-20", "2024-02-03"]),
                    "sumActiveEnergyBurned": [300.0, 200.0, 450.0],
                }
            )
        )

        result = workouts.get_calories_by_period("M")

        # Check if all keys are strings (we expect YYYY-MM format)
        assert all(isinstance(key, str) for key in result.keys())

        assert result == {
            "2024-01": 500,
            "2024-02": 450,
        }

    def test_get_calories_by_period_filters_activity(self) -> None:
        """Aggregate calories by month for a specific activity."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-20", "2024-02-03"]),
                    "sumActiveEnergyBurned": [300.0, 200.0, 450.0],
                }
            )
        )

        result = workouts.get_calories_by_period("M", activity_type="Running")

        assert result == {
            "2024-01": 300,
            "2024-02": 200,
        }

    def test_get_calories_by_period_filters_zero_values(self) -> None:
        """Drop zero-valued periods when filter_zeros applies."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-05"]),
                    "sumActiveEnergyBurned": [0.0, 150.0],
                }
            )
        )

        result = workouts.get_calories_by_period("M", fill_missing_periods=False)

        assert result == {"2024-02": 150}


class TestGetDistanceByPeriod:
    """Test suite for WorkoutManager.get_distance_by_period method."""

    def test_get_distance_by_period_empty(self) -> None:
        """Return empty dict for empty DataFrame."""
        workouts = wm.WorkoutManager()

        result = workouts.get_distance_by_period("M")

        assert result == {}

    def test_get_distance_by_period_missing_columns(self) -> None:
        """Return empty dict when required columns are missing."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": pd.to_datetime(["2024-01-01"]),
                }
            )
        )

        result = workouts.get_distance_by_period("M")

        assert result == {}

    def test_get_distance_by_period_groups_by_month_km(self) -> None:
        """Aggregate distance by month in kilometers (default unit)."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-01-20", "2024-02-03"]),
                    "distance": [5000.0, 7000.0, 20000.0],  # meters
                }
            )
        )

        result = workouts.get_distance_by_period("M")

        assert result == {
            "2024-01": 12,  # (5000 + 7000) / 1000 = 12 km
            "2024-02": 20,  # 20000 / 1000 = 20 km
        }

    def test_get_distance_by_period_groups_by_month_meters(self) -> None:
        """Aggregate distance by month in meters."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-03"]),
                    "distance": [5000.0, 20000.0],
                }
            )
        )

        result = workouts.get_distance_by_period("M", unit="m")

        assert result == {
            "2024-01": 5000,
            "2024-02": 20000,
        }

    def test_get_distance_by_period_groups_by_month_miles(self) -> None:
        """Aggregate distance by month in miles."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": pd.to_datetime(["2024-01-05"]),
                    "distance": [1609.34],  # 1 mile in meters
                }
            )
        )

        result = workouts.get_distance_by_period("M", unit="mi")

        assert result == {
            "2024-01": 1,
        }

    def test_get_distance_by_period_filters_activity(self) -> None:
        """Aggregate distance by month for a specific activity."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-20", "2024-02-03"]),
                    "distance": [5000.0, 10000.0, 20000.0],
                }
            )
        )

        result = workouts.get_distance_by_period("M", activity_type="Running")

        assert result == {
            "2024-01": 5,
            "2024-02": 10,
        }

    def test_get_distance_by_period_groups_small_periods(self) -> None:
        """Group small periods into Others based on threshold."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-05"]),
                    "distance": [50000.0, 1000.0],  # 50km, 1km
                }
            )
        )

        result = workouts.get_distance_by_period("M")

        assert result == {
            "2024-01": 50,
            "Others": 1,
        }

    def test_get_distance_by_period_filters_zero_values(self) -> None:
        """Drop zero-valued periods when filter_zeros applies."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-05"]),
                    "distance": [0.0, 10000.0],
                }
            )
        )

        result = workouts.get_distance_by_period("M")

        assert result == {"2024-01": 0, "2024-02": 10}

    def test_get_distance_by_period_with_fill_missing_periods(self) -> None:
        """Fill missing periods with zero values when fill_missing_periods is True."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": pd.to_datetime(["2023-12-31", "2024-02-01"]),
                    "distance": [5000.0, 10000.0],
                }
            )
        )

        result = workouts.get_distance_by_period("M")

        assert result == {
            "2023-12": 5,
            "2024-01": 0,
            "2024-02": 10,
        }

    def test_get_distance_by_period_groups_by_year(self) -> None:
        """Aggregate distance by year without grouping threshold."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2023-12-31", "2024-01-01", "2024-06-15"]),
                    "distance": [5000.0, 10000.0, 20000.0],
                }
            )
        )

        result = workouts.get_distance_by_period("Y")

        assert result == {
            "2023": 5,
            "2024": 30,
        }


class TestGetCountByPeriod:
    """Test suite for WorkoutManager.get_count_by_period method."""

    def test_get_count_by_period_empty(self) -> None:
        """Return empty dict for empty DataFrame."""
        workouts = wm.WorkoutManager()

        result = workouts.get_count_by_period("M")

        assert result == {}

    def test_get_count_by_period_missing_columns(self) -> None:
        """Return empty dict when required columns are missing."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "startDate": pd.to_datetime(["2024-01-01"]),
                }
            )
        )

        result = workouts.get_count_by_period("M")

        assert result == {}

    def test_get_count_by_period_groups_by_month(self) -> None:
        """Count workouts by month without fill_missing_periods."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-01-20", "2024-02-03"]),
                }
            )
        )

        result = workouts.get_count_by_period("M", fill_missing_periods=False)

        assert result == {
            "2024-01": 2,
            "2024-02": 1,
        }

    def test_get_count_by_period_filters_activity(self) -> None:
        """Count workouts by month for a specific activity."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-20", "2024-02-03"]),
                }
            )
        )

        result = workouts.get_count_by_period(
            "M",
            fill_missing_periods=False,
            activity_type="Running",
        )

        assert result == {
            "2024-01": 1,
            "2024-02": 1,
        }

    def test_get_count_by_period_multiple_activities_in_month(self) -> None:
        """Count multiple different activities in same month."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"] * 9 + ["Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05"] * 9 + ["2024-01-20"]),
                }
            )
        )

        result = workouts.get_count_by_period("M", fill_missing_periods=False)

        assert result == {
            "2024-01": 10,
        }

    def test_get_count_by_period_no_fill_missing(self) -> None:
        """Don't fill missing periods when fill_missing_periods is False."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-05"]),
                }
            )
        )

        result = workouts.get_count_by_period("M", fill_missing_periods=False)

        assert result == {"2024-01": 1, "2024-02": 1}

    def test_get_count_by_period_with_fill_missing_periods(self) -> None:
        """Fill missing periods, but filter out zero values by default."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Cycling"],
                    "startDate": pd.to_datetime(["2023-12-31", "2024-02-01"]),
                }
            )
        )

        result = workouts.get_count_by_period("M")

        # zero values should not be removed when fill_missing_periods is True
        assert result == {
            "2023-12": 1,
            "2024-01": 0,
            "2024-02": 1,
        }

    def test_get_count_by_period_groups_by_year(self) -> None:
        """Count workouts by year."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2023-12-31", "2024-01-01", "2024-06-15"]),
                }
            )
        )

        result = workouts.get_count_by_period("Y", fill_missing_periods=False)

        assert result == {
            "2023": 1,
            "2024": 2,
        }

    def test_get_count_by_period_single_in_month(self) -> None:
        """Count with single workout in a month."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": pd.to_datetime(["2024-03-15"]),
                }
            )
        )

        result = workouts.get_count_by_period("M", fill_missing_periods=False)

        assert result == {"2024-03": 1}


class TestGetDurationByPeriod:
    """Test suite for WorkoutManager.get_duration_by_period method."""

    def test_get_duration_by_period_empty(self) -> None:
        """Return empty dict for empty DataFrame."""
        workouts = wm.WorkoutManager()

        result = workouts.get_duration_by_period("M")

        assert result == {}

    def test_get_duration_by_period_missing_columns(self) -> None:
        """Return empty dict when required columns are missing."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": pd.to_datetime(["2024-01-01"]),
                }
            )
        )

        result = workouts.get_duration_by_period("M")

        assert result == {}

    def test_get_duration_by_period_groups_by_month(self) -> None:
        """Aggregate duration by month in hours."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-01-20", "2024-02-03"]),
                    "duration": [3600.0, 1800.0, 7200.0],  # seconds
                }
            )
        )

        result = workouts.get_duration_by_period("M", fill_missing_periods=False)

        assert result == {
            "2024-01": 2,  # (3600 + 1800) / 3600 = 1.58 ≈ 2 hours
            "2024-02": 2,  # 7200 / 3600 = 2 hours
        }

    def test_get_duration_by_period_filters_activity(self) -> None:
        """Aggregate duration by month for a specific activity."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-20", "2024-02-03"]),
                    "duration": [3600.0, 7200.0, 10800.0],
                }
            )
        )

        result = workouts.get_duration_by_period(
            "M",
            fill_missing_periods=False,
            activity_type="Running",
        )

        assert result == {
            "2024-01": 1,
            "2024-02": 2,
        }

    def test_get_duration_by_period_multiple_in_period(self) -> None:
        """Multiple workouts aggregated in same period (zeros filtered)."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-05"]),
                    "duration": [36000.0, 360.0],  # 10 hours, 6 minutes
                }
            )
        )

        result = workouts.get_duration_by_period("M", fill_missing_periods=False)

        # Zero values are filtered by default for duration
        assert result == {
            "2024-01": 10,
        }

    def test_get_duration_by_period_with_fill_missing_periods(self) -> None:
        """Fill missing periods, but zeros are filtered by default."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Cycling"],
                    "startDate": pd.to_datetime(["2023-12-31", "2024-02-01"]),
                    "duration": [3600.0, 7200.0],
                }
            )
        )

        result = workouts.get_duration_by_period("M", fill_missing_periods=True)

        # Zero values should not be filtered with fill_missing_periods=True
        assert result == {
            "2023-12": 1,
            "2024-01": 0,
            "2024-02": 2,
        }

    def test_get_duration_by_period_groups_by_year(self) -> None:
        """Aggregate duration by year."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2023-12-31", "2024-01-01", "2024-06-15"]),
                    "duration": [3600.0, 7200.0, 10800.0],
                }
            )
        )

        result = workouts.get_duration_by_period("Y", fill_missing_periods=False)

        assert result == {
            "2023": 1,
            "2024": 5,  # (7200 + 10800) / 3600 = 5 hours
        }

    def test_get_duration_by_period_fractional_hours(self) -> None:
        """Test rounding of fractional hours (both have non-zero values)."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-01-10"]),
                    "duration": [5400.0, 5400.0],  # 1.5 hours each
                }
            )
        )

        result = workouts.get_duration_by_period("M", fill_missing_periods=False)

        assert result == {
            "2024-01": 3,  # 1.5 + 1.5 = 3 hours
        }


class TestGetElevationByPeriod:
    """Test suite for WorkoutManager.get_elevation_by_period method."""

    def test_get_elevation_by_period_empty(self) -> None:
        """Return empty dict for empty DataFrame."""
        workouts = wm.WorkoutManager()

        result = workouts.get_elevation_by_period("M")

        assert result == {}

    def test_get_elevation_by_period_missing_columns(self) -> None:
        """Return empty dict when required columns are missing."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running"],
                    "startDate": pd.to_datetime(["2024-01-01"]),
                }
            )
        )

        result = workouts.get_elevation_by_period("M")

        assert result == {}

    def test_get_elevation_by_period_groups_by_month(self) -> None:
        """Aggregate elevation by month in kilometers."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-01-20", "2024-02-03"]),
                    "ElevationAscended": [1000.0, 500.0, 5000.0],  # meters
                }
            )
        )

        result = workouts.get_elevation_by_period("M", fill_missing_periods=False)

        assert result == {
            "2024-01": 2,  # (1000 + 500) / 1000 = 1.5 ≈ 2 km
            "2024-02": 5,  # 5000 / 1000 = 5 km
        }

    def test_get_elevation_by_period_filters_activity(self) -> None:
        """Aggregate elevation by month for a specific activity."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-20", "2024-02-03"]),
                    "ElevationAscended": [1000.0, 2000.0, 5000.0],
                }
            )
        )

        result = workouts.get_elevation_by_period(
            "M",
            fill_missing_periods=False,
            activity_type="Running",
        )

        assert result == {
            "2024-01": 1,
            "2024-02": 2,
        }

    def test_get_elevation_by_period_multiple_in_period(self) -> None:
        """Multiple workouts aggregated in same period."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-05"]),
                    "ElevationAscended": [10000.0, 5000.0],  # 10km, 5km
                }
            )
        )

        result = workouts.get_elevation_by_period("M", fill_missing_periods=False)

        assert result == {
            "2024-01": 10,
            "2024-02": 5,
        }

    def test_get_elevation_by_period_preserves_zero_values(self) -> None:
        """Skip very small elevation values that round to zero."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Cycling"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-05"]),
                    "ElevationAscended": [10000.0, 2000.0],  # 10km, 2km
                }
            )
        )

        result = workouts.get_elevation_by_period("M", fill_missing_periods=False)

        assert result == {"2024-01": 10, "2024-02": 2}

    def test_get_elevation_by_period_with_fill_missing_periods(self) -> None:
        """Fill missing periods with values (small values below threshold are grouped)."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Cycling"],
                    "startDate": pd.to_datetime(["2023-12-31", "2024-02-01"]),
                    "ElevationAscended": [10000.0, 30000.0],  # Both significant
                }
            )
        )

        result = workouts.get_elevation_by_period("M")

        assert result == {
            "2023-12": 10,
            "2024-01": 0,
            "2024-02": 30,
        }

    def test_get_elevation_by_period_groups_by_year(self) -> None:
        """Aggregate elevation by year."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Cycling"],
                    "startDate": pd.to_datetime(["2023-12-31", "2024-01-01", "2024-06-15"]),
                    "ElevationAscended": [1000.0, 2000.0, 5000.0],
                }
            )
        )

        result = workouts.get_elevation_by_period("Y", fill_missing_periods=False)

        assert result == {
            "2023": 1,
            "2024": 7,  # (2000 + 5000) / 1000 = 7 km
        }

    def test_get_elevation_by_period_high_elevation(self) -> None:
        """Test with high elevation values (edge case)."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Hiking"],
                    "startDate": pd.to_datetime(["2024-08-15"]),
                    "ElevationAscended": [1500000.0],  # 1500 km elevation
                }
            )
        )

        result = workouts.get_elevation_by_period("M", fill_missing_periods=False)

        assert result == {"2024-08": 1500}
