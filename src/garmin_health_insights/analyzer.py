"""Readiness and health insight calculations."""

from __future__ import annotations

from datetime import date
from statistics import mean
from typing import Callable, Iterable

from garmin_health_insights.models import DailyMetrics, InsightReport


MetricGetter = Callable[[DailyMetrics], float | None]


class HealthAnalyzer:
    """Turn daily Garmin metrics into a practical readiness report."""

    def __init__(self, baseline_days: int = 21) -> None:
        self.baseline_days = baseline_days

    def analyze(self, metrics: Iterable[DailyMetrics], target_day: date | None = None) -> InsightReport:
        ordered = sorted(metrics, key=lambda item: item.day)
        if not ordered:
            raise ValueError("No metrics available for analysis.")

        current = self._select_day(ordered, target_day)
        history = [item for item in ordered if item.day < current.day][-self.baseline_days :]

        components = self._score_components(current, history)
        readiness_score = self._weighted_score(components)
        readiness_label = self._label(readiness_score)
        signals = tuple(self._build_signals(current, history))
        suggestions = tuple(self._build_suggestions(current, history, readiness_score))

        return InsightReport(
            day=current.day,
            readiness_score=readiness_score,
            readiness_label=readiness_label,
            summary=self._summary(readiness_score, readiness_label),
            signals=signals,
            suggestions=suggestions,
        )

    @staticmethod
    def _select_day(metrics: list[DailyMetrics], target_day: date | None) -> DailyMetrics:
        if target_day is None:
            return metrics[-1]

        for item in metrics:
            if item.day == target_day:
                return item

        raise ValueError(f"No metrics found for {target_day.isoformat()}.")

    def _score_components(
        self, current: DailyMetrics, history: list[DailyMetrics]
    ) -> list[tuple[float, float]]:
        components: list[tuple[float, float]] = []

        sleep = current.sleep_score
        if sleep is None and current.sleep_hours is not None:
            sleep = min(100.0, max(0.0, (current.sleep_hours / 8.0) * 100.0))
        if sleep is not None:
            components.append((sleep, 0.25))

        if current.hrv_ms is not None:
            baseline = self._baseline(history, lambda item: item.hrv_ms)
            if baseline:
                components.append((min(100.0, max(0.0, (current.hrv_ms / baseline) * 100.0)), 0.20))
            else:
                components.append((self._heuristic_hrv_score(current.hrv_ms), 0.20))

        if current.resting_hr is not None:
            baseline = self._baseline(history, lambda item: item.resting_hr)
            if baseline:
                delta = current.resting_hr - baseline
                components.append((max(0.0, min(100.0, 90.0 - max(0.0, delta) * 8.0)), 0.15))
            else:
                components.append((self._heuristic_rhr_score(current.resting_hr), 0.15))

        if current.body_battery is not None:
            components.append((max(0.0, min(100.0, current.body_battery)), 0.15))

        if current.stress_score is not None:
            components.append((max(0.0, 100.0 - current.stress_score), 0.10))

        if current.recovery_hours is not None:
            components.append((self._recovery_score(current.recovery_hours), 0.10))

        if current.training_load is not None:
            baseline = self._baseline(history, lambda item: item.training_load)
            if baseline:
                ratio = current.training_load / baseline
                if ratio <= 1.1:
                    load_score = 85.0
                elif ratio <= 1.35:
                    load_score = 65.0
                elif ratio <= 1.7:
                    load_score = 45.0
                else:
                    load_score = 25.0
                components.append((load_score, 0.05))
            else:
                components.append((60.0, 0.05))

        return components or [(50.0, 1.0)]

    @staticmethod
    def _weighted_score(components: list[tuple[float, float]]) -> int:
        total_weight = sum(weight for _, weight in components)
        score = sum(score * weight for score, weight in components) / total_weight
        return int(round(max(0.0, min(100.0, score))))

    @staticmethod
    def _label(score: int) -> str:
        if score >= 80:
            return "wysoka"
        if score >= 60:
            return "umiarkowana"
        return "niska"

    @staticmethod
    def _summary(score: int, label: str) -> str:
        if score >= 80:
            return "Organizm wygląda na dobrze zregenerowany i gotowy na mocniejszy bodziec."
        if score >= 60:
            return "Parametry są mieszane; warto trenować z kontrolą intensywności."
        return "Wskaźniki sugerują obniżoną regenerację i potrzebę lżejszego dnia."

    def _build_signals(self, current: DailyMetrics, history: list[DailyMetrics]) -> list[str]:
        signals: list[str] = []

        self._append_with_baseline(
            signals,
            "HRV",
            current.hrv_ms,
            self._baseline(history, lambda item: item.hrv_ms),
            higher_is_better=True,
            unit="ms",
        )
        self._append_with_baseline(
            signals,
            "Tętno spoczynkowe",
            current.resting_hr,
            self._baseline(history, lambda item: item.resting_hr),
            higher_is_better=False,
            unit="bpm",
        )

        if current.sleep_score is not None:
            signals.append(f"Sen: wynik {current.sleep_score:.0f}/100.")
        elif current.sleep_hours is not None:
            signals.append(f"Sen: {current.sleep_hours:.1f} h.")

        if current.body_battery is not None:
            signals.append(f"Body Battery: {current.body_battery:.0f}/100.")

        if current.stress_score is not None:
            signals.append(f"Średni stres: {current.stress_score:.0f}/100.")

        if current.recovery_hours is not None:
            signals.append(f"Szacowany czas regeneracji: {current.recovery_hours:.0f} h.")

        if current.training_load is not None:
            baseline = self._baseline(history, lambda item: item.training_load)
            if baseline:
                ratio = current.training_load / baseline
                signals.append(f"Obciążenie treningowe: {ratio:.0%} średniej z ostatnich dni.")
            else:
                signals.append(f"Obciążenie treningowe: {current.training_load:.0f}.")

        return signals or ["Za mało danych, aby wskazać konkretne sygnały."]

    def _build_suggestions(
        self, current: DailyMetrics, history: list[DailyMetrics], readiness_score: int
    ) -> list[str]:
        suggestions: list[str] = []
        hrv_baseline = self._baseline(history, lambda item: item.hrv_ms)
        rhr_baseline = self._baseline(history, lambda item: item.resting_hr)

        if readiness_score >= 80:
            suggestions.append("Możesz rozważyć trening jakościowy, jeśli samopoczucie to potwierdza.")
        elif readiness_score >= 60:
            suggestions.append("Postaw na trening tlenowy lub techniczny i obserwuj reakcję organizmu.")
        else:
            suggestions.append("Rozważ odpoczynek, mobilność albo bardzo lekką jednostkę regeneracyjną.")

        if current.sleep_score is not None and current.sleep_score < 70:
            suggestions.append("Priorytetem na dziś jest higiena snu i wcześniejsze wyciszenie wieczorem.")
        elif current.sleep_hours is not None and current.sleep_hours < 7:
            suggestions.append("Sen był krótki; unikaj dokładania intensywności tylko dlatego, że plan ją zakłada.")

        if current.hrv_ms is not None and hrv_baseline and current.hrv_ms < hrv_baseline * 0.9:
            suggestions.append("HRV jest poniżej normy, więc ogranicz akcenty beztlenowe.")

        if current.resting_hr is not None and rhr_baseline and current.resting_hr > rhr_baseline + 5:
            suggestions.append("Podwyższone tętno spoczynkowe może oznaczać zmęczenie, stres lub infekcję.")

        if current.stress_score is not None and current.stress_score > 55:
            suggestions.append("Zaplanuj przerwy od bodźców i krótki spacer lub ćwiczenia oddechowe.")

        if current.recovery_hours is not None and current.recovery_hours > 36:
            suggestions.append("Garmin wskazuje długi czas regeneracji; skróć lub uprość dzisiejszą jednostkę.")

        if len(suggestions) == 1:
            suggestions.append("Uzupełniaj dane przez kilka tygodni, aby rekomendacje lepiej pasowały do Twojej normy.")

        return suggestions

    @staticmethod
    def _append_with_baseline(
        signals: list[str],
        label: str,
        current: float | None,
        baseline: float | None,
        higher_is_better: bool,
        unit: str,
    ) -> None:
        if current is None:
            return
        if baseline is None:
            signals.append(f"{label}: {current:.0f} {unit}.")
            return

        diff = current - baseline
        direction = "powyżej" if diff > 0 else "poniżej"
        favorable = diff >= 0 if higher_is_better else diff <= 0
        note = "dobry sygnał" if favorable else "sygnał ostrzegawczy"
        signals.append(f"{label}: {current:.0f} {unit}, {abs(diff):.0f} {unit} {direction} normy ({note}).")

    @staticmethod
    def _baseline(history: list[DailyMetrics], getter: MetricGetter) -> float | None:
        values = [value for item in history if (value := getter(item)) is not None]
        return mean(values) if values else None

    @staticmethod
    def _heuristic_hrv_score(hrv_ms: float) -> float:
        if hrv_ms >= 65:
            return 85.0
        if hrv_ms >= 45:
            return 70.0
        if hrv_ms >= 30:
            return 50.0
        return 30.0

    @staticmethod
    def _heuristic_rhr_score(resting_hr: float) -> float:
        if resting_hr <= 60:
            return 85.0
        if resting_hr <= 70:
            return 70.0
        if resting_hr <= 80:
            return 50.0
        return 30.0

    @staticmethod
    def _recovery_score(recovery_hours: float) -> float:
        if recovery_hours <= 12:
            return 90.0
        if recovery_hours <= 24:
            return 70.0
        if recovery_hours <= 48:
            return 45.0
        return 25.0
