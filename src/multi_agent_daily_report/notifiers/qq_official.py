from __future__ import annotations

import base64
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

API_BASE = "https://api.sgroup.qq.com"
TOKEN_URL = "https://bots.qq.com/app/getAppAccessToken"
MEDIA_FILE_TYPE_FILE = 4


@dataclass(frozen=True)
class QQOfficialConfig:
    app_id: str
    client_secret: str
    target_type: str
    target_id: str
    markdown: bool = False


class QQOfficialNotifier:
    def __init__(self, config: QQOfficialConfig) -> None:
        self.config = config

    @classmethod
    def from_config(cls, config: dict[str, Any]) -> QQOfficialNotifier:
        notify = config.get("notify", {})
        qq = notify.get("qq", {})
        app_id = str(qq.get("app_id") or qq.get("appId") or "")
        client_secret = resolve_secret(qq, "client_secret", "client_secret_env")
        target_type = str(qq.get("target_type") or "c2c")
        target_id = str(
            qq.get("target_id") or qq.get("openid") or qq.get("group_openid") or ""
        )
        markdown = bool(qq.get("markdown", False))
        if not app_id:
            raise ValueError("notify.qq.app_id is required")
        if not client_secret:
            raise ValueError(
                "notify.qq.client_secret or notify.qq.client_secret_env is required"
            )
        if target_type not in {"c2c", "group"}:
            raise ValueError("notify.qq.target_type must be c2c or group")
        if not target_id:
            raise ValueError("notify.qq.target_id is required")
        return cls(
            QQOfficialConfig(app_id, client_secret, target_type, target_id, markdown)
        )

    def send(self, message: str) -> dict[str, Any]:
        access_token = self._get_access_token()
        path = self._message_path()
        body = self._message_body(message)
        return api_request("POST", path, access_token, body)

    def send_file(self, path: Path, caption: str | None = None) -> dict[str, Any]:
        access_token = self._get_access_token()
        file_info = self._upload_file(access_token, path)
        return self._send_media_message(
            access_token, file_info, caption or f"日报文件：{path.name}"
        )

    def _get_access_token(self) -> str:
        payload = {
            "appId": self.config.app_id,
            "clientSecret": self.config.client_secret,
        }
        data = http_json(
            "POST", TOKEN_URL, payload, headers={"Content-Type": "application/json"}
        )
        token = data.get("access_token")
        if not token:
            raise RuntimeError(
                f"Failed to get QQ access_token: {sanitize_response(data)}"
            )
        return str(token)

    def _message_path(self) -> str:
        if self.config.target_type == "group":
            return f"/v2/groups/{self.config.target_id}/messages"
        return f"/v2/users/{self.config.target_id}/messages"

    def _files_path(self) -> str:
        if self.config.target_type == "group":
            return f"/v2/groups/{self.config.target_id}/files"
        return f"/v2/users/{self.config.target_id}/files"

    def _message_body(self, message: str) -> dict[str, Any]:
        if not message.strip():
            raise ValueError("QQ message cannot be empty")
        if self.config.markdown:
            return {"markdown": {"content": message}, "msg_type": 2}
        return {"content": message, "msg_type": 0}

    def _upload_file(self, access_token: str, path: Path) -> str:
        file_data = base64.b64encode(path.read_bytes()).decode("ascii")
        body = {
            "file_type": MEDIA_FILE_TYPE_FILE,
            "file_data": file_data,
            "srv_send_msg": False,
        }
        data = api_request("POST", self._files_path(), access_token, body)
        file_info = data.get("file_info")
        if not file_info:
            raise RuntimeError(
                f"QQ file upload did not return file_info: {sanitize_response(data)}"
            )
        return str(file_info)

    def _send_media_message(
        self, access_token: str, file_info: str, caption: str | None = None
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "msg_type": 7,
            "media": {"file_info": file_info},
            "msg_seq": 1,
        }
        if caption:
            body["content"] = caption
        return api_request("POST", self._message_path(), access_token, body)


def resolve_secret(config: dict[str, Any], value_key: str, env_key: str) -> str:
    env_name = config.get(env_key)
    if env_name and os.environ.get(str(env_name)):
        return str(os.environ[str(env_name)])
    if config.get(value_key):
        return str(config[value_key])
    return ""


def api_request(
    method: str, path: str, access_token: str, payload: dict[str, Any]
) -> dict[str, Any]:
    return http_json(
        method,
        f"{API_BASE}{path}",
        payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"QQBot {access_token}",
        },
    )


def http_json(
    method: str, url: str, payload: dict[str, Any], headers: dict[str, str]
) -> dict[str, Any]:
    request = Request(
        url,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers=headers,
        method=method,
    )
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="ignore")
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"QQ API HTTP {error.code}: {raw}") from error
    except URLError as error:
        raise RuntimeError(f"QQ API network error: {error.reason}") from error
    if not raw:
        return {}
    try:
        result: dict[str, Any] = json.loads(raw)
        return result
    except json.JSONDecodeError as error:
        raise RuntimeError(f"QQ API returned non-JSON response: {raw[:500]}") from error


def sanitize_response(data: dict[str, Any]) -> dict[str, Any]:
    sanitized = dict(data)
    if "access_token" in sanitized:
        sanitized["access_token"] = "***"
    if "file_info" in sanitized:
        sanitized["file_info"] = "***"
    return sanitized
