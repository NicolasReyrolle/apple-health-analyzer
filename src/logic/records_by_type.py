"""Logic for working with HealthKit records grouped by type."""

from dataclasses import dataclass
from enum import Enum

import pandas as pd


@dataclass(frozen=True)
class RecordsByType:
    """Thin wrapper around raw record DataFrames grouped by HealthKit type."""

    data: dict[str, pd.DataFrame]

    HEART_RATE_TYPE = "HeartRate"
    BODY_MASS_TYPE = "BodyMass"

    class HeartRateMeasureContext(Enum):
        """Context of a heart rate measurement."""

        UNKNOWN = 0
        SEDENTARY = 1
        ACTIVE = 2

    def get(self, record_type: str) -> pd.DataFrame:
        """Return DataFrame for a HealthKit type, or empty DataFrame."""
        return self.data.get(record_type, pd.DataFrame())

    def heart_rate(self) -> pd.DataFrame:
        """Return DataFrame for heart rate records."""
        return self.get(self.HEART_RATE_TYPE)

    def weight(self) -> pd.DataFrame:
        """Return DataFrame for weight records."""
        return self.get(self.BODY_MASS_TYPE)

    def stats_by_period(
        self,
        record_type: str,
        period: str = "M",
        value_col: str = "value",
        date_col: str = "startDate",
        query_filter: str | None = None,
    ) -> pd.DataFrame:
        """Aggregate avg/min/max/count by period for one record type."""
        df = self.get(record_type)
        if df.empty or value_col not in df.columns or date_col not in df.columns:
            return pd.DataFrame(columns=["period", "avg", "min", "max", "count"])

        if query_filter:
            df = df.query(query_filter)

        if df.empty:
            return pd.DataFrame(columns=["period", "avg", "min", "max", "count"])

        work = df[[date_col, value_col]].copy()
        work[date_col] = pd.to_datetime(work[date_col], errors="coerce")
        work[value_col] = pd.to_numeric(work[value_col], errors="coerce")
        work = work.dropna(subset=[date_col, value_col])

        if work.empty:
            return pd.DataFrame(columns=["period", "avg", "min", "max", "count"])

        result = (
            work.groupby(work[date_col].dt.to_period(period))[value_col]
            .agg(avg="mean", min="min", max="max", count="count")
            .reset_index()
            .rename(columns={date_col: "period"})
            .sort_values("period")
        )
        return result

    def heart_rate_stats(
        self, period: str = "M", context: HeartRateMeasureContext = HeartRateMeasureContext.SEDENTARY
    ) -> pd.DataFrame:
        """Return aggregated heart rate stats by period."""
        heart_rate_df = self.heart_rate()
        query_filter = None
        if "HeartRateMotionContext" in heart_rate_df.columns:
            query_filter = f"HeartRateMotionContext == {context.value}"

        return self.stats_by_period(
            self.HEART_RATE_TYPE,
            period=period,
            query_filter=query_filter,
        )

    def weight_stats(self, period: str = "M") -> pd.DataFrame:
        """Return aggregated weight stats by period."""
        return self.stats_by_period(self.BODY_MASS_TYPE, period=period)
