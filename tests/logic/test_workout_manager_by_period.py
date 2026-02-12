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

        result = workouts.get_calories_by_period("M", combination_threshold=0)

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

        result = workouts.get_calories_by_period(
            "M",
            combination_threshold=0,
            activity_type="Running",
        )

        assert result == {
            "2024-01": 300,
            "2024-02": 200,
        }

    def test_get_calories_by_period_groups_small_periods(self) -> None:
        """Group small periods into Others based on threshold."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running"],
                    "startDate": pd.to_datetime(["2024-01-05", "2024-02-05"]),
                    "sumActiveEnergyBurned": [900.0, 50.0],
                }
            )
        )

        result = workouts.get_calories_by_period("M", combination_threshold=10.0)

        assert result == {
            "2024-01": 900,
            "Others": 50,
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

        result = workouts.get_calories_by_period(
            "M", combination_threshold=0, fill_missing_periods=False
        )

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

        result = workouts.get_distance_by_period("M", combination_threshold=0)

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

        result = workouts.get_distance_by_period("M", combination_threshold=0, unit="m")

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

        result = workouts.get_distance_by_period("M", combination_threshold=0, unit="mi")

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

        result = workouts.get_distance_by_period(
            "M",
            combination_threshold=0,
            activity_type="Running",
        )

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

        result = workouts.get_distance_by_period("M", combination_threshold=10.0)

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

        result = workouts.get_distance_by_period("M", combination_threshold=0)

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

        result = workouts.get_distance_by_period("M", combination_threshold=0)

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

        result = workouts.get_distance_by_period("Y", combination_threshold=0)

        assert result == {
            "2023": 5,
            "2024": 30,
        }
