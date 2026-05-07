from __future__ import annotations

import json
from pathlib import Path

from multi_agent_daily_report.date_utils import (
    ReportWindow,
    file_mtime_in_window,
    timestamp_in_window,
    timestamp_to_iso,
)
from multi_agent_daily_report.models import Activity
from multi_agent_daily_report.text_utils import (
    compact_text,
    encoded_project_path,
    is_noise_text,
)


class ClaudeCollector:
    name = "claude"

    def __init__(self, root: Path) -> None:
        self.root = root

    def collect(self, window: ReportWindow) -> list[Activity]:
        if not self.root.exists():
            return []

        activities: list[Activity] = []
        for path in self._iter_jsonl_files(window):
            project = encoded_project_path(path.parent.name)
            for line in self._iter_lines(path):
                activity = self._parse_line(line, project, path, window)
                if activity:
                    activities.append(activity)
        return activities

    def _iter_jsonl_files(self, window: ReportWindow):
        try:
            paths = self.root.rglob("*.jsonl")
            for path in paths:
                try:
                    if file_mtime_in_window(path, window):
                        yield path
                except OSError:
                    continue
        except OSError:
            return

    def _iter_lines(self, path: Path):
        try:
            with path.open(encoding="utf-8", errors="ignore") as f:
                yield from f
        except OSError:
            return

    def _parse_line(
        self, line: str, project: str, path: Path, window: ReportWindow
    ) -> Activity | None:
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            return None

        timestamp = str(event.get("timestamp") or event.get("created_at") or "")
        if not timestamp_in_window(timestamp, window):
            return None

        event_type = str(event.get("type") or "")
        if event_type not in {"user", "assistant", "summary"}:
            return None

        message = self._extract_message(event)
        if is_noise_text(message):
            return None

        cwd = event.get("cwd")
        if cwd:
            project = Path(cwd).name

        tool_names = self._extract_tool_names(event)

        return Activity(
            source=self.name,
            project=project,
            time=timestamp_to_iso(timestamp, window.timezone),
            summary=message,
            metadata={
                "path": str(path),
                "session_id": event.get("sessionId"),
                "type": event_type,
                "cwd": cwd,
                "tool_use": tool_names,
            },
        )

    def _extract_message(self, event: dict) -> str:
        if event.get("type") == "summary":
            return compact_text(event.get("summary"), 500)
        message = event.get("message") or {}
        if isinstance(message, dict):
            return self._extract_content(message.get("content"))
        return compact_text(message, 500)

    def _extract_content(self, content) -> str:
        if isinstance(content, str):
            return compact_text(content, 500)
        if not isinstance(content, list):
            return compact_text(content, 500)

        parts: list[str] = []
        for item in content:
            if not isinstance(item, dict):
                parts.append(str(item))
                continue
            item_type = item.get("type")
            if item_type == "text":
                parts.append(str(item.get("text") or ""))
            elif item_type == "tool_use":
                name = item.get("name", "")
                if name:
                    parts.append(f"[tool: {name}]")
        return compact_text("\n".join(parts), 500)

    def _extract_tool_names(self, event: dict) -> list[str]:
        message = event.get("message") or {}
        if not isinstance(message, dict):
            return []
        content = message.get("content")
        if not isinstance(content, list):
            return []
        return [
            item["name"]
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "tool_use"
            and item.get("name")
        ]
