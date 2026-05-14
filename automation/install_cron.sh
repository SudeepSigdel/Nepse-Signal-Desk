#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/opt/final-year-project}"
RUN_AT="${RUN_AT:-16:30}"
SOURCE="${SOURCE:-sharesansar}"
DELAY="${DELAY:-0.2}"

if [[ ! "$RUN_AT" =~ ^[0-2][0-9]:[0-5][0-9]$ ]]; then
  echo "RUN_AT must be HH:MM (24-hour format), got: $RUN_AT"
  exit 1
fi

HH="${RUN_AT%%:*}"
MM="${RUN_AT##*:}"

# Remove leading zeros safely for cron numeric fields.
HH=$((10#$HH))
MM=$((10#$MM))

mkdir -p "$PROJECT_ROOT/outputs/logs"

CRON_CMD="PROJECT_ROOT=\"$PROJECT_ROOT\" SOURCE=\"$SOURCE\" DELAY=\"$DELAY\" /bin/bash \"$PROJECT_ROOT/automation/run_daily_pipeline.sh\" >> \"$PROJECT_ROOT/outputs/logs/cron_daily_pipeline.log\" 2>&1"
CRON_ENTRY="$MM $HH * * * $CRON_CMD"

( crontab -l 2>/dev/null | grep -v "run_daily_pipeline.sh" || true; echo "$CRON_ENTRY" ) | crontab -

echo "Installed daily cron job at $RUN_AT"
echo "$CRON_ENTRY"
