#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="${0:A:h}"
PROJECT_DIR="${SCRIPT_DIR:h}"
LOG_DIR="$PROJECT_DIR/logs"

PYTHON="$(command -v python3 || echo /usr/bin/python3)"
CLAUDE="$(command -v claude || echo /opt/homebrew/bin/claude)"
mkdir -p "$LOG_DIR"

cd "$PROJECT_DIR"

DECISION="$($PYTHON scripts/workday.py should-send)"
echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] workday decision: $DECISION" >> "$LOG_DIR/claude-send-yesterday-qq.log"

SHOULD_SEND="$($PYTHON -c 'import json,sys; print(json.loads(sys.argv[1])["send"])' "$DECISION")"
if [[ "$SHOULD_SEND" != "True" ]]; then
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] skip non-workday" >> "$LOG_DIR/claude-send-yesterday-qq.log"
  exit 0
fi

REPORT_DATE="$($PYTHON -c 'import json,sys; print(json.loads(sys.argv[1])["report_date"])' "$DECISION")"
echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] run report_date=$REPORT_DATE" >> "$LOG_DIR/claude-send-yesterday-qq.log"

exec "$CLAUDE" \
  -p "/multi-agent-daily-report $REPORT_DATE --compact --send qq" \
  --permission-mode dontAsk \
  --allowedTools "Bash,Read,Write" \
  --add-dir "$PROJECT_DIR" \
  >> "$LOG_DIR/claude-send-yesterday-qq.log" 2>&1
