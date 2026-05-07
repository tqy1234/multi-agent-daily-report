from __future__ import annotations

from typing import Protocol

from multi_agent_daily_report.date_utils import ReportWindow
from multi_agent_daily_report.models import Activity


class Collector(Protocol):
    name: str

    def collect(self, window: ReportWindow) -> list[Activity]: ...
