"""Report renderers."""

from __future__ import annotations

import json
from dataclasses import asdict

from garmin_health_insights.models import InsightReport


def render_markdown(report: InsightReport) -> str:
    """Render a daily report in Polish as Markdown."""

    lines = [
        f"# Raport zdrowia i gotowości - {report.day.isoformat()}",
        "",
        f"**Gotowość treningowa:** {report.readiness_score}/100 ({report.readiness_label})",
        "",
        report.summary,
        "",
        "## Najważniejsze sygnały",
    ]
    lines.extend(f"- {signal}" for signal in report.signals)
    lines.extend(["", "## Sugestie na dziś"])
    lines.extend(f"- {suggestion}" for suggestion in report.suggestions)
    return "\n".join(lines)


def render_json(report: InsightReport) -> str:
    """Render a daily report as stable JSON."""

    payload = asdict(report)
    payload["day"] = report.day.isoformat()
    return json.dumps(payload, ensure_ascii=False, indent=2)
