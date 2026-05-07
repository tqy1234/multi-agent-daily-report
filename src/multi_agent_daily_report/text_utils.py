from __future__ import annotations

import json
from typing import Any


def compact_text(value: Any, limit: int = 500) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        text = value
    elif isinstance(value, list):
        parts = []
        for item in value:
            if isinstance(item, dict):
                parts.append(str(item.get("text") or item.get("content") or item))
            else:
                parts.append(str(item))
        text = "\n".join(parts)
    elif isinstance(value, dict):
        text = str(
            value.get("text")
            or value.get("content")
            or json.dumps(value, ensure_ascii=False)
        )
    else:
        text = str(value)
    return " ".join(text.split())[:limit]


def is_noise_text(text: str) -> bool:
    normalized = text.strip()
    if not normalized:
        return True
    noise_prefixes = (
        "API Error:",
        "Base directory for this skill:",
        "Error:",
    )
    return normalized.startswith(noise_prefixes)


def encoded_project_path(name: str) -> str:
    if name.startswith("-"):
        return "/" + name[1:].replace("-", "/")
    return name
