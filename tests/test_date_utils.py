from __future__ import annotations

from datetime import datetime

from multi_agent_daily_report.date_utils import (
    build_report_window,
    normalize_report_date,
    parse_timestamp,
    timestamp_in_window,
    timestamp_to_date,
    timestamp_to_iso,
)


def test_normalize_today(monkeypatch):
    class FakeNow:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 4, 30, 10, 0, tzinfo=tz)

    monkeypatch.setattr("multi_agent_daily_report.date_utils.datetime", FakeNow)
    assert normalize_report_date("today") == "2026-04-30"


def test_normalize_yesterday(monkeypatch):
    class FakeNow:
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 4, 30, 10, 0, tzinfo=tz)

    monkeypatch.setattr("multi_agent_daily_report.date_utils.datetime", FakeNow)
    assert normalize_report_date("yesterday") == "2026-04-29"


def test_normalize_explicit_date():
    assert normalize_report_date("2026-04-15") == "2026-04-15"


def test_build_report_window():
    window = build_report_window("2026-04-15")
    assert window.date == "2026-04-15"
    assert window.start.isoformat() == "2026-04-15T00:00:00+08:00"
    assert window.end.isoformat() == "2026-04-16T00:00:00+08:00"


def test_parse_timestamp_iso():
    result = parse_timestamp("2026-04-15T08:30:00+08:00")
    assert result is not None
    assert result.year == 2026


# 2026-04-15 00:00 UTC = 1776211200
TIMESTAMP_2026_04_15 = 1776211200


def test_parse_timestamp_unix_seconds():
    result = parse_timestamp(TIMESTAMP_2026_04_15)
    assert result is not None
    assert result.year == 2026
    assert result.month == 4
    assert result.day == 15


def test_parse_timestamp_unix_milliseconds():
    result = parse_timestamp(TIMESTAMP_2026_04_15 * 1000)
    assert result is not None
    assert result.year == 2026


def test_parse_timestamp_none():
    assert parse_timestamp(None) is None


def test_parse_timestamp_empty_string():
    assert parse_timestamp("") is None


def test_timestamp_in_window_true():
    window = build_report_window("2026-04-15")
    assert timestamp_in_window("2026-04-15T08:30:00+08:00", window) is True


def test_timestamp_in_window_false():
    window = build_report_window("2026-04-15")
    assert timestamp_in_window("2026-04-14T08:30:00+08:00", window) is False


def test_timestamp_to_date():
    result = timestamp_to_date(TIMESTAMP_2026_04_15, "Asia/Shanghai")
    assert result == "2026-04-15"


def test_timestamp_to_iso():
    result = timestamp_to_iso(TIMESTAMP_2026_04_15, "Asia/Shanghai")
    assert "2026-04-15" in result
