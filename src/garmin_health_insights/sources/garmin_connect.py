"""Unofficial Garmin Connect account source.

This source logs in to Garmin Connect through the user's account by using the
`garminconnect` package. It does not talk to the watch directly: the watch must
first sync to Garmin Connect, then this source reads the synced account data.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from garmin_health_insights.models import DailyMetrics


PasswordProvider = Callable[[], str]
MfaProvider = Callable[[], str]


class GarminConnectSource:
    """Load daily health metrics from a Garmin Connect account."""

    def __init__(
        self,
        *,
        email: str | None = None,
        password: str | None = None,
        tokenstore: str | Path = "~/.garminconnect",
        days: int = 30,
        end_day: date | None = None,
        password_provider: PasswordProvider | None = None,
        mfa_provider: MfaProvider | None = None,
        client: Any | None = None,
    ) -> None:
        if days < 1:
            raise ValueError("days must be at least 1")

        self.email = email
        self.password = password
        self.tokenstore = str(Path(tokenstore).expanduser())
        self.days = days
        self.end_day = end_day or date.today()
        self.password_provider = password_provider
        self.mfa_provider = mfa_provider
        self._client = client

    def load(self) -> list[DailyMetrics]:
        client = self._client or self._login()
        records = [self._load_day(client, day) for day in self._date_range()]
        return [DailyMetrics.from_mapping(record) for record in records]

    def _login(self) -> Any:
        Garmin, auth_error, connection_error, too_many_requests_error = _import_garminconnect()

        tokenstore = self.tokenstore
        try:
            client = Garmin()
            client.login(tokenstore)
            return client
        except too_many_requests_error:
            raise
        except (auth_error, connection_error, OSError):
            pass

        if not self.email:
            raise RuntimeError(
                "No valid Garmin Connect token found. Provide --email or GARMIN_EMAIL for first login."
            )

        password = self.password
        if not password and self.password_provider:
            password = self.password_provider()
        if not password:
            raise RuntimeError(
                "No Garmin Connect password available. Use GARMIN_PASSWORD or interactive prompt."
            )

        client = Garmin(
            email=self.email,
            password=password,
            prompt_mfa=self.mfa_provider,
        )
        client.login(tokenstore)
        return client

    def _date_range(self) -> list[date]:
        start = self.end_day - timedelta(days=self.days - 1)
        return [start + timedelta(days=offset) for offset in range(self.days)]

    def _load_day(self, client: Any, day: date) -> dict[str, Any]:
        day_text = day.isoformat()
        summary = _safe_call(client, "get_user_summary", day_text)
        stats = _safe_call(client, "get_stats", day_text)
        sleep = _safe_call(client, "get_sleep_data", day_text)
        hrv = _safe_call(client, "get_hrv_data", day_text)
        body_battery = _safe_call(client, "get_body_battery", day_text)
        training_readiness = _safe_call(client, "get_training_readiness", day_text)

        record: dict[str, Any] = {
            "date": day_text,
            "resting_hr": _first_number(summary, stats, keys=("restingHeartRate", "resting_hr")),
            "steps": _first_number(summary, stats, keys=("totalSteps", "steps")),
            "calories": _first_number(
                summary,
                stats,
                keys=("activeKilocalories", "activeCalories", "totalKilocalories", "calories"),
            ),
            "stress_score": _first_number(
                summary,
                stats,
                keys=("averageStressLevel", "avgStressLevel", "stressScore", "stress"),
            ),
            "vo2max": _first_number(summary, stats, keys=("vo2MaxValue", "vo2max", "generic")),
            "sleep_score": _sleep_score(sleep),
            "sleep_hours": _sleep_hours(sleep),
            "hrv_ms": _hrv_ms(hrv),
            "body_battery": _body_battery(body_battery),
            "training_readiness": _training_readiness_score(training_readiness),
            "raw_garmin": {
                "summary": summary,
                "stats": stats,
                "sleep": sleep,
                "hrv": hrv,
                "body_battery": body_battery,
                "training_readiness": training_readiness,
            },
        }
        return {key: value for key, value in record.items() if value is not None}


def _import_garminconnect() -> tuple[type[Any], type[BaseException], type[BaseException], type[BaseException]]:
    try:
        from garminconnect import (  # type: ignore[import-untyped]
            Garmin,
            GarminConnectAuthenticationError,
            GarminConnectConnectionError,
            GarminConnectTooManyRequestsError,
        )
    except ImportError as exc:
        raise RuntimeError(
            "Garmin Connect sync requires the 'garminconnect' package. "
            "Install the project with dependencies or run: pip install garminconnect"
        ) from exc

    return (
        Garmin,
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )


def _safe_call(client: Any, method_name: str, *args: Any) -> Any:
    method = getattr(client, method_name, None)
    if method is None:
        return None
    try:
        return method(*args)
    except Exception as exc:  # Garmin may omit endpoints for a day/device.
        return {"_error": str(exc)}


def _first_number(*payloads: Any, keys: tuple[str, ...]) -> float | None:
    for payload in payloads:
        for key in keys:
            value = _find_first(payload, key)
            number = _to_float(value)
            if number is not None:
                return number
    return None


def _find_first(payload: Any, key: str) -> Any:
    if isinstance(payload, dict):
        if key in payload:
            return payload[key]
        for value in payload.values():
            found = _find_first(value, key)
            if found is not None:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _find_first(item, key)
            if found is not None:
                return found
    return None


def _to_float(value: Any) -> float | None:
    if value in ("", None):
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).replace(",", "."))
    except ValueError:
        return None


def _sleep_score(payload: Any) -> float | None:
    for key in ("sleepScore", "overallSleepScore", "sleep_score"):
        value = _first_number(payload, keys=(key,))
        if value is not None:
            return value

    scores = _find_first(payload, "sleepScores")
    if isinstance(scores, dict):
        overall = scores.get("overall")
        if isinstance(overall, dict):
            return _to_float(overall.get("value"))
        return _to_float(overall)
    return None


def _sleep_hours(payload: Any) -> float | None:
    seconds = _first_number(
        payload,
        keys=("sleepTimeSeconds", "sleepWindowConfirmedSleepSeconds", "sleepDurationSeconds"),
    )
    if seconds is not None:
        return round(seconds / 3600.0, 2)

    milliseconds = _first_number(payload, keys=("sleepDuration", "sleepTimeMilliseconds"))
    if milliseconds is not None:
        return round(milliseconds / 3_600_000.0, 2)

    return _first_number(payload, keys=("sleepHours", "sleep_hours"))


def _hrv_ms(payload: Any) -> float | None:
    summary = _find_first(payload, "hrvSummary")
    return _first_number(summary, payload, keys=("lastNightAvg", "weeklyAvg", "hrv", "hrv_ms"))


def _body_battery(payload: Any) -> float | None:
    values_array = _find_first(payload, "bodyBatteryValuesArray")
    if isinstance(values_array, list):
        for row in reversed(values_array):
            if isinstance(row, list) and len(row) >= 2:
                value = _to_float(row[1])
                if value is not None:
                    return value

    return _last_number(payload, keys=("bodyBatteryMostRecentValue", "bodyBatteryLevel", "bodyBattery", "value"))


def _training_readiness_score(payload: Any) -> float | None:
    return _last_number(
        payload,
        keys=(
            "trainingReadinessScore",
            "trainingReadiness",
            "readinessScore",
            "score",
        ),
    )


def _last_number(payload: Any, keys: tuple[str, ...]) -> float | None:
    if isinstance(payload, list):
        for item in reversed(payload):
            value = _last_number(item, keys)
            if value is not None:
                return value
    elif isinstance(payload, dict):
        for key in keys:
            if key in payload:
                value = _to_float(payload[key])
                if value is not None:
                    return value
        for value in reversed(list(payload.values())):
            found = _last_number(value, keys)
            if found is not None:
                return found
    return None
