from __future__ import annotations

import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from garmin_health_insights.analyzer import HealthAnalyzer
from garmin_health_insights.models import DailyMetrics
from garmin_health_insights.renderers import render_json, render_markdown
from garmin_health_insights.sources import GarminExportSource


class GarminExportSourceTest(unittest.TestCase):
    def test_loads_json_records_sorted_by_date(self) -> None:
        payload = {
            "days": [
                {"date": "2026-06-02", "sleepScore": 70, "restingHeartRate": 52},
                {"date": "2026-06-01", "sleepScore": 82, "restingHeartRate": 49},
            ]
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.json"
            path.write_text(json.dumps(payload), encoding="utf-8")

            metrics = GarminExportSource(path).load()

        self.assertEqual([item.day for item in metrics], [date(2026, 6, 1), date(2026, 6, 2)])
        self.assertEqual(metrics[0].sleep_score, 82)
        self.assertEqual(metrics[1].resting_hr, 52)

    def test_loads_csv_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metrics.csv"
            with path.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(handle, fieldnames=["date", "sleep_hours", "hrv"])
                writer.writeheader()
                writer.writerow({"date": "2026-06-01", "sleep_hours": "7.5", "hrv": "62"})

            metrics = GarminExportSource(path).load()

        self.assertEqual(metrics[0].day, date(2026, 6, 1))
        self.assertEqual(metrics[0].sleep_hours, 7.5)
        self.assertEqual(metrics[0].hrv_ms, 62)


class HealthAnalyzerTest(unittest.TestCase):
    def test_generates_low_readiness_for_worse_than_baseline_day(self) -> None:
        metrics = [
            DailyMetrics(day=date(2026, 6, 1), resting_hr=49, hrv_ms=63, sleep_score=86, body_battery=80),
            DailyMetrics(day=date(2026, 6, 2), resting_hr=50, hrv_ms=62, sleep_score=84, body_battery=78),
            DailyMetrics(
                day=date(2026, 6, 3),
                resting_hr=58,
                hrv_ms=49,
                sleep_score=61,
                body_battery=42,
                stress_score=65,
                recovery_hours=46,
                training_load=500,
            ),
        ]

        report = HealthAnalyzer().analyze(metrics)

        self.assertEqual(report.day, date(2026, 6, 3))
        self.assertLess(report.readiness_score, 60)
        self.assertEqual(report.readiness_label, "niska")
        self.assertTrue(any("odpoczynek" in suggestion for suggestion in report.suggestions))
        self.assertTrue(any("HRV" in signal for signal in report.signals))


class RenderersTest(unittest.TestCase):
    def test_renders_markdown_and_json(self) -> None:
        report = HealthAnalyzer().analyze(
            [
                DailyMetrics(day=date(2026, 6, 1), sleep_score=80),
                DailyMetrics(day=date(2026, 6, 2), sleep_score=82),
            ]
        )

        markdown = render_markdown(report)
        payload = json.loads(render_json(report))

        self.assertIn("Raport zdrowia", markdown)
        self.assertEqual(payload["day"], "2026-06-02")
        self.assertIn("readiness_score", payload)


if __name__ == "__main__":
    unittest.main()
