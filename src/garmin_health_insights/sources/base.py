"""Source adapter protocol."""

from __future__ import annotations

from typing import Protocol

from garmin_health_insights.models import DailyMetrics


class MetricsSource(Protocol):
    """A source capable of returning normalized Garmin daily metrics."""

    def load(self) -> list[DailyMetrics]:
        """Load metrics sorted by day ascending."""
