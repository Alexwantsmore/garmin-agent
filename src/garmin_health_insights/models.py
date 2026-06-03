"""Domain models used by the insight engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Mapping


def _first_value(raw: Mapping[str, Any], names: tuple[str, ...]) -> Any:
    for name in names:
        if name in raw and raw[name] not in ("", None):
            return raw[name]
    return None


def _to_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _to_date(value: Any) -> date:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if value in ("", None):
        raise ValueError("Daily metrics record is missing a date")

    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue

    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise ValueError(f"Unsupported date format: {text!r}") from exc


@dataclass(frozen=True)
class DailyMetrics:
    """One calendar day of health and training metrics from Garmin."""

    day: date
    resting_hr: float | None = None
    hrv_ms: float | None = None
    sleep_score: float | None = None
    sleep_hours: float | None = None
    body_battery: float | None = None
    stress_score: float | None = None
    spo2: float | None = None
    steps: float | None = None
    calories: float | None = None
    training_load: float | None = None
    recovery_hours: float | None = None
    vo2max: float | None = None
    notes: str | None = None
    raw: Mapping[str, Any] = field(default_factory=dict, repr=False)

    @classmethod
    def from_mapping(cls, raw: Mapping[str, Any]) -> "DailyMetrics":
        """Create metrics from Garmin-like JSON/CSV key names.

        Garmin exports and community tools use slightly different names, so the
        importer accepts common aliases while keeping the model normalized.
        """

        return cls(
            day=_to_date(
                _first_value(
                    raw,
                    (
                        "date",
                        "day",
                        "calendarDate",
                        "summaryDate",
                        "startDate",
                    ),
                )
            ),
            resting_hr=_to_float(
                _first_value(raw, ("resting_hr", "restingHeartRate", "restingHeartRateInBeatsPerMinute"))
            ),
            hrv_ms=_to_float(_first_value(raw, ("hrv_ms", "hrv", "lastNightAvg", "weeklyAvg"))),
            sleep_score=_to_float(_first_value(raw, ("sleep_score", "sleepScore", "overallSleepScore"))),
            sleep_hours=_to_float(_first_value(raw, ("sleep_hours", "sleepHours", "sleepDurationHours"))),
            body_battery=_to_float(_first_value(raw, ("body_battery", "bodyBattery", "bodyBatteryMostRecentValue"))),
            stress_score=_to_float(_first_value(raw, ("stress_score", "stress", "avgStressLevel"))),
            spo2=_to_float(_first_value(raw, ("spo2", "averageSpo2", "avgSPO2"))),
            steps=_to_float(_first_value(raw, ("steps", "totalSteps"))),
            calories=_to_float(_first_value(raw, ("calories", "activeCalories", "totalCalories"))),
            training_load=_to_float(_first_value(raw, ("training_load", "trainingLoad", "acuteTrainingLoad"))),
            recovery_hours=_to_float(_first_value(raw, ("recovery_hours", "recoveryTime", "recoveryTimeHours"))),
            vo2max=_to_float(_first_value(raw, ("vo2max", "vo2MaxValue", "generic"))),
            notes=str(_first_value(raw, ("notes", "note")) or "") or None,
            raw=dict(raw),
        )


@dataclass(frozen=True)
class InsightReport:
    """Daily report produced by the analyzer."""

    day: date
    readiness_score: int
    readiness_label: str
    summary: str
    signals: tuple[str, ...]
    suggestions: tuple[str, ...]
