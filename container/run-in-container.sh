#!/bin/sh
set -eu

PROJECT_ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
IMAGE="${IMAGE:-tinyos-request-reply:local}"
SCENARIO="${1:-baseline}"
LOG_FILE="${LOG_FILE:-log.txt}"

docker build -t "$IMAGE" "$PROJECT_ROOT"
docker run --rm \
  -v "$PROJECT_ROOT:/app" \
  -w /app \
  -e "LOG_FILE=$LOG_FILE" \
  "$IMAGE" "$SCENARIO"
