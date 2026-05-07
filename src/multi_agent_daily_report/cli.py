from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from multi_agent_daily_report.collectors import build_collectors
from multi_agent_daily_report.compact import compact_activities
from multi_agent_daily_report.config import load_config, write_default_config
from multi_agent_daily_report.date_utils import (
    build_report_window,
    normalize_report_date,
)
from multi_agent_daily_report.db import insert_activities, upsert_run
from multi_agent_daily_report.models import Activity, ReportContext
from multi_agent_daily_report.notifiers.qq_official import QQOfficialNotifier


def main() -> None:
    parser = argparse.ArgumentParser(prog="daily-report")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init")

    collect_parser = subparsers.add_parser("collect")
    collect_parser.add_argument("--date", default="yesterday")
    collect_parser.add_argument("--sources", default="all")
    collect_parser.add_argument("--config")
    collect_parser.add_argument("--output")

    render_parser = subparsers.add_parser("render")
    render_parser.add_argument("--date", default="yesterday")
    render_parser.add_argument("--input")
    render_parser.add_argument("--output")
    render_parser.add_argument("--compact", action="store_true")
    render_parser.add_argument("--config")

    send_parser = subparsers.add_parser("send")
    send_parser.add_argument("--date", default="yesterday")
    send_parser.add_argument("--input")
    send_parser.add_argument("--channel", default="qq")
    send_parser.add_argument("--config")

    args = parser.parse_args()
    if args.command == "init":
        path = write_default_config()
        print(f"Config ready: {path}")
        return
    if args.command == "collect":
        collect(args)
        return
    if args.command == "render":
        render(args)
        return
    if args.command == "send":
        send(args)
        return


def collect(args: argparse.Namespace) -> None:
    config = load_config(Path(args.config).expanduser() if args.config else None)
    timezone_name = config.get("output", {}).get("timezone")
    window = build_report_window(args.date, timezone_name)
    requested_sources = (
        None
        if args.sources == "all"
        else [item.strip() for item in args.sources.split(",") if item.strip()]
    )
    activities = []
    try:
        for collector in build_collectors(config, requested_sources):
            activities.extend(collector.collect(window))
    except Exception as exc:
        upsert_run(config, window.date, status="failed", error=str(exc))
        raise

    context = ReportContext.build(window.date, activities)
    output_path = resolve_output_path(args.output, config, window.date, "json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(context.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    insert_activities(config, window.date, activities)
    upsert_run(config, window.date, status="collected", raw_path=str(output_path))
    print(f"Collected {len(activities)} activities: {output_path}")


def render(args: argparse.Namespace) -> None:
    config = load_config(Path(args.config).expanduser() if args.config else None)
    report_date = normalize_report_date(
        args.date, config.get("output", {}).get("timezone")
    )
    input_path = (
        Path(args.input).expanduser()
        if args.input
        else Path("reports") / f"{report_date}.json"
    )
    data = json.loads(input_path.read_text(encoding="utf-8"))
    activities = [activity_from_dict(item) for item in data.get("activities", [])]
    if args.compact:
        activities = compact_activities(activities)

    lines = [f"# Agent Context - {data['date']}", ""]

    for activity in activities:
        lines.append(f"## {activity.source} / {activity.project}")
        if activity.time:
            lines.append(f"- Time: {activity.time}")
        lines.append(f"- Summary: {activity.summary}")
        if activity.files:
            lines.append(f"- Files: {', '.join(activity.files)}")
        if args.compact and activity.metadata.get("evidence_count"):
            lines.append(f"- Evidence: {activity.metadata['evidence_count']} events")
        lines.append("")

    output_path = (
        Path(args.output).expanduser()
        if args.output
        else Path("reports") / f"{report_date}_context.md"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    upsert_run(config, report_date, status="rendered", md_path=str(output_path))
    print(f"Rendered context: {output_path}")


def send(args: argparse.Namespace) -> None:
    if args.channel != "qq":
        raise SystemExit(f"Unsupported channel: {args.channel}")
    config = load_config(Path(args.config).expanduser() if args.config else None)
    report_date = normalize_report_date(
        args.date, config.get("output", {}).get("timezone")
    )
    input_path = (
        Path(args.input).expanduser()
        if args.input
        else Path("final_reports") / f"{report_date}.md"
    )
    notifier = QQOfficialNotifier.from_config(config)
    target = f"qq:{config.get('notify', {}).get('qq', {}).get('target_id', '')}"
    try:
        result = notifier.send_file(input_path, caption=f"日报文件：{input_path.name}")
    except Exception as exc:
        upsert_run(config, report_date, status="failed", error=str(exc))
        raise
    upsert_run(
        config,
        report_date,
        status="sent",
        sent_at=datetime.now().isoformat(timespec="seconds"),
        target=target,
    )
    print(
        json.dumps(
            {"sent": True, "channel": "qq", "date": report_date, "result": result},
            ensure_ascii=False,
        )
    )


def activity_from_dict(value: dict) -> Activity:
    return Activity(
        source=value.get("source", "unknown"),
        project=value.get("project", "unknown"),
        summary=value.get("summary", ""),
        time=value.get("time"),
        files=value.get("files") or [],
        metadata=value.get("metadata") or {},
    )


def resolve_output_path(
    value: str | None, config: dict, report_date: str, extension: str
) -> Path:
    if value:
        return Path(value).expanduser()
    output_dir = Path(
        config.get("output", {}).get("directory", "./reports")
    ).expanduser()
    return output_dir / f"{report_date}.{extension}"


if __name__ == "__main__":
    main()
