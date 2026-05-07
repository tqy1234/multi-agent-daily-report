from __future__ import annotations

import subprocess
from pathlib import Path

from multi_agent_daily_report.date_utils import ReportWindow
from multi_agent_daily_report.models import Activity


class GitCollector:
    name = "git"

    def __init__(self, repos: list[Path]) -> None:
        self.repos = repos

    def collect(self, window: ReportWindow) -> list[Activity]:
        activities: list[Activity] = []
        for repo in self.repos:
            if not (repo / ".git").exists():
                continue
            activities.extend(self._collect_repo(repo, window))
        return activities

    def _collect_repo(self, repo: Path, window: ReportWindow) -> list[Activity]:
        result = subprocess.run(
            [
                "git",
                "log",
                f"--since={window.start_git}",
                f"--before={window.end_git}",
                "--pretty=format:--COMMIT--%x1f%H%x1f%h%x1f%aI%x1f%s",
                "--name-only",
            ],
            cwd=repo,
            check=False,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            return []
        return self._parse_log(repo, result.stdout)

    def _parse_log(self, repo: Path, output: str) -> list[Activity]:
        activities: list[Activity] = []
        current: dict | None = None
        files: list[str] = []

        def flush() -> None:
            if not current:
                return
            activities.append(
                Activity(
                    source=self.name,
                    project=repo.name,
                    time=current["time"],
                    summary=f"{current['short_hash']} {current['subject']}",
                    files=list(files),
                    metadata={"repo": str(repo), "commit": current["hash"]},
                )
            )

        for line in output.splitlines():
            if line.startswith("--COMMIT--"):
                flush()
                parts = line.removeprefix("--COMMIT--").split("\x1f")
                if len(parts) < 4:
                    current = None
                    files = []
                    continue
                current = {
                    "hash": parts[0],
                    "short_hash": parts[1],
                    "time": parts[2],
                    "subject": parts[3],
                }
                files = []
            elif current and line.strip():
                files.append(line.strip())
        flush()
        return activities
