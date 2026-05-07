from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Activity:
    source: str
    project: str
    summary: str
    time: str | None = None
    files: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReportContext:
    date: str
    generated_at: str
    activities: list[Activity]

    @classmethod
    def build(cls, date: str, activities: list[Activity]) -> ReportContext:
        return cls(
            date=date,
            generated_at=datetime.now().isoformat(timespec="seconds"),
            activities=activities,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date,
            "generated_at": self.generated_at,
            "activities": [activity.to_dict() for activity in self.activities],
        }
