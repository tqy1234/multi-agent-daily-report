# Multi Agent Daily Report

[![CI](https://github.com/tqy1234/multi-agent-daily-report/actions/workflows/ci.yml/badge.svg)](https://github.com/tqy1234/multi-agent-daily-report/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A local-first CLI that collects activity from multiple AI coding agents and engineering sources, then prepares structured context for Claude Code, Codex, Cursor, or any other agent to summarize into a daily report.

## Design

- **CLI** collects, cleans, and normalizes data from local sources.
- **Skill / Prompt** guides the current agent to generate a human-readable daily report.
- **No remote LLM calls** in the default CLI path — lower cost, no vendor lock-in, better privacy.

## Architecture

```text
~/.claude/projects/  ──┐
~/.codex/            ──┤  Collectors     ┌──────────┐     ┌──────────────┐
Cursor workspace     ──┼──────────────►  │  JSON    │ ──► │  Markdown    │
Git repos            ──┘                 │ context  │     │  context     │
                                         └──────────┘     └──────┬───────┘
                                                                │ Agent reads
                                                                ▼
                                         ┌──────────────────────────────┐
                                         │  Final daily report (.md)     │
                                         │  + optional QQ notification   │
                                         └──────────────────────────────┘
```

## Quick Start

```bash
pip install -e .
daily-report init
daily-report collect --date yesterday
daily-report render --date yesterday
```

Without `pip install`, run from the repository with:

```bash
PYTHONPATH=src python -m multi_agent_daily_report.cli collect --date yesterday
PYTHONPATH=src python -m multi_agent_daily_report.cli render --date yesterday
```

## Use `/multi-agent-daily-report` in Claude (Slash Command)

This repo includes a Claude skill (see `skills/SKILL.md`). Once installed, you can type `/multi-agent-daily-report ...` in a Claude chat and have Claude run collection/rendering, read the context, and generate the final daily report.

### 1) Install the skill into `~/.claude/skills/`

Recommended: symlink the `skills/` directory so changes in this repo take effect immediately:

```bash
mkdir -p ~/.claude/skills
ln -snf "$(pwd)/skills" ~/.claude/skills/multi-agent-daily-report
```

Or copy it (if you prefer a pinned snapshot):

```bash
mkdir -p ~/.claude/skills/multi-agent-daily-report
cp skills/SKILL.md ~/.claude/skills/multi-agent-daily-report/SKILL.md
```

### 2) Use it in a Claude chat

Basic usage (no args defaults to `yesterday`):

```bash
/multi-agent-daily-report
```

Examples:

```bash
/multi-agent-daily-report yesterday
/multi-agent-daily-report today
/multi-agent-daily-report 2026-04-24
/multi-agent-daily-report 2026-04-24 --sources claude,codex
/multi-agent-daily-report yesterday --sources claude,codex,cursor,git --compact
/multi-agent-daily-report 2026-04-26 --compact --send qq
```

Arguments (kept consistent with `skills/SKILL.md`):

- **date**: `today` / `yesterday` / `YYYY-MM-DD` (defaults to `yesterday`)
- **sources**: `--sources claude,codex,cursor,git` (defaults to all enabled)
- **compact**: `--compact` (deduplicated/aggregated context; recommended)
- **send**: `--send qq` (send the final report file via QQ bot; requires `notify.qq.*` config)

### 3) Prerequisites

- The slash command expects the `daily-report` CLI to be available; if not, it will run `pip install -e .` in the project directory.
- Requires **Python 3.10+**. If system Python is older, the skill falls back to `PYTHONPATH=src python -m multi_agent_daily_report.cli ...`.
- Outputs: context `reports/YYYY-MM-DD_context.md`, final report `final_reports/YYYY-MM-DD.md`.

### 4) Troubleshooting

- **`/multi-agent-daily-report` not found in Claude**: ensure `~/.claude/skills/multi-agent-daily-report/SKILL.md` exists. If you used a symlink, verify it still points to this repo’s `skills/` directory.
- **`daily-report: command not found`**: run `pip install -e .` in the repo root, then verify with `command -v daily-report`.
- **Python version error (< 3.10)**: install/run with a Python 3.10+ interpreter (venv recommended), or use the module form `PYTHONPATH=src python -m multi_agent_daily_report.cli ...` with a compatible Python.

## Sources

- **Claude Code** — session history from `~/.claude/projects/**/*.jsonl`
- **Codex** — local history (`history.jsonl`) and thread records (`state_5.sqlite`)
- **Cursor** — workspace metadata and local file history under `~/Library/Application Support/Cursor/User`
- **Git** — commit log from configured repos (auto-discovers repos under `~/work_space`)

Collectors are intentionally conservative and skip missing sources.

## Configuration

The CLI reads `cfg/config.yaml` first (project-level), falling back to `~/.config/multi-agent-daily-report/config.yaml`.

```bash
daily-report init              # generate default config
daily-report init --path ~/.config/multi-agent-daily-report/config.yaml
```

Config key highlights:

| Key | Description |
| --- | --- |
| `sources.*.enabled` | Toggle individual collectors |
| `sources.*.path` | Override default source paths |
| `output.directory` | Where reports are saved |
| `output.timezone` | Timezone for date filtering (default: Asia/Shanghai) |
| `state.backend` | `sqlite` (default) or `mysql` |
| `notify.*` | QQ official bot notification settings |

See `cfg/config.example.yaml` for the full reference.

## CLI Commands

| Command | Description |
| --- | --- |
| `daily-report init` | Generate default config |
| `daily-report collect --date <date>` | Collect activities to JSON |
| `daily-report render --date <date>` | Render Markdown context |
| `daily-report render --date <date> --compact` | Render deduplicated/aggregated context |
| `daily-report collect --sources claude,git` | Collect from specific sources only |
| `daily-report send --date <date> --channel qq` | Send report file via QQ Bot |

Dates support: `today`, `yesterday`, `YYYY-MM-DD`.

## Recommended Workflow

```bash
# 1. Collect activities from all sources
daily-report collect --date yesterday

# 2. Render compact context
daily-report render --date yesterday --compact

# 3. Have your current agent read reports/YYYY-MM-DD_context.md, generate the final report → final_reports/YYYY-MM-DD.md
```

## Skill Integration

The included skill (`skills/SKILL.md`) teaches any agent (Claude Code, Codex, Cursor) how to:

- Run the CLI commands to collect and render context
- Read the rendered context and extract technical signals
- Generate a well-structured daily report in Chinese or English
- Optionally send the report via QQ Bot

This means the same CLI can be reused across multiple agents — each just needs a thin skill/prompt wrapper.

## Output Files

| Directory | File | Description |
|-----------|------|-------------|
| `reports/` | `YYYY-MM-DD.json` | Raw activity data (collect) |
| `reports/` | `YYYY-MM-DD_context.md` | Agent-readable context (render) |
| `final_reports/` | `YYYY-MM-DD.md` | Final human-readable daily report (generated by agent) |

Intermediate activity data is also stored in SQLite (`~/.config/multi-agent-daily-report/drep.db`) for cross-date queries.

## Workday Scheduled Sending

The script `scripts/claude-send-yesterday-qq.sh` checks whether today is a Chinese workday before sending:

- Weekends and statutory holidays are skipped
- Adjusted workdays (e.g., Saturday makeup days) are treated as workdays

```bash
python3 scripts/workday.py should-send --date 2026-04-27
python3 scripts/workday.py previous-workday --date 2026-04-27
```

Calendar files are in `cfg/calendar/`.

## Privacy & Security

- No remote model calls by default
- Only summary context is generated — no requirement to upload raw conversation logs
- The skill instructs agents to avoid verbatim sensitive prompts, preferring project-level summaries
- Secrets (QQ keys, DB passwords) are resolved from environment variables, not stored in committed config

## Development

```bash
pip install -e ".[dev]"    # install with dev tools
ruff check src/ tests/      # lint
mypy src/                   # type check
pytest tests/ -v            # run tests
```

## Limitations

- Claude and Codex local records are well-supported.
- Cursor is based on workspace metadata and file history — full Cursor Chat/Agent conversation coverage is not guaranteed.
- The current `render` output is "activity context", not a final report. Final reports should be generated by an agent following `skills/SKILL.md`.

## License

MIT — see [LICENSE](LICENSE).
