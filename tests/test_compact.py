from __future__ import annotations

from multi_agent_daily_report.compact import (
    compact_activities,
    dedupe_activities,
    is_low_signal_activity,
    normalize_summary,
)
from multi_agent_daily_report.models import Activity


def _make(
    source="test",
    project="project",
    summary="did something",
    time=None,
    files=None,
    metadata=None,
):
    return Activity(
        source=source,
        project=project,
        summary=summary,
        time=time,
        files=files or [],
        metadata=metadata or {},
    )


def test_is_low_signal_ok():
    assert is_low_signal_activity(_make(summary="ok")) is True


def test_is_low_signal_continue_cn():
    assert is_low_signal_activity(_make(summary="继续")) is True
    assert is_low_signal_activity(_make(summary="继续执行")) is True


def test_is_low_signal_valid():
    assert (
        is_low_signal_activity(_make(summary="refactored the config module")) is False
    )


def test_compact_removes_low_signal():
    activities = [
        _make(summary="ok"),
        _make(summary="real work done"),
    ]
    result = compact_activities(activities)
    assert len(result) == 1
    assert result[0].summary == "real work done"


def test_dedupe_identical():
    activities = [
        _make(summary="same thing", project="proj"),
        _make(summary="same thing", project="proj"),
    ]
    result = dedupe_activities(activities)
    assert len(result) == 1


def test_dedupe_different():
    activities = [
        _make(summary="thing A"),
        _make(summary="thing B"),
    ]
    result = dedupe_activities(activities)
    assert len(result) == 2


def test_normalize_summary():
    assert normalize_summary("  Hello World.  ") == "helloworld"


def test_compact_aggregates_by_session():
    activities = [
        _make(summary="edit A", metadata={"session_id": "s1"}),
        _make(summary="edit B", metadata={"session_id": "s1"}),
        _make(summary="edit C", metadata={"session_id": "s2"}),
    ]
    result = compact_activities(activities)
    assert len(result) == 2
