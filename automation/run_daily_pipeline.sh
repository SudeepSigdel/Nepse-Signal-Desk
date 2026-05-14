#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${PROJECT_ROOT:-/opt/final-year-project}"
SOURCE="${SOURCE:-sharesansar}"
DELAY="${DELAY:-0.2}"

PYTHON_EXE="$PROJECT_ROOT/venv/bin/python"
RUNNER="$PROJECT_ROOT/automation/daily_pipeline.py"

if [[ ! -x "$PYTHON_EXE" ]]; then
  echo "Python executable not found: $PYTHON_EXE"
  exit 1
fi

if [[ ! -f "$RUNNER" ]]; then
  echo "Runner script not found: $RUNNER"
  exit 1
fi

mkdir -p "$PROJECT_ROOT/outputs/logs"
cd "$PROJECT_ROOT"

MPLBACKEND=Agg PYTHONUNBUFFERED=1 \
  "$PYTHON_EXE" "$RUNNER" --source "$SOURCE" --delay "$DELAY" "$@"
