#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)

HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8080}
PYTHON_BIN=${PYTHON_BIN:-python3}

cd "$REPO_ROOT"
exec "$PYTHON_BIN" ui/server.py --host "$HOST" --port "$PORT"
