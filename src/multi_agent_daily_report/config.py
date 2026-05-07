from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from multi_agent_daily_report.date_utils import BEIJING_TIMEZONE

DEFAULT_CONFIG_PATH = (
    Path.home() / ".config" / "multi-agent-daily-report" / "config.yaml"
)
PROJECT_CONFIG_PATH = Path.cwd() / "cfg" / "config.yaml"

DEFAULT_CONFIG: dict[str, Any] = {
    "sources": {
        "claude": {"enabled": True, "path": "~/.claude/projects"},
        "codex": {"enabled": True, "path": "~/.codex"},
        "cursor": {"enabled": True, "path": "~/Library/Application Support/Cursor"},
        "git": {"enabled": True, "repos": []},
    },
    "output": {"directory": "./reports", "timezone": BEIJING_TIMEZONE},
}


def expand_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def load_config(path: Path | None = None) -> dict[str, Any]:
    config_path = path or resolve_default_config_path()
    if not config_path.exists():
        return DEFAULT_CONFIG
    with config_path.open("r", encoding="utf-8") as file:
        loaded = yaml.safe_load(file) or {}
    return merge_dicts(DEFAULT_CONFIG, loaded)


def resolve_default_config_path() -> Path:
    if PROJECT_CONFIG_PATH.exists():
        return PROJECT_CONFIG_PATH
    return DEFAULT_CONFIG_PATH


def write_default_config(path: Path | None = None) -> Path:
    config_path = path or DEFAULT_CONFIG_PATH
    config_path.parent.mkdir(parents=True, exist_ok=True)
    if not config_path.exists():
        with config_path.open("w", encoding="utf-8") as file:
            yaml.safe_dump(DEFAULT_CONFIG, file, sort_keys=False, allow_unicode=True)
    return config_path


def merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_dicts(merged[key], value)
        else:
            merged[key] = value
    return merged
