from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import replace
from typing import Any

from multi_agent_daily_report.models import Activity

LOW_SIGNAL_EXACT = {"继续", "继续重试", "继续执行", "ok", "okay", "好的", "好"}


def compact_activities(activities: list[Activity]) -> list[Activity]:
    filtered = [
        activity for activity in activities if not is_low_signal_activity(activity)
    ]
    deduped = dedupe_activities(filtered)
    return aggregate_activities(deduped)


def is_low_signal_activity(activity: Activity) -> bool:
    normalized = normalize_summary(activity.summary)
    return normalized in LOW_SIGNAL_EXACT


def dedupe_activities(activities: list[Activity]) -> list[Activity]:
    seen: dict[tuple[Any, ...], Activity] = {}
    duplicate_counts: dict[tuple[Any, ...], int] = defaultdict(int)

    for activity in activities:
        key = activity_fingerprint(activity)
        duplicate_counts[key] += 1
        if key not in seen:
            seen[key] = activity
            continue
        seen[key] = merge_duplicate(seen[key], activity, duplicate_counts[key])

    return list(seen.values())


def aggregate_activities(activities: list[Activity]) -> list[Activity]:
    groups: dict[tuple[Any, ...], list[Activity]] = defaultdict(list)
    for activity in activities:
        groups[aggregation_key(activity)].append(activity)

    compacted: list[Activity] = []
    for group in groups.values():
        ordered = sorted(group, key=lambda item: item.time or "")
        if len(ordered) == 1:
            compacted.append(ordered[0])
        else:
            compacted.append(merge_group(ordered))
    return sorted(
        compacted, key=lambda item: (item.time or "", item.source, item.project)
    )


def activity_fingerprint(activity: Activity) -> tuple[Any, ...]:
    metadata = activity.metadata or {}
    stable_id = (
        metadata.get("commit")
        or metadata.get("thread_id")
        or metadata.get("session_id")
    )
    return (
        activity.source,
        normalize_project(activity.project),
        normalize_summary(activity.summary),
        tuple(sorted(activity.files or [])),
        stable_id,
    )


def aggregation_key(activity: Activity) -> tuple[Any, ...]:
    metadata = activity.metadata or {}
    stable_session = metadata.get("session_id") or metadata.get("thread_id")
    if activity.source == "git":
        stable_session = metadata.get("commit")
    return (
        activity.source,
        normalize_project(activity.project),
        stable_session,
    )


def merge_duplicate(
    existing: Activity, duplicate: Activity, duplicate_count: int
) -> Activity:
    metadata = dict(existing.metadata or {})
    metadata["duplicate_count"] = duplicate_count
    metadata.setdefault("duplicate_paths", [])
    duplicate_path = (duplicate.metadata or {}).get("path")
    if duplicate_path and duplicate_path not in metadata["duplicate_paths"]:
        metadata["duplicate_paths"].append(duplicate_path)
    files = sorted(set(existing.files or []) | set(duplicate.files or []))
    return replace(existing, files=files, metadata=metadata)


def merge_group(group: list[Activity]) -> Activity:
    first = group[0]
    summaries = unique_preserving_order(
        activity.summary for activity in group if activity.summary
    )
    files = sorted({file for activity in group for file in activity.files})
    sources = sorted({activity.source for activity in group})
    times = [activity.time for activity in group if activity.time]
    summary = build_group_summary(summaries, len(group))
    metadata = {
        "compact": True,
        "evidence_count": len(group),
        "sources": sources,
        "time_start": times[0] if times else None,
        "time_end": times[-1] if times else None,
        "original_summaries": summaries[:20],
        "original_metadata": [activity.metadata for activity in group[:20]],
    }
    time = (
        f"{times[0]} ~ {times[-1]}" if len(times) > 1 else (times[0] if times else None)
    )
    return Activity(
        source=first.source,
        project=first.project,
        time=time,
        summary=summary,
        files=files,
        metadata=metadata,
    )


def build_group_summary(summaries: list[str], event_count: int) -> str:
    shown = summaries[:5]
    summary = "; ".join(shown)
    if len(summaries) > len(shown):
        summary = f"{summary}; ... and {len(summaries) - len(shown)} more"
    return f"{event_count} events: {summary}"


def unique_preserving_order(values) -> list[str]:
    seen = set()
    result = []
    for value in values:
        normalized = normalize_summary(value)
        if normalized in seen:
            continue
        seen.add(normalized)
        result.append(value)
    return result


def normalize_project(project: str) -> str:
    return project.strip().rstrip("/")


def normalize_summary(summary: str) -> str:
    normalized = summary.strip().lower()
    normalized = re.sub(r"\s+", "", normalized)
    normalized = normalized.strip("。.!！?？,，;；:：")
    return normalized
