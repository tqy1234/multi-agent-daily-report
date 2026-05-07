#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

PROJECT_DIR = Path(__file__).resolve().parents[1]
CALENDAR_DIR = PROJECT_DIR / "cfg" / "calendar"
TIMEZONE = ZoneInfo("Asia/Shanghai")


def today() -> date:
    return datetime.now(TIMEZONE).date()


def load_overrides(year: int) -> dict[str, dict]:
    path = CALENDAR_DIR / f"holiday-cn-{year}.json"
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {item["date"]: item for item in data.get("days", [])}


def is_workday(day: date) -> bool:
    overrides = load_overrides(day.year)
    item = overrides.get(day.isoformat())
    if item is not None:
        return not bool(item.get("isOffDay"))
    return day.weekday() < 5


def previous_workday(day: date) -> date:
    current = day - timedelta(days=1)
    for _ in range(370):
        if is_workday(current):
            return current
        current -= timedelta(days=1)
    raise RuntimeError("previous workday not found within 370 days")


def parse_day(value: str | None) -> date:
    if not value or value == "today":
        return today()
    if value == "yesterday":
        return today() - timedelta(days=1)
    return date.fromisoformat(value)


def explain(day: date) -> str:
    item = load_overrides(day.year).get(day.isoformat())
    if item:
        return f"{item.get('name')} {'休息日' if item.get('isOffDay') else '调休工作日'}"
    return "周末" if day.weekday() >= 5 else "普通工作日"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["is-workday", "previous-workday", "should-send"])
    parser.add_argument("--date", default="today")
    args = parser.parse_args()

    day = parse_day(args.date)
    if args.command == "is-workday":
        print("true" if is_workday(day) else "false")
    elif args.command == "previous-workday":
        print(previous_workday(day).isoformat())
    elif args.command == "should-send":
        if is_workday(day):
            print(json.dumps({"send": True, "today": day.isoformat(), "report_date": previous_workday(day).isoformat(), "reason": explain(day)}, ensure_ascii=False))
        else:
            print(json.dumps({"send": False, "today": day.isoformat(), "reason": explain(day)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
