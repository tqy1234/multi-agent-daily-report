from __future__ import annotations

from pathlib import Path
from typing import Any

from multi_agent_daily_report.collectors.base import Collector
from multi_agent_daily_report.collectors.claude import ClaudeCollector
from multi_agent_daily_report.collectors.codex import CodexCollector
from multi_agent_daily_report.collectors.cursor import CursorCollector
from multi_agent_daily_report.collectors.git import GitCollector
from multi_agent_daily_report.config import expand_path


def build_collectors(
    config: dict[str, Any], requested_sources: list[str] | None = None
) -> list[Collector]:
    source_config = config.get("sources", {})
    requested = set(requested_sources or [])

    def enabled(name: str) -> bool:
        if requested and name not in requested:
            return False
        return bool(source_config.get(name, {}).get("enabled", False))

    collectors: list[Collector] = []
    if enabled("claude"):
        collectors.append(
            ClaudeCollector(
                expand_path(source_config["claude"].get("path", "~/.claude/projects"))
            )
        )
    if enabled("codex"):
        collectors.append(
            CodexCollector(expand_path(source_config["codex"].get("path", "~/.codex")))
        )
    if enabled("cursor"):
        collectors.append(
            CursorCollector(
                expand_path(
                    source_config["cursor"].get(
                        "path", "~/Library/Application Support/Cursor"
                    )
                )
            )
        )
    if enabled("git"):
        repos = [expand_path(repo) for repo in source_config["git"].get("repos", [])]
        if not repos:
            repos = discover_git_repos(Path.home() / "work_space")
        collectors.append(GitCollector(repos))
    return collectors


def discover_git_repos(root: Path) -> list[Path]:
    if not root.exists():
        return []
    repos: list[Path] = []
    seen: set[Path] = set()
    for pattern in ("*/.git", "*/*/.git"):
        for path in root.glob(pattern):
            parent = path.parent
            if parent not in seen:
                seen.add(parent)
                repos.append(parent)
    return repos
