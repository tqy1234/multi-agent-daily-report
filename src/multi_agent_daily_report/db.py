from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path
from typing import Any

from multi_agent_daily_report.models import Activity

try:
    import pymysql as _pymysql

    _HAS_PYMYSQL = True
except ImportError:
    _HAS_PYMYSQL = False


def _resolve_password(mysql: dict[str, Any]) -> str:
    env_name = mysql.get("password_env")
    if env_name and os.environ.get(str(env_name)):
        return str(os.environ[str(env_name)])
    return str(mysql.get("password", ""))


def _connect_mysql(config: dict[str, Any]):
    mysql = config.get("state", {}).get("mysql", {})
    return _pymysql.connect(
        host=mysql.get("host", "127.0.0.1"),
        port=int(mysql.get("port", 3306)),
        user=mysql.get("user", "root"),
        password=_resolve_password(mysql),
        database=mysql.get("database", "drep"),
        charset="utf8mb4",
        autocommit=True,
    )


def _connect_sqlite(config: dict[str, Any]):
    db_dir = Path.home() / ".config" / "multi-agent-daily-report"
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / "drep.db"
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS daily_runs (
            report_date TEXT PRIMARY KEY,
            timezone TEXT NOT NULL DEFAULT 'Asia/Shanghai',
            status TEXT NOT NULL,
            raw_path TEXT,
            md_path TEXT,
            sent_at TEXT,
            target TEXT,
            error TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_date TEXT NOT NULL,
            source TEXT NOT NULL,
            project TEXT NOT NULL,
            summary TEXT,
            time TEXT,
            files TEXT,
            metadata TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_activities_date
        ON activities(report_date)
    """)
    conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_activities_source
        ON activities(report_date, source)
    """)
    conn.commit()
    return conn


def _is_mysql(config: dict[str, Any]) -> bool:
    return config.get("state", {}).get("backend") == "mysql" and _HAS_PYMYSQL


def get_connection(config: dict[str, Any]):
    if _is_mysql(config):
        return _connect_mysql(config)
    return _connect_sqlite(config)


def upsert_run(config: dict[str, Any], report_date: str, **fields: Any) -> None:
    timezone = fields.get(
        "timezone", config.get("output", {}).get("timezone", "Asia/Shanghai")
    )
    status = fields.get("status", "")
    raw_path = fields.get("raw_path")
    md_path = fields.get("md_path")
    sent_at = fields.get("sent_at")
    target = fields.get("target")
    error = fields.get("error")
    values = (report_date, timezone, status, raw_path, md_path, sent_at, target, error)

    conn = get_connection(config)
    try:
        cursor = conn.cursor()
        if _is_mysql(config):
            cursor.execute(
                """
                INSERT INTO daily_runs (report_date, timezone, status, raw_path, md_path, sent_at, target, error)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    timezone=VALUES(timezone), status=VALUES(status),
                    raw_path=COALESCE(NULLIF(VALUES(raw_path), NULL), raw_path),
                    md_path=COALESCE(NULLIF(VALUES(md_path), NULL), md_path),
                    sent_at=COALESCE(NULLIF(VALUES(sent_at), NULL), sent_at),
                    target=COALESCE(NULLIF(VALUES(target), NULL), target),
                    error=VALUES(error), updated_at=NOW()
                """,
                values,
            )
        else:
            cursor.execute(
                """
                INSERT INTO daily_runs (report_date, timezone, status, raw_path, md_path, sent_at, target, error)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(report_date) DO UPDATE SET
                    timezone=excluded.timezone, status=excluded.status,
                    raw_path=CASE WHEN excluded.raw_path IS NOT NULL THEN excluded.raw_path ELSE daily_runs.raw_path END,
                    md_path=CASE WHEN excluded.md_path IS NOT NULL THEN excluded.md_path ELSE daily_runs.md_path END,
                    sent_at=CASE WHEN excluded.sent_at IS NOT NULL THEN excluded.sent_at ELSE daily_runs.sent_at END,
                    target=CASE WHEN excluded.target IS NOT NULL THEN excluded.target ELSE daily_runs.target END,
                    error=excluded.error, updated_at=datetime('now')
                """,
                values,
            )
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()


def insert_activities(
    config: dict[str, Any], report_date: str, activities: list[Activity]
) -> None:
    if not activities:
        return
    conn = get_connection(config)
    try:
        cursor = conn.cursor()
        if _is_mysql(config):
            for activity in activities:
                cursor.execute(
                    """
                    INSERT INTO activities (report_date, source, project, summary, time, files, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE summary=VALUES(summary)
                    """,
                    (
                        report_date,
                        activity.source,
                        activity.project,
                        activity.summary,
                        activity.time,
                        json.dumps(activity.files, ensure_ascii=False),
                        json.dumps(activity.metadata, ensure_ascii=False),
                    ),
                )
        else:
            # Clear previous entries for this date before inserting fresh data
            cursor.execute(
                "DELETE FROM activities WHERE report_date = ?", (report_date,)
            )
            for activity in activities:
                cursor.execute(
                    """
                    INSERT INTO activities (report_date, source, project, summary, time, files, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        report_date,
                        activity.source,
                        activity.project,
                        activity.summary,
                        activity.time,
                        json.dumps(activity.files, ensure_ascii=False),
                        json.dumps(activity.metadata, ensure_ascii=False),
                    ),
                )
            conn.commit()
    except Exception:
        try:
            conn.rollback()
        except Exception:
            pass
        raise
    finally:
        conn.close()
