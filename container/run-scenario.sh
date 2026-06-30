#!/bin/sh
set -eu

if [ "${1:-}" = "--help" ]; then
  cat <<'EOF'
Usage: sh container/run-scenario.sh [scenario]

Builds the TinyOS/TOSSIM simulation and runs one scenario.

Environment:
  LOG_FILE    Log path written by sim.py. Default: log.txt
  SKIP_BUILD  Set to 1 to skip make clean && make micaz sim.

Examples:
  sh container/run-scenario.sh baseline
  sh container/run-scenario.sh multihop_chain
  LOG_FILE=logs/multihop.txt sh container/run-scenario.sh multihop_chain
EOF
  exit 0
fi

SCENARIO="${1:-${SCENARIO:-baseline}}"
LOG_FILE="${LOG_FILE:-log.txt}"

if [ "${SKIP_BUILD:-0}" != "1" ]; then
  make clean
  make micaz sim
fi

python sim.py "$SCENARIO" --log "$LOG_FILE"
python analyze_log.py "$SCENARIO" --log "$LOG_FILE"
