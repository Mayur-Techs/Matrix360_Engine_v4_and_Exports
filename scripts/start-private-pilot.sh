#!/bin/sh
# Run the HTTP console and its local worker in one intentional single-instance
# pilot container. Multi-tenant cloud production needs separate durable adapters.
set -eu

python -m services.worker.runner --interval "${MATRIX_WORKER_INTERVAL:-1}" &
worker_pid=$!
uvicorn services.api.app:app --host 0.0.0.0 --port "${PORT:-8000}" &
api_pid=$!

shutdown() {
  kill "$api_pid" "$worker_pid" 2>/dev/null || true
  wait "$api_pid" "$worker_pid" 2>/dev/null || true
}
trap shutdown INT TERM EXIT

while kill -0 "$api_pid" 2>/dev/null && kill -0 "$worker_pid" 2>/dev/null; do
  sleep 1
done
exit 1
