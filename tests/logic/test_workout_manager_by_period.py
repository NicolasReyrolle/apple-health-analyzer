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

        result = workouts.get_calories_by_period("M", combination_threshold=0)

        assert result == {"2024-02": 150}
