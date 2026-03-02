"""Test suite for RecordsByType wrapper around HealthKit record DataFrames."""

from typing import Callable

import pandas as pd

from logic.export_parser import ExportParser
from logic.records_by_type import RecordsByType

from tests.conftest import build_health_export_xml, load_export_fragment


class TestRecordsByTypeGetters:
    """Test basic accessors and convenience getters."""

    def test_get_returns_dataframe_for_existing_type(self) -> None:
        """Return the stored DataFrame when the record type exists."""
        heart_rate_df = pd.DataFrame({"value": [60, 65]})
        records = RecordsByType({"HeartRate": heart_rate_df})

        result = records.get("HeartRate")

        assert result is heart_rate_df
        assert len(result) == 2

    def test_get_returns_empty_dataframe_for_missing_type(self) -> None:
        """Return an empty DataFrame when the record type does not exist."""
        records = RecordsByType({})

        result = records.get("MissingType")

        assert isinstance(result, pd.DataFrame)
        assert result.empty

    def test_heart_rate_and_weight_helpers_return_expected_types(self) -> None:
        """Expose heart-rate and body-mass data via helper methods."""
        heart_rate_df = pd.DataFrame({"value": [58, 62]})
        body_mass_df = pd.DataFrame({"value": [70.5, 70.2]})
        records = RecordsByType({"HeartRate": heart_rate_df, "BodyMass": body_mass_df})

        heart_rate_result = records.heart_rate()
        body_mass_result = records.weight()

        assert heart_rate_result is heart_rate_df
        assert body_mass_result is body_mass_df


class TestRecordsByTypeStatsByPeriod:
    """Test period-based aggregation logic."""

    def test_stats_by_period_returns_empty_when_required_columns_missing(self) -> None:
        """Return an empty shaped DataFrame when date/value columns are missing."""
        records = RecordsByType({"HeartRate": pd.DataFrame({"not_value": [1]})})

        result = records.stats_by_period("HeartRate")

        assert list(result.columns) == ["period", "avg", "min", "max", "count"]
        assert result.empty

    def test_stats_by_period_drops_invalid_dates_and_values(self) -> None:
        """Ignore rows with invalid dates or non-numeric values before aggregation."""
        heart_rate_df = pd.DataFrame(
            {
                "startDate": ["2024-01-01", "not-a-date", "2024-01-15"],
                "value": [60, 75, "invalid"],
            }
        )
        records = RecordsByType({"HeartRate": heart_rate_df})

        result = records.stats_by_period("HeartRate", period="M")

        assert len(result) == 1
        assert result.iloc[0]["period"].strftime("%Y-%m") == "2024-01"
        assert result.iloc[0]["avg"] == 60
        assert result.iloc[0]["min"] == 60
        assert result.iloc[0]["max"] == 60
        assert result.iloc[0]["count"] == 1

    def test_stats_by_period_groups_by_month(self) -> None:
        """Aggregate avg/min/max/count correctly for monthly periods."""
        heart_rate_df = pd.DataFrame(
            {
                "startDate": ["2024-01-01", "2024-01-20", "2024-02-10"],
                "value": [60, 80, 70],
            }
        )
        records = RecordsByType({"HeartRate": heart_rate_df})

        result = records.stats_by_period("HeartRate", period="M")

        assert list(result["period"].astype(str)) == ["2024-01", "2024-02"]
        assert list(result["avg"]) == [70.0, 70.0]
        assert list(result["min"]) == [60, 70]
        assert list(result["max"]) == [80, 70]
        assert list(result["count"]) == [2, 1]

    def test_stats_by_period_groups_by_quarter(self) -> None:
        """Aggregate values into quarter buckets when period='Q'."""
        heart_rate_df = pd.DataFrame(
            {
                "startDate": ["2024-01-01", "2024-03-15", "2024-04-10"],
                "value": [60, 90, 75],
            }
        )
        records = RecordsByType({"HeartRate": heart_rate_df})

        result = records.stats_by_period("HeartRate", period="Q")

        assert list(result["period"].astype(str)) == ["2024Q1", "2024Q2"]
        assert list(result["avg"]) == [75.0, 75.0]
        assert list(result["min"]) == [60, 75]
        assert list(result["max"]) == [90, 75]
        assert list(result["count"]) == [2, 1]


class TestRecordsByTypeConvenienceStats:
    """Test convenience wrappers around stats_by_period."""

    def test_heart_rate_stats_uses_heart_rate_type(self) -> None:
        """Use the HeartRate type constant in heart_rate_stats."""
        heart_rate_df = pd.DataFrame(
            {
                "startDate": ["2024-01-01", "2024-01-02"],
                "value": [60, 70],
            }
        )
        records = RecordsByType({"HeartRate": heart_rate_df})

        result = records.heart_rate_stats("M")

        assert len(result) == 1
        assert result.iloc[0]["avg"] == 65.0

    def test_heart_rate_stats_filters_unknown_context(self) -> None:
        """Filter heart rate stats by UNKNOWN context."""
        heart_rate_df = pd.DataFrame(
            {
                "startDate": ["2024-01-01", "2024-01-02", "2024-01-03"],
                "value": [68, 69, 75],
                "HeartRateMotionContext": [0, 0, 2],
            }
        )
        records = RecordsByType({"HeartRate": heart_rate_df})

        result = records.heart_rate_stats(
            "M", context=RecordsByType.HeartRateMeasureContext.UNKNOWN
        )

        assert len(result) == 1
        assert result.iloc[0]["count"] == 2
        assert result.iloc[0]["avg"] == 68.5

    def test_weight_stats_uses_body_mass_type(self) -> None:
        """Use the BodyMass type constant in weight_stats."""
        body_mass_df = pd.DataFrame(
            {
                "startDate": ["2024-01-01", "2024-01-10", "2024-02-10"],
                "value": [70.5, 69.5, 70.0],
            }
        )
        records = RecordsByType({"BodyMass": body_mass_df})

        result = records.weight_stats("M")

        assert list(result["period"].astype(str)) == ["2024-01", "2024-02"]
        assert list(result["avg"]) == [70.0, 70.0]

    def test_heart_rate_stats_from_export_sample_zip(
        self, create_health_zip: Callable[..., str]
    ) -> None:
        """Aggregate heart rate stats from the export_sample.zip fixture."""
        xml_content = build_health_export_xml([load_export_fragment("record_heart_rate.xml")])
        zip_path = create_health_zip(xml_content=xml_content)

        with ExportParser() as parser:
            parsed = parser.parse(str(zip_path))

        records = RecordsByType(data=parsed.records_by_type)
        heart_rate_df = records.heart_rate()
        result = records.heart_rate_stats("M")

        assert not heart_rate_df.empty
        assert list(result.columns) == ["period", "avg", "min", "max", "count"]
        assert not result.empty
        assert int(result["count"].sum()) == len(heart_rate_df)
        assert (result["min"] <= result["avg"]).all()
        assert (result["avg"] <= result["max"]).all()
