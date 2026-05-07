from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from multi_agent_daily_report.date_utils import (
    ReportWindow,
    timestamp_to_date,
    timestamp_to_iso,
)
from multi_agent_daily_report.models import Activity
from multi_agent_daily_report.text_utils import compact_text, is_noise_text


class CodexCollector:
    name = "codex"

    def __init__(self, root: Path) -> None:
        self.root = root

    def collect(self, window: ReportWindow) -> list[Activity]:
        if not self.root.exists():
            return []

        activities: list[Activity] = []
        activities.extend(self._collect_history_jsonl(window))
        activities.extend(self._collect_threads(window))
        return activities

    def _collect_history_jsonl(self, window: ReportWindow) -> list[Activity]:
        path = self.root / "history.jsonl"
        if not path.exists():
            return []

        activities: list[Activity] = []
        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            return []
        for line in lines:
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            timestamp = event.get("ts")
            if (
                not isinstance(timestamp, int | float)
                or timestamp_to_date(timestamp, window.timezone) != window.date
            ):
                continue
            text = compact_text(event.get("text"), 500)
            if is_noise_text(text):
                continue
            cwd = event.get("cwd")
            project = Path(cwd).name if cwd else "codex-history"
            activities.append(
                Activity(
                    source=self.name,
                    project=project,
                    time=timestamp_to_iso(timestamp, window.timezone),
                    summary=text,
                    metadata={"session_id": event.get("session_id"), "path": str(path)},
                )
            )
        return activities

    def _collect_threads(self, window: ReportWindow) -> list[Activity]:
        db_path = self.root / "state_5.sqlite"
        if not db_path.exists():
            return []

        query = """
            SELECT id, cwd, title, first_user_message, updated_at, model, git_branch
            FROM threads
            WHERE updated_at >= ? AND updated_at < ?
            ORDER BY updated_at DESC
        """
        activities: list[Activity] = []
        try:
            with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True) as connection:
                for row in connection.execute(
                    query, (window.start_epoch, window.end_epoch)
                ):
                    (
                        thread_id,
                        cwd,
                        title,
                        first_user_message,
                        updated_at,
                        model,
                        git_branch,
                    ) = row
                    summary = compact_text(first_user_message or title, 500)
                    if is_noise_text(summary):
                        continue
                    project = Path(cwd).name if cwd else "codex-thread"
                    activities.append(
                        Activity(
                            source=self.name,
                            project=project,
                            time=timestamp_to_iso(updated_at, window.timezone),
                            summary=summary,
                            metadata={
                                "thread_id": thread_id,
                                "cwd": cwd,
                                "title": title,
                                "model": model,
                                "git_branch": git_branch,
                                "path": str(db_path),
                            },
                        )
                    )
        except sqlite3.Error:
            return []
        return activities
