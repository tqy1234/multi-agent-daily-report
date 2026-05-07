from __future__ import annotations

import json
from pathlib import Path

from multi_agent_daily_report.date_utils import (
    ReportWindow,
    file_mtime_in_window,
    timestamp_in_window,
    timestamp_to_date,
    timestamp_to_iso,
)
from multi_agent_daily_report.models import Activity


class CursorCollector:
    name = "cursor"

    def __init__(self, root: Path) -> None:
        self.root = root

    def collect(self, window: ReportWindow) -> list[Activity]:
        if not self.root.exists():
            return []

        activities: list[Activity] = []
        activities.extend(self._collect_workspace_storage(window))
        activities.extend(self._collect_file_history(window))
        return activities

    def _collect_workspace_storage(self, window: ReportWindow) -> list[Activity]:
        storage_root = self.root / "User" / "workspaceStorage"
        if not storage_root.exists():
            return []

        activities: list[Activity] = []
        try:
            workspace_files = list(storage_root.glob("*/workspace.json"))
        except OSError:
            return []
        for workspace_file in workspace_files:
            try:
                stat = workspace_file.stat()
            except OSError:
                continue
            workspace = self._read_json(workspace_file)
            folder = workspace.get("folder") or workspace.get("workspace") or ""
            project = (
                Path(str(folder).replace("file://", "")).name
                or workspace_file.parent.name
            )

            # Prefer activity timestamp from JSON, fall back to file mtime
            activity_ts = workspace.get("lastModified") or workspace.get(
                "remoteAuthority"
            )
            if activity_ts and timestamp_in_window(activity_ts, window):
                time_str = timestamp_to_iso(activity_ts, window.timezone)
            elif file_mtime_in_window(workspace_file, window):
                time_str = timestamp_to_iso(stat.st_mtime, window.timezone)
            else:
                continue

            activities.append(
                Activity(
                    source=self.name,
                    project=project,
                    time=time_str,
                    summary=f"Cursor workspace activity in {folder or project}",
                    metadata={"path": str(workspace_file), "folder": folder},
                )
            )
        return activities

    def _collect_file_history(self, window: ReportWindow) -> list[Activity]:
        history_root = self.root / "User" / "History"
        if not history_root.exists():
            return []

        activities: list[Activity] = []
        try:
            entries_files = list(history_root.glob("*/entries.json"))
        except OSError:
            return []
        for entries_file in entries_files:
            try:
                if not file_mtime_in_window(entries_file, window):
                    continue
            except OSError:
                continue
            entries = self._read_json(entries_file)
            if not isinstance(entries, dict):
                continue
            resource = entries.get("resource") or entries.get("source") or ""
            entries_list = entries.get("entries") or []
            changed_entries = [
                entry
                for entry in entries_list
                if self._entry_date(entry, entries_file, window) == window.date
            ]
            if not changed_entries:
                continue
            project = (
                Path(str(resource).replace("file://", "")).parent.name
                or entries_file.parent.name
            )
            activities.append(
                Activity(
                    source=self.name,
                    project=project,
                    time=self._entry_time(changed_entries[-1], entries_file, window),
                    summary=f"Cursor edited {resource or entries_file.parent.name} ({len(changed_entries)} history entries)",
                    files=[str(resource).replace("file://", "")] if resource else [],
                    metadata={
                        "path": str(entries_file),
                        "entry_count": len(changed_entries),
                    },
                )
            )
        return activities

    def _read_json(self, path: Path):
        try:
            return json.loads(path.read_text(encoding="utf-8", errors="ignore"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _entry_date(
        self, entry: dict, fallback_path: Path, window: ReportWindow
    ) -> str:
        timestamp = (
            entry.get("timestamp") or entry.get("mtime") or entry.get("lastModified")
        )
        if isinstance(timestamp, int | float):
            return timestamp_to_date(timestamp, window.timezone)
        try:
            return timestamp_to_date(fallback_path.stat().st_mtime, window.timezone)
        except OSError:
            return ""

    def _entry_time(
        self, entry: dict, fallback_path: Path, window: ReportWindow
    ) -> str:
        timestamp = (
            entry.get("timestamp") or entry.get("mtime") or entry.get("lastModified")
        )
        if isinstance(timestamp, int | float):
            return timestamp_to_iso(timestamp, window.timezone)
        try:
            return timestamp_to_iso(fallback_path.stat().st_mtime, window.timezone)
        except OSError:
            return ""
