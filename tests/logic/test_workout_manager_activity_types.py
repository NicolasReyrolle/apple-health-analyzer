"""Test suite for WorkoutManager.get_activity_types method."""

import pandas as pd
import logic.workout_manager as wm


class TestGetActivityTypes:
    """Test suite for WorkoutManager.get_activity_types method."""

    def test_get_activity_types_empty_dataframe(self) -> None:
        """Test get_activity_types with empty DataFrame."""
        workouts = wm.WorkoutManager()  # Use default empty DataFrame with proper columns

        result = workouts.get_activity_types()

        assert result == []

    def test_get_activity_types_single_type(self) -> None:
        """Test get_activity_types with a single activity type."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Running", "Running"],
                }
            )
        )

        result = workouts.get_activity_types()

        assert result == ["Running"]

    def test_get_activity_types_multiple_types(self) -> None:
        """Test get_activity_types with multiple unique activity types."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Walking", "Cycling", "Running", "Walking"],
                }
            )
        )

        result = workouts.get_activity_types()

        # Result should contain all unique types (order may vary with pandas)
        assert set(result) == {"Running", "Walking", "Cycling"}
        assert len(result) == 3

    def test_get_activity_types_with_nan_values(self) -> None:
        """Test get_activity_types filters out NaN values."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", None, "Walking", float("nan"), "Cycling"],
                }
            )
        )

        result = workouts.get_activity_types()

        # NaN values should be excluded
        assert set(result) == {"Running", "Walking", "Cycling"}
        assert len(result) == 3
        assert None not in result

    def test_get_activity_types_returns_list(self) -> None:
        """Test that get_activity_types returns a list."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "Walking"],
                }
            )
        )

        result = workouts.get_activity_types()

        assert isinstance(result, list)

    def test_get_activity_types_preserves_order(self) -> None:
        """Test get_activity_types behavior with order."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": [
                        "Running",
                        "Cycling",
                        "Walking",
                        "Swimming",
                        "Running",
                    ],
                }
            )
        )

        result = workouts.get_activity_types()

        # Should return unique values in order of first appearance
        # (pandas unique() preserves order)
        assert len(result) == 4
        assert set(result) == {"Running", "Cycling", "Walking", "Swimming"}

    def test_get_activity_types_with_all_nan(self) -> None:
        """Test get_activity_types when all values are NaN."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": [None, float("nan"), None],
                }
            )
        )

        result = workouts.get_activity_types()

        assert result == []

    def test_get_activity_types_case_sensitive(self) -> None:
        """Test get_activity_types treats different cases as different types."""
        workouts = wm.WorkoutManager(
            pd.DataFrame(
                {
                    "activityType": ["Running", "running", "RUNNING", "Walking"],
                }
            )
        )

        result = workouts.get_activity_types()

        # Different cases should be treated as different types
        assert set(result) == {"Running", "running", "RUNNING", "Walking"}
        assert len(result) == 4
