---
name: multi-agent-daily-report
description: 生成跨 Agent 日报：采集 Claude Code、Codex、Cursor、Git 等本地活动，渲染上下文，并总结为日报
user-invocable: true
argument-hint: "[today|yesterday|YYYY-MM-DD] [--sources claude,codex,cursor,git] [--compact] [--send qq]"
allowed-tools: Bash, Read, Write
---

用户希望生成跨 Agent 日报、站会更新、工作总结，或查看某天的 Claude/Codex/Cursor/Git 活动摘要。请按以下流程处理。

## 输入

用户传入的参数：`$ARGUMENTS`

支持形式：

```bash
/multi-agent-daily-report
/multi-agent-daily-report yesterday
/multi-agent-daily-report today
/multi-agent-daily-report 2026-04-24
/multi-agent-daily-report 2026-04-24 --sources claude,codex
/multi-agent-daily-report yesterday --sources claude,codex,cursor,git --compact
/multi-agent-daily-report 2026-04-26 --compact --send qq
```

## 参数解析

从 `$ARGUMENTS` 中解析：

- **日期**：可选。支持 `today`、`yesterday`、`YYYY-MM-DD`。如果没有提供，默认使用 `yesterday`。
- **sources**：可选。格式为 `--sources claude,codex,cursor,git`。如果没有提供，默认采集全部已启用来源。
- **compact**：可选。出现 `--compact` 时，渲染阶段使用去重/聚合后的上下文。默认建议开启 compact，除非用户明确要求 raw/raw context/原始上下文。
- **send**：可选。格式为 `--send qq`。出现时，在生成最终日报 Markdown 后调用 `daily-report send --channel qq`，以 `.md` 文件附件形式发送到配置里的 QQ 官方 Bot 目标。

如果用户输入无法解析日期，先使用 `yesterday`，并在最终结果里说明假设。

## 常量定义

- 项目目录：通过 `git rev-parse --show-toplevel` 获取，或从 SKILL 文件所在路径向上两级的 `skills/../..` 推断
- 默认报告目录：项目目录下的 `reports/`
- 配置文件：`~/.config/multi-agent-daily-report/config.yaml`
- CLI 命令：`daily-report`

## 前置检查

1. 检查 `daily-report` 命令是否可用：

```bash
command -v daily-report
```

1. 如果不可用，在项目目录安装：

```bash
cd <PROJECT_DIR> && pip install -e .
```

1. 如果仍不可用，使用 Python 模块方式运行：

```bash
cd <PROJECT_DIR> && PYTHONPATH=src python -m multi_agent_daily_report.cli <command>
```

## 执行流程

### 步骤 1：确定运行参数

根据 `$ARGUMENTS` 得到：

- `REPORT_DATE`：默认 `yesterday`
- `SOURCES_ARG`：如果用户指定 sources，则为 `--sources xxx`，否则为空
- `RENDER_MODE`：默认 `--compact`；如果用户明确要原始上下文，则为空
- `SEND_CHANNEL`：如果用户传入 `--send qq`，则为 `qq`；否则为空

### 步骤 2：采集活动

在项目目录执行：

```bash
cd <PROJECT_DIR>
daily-report collect --date <REPORT_DATE> <SOURCES_ARG> --output reports/<REPORT_DATE>.json
```

注意：如果 `REPORT_DATE` 是 `today` 或 `yesterday`，输出文件名应使用实际日期。可以先运行 collect，再根据输出信息读取实际路径；必要时用 `date` 计算或查看命令输出。

### 步骤 3：渲染上下文

默认使用 compact：

```bash
daily-report render --date <REPORT_DATE> --input reports/<实际日期>.json --output reports/<实际日期>_context.md --compact
```

如果用户明确要求 raw/raw context/原始上下文，则不要加 `--compact`：

```bash
daily-report render --date <REPORT_DATE> --input reports/<实际日期>.json --output reports/<实际日期>_context.md
```

### 步骤 4：读取上下文

读取生成的 Markdown：

```bash
cat reports/<实际日期>_context.md
```

阅读上下文时，重点提取以下信号：
- **Git**：commit message、改动文件路径、diff 中的函数/类名。
- **Claude/Codex**：对话里出现的报错信息（errno、error code、stack trace 关键行）、执行的命令、涉及的配置项/API/SQL/文件路径。
- **Cursor**：被编辑的具体文件名（`Files:` 字段）及对应项目。

不要把原始上下文整段照搬给用户，要基于上述信号提炼成日报。

### 步骤 5：输出日报

**写作规则（每条必须满足）：**

