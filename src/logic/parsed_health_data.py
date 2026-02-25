"""Models representing the structured data extracted from the Apple Health export."""

from dataclasses import dataclass

import pandas as pd

from logic.records_by_type import RecordsByType


@dataclass(frozen=True)
class ParsedHealthData:
    """Structured data extracted from the Apple Health export."""

    workouts: pd.DataFrame
    records_by_type: dict[str, pd.DataFrame]

    @property
    def records(self) -> RecordsByType:
        """Typed access helpers over records_by_type."""
        return RecordsByType(self.records_by_type)

    @property
    def all_records(self) -> pd.DataFrame:
        """Combine all records into a single DataFrame."""
        frames: list[pd.DataFrame] = list(self.records_by_type.values())
        return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()
