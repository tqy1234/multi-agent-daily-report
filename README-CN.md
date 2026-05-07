# Multi Agent Daily Report

[![CI](https://github.com/user/multi-agent-daily-report/actions/workflows/ci.yml/badge.svg)](https://github.com/user/multi-agent-daily-report/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

一个本地优先的多 Agent 日报 CLI。它会从 Claude Code、Codex、Cursor、Git 等来源采集活动记录，整理成结构化上下文，再交给 Codex、Claude、Cursor 或其他智能体总结成日报。

## 设计思路

- **CLI** 负责采集、清洗和标准化数据。
- **Skill / Prompt** 负责指导当前智能体生成日报。
- **默认不调用远程模型**，避免强绑定某个模型供应商，也降低成本和隐私风险。

## 架构

```text
~/.claude/projects/  ──┐
~/.codex/            ──┤  采集器         ┌──────────┐     ┌──────────────┐
Cursor workspace     ──┼──────────────►  │  JSON    │ ──► │  Markdown    │
Git repos            ──┘                 │ context  │     │  context     │
                                         └──────────┘     └──────┬───────┘
                                                                │ Agent 读取
                                                                ▼
                                         ┌──────────────────────────────┐
                                         │  最终日报 (.md)               │
                                         │  + 可选 QQ 通知               │
                                         └──────────────────────────────┘
```

## 快速开始

```bash
pip install -e .
daily-report init
daily-report collect --date yesterday
daily-report render --date yesterday
```

如果不想安装，也可以在项目根目录直接运行：

```bash
PYTHONPATH=src python -m multi_agent_daily_report.cli collect --date yesterday
PYTHONPATH=src python -m multi_agent_daily_report.cli render --date yesterday
```

## 在 Claude 里用 `/multi-agent-daily-report`（Slash Command）

本项目自带一个 Claude Skill（见 `skills/SKILL.md`），安装后你可以在 Claude 对话里直接输入 `/multi-agent-daily-report ...` 让 Claude 自动执行采集/渲染/总结，并产出最终日报文件。

### 1) 安装 Skill 到 `~/.claude/skills/`

推荐使用软链接（便于你修改本仓库的 `skills/SKILL.md` 后立即生效）：

```bash
mkdir -p ~/.claude/skills
ln -snf "$(pwd)/skills" ~/.claude/skills/multi-agent-daily-report
```

或者复制一份（适合你只想固定版本）：

```bash
mkdir -p ~/.claude/skills/multi-agent-daily-report
cp skills/SKILL.md ~/.claude/skills/multi-agent-daily-report/SKILL.md
```

### 2) 在 Claude 对话里使用

基础用法（不带参数默认 `yesterday`）：

```bash
/multi-agent-daily-report
```

常用示例：

```bash
/multi-agent-daily-report yesterday
/multi-agent-daily-report today
/multi-agent-daily-report 2026-04-24
/multi-agent-daily-report 2026-04-24 --sources claude,codex
/multi-agent-daily-report yesterday --sources claude,codex,cursor,git --compact
/multi-agent-daily-report 2026-04-26 --compact --send qq
```

参数说明（与 `skills/SKILL.md` 保持一致）：

- **日期**：`today` / `yesterday` / `YYYY-MM-DD`（省略则默认 `yesterday`）
- **sources**：`--sources claude,codex,cursor,git`（省略则采集全部已启用来源）
- **compact**：`--compact`（渲染更聚合/去重的上下文，建议默认使用）
- **send**：`--send qq`（生成最终日报后发送 QQ 文件附件，需先配置 `notify.qq.*`）

### 3) 运行前提（非常重要）

- Slash 命令执行时会尝试调用 `daily-report` CLI；若不可用，会在项目目录执行 `pip install -e .` 安装。
- 需要 **Python 3.10+**。如果你的系统 Python 版本偏老，Skill 会回退到 `PYTHONPATH=src python -m multi_agent_daily_report.cli ...` 的方式运行。
- 生成文件：上下文 `reports/YYYY-MM-DD_context.md`，最终日报 `final_reports/YYYY-MM-DD.md`。

### 4) 常见问题（Troubleshooting）

- **Claude 里提示找不到 `/multi-agent-daily-report`**：检查 `~/.claude/skills/multi-agent-daily-report/SKILL.md` 是否存在；如果你用的是软链接，确认链接目标仍指向当前仓库的 `skills/` 目录。
- **运行时提示 `daily-report: command not found`**：在仓库根目录执行 `pip install -e .`，然后用 `command -v daily-report` 验证是否安装到当前环境的 PATH。
- **Python 版本报错（< 3.10）**：用 `python3.10+` 的解释器创建虚拟环境后在该环境里安装；或直接使用 README 里的 `PYTHONPATH=src python -m multi_agent_daily_report.cli ...` 方式运行（确保该 `python` 版本满足 3.10+）。

## 数据源

- **Claude Code** — `~/.claude/projects/**/*.jsonl` 会话历史
- **Codex** — `~/.codex/history.jsonl` 本地历史与 `state_5.sqlite` 线程记录
- **Cursor** — `~/Library/Application Support/Cursor/User` 下工作区元数据和本地文件历史
- **Git** — 配置仓库的 commit 记录（未配置时自动发现 `~/work_space` 下一级仓库）

采集器采用保守策略：如果某个数据源不存在或无法读取，会自动跳过，不会中断整个日报流程。

## 配置

项目根目录优先读取 `cfg/config.yaml`，否则回退到 `~/.config/multi-agent-daily-report/config.yaml`。

```bash
daily-report init              # 生成默认配置
daily-report init --path ~/.config/multi-agent-daily-report/config.yaml
```

主要配置项：

| 配置 | 说明 |
| --- | --- |
| `sources.*.enabled` | 开关单个采集器 |
| `sources.*.path` | 覆盖默认数据源路径 |
| `output.directory` | 报告输出目录 |
| `output.timezone` | 日期过滤时区（默认：Asia/Shanghai） |
| `state.backend` | 状态存储：`sqlite`（默认）或 `mysql` |
| `notify.*` | QQ 官方 Bot 通知配置 |

完整参考见 `cfg/config.example.yaml`。

## CLI 命令

| 命令 | 说明 |
| --- | --- |
| `daily-report init` | 生成默认配置 |
| `daily-report collect --date <date>` | 采集活动到 JSON |
| `daily-report render --date <date>` | 渲染 Markdown 上下文 |
| `daily-report render --date <date> --compact` | 渲染去重/聚合后的上下文 |
| `daily-report collect --sources claude,git` | 只采集指定来源 |
| `daily-report send --date <date> --channel qq` | 发送日报文件到 QQ Bot |

日期支持：`today`、`yesterday`、`YYYY-MM-DD`。

## 推荐工作流

```bash
# 1. 采集昨天所有来源的活动
daily-report collect --date yesterday

# 2. 渲染去重后的上下文
daily-report render --date yesterday --compact

# 3. 让当前 Agent 读取 reports/YYYY-MM-DD_context.md，生成最终日报 → final_reports/YYYY-MM-DD.md
```

## Skill 的作用

CLI 是真正干活的数据引擎；Skill 是给智能体看的使用说明。

典型分工是：

- **CLI**：收集 Claude / Codex / Cursor / Git 等来源的数据。
- **Skill**：规定日报结构、隐私规则、去重规则和追问策略。
- **当前 Agent**：理解上下文，合并重复事项，生成自然语言日报。

这意味着同一个 CLI 可以被多个 Agent 复用：Codex、Claude、Cursor 只需要各自有一层很薄的 Skill / Rule / Prompt 包装。

## 输出文件

| 目录 | 文件 | 说明 |
|------|------|------|
| `reports/` | `YYYY-MM-DD.json` | 原始活动数据（collect） |
| `reports/` | `YYYY-MM-DD_context.md` | Agent 可读上下文（render） |
| `final_reports/` | `YYYY-MM-DD.md` | 最终人可读日报（Agent 生成） |

中间态活动数据同时写入 SQLite（`~/.config/multi-agent-daily-report/drep.db`），支持跨日期查询。

## 工作日定时发送

定时脚本 `scripts/claude-send-yesterday-qq.sh` 会先判断北京时间当天是否为工作日：

- 如果当天是周末或法定节假日，直接跳过，不发送。
- 如果当天是工作日，发送"上一个工作日"的日报。
- 如果当天是调休工作日，即使是周六/周日也会发送。

工作日判断使用本地日历文件：

```bash
python3 scripts/workday.py should-send --date 2026-04-27
python3 scripts/workday.py previous-workday --date 2026-04-27
```

日历文件在 `cfg/calendar/` 目录下。

## 隐私与安全

- 默认不调用远程模型。
- 默认只生成摘要上下文，不要求上传原始会话记录。
- Skill 中要求避免原文引用敏感 prompt，优先使用项目级摘要。
- 密钥（QQ key、数据库密码）通过环境变量注入，不存储在已提交的配置文件中。

## 开发

```bash
pip install -e ".[dev]"    # 安装开发依赖
ruff check src/ tests/      # 代码检查
mypy src/                   # 类型检查
pytest tests/ -v            # 运行测试
```

## 当前限制

- Claude 和 Codex 的本地记录解析已经比较直接可用。
- Cursor 目前主要基于 workspace metadata 和 file history，未保证完整覆盖 Cursor Chat / Agent 对话。
- 当前 `render` 输出仍偏"活动上下文"，还不是最终日报；最终日报建议由 Agent 根据 `skills/SKILL.md` 生成。

## License

MIT — 见 [LICENSE](LICENSE)。
