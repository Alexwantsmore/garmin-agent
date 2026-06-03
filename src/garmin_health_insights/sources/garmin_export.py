"""Import metrics from Garmin Connect exports or prepared JSON/CSV files."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from garmin_health_insights.models import DailyMetrics


class GarminExportSource:
    """Load daily health metrics from a local Garmin export file.

    The adapter intentionally handles plain JSON and CSV so the first version
    can run without storing Garmin credentials. A future Garmin Connect/Health
    API source can reuse the same `DailyMetrics` model.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def load(self) -> list[DailyMetrics]:
        if not self.path.exists():
            raise FileNotFoundError(f"Input file does not exist: {self.path}")

        suffix = self.path.suffix.lower()
        if suffix == ".json":
            records = self._load_json()
        elif suffix == ".csv":
            records = self._load_csv()
        else:
            raise ValueError("Unsupported input format. Use .json or .csv.")

        metrics = [DailyMetrics.from_mapping(record) for record in records]
        return sorted(metrics, key=lambda item: item.day)

    def _load_json(self) -> list[dict[str, Any]]:
        with self.path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        if isinstance(payload, list):
            return [self._ensure_mapping(record) for record in payload]

        if isinstance(payload, dict):
            for key in ("days", "data", "records", "dailyMetrics"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [self._ensure_mapping(record) for record in value]

            if all(isinstance(value, dict) for value in payload.values()):
                records: list[dict[str, Any]] = []
                for day, value in payload.items():
                    record = dict(value)
                    record.setdefault("date", day)
                    records.append(record)
                return records

        raise ValueError("JSON input must be a list of records or an object containing daily records.")

    def _load_csv(self) -> list[dict[str, Any]]:
        with self.path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]

    @staticmethod
    def _ensure_mapping(record: Any) -> dict[str, Any]:
        if not isinstance(record, dict):
            raise ValueError("Each daily metrics record must be an object.")
        return dict(record)