- 每项工作写 **恰好 2 句话**：第 1 句说"做了什么 / 解决了什么"，第 2 句说"用了什么技术手段 / 遇到什么关键错误 / 最终结果或决策"。
- 必须保留具体技术词汇：函数名、文件名、表名、错误码、配置字段、SQL 关键字、框架/工具版本、端口号、socket 路径等，不要替换成泛化描述。
- 禁止空洞句式：不能写"处理了某个问题"、"完成了相关功能"、"进行了调研"——必须说清楚**是什么问题 / 哪个功能 / 调研了什么结论**。
- 证据（commit hash、文件路径、thread_id）统一归入 Notes 区，正文只保留人可读的技术摘要。

**坏例子 vs 好例子：**

| 坏（粒度太粗） | 好（2 句 + 技术点） |
|---|---|
| 修了 MySQL 连接问题 | MySQL 启动失败，原因是 `ibdata1` 被 3307 端口的旧实例持有文件锁（errno 35）。停止冲突进程后，默认 socket `/tmp/mysql.sock` 恢复，root 无密码登录成功。 |
| 整理了 Claude skills 目录 | 对比 `~/xhs-claude-skills/` 与 `~/.claude/skills/`，确认 `xhs`/`xhs-analyze`/`xhs-batch`/`xhs-cover` 四个 skill 已完整集成后删除源目录（释放约 200 KB）。同步评估 `~/claude-skills/`（37 MB）中 `executive-mentor`、`playwright-pro` 等是否可迁移到统一路径。 |
| 看了一些代码 | 在 Cursor 中打开 `cc-recovered-main/src/QueryEngine.ts`，进行了 2 次历史版本编辑。该文件属于轻量 Claude Code 复刻项目的查询引擎模块。 |

使用以下格式输出：

```markdown
# Daily Report - YYYY-MM-DD

## Yesterday / 当日完成
- **[项目名] 简短标题**：第 1 句，做了什么/解决了什么。第 2 句，具体技术手段/错误/结果/决策。
- **[项目名] 简短标题**：...

## Today / 下一步
- **[项目名]**：下一步行动，尽量具体到任务/文件/接口级别。

## Blockers / 阻塞
- 无 / 具体说明（包含错误信息或依赖项）

## Notes / 证据与备注
- 来源：Claude/Codex/Cursor/Git
- commit hash、文件路径、session_id、关键命令或配置变更
```

如果用户要中文，默认输出中文。

### 步骤 6：保存最终日报

将你在步骤 5 生成的最终日报写入文件。注意：`reports/<实际日期>_context.md` 是 CLI 渲染的 Agent 上下文，不是最终日报；最终日报必须单独保存到 `final_reports/` 目录：

```bash
final_reports/<实际日期>.md
```

使用 Write 工具写入完整最终日报内容，不要只写摘要。最终日报文件应包含步骤 5 的完整 Markdown 输出。

### 步骤 7：可选发送到 QQ

如果 `$ARGUMENTS` 包含 `--send qq`，必须发送最终日报文件，而不是上下文文件；`daily-report send --channel qq` 默认从 `final_reports/` 读取 `.md` 作为 QQ 文件附件发送，不要把 Markdown 正文贴到聊天框：

```bash
daily-report send --date <REPORT_DATE> --input final_reports/<实际日期>.md --channel qq
```

发送后告诉用户：

- 发送目标：QQ 官方 Bot 配置里的 `notify.qq.target_id`
- 发送文件附件：`final_reports/<实际日期>.md`
- 上下文文件：`reports/<实际日期>_context.md`
- 如果发送失败，保留错误信息并提示检查 QQ Bot 主动消息配额、AppSecret、target_id。

## 隐私规则

- 不包含无关个人项目，除非用户明确要求。
- 不原文引用敏感 prompt、密钥、数据库密码、cookie、token。
- 如果上下文里出现明显敏感命令，只描述动作，不暴露参数。

## 来源优先级

- Git commit：优先作为"实际代码变更"的事实依据。
- Claude/Codex/Cursor 会话：用于补充意图、调研过程、验证过程和未提交工作。
- Cursor file history：用于提示文件活动，但不要过度解读为已完成任务。

## 命令参考


| 命令                                            | 说明              |
| --------------------------------------------- | --------------- |
| `daily-report init`                           | 生成默认配置          |
| `daily-report collect --date <date>`          | 采集活动到 JSON      |
| `daily-report render --date <date>`           | 渲染 Markdown 上下文 |
| `daily-report render --date <date> --compact` | 渲染去重/聚合后的上下文    |
| `daily-report collect --sources claude,git`   | 只采集指定来源         |
| `daily-report send --date <date> --channel qq` | 发送日报 Markdown 文件附件到 QQ 官方 Bot |
| `daily-report send --input final_reports/<date>.md --channel qq` | 发送最终日报文件附件到 QQ 官方 Bot |


日期支持：`today`、`yesterday`、`YYYY-MM-DD`。
