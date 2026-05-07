from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

BEIJING_TIMEZONE = "Asia/Shanghai"


@dataclass(frozen=True)
class ReportWindow:
    date: str
    timezone: str
    start: datetime
    end: datetime

    @property
    def start_epoch(self) -> int:
        return int(self.start.timestamp())

    @property
    def end_epoch(self) -> int:
        return int(self.end.timestamp())

    @property
    def start_git(self) -> str:
        return self.start.isoformat(timespec="seconds")

    @property
    def end_git(self) -> str:
        return self.end.isoformat(timespec="seconds")


def get_zone(timezone_name: str | None) -> ZoneInfo:
    try:
        return ZoneInfo(timezone_name or BEIJING_TIMEZONE)
    except ZoneInfoNotFoundError:
        return ZoneInfo(BEIJING_TIMEZONE)


def normalize_report_date(value: str, timezone_name: str | None = None) -> str:
    zone = get_zone(timezone_name)
    today = datetime.now(zone).date()
    if value == "today":
        return today.isoformat()
    if value == "yesterday":
        return (today - timedelta(days=1)).isoformat()
    return date.fromisoformat(value).isoformat()


def build_report_window(value: str, timezone_name: str | None = None) -> ReportWindow:
    zone = get_zone(timezone_name)
    report_date = normalize_report_date(value, timezone_name)
    day = date.fromisoformat(report_date)
    start = datetime.combine(day, time.min, tzinfo=zone)
    end = start + timedelta(days=1)
    return ReportWindow(date=report_date, timezone=str(zone.key), start=start, end=end)


def parse_timestamp(
    value: str | int | float | None, timezone_name: str | None = None
) -> datetime | None:
    if value is None:
        return None
    zone = get_zone(timezone_name)
    if isinstance(value, int | float):
        timestamp = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(timestamp, tz=zone)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=zone)
    return parsed.astimezone(zone)


def timestamp_in_window(value: str | int | float | None, window: ReportWindow) -> bool:
    parsed = parse_timestamp(value, window.timezone)
    return parsed is not None and window.start <= parsed < window.end


def timestamp_to_date(value: int | float, timezone_name: str | None = None) -> str:
    parsed = parse_timestamp(value, timezone_name)
    if parsed is None:
        return ""
    return parsed.date().isoformat()


def timestamp_to_iso(value: str | int | float | None, timezone_name: str | None = None) -> str:
    parsed = parse_timestamp(value, timezone_name)
    if parsed is None:
        return ""
    return parsed.isoformat(timespec="seconds")


def file_mtime_in_window(path, window: ReportWindow, max_age_days: int = 2) -> bool:
    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=get_zone(window.timezone))
    return (
        window.start - timedelta(days=max_age_days)
        <= mtime
        < window.end + timedelta(days=1)
    )
